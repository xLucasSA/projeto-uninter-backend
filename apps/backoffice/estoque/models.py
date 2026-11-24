from django.conf import settings
from django.db import models
from django.db.models.functions import Now

from catalogo.models import Produto
from core.models import UnidadeScopedModel


class TipoMovimentacao(models.TextChoices):
    ENTRADA = "ENTRADA", "Entrada"
    SAIDA_PEDIDO = "SAIDA_PEDIDO", "Saída por pedido"
    ESTORNO_PEDIDO = "ESTORNO_PEDIDO", "Estorno de pedido"
    AJUSTE = "AJUSTE", "Ajuste"


class OrigemMovimentacao(models.TextChoices):
    BACKOFFICE = "BACKOFFICE", "Back-office"
    API = "API", "API"


class Estoque(UnidadeScopedModel):
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT, related_name="estoques")
    quantidade = models.IntegerField(default=0)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "estoque"
        verbose_name = "estoque"
        verbose_name_plural = "estoque"
        ordering = ["unidade", "produto"]
        constraints = [
            models.UniqueConstraint(fields=["unidade", "produto"], name="estoque_unidade_produto_unico"),
            models.CheckConstraint(
                condition=models.Q(quantidade__gte=0), name="estoque_quantidade_nao_negativa"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.produto} @ {self.unidade}: {self.quantidade}"


class MovimentacaoEstoque(UnidadeScopedModel):
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT, related_name="movimentacoes")
    tipo = models.CharField(max_length=20, choices=TipoMovimentacao.choices)
    origem = models.CharField(max_length=12, choices=OrigemMovimentacao.choices)
    quantidade = models.IntegerField()
    saldo_apos = models.IntegerField()
    # Referência lógica a vendas.pedidos, sem FK: uma FK criaria dependência circular entre as
    # migrations do Django (catalogo) e do Alembic (vendas).
    pedido_id = models.UUIDField(null=True, blank=True)
    funcionario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="movimentacoes_estoque",
    )
    motivo = models.CharField(max_length=200, null=True, blank=True)  # noqa: DJ001 (a API grava NULL)
    criado_em = models.DateTimeField(db_default=Now(), editable=False)

    class Meta:
        db_table = "movimentacao_estoque"
        verbose_name = "movimentação de estoque"
        verbose_name_plural = "movimentações de estoque"
        ordering = ["-criado_em"]
        indexes = [
            models.Index(fields=["unidade", "produto", "-criado_em"], name="mov_estoque_saldo_idx"),
            models.Index(fields=["pedido_id"], name="mov_estoque_pedido_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=~models.Q(quantidade=0), name="mov_estoque_quantidade_nao_zero"),
            models.CheckConstraint(
                condition=models.Q(tipo__in=TipoMovimentacao.values), name="mov_estoque_tipo_valido"
            ),
            models.CheckConstraint(
                condition=models.Q(origem__in=OrigemMovimentacao.values), name="mov_estoque_origem_valida"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.tipo} {self.quantidade:+d} {self.produto} @ {self.unidade}"
