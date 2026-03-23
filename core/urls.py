from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .api import escala as api_escala
from .api import eventos as api_eventos
from .api import kb as api_kb
from .api import quadro as api_quadro
from .api import tasks as api_tasks
from .api import desempenho as api_desempenho
from .api import refunds as api_refunds
from .api import stores as api_stores
from .api import kanban as api_kanban
from .api import store_verification as api_store_verification
from .api import auditoria as api_auditoria
from .api import chat_inactivity as api_chat_inactivity
from .api import rh as api_rh
from .api import ponto as api_ponto
from . import views_ponto
from .api.quadro import api_quadro_data, api_cartao_create, api_cartao_move, api_cartao_update, api_cartao_delete, api_cartao_details, api_comentario_add, api_anexo_add, api_anexo_delete, api_lista_create, api_lista_delete



urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', views.login_view_custom, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    path('tarefas/', views.tasks_view, name='tasks_view'),
    path('complaints/', views.complaint_list, name='complaint_list'),
    path('complaints/<int:pk>/', views.complaint_detail, name='complaint_detail'),
    path('complaints/new/', views.complaint_create, name='complaint_create'),
    path('complaints/<int:pk>/edit/', views.complaint_edit, name='complaint_edit'),
    path('complaints/<int:pk>/delete/', views.complaint_delete, name='complaint_delete'),
    path('complaints/bulk-delete/', views.complaint_bulk_delete, name='complaint_bulk_delete'),
    path('stores/', views.store_list, name='store_list'),
    path('stores/<str:loja_cod>/', views.store_complaints, name='store_complaints'),
    path('users/', views.user_list, name='user_list'),
    path('users/new/', views.user_create, name='user_create'),
    path('users/<int:pk>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:pk>/delete/', views.user_delete, name='user_delete'),
    path('users/history/', views.user_access_history, name='user_access_history'),
    path('settings/', views.settings_view, name='settings'),
    path('export/complaints/csv/', views.export_complaints_csv, name='export_complaints_csv'),
    path('export/complaints/xlsx/', views.export_complaints_xlsx, name='export_complaints_xlsx'),
    path('export/stores/csv/', views.export_stores_csv, name='export_stores_csv'),
    path('export/stores/xlsx/', views.export_stores_xlsx, name='export_stores_xlsx'),
    path('export/users/csv/', views.export_users_csv, name='export_users_csv'),
    path('export/users/xlsx/', views.export_users_xlsx, name='export_users_xlsx'),
    path('complaints/import/', views.import_complaints_xlsx, name='import_complaints_xlsx'),
    path('complaints/import/batch/', views.import_complaints_batch, name='import_complaints_batch'),
    path('reports/', views.reports_view, name='reports'),
    path('department/change/<int:dept_id>/', views.change_department, name='change_department'),
    
    
    # Abas em desenvolvimento - CS Clientes
    path('google-meu-negocio/', views.under_development, {'page_name': 'Google Meu Negócio'}, name='google_meu_negocio'),
    
    # NRS Suporte - Abas implementadas
    path('escala/', views.escala_view, name='escala'),
    path('sites/', views.sites_view, name='sites'),
    path('localizacao-lojas/', views.localizacao_view, name='localizacao'),
    path('verificacao-lojas/', views.verificacao_lojas, name='verificacao_lojas'),
    path('verificacao-lojas/auditoria/<int:store_id>/', views.store_audit_create, name='store_audit_create'),
    path('verificacao-lojas/resolver/<int:issue_id>/', views.store_issue_resolve, name='store_issue_resolve'),
    path('verificacao-lojas/loja/nova/', views.store_create, name='store_create'),
    path('verificacao-lojas/loja/importar/', views.import_stores_xlsx, name='import_stores_xlsx'),
    path('verificacao-lojas/loja/<int:store_id>/editar/', views.store_edit, name='store_edit'),
    path('verificacao-lojas/loja/<int:store_id>/excluir/', views.store_delete, name='store_delete'),
    path('verificacao-lojas/pendencia/<int:issue_id>/editar/', views.store_issue_edit, name='store_issue_edit'),
    path('verificacao-lojas/pendencia/<int:issue_id>/excluir/', views.store_issue_delete, name='store_issue_delete'),
    path('verificacao-lojas/loja/excluir-todas/', views.store_bulk_delete, name='store_bulk_delete'),
    
    # NRS Suporte - Abas em desenvolvimento

    path('calendario/', views.calendar_view, name='calendario'),
    path('base-conhecimento/', views.knowledge_base_view, name='base_conhecimento'),
    path('desempenho/', views.performance_view, name='desempenho'),
    path('quadro/', views.quadro_view, name='quadro'),
    
    # API Quadro
    path('api/quadro/data/', api_quadro.api_quadro_data, name='api_quadro_data'),
    path('api/quadro/cartao/create/', api_cartao_create, name='api_cartao_create'),
    path('api/quadro/cartao/move/', api_cartao_move, name='api_cartao_move'),
    path('api/quadro/cartao/<int:cartao_id>/update/', api_cartao_update, name='api_cartao_update'),
    path('api/quadro/cartao/<int:cartao_id>/delete/', api_cartao_delete, name='api_cartao_delete'),
    path('api/quadro/cartao/<int:cartao_id>/details/', api_quadro.api_cartao_details, name='api_cartao_details'),
    path('api/quadro/cartao/<int:cartao_id>/comentario/', api_quadro.api_comentario_add, name='api_comentario_add'),
    path('api/quadro/cartao/<int:cartao_id>/anexo/', api_quadro.api_anexo_add, name='api_anexo_add'),
    path('api/quadro/anexo/<int:anexo_id>/delete/', api_quadro.api_anexo_delete, name='api_anexo_delete'),
    path('api/quadro/lista/create/', api_quadro.api_lista_create, name='api_lista_create'),
    path('api/quadro/lista/move/', api_quadro.api_lista_move, name='api_lista_move'),
    path('api/quadro/lista/<int:lista_id>/delete/', api_quadro.api_lista_delete, name='api_lista_delete'),
    path('api/quadro/lista/<int:lista_id>/archive/', api_quadro.api_lista_archive, name='api_lista_archive'),
    path('api/quadro/cartao/<int:cartao_id>/archive/', api_quadro.api_cartao_archive, name='api_cartao_archive'),
    
    # Abas em desenvolvimento - Onboarding
    path('onboarding/dev1/', views.under_development, {'page_name': 'Onboarding - Em Desenvolvimento 1'}, name='onboarding_dev_1'),
    path('onboarding/dev2/', views.under_development, {'page_name': 'Onboarding - Em Desenvolvimento 2'}, name='onboarding_dev_2'),
    path('onboarding/dev3/', views.under_development, {'page_name': 'Onboarding - Em Desenvolvimento 3'}, name='onboarding_dev_3'),

    # Abas em desenvolvimento - RH
    path('rh/ponto-frequencia/', views.under_development, {
        'page_name': 'Gestão de Ponto e Frequência',
        'description': 'Integração para comparação entre a escala planejada e o registro de ponto realizado, permitindo identificar divergências de horário automaticamente.'
    }, name='rh_ponto_frequencia'),
    path('rh/ferias-folgas/', views.under_development, {
        'page_name': 'Solicitação de Férias e Folgas',
        'description': 'Portal para que colaboradores solicitem períodos de descanso, com fluxo de aprovação integrado entre gestores de operação e RH.'
    }, name='rh_ferias_folgas'),
    path('rh/absenteismo/', views.under_development, {
        'page_name': 'Dashboard de Absenteísmo',
        'description': 'Indicadores automáticos de taxas de falta e rotatividade (turnover) baseados nos registros de escala e frequência.'
    }, name='rh_absenteismo'),
    path('rh/colaboradores/', views.rh_colaboradores_view, name='rh_colaboradores'),
    path('rh/colaboradores/novo/', views.rh_cadastro_funcionario_view, name='rh_cadastro_funcionario'),
    path('rh/colaboradores/<int:pk>/', views.rh_colaborador_perfil_view, name='rh_colaborador_perfil'),
    path('rh/colaboradores/<int:pk>/editar/', views.rh_cadastro_funcionario_view, name='rh_editar_funcionario'),
    # Empresas
    path('rh/empresas/', views.rh_empresas_view, name='rh_empresas'),
    path('rh/empresas/novo/', views.rh_cadastro_empresa_view, name='rh_cadastro_empresa'),
    path('rh/empresas/<int:pk>/editar/', views.rh_cadastro_empresa_view, name='rh_editar_empresa'),
    # Departamentos
    path('rh/departamentos/', views.rh_departamentos_view, name='rh_departamentos'),
    # Centros de Custo
    path('rh/centros-custo/', views.rh_centros_custo_view, name='rh_centros_custo'),
    # Cargos
    path('rh/cargos/', views.rh_cargos_view, name='rh_cargos'),
    # Feriados e Atribuições
    path('rh/feriados/', views.rh_feriados_view, name='rh_feriados'),
    path('rh/atribuicoes-massa/', views.rh_atribuicoes_massa_view, name='rh_atribuicoes_massa'),
    path('rh/horarios/', views.rh_horarios_view, name='rh_horarios'),
    path('rh/horarios/add/', views.rh_cadastro_horario_view, name='rh_cadastro_horario_add'),
    path('rh/horarios/<int:pk>/', views.rh_cadastro_horario_view, name='rh_cadastro_horario'),
    # Apuração de Ponto
    path('rh/apuracao/', views.rh_apuracao_view, name='rh_apuracao'),
    # API Empresas
    path('api/rh/empresas/', api_rh.api_empresas_list, name='api_empresas_list'),
    path('api/rh/empresas/save/', api_rh.api_save_empresa, name='api_save_empresa'),
    path('api/rh/empresas/<int:pk>/delete/', api_rh.api_delete_empresa, name='api_delete_empresa'),
    # API Departamentos
    path('api/rh/departamentos/', api_rh.api_departamentos_list, name='api_departamentos_list'),
    path('api/rh/departamentos/save/', api_rh.api_save_departamento, name='api_save_departamento'),
    path('api/rh/departamentos/<int:pk>/delete/', api_rh.api_delete_departamento, name='api_delete_departamento'),
    # API Cargos
    path('api/rh/cargos/', api_rh.api_cargos_list, name='api_cargos_list'),
    path('api/rh/cargos/save/', api_rh.api_save_cargo, name='api_save_cargo'),
    path('api/rh/cargos/<int:pk>/delete/', api_rh.api_delete_cargo, name='api_delete_cargo'),
    # API Centros de Custo
    path('api/rh/centros-custo/', api_rh.api_centros_custo_list, name='api_centros_custo_list'),
    path('api/rh/centros-custo/save/', api_rh.api_save_centro_custo, name='api_save_centro_custo'),
    path('api/rh/centros-custo/delete/<int:pk>/', api_rh.api_delete_centro_custo, name='api_delete_centro_custo'),
    # API Feriados
    path('api/rh/feriados/', api_rh.api_feriados_list, name='api_feriados_list'),
    path('api/rh/feriados/save/', api_rh.api_save_feriado, name='api_save_feriado'),
    path('api/rh/feriados/<int:pk>/delete/', api_rh.api_delete_feriado, name='api_delete_feriado'),
    path('rh/onboarding/', views.under_development, {
        'page_name': 'Acompanhamento de Onboarding',
        'description': 'Checklist interativo para garantir que todos os novos colaboradores recebam equipamentos, acessos e treinamentos necessários.'
    }, name='rh_onboarding'),
    
    # API Escala NRS
    path('api/escala/turnos/', api_escala.api_turnos_list, name='api_turnos_list'),
    path('api/escala/turnos/create/', api_escala.api_turno_create, name='api_turno_create'),
    path('api/escala/turnos/<int:pk>/', api_escala.api_turno_detail, name='api_turno_detail'),
    path('api/escala/turnos/reorder/', api_escala.api_turnos_reorder, name='api_turnos_reorder'),
    path('api/escala/analistas/', api_escala.api_analistas_list, name='api_analistas_list'),
    path('api/escala/analistas/create/', api_escala.api_analista_create, name='api_analista_create'),
    path('api/escala/analistas/reorder/', api_escala.api_analistas_reorder, name='api_analistas_reorder'),
    path('api/escala/analistas/<int:pk>/', api_escala.api_analista_detail, name='api_analista_detail'),
    path('api/escala/folgas/', api_escala.api_folgas_list, name='api_folgas_list'),
    path('api/escala/folgas/save/', api_escala.api_folga_save, name='api_folga_save'),
    path('api/escala/folgas/<int:pk>/delete/', api_escala.api_folga_delete, name='api_folga_delete'),
    
    # API Calendário
    path('api/eventos/users/', api_eventos.api_eventos_users_list, name='api_eventos_users_list'),
    path('api/eventos/', api_eventos.api_eventos_list, name='api_eventos_list'),
    path('api/eventos/create/', api_eventos.api_evento_create, name='api_evento_create'),
    path('api/eventos/<int:pk>/', api_eventos.api_evento_detail, name='api_evento_detail'),
    
    # API Base de Conhecimento
    path('api/kb/articles/', api_kb.api_kb_articles_list, name='api_kb_articles_list'),
    path('api/kb/articles/create/', api_kb.api_kb_article_create, name='api_kb_article_create'),
    path('api/kb/articles/<int:pk>/', api_kb.api_kb_article_detail, name='api_kb_article_detail'),
    path('api/kb/tools/', api_kb.api_kb_tools_list, name='api_kb_tools_list'),
    
    # API Desempenho
    path('api/desempenho/kpis/', api_desempenho.api_kpis_list, name='api_kpis_list'),
    path('api/desempenho/kpis/save/', api_desempenho.api_kpi_save, name='api_kpi_save'),
    path('api/desempenho/kpis/<int:pk>/delete/', api_desempenho.api_kpi_delete, name='api_kpi_delete'),
    path('api/desempenho/metas/global/', api_desempenho.api_global_metas_list, name='api_global_metas_list'),
    path('api/desempenho/metas/global/save/', api_desempenho.api_global_meta_save, name='api_global_meta_save'),
    path('api/desempenho/metas/global/<int:pk>/delete/', api_desempenho.api_global_meta_delete, name='api_global_meta_delete'),
    path('api/desempenho/ranking/', api_desempenho.api_ranking, name='api_ranking'),
    path('api/desempenho/podium/', api_desempenho.api_podium, name='api_podium'),


    # API Tarefas e Rotinas
    path('api/tasks/', api_tasks.api_tasks_list, name='api_tasks_list'),
    path('api/tasks/create/', api_tasks.api_task_create, name='api_task_create'),
    path('api/tasks/<int:pk>/toggle/', api_tasks.api_task_toggle, name='api_task_toggle'),
    path('api/tasks/<int:pk>/edit/', api_tasks.api_task_edit, name='api_task_edit'),
    path('api/tasks/<int:pk>/delete/', api_tasks.api_task_delete, name='api_task_delete'),
    path('api/notifications/check/', api_tasks.api_notifications_check, name='api_notifications_check'),
    path('api/system/notifications/', views.api_get_system_notifications, name='api_get_system_notifications'),

    
    path('api/routines/daily/', api_tasks.api_routines_daily, name='api_routines_daily'),
    path('api/routines/create/', api_tasks.api_routine_create, name='api_routine_create'),
    path('api/routines/check/<int:log_id>/', api_tasks.api_routine_check, name='api_routine_check'),
    path('api/routines/alerts/', api_tasks.api_manager_alerts, name='api_manager_alerts'),
    path('api/routines/overview/', api_tasks.api_routines_overview, name='api_routines_overview'),
    
    # Refund Request APIs
    path('solicitacoes/', views.solicitacoes_view, name='solicitacoes'),
    path('api/refunds/create/', api_refunds.api_refund_create, name='api_refund_create'),
    path('api/refunds/list/', api_refunds.api_refund_list, name='api_refund_list'),
    path('api/refunds/<int:pk>/', api_refunds.api_refund_detail, name='api_refund_detail'),
    path('api/refunds/<int:pk>/status/', api_refunds.api_refund_update_status, name='api_refund_update_status'),
    path('api/refunds/<int:pk>/attachment/', api_refunds.api_refund_add_attachment, name='api_refund_add_attachment'),
    path('api/refunds/<int:pk>/cancel/', api_refunds.api_refund_request_cancellation, name='api_refund_cancel'),
    path('api/refunds/<int:pk>/delete/', api_refunds.api_refund_delete, name='api_refund_delete'),
    path('api/refunds/notifications/', api_refunds.api_refund_notifications, name='api_refund_notifications'),
    path('api/refunds/stats/', api_refunds.api_refund_stats, name='api_refund_stats'),
    path('api/refunds/<int:pk>/edit/', api_refunds.api_refund_edit, name='api_refund_edit'),
    path('api/users/nrs-analysts/', api_refunds.api_nrs_analysts, name='api_nrs_analysts'),

    
    # Store Presence and History APIs
    path('api/stores/presence/', api_stores.api_stores_all_presence, name='api_stores_all_presence'),
    path('api/stores/<int:store_id>/detail/', views.api_store_detail, name='api_store_detail'),
    path('api/stores/<int:store_id>/presence/heartbeat/', api_stores.api_store_presence_heartbeat, name='api_store_presence_heartbeat'),
    path('api/stores/<int:store_id>/presence/', api_stores.api_store_presence_list, name='api_store_presence_list'),
    path('api/stores/<int:store_id>/presence/leave/', api_stores.api_store_presence_leave, name='api_store_presence_leave'),
    path('api/stores/<int:store_id>/history/', api_stores.api_store_audit_history, name='api_store_audit_history'),
    
    # Store Verification APIs - Notificações e Timers
    path('api/store-verification/issue/<int:issue_id>/notify/', api_store_verification.api_notify_franchisee, name='api_notify_franchisee'),
    path('api/store-verification/issue/<int:issue_id>/whatsapp/start/', api_store_verification.api_start_whatsapp_notification, name='api_start_whatsapp_notification'),
    path('api/store-verification/issue/<int:issue_id>/ticket/create/', api_store_verification.api_create_ticket_from_issue, name='api_create_ticket_from_issue'),
    path('api/store-verification/issue/<int:issue_id>/resolve/', api_store_verification.api_mark_issue_resolved, name='api_mark_issue_resolved'),
    path('api/store-verification/issue/<int:issue_id>/timer/status/', api_store_verification.api_get_timer_status, name='api_get_timer_status'),
    path('api/store-verification/issue/<int:issue_id>/escalate/', api_store_verification.api_escalate_to_ticket, name='api_escalate_to_ticket'),
    
    # Store Verification APIs - Gestão de Analistas
    path('api/store-verification/analyst/assignments/', api_store_verification.api_get_analyst_assignments, name='api_get_analyst_assignments'),
    path('api/store-verification/analyst/all-assignments/', api_store_verification.api_get_all_assignments, name='api_get_all_assignments'),
    path('api/store-verification/analyst/assign/', api_store_verification.api_assign_store_to_analyst, name='api_assign_store_to_analyst'),
    path('api/store-verification/analyst/available-stores/', api_store_verification.api_get_available_stores, name='api_get_available_stores'),
    path('api/store-verification/analyst/bulk-assign/', api_store_verification.api_bulk_assign_stores, name='api_bulk_assign_stores'),
    path('api/store-verification/analyst/auto-distribute/', api_store_verification.api_auto_distribute_stores, name='api_auto_distribute_stores'),
    path('api/store-verification/analyst/unassign/<int:assignment_id>/', api_store_verification.api_unassign_store, name='api_unassign_store'),
    path('api/store-verification/analyst/unassign-all/', api_store_verification.api_unassign_all_stores, name='api_unassign_all_stores'),
    path('api/store-verification/analyst/dashboard/', api_store_verification.api_get_analyst_dashboard, name='api_get_analyst_dashboard'),
    path('api/store-verification/analyst/monthly-kpi/', api_store_verification.api_get_monthly_kpi, name='api_get_monthly_kpi'),
    path('api/store-verification/analyst/overview/', api_store_verification.api_get_analysts_overview, name='api_get_analysts_overview'),
    path('api/store-verification/manager/all-analysts-kpi/', api_store_verification.api_get_all_analysts_monthly_kpi, name='api_get_all_analysts_monthly_kpi'),
    path('api/store-verification/analyst/override-quota/', api_store_verification.api_override_daily_quota, name='api_override_daily_quota'),
    
    # Chat - REMOVED
    
    # Kanban API
    path('api/kanban/boards/', api_kanban.api_boards, name='api_kanban_boards'),
    path('api/kanban/boards/<int:board_id>/', api_kanban.api_board_detail, name='api_kanban_board_detail'),
    path('api/kanban/boards/<int:board_id>/lists/', api_kanban.api_board_lists, name='api_kanban_board_lists'),
    path('api/kanban/boards/<int:board_id>/lists/reorder/', api_kanban.api_lists_reorder, name='api_kanban_lists_reorder'),
    path('api/kanban/lists/<int:list_id>/', api_kanban.api_list_detail, name='api_kanban_list_detail'),
    path('api/kanban/lists/<int:list_id>/cards/', api_kanban.api_list_cards, name='api_kanban_list_cards'),
    path('api/kanban/lists/<int:list_id>/cards/reorder/', api_kanban.api_cards_reorder, name='api_kanban_cards_reorder'),
    path('api/kanban/cards/<int:card_id>/', api_kanban.api_card_detail, name='api_kanban_card_detail'),
    path('api/kanban/cards/<int:card_id>/move/', api_kanban.api_card_move, name='api_kanban_card_move'),
    path('api/kanban/cards/<int:card_id>/labels/', api_kanban.api_card_labels, name='api_kanban_card_labels'),
    path('api/kanban/cards/<int:card_id>/checklists/', api_kanban.api_card_checklists, name='api_kanban_card_checklists'),
    path('api/kanban/checklists/<int:checklist_id>/items/', api_kanban.api_checklist_items, name='api_kanban_checklist_items'),
    path('api/kanban/cards/<int:card_id>/comments/', api_kanban.api_card_comments, name='api_kanban_card_comments'),
    path('api/kanban/cards/<int:card_id>/members/', api_kanban.api_card_members, name='api_kanban_card_members'),
    path('api/kanban/cards/<int:card_id>/attachments/', api_kanban.api_card_attachments, name='api_kanban_card_attachments'),
    path('api/kanban/cards/<int:card_id>/attachments/<int:attachment_id>/', api_kanban.api_card_attachment_delete, name='api_kanban_card_attachment_delete'),
    path('api/kanban/search/', api_kanban.api_kanban_search, name='api_kanban_search'),
    
    # Label CRUD
    path('api/kanban/boards/<int:board_id>/labels/', api_kanban.api_board_labels, name='api_kanban_board_labels'),
    path('api/kanban/labels/<int:label_id>/', api_kanban.api_label_detail, name='api_kanban_label_detail'),
    
    # Auditoria de Atendimentos
    path('auditoria-atendimentos/', views.auditoria_atendimentos_view, name='auditoria_atendimentos'),
    
    # API Auditoria de Atendimentos
    path('api/auditoria/create/', api_auditoria.api_auditoria_create, name='api_auditoria_create'),
    path('api/auditoria/list/', api_auditoria.api_auditoria_list, name='api_auditoria_list'),
    path('api/auditoria/<int:pk>/', api_auditoria.api_auditoria_detail, name='api_auditoria_detail'),
    path('api/auditoria/<int:pk>/update/', api_auditoria.api_auditoria_update, name='api_auditoria_update'),
    path('api/auditoria/<int:pk>/delete/', api_auditoria.api_auditoria_delete, name='api_auditoria_delete'),
    path('api/auditoria/ranking/', api_auditoria.api_ranking_analistas, name='api_ranking_analistas'),
    path('api/auditoria/analista/<int:analista_id>/', api_auditoria.api_estatisticas_analista, name='api_estatisticas_analista'),
    path('api/auditoria/dashboard/', api_auditoria.api_dashboard_auditoria, name='api_dashboard_auditoria'),
    path('api/auditoria/config/', api_auditoria.api_configuracao_get, name='api_configuracao_get'),
    path('api/auditoria/config/update/', api_auditoria.api_configuracao_update, name='api_configuracao_update'),
    path('api/auditoria/analistas/', api_auditoria.api_analistas_list, name='api_auditoria_analistas_list'),
    path('api/auditoria/<int:pk>/feedback/', api_auditoria.api_registrar_feedback, name='api_registrar_feedback'),
    path('api/auditoria/check-id/', api_auditoria.api_check_conversation_id, name='api_check_conversation_id'),
    path('api/auditoria/<int:pk>/ciente/', api_auditoria.api_registrar_ciente, name='api_registrar_ciente'),

    # Chat Inactivity Removal APIs
    path('api/chat-inactivity/list/', api_chat_inactivity.api_chat_inactivity_list, name='api_chat_inactivity_list'),
    path('api/chat-inactivity/create/', api_chat_inactivity.api_chat_inactivity_create, name='api_chat_inactivity_create'),
    path('api/chat-inactivity/<str:pk>/delete/', api_chat_inactivity.api_chat_inactivity_delete, name='api_chat_inactivity_delete'),
    path('api/chat-inactivity/<str:pk>/action/', api_chat_inactivity.api_chat_inactivity_action, name='api_chat_inactivity_action'),

    # API RH - Colaboradores
    path('api/rh/auxiliar-data/', api_rh.api_rh_auxiliar_data, name='api_rh_auxiliar_data'),
    path('api/rh/auxiliar/', api_rh.api_rh_auxiliar_data, name='api_rh_auxiliar'),
    path('api/rh/colaboradores/', api_rh.api_colaboradores_list, name='api_rh_colaboradores_list'),
    path('api/rh/colaboradores/save/', api_rh.api_save_colaborador, name='api_rh_save_colaborador'),
    path('api/rh/colaboradores/<int:pk>/', api_rh.api_colaborador_detail, name='api_rh_colaborador_detail'),
    path('api/rh/colaboradores/<int:pk>/delete/', api_rh.api_delete_colaborador, name='api_rh_delete_colaborador'),
    
    # API RH - Horários
    path('api/rh/horarios/', api_rh.api_rh_horarios_list, name='api_rh_horarios_list'),
    path('api/rh/horarios/save/', api_rh.api_save_horario, name='api_rh_save_horario'),
    path('api/rh/horarios/<int:pk>/', api_rh.api_rh_horario_detail, name='api_rh_horario_detail'),
    path('api/rh/horarios/<int:pk>/delete/', api_rh.api_delete_horario, name='api_rh_delete_horario'),
    path('api/rh/colaboradores/historico/save/', api_rh.api_save_historico, name='api_rh_save_historico'),
    path('api/rh/colaboradores/historico/<int:pk>/delete/', api_rh.api_delete_historico, name='api_rh_delete_historico'),
    path('api/rh/colaboradores/performance/save/', api_rh.api_save_performance, name='api_rh_save_performance'),
    path('api/rh/colaboradores/documentos/upload/', api_rh.api_upload_documento, name='api_rh_upload_documento'),
    path('api/rh/colaboradores/documentos/<int:pk>/delete/', api_rh.api_delete_documento, name='api_rh_delete_documento'),

    # API RH - Apuração Visuais
    path('api/rh/apuracao/layout/listar/', api_rh.api_listar_visuais_apuracao, name='api_listar_visuais_apuracao'),
    path('api/rh/apuracao/layout/salvar/', api_rh.api_salvar_visual_apuracao, name='api_salvar_visual_apuracao'),
    path('api/rh/apuracao/layout/excluir/<int:pk>/', api_rh.api_excluir_visual_apuracao, name='api_excluir_visual_apuracao'),
    path('api/rh/apuracao-dados/', api_rh.api_rh_apuracao_dados, name='api_rh_apuracao_dados'),

    # Ponto Eletrônico - Views
    path('ponto/tablet/', views_ponto.ponto_kiosk, name='ponto_kiosk'),
    path('rh/ponto/', views_ponto.ponto_admin, name='ponto_admin'),
    path('rh/ponto/relatorios/', views_ponto.ponto_relatorios, name='ponto_relatorios'),

    # Ponto Eletrônico - API
    path('api/rh/atribuicoes-massa/execute/', api_rh.api_execute_atribuicao_massa, name='api_rh_execute_atribuicao_massa'),
    path('api/ponto/buscar-colaborador/', api_ponto.buscar_colaborador, name='api_ponto_buscar_colaborador'),
    path('api/ponto/registrar/', api_ponto.registrar_ponto, name='api_ponto_registrar_ponto'),
    path('api/ponto/registros/', api_ponto.listar_registros, name='api_ponto_listar_registros'),
    path('api/ponto/ajustar/<int:pk>/', api_ponto.ajustar_registro, name='api_ponto_ajustar_registro'),
    path('api/ponto/ajustar/', api_ponto.ajustar_registro, name='api_ponto_ajustar_registro_new'),
    path('api/ponto/<int:pk>/delete/', api_ponto.deletar_registro, name='api_ponto_deletar_registro'),
    path('api/ponto/dashboard/', api_ponto.dashboard_ponto, name='api_ponto_dashboard_ponto'),
    path('api/ponto/banco-horas/<int:pk>/', api_ponto.banco_horas, name='api_ponto_banco_horas'),
    path('api/ponto/relatorio/', api_ponto.relatorio_mensal, name='api_ponto_relatorio_mensal'),
    path('api/ponto/exportar-excel/', api_ponto.exportar_excel, name='api_ponto_exportar_excel'),
]

