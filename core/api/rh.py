"""
APIs para o Módulo de RH - Gestão de Colaboradores
"""

from django.http import JsonResponse, Http404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from django.core.cache import cache
import json
import logging
import calendar
from datetime import datetime, timedelta, date
from ..models import (
    Colaborador, Department, HistoricoProfissional, 
    PerformanceRH, User, DocumentoColaborador,    Empresa, Cargo, CentroCusto, Holiday, Turno, 
    JustificativaPonto, EscalaMensal, Horario, HorarioDetalhe, RegistroPonto, VisualColunaApuracao,
    TipoInconsistencia, LancamentoJustificativa
)

logger = logging.getLogger(__name__)


def parse_decimal(value):
    """Auxiliar para converter valores decimais que podem vir com vírgula da UI"""
    if not value or str(value).strip() == '':
        return None
    try:
        if isinstance(value, str):
            value = value.strip()
            if '.' in value and ',' not in value:
                pass
            elif ',' in value and '.' not in value:
                value = value.replace(',', '.')
            elif '.' in value and ',' in value:
                value = value.replace('.', '').replace(',', '.')
        return float(value)
    except (ValueError, TypeError):
        return None

def time_to_min(t):
    if not t: return 0
    if isinstance(t, str):
        try:
            parts = t.split(':')
            return int(parts[0]) * 60 + int(parts[1])
        except: return 0
    return t.hour * 60 + t.minute

def min_to_str(m):
    if m <= 0: return ""
    h = int(m // 60)
    mi = int(m % 60)
    return f"{h:02d}:{mi:02d}"

def get_intersection(r1_start, r1_end, r2_start, r2_end):
    """Retorna o total de minutos de interseção entre dois intervalos [start, end]"""
    s = max(r1_start, r2_start)
    e = min(r1_end, r2_end)
    return max(0, e - s)

def get_interval_intersections(intervals1, intervals2):
    """
    Soma a interseção de múltiplos intervalos.
    intervals: lista de tuplas (start_min, end_min)
    """
    total = 0
    for s1, e1 in intervals1:
        for s2, e2 in intervals2:
            total += get_intersection(s1, e1, s2, e2)
    return total

def split_night_shift(start_min, end_min, night_start=1320, night_end=300):
    """
    Divide um intervalo em diurno e noturno (padrão 22h-05h).
    Retorna (diurno_min, noturno_min)
    """
    # Período noturno: [1320, 1440] e [0, 300]
    # Se o intervalo cruza meia-noite (end < start), tratamos como dois intervalos
    intervals = []
    if end_min < start_min:
        intervals.append((start_min, 1440))
        intervals.append((0, end_min))
    else:
        intervals.append((start_min, end_min))
    
    total_min = sum(e - s for s, e in intervals)
    
    night_intervals = [(night_start, 1440), (0, night_end)]
    noturno_min = get_interval_intersections(intervals, night_intervals)
    diurno_min = total_min - noturno_min
    
    return diurno_min, noturno_min

@login_required
@require_http_methods(["GET"])
def api_colaboradores_list(request):
    """Retorna listagem de colaboradores + usuários Nexus que ainda não têm ficha RH"""
    if not (request.user.is_gestor() or request.user.is_administrador() or getattr(request.user.department, 'name', '') == 'RH'):
        return JsonResponse({'erro': 'Acesso negado'}, status=403)
        
    status_filter = request.GET.get('status', 'ativo')
    dept_filter = request.GET.get('department')
    empresa_filter = request.GET.get('empresa')
    cargo_filter = request.GET.get('cargo')
    centro_filter = request.GET.get('centro_custo')

    colaboradores = Colaborador.objects.all()
    if status_filter != 'todos':
        colaboradores = colaboradores.filter(status=status_filter)
    if dept_filter:
        colaboradores = colaboradores.filter(department_id=dept_filter)
    if empresa_filter:
        colaboradores = colaboradores.filter(empresa_id=empresa_filter)
    if cargo_filter:
        colaboradores = colaboradores.filter(cargo_atual=cargo_filter)
    if centro_filter:
        colaboradores = colaboradores.filter(centro_custo_id=centro_filter)

    data = []
    for c in colaboradores.select_related('department', 'empresa', 'centro_custo'):
        data.append({
            'tipo': 'colaborador',
            'id': str(c.id),
            'nome': c.nome_completo,
            'nome_completo': c.nome_completo,
            'cargo': c.cargo_atual,
            'cargo_atual': c.cargo_atual,
            'cpf': c.cpf or '',
            'department': c.department.name if c.department else '—',
            'department_id': c.department_id,
            'empresa': c.empresa.nome if c.empresa else '—',
            'empresa_id': c.empresa_id,
            'centro_custo': c.centro_custo.nome if c.centro_custo else '—',
            'centro_custo_id': c.centro_custo_id,
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
    if not (request.user.is_gestor() or request.user.is_administrador() or getattr(request.user.department, 'name', '') == 'RH'):
        return JsonResponse({'erro': 'Acesso negado'}, status=403)
        
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
            'data_nascimento': colaborador.data_nascimento.strftime('%d/%m/%Y') if colaborador.data_nascimento else None,
            'endereco': colaborador.endereco,
            'telefone': colaborador.telefone,
            'email_pessoal': colaborador.email_pessoal,
            'data_admissao': colaborador.data_admissao.strftime('%d/%m/%Y') if colaborador.data_admissao else None,
            'data_desligamento': colaborador.data_desligamento.strftime('%d/%m/%Y') if colaborador.data_desligamento else None,
            'cargo_atual': colaborador.cargo_atual,
            'department': colaborador.department.name if colaborador.department else '',
            'department_id': str(colaborador.department.id) if colaborador.department_id else '',
            'empresa_id': str(colaborador.empresa_id) if colaborador.empresa_id else '',
            'empresa': colaborador.empresa.nome if colaborador.empresa else '',
            'salario_atual': float(colaborador.salario_atual),
            'tipo_contrato': colaborador.tipo_contrato,
            'jornada': colaborador.jornada_trabalho,
            'horario_padrao_id': str(colaborador.horario_padrao_id) if colaborador.horario_padrao_id else '',
            'horario_padrao_nome': colaborador.horario_padrao.nome if colaborador.horario_padrao else '',
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
        if pk:
            pk = str(pk).replace('.', '').replace(',', '')  # Failsafe for localized IDs
        
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
            dn = data.get('data_nascimento', '')
            colaborador.data_nascimento = dn if dn else None
            colaborador.data_admissao = data.get('data_admissao')
            colaborador.cargo_atual = data.get('cargo')
            colaborador.cargo_inicial = data.get('cargo_inicial', '')
            colaborador.department_id = data.get('department_id')
            centro_custo_id = data.get('centro_custo') or None
            colaborador.centro_custo_id = centro_custo_id if centro_custo_id else None
            empresa_id = data.get('empresa_id') or None
            colaborador.empresa_id = empresa_id if empresa_id else None
            colaborador.salario_atual = parse_decimal(data.get('salario_atual'))
            colaborador.status = data.get('status', 'ativo')
            colaborador.tipo_contrato = data.get('tipo_contrato', 'clt')
            colaborador.email_pessoal = data.get('email_pessoal', '')
            colaborador.telefone = data.get('telefone', '')
            colaborador.ramal = data.get('ramal', '')
            colaborador.endereco = data.get('endereco', '')
            colaborador.cep = data.get('cep', '')
            colaborador.bairro = data.get('bairro', '')
            colaborador.cidade = data.get('cidade', '')
            colaborador.uf = data.get('uf', '')
            colaborador.nome_pai = data.get('nome_pai', '')
            colaborador.nome_mae = data.get('nome_mae', '')
            colaborador.genero = data.get('genero', '')
            colaborador.jornada_trabalho = data.get('jornada_trabalho', '')
            colaborador.horario_padrao_id = data.get('horario_padrao_id') or None
            colaborador.pis = data.get('pis', '')
            colaborador.matricula = data.get('matricula', '')
            colaborador.numero_folha = data.get('numero_folha', '')
            colaborador.ctps = data.get('ctps', '')
            sup_id = data.get('superior_direto_id')
            colaborador.superior_direto_id = sup_id if sup_id else None
            dd = data.get('data_desligamento', '')
            colaborador.data_desligamento = dd if dd else None
            # Identificação Web
            colaborador.email_acesso = data.get('email_acesso', '')
            colaborador.ponto_web_permitido = data.get('ponto_web_permitido') == 'on'
            colaborador.ponto_web_foto = data.get('ponto_web_foto') == 'on'
            colaborador.ponto_web_inserir = data.get('ponto_web_inserir') == 'on'
            colaborador.ponto_web_justificativa = data.get('ponto_web_justificativa') == 'on'
            
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
            
    except Http404:
        return JsonResponse({'success': False, 'error': 'Colaborador não encontrado.'}, status=404)
    except Exception as e:
        logger.error(f"Erro ao salvar colaborador: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def api_rh_auxiliar_data(request):
    """Retorna dados para combos e listas auxiliares do RH"""
    cargos = list(Cargo.objects.all().values('id', 'nome', 'department_id'))
    for cargo in cargos:
        cargo['id'] = str(cargo['id'])
        cargo['department_id'] = str(cargo['department_id'])
    
    centros = list(CentroCusto.objects.all().values('id', 'nome'))
    for c in centros:
        c['id'] = str(c['id'])
    
    depts = list(Department.objects.all().values('id', 'name'))
    for dept in depts:
        dept['id'] = str(dept['id'])
    
    empresas = list(Empresa.objects.all().values('id', 'nome', 'nome_fantasia'))
    for e in empresas:
        e['id'] = str(e['id'])
        
    turnos = list(Turno.objects.all().values('id', 'nome', 'horario'))
    for t in turnos:
        t['id'] = str(t['id'])

    justificativas = list(JustificativaPonto.objects.all().values('id', 'nome'))
    for j in justificativas:
        j['id'] = str(j['id'])

    colabs = list(Colaborador.objects.filter(status='ativo').values('id', 'nome_completo'))
    for c in colabs:
        c['id'] = str(c['id'])
        
    horarios = list(Horario.objects.all().values('id', 'nome', 'tipo'))
    for h in horarios:
        h['id'] = str(h['id'])

    response_data = {
        'success': True,
        'cargos': cargos,
        'departments': depts,
        'centros_custo': centros,
        'empresas': empresas,
        'turnos': turnos,
        'horarios': horarios,
        'justificativas': justificativas,
        'colaboradores': colabs,
        'status_choices': dict(Colaborador.STATUS_CHOICES),
        'tipo_contrato_choices': dict(Colaborador.TIPO_CONTRATO_CHOICES),
        'tipo_evento_choices': dict(HistoricoProfissional.TIPO_EVENTO_CHOICES),
        'tipo_performance_choices': dict(PerformanceRH.TIPO_CHOICES),
        'tipo_horario_choices': dict(Horario.TIPO_CHOICES)
    }
        
    return JsonResponse(response_data)


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


# ─────────────────────────────────────────────
#  EMPRESAS
# ─────────────────────────────────────────────

@login_required
@require_http_methods(["GET"])
def api_empresas_list(request):
    """Lista todas as empresas"""
    try:
        empresas = Empresa.objects.all()
        return JsonResponse({'success': True, 'empresas': [
            {
                'id': str(e.id),  # string to avoid JS precision loss on large CockroachDB IDs
                'nome': e.nome,
                'nome_fantasia': e.nome_fantasia,
                'cnpj': e.cnpj,
                'num_funcionarios': e.num_funcionarios,
                'logo_url': e.logo.url if e.logo else None,
            } for e in empresas
        ]})
    except Exception as ex:
        return JsonResponse({'success': False, 'error': str(ex)}, status=500)


@login_required
@require_http_methods(["POST"])
def api_save_empresa(request):
    """Cria ou atualiza uma empresa"""
    try:
        data = request.POST
        pk = data.get('id')
        if pk:
            pk = str(pk).replace('.', '').replace(',', '')  # Failsafe for localized IDs
        with transaction.atomic():
            if pk:
                empresa = get_object_or_404(Empresa, pk=pk)
            else:
                empresa = Empresa()

            empresa.nome = data.get('nome', '')
            empresa.nome_fantasia = data.get('nome_fantasia', '')
            empresa.cnpj = data.get('cnpj', '')
            empresa.cei = data.get('cei', '')
            empresa.cep = data.get('cep', '')
            empresa.endereco = data.get('endereco', '')
            empresa.bairro = data.get('bairro', '')
            empresa.cidade = data.get('cidade', '')
            empresa.uf = data.get('uf', '')
            empresa.numero_folha = data.get('numero_folha', '')
            empresa.inscricao_estadual = data.get('inscricao_estadual', '')
            empresa.fluxo_aprovacao = data.get('fluxo_aprovacao', '')
            empresa.responsavel_cpf = data.get('responsavel_cpf', '')
            empresa.responsavel_nome = data.get('responsavel_nome', '')
            empresa.responsavel_cargo = data.get('responsavel_cargo', '')
            empresa.responsavel_email = data.get('responsavel_email', '')

            if data.get('logo_delete') == '1':
                empresa.logo = None
            elif 'logo' in request.FILES:
                empresa.logo = request.FILES['logo']

            empresa.save()

        return JsonResponse({'success': True, 'message': 'Empresa salva com sucesso.', 'id': str(empresa.id)})
    except Http404:
        return JsonResponse({'success': False, 'error': 'Empresa não encontrada.'}, status=404)
    except Exception as ex:
        logger.error(f"Erro ao salvar empresa: {ex}")
        return JsonResponse({'success': False, 'error': str(ex)}, status=500)


@login_required
@require_http_methods(["DELETE"])
def api_delete_empresa(request, pk):
    """Exclui uma empresa"""
    try:
        empresa = get_object_or_404(Empresa, pk=pk)
        empresa.delete()
        return JsonResponse({'success': True, 'message': 'Empresa excluída com sucesso.'})
    except Http404:
        return JsonResponse({'success': False, 'error': 'Empresa não encontrada.'}, status=404)
    except Exception as ex:
        logger.error(f"Erro ao excluir empresa: {ex}")
        return JsonResponse({'success': False, 'error': str(ex)}, status=500)

# ─────────────────────────────────────────────
#  DEPARTAMENTOS
# ─────────────────────────────────────────────

@login_required
@require_http_methods(["GET"])
def api_departamentos_list(request):
    """Lista todos os departamentos com contagem de funcionários"""
    try:
        from django.db.models import Count
        depts = Department.objects.annotate(num_funcionarios=Count('colaboradores_rh'))
        return JsonResponse({'success': True, 'departamentos': [
            {
                'id': str(d.id),
                'name': d.name,
                'description': d.description,
                'fluxo_aprovacao': d.fluxo_aprovacao,
                'show_in_nav': d.show_in_nav,
                'num_funcionarios': d.num_funcionarios,
            } for d in depts
        ]})
    except Exception as ex:
        return JsonResponse({'success': False, 'error': str(ex)}, status=500)


@login_required
@require_http_methods(["POST"])
def api_save_departamento(request):
    """Cria ou atualiza um departamento"""
    try:
        data = json.loads(request.body)
        pk = data.get('id')
        
        with transaction.atomic():
            if pk:
                dept = get_object_or_404(Department, pk=pk)
            else:
                dept = Department()
            
            dept.name = data.get('name', '')
            dept.description = data.get('description', '')
            dept.fluxo_aprovacao = data.get('fluxo_aprovacao', '')
            dept.show_in_nav = data.get('show_in_nav', False)
            
            # Gerar slug se for novo
            if not pk:
                from django.utils.text import slugify
                dept.slug = slugify(dept.name)
                # Garantir unicidade
                base_slug = dept.slug
                counter = 1
                while Department.objects.filter(slug=dept.slug).exists():
                    dept.slug = f"{base_slug}-{counter}"
                    counter += 1
            
            dept.save()

        return JsonResponse({'success': True, 'message': 'Departamento salvo com sucesso.', 'id': str(dept.id)})
    except Exception as ex:
        logger.error(f"Erro ao salvar departamento: {ex}")
        return JsonResponse({'success': False, 'error': str(ex)}, status=500)


@login_required
@require_http_methods(["DELETE"])
def api_delete_departamento(request, pk):
    """Exclui um departamento"""
    try:
        dept = get_object_or_404(Department, pk=pk)
        # Verificar se existem colaboradores vinculados
        if dept.colaboradores_rh.exists():
            return JsonResponse({'success': False, 'error': 'Não é possível excluir um departamento que possui colaboradores.'}, status=400)
        
        dept.delete()
        return JsonResponse({'success': True, 'message': 'Departamento excluído com sucesso.'})
    except Exception as ex:
        logger.error(f"Erro ao excluir departamento: {ex}")
        return JsonResponse({'success': False, 'error': str(ex)}, status=500)


# ─────────────────────────────────────────────
#  CARGOS
# ─────────────────────────────────────────────

@login_required
@require_http_methods(["GET"])
def api_cargos_list(request):
    """Lista todos os cargos com contagem de funcionários"""
    try:
        cargos = Cargo.objects.all().select_related('department')
        data = []
        for c in cargos:
            # Contagem baseada no nome do cargo no modelo Colaborador
            count = Colaborador.objects.filter(cargo_atual=c.nome).count()
            data.append({
                'id': str(c.id),
                'nome': c.nome,
                'department_id': str(c.department_id),
                'department_name': c.department.name if c.department else '—',
                'descricao': c.descricao,
                'count_colaboradores': count
            })
        return JsonResponse({'success': True, 'cargos': data})
    except Exception as ex:
        return JsonResponse({'success': False, 'error': str(ex)}, status=500)


@login_required
@require_http_methods(["POST"])
def api_save_cargo(request):
    """Cria ou atualiza um cargo"""
    try:
        data = json.loads(request.body)
        pk = data.get('id')
        
        with transaction.atomic():
            if pk:
                cargo = get_object_or_404(Cargo, pk=pk)
            else:
                cargo = Cargo()
            
            cargo.nome = data.get('nome', '')
            cargo.department_id = data.get('department_id')
            cargo.descricao = data.get('descricao', '')
            cargo.save()

        return JsonResponse({'success': True, 'message': 'Cargo salvo com sucesso.', 'id': str(cargo.id)})
    except Exception as ex:
        logger.error(f"Erro ao salvar cargo: {ex}")
        return JsonResponse({'success': False, 'error': str(ex)}, status=500)


@login_required
@require_http_methods(["DELETE"])
def api_delete_cargo(request, pk):
    """Exclui um cargo"""
    try:
        cargo = get_object_or_404(Cargo, pk=pk)
        cargo.delete()
        return JsonResponse({'success': True, 'message': 'Cargo excluído com sucesso.'})
    except Exception as ex:
        logger.error(f"Erro ao excluir cargo: {ex}")
        return JsonResponse({'success': False, 'error': str(ex)}, status=500)

# ─────────────────────────────────────────────
#  CENTROS DE CUSTO
# ─────────────────────────────────────────────

@login_required
@require_http_methods(["GET"])
def api_centros_custo_list(request):
    """Lista todos os centros de custo com contagem de funcionários"""
    try:
        from django.db.models import Count
        centros = CentroCusto.objects.annotate(num_funcionarios=Count('colaboradores'))
        return JsonResponse({'success': True, 'centros': [
            {
                'id': str(c.id),
                'nome': c.nome,
                'num_funcionarios': c.num_funcionarios,
            } for c in centros
        ]})
    except Exception as ex:
        return JsonResponse({'success': False, 'error': str(ex)}, status=500)


@login_required
@require_http_methods(["POST"])
def api_save_centro_custo(request):
    """Cria ou atualiza um centro de custo"""
    try:
        data = json.loads(request.body)
        pk = data.get('id')
        
        if pk:
            centro = get_object_or_404(CentroCusto, pk=pk)
        else:
            centro = CentroCusto()
        
        centro.nome = data.get('nome', '')
        centro.save()
        
        return JsonResponse({'success': True, 'message': 'Centro de custo salvo com sucesso.', 'id': str(centro.id)})
    except Exception as ex:
        return JsonResponse({'success': False, 'error': str(ex)}, status=500)


@login_required
@require_http_methods(["DELETE"])
def api_delete_centro_custo(request, pk):
    """Exclui um centro de custo"""
    try:
        centro = get_object_or_404(CentroCusto, pk=pk)
        centro.delete()
        return JsonResponse({'success': True, 'message': 'Centro de custo excluído com sucesso.'})
    except Exception as ex:
        return JsonResponse({'success': False, 'error': str(ex)}, status=500)


# ─────────────────────────────────────────────
#  HORÁRIOS
# ─────────────────────────────────────────────

@login_required
@require_http_methods(["GET"])
def api_rh_horarios_list(request):
    """Lista todos os horários cadastrados"""
    try:
        horarios = Horario.objects.all()
        data = []
        for h in horarios:
            # Resumo do horário
            detalhes = h.detalhes.all()
            resumo = ""
            if h.tipo == 'semanal':
                # Ex: Seg Ter Qua Qui Sex: 08:00-12:00 13:00-17:00
                days_short = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]
                schedule_groups = {} # schedule_str -> list of day_indices
                
                detalhes = h.detalhes.all().order_by('dia_index')
                for d in detalhes:
                    if d.neutro:
                        s_str = "Folga"
                    elif d.compensado:
                        s_str = "Comp."
                    else:
                        parts = []
                        if d.entrada_1 and d.saida_1:
                            parts.append(f"{d.entrada_1.strftime('%H:%M')}-{d.saida_1.strftime('%H:%M')}")
                        if d.entrada_2 and d.saida_2:
                            parts.append(f"{d.entrada_2.strftime('%H:%M')}-{d.saida_2.strftime('%H:%M')}")
                        s_str = " ".join(parts) if parts else "---"
                    
                    if s_str not in schedule_groups:
                        schedule_groups[s_str] = []
                    schedule_groups[s_str].append(d.dia_index)
                
                summary_parts = []
                # Para manter a ordem dos dias, ordenamos os grupos pelo menor índice de dia
                sorted_groups = sorted(schedule_groups.items(), key=lambda x: min(x[1]))
                
                for s_str, indices in sorted_groups:
                    if s_str in ["---", "Folga"] and len(sorted_groups) > 1:
                        continue # Pula folgas se houver horários úteis (para encurtar)
                    
                    indices.sort()
                    days_str = ", ".join([days_short[i] for i in indices])
                    summary_parts.append(f"{days_str}: {s_str}")
                
                resumo = " | ".join(summary_parts)
                if not resumo: # Caso só tenha folga
                    resumo = "Folga"
            elif h.tipo == 'ciclico':
                resumo = f"Ciclo de {h.dias_ciclo} dias"
            else:
                resumo = "Jornada Móvel"
            
            data.append({
                'id': str(h.id),
                'nome': h.nome,
                'tipo': h.tipo,
                'tipo_display': h.get_tipo_display(),
                'cor': h.cor,
                'sigla': h.sigla,
                'resumo': resumo
            })
        return JsonResponse({'success': True, 'horarios': data})
    except Exception as ex:
        return JsonResponse({'success': False, 'error': str(ex)}, status=500)


@login_required
@require_http_methods(["GET"])
def api_rh_horario_detail(request, pk):
    """Retorna detalhes completos de um horário específico"""
    try:
        h = get_object_or_404(Horario, pk=pk)
        detalhes = []
        for d in h.detalhes.all():
            detalhes.append({
                'id': d.id,
                'dia_index': d.dia_index,
                'nome_dia': d.nome_dia,
                'entrada_1': d.entrada_1.strftime('%H:%M') if d.entrada_1 else '',
                'saida_1': d.saida_1.strftime('%H:%M') if d.saida_1 else '',
                'entrada_2': d.entrada_2.strftime('%H:%M') if d.entrada_2 else '',
                'saida_2': d.saida_2.strftime('%H:%M') if d.saida_2 else '',
                'total_horas': d.total_horas,
                'almoco_livre': d.almoco_livre,
                'compensado': d.compensado,
                'neutro': d.neutro,
                'fechamento_noturno': d.fechamento_noturno.strftime('%H:%M') if d.fechamento_noturno else '00:00'
            })
            
        return JsonResponse({
            'success': True,
            'horario': {
                'id': str(h.id),
                'nome': h.nome,
                'tipo': h.tipo,
                'sigla': h.sigla,
                'cor': h.cor,
                'data_inicio': h.data_inicio.strftime('%Y-%m-%d') if h.data_inicio else '',
                'dias_ciclo': h.dias_ciclo,
                'folga_nos_intervalos': h.folga_nos_intervalos,
                'tol_entrada': h.tol_entrada,
                'tol_saida': h.tol_saida,
                'tol_intervalo': h.tol_intervalo,
                'tol_diaria': h.tol_diaria,
                'dia_dsr': h.dia_dsr,
                'minimo_horas_dsr': float(h.minimo_horas_dsr),
                'descontar_faltas_dsr': h.descontar_faltas_dsr,
                'utiliza_banco_horas': h.utiliza_banco_horas,
                'modo_extra': h.modo_extra,
                'percentual_diurno': float(h.percentual_diurno),
                'percentual_noturno': float(h.percentual_noturno),
                
                # Modo Simples Detalhado
                'perc_extra_dia_diurno': float(h.perc_extra_dia_diurno),
                'perc_extra_dia_noturno': float(h.perc_extra_dia_noturno),
                'perc_extra_sab_diurno': float(h.perc_extra_sab_diurno),
                'perc_extra_sab_noturno': float(h.perc_extra_sab_noturno),
                'perc_extra_dom_diurno': float(h.perc_extra_dom_diurno),
                'perc_extra_dom_noturno': float(h.perc_extra_dom_noturno),
                'perc_extra_feriado_diurno': float(h.perc_extra_feriado_diurno),
                'perc_extra_feriado_noturno': float(h.perc_extra_feriado_noturno),
                
                # Modo Avançado
                'politicas_avancadas': [
                    {
                        'id': p.id,
                        'seq': p.seq,
                        'dias': p.dias,
                        'feriado': p.feriado,
                        'noturno': p.noturno,
                        'intervalo': p.intervalo,
                        'dia_especifico': p.dia_especifico,
                        'acumulo': p.acumulo,
                        'eventos': p.eventos,
                        'faixas': [
                            {
                                'de_horas': float(f.de_horas),
                                'ate_horas': float(f.ate_horas),
                                'acrescimo_percentual': float(f.acrescimo_percentual),
                                'banco_horas': f.banco_horas,
                                'codigo_evento': f.codigo_evento,
                                'codigo_evento_acrescimo': f.codigo_evento_acrescimo
                            } for f in p.faixas.all()
                        ]
                    } for p in h.politicas_hora_extra.all()
                ],
                'inicio_noturno': h.inicio_noturno.strftime('%H:%M'),
                'fim_noturno': h.fim_noturno.strftime('%H:%M'),
                'fator_noturno': h.fator_noturno,
                'fechamento_noturno_global': h.fechamento_noturno_global.strftime('%H:%M'),
                'pre_assinalar': h.pre_assinalar,
                'modo_compensacao': h.modo_compensacao,
                'inicio_mes': h.inicio_mes,
                'refeicao_tipo': h.refeicao_tipo,
                'quando_feriado': h.quando_feriado,
                'quando_domingo': h.quando_domingo,
                'considera_extra_antes': h.considera_extra_antes,
                'considera_extra_depois': h.considera_extra_depois,
                'considera_extra_intervalo': h.considera_extra_intervalo,
                'considera_extra_intervalo_curto': h.considera_extra_intervalo_curto,
                'considera_atraso_inicio': h.considera_atraso_inicio,
                'considera_atraso_fim': h.considera_atraso_fim,
                'considera_atraso_intervalo': h.considera_atraso_intervalo,
                
                # Novos campos - Tolerâncias
                'tol_clt': h.tol_clt,
                'tol_extra_batida': h.tol_extra_batida,
                'tol_falta_batida': h.tol_falta_batida,
                'limite_extra_diario': h.limite_extra_diario,
                'limite_falta_diario': h.limite_falta_diario,
                'descontar_tol_faltas': h.descontar_tol_faltas,
                'descontar_tol_extras': h.descontar_tol_extras,
                'quando_limite_extra': h.quando_limite_extra,
                'quando_limite_falta': h.quando_limite_falta,
                
                # Novos campos - DSR
                'primeiro_dia_semana': h.primeiro_dia_semana,
                'tempo_dsr': h.tempo_dsr,
                'max_faltas_dsr': h.max_faltas_dsr,
                'desconto_dsr_feriado': h.desconto_dsr_feriado,
                
                # Aba Avançada
                'desconto_faltas_extras': h.desconto_faltas_extras,
                'modo_neutro': h.modo_neutro,
                'calculo_extra_interjornada': h.calculo_extra_interjornada,
                'perc_extra_interjornada': float(h.perc_extra_interjornada) if h.perc_extra_interjornada is not None else 50.0,
                'folgas_semana': h.folgas_semana,
                
                'detalhes': detalhes
            }
        })
    except Exception as ex:
        return JsonResponse({'success': False, 'error': str(ex)}, status=500)


@login_required
@require_http_methods(["POST"])
def api_save_horario(request):
    """Salva ou atualiza um horário e seus detalhes"""
    try:
        data = json.loads(request.body)
        pk = data.get('id')
        
        with transaction.atomic():
            if pk:
                h = get_object_or_404(Horario, pk=pk)
            else:
                h = Horario()
            
            h.nome = data.get('nome')
            h.tipo = data.get('tipo', 'semanal')
            h.sigla = data.get('sigla')
            h.cor = data.get('cor', '#2563eb')
            
            di = data.get('data_inicio')
            h.data_inicio = di if di else None
            h.dias_ciclo = data.get('dias_ciclo')
            
            h.folga_nos_intervalos = data.get('folga_nos_intervalos', False)
            h.tol_entrada = data.get('tol_entrada', 5)
            h.tol_saida = data.get('tol_saida', 5)
            h.tol_intervalo = data.get('tol_intervalo', 5)
            h.tol_diaria = data.get('tol_diaria', 10)
            
            h.dia_dsr = data.get('dia_dsr', 6)
            h.minimo_horas_dsr = data.get('minimo_horas_dsr', 0)
            h.descontar_faltas_dsr = data.get('descontar_faltas_dsr', True)
            
            h.utiliza_banco_horas = data.get('utiliza_banco_horas', False)
            h.modo_extra = data.get('modo_extra', 'simples')
            h.percentual_diurno = data.get('percentual_diurno', 50)
            h.percentual_noturno = data.get('percentual_noturno', 50)
            
            # Modo Simples Detalhado
            h.perc_extra_dia_diurno = data.get('perc_extra_dia_diurno', 50)
            h.perc_extra_dia_noturno = data.get('perc_extra_dia_noturno', 50)
            h.perc_extra_sab_diurno = data.get('perc_extra_sab_diurno', 100)
            h.perc_extra_sab_noturno = data.get('perc_extra_sab_noturno', 100)
            h.perc_extra_dom_diurno = data.get('perc_extra_dom_diurno', 100)
            h.perc_extra_dom_noturno = data.get('perc_extra_dom_noturno', 100)
            h.perc_extra_feriado_diurno = data.get('perc_extra_feriado_diurno', 100)
            h.perc_extra_feriado_noturno = data.get('perc_extra_feriado_noturno', 100)
            
            h.inicio_noturno = data.get('inicio_noturno', '22:00')
            h.fim_noturno = data.get('fim_noturno', '05:00')
            h.fator_noturno = data.get('fator_noturno', 60)
            h.fechamento_noturno_global = data.get('fechamento_noturno_global', '00:00')
            
            # Novos campos Parâmetros Básicos
            h.pre_assinalar = data.get('pre_assinalar', 'sem_marcacao')
            h.modo_compensacao = data.get('modo_compensacao', 'sem_compensacao')
            h.inicio_mes = data.get('inicio_mes', 1)
            h.refeicao_tipo = data.get('refeicao_tipo', 's1_e2')
            h.quando_feriado = data.get('quando_feriado', 'extra')
            h.quando_domingo = data.get('quando_domingo', 'extra')
            h.considera_extra_antes = data.get('considera_extra_antes', 'considera')
            h.considera_extra_depois = data.get('considera_extra_depois', 'considera')
            h.considera_extra_intervalo = data.get('considera_extra_intervalo', 'considera')
            h.considera_extra_intervalo_curto = data.get('considera_extra_intervalo_curto', 'minutos_trabalhados')
            h.considera_atraso_inicio = data.get('considera_atraso_inicio', 'considera')
            h.considera_atraso_fim = data.get('considera_atraso_fim', 'considera')
            h.considera_atraso_intervalo = data.get('considera_atraso_intervalo', 'considera')
            
            # Novos campos - Tolerâncias
            h.tol_clt = data.get('tol_clt', True)
            h.tol_extra_batida = data.get('tol_extra_batida', 5)
            h.tol_falta_batida = data.get('tol_falta_batida', 5)
            h.limite_extra_diario = data.get('limite_extra_diario', 10)
            h.limite_falta_diario = data.get('limite_falta_diario', 10)
            h.descontar_tol_faltas = data.get('descontar_tol_faltas', 'nunca_desconta')
            h.descontar_tol_extras = data.get('descontar_tol_extras', 'nunca_desconta')
            h.quando_limite_extra = data.get('quando_limite_extra', 'considera_tudo')
            h.quando_limite_falta = data.get('quando_limite_falta', 'considera_tudo')
            
            # Novos campos - DSR
            h.primeiro_dia_semana = data.get('primeiro_dia_semana', 1)
            h.tempo_dsr = data.get('tempo_dsr', '07:20')
            h.max_faltas_dsr = data.get('max_faltas_dsr', '02:00')
            h.desconto_dsr_feriado = data.get('desconto_dsr_feriado', 'desconta_normais')
            
            # Aba Avançada
            h.desconto_faltas_extras = data.get('desconto_faltas_extras', 'desconta_maior')
            h.modo_neutro = data.get('modo_neutro', 'desconsidera_faltas')
            h.calculo_extra_interjornada = data.get('calculo_extra_interjornada', 'nao_calcula')
            h.perc_extra_interjornada = data.get('perc_extra_interjornada', 50.0)
            h.folgas_semana = data.get('folgas_semana', 0)
            
            h.save()
            
            # Detalhes
            if 'detalhes' in data:
                # Se for cíclico e o nº de dias mudou, talvez queira limpar?
                # Por simplicidade, vamos atualizar/criar
                for d_data in data['detalhes']:
                    detalhe, _ = HorarioDetalhe.objects.get_or_create(
                        horario=h, 
                        dia_index=d_data['dia_index']
                    )
                    detalhe.nome_dia = d_data.get('nome_dia', '')
                    
                    e1 = d_data.get('entrada_1')
                    detalhe.entrada_1 = e1 if e1 else None
                    s1 = d_data.get('saida_1')
                    detalhe.saida_1 = s1 if s1 else None
                    e2 = d_data.get('entrada_2')
                    detalhe.entrada_2 = e2 if e2 else None
                    s2 = d_data.get('saida_2')
                    detalhe.saida_2 = s2 if s2 else None
                    
                    detalhe.total_horas = d_data.get('total_horas', '00:00')
                    detalhe.almoco_livre = d_data.get('almoco_livre', False)
                    detalhe.compensado = d_data.get('compensado', False)
                    detalhe.neutro = d_data.get('neutro', False)
                    detalhe.fechamento_noturno = d_data.get('fechamento_noturno', '00:00')
                    detalhe.save()

            # Modo Avançado - Políticas e Faixas de Extras
            if 'politicas_avancadas' in data:
                from core.models import PoliticaHoraExtra, FaixaHoraExtra
                # Limpar antigas e recriar
                h.politicas_hora_extra.all().delete()
                
                for p_idx, p_data in enumerate(data['politicas_avancadas']):
                    politica = PoliticaHoraExtra.objects.create(
                        horario=h,
                        seq=p_idx + 1,
                        dias=p_data.get('dias', 'qualquer_dia'),
                        feriado=p_data.get('feriado', 'qualquer'),
                        noturno=p_data.get('noturno', 'ambos'),
                        intervalo=p_data.get('intervalo', 'tudo'),
                        dia_especifico=p_data.get('dia_especifico', 'qualquer'),
                        acumulo=p_data.get('acumulo', 'diario'),
                        eventos=p_data.get('eventos', '')
                    )
                    
                    faixas = p_data.get('faixas', [])
                    for f_data in faixas:
                        FaixaHoraExtra.objects.create(
                            politica=politica,
                            de_horas=f_data.get('de_horas', 0),
                            ate_horas=f_data.get('ate_horas', 24),
                            acrescimo_percentual=f_data.get('acrescimo_percentual', 50),
                            banco_horas=f_data.get('banco_horas', True),
                            codigo_evento=f_data.get('codigo_evento', ''),
                            codigo_evento_acrescimo=f_data.get('codigo_evento_acrescimo', '')
                        )

        # Invalidar cache de dados auxiliares
        cache.delete('aux_data:all')
        
        return JsonResponse({'success': True, 'message': 'Horário salvo com sucesso', 'id': str(h.id)})
    except Exception as ex:
        logger.error(f"Erro ao salvar horario: {str(ex)}")
        return JsonResponse({'success': False, 'error': str(ex)}, status=500)


@login_required
@require_http_methods(["DELETE"])
def api_delete_horario(request, pk):
    """Exclui um horário"""
    try:
        h = get_object_or_404(Horario, pk=pk)
        h.delete()
        cache.delete('aux_data:all')
        return JsonResponse({'success': True, 'message': 'Horário removido com sucesso'})
    except Exception as ex:
        return JsonResponse({'success': False, 'error': str(ex)}, status=500)

@login_required
@require_http_methods(["GET"])
def api_feriados_list(request):
    """Lista todos os feriados"""
    try:
        from core.utils.holidays_util import get_all_holidays
        from datetime import date
        
        # Gerar cobertura de 3 anos (ano passado, atual e proximo) para folga e listagens
        current_year = date.today().year
        data = get_all_holidays(current_year - 1, current_year + 1)
        
        return JsonResponse({'success': True, 'feriados': data})
    except Exception as ex:
        return JsonResponse({'success': False, 'error': str(ex)}, status=500)


@login_required
@require_http_methods(["POST"])
def api_save_feriado(request):
    """Cria ou atualiza um feriado"""
    try:
        data = json.loads(request.body)
        pk = data.get('id')
        
        with transaction.atomic():
            if pk:
                feriado = get_object_or_404(Holiday, pk=pk)
            else:
                feriado = Holiday()
            
            feriado.name = data.get('name')
            feriado.date = data.get('date')
            feriado.repeats_annually = data.get('repeats_annually', True)
            feriado.apply_to_all = data.get('apply_to_all', True)
            feriado.save()
            
            # ManyToMany fields
            if not feriado.apply_to_all:
                feriado.target_companies.set(data.get('target_companies', []))
                feriado.target_departments.set(data.get('target_departments', []))
                feriado.target_turnos.set(data.get('target_turnos', []))
            else:
                feriado.target_companies.clear()
                feriado.target_departments.clear()
                feriado.target_turnos.clear()

        return JsonResponse({'success': True, 'message': 'Feriado salvo com sucesso.', 'id': str(feriado.id)})
    except Exception as ex:
        logger.error(f"Erro ao salvar feriado: {ex}")
        return JsonResponse({'success': False, 'error': str(ex)}, status=500)


@login_required
@require_http_methods(["DELETE"])
def api_delete_feriado(request, pk):
    """Exclui um feriado"""
    try:
        feriado = get_object_or_404(Holiday, pk=pk)
        feriado.delete()
        return JsonResponse({'success': True, 'message': 'Feriado excluído com sucesso.'})
    except Exception as ex:
        logger.error(f"Erro ao excluir feriado: {ex}")
        return JsonResponse({'success': False, 'error': str(ex)}, status=500)


@login_required
@require_http_methods(["POST"])
def api_execute_atribuicao_massa(request):
    """Executa a atribuição em massa baseada no tipo e nos filtros selecionados"""
    try:
        data = json.loads(request.body)
        filters = data.get('filters', {})
        payload = data.get('payload', {})
        tipo_atribuicao = data.get('tipo_atribuicao')
        
        # Iniciar query base
        colaboradores = Colaborador.objects.all()
        
        # Se houver IDs específicos, usar apenas eles
        colab_ids = filters.get('colaborador_ids', [])
        if colab_ids:
            colaboradores = colaboradores.filter(id__in=colab_ids)
        else:
            # Caso contrário, aplicar filtros cumulativos
            if filters.get('empresa_id'):
                colaboradores = colaboradores.filter(empresa_id=filters.get('empresa_id'))
            if filters.get('department_id'):
                colaboradores = colaboradores.filter(department_id=filters.get('department_id'))
            if filters.get('centro_custo_id'):
                colaboradores = colaboradores.filter(centro_custo_id=filters.get('centro_custo_id'))
            if filters.get('cargo'):
                colaboradores = colaboradores.filter(cargo_atual=filters.get('cargo'))
            if filters.get('horario_id'):
                # Filtro por turno (baseado na string jornada_trabalho ou similar)
                # Como os colaboradores guardam a jornada como string, tentamos um match parcial
                turno = Turno.objects.filter(id=filters.get('horario_id')).first()
                if turno:
                    colaboradores = colaboradores.filter(jornada_trabalho__icontains=turno.nome)

        if not colaboradores.exists():
            return JsonResponse({'success': False, 'error': 'Nenhum colaborador encontrado com os filtros selecionados.'}, status=400)

        with transaction.atomic():
            # A partir daqui a lógica continua a mesma, mas usando o queryset 'colaboradores' filtrado
            
            if tipo_atribuicao == 'horario':
                # Atribuição de Turno (Horário)
                turno_id = payload.get('turno_id')
                if not turno_id:
                    return JsonResponse({'success': False, 'error': 'Turno não selecionado.'}, status=400)
                
                turno = Turno.objects.filter(id=turno_id).first()
                if turno:
                    colaboradores.update(jornada_trabalho=f"{turno.nome} ({turno.horario})")
            
            elif tipo_atribuicao == 'jornada':
                # Atribuição de Jornada (Painting Grid)
                pinturas = payload.get('pinturas', [])
                for colab in colaboradores:
                    for pintura in pinturas:
                        EscalaMensal.objects.update_or_create(
                            colaborador=colab,
                            data=pintura.get('data'),
                            defaults={
                                'horario_previsto_id': pintura.get('turno_id'),
                                'tipo': pintura.get('tipo', 'trabalho'),
                                'justificativa_id': pintura.get('justificativa_id')
                            }
                        )
            
            elif tipo_atribuicao == 'grupos_cargos':
                # Atualização de Empresa, Depto, Cargo, etc.
                updates = {}
                if payload.get('empresa_id'): updates['empresa_id'] = payload.get('empresa_id')
                if payload.get('department_id'): updates['department_id'] = payload.get('department_id')
                if payload.get('cargo'): updates['cargo_atual'] = payload.get('cargo')
                if payload.get('centro_custo_id'): updates['centro_custo_id'] = payload.get('centro_custo_id')
                if payload.get('status'): updates['status'] = payload.get('status')
                
                if updates:
                    colaboradores.update(**updates)
            
            elif tipo_atribuicao == 'justificativa':
                # Aplicação de Justificativa em massa para um período
                justificativa_id = payload.get('justificativa_id')
                data_inicio = payload.get('data_inicio')
                data_fim = payload.get('data_fim')
                
                if not all([justificativa_id, data_inicio, data_fim]):
                    return JsonResponse({'success': False, 'error': 'Dados incompletos para justificativa.'}, status=400)
                
                # Converter datas
                d_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
                d_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
                curr_date = d_inicio
                
                while curr_date <= d_fim:
                    for colab in colaboradores:
                        EscalaMensal.objects.update_or_create(
                            colaborador=colab,
                            data=curr_date,
                            defaults={
                                'justificativa_id': justificativa_id,
                                'tipo': 'afastamento'
                            }
                        )
                    curr_date += timedelta(days=1)

            elif tipo_atribuicao == 'batidas':
                # Criação de Batidas de Ponto em massa
                b_data = payload.get('data')
                b_hora = payload.get('hora')
                b_tipo = payload.get('tipo', 'entrada')
                
                if not all([b_data, b_hora, b_tipo]):
                    return JsonResponse({'success': False, 'error': 'Dados incompletos para a batida.'}, status=400)
                
                for colab in colaboradores:
                    RegistroPonto.objects.create(
                        colaborador=colab,
                        data=b_data,
                        hora=b_hora,
                        tipo=b_tipo,
                        origem='admin',
                        registrado_por=request.user
                    )

        return JsonResponse({'success': True, 'message': f'Atribuição de "{tipo_atribuicao}" executada com sucesso para {colaboradores.count()} colaboradores.'})
    
    except Exception as ex:
        logger.error(f"Erro na atribuição em massa: {ex}")
        return JsonResponse({'success': False, 'error': str(ex)}, status=500)


# ─────────────────────────────────────────────
#  APURAÇÃO DE PONTO - VISUAIS
# ─────────────────────────────────────────────

from ..models import VisualColunaApuracao

@login_required
@require_http_methods(["GET"])
def api_listar_visuais_apuracao(request):
    try:
        visuais = VisualColunaApuracao.objects.filter(usuario=request.user)
        return JsonResponse({'success': True, 'visuais': [
            {
                'id': str(v.id),
                'nome': v.nome,
                'icone': v.icone,
                'colunas': v.colunas,
                'padrao': v.padrao
            } for v in visuais
        ]})
    except Exception as ex:
        return JsonResponse({'success': False, 'error': str(ex)}, status=500)


@login_required
@require_http_methods(["POST"])
def api_salvar_visual_apuracao(request):
    try:
        data = json.loads(request.body)
        pk = data.get('id')
        nome = data.get('nome')
        icone = data.get('icone', 'bi-layout-text-window')
        colunas = data.get('colunas', [])
        padrao = data.get('padrao', False)

        with transaction.atomic():
            if padrao:
                # Se esse vai ser o padrão, desmarca os outros
                VisualColunaApuracao.objects.filter(usuario=request.user, padrao=True).update(padrao=False)

            if pk:
                visual = get_object_or_404(VisualColunaApuracao, pk=pk, usuario=request.user)
            else:
                visual = VisualColunaApuracao(usuario=request.user)

            visual.nome = nome
            visual.icone = icone
            visual.colunas = colunas
            visual.padrao = padrao
            visual.save()
            
        return JsonResponse({'success': True, 'id': str(visual.id), 'message': 'Visual salvo com sucesso', 'colunas': visual.colunas})
    except Exception as ex:
        return JsonResponse({'success': False, 'error': str(ex)}, status=500)
        
@login_required
@require_http_methods(["DELETE"])
def api_excluir_visual_apuracao(request, pk):
    try:
        visual = get_object_or_404(VisualColunaApuracao, pk=pk, usuario=request.user)
        visual.delete()
        return JsonResponse({'success': True, 'message': 'Visual excluído com sucesso'})
    except Exception as ex:
        return JsonResponse({'success': False, 'error': str(ex)}, status=500)

def get_dia_index_para_horario(horario, current_date):
    """
    Calcula o índice do dia (dia_index) para um determinado horário e data.
    Para horários semanais, retorna current_date.weekday() (0-6).
    Para horários cíclicos, calcula a posição no ciclo com base na data_inicio_ciclo.
    """
    if horario.tipo == 'ciclico' and horario.data_inicio:
        delta = (current_date - horario.data_inicio).days
        if delta < 0:
            # Ajustar Python weekday (0=Seg) para bater com Frontend/DB (0=Dom)
            return (current_date.weekday() + 1) % 7
        
        # Busca o total de dias do ciclo (maior dia_index + 1)
        from django.db.models import Max
        max_dia = HorarioDetalhe.objects.filter(horario=horario).aggregate(Max('dia_index'))['dia_index__max']
        if max_dia is not None:
            ciclo_total = max_dia + 1
            return delta % ciclo_total
            
    # Ajustar Python weekday (0=Seg) para bater com Frontend/DB (0=Dom)
    return (current_date.weekday() + 1) % 7

@login_required
@require_http_methods(["POST"])
def api_rh_save_escala_flags(request):
    """Atualiza as flags de um dia na escala (Compensado, Almoço Livre, Folga, Neutro)"""
    try:
        data = json.loads(request.body)
        colaborador_id = data.get('colaborador_id')
        data_str = data.get('data') # YYYY-MM-DD
        flag = data.get('flag') # is_compensado, is_almoco_livre, is_folga, is_neutro
        checked = data.get('checked', False)
        
        if not all([colaborador_id, data_str, flag]):
            return JsonResponse({'success': False, 'error': 'Parâmetros incompletos'}, status=400)
            
        valid_flags = ['is_compensado', 'is_almoco_livre', 'is_folga', 'is_neutro']
        if flag not in valid_flags:
            return JsonResponse({'success': False, 'error': 'Flag inválida'}, status=400)
            
        # Converter data para objeto date
        try:
            data_obj = datetime.strptime(data_str, '%Y-%m-%d').date()
        except ValueError:
             data_obj = datetime.strptime(data_str, '%d/%m/%Y').date()
        
        escala, created = EscalaMensal.objects.get_or_create(
            colaborador_id=colaborador_id,
            data=data_obj
        )
        
        setattr(escala, flag, checked)
        escala.save()
        
        return JsonResponse({'success': True})
    except Exception as ex:
        return JsonResponse({'success': False, 'error': str(ex)}, status=500)

@login_required
@require_http_methods(["POST"])
def api_rh_delete_ponto(request):
    """Marca um registro de ponto como excluído (soft delete) com motivo"""
    try:
        data = json.loads(request.body)
        ponto_id = data.get('ponto_id')
        motivo = data.get('motivo')
        
        if not all([ponto_id, motivo]):
            return JsonResponse({'success': False, 'error': 'ID e motivo são obrigatórios'}, status=400)
            
        ponto = RegistroPonto.objects.get(id=ponto_id)
        ponto.is_deleted = True
        ponto.observacao = motivo
        ponto.registrado_por = request.user
        ponto.save()
        
        return JsonResponse({'success': True})
    except RegistroPonto.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Registro não encontrado'}, status=404)
    except Exception as ex:
        return JsonResponse({'success': False, 'error': str(ex)}, status=500)

@login_required
@require_http_methods(["GET"])
def api_rh_apuracao_dados(request):
    """
    Retorna os dados reais de apuração (batidas diárias) para um colaborador.
    Params: colaborador_id, mes, ano
    """
    try:
        colaborador_id = request.GET.get('colaborador_id')
        data_inicio_str = request.GET.get('data_inicio')
        data_fim_str = request.GET.get('data_fim')
        
        mes = int(request.GET.get('mes', 0))
        ano = int(request.GET.get('ano', 0))

        if not colaborador_id:
            return JsonResponse({'success': False, 'error': 'Colaborador não informado'}, status=400)

        colaborador = get_object_or_404(Colaborador, pk=colaborador_id)
        
        # Determinar o intervalo de datas
        start_date = None
        end_date = None

        if data_inicio_str and data_fim_str:
            try:
                start_date = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
            except ValueError:
                try:
                    start_date = datetime.strptime(data_inicio_str, '%d/%m/%Y').date()
                    end_date = datetime.strptime(data_fim_str, '%d/%m/%Y').date()
                except ValueError:
                    return JsonResponse({'success': False, 'error': 'Formato de data inválido'}, status=400)
        
        if not start_date or not end_date:
            if mes and ano:
                last_day = calendar.monthrange(ano, mes)[1]
                start_date = date(ano, mes, 1)
                end_date = date(ano, mes, last_day)
            else:
                now = timezone.localtime()
                m = mes or now.month
                a = ano or now.year
                last_day = calendar.monthrange(a, m)[1]
                start_date = date(a, m, 1)
                end_date = date(a, m, last_day)

        # Buscar registros de ponto por período para organizar em memória
        registros_todos = RegistroPonto.objects.filter(
            colaborador=colaborador,
            data__range=[start_date, end_date]
        ).order_by('data', 'hora')

        registros = [r for r in registros_todos if not r.is_deleted]
        excluidos = [r for r in registros_todos if r.is_deleted]

        registros_por_dia = {}
        for r in registros:
            if r.data not in registros_por_dia:
                registros_por_dia[r.data] = []
            registros_por_dia[r.data].append(r)
            
        excluidos_por_dia = {}
        for r in excluidos:
            if r.data not in excluidos_por_dia:
                excluidos_por_dia[r.data] = []
            excluidos_por_dia[r.data].append({
                'hora': r.hora.strftime('%H:%M'),
                'motivo': r.observacao or "Não informado",
                'tipo': r.get_tipo_display()
            })

        # Buscar escalas do mês
        escalas = EscalaMensal.objects.filter(
            colaborador=colaborador, 
            data__range=[start_date, end_date]
        ).select_related('horario_previsto')
        escalas_por_data = {e.data: e for e in escalas}

        # Coletar horários envolvidos (pintados + padrão) para buscar detalhes em lote
        horarios_ids = set()
        for e in escalas:
            if e.horario_previsto_id:
                horarios_ids.add(e.horario_previsto_id)
        if colaborador.horario_padrao_id:
            horarios_ids.add(colaborador.horario_padrao_id)
        
        detalhes_qs = HorarioDetalhe.objects.filter(horario_id__in=horarios_ids)
        detalhes_map = {} # (horario_id, dia_index) -> detalhe
        for d in detalhes_qs:
            detalhes_map[(d.horario_id, d.dia_index)] = d

        # Mapear Horários
        horarios_objs = Horario.objects.filter(id__in=horarios_ids)
        horarios_map = {h.id: h for h in horarios_objs}

        considerar_feriados = colaborador.empresa.considerar_feriados_ponto if (colaborador.empresa and hasattr(colaborador.empresa, 'considerar_feriados_ponto')) else True
        
        from core.utils.holidays_util import get_all_holidays
        all_feriados = get_all_holidays(start_date.year, end_date.year)
        datas_feriados_set = set()
        
        from core.models import TrocaFeriado
        trocas_por_original = {}
        trocas_por_troca = {}

        if considerar_feriados:
            if colaborador.empresa:
                trocas = TrocaFeriado.objects.filter(empresa=colaborador.empresa)
                for t in trocas:
                    hb = list(t.horarios_beneficiados.values_list('id', flat=True))
                    if getattr(t, 'repete_anualmente', False):
                        for y in range(start_date.year, end_date.year + 1):
                            try:
                                trocas_por_original[date(y, t.data_feriado.month, t.data_feriado.day)] = {'troca': t, 'hb': hb}
                                trocas_por_troca[date(y, t.data_troca.month, t.data_troca.day)] = {'troca': t, 'hb': hb}
                            except ValueError:
                                pass
                    else:
                        trocas_por_original[t.data_feriado] = {'troca': t, 'hb': hb}
                        trocas_por_troca[t.data_troca] = {'troca': t, 'hb': hb}

            for f_dict in all_feriados:
                if not f_dict['apply_to_all']:
                    if (colaborador.empresa_id not in f_dict['target_companies'] and 
                        (colaborador.department_id not in f_dict['target_departments'] if colaborador.department_id else True)):
                        continue
                d = f_dict['date']
                if f_dict['repeats_annually']:
                    for y in range(start_date.year, end_date.year + 1):
                        try:
                            datas_feriados_set.add(date(y, d.month, d.day))
                        except ValueError:
                            datas_feriados_set.add(date(y, 2, 28))
                else:
                    datas_feriados_set.add(d)

        dias_semana_nome = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
        dados_apuracao = []
        delta = end_date - start_date
        
        last_out_min = None # Para cálculo de interjornada
        
        # Variáveis para Banco de Horas e DSR
        current_banco_acumulado = 0
        semanas_info = {} # {week_year: {"faltas": 0, "atrasos": 0}}

        # ─────────────────────────────────────────────────────────────
        #  PRÉ-CARGA: Justificativas lançadas no período
        # ─────────────────────────────────────────────────────────────
        lancamentos_just = LancamentoJustificativa.objects.filter(
            colaborador=colaborador,
            data_inicio__lte=end_date,
            data_fim__gte=start_date,
        ).select_related('justificativa')

        # Mapa: date -> lista de LancamentoJustificativa que cobrem este dia
        just_por_dia = {}
        for lj in lancamentos_just:
            d_iter = lj.data_inicio
            while d_iter <= lj.data_fim:
                if d_iter not in just_por_dia:
                    just_por_dia[d_iter] = []
                just_por_dia[d_iter].append(lj)
                d_iter += timedelta(days=1)

        # Semanas onde o DSR não deve ser descontado (abonar_dsr)
        semanas_dsr_abonadas = set()
        for lj in lancamentos_just:
            if lj.justificativa.tipo == 'abonar_dsr':
                d_iter = lj.data_inicio
                while d_iter <= lj.data_fim:
                    semanas_dsr_abonadas.add(d_iter.strftime('%Y-%U'))
                    d_iter += timedelta(days=1)

        
        for i in range(delta.days + 1):
            current_date = start_date + timedelta(days=i)
            week_id = current_date.strftime('%Y-%U') # Semana do ano
            if week_id not in semanas_info:
                semanas_info[week_id] = {"atrasos": 0, "faltas": 0}
            
            dia_semana = dias_semana_nome[current_date.weekday()]
            
            regs = registros_por_dia.get(current_date, [])
            
            # Mapear batidas (assumindo ordem cronológica para simplificar)
            ent1 = next((r.hora.strftime('%H:%M') for r in regs if r.tipo == 'entrada'), "")
            ent1_id = next((r.id for r in regs if r.tipo == 'entrada'), None)
            sai1 = next((r.hora.strftime('%H:%M') for r in regs if r.tipo == 'saida_almoco'), "")
            sai1_id = next((r.id for r in regs if r.tipo == 'saida_almoco'), None)
            ent2 = next((r.hora.strftime('%H:%M') for r in regs if r.tipo == 'retorno_almoco'), "")
            ent2_id = next((r.id for r in regs if r.tipo == 'retorno_almoco'), None)
            sai2 = next((r.hora.strftime('%H:%M') for r in regs if r.tipo == 'saida'), "")
            sai2_id = next((r.id for r in regs if r.tipo == 'saida'), None)

            # Se as batidas não estiverem tipadas corretamente, pega as 4 primeiras
            if not any([ent1, sai1, ent2, sai2]) and len(regs) > 0:
                regs_sorted = sorted(regs, key=lambda x: x.hora)
                if len(regs_sorted) >= 1: 
                    ent1 = regs_sorted[0].hora.strftime('%H:%M')
                    ent1_id = regs_sorted[0].id
                if len(regs_sorted) >= 2: 
                    sai1 = regs_sorted[1].hora.strftime('%H:%M')
                    sai1_id = regs_sorted[1].id
                if len(regs_sorted) >= 3: 
                    ent2 = regs_sorted[2].hora.strftime('%H:%M')
                    ent2_id = regs_sorted[2].id
                if len(regs_sorted) >= 4: 
                    sai2 = regs_sorted[3].hora.strftime('%H:%M')
                    sai2_id = regs_sorted[3].id

            # Cálculo básico de horas trabalhadas (minutos)
            total_minutos = 0
            try:
                # Soma bruta de todos os pares entrada-saida (Total Trabalhado)
                # Assumindo registros ordenados cronologicamente
                for j in range(0, len(regs) - 1, 2):
                    r_ent = regs[j]
                    r_sai = regs[j+1]
                    if r_ent.tipo in ['entrada', 'retorno_almoco'] and r_sai.tipo in ['saida_almoco', 'saida']:
                        t_diff = datetime.combine(date.min, r_sai.hora) - datetime.combine(date.min, r_ent.hora)
                        total_minutos += max(0, t_diff.total_seconds() / 60)
            except Exception:
                pass
            
            def fmt_min(m):
                if m <= 0: return ""
                h = int(m // 60)
                mi = int(m % 60)
                return f"{h:02d}:{mi:02d}"

            # Buscar horário previsto
            escala = escalas_por_data.get(current_date)
            
            previsto = ""
            horario_id = None
            detalhe = None
            
            if escala and escala.horario_previsto:
                horario_id = str(escala.horario_previsto.id)
                di = get_dia_index_para_horario(escala.horario_previsto, current_date)
                detalhe = detalhes_map.get((escala.horario_previsto.id, di))
            elif colaborador.horario_padrao:
                horario_id = str(colaborador.horario_padrao.id)
                di = get_dia_index_para_horario(colaborador.horario_padrao, current_date)
                detalhe = detalhes_map.get((colaborador.horario_padrao.id, di))

            if detalhe:
                partes = []
                if detalhe.entrada_1 and detalhe.saida_1:
                    partes.append(f"{detalhe.entrada_1.strftime('%H:%M')}-{detalhe.saida_1.strftime('%H:%M')}")
                if detalhe.entrada_2 and detalhe.saida_2:
                    partes.append(f"{detalhe.entrada_2.strftime('%H:%M')}-{detalhe.saida_2.strftime('%H:%M')}")
                previsto = "<br>".join(partes)
            else:
                if escala and escala.tipo == 'folga': previsto = "Folga"
                elif current_date.weekday() >= 5: previsto = "Folga"
                else: previsto = "S/ Horário"

            # ─────────────────────────────────────────────────────────────
            #  CÁLCULOS AVANÇADOS
            # ─────────────────────────────────────────────────────────────
            
            # 1. Intervalos Previstos (P)
            p_intervals = []
            if detalhe:
                if detalhe.entrada_1 and detalhe.saida_1:
                    p_intervals.append((time_to_min(detalhe.entrada_1), time_to_min(detalhe.saida_1)))
                if detalhe.entrada_2 and detalhe.saida_2:
                    p_intervals.append((time_to_min(detalhe.entrada_2), time_to_min(detalhe.saida_2)))
            
            # 2. Intervalos Trabalhados (W)
            w_intervals = []
            for j in range(0, len(regs) - 1, 2):
                r_ent = regs[j]
                r_sai = regs[j+1]
                w_intervals.append((time_to_min(r_ent.hora), time_to_min(r_sai.hora)))

            # Total Normais: Interseção entre Trabalhado e Previsto
            total_normais_min = get_interval_intersections(w_intervals, p_intervals)
            
            # Diurnas/Noturnas Normais (quebra das horas normais)
            normal_intervals = []
            for ws, we in w_intervals:
                for ps, pe in p_intervals:
                    s = max(ws, ps)
                    e = min(we, pe)
                    if s < e: normal_intervals.append((s, e))
            
            di_normais_min = 0
            no_normais_min = 0
            for ns, ne in normal_intervals:
                d, n = split_night_shift(ns, ne)
                di_normais_min += d
                no_normais_min += n
            
            # Intervalo: Gaps entre batidas (saida -> entrada)
            intervalo_min = 0
            for j in range(1, len(regs) - 1, 2):
                r_sai = regs[j]
                r_ent = regs[j+1]
                diff = time_to_min(r_ent.hora) - time_to_min(r_sai.hora)
                intervalo_min += max(0, diff)
            
            # Total Noturno: Tudo trabalhado no período noturno
            total_noturno_min = 0
            for ws, we in w_intervals:
                _, n = split_night_shift(ws, we)
                total_noturno_min += n

            # Verifica se current_date é feriado considerando as trocas
            is_feriado_hoje = False
            
            if considerar_feriados:
                horario_aplicado_id = None
                if horario_id:
                    try:
                        horario_aplicado_id = int(horario_id)
                    except:
                        pass
                
                # Se hoje é a data original de um feriado que foi trocado
                if current_date in trocas_por_original:
                    t_info = trocas_por_original[current_date]
                    if horario_aplicado_id and horario_aplicado_id in t_info['hb']:
                        # Feriado movido para outro dia -> hoje é dia normal
                        is_feriado_hoje = False
                    else:
                        is_feriado_hoje = True
                # Se hoje é a data de troca (o dia que virou feriado)
                elif current_date in trocas_por_troca:
                    t_info = trocas_por_troca[current_date]
                    if horario_aplicado_id and horario_aplicado_id in t_info['hb']:
                        is_feriado_hoje = True
                    else:
                        is_feriado_hoje = current_date in datas_feriados_set
                else:
                    is_feriado_hoje = current_date in datas_feriados_set

            # Horas previstas do dia
            if is_feriado_hoje:
                minutos_previstos = 0
                previsto = "Feriado"
                dia_util = ""
                p_intervals = [] # Limpando para garantir que não seja intersecionado indevidamente
            else:
                minutos_previstos = sum(e - s for s, e in p_intervals)
                dia_util = 1 if p_intervals else ""

            # ─────────────────────────────────────────────────────────────
            #  FASE 4: EXTRAS ESPECÍFICAS (Intervalo/Antecipada)
            # ─────────────────────────────────────────────────────────────
            
            # 1. Extra Intervalo: Trabalho nos gaps entre p_intervals
            p_breaks = []
            if len(p_intervals) > 1:
                for j in range(len(p_intervals) - 1):
                    p_breaks.append((p_intervals[j][1], p_intervals[j+1][0]))
            
            extra_interval_min = get_interval_intersections(w_intervals, p_breaks)
            
            # 2. Entrada Antecipada: Trabalho antes do 1º previsto
            entrada_ante_min = 0
            if p_intervals and regs:
                primeira_prev = p_intervals[0][0]
                primeira_real = time_to_min(regs[0].hora)
                if primeira_real < primeira_prev:
                    # Só conta se o primeiro intervalo trabalhado intersectar ou começar antes
                    entrada_ante_min = max(0, primeira_prev - primeira_real)

            # 3. Marcações Faltantes / Ímpares / Pulou Almoço
            # Detecta se:
            # - O número de batidas é ímpar (batida faltando).
            # - Ou o número de batidas é menor que o esperado (ex: fez 2 mas previu 4).
            pulou_almoco = 0
            expected_punches = len(p_intervals) * 2
            
            # Só disparamos a inconsistência de "Marcação Incompleta" se houver pelo menos 1 registro.
            # Se for 0 registros, isso se classifica como "Falta" e já será pego na Fase 3.
            if len(regs) > 0:
                if len(regs) % 2 != 0:
                    # Batida ímpar
                    pulou_almoco = 1
                elif minutos_previstos > 0 and expected_punches > 0 and len(regs) < expected_punches:
                    # Fez menos batidas do que os intervalos previstos exigiriam (ex: devia ter 4, deu 2)
                    pulou_almoco = 1

            # ─────────────────────────────────────────────────────────────
            #  FASE 3: ABSENTEÍSMO E ATRASOS
            # ─────────────────────────────────────────────────────────────
            
            # Dia Falta: 1 se tem jornada prevista mas < 2 marcações
            dia_falta = 1 if minutos_previstos > 0 and len(regs) < 2 else 0
            
            # Dias Trabalhados: 1 se tem >= 2 marcações
            dias_trabalhados = 1 if len(regs) >= 2 else 0
            
            # Atraso Entrada: 1ª Real - 1ª Prevista
            atraso_entrada_min = 0
            if detalhe and detalhe.entrada_1 and regs:
                atraso_entrada_min = max(0, time_to_min(regs[0].hora) - time_to_min(detalhe.entrada_1))
            
            # Saída Antecipada: Última Prevista - Última Real
            saida_antecipada_min = 0
            if detalhe and regs:
                ultima_prevista = time_to_min(detalhe.saida_2) if detalhe.saida_2 else time_to_min(detalhe.saida_1) if detalhe.saida_1 else None
                if ultima_prevista:
                    saida_antecipada_min = max(0, ultima_prevista - time_to_min(regs[-1].hora))

            # Atraso Intervalo: Entrada 2 Real - Entrada 2 Prevista
            atraso_intervalo_min = 0
            if detalhe and detalhe.entrada_2 and len(regs) >= 3:
                atraso_intervalo_min = max(0, time_to_min(regs[2].hora) - time_to_min(detalhe.entrada_2))

            # ─────────────────────────────────────────────────────────────
            #  FASE 3 (EXT): ABSENTEÍSMO EM HORAS
            # ─────────────────────────────────────────────────────────────
            
            # Horas Falta: Se Dia Falta=1, é o previsto total do dia
            horas_falta_min = minutos_previstos if dia_falta == 1 else 0
            
            # Horas Atraso: Previsto - Normal (o que ele "deveu" na jornada)
            horas_atraso_min = max(0, minutos_previstos - total_normais_min)
            
            # Atraso Diurno/Noturno: Split do previsto para comparar
            di_prev_min = 0
            no_prev_min = 0
            for ps, pe in p_intervals:
                d, n = split_night_shift(ps, pe)
                di_prev_min += d
                no_prev_min += n
            
            atraso_diurno_min = max(0, di_prev_min - di_normais_min)
            atraso_noturno_min = max(0, no_prev_min - no_normais_min)
            
            # Falta e Atraso (Soma consolidada de dívida)
            falta_atraso_min = horas_atraso_min

            # ─────────────────────────────────────────────────────────────
            #  FASE 3.5: APLICAÇÃO DE JUSTIFICATIVAS
            # ─────────────────────────────────────────────────────────────
            abono_min = 0
            is_justificado = False
            justificativa_info = None

            lancamentos_do_dia = just_por_dia.get(current_date, [])
            for lj in lancamentos_do_dia:
                j = lj.justificativa
                debito_restante = falta_atraso_min  # quanto ainda está em débito

                # ─── Calcular quantos minutos este lançamento "cobre" ───
                credito_min = 0

                if j.tipo == 'dia_inteiro':
                    # Abona tudo que estava em débito no dia (falta ou atraso)
                    credito_min = debito_restante

                elif j.tipo == 'abonar_horas':
                    # Abona um número fixo de horas informado no lançamento
                    if lj.hora_inicio and lj.hora_fim:
                        # hora_inicio usado como "quantidade": ex 08:00 -> 02:00 = 2h
                        credito_min = max(0, time_to_min(lj.hora_fim) - time_to_min(lj.hora_inicio))
                    else:
                        # Fallback: abona o débito do dia por inteiro
                        credito_min = debito_restante

                elif j.tipo == 'periodo_especifico':
                    # Abona apenas o período especificado (hora_inicio -> hora_fim)
                    if lj.hora_inicio and lj.hora_fim:
                        periodo_min = max(0, time_to_min(lj.hora_fim) - time_to_min(lj.hora_inicio))
                        # Abate apenas o que o período cobre, limitado ao débito real
                        credito_min = min(periodo_min, debito_restante)
                    else:
                        credito_min = debito_restante

                elif j.tipo == 'ajustar_horas':
                    # Ajusta diretamente o banco de horas (pode ser positivo/negativo)
                    if lj.hora_inicio and lj.hora_fim:
                        credito_min = time_to_min(lj.hora_fim) - time_to_min(lj.hora_inicio)
                    else:
                        credito_min = 0

                elif j.tipo == 'relocar_extrafalta':
                    # Move extra/falta: não altera o débito, mas marca como justificado
                    credito_min = debito_restante

                elif j.tipo == 'abonar_dsr':
                    # Não altera o débito do dia, apenas marca semana para não descontar DSR
                    credito_min = 0

                # ─── Aplicar o crédito selon a coluna de destino ───
                coluna = j.mostrar_em_coluna or 'apenas_justificar'
                
                if credito_min > 0 or j.tipo in ('dia_inteiro', 'relocar_extrafalta'):
                    if credito_min > 0:
                        # Reduz o débito do dia
                        falta_atraso_min = max(0, falta_atraso_min - credito_min)
                        horas_atraso_min = max(0, horas_atraso_min - credito_min)
                        horas_falta_min = max(0, horas_falta_min - credito_min)

                    if coluna == 'coluna_abono':
                        abono_min += credito_min
                    elif coluna == 'coluna_extra':
                        extra_total_min = extra_total_min + credito_min if 'extra_total_min' in dir() else credito_min
                    elif coluna == 'banco_horas':
                        abono_min += credito_min  # Será somado ao banco_minutos abaixo
                    # coluna 'apenas_justificar': apenas remove o erro visual

                    is_justificado = True
                    justificativa_info = {
                        'nome': j.nome,
                        'abreviacao': j.abreviacao,
                        'tipo': j.tipo,
                        'coluna_destino': coluna,
                        'credito_min': credito_min,
                    }
                    
                    # Se de dia inteiro E abonar_dia_falta, marcar dia como não faltoso
                    if j.abonar_dia_falta and j.tipo in ('dia_inteiro', 'relocar_extrafalta'):
                        dia_falta = 0
                        dias_trabalhados = 1

            # Registrar para DSR da semana (respeitando dsr_abonadas)
            if horas_falta_min > 0 and week_id not in semanas_dsr_abonadas:
                semanas_info[week_id]["faltas"] += 1
            semanas_info[week_id]["atrasos"] += horas_atraso_min


            # ─────────────────────────────────────────────────────────────
            #  FASE 4: EXTRAS E INTERJORNADA
            # ─────────────────────────────────────────────────────────────
            
            # Extra Diurna: Trabalhado Diurno - Normal Diurno
            extra_diurna_min = max(0, (total_minutos - total_noturno_min) - di_normais_min)
            
            # Extra Noturna: Trabalhado Noturno - Normal Noturno
            extra_noturna_min = max(0, total_noturno_min - no_normais_min)
            
            # Extra Total: Soma
            extra_total_min = extra_diurna_min + extra_noturna_min

            # Interjornada: 11h de descanso (660min)
            interjornada_min = 0
            if last_out_min is not None and regs:
                first_in_min = time_to_min(regs[0].hora)
                diff_descanso = (1440 - last_out_min) + first_in_min
                if diff_descanso < 660:
                    interjornada_min = 660 - diff_descanso
            
            # Atualiza last_out para o próximo dia
            if regs:
                last_out_min = time_to_min(regs[-1].hora)
            elif last_out_min is not None:
                # Se não trabalhou, o descanso "estica"
                last_out_min -= 1440 

            dados_apuracao.append({
                'colaborador_id': str(colaborador.id),
                'data': current_date.strftime('%d/%m'),
                'data_full': current_date.strftime('%d/%m/%Y'),
                'data_db': current_date.strftime('%Y-%m-%d'),
                'dia_semana': dia_semana,
                'is_weekend': current_date.weekday() >= 5,
                
                'previsto': "Feriado" if is_feriado_hoje else (previsto if minutos_previstos > 0 else "FOLGA"),
                'horario_id': horario_id,
                'ent1': ent1, 'ent1_id': ent1_id,
                'sai1': sai1, 'sai1_id': sai1_id,
                'ent2': ent2, 'ent2_id': ent2_id,
                'sai2': sai2, 'sai2_id': sai2_id,
                
                'status': 'Justificado' if is_justificado else ('OK' if (len(regs) % 2 == 0 and not (minutos_previstos > 0 and len(regs) == 0)) else 'Inconsistência'),
                'is_compensado': detalhe.compensado if detalhe else False,
                'is_almoco_livre': detalhe.almoco_livre if detalhe else False,
                'is_folga': minutos_previstos == 0,
                'is_neutro': detalhe.neutro if detalhe else False,
                'excluidos': excluidos_por_dia.get(current_date, []),
                
                # Novos Cálculos
                'horas_previstas': min_to_str(minutos_previstos),
                'total_trabalhado': min_to_str(total_minutos),
                'total_normais': min_to_str(total_normais_min),
                'diurnas_normais': min_to_str(di_normais_min),
                'noturnas_normais': min_to_str(no_normais_min),
                'total_noturno': min_to_str(total_noturno_min),
                'intervalo': min_to_str(intervalo_min),
                'dia_util': dia_util,
                
                # FASE 3
                'dia_falta': dia_falta,
                'dias_trabalhados': dias_trabalhados,
                'atraso_entrada': min_to_str(atraso_entrada_min) if atraso_entrada_min > 0 else "",
                'saida_antecipada': min_to_str(saida_antecipada_min),
                'atraso_intervalo': min_to_str(atraso_intervalo_min),
                
                # Extended Phase 3
                'horas_falta': min_to_str(horas_falta_min),
                'horas_atraso': min_to_str(horas_atraso_min),
                'atraso_diurno': min_to_str(atraso_diurno_min),
                'atraso_noturno': min_to_str(atraso_noturno_min),
                'falta_atraso': min_to_str(falta_atraso_min),

                # Phase 4
                'extra_diurna': min_to_str(extra_diurna_min),
                'extra_noturna': min_to_str(extra_noturna_min),
                'extra_total': min_to_str(extra_total_min),
                'interjornada': min_to_str(interjornada_min),
                'extra_intervalo': min_to_str(extra_interval_min),
                'entrada_antecipada': min_to_str(entrada_ante_min),
                'pulou_almoco': pulou_almoco,
                
                # DSR e Banco (Serão preenchidos em uma segunda passada ou ao final)
                'dsr_cons': "00:00",
                'desconta_dsr': 0,
                'dsr_deb': "00:00",
                # banco_minutos: extra - débito_restante + abono direcionado ao banco
                'banco_cred_deb': min_to_str(extra_total_min - falta_atraso_min + abono_min),
                'banco_saldo': "00:00",
                'banco_minutos': extra_total_min - falta_atraso_min + abono_min,
                'abono': min_to_str(abono_min),
                'ajuste': "00:00",

                # Justificativa aplicada ao dia
                'is_justificado': is_justificado,
                'justificativa': justificativa_info,
            })

        
        # Segunda Passada: DSR e Saldo Acumulado
        banco_acumulado = 0
        for dia in dados_apuracao:
            # DSR: Se na semana desse dia houve falta ou atraso excessivo (>10 min por ex)
            # Pegamos o week_id do banco_db
            d_obj = datetime.strptime(dia['data_db'], '%Y-%m-%d')
            w_id = d_obj.strftime('%Y-%U')
            
            # Se é o dia de DSR (ex: Domingo no semanal, ou folga no cíclico)
            is_dsr_day = False
            h_id_int = int(dia['horario_id']) if dia.get('horario_id') else None
            hor_obj = horarios_map.get(h_id_int) if h_id_int else None

            if hor_obj:
                if hor_obj.tipo == 'semanal':
                    # Ajusta Python weekday para comparar com frontend (0=Dom)
                    is_dsr_day = (((d_obj.weekday() + 1) % 7) == hor_obj.dia_dsr)
                elif hor_obj.tipo == 'ciclico':
                    # No cíclico, os dias com 0 horas previstas são os DSRs
                    is_dsr_day = dia.get('is_folga', False)

                if is_dsr_day:
                    # Carregamos o tempo configurado para o DSR
                    tempo_dsr_min = time_to_min(hor_obj.tempo_dsr) if hor_obj.tempo_dsr else 440
                    
                    if semanas_info[w_id]["faltas"] > 0 or semanas_info[w_id]["atrasos"] > 10:
                        dia['desconta_dsr'] = 1
                        dia['dsr_deb'] = min_to_str(tempo_dsr_min)
                    else:
                        dia['dsr_cons'] = min_to_str(tempo_dsr_min)
            else:
                # Comportamento padrão caso não tenha horário vinculado
                if d_obj.weekday() == 6: # Domingo
                    if semanas_info[w_id]["faltas"] > 0 or semanas_info[w_id]["atrasos"] > 10:
                        dia['desconta_dsr'] = 1
                        dia['dsr_deb'] = "07:20"
                    else:
                        dia['dsr_cons'] = "07:20"

            # Saldo Acumulado
            banco_acumulado += dia['banco_minutos']
            dia['banco_saldo'] = ('' if banco_acumulado >= 0 else '-') + min_to_str(abs(banco_acumulado))
            if not dia['banco_saldo']: dia['banco_saldo'] = "00:00"

        # Terceira Passada: Inconsistências
        incon_config = list(TipoInconsistencia.objects.filter(ativo=True).order_by('prioridade'))
        for dia in dados_apuracao:
            dia['inconsistencia'] = detectar_inconsistencias(dia, incon_config)

        return JsonResponse({
            'success': True,
            'colaborador_nome': colaborador.nome_completo,
            'dias': dados_apuracao
        })
    except Exception as ex:
        logger.error(f"Erro na api_rh_apuracao_dados: {str(ex)}")
        return JsonResponse({'success': False, 'error': str(ex)}, status=500)

@login_required
@require_http_methods(["GET"])
def api_inconsistencias_list(request):
    """Lista todos os tipos de inconsistência configurados"""
    incon = TipoInconsistencia.objects.all()
    data = []
    for i in incon:
        data.append({
            'id': i.id,
            'nome': i.nome,
            'campo': i.campo,
            'campo_str': i.get_campo_display(),
            'tolerancia': i.tolerancia,
            'prioridade': i.prioridade,
            'icone': i.icone,
            'cor': i.cor,
            'ativo': i.ativo
        })
    return JsonResponse(data, safe=False)

@login_required
@require_http_methods(["POST"])
def api_save_inconsistencia(request):
    """Cria ou atualiza um tipo de inconsistência"""
    if not request.user.is_administrador():
        return JsonResponse({'erro': 'Acesso negado'}, status=403)
    
    try:
        data = json.loads(request.body)
        pk = data.get('id')
        
        if pk:
            incon = get_object_or_404(TipoInconsistencia, pk=pk)
        else:
            incon = TipoInconsistencia()
            
        incon.nome = data.get('nome')
        incon.campo = data.get('campo')
        incon.tolerancia = int(data.get('tolerancia', 1))
        incon.prioridade = int(data.get('prioridade', 5))
        incon.icone = data.get('icone', 'bi-exclamation-circle-fill')
        incon.cor = data.get('cor', '#dc3545')
        incon.ativo = data.get('ativo', True)
        incon.save()
        
        return JsonResponse({'success': True, 'id': incon.id})
    except Exception as e:
        return JsonResponse({'success': False, 'erro': str(e)}, status=500)

@login_required
@require_http_methods(["POST"])
def api_delete_inconsistencia(request, pk):
    """Exclui um tipo de inconsistência"""
    if not request.user.is_administrador():
        return JsonResponse({'erro': 'Acesso negado'}, status=403)
    
    incon = get_object_or_404(TipoInconsistencia, pk=pk)
    incon.delete()
    return JsonResponse({'success': True})

def detectar_inconsistencias(dia_data, inconsistencias_config):
    """
    Analisa um dia de apuração e retorna a inconsistência de maior prioridade detectada.
    """
    disparadas = []
    
    for config in inconsistencias_config:
        valor_min = 0
        disparar = False
        
        if config.campo == 'atraso':
            valor_min = time_to_min(dia_data.get('horas_atraso', '00:00'))
        elif config.campo == 'falta':
            if dia_data.get('dia_falta') == 1:
                # Dia total de falta flagrado; set a high value to definitely trigger
                valor_min = 1000
            else:
                # Falta parcial: use horas_falta respecting tolerance
                valor_min = time_to_min(dia_data.get('horas_falta', '00:00'))
        elif config.campo == 'extra_total':
            valor_min = time_to_min(dia_data.get('extra_total', '00:00'))
        elif config.campo == 'banco_pos':
            b_min = dia_data.get('banco_minutos', 0)
            valor_min = b_min if b_min > 0 else 0
        elif config.campo == 'banco_neg':
            b_min = dia_data.get('banco_minutos', 0)
            valor_min = abs(b_min) if b_min < 0 else 0
        elif config.campo == 'intervalo_curto':
            valor_min = time_to_min(dia_data.get('extra_intervalo', '00:00'))
        elif config.campo == 'interjornada':
            valor_min = time_to_min(dia_data.get('interjornada', '00:00'))
        elif config.campo == 'marcacoes_impares':
            disparar = bool(dia_data.get('pulou_almoco', 0))
            
        if not disparar and valor_min >= config.tolerancia:
            disparar = True
            
        if disparar:
            disparadas.append(config)
            
    if not disparadas:
        return None
        
    # Desempate de severidade estrutural para itens de mesma prioridade
    severity = {
        'marcacoes_impares': 1,
        'falta': 2,
        'banco_neg': 3,
        'atraso': 4,
        'interjornada': 5,
        'intervalo_curto': 6,
        'banco_pos': 7,
        'extra_total': 8
    }
    
    disparadas.sort(key=lambda c: (c.prioridade, severity.get(c.campo, 99)))
    
    best = disparadas[0]
    return {
        'id': best.id,
        'nome': best.nome,
        'icone': best.icone,
        'cor': best.cor,
        'prioridade': best.prioridade
    }

@login_required
@require_http_methods(["GET"])
def api_rh_filtro_inconsistencias_dados(request):
    """
    Pesquisa inconsistências em um range de datas para N funcionários.
    Utiliza o motor do api_rh_apuracao_dados.
    """
    try:
        empresa = request.GET.get('empresa')
        departamento = request.GET.get('department')
        centro_custo = request.GET.get('centro_custo')
        cargo = request.GET.get('cargo')
        colaborador_id = request.GET.get('colaborador_id', '')
        pessoas = request.GET.get('pessoas', '')
        inconsistencias_selecionadas = request.GET.get('tipos_inconsistencia', '')

        colaboradores = Colaborador.objects.filter(status='ativo').order_by('nome_completo')
        
        if empresa: colaboradores = colaboradores.filter(empresa_id=empresa)
        if departamento: colaboradores = colaboradores.filter(department_id=departamento)
        if centro_custo: colaboradores = colaboradores.filter(centro_custo_id=centro_custo)
        if cargo: colaboradores = colaboradores.filter(cargo_id=cargo)
        
        # Filtro por colaborador específico (campo 'colaborador_id' do formulário)
        if colaborador_id:
            try:
                colaboradores = colaboradores.filter(id=int(colaborador_id))
            except (ValueError, TypeError):
                pass

        # Filtro legado por lista de pessoas separadas por vírgula
        if pessoas:
            lista_ids = [int(x.strip()) for x in pessoas.split(',') if x.strip()]
            if lista_ids:
                colaboradores = colaboradores.filter(id__in=lista_ids)

        tipos_busca = [int(x.strip()) for x in inconsistencias_selecionadas.split(',') if x.strip()]

        req_copy = request.GET.copy()
        original_get = request.GET
        
        resultados_finais = []
        
        import json
        for colab in colaboradores:
            try:
                req_copy['colaborador_id'] = str(colab.id)
                request.GET = req_copy
                
                # Chama a API de apuração original
                resp = api_rh_apuracao_dados(request)
                if resp.status_code == 200:
                    data = json.loads(resp.content)
                    dias = data.get('dias', [])
                    
                    for dia in dias:
                        incon = dia.get('inconsistencia')
                        if not incon: 
                            continue # Dia sem inconsistencia nao interessa
                        
                        if not tipos_busca or incon.get('id') in tipos_busca:
                            # Adicionamos metadados do funcionário pois a grid é misturada
                            dia['colaborador_id'] = colab.id
                            dia['colaborador_nome'] = colab.nome_completo
                            dia['pis'] = colab.pis if colab.pis else ''
                            resultados_finais.append(dia)
                else:
                    logger.warning(f"api_rh_apuracao_dados retornou {resp.status_code} para {colab.nome_completo}")
            except Exception as e:
                logger.error(f"Erro analisando colaborador {colab.nome_completo}: {str(e)}")
                continue
            finally:
                request.GET = original_get
                
        return JsonResponse({'success': True, 'items': resultados_finais})
    except Exception as ex:
        logger.error(f"Erro fatal em api_rh_filtro_inconsistencias_dados: {str(ex)}")
        return JsonResponse({'success': False, 'error': str(ex)}, status=500)

@login_required
@require_http_methods(["GET"])
def api_rh_ponto_diario_dados(request):
    """
    Retorna os dados de apuração de múltiplos colaboradores para um único dia.
    Usado na tela de Ponto Diário (Equipe).
    """
    try:
        data_sel = request.GET.get('data')
        if not data_sel:
            return JsonResponse({'success': False, 'erro': 'Data não informada'}, status=400)
        
        # Filtros
        empresa_id = request.GET.get('empresa')
        dept_id = request.GET.get('department')
        cargo_id = request.GET.get('cargo')
        cc_id = request.GET.get('centro_custo')
        horario_id = request.GET.get('horario')
        apenas_incon = request.GET.get('apenas_incon') == 'true'
        
        # Colaboradores
        colaboradores = Colaborador.objects.filter(status='ativo')
        if empresa_id: colaboradores = colaboradores.filter(empresa_id=empresa_id)
        if dept_id: colaboradores = colaboradores.filter(department_id=dept_id)
        if cargo_id: colaboradores = colaboradores.filter(cargo_id=cargo_id)
        if cc_id: colaboradores = colaboradores.filter(centro_custo_id=cc_id)
        
        target_date = datetime.strptime(data_sel, '%Y-%m-%d').date()
        incon_config = list(TipoInconsistencia.objects.filter(ativo=True).order_by('prioridade'))
        
        # Otimização: Pegamos todos os registros de ponto do dia para os colaboradores filtrados
        registros_ponto = RegistroPonto.objects.filter(data=target_date, colaborador__in=colaboradores).select_related('colaborador')
        regs_map = {}
        for r in registros_ponto:
            if r.colaborador_id not in regs_map: regs_map[r.colaborador_id] = []
            regs_map[r.colaborador_id].append(r)

        # Pegamos a escala de quem possuir para o dia, senão cai no padrão
        escalas = EscalaMensal.objects.filter(data=target_date, colaborador__in=colaboradores)
        escalas_map = {e.colaborador_id: e.horario_previsto_id for e in escalas if e.horario_previsto_id}

        horarios_list = Horario.objects.all().prefetch_related('detalhes')
        horarios_map = {h.id: h for h in horarios_list}
        
        # Pegamos os lançamentos de justificativa para o dia
        lancamentos_just = LancamentoJustificativa.objects.filter(
            data_inicio__lte=target_date, 
            data_fim__gte=target_date,
            colaborador__in=colaboradores
        ).select_related('justificativa')
        just_map = {lj.colaborador_id: lj for lj in lancamentos_just}
        
        resultados = []
        for colab in colaboradores:
            # Lógica simplificada de apuração para 1 dia
            horario_id = escalas_map.get(colab.id, colab.horario_padrao_id)
            horario = horarios_map.get(horario_id) if horario_id else None
            regs = regs_map.get(colab.id, [])
            
            # Aqui deveríamos chamar a mesma lógica de cálculo, mas por ser 1 dia 
            # e para performance, vamos omitir o loop pesado e focar no essencial.
            # TODO: Refatorar core para permitir cálculo de dia isolado sem overhead.
            
            dia_item = {
                'colaborador_id': colab.id,
                'colaborador_nome': colab.nome_completo,
                'cargo_nome': colab.cargo_atual,
                'data_db': data_sel,
                'status': 'OK' if regs else 'Inconsistência',
                'justificativa': None,
                'ent1': regs[0].hora.strftime('%H:%M') if len(regs) > 0 else '',
                'sai1': regs[1].hora.strftime('%H:%M') if len(regs) > 1 else '',
                'ent2': regs[2].hora.strftime('%H:%M') if len(regs) > 2 else '',
                'sai2': regs[3].hora.strftime('%H:%M') if len(regs) > 3 else '',
                'banco_horas': '00:00',
                'is_justificado': False
            }
            
            # Verificar se há justificativa
            justificativa_ativa = just_map.get(colab.id)
            if justificativa_ativa:
                dia_item['justificativa'] = {
                    'nome': justificativa_ativa.justificativa.nome,
                    'abreviacao': justificativa_ativa.justificativa.abreviacao,
                    'abona_falta': justificativa_ativa.justificativa.abonar_dia_falta
                }
                if justificativa_ativa.justificativa.abonar_dia_falta:
                    dia_item['status'] = 'Justificado'
                    dia_item['is_justificado'] = True

            # Detecção de inconsistência básica
            dia_item['inconsistencia'] = detectar_inconsistencias(dia_item, incon_config)
            
            # Se foi justificado e a justificativa abona falta, limpamos a inconsistência visual
            if dia_item.get('is_justificado') and dia_item['inconsistencia']:
                 # Se for falta total ou banco negativo, e houver abono, limpamos a flag de erro
                 dia_item['inconsistencia'] = None
            
            if apenas_incon and not dia_item['inconsistencia'] and dia_item['status'] == 'OK':
                continue
                
            resultados.append(dia_item)

        return JsonResponse({'success': True, 'dias': resultados})
    except Exception as e:
        logger.error(f"Erro na api_rh_ponto_diario_dados: {str(e)}")
        return JsonResponse({'success': False, 'erro': str(e)}, status=500)


# ─────────────────────────────────────────────
#  JUSTIFICATIVAS (CADASTRO)
# ─────────────────────────────────────────────

@login_required
@require_http_methods(["GET"])
def api_justificativas_list(request):
    try:
        from core.models import JustificativaPonto
        justificativas = JustificativaPonto.objects.all()
        return JsonResponse({'success': True, 'justificativas': [
            {
                'id': str(j.id),
                'nome': j.nome,
                'abreviacao': j.abreviacao,
                'tipo': j.tipo,
                'tipo_display': j.get_tipo_display() if hasattr(j, 'get_tipo_display') else j.tipo,
                'descontar_dsr': j.descontar_dsr,
                'pedir_texto_motivo': j.pedir_texto_motivo,
                'abonar_dia_falta': j.abonar_dia_falta,
                'informar_cid': j.informar_cid,
                'mostrar_em_coluna': j.mostrar_em_coluna,
            } for j in justificativas
        ]})
    except Exception as ex:
        return JsonResponse({'success': False, 'error': str(ex)}, status=500)

@login_required
@require_http_methods(["POST"])
def api_save_justificativa(request):
    from core.models import JustificativaPonto
    try:
        import json
        data = json.loads(request.body)
        pk = data.get('id')
        
        from django.db import transaction
        with transaction.atomic():
            if pk:
                j = get_object_or_404(JustificativaPonto, pk=pk)
            else:
                j = JustificativaPonto()
            
            j.nome = data.get('nome', '')
            j.abreviacao = data.get('abreviacao', '')
            j.tipo = data.get('tipo', 'periodo_especifico')
            j.descontar_dsr = data.get('descontar_dsr', False)
            j.pedir_texto_motivo = data.get('pedir_texto_motivo', True)
            j.abonar_dia_falta = data.get('abonar_dia_falta', True)
            j.informar_cid = data.get('informar_cid', False)
            j.mostrar_em_coluna = data.get('mostrar_em_coluna', 'apenas_justificar')
            
            j.save()
            
        return JsonResponse({'success': True, 'message': 'Salvo com sucesso', 'id': str(j.id)})
    except Exception as ex:
        import logging
        logging.getLogger(__name__).error(f"Erro salvando justificativa: {ex}")
        return JsonResponse({'success': False, 'error': str(ex)}, status=500)

@login_required
@require_http_methods(["DELETE"])
def api_delete_justificativa(request, pk):
    from core.models import JustificativaPonto
    try:
        j = get_object_or_404(JustificativaPonto, pk=pk)
        j.delete()
        return JsonResponse({'success': True, 'message': 'Excluído com sucesso'})
    except Exception as ex:
        return JsonResponse({'success': False, 'error': str(ex)}, status=500)


# ─────────────────────────────────────────────
#  LANÇAMENTOS DE JUSTIFICATIVAS
# ─────────────────────────────────────────────

@login_required
@require_http_methods(["POST"])
def api_save_lancamento_justificativa(request):
    from core.models import LancamentoJustificativa, JustificativaPonto, Colaborador
    try:
        import json
        data = json.loads(request.body)
        pk = data.get('id')

        colaborador_id = data.get('colaborador_id')
        justificativa_id = data.get('justificativa_id')

        if not colaborador_id or not justificativa_id:
            return JsonResponse({'success': False, 'error': 'colaborador_id e justificativa_id são obrigatórios'}, status=400)

        colaborador = get_object_or_404(Colaborador, pk=colaborador_id)
        justificativa = get_object_or_404(JustificativaPonto, pk=justificativa_id)

        from django.db import transaction
        with transaction.atomic():
            if pk:
                lj = get_object_or_404(LancamentoJustificativa, pk=pk)
            else:
                lj = LancamentoJustificativa()

            lj.colaborador = colaborador
            lj.justificativa = justificativa
            lj.data_inicio = data.get('data_inicio')
            lj.hora_inicio = data.get('hora_inicio') or None
            lj.data_fim = data.get('data_fim')
            lj.hora_fim = data.get('hora_fim') or None
            lj.motivo_texto = data.get('motivo_texto', '')
            lj.cid = data.get('cid', '')
            lj.lancado_por = request.user
            lj.save()

        return JsonResponse({
            'success': True,
            'message': 'Justificativa lançada com sucesso',
            'id': str(lj.id),
        })
    except Exception as ex:
        import logging
        logging.getLogger(__name__).error(f"Erro salvando lançamento: {ex}")
        return JsonResponse({'success': False, 'error': str(ex)}, status=500)


@login_required
@require_http_methods(["DELETE"])
def api_delete_lancamento_justificativa(request, pk):
    from core.models import LancamentoJustificativa
    try:
        lj = get_object_or_404(LancamentoJustificativa, pk=pk)
        lj.delete()
        return JsonResponse({'success': True, 'message': 'Lançamento excluído'})
    except Exception as ex:
        return JsonResponse({'success': False, 'error': str(ex)}, status=500)


@login_required
@require_http_methods(["GET"])
def api_list_lancamentos_justificativa(request):
    from core.models import LancamentoJustificativa
    try:
        colaborador_id = request.GET.get('colaborador_id')
        data_inicio = request.GET.get('data_inicio')
        data_fim = request.GET.get('data_fim')

        qs = LancamentoJustificativa.objects.select_related('colaborador', 'justificativa', 'lancado_por')

        if colaborador_id:
            qs = qs.filter(colaborador_id=colaborador_id)
        if data_inicio:
            qs = qs.filter(data_inicio__gte=data_inicio)
        if data_fim:
            qs = qs.filter(data_fim__lte=data_fim)

        return JsonResponse({'success': True, 'lancamentos': [
            {
                'id': str(lj.id),
                'colaborador_id': str(lj.colaborador_id),
                'colaborador_nome': lj.colaborador.nome_completo,
                'justificativa_id': str(lj.justificativa_id),
                'justificativa_nome': lj.justificativa.nome,
                'justificativa_tipo': lj.justificativa.tipo,
                'data_inicio': lj.data_inicio.strftime('%Y-%m-%d'),
                'hora_inicio': lj.hora_inicio.strftime('%H:%M') if lj.hora_inicio else None,
                'data_fim': lj.data_fim.strftime('%Y-%m-%d'),
                'hora_fim': lj.hora_fim.strftime('%H:%M') if lj.hora_fim else None,
                'motivo_texto': lj.motivo_texto,
                'cid': lj.cid,
                'lancado_por': lj.lancado_por.get_full_name() if lj.lancado_por else '',
                'data_lancamento': lj.data_lancamento.strftime('%d/%m/%Y %H:%M'),
            } for lj in qs
        ]})
    except Exception as ex:
        return JsonResponse({'success': False, 'error': str(ex)}, status=500)


# ─────────────────────────────────────────────
#  RELATÓRIO DE INCONSISTÊNCIAS (CSV)
# ─────────────────────────────────────────────

@login_required
def api_relatorio_inconsistencias_csv(request):
    """
    Exporta as inconsistências detectadas em formato CSV.
    Baseado nos mesmos filtros da busca de inconsistências.
    """
    import csv
    import json
    from django.http import HttpResponse
    from datetime import datetime
    import logging

    logger = logging.getLogger(__name__)

    try:
        # 1. Filtros (Reutilizando a lógica da API de dados)
        empresa_id = request.GET.get('empresa')
        dept_id = request.GET.get('department')
        colab_id = request.GET.get('colaborador_id')
        data_ini = request.GET.get('data_inicio')
        data_fim = request.GET.get('data_fim')
        tipos_incon_str = request.GET.get('tipos_inconsistencia', '')
        
        # Colunas selecionadas pelo usuário (CSV separado por vírgula no param 'columns')
        columns_str = request.GET.get('columns', 'colaborador_nome,data,pis,inconsistencia_nome')
        selected_columns = [c.strip() for c in columns_str.split(',') if c.strip()]

        from core.models import Colaborador
        colaboradores = Colaborador.objects.filter(status='ativo').order_by('nome_completo')
        if empresa_id: colaboradores = colaboradores.filter(empresa_id=empresa_id)
        if dept_id: colaboradores = colaboradores.filter(department_id=dept_id)
        if colab_id: colaboradores = colaboradores.filter(id=colab_id)

        tipos_busca = [int(x.strip()) for x in tipos_incon_str.split(',') if x.strip()]

        # 2. Setup do Response CSV
        filename = f"relatorio_inconsistencias_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # BOM for Excel UTF-8
        response.write(u'\ufeff'.encode('utf8'))
        
        writer = csv.writer(response, delimiter=';')

        # Map de headers amigáveis
        header_map = {
            'colaborador_nome': 'Funcionário',
            'pis': 'PIS',
            'data': 'Data',
            'inconsistencia_nome': 'Inconsistência',
            'ent1': 'Ent. 1', 'sai1': 'Saí. 1', 'ent2': 'Ent. 2', 'sai2': 'Saí. 2',
            'horas_trabalhadas': 'Trab.',
            'horas_falta': 'Falta',
            'horas_atraso': 'Atraso',
            'extra_total': 'Extra',
            'total_diario': 'Total Dia'
        }
        
        # Cabeçalho formatado
        writer.writerow([header_map.get(c, c) for c in selected_columns])

        # 3. Processamento
        # Salvamos o estado original do GET pois vamos modificá-lo para cada chamada
        original_get = request.GET
        req_copy = request.GET.copy()

        for colab in colaboradores:
            try:
                # Simulamos o request para cada colaborador usando a API de apuração existente
                req_copy['colaborador_id'] = str(colab.id)
                request.GET = req_copy
                
                # Importamos localmente para evitar circular dependency se houver
                from core.api.rh import api_rh_apuracao_dados
                
                resp = api_rh_apuracao_dados(request)
                if resp.status_code == 200:
                    data_json = json.loads(resp.content)
                    dias = data_json.get('dias', [])
                    
                    for dia in dias:
                        incon = dia.get('inconsistencia')
                        if not incon: 
                            continue
                        
                        inc_id = incon.get('id')
                        if not tipos_busca or inc_id in tipos_busca:
                            row = []
                            for col in selected_columns:
                                val = ''
                                if col == 'colaborador_nome': 
                                    val = colab.nome_completo
                                elif col == 'pis': 
                                    val = colab.pis or ''
                                elif col == 'inconsistencia_nome': 
                                    val = incon.get('nome', '')
                                elif col == 'data': 
                                    val = dia.get('data', '')
                                else: 
                                    val = dia.get(col, '')
                                row.append(val)
                            writer.writerow(row)
            except Exception as e:
                logger.error(f"Erro processando colab {colab.id} no relatorio: {e}")
                continue
            finally:
                request.GET = original_get

        return response
    except Exception as ex:
        logger.error(f"Erro fatal gerando CSV de inconsistências: {ex}")
        return HttpResponse(f"Erro ao gerar CSV: {str(ex)}", status=500)

# ─────────────────────────────────────────────
# CONFIGURAÇÃO E TROCA DE FERIADOS
# ─────────────────────────────────────────────

@login_required
@require_http_methods(["GET", "POST"])
def api_rh_configurar_feriados(request):
    if request.method == "GET":
        empresas = Empresa.objects.all().values('id', 'nome', 'considerar_feriados_ponto')
        return JsonResponse({'success': True, 'empresas': list(empresas)})
    else:
        data = json.loads(request.body)
        empresa_id = data.get('empresa_id')
        valor = data.get('considerar_feriados_ponto')
        emp = get_object_or_404(Empresa, pk=empresa_id)
        emp.considerar_feriados_ponto = valor
        emp.save()
        return JsonResponse({'success': True})

@login_required
@require_http_methods(["GET", "POST"])
def api_rh_trocas_feriados(request):
    from core.models import TrocaFeriado
    if request.method == "GET":
        trocas = TrocaFeriado.objects.select_related('empresa').all()
        dados = []
        for t in trocas:
            hb_list = []
            for h in t.horarios_beneficiados.all():
                hb_list.append({'id': h.id, 'nome': h.nome})
            dados.append({
                'id': t.id,
                'empresa_id': t.empresa_id,
                'empresa_nome': t.empresa.nome,
                'descricao': t.descricao,
                'data_feriado': t.data_feriado.strftime('%Y-%m-%d'),
                'data_feriado_str': t.data_feriado.strftime('%d/%m/%Y'),
                'data_troca': t.data_troca.strftime('%Y-%m-%d'),
                'data_troca_str': t.data_troca.strftime('%d/%m/%Y'),
                'repete_anualmente': getattr(t, 'repete_anualmente', False),
                'horarios_beneficiados': hb_list,
                'horarios_ids': [h['id'] for h in hb_list]
            })
        return JsonResponse({'success': True, 'trocas': dados})
    else:
        data = json.loads(request.body)
        if data.get('id'):
            t = get_object_or_404(TrocaFeriado, pk=data.get('id'))
        else:
            t = TrocaFeriado()
        t.empresa_id = data.get('empresa_id')
        t.data_feriado = data.get('data_feriado')
        t.descricao = data.get('descricao')
        t.data_troca = data.get('data_troca')
        t.repete_anualmente = data.get('repete_anualmente', False)
        t.save()
        if data.get('horarios_beneficiados'):
            t.horarios_beneficiados.set(data.get('horarios_beneficiados'))
        return JsonResponse({'success': True})

@login_required
@require_http_methods(["DELETE"])
def api_rh_delete_troca_feriado(request, pk):
    from core.models import TrocaFeriado
    t = get_object_or_404(TrocaFeriado, pk=pk)
    t.delete()
    return JsonResponse({'success': True})
