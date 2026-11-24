"""Schema vendas: clientes, pedidos, pagamentos, fidelidade, idempotência, auditoria e outbox.

Revision ID: 0001
Revises:
Create Date: 2026-11-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "vendas"

CANAIS_PEDIDO = ("APP", "TOTEM", "BALCAO", "PICKUP", "WEB")
STATUS_PEDIDO = (
    "AGUARDANDO_PAGAMENTO",
    "PAGO",
    "EM_PREPARO",
    "PRONTO",
    "ENTREGUE",
    "PAGAMENTO_RECUSADO",
    "CANCELADO",
)
STATUS_PAGAMENTO = ("PENDENTE", "APROVADO", "RECUSADO", "ERRO")
FORMAS_PAGAMENTO = ("MOCK",)
TIPOS_ATOR = ("CLIENTE", "FUNCIONARIO", "DISPOSITIVO", "SISTEMA")
SUJEITOS_REFRESH = ("CLIENTE", "FUNCIONARIO")
FINALIDADES_CONSENTIMENTO = ("FIDELIDADE", "MARKETING")
TIPOS_LANCAMENTO = ("CREDITO", "ESTORNO")
STATUS_IDEMPOTENCIA = ("PROCESSANDO", "CONCLUIDA")


def _valor_em(coluna: str, valores: Sequence[str]) -> str:
    return f"{coluna} IN ({', '.join(repr(valor) for valor in valores)})"


def _criado_em() -> sa.Column[object]:
    return sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())


def upgrade() -> None:
    op.create_table(
        "clientes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("nome", sa.String(120), nullable=False),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("telefone", sa.String(16), nullable=True),
        sa.Column("senha_hash", sa.String(255), nullable=True),
        _criado_em(),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("anonimizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("email", name="clientes_email_unico"),
        sa.UniqueConstraint("telefone", name="clientes_telefone_unico"),
        sa.CheckConstraint("email = lower(email)", name="clientes_email_minusculo"),
        schema=SCHEMA,
    )

    op.create_table(
        "consentimentos",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("cliente_id", sa.Uuid(), nullable=False),
        sa.Column("finalidade", sa.String(20), nullable=False),
        sa.Column("versao_termo", sa.String(20), nullable=False),
        sa.Column("canal_origem", sa.String(10), nullable=False),
        sa.Column("concedido_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("revogado_em", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["cliente_id"], [f"{SCHEMA}.clientes.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            _valor_em("finalidade", FINALIDADES_CONSENTIMENTO), name="consentimentos_finalidade"
        ),
        sa.CheckConstraint(_valor_em("canal_origem", CANAIS_PEDIDO), name="consentimentos_canal_origem"),
        schema=SCHEMA,
    )
    op.create_index(
        "consentimentos_ativo_unico",
        "consentimentos",
        ["cliente_id", "finalidade"],
        unique=True,
        schema=SCHEMA,
        postgresql_where=sa.text("revogado_em IS NULL"),
    )

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("sujeito_tipo", sa.String(12), nullable=False),
        sa.Column("sujeito_id", sa.String(64), nullable=False),
        sa.Column("token_hash", sa.CHAR(64), nullable=False),
        sa.Column("familia_id", sa.Uuid(), nullable=False),
        sa.Column("substituido_por", sa.Uuid(), nullable=True),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revogado_em", sa.DateTime(timezone=True), nullable=True),
        _criado_em(),
        sa.UniqueConstraint("token_hash", name="refresh_tokens_hash_unico"),
        sa.CheckConstraint(_valor_em("sujeito_tipo", SUJEITOS_REFRESH), name="refresh_tokens_sujeito_tipo"),
        schema=SCHEMA,
    )
    op.create_index("refresh_tokens_familia_idx", "refresh_tokens", ["familia_id"], schema=SCHEMA)

    op.create_table(
        "pedidos",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("unidade_id", sa.BigInteger(), nullable=False),
        sa.Column("cliente_id", sa.Uuid(), nullable=True),
        sa.Column("canal_pedido", sa.String(10), nullable=False),
        sa.Column("status", sa.String(25), nullable=False),
        sa.Column("total", sa.Numeric(10, 2), nullable=False),
        sa.Column("criado_por_tipo", sa.String(12), nullable=False),
        sa.Column("criado_por_id", sa.String(64), nullable=False),
        sa.Column("observacao", sa.String(200), nullable=True),
        _criado_em(),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["unidade_id"], ["catalogo.unidades.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cliente_id"], [f"{SCHEMA}.clientes.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(_valor_em("canal_pedido", CANAIS_PEDIDO), name="pedidos_canal_pedido"),
        sa.CheckConstraint(_valor_em("status", STATUS_PEDIDO), name="pedidos_status"),
        sa.CheckConstraint(_valor_em("criado_por_tipo", TIPOS_ATOR), name="pedidos_criado_por_tipo"),
        sa.CheckConstraint("total >= 0", name="pedidos_total_nao_negativo"),
        schema=SCHEMA,
    )
    op.create_index(
        "pedidos_unidade_status_idx",
        "pedidos",
        ["unidade_id", "status", sa.text("criado_em DESC")],
        schema=SCHEMA,
    )
    op.create_index(
        "pedidos_canal_idx", "pedidos", ["canal_pedido", sa.text("criado_em DESC")], schema=SCHEMA
    )
    op.create_index(
        "pedidos_cliente_idx", "pedidos", ["cliente_id", sa.text("criado_em DESC")], schema=SCHEMA
    )

    op.create_table(
        "itens_pedido",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("pedido_id", sa.Uuid(), nullable=False),
        sa.Column("produto_id", sa.BigInteger(), nullable=False),
        sa.Column("nome_produto", sa.String(120), nullable=False),
        sa.Column("quantidade", sa.Integer(), nullable=False),
        sa.Column("preco_unitario", sa.Numeric(10, 2), nullable=False),
        sa.Column("subtotal", sa.Numeric(10, 2), nullable=False),
        sa.ForeignKeyConstraint(["pedido_id"], [f"{SCHEMA}.pedidos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["produto_id"], ["catalogo.produtos.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("pedido_id", "produto_id", name="itens_pedido_produto_unico"),
        sa.CheckConstraint("quantidade BETWEEN 1 AND 20", name="itens_pedido_quantidade"),
        sa.CheckConstraint("preco_unitario > 0", name="itens_pedido_preco_positivo"),
        sa.CheckConstraint("subtotal >= 0", name="itens_pedido_subtotal_nao_negativo"),
        schema=SCHEMA,
    )

    op.create_table(
        "historico_status_pedido",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("pedido_id", sa.Uuid(), nullable=False),
        sa.Column("status_anterior", sa.String(25), nullable=True),
        sa.Column("status_novo", sa.String(25), nullable=False),
        sa.Column("ator_tipo", sa.String(12), nullable=False),
        sa.Column("ator_id", sa.String(64), nullable=False),
        sa.Column("motivo", sa.String(200), nullable=True),
        sa.Column("ocorrido_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["pedido_id"], [f"{SCHEMA}.pedidos.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            f"status_anterior IS NULL OR {_valor_em('status_anterior', STATUS_PEDIDO)}",
            name="historico_status_anterior",
        ),
        sa.CheckConstraint(_valor_em("status_novo", STATUS_PEDIDO), name="historico_status_novo"),
        sa.CheckConstraint(_valor_em("ator_tipo", TIPOS_ATOR), name="historico_ator_tipo"),
        schema=SCHEMA,
    )
    op.create_index(
        "historico_pedido_idx", "historico_status_pedido", ["pedido_id", "ocorrido_em"], schema=SCHEMA
    )

    op.create_table(
        "pagamentos",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("pedido_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("forma", sa.String(10), nullable=False),
        sa.Column("valor", sa.Numeric(10, 2), nullable=False),
        sa.Column("transacao_externa_id", sa.String(64), nullable=True),
        sa.Column("motivo_recusa", sa.String(60), nullable=True),
        sa.Column("tentativas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("solicitado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("concluido_em", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["pedido_id"], [f"{SCHEMA}.pedidos.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("transacao_externa_id", name="pagamentos_transacao_externa_unica"),
        sa.CheckConstraint(_valor_em("status", STATUS_PAGAMENTO), name="pagamentos_status"),
        sa.CheckConstraint(_valor_em("forma", FORMAS_PAGAMENTO), name="pagamentos_forma"),
        sa.CheckConstraint("valor > 0", name="pagamentos_valor_positivo"),
        sa.CheckConstraint("tentativas >= 0", name="pagamentos_tentativas_nao_negativas"),
        schema=SCHEMA,
    )
    op.create_index(
        "pagamentos_ativo_unico",
        "pagamentos",
        ["pedido_id"],
        unique=True,
        schema=SCHEMA,
        postgresql_where=sa.text("status IN ('PENDENTE', 'APROVADO')"),
    )

    op.create_table(
        "webhooks_recebidos",
        sa.Column("event_id", sa.Uuid(), primary_key=True),
        sa.Column("transacao_externa_id", sa.String(64), nullable=False),
        sa.Column("tipo", sa.String(40), nullable=False),
        sa.Column("payload_hash", sa.CHAR(64), nullable=False),
        sa.Column("recebido_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema=SCHEMA,
    )

    op.create_table(
        "lancamentos_fidelidade",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("cliente_id", sa.Uuid(), nullable=False),
        sa.Column("pedido_id", sa.Uuid(), nullable=False),
        sa.Column("tipo", sa.String(10), nullable=False),
        sa.Column("pontos", sa.Integer(), nullable=False),
        _criado_em(),
        sa.ForeignKeyConstraint(["cliente_id"], [f"{SCHEMA}.clientes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["pedido_id"], [f"{SCHEMA}.pedidos.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("pedido_id", "tipo", name="lancamentos_pedido_tipo_unico"),
        sa.CheckConstraint(_valor_em("tipo", TIPOS_LANCAMENTO), name="lancamentos_tipo"),
        sa.CheckConstraint(
            "(tipo = 'CREDITO' AND pontos > 0) OR (tipo = 'ESTORNO' AND pontos < 0)",
            name="lancamentos_sinal_dos_pontos",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "lancamentos_cliente_idx",
        "lancamentos_fidelidade",
        ["cliente_id", sa.text("criado_em DESC")],
        schema=SCHEMA,
    )

    op.create_table(
        "idempotency_keys",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("sujeito", sa.String(80), nullable=False),
        sa.Column("rota", sa.String(120), nullable=False),
        sa.Column("chave", sa.Uuid(), nullable=False),
        sa.Column("request_hash", sa.CHAR(64), nullable=False),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("resposta", postgresql.JSONB(), nullable=True),
        _criado_em(),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("sujeito", "rota", "chave", name="idempotency_keys_escopo_unico"),
        sa.CheckConstraint(_valor_em("status", STATUS_IDEMPOTENCIA), name="idempotency_keys_status"),
        schema=SCHEMA,
    )

    op.create_table(
        "auditoria",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("ocorrido_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("ator_tipo", sa.String(12), nullable=False),
        sa.Column("ator_id", sa.String(64), nullable=False),
        sa.Column("acao", sa.String(60), nullable=False),
        sa.Column("entidade", sa.String(40), nullable=False),
        sa.Column("entidade_id", sa.String(64), nullable=False),
        sa.Column("unidade_id", sa.BigInteger(), nullable=True),
        sa.Column("dados", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("request_id", sa.String(64), nullable=True),
        sa.Column("ip", postgresql.INET(), nullable=True),
        sa.ForeignKeyConstraint(["unidade_id"], ["catalogo.unidades.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(_valor_em("ator_tipo", TIPOS_ATOR), name="auditoria_ator_tipo"),
        schema=SCHEMA,
    )
    op.create_index("auditoria_entidade_idx", "auditoria", ["entidade", "entidade_id"], schema=SCHEMA)
    op.create_index(
        "auditoria_unidade_data_idx", "auditoria", ["unidade_id", sa.text("ocorrido_em DESC")], schema=SCHEMA
    )

    op.create_table(
        "outbox_eventos",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("aggregatetype", sa.String(40), nullable=False),
        sa.Column("aggregateid", sa.String(64), nullable=False),
        sa.Column("type", sa.String(80), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("ocorrido_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema=SCHEMA,
    )
    op.create_index("outbox_ocorrido_em_idx", "outbox_eventos", ["ocorrido_em"], schema=SCHEMA)

    op.execute("GRANT SELECT ON vendas.outbox_eventos TO debezium")


def downgrade() -> None:
    op.execute("REVOKE SELECT ON vendas.outbox_eventos FROM debezium")
    for tabela in (
        "outbox_eventos",
        "auditoria",
        "idempotency_keys",
        "lancamentos_fidelidade",
        "webhooks_recebidos",
        "pagamentos",
        "historico_status_pedido",
        "itens_pedido",
        "pedidos",
        "refresh_tokens",
        "consentimentos",
        "clientes",
    ):
        op.drop_table(tabela, schema=SCHEMA)
