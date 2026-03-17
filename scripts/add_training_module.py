# Script temporário para adicionar o módulo de treinamento
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestao_reclame_aqui.settings')
django.setup()

from core.models import ArtigoBaseConhecimento, Department, User

# Get department NRS Suporte
department = Department.objects.filter(name='NRS Suporte').first()

# Get an admin user
admin_user = User.objects.filter(role='administrador').first()

if not department:
    print("Erro: Departamento 'NRS Suporte' não encontrado!")
    exit(1)

if not admin_user:
    print("Erro: Usuário administrador não encontrado!")
    exit(1)

# Conteúdo do módulo
content = """Desenvolva habilidades essenciais para transformar cada interação em uma experiência positiva, profissional e orientada à solução.

### Objetivo do Módulo

**Postura e Comunicação**

Desenvolver técnicas eficazes de comunicação clara e postura profissional, fundamentais para um atendimento de excelência.

**Redução de Conflitos**

Acelerar diagnósticos e melhorar a experiência do franqueado por meio de técnicas comprovadas de atendimento e desescalada.

**Consultor Técnico**

Evoluir de um perfil operacional para um consultor técnico estratégico, agregando valor real ao negócio da franquia.

### Entendendo Quem Você Atende

**Cliente Final**

- Busca lavar e secar roupas de forma rápida e prática
- Precisa de soluções simples e objetivas  
- Evite termos técnicos complexos
- Nunca solicite procedimentos impossíveis, como abertura de máquinas

**Franqueado**

- Atua como investidor, com foco em ROI
- Prioriza faturamento e eficiência operacional
- Espera explicações claras, lógicas e seguras
- Busca diagnósticos precisos, não suposições

### Fundamentos da Boa Comunicação

**Clareza na Mensagem**

- Utilize frases diretas e objetivas.
- Evite textos longos e confusos.
- Prefira listas, tópicos e instruções numeradas, sempre que possível.

**Tom de Voz Adequado**

Mantenha uma postura:
- Profissional
- Educada
- Simples e respeitosa

Evite gírias excessivas, ironia, sarcasmo ou respostas secas que prejudiquem o relacionamento.

**Regra das 2 Leituras**

Antes de responder:
1. Leia a mensagem por completo
2. Releia para garantir total compreensão
3. Havendo dúvida, peça esclarecimentos antes de agir

**A Regra do "Informe Sempre"**

Nunca deixe o franqueado ou o cliente sem retorno.

A comunicação contínua reduz ansiedade e diminui significativamente reclamações.

Exemplos de mensagens adequadas:
- "Estou analisando o seu caso, peço um momento."
- "Estou testando a ESP da secadora."
- "Verificando a configuração do Mikrotik."

### Comunicação Escrita – Padrão TI 60 Minutos

1. **Saudação breve** - Inicie com um cumprimento cordial
2. **Confirmação do problema** - Demonstre que compreendeu a situação
3. **Ação imediata** - Informe claramente o que será feito
4. **Retorno do teste** - Atualize sobre os resultados obtidos
5. **Confirmação** - Valide a solução com o franqueado
6. **Fechamento** - Encerre de forma educada e profissional

**Exemplo Prático:**

"Bom dia! Verifiquei que a lavadora 654 da loja PB05 não está respondendo ao comando de liberação. Peço, por favor, que a desligue da tomada por 1 minuto e ligue novamente. Assim que finalizar, me avise para que eu realize o teste de conexão."

### Inteligência Emocional no Suporte

**O Franqueado Irritado**

Lembre-se: A insatisfação não é pessoal, mas sim resultado do impacto financeiro que a falha causa no negócio.

**Técnica de Desescalada:**

1. Ouça ou leia com atenção, sem interromper
2. Valide a frustração do franqueado
3. Transmita segurança técnica
4. Demonstre ação imediata e objetiva
5. Evite justificativas longas

**Exemplo:** "Entendo sua preocupação. Vamos resolver juntos. Já estou verificando a rede da loja."

### Gestão de Conflitos

**O Que Nunca Fazer:**

- Culpar o franqueado
- Dizer "não sei" sem escalar o problema
- Prometer prazos irreais
- Ignorar reclamações legítimas
- Entrar em confronto direto

**Como Proceder Corretamente:**

- Manter neutralidade e profissionalismo
- Ser educado mesmo em situações tensas
- Escalar para o supervisor quando necessário
- Registrar todas as ações no Bitrix
- Focar sempre na solução, não no problema

### Etiqueta em Calls e Google Meet

**Antes da Call:**

- Testar microfone e áudio
- Utilizar fundo institucional ou blur
- Windows preparado para gravação

**Durante a Call:**

- Falar de forma clara e pausada
- Não comer, deitar ou demonstrar desatenção
- Apresentar soluções passo a passo
- Manter postura totalmente profissional

**Após a Call:**

- Salvar a gravação no sistema
- Informar o status final ao franqueado
- Finalizar o chamado e fechar o card

### Postura do Analista

**O Que Você Representa:**

- Segurança técnica da loja
- Garantia de funcionamento
- Suporte direto ao faturamento da franquia
- Referência técnica para o franqueado

**Mentalidade Profissional:**

- Diagnóstico rápido e preciso
- Comunicação clara e objetiva
- Registro completo das ações
- Postura assertiva e respeitosa

### Encerramento do Módulo

Valide seu aprendizado utilizando o checklist abaixo:

✅ **Clareza na Comunicação** - Respondo de forma clara e objetiva?

✅ **Técnica de Desescalada** - Aplico corretamente em situações de conflito?

✅ **Comunicação Constante** - Informo o status durante análises?

✅ **Postura Profissional** - Mantenho consistência no atendimento?

✅ **Documentação Completa** - Registro todas as ações no Bitrix?
"""

# Criar o artigo
article = ArtigoBaseConhecimento.objects.create(
    titulo='Módulo – A Arte do Atendimento',
    conteudo=content,
    categoria='training',
    tags='atendimento, comunicação, treinamento, profissionalismo, suporte',
    department=department,
    usuario=admin_user
)

print(f"✅ Módulo criado com sucesso! ID: {article.id}")
print(f"   Título: {article.titulo}")
print(f"   Categoria: {article.categoria}")
print(f"   Departamento: {department.name}")
