from fastapi import APIRouter, Depends, Response, status

from raizes_api.api.dependencies.autenticacao import obter_ator
from raizes_api.api.dependencies.casos_de_uso import (
    obter_encerrar_sessao,
    obter_login_cliente,
    obter_login_dispositivo,
    obter_login_funcionario,
    obter_renovar_sessao,
)
from raizes_api.api.openapi import respostas_de_erro
from raizes_api.api.schemas.autenticacao import (
    DispositivoResponse,
    LoginClienteResponse,
    LoginFuncionarioRequest,
    LoginFuncionarioResponse,
    LoginRequest,
    RefreshTokenRequest,
    SessaoResponse,
    TokenDispositivoRequest,
    TokenDispositivoResponse,
    UsuarioClienteResponse,
    UsuarioFuncionarioResponse,
)
from raizes_api.application.commands.autenticacao.login import (
    LoginCliente,
    LoginDispositivo,
    LoginFuncionario,
)
from raizes_api.application.commands.autenticacao.renovacao import EncerrarSessao, RenovarSessao
from raizes_api.domain.compartilhado.atores import AtorAutenticado

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/login",
    summary="Login de cliente",
    description=(
        "Autentica o cliente por e-mail e senha e emite um access token (15 min) e um refresh token rotativo "
        "(30 dias). Falhas respondem sempre `CREDENCIAIS_INVALIDAS`, sem revelar se o e-mail existe."
    ),
    responses=respostas_de_erro(401, 422),
)
async def login_cliente(
    corpo: LoginRequest, caso_de_uso: LoginCliente = Depends(obter_login_cliente)
) -> LoginClienteResponse:
    resultado = await caso_de_uso.executar(corpo.email, corpo.senha)
    return LoginClienteResponse(
        access_token=resultado.sessao.token_acesso,
        refresh_token=resultado.sessao.refresh_token,
        expires_in=resultado.sessao.expira_em_segundos,
        user=UsuarioClienteResponse(id=resultado.cliente.id, nome=resultado.cliente.nome),
    )


@router.post(
    "/staff/login",
    summary="Login de funcionário",
    description=(
        "Autentica um funcionário do back-office (usuário do Django). O token leva os perfis (Groups; "
        "superusuário vira `MATRIZ`) e as unidades do escopo. Funcionário inativo não autentica."
    ),
    responses=respostas_de_erro(401, 422),
)
async def login_funcionario(
    corpo: LoginFuncionarioRequest, caso_de_uso: LoginFuncionario = Depends(obter_login_funcionario)
) -> LoginFuncionarioResponse:
    resultado = await caso_de_uso.executar(corpo.email, corpo.senha)
    funcionario = resultado.funcionario
    return LoginFuncionarioResponse(
        access_token=resultado.sessao.token_acesso,
        refresh_token=resultado.sessao.refresh_token,
        expires_in=resultado.sessao.expira_em_segundos,
        user=UsuarioFuncionarioResponse(
            id=funcionario.id,
            nome=funcionario.nome,
            perfis=sorted(funcionario.perfis()),
            unidades=sorted(funcionario.unidades),
        ),
    )


@router.post(
    "/dispositivos/token",
    summary="Token de totem",
    description=(
        "Autentica um totem de autoatendimento por `clientId` e `clientSecret`. Emite só access token "
        "(12 h), sem refresh, vinculado à unidade do dispositivo."
    ),
    responses=respostas_de_erro(401, 422),
)
async def token_dispositivo(
    corpo: TokenDispositivoRequest, caso_de_uso: LoginDispositivo = Depends(obter_login_dispositivo)
) -> TokenDispositivoResponse:
    resultado = await caso_de_uso.executar(corpo.client_id, corpo.client_secret)
    dispositivo = resultado.dispositivo
    return TokenDispositivoResponse(
        access_token=resultado.acesso.token_acesso,
        expires_in=resultado.acesso.expira_em_segundos,
        dispositivo=DispositivoResponse(
            id=dispositivo.id, nome=dispositivo.nome, unidade_id=dispositivo.unidade_id
        ),
    )


@router.post(
    "/refresh",
    summary="Renovar sessão",
    description=(
        "Troca o refresh token por um novo par. O token usado deixa de valer; reapresentá-lo indica roubo: "
        "a sessão inteira é revogada e a resposta é `REFRESH_TOKEN_REUTILIZADO`."
    ),
    responses=respostas_de_erro(401, 422),
)
async def renovar_sessao(
    corpo: RefreshTokenRequest, caso_de_uso: RenovarSessao = Depends(obter_renovar_sessao)
) -> SessaoResponse:
    sessao = await caso_de_uso.executar(corpo.refresh_token)
    return SessaoResponse(
        access_token=sessao.token_acesso,
        refresh_token=sessao.refresh_token,
        expires_in=sessao.expira_em_segundos,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Encerrar sessão",
    description=(
        "Revoga a sessão do refresh token informado (todos os refresh tokens dela). O access token atual "
        "expira sozinho em até 15 minutos."
    ),
    responses=respostas_de_erro(401, 422),
)
async def encerrar_sessao(
    corpo: RefreshTokenRequest,
    ator: AtorAutenticado = Depends(obter_ator),
    caso_de_uso: EncerrarSessao = Depends(obter_encerrar_sessao),
) -> Response:
    await caso_de_uso.executar(ator, corpo.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
