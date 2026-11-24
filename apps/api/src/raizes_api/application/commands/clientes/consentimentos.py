import uuid
from dataclasses import dataclass

from raizes_api.application.erros import TokenInvalido
from raizes_api.application.ports.auditoria import AcaoAuditoria, RegistroAuditoria
from raizes_api.application.ports.clientes import RepositorioClientes
from raizes_api.application.ports.relogio import Relogio
from raizes_api.application.ports.unit_of_work import UnitOfWork
from raizes_api.domain.clientes.cliente import Cliente, Consentimento, FinalidadeConsentimento
from raizes_api.domain.compartilhado.atores import TipoAtor
from raizes_api.domain.compartilhado.canais import CanalPedido

ENTIDADE_CONSENTIMENTO = "CONSENTIMENTO"


@dataclass(frozen=True, slots=True)
class ConsentimentoSolicitado:
    finalidade: FinalidadeConsentimento
    versao_termo: str
    canal_origem: CanalPedido


class ConcederConsentimento:
    def __init__(self, uow: UnitOfWork, relogio: Relogio) -> None:
        self._uow = uow
        self._relogio = relogio

    async def executar(self, cliente_id: uuid.UUID, solicitado: ConsentimentoSolicitado) -> Consentimento:
        async with self._uow as uow:
            cliente = await obter_cliente_para_atualizacao(uow.clientes, cliente_id)
            consentimento = cliente.conceder_consentimento(
                solicitado.finalidade,
                versao_termo=solicitado.versao_termo,
                canal_origem=solicitado.canal_origem,
                agora=self._relogio.agora(),
            )
            await uow.clientes.adicionar_consentimento(cliente.id, consentimento)
            await uow.auditoria.registrar(
                registro_de_consentimento(cliente, consentimento, AcaoAuditoria.CONSENTIMENTO_CONCEDIDO)
            )
            await uow.commit()
        return consentimento


class RevogarConsentimento:
    def __init__(self, uow: UnitOfWork, relogio: Relogio) -> None:
        self._uow = uow
        self._relogio = relogio

    async def executar(self, cliente_id: uuid.UUID, finalidade: FinalidadeConsentimento) -> None:
        async with self._uow as uow:
            cliente = await obter_cliente_para_atualizacao(uow.clientes, cliente_id)
            consentimento = cliente.revogar_consentimento(finalidade, self._relogio.agora())
            await uow.clientes.registrar_revogacao(consentimento)
            await uow.auditoria.registrar(
                registro_de_consentimento(cliente, consentimento, AcaoAuditoria.CONSENTIMENTO_REVOGADO)
            )
            await uow.commit()


async def obter_cliente_para_atualizacao(clientes: RepositorioClientes, cliente_id: uuid.UUID) -> Cliente:
    """O titular do token precisa existir e não estar anonimizado; senão o token não vale mais."""
    cliente = await clientes.obter_para_atualizacao(cliente_id)
    if cliente is None or not cliente.pode_autenticar():
        raise TokenInvalido()
    return cliente


def registro_de_consentimento(
    cliente: Cliente, consentimento: Consentimento, acao: AcaoAuditoria
) -> RegistroAuditoria:
    return RegistroAuditoria(
        ator_tipo=TipoAtor.CLIENTE,
        ator_id=str(cliente.id),
        acao=acao,
        entidade=ENTIDADE_CONSENTIMENTO,
        entidade_id=str(consentimento.id),
        dados={
            "finalidade": consentimento.finalidade,
            "versaoTermo": consentimento.versao_termo,
            "canalOrigem": consentimento.canal_origem,
        },
    )
