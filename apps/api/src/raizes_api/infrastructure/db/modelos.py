"""Mapeamento ORM das tabelas usadas pela API.

O schema `vendas` é versionado pelas migrations do Alembic (fonte da verdade das constraints);
as tabelas de `catalogo` pertencem ao Django e aqui são só lidas, exceto `estoque`,
`movimentacao_estoque` e `dispositivos.ultimo_uso_em`, nos limites dos grants (guideline 02).
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CHAR,
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Table,
    func,
)
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

CATALOGO = "catalogo"
VENDAS = "vendas"


class Base(DeclarativeBase):
    type_annotation_map = {
        datetime: DateTime(timezone=True),
        Decimal: Numeric(10, 2),
        dict[str, Any]: JSONB,
    }


class UnidadeModel(Base):
    __tablename__ = "unidades"
    __table_args__ = {"schema": CATALOGO}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(20))
    nome: Mapped[str] = mapped_column(String(100))
    cidade: Mapped[str] = mapped_column(String(80))
    uf: Mapped[str] = mapped_column(String(2))
    regiao: Mapped[str] = mapped_column(String(2))
    tipo: Mapped[str] = mapped_column(String(10))
    ativa: Mapped[bool]


class ProdutoModel(Base):
    __tablename__ = "produtos"
    __table_args__ = {"schema": CATALOGO}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    sku: Mapped[str] = mapped_column(String(30))
    nome: Mapped[str] = mapped_column(String(120))
    descricao: Mapped[str]
    categoria: Mapped[str] = mapped_column(String(10))
    requer_cozinha_completa: Mapped[bool]
    ativo: Mapped[bool]


class CardapioUnidadeModel(Base):
    __tablename__ = "cardapio_unidade"
    __table_args__ = {"schema": CATALOGO}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    unidade_id: Mapped[int] = mapped_column(BigInteger, ForeignKey(f"{CATALOGO}.unidades.id"))
    produto_id: Mapped[int] = mapped_column(BigInteger, ForeignKey(f"{CATALOGO}.produtos.id"))
    preco: Mapped[Decimal]
    ativo: Mapped[bool]
    disponivel_de: Mapped[date | None]
    disponivel_ate: Mapped[date | None]


class EstoqueModel(Base):
    __tablename__ = "estoque"
    __table_args__ = {"schema": CATALOGO}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    unidade_id: Mapped[int] = mapped_column(BigInteger, ForeignKey(f"{CATALOGO}.unidades.id"))
    produto_id: Mapped[int] = mapped_column(BigInteger, ForeignKey(f"{CATALOGO}.produtos.id"))
    quantidade: Mapped[int]
    atualizado_em: Mapped[datetime]


class MovimentacaoEstoqueModel(Base):
    __tablename__ = "movimentacao_estoque"
    __table_args__ = {"schema": CATALOGO}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    unidade_id: Mapped[int] = mapped_column(BigInteger, ForeignKey(f"{CATALOGO}.unidades.id"))
    produto_id: Mapped[int] = mapped_column(BigInteger, ForeignKey(f"{CATALOGO}.produtos.id"))
    tipo: Mapped[str] = mapped_column(String(20))
    origem: Mapped[str] = mapped_column(String(12))
    quantidade: Mapped[int]
    saldo_apos: Mapped[int]
    pedido_id: Mapped[uuid.UUID | None]
    funcionario_id: Mapped[int | None] = mapped_column(BigInteger)
    motivo: Mapped[str | None] = mapped_column(String(200))
    criado_em: Mapped[datetime] = mapped_column(server_default=func.now())


class FuncionarioModel(Base):
    __tablename__ = "funcionarios"
    __table_args__ = {"schema": CATALOGO}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    email: Mapped[str] = mapped_column(String(254))
    nome: Mapped[str] = mapped_column(String(120))
    password: Mapped[str] = mapped_column(String(128))
    is_active: Mapped[bool]
    is_superuser: Mapped[bool]


funcionarios_unidades = Table(
    "funcionarios_unidades",
    Base.metadata,
    Column("id", BigInteger, primary_key=True),
    Column("funcionario_id", BigInteger, ForeignKey(f"{CATALOGO}.funcionarios.id")),
    Column("unidade_id", BigInteger, ForeignKey(f"{CATALOGO}.unidades.id")),
    schema=CATALOGO,
)

auth_group = Table(
    "auth_group",
    Base.metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(150)),
    schema=CATALOGO,
)

funcionarios_groups = Table(
    "funcionarios_groups",
    Base.metadata,
    Column("id", BigInteger, primary_key=True),
    Column("funcionario_id", BigInteger, ForeignKey(f"{CATALOGO}.funcionarios.id")),
    Column("group_id", Integer, ForeignKey(f"{CATALOGO}.auth_group.id")),
    schema=CATALOGO,
)


class DispositivoModel(Base):
    __tablename__ = "dispositivos"
    __table_args__ = {"schema": CATALOGO}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    unidade_id: Mapped[int] = mapped_column(BigInteger, ForeignKey(f"{CATALOGO}.unidades.id"))
    nome: Mapped[str] = mapped_column(String(80))
    client_id: Mapped[str] = mapped_column(String(60))
    secret_hash: Mapped[str] = mapped_column(String(255))
    ativo: Mapped[bool]
    ultimo_uso_em: Mapped[datetime | None]


class ClienteModel(Base):
    __tablename__ = "clientes"
    __table_args__ = {"schema": VENDAS}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(254))
    telefone: Mapped[str | None] = mapped_column(String(16))
    senha_hash: Mapped[str | None] = mapped_column(String(255))
    criado_em: Mapped[datetime] = mapped_column(server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(server_default=func.now())
    anonimizado_em: Mapped[datetime | None]


class ConsentimentoModel(Base):
    __tablename__ = "consentimentos"
    __table_args__ = {"schema": VENDAS}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    cliente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(f"{VENDAS}.clientes.id"))
    finalidade: Mapped[str] = mapped_column(String(20))
    versao_termo: Mapped[str] = mapped_column(String(20))
    canal_origem: Mapped[str] = mapped_column(String(10))
    concedido_em: Mapped[datetime] = mapped_column(server_default=func.now())
    revogado_em: Mapped[datetime | None]


class RefreshTokenModel(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = {"schema": VENDAS}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    sujeito_tipo: Mapped[str] = mapped_column(String(12))
    sujeito_id: Mapped[str] = mapped_column(String(64))
    token_hash: Mapped[str] = mapped_column(CHAR(64))
    familia_id: Mapped[uuid.UUID]
    substituido_por: Mapped[uuid.UUID | None]
    expira_em: Mapped[datetime]
    revogado_em: Mapped[datetime | None]
    criado_em: Mapped[datetime] = mapped_column(server_default=func.now())


class PedidoModel(Base):
    __tablename__ = "pedidos"
    __table_args__ = {"schema": VENDAS}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    unidade_id: Mapped[int] = mapped_column(BigInteger, ForeignKey(f"{CATALOGO}.unidades.id"))
    cliente_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey(f"{VENDAS}.clientes.id"))
    canal_pedido: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(25))
    total: Mapped[Decimal]
    criado_por_tipo: Mapped[str] = mapped_column(String(12))
    criado_por_id: Mapped[str] = mapped_column(String(64))
    observacao: Mapped[str | None] = mapped_column(String(200))
    criado_em: Mapped[datetime] = mapped_column(server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(server_default=func.now())


class ItemPedidoModel(Base):
    __tablename__ = "itens_pedido"
    __table_args__ = {"schema": VENDAS}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    pedido_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(f"{VENDAS}.pedidos.id", ondelete="CASCADE"))
    produto_id: Mapped[int] = mapped_column(BigInteger, ForeignKey(f"{CATALOGO}.produtos.id"))
    nome_produto: Mapped[str] = mapped_column(String(120))
    quantidade: Mapped[int]
    preco_unitario: Mapped[Decimal]
    subtotal: Mapped[Decimal]


class HistoricoStatusPedidoModel(Base):
    __tablename__ = "historico_status_pedido"
    __table_args__ = {"schema": VENDAS}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    pedido_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(f"{VENDAS}.pedidos.id"))
    status_anterior: Mapped[str | None] = mapped_column(String(25))
    status_novo: Mapped[str] = mapped_column(String(25))
    ator_tipo: Mapped[str] = mapped_column(String(12))
    ator_id: Mapped[str] = mapped_column(String(64))
    motivo: Mapped[str | None] = mapped_column(String(200))
    ocorrido_em: Mapped[datetime] = mapped_column(server_default=func.now())


class PagamentoModel(Base):
    __tablename__ = "pagamentos"
    __table_args__ = {"schema": VENDAS}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    pedido_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(f"{VENDAS}.pedidos.id"))
    status: Mapped[str] = mapped_column(String(10))
    forma: Mapped[str] = mapped_column(String(10))
    valor: Mapped[Decimal]
    transacao_externa_id: Mapped[str | None] = mapped_column(String(64))
    motivo_recusa: Mapped[str | None] = mapped_column(String(60))
    tentativas: Mapped[int] = mapped_column(server_default="0")
    solicitado_em: Mapped[datetime] = mapped_column(server_default=func.now())
    concluido_em: Mapped[datetime | None]


class WebhookRecebidoModel(Base):
    __tablename__ = "webhooks_recebidos"
    __table_args__ = {"schema": VENDAS}

    event_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    transacao_externa_id: Mapped[str] = mapped_column(String(64))
    tipo: Mapped[str] = mapped_column(String(40))
    payload_hash: Mapped[str] = mapped_column(CHAR(64))
    recebido_em: Mapped[datetime] = mapped_column(server_default=func.now())


class LancamentoFidelidadeModel(Base):
    __tablename__ = "lancamentos_fidelidade"
    __table_args__ = {"schema": VENDAS}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    cliente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(f"{VENDAS}.clientes.id"))
    pedido_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(f"{VENDAS}.pedidos.id"))
    tipo: Mapped[str] = mapped_column(String(10))
    pontos: Mapped[int]
    criado_em: Mapped[datetime] = mapped_column(server_default=func.now())


class IdempotencyKeyModel(Base):
    __tablename__ = "idempotency_keys"
    __table_args__ = {"schema": VENDAS}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    sujeito: Mapped[str] = mapped_column(String(80))
    rota: Mapped[str] = mapped_column(String(120))
    chave: Mapped[uuid.UUID]
    request_hash: Mapped[str] = mapped_column(CHAR(64))
    status: Mapped[str] = mapped_column(String(12))
    status_code: Mapped[int | None]
    resposta: Mapped[dict[str, Any] | None]
    criado_em: Mapped[datetime] = mapped_column(server_default=func.now())
    expira_em: Mapped[datetime]


class AuditoriaModel(Base):
    __tablename__ = "auditoria"
    __table_args__ = {"schema": VENDAS}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    ocorrido_em: Mapped[datetime]
    ator_tipo: Mapped[str] = mapped_column(String(12))
    ator_id: Mapped[str] = mapped_column(String(64))
    acao: Mapped[str] = mapped_column(String(60))
    entidade: Mapped[str] = mapped_column(String(40))
    entidade_id: Mapped[str] = mapped_column(String(64))
    unidade_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey(f"{CATALOGO}.unidades.id"))
    dados: Mapped[dict[str, Any]]
    request_id: Mapped[str | None] = mapped_column(String(64))
    ip: Mapped[str | None] = mapped_column(INET)


class OutboxEventoModel(Base):
    __tablename__ = "outbox_eventos"
    __table_args__ = {"schema": VENDAS}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    aggregatetype: Mapped[str] = mapped_column(String(40))
    aggregateid: Mapped[str] = mapped_column(String(64))
    type: Mapped[str] = mapped_column(String(80))
    payload: Mapped[dict[str, Any]]
    ocorrido_em: Mapped[datetime]
