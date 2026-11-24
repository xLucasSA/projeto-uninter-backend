import uuid

from sqlalchemy import Select, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from raizes_api.domain.clientes.cliente import Cliente, Consentimento, FinalidadeConsentimento
from raizes_api.domain.clientes.erros import EmailJaCadastrado, TelefoneJaCadastrado
from raizes_api.domain.compartilhado.canais import CanalPedido
from raizes_api.domain.compartilhado.contato import Telefone
from raizes_api.domain.compartilhado.erros import ErroDominio
from raizes_api.infrastructure.db.modelos import ClienteModel, ConsentimentoModel

ERRO_POR_RESTRICAO_UNICA: dict[str, type[ErroDominio]] = {
    "clientes_email_unico": EmailJaCadastrado,
    "clientes_telefone_unico": TelefoneJaCadastrado,
}


class RepositorioClientesSql:
    def __init__(self, sessao: AsyncSession) -> None:
        self._sessao = sessao

    async def obter(self, cliente_id: uuid.UUID) -> Cliente | None:
        return await self._carregar(select(ClienteModel).where(ClienteModel.id == cliente_id))

    async def obter_para_atualizacao(self, cliente_id: uuid.UUID) -> Cliente | None:
        return await self._carregar(
            select(ClienteModel).where(ClienteModel.id == cliente_id).with_for_update()
        )

    async def obter_por_email(self, email: str) -> Cliente | None:
        return await self._carregar(select(ClienteModel).where(ClienteModel.email == email))

    async def obter_por_telefone(self, telefone: Telefone) -> Cliente | None:
        return await self._carregar(select(ClienteModel).where(ClienteModel.telefone == telefone.numero))

    async def adicionar(self, cliente: Cliente) -> None:
        self._sessao.add(
            ClienteModel(
                id=cliente.id,
                nome=cliente.nome,
                email=cliente.email,
                telefone=cliente.telefone.numero if cliente.telefone else None,
                senha_hash=cliente.senha_hash,
                criado_em=cliente.criado_em,
                atualizado_em=cliente.criado_em,
            )
        )
        try:
            await self._sessao.flush()
        except IntegrityError as erro:
            traducao = _erro_de_unicidade(erro)
            if traducao is None:
                raise
            raise traducao from erro
        for consentimento in cliente.consentimentos:
            self._sessao.add(_modelo_de_consentimento(cliente.id, consentimento))
        await self._sessao.flush()

    async def adicionar_consentimento(self, cliente_id: uuid.UUID, consentimento: Consentimento) -> None:
        self._sessao.add(_modelo_de_consentimento(cliente_id, consentimento))
        await self._sessao.flush()

    async def registrar_revogacao(self, consentimento: Consentimento) -> None:
        await self._sessao.execute(
            update(ConsentimentoModel)
            .where(ConsentimentoModel.id == consentimento.id)
            .values(revogado_em=consentimento.revogado_em)
            .execution_options(synchronize_session=False)
        )

    async def _carregar(self, consulta: Select[ClienteModel]) -> Cliente | None:
        modelo = (await self._sessao.execute(consulta)).scalar_one_or_none()
        if modelo is None:
            return None
        consentimentos = (
            await self._sessao.execute(
                select(ConsentimentoModel)
                .where(ConsentimentoModel.cliente_id == modelo.id)
                .order_by(ConsentimentoModel.concedido_em)
            )
        ).scalars()
        return Cliente(
            id=modelo.id,
            nome=modelo.nome,
            email=modelo.email,
            telefone=Telefone(modelo.telefone) if modelo.telefone else None,
            senha_hash=modelo.senha_hash,
            criado_em=modelo.criado_em,
            consentimentos=[_consentimento_de(item) for item in consentimentos],
            anonimizado_em=modelo.anonimizado_em,
        )


def _erro_de_unicidade(erro: IntegrityError) -> ErroDominio | None:
    detalhe = str(erro.orig)
    for restricao, tipo_erro in ERRO_POR_RESTRICAO_UNICA.items():
        if restricao in detalhe:
            return tipo_erro()
    return None


def _modelo_de_consentimento(cliente_id: uuid.UUID, consentimento: Consentimento) -> ConsentimentoModel:
    return ConsentimentoModel(
        id=consentimento.id,
        cliente_id=cliente_id,
        finalidade=consentimento.finalidade.value,
        versao_termo=consentimento.versao_termo,
        canal_origem=consentimento.canal_origem.value,
        concedido_em=consentimento.concedido_em,
        revogado_em=consentimento.revogado_em,
    )


def _consentimento_de(modelo: ConsentimentoModel) -> Consentimento:
    return Consentimento(
        id=modelo.id,
        finalidade=FinalidadeConsentimento(modelo.finalidade),
        versao_termo=modelo.versao_termo,
        canal_origem=CanalPedido(modelo.canal_origem),
        concedido_em=modelo.concedido_em,
        revogado_em=modelo.revogado_em,
    )
