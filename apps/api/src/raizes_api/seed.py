"""Cliente de demonstração para testes manuais no Swagger (`python -m raizes_api.seed`).

Idempotente: roda a cada `docker compose up` e não faz nada se o cliente já existir.
"""

import asyncio

import structlog

from raizes_api.application.commands.clientes.cadastro import CadastrarCliente, DadosCadastroCliente
from raizes_api.application.commands.clientes.consentimentos import ConsentimentoSolicitado
from raizes_api.domain.clientes.cliente import FinalidadeConsentimento
from raizes_api.domain.compartilhado.canais import CanalPedido
from raizes_api.domain.compartilhado.contato import Telefone
from raizes_api.infrastructure.db.banco import BancoDeDados
from raizes_api.infrastructure.observabilidade.logs import configurar_logs
from raizes_api.infrastructure.relogio import RelogioSistema
from raizes_api.infrastructure.security.senhas import HasherSenhaArgon2
from raizes_api.infrastructure.uow import UnidadeDeTrabalhoSqlAlchemy
from raizes_api.settings import Settings

VERSAO_TERMO_DEMO = "1.0"
CLIENTE_DEMO = DadosCadastroCliente(
    nome="Maria da Silva",
    email="maria@exemplo.com",
    telefone=Telefone("+5581999990000"),
    senha="Senha@123",
    consentimentos=(
        ConsentimentoSolicitado(
            finalidade=FinalidadeConsentimento.FIDELIDADE,
            versao_termo=VERSAO_TERMO_DEMO,
            canal_origem=CanalPedido.APP,
        ),
    ),
)

logger = structlog.get_logger(__name__)


async def aplicar_seed(settings: Settings) -> None:
    banco = BancoDeDados(settings.database_url)
    relogio = RelogioSistema()
    try:
        async with UnidadeDeTrabalhoSqlAlchemy(banco.fabrica_sessoes, relogio) as uow:
            existente = await uow.clientes.obter_por_email(CLIENTE_DEMO.email)
        if existente is not None:
            logger.info("seed_api_ja_aplicado")
            return
        cadastro = CadastrarCliente(
            UnidadeDeTrabalhoSqlAlchemy(banco.fabrica_sessoes, relogio), HasherSenhaArgon2(), relogio
        )
        await cadastro.executar(CLIENTE_DEMO)
        logger.info("seed_api_aplicado")
    finally:
        await banco.encerrar()


def main() -> None:
    settings = Settings()
    configurar_logs(settings.log_level)
    if not settings.seed_demo:
        logger.info("seed_api_ignorado", motivo="SEED_DEMO desligado")
        return
    asyncio.run(aplicar_seed(settings))


if __name__ == "__main__":
    main()
