from typing import cast

from fastapi import Depends, Request

from raizes_api.api.dependencies.autenticacao import obter_emissor_tokens
from raizes_api.api.dependencies.consultas import obter_verificacao_de_escopo
from raizes_api.api.dependencies.infraestrutura import obter_banco, obter_relogio, obter_uow
from raizes_api.api.schemas.pagamentos import resposta_de_pagamento_aceito
from raizes_api.api.schemas.pedidos import resposta_de_pedido_criado
from raizes_api.application.autorizacao import VerificacaoDeEscopo
from raizes_api.application.commands.autenticacao.login import (
    LoginCliente,
    LoginDispositivo,
    LoginFuncionario,
    RegistroDeLoginFalho,
)
from raizes_api.application.commands.autenticacao.renovacao import EncerrarSessao, RenovarSessao
from raizes_api.application.commands.autenticacao.sessoes import EmissaoDeSessao, ValidadesSessao
from raizes_api.application.commands.clientes.cadastro import CadastrarCliente
from raizes_api.application.commands.clientes.consentimentos import (
    ConcederConsentimento,
    RevogarConsentimento,
)
from raizes_api.application.commands.pagamentos.solicitacao import SolicitarPagamento
from raizes_api.application.commands.pagamentos.webhook import ProcessarWebhookPagamento
from raizes_api.application.commands.pedidos.cancelamento import CancelarPedido
from raizes_api.application.commands.pedidos.criacao import CriarPedido
from raizes_api.application.commands.pedidos.status import AtualizarStatusPedido
from raizes_api.application.ports.gateway_pagamento import GatewayPagamento
from raizes_api.application.ports.relogio import Relogio
from raizes_api.application.ports.seguranca import EmissorTokens, HasherSenha
from raizes_api.application.ports.unit_of_work import UnitOfWork
from raizes_api.application.queries.clientes import ObterMeusDados
from raizes_api.infrastructure.auditoria import GravadorAuditoriaIndependenteSql
from raizes_api.infrastructure.db.banco import BancoDeDados


def obter_hasher(request: Request) -> HasherSenha:
    return cast(HasherSenha, request.app.state.hasher)


def obter_emissao_de_sessao(
    request: Request,
    emissor: EmissorTokens = Depends(obter_emissor_tokens),
    relogio: Relogio = Depends(obter_relogio),
) -> EmissaoDeSessao:
    return EmissaoDeSessao(emissor, relogio, cast(ValidadesSessao, request.app.state.validades_sessao))


def obter_registro_de_login_falho(
    banco: BancoDeDados = Depends(obter_banco), relogio: Relogio = Depends(obter_relogio)
) -> RegistroDeLoginFalho:
    return RegistroDeLoginFalho(GravadorAuditoriaIndependenteSql(banco.fabrica_sessoes, relogio))


def obter_login_cliente(
    uow: UnitOfWork = Depends(obter_uow),
    hasher: HasherSenha = Depends(obter_hasher),
    sessoes: EmissaoDeSessao = Depends(obter_emissao_de_sessao),
    falhas: RegistroDeLoginFalho = Depends(obter_registro_de_login_falho),
) -> LoginCliente:
    return LoginCliente(uow, hasher, sessoes, falhas)


def obter_login_funcionario(
    uow: UnitOfWork = Depends(obter_uow),
    hasher: HasherSenha = Depends(obter_hasher),
    sessoes: EmissaoDeSessao = Depends(obter_emissao_de_sessao),
    falhas: RegistroDeLoginFalho = Depends(obter_registro_de_login_falho),
) -> LoginFuncionario:
    return LoginFuncionario(uow, hasher, sessoes, falhas)


def obter_login_dispositivo(
    uow: UnitOfWork = Depends(obter_uow),
    hasher: HasherSenha = Depends(obter_hasher),
    sessoes: EmissaoDeSessao = Depends(obter_emissao_de_sessao),
    falhas: RegistroDeLoginFalho = Depends(obter_registro_de_login_falho),
    relogio: Relogio = Depends(obter_relogio),
) -> LoginDispositivo:
    return LoginDispositivo(uow, hasher, sessoes, falhas, relogio)


def obter_renovar_sessao(
    uow: UnitOfWork = Depends(obter_uow),
    sessoes: EmissaoDeSessao = Depends(obter_emissao_de_sessao),
    relogio: Relogio = Depends(obter_relogio),
) -> RenovarSessao:
    return RenovarSessao(uow, sessoes, relogio)


def obter_encerrar_sessao(
    uow: UnitOfWork = Depends(obter_uow), relogio: Relogio = Depends(obter_relogio)
) -> EncerrarSessao:
    return EncerrarSessao(uow, relogio)


def obter_cadastrar_cliente(
    uow: UnitOfWork = Depends(obter_uow),
    hasher: HasherSenha = Depends(obter_hasher),
    relogio: Relogio = Depends(obter_relogio),
) -> CadastrarCliente:
    return CadastrarCliente(uow, hasher, relogio)


def obter_meus_dados(uow: UnitOfWork = Depends(obter_uow)) -> ObterMeusDados:
    return ObterMeusDados(uow)


def obter_conceder_consentimento(
    uow: UnitOfWork = Depends(obter_uow), relogio: Relogio = Depends(obter_relogio)
) -> ConcederConsentimento:
    return ConcederConsentimento(uow, relogio)


def obter_revogar_consentimento(
    uow: UnitOfWork = Depends(obter_uow), relogio: Relogio = Depends(obter_relogio)
) -> RevogarConsentimento:
    return RevogarConsentimento(uow, relogio)


def obter_criar_pedido(
    uow: UnitOfWork = Depends(obter_uow),
    relogio: Relogio = Depends(obter_relogio),
    escopo: VerificacaoDeEscopo = Depends(obter_verificacao_de_escopo),
) -> CriarPedido:
    return CriarPedido(uow, relogio, escopo, resposta_de_pedido_criado)


def obter_atualizar_status(
    uow: UnitOfWork = Depends(obter_uow),
    relogio: Relogio = Depends(obter_relogio),
    escopo: VerificacaoDeEscopo = Depends(obter_verificacao_de_escopo),
) -> AtualizarStatusPedido:
    return AtualizarStatusPedido(uow, relogio, escopo)


def obter_cancelar_pedido(
    uow: UnitOfWork = Depends(obter_uow),
    relogio: Relogio = Depends(obter_relogio),
    escopo: VerificacaoDeEscopo = Depends(obter_verificacao_de_escopo),
) -> CancelarPedido:
    return CancelarPedido(uow, relogio, escopo)


def obter_gateway_pagamento(request: Request) -> GatewayPagamento:
    return cast(GatewayPagamento, request.app.state.gateway_pagamento)


def obter_solicitar_pagamento(
    uow: UnitOfWork = Depends(obter_uow),
    relogio: Relogio = Depends(obter_relogio),
    escopo: VerificacaoDeEscopo = Depends(obter_verificacao_de_escopo),
    gateway: GatewayPagamento = Depends(obter_gateway_pagamento),
) -> SolicitarPagamento:
    return SolicitarPagamento(uow, relogio, escopo, gateway, resposta_de_pagamento_aceito)


def obter_processar_webhook(
    uow: UnitOfWork = Depends(obter_uow), relogio: Relogio = Depends(obter_relogio)
) -> ProcessarWebhookPagamento:
    return ProcessarWebhookPagamento(uow, relogio)
