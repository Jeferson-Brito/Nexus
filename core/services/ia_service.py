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


def chatbot_kb(pergunta: str, artigos: list, user_context: dict = None, historico: list = None) -> dict:
    """
    Responde a uma pergunta do analista com base nos artigos da Base de Conhecimento,
    ou executa ações baseadas nas intenções do usuário (Function Calling).

    Args:
        pergunta: Texto da pergunta do usuário.
        artigos: Lista de dicts com 'titulo' e 'conteudo' dos artigos.
        user_context: Dicionário contendo dados do usuário logado.
        historico: Lista de mensagens anteriores para contexto.

    Returns:
        Um dict com 'resposta' (texto) e opcionalmente 'action' (ação para o frontend).
    """
    try:
        from google.genai import types
        client = _get_client()
        historico = historico or []
        user_context = user_context or {}

        # Montar contexto com no máximo 25 artigos para não estourar tokens
        artigos_contexto = artigos[:25]
        if not artigos_contexto:
            return {
                "resposta": "A base de conhecimento ainda não possui artigos cadastrados. Peça ao seu gestor para adicionar conteúdo na seção Suporte."
            }

        contexto = "\n\n---\n\n".join([
            f"**{a.get('titulo', 'Sem título')}**\n{a.get('conteudo', '')}"
            for a in artigos_contexto
        ])

        nome = user_context.get('nome', '')
        email = user_context.get('email', '')
        cargo = user_context.get('cargo', '')
        departamento = user_context.get('departamento', '')

        perfil_usuario = ""
        if nome:
            perfil_usuario = f"\nPERFIL DO USUÁRIO ATUAL:\n- Nome: {nome}\n- E-mail: {email}\n- Cargo: {cargo}\n- Departamento: {departamento}\n"

        texto_historico = ""
        regra_historico = ""
        if historico:
            regra_historico = "6. Como já existe um histórico de conversa, NÃO repita saudações ou apresentações iniciais. Responda diretamente à nova pergunta."
            texto_historico = "HISTÓRICO RECENTE DA CONVERSA:\n"
            for msg in historico[-10:]:
                role_name = "Usuário" if msg.get('role') == 'user' else "Nexus IA"
                texto_historico += f"[{role_name}]: {msg.get('content')}\n\n"

        prompt = f"""Você é o Nexus IA, um assistente virtual humano, empático e extremamente prestativo da rede de lavanderias Hi Lavanderia.
Você conversa como uma pessoa real e é um assistente proativo.
{perfil_usuario}

REGRAS DE OURO DA SUA PERSONALIDADE:
1. Seja sempre amigável e natural. Trate o usuário pelo nome (se fornecido).
2. NUNCA pareça um robô que apenas copia e cola texto. Leia o artigo e explique com suas próprias palavras.
3. Use formatação limpa e organizada.
4. Se o usuário pedir para você executar alguma ação no sistema (ex: mudar a senha, navegar para uma tela), USE AS FERRAMENTAS DISPONÍVEIS. Nunca diga como fazer se você mesmo puder executar a ferramenta para ele.
5. Responda perguntas APENAS com base nos conhecimentos da base fornecida abaixo.
{regra_historico}

BASE DE CONHECIMENTO DO DEPARTAMENTO:
{contexto}

{texto_historico}
O USUÁRIO PERGUNTOU/FALOU:
{pergunta}

SUA RESPOSTA HUMANA E PRESTATIVA:"""

        def navegar_para_tela(nome_da_tela: str) -> str:
            """
            Navega o usuário para uma tela específica do sistema. 
            Telas disponíveis: 'inicio' (dashboard principal), 'configuracoes_ia' (Base IA), 'inconsistencias'.
            """
            return f"Navegação para {nome_da_tela} acionada."

        def alterar_senha_usuario(nova_senha: str) -> str:
            """
            Altera a senha do usuário logado no sistema para a nova_senha fornecida.
            A nova senha deve ter no mínimo 6 caracteres.
            """
            return "Senha alterada acionada."

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[navegar_para_tela, alterar_senha_usuario]
            )
        )

        # Processar se a IA chamou alguma ferramenta
        if response.function_calls:
            fc = response.function_calls[0]
            args = fc.args if isinstance(fc.args, dict) else dict(fc.args)

            if fc.name == 'navegar_para_tela':
                tela = args.get('nome_da_tela', '')
                url = '/'
                if 'ia' in tela.lower():
                    url = '/configuracoes/ia-base/'
                elif 'inconsistencia' in tela.lower():
                    url = '/rh/inconsistencias/'
                
                return {
                    "resposta": f"Claro, estou te redirecionando agora mesmo para lá!",
                    "action": {"type": "navigate", "url": url}
                }
            elif fc.name == 'alterar_senha_usuario':
                nova_senha = args.get('nova_senha', '')
                if len(nova_senha) < 6:
                    return {
                        "resposta": "A senha precisa ter pelo menos 6 caracteres. Por favor, escolha outra."
                    }
                return {
                    "resposta": "Prontinho! Sua senha foi alterada com sucesso no sistema.",
                    "action": {"type": "change_password", "nova_senha": nova_senha}
                }

        return {
            "resposta": response.text.strip()
        }

    except ValueError as e:
        logger.error(f"[Nexus IA] Configuração inválida: {e}")
        return {"resposta": "⚠️ O assistente de IA não está configurado. Entre em contato com o administrador do sistema."}
    except Exception as e:
        logger.error(f"[Nexus IA] Erro no chatbot: {type(e).__name__}: {e}")
        return {"resposta": f"⚠️ Ocorreu um erro ao processar sua pergunta ({type(e).__name__}). Tente novamente em instantes."}


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
