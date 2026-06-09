"""
Script para popular o banco com as primeiras Notificações do Sistema (Novidades).
Execute com: python manage.py shell < scripts/seed_system_notifications.py
Ou: python manage.py runscript seed_system_notifications  (se usar django-extensions)
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'brisoft.settings')
django.setup()

from core.models import SystemNotification

NOTIFICATIONS = [
    {
        'title': '🤖 Brisoft IA — Assistente Inteligente',
        'category': 'news',
        'message': 'O Brisoft agora conta com um assistente de IA integrado! Clique no ícone roxo ✨ no canto inferior direito para conversar com ele.',
        'details': """
<h5>🤖 Brisoft IA chegou!</h5>
<p>O <strong>Assistente Brisoft IA</strong> está disponível em todas as páginas do sistema. Ele usa a Base de Conhecimento do seu departamento para responder dúvidas, orientar processos e até executar ações no sistema.</p>
<h6>O que ele pode fazer:</h6>
<ul>
  <li>Responder perguntas com base na Base de Conhecimento do departamento</li>
  <li>Classificar reclamações do Reclame Aqui por urgência e sentimento</li>
  <li>Navegar para páginas do sistema por comando de voz/texto</li>
  <li>Auxiliar gestores em tarefas operacionais</li>
</ul>
<p><strong>Como acessar:</strong> clique no botão roxo com ✨ no canto inferior direito de qualquer página.</p>
"""
    },
    {
        'title': '🕐 Sistema de Ponto Eletrônico',
        'category': 'system',
        'message': 'Módulo completo de controle de ponto: apuração mensal, ponto diário, banco de horas, inconsistências e exportação de relatórios.',
        'details': """
<h5>Sistema de Ponto Eletrônico</h5>
<p>O módulo de RH & Ponto está completamente funcional com os seguintes recursos:</p>
<ul>
  <li><strong>Ponto Eletrônico (Tablet/Kiosk):</strong> colaboradores batem ponto via tablet com identificação por matrícula</li>
  <li><strong>Apuração de Ponto:</strong> cálculo automático de horas trabalhadas, extras, faltas e inconsistências</li>
  <li><strong>Ponto Diário:</strong> visão em tempo real do dia atual para todos os colaboradores</li>
  <li><strong>Inconsistências:</strong> listagem e gestão de registros irregulares com exportação PDF</li>
  <li><strong>Justificativas:</strong> lançamento de abonos, atestados, DSR e extras com impacto na folha</li>
</ul>
<p><em>Acesse pelo menu Departamento → RH → Apuração e Cálculo</em></p>
"""
    },
    {
        'title': '🏪 Auditoria de Lojas — Sistema Completo',
        'category': 'system',
        'message': 'Auditoria de lojas com checklists por critérios, gestão de analistas, KPIs semanais, timers de resolução e histórico completo.',
        'details': """
<h5>Auditoria de Lojas</h5>
<p>Módulo completo para verificação e conformidade das lojas franqueadas:</p>
<ul>
  <li><strong>Checklists:</strong> 8 critérios por auditoria (câmeras, estofados, layout, marketing, etc.)</li>
  <li><strong>Gestão de Analistas:</strong> distribuição de lojas, metas diárias e KPIs individuais</li>
  <li><strong>Pendências com Timer:</strong> acompanhe o prazo de resolução de irregularidades</li>
  <li><strong>Notificações ao franqueado:</strong> WhatsApp e e-mail direto do sistema</li>
  <li><strong>Histórico completo:</strong> todas as auditorias organizadas por data e analista</li>
</ul>
<p><em>Disponível para o departamento NRS Suporte</em></p>
"""
    },
    {
        'title': '✨ Classificação de Reclamações por IA',
        'category': 'news',
        'message': 'Reclamações do Reclame Aqui agora podem ser classificadas automaticamente por Urgência e Sentimento usando Inteligência Artificial.',
        'details': """
<h5>Classificação de Reclamações com IA</h5>
<p>A Brisoft IA agora analisa o texto das reclamações e retorna:</p>
<ul>
  <li><strong>Urgência:</strong> Baixa, Média, Alta ou Crítica — baseada no tom e conteúdo</li>
  <li><strong>Sentimento:</strong> Satisfeito, Neutro, Frustrado ou Muito Irritado</li>
</ul>
<p><strong>Como usar:</strong></p>
<ol>
  <li>Acesse a lista de reclamações (Reclame Aqui → Reclamações)</li>
  <li>Abra uma reclamação e clique em "Classificar com IA"</li>
  <li>Ou use a classificação em lote para processar várias de uma vez</li>
</ol>
<p><em>Os resultados são salvos e ficam visíveis na lista e no detalhe de cada reclamação.</em></p>
"""
    },
    {
        'title': '📄 Relatório de Inconsistências em PDF',
        'category': 'system',
        'message': 'Geração de Cartão de Ponto individualizado em PDF com todas as marcações, cálculos e inconsistências do mês por colaborador.',
        'details': """
<h5>Relatório de Inconsistências — PDF</h5>
<p>Agora é possível gerar relatórios profissionais em PDF diretamente do módulo de RH.</p>
<ul>
  <li>Layout de <strong>Cartão de Ponto</strong> por colaborador com grade do mês</li>
  <li>Seção de <strong>Alterações/Inconsistências</strong> no rodapé de cada cartão</li>
  <li>Dados de horas trabalhadas, extras, faltas, DSR e justificativas</li>
  <li>Cabeçalho com dados do colaborador, empresa e período</li>
  <li>Pronto para impressão e arquivamento</li>
</ul>
<p><em>Acesse: RH → Análise → Relatórios → Inconsistências</em></p>
"""
    },
    {
        'title': '📊 Auditoria de Atendimentos 2.0',
        'category': 'news',
        'message': 'Nova interface de auditoria com gráficos de evolução, pilares de qualidade e insights automáticos via Brisoft IA.',
        'details': """
<h5>Auditoria de Atendimentos 2.0</h5>
<p>A aba de auditoria foi totalmente modernizada para oferecer uma análise mais profunda do desempenho:</p>
<ul>
  <li><strong>Gráficos de Evolução:</strong> Acompanhe a média de notas ao longo do tempo.</li>
  <li><strong>Pilares de Qualidade:</strong> Gráfico de radar mostrando pontos fortes e fracos (Cordialidade, Agilidade, etc).</li>
  <li><strong>Brisoft IA Mentor:</strong> Inteligência Artificial que analisa o histórico do analista e gera feedbacks estruturados para reuniões de 1-on-1.</li>
  <li><strong>Filtros Inteligentes:</strong> Agora o sistema exibe automaticamente os dados do mês atual.</li>
</ul>
<p><em>Acesse: NRS Suporte → Auditoria de Atendimentos</em></p>
"""
    },
    {
        'title': '↩️ Melhoria na Navegação do Ponto',
        'category': 'system',
        'message': 'Adicionado botão de retorno ao Brisoft na tela de registro de ponto para acessos via computador/celular.',
        'details': """
<h5>Navegação Facilitada no Ponto</h5>
<p>Para melhorar a experiência de quem bate ponto pelo próprio cadastro:</p>
<ul>
  <li><strong>Botão Voltar:</strong> Agora você pode retornar ao Dashboard do Brisoft diretamente da tela de ponto.</li>
  <li><strong>Segurança Kiosk:</strong> O botão de saída permanece oculto em tablets de recepção para garantir a integridade do terminal.</li>
</ul>
"""
    },
]


def run():
    created = 0
    skipped = 0
    for data in NOTIFICATIONS:
        obj, is_new = SystemNotification.objects.get_or_create(
            title=data['title'],
            defaults={
                'category': data['category'],
                'message': data['message'],
                'details': data.get('details', ''),
                'is_active': True,
            }
        )
        if is_new:
            created += 1
            print(f"  ✅ Criada: {obj.title}")
        else:
            skipped += 1
            print(f"  ⏭  Já existe: {obj.title}")

    print(f"\nFinalizado: {created} criadas, {skipped} já existiam.")


if __name__ == '__main__':
    run()
