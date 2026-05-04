"""
Serviço de integração com a API do Contact Center (Bitrix24 Analytics).
Responsável por buscar sessões de chat e seus transcripts.
"""
import logging
import requests
from datetime import date, timedelta
from django.conf import settings

logger = logging.getLogger(__name__)

# Mapeamento de filas → tipo de atendimento
FILA_TIPO_MAP = {
    'NRS': 'cliente',
    'NRS (nível 2)': 'cliente',
    'NRS Franqueados': 'franqueado',
    'HiPag Suporte': 'cliente',
    'Laundry In Box Suporte': 'cliente',
}

# Filas auditáveis (ignorar outros bots/filas não relevantes)
FILAS_AUDITAVEIS = set(FILA_TIPO_MAP.keys())


def _get_headers():
    """Retorna os headers de autenticação da API."""
    api_key = getattr(settings, 'CONTACTCENTER_API_KEY', '')
    if not api_key:
        raise ValueError("CONTACTCENTER_API_KEY não configurada. Adicione ao .env.")
    
    # Remove espaços em branco ou quebras de linha acidentais
    api_key = api_key.strip()
    
    return {
        'X-Api-Key': api_key,
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }


def _get_base_url():
    """Retorna a URL base da API."""
    return getattr(settings, 'CONTACTCENTER_API_URL', 'https://contactcenter.ikli.com.br')


def get_linhas_disponiveis():
    """
    Retorna todas as linhas (filas) disponíveis na API.
    GET /api/v1/dashboard/available-lines
    """
    try:
        url = f"{_get_base_url()}/api/v1/dashboard/available-lines"
        response = requests.get(url, headers=_get_headers(), timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"[Bitrix] Erro ao buscar linhas disponíveis: {e}")
        return []


def get_sessoes_dia_anterior(data: date = None, limit: int = 200):
    """
    Busca todas as sessões finalizadas do dia anterior (ou da data especificada).
    Filtra apenas filas auditáveis.
    
    GET /api/v1/sessions?status=finished&start_date=...&end_date=...&limit=200
    """
    if data is None:
        data = date.today() - timedelta(days=1)

    start_dt = f"{data}T00:00:00Z"
    end_dt = f"{data}T23:59:59Z"

    try:
        url = f"{_get_base_url()}/api/v1/sessions"
        params = {
            'status': 'finished',
            'start_date': start_dt,
            'end_date': end_dt,
            'limit': limit,
            'order_by': 'started_at',
            'order_dir': 'asc',
        }
        response = requests.get(url, headers=_get_headers(), params=params, timeout=60)
        response.raise_for_status()
        data_json = response.json()

        # A API pode retornar lista direta ou dict com 'items'
        sessoes = data_json if isinstance(data_json, list) else data_json.get('items', data_json.get('sessions', []))

        # Filtrar apenas filas auditáveis
        sessoes_filtradas = []
        for s in sessoes:
            nome_fila = (
                s.get('line_name') or
                s.get('line', {}).get('name', '') if isinstance(s.get('line'), dict) else s.get('line', '')
            )
            if nome_fila in FILAS_AUDITAVEIS:
                s['_tipo_atendimento'] = FILA_TIPO_MAP[nome_fila]
                s['_nome_fila'] = nome_fila
                sessoes_filtradas.append(s)

        logger.info(f"[Bitrix] {len(sessoes_filtradas)} sessões auditáveis de {len(sessoes)} totais em {data}")
        return sessoes_filtradas

    except Exception as e:
        logger.error(f"[Bitrix] Erro ao buscar sessões: {e}")
        return []


def get_mensagens_sessao(session_id: int) -> list:
    """
    Busca todas as mensagens de uma sessão (transcript).
    GET /api/v1/sessions/{session_id}/messages
    """
    try:
        url = f"{_get_base_url()}/api/v1/sessions/{session_id}/messages"
        response = requests.get(url, headers=_get_headers(), timeout=30)
        response.raise_for_status()
        data = response.json()

        # Pode ser lista ou dict com 'messages'
        mensagens = data if isinstance(data, list) else data.get('messages', [])
        return mensagens

    except Exception as e:
        logger.error(f"[Bitrix] Erro ao buscar mensagens da sessão {session_id}: {e}")
        return []


def formatar_transcript(mensagens: list) -> str:
    """
    Converte lista de mensagens em texto formatado para o prompt da IA.
    """
    if not mensagens:
        return "[Sem mensagens registradas]"

    linhas = []
    for msg in mensagens:
        # Campos comuns nos retornos de API de chat
        autor = (
            msg.get('author_name') or
            msg.get('author') or
            msg.get('sender_name') or
            msg.get('sender') or
            'Desconhecido'
        )
        texto = (
            msg.get('text') or
            msg.get('message') or
            msg.get('content') or
            ''
        )
        if texto:
            linhas.append(f"[{autor}]: {texto}")

    return "\n".join(linhas) if linhas else "[Sem mensagens de texto]"


def encontrar_analista_nexus(email_analista: str):
    """
    Encontra o User do Nexus correspondente ao e-mail do analista no Bitrix.
    Retorna o objeto User ou None.
    """
    if not email_analista:
        return None
    try:
        from core.models import User
        return User.objects.filter(email__iexact=email_analista.strip()).first()
    except Exception as e:
        logger.error(f"[Bitrix] Erro ao buscar analista por email {email_analista}: {e}")
        return None


def identificar_tipo_atendimento(nome_fila: str) -> str:
    """
    Retorna 'cliente' ou 'franqueado' baseado no nome da fila.
    """
    return FILA_TIPO_MAP.get(nome_fila, 'cliente')
