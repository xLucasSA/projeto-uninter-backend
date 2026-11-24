"""Consultas direto do banco de escrita (`READ_MODEL_SOURCE=write`): DTOs montados do SQL."""

import uuid
from typing import Any

from sqlalchemy import ColumnElement, Select, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from raizes_api.application.paginacao import Pagina, Paginacao
from raizes_api.application.ports.leitura import (
    FiltroAuditoria,
    FiltroPedidos,
    ItemDetalhe,
    LancamentoResumo,
    MudancaDeStatus,
    OfertaDeCardapio,
    PagamentoResumo,
    PedidoDetalhe,
    PedidoResumo,
    ProdutoResumo,
    RegistroDaTrilha,
    SaldoEstoque,
    UnidadeResumo,
)
from raizes_api.domain.catalogo.catalogo import CategoriaProduto, OfertaNaUnidade
from raizes_api.domain.compartilhado.atores import TipoAtor
from raizes_api.domain.compartilhado.canais import CanalPedido
from raizes_api.domain.compartilhado.dinheiro import Dinheiro
from raizes_api.domain.fidelidade.lancamento import TipoLancamento
from raizes_api.domain.pagamentos.pagamento import FormaPagamento, StatusPagamento
from raizes_api.domain.pedidos.acesso import VinculosDoPedido
from raizes_api.domain.pedidos.status import StatusPedido
from raizes_api.infrastructure.db.modelos import (
    AuditoriaModel,
    CardapioUnidadeModel,
    EstoqueModel,
    HistoricoStatusPedidoModel,
    ItemPedidoModel,
    LancamentoFidelidadeModel,
    PagamentoModel,
    PedidoModel,
    ProdutoModel,
    UnidadeModel,
)


async def _paginar(
    sessao: AsyncSession, consulta: Select[*tuple[Any, ...]], paginacao: Paginacao
) -> tuple[list[Any], int]:
    total = await sessao.scalar(select(func.count()).select_from(consulta.order_by(None).subquery()))
    linhas = await sessao.execute(consulta.limit(paginacao.limite).offset(paginacao.deslocamento))
    return list(linhas), total or 0


class LeituraCatalogoSql:
    def __init__(self, fabrica_sessoes: async_sessionmaker[AsyncSession]) -> None:
        self._fabrica_sessoes = fabrica_sessoes

    async def listar_unidades(self, paginacao: Paginacao) -> Pagina[UnidadeResumo]:
        consulta = select(UnidadeModel).where(UnidadeModel.ativa).order_by(UnidadeModel.codigo)
        async with self._fabrica_sessoes() as sessao:
            linhas, total = await _paginar(sessao, consulta, paginacao)
        return Pagina(
            itens=tuple(_unidade(linha.UnidadeModel) for linha in linhas),
            pagina=paginacao.pagina,
            limite=paginacao.limite,
            total=total,
        )

    async def obter_unidade(self, unidade_id: int) -> UnidadeResumo | None:
        async with self._fabrica_sessoes() as sessao:
            modelo = await sessao.scalar(
                select(UnidadeModel).where(UnidadeModel.id == unidade_id, UnidadeModel.ativa)
            )
        return _unidade(modelo) if modelo else None

    async def ofertas_da_unidade(
        self, unidade_id: int, categoria: CategoriaProduto | None
    ) -> list[OfertaDeCardapio]:
        consulta = (
            select(
                CardapioUnidadeModel,
                ProdutoModel,
                func.coalesce(EstoqueModel.quantidade, 0).label("quantidade"),
            )
            .join(ProdutoModel, ProdutoModel.id == CardapioUnidadeModel.produto_id)
            .outerjoin(
                EstoqueModel,
                and_(
                    EstoqueModel.unidade_id == CardapioUnidadeModel.unidade_id,
                    EstoqueModel.produto_id == CardapioUnidadeModel.produto_id,
                ),
            )
            .where(CardapioUnidadeModel.unidade_id == unidade_id)
            .order_by(ProdutoModel.categoria, ProdutoModel.nome)
        )
        if categoria is not None:
            consulta = consulta.where(ProdutoModel.categoria == categoria.value)
        async with self._fabrica_sessoes() as sessao:
            linhas = list(await sessao.execute(consulta))
        return [
            OfertaDeCardapio(
                oferta=OfertaNaUnidade(
                    produto_id=linha.ProdutoModel.id,
                    nome_produto=linha.ProdutoModel.nome,
                    produto_ativo=linha.ProdutoModel.ativo,
                    preco=Dinheiro(linha.CardapioUnidadeModel.preco),
                    cardapio_ativo=linha.CardapioUnidadeModel.ativo,
                    disponivel_de=linha.CardapioUnidadeModel.disponivel_de,
                    disponivel_ate=linha.CardapioUnidadeModel.disponivel_ate,
                ),
                descricao=linha.ProdutoModel.descricao,
                categoria=CategoriaProduto(linha.ProdutoModel.categoria),
                quantidade_em_estoque=linha.quantidade,
            )
            for linha in linhas
        ]

    async def listar_produtos(
        self, categoria: CategoriaProduto | None, paginacao: Paginacao
    ) -> Pagina[ProdutoResumo]:
        consulta = select(ProdutoModel).where(ProdutoModel.ativo).order_by(ProdutoModel.nome)
        if categoria is not None:
            consulta = consulta.where(ProdutoModel.categoria == categoria.value)
        async with self._fabrica_sessoes() as sessao:
            linhas, total = await _paginar(sessao, consulta, paginacao)
        return Pagina(
            itens=tuple(_produto(linha.ProdutoModel) for linha in linhas),
            pagina=paginacao.pagina,
            limite=paginacao.limite,
            total=total,
        )

    async def obter_produto(self, produto_id: int) -> ProdutoResumo | None:
        async with self._fabrica_sessoes() as sessao:
            modelo = await sessao.scalar(
                select(ProdutoModel).where(ProdutoModel.id == produto_id, ProdutoModel.ativo)
            )
        return _produto(modelo) if modelo else None


class LeituraEstoqueSql:
    def __init__(self, fabrica_sessoes: async_sessionmaker[AsyncSession]) -> None:
        self._fabrica_sessoes = fabrica_sessoes

    async def saldos(self, unidade_id: int, paginacao: Paginacao) -> Pagina[SaldoEstoque]:
        consulta = (
            select(EstoqueModel, ProdutoModel)
            .join(ProdutoModel, ProdutoModel.id == EstoqueModel.produto_id)
            .where(EstoqueModel.unidade_id == unidade_id)
            .order_by(ProdutoModel.nome)
        )
        async with self._fabrica_sessoes() as sessao:
            linhas, total = await _paginar(sessao, consulta, paginacao)
        return Pagina(
            itens=tuple(
                SaldoEstoque(
                    produto_id=linha.ProdutoModel.id,
                    sku=linha.ProdutoModel.sku,
                    nome_produto=linha.ProdutoModel.nome,
                    quantidade=linha.EstoqueModel.quantidade,
                    atualizado_em=linha.EstoqueModel.atualizado_em,
                )
                for linha in linhas
            ),
            pagina=paginacao.pagina,
            limite=paginacao.limite,
            total=total,
        )


class LeituraPedidosSql:
    def __init__(self, fabrica_sessoes: async_sessionmaker[AsyncSession]) -> None:
        self._fabrica_sessoes = fabrica_sessoes

    async def listar(self, filtro: FiltroPedidos, paginacao: Paginacao) -> Pagina[PedidoResumo]:
        consulta = _filtrar(select(PedidoModel), filtro).order_by(
            PedidoModel.criado_em.desc(), PedidoModel.id
        )
        async with self._fabrica_sessoes() as sessao:
            linhas, total = await _paginar(sessao, consulta, paginacao)
        return Pagina(
            itens=tuple(
                PedidoResumo(
                    id=linha.PedidoModel.id,
                    unidade_id=linha.PedidoModel.unidade_id,
                    canal=CanalPedido(linha.PedidoModel.canal_pedido),
                    status=StatusPedido(linha.PedidoModel.status),
                    total=linha.PedidoModel.total,
                    criado_em=linha.PedidoModel.criado_em,
                )
                for linha in linhas
            ),
            pagina=paginacao.pagina,
            limite=paginacao.limite,
            total=total,
        )

    async def obter(self, pedido_id: uuid.UUID) -> PedidoDetalhe | None:
        async with self._fabrica_sessoes() as sessao:
            pedido = await sessao.get(PedidoModel, pedido_id)
            if pedido is None:
                return None
            itens = await sessao.scalars(
                select(ItemPedidoModel)
                .where(ItemPedidoModel.pedido_id == pedido_id)
                .order_by(ItemPedidoModel.id)
            )
            return PedidoDetalhe(
                id=pedido.id,
                unidade_id=pedido.unidade_id,
                canal=CanalPedido(pedido.canal_pedido),
                status=StatusPedido(pedido.status),
                itens=tuple(
                    ItemDetalhe(
                        produto_id=item.produto_id,
                        nome_produto=item.nome_produto,
                        quantidade=item.quantidade,
                        preco_unitario=item.preco_unitario,
                        subtotal=item.subtotal,
                    )
                    for item in itens
                ),
                total=pedido.total,
                observacao=pedido.observacao,
                criado_em=pedido.criado_em,
                atualizado_em=pedido.atualizado_em,
                vinculos=VinculosDoPedido(
                    unidade_id=pedido.unidade_id,
                    cliente_id=pedido.cliente_id,
                    criado_por_tipo=TipoAtor(pedido.criado_por_tipo),
                    criado_por_id=pedido.criado_por_id,
                ),
            )

    async def historico(self, pedido_id: uuid.UUID) -> list[MudancaDeStatus]:
        async with self._fabrica_sessoes() as sessao:
            mudancas = await sessao.scalars(
                select(HistoricoStatusPedidoModel)
                .where(HistoricoStatusPedidoModel.pedido_id == pedido_id)
                .order_by(HistoricoStatusPedidoModel.ocorrido_em, HistoricoStatusPedidoModel.id)
            )
            return [
                MudancaDeStatus(
                    status_anterior=StatusPedido(mudanca.status_anterior)
                    if mudanca.status_anterior
                    else None,
                    status_novo=StatusPedido(mudanca.status_novo),
                    ator_tipo=TipoAtor(mudanca.ator_tipo),
                    motivo=mudanca.motivo,
                    ocorrido_em=mudanca.ocorrido_em,
                )
                for mudanca in mudancas
            ]


class LeituraPagamentosSql:
    def __init__(self, fabrica_sessoes: async_sessionmaker[AsyncSession]) -> None:
        self._fabrica_sessoes = fabrica_sessoes

    async def do_pedido(self, pedido_id: uuid.UUID) -> list[PagamentoResumo]:
        async with self._fabrica_sessoes() as sessao:
            pagamentos = await sessao.scalars(
                select(PagamentoModel)
                .where(PagamentoModel.pedido_id == pedido_id)
                .order_by(PagamentoModel.solicitado_em, PagamentoModel.id)
            )
            return [
                PagamentoResumo(
                    id=pagamento.id,
                    pedido_id=pagamento.pedido_id,
                    status=StatusPagamento(pagamento.status),
                    forma=FormaPagamento(pagamento.forma),
                    valor=pagamento.valor,
                    motivo_recusa=pagamento.motivo_recusa,
                    tentativas=pagamento.tentativas,
                    solicitado_em=pagamento.solicitado_em,
                    concluido_em=pagamento.concluido_em,
                )
                for pagamento in pagamentos
            ]


class LeituraFidelidadeSql:
    def __init__(self, fabrica_sessoes: async_sessionmaker[AsyncSession]) -> None:
        self._fabrica_sessoes = fabrica_sessoes

    async def saldo(self, cliente_id: uuid.UUID) -> int:
        async with self._fabrica_sessoes() as sessao:
            saldo = await sessao.scalar(
                select(func.coalesce(func.sum(LancamentoFidelidadeModel.pontos), 0)).where(
                    LancamentoFidelidadeModel.cliente_id == cliente_id
                )
            )
        return int(saldo or 0)

    async def extrato(self, cliente_id: uuid.UUID, paginacao: Paginacao) -> Pagina[LancamentoResumo]:
        consulta = (
            select(LancamentoFidelidadeModel)
            .where(LancamentoFidelidadeModel.cliente_id == cliente_id)
            .order_by(LancamentoFidelidadeModel.criado_em.desc(), LancamentoFidelidadeModel.id)
        )
        async with self._fabrica_sessoes() as sessao:
            linhas, total = await _paginar(sessao, consulta, paginacao)
        return Pagina(
            itens=tuple(
                LancamentoResumo(
                    pedido_id=linha.LancamentoFidelidadeModel.pedido_id,
                    tipo=TipoLancamento(linha.LancamentoFidelidadeModel.tipo),
                    pontos=linha.LancamentoFidelidadeModel.pontos,
                    criado_em=linha.LancamentoFidelidadeModel.criado_em,
                )
                for linha in linhas
            ),
            pagina=paginacao.pagina,
            limite=paginacao.limite,
            total=total,
        )


class LeituraAuditoriaSql:
    def __init__(self, fabrica_sessoes: async_sessionmaker[AsyncSession]) -> None:
        self._fabrica_sessoes = fabrica_sessoes

    async def listar(self, filtro: FiltroAuditoria, paginacao: Paginacao) -> Pagina[RegistroDaTrilha]:
        consulta = _filtrar_auditoria(select(AuditoriaModel), filtro).order_by(
            AuditoriaModel.ocorrido_em.desc(), AuditoriaModel.id
        )
        async with self._fabrica_sessoes() as sessao:
            linhas, total = await _paginar(sessao, consulta, paginacao)
        return Pagina(
            itens=tuple(_registro_da_trilha(linha.AuditoriaModel) for linha in linhas),
            pagina=paginacao.pagina,
            limite=paginacao.limite,
            total=total,
        )


def _filtrar_auditoria(
    consulta: Select[*tuple[Any, ...]], filtro: FiltroAuditoria
) -> Select[*tuple[Any, ...]]:
    condicoes: list[ColumnElement[bool]] = []
    if filtro.unidades is not None:
        # unidade_id NULL fica de fora do IN: registros sem unidade só aparecem para a MATRIZ.
        condicoes.append(AuditoriaModel.unidade_id.in_(filtro.unidades))
    if filtro.entidade is not None:
        condicoes.append(AuditoriaModel.entidade == filtro.entidade)
    if filtro.entidade_id is not None:
        condicoes.append(AuditoriaModel.entidade_id == filtro.entidade_id)
    if filtro.acao is not None:
        condicoes.append(AuditoriaModel.acao == filtro.acao)
    if filtro.unidade_id is not None:
        condicoes.append(AuditoriaModel.unidade_id == filtro.unidade_id)
    if filtro.inicio is not None:
        condicoes.append(AuditoriaModel.ocorrido_em >= filtro.inicio)
    if filtro.fim is not None:
        condicoes.append(AuditoriaModel.ocorrido_em <= filtro.fim)
    return consulta.where(*condicoes)


def _registro_da_trilha(modelo: AuditoriaModel) -> RegistroDaTrilha:
    return RegistroDaTrilha(
        id=modelo.id,
        ocorrido_em=modelo.ocorrido_em,
        ator_tipo=TipoAtor(modelo.ator_tipo),
        ator_id=modelo.ator_id,
        acao=modelo.acao,
        entidade=modelo.entidade,
        entidade_id=modelo.entidade_id,
        unidade_id=modelo.unidade_id,
        dados=modelo.dados,
        request_id=modelo.request_id,
    )


def _filtrar(consulta: Select[*tuple[Any, ...]], filtro: FiltroPedidos) -> Select[*tuple[Any, ...]]:
    condicoes: list[ColumnElement[bool]] = []
    if filtro.unidades is not None:
        condicoes.append(PedidoModel.unidade_id.in_(filtro.unidades))
    if filtro.cliente_id is not None:
        condicoes.append(PedidoModel.cliente_id == filtro.cliente_id)
    if filtro.unidade_id is not None:
        condicoes.append(PedidoModel.unidade_id == filtro.unidade_id)
    if filtro.canal is not None:
        condicoes.append(PedidoModel.canal_pedido == filtro.canal.value)
    if filtro.status is not None:
        condicoes.append(PedidoModel.status == filtro.status.value)
    if filtro.inicio is not None:
        condicoes.append(PedidoModel.criado_em >= filtro.inicio)
    if filtro.fim is not None:
        condicoes.append(PedidoModel.criado_em <= filtro.fim)
    return consulta.where(*condicoes)


def _unidade(modelo: UnidadeModel) -> UnidadeResumo:
    return UnidadeResumo(
        id=modelo.id,
        codigo=modelo.codigo,
        nome=modelo.nome,
        cidade=modelo.cidade,
        uf=modelo.uf,
        regiao=modelo.regiao,
        tipo=modelo.tipo,
    )


def _produto(modelo: ProdutoModel) -> ProdutoResumo:
    return ProdutoResumo(
        id=modelo.id,
        sku=modelo.sku,
        nome=modelo.nome,
        descricao=modelo.descricao,
        categoria=CategoriaProduto(modelo.categoria),
    )
