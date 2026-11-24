from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True, slots=True)
class DetalheErro:
    campo: str
    problema: str


class ErroDominio(Exception):
    """Base das violações de regra de negócio. A tradução para HTTP fica em `api/errors.py`."""

    codigo: ClassVar[str] = "ERRO_DOMINIO"
    mensagem_padrao: ClassVar[str] = "A operação viola uma regra de negócio."

    def __init__(self, mensagem: str | None = None, detalhes: Sequence[DetalheErro] = ()) -> None:
        self.mensagem = mensagem or self.mensagem_padrao
        self.detalhes = tuple(detalhes)
        super().__init__(self.mensagem)


class PermissaoNegada(ErroDominio):
    codigo = "PERMISSAO_NEGADA"
    mensagem_padrao = "Seu perfil não tem permissão para executar esta ação."


class ForaDoEscopoUnidade(ErroDominio):
    codigo = "FORA_DO_ESCOPO_UNIDADE"
    mensagem_padrao = "A unidade não faz parte do seu escopo de acesso."
