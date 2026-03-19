"""
APIs para o Módulo de RH - Gestão de Colaboradores
"""

from django.http import JsonResponse, Http404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
import json
import logging

from ..models import (
    Colaborador, Department, HistoricoProfissional, 
    PerformanceRH, User, DocumentoColaborador, Empresa
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
    """Dados auxiliares para formulários (Cargos, Departamentos, Opções)"""
    cargos = []
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

from ..models import Cargo

@login_required
@require_http_methods(["GET"])
def api_cargos_list(request):
    """Lista todos os cargos"""
    try:
        cargos = Cargo.objects.all().select_related('department')
        return JsonResponse({'success': True, 'cargos': [
            {
                'id': str(c.id),
                'nome': c.nome,
                'department_id': str(c.department_id),
                'department_name': c.department.name if c.department else '',
                'descricao': c.descricao,
            } for c in cargos
        ]})
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
