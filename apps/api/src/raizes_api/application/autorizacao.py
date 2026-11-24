import uuid

from raizes_api.application.ports.auditoria import (
    AcaoAuditoria,
    GravadorAuditoriaIndependente,
    RegistroAuditoria,
)
from raizes_api.domain.compartilhado.atores import AtorAutenticado
from raizes_api.domain.compartilhado.erros import ForaDoEscopoUnidade, PermissaoNegada
from raizes_api.domain.compartilhado.escopo import pode_acessar_unidade
from raizes_api.domain.pedidos.acesso import AcessoAoPedido, VinculosDoPedido, acesso_ao_pedido
from raizes_api.domain.pedidos.erros import PedidoNaoEncontrado

ENTIDADE_PEDIDO = "PEDIDO"


class VerificacaoDeEscopo:
    """Escopo por unidade. `ACESSO_NEGADO_ESCOPO` vai em transação própria: o comando faz rollback."""

    def __init__(self, gravador: GravadorAuditoriaIndependente) -> None:
        self._gravador = gravador

    async def exigir(
        self, ator: AtorAutenticado, unidade_id: int, *, entidade: str, entidade_id: str
    ) -> None:
        if not pode_acessar_unidade(ator, unidade_id):
            await self.negar(ator, unidade_id, entidade=entidade, entidade_id=entidade_id)

    async def exigir_acesso_ao_pedido(
        self, ator: AtorAutenticado, pedido_id: uuid.UUID, vinculos: VinculosDoPedido
    ) -> None:
        """Outro cliente ou outro totem → 404 (não revela que existe); staff fora do escopo → 403 auditado."""
        acesso = acesso_ao_pedido(ator, vinculos)
        if acesso is AcessoAoPedido.OCULTO:
            raise PedidoNaoEncontrado()
        if acesso is AcessoAoPedido.PROIBIDO:
            raise PermissaoNegada()
        if acesso is AcessoAoPedido.FORA_DO_ESCOPO:
            await self.negar(ator, vinculos.unidade_id, entidade=ENTIDADE_PEDIDO, entidade_id=str(pedido_id))

    async def negar(self, ator: AtorAutenticado, unidade_id: int, *, entidade: str, entidade_id: str) -> None:
        await self._gravador.registrar(
            RegistroAuditoria(
                ator_tipo=ator.tipo,
                ator_id=ator.id,
                acao=AcaoAuditoria.ACESSO_NEGADO_ESCOPO,
                entidade=entidade,
                entidade_id=entidade_id,
                unidade_id=unidade_id,
            )
        )
        raise ForaDoEscopoUnidade()
