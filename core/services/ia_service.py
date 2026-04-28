"""
Serviço de Inteligência Artificial — Nexus
Integração com Google Gemini (SDK google-genai) para chatbot da KB
e classificação automática de reclamações.
"""
import json
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def _get_client():
    """Retorna o cliente Gemini configurado com o novo SDK google-genai."""
    from google import genai
    api_key = getattr(settings, 'GEMINI_API_KEY', '')
    if not api_key:
        raise ValueError("GEMINI_API_KEY não configurada. Adicione ao .env e ao Render.")
    return genai.Client(api_key=api_key)


def chatbot_kb(pergunta: str, artigos: list) -> str:
    """
    Responde a uma pergunta do analista com base nos artigos da Base de Conhecimento.

    Args:
        pergunta: Texto da pergunta do usuário.
        artigos: Lista de dicts com 'titulo' e 'conteudo' dos artigos.

    Returns:
        Texto da resposta gerada pela IA.
    """
    try:
        client = _get_client()

        # Montar contexto com no máximo 25 artigos para não estourar tokens
        artigos_contexto = artigos[:25]
        if not artigos_contexto:
            return (
                "A base de conhecimento ainda não possui artigos cadastrados. "
                "Peça ao seu gestor para adicionar conteúdo na seção Suporte."
            )

        contexto = "\n\n---\n\n".join([
            f"**{a.get('titulo', 'Sem título')}**\n{a.get('conteudo', '')}"
            for a in artigos_contexto
        ])

        prompt = f"""Você é o Assistente Nexus IA, um assistente interno especializado em suporte ao cliente de uma rede de lavanderias chamada Hi Lavanderia.

Seu papel é ajudar os analistas de suporte a encontrar respostas rápidas com base na base de conhecimento interna.

REGRAS IMPORTANTES:
- Responda APENAS com base nos artigos fornecidos abaixo.
- Se a resposta não estiver nos artigos, diga claramente: "Não encontrei essa informação na base de conhecimento. Recomendo consultar seu gestor."
- Use linguagem profissional, direta e em português brasileiro.
- Seja objetivo — evite respostas longas demais.
- Quando relevante, cite o nome do artigo de onde veio a informação.

BASE DE CONHECIMENTO:
{contexto}

PERGUNTA DO ANALISTA:
{pergunta}

RESPOSTA:"""

        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt
        )
        return response.text.strip()

    except ValueError as e:
        logger.error(f"[Nexus IA] Configuração inválida: {e}")
        return "⚠️ O assistente de IA não está configurado. Entre em contato com o administrador do sistema."
    except Exception as e:
        logger.error(f"[Nexus IA] Erro no chatbot: {type(e).__name__}: {e}")
        return f"⚠️ Ocorreu um erro ao processar sua pergunta ({type(e).__name__}). Tente novamente em instantes."


def classificar_reclamacao(descricao: str, tipo_reclamacao: str) -> dict:
    """
    Classifica uma reclamação do Reclame Aqui, definindo urgência e sentimento.

    Args:
        descricao: Texto da reclamação do cliente.
        tipo_reclamacao: Tipo da reclamação (ex: 'lavagem', 'pagamento_cartao').

    Returns:
        Dict com 'urgencia' e 'sentimento', ou valores padrão em caso de erro.
    """
    try:
        client = _get_client()

        prompt = f"""Analise esta reclamação de cliente de uma rede de lavanderias e classifique-a.

TIPO DA RECLAMAÇÃO: {tipo_reclamacao}
DESCRIÇÃO: {descricao}

Retorne APENAS um objeto JSON válido, sem markdown, sem texto extra, exatamente neste formato:
{{"urgencia": "VALOR", "sentimento": "VALOR"}}

Valores possíveis para "urgencia":
- "baixa" → dúvida simples, problema já resolvido ou cliente cordial
- "media" → problema moderado, aguardando solução, sem ameaça
- "alta" → cliente muito insatisfeito, ameaça de não voltar, problema grave
- "critica" → ameaça processual, dano financeiro alto, post viral, risco reputacional grave

Valores possíveis para "sentimento":
- "satisfeito" → cliente cordial mesmo relatando problema
- "neutro" → tom neutro, apenas descrevendo a situação
- "frustrado" → claramente irritado mas controlado
- "muito_irritado" → extremamente irritado, agressivo, usa caps lock ou palavrões

RESPONDA APENAS COM O JSON:"""

        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt
        )
        texto = response.text.strip()

        # Limpar markdown se presente
        if "```" in texto:
            texto = texto.split("```")[1]
            if texto.startswith("json"):
                texto = texto[4:]
            texto = texto.strip()

        resultado = json.loads(texto)

        # Validar valores
        urgencias_validas = {'baixa', 'media', 'alta', 'critica'}
        sentimentos_validos = {'satisfeito', 'neutro', 'frustrado', 'muito_irritado'}

        urgencia = resultado.get('urgencia', 'media')
        sentimento = resultado.get('sentimento', 'neutro')

        if urgencia not in urgencias_validas:
            urgencia = 'media'
        if sentimento not in sentimentos_validos:
            sentimento = 'neutro'

        return {'urgencia': urgencia, 'sentimento': sentimento}

    except ValueError as e:
        logger.error(f"[Nexus IA] Configuração inválida: {e}")
        return {'urgencia': 'media', 'sentimento': 'neutro', 'erro': 'api_key_missing'}
    except Exception as e:
        logger.error(f"[Nexus IA] Erro na classificação: {type(e).__name__}: {e}")
        return {'urgencia': 'media', 'sentimento': 'neutro', 'erro': str(e)}
