"""
Serviço de Inteligência Artificial — Nexus
Integração com Google Gemini (SDK google-genai) para chatbot da KB,
classificação de reclamações e auditoria autônoma de atendimentos.
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
    """
    try:
        from google.genai import types
        client = _get_client()
        historico = historico or []
        user_context = user_context or {}

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
            regra_historico = "6. NÃO repita saudações se já houver histórico. Responda direto."
            texto_historico = "HISTÓRICO RECENTE DA CONVERSA:\n"
            for msg in historico[-10:]:
                role_name = "Usuário" if msg.get('role') == 'user' else "Nexus IA"
                texto_historico += f"[{role_name}]: {msg.get('content')}\n\n"

        prompt = f"""Você é o Nexus IA, um assistente virtual proativo e empático.
{perfil_usuario}

REGRAS DE OURO DA COMUNICAÇÃO:
1. Trate o usuário pelo nome e mantenha um tom caloroso, amigável e natural.
2. INSTRUÇÃO CRÍTICA SOBRE AÇÕES: Se o usuário pedir para navegar ou alterar dados, VOCÊ É OBRIGADO A CHAMAR A FUNÇÃO CORRESPONDENTE. NUNCA responda dizendo "eu fiz" em texto se não invocou a ferramenta.
3. Você pode:
   - Navegar para qualquer tela (Início, Auditoria, Kanban, Escala, Ponto, Reclamações, IA).
   - Alterar dados do próprio perfil (nome, sobrenome).
   - Alterar dados de reclamações (status, urgência) se souber o ID.
   - Alterar dados de tarefas (concluir, mudar prioridade) se souber o ID.
   - Alterar senha.
4. Responda perguntas APENAS com base nos conhecimentos da base fornecida abaixo.
{regra_historico}

REGRAS DE FORMATAÇÃO VISUAL:
- Use listas com bullets ("•" ou "-"). NUNCA use asteriscos ("*").
- Use parágrafos curtos.
- Vá direto ao ponto.

BASE DE CONHECIMENTO DO DEPARTAMENTO:
{contexto}

{texto_historico}
O USUÁRIO PERGUNTOU/FALOU:
{pergunta}

SUA RESPOSTA:"""

        tool_actions = types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name='navegar_para_tela',
                    description="Redireciona o usuário para uma tela específica do sistema.",
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            'destino': types.Schema(type=types.Type.STRING, description="Nome da tela: 'inicio', 'auditoria', 'kanban', 'escala', 'ponto', 'inconsistencias', 'reclamacoes', 'configuracoes_ia', 'refunds'.")
                        },
                        required=['destino']
                    )
                ),
                types.FunctionDeclaration(
                    name='alterar_dados_sistema',
                    description="Altera dados de entidades no banco de dados (Usuário, Reclamação, Tarefa, etc).",
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            'entidade': types.Schema(type=types.Type.STRING, description="Tipo da entidade: 'usuario', 'reclamacao', 'tarefa', 'evento'."),
                            'id': types.Schema(type=types.Type.STRING, description="ID da entidade (opcional para 'usuario' se for o próprio)."),
                            'campos': types.Schema(type=types.Type.STRING, description="Objeto JSON com campos e valores a alterar. Ex: '{\"first_name\": \"João\", \"status\": \"resolvido\"}'")
                        },
                        required=['entidade', 'campos']
                    )
                ),
                types.FunctionDeclaration(
                    name='alterar_senha_usuario',
                    description="Altera a senha do usuário logado.",
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            'nova_senha': types.Schema(type=types.Type.STRING, description="A nova senha (mínimo 6 caracteres).")
                        },
                        required=['nova_senha']
                    )
                )
            ]
        )

        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(tools=[tool_actions])
            )
        except Exception as e:
            if "503" in str(e) or "UNAVAILABLE" in str(e):
                logger.warning("[Nexus IA] Fallback para gemini-1.5-flash...")
                response = client.models.generate_content(
                    model='gemini-1.5-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(tools=[tool_actions])
                )
            else:
                raise e

        if response.function_calls:
            fc = response.function_calls[0]
            args = fc.args if isinstance(fc.args, dict) else dict(fc.args)

            if fc.name == 'navegar_para_tela':
                destino = args.get('destino', '').lower()
                mapping = {
                    'inicio': '/', 'dashboard': '/', 'auditoria': '/auditoria/atendimentos/',
                    'kanban': '/kanban/', 'tarefas': '/kanban/', 'escala': '/rh/escala/',
                    'ponto': '/rh/ponto/', 'inconsistencias': '/rh/inconsistencias/',
                    'reclamacoes': '/reclamacoes/', 'reclamacoes_lista': '/reclamacoes/',
                    'configuracoes_ia': '/configuracoes/ia-base/', 'ia': '/configuracoes/ia-base/',
                    'refunds': '/rh/refunds/', 'estornos': '/rh/refunds/'
                }
                url = mapping.get(destino, '/')
                return {"resposta": f"Sem problemas! Estou te levando para a tela de {destino} agora mesmo.", "action": {"type": "navigate", "url": url}}

            elif fc.name == 'alterar_dados_sistema':
                try:
                    campos_dict = json.loads(args.get('campos', '{}'))
                    return {"resposta": f"Entendido. Vou processar a alteração de {args.get('entidade')} agora.", "action": {"type": "update_data", "entidade": args.get('entidade'), "id": args.get('id'), "campos": campos_dict}}
                except:
                    return {"resposta": "Houve um erro ao processar os dados da alteração. Poderia repetir?"}

            elif fc.name == 'alterar_senha_usuario':
                nova_senha = args.get('nova_senha', '')
                if len(nova_senha) < 6:
                    return {"resposta": "A senha precisa ter pelo menos 6 caracteres. Por favor, escolha outra."}
                return {"resposta": "Prontinho! Sua senha foi alterada com sucesso no sistema.", "action": {"type": "change_password", "nova_senha": nova_senha}}

        return {"resposta": response.text.strip()}

    except ValueError as e:
        logger.error(f"[Nexus IA] Configuração inválida: {e}")
        return {"resposta": "⚠️ O assistente de IA não está configurado. Entre em contato com o administrador do sistema."}
    except Exception as e:
        logger.error(f"[Nexus IA] Erro no chatbot: {type(e).__name__}: {e}")
        return {"resposta": f"⚠️ Ocorreu um erro ao processar sua pergunta ({type(e).__name__}). Tente novamente em instantes."}


def classificar_reclamacao(descricao: str, tipo_reclamacao: str) -> dict:
    """Classifica uma reclamação do Reclame Aqui, definindo urgência e sentimento."""
    try:
        client = _get_client()
        prompt = f"""Analise esta reclamação de cliente de uma rede de lavanderias e classifique-a.

TIPO DA RECLAMAÇÃO: {tipo_reclamacao}
DESCRIÇÃO: {descricao}

Retorne APENAS um objeto JSON válido, sem markdown, sem texto extra, exatamente neste formato:
{{"urgencia": "VALOR", "sentimento": "VALOR"}}

Valores possíveis para "urgencia": "baixa", "media", "alta", "critica"
Valores possíveis para "sentimento": "satisfeito", "neutro", "frustrado", "muito_irritado"

RESPONDA APENAS COM O JSON:"""

        response = client.models.generate_content(model='gemini-flash-latest', contents=prompt)
        texto = response.text.strip()
        if "```" in texto:
            texto = texto.split("```")[1]
            if texto.startswith("json"): texto = texto[4:]
            texto = texto.strip()

        resultado = json.loads(texto)
        urgencias_validas = {'baixa', 'media', 'alta', 'critica'}
        sentimentos_validos = {'satisfeito', 'neutro', 'frustrado', 'muito_irritado'}
        urgencia = resultado.get('urgencia', 'media')
        sentimento = resultado.get('sentimento', 'neutro')
        if urgencia not in urgencias_validas: urgencia = 'media'
        if sentimento not in sentimentos_validos: sentimento = 'neutro'
        return {'urgencia': urgencia, 'sentimento': sentimento}

    except ValueError as e:
        logger.error(f"[Nexus IA] Configuração inválida: {e}")
        return {'urgencia': 'media', 'sentimento': 'neutro', 'erro': 'api_key_missing'}
    except Exception as e:
        logger.error(f"[Nexus IA] Erro na classificação: {type(e).__name__}: {e}")
        return {'urgencia': 'media', 'sentimento': 'neutro', 'erro': str(e)}


def gerar_avaliacao_auditoria(analista_nome: str, historico_auditorias: list, metricas: dict) -> dict:
    """Avalia o histórico de auditorias de um analista e gera um feedback humanizado."""
    try:
        client = _get_client()
        resumo_falhas = ""
        for crit, contagem in metricas.get('criterios_analise', {}).items():
            if contagem['falhas'] > 0:
                taxa = (contagem['falhas'] / (contagem['ok'] + contagem['falhas'])) * 100
                resumo_falhas += f"- {crit.replace('_', ' ').title()}: {contagem['falhas']} falhas ({taxa:.1f}% de erro)\n"
        if not resumo_falhas:
            resumo_falhas = "- Nenhuma falha registrada no período! Desempenho impecável.\n"

        detalhes_historico = ""
        for aud in historico_auditorias[:5]:
            falhas = ", ".join(aud.get('falhas_registradas', []))
            if not falhas: falhas = "Nenhuma falha"
            detalhes_historico += f"Data: {aud['data'][:10]} | Nota: {aud['nota']} | Classificação: {aud['classificacao']} | Observações: {falhas}\n"

        prompt = f"""Você é o Nexus IA, atuando como um Mentor de Qualidade e Desempenho Senior.
Sua tarefa é analisar os dados de auditoria recentes do analista '{analista_nome}' e gerar um relatório de feedback estruturado para o Gestor repassar ao Analista no One-on-One.

DADOS DA ANÁLISE:
- Total de Auditorias no Período: {metricas.get('total_avaliado')}
- Nota Média: {metricas.get('nota_media_periodo')}/100

PRINCIPAIS PONTOS DE ATENÇÃO (Falhas por critério):
{resumo_falhas}

AMOSTRA DAS ÚLTIMAS AUDITORIAS (Máx 5):
{detalhes_historico}

REGRAS DE RESPOSTA:
- Retorne APENAS texto formatado em Markdown.
- Tom construtivo, focado em desenvolvimento.
- Estrutura obrigatória: ### 🌟 Visão Geral / ### ✅ Pontos Fortes / ### 🎯 Áreas de Melhoria e Riscos / ### 🚀 Plano de Ação Prático"""

        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return {"resposta": response.text.strip()}

    except ValueError as e:
        logger.error(f"[Nexus IA] Configuração inválida: {e}")
        return {"resposta": "⚠️ A integração com a IA não está configurada."}
    except Exception as e:
        logger.error(f"[Nexus IA] Erro ao gerar avaliação: {type(e).__name__}: {e}")
        return {"resposta": "⚠️ Ocorreu um erro ao processar a avaliação com a IA."}


def auditar_chat_automatico(
    transcript: str,
    tipo_atendimento: str,
    base_auditoria: list,
    analista_nome: str = "Analista",
) -> dict:
    """
    Audita automaticamente um chat de atendimento com base nos 9 critérios.

    Args:
        transcript: Texto formatado do chat (mensagens concatenadas).
        tipo_atendimento: 'cliente' ou 'franqueado'.
        base_auditoria: Lista de dicts com 'titulo', 'conteudo' e 'categoria' da base de auditoria.
        analista_nome: Nome do analista para contextualizar a análise.

    Returns:
        Dict com os 9 critérios (bool) + justificativas + campo 'sucesso'.
    """
    try:
        client = _get_client()

        if base_auditoria:
            base_texto = "\n\n".join([
                f"[{a.get('categoria', 'geral').upper()}] {a.get('titulo', '')}:\n{a.get('conteudo', '')}"
                for a in base_auditoria
            ])
        else:
            base_texto = "Sem base de conhecimento configurada. Use boas práticas de atendimento ao cliente."

        tipo_label = "Cliente" if tipo_atendimento == 'cliente' else "Franqueado"

        prompt = f"""Você é o Nexus IA Auditor, um sistema especialista em avaliação de qualidade de atendimento.

Analise o transcript de um atendimento do tipo **{tipo_label}** realizado pelo analista **{analista_nome}** e avalie os 9 critérios de qualidade.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BASE DE CONHECIMENTO E REGRAS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{base_texto}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TRANSCRIPT DO ATENDIMENTO:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{transcript}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRITÉRIOS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. apresentou_corretamente — Apresentou-se corretamente no início?
2. analisou_historico — Demonstrou ter analisado o histórico?
3. entendeu_solicitacao — Entendeu e tratou a solicitação do {tipo_label.lower()}?
4. informacao_clara — Informações passadas foram claras e completas?
5. acordo_espera — Realizou acordo de espera corretamente? (Se não houve espera: true)
6. atendimento_respeitoso — Manteve tom respeitoso e profissional?
7. portugues_correto — Usou a língua portuguesa corretamente?
8. finalizacao_correta — Finalizou o atendimento adequadamente?
9. procedimento_correto — Seguiu os procedimentos corretos?

Retorne EXCLUSIVAMENTE um JSON válido, sem markdown, sem texto extra:

{{
  "apresentou_corretamente": true,
  "erro_apresentacao": "",
  "analisou_historico": true,
  "erro_historico": "",
  "entendeu_solicitacao": true,
  "erro_entendimento": "",
  "informacao_clara": true,
  "erro_informacao": "",
  "acordo_espera": true,
  "erro_acordo_espera": "",
  "atendimento_respeitoso": true,
  "erro_respeito": "",
  "portugues_correto": true,
  "erro_portugues": "",
  "finalizacao_correta": true,
  "erro_finalizacao": "",
  "procedimento_correto": true,
  "erro_procedimento": ""
}}

REGRAS: true = atendeu, false = não atendeu. Campos erro_X: vazio se true, 1-2 frases específicas se false. Só marque false com evidência clara no transcript.

RESPONDA APENAS COM O JSON:"""

        try:
            response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        except Exception as e:
            if "503" in str(e) or "UNAVAILABLE" in str(e):
                logger.warning("[Nexus IA Auditor] Fallback para gemini-1.5-flash")
                response = client.models.generate_content(model='gemini-1.5-flash', contents=prompt)
            else:
                raise e

        texto = response.text.strip()
        if "```" in texto:
            partes = texto.split("```")
            for parte in partes:
                if '{' in parte:
                    texto = parte
                    if texto.startswith("json"): texto = texto[4:]
                    texto = texto.strip()
                    break

        resultado = json.loads(texto)

        # Garantir todos os campos obrigatórios
        campos_bool = ['apresentou_corretamente', 'analisou_historico', 'entendeu_solicitacao',
                       'informacao_clara', 'acordo_espera', 'atendimento_respeitoso',
                       'portugues_correto', 'finalizacao_correta', 'procedimento_correto']
        campos_erro = ['erro_apresentacao', 'erro_historico', 'erro_entendimento',
                       'erro_informacao', 'erro_acordo_espera', 'erro_respeito',
                       'erro_portugues', 'erro_finalizacao', 'erro_procedimento']

        for campo in campos_bool:
            if campo not in resultado:
                resultado[campo] = True
        for campo in campos_erro:
            if campo not in resultado:
                resultado[campo] = ''

        resultado['sucesso'] = True
        return resultado

    except json.JSONDecodeError as e:
        logger.error(f"[Nexus IA Auditor] JSON inválido: {e}")
        return {'sucesso': False, 'erro': f'JSON inválido: {e}'}
    except ValueError as e:
        logger.error(f"[Nexus IA Auditor] Config inválida: {e}")
        return {'sucesso': False, 'erro': str(e)}
    except Exception as e:
        logger.error(f"[Nexus IA Auditor] Erro: {type(e).__name__}: {e}")
        return {'sucesso': False, 'erro': str(e)}
