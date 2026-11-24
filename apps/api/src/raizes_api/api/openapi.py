from typing import Any

from raizes_api.api.schemas.erros import ErroResponse

DESCRICOES_STATUS = {
    400: "Requisição malformada",
    401: "Não autenticado",
    403: "Sem permissão",
    404: "Não encontrado",
    409: "Conflito com regra de negócio",
    422: "Validação",
    503: "Dependência indisponível",
}


def respostas_de_erro(*status: int) -> dict[int | str, dict[str, Any]]:
    """Documenta no OpenAPI os status de erro da rota, todos no formato `ErroResponse`."""
    return {codigo: {"model": ErroResponse, "description": DESCRICOES_STATUS[codigo]} for codigo in status}


DESCRICAO_API = """
API back-end da rede **Raízes do Nordeste**.

Fluxo crítico: **Pedido → Pagamento (mock) → Atualização de status**, com autenticação JWT,
perfis, escopo por unidade, estoque consistente sob concorrência, idempotência, LGPD e auditoria.

Todas as falhas seguem o mesmo formato (`ErroResponse`), com `requestId` para correlação com os logs.
"""

TAGS = [
    {
        "name": "Auth",
        "description": (
            "Login de clientes, funcionários e totens; renovação rotativa e encerramento da sessão. "
            "Envie o access token em `Authorization: Bearer <token>`."
        ),
    },
    {
        "name": "Clientes",
        "description": "Cadastro, dados do próprio titular e consentimentos (LGPD).",
    },
    {"name": "Unidades", "description": "Unidades da rede, cardápio do dia e saldo de estoque."},
    {"name": "Produtos", "description": "Catálogo de produtos da rede."},
    {
        "name": "Pedidos",
        "description": (
            "Criação com `canalPedido`, reserva de estoque e idempotência; consulta com escopo por unidade; "
            "operação da loja (status) e cancelamento com estorno."
        ),
    },
    {
        "name": "Pagamentos",
        "description": (
            "Solicitação ao gateway simulado (202) e consulta das tentativas. O resultado chega pelo webhook."
        ),
    },
    {
        "name": "Webhooks",
        "description": (
            "Notificações do gateway, autenticadas por HMAC-SHA256 (sem JWT) e deduplicadas por `eventId`."
        ),
    },
    {"name": "Fidelidade", "description": "Saldo e extrato de pontos do cliente autenticado."},
    {"name": "Auditoria", "description": "Trilha das ações sensíveis da API, para a gerência e a matriz."},
    {"name": "Health", "description": "Verificações de vida e prontidão usadas pelo Docker Compose."},
]
