"""
Migration gerada manualmente.
Adiciona:
- Model BaseAuditoria (base de conhecimento para a IA de auditoria)
- Campo gerado_por_ia em AuditoriaAtendimento
- Campo observacao_ia em AuditoriaAtendimento
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0095_nexusiabase'),
    ]

    operations = [
        # Novo model BaseAuditoria
        migrations.CreateModel(
            name='BaseAuditoria',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=200, verbose_name='Título')),
                ('conteudo', models.TextField(verbose_name='Conteúdo')),
                ('categoria', models.CharField(
                    choices=[
                        ('apresentacao', 'Critério 1 — Apresentação'),
                        ('historico', 'Critério 2 — Análise de Histórico'),
                        ('entendimento', 'Critério 3 — Entendimento da Solicitação'),
                        ('informacao', 'Critério 4 — Clareza da Informação'),
                        ('acordo_espera', 'Critério 5 — Acordo de Espera'),
                        ('respeito', 'Critério 6 — Respeito'),
                        ('portugues', 'Critério 7 — Língua Portuguesa'),
                        ('finalizacao', 'Critério 8 — Finalização do Atendimento'),
                        ('procedimento', 'Critério 9 — Procedimento Correto'),
                        ('geral', 'Regras Gerais de Atendimento'),
                    ],
                    default='geral',
                    max_length=30,
                    verbose_name='Categoria / Critério',
                )),
                ('ativo', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('department', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='base_auditoria_ia',
                    to='core.department',
                )),
            ],
            options={
                'verbose_name': 'Base de Auditoria IA',
                'verbose_name_plural': 'Base de Auditoria IA',
                'ordering': ['categoria', 'titulo'],
            },
        ),
        # Novo campo: gerado_por_ia em AuditoriaAtendimento
        migrations.AddField(
            model_name='auditoriaatendimento',
            name='gerado_por_ia',
            field=models.BooleanField(
                default=False,
                help_text='Indica se esta auditoria foi gerada automaticamente pelo Nexus IA Auditor',
                verbose_name='Gerado por IA',
            ),
        ),
        # Novo campo: observacao_ia em AuditoriaAtendimento
        migrations.AddField(
            model_name='auditoriaatendimento',
            name='observacao_ia',
            field=models.TextField(
                blank=True,
                help_text='JSON com justificativas da IA para cada critério avaliado',
                verbose_name='Justificativas da IA',
            ),
        ),
    ]
