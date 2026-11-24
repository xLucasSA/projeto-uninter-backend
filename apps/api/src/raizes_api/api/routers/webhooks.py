import hashlib

import structlog
from fastapi import APIRouter, Depends

from raizes_api.api.dependencies.casos_de_uso import obter_processar_webhook
from raizes_api.api.dependencies.webhooks import exigir_assinatura_do_gateway
from raizes_api.api.openapi import respostas_de_erro
from raizes_api.api.schemas.pagamentos import WebhookPagamentoRequest, WebhookResponse
from raizes_api.application.commands.pagamentos.webhook import (
    NotificacaoDePagamento,
    ProcessarWebhookPagamento,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post(
    "/pagamentos",
    summary="Notificação do gateway de pagamento",
    description=(
        'Chamado pelo gateway, sem JWT: a autenticação é o HMAC-SHA256 de `"{timestamp}.{corpo}"` em '
        "`X-Signature`, com timestamp a até 300 s do relógio da API. Idempotente por `eventId`: a repetição "
        "responde 200 `IGNORADO`, sem nova transição nem novo crédito de pontos."
    ),
    responses=respostas_de_erro(401, 422),
)
async def receber_webhook(
    corpo: WebhookPagamentoRequest,
    corpo_bruto: bytes = Depends(exigir_assinatura_do_gateway),
    caso_de_uso: ProcessarWebhookPagamento = Depends(obter_processar_webhook),
) -> WebhookResponse:
    desfecho = await caso_de_uso.executar(
        NotificacaoDePagamento(
            event_id=corpo.event_id,
            tipo=corpo.tipo,
            transacao_id=corpo.transacao_id,
            pagamento_id=corpo.pagamento_id,
            pedido_id=corpo.pedido_id,
            resultado=corpo.status,
            valor=corpo.valor,
            motivo=corpo.motivo,
            hash_do_corpo=hashlib.sha256(corpo_bruto).hexdigest(),
        )
    )
    if desfecho.exige_alerta:
        # Assinado pelo gateway, mas sem correspondência aqui. Só IDs no log, nunca o payload.
        logger.warning("webhook_sem_correspondencia", desfecho=desfecho, event_id=str(corpo.event_id))
    else:
        logger.info("webhook_recebido", desfecho=desfecho, event_id=str(corpo.event_id))
    return WebhookResponse(status="PROCESSADO" if desfecho.aplicado else "IGNORADO")
