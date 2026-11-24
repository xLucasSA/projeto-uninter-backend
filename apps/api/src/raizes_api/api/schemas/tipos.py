from decimal import Decimal
from typing import Annotated

from email_validator import EmailNotValidError, validate_email
from pydantic import AfterValidator, Field, PlainSerializer

from raizes_api.domain.compartilhado.contato import Telefone

TAMANHO_MAXIMO_EMAIL = 254
TAMANHO_MINIMO_SENHA = 8
TAMANHO_MAXIMO_SENHA = 128


def _validar_email(email: str) -> str:
    try:
        return validate_email(email, check_deliverability=False).normalized
    except EmailNotValidError as erro:
        raise ValueError("Informe um e-mail válido, por exemplo maria@exemplo.com.") from erro


def _validar_telefone(numero: str) -> str:
    return Telefone(numero).numero


def _validar_senha_nova(senha: str) -> str:
    tem_letra = any(caractere.isalpha() for caractere in senha)
    tem_numero = any(caractere.isdigit() for caractere in senha)
    if len(senha) < TAMANHO_MINIMO_SENHA or not (tem_letra and tem_numero):
        raise ValueError(
            f"A senha deve ter pelo menos {TAMANHO_MINIMO_SENHA} caracteres, com letras e números."
        )
    return senha


Email = Annotated[
    str,
    Field(max_length=TAMANHO_MAXIMO_EMAIL, json_schema_extra={"format": "email"}),
    AfterValidator(_validar_email),
]
TelefoneE164 = Annotated[str, Field(examples=["+5581999990000"]), AfterValidator(_validar_telefone)]
Senha = Annotated[str, Field(min_length=1, max_length=TAMANHO_MAXIMO_SENHA)]
SenhaNova = Annotated[str, Field(max_length=TAMANHO_MAXIMO_SENHA), AfterValidator(_validar_senha_nova)]
# O Pydantic serializa Decimal como texto; o contrato da API usa número com 2 casas (guideline 05).
DinheiroJson = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]
