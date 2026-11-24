import uuid

from raizes_api.application.autorizacao import VerificacaoDeEscopo
from raizes_api.application.commands.pedidos.criacao import detalhe_do_pedido
from raizes_api.application.commands.pedidos.efeitos import (
    AGREGADO_FIDELIDADE,
    AGREGADO_PEDIDO,
    auditoria_do_pedido,
    devolver_estoque,
    evento,
    itens_do_evento,
)
from raizes_api.application.ports.auditoria import AcaoAuditoria
from raizes_api.application.ports.leitura import PedidoDetalhe
from raizes_api.application.ports.relogio import Relogio
from raizes_api.application.ports.unit_of_work import UnitOfWork
from raizes_api.domain.compartilhado.atores import AtorAutenticado
from raizes_api.domain.fidelidade.lancamento import LancamentoFidelidade
from raizes_api.domain.pagamentos.erros import PagamentoEmAndamento
from raizes_api.domain.pedidos.erros import PedidoNaoEncontrado
from raizes_api.domain.pedidos.pedido import MudancaDeStatusPedido, Pedido
from raizes_api.domain.pedidos.status import StatusPedido


class CancelarPedido:
    """Cancela o pedido e devolve o estoque; se ele já estava pago (só GERENTE/MATRIZ), estorna os pontos.

    O reembolso no gateway fica documentado: o pagamento aprovado continua APROVADO.
    """

    def __init__(self, uow: UnitOfWork, relogio: Relogio, escopo: VerificacaoDeEscopo) -> None:
        self._uow = uow
        self._relogio = relogio
        self._escopo = escopo

    async def executar(self, ator: AtorAutenticado, pedido_id: uuid.UUID, motivo: str) -> PedidoDetalhe:
        agora = self._relogio.agora()
        async with self._uow as uow:
            pedido = await uow.pedidos.obter_para_atualizacao(pedido_id)
            if pedido is None:
                raise PedidoNaoEncontrado()
            await self._escopo.exigir_acesso_ao_pedido(ator, pedido.id, pedido.vinculos)
            estava_pago = pedido.status is StatusPedido.PAGO
            mudanca = pedido.mudar_status(StatusPedido.CANCELADO, ator, agora=agora, motivo=motivo)
            pagamento = await uow.pagamentos.ativo_do_pedido(pedido.id)
            if pagamento is not None and pagamento.esta_pendente:
                # O webhook ainda pode aprovar: cancelar agora deixaria um pedido cancelado e pago.
                raise PagamentoEmAndamento()

            await uow.pedidos.registrar_mudanca(pedido, mudanca)
            await devolver_estoque(uow, pedido, agora)
            if estava_pago:
                credito = await uow.fidelidade.credito_do_pedido(pedido.id)
                if credito is not None:
                    await _estornar_pontos(uow, pedido, mudanca, credito.estornar(agora))
            await _registrar_cancelamento(uow, pedido, mudanca, estava_pago=estava_pago)
            await uow.commit()
        return detalhe_do_pedido(pedido)


async def _estornar_pontos(
    uow: UnitOfWork, pedido: Pedido, mudanca: MudancaDeStatusPedido, estorno: LancamentoFidelidade
) -> None:
    await uow.fidelidade.adicionar(estorno)
    await uow.auditoria.registrar(
        auditoria_do_pedido(
            pedido, mudanca.autoria, AcaoAuditoria.PONTOS_ESTORNADOS, {"pontos": estorno.pontos}
        )
    )
    await uow.outbox.publicar(
        evento(
            pedido,
            "PontosEstornados",
            AGREGADO_FIDELIDADE,
            str(estorno.cliente_id),
            {"clienteId": estorno.cliente_id, "pedidoId": pedido.id, "pontos": estorno.pontos},
        )
    )


async def _registrar_cancelamento(
    uow: UnitOfWork, pedido: Pedido, mudanca: MudancaDeStatusPedido, *, estava_pago: bool
) -> None:
    await uow.auditoria.registrar(
        auditoria_do_pedido(
            pedido,
            mudanca.autoria,
            AcaoAuditoria.PEDIDO_CANCELADO,
            {"statusAnterior": mudanca.status_anterior, "motivo": mudanca.motivo, "estavaPago": estava_pago},
        )
    )
    await uow.outbox.publicar(
        evento(
            pedido,
            "PedidoCancelado",
            AGREGADO_PEDIDO,
            str(pedido.id),
            {
                "pedidoId": pedido.id,
                "statusAnterior": mudanca.status_anterior,
                "total": pedido.total.valor,
                "itens": itens_do_evento(pedido),
                "estavaPago": estava_pago,
            },
        )
    )
