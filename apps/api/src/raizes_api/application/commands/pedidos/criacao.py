import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime

from raizes_api.application.autorizacao import VerificacaoDeEscopo
from raizes_api.application.commands.pedidos.efeitos import (
    AGREGADO_PEDIDO,
    auditoria_do_pedido,
    evento,
    itens_do_evento,
    registrar_movimentacoes,
)
from raizes_api.application.idempotencia import RespostaIdempotente, reservar_ou_reproduzir
from raizes_api.application.ports.auditoria import AcaoAuditoria
from raizes_api.application.ports.catalogo import Movimentacao
from raizes_api.application.ports.idempotencia import ChaveIdempotente, RespostaGravada
from raizes_api.application.ports.leitura import ItemDetalhe, PedidoDetalhe
from raizes_api.application.ports.relogio import Relogio
from raizes_api.application.ports.unit_of_work import UnitOfWork
from raizes_api.domain.catalogo.catalogo import OfertaNaUnidade, TipoMovimentacao
from raizes_api.domain.catalogo.erros import (
    ProdutoIndisponivelNaUnidade,
    ProdutoNaoEncontrado,
    UnidadeNaoEncontrada,
)
from raizes_api.domain.compartilhado.atores import AtorAutenticado, TipoAtor
from raizes_api.domain.compartilhado.canais import CanalPedido
from raizes_api.domain.compartilhado.contato import Telefone
from raizes_api.domain.compartilhado.dinheiro import Dinheiro
from raizes_api.domain.compartilhado.erros import DetalheErro
from raizes_api.domain.compartilhado.tempo import data_local
from raizes_api.domain.pedidos.canal import validar_criacao_pelo_ator
from raizes_api.domain.pedidos.erros import EstoqueInsuficiente
from raizes_api.domain.pedidos.pedido import ItemPedido, Pedido

ROTA_CRIAR_PEDIDO = "POST /pedidos"
ENTIDADE_UNIDADE = "UNIDADE"

ApresentadorDePedido = Callable[[PedidoDetalhe], RespostaGravada]


@dataclass(frozen=True, slots=True)
class ItemSolicitado:
    produto_id: int
    quantidade: int


@dataclass(frozen=True, slots=True)
class DadosNovoPedido:
    canal: CanalPedido
    unidade_id: int
    itens: tuple[ItemSolicitado, ...]
    telefone_cliente: Telefone | None = None
    observacao: str | None = None


class CriarPedido:
    """Cria o pedido com reserva de estoque, numa única transação idempotente (guideline 03).

    `apresentar` monta a resposta HTTP, que fica gravada junto com a chave para ser reproduzida.
    """

    def __init__(
        self,
        uow: UnitOfWork,
        relogio: Relogio,
        escopo: VerificacaoDeEscopo,
        apresentar: ApresentadorDePedido,
    ) -> None:
        self._uow = uow
        self._relogio = relogio
        self._escopo = escopo
        self._apresentar = apresentar

    async def executar(
        self, ator: AtorAutenticado, dados: DadosNovoPedido, chave: ChaveIdempotente
    ) -> RespostaIdempotente:
        validar_criacao_pelo_ator(
            ator, dados.canal, informou_identificacao_cliente=dados.telefone_cliente is not None
        )
        await self._escopo.exigir(
            ator, dados.unidade_id, entidade=ENTIDADE_UNIDADE, entidade_id=str(dados.unidade_id)
        )
        agora = self._relogio.agora()
        async with self._uow as uow:
            reproduzida = await reservar_ou_reproduzir(uow.idempotencia, chave, agora)
            if reproduzida is not None:
                return reproduzida
            pedido = await self._montar_pedido(uow, ator, dados, agora)
            movimentacoes = await _reservar_estoque(uow, pedido, agora)
            await uow.pedidos.adicionar(pedido)
            await _registrar_auditoria_e_evento(uow, pedido)
            await registrar_movimentacoes(uow, pedido, movimentacoes)
            resposta = self._apresentar(detalhe_do_pedido(pedido))
            await uow.idempotencia.concluir(chave, resposta)
            await uow.commit()
        return RespostaIdempotente(status_code=resposta.status_code, corpo=resposta.corpo, reproduzida=False)

    async def _montar_pedido(
        self, uow: UnitOfWork, ator: AtorAutenticado, dados: DadosNovoPedido, agora: datetime
    ) -> Pedido:
        unidade = await uow.catalogo.obter_unidade(dados.unidade_id)
        if unidade is None or not unidade.esta_ativa:
            raise UnidadeNaoEncontrada()
        ofertas = await uow.catalogo.ofertas(unidade.id, [item.produto_id for item in dados.itens])
        precos = _precos_de_venda(dados.itens, ofertas, data_local(agora))
        itens = [
            ItemPedido(
                produto_id=item.produto_id,
                nome_produto=ofertas[item.produto_id].nome_produto,
                quantidade=item.quantidade,
                preco_unitario=precos[item.produto_id],
            )
            for item in dados.itens
        ]
        return Pedido.criar(
            unidade_id=unidade.id,
            canal=dados.canal,
            itens=itens,
            cliente_id=await _cliente_do_pedido(uow, ator, dados.telefone_cliente),
            criado_por=ator,
            observacao=dados.observacao,
            agora=agora,
        )


def _precos_de_venda(
    itens: Sequence[ItemSolicitado], ofertas: Mapping[int, OfertaNaUnidade], hoje: date
) -> dict[int, Dinheiro]:
    inexistentes = [
        DetalheErro(f"itens[{posicao}].produtoId", f"Produto {item.produto_id} não existe.")
        for posicao, item in enumerate(itens)
        if item.produto_id not in ofertas
    ]
    if inexistentes:
        raise ProdutoNaoEncontrado(detalhes=inexistentes)

    precos: dict[int, Dinheiro] = {}
    indisponiveis: list[DetalheErro] = []
    for posicao, item in enumerate(itens):
        preco = ofertas[item.produto_id].preco_em(hoje)
        if preco is None:
            indisponiveis.append(
                DetalheErro(
                    f"itens[{posicao}].produtoId", "Fora do cardápio da unidade, inativo ou fora de época."
                )
            )
        else:
            precos[item.produto_id] = preco
    if indisponiveis:
        raise ProdutoIndisponivelNaUnidade(detalhes=indisponiveis)
    return precos


async def _cliente_do_pedido(
    uow: UnitOfWork, ator: AtorAutenticado, telefone: Telefone | None
) -> uuid.UUID | None:
    """Cliente vem do token; no totem e no balcão, do telefone. Telefone sem cadastro: pedido anônimo."""
    if ator.tipo is TipoAtor.CLIENTE:
        return uuid.UUID(ator.id)
    if telefone is None:
        return None
    cliente = await uow.clientes.obter_por_telefone(telefone)
    return cliente.id if cliente is not None and cliente.pode_autenticar() else None


async def _reservar_estoque(uow: UnitOfWork, pedido: Pedido, agora: datetime) -> list[Movimentacao]:
    movimentacoes: list[Movimentacao] = []
    faltas: list[tuple[int, DetalheErro]] = []
    for posicao, item in pedido.itens_em_ordem_de_reserva():
        saldo_apos = await uow.estoque.reservar(pedido.unidade_id, item.produto_id, item.quantidade, agora)
        if saldo_apos is None:
            disponivel = await uow.estoque.saldo(pedido.unidade_id, item.produto_id)
            faltas.append((posicao, DetalheErro(f"itens[{posicao}].quantidade", f"Disponível: {disponivel}")))
            continue
        movimentacoes.append(
            Movimentacao(
                tipo=TipoMovimentacao.SAIDA_PEDIDO,
                unidade_id=pedido.unidade_id,
                produto_id=item.produto_id,
                quantidade=-item.quantidade,
                saldo_apos=saldo_apos,
                pedido_id=pedido.id,
            )
        )
    if faltas:
        raise EstoqueInsuficiente(
            detalhes=[detalhe for _, detalhe in sorted(faltas, key=lambda falta: falta[0])]
        )
    return movimentacoes


async def _registrar_auditoria_e_evento(uow: UnitOfWork, pedido: Pedido) -> None:
    await uow.auditoria.registrar(
        auditoria_do_pedido(
            pedido,
            pedido.criado_por,
            AcaoAuditoria.PEDIDO_CRIADO,
            {
                "canalPedido": pedido.canal,
                "status": pedido.status,
                "total": pedido.total.valor,
                "itens": [
                    {"produtoId": item.produto_id, "quantidade": item.quantidade} for item in pedido.itens
                ],
            },
        )
    )
    await uow.outbox.publicar(
        evento(
            pedido,
            "PedidoCriado",
            AGREGADO_PEDIDO,
            str(pedido.id),
            {
                "pedidoId": pedido.id,
                "canalPedido": pedido.canal,
                "clienteId": pedido.cliente_id,
                "total": pedido.total.valor,
                "itens": itens_do_evento(pedido),
                "criadoEm": pedido.criado_em,
            },
        )
    )


def detalhe_do_pedido(pedido: Pedido) -> PedidoDetalhe:
    return PedidoDetalhe(
        id=pedido.id,
        unidade_id=pedido.unidade_id,
        canal=pedido.canal,
        status=pedido.status,
        itens=tuple(
            ItemDetalhe(
                produto_id=item.produto_id,
                nome_produto=item.nome_produto,
                quantidade=item.quantidade,
                preco_unitario=item.preco_unitario.valor,
                subtotal=item.subtotal.valor,
            )
            for item in pedido.itens
        ),
        total=pedido.total.valor,
        observacao=pedido.observacao,
        criado_em=pedido.criado_em,
        atualizado_em=pedido.atualizado_em,
        vinculos=pedido.vinculos,
    )
