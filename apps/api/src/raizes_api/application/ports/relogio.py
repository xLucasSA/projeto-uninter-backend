from datetime import datetime
from typing import Protocol


class Relogio(Protocol):
    def agora(self) -> datetime:
        """Instante atual com fuso horário (UTC)."""
        ...
