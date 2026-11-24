from typing import Literal

from raizes_api.api.schemas.base import SchemaBase


class StatusSaudeResponse(SchemaBase):
    status: Literal["ok"] = "ok"
