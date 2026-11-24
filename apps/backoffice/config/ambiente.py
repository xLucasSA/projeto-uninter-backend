import os

from django.core.exceptions import ImproperlyConfigured

VALORES_VERDADEIROS = frozenset({"1", "true", "yes", "sim", "on"})


def ler_obrigatoria(nome: str) -> str:
    valor = os.environ.get(nome, "").strip()
    if not valor:
        raise ImproperlyConfigured(f"Variável de ambiente obrigatória ausente: {nome}")
    return valor


def ler_booleano(nome: str, *, padrao: bool) -> bool:
    valor = os.environ.get(nome)
    if valor is None:
        return padrao
    return valor.strip().lower() in VALORES_VERDADEIROS


def ler_lista(nome: str) -> list[str]:
    return [item.strip() for item in os.environ.get(nome, "").split(",") if item.strip()]
