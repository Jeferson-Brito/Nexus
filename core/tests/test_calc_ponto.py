"""
Testes unitários para as funções puras de cálculo de ponto.
Estas funções não dependem de banco de dados (zero fixtures necessárias).

Execução:
    python manage.py test core.tests.test_calc_ponto -v 2
"""
from django.test import TestCase
from core.api.rh import (
    time_to_min,
    min_to_str,
    get_intersection,
    get_interval_intersections,
    split_night_shift,
    detectar_inconsistencias,
)


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers: time_to_min / min_to_str
# ─────────────────────────────────────────────────────────────────────────────

class TimeToMinTests(TestCase):
    """Testa a conversão de horário (string/time) para minutos desde meia-noite."""

    def test_string_hhmm(self):
        self.assertEqual(time_to_min("08:00"), 480)

    def test_string_zeros(self):
        self.assertEqual(time_to_min("00:00"), 0)

    def test_string_meia_noite_passada(self):
        self.assertEqual(time_to_min("23:59"), 1439)

    def test_string_vazia(self):
        self.assertEqual(time_to_min(""), 0)

    def test_none(self):
        self.assertEqual(time_to_min(None), 0)

    def test_objeto_time(self):
        from datetime import time
        self.assertEqual(time_to_min(time(9, 30)), 570)

    def test_string_invalida(self):
        # Deve retornar 0 sem explodir
        self.assertEqual(time_to_min("invalido"), 0)


class MinToStrTests(TestCase):
    """Testa a formatação de minutos para string HH:MM."""

    def test_480_minutos(self):
        self.assertEqual(min_to_str(480), "08:00")

    def test_90_minutos(self):
        self.assertEqual(min_to_str(90), "01:30")

    def test_zero_retorna_vazio(self):
        # Convenção: 0 min = sem valor = string vazia
        self.assertEqual(min_to_str(0), "")

    def test_negativo_retorna_vazio(self):
        self.assertEqual(min_to_str(-10), "")

    def test_1_minuto(self):
        self.assertEqual(min_to_str(1), "00:01")

    def test_valores_cheios(self):
        self.assertEqual(min_to_str(60), "01:00")
        self.assertEqual(min_to_str(120), "02:00")


# ─────────────────────────────────────────────────────────────────────────────
#  Interseção de intervalos
# ─────────────────────────────────────────────────────────────────────────────

class GetIntersectionTests(TestCase):
    """Testa a interseção entre dois intervalos simples em minutos."""

    def test_sobreposicao_parcial(self):
        # [480, 720] ∩ [600, 780] = [600, 720] = 120 min
        self.assertEqual(get_intersection(480, 720, 600, 780), 120)

    def test_sem_sobreposicao(self):
        # [480, 540] ∩ [600, 660] = 0
        self.assertEqual(get_intersection(480, 540, 600, 660), 0)

    def test_contido(self):
        # [480, 1020] ∩ [540, 720] = [540, 720] = 180 min
        self.assertEqual(get_intersection(480, 1020, 540, 720), 180)

    def test_identico(self):
        self.assertEqual(get_intersection(480, 720, 480, 720), 240)

    def test_adjacente_sem_sobreposicao(self):
        # [480, 600] ∩ [600, 720] = 0 (extremos tocam mas não sobrepõem)
        self.assertEqual(get_intersection(480, 600, 600, 720), 0)


class GetIntervalIntersectionsTests(TestCase):
    """Testa a soma de interseções de listas de intervalos (usado em horas normais)."""

    def test_dois_periodos_vs_dois_periodos(self):
        # Trabalhado: 08:00-12:00, 13:00-17:00 (480-720, 780-1020)
        # Previsto:   08:00-12:00, 13:00-17:00 (mesmo)
        # Interseção = 240 + 240 = 480 min (8h)
        worked = [(480, 720), (780, 1020)]
        planned = [(480, 720), (780, 1020)]
        self.assertEqual(get_interval_intersections(worked, planned), 480)

    def test_trabalhado_parcialmente(self):
        # Trabalhou apenas 09:00-12:00 (metade do previsto 08:00-12:00)
        worked = [(540, 720)]
        planned = [(480, 720)]
        self.assertEqual(get_interval_intersections(worked, planned), 180)

    def test_lista_vazia(self):
        self.assertEqual(get_interval_intersections([], [(480, 720)]), 0)
        self.assertEqual(get_interval_intersections([(480, 720)], []), 0)
        self.assertEqual(get_interval_intersections([], []), 0)


# ─────────────────────────────────────────────────────────────────────────────
#  Noturno: split_night_shift
# ─────────────────────────────────────────────────────────────────────────────

class SplitNightShiftTests(TestCase):
    """Testa a divisão de intervalos em diurno/noturno (padrão: 22h-05h = 1320-300)."""

    def test_totalmente_diurno(self):
        # 08:00 (480) até 17:00 (1020) — completamente diurno
        diurno, noturno = split_night_shift(480, 1020)
        self.assertEqual(noturno, 0)
        self.assertEqual(diurno, 540)

    def test_totalmente_noturno(self):
        # 22:00 (1320) até 23:00 (1380) — completamente noturno
        diurno, noturno = split_night_shift(1320, 1380)
        self.assertEqual(noturno, 60)
        self.assertEqual(diurno, 0)

    def test_atravessa_meia_noite(self):
        # 22:00 (1320) até 02:00 (120) — 4h noturnas
        diurno, noturno = split_night_shift(1320, 120)
        self.assertEqual(noturno, 180 + 120)  # 3h após 22h + 2h antes de 05h
        self.assertEqual(diurno, 0)

    def test_parcialmente_noturno(self):
        # 20:00 (1200) até 23:00 (1380) — 2h diurnas + 1h noturna
        diurno, noturno = split_night_shift(1200, 1380)
        self.assertEqual(noturno, 60)  # 22:00 → 23:00
        self.assertEqual(diurno, 120)  # 20:00 → 22:00

    def test_inicio_cinco_da_manha(self):
        # 05:00 (300) até 12:00 (720) — completamente diurno após às 5h
        diurno, noturno = split_night_shift(300, 720)
        self.assertEqual(noturno, 0)
        self.assertEqual(diurno, 420)


# ─────────────────────────────────────────────────────────────────────────────
#  Detecção de Inconsistências
# ─────────────────────────────────────────────────────────────────────────────

class MockInconsistenciaConfig:
    """
    Substituto simples para TipoInconsistencia sem precisar de banco de dados.
    Permite testar detectar_inconsistencias() de forma isolada.
    """
    def __init__(self, id, nome, campo, tolerancia, prioridade=5,
                 icone="bi-exclamation-circle", cor="#dc3545"):
        self.id = id
        self.nome = nome
        self.campo = campo
        self.tolerancia = tolerancia
        self.prioridade = prioridade
        self.icone = icone
        self.cor = cor


def _dia_base(**kwargs):
    """Retorna um dicionário de dia-apuração com valores padrão (dia normal sem incidências)."""
    defaults = {
        'horas_atraso': '00:00',
        'extra_total': '00:00',
        'dia_falta': 0,
        'status': 'OK',
        'banco_minutos': 0,
        'extra_intervalo': '00:00',
        'interjornada': '00:00',
        'pulou_almoco': 0,
    }
    defaults.update(kwargs)
    return defaults


class DetectarInconsistenciasTests(TestCase):
    """
    Testa a função detectar_inconsistencias() — o motor central de alertas.
    Usa o mock ao invés do banco de dados.
    """

    # ── Tipo: Atraso ──────────────────────────────────────────────────────────

    def test_detecta_atraso_acima_tolerancia(self):
        config = [MockInconsistenciaConfig(1, 'Atraso', 'atraso', tolerancia=10)]
        dia = _dia_base(horas_atraso='00:15')  # 15 min de atraso
        resultado = detectar_inconsistencias(dia, config)
        self.assertIsNotNone(resultado)
        self.assertEqual(resultado['nome'], 'Atraso')

    def test_nao_detecta_atraso_dentro_tolerancia(self):
        config = [MockInconsistenciaConfig(1, 'Atraso', 'atraso', tolerancia=10)]
        dia = _dia_base(horas_atraso='00:05')  # 5 min < tolerância de 10
        resultado = detectar_inconsistencias(dia, config)
        self.assertIsNone(resultado)

    def test_nao_detecta_atraso_zero(self):
        config = [MockInconsistenciaConfig(1, 'Atraso', 'atraso', tolerancia=1)]
        dia = _dia_base(horas_atraso='00:00')
        resultado = detectar_inconsistencias(dia, config)
        self.assertIsNone(resultado)

    def test_detecta_atraso_exatamente_na_tolerancia(self):
        # Tolerância = 10 min; atraso = 10 min → DEVE disparar (>=)
        config = [MockInconsistenciaConfig(1, 'Atraso', 'atraso', tolerancia=10)]
        dia = _dia_base(horas_atraso='00:10')
        resultado = detectar_inconsistencias(dia, config)
        self.assertIsNotNone(resultado)

    # ── Tipo: Horas Extras ────────────────────────────────────────────────────

    def test_detecta_hora_extra(self):
        config = [MockInconsistenciaConfig(2, 'Hora Extra', 'extra_total', tolerancia=30)]
        dia = _dia_base(extra_total='01:00')  # 60 min > 30
        resultado = detectar_inconsistencias(dia, config)
        self.assertIsNotNone(resultado)
        self.assertEqual(resultado['nome'], 'Hora Extra')

    def test_nao_detecta_hora_extra_zerada(self):
        config = [MockInconsistenciaConfig(2, 'Hora Extra', 'extra_total', tolerancia=30)]
        dia = _dia_base(extra_total='00:00')
        resultado = detectar_inconsistencias(dia, config)
        self.assertIsNone(resultado)

    # ── Tipo: Marcações Ímpares (pulou almoço) ────────────────────────────────

    def test_detecta_marcacoes_impares(self):
        config = [MockInconsistenciaConfig(3, 'Sem Almoço', 'marcacoes_impares', tolerancia=1)]
        dia = _dia_base(pulou_almoco=1)
        resultado = detectar_inconsistencias(dia, config)
        self.assertIsNotNone(resultado)

    def test_nao_detecta_marcacoes_impares_quando_zero(self):
        config = [MockInconsistenciaConfig(3, 'Sem Almoço', 'marcacoes_impares', tolerancia=1)]
        dia = _dia_base(pulou_almoco=0)
        resultado = detectar_inconsistencias(dia, config)
        self.assertIsNone(resultado)

    # ── Tipo: Banco Positivo ──────────────────────────────────────────────────

    def test_detecta_banco_positivo(self):
        config = [MockInconsistenciaConfig(4, 'Banco +', 'banco_pos', tolerancia=60)]
        dia = _dia_base(banco_minutos=90)  # 90 min de saldo positivo
        resultado = detectar_inconsistencias(dia, config)
        self.assertIsNotNone(resultado)

    def test_nao_detecta_banco_positivo_quando_negativo(self):
        config = [MockInconsistenciaConfig(4, 'Banco +', 'banco_pos', tolerancia=60)]
        dia = _dia_base(banco_minutos=-90)
        resultado = detectar_inconsistencias(dia, config)
        self.assertIsNone(resultado)

    # ── Tipo: Banco Negativo ──────────────────────────────────────────────────

    def test_detecta_banco_negativo(self):
        config = [MockInconsistenciaConfig(5, 'Banco -', 'banco_neg', tolerancia=60)]
        dia = _dia_base(banco_minutos=-90)
        resultado = detectar_inconsistencias(dia, config)
        self.assertIsNotNone(resultado)

    def test_nao_detecta_banco_negativo_quando_positivo(self):
        config = [MockInconsistenciaConfig(5, 'Banco -', 'banco_neg', tolerancia=60)]
        dia = _dia_base(banco_minutos=90)
        resultado = detectar_inconsistencias(dia, config)
        self.assertIsNone(resultado)

    # ── Tipo: Interjornada ────────────────────────────────────────────────────

    def test_detecta_interjornada(self):
        config = [MockInconsistenciaConfig(6, 'Interjornada', 'interjornada', tolerancia=1)]
        dia = _dia_base(interjornada='00:30')
        resultado = detectar_inconsistencias(dia, config)
        self.assertIsNotNone(resultado)

    # ── Prioridade ────────────────────────────────────────────────────────────

    def test_retorna_maior_prioridade_primeiro(self):
        """Quando dois tipos disparam, retorna o de menor número de prioridade (= mais urgente)."""
        configs = [
            MockInconsistenciaConfig(1, 'Crítico', 'atraso', tolerancia=1, prioridade=1),
            MockInconsistenciaConfig(2, 'Aviso', 'extra_total', tolerancia=1, prioridade=5),
        ]
        dia = _dia_base(horas_atraso='01:00', extra_total='02:00')
        # A lista já deve estar ordenada por prioridade (como o queryset faz)
        resultado = detectar_inconsistencias(dia, configs)
        self.assertEqual(resultado['nome'], 'Crítico')

    def test_lista_configs_vazia_retorna_none(self):
        dia = _dia_base(horas_atraso='01:00')
        resultado = detectar_inconsistencias(dia, [])
        self.assertIsNone(resultado)

    def test_dia_sem_nenhuma_incidencia_retorna_none(self):
        configs = [
            MockInconsistenciaConfig(1, 'Atraso', 'atraso', tolerancia=5),
            MockInconsistenciaConfig(2, 'Extra', 'extra_total', tolerancia=30),
        ]
        dia = _dia_base()  # tudo zerado
        resultado = detectar_inconsistencias(dia, configs)
        self.assertIsNone(resultado)

    def test_retorna_estrutura_correta(self):
        """Garante que o dicionário retornado tem as chaves esperadas pelo frontend."""
        configs = [MockInconsistenciaConfig(42, 'Atraso Grave', 'atraso', tolerancia=1,
                                            icone='bi-alarm', cor='#ff0000')]
        dia = _dia_base(horas_atraso='00:30')
        resultado = detectar_inconsistencias(dia, configs)
        self.assertIsNotNone(resultado)
        self.assertIn('id', resultado)
        self.assertIn('nome', resultado)
        self.assertIn('icone', resultado)
        self.assertIn('cor', resultado)
        self.assertIn('prioridade', resultado)
        self.assertEqual(resultado['id'], 42)
        self.assertEqual(resultado['icone'], 'bi-alarm')
        self.assertEqual(resultado['cor'], '#ff0000')
