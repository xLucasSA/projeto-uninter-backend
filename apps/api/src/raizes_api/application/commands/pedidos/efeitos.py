"""Efeitos que acompanham o pedido na mesma transação (guideline 03): estoque, histórico, auditoria e outbox.

A auditoria do fluxo (pedido, pagamento e pontos) usa `entidade = PEDIDO`, a raiz do agregado: a trilha de um
pedido sai inteira de `GET /auditoria?entidade=PEDIDO&entidadeId=<id>` (T18).
"""

from collections.abc import Mapping, Sequence
from datetime import datetime

from raizes_api.application.ports.auditoria import AcaoAuditoria, RegistroAuditoria
from raizes_api.application.ports.catalogo import Movimentacao
from raizes_api.application.ports.outbox import EventoIntegracao
from raizes_api.application.ports.unit_of_work import UnitOfWork
from raizes_api.domain.catalogo.catalogo import TipoMovimentacao
from raizes_api.domain.pedidos.pedido import Autoria, MudancaDeStatusPedido, Pedido

ENTIDADE_PEDIDO = "PEDIDO"
AGREGADO_PEDIDO = "pedido"
AGREGADO_ESTOQUE = "estoque"
AGREGADO_PAGAMENTO = "pagamento"
AGREGADO_FIDELIDADE = "fidelidade"


def auditoria_do_pedido(
    pedido: Pedido, autoria: Autoria, acao: AcaoAuditoria, dados: Mapping[str, object]
) -> RegistroAuditoria:
    return RegistroAuditoria(
        ator_tipo=autoria.tipo,
        ator_id=autoria.id,
        acao=acao,
        entidade=ENTIDADE_PEDIDO,
        entidade_id=str(pedido.id),
        unidade_id=pedido.unidade_id,
        dados=dados,
    )


def evento(
    pedido: Pedido, tipo: str, tipo_agregado: str, agregado_id: str, dados: Mapping[str, object]
) -> EventoIntegracao:
    return EventoIntegracao(
        tipo=tipo,
        tipo_agregado=tipo_agregado,
        agregado_id=agregado_id,
        unidade_id=pedido.unidade_id,
        dados=dados,
    )


def dados_da_mudanca(mudanca: MudancaDeStatusPedido) -> dict[str, object]:
    return {
        "statusAnterior": mudanca.status_anterior,
        "statusNovo": mudanca.status_novo,
        "motivo": mudanca.motivo,
    }


def itens_do_evento(pedido: Pedido) -> list[dict[str, object]]:
    return [
        {
            "produtoId": item.produto_id,
            "quantidade": item.quantidade,
            "precoUnitario": item.preco_unitario.valor,
            "subtotal": item.subtotal.valor,
        }
        for item in pedido.itens
    ]


async def gravar_mudanca_de_status(uow: UnitOfWork, pedido: Pedido, mudanca: MudancaDeStatusPedido) -> None:
    """Status novo + histórico + evento `PedidoStatusAlterado`."""
    await uow.pedidos.registrar_mudanca(pedido, mudanca)
    await uow.outbox.publicar(
        evento(
            pedido,
            "PedidoStatusAlterado",
            AGREGADO_PEDIDO,
            str(pedido.id),
            {
                "pedidoId": pedido.id,
                "statusAnterior": mudanca.status_anterior,
                "statusNovo": mudanca.status_novo,
                "atorTipo": mudanca.autoria.tipo,
            },
        )
    )


async def devolver_estoque(uow: UnitOfWork, pedido: Pedido, agora: datetime) -> None:
    """Estorno dos itens (`ESTORNO_PEDIDO`), na mesma ordem da reserva para não haver deadlock.

    Estornar duas vezes é impossível: a transição de status que chama esta função só acontece uma vez.
    """
    movimentacoes = [
        Movimentacao(
            tipo=TipoMovimentacao.ESTORNO_PEDIDO,
            unidade_id=pedido.unidade_id,
            produto_id=item.produto_id,
            quantidade=item.quantidade,
            saldo_apos=await uow.estoque.devolver(pedido.unidade_id, item.produto_id, item.quantidade, agora),
            pedido_id=pedido.id,
        )
        for _, item in pedido.itens_em_ordem_de_reserva()
    ]
    await registrar_movimentacoes(uow, pedido, movimentacoes)


async def registrar_movimentacoes(
    uow: UnitOfWork, pedido: Pedido, movimentacoes: Sequence[Movimentacao]
) -> None:
    await uow.estoque.registrar_movimentacoes(movimentacoes)
    for movimentacao in movimentacoes:
        await uow.outbox.publicar(
            evento(
                pedido,
                "EstoqueMovimentado",
                AGREGADO_ESTOQUE,
                f"{movimentacao.unidade_id}:{movimentacao.produto_id}",
                {
                    "produtoId": movimentacao.produto_id,
                    "tipo": movimentacao.tipo,
                    "quantidade": movimentacao.quantidade,
                    "saldoApos": movimentacao.saldo_apos,
                    "pedidoId": movimentacao.pedido_id,
                },
            )
        )
