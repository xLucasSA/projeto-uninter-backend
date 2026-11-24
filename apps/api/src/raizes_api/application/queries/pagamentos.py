import uuid

from raizes_api.application.autorizacao import VerificacaoDeEscopo
from raizes_api.application.ports.leitura import LeituraPagamentos, LeituraPedidos, PagamentoResumo
from raizes_api.domain.compartilhado.atores import AtorAutenticado
from raizes_api.domain.pedidos.erros import PedidoNaoEncontrado


class ListarPagamentosDoPedido:
    """Tentativas de pagamento do pedido, para quem pode ver o pedido."""

    def __init__(
        self, pedidos: LeituraPedidos, pagamentos: LeituraPagamentos, escopo: VerificacaoDeEscopo
    ) -> None:
        self._pedidos = pedidos
        self._pagamentos = pagamentos
        self._escopo = escopo

    async def executar(self, ator: AtorAutenticado, pedido_id: uuid.UUID) -> list[PagamentoResumo]:
        pedido = await self._pedidos.obter(pedido_id)
        if pedido is None:
            raise PedidoNaoEncontrado()
        await self._escopo.exigir_acesso_ao_pedido(ator, pedido.id, pedido.vinculos)
        return await self._pagamentos.do_pedido(pedido_id)
