from collections.abc import Iterable, Iterator
from contextlib import AbstractContextManager, contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class EscopoUnidade:
    ver_todas: bool
    unidade_ids: frozenset[int] = frozenset()

    @classmethod
    def todas(cls) -> "EscopoUnidade":
        return cls(ver_todas=True)

    @classmethod
    def das_unidades(cls, unidade_ids: Iterable[int]) -> "EscopoUnidade":
        return cls(ver_todas=False, unidade_ids=frozenset(unidade_ids))


@runtime_checkable
class PossuiEscopoUnidade(Protocol):
    def escopo_unidade(self) -> EscopoUnidade: ...


_escopo_atual: ContextVar[EscopoUnidade | None] = ContextVar("escopo_unidade", default=None)


def escopo_atual() -> EscopoUnidade | None:
    return _escopo_atual.get()


@contextmanager
def usar_escopo(escopo: EscopoUnidade) -> Iterator[EscopoUnidade]:
    token = _escopo_atual.set(escopo)
    try:
        yield escopo
    finally:
        _escopo_atual.reset(token)


def escopo_sistema() -> AbstractContextManager[EscopoUnidade]:
    """Escopo irrestrito para código fora de request (seed, comandos, testes).

    Sem um escopo declarado, os managers com escopo devolvem queryset vazio (fail-closed).
    """
    return usar_escopo(EscopoUnidade.todas())


def escopo_de(usuario: PossuiEscopoUnidade) -> AbstractContextManager[EscopoUnidade]:
    return usar_escopo(usuario.escopo_unidade())
