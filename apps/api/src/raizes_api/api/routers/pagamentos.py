import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Path
from fastapi.responses import JSONResponse

from raizes_api.api.dependencies.autenticacao import exigir_perfis
from raizes_api.api.dependencies.casos_de_uso import obter_solicitar_pagamento
from raizes_api.api.dependencies.consultas import obter_pagamentos_do_pedido
from raizes_api.api.dependencies.idempotencia import (
    HEADER_IDEMPOTENCY_KEY,
    HEADER_REPRODUZIDA,
    uuid_da_chave,
)
from raizes_api.api.openapi import respostas_de_erro
from raizes_api.api.schemas.pagamentos import (
    PagamentoAceitoResponse,
    PagamentoResponse,
    SolicitarPagamentoRequest,
)
from raizes_api.application.commands.pagamentos.solicitacao import (
    ROTA_SOLICITAR_PAGAMENTO,
    DadosPagamento,
    SolicitarPagamento,
)
from raizes_api.application.idempotencia import chave_idempotente
from raizes_api.application.queries.pagamentos import ListarPagamentosDoPedido
from raizes_api.domain.compartilhado.atores import AtorAutenticado, Perfil
from raizes_api.domain.pagamentos.pagamento import FormaPagamento

router = APIRouter(prefix="/pedidos", tags=["Pagamentos"])

exigir_quem_paga = exigir_perfis(Perfil.CLIENTE, Perfil.DISPOSITIVO, Perfil.ATENDENTE)
exigir_quem_ve_pedido = exigir_perfis(
    Perfil.CLIENTE, Perfil.DISPOSITIVO, Perfil.ATENDENTE, Perfil.COZINHA, Perfil.GERENTE, Perfil.MATRIZ
)
IdDoPedido = Annotated[uuid.UUID, Path(alias="pedidoId", description="ID do pedido (UUID).")]


@router.post(
    "/{pedidoId}/pagamentos",
    status_code=202,
    response_model=PagamentoAceitoResponse,
    summary="Solicitar pagamento",
    description=(
        "Registra o pagamento `PENDENTE` e chama o gateway (timeout de 2 s, até 2 retentativas). O resultado "
        "chega pelo webhook: acompanhe em `GET /pedidos/{pedidoId}`. Gateway fora do ar: 503 "
        "`GATEWAY_INDISPONIVEL`, pagamento `ERRO` e o pedido segue aguardando pagamento (nova tentativa com "
        "outra `Idempotency-Key`). Exige `Idempotency-Key` (UUID); a repetição devolve o mesmo 202 com "
        "`Idempotent-Replayed: true`."
    ),
    responses=respostas_de_erro(400, 401, 403, 404, 409, 422, 503),
)
async def solicitar_pagamento(
    pedido_id: IdDoPedido,
    corpo: SolicitarPagamentoRequest,
    ator: AtorAutenticado = Depends(exigir_quem_paga),
    idempotency_key: Annotated[
        str | None,
        Header(alias=HEADER_IDEMPOTENCY_KEY, description="UUID gerado pelo cliente para esta solicitação."),
    ] = None,
    caso_de_uso: SolicitarPagamento = Depends(obter_solicitar_pagamento),
) -> JSONResponse:
    # O pedidoId entra no hash: a mesma chave em outro pedido é reutilização (422), não replay.
    chave = chave_idempotente(
        ator,
        rota=ROTA_SOLICITAR_PAGAMENTO,
        chave=uuid_da_chave(idempotency_key),
        corpo={"pedidoId": str(pedido_id), **corpo.model_dump(mode="json")},
    )
    dados = DadosPagamento(forma=FormaPagamento(corpo.forma_pagamento), token_pagamento=corpo.token_pagamento)
    resultado = await caso_de_uso.executar(ator, pedido_id, dados, chave)
    headers = {HEADER_REPRODUZIDA: "true"} if resultado.reproduzida else {}
    return JSONResponse(resultado.corpo, status_code=resultado.status_code, headers=headers)


@router.get(
    "/{pedidoId}/pagamentos",
    summary="Pagamentos do pedido",
    description="Todas as tentativas, da mais antiga para a mais recente. Mesmas regras de acesso do pedido.",
    responses=respostas_de_erro(401, 403, 404, 422),
)
async def listar_pagamentos(
    pedido_id: IdDoPedido,
    ator: AtorAutenticado = Depends(exigir_quem_ve_pedido),
    consulta: ListarPagamentosDoPedido = Depends(obter_pagamentos_do_pedido),
) -> list[PagamentoResponse]:
    return [PagamentoResponse.de(pagamento) for pagamento in await consulta.executar(ator, pedido_id)]
