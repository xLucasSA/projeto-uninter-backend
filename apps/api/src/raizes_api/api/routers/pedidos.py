import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Path, Query
from fastapi.responses import JSONResponse
from pydantic import AwareDatetime

from raizes_api.api.dependencies.autenticacao import exigir_perfis
from raizes_api.api.dependencies.casos_de_uso import (
    obter_atualizar_status,
    obter_cancelar_pedido,
    obter_criar_pedido,
)
from raizes_api.api.dependencies.consultas import (
    obter_historico_do_pedido,
    obter_listar_pedidos,
    obter_obter_pedido,
    parametros_de_paginacao,
)
from raizes_api.api.dependencies.idempotencia import HEADER_REPRODUZIDA, uuid_da_chave
from raizes_api.api.openapi import respostas_de_erro
from raizes_api.api.schemas.paginacao import PaginaResponse
from raizes_api.api.schemas.pedidos import (
    AtualizarStatusRequest,
    CancelarPedidoRequest,
    CriarPedidoRequest,
    MudancaDeStatusResponse,
    PedidoResponse,
    PedidoResumoResponse,
)
from raizes_api.application.commands.pedidos.cancelamento import CancelarPedido
from raizes_api.application.commands.pedidos.criacao import (
    ROTA_CRIAR_PEDIDO,
    CriarPedido,
    DadosNovoPedido,
    ItemSolicitado,
)
from raizes_api.application.commands.pedidos.status import AtualizarStatusPedido
from raizes_api.application.idempotencia import chave_idempotente
from raizes_api.application.paginacao import Paginacao
from raizes_api.application.queries.pedidos import (
    CriteriosDaLista,
    ListarPedidos,
    ObterHistoricoDoPedido,
    ObterPedido,
)
from raizes_api.domain.compartilhado.atores import AtorAutenticado, Perfil
from raizes_api.domain.compartilhado.canais import CanalPedido
from raizes_api.domain.compartilhado.contato import Telefone
from raizes_api.domain.pedidos.status import StatusPedido

router = APIRouter(prefix="/pedidos", tags=["Pedidos"])

exigir_quem_cria_pedido = exigir_perfis(Perfil.CLIENTE, Perfil.DISPOSITIVO, Perfil.ATENDENTE)
exigir_quem_lista_pedidos = exigir_perfis(
    Perfil.CLIENTE, Perfil.ATENDENTE, Perfil.COZINHA, Perfil.GERENTE, Perfil.MATRIZ
)
exigir_quem_ve_pedido = exigir_perfis(
    Perfil.CLIENTE, Perfil.DISPOSITIVO, Perfil.ATENDENTE, Perfil.COZINHA, Perfil.GERENTE, Perfil.MATRIZ
)
exigir_quem_opera_pedido = exigir_perfis(Perfil.COZINHA, Perfil.ATENDENTE, Perfil.GERENTE, Perfil.MATRIZ)
exigir_quem_cancela_pedido = exigir_perfis(
    Perfil.CLIENTE, Perfil.DISPOSITIVO, Perfil.ATENDENTE, Perfil.GERENTE, Perfil.MATRIZ
)
IdDoPedido = Annotated[uuid.UUID, Path(alias="pedidoId", description="ID do pedido (UUID).")]


@router.post(
    "",
    status_code=201,
    response_model=PedidoResponse,
    summary="Criar pedido",
    description=(
        "Fluxo crítico. Valida `canalPedido` contra quem está autenticado (cliente: APP/WEB/PICKUP; "
        "totem: TOTEM; atendente: BALCAO), o escopo de unidade e o cardápio do dia; reserva o estoque de "
        "forma atômica e "
        "calcula o total. Exige `Idempotency-Key` (UUID): repetir a chave com o mesmo corpo devolve a mesma "
        "resposta, com o header `Idempotent-Replayed: true`, sem criar outro pedido."
    ),
    responses=respostas_de_erro(400, 401, 403, 404, 409, 422),
)
async def criar_pedido(
    corpo: CriarPedidoRequest,
    ator: AtorAutenticado = Depends(exigir_quem_cria_pedido),
    idempotency_key: str | None = Header(
        default=None, alias="Idempotency-Key", description="UUID gerado pelo cliente para esta criação."
    ),
    caso_de_uso: CriarPedido = Depends(obter_criar_pedido),
) -> JSONResponse:
    chave = chave_idempotente(
        ator,
        rota=ROTA_CRIAR_PEDIDO,
        chave=uuid_da_chave(idempotency_key),
        corpo=corpo.model_dump(mode="json"),
    )
    resultado = await caso_de_uso.executar(ator, _dados_do_pedido(corpo), chave)
    headers = {"Location": f"/pedidos/{resultado.corpo['pedidoId']}"}
    if resultado.reproduzida:
        headers[HEADER_REPRODUZIDA] = "true"
    return JSONResponse(resultado.corpo, status_code=resultado.status_code, headers=headers)


@router.get(
    "",
    summary="Listar pedidos",
    description=(
        "Cliente: só os próprios. Funcionário: as unidades do escopo (`unidadeId` fora dele → 403). "
        "`MATRIZ`: todos. Mais recentes primeiro."
    ),
    responses=respostas_de_erro(401, 403, 422),
)
async def listar_pedidos(
    canal_pedido: CanalPedido | None = Query(default=None, alias="canalPedido"),
    status: StatusPedido | None = Query(default=None),
    unidade_id: int | None = Query(default=None, alias="unidadeId", ge=1),
    data_inicio: AwareDatetime | None = Query(
        default=None, alias="dataInicio", description="ISO 8601 com fuso."
    ),
    data_fim: AwareDatetime | None = Query(default=None, alias="dataFim", description="ISO 8601 com fuso."),
    paginacao: Paginacao = Depends(parametros_de_paginacao),
    ator: AtorAutenticado = Depends(exigir_quem_lista_pedidos),
    consulta: ListarPedidos = Depends(obter_listar_pedidos),
) -> PaginaResponse[PedidoResumoResponse]:
    criterios = CriteriosDaLista(
        unidade_id=unidade_id, canal=canal_pedido, status=status, inicio=data_inicio, fim=data_fim
    )
    pagina = await consulta.executar(ator, criterios, paginacao)
    return PaginaResponse[PedidoResumoResponse].de(
        pagina, [PedidoResumoResponse.de(item) for item in pagina.itens]
    )


@router.get(
    "/{pedidoId}",
    summary="Detalhar pedido",
    description=(
        "Dono (cliente), totem que criou ou funcionário com a unidade no escopo. "
        "Pedido de outro cliente: 404."
    ),
    responses=respostas_de_erro(401, 403, 404, 422),
)
async def obter_pedido(
    pedido_id: IdDoPedido,
    ator: AtorAutenticado = Depends(exigir_quem_ve_pedido),
    consulta: ObterPedido = Depends(obter_obter_pedido),
) -> PedidoResponse:
    return PedidoResponse.de(await consulta.executar(ator, pedido_id))


@router.get(
    "/{pedidoId}/historico",
    summary="Histórico de status",
    description="Mudanças de status em ordem cronológica. Mesmas regras de acesso do detalhe.",
    responses=respostas_de_erro(401, 403, 404, 422),
)
async def obter_historico(
    pedido_id: IdDoPedido,
    ator: AtorAutenticado = Depends(exigir_quem_ve_pedido),
    consulta: ObterHistoricoDoPedido = Depends(obter_historico_do_pedido),
) -> list[MudancaDeStatusResponse]:
    return [MudancaDeStatusResponse.de(mudanca) for mudanca in await consulta.executar(ator, pedido_id)]


@router.patch(
    "/{pedidoId}/status",
    summary="Atualizar status (operação da loja)",
    description=(
        "Fluxo da loja: `PAGO → EM_PREPARO → PRONTO` (cozinha ou gerência) e `PRONTO → ENTREGUE` "
        "(atendente ou gerência). Ordem das checagens: escopo da unidade (403 `FORA_DO_ESCOPO_UNIDADE`), "
        "transição existe (409 `TRANSICAO_STATUS_INVALIDA`), perfil pode fazê-la (403 `PERMISSAO_NEGADA`). "
        "Grava histórico, auditoria `PEDIDO_STATUS_ALTERADO` e o evento na outbox."
    ),
    responses=respostas_de_erro(401, 403, 404, 409, 422),
)
async def atualizar_status(
    pedido_id: IdDoPedido,
    corpo: AtualizarStatusRequest,
    ator: AtorAutenticado = Depends(exigir_quem_opera_pedido),
    caso_de_uso: AtualizarStatusPedido = Depends(obter_atualizar_status),
) -> PedidoResponse:
    return PedidoResponse.de(await caso_de_uso.executar(ator, pedido_id, corpo.status, corpo.motivo))


@router.post(
    "/{pedidoId}/cancelamento",
    summary="Cancelar pedido",
    description=(
        "Aguardando pagamento: dono, totem que criou, atendente ou gerência. Pago: só gerência, com estorno "
        "dos pontos. O estoque sempre volta (`ESTORNO_PEDIDO`). Com pagamento em andamento: 409 "
        "`PAGAMENTO_EM_ANDAMENTO` (o webhook ainda pode aprovar). O reembolso no gateway é evolução "
        "documentada."
    ),
    responses=respostas_de_erro(401, 403, 404, 409, 422),
)
async def cancelar_pedido(
    pedido_id: IdDoPedido,
    corpo: CancelarPedidoRequest,
    ator: AtorAutenticado = Depends(exigir_quem_cancela_pedido),
    caso_de_uso: CancelarPedido = Depends(obter_cancelar_pedido),
) -> PedidoResponse:
    return PedidoResponse.de(await caso_de_uso.executar(ator, pedido_id, corpo.motivo))


def _dados_do_pedido(corpo: CriarPedidoRequest) -> DadosNovoPedido:
    identificacao = corpo.identificacao_cliente
    return DadosNovoPedido(
        canal=corpo.canal_pedido,
        unidade_id=corpo.unidade_id,
        itens=tuple(
            ItemSolicitado(produto_id=item.produto_id, quantidade=item.quantidade) for item in corpo.itens
        ),
        telefone_cliente=Telefone(identificacao.telefone) if identificacao else None,
        observacao=corpo.observacao,
    )
