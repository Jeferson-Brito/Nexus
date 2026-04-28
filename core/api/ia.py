"""
API Views de IA — Nexus
Endpoints para o chatbot da KB e classificação automática de reclamações.
"""
import json
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from ..models import ArtigoBaseConhecimento, Complaint
from ..services.ia_service import chatbot_kb, classificar_reclamacao


@csrf_exempt
@login_required
@require_http_methods(["POST"])
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

        # Buscar artigos do departamento do usuário (ou todos se admin)
        if request.user.is_administrador():
            selected_dept_id = request.session.get('selected_department_id')
            if selected_dept_id:
                queryset = ArtigoBaseConhecimento.objects.filter(department_id=selected_dept_id)
            else:
                queryset = ArtigoBaseConhecimento.objects.all()
        else:
            queryset = ArtigoBaseConhecimento.objects.filter(department=request.user.department)

        artigos = [
            {'titulo': a.titulo, 'conteudo': a.conteudo}
            for a in queryset.only('titulo', 'conteudo')
        ]

        resposta = chatbot_kb(pergunta, artigos)
        return JsonResponse({'resposta': resposta})

    except json.JSONDecodeError:
        return JsonResponse({'erro': 'Dados inválidos.'}, status=400)
    except Exception as e:
        return JsonResponse({'erro': f'Erro interno: {str(e)}'}, status=500)


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def api_classificar_reclamacao(request, pk):
    """
    Classifica uma reclamação específica com IA.
    """
    if not (request.user.is_gestor() or request.user.is_administrador()):
        return JsonResponse({'erro': 'Acesso negado.'}, status=403)

    try:
        complaint = Complaint.objects.get(pk=pk)
        resultado = classificar_reclamacao(
            descricao=complaint.descricao or complaint.feedback_text or '',
            tipo_reclamacao=complaint.get_tipo_reclamacao_display()
        )

        if 'erro' not in resultado:
            complaint.ia_urgencia = resultado['urgencia']
            complaint.ia_sentimento = resultado['sentimento']
            complaint.ia_classificado_em = timezone.now()
            complaint.save(update_fields=['ia_urgencia', 'ia_sentimento', 'ia_classificado_em'])

        return JsonResponse({
            'status': 'ok',
            'urgencia': resultado.get('urgencia'),
            'sentimento': resultado.get('sentimento'),
        })

    except Complaint.DoesNotExist:
        return JsonResponse({'erro': 'Reclamação não encontrada.'}, status=404)
    except Exception as e:
        return JsonResponse({'erro': str(e)}, status=500)


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def api_classificar_lote(request):
    """
    Classifica em lote todas as reclamações sem classificação IA.
    Limita a 50 por chamada para não travar o servidor.
    """
    if not (request.user.is_gestor() or request.user.is_administrador()):
        return JsonResponse({'erro': 'Acesso negado.'}, status=403)

    try:
        # Filtrar reclamações sem classificação IA
        qs = Complaint.objects.filter(ia_urgencia__isnull=True)

        # Filtrar por departamento se não for admin
        if not request.user.is_administrador():
            qs = qs.filter(department=request.user.department)

        pendentes = qs.order_by('-created_at')[:50]
        classificadas = 0
        erros = 0

        for complaint in pendentes:
            descricao = complaint.descricao or complaint.feedback_text or ''
            if not descricao.strip():
                continue

            resultado = classificar_reclamacao(
                descricao=descricao,
                tipo_reclamacao=complaint.get_tipo_reclamacao_display()
            )

            if 'erro' not in resultado or resultado.get('erro') != 'api_key_missing':
                complaint.ia_urgencia = resultado['urgencia']
                complaint.ia_sentimento = resultado['sentimento']
                complaint.ia_classificado_em = timezone.now()
                complaint.save(update_fields=['ia_urgencia', 'ia_sentimento', 'ia_classificado_em'])
                classificadas += 1
            else:
                erros += 1
                break  # Parar se a API key está faltando

        total_restante = Complaint.objects.filter(ia_urgencia__isnull=True).count()

        return JsonResponse({
            'status': 'ok',
            'classificadas': classificadas,
            'erros': erros,
            'restante': total_restante
        })

    except Exception as e:
        return JsonResponse({'erro': str(e)}, status=500)
