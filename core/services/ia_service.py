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


def chatbot_kb(pergunta: str, artigos: list, nome_usuario: str = "", historico: list = None) -> str:
    """
    Responde a uma pergunta do analista com base nos artigos da Base de Conhecimento.

    Args:
        pergunta: Texto da pergunta do usuário.
        artigos: Lista de dicts com 'titulo' e 'conteudo' dos artigos.
        nome_usuario: Nome do usuário para tornar o atendimento personalizado.
        historico: Lista de mensagens anteriores para contexto (ex: [{'role': 'user', 'content': '...'}])

    Returns:
        Texto da resposta gerada pela IA.
    """
    try:
        client = _get_client()
        historico = historico or []

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

        saudacao_nome = f"Você está conversando com {nome_usuario}." if nome_usuario else ""
        
        texto_historico = ""
        regra_historico = ""
        if historico:
            regra_historico = "6. Como já existe um histórico de conversa, NÃO repita saudações ou apresentações iniciais. Responda diretamente à nova pergunta continuando o assunto."
            texto_historico = "HISTÓRICO RECENTE DA CONVERSA:\n"
            # Pega as últimas 10 mensagens para não pesar
            for msg in historico[-10:]:
                role_name = "Usuário" if msg.get('role') == 'user' else "Nexus IA"
                texto_historico += f"[{role_name}]: {msg.get('content')}\n\n"

        prompt = f"""Você é o Nexus IA, um assistente virtual humano, empático e extremamente prestativo da rede de lavanderias Hi Lavanderia.
Você conversa como uma pessoa real, um colega de trabalho sênior que está ajudando um analista de suporte a resolver problemas.
{saudacao_nome}

REGRAS DE OURO DA SUA PERSONALIDADE:
1. Seja sempre amigável e natural. Trate o usuário pelo nome e comece as respostas com saudações leves ou confirmando o entendimento (ex: "Fala [nome do usuário], claro, vamos resolver isso!", "Entendi a situação, [nome do usuário].", "Pode deixar que eu te ajudo com isso.").
2. NUNCA pareça um robô que apenas copia e cola texto. Leia o artigo e explique com suas próprias palavras de forma didática e clara.
3. Use formatação limpa e organizada (tópicos curtos, negrito nas partes importantes).
4. Se o analista não der detalhes suficientes, pergunte gentilmente.
5. Responda APENAS com base nos conhecimentos da base fornecida abaixo. Se a informação não estiver lá, diga algo como: "Poxa, eu dei uma olhada na nossa base de conhecimento e não encontrei um procedimento oficial para isso. Acho melhor você confirmar com o seu gestor, tudo bem?"
{regra_historico}

BASE DE CONHECIMENTO DO DEPARTAMENTO (USE ISSO PARA BASEAR SUA RESPOSTA):
{contexto}

{texto_historico}
O ANALISTA PERGUNTOU/FALOU:
{pergunta}

SUA RESPOSTA HUMANA E PRESTATIVA:"""

        response = client.models.generate_content(
            model='gemini-flash-latest',
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
            model='gemini-flash-latest',
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
