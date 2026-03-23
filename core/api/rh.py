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
    JustificativaPonto, EscalaMensal, Horario, HorarioDetalhe, RegistroPonto, VisualColunaApuracao
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
                
                # Novos campos RHID - Tolerâncias
                'tol_clt': h.tol_clt,
                'tol_extra_batida': h.tol_extra_batida,
                'tol_falta_batida': h.tol_falta_batida,
                'limite_extra_diario': h.limite_extra_diario,
                'limite_falta_diario': h.limite_falta_diario,
                'descontar_tol_faltas': h.descontar_tol_faltas,
                'descontar_tol_extras': h.descontar_tol_extras,
                'quando_limite_extra': h.quando_limite_extra,
                'quando_limite_falta': h.quando_limite_falta,
                
                # Novos campos RHID - DSR
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
            
            # Novos campos RHID - Tolerâncias
            h.tol_clt = data.get('tol_clt', True)
            h.tol_extra_batida = data.get('tol_extra_batida', 5)
            h.tol_falta_batida = data.get('tol_falta_batida', 5)
            h.limite_extra_diario = data.get('limite_extra_diario', 10)
            h.limite_falta_diario = data.get('limite_falta_diario', 10)
            h.descontar_tol_faltas = data.get('descontar_tol_faltas', 'nunca_desconta')
            h.descontar_tol_extras = data.get('descontar_tol_extras', 'nunca_desconta')
            h.quando_limite_extra = data.get('quando_limite_extra', 'considera_tudo')
            h.quando_limite_falta = data.get('quando_limite_falta', 'considera_tudo')
            
            # Novos campos RHID - DSR
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
        feriados = Holiday.objects.all().order_by('date')
        data = []
        for f in feriados:
            data.append({
                'id': str(f.id),
                'name': f.name,
                'date': f.date.isoformat(),
                'date_display': f.date.strftime('%d/%m/%Y') if not f.repeats_annually else f.date.strftime('%d/%m'),
                'repeats_annually': f.repeats_annually,
                'apply_to_all': f.apply_to_all,
                'target_companies': list(f.target_companies.values_list('id', flat=True)),
                'target_departments': list(f.target_departments.values_list('id', flat=True)),
                'target_turnos': list(f.target_turnos.values_list('id', flat=True)),
            })
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
        if data_inicio_str and data_fim_str:
            try:
                start_date = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
            except ValueError:
                # Tenta formato brasileiro se vier do frontend assim (mas input type=date geralmente manda ISO)
                try:
                    start_date = datetime.strptime(data_inicio_str, '%d/%m/%Y').date()
                    end_date = datetime.strptime(data_fim_str, '%d/%m/%Y').date()
                except ValueError:
                    return JsonResponse({'success': False, 'error': 'Formato de data inválido'}, status=400)
        elif mes and ano:
            last_day = calendar.monthrange(ano, mes)[1]
            start_date = date(ano, mes, 1)
            end_date = date(ano, mes, last_day)
        else:
            # Default para o mês atual
            now = timezone.now()
            mes = now.month
            ano = now.year
            last_day = calendar.monthrange(ano, mes)[1]
            start_date = date(ano, mes, 1)
            end_date = date(ano, mes, last_day)

        # Buscar registros de ponto
        registros = RegistroPonto.objects.filter(
            colaborador=colaborador,
            data__range=[start_date, end_date]
        ).order_by('data', 'hora')

        # Organizar registros por dia
        registros_por_dia = {}
        for r in registros:
            if r.data not in registros_por_dia:
                registros_por_dia[r.data] = []
            registros_por_dia[r.data].append(r)

        dias_semana_nome = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]

        dados_apuracao = []
        delta = end_date - start_date
        for i in range(delta.days + 1):
            current_date = start_date + timedelta(days=i)
            dia_semana = dias_semana_nome[current_date.weekday()]
            
            regs = registros_por_dia.get(current_date, [])
            
            # Mapear batidas (assumindo ordem cronológica para simplificar)
            # Buscando tipos específicos se disponíveis
            ent1 = next((r.hora.strftime('%H:%M') for r in regs if r.tipo == 'entrada'), "")
            sai1 = next((r.hora.strftime('%H:%M') for r in regs if r.tipo == 'saida_almoco'), "")
            ent2 = next((r.hora.strftime('%H:%M') for r in regs if r.tipo == 'retorno_almoco'), "")
            sai2 = next((r.hora.strftime('%H:%M') for r in regs if r.tipo == 'saida'), "")

            # Se as batidas não estiverem tipadas corretamente (ex: manual sem tipo certo), pega as 4 primeiras
            if not any([ent1, sai1, ent2, sai2]) and len(regs) > 0:
                times = sorted([r.hora.strftime('%H:%M') for r in regs])
                if len(times) >= 1: ent1 = times[0]
                if len(times) >= 2: sai1 = times[1]
                if len(times) >= 3: ent2 = times[2]
                if len(times) >= 4: sai2 = times[3]

            # Cálculo básico de horas trabalhadas (minutos)
            total_minutos = 0
            try:
                if ent1 and sai1:
                    t1 = datetime.strptime(sai1, '%H:%M') - datetime.strptime(ent1, '%H:%M')
                    total_minutos += max(0, t1.total_seconds() / 60)
                if ent2 and sai2:
                    t2 = datetime.strptime(sai2, '%H:%M') - datetime.strptime(ent2, '%H:%M')
                    total_minutos += max(0, t2.total_seconds() / 60)
            except Exception:
                pass
            
            def fmt_min(m):
                if m <= 0: return ""
                h = int(m // 60)
                mi = int(m % 60)
                return f"{h:02d}:{mi:02d}"

            # Buscar horário previsto na EscalaMensal
            escala = EscalaMensal.objects.filter(colaborador=colaborador, data=current_date).select_related('horario_previsto').first()
            
            previsto = ""
            horario_id = None
            
            if escala and escala.horario_previsto:
                horario_id = str(escala.horario_previsto.id)
                # Buscar detalhes do horário para o dia da semana (0-6)
                # Nota: current_date.weekday() já retorna 0-6 (Seg-Dom)
                detalhe = HorarioDetalhe.objects.filter(horario=escala.horario_previsto, dia_index=current_date.weekday()).first()
                if detalhe:
                    partes = []
                    if detalhe.entrada_1 and detalhe.saida_1:
                        partes.append(f"{detalhe.entrada_1.strftime('%H:%M')}-{detalhe.saida_1.strftime('%H:%M')}")
                    if detalhe.entrada_2 and detalhe.saida_2:
                        partes.append(f"{detalhe.entrada_2.strftime('%H:%M')}-{detalhe.saida_2.strftime('%H:%M')}")
                    previsto = "<br>".join(partes)
                else:
                    previsto = "Folga" if escala.tipo == 'folga' else "S/ Horário"
            else:
                # Fallback: Usar horário padrão do colaborador se não houver escala pintada
                if colaborador.horario_padrao:
                    horario_id = str(colaborador.horario_padrao.id)
                    detalhe = HorarioDetalhe.objects.filter(horario=colaborador.horario_padrao, dia_index=current_date.weekday()).first()
                    if detalhe:
                        partes = []
                        if detalhe.entrada_1 and detalhe.saida_1:
                            partes.append(f"{detalhe.entrada_1.strftime('%H:%M')}-{detalhe.saida_1.strftime('%H:%M')}")
                        if detalhe.entrada_2 and detalhe.saida_2:
                            partes.append(f"{detalhe.entrada_2.strftime('%H:%M')}-{detalhe.saida_2.strftime('%H:%M')}")
                        previsto = "<br>".join(partes)
                    else:
                        previsto = "Folga"
                else:
                    # Fallback final se nem o colaborador tiver horário vinculado
                    is_weekend = current_date.weekday() >= 5
                    if is_weekend:
                        previsto = "Folga"
                    else:
                        previsto = "08:00-12:00<br>13:00-17:00"

            dados_apuracao.append({
                'data': current_date.strftime('%d/%m'),
                'data_full': current_date.strftime('%d/%m/%Y'),
                'dia_semana': dia_semana,
                'is_weekend': current_date.weekday() >= 5,
                'previsto': previsto,
                'horario_id': horario_id,
                'ent1': ent1,
                'sai1': sai1,
                'ent2': ent2,
                'sai2': sai2,
                'total_normais': fmt_min(total_minutos),
                'status': 'OK' if (len(regs) % 2 == 0 and len(regs) > 0) or len(regs) == 0 else 'Inconsistência'
            })

        return JsonResponse({
            'success': True,
            'colaborador_nome': colaborador.nome_completo,
            'dias': dados_apuracao
        })
    except Exception as ex:
        logger.error(f"Erro na api_rh_apuracao_dados: {str(ex)}")
        return JsonResponse({'success': False, 'error': str(ex)}, status=500)
