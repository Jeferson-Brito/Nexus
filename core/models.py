from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import datetime, timedelta


class Department(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    slug = models.SlugField(unique=True)
    fluxo_aprovacao = models.CharField(max_length=100, blank=True, verbose_name='Fluxo de Aprovação')
    show_in_nav = models.BooleanField(default=False, verbose_name='Exibir no Menu de Navegação')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class User(AbstractUser):
    ROLE_CHOICES = [
        ('analista', 'Analista'),
        ('gestor', 'Gestor'),
        ('administrador', 'Administrador'),
        ('tablet', 'Tablet (Ponto)'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='analista')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='users')
    ativo = models.BooleanField(default=True)
    profile_photo = models.ImageField(upload_to='profile_photos/', null=True, blank=True, verbose_name='Foto de Perfil')
    acesso_ponto = models.BooleanField(default=False, verbose_name='Acesso Ponto Eletrônico')
    acesso_escala = models.BooleanField(default=False, verbose_name='Acesso Escala')
    
    def is_gestor(self):
        return self.role == 'gestor'
    
    def is_analista(self):
        return self.role == 'analista'
    
    def is_administrador(self):
        return self.role == 'administrador'
    

    def get_initials(self):
        """Retorna as iniciais do usuário para usar como fallback do avatar"""
        if self.first_name and self.last_name:
            return f"{self.first_name[0]}{self.last_name[0]}".upper()
        elif self.first_name:
            return self.first_name[0].upper()
        elif self.username:
            return self.username[0].upper()
        return "?"


class SystemNotification(models.Model):
    CATEGORY_CHOICES = [
        ('system', 'Melhoria do Sistema'),
        ('event', 'Evento'),
        ('news', 'Novidade'),
        ('alert', 'Alerta'),
    ]
    
    title = models.CharField(max_length=200)
    message = models.TextField(verbose_name="Mensagem Resumida")
    details = models.TextField(verbose_name="Detalhes Completos (HTML)", blank=True, null=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='system')
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Notificação do Sistema"
        verbose_name_plural = "Notificações do Sistema"

    def __str__(self):
        return f"[{self.get_category_display()}] {self.title}"

class Escala(models.Model):
    """Modelo legado ou simplificado para manter compatibilidade"""
    nome = models.CharField(max_length=100)
    ativo = models.BooleanField(default=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, null=True, blank=True)
    
    def __str__(self):
        return self.nome



class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('create', 'Criar'),
        ('update', 'Atualizar'),
        ('delete', 'Excluir'),
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('password_reset', 'Reset de Senha'),
        ('status_change', 'Mudança de Status'),
        ('admin_action', 'Ação Administrativa'),
        ('financial_action', 'Ação Financeira'),
        ('permission_change', 'Alteração de Permissões'),
        ('export_data', 'Exportação de Dados'),
        ('ai_usage', 'Uso de IA'),
    ]
    
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    tenant = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    target_type = models.CharField(max_length=100, blank=True)
    target_id = models.IntegerField(null=True, blank=True)
    detalhes_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.usuario} - {self.action}"


# ========================================
# MODELOS PARA ESCALA
# ========================================

class ModeloEscala(models.Model):
    """Regras de jornada (ex: 5x2, 6x1, 12x36) utilizadas dinamicamente"""
    TIPO_CHOICES = [
        ('fixa', 'Fixa'),
        ('rotativa', 'Rotativa'),
        ('personalizado', 'Personalizado'),
    ]

    nome = models.CharField(max_length=100)
    dias_trabalhados = models.IntegerField(default=5)
    dias_folga = models.IntegerField(default=2)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='fixa')
    permite_fim_de_semana = models.BooleanField(default=True, verbose_name="Permitir Finais de Semana")
    observacao = models.TextField(blank=True, null=True)
    # Campo exclusivo para tipo='personalizado': armazena o padrão semanal de ciclo
    # Ex: {"ciclo_semanas": 3, "semanas": [{"dias_folga": [5,6]}, {"dias_folga": [0,1]}, {"dias_folga": [5,6,0]}]}
    ciclo_personalizado = models.JSONField(
        null=True, blank=True,
        verbose_name='Ciclo Personalizado',
        help_text='Padrão semanal de folgas para escala personalizada (JSON)'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'Modelo de Escala'
        verbose_name_plural = 'Modelos de Escala'

    def __str__(self):
        if self.tipo == 'personalizado':
            return f"{self.nome} (Personalizado)"
        return f"{self.nome} ({self.dias_trabalhados}x{self.dias_folga} - {self.get_tipo_display()})"


class ConfiguracaoEscala(models.Model):
    """Singleton para armazenar configurações da Escala Principal"""
    modelo_escala_principal = models.ForeignKey(
        ModeloEscala, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='configuracoes_operacional'
    )
    modelo_escala_principal_gestao = models.ForeignKey(
        ModeloEscala, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='configuracoes_gestao',
        verbose_name='Modelo Principal (Gestão)'
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Configuração de Escala'
        verbose_name_plural = 'Configurações de Escala'

    def __str__(self):
        return "Configuração Principal do Sistema"


class EscalaRascunho(models.Model):
    """Rascunhos/Simulações de escala independentes da escala principal"""
    ESCALA_TIPO_CHOICES = [
        ('operacional', 'Operacional'),
        ('gestao', 'Gestão'),
    ]
    nome = models.CharField(max_length=100)
    autor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rascunhos_escala')
    modelo_escala = models.ForeignKey(ModeloEscala, on_delete=models.SET_NULL, null=True, blank=True, related_name='rascunhos')
    escala_tipo = models.CharField(
        max_length=20, choices=ESCALA_TIPO_CHOICES, default='operacional',
        verbose_name='Tipo de Escala'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Rascunho de Escala'
        verbose_name_plural = 'Rascunhos de Escala'
    
    def __str__(self):
        return f"{self.nome} ({self.autor.username}) [{self.get_escala_tipo_display()}]"

class Turno(models.Model):
    """Turnos de trabalho para a escala"""
    ESCALA_TIPO_CHOICES = [
        ('operacional', 'Operacional'),
        ('gestao', 'Gestão'),
    ]
    rascunho = models.ForeignKey(EscalaRascunho, on_delete=models.CASCADE, null=True, blank=True, related_name='turnos')
    nome = models.CharField(max_length=100)
    horario = models.CharField(max_length=50)  # Ex: "22:00 - 06:00"
    cor = models.CharField(max_length=20, default='#2563eb')  # Cor hexadecimal
    ordem = models.IntegerField(default=0)
    min_analistas = models.IntegerField(default=0, help_text='Número mínimo de analistas ativos exigido no turno. 0 = sem restrição.')
    escala_tipo = models.CharField(
        max_length=20, choices=ESCALA_TIPO_CHOICES, default='operacional',
        verbose_name='Tipo de Escala'
    )
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['ordem', 'nome']
    
    def __str__(self):
        return f"{self.nome} ({self.horario})"


class AnalistaEscala(models.Model):
    """Analistas/Supervisores específicos para a escala NRS (separado do User para flexibilidade)"""
    ESCALA_TIPO_CHOICES = [
        ('operacional', 'Operacional'),
        ('gestao', 'Gestão'),
    ]
    rascunho = models.ForeignKey(EscalaRascunho, on_delete=models.CASCADE, null=True, blank=True, related_name='analistas')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='escala_perfis')
    nome = models.CharField(max_length=200)
    turno = models.ForeignKey(Turno, on_delete=models.SET_NULL, null=True, blank=True, related_name='analistas')
    modelo_escala = models.ForeignKey(ModeloEscala, on_delete=models.SET_NULL, null=True, blank=True, related_name='analistas', help_text="Override do modelo de escala do rascunho/principal")
    pausa = models.CharField(max_length=50, blank=True)  # Ex: "01:00 - 02:00"
    data_primeira_folga = models.DateField(null=True, blank=True)  # Data da primeira folga no ciclo 6x2
    escala_tipo = models.CharField(
        max_length=20, choices=ESCALA_TIPO_CHOICES, default='operacional',
        verbose_name='Tipo de Escala'
    )
    ordem = models.IntegerField(default=0)
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['turno__ordem', 'ordem', 'nome']
    
    def __str__(self):
        return f"{self.nome} - {self.turno.nome if self.turno else 'Sem turno'}"

    @staticmethod
    def format_schedule_name(first_name, last_name):
        """Formata para 'PrimeiroNome S.'"""
        if not first_name:
            return ""
        
        initial = ""
        if last_name:
            initial = f" {last_name[0].upper()}."
        
        return f"{first_name}{initial}"


class FolgaManual(models.Model):
    """Folgas, férias, atestados manuais que sobrescrevem o cálculo automático"""
    TIPO_CHOICES = [
        ('folga', 'Folga'),
        ('ferias', 'Férias'),
        ('atestado', 'Atestado'),
        ('trabalho', 'Trabalho'),  # Para forçar trabalho quando era folga automática
    ]
    
    rascunho = models.ForeignKey(EscalaRascunho, on_delete=models.CASCADE, null=True, blank=True, related_name='folgas')
    analista = models.ForeignKey(AnalistaEscala, on_delete=models.CASCADE, related_name='folgas_manuais')
    data = models.DateField()
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    motivo = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['data']
        unique_together = ['analista', 'data']
    
    def __str__(self):
        return f"{self.analista.nome} - {self.data} - {self.tipo}"


class TrocaFolga(models.Model):
    """Solicitações de troca de folga entre analistas ou para outro dia"""

    TIPO_CHOICES = [
        ('propria', 'Troca de Folga Própria'),    # Cenário 1: mover folga para outro dia
        ('analista', 'Troca com Analista'),        # Cenário 2: trocar folgas com outro analista
    ]

    STATUS_CHOICES = [
        ('pendente_analista', 'Aguardando Analista'),  # Cenário 2: aguardando receptor
        ('pendente_gestor', 'Aguardando Gestor'),       # Aprovado pelo receptor / Cenário 1 direto
        ('aprovada', 'Aprovada'),
        ('rejeitada', 'Rejeitada'),
        ('cancelada', 'Cancelada'),
    ]

    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    rascunho = models.ForeignKey(
        EscalaRascunho, on_delete=models.CASCADE, null=True, blank=True,
        related_name='trocas_folga'
    )

    # Quem solicita
    solicitante = models.ForeignKey(
        AnalistaEscala, on_delete=models.CASCADE,
        related_name='trocas_solicitadas'
    )
    data_solicitante = models.DateField()   # Dia que o solicitante vai ceder (sua folga atual)

    # Contraparte (apenas Cenário 2)
    receptor = models.ForeignKey(
        AnalistaEscala, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='trocas_recebidas'
    )
    data_receptor = models.DateField(null=True, blank=True)  # Dia que o receptor vai ceder / novo dia no Cenário 1

    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pendente_gestor')
    motivo = models.TextField(blank=True)

    # Rastreio de aprovações
    aprovado_receptor_em = models.DateTimeField(null=True, blank=True)
    aprovado_gestor_por = models.ForeignKey(
        'User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='trocas_aprovadas_gestor'
    )
    aprovado_gestor_em = models.DateTimeField(null=True, blank=True)
    motivo_rejeicao = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Troca de Folga'
        verbose_name_plural = 'Trocas de Folga'

    def __str__(self):
        if self.tipo == 'propria':
            return f"{self.solicitante.nome}: mover folga {self.data_solicitante} → {self.data_receptor} [{self.status}]"
        return f"{self.solicitante.nome} ↔ {self.receptor.nome if self.receptor else '?'}: {self.data_solicitante} ↔ {self.data_receptor} [{self.status}]"


class SolicitacaoFolga(models.Model):
    """Solicitações de folga extra (avulsa, banco de horas, outros)"""

    TIPO_CHOICES = [
        ('avulsa', 'Folga Avulsa'),
        ('banco', 'Folga Banco de Horas'),
        ('outros', 'Outros'),
    ]

    STATUS_CHOICES = [
        ('pendente_gestor', 'Aguardando Gestor'),
        ('aprovada', 'Aprovada'),
        ('rejeitada', 'Rejeitada'),
        ('cancelada', 'Cancelada'),
    ]

    analista = models.ForeignKey(
        AnalistaEscala, on_delete=models.CASCADE,
        related_name='solicitacoes_folga'
    )
    rascunho = models.ForeignKey(
        EscalaRascunho, on_delete=models.CASCADE, null=True, blank=True,
        related_name='solicitacoes_folga'
    )
    data = models.DateField()
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    motivo = models.TextField()
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pendente_gestor')

    # Rastreio de aprovações
    aprovado_gestor_por = models.ForeignKey(
        'User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='folgas_solicitadas_aprovadas_gestor'
    )
    aprovado_gestor_em = models.DateTimeField(null=True, blank=True)
    motivo_rejeicao = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Solicitação de Folga'
        verbose_name_plural = 'Solicitações de Folga'

    def __str__(self):
        return f"{self.analista.nome}: {self.get_tipo_display()} em {self.data} [{self.status}]"


# ========================================
# MODELOS PARA ESCALA PERSONALIZADA
# ========================================

class EscalaPersonalizada(models.Model):
    """Grade mensal de folgas/trabalho definida manualmente, dia a dia, por analista.
    Usada quando o analista tem modelo_escala de tipo='personalizado'.
    Sobrescreve completamente o cálculo automático de ciclo para o mês referenciado.
    """
    analista = models.ForeignKey(
        'AnalistaEscala', on_delete=models.CASCADE,
        related_name='escalas_personalizadas'
    )
    rascunho = models.ForeignKey(
        'EscalaRascunho', on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='escalas_personalizadas'
    )
    ano = models.IntegerField(verbose_name='Ano')
    mes = models.IntegerField(verbose_name='Mês')  # 1-12
    # Dicionário com status por data: {"2026-06-01": "folga", "2026-06-02": "trabalho", ...}
    # Valores possíveis: "trabalho", "folga", "ferias", "atestado", "feriado"
    dados = models.JSONField(
        default=dict,
        verbose_name='Dados do Mês',
        help_text='Dicionário {"YYYY-MM-DD": "status"} definindo cada dia do mês'
    )
    # Flag de modo teste — meses em teste não afetam a escala publicada
    modo_teste = models.BooleanField(
        default=False,
        verbose_name='Modo Teste',
        help_text='Se marcado, esse mês não afeta a escala publicada e serve apenas para simulação'
    )
    criado_por = models.ForeignKey(
        'User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='escalas_personalizadas_criadas'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['ano', 'mes', 'analista']
        unique_together = ['analista', 'rascunho', 'ano', 'mes']
        verbose_name = 'Escala Personalizada'
        verbose_name_plural = 'Escalas Personalizadas'
        indexes = [
            models.Index(fields=['analista', 'ano', 'mes']),
            models.Index(fields=['rascunho', 'ano', 'mes']),
        ]

    def __str__(self):
        return f"{self.analista.nome} — {self.mes:02d}/{self.ano}"


class EscalaPersonalizadaTemplate(models.Model):
    """Templates reutilizáveis de escalas personalizadas para replicação entre meses/analistas."""
    nome = models.CharField(max_length=150, verbose_name='Nome do Template')
    descricao = models.TextField(blank=True, verbose_name='Descrição')
    # Dados de um mês de referência — as datas são armazenadas como offsets relativos ao dia 1
    # Ex: {"1": "trabalho", "2": "trabalho", "7": "folga", "8": "folga", ...}
    # Chave = número do dia do mês ("1" a "31"), valor = status
    dados_template = models.JSONField(
        verbose_name='Dados do Template',
        help_text='Dicionário {"DD": "status"} com padrão de um mês de referência'
    )
    # Metadados extras para facilitar a visualização do template
    total_folgas = models.IntegerField(default=0, verbose_name='Total de Folgas')
    total_trabalho = models.IntegerField(default=0, verbose_name='Total de Trabalho')
    criado_por = models.ForeignKey(
        'User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='templates_escala_criados'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'Template de Escala Personalizada'
        verbose_name_plural = 'Templates de Escala Personalizada'

    def __str__(self):
        return f"{self.nome} ({self.total_folgas}F / {self.total_trabalho}T)"





# ========================================
# MODELOS PARA DESEMPENHO DO TIME
# ========================================

class IndicadorDesempenho(models.Model):
    """Métricas mensais de desempenho para analistas"""
    analista = models.ForeignKey(User, on_delete=models.CASCADE, related_name='indicadores_desempenho')
    mes = models.IntegerField()  # 1-12
    ano = models.IntegerField()  # Ex: 2026
    nps = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)  # 0.00 a 10.00
    tme = models.IntegerField(null=True, blank=True)  # Tempo Médio de Espera (segundos)
    chats = models.IntegerField(default=0)  # Volume de atendimentos
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='indicadores_desempenho')
    
    # Metas mensais
    meta_tme = models.IntegerField(null=True, blank=True, help_text="Meta de TME em segundos")
    meta_nps = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True, help_text="Meta de NPS")
    meta_chats = models.IntegerField(null=True, blank=True, help_text="Meta de quantidade de chats")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-ano', '-mes']
        unique_together = ['analista', 'mes', 'ano']
        verbose_name = 'Indicador de Desempenho'
        verbose_name_plural = 'Indicadores de Desempenho'
        
    def __str__(self):
        return f"{self.analista.username} - {self.mes}/{self.ano} (NPS: {self.nps})"


class MetaMensalGlobal(models.Model):
    """Metas globais aplicáveis a todos os analistas em um determinado mês/ano"""
    mes = models.IntegerField()  # 1-12
    ano = models.IntegerField()  # Ex: 2026
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='metas_globais')
    
    meta_tme = models.IntegerField(null=True, blank=True, help_text="Meta global de TME em segundos")
    meta_nps = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True, help_text="Meta global de NPS")
    meta_chats = models.IntegerField(null=True, blank=True, help_text="Meta global de quantidade de chats")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-ano', '-mes']
        unique_together = ['mes', 'ano', 'department']
        verbose_name = 'Meta Mensal Global'
        verbose_name_plural = 'Metas Mensais Globais'
        
    def __str__(self):
        return f"Meta Global - {self.mes}/{self.ano} ({self.department.name})"


class ObservacaoDesempenho(models.Model):
    """Feedbacks, eventos ou observações sobre o desempenho do analista"""
    TIPO_CHOICES = [
        ('feedback', 'Feedback'),
        ('evento', 'Evento'),
        ('treinamento', 'Treinamento'),
        ('elogio', 'Elogio'),
        ('alerta', 'Alerta'),
    ]
    
    analista = models.ForeignKey(User, on_delete=models.CASCADE, related_name='observacoes_desempenho')
    autor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='observacoes_criadas')
    data = models.DateField()
    texto = models.TextField()
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='feedback')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='observacoes_desempenho')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-data', '-created_at']
        verbose_name = 'Observação de Desempenho'
        verbose_name_plural = 'Observações de Desempenho'
    def __str__(self):
        return f"{self.analista.username} - {self.tipo} - {self.data}"





# ========================================
# MODELOS PARA AUDITORIA DE ATENDIMENTOS
# ========================================

class ConfiguracaoAuditoria(models.Model):
    """Configurações globais para o sistema de auditoria de atendimentos"""
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='config_auditoria')
    percentual_minimo_aceitavel = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=77.78,
        help_text="Percentual mínimo de pontuação (0-100) para não gerar alerta. Padrão: 77.78% (7/9 critérios)"
    )
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Configuração de Auditoria'
        verbose_name_plural = 'Configurações de Auditoria'
        unique_together = ['department']
    
    def __str__(self):
        return f"Config Auditoria - {self.department.name} (Mínimo: {self.percentual_minimo_aceitavel}%)"


class BaseAuditoria(models.Model):
    """Base de Conhecimento para a IA de Auditoria de Atendimentos.
    Contém regras, procedimentos e exemplos por critério que a IA usa para auditar chats.
    """
    CATEGORIA_CHOICES = [
        ('apresentacao', 'Critério 1 — Apresentação'),
        ('historico', 'Critério 2 — Análise de Histórico'),
        ('entendimento', 'Critério 3 — Entendimento da Solicitação'),
        ('informacao', 'Critério 4 — Clareza da Informação'),
        ('acordo_espera', 'Critério 5 — Acordo de Espera'),
        ('respeito', 'Critério 6 — Respeito'),
        ('portugues', 'Critério 7 — Língua Portuguesa'),
        ('finalizacao', 'Critério 8 — Finalização do Atendimento'),
        ('procedimento', 'Critério 9 — Procedimento Correto'),
        ('geral', 'Regras Gerais de Atendimento'),
    ]

    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='base_auditoria_ia'
    )
    titulo = models.CharField(max_length=200, verbose_name='Título')
    conteudo = models.TextField(verbose_name='Conteúdo')
    categoria = models.CharField(
        max_length=30,
        choices=CATEGORIA_CHOICES,
        default='geral',
        verbose_name='Categoria / Critério'
    )
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['categoria', 'titulo']
        verbose_name = 'Base de Auditoria IA'
        verbose_name_plural = 'Base de Auditoria IA'

    def __str__(self):
        return f"[{self.get_categoria_display()}] {self.titulo}"


class AuditoriaAtendimento(models.Model):
    """Registro de auditoria de atendimento de analista"""
    TIPO_ATENDIMENTO_CHOICES = [
        ('cliente', 'Cliente'),
        ('franqueado', 'Franqueado'),
    ]
    
    CLASSIFICACAO_CHOICES = [
        ('excelente', 'Excelente'),
        ('bom', 'Bom'),
        ('regular', 'Regular'),
        ('insatisfatorio', 'Insatisfatório'),
    ]
    
    # Informações básicas
    data_atendimento = models.DateField(verbose_name="Data do Atendimento")
    id_conversa = models.CharField(max_length=200, verbose_name="ID da Conversa")
    link_conversa = models.URLField(max_length=500, blank=True, null=True, verbose_name="Link da Conversa")
    tipo_atendimento = models.CharField(max_length=20, choices=TIPO_ATENDIMENTO_CHOICES)
    
    # Relacionamentos
    analista_auditado = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='auditorias_recebidas',
        verbose_name="Analista Auditado"
    )
    auditor = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='auditorias_realizadas',
        verbose_name="Auditor"
    )
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='auditorias_atendimento')
    
    # Critérios de avaliação (9 critérios)
    apresentou_corretamente = models.BooleanField(
        default=True, 
        verbose_name="1. Apresentou-se corretamente?"
    )
    erro_apresentacao = models.TextField(blank=True, verbose_name="Descrição do erro")
    
    analisou_historico = models.BooleanField(
        default=True, 
        verbose_name="2. Analisou o histórico?"
    )
    erro_historico = models.TextField(blank=True, verbose_name="Descrição do erro")
    
    entendeu_solicitacao = models.BooleanField(
        default=True, 
        verbose_name="3. Entendeu a solicitação do cliente/franqueado?"
    )
    erro_entendimento = models.TextField(blank=True, verbose_name="Descrição do erro")
    
    informacao_clara = models.BooleanField(
        default=True, 
        verbose_name="4. Passou a informação de forma clara?"
    )
    erro_informacao = models.TextField(blank=True, verbose_name="Descrição do erro")
    
    acordo_espera = models.BooleanField(
        default=True, 
        verbose_name="5. Realizou acordo de espera corretamente?"
    )
    erro_acordo_espera = models.TextField(blank=True, verbose_name="Descrição do erro")
    
    atendimento_respeitoso = models.BooleanField(
        default=True, 
        verbose_name="6. Realizou atendimento de forma respeitosa?"
    )
    erro_respeito = models.TextField(blank=True, verbose_name="Descrição do erro")
    
    portugues_correto = models.BooleanField(
        default=True, 
        verbose_name="7. Usou a língua portuguesa de forma correta?"
    )
    erro_portugues = models.TextField(blank=True, verbose_name="Descrição do erro")
    
    finalizacao_correta = models.BooleanField(
        default=True, 
        verbose_name="8. Realizou finalização do atendimento corretamente?"
    )
    erro_finalizacao = models.TextField(blank=True, verbose_name="Descrição do erro")
    
    procedimento_correto = models.BooleanField(
        default=True, 
        verbose_name="9. Seguiu o procedimento correto?"
    )
    erro_procedimento = models.TextField(blank=True, verbose_name="Descrição do erro")
    
    # Evidências visuais por critério (opcional)
    imagem_erro_apresentacao = models.TextField(
        blank=True, null=True,
        verbose_name="Evidência - Apresentação",
        help_text="URL ou dados base64 da imagem"
    )
    imagem_erro_historico = models.TextField(
        blank=True, null=True,
        verbose_name="Evidência - Histórico",
        help_text="URL ou dados base64 da imagem"
    )
    imagem_erro_entendimento = models.TextField(
        blank=True, null=True,
        verbose_name="Evidência - Entendimento",
        help_text="URL ou dados base64 da imagem"
    )
    imagem_erro_informacao = models.TextField(
        blank=True, null=True,
        verbose_name="Evidência - Informação",
        help_text="URL ou dados base64 da imagem"
    )
    imagem_erro_acordo_espera = models.TextField(
        blank=True, null=True,
        verbose_name="Evidência - Acordo de Espera",
        help_text="URL ou dados base64 da imagem"
    )
    imagem_erro_respeito = models.TextField(
        blank=True, null=True,
        verbose_name="Evidência - Respeito",
        help_text="URL ou dados base64 da imagem"
    )
    imagem_erro_portugues = models.TextField(
        blank=True, null=True,
        verbose_name="Evidência - Português",
        help_text="URL ou dados base64 da imagem"
    )
    imagem_erro_finalizacao = models.TextField(
        blank=True, null=True,
        verbose_name="Evidência - Finalização",
        help_text="URL ou dados base64 da imagem"
    )
    imagem_erro_procedimento = models.TextField(
        blank=True, null=True,
        verbose_name="Evidência - Procedimento",
        help_text="URL ou dados base64 da imagem"
    )
    
    # Campos calculados automaticamente
    pontuacao = models.IntegerField(default=0, verbose_name="Pontuação (0-9)")
    nota = models.DecimalField(max_digits=4, decimal_places=2, default=0.0, verbose_name="Nota (0-10)")
    classificacao = models.CharField(
        max_length=20, 
        choices=CLASSIFICACAO_CHOICES, 
        default='excelente',
        verbose_name="Classificação"
    )
    requer_acao = models.BooleanField(
        default=False, 
        verbose_name="Requer Ação (Alerta)",
        help_text="Marcado automaticamente quando nota está abaixo do percentual mínimo aceitável"
    )
    
    # Campos de feedback/conversa com o analista
    feedback_data = models.DateField(
        blank=True, null=True,
        verbose_name="Data da Conversa",
        help_text="Data em que o gestor conversou com o analista sobre o alerta"
    )
    feedback_gestor = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='feedbacks_dados',
        verbose_name="Gestor que conversou"
    )
    
    # Ciente do analista sobre a auditoria (para casos de alerta)
    ciente_analista = models.BooleanField(
        default=False,
        verbose_name="Ciente pelo Analista",
        help_text="Marcado pelo analista ao reconhecer a auditoria"
    )
    data_ciente = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Data do Ciente"
    )
    
    # Rastreamento de origem da auditoria
    gerado_por_ia = models.BooleanField(
        default=False,
        verbose_name='Gerado por IA',
        help_text='Indica se esta auditoria foi gerada automaticamente pelo Brisoft IA Auditor'
    )
    observacao_ia = models.TextField(
        blank=True,
        verbose_name='Justificativas da IA',
        help_text='JSON com justificativas da IA para cada critério avaliado'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-data_atendimento', '-created_at']
        verbose_name = 'Auditoria de Atendimento'
        verbose_name_plural = 'Auditorias de Atendimento'
        indexes = [
            models.Index(fields=['analista_auditado', 'data_atendimento']),
            models.Index(fields=['department', 'data_atendimento']),
            models.Index(fields=['classificacao']),
            models.Index(fields=['requer_acao']),
        ]
    
    def calcular_pontuacao(self):
        """Calcula pontuação com base nos critérios atendidos"""
        criterios = [
            self.apresentou_corretamente,
            self.analisou_historico,
            self.entendeu_solicitacao,
            self.informacao_clara,
            self.acordo_espera,
            self.atendimento_respeitoso,
            self.portugues_correto,
            self.finalizacao_correta,
            self.procedimento_correto,
        ]
        return sum(1 for c in criterios if c)
    
    def calcular_nota(self, pontuacao):
        """Calcula nota de 0 a 10 com base na pontuação"""
        return round((pontuacao / 9) * 10, 2)
    
    def calcular_classificacao(self, pontuacao):
        """Determina classificação com base na pontuação"""
        if pontuacao == 9:
            return 'excelente'
        elif pontuacao >= 7:
            return 'bom'
        elif pontuacao >= 5:
            return 'regular'
        else:
            return 'insatisfatorio'
    
    def verificar_alerta(self, nota):
        """Verifica se a nota está abaixo do percentual mínimo aceitável"""
        try:
            # Cache na instância para evitar query repetida durante o mesmo save()
            config = getattr(self, '_config_auditoria_cache', None)
            if config is None:
                config = ConfiguracaoAuditoria.objects.filter(
                    department=self.department,
                    ativo=True
                ).first()
                self._config_auditoria_cache = config
            if config:
                # Converter nota (0-10) para percentual (0-100) para comparação
                return (nota * 10) < float(config.percentual_minimo_aceitavel)
            return False
        except:
            return False
    
    def save(self, *args, **kwargs):
        """Override save para calcular automaticamente pontuação, nota e classificação"""
        # Calcular pontuação
        self.pontuacao = self.calcular_pontuacao()
        
        # Calcular nota
        self.nota = self.calcular_nota(self.pontuacao)
        
        # Determinar classificação
        self.classificacao = self.calcular_classificacao(self.pontuacao)
        
        # Verificar se requer ação
        self.requer_acao = self.verificar_alerta(self.nota)
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Auditoria #{self.id} - {self.analista_auditado.username} - {self.data_atendimento} (Nota: {self.nota})"


# ==================================================
# Modelos para Gestão de RH e Colaboradores
# ==================================================

class CentroCusto(models.Model):
    """Modelo para representar centros de custo"""
    nome = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Centro de Custo"
        verbose_name_plural = "Centros de Custo"
        ordering = ['nome']

    def __str__(self):
        return self.nome


class Cargo(models.Model):
    """Modelo para representar cargos na empresa"""
    nome = models.CharField(max_length=100)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='cargos')
    salario_base = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    descricao = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cargo"
        verbose_name_plural = "Cargos"
        ordering = ['nome']

    def __str__(self):
        return f"{self.nome} ({self.department.name})"


class Holiday(models.Model):
    """Modelo para representar feriados no sistema"""
    name = models.CharField(max_length=100, verbose_name="Nome do Feriado")
    date = models.DateField(verbose_name="Data")
    repeats_annually = models.BooleanField(default=True, verbose_name="Repete todo ano")
    
    # Filtros de aplicação
    apply_to_all = models.BooleanField(default=True, verbose_name="Todos os Funcionários")
    target_companies = models.ManyToManyField('Empresa', blank=True, related_name='holidays', verbose_name="Empresas")
    target_departments = models.ManyToManyField('Department', blank=True, related_name='holidays', verbose_name="Departamentos")
    target_turnos = models.ManyToManyField('Turno', blank=True, related_name='holidays', verbose_name="Horários")

    # Metadados
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Feriado"
        verbose_name_plural = "Feriados"
        ordering = ['date']

    def __str__(self):
        # Para feriado anual, mostrar apenas dia/mês
        if self.repeats_annually:
             return f"{self.name} ({self.date.strftime('%d/%m')})"
        return f"{self.name} ({self.date.strftime('%d/%m/%Y')})"



class Empresa(models.Model):
    """Empresa cadastrada no sistema de ponto / RH"""
    # Informações Gerais
    nome = models.CharField(max_length=255, verbose_name='Nome')
    nome_fantasia = models.CharField(max_length=255, blank=True, verbose_name='Nome Fantasia')
    cnpj = models.CharField(max_length=18, blank=True, verbose_name='CNPJ')
    cei = models.CharField(max_length=30, blank=True, verbose_name='CEI')
    cep = models.CharField(max_length=10, blank=True)
    endereco = models.CharField(max_length=255, blank=True, verbose_name='Endereço')
    bairro = models.CharField(max_length=100, blank=True)
    cidade = models.CharField(max_length=100, blank=True)
    uf = models.CharField(max_length=2, blank=True, verbose_name='UF')
    numero_folha = models.CharField(max_length=30, blank=True, verbose_name='Número da Folha')
    inscricao_estadual = models.CharField(max_length=30, blank=True, verbose_name='Inscrição Estadual')
    fluxo_aprovacao = models.CharField(max_length=100, blank=True, verbose_name='Fluxo de Aprovação')

    # Responsável Legal
    responsavel_cpf = models.CharField(max_length=14, blank=True, verbose_name='CPF do Responsável')
    responsavel_nome = models.CharField(max_length=255, blank=True, verbose_name='Nome do Responsável')
    responsavel_cargo = models.CharField(max_length=100, blank=True, verbose_name='Cargo do Responsável')
    responsavel_email = models.EmailField(blank=True, verbose_name='E-mail do Responsável')

    # Logo
    logo = models.ImageField(upload_to='empresas_logos/', null=True, blank=True)

    # Metadados
    considerar_feriados_ponto = models.BooleanField(default=True, verbose_name='Considerar Feriados no Ponto')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'
        ordering = ['nome']
        indexes = [
            models.Index(fields=['nome']),
        ]

    def __str__(self):
        return self.nome_fantasia or self.nome

    @property
    def num_funcionarios(self):
        try:
            return self.colaboradores_empresa.count()
        except Exception:
            return 0



class Colaborador(models.Model):
    """Modelo central do RH para gestão de informações do funcionário"""

    STATUS_CHOICES = [
        ('ativo', 'Ativo'),
        ('ferias', 'Férias'),
        ('afastado', 'Afastado'),
        ('desligado', 'Desligado'),
    ]
    
    TIPO_CONTRATO_CHOICES = [
        ('clt', 'CLT'),
        ('pj', 'PJ'),
        ('estagio', 'Estágio'),
        ('temporario', 'Temporário'),
    ]

    # Relacionamento opcional com User (caso o colaborador tenha acesso ao sistema)
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='colaborador_perfil')
    
    # Dados Pessoais
    nome_completo = models.CharField(max_length=255)
    cpf = models.CharField(max_length=14, unique=True)
    rg = models.CharField(max_length=20, blank=True)
    data_nascimento = models.DateField(null=True, blank=True)
    endereco = models.TextField(blank=True)
    cep = models.CharField(max_length=10, blank=True)
    bairro = models.CharField(max_length=100, blank=True)
    cidade = models.CharField(max_length=100, blank=True)
    uf = models.CharField(max_length=2, blank=True)
    ramal = models.CharField(max_length=20, blank=True)
    nome_pai = models.CharField(max_length=255, blank=True)
    nome_mae = models.CharField(max_length=255, blank=True)
    genero = models.CharField(max_length=1, blank=True, choices=[('M','Masculino'),('F','Feminino'),('O','Outro')])
    telefone = models.CharField(max_length=20, blank=True)
    email_pessoal = models.EmailField(blank=True)
    foto = models.ImageField(upload_to='colaboradores_fotos/', null=True, blank=True)
    
    # Dados Contratuais
    data_admissao = models.DateField()
    data_desligamento = models.DateField(null=True, blank=True)
    cargo_atual = models.CharField(max_length=100)
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='colaboradores_rh')
    centro_custo = models.ForeignKey('CentroCusto', on_delete=models.SET_NULL, null=True, blank=True, related_name='colaboradores', verbose_name='Centro de Custo')
    empresa = models.ForeignKey('Empresa', on_delete=models.SET_NULL, null=True, blank=True, related_name='colaboradores_empresa', verbose_name='Empresa')
    salario_atual = models.DecimalField(max_digits=10, decimal_places=2)
    tipo_contrato = models.CharField(max_length=20, choices=TIPO_CONTRATO_CHOICES, default='clt')
    jornada_trabalho = models.CharField(max_length=100, blank=True, help_text="Ex: 44h semanais, 10h às 19h")
    horario_padrao = models.ForeignKey('Horario', on_delete=models.SET_NULL, null=True, blank=True, related_name='colaboradores_vinculados')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ativo')
    pis = models.CharField(max_length=14, blank=True, verbose_name='PIS/NIS')
    matricula = models.CharField(max_length=30, blank=True, verbose_name='Matrícula')
    numero_folha = models.CharField(max_length=30, blank=True, verbose_name='Número da Folha')
    ctps = models.CharField(max_length=30, blank=True, verbose_name='CTPS')
    superior_direto = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subordinados', verbose_name='Superior Direto')
    cargo_inicial = models.CharField(max_length=100, blank=True, verbose_name='Cargo na Admissão')

    # Identificação Web / App Mobile
    email_acesso = models.EmailField(blank=True, verbose_name='E-mail de Acesso Web')
    ponto_web_permitido = models.BooleanField(default=False, verbose_name='Permite marcação via Web')
    ponto_web_foto = models.BooleanField(default=False, verbose_name='Exige foto na marcação')
    ponto_web_inserir = models.BooleanField(default=False, verbose_name='Permite inserção de pontos')
    ponto_web_justificativa = models.BooleanField(default=False, verbose_name='Permite inserção de justificativas')
    
    # Metadados
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Colaborador"
        verbose_name_plural = "Colaboradores"
        ordering = ['nome_completo']
        indexes = [
            models.Index(fields=['nome_completo']),
            models.Index(fields=['department']),
            models.Index(fields=['empresa']),
            models.Index(fields=['status']),
        ]

    @property
    def tempo_empresa(self):
        """Calcula o tempo de empresa em anos e meses"""
        fim = self.data_desligamento or timezone.now().date()
        delta = fim - self.data_admissao
        anos = delta.days // 365
        meses = (delta.days % 365) // 30
        
        if anos > 0:
            return f"{anos} ano{'s' if anos > 1 else ''} e {meses} { 'mês' if meses == 1 else 'meses'}"
        return f"{meses} { 'mês' if meses == 1 else 'meses'}"

    def __str__(self):
        return self.nome_completo


class HistoricoProfissional(models.Model):
    """Registro de evolução e mudanças na carreira do colaborador"""
    TIPO_EVENTO_CHOICES = [
        ('admissao', 'Admissão'),
        ('promocao', 'Promoção'),
        ('aumento_salarial', 'Alteração Salarial'),
        ('mudanca_funcao', 'Mudança de Função'),
        ('mudanca_departamento', 'Mudança de Departamento'),
        ('desligamento', 'Desligamento'),
    ]

    colaborador = models.ForeignKey(Colaborador, on_delete=models.CASCADE, related_name='historico')
    data_evento = models.DateField(default=timezone.now)
    tipo_evento = models.CharField(max_length=30, choices=TIPO_EVENTO_CHOICES)
    
    cargo_anterior = models.CharField(max_length=100, blank=True, null=True)
    cargo_novo = models.CharField(max_length=100, blank=True, null=True)
    
    salario_anterior = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    salario_novo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    observacoes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Histórico Profissional"
        verbose_name_plural = "Históricos Profissionais"
        ordering = ['-data_evento']

    def __str__(self):
        return f"{self.colaborador.nome_completo} - {self.get_tipo_evento_display()} em {self.data_evento}"


class PerformanceRH(models.Model):
    """Avaliações de desempenho, feedbacks e PDI"""
    TIPO_CHOICES = [
        ('feedback', 'Feedback'),
        ('pdi', 'Plano de Desenvolvimento (PDI)'),
        ('treinamento', 'Treinamento Realizado'),
        ('avaliacao_anual', 'Avaliação de Desempenho'),
    ]

    colaborador = models.ForeignKey(Colaborador, on_delete=models.CASCADE, related_name='performance')
    avaliador = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='avaliacoes_feitas')
    data_registro = models.DateField(default=timezone.now)
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES)
    
    titulo = models.CharField(max_length=200)
    comentarios = models.TextField()
    proximos_passos = models.TextField(blank=True, verbose_name="Plano de Ação / Próximos Passos")
    
    # Para avaliações quantitativas (NPS, Meta, Nota)
    nota_quantitativa = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Registro de Performance"
        verbose_name_plural = "Registros de Performance"
        ordering = ['-data_registro']

    def __str__(self):
        return f"{self.colaborador.nome_completo} - {self.get_tipo_display()} ({self.data_registro})"


class DocumentoColaborador(models.Model):
    """Documentos anexos ao dossiê do colaborador"""
    colaborador = models.ForeignKey(Colaborador, on_delete=models.CASCADE, related_name='documentos')
    nome = models.CharField(max_length=255)
    arquivo = models.FileField(upload_to='colaboradores_documentos/')
    data_upload = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    class Meta:
        verbose_name = "Documento do Colaborador"
        verbose_name_plural = "Documentos dos Colaboradores"
        ordering = ['-data_upload']

    def __str__(self):
        return f"{self.nome} - {self.colaborador.nome_completo}"


# ==================================================
# SISTEMA DE CONTROLE DE PONTO
# ==================================================

class JustificativaPonto(models.Model):
    """Tipos de justificativa para ocorrências no ponto (faltas, atrasos, etc)"""
    TIPO_CHOICES = [
        ('dia_inteiro', 'Justificar dia inteiro'),
        ('periodo_especifico', 'Período Específico'),
        ('abonar_horas', 'Abonar quantidade de horas'),
        ('ajustar_horas', 'Ajustar quantidade de horas'),
        ('relocar_extrafalta', 'Relocar extra/falta do dia'),
        ('abonar_dsr', 'Abonar apenas DSR (não a ausência)'),
    ]

    nome = models.CharField(max_length=100, verbose_name="Nome/Descrição")
    abreviacao = models.CharField(max_length=20, blank=True, verbose_name="Abreviação")
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES, default='periodo_especifico')
    
    # Parâmetros
    descontar_dsr = models.BooleanField(default=False, verbose_name="Descontar DSR?")
    pedir_texto_motivo = models.BooleanField(default=True, verbose_name="Pedir texto de motivo a cada lançamento")
    abonar_dia_falta = models.BooleanField(default=True, verbose_name="Abonar dia faltoso?")
    informar_cid = models.BooleanField(default=False, verbose_name="Informar CID ao lançar a justificativa")
    mostrar_em_coluna = models.CharField(max_length=50, default='apenas_justificar', verbose_name="Coluna para mostrar")

    # Legado (Mantido temporariamente para sync/retrocompatibilidade)
    codigo = models.CharField(max_length=20, blank=True, verbose_name="Código")
    abonar = models.BooleanField(default=True, verbose_name="Abona Horas?")
    descricao = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Tipo de Justificativa"
        verbose_name_plural = "Tipos de Justificativa"
        ordering = ['nome']

    def __str__(self):
        return self.nome


class LancamentoJustificativa(models.Model):
    """Registro efetivo de uma justificativa aplicada a um funcionário."""
    colaborador = models.ForeignKey(
        'Colaborador', on_delete=models.CASCADE,
        related_name='justificativas_lancadas'
    )
    justificativa = models.ForeignKey(
        JustificativaPonto, on_delete=models.PROTECT
    )
    
    data_inicio = models.DateField(verbose_name="Data Início")
    hora_inicio = models.TimeField(null=True, blank=True, verbose_name="Hora Início")
    data_fim = models.DateField(verbose_name="Data Término")
    hora_fim = models.TimeField(null=True, blank=True, verbose_name="Hora Término")
    
    motivo_texto = models.TextField(blank=True, verbose_name="Texto Justificativa")
    cid = models.CharField(max_length=20, blank=True, verbose_name="CID")
    
    lancado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    data_lancamento = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Lançamento de Justificativa"
        verbose_name_plural = "Lançamentos de Justificativas"
        ordering = ['-data_inicio', '-hora_inicio']
        indexes = [
            models.Index(fields=['colaborador', 'data_inicio']),
        ]

    def __str__(self):
        return f"{self.colaborador.nome_completo} - {self.justificativa.nome} em {self.data_inicio}"


class Horario(models.Model):
    """Modelo principal para definição de regras de cálculo e tipos de horário"""
    TIPO_CHOICES = [
        ('semanal', 'Semanal'),
        ('ciclico', 'Cíclico'),
        ('jornada', 'Jornada'),
    ]
    
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='semanal')
    
    # Novos campos da aba Parâmetros Básicos
    pre_assinalar = models.CharField(max_length=50, default='sem_marcacao', blank=True, null=True)
    modo_compensacao = models.CharField(max_length=50, default='sem_compensacao', blank=True, null=True)
    inicio_mes = models.IntegerField(default=1)
    refeicao_tipo = models.CharField(max_length=50, default='s1_e2', blank=True, null=True)
    quando_feriado = models.CharField(max_length=50, default='extra', blank=True, null=True)
    quando_domingo = models.CharField(max_length=50, default='extra', blank=True, null=True)
    considera_extra_antes = models.CharField(max_length=50, default='considera', blank=True, null=True)
    considera_extra_depois = models.CharField(max_length=50, default='considera', blank=True, null=True)
    considera_extra_intervalo = models.CharField(max_length=50, default='considera', blank=True, null=True)
    considera_extra_intervalo_curto = models.CharField(max_length=50, default='minutos_trabalhados', blank=True, null=True)
    considera_atraso_inicio = models.CharField(max_length=50, default='considera', blank=True, null=True)
    considera_atraso_fim = models.CharField(max_length=50, default='considera', blank=True, null=True)
    considera_atraso_intervalo = models.CharField(max_length=50, default='considera', blank=True, null=True)

    # Novos campos - Tolerâncias
    tol_clt = models.BooleanField(default=True)
    tol_extra_batida = models.IntegerField(default=5)
    tol_falta_batida = models.IntegerField(default=5)
    limite_extra_diario = models.IntegerField(default=10)
    limite_falta_diario = models.IntegerField(default=10)
    descontar_tol_faltas = models.CharField(max_length=50, default='nunca_desconta', blank=True, null=True)
    descontar_tol_extras = models.CharField(max_length=50, default='nunca_desconta', blank=True, null=True)
    quando_limite_extra = models.CharField(max_length=50, default='considera_tudo', blank=True, null=True)
    quando_limite_falta = models.CharField(max_length=50, default='considera_tudo', blank=True, null=True)

    # Novos campos - DSR
    primeiro_dia_semana = models.IntegerField(default=1) # 0=Dom, 1=Seg...
    tempo_dsr = models.CharField(max_length=10, default='07:20')
    max_faltas_dsr = models.CharField(max_length=10, default='02:00')
    desconto_dsr_feriado = models.CharField(max_length=50, default='desconta_normais', blank=True, null=True)

    # Campos específicos para Jornada
    sigla = models.CharField(max_length=10, blank=True, null=True)
    cor = models.CharField(max_length=20, default='#2563eb')
    
    # Campos específicos para Cíclico
    data_inicio = models.DateField(null=True, blank=True)
    dias_ciclo = models.IntegerField(null=True, blank=True)
    
    # Parâmetros Básicos
    folga_nos_intervalos = models.BooleanField(default=False, verbose_name="Folga nos Intervalos (não refeição)")
    almoço_livre_global = models.BooleanField(default=False)
    compensado_global = models.BooleanField(default=False)
    neutro_global = models.BooleanField(default=False)
    
    # Tolerâncias (Art. 58 CLT padrão: 5 min/batida, 10 min/dia)
    tol_entrada = models.IntegerField(default=5)
    tol_saida = models.IntegerField(default=5)
    tol_intervalo = models.IntegerField(default=5)
    tol_diaria = models.IntegerField(default=10)
    
    # DSR
    dia_dsr = models.IntegerField(default=6, choices=[(0, 'Segunda'), (1, 'Terça'), (2, 'Quarta'), (3, 'Quinta'), (4, 'Sexta'), (5, 'Sábado'), (6, 'Domingo')])
    minimo_horas_dsr = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    descontar_faltas_dsr = models.BooleanField(default=True)
    
    # Horas Extras
    utiliza_banco_horas = models.BooleanField(default=False)
    MODO_EXTRA_CHOICES = [
        ('simples', 'Simples (Diário)'),
        ('semanal', 'Semanal'),
        ('mensal', 'Mensal'),
        ('avançado', 'Avançado'),
    ]
    modo_extra = models.CharField(max_length=20, choices=MODO_EXTRA_CHOICES, default='simples')
    percentual_diurno = models.DecimalField(max_digits=5, decimal_places=2, default=50)
    percentual_noturno = models.DecimalField(max_digits=5, decimal_places=2, default=50)
    
    # Modo Simples - Percentuais Detalhados
    perc_extra_dia_diurno = models.DecimalField(max_digits=5, decimal_places=2, default=50)
    perc_extra_dia_noturno = models.DecimalField(max_digits=5, decimal_places=2, default=50)
    perc_extra_sab_diurno = models.DecimalField(max_digits=5, decimal_places=2, default=100)
    perc_extra_sab_noturno = models.DecimalField(max_digits=5, decimal_places=2, default=100)
    perc_extra_dom_diurno = models.DecimalField(max_digits=5, decimal_places=2, default=100)
    perc_extra_dom_noturno = models.DecimalField(max_digits=5, decimal_places=2, default=100)
    perc_extra_feriado_diurno = models.DecimalField(max_digits=5, decimal_places=2, default=100)
    perc_extra_feriado_noturno = models.DecimalField(max_digits=5, decimal_places=2, default=100)
    
    # Noturno
    inicio_noturno = models.TimeField(default='22:00')
    fim_noturno = models.TimeField(default='05:00')
    fator_noturno = models.IntegerField(default=60) # em minutos
    fechamento_noturno_global = models.TimeField(default='00:00')
    
    # Avançado
    desconto_faltas_extras = models.CharField(max_length=50, default='desconta_maior', blank=True, null=True)
    modo_neutro = models.CharField(max_length=50, default='desconsidera_faltas', blank=True, null=True)
    calculo_extra_interjornada = models.CharField(max_length=50, default='nao_calcula', blank=True, null=True)
    perc_extra_interjornada = models.DecimalField(max_digits=5, decimal_places=2, default=50, blank=True, null=True)
    folgas_semana = models.IntegerField(default=0, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Horário"
        verbose_name_plural = "Horários"
        ordering = ['nome']

    def __str__(self):
        return f"{self.nome} ({self.get_tipo_display()})"


class HorarioDetalhe(models.Model):
    """Configuração diária do horário (entradas, saídas e flags)"""
    horario = models.ForeignKey(Horario, on_delete=models.CASCADE, related_name='detalhes')
    dia_index = models.IntegerField() # 0-6 para semanal, 1-N para cíclico, 1 para jornada
    nome_dia = models.CharField(max_length=20, blank=True) # Ex: "Segunda-feira"
    
    entrada_1 = models.TimeField(null=True, blank=True)
    saida_1 = models.TimeField(null=True, blank=True)
    entrada_2 = models.TimeField(null=True, blank=True)
    saida_2 = models.TimeField(null=True, blank=True)
    
    total_horas = models.CharField(max_length=10, default="00:00")
    
    almoco_livre = models.BooleanField(default=False)
    compensado = models.BooleanField(default=False)
    neutro = models.BooleanField(default=False)
    fechamento_noturno = models.TimeField(default='00:00')

    class Meta:
        ordering = ['dia_index']
        unique_together = ['horario', 'dia_index']

    def __str__(self):
        return f"{self.horario.nome} - Dia {self.dia_index}"


class PoliticaHoraExtra(models.Model):
    """Políticas do Modo Avançado de Horas Extras"""
    horario = models.ForeignKey(Horario, on_delete=models.CASCADE, related_name='politicas_hora_extra')
    seq = models.IntegerField(default=1) # Ordem de prioridade
    
    dias = models.CharField(max_length=100, default='qualquer_dia')
    feriado = models.CharField(max_length=100, default='qualquer')
    noturno = models.CharField(max_length=100, default='ambos')
    intervalo = models.CharField(max_length=100, default='tudo')
    dia_especifico = models.CharField(max_length=100, default='qualquer')
    acumulo = models.CharField(max_length=100, default='diario')
    eventos = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['seq']
        verbose_name = "Política de Hora Extra"
        verbose_name_plural = "Políticas de Hora Extra"

    def __str__(self):
        return f"Política #{self.seq} - {self.horario.nome}"


class FaixaHoraExtra(models.Model):
    """Faixas percentuais dentro de uma Política do Modo Avançado"""
    politica = models.ForeignKey(PoliticaHoraExtra, on_delete=models.CASCADE, related_name='faixas')
    de_horas = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    ate_horas = models.DecimalField(max_digits=5, decimal_places=2, default=24)
    acrescimo_percentual = models.DecimalField(max_digits=5, decimal_places=2, default=50)
    banco_horas = models.BooleanField(default=True)
    codigo_evento = models.CharField(max_length=50, blank=True)
    codigo_evento_acrescimo = models.CharField(max_length=50, blank=True)
    
    class Meta:
        ordering = ['de_horas']
        verbose_name = "Faixa de Hora Extra"
        verbose_name_plural = "Faixas de Hora Extra"
        
    def __str__(self):
        return f"{self.de_horas}h às {self.ate_horas}h ({self.acrescimo_percentual}%)"


class EscalaMensal(models.Model):
    """Armazena a escala/jornada diária pintada para o colaborador"""
    TIPO_CHOICES = [
        ('trabalho', 'Trabalho (Regular)'),
        ('folga', 'Folga'),
        ('neutro', 'Dia Neutro'),
        ('compensado', 'Compensado'),
        ('almoço_livre', 'Almoço Livre'),
        ('afastamento', 'Afastamento/Atestado'),
    ]

    colaborador = models.ForeignKey(Colaborador, on_delete=models.CASCADE, related_name='escalas_mensais')
    data = models.DateField()
    horario_previsto = models.ForeignKey(Horario, on_delete=models.SET_NULL, null=True, blank=True, related_name='escalas_mensais')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='trabalho')
    justificativa = models.ForeignKey(JustificativaPonto, on_delete=models.SET_NULL, null=True, blank=True)
    observacao = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Flags (independentes)
    is_compensado = models.BooleanField(default=False)
    is_almoco_livre = models.BooleanField(default=False)
    is_folga = models.BooleanField(default=False)
    is_neutro = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Escala Mensal"
        verbose_name_plural = "Escalas Mensais"
        unique_together = ['colaborador', 'data']
        ordering = ['data']
        indexes = [
            models.Index(fields=['colaborador', 'data']),
        ]

    def __str__(self):
        return f"{self.colaborador.nome_completo} - {self.data} ({self.get_tipo_display()})"


class ConfiguracaoPonto(models.Model):
    """Configuração de jornada e tolerâncias por departamento"""
    department = models.OneToOneField(
        Department, on_delete=models.CASCADE,
        related_name='configuracao_ponto',
        verbose_name='Departamento'
    )
    horario_entrada = models.TimeField(default='08:00', verbose_name='Horário de Entrada')
    horario_saida = models.TimeField(default='17:00', verbose_name='Horário de Saída')
    tolerancia_atraso = models.IntegerField(
        default=10, verbose_name='Tolerância de Atraso (minutos)'
    )
    intervalo_almoco_min = models.IntegerField(
        default=60, verbose_name='Intervalo Mínimo de Almoço (minutos)'
    )
    carga_horaria_diaria = models.IntegerField(
        default=480, verbose_name='Carga Horária Diária (minutos)',
        help_text='Em minutos. Ex: 8h = 480'
    )
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Configuração de Ponto'
        verbose_name_plural = 'Configurações de Ponto'

    def __str__(self):
        return f'Config Ponto — {self.department.name}'


class RegistroPonto(models.Model):
    """Registro individual de ponto eletrônico"""
    TIPO_CHOICES = [
        ('entrada', 'Entrada'),
        ('saida_almoco', 'Saída para Almoço'),
        ('retorno_almoco', 'Retorno do Almoço'),
        ('saida', 'Saída Final'),
    ]
    ORIGEM_CHOICES = [
        ('tablet', 'Tablet'),
        ('web', 'Web (Admin)'),
        ('admin', 'Lançamento Manual'),
    ]

    colaborador = models.ForeignKey(
        'Colaborador', on_delete=models.CASCADE,
        related_name='registros_ponto',
        verbose_name='Colaborador'
    )
    tipo = models.CharField(
        max_length=20, choices=TIPO_CHOICES,
        verbose_name='Tipo de Registro'
    )
    data = models.DateField(verbose_name='Data')
    hora = models.TimeField(verbose_name='Hora')
    foto = models.ImageField(
        upload_to='ponto_fotos/%Y/%m/',
        null=True, blank=True,
        verbose_name='Foto do Registro'
    )
    origem = models.CharField(
        max_length=10, choices=ORIGEM_CHOICES,
        default='tablet', verbose_name='Origem'
    )
    registrado_por = models.ForeignKey(
        'User', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='pontos_registrados',
        verbose_name='Registrado por'
    )
    observacao = models.TextField(
        blank=True, verbose_name='Observação'
    )
    is_deleted = models.BooleanField(default=False, verbose_name='Excluído')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Registro de Ponto'
        verbose_name_plural = 'Registros de Ponto'
        ordering = ['-data', '-hora']
        indexes = [
            models.Index(fields=['colaborador', 'data'], name='ponto_colab_data_idx'),
            models.Index(fields=['data', 'tipo'], name='ponto_data_tipo_idx'),
        ]

    def __str__(self):
        return f'{self.colaborador.nome_completo} — {self.get_tipo_display()} {self.data} {self.hora}'


class BancoHoras(models.Model):
    """Saldo de banco de horas por colaborador (atualizado automaticamente)"""
    colaborador = models.OneToOneField(
        'Colaborador', on_delete=models.CASCADE,
        related_name='banco_horas',
        verbose_name='Colaborador'
    )
    # Saldo em minutos (positivo = crédito, negativo = débito acumulado)
    saldo_minutos = models.IntegerField(
        default=0,
        verbose_name='Saldo (minutos)',
        help_text='Positivo = horas extras, Negativo = horas devidas'
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Banco de Horas'
        verbose_name_plural = 'Banco de Horas'

    @property
    def saldo_formatado(self):
        """Retorna o saldo no formato ±HH:MM"""
        total = abs(self.saldo_minutos)
        horas = total // 60
        mins = total % 60
        sinal = '+' if self.saldo_minutos >= 0 else '-'
        return f'{sinal}{horas:02d}:{mins:02d}'

    def __str__(self):
        return f'Banco Horas — {self.colaborador.nome_completo} ({self.saldo_formatado})'

class VisualColunaApuracao(models.Model):
    """Layouts personalizados de colunas para a tela de Apuração de Ponto"""
    usuario = models.ForeignKey('User', on_delete=models.CASCADE, related_name='visuais_apuracao')
    nome = models.CharField(max_length=100)
    icone = models.CharField(max_length=50, default='bi-layout-text-window')
    colunas = models.JSONField(default=list)
    padrao = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-padrao', 'nome']

    def __str__(self):
        return f'{self.nome} ({self.usuario.username})'

class TipoInconsistencia(models.Model):
    """Configuração de tipos de inconsistência detectáveis na apuração"""
    CAMPO_CHOICES = [
        ('atraso', 'Horas Atraso'),
        ('falta', 'Dia de Falta'),
        ('extra_total', 'Extras Total'),
        ('banco_pos', 'Banco Positivo'),
        ('banco_neg', 'Banco Negativo'),
        ('intervalo_curto', 'Intervalo Curto'),
        ('interjornada', 'Interjornada'),
        ('marcacoes_impares', 'Marcações Ímpares'),
    ]
    
    nome = models.CharField(max_length=100)
    campo = models.CharField(max_length=30, choices=CAMPO_CHOICES)
    tolerancia = models.IntegerField(default=1, help_text="A partir de quantos minutos disparar?")
    prioridade = models.IntegerField(default=5) # 1 mais alta
    icone = models.CharField(max_length=100, default='bi-exclamation-circle-fill')
    cor = models.CharField(max_length=7, default='#dc3545') # Hex code
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['prioridade', 'nome']
        verbose_name = 'Tipo de Inconsistência'
        verbose_name_plural = 'Tipos de Inconsistência'

    def __str__(self):
        return self.nome

class TrocaFeriado(models.Model):
    """Armazena informações de trocas de feriados realizadas pelas empresas."""
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="trocas_feriados")
    data_feriado = models.DateField(verbose_name="Data Original do Feriado")
    descricao = models.CharField(max_length=200, verbose_name="Descrição do Feriado")
    data_troca = models.DateField(verbose_name="Trocado para")
    horarios_beneficiados = models.ManyToManyField(Horario, blank=True, verbose_name="Horários Beneficiados")
    repete_anualmente = models.BooleanField(default=False, verbose_name="Repete Troca Anualmente")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Troca de Feriado"
        verbose_name_plural = "Trocas de Feriado"
        ordering = ['-data_feriado']

    def __str__(self):
        return f"{self.empresa.nome} - {self.descricao} ({self.data_feriado.strftime('%d/%m/%Y')} -> {self.data_troca.strftime('%d/%m/%Y')})"


class BrisoftIABase(models.Model):
    """Base de Conhecimento específica para a IA do Brisoft."""
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="ia_articles", verbose_name="Departamento")
    titulo = models.CharField(max_length=200, verbose_name="Título")
    conteudo = models.TextField(verbose_name="Conteúdo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_nexusiabase'
        verbose_name = "Artigo da Base Brisoft IA"
        verbose_name_plural = "Artigos da Base Brisoft IA"
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.department.name}] {self.titulo}"


class IAQuota(models.Model):
    tenant = models.OneToOneField(Department, on_delete=models.CASCADE, related_name='ia_quota')
    daily_limit = models.IntegerField(default=100)
    monthly_limit = models.IntegerField(default=3000)
    alert_threshold_percent = models.IntegerField(default=80)
    
    def __str__(self):
        return f"Quota IA: {self.tenant.name} (Dia: {self.daily_limit} / Mês: {self.monthly_limit})"

class IAConsumptionLog(models.Model):
    tenant = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='ia_consumptions')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    endpoint = models.CharField(max_length=100)
    tokens_used = models.IntegerField(default=0)
    cost = models.DecimalField(max_digits=10, decimal_places=6, default=0.0)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.tenant.name} - {self.endpoint} em {self.timestamp.strftime('%d/%m/%Y')}"
