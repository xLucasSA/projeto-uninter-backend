from django.apps.registry import Apps
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor

# A API mapeia estes nomes para os perfis do token (guideline 05): Atendente→ATENDENTE etc.
GRUPOS = ["Atendente", "Cozinha", "Estoquista", "Gerente", "Matriz"]


def criar_grupos(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    Group = apps.get_model("auth", "Group")
    for nome in GRUPOS:
        Group.objects.get_or_create(name=nome)


def remover_grupos(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name__in=GRUPOS).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("contas", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(criar_grupos, remover_grupos),
    ]
