from fastapi import APIRouter, Depends

from raizes_api.api.dependencies.infraestrutura import obter_verificacao_prontidao
from raizes_api.api.openapi import respostas_de_erro
from raizes_api.api.schemas.saude import StatusSaudeResponse
from raizes_api.application.ports.prontidao import VerificacaoProntidao

router = APIRouter(prefix="/health", tags=["Health"])


@router.get(
    "/live",
    summary="Processo no ar",
    description="Responde enquanto o processo estiver de pé, sem consultar dependências.",
)
async def verificar_vida() -> StatusSaudeResponse:
    return StatusSaudeResponse()


@router.get(
    "/ready",
    summary="Pronto para receber tráfego",
    description="Confirma que o banco de dados responde. Retorna 503 `SERVICO_INDISPONIVEL` caso contrário.",
    responses=respostas_de_erro(503),
)
async def verificar_prontidao(
    verificacao: VerificacaoProntidao = Depends(obter_verificacao_prontidao),
) -> StatusSaudeResponse:
    await verificacao.verificar()
    return StatusSaudeResponse()
