from fastapi import APIRouter, Depends

from raizes_api.api.dependencies.autenticacao import exigir_perfis
from raizes_api.api.dependencies.consultas import (
    obter_extrato_de_pontos,
    obter_saldo_de_pontos,
    parametros_de_paginacao,
)
from raizes_api.api.openapi import respostas_de_erro
from raizes_api.api.schemas.fidelidade import LancamentoResponse, SaldoResponse
from raizes_api.api.schemas.paginacao import PaginaResponse
from raizes_api.application.paginacao import Paginacao
from raizes_api.application.queries.fidelidade import ConsultarExtratoDePontos, ConsultarSaldoDePontos
from raizes_api.domain.compartilhado.atores import AtorAutenticado, Perfil

router = APIRouter(prefix="/fidelidade", tags=["Fidelidade"])

exigir_cliente = exigir_perfis(Perfil.CLIENTE)


@router.get(
    "/saldo",
    summary="Saldo de pontos",
    description=(
        "1 ponto por real inteiro do pedido pago, com consentimento `FIDELIDADE` ativo na aprovação. "
        "Revogar o consentimento interrompe novos créditos; o saldo existente permanece."
    ),
    responses=respostas_de_erro(401, 403),
)
async def consultar_saldo(
    ator: AtorAutenticado = Depends(exigir_cliente),
    consulta: ConsultarSaldoDePontos = Depends(obter_saldo_de_pontos),
) -> SaldoResponse:
    return SaldoResponse(saldo=await consulta.executar(ator))


@router.get(
    "/extrato",
    summary="Extrato de pontos",
    description="Créditos e estornos, mais recentes primeiro.",
    responses=respostas_de_erro(401, 403, 422),
)
async def consultar_extrato(
    paginacao: Paginacao = Depends(parametros_de_paginacao),
    ator: AtorAutenticado = Depends(exigir_cliente),
    consulta: ConsultarExtratoDePontos = Depends(obter_extrato_de_pontos),
) -> PaginaResponse[LancamentoResponse]:
    pagina = await consulta.executar(ator, paginacao)
    return PaginaResponse[LancamentoResponse].de(
        pagina, [LancamentoResponse.de(item) for item in pagina.itens]
    )
