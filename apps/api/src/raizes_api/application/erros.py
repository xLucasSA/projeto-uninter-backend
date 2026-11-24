from raizes_api.domain.compartilhado.erros import ErroDominio


class ServicoIndisponivel(ErroDominio):
    codigo = "SERVICO_INDISPONIVEL"
    mensagem_padrao = "O serviço está temporariamente indisponível."


class TokenAusente(ErroDominio):
    codigo = "TOKEN_AUSENTE"
    mensagem_padrao = "Autenticação obrigatória: envie o header Authorization: Bearer <token>."


class TokenInvalido(ErroDominio):
    codigo = "TOKEN_INVALIDO"
    mensagem_padrao = "O token de acesso é inválido ou expirou."


class CredenciaisInvalidas(ErroDominio):
    codigo = "CREDENCIAIS_INVALIDAS"
    mensagem_padrao = "Credenciais inválidas."


class RefreshTokenInvalido(ErroDominio):
    codigo = "REFRESH_TOKEN_INVALIDO"
    mensagem_padrao = "O refresh token é inválido, expirou ou foi revogado. Faça login novamente."


class RefreshTokenReutilizado(ErroDominio):
    codigo = "REFRESH_TOKEN_REUTILIZADO"
    mensagem_padrao = "O refresh token já foi utilizado. Por segurança, a sessão foi encerrada."


class IdempotencyKeyAusente(ErroDominio):
    codigo = "IDEMPOTENCY_KEY_AUSENTE"
    mensagem_padrao = "Envie o header Idempotency-Key com um UUID."


class IdempotencyKeyReutilizada(ErroDominio):
    codigo = "IDEMPOTENCY_KEY_REUTILIZADA"
    mensagem_padrao = "Esta Idempotency-Key já foi usada com outro corpo de requisição."


class RequisicaoEmProcessamento(ErroDominio):
    codigo = "REQUISICAO_EM_PROCESSAMENTO"
    mensagem_padrao = "Uma requisição com esta Idempotency-Key ainda está em processamento."


class AssinaturaWebhookInvalida(ErroDominio):
    codigo = "ASSINATURA_WEBHOOK_INVALIDA"
    mensagem_padrao = "Assinatura do webhook ausente ou inválida."


class GatewayIndisponivel(ErroDominio):
    codigo = "GATEWAY_INDISPONIVEL"
    mensagem_padrao = (
        "O gateway de pagamento não respondeu. O pedido continua aguardando pagamento: tente novamente."
    )

    def __init__(self, tentativas: int) -> None:
        super().__init__()
        self.tentativas = tentativas
