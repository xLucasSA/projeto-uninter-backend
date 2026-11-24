import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from raizes_api.domain.clientes.erros import ConsentimentoJaAtivo, ConsentimentoNaoEncontrado
from raizes_api.domain.compartilhado.atores import AtorAutenticado, Perfil, TipoAtor
from raizes_api.domain.compartilhado.canais import CanalPedido
from raizes_api.domain.compartilhado.contato import Telefone, normalizar_email


class FinalidadeConsentimento(StrEnum):
    FIDELIDADE = "FIDELIDADE"
    MARKETING = "MARKETING"


@dataclass(eq=False, slots=True)
class Consentimento:
    """Prova do consentimento (LGPD art. 8º §2º): revogar preenche `revogado_em`, nunca apaga."""

    id: uuid.UUID
    finalidade: FinalidadeConsentimento
    versao_termo: str
    canal_origem: CanalPedido
    concedido_em: datetime
    revogado_em: datetime | None = None

    def esta_ativo(self) -> bool:
        return self.revogado_em is None

    def revogar(self, agora: datetime) -> None:
        self.revogado_em = agora


@dataclass(eq=False, slots=True)
class Cliente:
    id: uuid.UUID
    nome: str
    email: str
    telefone: Telefone | None
    senha_hash: str | None
    criado_em: datetime
    consentimentos: list[Consentimento] = field(default_factory=list)
    anonimizado_em: datetime | None = None

    @classmethod
    def cadastrar(
        cls, *, nome: str, email: str, telefone: Telefone | None, senha_hash: str, agora: datetime
    ) -> "Cliente":
        return cls(
            id=uuid.uuid4(),
            nome=nome.strip(),
            email=normalizar_email(email),
            telefone=telefone,
            senha_hash=senha_hash,
            criado_em=agora,
        )

    def pode_autenticar(self) -> bool:
        return self.anonimizado_em is None and self.senha_hash is not None

    def como_ator(self) -> AtorAutenticado:
        return AtorAutenticado(tipo=TipoAtor.CLIENTE, id=str(self.id), perfis=frozenset({Perfil.CLIENTE}))

    def tem_consentimento_ativo(self, finalidade: FinalidadeConsentimento) -> bool:
        return self._consentimento_ativo(finalidade) is not None

    def conceder_consentimento(
        self,
        finalidade: FinalidadeConsentimento,
        *,
        versao_termo: str,
        canal_origem: CanalPedido,
        agora: datetime,
    ) -> Consentimento:
        if self.tem_consentimento_ativo(finalidade):
            raise ConsentimentoJaAtivo()
        consentimento = Consentimento(
            id=uuid.uuid4(),
            finalidade=finalidade,
            versao_termo=versao_termo,
            canal_origem=canal_origem,
            concedido_em=agora,
        )
        self.consentimentos.append(consentimento)
        return consentimento

    def revogar_consentimento(self, finalidade: FinalidadeConsentimento, agora: datetime) -> Consentimento:
        consentimento = self._consentimento_ativo(finalidade)
        if consentimento is None:
            raise ConsentimentoNaoEncontrado()
        consentimento.revogar(agora)
        return consentimento

    def _consentimento_ativo(self, finalidade: FinalidadeConsentimento) -> Consentimento | None:
        return next(
            (item for item in self.consentimentos if item.finalidade == finalidade and item.esta_ativo()),
            None,
        )
