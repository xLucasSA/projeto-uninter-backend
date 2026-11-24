from typing import cast

from fastapi import Depends, Query, Request

from raizes_api.api.dependencies.infraestrutura import obter_banco, obter_relogio
from raizes_api.application.autorizacao import VerificacaoDeEscopo
from raizes_api.application.paginacao import Paginacao
from raizes_api.application.ports.leitura import (
    LeituraAuditoria,
    LeituraCatalogo,
    LeituraEstoque,
    LeituraFidelidade,
    LeituraPagamentos,
    LeituraPedidos,
)
from raizes_api.application.ports.relogio import Relogio
from raizes_api.application.queries.auditoria import ConsultarAuditoria
from raizes_api.application.queries.catalogo import (
    ConsultarCardapio,
    ListarProdutos,
    ListarUnidades,
    ObterProduto,
    ObterUnidade,
)
from raizes_api.application.queries.estoque import ConsultarEstoque
from raizes_api.application.queries.fidelidade import ConsultarExtratoDePontos, ConsultarSaldoDePontos
from raizes_api.application.queries.pagamentos import ListarPagamentosDoPedido
from raizes_api.application.queries.pedidos import ListarPedidos, ObterHistoricoDoPedido, ObterPedido
from raizes_api.infrastructure.auditoria import GravadorAuditoriaIndependenteSql
from raizes_api.infrastructure.db.banco import BancoDeDados

LIMITE_MAXIMO_POR_PAGINA = 100


def parametros_de_paginacao(
    page: int = Query(default=1, ge=1, description="Página, a partir de 1."),
    limit: int = Query(
        default=10, ge=1, le=LIMITE_MAXIMO_POR_PAGINA, description="Itens por página (máx. 100)."
    ),
) -> Paginacao:
    return Paginacao(pagina=page, limite=limit)


def obter_leitura_catalogo(request: Request) -> LeituraCatalogo:
    return cast(LeituraCatalogo, request.app.state.leitura_catalogo)


def obter_leitura_estoque(request: Request) -> LeituraEstoque:
    return cast(LeituraEstoque, request.app.state.leitura_estoque)


def obter_leitura_pedidos(request: Request) -> LeituraPedidos:
    return cast(LeituraPedidos, request.app.state.leitura_pedidos)


def obter_leitura_pagamentos(request: Request) -> LeituraPagamentos:
    return cast(LeituraPagamentos, request.app.state.leitura_pagamentos)


def obter_leitura_fidelidade(request: Request) -> LeituraFidelidade:
    return cast(LeituraFidelidade, request.app.state.leitura_fidelidade)


def obter_leitura_auditoria(request: Request) -> LeituraAuditoria:
    return cast(LeituraAuditoria, request.app.state.leitura_auditoria)


def obter_verificacao_de_escopo(
    banco: BancoDeDados = Depends(obter_banco), relogio: Relogio = Depends(obter_relogio)
) -> VerificacaoDeEscopo:
    return VerificacaoDeEscopo(GravadorAuditoriaIndependenteSql(banco.fabrica_sessoes, relogio))


def obter_listar_unidades(leitura: LeituraCatalogo = Depends(obter_leitura_catalogo)) -> ListarUnidades:
    return ListarUnidades(leitura)


def obter_obter_unidade(leitura: LeituraCatalogo = Depends(obter_leitura_catalogo)) -> ObterUnidade:
    return ObterUnidade(leitura)


def obter_consultar_cardapio(
    leitura: LeituraCatalogo = Depends(obter_leitura_catalogo), relogio: Relogio = Depends(obter_relogio)
) -> ConsultarCardapio:
    return ConsultarCardapio(leitura, relogio)


def obter_listar_produtos(leitura: LeituraCatalogo = Depends(obter_leitura_catalogo)) -> ListarProdutos:
    return ListarProdutos(leitura)


def obter_obter_produto(leitura: LeituraCatalogo = Depends(obter_leitura_catalogo)) -> ObterProduto:
    return ObterProduto(leitura)


def obter_consultar_estoque(
    catalogo: LeituraCatalogo = Depends(obter_leitura_catalogo),
    estoque: LeituraEstoque = Depends(obter_leitura_estoque),
    escopo: VerificacaoDeEscopo = Depends(obter_verificacao_de_escopo),
) -> ConsultarEstoque:
    return ConsultarEstoque(catalogo, estoque, escopo)


def obter_listar_pedidos(
    leitura: LeituraPedidos = Depends(obter_leitura_pedidos),
    escopo: VerificacaoDeEscopo = Depends(obter_verificacao_de_escopo),
) -> ListarPedidos:
    return ListarPedidos(leitura, escopo)


def obter_obter_pedido(
    leitura: LeituraPedidos = Depends(obter_leitura_pedidos),
    escopo: VerificacaoDeEscopo = Depends(obter_verificacao_de_escopo),
) -> ObterPedido:
    return ObterPedido(leitura, escopo)


def obter_historico_do_pedido(
    leitura: LeituraPedidos = Depends(obter_leitura_pedidos),
    escopo: VerificacaoDeEscopo = Depends(obter_verificacao_de_escopo),
) -> ObterHistoricoDoPedido:
    return ObterHistoricoDoPedido(leitura, escopo)


def obter_pagamentos_do_pedido(
    pedidos: LeituraPedidos = Depends(obter_leitura_pedidos),
    pagamentos: LeituraPagamentos = Depends(obter_leitura_pagamentos),
    escopo: VerificacaoDeEscopo = Depends(obter_verificacao_de_escopo),
) -> ListarPagamentosDoPedido:
    return ListarPagamentosDoPedido(pedidos, pagamentos, escopo)


def obter_saldo_de_pontos(
    leitura: LeituraFidelidade = Depends(obter_leitura_fidelidade),
) -> ConsultarSaldoDePontos:
    return ConsultarSaldoDePontos(leitura)


def obter_extrato_de_pontos(
    leitura: LeituraFidelidade = Depends(obter_leitura_fidelidade),
) -> ConsultarExtratoDePontos:
    return ConsultarExtratoDePontos(leitura)


def obter_consultar_auditoria(
    leitura: LeituraAuditoria = Depends(obter_leitura_auditoria),
    escopo: VerificacaoDeEscopo = Depends(obter_verificacao_de_escopo),
) -> ConsultarAuditoria:
    return ConsultarAuditoria(leitura, escopo)
