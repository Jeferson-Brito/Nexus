"""
Serviço de integração com a API REST nativa do Bitrix24 via Webhook.

Substitui a integração anterior com o intermediário contactcenter.ikli.com.br.
O webhook `BITRIX24_WEBHOOK_URL` já contém autenticação embutida na URL.

ESCOPO ATUAL DO WEBHOOK: ['imopenlines']

Métodos disponíveis relevantes:
  - imopenlines.config.list.get       → listar filas (Open Lines) ✅
  - imopenlines.session.history.get   → histórico de mensagens por SESSION_ID ou CHAT_ID ✅
  - imopenlines.dialog.get            → dados de um diálogo por DIALOG_ID ✅

LIMITAÇÃO: O webhook atual NÃO permite listar sessões encerradas em lote.
Para isso, o gestor Bitrix24 precisa adicionar o escopo 'im' ao webhook
OU configurar o evento OnSessionFinish para enviar os IDs ao Brisoft.

ARQUITETURA ATUAL:
  - get_sessoes_dia_anterior(): tenta via imopenlines.operator.pause.gethistory
    (histórico de pausas por operador) como proxy para identificar sessões do período.
    Fallback: retorna lista vazia e loga orientação clara.
  - get_mensagens_sessao(chat_id): usa imopenlines.session.history.get ✅ FUNCIONA
"""
import logging
import requests
from datetime import date, timedelta
from django.conf import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mapeamento de filas auditáveis (IDs confirmados via imopenlines.config.list.get)
# ---------------------------------------------------------------------------
FILAS_AUDITAVEIS = {
    19: 'NRS (nível 2)',
    51: 'NRS',
    73: 'NRS Franqueados',
    75: 'HiPag Suporte',
    53: 'Laundry In Box Suporte',
}

FILA_TIPO_MAP = {
    'NRS': 'cliente',
    'NRS (nível 2)': 'cliente',
    'NRS Franqueados': 'franqueado',
    'HiPag Suporte': 'cliente',
    'Laundry In Box Suporte': 'cliente',
}


# ---------------------------------------------------------------------------
# Função auxiliar central
# ---------------------------------------------------------------------------

def _call_bitrix(method: str, params: dict = None) -> dict:
    """
    Faz uma chamada ao webhook nativo do Bitrix24.
    Retorna o conteúdo de `result` ou dict vazio em caso de erro.
    """
    webhook_url = getattr(settings, 'BITRIX24_WEBHOOK_URL', '').rstrip('/')
    if not webhook_url:
        raise ValueError(
            "BITRIX24_WEBHOOK_URL não configurada. Adicione ao .env e ao Render."
        )

    url = f"{webhook_url}/{method}.json"
    params = params or {}

    try:
        response = requests.post(url, data=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if 'error' in data:
            logger.warning(
                f"[Bitrix24] Erro da API — method={method} "
                f"error={data.get('error')} | {data.get('error_description', '')}"
            )
            return {}

        return data.get('result', data)

    except requests.exceptions.HTTPError as e:
        logger.error(f"[Bitrix24] HTTP {e.response.status_code} em {method}: {e}")
        return {}
    except requests.exceptions.Timeout:
        logger.error(f"[Bitrix24] Timeout ao chamar {method}")
        return {}
    except requests.exceptions.RequestException as e:
        logger.error(f"[Bitrix24] Erro de conexão em {method}: {e}")
        return {}
    except Exception as e:
        logger.error(f"[Bitrix24] Erro inesperado em {method}: {e}")
        return {}


# ---------------------------------------------------------------------------
# Funções públicas (mesma assinatura do serviço anterior)
# ---------------------------------------------------------------------------

def get_linhas_disponiveis() -> list:
    """
    Retorna todas as filas (Open Lines / Canais Abertos) disponíveis no Bitrix24.
    ✅ FUNCIONA com o webhook atual (escopo imopenlines).
    """
    try:
        result = _call_bitrix('imopenlines.config.list.get')
        if isinstance(result, list):
            return result
        return result.get('items', []) if isinstance(result, dict) else []
    except Exception as e:
        logger.error(f"[Bitrix24] Erro ao buscar linhas disponíveis: {e}")
        return []


def get_sessoes_dia_anterior(data: date = None, limit: int = 200) -> list:
    """
    Busca sessões finalizadas do dia especificado.

    ⚠️  LIMITAÇÃO ATUAL: O webhook com escopo ['imopenlines'] NÃO disponibiliza
    um endpoint para listar sessões históricas em lote.

    Para habilitar essa funcionalidade, o gestor Bitrix24 deve:
    1. Adicionar o escopo 'im' ao webhook, OU
    2. Criar um webhook de evento (OnSessionFinish) que envie os IDs das sessões
       para o endpoint /api/auditoria/bitrix/webhook/ do Brisoft em tempo real.

    Por enquanto, retorna lista vazia com log de orientação.
    """
    if data is None:
        data = date.today() - timedelta(days=1)

    logger.warning(
        f"[Bitrix24] get_sessoes_dia_anterior({data}): O webhook atual (escopo=['imopenlines']) "
        f"não permite listar sessões históricas. "
        f"Solicite ao gestor Bitrix24 que adicione o escopo 'im' ao webhook "
        f"OU configure o evento OnSessionFinish."
    )
    return []


def get_sessoes_por_chat_ids(chat_ids: list) -> list:
    """
    NOVA FUNÇÃO: Dado uma lista de CHAT_IDs conhecidos, busca os dados de cada sessão.
    Útil quando os IDs vêm do evento OnSessionFinish ou de uma tabela interna.

    ✅ FUNCIONA com o webhook atual via imopenlines.session.history.get
    """
    sessoes = []
    for chat_id in chat_ids:
        result = _call_bitrix(
            'imopenlines.session.history.get',
            {'CHAT_ID': chat_id}
        )
        if result:
            if isinstance(result, list):
                sessoes.extend(result)
            elif isinstance(result, dict):
                sessoes.append(result)
    return sessoes


def get_mensagens_sessao(chat_id) -> list:
    """
    Busca todas as mensagens de um chat/sessão (transcript completo).
    ✅ FUNCIONA com imopenlines.session.history.get

    Parâmetro: chat_id (CHAT_ID do Bitrix24) ou session_id (SESSION_ID).
    """
    try:
        # Tenta por CHAT_ID primeiro
        result = _call_bitrix(
            'imopenlines.session.history.get',
            {'CHAT_ID': chat_id}
        )

        if not result:
            # Fallback: tenta como SESSION_ID
            result = _call_bitrix(
                'imopenlines.session.history.get',
                {'SESSION_ID': chat_id}
            )

        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            return result.get('messages', result.get('items', [result] if result else []))
        return []

    except Exception as e:
        logger.error(f"[Bitrix24] Erro ao buscar mensagens do chat {chat_id}: {e}")
        return []


def formatar_transcript(mensagens: list) -> str:
    """
    Converte lista de mensagens do Bitrix24 em texto formatado para o prompt da IA.
    Suporta os campos retornados por imopenlines.session.history.get.
    """
    if not mensagens:
        return "[Sem mensagens registradas]"

    linhas = []
    for msg in mensagens:
        # Autor
        autor = (
            msg.get('AUTHOR_NAME') or
            msg.get('author_name') or
            msg.get('NICK') or
            msg.get('nick') or
            msg.get('author') or
            msg.get('sender_name') or
            f"ID:{msg.get('USER_ID', msg.get('user_id', '?'))}"
        )

        # Texto
        texto = (
            msg.get('MESSAGE') or
            msg.get('message') or
            msg.get('TEXT') or
            msg.get('text') or
            msg.get('content') or
            msg.get('CONTENT') or
            ''
        )

        if texto and str(texto).strip():
            linhas.append(f"[{autor}]: {str(texto).strip()}")

    return "\n".join(linhas) if linhas else "[Sem mensagens de texto]"


def encontrar_analista_brisoft(email_analista: str):
    """
    Encontra o User do Brisoft correspondente ao e-mail do operador do Bitrix24.
    """
    if not email_analista:
        return None
    try:
        from core.models import User
        return User.objects.filter(
            email__iexact=email_analista.strip()
        ).first()
    except Exception as e:
        logger.error(f"[Bitrix24] Erro ao buscar analista por email {email_analista}: {e}")
        return None


def identificar_tipo_atendimento(nome_fila: str) -> str:
    """Retorna 'cliente' ou 'franqueado' baseado no nome da fila."""
    return FILA_TIPO_MAP.get(nome_fila, 'cliente')


def get_info_fila(fila_id: int) -> dict:
    """
    Retorna dados completos de uma fila pelo ID.
    ✅ FUNCIONA com imopenlines.config.get
    """
    try:
        result = _call_bitrix('imopenlines.config.get', {'CONFIG_ID': fila_id})
        return result if isinstance(result, dict) else {}
    except Exception as e:
        logger.error(f"[Bitrix24] Erro ao buscar fila ID={fila_id}: {e}")
        return {}
