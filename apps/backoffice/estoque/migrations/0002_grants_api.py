from django.db import migrations

# Least privilege do api_app no schema catalogo (guideline 02). O api_app não tem nenhum outro acesso aqui.
GRANTS = """
GRANT SELECT ON
    catalogo.unidades,
    catalogo.produtos,
    catalogo.cardapio_unidade,
    catalogo.funcionarios,
    catalogo.funcionarios_unidades,
    catalogo.funcionarios_groups,
    catalogo.auth_group,
    catalogo.dispositivos
TO api_app;
GRANT REFERENCES ON catalogo.unidades, catalogo.produtos TO api_app;
GRANT SELECT ON catalogo.estoque TO api_app;
GRANT UPDATE (quantidade, atualizado_em) ON catalogo.estoque TO api_app;
GRANT INSERT ON catalogo.movimentacao_estoque TO api_app;
GRANT UPDATE (ultimo_uso_em) ON catalogo.dispositivos TO api_app;
"""

REVOKES = """
REVOKE ALL ON
    catalogo.unidades,
    catalogo.produtos,
    catalogo.cardapio_unidade,
    catalogo.funcionarios,
    catalogo.funcionarios_unidades,
    catalogo.funcionarios_groups,
    catalogo.auth_group,
    catalogo.dispositivos,
    catalogo.estoque,
    catalogo.movimentacao_estoque
FROM api_app;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("catalogo", "0001_initial"),
        ("contas", "0001_initial"),
        ("estoque", "0001_initial"),
        ("unidades", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(sql=GRANTS, reverse_sql=REVOKES),
    ]
