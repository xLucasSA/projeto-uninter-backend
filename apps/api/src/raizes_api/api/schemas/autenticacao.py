import uuid
from typing import Final, Literal

from pydantic import ConfigDict, Field

from raizes_api.api.schemas.base import SchemaBase
from raizes_api.api.schemas.tipos import Email, Senha
from raizes_api.domain.compartilhado.atores import Perfil

ESQUEMA_BEARER: Final = "Bearer"


class LoginRequest(SchemaBase):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"email": "maria@exemplo.com", "senha": "Senha@123"}]}
    )

    email: Email
    senha: Senha


class LoginFuncionarioRequest(LoginRequest):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"email": "atendente.rec@raizes.dev", "senha": "Senha@123"}]}
    )


class TokenDispositivoRequest(SchemaBase):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"clientId": "totem-rec-01", "clientSecret": "totem-rec-01-segredo-demo"}]
        }
    )

    client_id: str = Field(min_length=1, max_length=60)
    client_secret: Senha


class RefreshTokenRequest(SchemaBase):
    model_config = ConfigDict(json_schema_extra={"examples": [{"refreshToken": "q8Zk3vN1..."}]})

    refresh_token: str = Field(min_length=1, max_length=256)


class SessaoResponse(SchemaBase):
    access_token: str = Field(examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."])
    refresh_token: str = Field(examples=["q8Zk3vN1..."])
    token_type: Literal["Bearer"] = ESQUEMA_BEARER
    expires_in: int = Field(description="Validade do access token, em segundos.", examples=[900])


class UsuarioClienteResponse(SchemaBase):
    id: uuid.UUID
    nome: str = Field(examples=["Maria"])
    perfil: Literal["CLIENTE"] = "CLIENTE"


class LoginClienteResponse(SessaoResponse):
    user: UsuarioClienteResponse


class UsuarioFuncionarioResponse(SchemaBase):
    id: int = Field(examples=[1])
    nome: str = Field(examples=["Atendente Recife"])
    perfis: list[Perfil] = Field(examples=[["ATENDENTE"]])
    unidades: list[int] = Field(description="IDs das unidades do escopo.", examples=[[1]])


class LoginFuncionarioResponse(SessaoResponse):
    user: UsuarioFuncionarioResponse


class DispositivoResponse(SchemaBase):
    id: int = Field(examples=[1])
    nome: str = Field(examples=["Totem 01 — Recife Boa Viagem"])
    unidade_id: int = Field(examples=[1])


class TokenDispositivoResponse(SchemaBase):
    access_token: str = Field(examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."])
    token_type: Literal["Bearer"] = ESQUEMA_BEARER
    expires_in: int = Field(description="Validade do access token, em segundos.", examples=[43200])
    dispositivo: DispositivoResponse
