from datetime import date, datetime
from zoneinfo import ZoneInfo

FUSO_DA_REDE = ZoneInfo("America/Sao_Paulo")


def data_local(instante: datetime) -> date:
    """Data civil da rede. O banco guarda UTC, mas "hoje" no cardápio é o dia em São Paulo."""
    return instante.astimezone(FUSO_DA_REDE).date()
