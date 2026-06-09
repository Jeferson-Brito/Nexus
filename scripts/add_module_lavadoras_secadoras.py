# Script para adicionar o Módulo - Lavadoras e Secadoras
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'brisoft.settings')
django.setup()

from core.models import ArtigoBaseConhecimento, Department, User

# Get department
department = Department.objects.filter(name='NRS Suporte').first()
admin_user = User.objects.filter(role='administrador').first()

if not department or not admin_user:
    print("Erro: Departamento ou usuário não encontrado!")
    exit(1)

# Conteúdo do módulo (parte 1)
content_part1 = """Diagnóstico Completo, Erros Comuns e Procedimentos Técnicos Oficiais

### Visão Geral do Módulo

Este módulo apresenta o conhecimento técnico essencial para diagnóstico e resolução de problemas em equipamentos de lavanderia industrial. O conteúdo foi estruturado para capacitar técnicos de manutenção e franqueados com procedimentos validados e testados em campo.

**Identificação de Erros**

Métodos para identificar rapidamente códigos de erro em lavadoras e secadoras através do display e comportamento da máquina

**Diferenciação de Falhas**

Técnicas para distinguir entre falhas mecânicas da máquina e problemas de automação do sistema

**Procedimentos Oficiais**

Passo a passo validado para tratativas com franqueados, incluindo critérios de suspensão e liberação

### Categorização dos Equipamentos

Os equipamentos são categorizados em dois grupos principais com sistemas distintos:

**Lavadoras:**
- Sistema de abastecimento de água
- Sensores de nível e pressão
- Drenagem e bombeamento
- Pressurização hidráulica

**Secadoras:**
- Sistema de aquecimento
- Gerenciamento de gás
- Ventilação e exaustão
- Segurança térmica

### Identificando o Tipo do Problema

Antes de iniciar qualquer atendimento, é fundamental seguir uma sequência estruturada de verificações para identificar corretamente a origem do problema.

**01 - Verificação no Totem**

A máquina aparece no sistema do totem?

- **Sim, mas não inicia:** Indica falha física ou erro no display da máquina
- **Não aparece:** Problema de automação (ESP, rede ou energia)

**02 - Teste de Ping no ESP**

O módulo ESP responde ao comando PING?

- **Responde:** Automação funcionando corretamente → direcionar foco para a máquina
- **Não responde:** Problema de rede, energia elétrica ou ESP queimado

**03 - Análise do Display**

Existe código de erro sendo exibido no display?

Cada código de erro indica um caminho específico de diagnóstico e procedimento técnico validado

### LAVADORAS: Diagnóstico + Erros + Procedimentos

**Funcionamento Técnico da Lavadora**

Compreender o ciclo operacional completo da lavadora é essencial para diagnosticar problemas com precisão. O processo segue uma sequência lógica de etapas interdependentes.

**Ciclo Operacional:**

1. **Travamento da Porta** - Sistema de segurança ativa a trava eletromagnética
2. **Entrada de Água** - Válvula solenoide controla o abastecimento
3. **Lavagem** - Motor aciona o tambor em rotação programada
4. **Drenagem** - Bomba remove a água utilizada
5. **Centrifugação** - Alta rotação para remoção de umidade

**Componentes Físicos:**

- Trava de porta eletromagnética
- Válvula solenoide de água
- Pressostato de nível
- Bomba de drenagem
- Motor de acionamento

**Sistema de Automação:**

- Módulo ESP8266
- Sensores de nível
- Controlador eletrônico
- Interface de comunicação

### PRINCIPAIS ERROS EM LAVADORAS

### ERRO IE: Falta de Água / Filtro Obstruído

⚠️ **ATENÇÃO:** Este é o erro mais comum em lavadoras industriais, representando aproximadamente 70% das ocorrências de falha no sistema de abastecimento de água.

O erro IE indica que a máquina não conseguiu completar o enchimento de água no tempo programado.

**Ações Imediatas ao Franqueado/Cliente:**

1. **Bloqueio Temporário** - Informar que a máquina será bloqueada temporariamente no sistema
2. **Destravamento da Porta** - Explicar procedimento de destravamento manual
3. **Estorno de Pagamento** - Informar sobre o processo de estorno se houver pagamento
4. **Início do Diagnóstico** - Começar imediatamente o diagnóstico técnico

**Diagnóstico ERRO IE: Com Abastecimento de Água na Loja**

**Passo 1: Localizar os Filtros**
Os filtros estão localizados na parte traseira da máquina, na conexão de entrada de água.

**Passo 2: Remover e Limpar**
- Fechar completamente o registro de água
- Remover cuidadosamente o filtro laranja/azul
- Limpar resíduos com chave de fenda se necessário
- Verificar se há danos na tela do filtro

**Passo 3: Testar Funcionamento**
Reinstalar o filtro, abrir o registro e liberar um ciclo de teste

💡 **ESTATÍSTICA:** 70% dos erros IE são resolvidos apenas com limpeza do filtro de entrada de água.

**Diagnóstico ERRO IE: Persistência Após Limpeza**

Se o erro continuar após limpeza dos filtros:

**1. Bomba Pressurizadora**
- Confirmar se a bomba está ligada e energizada
- Verificar leitura do manômetro (se equipamento possuir)
- Escutar ruídos anormais de funcionamento

**2. Teste de Pressão (OBRIGATÓRIO)**
1. Fechar o registro de água completamente
2. Posicionar mangueiras em balde de 10 litros
3. Abrir o registro lentamente
4. Observar volume e força do jato de água
5. Se jato fraco: Solicitar técnico especializado

### ERRO OE: Dreno Obstruído

**Sintomas Característicos:**
- Máquina trava em 13 minutos ou 8 minutos
- Água permanece acumulada no tambor
- Barulho estranho ou anormal na bomba
- Display exibe código OE

**Procedimento de Resolução:**

1. **Suspensão da Máquina** - Bloquear imediatamente no sistema
2. **Esvaziamento Seguro** - Orientar franqueado sobre como esvaziar com segurança
3. **Acesso ao Filtro** - Abrir tampa frontal para acessar compartimento
4. **Limpeza Completa** - Retirar e limpar filtro do dreno
5. **Inversão das Bombas** - Realizar procedimento conforme manual técnico
6. **Teste de Validação** - Executar ciclo rápido para confirmar drenagem

⚠️ **Se o problema continuar:** Bomba de drenagem queimada → Solicitar técnico

### ERRO DE1: Porta Aberta / Obstruída

O erro DE1 é um dos mais simples de resolver, geralmente causado por fechamento inadequado.

**Procedimento:**

1. **Abertura Total da Porta** - Solicitar que abra completamente
2. **Verificação de Obstruções** - Verificar roupas ou objetos na vedação
3. **Fechamento Correto** - Fechar com firmeza até ouvir o clique
4. **Reinicialização** - Reiniciar o ciclo de lavagem

💡 **TAXA DE RESOLUÇÃO:** 90% dos erros DE1 são resolvidos apenas com orientação adequada

### ERRO DE2: Falha na Trava da Porta

🚨 **ERRO CRÍTICO DE SEGURANÇA:** Máquina não pode ser liberada com este erro.

O erro DE2 indica falha no sistema de travamento de segurança da porta.

**Procedimento de Tentativa de Correção:**

1. Solicitar fechamento da porta com firmeza
2. Reiniciar o ciclo de lavagem
3. Desligar e ligar a máquina completamente (aguardar 30 segundos)

**Se o Erro Persistir:**

- **Suspensão Imediata** - Bloquear máquina sem exceções
- **Substituição da Trava** - Providenciar substituição da trava eletromagnética
- **Abertura de Manutenção** - Abrir ordem de serviço oficial

⚠️ **IMPORTANTE:** Máquina com erro DE2 persistente não pode funcionar sob nenhuma circunstância.

### ERRO SUD5: Excesso de Sabão

O erro SUD5 ocorre quando há formação excessiva de espuma durante o ciclo.

**Procedimento:**

1. **Verificação do Produto** - Confirmar se foi utilizado sabão adequado
2. **Liberação Alternativa** - Liberar outra máquina disponível
3. **Aferição da Dosadora** - Solicitar verificação completa do sistema
4. **Calibração** - Orientar calibração correta da dosagem

💡 **PREVENÇÃO:** 90% dos casos podem ser evitados com dosadora calibrada

### Vazamentos de Água

**Vazamento pelo Suspiro**

Normal quando há quantidade elevada de roupas. O suspiro permite escape de pressão.

**Vazamento pelo Dispenser**

Solicitar remoção e limpeza minuciosa do dispenser. Se persistir, solicitar técnico.

**Vazamento pela Porta**

Indica borracha de vedação danificada. Requer substituição imediata. Suspender máquina.

### SECADORAS - Erros Comuns

### Problema: Secadora Não Aquece

A falta de aquecimento é uma das falhas mais críticas em secadoras.

**Causas Principais:**

- Filtro de ar sujo ou obstruído
- Exaustor com obstrução
- Termostato com problema
- Excesso de roupas no tambor
- Falha no sistema de gás

**Soluções Técnicas:**

1. Solicitar limpeza completa do filtro
2. Verificar e desobstruir duto exaustor
3. Testar botões de temperatura alta e média
4. Reduzir carga de roupas para quantidade adequada
5. Se persistir, orientar franqueado a chamar técnico

### Secadora: Liberação Acima de 45 Minutos

⚠️ **ATENÇÃO:** Secadoras configuradas corretamente devem liberar em frações de 15 minutos, nunca excedendo 45 minutos totais.

**Causa 1: Configuração Não Realizada**
- **Solução:** Configurar fracionamento via reunião remota (Meet)

**Causa 2: Perda de Configuração do Painel**
- **Solução:** Reconfigurar parâmetros do painel de controle

**Causa 3: Módulo Defeituoso**
- **Solução:** Reconfigurar ou substituir ESP

**Validação:** Após correção, liberar ciclo de teste. Deve liberar 15 em 15 minutos.

### Secadora: Outros Problemas Técnicos

**Barulho Forte / Rolamento Desgastado**

Procedimento:
- Solicitar vídeo detalhado do ruído
- Analisar características do som
- Se confirmado problema mecânico → Manutenção física obrigatória
- Franqueado deve adquirir peça e solicitar técnico

**Problemas Incomuns ou Não Catalogados**

Protocolo:
- Documentar com fotos e vídeos
- Chamar coordenador ou supervisor
- Orientar franqueado a chamar técnico
- Registrar ocorrência para base de conhecimento

### Quando o Problema é Automação (ESP)

Problemas no módulo ESP8266 são distintos de falhas mecânicas.

**Indícios de Problema na Automação:**

- Máquina não aparece ou não libera pelo totem
- Totem libera e retira créditos, mas máquina não inicia
- Comando PING não retorna resposta
- PING responde mas máquina não libera

**Soluções por Ordem de Complexidade:**

**Nível 1: Reset Simples**
Desligar e ligar completamente (aguardar 30 segundos)

**Nível 2: Verificação Física**
Abrir painel e verificar conexões do módulo ESP

**Nível 3: Reconfiguração**
Reconfigurar placa ESP com parâmetros de fábrica

**Nível 4: Substituição**
Solicitar novo módulo se não houver resposta

### Testes Obrigatórios do Analista

Todo atendimento técnico deve seguir sequência padronizada:

1. **Teste no Totem** - Verificar visibilidade e resposta aos comandos
2. **Teste de Ping** - Confirmar conectividade de rede
3. **Verificar ESP** - Analisar logs, configurações e firmware
4. **Solicitar Vídeo** - Documentação visual do comportamento
5. **Validar Comportamento Real** - Confirmar problema através de teste prático

### Quando Suspender Máquina

Critérios claros para suspensão:

- **Porta Não Trava** - Suspensão imediata por segurança
- **Máquina Não Drena** - Suspender para evitar danos
- **Secadora Sem Aquecer** - Não cumpre função principal
- **Ruído Mecânico Forte** - Após validação com franqueado
- **Vazamento de Água** - Suspensão obrigatória para vazamentos pela porta

⚠️ **IMPORTANTE:** Toda suspensão deve ser documentada com motivo, prints e previsão.

### Quando Abrir Expedição

A abertura de expedição para peças em garantia requer documentação completa.

**Situações que Justificam:**

- Válvula solenoide com defeito comprovado
- Pressostato defeituoso ou descalibrado
- Placa eletrônica danificada
- Módulo ESP queimado ou irrecuperável

**Documentação Obrigatória:**

- Vídeo mostrando defeito em operação
- Fotos de alta qualidade do componente
- Etiqueta do número de série da máquina
- Descrição técnica detalhada
- Histórico de testes realizados

🚨 **ATENÇÃO CRÍTICA:** SÓ ABRIR CARD DE PEÇAS QUE NÃO SE ENQUADREM EM PEÇAS DE DESGASTE. Em caso de dúvida, SEMPRE validar com coordenador.

### Checklist Final para Encerramento

O encerramento adequado garante que nada foi esquecido:

✓ **Franqueado Testou?** - Confirmar teste prático após intervenção

✓ **Problema Realmente Resolvido?** - Validar eliminação completa, não contorno temporário

✓ **Prints/Screen e Vídeos no Bitrix24?** - Verificar documentação anexada

✓ **Máquina Liberada e Documentada?** - Confirmar liberação no sistema e registro completo

**Conclusão:** Seguindo rigorosamente estes procedimentos técnicos, você garantirá atendimento profissional, diagnósticos precisos e resolução eficiente de problemas em lavadoras e secadoras industriais.
"""

# Criar o artigo
article = ArtigoBaseConhecimento.objects.create(
    titulo='MÓDULO 3 – LAVADORAS E SECADORAS',
    conteudo=content_part1,
    categoria='training',
    tags='lavadoras, secadoras, erros, diagnóstico, troubleshooting, manutenção, procedimentos, IE, OE, DE1, DE2',
    department=department,
    usuario=admin_user
)

print(f"✅ Módulo LAVADORAS E SECADORAS criado com sucesso! ID: {article.id}")
print(f"   Título: {article.titulo}")
print(f"   Categoria: {article.categoria}")
