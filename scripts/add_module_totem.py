# Script para adicionar o Módulo - O Totem
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
content = """Conheça o coração tecnológico da Lavanderia 60 Min: o sistema que conecta cliente, máquinas e pagamentos em uma experiência integrada.

### Visão Geral do Sistema

Neste módulo, você irá aprender tudo o que envolve o totem da Lavanderia 60 Min: como ele funciona, como é instalado, como se comunica com a maquineta, com as máquinas e com o sistema interno.

**Funções Principais:**

- **Interface com Cliente** - Exibe informações e opções de forma clara e intuitiva
- **Controle de Máquinas** - Envia comandos para lavadoras e secadoras
- **Processamento de Pagamentos** - Gerencia transações via maquineta e PIX
- **Programação Visual** - Exibe conteúdo da TV para engajamento

⚠️ **Qualquer falha no totem impede completamente o cliente de usar a loja**

### Hardware do Totem: Mini PC

**Configuração Padrão dos Novos Totens:**

- **Processador:** Intel Core i5 de 4ª geração → potência suficiente para multitarefas
- **Memória RAM:** 4GB DDR3 → capacidade adequada para o sistema operacional
- **Armazenamento:** SSD de 128GB → velocidade e confiabilidade para o Windows
- **Alimentação:** Fonte chaveada 12V 50A → fornece energia estável

### Tela Touch: Problemas e Soluções

**Conexão:**
A tela touch é conectada via cabo flat USB, que transmite tanto energia quanto dados de toque.

**Problemas Comuns:**

- Cabo flat desconectado ou danificado
- Entrada flat com defeito físico
- Driver não reconhecido pelo Windows
- Tela com falha na controladora interna
- TV sendo reconhecida como tela principal
- Toques fantasmas (registros incorretos)
- Sujeira entre moldura e vidro
- Tela preta sem imagem
- Resolução fora do padrão configurado

**Procedimento de Resolução:**

1. **Verificação Física** - Checar cabo flat e portas USB
2. **Software** - Reinstalar drivers e calibrar tela
3. **Substituição** - Trocar totem se necessário

### Processador e Sistema de Resfriamento

O processador precisa estar sempre resfriado corretamente para manter o desempenho e evitar travamentos. O superaquecimento é uma das causas mais comuns de problemas intermitentes.

**Sintomas de Problemas:**

- Cooler travado ou com acúmulo de sujeira
- Processador superaquecendo → reinícios aleatórios
- Queda de desempenho no Windows
- Sistema travando após alguns minutos de uso

**Soluções Práticas:**

1. Limpar cooler com cuidado
2. Aplicar limpa contato no cooler
3. Limitar uso da CPU no plano de energia (Painel de Controle)
4. Verificar pasta térmica do processador

### Fonte de Alimentação 12V 50A

**01 - Identificação**
Responsável por alimentar todo o sistema do totem com energia estável

**02 - Problemas Típicos**
Fonte fraca/piscando, cabos desconectados, pontas queimadas, oxidação nos conectores

**03 - Diagnóstico**
Conferir saída com multímetro para verificar tensão de 12V constante

**04 - Correção**
Substituir fonte defeituosa, reapertar conexões, cortar pontas queimadas, limpar oxidação

⚠️ **Tensão irregular na fonte causa travamentos misteriosos e difíceis de diagnosticar**

### SSD: Armazenamento e Performance

**Função:**
Armazena o sistema operacional Windows e o aplicativo ikli_totem, garantindo inicialização rápida.

**Problemas e Soluções:**

- **Windows não inicializa** → Trocar o SSD por um novo e reinstalar o sistema
- **Sistema extremamente lento** → Verificar saúde do SSD e substituir se necessário
- **Arquivos corrompidos** → Tentar comandos no CMD para recuperar o Windows (sfc /scannow)

### Memória RAM: Problemas e Diagnóstico

**Sintomas:**

- **Tela Azul (BSOD)** - Indica falha crítica na memória
- **Travamentos Aleatórios** - Sistema congela sem motivo aparente
- **Apps Fechando Sozinhos** - Aplicativos terminam inesperadamente
- **Inicialização Lenta** - Windows demora muito para carregar

**Soluções Recomendadas:**

✓ Limpar os contatos da memória RAM com borracha branca
✓ Fazer teste de memória usando o Windows Memory Diagnostic

### Televisão: Configuração Inicial

A TV funciona como segunda tela, conectada via HDMI, exibindo a programação da franquia. O ikli_totem identifica automaticamente quando a saída está configurada corretamente.

**Passos de Configuração:**

1. **Conexão Física** - Conecte a TV ao totem usando cabo HDMI de qualidade
2. **Configuração de Som** - Windows → Configurações → Sistema → Som → Identificar dispositivo da TV
3. **Renomear Dispositivo** - Renomeie o dispositivo de áudio para "TV" (sem aspas)
4. **Detecção Automática** - O ikli_totem detecta e ajusta automaticamente áudio e vídeo
5. **Verificação Final** - Confirmar que TV está como segunda tela, não principal

### TV: Resolução de Problemas

**TV sem imagem**

- **Causas:** Cabo HDMI desconectado, entrada com mau contato, HDMI quebrado, adaptador mini HDMI defeituoso, TV como tela principal
- **Correções:** Verificar conexões, testar outras portas HDMI, trocar cabo, detectar telas no Windows, ajustar resolução para 1366x768

**TV como Tela Principal**

- **Causas:** Windows reorganizou telas, HDMI conectado antes do boot, driver da GPU forçou prioridade
- **Correções:** Windows → Sistema → Tela → Clicar monitor 1 → Tornar esta minha tela principal → Reiniciar

**Som sem imagem**

- **Causas:** Modo de exibição errado, resolução incompatível, HDMI enviando só áudio
- **Correções:** Windows + P → Estender, ajustar resolução 1366x768, trocar cabo HDMI

**Sem som ou som errado**

- **Causas:** Dispositivo não renomeado "TV", saída de áudio errada, TV no mudo, driver não carregado
- **Correções:** Configurações → Som → Saída → Escolher TV, testar volume no controle, reiniciar totem

**Imagem tremendo/piscando**

- **Causas:** Cabo HDMI ruim, porta com mau contato, fonte instável, driver desatualizado
- **Correções:** Trocar HDMI, reconectar com firmeza, limpa contato, testar outra porta, reiniciar totem

### Comunicação com a Maquineta

**Ponto Crítico do Sistema**

A maquineta é identificada pelo sistema através da porta COM. O ikli_totem busca automaticamente a porta COM configurada nas variáveis de ambiente do Windows.

**Variáveis Essenciais:**

- **PORT_PINPAD** → Porta COM da maquineta
- **STORE_ID** → Identificação única da loja

**Problemas Comuns:**

- Porta COM não aparece no sistema
- Driver não reconhecido pelo Windows
- Cabo USB com mau contato
- Maquineta desligando sozinha
- Totem exibe erro de pagamento

**Soluções:**

1. Confirmar porta COM correta nas variáveis
2. Trocar entrada USB do totem
3. Reiniciar maquineta (desligar e ligar)
4. Reinstalar drivers da maquineta
5. Reiniciar o totem completamente
6. Validar código TEF no sistema admin

⚠️ **Se nenhum procedimento funcionar, solicitar ao franqueado que entre em contato com a Stone para substituição**

### Comunicação com as Máquinas

O totem se comunica com o sistema central, que envia comandos aos ESP8266 instalados em lavadoras, secadoras e dosadoras. Esta comunicação é feita via rede WiFi local.

**Problemas Comuns:**

1. **ESP Offline** - Máquina não libera no totem, dosadora ou ar condicionado não acionam
2. **Rede Fraca** - Atraso no acionamento ou máquinas não respondem aos comandos
3. **Loja Sem Conexão** - Internet caiu e sistema parou completamente

**Soluções:**

- Reiniciar máquinas, dosadoras e sensor do ar condicionado
- Verificar configuração do MikroTik (roteador da loja)
- Testar força do sinal WiFi próximo às máquinas
- Contatar franqueado para relatar problema à provedora de internet
- Verificar se todos os ESPs estão alimentados corretamente

### Sistema ikli_totem

**O Coração do Totem**

O ikli_totem é o software principal que roda no totem, responsável por toda a interface com o cliente, processamento de pagamentos e comunicação com as máquinas.

**Localização Padrão:**
`C:\\Lavanderia60minutos\\ikli_totem\\win_unpacked`

Esta pasta contém todos os arquivos necessários para executar o sistema: executável do ikli_totem, arquivos de configuração, DLLs e recursos do sistema.

### Execução Automática no Windows

Para garantir que o sistema inicie automaticamente quando o totem ligar, diversos arquivos precisam estar na pasta `shell:startup` do Windows.

**Arquivos Principais:**

- **Atalho para o ikli_totem** - Inicia o sistema principal da lavanderia
- **volume.vbs** - Configura o volume padrão do sistema automaticamente
- **Parar_modo_espera.vbs** - Impede que o totem entre em modo de espera ou hibernação
- **Barradetarefas.ahk** - Oculta a barra de tarefas do Windows para interface limpa
- **AutoTEF.service** - Atalho para o serviço de comunicação com a maquineta
- **Scripts personalizados** - Configurações adicionais de acordo com necessidade do franqueado

**Problemas Comuns:**

- Atalho apagado → Totem inicia Windows mas não carrega o sistema
- Barra de tarefas visível → Arquivo Barradetarefas.ahk não está na pasta startup
- Volume fora do padrão → Script volume.vbs não foi iniciado corretamente

### Instalação Completa do Totem

Passo a passo utilizado pela equipe técnica para configurar um totem do zero:

**01 - Atualização do ikli_totem**
Instalar versão mais recente do sistema

**02 - Variáveis de Ambiente**
Configurar PORT_PINPAD e STORE_ID

**03 - Configuração da TV**
Conectar HDMI e renomear dispositivo de áudio

**04 - Conexão da Maquineta**
Identificar porta COM e testar comunicação

**05 - Registro na Startup**
Adicionar todos os scripts na shell:startup

**06 - Ajuste de Resolução**
Configurar resolução padrão das telas

**07 - Conexão de Rede**
Cabo Ethernet conectado ao MikroTik da loja

**08 - Testes Finais**
Validar todo o fluxo do cliente

**Checklist de Testes:**

✓ Processamento de pagamento (cartão e PIX)
✓ Comunicação com ESP das máquinas
✓ Liberação de lavadora e secadora
✓ Fluxo completo do cliente do início ao fim
✓ Acesso à área restrita do franqueado

### Quando Solicitar um Novo Totem

Solicite um novo totem apenas quando não existe solução remota e o equipamento impede completamente a operação da loja.

**Hardware Crítico Danificado:**

- Totem não liga mesmo com energia estável
- Fonte queimada sem possibilidade de reparo
- Superaquecimento persistente após limpeza
- SSD com defeito irrecuperável
- Memória RAM com problema confirmado
- Liga e desliga em loop infinito

**Sistema Corrompido Sem Recuperação:**

- Windows em loop de reparo automático
- Blue screen repetitivo e persistente
- Sistema operacional corrompido além do reparo
- Impossibilidade de reinstalar o Windows

⚠️ **Antes de solicitar novo totem, sempre tente todas as soluções documentadas neste módulo**
"""

# Criar o artigo
article = ArtigoBaseConhecimento.objects.create(
    titulo='MÓDULO – O TOTEM',
    conteudo=content,
    categoria='training',
    tags='totem, hardware, troubleshooting, maquineta, ikli_totem, configuração, instalação',
    department=department,
    usuario=admin_user
)

print(f"✅ Módulo O TOTEM criado com sucesso! ID: {article.id}")
print(f"   Título: {article.titulo}")
print(f"   Categoria: {article.categoria}")
