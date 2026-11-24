from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from catalogo.models import CardapioUnidade, CategoriaProduto, Produto
from contas.models import Funcionario
from core.escopo import escopo_sistema
from estoque.models import Estoque, MovimentacaoEstoque, OrigemMovimentacao, TipoMovimentacao
from unidades.models import Dispositivo, Regiao, TipoUnidade, Unidade

SENHA_DEMO = "Senha@123"
TOTEM_DEMO_CLIENT_ID = "totem-rec-01"
TOTEM_DEMO_SEGREDO = "totem-rec-01-segredo-demo"
ESTOQUE_INICIAL = 50
ESTOQUE_UNIDADE_DE_CARGA = 1_000_000
MOTIVO_CARGA_INICIAL = "Carga inicial de demonstração"
INICIO_JANELA_JUNINA = (6, 1)
FIM_JANELA_JUNINA = (7, 31)


@dataclass(frozen=True, slots=True)
class UnidadeDemo:
    codigo: str
    nome: str
    cidade: str
    uf: str
    regiao: Regiao
    tipo: TipoUnidade


@dataclass(frozen=True, slots=True)
class ProdutoDemo:
    sku: str
    nome: str
    categoria: CategoriaProduto
    requer_cozinha_completa: bool = False
    sazonal_junino: bool = False


@dataclass(frozen=True, slots=True)
class FuncionarioDemo:
    email: str
    nome: str
    grupo: str | None
    unidades: tuple[str, ...] = ()
    acessa_admin: bool = False
    superuser: bool = False


UNIDADES = [
    UnidadeDemo("REC-01", "Recife Boa Viagem", "Recife", "PE", Regiao.NE, TipoUnidade.COMPLETA),
    UnidadeDemo("FOR-01", "Fortaleza Centro", "Fortaleza", "CE", Regiao.NE, TipoUnidade.COMPLETA),
    UnidadeDemo("SAO-01", "São Paulo Paulista", "São Paulo", "SP", Regiao.SE, TipoUnidade.REDUZIDA),
    UnidadeDemo("CARGA-01", "Unidade de teste de carga", "Recife", "PE", Regiao.NE, TipoUnidade.COMPLETA),
]

PRODUTOS = [
    ProdutoDemo("TAP-QUEIJO", "Tapioca de queijo coalho", CategoriaProduto.TAPIOCA),
    ProdutoDemo("TAP-CARNE-SOL", "Tapioca de carne de sol", CategoriaProduto.TAPIOCA),
    ProdutoDemo("CUS-RECHEADO", "Cuscuz recheado", CategoriaProduto.CUSCUZ),
    ProdutoDemo("BOL-MACAXEIRA", "Bolo de macaxeira", CategoriaProduto.BOLO),
    ProdutoDemo("SUC-CAJA", "Suco de cajá", CategoriaProduto.BEBIDA),
    ProdutoDemo("CAF-COADO", "Café coado", CategoriaProduto.CAFE),
    ProdutoDemo("CMB-CAFE-MANHA", "Combo café da manhã", CategoriaProduto.COMBO),
    ProdutoDemo("SAZ-CANJICA", "Canjica", CategoriaProduto.BOLO, sazonal_junino=True),
    ProdutoDemo("SAZ-PAMONHA", "Pamonha", CategoriaProduto.BOLO, sazonal_junino=True),
    ProdutoDemo("PRA-BAIAO", "Baião de dois", CategoriaProduto.PRATO, requer_cozinha_completa=True),
]

PRECOS_RECIFE = {
    "TAP-QUEIJO": "14.90",
    "TAP-CARNE-SOL": "18.90",
    "CUS-RECHEADO": "16.90",
    "BOL-MACAXEIRA": "8.90",
    "SUC-CAJA": "9.90",
    "CAF-COADO": "5.90",
    "CMB-CAFE-MANHA": "24.90",
    "SAZ-CANJICA": "9.90",
    "SAZ-PAMONHA": "8.90",
    "PRA-BAIAO": "32.90",
}

PRECOS_POR_UNIDADE: dict[str, dict[str, str]] = {
    "REC-01": PRECOS_RECIFE,
    "CARGA-01": PRECOS_RECIFE,
    "FOR-01": {
        "TAP-QUEIJO": "14.50",
        "TAP-CARNE-SOL": "18.50",
        "CUS-RECHEADO": "16.50",
        "BOL-MACAXEIRA": "8.50",
        "SUC-CAJA": "9.50",
        "CAF-COADO": "5.50",
        "CMB-CAFE-MANHA": "23.90",
        "SAZ-CANJICA": "9.50",
        "SAZ-PAMONHA": "8.50",
        "PRA-BAIAO": "31.90",
    },
    "SAO-01": {
        "TAP-QUEIJO": "16.90",
        "TAP-CARNE-SOL": "21.90",
        "CUS-RECHEADO": "19.90",
        "BOL-MACAXEIRA": "10.90",
        "SUC-CAJA": "11.90",
        "CAF-COADO": "6.90",
        "CMB-CAFE-MANHA": "28.90",
        "SAZ-CANJICA": "11.90",
        "SAZ-PAMONHA": "10.90",
    },
}

# Saldo 1 para o cenário de estoque insuficiente (T10 da coleção Postman).
ESTOQUES_ESPECIAIS = {("REC-01", "BOL-MACAXEIRA"): 1}

FUNCIONARIOS = [
    FuncionarioDemo("atendente.rec@raizes.dev", "Atendente Recife", "Atendente", ("REC-01",)),
    FuncionarioDemo("cozinha.rec@raizes.dev", "Cozinha Recife", "Cozinha", ("REC-01",)),
    FuncionarioDemo(
        "estoquista.rec@raizes.dev", "Estoquista Recife", "Estoquista", ("REC-01",), acessa_admin=True
    ),
    FuncionarioDemo("gerente.rec@raizes.dev", "Gerente Recife", "Gerente", ("REC-01",), acessa_admin=True),
    FuncionarioDemo("atendente.sao@raizes.dev", "Atendente São Paulo", "Atendente", ("SAO-01",)),
    FuncionarioDemo("cozinha.sao@raizes.dev", "Cozinha São Paulo", "Cozinha", ("SAO-01",)),
    FuncionarioDemo("matriz@raizes.dev", "Matriz", "Matriz", acessa_admin=True),
    FuncionarioDemo("admin@raizes.dev", "Administrador", None, superuser=True),
]


class Command(BaseCommand):
    help = "Cria os dados de demonstração (idempotente: só cria o que ainda não existe)."

    def handle(self, *args: Any, **options: Any) -> None:
        if not (settings.DEBUG or settings.SEED_DEMO):
            self.stdout.write("Seed de demonstração ignorado: DJANGO_DEBUG e SEED_DEMO estão desligados.")
            return

        with escopo_sistema(), transaction.atomic():
            unidades = self._garantir_unidades()
            produtos = self._garantir_produtos()
            self._garantir_cardapio_e_estoque(unidades, produtos)
            self._garantir_funcionarios(unidades)
            self._garantir_totem(unidades["REC-01"])

        self.stdout.write(self.style.SUCCESS("Seed de demonstração aplicado."))

    def _garantir_unidades(self) -> dict[str, Unidade]:
        unidades = {}
        for dados in UNIDADES:
            unidade, _ = Unidade.objects.get_or_create(
                codigo=dados.codigo,
                defaults={
                    "nome": dados.nome,
                    "cidade": dados.cidade,
                    "uf": dados.uf,
                    "regiao": dados.regiao,
                    "tipo": dados.tipo,
                },
            )
            unidades[dados.codigo] = unidade
        return unidades

    def _garantir_produtos(self) -> dict[str, tuple[Produto, ProdutoDemo]]:
        produtos = {}
        for dados in PRODUTOS:
            produto, _ = Produto.objects.get_or_create(
                sku=dados.sku,
                defaults={
                    "nome": dados.nome,
                    "categoria": dados.categoria,
                    "requer_cozinha_completa": dados.requer_cozinha_completa,
                },
            )
            produtos[dados.sku] = (produto, dados)
        return produtos

    def _garantir_cardapio_e_estoque(
        self, unidades: dict[str, Unidade], produtos: dict[str, tuple[Produto, ProdutoDemo]]
    ) -> None:
        for codigo, precos in PRECOS_POR_UNIDADE.items():
            unidade = unidades[codigo]
            for sku, preco in precos.items():
                produto, dados = produtos[sku]
                self._garantir_item_cardapio(
                    unidade, produto, Decimal(preco), sazonal_junino=dados.sazonal_junino
                )
                self._garantir_estoque(unidade, produto, self._estoque_inicial(codigo, sku))

    def _garantir_item_cardapio(
        self, unidade: Unidade, produto: Produto, preco: Decimal, *, sazonal_junino: bool
    ) -> None:
        if CardapioUnidade.objects.filter(unidade=unidade, produto=produto).exists():
            return
        inicio, fim = self._janela_junina() if sazonal_junino else (None, None)
        item = CardapioUnidade(
            unidade=unidade, produto=produto, preco=preco, disponivel_de=inicio, disponivel_ate=fim
        )
        item.full_clean()
        item.save()

    def _garantir_estoque(self, unidade: Unidade, produto: Produto, quantidade: int) -> None:
        _, criado = Estoque.objects.get_or_create(
            unidade=unidade, produto=produto, defaults={"quantidade": quantidade}
        )
        if not criado:
            return
        MovimentacaoEstoque.objects.create(
            unidade=unidade,
            produto=produto,
            tipo=TipoMovimentacao.ENTRADA,
            origem=OrigemMovimentacao.BACKOFFICE,
            quantidade=quantidade,
            saldo_apos=quantidade,
            motivo=MOTIVO_CARGA_INICIAL,
        )

    def _garantir_funcionarios(self, unidades: dict[str, Unidade]) -> None:
        for dados in FUNCIONARIOS:
            funcionario = Funcionario.objects.filter(email=dados.email).first()
            if funcionario is None:
                funcionario = self._criar_funcionario(dados)
            if dados.grupo:
                funcionario.groups.add(Group.objects.get(name=dados.grupo))
            funcionario.unidades.add(*(unidades[codigo] for codigo in dados.unidades))

    def _criar_funcionario(self, dados: FuncionarioDemo) -> Funcionario:
        if dados.superuser:
            return Funcionario.objects.create_superuser(dados.email, dados.nome, SENHA_DEMO)
        return Funcionario.objects.create_user(
            dados.email, dados.nome, SENHA_DEMO, is_staff=dados.acessa_admin
        )

    def _garantir_totem(self, unidade: Unidade) -> None:
        if Dispositivo.objects.filter(client_id=TOTEM_DEMO_CLIENT_ID).exists():
            return
        totem = Dispositivo(
            unidade=unidade, nome="Totem 01 — Recife Boa Viagem", client_id=TOTEM_DEMO_CLIENT_ID
        )
        totem.definir_segredo(TOTEM_DEMO_SEGREDO)
        totem.save()

    @staticmethod
    def _estoque_inicial(codigo_unidade: str, sku: str) -> int:
        if codigo_unidade == "CARGA-01":
            return ESTOQUE_UNIDADE_DE_CARGA
        return ESTOQUES_ESPECIAIS.get((codigo_unidade, sku), ESTOQUE_INICIAL)

    @staticmethod
    def _janela_junina() -> tuple[date, date]:
        ano = timezone.localdate().year
        return date(ano, *INICIO_JANELA_JUNINA), date(ano, *FIM_JANELA_JUNINA)
