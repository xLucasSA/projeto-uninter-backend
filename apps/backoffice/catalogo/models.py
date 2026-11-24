from django.core.exceptions import ValidationError
from django.db import models

from core.models import TimeStampedModel, UnidadeScopedModel


class CategoriaProduto(models.TextChoices):
    TAPIOCA = "TAPIOCA", "Tapioca"
    CUSCUZ = "CUSCUZ", "Cuscuz"
    BOLO = "BOLO", "Bolo"
    PRATO = "PRATO", "Prato"
    BEBIDA = "BEBIDA", "Bebida"
    CAFE = "CAFE", "Café"
    COMBO = "COMBO", "Combo"


class Produto(TimeStampedModel):
    sku = models.CharField(max_length=30, unique=True)
    nome = models.CharField(max_length=120)
    descricao = models.TextField(blank=True)
    categoria = models.CharField(max_length=10, choices=CategoriaProduto.choices)
    requer_cozinha_completa = models.BooleanField(default=False)
    ativo = models.BooleanField(default=True)

    class Meta:
        db_table = "produtos"
        verbose_name = "produto"
        verbose_name_plural = "produtos"
        ordering = ["nome"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(categoria__in=CategoriaProduto.values), name="produtos_categoria_valida"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.sku} — {self.nome}"


class CardapioUnidade(UnidadeScopedModel, TimeStampedModel):
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT, related_name="cardapios")
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    ativo = models.BooleanField(default=True)
    disponivel_de = models.DateField(null=True, blank=True)
    disponivel_ate = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "cardapio_unidade"
        verbose_name = "item do cardápio da unidade"
        verbose_name_plural = "cardápio das unidades"
        ordering = ["unidade", "produto"]
        constraints = [
            models.UniqueConstraint(fields=["unidade", "produto"], name="cardapio_unidade_produto_unico"),
            models.CheckConstraint(condition=models.Q(preco__gt=0), name="cardapio_preco_positivo"),
            models.CheckConstraint(
                condition=(
                    models.Q(disponivel_ate__isnull=True)
                    | models.Q(disponivel_de__isnull=True)
                    | models.Q(disponivel_ate__gte=models.F("disponivel_de"))
                ),
                name="cardapio_janela_valida",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.produto} @ {self.unidade}"

    def clean(self) -> None:
        super().clean()
        if self.produto.requer_cozinha_completa and not self.unidade.possui_cozinha_completa():
            raise ValidationError(
                {"produto": "Este produto exige cozinha completa e a unidade é de formato reduzido."}
            )
