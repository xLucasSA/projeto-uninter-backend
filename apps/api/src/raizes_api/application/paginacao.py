from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Paginacao:
    pagina: int
    limite: int

    @property
    def deslocamento(self) -> int:
        return (self.pagina - 1) * self.limite

    def recortar[T](self, itens: Sequence[T]) -> "Pagina[T]":
        return Pagina(
            itens=tuple(itens[self.deslocamento : self.deslocamento + self.limite]),
            pagina=self.pagina,
            limite=self.limite,
            total=len(itens),
        )


@dataclass(frozen=True, slots=True)
class Pagina[T]:
    itens: tuple[T, ...]
    pagina: int
    limite: int
    total: int
