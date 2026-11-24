import uuid

from raizes_api.application.erros import TokenInvalido
from raizes_api.application.ports.unit_of_work import UnitOfWork
from raizes_api.domain.clientes.cliente import Cliente


class ObterMeusDados:
    """Dados pessoais do próprio titular (LGPD art. 18, confirmação e acesso).

    Lê do banco de escrita: o read model não guarda dados pessoais.
    """

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def executar(self, cliente_id: uuid.UUID) -> Cliente:
        async with self._uow as uow:
            cliente = await uow.clientes.obter(cliente_id)
        if cliente is None or not cliente.pode_autenticar():
            raise TokenInvalido()
        return cliente
