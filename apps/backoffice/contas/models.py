from typing import Any

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

from core.escopo import EscopoUnidade


class FuncionarioManager(BaseUserManager["Funcionario"]):
    use_in_migrations = True

    @classmethod
    def normalize_email(cls, email: str | None) -> str:
        return (email or "").strip().lower()

    def create_user(self, email: str, nome: str, password: str | None = None, **campos: Any) -> "Funcionario":
        funcionario = self.model(email=self.normalize_email(email), nome=nome, **campos)
        funcionario.set_password(password)
        funcionario.save(using=self._db)
        return funcionario

    def create_superuser(self, email: str, nome: str, password: str, **campos: Any) -> "Funcionario":
        campos.update(is_staff=True, is_superuser=True)
        return self.create_user(email, nome, password, **campos)


class Funcionario(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    nome = models.CharField(max_length=120)
    unidades = models.ManyToManyField("unidades.Unidade", related_name="funcionarios", blank=True)
    is_active = models.BooleanField("ativo", default=True)
    is_staff = models.BooleanField("acessa o admin", default=False)
    date_joined = models.DateTimeField("cadastrado em", default=timezone.now)

    # Sem escopo de propósito: autenticação e sessão do Django usam o manager padrão
    # (`get_by_natural_key`, `get_user`), e um manager fail-closed impediria qualquer login.
    objects = FuncionarioManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["nome"]

    class Meta:
        db_table = "funcionarios"
        verbose_name = "funcionário"
        verbose_name_plural = "funcionários"
        ordering = ["email"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(email=Lower("email")), name="funcionarios_email_minusculo"
            ),
        ]

    def __str__(self) -> str:
        return self.email

    def clean(self) -> None:
        super().clean()
        self.email = FuncionarioManager.normalize_email(self.email)

    def escopo_unidade(self) -> EscopoUnidade:
        if self.is_superuser:
            return EscopoUnidade.todas()
        # Lê a tabela de ligação direto: o manager de Unidade é fail-closed e ainda não há escopo aqui.
        unidade_ids = Funcionario.unidades.through.objects.filter(funcionario_id=self.pk).values_list(
            "unidade_id", flat=True
        )
        return EscopoUnidade.das_unidades(unidade_ids)
