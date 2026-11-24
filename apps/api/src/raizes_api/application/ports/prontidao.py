from typing import Protocol


class VerificacaoProntidao(Protocol):
    async def verificar(self) -> None:
        """Confirma que as dependências essenciais respondem; senão lança `ServicoIndisponivel`."""
        ...
