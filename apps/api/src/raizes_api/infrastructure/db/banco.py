import asyncio

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from raizes_api.application.erros import ServicoIndisponivel

TIMEOUT_VERIFICACAO_SEGUNDOS = 2


class BancoDeDados:
    def __init__(self, url: str) -> None:
        self.engine = create_async_engine(url, pool_pre_ping=True, pool_size=10, max_overflow=10)
        self.fabrica_sessoes: async_sessionmaker[AsyncSession] = async_sessionmaker(
            self.engine, expire_on_commit=False
        )

    async def verificar(self) -> None:
        try:
            async with asyncio.timeout(TIMEOUT_VERIFICACAO_SEGUNDOS), self.engine.connect() as conexao:
                await conexao.execute(text("SELECT 1"))
        except (SQLAlchemyError, OSError, TimeoutError) as erro:
            raise ServicoIndisponivel("O banco de dados não está acessível.") from erro

    async def encerrar(self) -> None:
        await self.engine.dispose()
