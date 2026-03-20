from django.core.management.base import BaseCommand
from core.models import Holiday
from datetime import date
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Popula o sistema com os feriados nacionais brasileiros'

    def handle(self, *args, **options):
        # Lista de feriados nacionais brasileiros (fixos)
        # Formato: (Dia, Mês, Nome)
        # Nota: Carnaval e Sexta-feira Santa variam, mas o usuário pode cadastrar 
        # manualmente ou podemos adicionar lógica para anos específicos.
        # Por enquanto, focaremos nos fixos e alguns móveis de 2024/2025.
        
        feriados_fixos = [
            (1, 1, "Confraternização Universal"),
            (21, 4, "Tiradentes"),
            (1, 5, "Dia do Trabalhador"),
            (7, 9, "Independência do Brasil"),
            (12, 10, "Nossa Senhora Aparecida"),
            (2, 11, "Finados"),
            (15, 11, "Proclamação da República"),
            (20, 11, "Dia da Consciência Negra"),
            (25, 12, "Natal"),
        ]

        # Feriados Móveis 2024 (Exemplo)
        feriados_2024 = [
            (date(2024, 2, 13), "Carnaval"),
            (date(2024, 3, 29), "Sexta-feira Santa"),
            (date(2024, 5, 30), "Corpus Christi"),
        ]

        # Feriados Móveis 2025
        feriados_2025 = [
            (date(2025, 3, 4), "Carnaval"),
            (date(2025, 4, 18), "Sexta-feira Santa"),
            (date(2025, 6, 19), "Corpus Christi"),
        ]

        count = 0

        # Adicionar fixos
        hoje = date.today()
        for dia, mes, nome in feriados_fixos:
            data_ref = date(hoje.year, mes, dia)
            obj, created = Holiday.objects.get_or_create(
                name=nome,
                date=data_ref,
                defaults={'repeats_annually': True}
            )
            if created:
                count += 1

        # Adicionar móveis (não repetem anualmente no mesmo dia)
        for data_ref, nome in feriados_2024 + feriados_2025:
            obj, created = Holiday.objects.get_or_create(
                name=nome,
                date=data_ref,
                defaults={'repeats_annually': False}
            )
            if created:
                count += 1

        self.stdout.write(self.style.SUCCESS(f'{count} feriados criados com sucesso.'))
