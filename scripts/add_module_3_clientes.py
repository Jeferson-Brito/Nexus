# Script para adicionar o Módulo 3 Clientes
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestao_reclame_aqui.settings')
django.setup()

from core.models import ArtigoBaseConhecimento, Department, User

# Get department
department = Department.objects.filter(name='NRS Suporte').first()
admin_user = User.objects.filter(role='administrador').first()

if not department or not admin_user:
    print("Erro: Departamento ou usuário não encontrado!")
    exit(1)

# Conteúdo do módulo
content = """**Setor:** NRS 3 Lavanderia 60 Minutos

**Objetivo:** Padronizar o atendimento e a execução de procedimentos relacionados aos clientes, garantindo agilidade, clareza e registro correto das ocorrências.

Este documento consolida todos os processos essenciais do Núcleo de Relacionamento com o Cliente, servindo como guia completo para a equipe de TI e Helpdesk. Aqui você encontrará procedimentos detalhados desde a emissão de nota fiscal até resolução de problemas técnicos nas máquinas, sempre com foco na excelência do atendimento.

### 1. Nota Fiscal

**1.1 Cliente não recebeu a nota fiscal**

Este é um dos contatos mais comuns no atendimento. O procedimento correto garante que o cliente receba seu documento fiscal sem demora.

**Passos iniciais:**

1. Solicite o CPF do cliente
2. Acesse o sistema administrativo
3. Localize a compra correspondente
4. Verifique o status de emissão

**Se a nota foi emitida:**

- Clique no ícone da Nota Fiscal
- Efetue o download do arquivo
- Encaminhe ao cliente
- Gere ocorrência ao CS

**Se a nota NÃO foi emitida:**

- Execute procedimento de reemissão
- Se conseguir: baixe e envie ao cliente
- Se não: oriente envio de e-mail para atendimento@lavanderia60minutos.com.br
- Gere ocorrência

### 2. Cadastro de Clientes

**2.1 Alteração de Senha**

⚠️ **Segurança em primeiro lugar:** Apenas o titular da conta pode alterar dados. Sempre confirme a identidade antes de prosseguir.

**Procedimento:**

1. Solicite o CPF do cliente
2. Solicite uma nova senha de 4 dígitos
3. Altere no sistema administrativo

**2.2 Alteração de Dados de Contato**

⚠️ **Atenção:** A validação da identidade é essencial para proteger os dados do cliente.

**Procedimento:**

1. Solicite o CPF do cliente
2. Verifique qual informação precisa ser atualizada
3. Faça a alteração no sistema administrativo

❗ **Importante:** Apenas o titular da conta pode solicitar alterações de senha ou dados pessoais. Confirme sempre a identidade antes de realizar qualquer modificação no cadastro.

### 3. Problemas na Infraestrutura

**3.1 Ar-condicionado não liga ao inserir CPF**

**01 - Acesso Remoto**

Conecte-se ao totem da loja remotamente

**02 - Teste de Ping**

Execute teste de conectividade no ar-condicionado

**03 - Análise de Resposta**

Verifique se o equipamento está respondendo na rede

**04 - Ação Corretiva**

Aplique o procedimento adequado conforme resultado

**Se o equipamento responde:**

- Envie comando para alterar temperatura
- Se funcionar: Pergunte se ajuda em algo mais
- Se não funcionar: Informe franqueado sobre sensor desalinhado e comunique o cliente

**Se o equipamento NÃO responde:**

- Verifique conexão física do equipamento
- Teste reinicialização do sistema
- Escalate para manutenção se necessário
"""

# Criar o artigo
article = ArtigoBaseConhecimento.objects.create(
    titulo='Módulo 3 – Clientes',
    conteudo=content,
    categoria='training',
    tags='clientes, atendimento, nota fiscal, cadastro, infraestrutura, procedimentos',
    department=department,
    usuario=admin_user
)

print(f"✅ Módulo 3 criado com sucesso! ID: {article.id}")
print(f"   Título: {article.titulo}")
print(f"   Categoria: {article.categoria}")
