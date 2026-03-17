"""
APIs para o Módulo de RH - Gestão de Colaboradores
"""

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
import json
import logging

from ..models import (
    Colaborador, Cargo, Department, HistoricoProfissional, 
    PerformanceRH, User, DocumentoColaborador
)

logger = logging.getLogger(__name__)


def parse_decimal(value):
    """Auxiliar para converter valores decimais que podem vir com vírgula da UI"""
    if not value:
        return None
    try:
        # Resolve problema de locale: 3120,00 -> 3120.00
        if isinstance(value, str):
            value = value.replace('.', '').replace(',', '.')
        return float(value)
    except (ValueError, TypeError):
        return None

@login_required
@require_http_methods(["GET"])
def api_colaboradores_list(request):
    """Retorna listagem de colaboradores + usuários Nexus que ainda não têm ficha RH"""
    status_filter = request.GET.get('status', 'ativo')
    dept_filter = request.GET.get('department')

    colaboradores = Colaborador.objects.all()
    if status_filter != 'todos':
        colaboradores = colaboradores.filter(status=status_filter)
    if dept_filter:
        colaboradores = colaboradores.filter(department_id=dept_filter)

    data = []
    for c in colaboradores.select_related('department'):
        data.append({
            'tipo': 'colaborador',
            'id': str(c.id),
            'nome': c.nome_completo,
            'nome_completo': c.nome_completo,
            'cargo': c.cargo_atual,
            'cargo_atual': c.cargo_atual,
            'cpf': c.cpf or '',
            'department': c.department.name,
            'department_id': c.department_id,
            'status': c.status,
            'status_display': c.get_status_display(),
            'data_admissao': c.data_admissao.strftime('%d/%m/%Y'),
            'tempo_empresa': c.tempo_empresa,
            'foto_url': c.foto.url if c.foto else None
        })

    # Usuários do Nexus que ainda não têm ficha de colaborador (podem aparecer como cards para "Criar ficha")
    users_sem_ficha = User.objects.filter(ativo=True).filter(colaborador_perfil__isnull=True).select_related('department')
    if dept_filter:
        users_sem_ficha = users_sem_ficha.filter(department_id=dept_filter)

    usuarios_sem_ficha = []
    for u in users_sem_ficha:
        nome = (u.get_full_name() or u.username or '').strip() or u.username
        usuarios_sem_ficha.append({
            'tipo': 'usuario_sem_ficha',
            'user_id': str(u.id),
            'id': 'user_' + str(u.id),
            'nome': nome,
            'cargo': u.get_role_display() if hasattr(u, 'get_role_display') else 'Usuário Nexus',
            'department': u.department.name if u.department else '—',
            'department_id': str(u.department_id) if u.department_id else '',
            'username': u.username,
            'email': u.email or '',
            'foto_url': u.profile_photo.url if u.profile_photo else None
        })

    total_colab = Colaborador.objects.count()
    ativos_colab = Colaborador.objects.filter(status='ativo').count()

    return JsonResponse({
        'success': True,
        'colaboradores': data,
        'usuarios_sem_ficha': usuarios_sem_ficha,
        'stats': {'total': total_colab, 'ativos': ativos_colab}
    })


@login_required
@require_http_methods(["GET"])
def api_colaborador_detail(request, pk):
    """Retorna detalhes completos de um colaborador (Dossiê)"""
    colaborador = get_object_or_404(Colaborador.objects.select_related('department', 'user'), pk=pk)
    
    # Histórico Profissional
    historico = []
    for h in colaborador.historico.all():
        historico.append({
            'id': str(h.id),
            'data': h.data_evento.strftime('%d/%m/%Y'),
            'tipo': h.get_tipo_evento_display(),
            'cargo_anterior': h.cargo_anterior,
            'cargo_novo': h.cargo_novo,
            'salario_anterior': float(h.salario_anterior) if h.salario_anterior else None,
            'salario_novo': float(h.salario_novo) if h.salario_novo else None,
            'observacoes': h.observacoes
        })
        
    # Performance
    performance = []
    for p in colaborador.performance.all().select_related('avaliador'):
        performance.append({
            'id': str(p.id),
            'data': p.data_registro.strftime('%d/%m/%Y'),
            'tipo': p.get_tipo_display(),
            'titulo': p.titulo,
            'avaliador': p.avaliador.get_full_name() if p.avaliador else "Sistema",
            'comentarios': p.comentarios,
            'proximos_passos': p.proximos_passos,
            'nota': float(p.nota_quantitativa) if p.nota_quantitativa else None
        })
        
    # Documentos
    documentos = []
    for d in colaborador.documentos.all():
        documentos.append({
            'id': d.id,
            'nome': d.nome,
            'url': d.arquivo.url,
            'data': d.data_upload.strftime('%d/%m/%Y %H:%M'),
            'extensao': d.arquivo.name.split('.')[-1].lower() if '.' in d.arquivo.name else ''
        })
        
    return JsonResponse({
        'success': True,
        'colaborador': {
            'id': str(colaborador.id),
            'nome_completo': colaborador.nome_completo,
            'cpf': colaborador.cpf,
            'rg': colaborador.rg,
            'data_nascimento': colaborador.data_nascimento.strftime('%d/%m/%Y'),
            'endereco': colaborador.endereco,
            'telefone': colaborador.telefone,
            'email_pessoal': colaborador.email_pessoal,
            'data_admissao': colaborador.data_admissao.strftime('%d/%m/%Y'),
            'data_desligamento': colaborador.data_desligamento.strftime('%d/%m/%Y') if colaborador.data_desligamento else None,
            'cargo_atual': colaborador.cargo_atual,
            'department': colaborador.department.name,
            'department_id': str(colaborador.department.id),
            'salario_atual': float(colaborador.salario_atual),
            'tipo_contrato': colaborador.tipo_contrato,
            'jornada': colaborador.jornada_trabalho,
            'status': colaborador.status,
            'tempo_empresa': colaborador.tempo_empresa,
            'foto_url': colaborador.foto.url if colaborador.foto else None,
            'historico': historico,
            'performance': performance,
            'documentos': documentos
        }
    })


@login_required
@require_http_methods(["POST"])
def api_save_colaborador(request):
    """Cria ou atualiza um colaborador"""
    try:
        # Nota: multipart/form-data para fotos
        data = request.POST
        pk = data.get('id')
        
        with transaction.atomic():
            if pk:
                colaborador = get_object_or_404(Colaborador, pk=pk)
                created = False
            else:
                colaborador = Colaborador()
                created = True
                # Vincular a um usuário Nexus (opcional): RH pode criar ficha a partir do card "usuário sem ficha"
                user_id = data.get('user_id')
                if user_id:
                    try:
                        user = User.objects.get(pk=user_id)
                        colaborador.user = user
                    except User.DoesNotExist:
                        pass

            colaborador.nome_completo = data.get('nome_completo')
            colaborador.cpf = data.get('cpf')
            colaborador.rg = data.get('rg', '')
            colaborador.data_nascimento = data.get('data_nascimento')
            colaborador.data_admissao = data.get('data_admissao')
            colaborador.cargo_atual = data.get('cargo')
            colaborador.department_id = data.get('department_id')
            colaborador.salario_atual = parse_decimal(data.get('salario_atual'))
            colaborador.status = data.get('status', 'ativo')
            colaborador.tipo_contrato = data.get('tipo_contrato', 'clt')
            colaborador.email_pessoal = data.get('email_pessoal', '')
            colaborador.telefone = data.get('telefone', '')
            colaborador.endereco = data.get('endereco', '')
            
            if 'foto' in request.FILES:
                colaborador.foto = request.FILES['foto']
                
            colaborador.save()
            
            # Se for novo, criar histórico de admissão
            # Se for novo, criar histórico de admissão
            if created:
                cargo_cadastrado = data.get('cargo')
                cargo_inicial = data.get('cargo_inicial') or cargo_cadastrado
                data_admissao = data.get('data_admissao', timezone.now().date())
                
                HistoricoProfissional.objects.create(
                    colaborador=colaborador,
                    data_evento=data_admissao,
                    tipo_evento='admissao',
                    cargo_anterior=None,
                    cargo_novo=cargo_inicial,
                    salario_novo=colaborador.salario_atual,
                    observacoes="Registro inicial de admissão"
                )
                
                # Se o cargo atual for diferente do inicial, registramos a promoção/mudança imediata
                if cargo_inicial != cargo_cadastrado:
                    HistoricoProfissional.objects.create(
                        colaborador=colaborador,
                        data_evento=data_admissao,
                        tipo_evento='mudanca_funcao',
                        cargo_anterior=cargo_inicial,
                        cargo_novo=cargo_cadastrado,
                        salario_novo=colaborador.salario_atual,
                        observacoes="Cargo atual no momento do cadastro"
                    )
                
                # Se o cargo inicial for diferente do cargo atual cadastrado, 
                # significa que houve uma evolução não registrada ou o usuário quer 
                # que o cargo atual seja o que ele preencheu no campo 'Cargo'
                if cargo_inicial != cargo_cadastrado:
                    # O cargo_atual já foi salvo como 'cargo' do form. 
                    # Se o inicial for diferente, talvez devêssemos criar uma promoção?
                    # Por enquanto, apenas garantimos que a admissão use o 'cargo_inicial'.
                    pass
                
            return JsonResponse({'success': True, 'id': str(colaborador.id), 'message': 'Dados salvos com sucesso'})
            
    except Exception as e:
        logger.error(f"Erro ao salvar colaborador: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def api_rh_auxiliar_data(request):
    """Dados auxiliares para formulários (Cargos, Departamentos, Opções)"""
    cargos = list(Cargo.objects.all().values('id', 'nome', 'department__name'))
    for cargo in cargos:
        cargo['id'] = str(cargo['id'])
    depts = list(Department.objects.all().values('id', 'name'))
    for dept in depts:
        dept['id'] = str(dept['id'])
    
    return JsonResponse({
        'success': True,
        'cargos': cargos,
        'departments': depts,
        'status_choices': dict(Colaborador.STATUS_CHOICES),
        'tipo_contrato_choices': dict(Colaborador.TIPO_CONTRATO_CHOICES),
        'tipo_evento_choices': dict(HistoricoProfissional.TIPO_EVENTO_CHOICES),
        'tipo_performance_choices': dict(PerformanceRH.TIPO_CHOICES)
    })


@login_required
@require_http_methods(["POST"])
def api_save_historico(request):
    """Cria ou atualiza uma evolução no histórico do colaborador"""
    try:
        data = request.POST
        historico_id = data.get('id')
        colaborador_id = data.get('colaborador_id')
        colaborador = get_object_or_404(Colaborador, pk=colaborador_id)

        with transaction.atomic():
            if historico_id:
                h = get_object_or_404(HistoricoProfissional, pk=historico_id)
            else:
                h = HistoricoProfissional(colaborador=colaborador)

            h.data_evento = data.get('data_evento', timezone.now().date())
            h.tipo_evento = data.get('tipo_evento')
            h.cargo_anterior = data.get('cargo_anterior')
            h.cargo_novo = data.get('cargo_novo')
            h.salario_anterior = parse_decimal(data.get('salario_anterior'))
            h.salario_novo = parse_decimal(data.get('salario_novo'))
            h.observacoes = data.get('observacoes', '')
            h.save()

            # Atualizar dados atuais do colaborador se for a entrada mais recente
            # (Simplificado: se o cargo_novo foi preenchido, assume atualização do perfil)
            if data.get('cargo_novo'):
                colaborador.cargo_atual = data.get('cargo_novo')
            if data.get('salario_novo'):
                colaborador.salario_atual = parse_decimal(data.get('salario_novo'))
            
            colaborador.save()

        return JsonResponse({'success': True, 'message': 'Histórico salvo com sucesso'})
    except Exception as e:
        logger.error(f"Erro ao salvar historico: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def api_delete_historico(request, pk):
    """Exclui uma entrada específica do histórico"""
    try:
        h = get_object_or_404(HistoricoProfissional, pk=pk)
        h.delete()
        return JsonResponse({'success': True, 'message': 'Histórico removido com sucesso'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def api_delete_colaborador(request, pk):
    """Exclui um colaborador e seus dados relacionados"""
    try:
        colaborador = get_object_or_404(Colaborador, pk=pk)
        colaborador.delete()
        return JsonResponse({'success': True, 'message': 'Colaborador excluído com sucesso'})
    except Exception as e:
        logger.error(f"Erro ao excluir colaborador: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def api_save_performance(request):
    """Registra um novo feedback/performance para o colaborador"""
    try:
        data = request.POST
        colaborador_id = data.get('colaborador_id')
        colaborador = get_object_or_404(Colaborador, pk=colaborador_id)

        PerformanceRH.objects.create(
            colaborador=colaborador,
            avaliador=request.user,
            data_registro=data.get('data_registro', timezone.now().date()),
            tipo=data.get('tipo'),
            titulo=data.get('titulo'),
            comentarios=data.get('comentarios'),
            proximos_passos=data.get('proximos_passos', ''),
            nota_quantitativa=data.get('nota') or None
        )

        return JsonResponse({'success': True, 'message': 'Feedback registrado com sucesso'})
    except Exception as e:
        logger.error(f"Erro ao salvar performance: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def api_upload_documento(request):
    """Realiza upload de um novo documento para o colaborador"""
    try:
        colaborador_id = request.POST.get('colaborador_id')
        colaborador = get_object_or_404(Colaborador, pk=colaborador_id)
        
        if 'arquivo' not in request.FILES:
            return JsonResponse({'success': False, 'error': 'Nenhum arquivo enviado'}, status=400)
            
        arquivo = request.FILES['arquivo']
        nome = request.POST.get('nome', arquivo.name)
        
        DocumentoColaborador.objects.create(
            colaborador=colaborador,
            nome=nome,
            arquivo=arquivo,
            uploaded_by=request.user
        )
        
        return JsonResponse({'success': True, 'message': 'Documento enviado com sucesso'})
    except Exception as e:
        logger.error(f"Erro ao upload documento: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def api_delete_documento(request, pk):
    """Remove um documento do colaborador"""
    try:
        doc = get_object_or_404(DocumentoColaborador, pk=pk)
        doc.delete()
        return JsonResponse({'success': True, 'message': 'Documento removido com sucesso'})
    except Exception as e:
        logger.error(f"Erro ao deletar documento: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
