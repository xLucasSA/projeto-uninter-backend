import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from raizes_api.settings import Settings

# As migrations são escritas à mão (sem autogenerate): o schema catalogo pertence ao Django.
VERSION_TABLE_SCHEMA = "vendas"

if context.config.config_file_name:
    fileConfig(context.config.config_file_name)


def executar_migracoes(conexao: Connection) -> None:
    context.configure(
        connection=conexao,
        target_metadata=None,
        version_table_schema=VERSION_TABLE_SCHEMA,
        transaction_per_migration=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def executar_online() -> None:
    engine = create_async_engine(Settings().database_url, poolclass=pool.NullPool)
    async with engine.connect() as conexao:
        await conexao.run_sync(executar_migracoes)
    await engine.dispose()


if context.is_offline_mode():
    raise SystemExit("Modo offline não suportado: rode `alembic upgrade head` com o banco disponível.")

asyncio.run(executar_online())
