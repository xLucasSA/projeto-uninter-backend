import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import ConfigDict, Field, StringConstraints

from raizes_api.api.schemas.base import SchemaBase
from raizes_api.api.schemas.tipos import Email, SenhaNova, TelefoneE164
from raizes_api.domain.clientes.cliente import Cliente, Consentimento, FinalidadeConsentimento
from raizes_api.domain.compartilhado.canais import CanalPedido

# MARKETING existe no banco, mas fica reservado: nenhuma funcionalidade usa esse consentimento ainda.
FinalidadeImplementada = Literal[FinalidadeConsentimento.FIDELIDADE]


class ConsentimentoRequest(SchemaBase):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"finalidade": "FIDELIDADE", "versaoTermo": "1.0", "canalOrigem": "APP"}]
        }
    )

    finalidade: FinalidadeImplementada
    versao_termo: str = Field(min_length=1, max_length=20)
    canal_origem: CanalPedido


class CadastroClienteRequest(SchemaBase):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "nome": "Maria da Silva",
                    "email": "maria@exemplo.com",
                    "telefone": "+5581999990000",
                    "senha": "Senha@123",
                    "consentimentos": [
                        {"finalidade": "FIDELIDADE", "versaoTermo": "1.0", "canalOrigem": "APP"}
                    ],
                }
            ]
        }
    )

    nome: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]
    email: Email
    telefone: TelefoneE164 | None = None
    senha: SenhaNova
    consentimentos: list[ConsentimentoRequest] = Field(default_factory=list, max_length=5)


class ConsentimentoResponse(SchemaBase):
    id: uuid.UUID
    finalidade: FinalidadeConsentimento
    versao_termo: str = Field(examples=["1.0"])
    canal_origem: CanalPedido
    concedido_em: datetime
    revogado_em: datetime | None = None

    @classmethod
    def de(cls, consentimento: Consentimento) -> "ConsentimentoResponse":
        return cls(
            id=consentimento.id,
            finalidade=consentimento.finalidade,
            versao_termo=consentimento.versao_termo,
            canal_origem=consentimento.canal_origem,
            concedido_em=consentimento.concedido_em,
            revogado_em=consentimento.revogado_em,
        )


class ClienteResponse(SchemaBase):
    """Dados do próprio titular. Nunca inclui o hash da senha."""

    id: uuid.UUID
    nome: str = Field(examples=["Maria da Silva"])
    email: str = Field(examples=["maria@exemplo.com"])
    telefone: str | None = Field(default=None, examples=["+5581999990000"])
    criado_em: datetime
    consentimentos: list[ConsentimentoResponse] = Field(
        description="Histórico completo, inclusive os revogados (prova do consentimento)."
    )

    @classmethod
    def de(cls, cliente: Cliente) -> "ClienteResponse":
        return cls(
            id=cliente.id,
            nome=cliente.nome,
            email=cliente.email,
            telefone=cliente.telefone.numero if cliente.telefone else None,
            criado_em=cliente.criado_em,
            consentimentos=[ConsentimentoResponse.de(item) for item in cliente.consentimentos],
        )
