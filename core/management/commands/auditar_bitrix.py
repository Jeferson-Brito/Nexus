"""
Management command para auditoria automática de atendimentos via Nexus IA + Bitrix.

Uso:
    python manage.py auditar_bitrix                 # Audita o dia anterior
    python manage.py auditar_bitrix --data 2026-05-03  # Audita uma data específica
    python manage.py auditar_bitrix --dry-run        # Simula sem salvar
    python manage.py auditar_bitrix --max-por-analista 15  # Limita amostras
"""
import json
import logging
import random
from collections import defaultdict
from datetime import date, datetime

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

logger = logging.getLogger(__name__)

MAX_POR_ANALISTA_DEFAULT = 30


class Command(BaseCommand):
    help = 'Audita automaticamente os atendimentos do dia anterior via Nexus IA + Bitrix API'

    def add_arguments(self, parser):
        parser.add_argument(
            '--data',
            type=str,
            help='Data a auditar no formato YYYY-MM-DD. Padrão: dia anterior.',
            default=None,
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Executa sem salvar auditorias no banco. Apenas loga os resultados.',
        )
        parser.add_argument(
            '--max-por-analista',
            type=int,
            default=MAX_POR_ANALISTA_DEFAULT,
            help=f'Número máximo de chats a auditar por analista. Padrão: {MAX_POR_ANALISTA_DEFAULT}',
        )
        parser.add_argument(
            '--analista-email',
            type=str,
            help='Auditar apenas um analista específico (pelo e-mail).',
            default=None,
        )

    def handle(self, *args, **options):
        from core.models import AuditoriaAtendimento, BaseAuditoria, Department, User
        from core.services import bitrix_service, ia_service

        dry_run = options['dry_run']
        max_por_analista = options['max_por_analista']
        analista_email_filtro = options.get('analista_email')

        # Determinar data alvo
        if options['data']:
            try:
                data_alvo = datetime.strptime(options['data'], '%Y-%m-%d').date()
            except ValueError:
                raise CommandError("Data inválida. Use o formato YYYY-MM-DD.")
        else:
            from datetime import timedelta
            data_alvo = date.today() - timedelta(days=1)

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\n{'=' * 60}\n"
            f"  🤖 Nexus IA Auditor — {data_alvo}\n"
            f"  Modo: {'DRY-RUN (nada será salvo)' if dry_run else 'PRODUÇÃO'}\n"
            f"  Máx por analista: {max_por_analista}\n"
            f"{'=' * 60}\n"
        ))

        # 1. Buscar sessões do dia anterior
        self.stdout.write("📡 Buscando sessões no Contact Center...")
        sessoes = bitrix_service.get_sessoes_dia_anterior(data=data_alvo)

        if not sessoes:
            self.stdout.write(self.style.WARNING("⚠️  Nenhuma sessão encontrada para o período."))
            return

        self.stdout.write(self.style.SUCCESS(f"✅ {len(sessoes)} sessões auditáveis encontradas."))

        # 2. Agrupar sessões por analista
        sessoes_por_analista = defaultdict(list)
        for s in sessoes:
            email_analista = (
                s.get('analyst_email') or
                s.get('analyst', {}).get('email', '') if isinstance(s.get('analyst'), dict)
                else s.get('analyst_name', '')
            )
            sessoes_por_analista[email_analista].append(s)

        # 3. Buscar base de conhecimento de auditoria (agora sem filtro de department)
        base_auditoria_qs = BaseAuditoria.objects.filter(ativo=True).values('titulo', 'conteudo', 'categoria')
        base_auditoria = list(base_auditoria_qs)
        self.stdout.write(f"📚 {len(base_auditoria)} artigos na base de auditoria IA.")

        # 4. Processar cada analista
        total_criadas = 0
        total_erros = 0
        total_puladas = 0

        for email_analista, sessoes_analista in sessoes_por_analista.items():

            # Filtro por analista específico, se informado
            if analista_email_filtro and email_analista.lower() != analista_email_filtro.lower():
                continue

            # Encontrar User no Nexus
            user_nexus = bitrix_service.encontrar_analista_nexus(email_analista)
            if not user_nexus:
                self.stdout.write(self.style.WARNING(
                    f"  ⚠️  Analista não encontrado no Nexus: {email_analista or 'sem e-mail'} "
                    f"({len(sessoes_analista)} sessões ignoradas)"
                ))
                total_puladas += len(sessoes_analista)
                continue

            analista_nome = user_nexus.get_full_name() or user_nexus.username
            department = user_nexus.department

            if not department:
                self.stdout.write(self.style.WARNING(f"  ⚠️  {analista_nome} sem departamento. Pulando."))
                continue

            self.stdout.write(f"\n👤 {analista_nome} ({email_analista}) — {len(sessoes_analista)} sessões")

            # Aplicar amostragem: máx N por analista
            if len(sessoes_analista) > max_por_analista:
                sessoes_amostra = random.sample(sessoes_analista, max_por_analista)
                self.stdout.write(f"   📊 Amostragem: {max_por_analista}/{len(sessoes_analista)} selecionadas aleatoriamente")
            else:
                sessoes_amostra = sessoes_analista

            for sessao in sessoes_amostra:
                session_id = sessao.get('id') or sessao.get('session_id')
                chat_id = sessao.get('chat_id') or sessao.get('bitrix_session_id') or str(session_id)
                tipo_atendimento = sessao.get('_tipo_atendimento', 'cliente')
                nome_fila = sessao.get('_nome_fila', '')

                # Verificar se já existe auditoria para este chat
                if not dry_run and AuditoriaAtendimento.objects.filter(id_conversa=str(chat_id)).exists():
                    self.stdout.write(f"   ⏭️  Chat {chat_id} já auditado. Pulando.")
                    total_puladas += 1
                    continue

                # Buscar mensagens do chat
                mensagens = bitrix_service.get_mensagens_sessao(session_id)
                if not mensagens:
                    self.stdout.write(f"   ⚠️  Chat {chat_id}: sem mensagens. Pulando.")
                    total_puladas += 1
                    continue

                transcript = bitrix_service.formatar_transcript(mensagens)

                # Montar link do chat (padrão Bitrix)
                link_chat = sessao.get('dialog_url') or sessao.get('link') or ''

                self.stdout.write(f"   🔍 Auditando chat {chat_id} ({tipo_atendimento}, fila: {nome_fila})...")

                # Chamar IA para auditar
                resultado_ia = ia_service.auditar_chat_automatico(
                    transcript=transcript,
                    tipo_atendimento=tipo_atendimento,
                    base_auditoria=base_auditoria,
                    analista_nome=analista_nome,
                )

                if not resultado_ia.get('sucesso'):
                    erro = resultado_ia.get('erro', 'Erro desconhecido')
                    self.stdout.write(self.style.ERROR(f"   ❌ Falha na auditoria IA: {erro}"))
                    total_erros += 1
                    continue

                # Montar justificativas em JSON para armazenar
                observacao_ia = json.dumps({
                    'apresentacao': resultado_ia.get('erro_apresentacao', ''),
                    'historico': resultado_ia.get('erro_historico', ''),
                    'entendimento': resultado_ia.get('erro_entendimento', ''),
                    'informacao': resultado_ia.get('erro_informacao', ''),
                    'acordo_espera': resultado_ia.get('erro_acordo_espera', ''),
                    'respeito': resultado_ia.get('erro_respeito', ''),
                    'portugues': resultado_ia.get('erro_portugues', ''),
                    'finalizacao': resultado_ia.get('erro_finalizacao', ''),
                    'procedimento': resultado_ia.get('erro_procedimento', ''),
                }, ensure_ascii=False)

                if dry_run:
                    pontos_ok = sum(1 for k in [
                        'apresentou_corretamente', 'analisou_historico', 'entendeu_solicitacao',
                        'informacao_clara', 'acordo_espera', 'atendimento_respeitoso',
                        'portugues_correto', 'finalizacao_correta', 'procedimento_correto'
                    ] if resultado_ia.get(k, True))
                    self.stdout.write(self.style.SUCCESS(
                        f"   [DRY-RUN] Chat {chat_id}: {pontos_ok}/9 critérios OK"
                    ))
                    total_criadas += 1
                    continue

                # Buscar auditor "sistema" (usuário IA)
                auditor_ia = User.objects.filter(username='nexus_ia_auditor').first()
                if not auditor_ia:
                    # Usar o primeiro admin/gestor do departamento como auditor substituto
                    auditor_ia = User.objects.filter(
                        department=department,
                        role__in=['administrador', 'gestor']
                    ).first() or User.objects.filter(is_superuser=True).first()

                if not auditor_ia:
                    self.stdout.write(self.style.ERROR("   ❌ Nenhum auditor disponível. Configure um gestor no departamento."))
                    total_erros += 1
                    continue

                # Salvar auditoria no banco
                try:
                    auditoria = AuditoriaAtendimento(
                        data_atendimento=data_alvo,
                        id_conversa=str(chat_id),
                        link_conversa=link_chat,
                        tipo_atendimento=tipo_atendimento,
                        analista_auditado=user_nexus,
                        auditor=auditor_ia,
                        department=department,
                        # Critérios
                        apresentou_corretamente=resultado_ia.get('apresentou_corretamente', True),
                        erro_apresentacao=resultado_ia.get('erro_apresentacao', ''),
                        analisou_historico=resultado_ia.get('analisou_historico', True),
                        erro_historico=resultado_ia.get('erro_historico', ''),
                        entendeu_solicitacao=resultado_ia.get('entendeu_solicitacao', True),
                        erro_entendimento=resultado_ia.get('erro_entendimento', ''),
                        informacao_clara=resultado_ia.get('informacao_clara', True),
                        erro_informacao=resultado_ia.get('erro_informacao', ''),
                        acordo_espera=resultado_ia.get('acordo_espera', True),
                        erro_acordo_espera=resultado_ia.get('erro_acordo_espera', ''),
                        atendimento_respeitoso=resultado_ia.get('atendimento_respeitoso', True),
                        erro_respeito=resultado_ia.get('erro_respeito', ''),
                        portugues_correto=resultado_ia.get('portugues_correto', True),
                        erro_portugues=resultado_ia.get('erro_portugues', ''),
                        finalizacao_correta=resultado_ia.get('finalizacao_correta', True),
                        erro_finalizacao=resultado_ia.get('erro_finalizacao', ''),
                        procedimento_correto=resultado_ia.get('procedimento_correto', True),
                        erro_procedimento=resultado_ia.get('erro_procedimento', ''),
                        # Rastreamento IA
                        gerado_por_ia=True,
                        observacao_ia=observacao_ia,
                    )
                    auditoria.save()  # O save() do model calcula pontuacao/nota/classificacao automaticamente
                    total_criadas += 1
                    self.stdout.write(self.style.SUCCESS(
                        f"   ✅ Chat {chat_id}: Nota {auditoria.nota} ({auditoria.classificacao}) — salvo!"
                    ))

                except Exception as e:
                    logger.error(f"[auditar_bitrix] Erro ao salvar auditoria do chat {chat_id}: {e}")
                    self.stdout.write(self.style.ERROR(f"   ❌ Erro ao salvar: {e}"))
                    total_erros += 1

        # Resumo final
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\n{'=' * 60}\n"
            f"  📊 RESUMO DA EXECUÇÃO\n"
            f"  ✅ Auditorias {'simuladas' if dry_run else 'criadas'}: {total_criadas}\n"
            f"  ⏭️  Puladas: {total_puladas}\n"
            f"  ❌ Erros: {total_erros}\n"
            f"{'=' * 60}\n"
        ))
