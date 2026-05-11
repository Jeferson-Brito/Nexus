# Nexus - Ecossistema de Gestão Operacional & Inteligência

![Nexus Banner](https://img.shields.io/badge/Status-Active-brightgreen)
![Django](https://img.shields.io/badge/Framework-Django%205.0-092E20?logo=django)
![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL-336791?logo=postgresql)
![AI](https://img.shields.io/badge/Intelligence-Gemini%20API-4285F4?logo=google-gemini)

O Nexus é uma plataforma corporativa robusta projetada para centralizar a gestão de reclamações, auditoria operacional e planejamento de escalas (NRS), integrando Inteligência Artificial para suporte à decisão.

---

## 💎 Módulos Principais

### 📅 Nexus Escala (NRS)
Sistema de gestão de escalas inteligente e dinâmico:
- **Gestão de Folgas**: Solicitações de folga avulsa, banco de horas e outros motivos com fluxo de aprovação.
- **Trocas de Turno**: Sistema de troca de folgas entre analistas ou movimentação de folga própria.
- **Análise de Cobertura**: Painel de suporte à decisão para gestores com visão em tempo real da capacidade operacional e alertas de subdimensionamento.
- **Timeline Visual**: Visualização horária da cobertura por turnos (Madrugada, Matinal, Matutino, Diurno, Tarde).
- **Simulações (Rascunhos)**: Crie e teste novas configurações de escala em ambiente isolado antes de publicar.

### 🤖 Nexus IA & Auditoria
Integração nativa com Google Gemini:
- **Auditor de Conformidade**: Análise automática de escalas frente às leis trabalhistas e regras internas.
- **Chatbot Inteligente**: Assistente virtual para navegação no sistema e consulta rápida de dados.

### 📑 Gestão de Reclamações
Fluxo completo de tratamento de ocorrências:
- Dashboard interativo com métricas de performance.
- Importação/Exportação inteligente (XLSX/CSV).
- Histórico de auditoria detalhado por reclamação.

---

## 🎨 Design & UX
- **Interface Premium**: Desenvolvida com conceitos de *Glassmorphism* e design corporativo moderno.
- **Modo Dark/Light**: Adaptação completa para o conforto visual do usuário.
- **Micro-interações**: Feedback visual fluido e transições suaves.

---

## 🚀 Guia Rápido de Instalação

1. **Ambiente Virtual**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

2. **Dependências**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Banco de Dados & Migrações**:
   ```bash
   python manage.py migrate
   python manage.py create_admin_user
   ```

4. **Execução**:
   ```bash
   python manage.py runserver
   ```

---

## 🛠️ Comandos de Administração

- **Setup de Admin**: `python manage.py create_admin_user`
- **Massa de Dados**: `python manage.py create_sample_data`
- **Segurança**: `python generate_secret_key.py`

---

## 📄 Licença
Propriedade privada. Uso restrito e interno.

