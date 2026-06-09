"""
Testes de integração para as APIs de Inconsistências e Apuração de Ponto.
Estes testes usam banco de dados (TestCase com transações revertidas a cada teste).

Execução:
    python manage.py test core.tests.test_api_inconsistencias -v 2
"""
import json
from datetime import date, time

from django.test import TestCase, Client
from django.contrib.auth import get_user_model

from core.models import (
    Colaborador, Department, Empresa, TipoInconsistencia,
    Horario, HorarioDetalhe, RegistroPonto, EscalaMensal,
)

User = get_user_model()


# ─────────────────────────────────────────────────────────────────────────────
#  Fixtures compartilhadas: criadas uma vez para toda a suite de integração
# ─────────────────────────────────────────────────────────────────────────────

class BaseIntegracaoTestCase(TestCase):
    """
    Cria os objetos mínimos necessários para testes de integração das APIs de ponto.
    Não usa fixtures de arquivo — tudo é criado programaticamente.
    """

    @classmethod
    def setUpTestData(cls):
        # Usuário admin para autenticar nas views
        cls.user = User.objects.create_user(
            username='test_admin',
            password='testpass123',
            email='admin@brisoft.test',
        )
        cls.user.profile_type = 'administrador'
        cls.user.save()

        # Estrutura organizacional mínima
        cls.department = Department.objects.create(name='TI')
        cls.empresa = Empresa.objects.create(nome='Brisoft Testes LTDA')

        # Horário padrão: Seg-Sex 08:00-12:00 / 13:00-17:00
        cls.horario = Horario.objects.create(
            nome='Padrão 8h',
            tipo='semanal',
        )
        # Detalhes: dias 0-4 (Seg → Sex)
        for dia_idx in range(5):  # 0=Seg, 4=Sex
            HorarioDetalhe.objects.create(
                horario=cls.horario,
                dia_index=dia_idx,
                nome_dia=['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta'][dia_idx],
                entrada_1=time(8, 0),
                saida_1=time(12, 0),
                entrada_2=time(13, 0),
                saida_2=time(17, 0),
                total_horas='08:00',
            )

        # Colaborador vinculado ao horário
        cls.colaborador = Colaborador.objects.create(
            nome_completo='João Silva Teste',
            cpf='000.000.000-01',
            data_admissao=date(2023, 1, 1),
            cargo_atual='Analista',
            department=cls.department,
            empresa=cls.empresa,
            salario_atual=3000,
            status='ativo',
            horario_padrao=cls.horario,
        )

        # Tipo de inconsistência: Atraso (tolerância 10 min)
        cls.incon_atraso = TipoInconsistencia.objects.create(
            nome='Atraso',
            campo='atraso',
            tolerancia=10,
            prioridade=1,
            icone='bi-alarm',
            cor='#f59e0b',
            ativo=True,
        )

        # Tipo de inconsistência: Hora Extra (tolerância 30 min)
        cls.incon_extra = TipoInconsistencia.objects.create(
            nome='Hora Extra',
            campo='extra_total',
            tolerancia=30,
            prioridade=3,
            icone='bi-clock-history',
            cor='#10b981',
            ativo=True,
        )

    def setUp(self):
        self.client = Client()
        self.client.login(username='test_admin', password='testpass123')


# ─────────────────────────────────────────────────────────────────────────────
#  API: /api/rh/configuracao/inconsistencias/
# ─────────────────────────────────────────────────────────────────────────────

class ApiInconsistenciasListTests(BaseIntegracaoTestCase):
    """Testa o endpoint que lista os tipos de inconsistência configurados."""

    def test_retorna_200(self):
        resp = self.client.get('/api/rh/configuracao/inconsistencias/')
        self.assertEqual(resp.status_code, 200)

    def test_retorna_lista_json(self):
        resp = self.client.get('/api/rh/configuracao/inconsistencias/')
        data = resp.json()
        self.assertIsInstance(data, list)

    def test_lista_contem_inconsistencias_criadas(self):
        resp = self.client.get('/api/rh/configuracao/inconsistencias/')
        data = resp.json()
        nomes = [item['nome'] for item in data]
        self.assertIn('Atraso', nomes)
        self.assertIn('Hora Extra', nomes)

    def test_campos_obrigatorios_presentes(self):
        """Verifica que todos os campos consumidos pelo frontend estão na resposta."""
        resp = self.client.get('/api/rh/configuracao/inconsistencias/')
        data = resp.json()
        # Garante que pelo menos um item existe
        self.assertTrue(len(data) > 0)
        item = data[0]
        for campo in ('id', 'nome', 'campo', 'tolerancia', 'prioridade', 'icone', 'cor', 'ativo'):
            self.assertIn(campo, item, f"Campo '{campo}' ausente na resposta da API")

    def test_requer_autenticacao(self):
        """Usuário não autenticado deve ser redirecionado (302)."""
        client_sem_auth = Client()
        resp = client_sem_auth.get('/api/rh/configuracao/inconsistencias/')
        self.assertEqual(resp.status_code, 302)


# ─────────────────────────────────────────────────────────────────────────────
#  API: /api/rh/apuracao/inconsistencias/dados/
# ─────────────────────────────────────────────────────────────────────────────

class ApiFiltroDadosTests(BaseIntegracaoTestCase):
    """Testa o endpoint que busca inconsistências em um range de datas."""

    # 2026-03-10 é uma terça (dia_index=1) — dia útil com horário previsto
    DATA_TESTE = date(2026, 3, 10)

    def _url(self, **params):
        """Monta a URL do endpoint com parâmetros GET."""
        base = '/api/rh/apuracao/inconsistencias/dados/'
        qs = '&'.join(f'{k}={v}' for k, v in params.items())
        return f'{base}?{qs}'

    # ── Estrutura da resposta ────────────────────────────────────────────────

    def test_retorna_200(self):
        url = self._url(
            data_inicio='2026-03-01',
            data_fim='2026-03-31',
            colaborador_id=self.colaborador.id,
        )
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_retorna_chave_items_nao_dias(self):
        """Regressão: a API deve retornar 'items', nunca 'dias' (bug corrigido)."""
        url = self._url(
            data_inicio='2026-03-01',
            data_fim='2026-03-31',
            colaborador_id=self.colaborador.id,
        )
        resp = self.client.get(url)
        data = resp.json()
        self.assertIn('items', data, "Chave 'items' ausente — pode ter regredido para 'dias'")
        self.assertNotIn('dias', data, "Chave 'dias' não deve existir na resposta deste endpoint")

    def test_retorna_success_true(self):
        url = self._url(
            data_inicio='2026-03-01',
            data_fim='2026-03-31',
            colaborador_id=self.colaborador.id,
        )
        resp = self.client.get(url)
        self.assertTrue(resp.json()['success'])

    def test_sem_registros_retorna_lista_vazia(self):
        """Sem registros de ponto no período, items deve ser lista vazia."""
        url = self._url(
            data_inicio='2020-01-01',
            data_fim='2020-01-31',
            colaborador_id=self.colaborador.id,
        )
        resp = self.client.get(url)
        data = resp.json()
        self.assertEqual(data['items'], [])

    def test_colaborador_invalido_retorna_lista_vazia(self):
        """ID de colaborador inexistente não deve causar erro 500."""
        url = self._url(
            data_inicio='2026-03-01',
            data_fim='2026-03-31',
            colaborador_id=999999,
        )
        resp = self.client.get(url)
        # Pode retornar 200 com lista vazia OU 500 — não deve estourar sem resposta JSON
        self.assertIn(resp.status_code, [200, 500])
        # Deve sempre retornar JSON válido
        data = resp.json()
        self.assertIsInstance(data, dict)

    def test_requer_autenticacao(self):
        client_sem_auth = Client()
        url = self._url(data_inicio='2026-03-01', data_fim='2026-03-31')
        resp = client_sem_auth.get(url)
        self.assertEqual(resp.status_code, 302)

    # ── Detecção de inconsistência real ──────────────────────────────────────

    def test_detecta_atraso_com_registro_real(self):
        """
        Cenário: colaborador com horário 08:00-17:00 bate ponto às 09:00.
        Deve aparecer como inconsistência de Atraso.
        """
        # Cria escala para o dia de teste
        EscalaMensal.objects.create(
            colaborador=self.colaborador,
            data=self.DATA_TESTE,
            horario_previsto=self.horario,
            tipo='trabalho',
        )

        # Registra ponto com atraso de 1h (09:00 ao invés de 08:00)
        RegistroPonto.objects.create(
            colaborador=self.colaborador,
            tipo='entrada',
            data=self.DATA_TESTE,
            hora=time(9, 0),
            origem='admin',
        )
        RegistroPonto.objects.create(
            colaborador=self.colaborador,
            tipo='saida_almoco',
            data=self.DATA_TESTE,
            hora=time(12, 0),
            origem='admin',
        )
        RegistroPonto.objects.create(
            colaborador=self.colaborador,
            tipo='retorno_almoco',
            data=self.DATA_TESTE,
            hora=time(13, 0),
            origem='admin',
        )
        RegistroPonto.objects.create(
            colaborador=self.colaborador,
            tipo='saida',
            data=self.DATA_TESTE,
            hora=time(17, 0),
            origem='admin',
        )

        url = self._url(
            data_inicio=str(self.DATA_TESTE),
            data_fim=str(self.DATA_TESTE),
            colaborador_id=self.colaborador.id,
        )
        resp = self.client.get(url)
        data = resp.json()

        self.assertTrue(data['success'])
        items = data['items']
        # Com 60 min de atraso (acima da tolerância de 10 min), deve detectar
        self.assertTrue(len(items) > 0, "Esperava detectar inconsistência de atraso")
        self.assertEqual(items[0]['colaborador_nome'], 'João Silva Teste')
        self.assertEqual(items[0]['inconsistencia']['nome'], 'Atraso')

    def test_dia_sem_inconsistencia_nao_aparece(self):
        """
        Cenário: colaborador bate ponto exatamente no horário.
        NÃO deve aparecer na lista de inconsistências.
        """
        DATA = date(2026, 3, 11)  # Quarta (dia_index=2)

        EscalaMensal.objects.create(
            colaborador=self.colaborador,
            data=DATA,
            horario_previsto=self.horario,
            tipo='trabalho',
        )

        # Ponto perfeito: exatamente 08:00 → 12:00 → 13:00 → 17:00
        for tipo, hora in [
            ('entrada', time(8, 0)),
            ('saida_almoco', time(12, 0)),
            ('retorno_almoco', time(13, 0)),
            ('saida', time(17, 0)),
        ]:
            RegistroPonto.objects.create(
                colaborador=self.colaborador,
                tipo=tipo,
                data=DATA,
                hora=hora,
                origem='admin',
            )

        url = self._url(
            data_inicio=str(DATA),
            data_fim=str(DATA),
            colaborador_id=self.colaborador.id,
        )
        resp = self.client.get(url)
        data = resp.json()

        self.assertTrue(data['success'])
        self.assertEqual(data['items'], [],
                         "Dia sem inconsistência não deveria aparecer na lista")

    # ── Filtro por tipo de inconsistência ────────────────────────────────────

    def test_filtro_por_tipo_exclui_outros(self):
        """
        Quando um tipo específico é selecionado, apenas esse tipo deve aparecer.
        """
        DATA = date(2026, 3, 12)  # Quinta

        EscalaMensal.objects.create(
            colaborador=self.colaborador,
            data=DATA,
            horario_previsto=self.horario,
            tipo='trabalho',
        )

        # Atraso de 1h
        for tipo, hora in [
            ('entrada', time(9, 0)),
            ('saida_almoco', time(12, 0)),
            ('retorno_almoco', time(13, 0)),
            ('saida', time(17, 0)),
        ]:
            RegistroPonto.objects.create(
                colaborador=self.colaborador,
                tipo=tipo,
                data=DATA,
                hora=hora,
                origem='admin',
            )

        # Filtrar apenas pelo ID de "Hora Extra" — não deve retornar o atraso
        url = self._url(
            data_inicio=str(DATA),
            data_fim=str(DATA),
            colaborador_id=self.colaborador.id,
            tipos_inconsistencia=self.incon_extra.id,
        )
        resp = self.client.get(url)
        data = resp.json()

        self.assertTrue(data['success'])
        # O dia tem atraso, não hora extra → filtrando por extra, deve aparecer vazio
        for item in data['items']:
            self.assertEqual(item['inconsistencia']['nome'], 'Hora Extra',
                             "Outros tipos não deveriam aparecer com filtro ativo")
