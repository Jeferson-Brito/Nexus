from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0093_trocaferiado_repete_anualmente'),
    ]

    operations = [
        migrations.AddField(
            model_name='complaint',
            name='ia_urgencia',
            field=models.CharField(
                blank=True,
                choices=[('baixa', 'Baixa'), ('media', 'Média'), ('alta', 'Alta'), ('critica', 'Crítica')],
                max_length=20,
                null=True,
                verbose_name='Urgência (IA)',
            ),
        ),
        migrations.AddField(
            model_name='complaint',
            name='ia_sentimento',
            field=models.CharField(
                blank=True,
                choices=[
                    ('satisfeito', 'Satisfeito'),
                    ('neutro', 'Neutro'),
                    ('frustrado', 'Frustrado'),
                    ('muito_irritado', 'Muito Irritado'),
                ],
                max_length=30,
                null=True,
                verbose_name='Sentimento (IA)',
            ),
        ),
        migrations.AddField(
            model_name='complaint',
            name='ia_classificado_em',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Classificado por IA em'),
        ),
    ]
