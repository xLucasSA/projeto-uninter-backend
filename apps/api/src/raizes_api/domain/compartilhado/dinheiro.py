from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

CENTAVOS = Decimal("0.01")


@dataclass(frozen=True, slots=True, order=True)
class Dinheiro:
    valor: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.valor, Decimal):
            raise TypeError("Dinheiro exige Decimal: float perde precisão em valores monetários.")
        if not self.valor.is_finite() or self.valor < 0:
            raise ValueError(f"Valor monetário inválido: {self.valor}")
        object.__setattr__(self, "valor", self.valor.quantize(CENTAVOS, rounding=ROUND_HALF_UP))

    @classmethod
    def de(cls, valor: Decimal | str | int) -> "Dinheiro":
        return cls(Decimal(valor))

    @classmethod
    def zero(cls) -> "Dinheiro":
        return cls(Decimal(0))

    @classmethod
    def somar(cls, valores: Iterable["Dinheiro"]) -> "Dinheiro":
        return cls(sum((item.valor for item in valores), Decimal(0)))

    def __add__(self, outro: "Dinheiro") -> "Dinheiro":
        return Dinheiro(self.valor + outro.valor)

    def multiplicado_por(self, quantidade: int) -> "Dinheiro":
        return Dinheiro(self.valor * quantidade)

    def reais_inteiros(self) -> int:
        return int(self.valor)
