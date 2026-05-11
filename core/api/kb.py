import json
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from ..models import ArtigoBaseConhecimento, FerramentaIA, Department

@login_required
def api_kb_articles_list(request):
    """Lista artigos da base de conhecimento"""
    selected_dept_id = request.session.get('selected_department_id')
    
    if request.user.is_administrador():
        if selected_dept_id:
            queryset = ArtigoBaseConhecimento.objects.filter(department_id=selected_dept_id)
        else:
            queryset = ArtigoBaseConhecimento.objects.all()
    else:
        queryset = ArtigoBaseConhecimento.objects.filter(department=request.user.department)

    # Filtros de categoria e busca
    categoria = request.GET.get('categoria')
    search = request.GET.get('search')
    
    if categoria and categoria != 'all':
        queryset = queryset.filter(categoria=categoria)
    if search:
        queryset = queryset.filter(
            titulo__icontains=search) | queryset.filter(
            conteudo__icontains=search) | queryset.filter(
            tags__icontains=search)

    data = [{
        'id': a.id,
        'titulo': a.titulo,
        'conteudo': a.conteudo,
        'categoria': a.categoria,
        'tags': [t.strip() for t in a.tags.split(',')] if a.tags else [],
        'views': a.views,
        'votos_uteis': a.votos_uteis,
        'votos_inuteis': a.votos_inuteis,
        'author': a.usuario.get_full_name() or a.usuario.username if a.usuario else 'Sistema',
        'created_at': a.created_at.isoformat(),
        'updated_at': a.updated_at.isoformat()
    } for a in queryset]
    
    return JsonResponse(data, safe=False)

@csrf_exempt
@login_required
@require_http_methods(["POST"])
def api_kb_article_create(request):
    """Cria um novo artigo"""
    try:
        data = json.loads(request.body)
        
        dept = None
        if request.user.is_administrador():
            selected_dept_id = request.session.get('selected_department_id')
            if selected_dept_id:
                dept = get_object_or_404(Department, id=selected_dept_id)
        else:
            dept = request.user.department
            
        if not dept:
            return JsonResponse({'error': 'Departamento não definido.'}, status=400)

        artigo = ArtigoBaseConhecimento.objects.create(
            titulo=data.get('titulo'),
            conteudo=data.get('conteudo'),
            categoria=data.get('categoria', 'tutorials'),
            tags=data.get('tags', ''),
            department=dept,
            usuario=request.user
        )
        
        return JsonResponse({
            'status': 'success',
            'id': artigo.id,
            'titulo': artigo.titulo
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
@login_required
@require_http_methods(["GET", "PUT", "DELETE"])
def api_kb_article_detail(request, pk):
    """Detalhes, atualização ou exclusão de um artigo"""
    if request.user.is_administrador():
        artigo = get_object_or_404(ArtigoBaseConhecimento, pk=pk)
    else:
        artigo = get_object_or_404(ArtigoBaseConhecimento, pk=pk, department=request.user.department)

    if request.method == "GET":
        # Incrementar views
        artigo.views += 1
        artigo.save()
        
        return JsonResponse({
            'id': artigo.id,
            'titulo': artigo.titulo,
            'conteudo': artigo.conteudo,
            'categoria': artigo.categoria,
            'tags': [t.strip() for t in artigo.tags.split(',')] if artigo.tags else [],
            'views': artigo.views,
            'votos_uteis': artigo.votos_uteis,
            'votos_inuteis': artigo.votos_inuteis,
            'author': artigo.usuario.get_full_name() or artigo.usuario.username if artigo.usuario else 'Sistema',
            'created_at': artigo.created_at.isoformat(),
            'updated_at': artigo.updated_at.isoformat()
        })
    
    elif request.method == "PUT":
        try:
            data = json.loads(request.body)
            artigo.titulo = data.get('titulo', artigo.titulo)
            artigo.conteudo = data.get('conteudo', artigo.conteudo)
            artigo.categoria = data.get('categoria', artigo.categoria)
            artigo.tags = data.get('tags', artigo.tags)
            artigo.save()
            
            # Retornar o artigo completo atualizado
            return JsonResponse({
                'status': 'success',
                'article': {
                    'id': artigo.id,
                    'titulo': artigo.titulo,
                    'conteudo': artigo.conteudo,
                    'categoria': artigo.categoria,
                    'tags': [t.strip() for t in artigo.tags.split(',')] if artigo.tags else [],
                    'views': artigo.views,
                    'votos_uteis': artigo.votos_uteis,
                    'votos_inuteis': artigo.votos_inuteis,
                    'author': artigo.usuario.get_full_name() or artigo.usuario.username if artigo.usuario else 'Sistema',
                    'created_at': artigo.created_at.isoformat(),
                    'updated_at': artigo.updated_at.isoformat()
                }
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
            
    elif request.method == "DELETE":
        artigo.delete()
        return JsonResponse({'status': 'success'})

@login_required
def api_kb_tools_list(request):
    """Lista ferramentas de IA"""
    queryset = FerramentaIA.objects.all()
    
    # Se não houver ferramentas, semear com as padrão
    if not queryset.exists():
        _seed_tools()
        queryset = FerramentaIA.objects.all()
        
    search = request.GET.get('search')
    if search:
        queryset = queryset.filter(
            titulo__icontains=search) | queryset.filter(
            descricao__icontains=search)

    data = [{
        'id': t.id,
        'titulo': t.titulo,
        'url': t.url,
        'descricao': t.descricao,
        'categoria': t.categoria
    } for t in queryset]
    
    return JsonResponse(data, safe=False)

def _seed_tools():
    """Semeia ferramentas de IA padrão"""
    default_tools = [
        # IA Gerais
        ('ChatGPT', 'https://chat.openai.com/', 'Modelo de linguagem da OpenAI.', 'ia'),
        ('Google Gemini', 'https://gemini.google.com/', 'IA multimodal do Google.', 'ia'),
        ('Claude.ai', 'https://claude.ai/', 'Assistente de IA da Anthropic.', 'ia'),
        # Design
        ('Canva AI', 'https://www.canva.com/', 'Plataforma de design com IA.', 'ia'),
        ('Adobe Firefly', 'https://www.adobe.com/sensei/generative-ai/firefly.html', 'Geração de imagens da Adobe.', 'ia'),
        # Outros... vou adicionar mais alguns importantes
        ('ElevenLabs', 'https://elevenlabs.io/', 'Síntese de voz com IA.', 'ia'),
        ('Runway ML', 'https://runwayml.com/', 'Edição de vídeo com IA.', 'ia'),
    ]
    
    for titulo, url, descricao, categoria in default_tools:
        FerramentaIA.objects.get_or_create(
            titulo=titulo,
            url=url,
            defaults={'descricao': descricao, 'categoria': categoria}
        )


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def api_kb_article_vote(request, pk):
    """Incrementa voto_util ou voto_inutil para o artigo"""
    artigo = get_object_or_404(ArtigoBaseConhecimento, pk=pk)
    try:
        data = json.loads(request.body)
        voto = data.get('voto')  # 'sim' ou 'nao'
        if voto == 'sim':
            artigo.votos_uteis += 1
        elif voto == 'nao':
            artigo.votos_inuteis += 1
        else:
            return JsonResponse({'error': 'Tipo de voto inválido.'}, status=400)
        artigo.save()
        return JsonResponse({
            'status': 'success',
            'votos_uteis': artigo.votos_uteis,
            'votos_inuteis': artigo.votos_inuteis
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
