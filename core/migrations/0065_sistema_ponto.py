# Generated manually for Sistema de Ponto

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0064_alter_analystassignment_active_and_more'),
    ]

    operations = [
        # Adicionar role 'tablet' ao campo role do User
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[
                    ('analista', 'Analista'),
                    ('gestor', 'Gestor'),
                    ('administrador', 'Administrador'),
                    ('tablet', 'Tablet (Ponto)'),
                ],
                default='analista',
                max_length=20,
            ),
        ),

        # Model ConfiguracaoPonto
        migrations.CreateModel(
            name='ConfiguracaoPonto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('horario_entrada', models.TimeField(default='08:00', verbose_name='Horário de Entrada')),
                ('horario_saida', models.TimeField(default='17:00', verbose_name='Horário de Saída')),
                ('tolerancia_atraso', models.IntegerField(default=10, verbose_name='Tolerância de Atraso (minutos)')),
                ('intervalo_almoco_min', models.IntegerField(default=60, verbose_name='Intervalo Mínimo de Almoço (minutos)')),
                ('carga_horaria_diaria', models.IntegerField(
                    default=480,
                    help_text='Em minutos. Ex: 8h = 480',
                    verbose_name='Carga Horária Diária (minutos)'
                )),
                ('ativo', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('department', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='configuracao_ponto',
                    to='core.department',
                    verbose_name='Departamento'
                )),
            ],
            options={
                'verbose_name': 'Configuração de Ponto',
                'verbose_name_plural': 'Configurações de Ponto',
            },
        ),

        # Model RegistroPonto
        migrations.CreateModel(
            name='RegistroPonto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(
                    choices=[
                        ('entrada', 'Entrada'),
                        ('saida_almoco', 'Saída para Almoço'),
                        ('retorno_almoco', 'Retorno do Almoço'),
                        ('saida', 'Saída Final'),
                    ],
                    max_length=20,
                    verbose_name='Tipo de Registro'
                )),
                ('data', models.DateField(verbose_name='Data')),
                ('hora', models.TimeField(verbose_name='Hora')),
                ('foto', models.ImageField(blank=True, null=True, upload_to='ponto_fotos/%Y/%m/', verbose_name='Foto do Registro')),
                ('origem', models.CharField(
                    choices=[
                        ('tablet', 'Tablet'),
                        ('web', 'Web (Admin)'),
                        ('admin', 'Lançamento Manual'),
                    ],
                    default='tablet',
                    max_length=10,
                    verbose_name='Origem'
                )),
                ('observacao', models.TextField(blank=True, verbose_name='Observação')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('colaborador', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='registros_ponto',
                    to='core.colaborador',
                    verbose_name='Colaborador'
                )),
                ('registrado_por', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='pontos_registrados',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Registrado por'
                )),
            ],
            options={
                'verbose_name': 'Registro de Ponto',
                'verbose_name_plural': 'Registros de Ponto',
                'ordering': ['-data', '-hora'],
            },
        ),

        # Indexes para RegistroPonto
        migrations.AddIndex(
            model_name='registroponto',
            index=models.Index(fields=['colaborador', 'data'], name='ponto_colab_data_idx'),
        ),
        migrations.AddIndex(
            model_name='registroponto',
            index=models.Index(fields=['data', 'tipo'], name='ponto_data_tipo_idx'),
        ),

        # Model BancoHoras
        migrations.CreateModel(
            name='BancoHoras',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('saldo_minutos', models.IntegerField(
                    default=0,
                    help_text='Positivo = horas extras, Negativo = horas devidas',
                    verbose_name='Saldo (minutos)'
                )),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('colaborador', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='banco_horas',
                    to='core.colaborador',
                    verbose_name='Colaborador'
                )),
            ],
            options={
                'verbose_name': 'Banco de Horas',
                'verbose_name_plural': 'Banco de Horas',
            },
        ),
    ]
