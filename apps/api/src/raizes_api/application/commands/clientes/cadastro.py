from dataclasses import dataclass

from raizes_api.application.commands.clientes.consentimentos import (
    ConsentimentoSolicitado,
    registro_de_consentimento,
)
from raizes_api.application.ports.auditoria import AcaoAuditoria, RegistroAuditoria
from raizes_api.application.ports.relogio import Relogio
from raizes_api.application.ports.seguranca import HasherSenha
from raizes_api.application.ports.unit_of_work import UnitOfWork
from raizes_api.domain.clientes.cliente import Cliente
from raizes_api.domain.compartilhado.atores import TipoAtor
from raizes_api.domain.compartilhado.contato import Telefone

ENTIDADE_CLIENTE = "CLIENTE"


@dataclass(frozen=True, slots=True)
class DadosCadastroCliente:
    nome: str
    email: str
    telefone: Telefone | None
    senha: str
    consentimentos: tuple[ConsentimentoSolicitado, ...] = ()


class CadastrarCliente:
    def __init__(self, uow: UnitOfWork, hasher: HasherSenha, relogio: Relogio) -> None:
        self._uow = uow
        self._hasher = hasher
        self._relogio = relogio

    async def executar(self, dados: DadosCadastroCliente) -> Cliente:
        agora = self._relogio.agora()
        cliente = Cliente.cadastrar(
            nome=dados.nome,
            email=dados.email,
            telefone=dados.telefone,
            senha_hash=await self._hasher.gerar_hash(dados.senha),
            agora=agora,
        )
        for solicitado in dados.consentimentos:
            cliente.conceder_consentimento(
                solicitado.finalidade,
                versao_termo=solicitado.versao_termo,
                canal_origem=solicitado.canal_origem,
                agora=agora,
            )

        async with self._uow as uow:
            await uow.clientes.adicionar(cliente)
            await uow.auditoria.registrar(_registro_de_cadastro(cliente))
            for consentimento in cliente.consentimentos:
                await uow.auditoria.registrar(
                    registro_de_consentimento(cliente, consentimento, AcaoAuditoria.CONSENTIMENTO_CONCEDIDO)
                )
            await uow.commit()
        return cliente


def _registro_de_cadastro(cliente: Cliente) -> RegistroAuditoria:
    return RegistroAuditoria(
        ator_tipo=TipoAtor.CLIENTE,
        ator_id=str(cliente.id),
        acao=AcaoAuditoria.CLIENTE_CADASTRADO,
        entidade=ENTIDADE_CLIENTE,
        entidade_id=str(cliente.id),
        dados={"telefoneInformado": cliente.telefone is not None},
    )
