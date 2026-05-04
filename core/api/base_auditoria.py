"""
API para gestão da Base de Conhecimento de Auditoria IA.
Permite CRUD dos artigos que a IA usa para auditar chats automaticamente.
"""
import json
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods, require_GET
from django.views.decorators.csrf import csrf_exempt
from ..models import BaseAuditoria, Department


def _gestor_ou_admin(user):
    return user.is_authenticated and (user.is_gestor() or user.is_administrador())


@login_required
@require_GET
def api_base_auditoria_list(request):
    """Lista artigos da base de auditoria IA com filtros opcionais."""
    if not _gestor_ou_admin(request.user):
        return JsonResponse({'error': 'Acesso negado.'}, status=403)

    department = request.user.department
    queryset = BaseAuditoria.objects.filter(department=department, ativo=True)

    categoria = request.GET.get('categoria')
    search = request.GET.get('search', '').strip()

    if categoria and categoria != 'todos':
        queryset = queryset.filter(categoria=categoria)
    if search:
        queryset = queryset.filter(titulo__icontains=search) | queryset.filter(conteudo__icontains=search)

    data = [{
        'id': a.id,
        'titulo': a.titulo,
        'conteudo': a.conteudo,
        'categoria': a.categoria,
        'categoria_display': a.get_categoria_display(),
        'ativo': a.ativo,
        'created_at': a.created_at.isoformat(),
        'updated_at': a.updated_at.isoformat(),
    } for a in queryset]

    return JsonResponse({'success': True, 'artigos': data, 'total': len(data)})


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def api_base_auditoria_create(request):
    """Cria um novo artigo na base de auditoria IA."""
    if not _gestor_ou_admin(request.user):
        return JsonResponse({'error': 'Acesso negado.'}, status=403)

    try:
        data = json.loads(request.body)
        department = request.user.department
        if not department:
            return JsonResponse({'error': 'Usuário sem departamento.'}, status=400)

        artigo = BaseAuditoria.objects.create(
            titulo=data.get('titulo', '').strip(),
            conteudo=data.get('conteudo', '').strip(),
            categoria=data.get('categoria', 'geral'),
            department=department,
            ativo=True,
        )
        return JsonResponse({
            'success': True,
            'artigo': {
                'id': artigo.id,
                'titulo': artigo.titulo,
                'categoria': artigo.categoria,
                'categoria_display': artigo.get_categoria_display(),
            }
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido.'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@login_required
@require_http_methods(["GET", "PUT", "DELETE"])
def api_base_auditoria_detail(request, pk):
    """Detalhes, atualização ou exclusão de um artigo da base de auditoria."""
    if not _gestor_ou_admin(request.user):
        return JsonResponse({'error': 'Acesso negado.'}, status=403)

    artigo = get_object_or_404(BaseAuditoria, pk=pk, department=request.user.department)

    if request.method == "GET":
        return JsonResponse({
            'success': True,
            'artigo': {
                'id': artigo.id,
                'titulo': artigo.titulo,
                'conteudo': artigo.conteudo,
                'categoria': artigo.categoria,
                'categoria_display': artigo.get_categoria_display(),
                'ativo': artigo.ativo,
                'created_at': artigo.created_at.isoformat(),
            }
        })

    elif request.method == "PUT":
        try:
            data = json.loads(request.body)
            artigo.titulo = data.get('titulo', artigo.titulo).strip()
            artigo.conteudo = data.get('conteudo', artigo.conteudo).strip()
            artigo.categoria = data.get('categoria', artigo.categoria)
            artigo.ativo = data.get('ativo', artigo.ativo)
            artigo.save()
            return JsonResponse({
                'success': True,
                'artigo': {
                    'id': artigo.id,
                    'titulo': artigo.titulo,
                    'categoria': artigo.categoria,
                    'categoria_display': artigo.get_categoria_display(),
                }
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    elif request.method == "DELETE":
        artigo.delete()
        return JsonResponse({'success': True})


@login_required
@require_GET
def api_base_auditoria_categorias(request):
    """Retorna as categorias disponíveis para a base de auditoria."""
    from ..models import BaseAuditoria as BA
    categorias = [{'value': k, 'label': v} for k, v in BA.CATEGORIA_CHOICES]
    return JsonResponse({'success': True, 'categorias': categorias})
