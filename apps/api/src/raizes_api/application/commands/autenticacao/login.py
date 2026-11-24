from dataclasses import dataclass

from raizes_api.application.commands.autenticacao.sessoes import AcessoEmitido, EmissaoDeSessao, SessaoEmitida
from raizes_api.application.erros import CredenciaisInvalidas
from raizes_api.application.ports.auditoria import (
    AcaoAuditoria,
    GravadorAuditoriaIndependente,
    RegistroAuditoria,
)
from raizes_api.application.ports.relogio import Relogio
from raizes_api.application.ports.seguranca import HasherSenha
from raizes_api.application.ports.unit_of_work import UnitOfWork
from raizes_api.domain.autenticacao.credenciais import Dispositivo, Funcionario
from raizes_api.domain.clientes.cliente import Cliente
from raizes_api.domain.compartilhado.atores import TipoAtor
from raizes_api.domain.compartilhado.contato import normalizar_email

ATOR_DESCONHECIDO = "DESCONHECIDO"
ENTIDADE_AUTENTICACAO = "AUTENTICACAO"


@dataclass(frozen=True, slots=True)
class LoginClienteRealizado:
    sessao: SessaoEmitida
    cliente: Cliente


@dataclass(frozen=True, slots=True)
class LoginFuncionarioRealizado:
    sessao: SessaoEmitida
    funcionario: Funcionario


@dataclass(frozen=True, slots=True)
class LoginDispositivoRealizado:
    acesso: AcessoEmitido
    dispositivo: Dispositivo


class RegistroDeLoginFalho:
    """`LOGIN_FALHOU` em transação própria.

    Guarda o tipo de ator e o IP; nunca o e-mail ou o clientId digitado.
    """

    def __init__(self, gravador: GravadorAuditoriaIndependente) -> None:
        self._gravador = gravador

    async def registrar(self, tipo: TipoAtor, ator_id: str | None) -> None:
        identificador = ator_id or ATOR_DESCONHECIDO
        await self._gravador.registrar(
            RegistroAuditoria(
                ator_tipo=tipo,
                ator_id=identificador,
                acao=AcaoAuditoria.LOGIN_FALHOU,
                entidade=ENTIDADE_AUTENTICACAO,
                entidade_id=identificador,
            )
        )


class LoginCliente:
    def __init__(
        self,
        uow: UnitOfWork,
        hasher: HasherSenha,
        sessoes: EmissaoDeSessao,
        falhas: RegistroDeLoginFalho,
    ) -> None:
        self._uow = uow
        self._hasher = hasher
        self._sessoes = sessoes
        self._falhas = falhas

    async def executar(self, email: str, senha: str) -> LoginClienteRealizado:
        async with self._uow as uow:
            cliente = await uow.clientes.obter_por_email(normalizar_email(email))
            senha_hash = cliente.senha_hash if cliente is not None and cliente.pode_autenticar() else None
            senha_confere = await self._hasher.confere(senha_hash, senha)
            if cliente is None or not senha_confere:
                await self._falhas.registrar(TipoAtor.CLIENTE, str(cliente.id) if cliente else None)
                raise CredenciaisInvalidas()
            sessao = await self._sessoes.abrir(uow.refresh_tokens, cliente.como_ator())
            await uow.commit()
        return LoginClienteRealizado(sessao=sessao, cliente=cliente)


class LoginFuncionario:
    def __init__(
        self,
        uow: UnitOfWork,
        hasher: HasherSenha,
        sessoes: EmissaoDeSessao,
        falhas: RegistroDeLoginFalho,
    ) -> None:
        self._uow = uow
        self._hasher = hasher
        self._sessoes = sessoes
        self._falhas = falhas

    async def executar(self, email: str, senha: str) -> LoginFuncionarioRealizado:
        async with self._uow as uow:
            funcionario = await uow.funcionarios.obter_por_email(normalizar_email(email))
            senha_hash = (
                funcionario.senha_hash if funcionario is not None and funcionario.esta_ativo else None
            )
            senha_confere = await self._hasher.confere(senha_hash, senha)
            if funcionario is None or not senha_confere:
                await self._falhas.registrar(
                    TipoAtor.FUNCIONARIO, str(funcionario.id) if funcionario else None
                )
                raise CredenciaisInvalidas()
            sessao = await self._sessoes.abrir(uow.refresh_tokens, funcionario.como_ator())
            await uow.commit()
        return LoginFuncionarioRealizado(sessao=sessao, funcionario=funcionario)


class LoginDispositivo:
    def __init__(
        self,
        uow: UnitOfWork,
        hasher: HasherSenha,
        sessoes: EmissaoDeSessao,
        falhas: RegistroDeLoginFalho,
        relogio: Relogio,
    ) -> None:
        self._uow = uow
        self._hasher = hasher
        self._sessoes = sessoes
        self._falhas = falhas
        self._relogio = relogio

    async def executar(self, client_id: str, segredo: str) -> LoginDispositivoRealizado:
        async with self._uow as uow:
            dispositivo = await uow.dispositivos.obter_por_client_id(client_id)
            segredo_hash = (
                dispositivo.segredo_hash if dispositivo is not None and dispositivo.esta_ativo else None
            )
            segredo_confere = await self._hasher.confere(segredo_hash, segredo)
            if dispositivo is None or not segredo_confere:
                await self._falhas.registrar(
                    TipoAtor.DISPOSITIVO, str(dispositivo.id) if dispositivo else None
                )
                raise CredenciaisInvalidas()
            await uow.dispositivos.registrar_uso(dispositivo.id, self._relogio.agora())
            await uow.commit()
        acesso = self._sessoes.acesso_de_dispositivo(dispositivo.como_ator())
        return LoginDispositivoRealizado(acesso=acesso, dispositivo=dispositivo)
