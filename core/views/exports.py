import csv
from datetime import datetime
from django.http import HttpResponse
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment
from ..models import Complaint, User, Store

@login_required
def export_complaints_csv(request):
    """Exportar reclamações para CSV - apenas gestores"""
    if not (request.user.is_gestor() or request.user.is_administrador()):
        messages.error(request, 'Você não tem permissão para exportar dados.')
        return redirect('dashboard')
    
    # Filtro base por departamento
    selected_dept_id = request.session.get('selected_department_id')
    if request.user.is_administrador():
        if selected_dept_id:
            complaints = Complaint.objects.filter(department_id=selected_dept_id).order_by('-created_at')
        else:
            complaints = Complaint.objects.all().order_by('-created_at')
    else:
        complaints = Complaint.objects.filter(department=request.user.department).order_by('-created_at')
    
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="reclamacoes_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['ID RA', 'CPF Cliente', 'Nome', 'E-mail', 'Telefone', 'Loja', 'Origem', 'Status', 'Analista', 'Data Reclamação', 'Nota', 'Volta Negócio'])
    
    for c in complaints:
        writer.writerow([
            c.id_ra,
            c.cpf_cliente,
            f"{c.nome_cliente} {c.sobrenome}",
            c.email_cliente,
            c.telefone,
            c.loja_cod,
            c.get_origem_contato_display(),
            c.get_status_display(),
            c.analista.username if c.analista else 'Não atribuído',
            c.data_reclamacao.strftime('%d/%m/%Y') if c.data_reclamacao else '',
            c.nota_satisfacao if c.nota_satisfacao is not None else '',
            c.get_volta_fazer_negocio_display() if c.volta_fazer_negocio else ''
        ])
    
    return response

@login_required
def export_complaints_xlsx(request):
    """Exportar reclamações para XLSX - apenas gestores"""
    if not (request.user.is_gestor() or request.user.is_administrador()):
        messages.error(request, 'Você não tem permissão para exportar dados.')
        return redirect('dashboard')
    
    # Filtro base por departamento
    selected_dept_id = request.session.get('selected_department_id')
    if request.user.is_administrador():
        if selected_dept_id:
            complaints = Complaint.objects.filter(department_id=selected_dept_id).order_by('-created_at')
        else:
            complaints = Complaint.objects.all().order_by('-created_at')
    else:
        complaints = Complaint.objects.filter(department=request.user.department).order_by('-created_at')
        
    wb = Workbook()
    ws = wb.active
    ws.title = "Reclamações"
    
    headers = ['ID RA', 'CPF Cliente', 'Nome', 'Sobrenome', 'E-mail', 'Telefone', 'Código Loja', 'Origem', 'Tipo', 'Status', 'Responsável', 'Data Reclamação', 'Data Resposta', 'Nota', 'Volta Negócio']
    
    # Estilo do cabeçalho
    header_fill = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num)
        cell.value = header
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center')
    
    for row_num, c in enumerate(complaints, 2):
        ws.cell(row=row_num, column=1, value=c.id_ra)
        ws.cell(row=row_num, column=2, value=c.cpf_cliente)
        ws.cell(row=row_num, column=3, value=c.nome_cliente)
        ws.cell(row=row_num, column=4, value=c.sobrenome)
        ws.cell(row=row_num, column=5, value=c.email_cliente)
        ws.cell(row=row_num, column=6, value=c.telefone)
        ws.cell(row=row_num, column=7, value=c.loja_cod)
        ws.cell(row=row_num, column=8, value=c.get_origem_contato_display())
        ws.cell(row=row_num, column=9, value=c.get_tipo_reclamacao_display() if c.tipo_reclamacao else '')
        ws.cell(row=row_num, column=10, value=c.get_status_display())
        ws.cell(row=row_num, column=11, value=c.analista.get_full_name() or c.analista.username if c.analista else 'Não atribuído')
        ws.cell(row=row_num, column=12, value=c.data_reclamacao.strftime('%d/%m/%Y') if c.data_reclamacao else '')
        ws.cell(row=row_num, column=13, value=c.data_resposta.strftime('%d/%m/%Y') if c.data_resposta else '')
        ws.cell(row=row_num, column=14, value=c.nota_satisfacao)
        ws.cell(row=row_num, column=15, value=c.get_volta_fazer_negocio_display() if c.volta_fazer_negocio else '')
        
    # Ajustar largura das colunas
    column_widths = [15, 15, 20, 20, 30, 15, 12, 12, 20, 15, 20, 15, 15, 8, 15]
    for col_num, width in enumerate(column_widths, 1):
        ws.column_dimensions[ws.cell(row=1, column=col_num).column_letter].width = width
    
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="reclamacoes_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
    
    wb.save(response)
    return response

@login_required
def export_stores_csv(request):
    """Exportar lojas para CSV - apenas gestores"""
    if not (request.user.is_gestor() or request.user.is_administrador()):
        messages.error(request, 'Você não tem permissão para exportar dados.')
        return redirect('dashboard')
    
    # Filtro base por departamento
    selected_dept_id = request.session.get('selected_department_id')
    
    if request.user.is_administrador():
        if selected_dept_id:
            base_queryset = Complaint.objects.filter(department_id=selected_dept_id)
        else:
            base_queryset = Complaint.objects.all()
    else:
        base_queryset = Complaint.objects.filter(department=request.user.department)

    stores = base_queryset.values('loja_cod').annotate(
        count=Count('id'),
        pendentes=Count('id', filter=Q(status='pendente')),
        em_andamento=Count('id', filter=Q(status='em_andamento')),
        resolvidas=Count('id', filter=Q(status='resolvido')),
        aguardando=Count('id', filter=Q(status='aguardando_avaliacao'))
    ).order_by('-count')
    
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="lojas_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Código da Loja', 'Total', 'Pendentes', 'Em Andamento', 'Aguardando Avaliação', 'Resolvidas'])
    
    for store in stores:
        writer.writerow([
            store['loja_cod'],
            store['count'],
            store['pendentes'],
            store['em_andamento'],
            store['aguardando'],
            store['resolvidas']
        ])
    
    return response

@login_required
def export_stores_xlsx(request):
    """Exportar resumo por loja para XLSX - apenas gestores"""
    if not (request.user.is_gestor() or request.user.is_administrador()):
        messages.error(request, 'Você não tem permissão para exportar dados.')
        return redirect('dashboard')
    
    # Filtro base por departamento
    selected_dept_id = request.session.get('selected_department_id')
    
    if request.user.is_administrador():
        if selected_dept_id:
            base_queryset = Complaint.objects.filter(department_id=selected_dept_id)
        else:
            base_queryset = Complaint.objects.all()
    else:
        base_queryset = Complaint.objects.filter(department=request.user.department)

    stores = base_queryset.values('loja_cod').annotate(
        count=Count('id'),
        pendentes=Count('id', filter=Q(status='pendente')),
        em_andamento=Count('id', filter=Q(status='em_andamento')),
        resolvidas=Count('id', filter=Q(status='resolvido')),
        aguardando=Count('id', filter=Q(status='aguardando_avaliacao'))
    ).order_by('-count')
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Lojas"
    
    headers = ['Código da Loja', 'Total', 'Pendentes', 'Em Andamento', 'Aguardando Avaliação', 'Resolvidas']
    
    header_fill = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num)
        cell.value = header
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center')
    
    for row_num, store in enumerate(stores, 2):
        ws.cell(row=row_num, column=1, value=store['loja_cod'])
        ws.cell(row=row_num, column=2, value=store['count'])
        ws.cell(row=row_num, column=3, value=store['pendentes'])
        ws.cell(row=row_num, column=4, value=store['em_andamento'])
        ws.cell(row=row_num, column=5, value=store['aguardando'])
        ws.cell(row=row_num, column=6, value=store['resolvidas'])
    
    column_widths = [20, 10, 12, 15, 20, 12]
    for col_num, width in enumerate(column_widths, 1):
        ws.column_dimensions[ws.cell(row=1, column=col_num).column_letter].width = width
    
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="lojas_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
    
    wb.save(response)
    return response

@login_required
def export_users_csv(request):
    """Exportar usuários para CSV - apenas gestores"""
    if not (request.user.is_gestor() or request.user.is_administrador()):
        messages.error(request, 'Você não tem permissão para exportar usuários.')
        return redirect('dashboard')
    
    # Filtro por departamento
    if request.user.is_administrador():
        users = User.objects.all().order_by('username')
    else:
        users = User.objects.filter(department=request.user.department).order_by('username')
    
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="usuarios_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Username', 'E-mail', 'Nome', 'Sobrenome', 'Perfil', 'Ativo', 'Último Login', 'Data de Criação'])
    
    for user in users:
        writer.writerow([
            user.username,
            user.email,
            user.first_name or '',
            user.last_name or '',
            user.get_role_display(),
            'Sim' if user.ativo else 'Não',
            user.last_login.strftime('%d/%m/%Y %H:%M') if user.last_login else '',
            user.date_joined.strftime('%d/%m/%Y %H:%M') if user.date_joined else ''
        ])
    
    return response

@login_required
def export_users_xlsx(request):
    """Exportar usuários para XLSX - apenas gestores e administradores"""
    if not (request.user.is_gestor() or request.user.is_administrador()):
        messages.error(request, 'Você não tem permissão para exportar usuários.')
        return redirect('dashboard')
    
    # Filtro por departamento
    if request.user.is_administrador():
        users = User.objects.all().order_by('username')
    else:
        users = User.objects.filter(department=request.user.department).order_by('username')
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Usuários"
    
    headers = ['Username', 'E-mail', 'Nome', 'Sobrenome', 'Perfil', 'Ativo', 'Último Login', 'Data de Criação']
    
    header_fill = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num)
        cell.value = header
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center')
    
    for row_num, user in enumerate(users, 2):
        ws.cell(row=row_num, column=1, value=user.username)
        ws.cell(row=row_num, column=2, value=user.email)
        ws.cell(row=row_num, column=3, value=user.first_name or '')
        ws.cell(row=row_num, column=4, value=user.last_name or '')
        ws.cell(row=row_num, column=5, value=user.get_role_display())
        ws.cell(row=row_num, column=6, value='Sim' if user.ativo else 'Não')
        ws.cell(row=row_num, column=7, value=user.last_login.strftime('%d/%m/%Y %H:%M') if user.last_login else '')
        ws.cell(row=row_num, column=8, value=user.date_joined.strftime('%d/%m/%Y %H:%M') if user.date_joined else '')
    
    column_widths = [20, 30, 20, 20, 15, 10, 20, 20]
    for col_num, width in enumerate(column_widths, 1):
        ws.column_dimensions[ws.cell(row=1, column=col_num).column_letter].width = width
    
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="usuarios_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
    
    wb.save(response)
    return response
