from typing import Annotated, cast

from fastapi import Depends, Header, Request

from raizes_api.application.ports.seguranca import VerificadorAssinaturaWebhook


def obter_verificador_webhook(request: Request) -> VerificadorAssinaturaWebhook:
    return cast(VerificadorAssinaturaWebhook, request.app.state.verificador_webhook)


async def exigir_assinatura_do_gateway(
    request: Request,
    timestamp: Annotated[
        str | None, Header(alias="X-Webhook-Timestamp", description="Unix epoch em segundos.")
    ] = None,
    assinatura: Annotated[
        str | None,
        Header(alias="X-Signature", description='`sha256=` + HMAC-SHA256 hex de `"{timestamp}.{corpo}"`.'),
    ] = None,
    verificador: VerificadorAssinaturaWebhook = Depends(obter_verificador_webhook),
) -> bytes:
    """O webhook não usa JWT: quem autentica é a assinatura do corpo bruto.

    As dependências rodam antes da validação do corpo, então um corpo forjado recebe 401, não 422.
    Retorna o corpo bruto, que alimenta a deduplicação (hash do payload).
    """
    corpo = await request.body()
    verificador.verificar(corpo, timestamp, assinatura)
    return corpo
