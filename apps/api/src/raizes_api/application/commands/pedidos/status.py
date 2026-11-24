import uuid

from raizes_api.application.autorizacao import VerificacaoDeEscopo
from raizes_api.application.commands.pedidos.criacao import detalhe_do_pedido
from raizes_api.application.commands.pedidos.efeitos import (
    auditoria_do_pedido,
    dados_da_mudanca,
    gravar_mudanca_de_status,
)
from raizes_api.application.ports.auditoria import AcaoAuditoria
from raizes_api.application.ports.leitura import PedidoDetalhe
from raizes_api.application.ports.relogio import Relogio
from raizes_api.application.ports.unit_of_work import UnitOfWork
from raizes_api.domain.compartilhado.atores import AtorAutenticado
from raizes_api.domain.pedidos.erros import PedidoNaoEncontrado
from raizes_api.domain.pedidos.status import StatusPedido


class AtualizarStatusPedido:
    """Operação da loja: PAGO → EM_PREPARO → PRONTO → ENTREGUE (guideline 03).

    Ordem das checagens: acesso ao pedido e escopo (403), transição existe (409), perfil pode (403).
    """

    def __init__(self, uow: UnitOfWork, relogio: Relogio, escopo: VerificacaoDeEscopo) -> None:
        self._uow = uow
        self._relogio = relogio
        self._escopo = escopo

    async def executar(
        self, ator: AtorAutenticado, pedido_id: uuid.UUID, novo: StatusPedido, motivo: str | None
    ) -> PedidoDetalhe:
        async with self._uow as uow:
            pedido = await uow.pedidos.obter_para_atualizacao(pedido_id)
            if pedido is None:
                raise PedidoNaoEncontrado()
            await self._escopo.exigir_acesso_ao_pedido(ator, pedido.id, pedido.vinculos)
            mudanca = pedido.mudar_status(novo, ator, agora=self._relogio.agora(), motivo=motivo)
            await gravar_mudanca_de_status(uow, pedido, mudanca)
            await uow.auditoria.registrar(
                auditoria_do_pedido(
                    pedido, mudanca.autoria, AcaoAuditoria.PEDIDO_STATUS_ALTERADO, dados_da_mudanca(mudanca)
                )
            )
            await uow.commit()
        return detalhe_do_pedido(pedido)
