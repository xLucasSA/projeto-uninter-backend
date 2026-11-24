from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql="GRANT SELECT ON catalogo.outbox_eventos TO debezium;",
            reverse_sql="REVOKE SELECT ON catalogo.outbox_eventos FROM debezium;",
        ),
    ]
