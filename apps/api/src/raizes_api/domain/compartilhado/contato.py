import re
from dataclasses import dataclass

FORMATO_E164 = re.compile(r"^\+[1-9]\d{7,14}$")


def normalizar_email(email: str) -> str:
    """E-mail é único sem diferenciar maiúsculas; o banco guarda sempre em minúsculas (CHECK)."""
    return email.strip().lower()


@dataclass(frozen=True, slots=True)
class Telefone:
    numero: str

    def __post_init__(self) -> None:
        if not FORMATO_E164.fullmatch(self.numero):
            raise ValueError("O telefone deve estar no formato E.164, por exemplo +5581999990000.")
