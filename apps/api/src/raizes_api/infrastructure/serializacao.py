import json
from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID


def para_json(dados: Mapping[str, object]) -> dict[str, Any]:
    """Converte `dados` de auditoria/outbox em JSON puro (Decimal → número, UUID/datas → texto)."""
    convertido: dict[str, Any] = json.loads(json.dumps(dados, default=_serializar))
    return convertido


def _serializar(valor: object) -> object:
    if isinstance(valor, Decimal):
        return float(valor)
    if isinstance(valor, Enum):
        return valor.value
    if isinstance(valor, datetime | date):
        return valor.isoformat()
    if isinstance(valor, UUID):
        return str(valor)
    raise TypeError(f"Tipo não serializável em JSON: {type(valor).__name__}")
