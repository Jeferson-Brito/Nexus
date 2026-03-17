# Script para adicionar o Módulo 3 Dosadoras
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
content = """Sistema automatizado de dosagem para lavadoras profissionais

### Visão Geral

Neste módulo, você aprende tudo sobre a dosadora – o equipamento responsável por aplicar automaticamente sabão e amaciante nas lavadoras da franquia.

A dosadora é um dos equipamentos com maior índice de falhas, por isso a padronização deste módulo é essencial para garantir diagnósticos precisos e soluções eficazes.

**O que você vai dominar:**

- Funcionamento de cada componente
- Ciclo completo de dosagem
- Diagnóstico correto de falhas
- Critérios para suspensão de máquina
- Solicitação de peças e equipamentos
- Documentação completa no Bitrix24

### Arquitetura da Dosadora

A dosadora funciona como um sistema eletrônico coordenado, onde cada componente desempenha uma função específica e essencial.

### ESP8266 (Cérebro)

**Funções Principais:**

- Recebe o sinal da lavadora
- Processa a lógica de dosagem
- Comanda o relé para acionar as bombas
- Mantém o IP estático da dosadora

**Falhas Típicas:**

- Travamento do sistema
- Perda de endereço IP
- Morte total do componente

### Regulador de Voltagem

**O Coração do Sistema**

Componente responsável por estabilizar a tensão em 5V e proteger a ESP8266 contra curtos-circuitos e oscilações de energia.

**Falhas Típicas:**

- Oscilação de voltagem → bombinha não aciona
- Acionamento contínuo sem parar
- Acionamento fraco ou intermitente

### Módulo Relé

**Os Interruptores**

Liga e desliga as bombas sob comando direto do ESP8266, funcionando como interruptores eletrônicos controlados.

**Problemas Comuns:**

- Relé colado (travado)
- Fio vermelho no local errado
- Estala mas não aciona

### Bombas 12V

**A Força de Trabalho**

As bombas executam a dosagem física de sabão e amaciante, transferindo o produto dos reservatórios para a lavadora no momento exato do ciclo.

**Falhas Comuns:**

- **Desgaste Interno** - Uso contínuo compromete vedações e componentes mecânicos
- **Rotor Quebrado** - Impede rotação adequada e bombeamento do produto
- **Ruído Excessivo** - Indica desgaste mecânico avançado ou obstrução

### Relé ATORK / 12V

**Os Ouvidos da Máquina**

Componente responsável por detectar o pulso elétrico enviado pela lavadora, seja em 220V, 12V ou contato direto.

Este relé traduz o sinal da lavadora em um comando que o ESP8266 pode interpretar e processar.

⚠️ **Falha Típica:** Pulso não chega à dosadora devido a problemas na fiação ou no chicote de conexão.

### LEDs Indicadores

**Sinalização Visual**

Os LEDs mostram qual bomba está acionando em tempo real e confirmam se a dosadora está energizada e operacional.

**Confirmação Instantânea**

Permitem validação visual imediata do funcionamento durante testes e diagnósticos, facilitando a identificação de falhas.

### O Ciclo da Dosagem

Todo o processo acontece em aproximadamente 5 segundos. Entender cada etapa é fundamental para diagnosticar onde a falha ocorre.

**1. Máquina Envia Pulso**

- **Com Wi-Fi:**
  - Sabão: 26 min
  - Amaciante: 16 min
- **Sem Wi-Fi:**
  - Sabão: 23 min
  - Amaciante: 13 min

**2. Relé Interpreta**

Converte o sinal da lavadora em nível lógico para a ESP processar

**3. ESP Decide**

Verifica qual produto deve ser acionado naquele momento

**4. Relé Comanda**

Portas são acionadas conforme sinal da ESP

**5. Bomba Executa**

LED acende → confirmação visual → produto dosado

### Diagnóstico Avançado

**Teste Inicial: Aferição Forçada**

Sempre comece por aqui. Este é o teste mais importante para determinar se o problema é no hardware da dosadora ou na comunicação com a lavadora.

**Se a Aferição FUNCIONA:**

Hardware está bom. A falha está entre lavadora → chicote → relé → ESP

Procedimentos:

1. Conferir chicote completo
2. Verificar fios por cor:
   - Sabão → Azul
   - Amaciante → Laranja
   - Neutro → Preto
3. Teste de ligação direta (com supervisão via meet)

**Se a Aferição NÃO Funciona:**

Problema confirmado no hardware da dosadora.

Procedimentos:

1. Verificar alimentação elétrica (12V)
2. Testar regulador de voltagem
3. Verificar conexões do módulo relé
4. Testar bombas individualmente
5. Substituir ESP8266 se necessário

### Mapeamento de Cores dos Fios

**Chicote de Conexão:**

- **Azul** → Sinal de Sabão
- **Laranja** → Sinal de Amaciante
- **Preto** → Neutro/Terra
- **Vermelho** → Alimentação 12V

⚠️ **Sempre documente a posição correta dos fios antes de desconectar**

### Critérios para Solicitação de Peças

**Quando solicitar nova dosadora completa:**

- ESP8266 queimada sem recuperação
- Múltiplos componentes danificados
- Problemas estruturais na caixa/montagem
- Histórico de falhas recorrentes

**Quando solicitar apenas componentes:**

- Bombas com desgaste ou ruído
- Relé travado ou com mau contato
- Regulador de voltagem com oscilação
- Chicote danificado

### Documentação no Bitrix24

**Informações obrigatórias:**

1. Loja afetada e máquina específica
2. Sintoma relatado pelo franqueado
3. Testes realizados remotamente
4. Resultado da aferição forçada
5. Componentes testados
6. Conclusão diagnóstica
7. Peças solicitadas (se aplicável)
8. Status: Resolvido ou Pendente

⚠️ **A documentação completa é essencial para rastreabilidade e melhoria contínua**

### Checklist de Resolução

Antes de dar o chamado como concluído, valide:

✓ Aferição forçada testada e funcionando
✓ Ciclo completo de dosagem executado com sucesso
✓ LEDs indicadores acendem corretamente
✓ Sem vazamentos nos reservatórios
✓ Chicote bem conectado e organizado
✓ Dosadora respondendo aos comandos da lavadora
✓ Documentação completa registrada no Bitrix24
"""

# Criar o artigo
article = ArtigoBaseConhecimento.objects.create(
    titulo='MÓDULO 3 – DOSADORAS',
    conteudo=content,
    categoria='training',
    tags='dosadoras, hardware, esp8266, bombas, diagnóstico, troubleshooting, manutenção',
    department=department,
    usuario=admin_user
)

print(f"✅ Módulo DOSADORAS criado com sucesso! ID: {article.id}")
print(f"   Título: {article.titulo}")
print(f"   Categoria: {article.categoria}")
