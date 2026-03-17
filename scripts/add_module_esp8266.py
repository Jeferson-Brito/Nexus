# Script para adicionar o Módulo ESP8266
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
content = """Domine a tecnologia que controla toda a automação da sua lavanderia

### Visão Geral do Sistema

**O Coração da Automação**

As placas ESP8266 são responsáveis por toda a automação da lavanderia. Sem elas, nenhum equipamento funciona automaticamente. Este módulo apresenta tudo o que você precisa saber para diagnosticar e solucionar problemas.

**Funções Controladas:**

- Liberação de lavadoras
- Liberação de secadoras
- Acionamento das dosadoras
- Acionamento do sensor do ar
- Comunicação Totem → Mikrotik → Máquina → Dosadora

⚠️ **Importante:** Se a ESP falha, toda a automação falha.

### O que é a ESP8266?

**Microcontrolador Wi-Fi**

Placa com Wi-Fi integrado que recebe comandos do totem através da rede local

**Repasse de Pulso**

Transmite o sinal elétrico para iniciar o ciclo da máquina

**Comunicação Estável**

Mantém conexão contínua com o Mikrotik via IP fixo

**Controle de Automações**

Aciona máquinas, sensores e dosadoras no momento correto

### Tipos de ESP na Lavanderia

**1. ESP de Lavadoras**

- 432 → 192.168.50.101
- 543 → 192.168.50.102
- 654 → 192.168.50.103

**2. ESP de Secadoras**

- 765 → 192.168.50.104
- 876 → 192.168.50.105
- 987 → 192.168.50.106

**3. ESP da Dosadora**

- 432 → 192.168.50.151
- 543 → 192.168.50.152
- 654 → 192.168.50.153
- Nova → 192.168.50.150

**4. ESP do Sensor do Ar**

- 192.168.50.110

💡 **Cada ESP possui um endereço IP fixo que permite sua identificação única na rede. Memorize esses IPs para facilitar o diagnóstico.**

### Funcionamento da Automação

**Fluxo Completo:**

**1. Totem**
Cliente seleciona máquina e inicia pagamento

**2. Mikrotik**
Roteador encaminha comando para ESP específica

**3. ESP**
Recebe sinal e executa acionamento físico

**4. Máquina**
Inicia ciclo de lavagem automaticamente

### Acionamento da Dosadora

**Sabão**

Após 26 minutos de ciclo, a máquina envia pulso para a dosadora, que aciona o sabão automaticamente

**Amaciante**

Em 16 minutos após o sabão, o pulso é enviado para o amaciante escolhido pelo cliente

### Principais Problemas

**1. ESP Offline**

**Sintomas:**
- Máquina não libera
- Teste de conexão falha
- ESP não responde ping

**Causas Possíveis:**
- Timeout com roteador
- Totem desconectado
- Falha de alimentação elétrica

**Correções:**
- Reiniciar a ESP
- Testar ping pelo CMD
- Reconfigurar via USB

### Mais Problemas Comuns

**2. Máquina Não Responde**

- **Sintomas:** ESP responde ping mas não aciona a máquina
- **Causas:** Firmware corrompido, ESP com defeito ou queimada
- **Solução:** Desligar e religar máquina, reconfigurar ESP ou solicitar novo módulo

**3. Falhas Intermitentes**

- **Sintomas:** Máquina libera só às vezes, dosadora dispara produto, ar condicionado não liga
- **Causas:** Oscilação Wi-Fi, ESP distante do Mikrotik, má conexão na dosadora
- **Solução:** Aproximar Mikrotik, reforçar fixação, testar conexão

### Reconfiguração da ESP

**Passo a Passo Completo:**

**1. Preparação**
Solicitar ao franqueado que leve a placa até o Totem e conecte via cabo micro-USB v8

**2. Abrir Configurador**
Abrir o aplicativo ESP8266Flasher.exe no computador

**3. Selecionar Arquivo**
Escolher o firmware correto conforme tipo de equipamento

**4. Importar e Flash**
Importar configuração e gravar na ESP

**5. Religar e Testar**
Desconectar USB, religar equipamento, testar ping e liberação pelo Totem

### Arquivos de Firmware por Equipamento

- **Lavadora:** LAV432.bin
- **Secadora:** SEC765.bin
- **Dosadora:** 432_CONTROLADORA_17122024.ino.bin
- **Ar Condicionado:** AR_CONDICIONADO_AL02.ino.nodemcu.bin

### Diagnóstico Express

**Checklist de Verificação Rápida**

Quando algo falhar, siga esta ordem de diagnóstico para identificar rapidamente a origem do problema:

**01 - Aparece no Mikrotik?**
Verificar se a ESP está registrada na lista de dispositivos conectados

**02 - Responde Ping?**
Testar conectividade através de ping pelo CMD ou Mikrotik

**03 - A Máquina Liga?**
Confirmar se há alimentação elétrica no equipamento

**04 - Desligou e Ligou?**
Verificar se o franqueado já tentou reiniciar o equipamento

**05 - Já Reconfigurei?**
Avaliar se já foi feita tentativa de reconfiguração da ESP

### Quando Solicitar uma Nova ESP?

**Reconfiguração Falha**

A ESP não aceita reconfiguração mesmo seguindo todos os passos corretamente

**Não Aparece no Mikrotik**

Mesmo com alimentação elétrica confirmada, não é detectada na rede

**Falha Múltipla**

A automação falha em várias máquinas simultaneamente

**Perda Recorrente**

A comunicação desaparece repetidamente sem causa aparente

⚠️ **Lembre-se:** Antes de escalar, sempre confirme que todos os passos de diagnóstico foram seguidos e que o problema não é de rede ou alimentação elétrica.

### Comandos Úteis para Diagnóstico

**Testar conectividade:**
```
ping 192.168.50.101
```

**Verificar dispositivos na rede:**
Acessar interface do Mikrotik e verificar lista de dispositivos DHCP/estáticos

**Localizar ESP específica:**
Use o IP correspondente à máquina conforme tabela de mapeamento

### Resumo de IPs por Função

| Equipamento | Número | IP |
|-------------|--------|-----|
| Lavadora | 432 | 192.168.50.101 |
| Lavadora | 543 | 192.168.50.102 |
| Lavadora | 654 | 192.168.50.103 |
| Secadora | 765 | 192.168.50.104 |
| Secadora | 876 | 192.168.50.105 |
| Secadora | 987 | 192.168.50.106 |
| Dosadora | 432 | 192.168.50.151 |
| Dosadora | 543 | 192.168.50.152 |
| Dosadora | 654 | 192.168.50.153 |
| Dosadora | Nova | 192.168.50.150 |
| Ar Condicionado | - | 192.168.50.110 |
"""

# Criar o artigo
article = ArtigoBaseConhecimento.objects.create(
    titulo='MÓDULO 3 – ESP8266',
    conteudo=content,
    categoria='training',
    tags='esp8266, automação, mikrotik, wifi, firmware, troubleshooting, iot, networking',
    department=department,
    usuario=admin_user
)

print(f"✅ Módulo ESP8266 criado com sucesso! ID: {article.id}")
print(f"   Título: {article.titulo}")
print(f"   Categoria: {article.categoria}")
