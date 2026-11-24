import uuid

from fastapi import APIRouter, Depends, Response, status

from raizes_api.api.dependencies.autenticacao import exigir_perfis
from raizes_api.api.dependencies.casos_de_uso import (
    obter_cadastrar_cliente,
    obter_conceder_consentimento,
    obter_meus_dados,
    obter_revogar_consentimento,
)
from raizes_api.api.openapi import respostas_de_erro
from raizes_api.api.schemas.clientes import (
    CadastroClienteRequest,
    ClienteResponse,
    ConsentimentoRequest,
    ConsentimentoResponse,
    FinalidadeImplementada,
)
from raizes_api.application.commands.clientes.cadastro import CadastrarCliente, DadosCadastroCliente
from raizes_api.application.commands.clientes.consentimentos import (
    ConcederConsentimento,
    ConsentimentoSolicitado,
    RevogarConsentimento,
)
from raizes_api.application.queries.clientes import ObterMeusDados
from raizes_api.domain.compartilhado.atores import AtorAutenticado, Perfil
from raizes_api.domain.compartilhado.contato import Telefone

LOCALIZACAO_DO_TITULAR = "/clientes/me"

router = APIRouter(prefix="/clientes", tags=["Clientes"])
exigir_cliente = exigir_perfis(Perfil.CLIENTE)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar cliente",
    description=(
        "Cria a conta do cliente. Telefone opcional, no formato E.164. Senha com pelo menos 8 caracteres, "
        "letras e números. Consentimentos opcionais (LGPD): hoje só a finalidade `FIDELIDADE`."
    ),
    responses=respostas_de_erro(409, 422),
)
async def cadastrar_cliente(
    corpo: CadastroClienteRequest,
    response: Response,
    caso_de_uso: CadastrarCliente = Depends(obter_cadastrar_cliente),
) -> ClienteResponse:
    cliente = await caso_de_uso.executar(
        DadosCadastroCliente(
            nome=corpo.nome,
            email=corpo.email,
            telefone=Telefone(corpo.telefone) if corpo.telefone else None,
            senha=corpo.senha,
            consentimentos=tuple(_consentimento_solicitado(item) for item in corpo.consentimentos),
        )
    )
    response.headers["Location"] = LOCALIZACAO_DO_TITULAR
    return ClienteResponse.de(cliente)


@router.get(
    "/me",
    summary="Meus dados",
    description="Dados pessoais e histórico de consentimentos do próprio cliente (LGPD, direito de acesso).",
    responses=respostas_de_erro(401, 403),
)
async def obter_meus_dados_do_cliente(
    ator: AtorAutenticado = Depends(exigir_cliente),
    consulta: ObterMeusDados = Depends(obter_meus_dados),
) -> ClienteResponse:
    return ClienteResponse.de(await consulta.executar(uuid.UUID(ator.id)))


@router.post(
    "/me/consentimentos",
    status_code=status.HTTP_201_CREATED,
    summary="Conceder consentimento",
    description=(
        "Registra o consentimento com a versão do termo e o canal de origem. Um ativo por finalidade."
    ),
    responses=respostas_de_erro(401, 403, 409, 422),
)
async def conceder_consentimento(
    corpo: ConsentimentoRequest,
    response: Response,
    ator: AtorAutenticado = Depends(exigir_cliente),
    caso_de_uso: ConcederConsentimento = Depends(obter_conceder_consentimento),
) -> ConsentimentoResponse:
    consentimento = await caso_de_uso.executar(uuid.UUID(ator.id), _consentimento_solicitado(corpo))
    response.headers["Location"] = LOCALIZACAO_DO_TITULAR
    return ConsentimentoResponse.de(consentimento)


@router.delete(
    "/me/consentimentos/{finalidade}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Revogar consentimento",
    description=(
        "Revoga o consentimento ativo da finalidade. O registro é mantido como prova (LGPD art. 8º §2º); "
        "pontos já acumulados permanecem, mas novos pedidos deixam de pontuar."
    ),
    responses=respostas_de_erro(401, 403, 404, 422),
)
async def revogar_consentimento(
    finalidade: FinalidadeImplementada,
    ator: AtorAutenticado = Depends(exigir_cliente),
    caso_de_uso: RevogarConsentimento = Depends(obter_revogar_consentimento),
) -> Response:
    await caso_de_uso.executar(uuid.UUID(ator.id), finalidade)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _consentimento_solicitado(corpo: ConsentimentoRequest) -> ConsentimentoSolicitado:
    return ConsentimentoSolicitado(
        finalidade=corpo.finalidade, versao_termo=corpo.versao_termo, canal_origem=corpo.canal_origem
    )
