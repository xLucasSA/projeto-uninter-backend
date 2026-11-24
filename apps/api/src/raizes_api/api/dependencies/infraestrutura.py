from typing import cast

from fastapi import Depends, Request

from raizes_api.application.ports.prontidao import VerificacaoProntidao
from raizes_api.application.ports.relogio import Relogio
from raizes_api.application.ports.unit_of_work import UnitOfWork
from raizes_api.infrastructure.db.banco import BancoDeDados
from raizes_api.infrastructure.uow import UnidadeDeTrabalhoSqlAlchemy


def obter_banco(request: Request) -> BancoDeDados:
    return cast(BancoDeDados, request.app.state.banco)


def obter_relogio(request: Request) -> Relogio:
    return cast(Relogio, request.app.state.relogio)


def obter_verificacao_prontidao(banco: BancoDeDados = Depends(obter_banco)) -> VerificacaoProntidao:
    return banco


def obter_uow(
    banco: BancoDeDados = Depends(obter_banco), relogio: Relogio = Depends(obter_relogio)
) -> UnitOfWork:
    return UnidadeDeTrabalhoSqlAlchemy(banco.fabrica_sessoes, relogio)
