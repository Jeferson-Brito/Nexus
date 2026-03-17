# Script para adicionar o Módulo - Explicação dos Usos das Ferramentas
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
content = """Domine as ferramentas essenciais do suporte técnico e maximize sua eficiência operacional.

### Objetivo do Módulo

**Função de Cada Ferramenta**

Compreenda profundamente o papel e a aplicação de cada sistema utilizado no dia a dia do suporte técnico.

**Limites e Possibilidades**

Identifique claramente o que pode e o que não pode ser executado em cada plataforma do ecossistema.

**Fluxo Operacional Completo**

Garanta domínio total do processo end-to-end, desde o recebimento até a resolução final de cada solicitação.

### Bitrix24 – Centro de Operações do Suporte

**Onde Trabalhamos no Bitrix:**

**Contact Center**

Hub principal para atendimento de todos os chats e interações com franqueados e clientes.

**Kanban**

Gestão visual de cards e acompanhamento do andamento de todas as tratativas em tempo real.

**Bitrix Drive**

Repositório centralizado de treinamentos, POPs e arquivos essenciais para operação diária.

**App Mobile**

Ferramenta para uso situacional quando necessário acesso remoto à plataforma.

### Regras Essenciais

**Princípios Inegociáveis:**

- **Tudo deve ser registrado** → Documentação completa é obrigatória
- **Nada por fora** → Resolução de problemas apenas através dos sistemas oficiais
- **Não documentado = não existiu** → Sem registro, não há rastreabilidade

### Fluxo de Atendimento no Bitrix

**1. Recebe o Chat**
Início do atendimento

**2. Identifica o Problema**
Diagnóstico inicial

**3. Automação Cria Card**
Para franqueados

**4. Atualiza Etapas**
Registro contínuo

**5. Confirma Solução**
Validação final

**6. Encerra com Observação**
Conclusão documentada

### Sistema Admin da Franquia

**O que o Admin Mostra:**

- **Dashboard** - Visão geral consolidada
- **Cupons e Notas Fiscais** - Documentação fiscal completa
- **Dados Cadastrais** - Clientes, franqueados e lojas
- **Relatórios** - Vendas, liberações e performance
- **Status de Máquinas** - Monitoramento operacional
- **Atualizações e Hibank** - Sistema de totem e integrações

### Funções Mais Usadas

**Mudança de Status**

Alterar máquinas entre ativa, ocupada e suspensa conforme necessidade operacional

**Consulta de Cadastros**

Acessar dados completos de clientes e histórico de pagamentos e usos

**Histórico de Limpeza**

Verificar registros de manutenção e higienização das lojas

**Controle de Temperatura**

Ajustar configurações do ar condicionado remotamente

**Área Restrita**

Adicionar e gerenciar acessos específicos do franqueado

**Abertura de Ocorrências**

Registrar e acompanhar problemas reportados

⚠️ **Observações Críticas:**

Sempre justificar qualquer alteração em cadastros de clientes e lojas. Abrir ocorrências corretamente seguindo o protocolo estabelecido. Em caso de dúvidas, sempre consultar supervisor ou coordenador antes de prosseguir.

### Agente do Aylton

**Para que Serve:**

**Monitoramento em Tempo Real**

Acompanhe a comunicação do totem e identifique problemas instantaneamente antes que afetem a operação.

**Status de ESPs**

Visualize o estado de cada ESP conectado, incluindo falhas, desconexões e registros técnicos detalhados.

**Ajustes e Liberações**

Configure dosagem das dosadoras e realize liberação de ciclos com registro completo de auditoria.

### Uso no Suporte

**01 - Verificar Status Online**
Confirmar se a ESP está conectada e operacional

**02 - Validar Comunicação**
Confirmar se o totem está transmitindo dados corretamente

**03 - Identificar Máquinas Offline**
Localizar equipamentos com problemas de conexão

**04 - Validar Falha**
Diagnosticar problema antes de acionar o franqueado

### Acesso Remoto

**AnyDesk / HopToDesk / DWService**

**Função Principal:**

**Atualizações**
Atualizar e hospedar o sistema ikli totem remotamente

**Configurações**
Ajustar drivers e corrigir porta COM da maquineta

**Liberações**
Liberar máquinas via CMD com registro de comando

**Diagnósticos**
Analisar e corrigir erros do Windows e ESP

**Placas ESP**
Configurar e testar comunicação com placas ESP

### Regras de Uso

**Padrões Obrigatórios:**

- **Manter o padrão do shell:startup** → Não alterar configurações de inicialização
- **Finalizar sessão corretamente** → Sempre reabrir o sistema antes de desconectar
- **Documentar bugs** → Registrar todos os erros encontrados no sistema para análise técnica

### Gravador do Windows

**Gravações Obrigatórias:**

**1. Quando Gravar**

Videochamadas: Todas as sessões de suporte via videochamada devem ser gravadas obrigatoriamente para fins de documentação, treinamento e garantia de qualidade no atendimento.

**2. Como Salvar**

Armazenamento interno do computador: Salvar todos os arquivos no disco local, nunca em nuvem externa ou drives compartilhados não autorizados.

**3. Nomenclatura**

Nomear corretamente: Utilizar padrão definido que inclua data, hora, nome do franqueado e tipo de atendimento para facilitar localização futura.

⚠️ **Lembre-se:** Gravações são evidências importantes para auditoria e resolução de conflitos. Mantenha organização rigorosa dos arquivos.

### Navegador e Favoritos

**Links que Devem Estar Favoritados:**

- **Bitrix** - Plataforma principal de atendimento
- **Admin** - Sistema de gestão da franquia
- **Agente** - Monitoramento de ESPs e totems
- **Simplay** - Sistema complementar de operação
- **Formulários** - Documentos e templates padrão

### Boas Práticas

✓ **Evitar E-mail Pessoal**
Utilize apenas e-mail corporativo para todas as comunicações relacionadas ao trabalho.

✓ **Não Salvar Logins Sensíveis**
Nunca salve senhas de sistemas críticos no navegador por questões de segurança.

✓ **WhatsApp Pessoal Fechado**
Mantenha aplicativos pessoais fechados durante o expediente para manter foco profissional.

### Encerramento do Módulo

**Checklist Final para Validar o Treinamento:**

**1. Bitrix Acessível e Funcionando**
Confirme que consegue acessar todas as áreas do Bitrix24, incluindo Contact Center, Kanban e Drive.

**2. Admin Acessado Corretamente**
Valide login no sistema Admin e navegação pelas principais funcionalidades de dashboard e relatórios.

**3. Agente Logado e Funcional**
Verifique conexão com o Agente do Aylton e visualização de status das ESPs em tempo real.

**4. Ferramentas de Acesso Remoto Testadas**
Teste conexão com AnyDesk, HopToDesk ou DWService e realize uma sessão de teste supervisionada.

**5. Favoritos Organizados**
Confirme que todos os links essenciais estão salvos e acessíveis rapidamente no navegador.

✅ **Parabéns! Você concluiu este módulo e agora domina as ferramentas essenciais do suporte técnico. Está pronto para aplicar esse conhecimento no atendimento diário.**
"""

# Criar o artigo
article = ArtigoBaseConhecimento.objects.create(
    titulo='Módulo 3 – Explicação dos Usos das Ferramentas',
    conteudo=content,
    categoria='training',
    tags='ferramentas, bitrix24, admin, agente, acesso remoto, suporte, procedimentos, fluxo',
    department=department,
    usuario=admin_user
)

print(f"✅ Módulo Ferramentas criado com sucesso! ID: {article.id}")
print(f"   Título: {article.titulo}")
print(f"   Categoria: {article.categoria}")
