"""
API Views de IA — Brisoft
Endpoints para o chatbot da KB e classificação automática de reclamações.
"""
import json
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from ..models import BrisoftIABase, Department
from ..services.ia_service import chatbot_kb
from django_ratelimit.decorators import ratelimit


@csrf_exempt
@login_required
@require_http_methods(["POST"])
@ratelimit(key='user', rate='20/m', block=True)
@ratelimit(key='ip', rate='50/m', block=True)
def api_chatbot_kb(request):
    """
    Endpoint do chatbot da Base de Conhecimento.
    Recebe {"pergunta": "..."} e retorna {"resposta": "..."}.
    """
    try:
        data = json.loads(request.body)
        pergunta = data.get('pergunta', '').strip()

        if not pergunta:
            return JsonResponse({'erro': 'Pergunta não pode ser vazia.'}, status=400)

        if len(pergunta) > 1000:
            return JsonResponse({'erro': 'Pergunta muito longa (máx. 1000 caracteres).'}, status=400)

        # Buscar artigos na Base da IA exclusiva
        if request.user.is_administrador():
            # Administrador tem contexto de todos os departamentos (ou do selecionado)
            selected_dept_id = request.session.get('selected_department_id')
            if selected_dept_id:
                queryset = BrisoftIABase.objects.filter(department_id=selected_dept_id)
            else:
                queryset = BrisoftIABase.objects.all()
        else:
            # Demais usuários (analistas/gestores) só veem a base do próprio departamento
            queryset = BrisoftIABase.objects.filter(department=request.user.department)

        artigos = [
            {'titulo': a.titulo, 'conteudo': a.conteudo}
            for a in queryset.only('titulo', 'conteudo')
        ]

        historico = data.get('historico', [])

        user_context = {
            'nome': request.user.first_name or request.user.username,
            'email': request.user.email,
            'cargo': request.user.role if hasattr(request.user, 'role') else '',
            'departamento': request.user.department.name if hasattr(request.user, 'department') and request.user.department else 'Nenhum'
        }

        resultado_ia = chatbot_kb(pergunta, artigos, user_context, historico)
        
        # Executar ação local no servidor se necessário
        if 'action' in resultado_ia:
            action = resultado_ia['action']
            if action['type'] == 'change_password':
                nova_senha = action.get('nova_senha')
                if nova_senha:
                    request.user.set_password(nova_senha)
                    request.user.save()
                    from django.contrib.auth import update_session_auth_hash
                    update_session_auth_hash(request, request.user)
            
            elif action['type'] == 'update_data':
                entidade = action.get('entidade')
                obj_id = action.get('id')
                campos = action.get('campos', {})
                
                try:
                    if entidade == 'usuario':
                        # Se não passar ID, altera o próprio
                        user = request.user
                        if obj_id and request.user.is_administrador():
                            from ..models import User
                            user = User.objects.get(pk=obj_id)
                        
                        # Impedir alteração de role por não-admin
                        if not request.user.is_administrador():
                            campos.pop('role', None)
                            campos.pop('is_staff', None)
                            campos.pop('is_superuser', None)

                        for k, v in campos.items():
                            if hasattr(user, k):
                                setattr(user, k, v)
                        user.save()



                except Exception as e:
                    resultado_ia['resposta'] = f"Consegui processar o pedido, mas houve um erro técnico ao salvar: {str(e)}"

        return JsonResponse(resultado_ia)

    except json.JSONDecodeError:
        return JsonResponse({'erro': 'Dados inválidos.'}, status=400)
    except Exception as e:
        return JsonResponse({'erro': f'Erro interno: {str(e)}'}, status=500)





# -------------------------------------------------------------
# APIs CRUD para a Base Brisoft IA
# -------------------------------------------------------------

@login_required
@require_http_methods(["GET"])
def api_ia_base_list(request):
    """Lista artigos da base Brisoft IA."""
    if not (request.user.is_gestor() or request.user.is_administrador()):
        return JsonResponse({'erro': 'Acesso negado.'}, status=403)

    try:
        dept_id = request.GET.get('department_id')
        
        if request.user.is_administrador():
            if dept_id:
                qs = BrisoftIABase.objects.filter(department_id=dept_id)
            else:
                qs = BrisoftIABase.objects.all()
        else:
            qs = BrisoftIABase.objects.filter(department=request.user.department)

        qs = qs.select_related('department').order_by('-created_at')
        
        data = []
        for a in qs:
            data.append({
                'id': a.id,
                'titulo': a.titulo,
                'conteudo': a.conteudo,
                'department_id': a.department.id if a.department else None,
                'department_name': a.department.name if a.department else 'N/A',
                'created_at': a.created_at.strftime("%d/%m/%Y %H:%M")
            })

        return JsonResponse({'artigos': data})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'erro': str(e)}, status=500)


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def api_ia_base_create(request):
    if not (request.user.is_gestor() or request.user.is_administrador()):
        return JsonResponse({'erro': 'Acesso negado.'}, status=403)

    try:
        data = json.loads(request.body)
        titulo = data.get('titulo', '').strip()
        conteudo = data.get('conteudo', '').strip()
        dept_id = data.get('department_id')

        if not titulo or not conteudo:
            return JsonResponse({'erro': 'Título e conteúdo são obrigatórios.'}, status=400)

        # Determinar departamento
        if request.user.is_administrador():
            if not dept_id:
                return JsonResponse({'erro': 'Selecione um departamento.'}, status=400)
            department = Department.objects.get(pk=dept_id)
        else:
            department = request.user.department

        artigo = BrisoftIABase.objects.create(
            department=department,
            titulo=titulo,
            conteudo=conteudo
        )

        return JsonResponse({'status': 'ok', 'id': artigo.id})
    except Department.DoesNotExist:
        return JsonResponse({'erro': 'Departamento não encontrado.'}, status=404)
    except Exception as e:
        return JsonResponse({'erro': str(e)}, status=500)


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def api_ia_base_update(request, pk):
    if not (request.user.is_gestor() or request.user.is_administrador()):
        return JsonResponse({'erro': 'Acesso negado.'}, status=403)

    try:
        artigo = BrisoftIABase.objects.get(pk=pk)
        
        # Validar permissão (gestor só edita do seu dept)
        if not request.user.is_administrador() and artigo.department != request.user.department:
            return JsonResponse({'erro': 'Você não tem permissão para editar este artigo.'}, status=403)

        data = json.loads(request.body)
        titulo = data.get('titulo', '').strip()
        conteudo = data.get('conteudo', '').strip()
        dept_id = data.get('department_id')

        if not titulo or not conteudo:
            return JsonResponse({'erro': 'Título e conteúdo são obrigatórios.'}, status=400)

        artigo.titulo = titulo
        artigo.conteudo = conteudo
        
        if request.user.is_administrador() and dept_id:
            artigo.department_id = dept_id
            
        artigo.save()

        return JsonResponse({'status': 'ok'})
    except BrisoftIABase.DoesNotExist:
        return JsonResponse({'erro': 'Artigo não encontrado.'}, status=404)
    except Exception as e:
        return JsonResponse({'erro': str(e)}, status=500)


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def api_ia_base_delete(request, pk):
    if not (request.user.is_gestor() or request.user.is_administrador()):
        return JsonResponse({'erro': 'Acesso negado.'}, status=403)

    try:
        artigo = BrisoftIABase.objects.get(pk=pk)
        if not request.user.is_administrador() and artigo.department != request.user.department:
            return JsonResponse({'erro': 'Acesso negado.'}, status=403)
            
        artigo.delete()
        return JsonResponse({'status': 'ok'})
    except BrisoftIABase.DoesNotExist:
        return JsonResponse({'erro': 'Artigo não encontrado.'}, status=404)
    except Exception as e:
        return JsonResponse({'erro': str(e)}, status=500)
