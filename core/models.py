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


class Store(models.Model):
    AUDIT_RESULT_CHOICES = [
        ('pending', 'Pendente'),
        ('conforme', 'Conforme'),
        ('irregular', 'Irregular'),
    ]
    
    SUSPENSION_REASON_CHOICES = [
        ('suspenso', 'Suspenso'),
        ('ponto', 'Ponto'),
        ('locacao', 'Locação'),
        ('implantacao', 'Implantação'),
        ('pausado', 'Pausado'),
        ('distrato', 'Distrato'),
    ]
    
    code = models.CharField(max_length=10, unique=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2)
    address = models.CharField(max_length=200, blank=True)
    active = models.BooleanField(default=True)
    suspension_reason = models.CharField(
        max_length=20, 
        choices=SUSPENSION_REASON_CHOICES, 
        blank=True, 
        null=True,
        verbose_name="Motivo da Suspensão"
    )
    
    # Campos para sistema de reverificação diária
    needs_reverification = models.BooleanField(default=False, verbose_name="Precisa Reverificação")
    last_audit_result = models.CharField(max_length=20, choices=AUDIT_RESULT_CHOICES, default='pending', verbose_name="Resultado da Última Auditoria")
    last_audit_date = models.DateTimeField(null=True, blank=True, verbose_name="Data da Última Auditoria")
    
    def __str__(self):
        return f"{self.code} - {self.city}"

    def save(self, *args, **kwargs):
        # Se for uma atualização (já tem ID)
        if self.pk:
            try:
                # Buscar o estado atual do banco
                old_instance = Store.objects.get(pk=self.pk)
                # Se mudou de Ativa para Suspensa
                if old_instance.active and not self.active:
                    # Remover todas as atribuições desta loja
                    self.analyst_assignments.all().delete()
            except Store.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)

class Escala(models.Model):
    """Modelo legado ou simplificado para manter compatibilidade"""
    nome = models.CharField(max_length=100)
    ativo = models.BooleanField(default=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, null=True, blank=True)
    
    def __str__(self):
        return self.nome
class Complaint(models.Model):
    ORIGEM_CHOICES = [
        ('RA', 'Reclame Aqui'),
        ('Telefone', 'Telefone'),
        ('Email', 'Email'),
        ('WhatsApp', 'WhatsApp'),
        ('Outro', 'Outro'),
    ]
    
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('em_andamento', 'Em Andamento'),
        ('em_replica', 'Em Réplica'),
        ('aguardando_avaliacao', 'Aguardando Avaliação'),
        ('resolvido', 'Resolvido'),
    ]
    
    TIPO_RECLAMACAO_CHOICES = [
        ('nota_fiscal', 'Nota fiscal'),
        ('pagamento_cartao', 'Pagamento não processado - Cartão'),
        ('pagamento_pix', 'Pagamento não processado - PIX'),
        ('pagamento_checkout', 'Pagamento não processado - Checkout Web'),
        ('assinatura_mensal', 'Assinatura mensal'),
        ('lavagem', 'Lavagem'),
        ('secagem', 'Secagem'),
        ('atendimento', 'Atendimento'),
        ('sistema_totem', 'Sistema/Totem'),
        ('cupons', 'Cupons'),
        ('outros', 'Outros'),
    ]
    
    VOLTA_FAZER_NEGOCIO_CHOICES = [
        ('sim', 'Sim'),
        ('nao', 'Não'),
        ('nao_informado', 'Não informado'),
    ]
    
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='complaints', null=True, blank=True)
    id_ra = models.CharField(max_length=100, unique=True)
    cpf_cliente = models.CharField(max_length=14)  # Aceita formato 000.000.000-00
    nome_cliente = models.CharField(max_length=200)
    sobrenome = models.CharField(max_length=200, blank=True)
    email_cliente = models.EmailField()
    telefone = models.CharField(max_length=20)
    loja_cod = models.CharField(max_length=50)
    origem_contato = models.CharField(max_length=20, choices=ORIGEM_CHOICES, default='RA')
    descricao = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    analista = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='complaints')
    data_reclamacao = models.DateField()
    data_resposta = models.DateField(null=True, blank=True)
    tipo_reclamacao = models.CharField(max_length=30, choices=TIPO_RECLAMACAO_CHOICES)
    nota_satisfacao = models.IntegerField(null=True, blank=True)  # 0 a 10
    volta_fazer_negocio = models.CharField(max_length=20, choices=VOLTA_FAZER_NEGOCIO_CHOICES, blank=True, null=True)
    feedback_text = models.TextField(blank=True)
    repeticoes_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['cpf_cliente']),
            models.Index(fields=['id_ra']),
            models.Index(fields=['email_cliente']),
            models.Index(fields=['loja_cod']),
            models.Index(fields=['analista']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            # Índices compostos para filtros por departamento (padrões de query mais comuns)
            models.Index(fields=['department', 'status'], name='complaint_dept_status_idx'),
            models.Index(fields=['department', 'created_at'], name='complaint_dept_created_idx'),
            models.Index(fields=['department', 'analista'], name='complaint_dept_analista_idx'),
        ]
    
    def __str__(self):
        return f"{self.id_ra} - {self.nome_cliente}"
    
    def save(self, *args, **kwargs):
        # Fallback: se o departamento não estiver definido mas houver um analista, 
        # usar o departamento do analista.
        if not self.department and self.analista:
            self.department = self.analista.department
        super().save(*args, **kwargs)


class Activity(models.Model):
    TIPO_CHOICES = [
        ('criacao', 'Criação'),
        ('atualizacao', 'Atualização'),
        ('resposta_cliente', 'Resposta ao Cliente'),
        ('mudanca_status', 'Mudança de Status'),
        ('avaliacao', 'Avaliação'),
        ('comentario_interno', 'Comentário Interno'),
        ('anexo_adicionado', 'Anexo Adicionado'),
    ]
    
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name='activities')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    comentario = models.TextField()
    tipo_interacao = models.CharField(max_length=20, choices=TIPO_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.complaint.id_ra} - {self.tipo_interacao}"


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('create', 'Criar'),
        ('update', 'Atualizar'),
        ('delete', 'Excluir'),
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('password_reset', 'Reset de Senha'),
        ('status_change', 'Mudança de Status'),
    ]
    
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    target_type = models.CharField(max_length=100, blank=True)
    target_id = models.IntegerField(null=True, blank=True)
    detalhes_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.usuario} - {self.action}"


# ========================================
# MODELOS PARA ESCALA NRS SUPORTE
# ========================================

class Turno(models.Model):
    """Turnos de trabalho para a escala"""
    nome = models.CharField(max_length=100)
    horario = models.CharField(max_length=50)  # Ex: "22:00 - 06:00"
    cor = models.CharField(max_length=20, default='#2563eb')  # Cor hexadecimal
    ordem = models.IntegerField(default=0)
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['ordem', 'nome']
    
    def __str__(self):
        return f"{self.nome} ({self.horario})"


class AnalistaEscala(models.Model):
    """Analistas específicos para a escala NRS (separado do User para flexibilidade)"""
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='escala_perfil')
    nome = models.CharField(max_length=200)
    turno = models.ForeignKey(Turno, on_delete=models.SET_NULL, null=True, blank=True, related_name='analistas')
    pausa = models.CharField(max_length=50, blank=True)  # Ex: "01:00 - 02:00"
    data_primeira_folga = models.DateField(null=True, blank=True)  # Data da primeira folga no ciclo 6x2
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


class Evento(models.Model):
    """Eventos para o calendário"""
    TIPO_CHOICES = [
        ('agendamento', 'Agendamento'),
        ('reuniao', 'Reunião'),
        ('visita', 'Visita'),
        ('outro', 'Outro'),
    ]
    
    titulo = models.CharField(max_length=200)
    descricao = models.TextField(blank=True, null=True)
    data_inicio = models.DateTimeField()
    horario = models.CharField(max_length=10, blank=True, null=True)  # Ex: "14:30"
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='agendamento')
    codigo_loja = models.CharField(max_length=50, blank=True, null=True)
    analista_nome = models.CharField(max_length=200, blank=True, null=True)
    observacao = models.TextField(blank=True, null=True)
    
    # Relações
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='eventos')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='eventos_criados')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['data_inicio', 'horario']
        verbose_name = 'Evento'
        verbose_name_plural = 'Eventos'
    
    def __str__(self):
        return f"{self.titulo} ({self.data_inicio.strftime('%d/%m/%Y')})"

class ArtigoBaseConhecimento(models.Model):
    """Artigos da Base de Conhecimento"""
    CATEGORIA_CHOICES = [
        ('tutorials', 'Tutoriais e Guias'),
        ('solutions', 'Soluções Comuns'),
        ('faq', 'Perguntas Frequentes'),
        ('troubleshooting', 'Resolução de Problemas'),
        ('training', 'Treinamentos'),
    ]
    
    titulo = models.CharField(max_length=200)
    conteudo = models.TextField()
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, default='tutorials')
    tags = models.CharField(max_length=255, blank=True)
    views = models.PositiveIntegerField(default=0)
    
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='artigos_kb')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='artigos_kb_criados')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-views', '-created_at']
        verbose_name = 'Artigo da Base de Conhecimento'
        verbose_name_plural = 'Artigos da Base de Conhecimento'

    def __str__(self):
        return self.titulo

class FerramentaIA(models.Model):
    """Links para ferramentas de IA"""
    titulo = models.CharField(max_length=200)
    url = models.URLField(max_length=500)
    descricao = models.TextField()
    categoria = models.CharField(max_length=100, default='ia')
    
    class Meta:
        ordering = ['titulo']
        verbose_name = 'Ferramenta de IA'
        verbose_name_plural = 'Ferramentas de IA'

    def __str__(self):
        return self.titulo


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
# MODELOS PARA QUADRO DE TAREFAS (KANBAN)
# ========================================

class QuadroEtiqueta(models.Model):
    """Etiquetas coloridas para o quadro"""
    nome = models.CharField(max_length=50)
    cor = models.CharField(max_length=20) # Hex code
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='etiquetas_quadro')
    
    class Meta:
        verbose_name = 'Etiqueta do Quadro'
        verbose_name_plural = 'Etiquetas do Quadro'
    
    def __str__(self):
        return f"{self.nome} ({self.department.name})"

class Lista(models.Model):
    """Colunas do Quadro Kanban (ex: A Fazer, Em Andamento)"""
    titulo = models.CharField(max_length=100)
    ordem = models.IntegerField(default=0)
    archived = models.BooleanField(default=False)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='listas_quadro')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['ordem']
        verbose_name = 'Lista do Quadro'
        verbose_name_plural = 'Listas do Quadro'
        
    def __str__(self):
        return f"{self.titulo} - {self.department.name}"


class Cartao(models.Model):
    """Cartões/Tarefas do Quadro Kanban"""
    PRIORIDADE_CHOICES = [
        ('baixa', 'Baixa'),
        ('media', 'Média'),
        ('alta', 'Alta'),
        ('urgente', 'Urgente'),
    ]
    
    titulo = models.CharField(max_length=200)
    descricao = models.TextField(blank=True)
    lista = models.ForeignKey(Lista, on_delete=models.CASCADE, related_name='cartoes')
    ordem = models.IntegerField(default=0)
    
    responsavel = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='cartoes_responsaveis')
    criado_por = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cartoes_criados')
    
    data_limite = models.DateField(null=True, blank=True)
    prioridade = models.CharField(max_length=20, choices=PRIORIDADE_CHOICES, default='media')
    tags = models.CharField(max_length=200, blank=True) # Separadas por vírgula
    
    archived = models.BooleanField(default=False)
    
    membros = models.ManyToManyField(User, related_name='cartoes_membro', blank=True)
    etiquetas = models.ManyToManyField(QuadroEtiqueta, related_name='cartoes', blank=True)
    
    # Nexus Features
    cover_color = models.CharField(max_length=20, blank=True)
    checklists = models.JSONField(default=list, blank=True)
    
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='cartoes_quadro')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['ordem']
        verbose_name = 'Cartão'
        verbose_name_plural = 'Cartões'
        
    def __str__(self):
        return self.titulo


class CartaoComentario(models.Model):
    """Comentários nos cartões"""
    cartao = models.ForeignKey(Cartao, on_delete=models.CASCADE, related_name='comentarios')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comentarios_cartao')
    texto = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']

class CartaoAnexo(models.Model):
    """Anexos nos cartões"""
    cartao = models.ForeignKey(Cartao, on_delete=models.CASCADE, related_name='anexos')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='anexos_cartao')
    arquivo = models.FileField(upload_to='quadro_anexos/%Y/%m/')
    nome_original = models.CharField(max_length=255)
    tipo_arquivo = models.CharField(max_length=100, blank=True)
    tamanho = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-uploaded_at']


# ========================================
# MODELOS PARA TAREFAS E ROTINAS
# ========================================

class Task(models.Model):
    """Tarefas avulsas criadas por gestores"""
    PRIORIDADE_CHOICES = [
        ('baixa', 'Baixa'),
        ('media', 'Média'),
        ('alta', 'Alta'),
        ('urgente', 'Urgente'),
    ]
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('concluida', 'Concluída'),
        ('atrasada', 'Atrasada'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    assigned_to = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assigned_tasks')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_tasks')
    due_date = models.DateTimeField(null=True, blank=True)
    priority = models.CharField(max_length=20, choices=PRIORIDADE_CHOICES, default='media')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    notified = models.BooleanField(default=False)
    warning_sent = models.BooleanField(default=False)
    
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.assigned_to.username})"
    
    class Meta:
        ordering = ['due_date', '-priority']


class Routine(models.Model):
    """Definição de rotinas (atribuições) recorrentes"""
    FREQUENCY_CHOICES = [
        ('diaria', 'Diária'),
        ('semanal', 'Semanal'),
        ('mensal', 'Mensal'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    assigned_to = models.ForeignKey(User, on_delete=models.CASCADE, related_name='routines')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_routines')
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='diaria')
    active = models.BooleanField(default=True)
    notified = models.BooleanField(default=False)
    time_limit = models.TimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Rotina: {self.title} - {self.assigned_to.username}"


class RoutineLog(models.Model):
    """Registro de cumprimento de rotina"""
    routine = models.ForeignKey(Routine, on_delete=models.CASCADE, related_name='logs')
    date = models.DateField()
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    warning_sent = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['routine', 'date']
        ordering = ['-date']

    def __str__(self):
        return f"Log {self.routine.title} - {self.date}"


class RefundRequest(models.Model):
    """Solicitações de estorno entre NRS Suporte e CS Clientes"""
    STATUS_CHOICES = [
        ('aberta', 'Aberta'),
        ('em_analise', 'Em Análise'),
        ('concluida', 'Concluída'),
        ('cancelada', 'Cancelada'),
    ]
    PURCHASE_LOCATION_CHOICES = [
        ('loja_fisica', 'Loja Física'),
        ('site', 'Site'),
    ]
    REFUND_TYPE_CHOICES = [
        ('pix', 'PIX'),
        ('cartao_credito', 'Cartão de Crédito'),
        ('cartao_debito', 'Cartão de Débito'),
        ('checkout_web', 'Checkout Web (Site)'),
        ('saldo_lavanderia', 'Estorno para Saldo da Lavanderia'),
    ]
    
    # Quem solicitou
    analyst = models.ForeignKey(User, on_delete=models.CASCADE, related_name='refund_requests_created')
    store_code = models.CharField(max_length=20)
    
    # Dados do cliente
    customer_name = models.CharField(max_length=200)
    customer_cpf = models.CharField(max_length=14)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=20)
    
    # Detalhes da solicitação
    incident_date = models.DateField()
    incident_time = models.TimeField(null=True, blank=True)  # Horário do ocorrido
    purchase_location = models.CharField(max_length=20, choices=PURCHASE_LOCATION_CHOICES)
    reason = models.TextField()
    checked_cameras = models.BooleanField(default=False)
    refund_value = models.DecimalField(max_digits=10, decimal_places=2)
    refund_type = models.CharField(max_length=30, choices=REFUND_TYPE_CHOICES)
    pix_key = models.CharField(max_length=100, blank=True)
    summary = models.TextField()
    
    # Status e rastreamento
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='aberta')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Rastreamento de visualização pelo CS Clientes
    viewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='viewed_refunds')
    viewed_at = models.DateTimeField(null=True, blank=True)
    
    # Cancelamento (solicitado pelo gestor NRS)
    cancellation_requested = models.BooleanField(default=False)
    cancellation_requested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='cancelled_refunds')
    cancellation_requested_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True, null=True)

    
    # Controle de notificações
    notified_cs = models.BooleanField(default=False)
    notified_nrs_completion = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Estorno #{self.id} - {self.customer_name} ({self.status})"



class RefundRequestAttachment(models.Model):
    """Anexos das solicitações de estorno"""
    refund_request = models.ForeignKey(RefundRequest, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='refund_attachments/')
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"Anexo {self.id} - Solicitação #{self.refund_request.id}"


class ChatInactivityRequest(models.Model):
    """Solicitações de remoção de inatividade em chats"""
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('aprovado', 'Aprovado'),
        ('reprovado', 'Reprovado'),
    ]
    
    analyst = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_inactivity_requests')
    chat_id = models.CharField(max_length=100)
    chat_link = models.URLField(max_length=500)
    chat_date = models.DateField()
    was_inactivity = models.BooleanField(default=True, verbose_name="Foi inatividade?")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_chat_requests')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Solicitação de Inatividade"
        verbose_name_plural = "Solicitações de Inatividade"

    def __str__(self):
        return f"Chat {self.chat_id} - {self.analyst.username} ({self.status})"


# ========================================
# MODELOS PARA VERIFICAÇÃO DE LOJAS (AUDITORIA)
# ========================================

class StoreAudit(models.Model):
    """Representa uma sessão de verificação/auditoria de uma loja"""
    analyst = models.ForeignKey(User, on_delete=models.CASCADE, related_name='store_audits')
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='audits')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Auditoria de Loja"
        verbose_name_plural = "Auditorias de Lojas"

    def __str__(self):
        return f"Auditoria {self.store.code} - {self.created_at.strftime('%d/%m/%Y %H:%M')}"

    def has_irregularities(self):
        return self.items.filter(is_compliant=False).exists()


class StoreAuditItem(models.Model):
    """Itens específicos verificados durante uma auditoria"""
    ITEM_CHOICES = [
        ('cameras', 'Câmeras'),
        ('estofados', 'Estofados'),
        ('cestos_medidas', 'Cestos de medidas'),
        ('layout', 'Layout'),
        ('tv', 'TV'),
        ('totem', 'Totem'),
        ('limpeza', 'Limpeza da loja'),
        ('marketing', 'Marketing'),
    ]
    
    audit = models.ForeignKey(StoreAudit, on_delete=models.CASCADE, related_name='items')
    issue = models.ForeignKey('StoreAuditIssue', on_delete=models.SET_NULL, null=True, blank=True, related_name='items')
    item_name = models.CharField(max_length=50, choices=ITEM_CHOICES)
    is_compliant = models.BooleanField(default=True)
    photo = models.ImageField(upload_to='audit_photos/', null=True, blank=True)
    description = models.TextField(blank=True, help_text="Observações sobre a irregularidade")
    
    # Campos específicos para Câmeras
    cameras_recording = models.BooleanField(null=True, blank=True, verbose_name="Câmeras gravando?")
    cameras_recording_mode = models.CharField(
        max_length=20, 
        choices=[('movimento', 'Por Movimento'), ('continuo', 'Contínuo/24h')],
        null=True, blank=True,
        verbose_name="Modo de gravação"
    )
    
    def __str__(self):
        status = "OK" if self.is_compliant else "IRREGULAR"
        return f"{self.get_item_name_display()} - {status}"


class StoreAuditIssue(models.Model):
    """Solicitação de resolução para itens irregulares de uma loja"""
    STATUS_CHOICES = [
        ('aberta', 'Aberta'),
        ('notificado_whatsapp', 'Notificado (WhatsApp)'),
        ('notificado_ticket', 'Notificado (Ticket)'),
        ('resolvida', 'Resolvida'),
        ('verificado', 'Verificado'),
    ]
    
    RESOLUTION_STAGE_CHOICES = [
        ('pendente', 'Pendente'),
        ('em_contato', 'Em Contato com Franqueado'),
        ('aguardando_acao', 'Aguardando Ação do Franqueado'),
        ('em_validacao', 'Em Validação'),
        ('resolvida', 'Resolvida'),
    ]
    
    NOTIFICATION_CHANNEL_CHOICES = [
        ('whatsapp', 'WhatsApp'),
        ('notificacao', 'Notificação/Email'),
        ('ticket', 'Ticket'),
        ('telefone', 'Telefone'),
        ('presencial', 'Presencial'),
    ]
    
    PRIORITY_CHOICES = [
        ('baixa', 'Baixa'),
        ('media', 'Média'),
        ('alta', 'Alta'),
    ]
    
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='audit_issues', null=True, blank=True)
    gestor_notes = models.TextField(blank=True, verbose_name="Notas do Gestor")
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_audit_issues')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='aberta', db_index=True)
    notified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    # Campos para rastreamento de resolução
    resolution_stage = models.CharField(max_length=30, choices=RESOLUTION_STAGE_CHOICES, default='pendente', verbose_name="Etapa da Resolução")
    notification_channel = models.CharField(max_length=20, choices=NOTIFICATION_CHANNEL_CHOICES, blank=True, null=True, verbose_name="Canal de Notificação")
    resolution_history = models.JSONField(default=list, blank=True, verbose_name="Histórico de Resolução")
    
    # Campos para WhatsApp Timer
    deadline_hours = models.IntegerField(null=True, blank=True, verbose_name="Prazo em Horas", help_text="24-48 horas para WhatsApp")
    deadline_datetime = models.DateTimeField(null=True, blank=True, verbose_name="Data/Hora Limite")
    timer_started_at = models.DateTimeField(null=True, blank=True, verbose_name="Timer Iniciado Em")
    timer_ended_at = models.DateTimeField(null=True, blank=True, verbose_name="Timer Encerrado Em")
    auto_escalated = models.BooleanField(default=False, verbose_name="Escalonado Automaticamente")
    escalation_question_shown = models.BooleanField(default=False, verbose_name="Pergunta de Escalonamento Exibida")
    
    # Campos para Ticket
    ticket_id = models.CharField(max_length=50, null=True, blank=True, verbose_name="ID do Ticket")
    ticket_priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='media', verbose_name="Prioridade do Ticket")
    ticket_responsible = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='ticket_responsible_issues', verbose_name="Responsável pelo Ticket")
    ticket_notes = models.TextField(blank=True, verbose_name="Observações do Ticket")
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Pendência de Auditoria"
        verbose_name_plural = "Pendências de Auditoria"

    def __str__(self):
        return f"Pendência: {self.store.code} ({self.get_status_display()})"
    
    def get_time_remaining(self):
        """Retorna o tempo restante em segundos (usado para o timer)"""
        from django.utils import timezone
        if self.deadline_datetime and self.status == 'notificado_whatsapp':
            now = timezone.now()
            if self.deadline_datetime > now:
                delta = self.deadline_datetime - now
                return delta.total_seconds()
            return 0
        return None
    
    def is_deadline_passed(self):
        """Verifica se o prazo foi ultrapassado"""
        from django.utils import timezone
        if self.deadline_datetime:
            return timezone.now() > self.deadline_datetime
        return False
    
    def get_progress_percentage(self):
        """Retorna a porcentagem do timer que já passou"""
        if not self.timer_started_at or not self.deadline_datetime:
            return 0
        from django.utils import timezone
        now = timezone.now()
        total_time = (self.deadline_datetime - self.timer_started_at).total_seconds()
        elapsed_time = (now - self.timer_started_at).total_seconds()
        if total_time <= 0:
            return 100
        percentage = (elapsed_time / total_time) * 100
        return min(100, max(0, percentage))



class StoreViewerSession(models.Model):
    """Tracks which analysts are currently viewing/auditing a store"""
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='viewer_sessions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='store_viewer_sessions')
    last_heartbeat = models.DateTimeField(auto_now=True)
    is_auditing = models.BooleanField(default=False, help_text="True if user is actively auditing, not just viewing")
    
    class Meta:
        unique_together = ['store', 'user']
        verbose_name = "Sessão de Visualização de Loja"
        verbose_name_plural = "Sessões de Visualização de Lojas"
    
    def __str__(self):
        action = "auditando" if self.is_auditing else "visualizando"
        return f"{self.user.get_full_name() or self.user.username} {action} {self.store.code}"
    
    @classmethod
    def get_active_viewers(cls, store, exclude_user=None, timeout_seconds=15):
        """Get users who have sent a heartbeat within the timeout period"""
        from django.utils import timezone
        from datetime import timedelta
        
        cutoff = timezone.now() - timedelta(seconds=timeout_seconds)
        viewers = cls.objects.filter(store=store, last_heartbeat__gte=cutoff)
        if exclude_user:
            viewers = viewers.exclude(user=exclude_user)
        return viewers


class AnalystAssignment(models.Model):
    """Atribuição de lojas a analistas para verificação"""
    analyst = models.ForeignKey(User, on_delete=models.CASCADE, related_name='store_assignments', db_index=True)
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='analyst_assignments', db_index=True)
    weekly_target = models.IntegerField(default=1, verbose_name="Meta Semanal", help_text="Quantas vezes por semana deve auditar")
    active = models.BooleanField(default=True, verbose_name="Ativo", db_index=True)
    
    # Campos para período personalizado
    period_start = models.DateField(null=True, blank=True, verbose_name="Início do Período")
    period_end = models.DateField(null=True, blank=True, verbose_name="Fim do Período")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['analyst', 'store']
        ordering = ['analyst', 'store__code']
        verbose_name = "Atribuição de Analista"
        verbose_name_plural = "Atribuições de Analistas"
    
    def __str__(self):
        return f"{self.analyst.get_full_name() or self.analyst.username} → {self.store.code}"
    
    def get_weekly_progress(self):
        """Retorna o progresso semanal de auditorias para esta loja"""
        from django.utils import timezone
        from datetime import timedelta
        
        # Calcula o início da semana (segunda-feira)
        today = timezone.now().date()
        start_of_week = today - timedelta(days=today.weekday())
        start_datetime = timezone.make_aware(datetime.combine(start_of_week, datetime.min.time()))
        
        # Conta auditorias feitas nesta semana
        audits_this_week = StoreAudit.objects.filter(
            analyst=self.analyst,
            store=self.store,
            created_at__gte=start_datetime
        ).count()
        
        return {
            'completed': audits_this_week,
            'target': self.weekly_target,
            'percentage': (audits_this_week / self.weekly_target * 100) if self.weekly_target > 0 else 0
        }
    
    def get_days_remaining(self):
        """Retorna dias restantes baseado no período personalizado"""
        from django.utils import timezone
        
        if not self.period_end:
            # Fallback: comportamento antigo (até domingo)
            today = timezone.now().date()
            days_until_sunday = (6 - today.weekday()) % 7
            return days_until_sunday if days_until_sunday > 0 else 0
        
        today = timezone.now().date()
        if today > self.period_end:
            return 0  # Período expirado
        
        delta = self.period_end - today
        return delta.days + 1  # Inclui o dia atual
    
    def get_period_progress(self):
        """Retorna progresso baseado no período personalizado"""
        from django.utils import timezone
        
        # Se não há período definido, usar comportamento semanal antigo
        if not self.period_start or not self.period_end:
            return self.get_weekly_progress()
        
        # Converter datas para datetime com timezone
        start_datetime = timezone.make_aware(
            datetime.combine(self.period_start, datetime.min.time())
        )
        end_datetime = timezone.make_aware(
            datetime.combine(self.period_end, datetime.max.time())
        )
        
        # Contar auditorias no período
        audits_in_period = StoreAudit.objects.filter(
            analyst=self.analyst,
            store=self.store,
            created_at__gte=start_datetime,
            created_at__lte=end_datetime
        ).count()
        
        return {
            'completed': audits_in_period,
            'target': self.weekly_target,
            'percentage': (audits_in_period / self.weekly_target * 100) if self.weekly_target > 0 else 0
        }


class WeeklyVerificationKPI(models.Model):
    """
    Rastreamento de KPI semanal para analistas de verificação de lojas.
    Registra o desempenho de cada semana para visualização de progresso mensal.
    """
    analyst = models.ForeignKey(User, on_delete=models.CASCADE, related_name='weekly_kpis')
    
    # Identificação da semana
    week_start_date = models.DateField(verbose_name="Início da Semana (Segunda)")
    week_number = models.IntegerField(verbose_name="Número da Semana")  # 1-53
    year = models.IntegerField(verbose_name="Ano")
    
    # Métricas de desempenho
    total_assigned_stores = models.IntegerField(default=0, verbose_name="Lojas Atribuídas")
    stores_verified = models.IntegerField(default=0, verbose_name="Lojas Verificadas")
    total_audits_performed = models.IntegerField(default=0, verbose_name="Total de Auditorias")
    
    # Resultado
    goal_met = models.BooleanField(default=False, verbose_name="Meta Atingida")
    completion_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0,
        verbose_name="% de Conclusão"
    )
    
    # Metadados
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-year', '-week_number']
        unique_together = ['analyst', 'year', 'week_number']
        verbose_name = "KPI Semanal de Verificação"
        verbose_name_plural = "KPIs Semanais de Verificação"
        indexes = [
            models.Index(fields=['analyst', 'year', 'week_number']),
            models.Index(fields=['week_start_date']),
        ]
    
    def __str__(self):
        return f"{self.analyst.get_full_name() or self.analyst.username} - Semana {self.week_number}/{self.year} ({self.completion_percentage}%)"
    
    def calculate_metrics(self):
        """Calcula e atualiza as métricas desta semana"""
        from django.utils import timezone
        from datetime import timedelta
        
        # Calcular fim da semana (domingo)
        week_end_date = self.week_start_date + timedelta(days=6)
        
        # Converter para datetime com timezone
        start_datetime = timezone.make_aware(
            datetime.combine(self.week_start_date, datetime.min.time())
        )
        end_datetime = timezone.make_aware(
            datetime.combine(week_end_date, datetime.max.time())
        )
        
        # Buscar atribuições ativas naquela semana
        assignments = AnalystAssignment.objects.filter(
            analyst=self.analyst,
            active=True,
            created_at__lte=end_datetime
        )
        
        self.total_assigned_stores = assignments.count()
        
        # Contar lojas únicas verificadas
        store_ids_verified = set()
        total_audits = 0
        
        for assignment in assignments:
            audits = StoreAudit.objects.filter(
                analyst=self.analyst,
                store=assignment.store,
                created_at__gte=start_datetime,
                created_at__lte=end_datetime
            )
            
            if audits.exists():
                store_ids_verified.add(assignment.store.id)
                total_audits += audits.count()
        
        self.stores_verified = len(store_ids_verified)
        self.total_audits_performed = total_audits
        
        # Calcular porcentagem e meta atingida
        if self.total_assigned_stores > 0:
            self.completion_percentage = (self.stores_verified / self.total_assigned_stores) * 100
            self.goal_met = self.stores_verified >= self.total_assigned_stores
        else:
            self.completion_percentage = 0
            self.goal_met = False
        
        self.save()
        return {
            'stores_verified': self.stores_verified,
            'total_assigned': self.total_assigned_stores,
            'percentage': float(self.completion_percentage),
            'goal_met': self.goal_met
        }


class DailyAuditQuota(models.Model):
    """
    Rastreamento de auditorias diárias por analista.
    Impede que analistas excedam a meta diária de auditorias.
    """
    analyst = models.ForeignKey(User, on_delete=models.CASCADE, related_name='daily_quotas')
    date = models.DateField(verbose_name="Data")
    
    # Meta diária (calculada dinamicamente baseada em lojas pendentes e dias restantes)
    daily_quota = models.IntegerField(default=0, verbose_name="Meta Diária")
    
    # Auditorias realizadas neste dia
    audits_completed = models.IntegerField(default=0, verbose_name="Auditorias Realizadas")

    # Quota extra manual (adicionada pelo gestor apenas para este dia)
    extra_quota = models.IntegerField(default=0, verbose_name="Quota Extra")
    
    # Metadados
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['analyst', 'date']
        ordering = ['-date']
        verbose_name = "Quota Diária de Auditoria"
        verbose_name_plural = "Quotas Diárias de Auditoria"
        indexes = [
            models.Index(fields=['analyst', 'date']),
            models.Index(fields=['date']),
        ]
    
    def __str__(self):
        return f"{self.analyst.get_full_name() or self.analyst.username} - {self.date} ({self.audits_completed}/{self.daily_quota})"
    
    @property
    def is_quota_reached(self):
        """Verifica se a quota diária foi atingida"""
        return self.audits_completed >= self.daily_quota
    
    @property
    def remaining_audits(self):
        """Retorna quantas auditorias ainda podem ser feitas hoje"""
        return max(0, self.daily_quota - self.audits_completed)
    
    @property
    def completion_percentage(self):
        """Porcentagem de conclusão da meta diária"""
        if self.daily_quota == 0:
            return 0
        return min(100, (self.audits_completed / self.daily_quota) * 100)
    
    @classmethod
    def get_or_create_today(cls, analyst):
        """
        Busca ou cria quota de hoje para o analista.
        Recalcula a meta diária automaticamente.
        """
        from django.utils import timezone
        
        # FIX: Use local time instead of UTC to determine "today"
        # This prevents audits done late in the evening (after 21:00 BRT) from counting as tomorrow
        today = timezone.localtime(timezone.now()).date()
        
        quota, created = cls.objects.get_or_create(
            analyst=analyst,
            date=today,
            defaults={'daily_quota': 0, 'audits_completed': 0}
        )
        
        # Recalcular quota diária (pode mudar se lojas forem atribuídas/removidas durante o dia)
        # Recalculate if created OR if audits_completed is 0 (to catch up) OR purely to ensure up-to-date
        # Always recalculating is safer to catch assignment changes
        quota.daily_quota = quota.calculate_daily_target()
        quota.save()
        
        return quota
    
    def is_working_day(self, date_to_check):
        """
        Verifica se é dia de trabalho para o analista, considerando:
        1. Folgas manuais (FolgaManual)
        2. Escala 6x2 (AnalistaEscala)
        """
        # Tentar buscar perfil de escala
        try:
           # O acesso reverso escala_perfil pode lançar exceção se não existir
           escala_profile = self.analyst.escala_perfil
        except Exception:
           # Se não tiver perfil de escala, assume que trabalha todo dia
           return True

        # 1. Verificar se tem folga manual registrada (Folga, Férias, Atestado)
        manual_folga = FolgaManual.objects.filter(
            analista=escala_profile,
            data=date_to_check
        ).first()

        if manual_folga:
            # Se for marcado como 'trabalho', sobrescreve folga automática
            if manual_folga.tipo == 'trabalho':
                return True
            return False # É folga/férias/atestado

        # 2. Calcular Escala 6x2
        if escala_profile.data_primeira_folga:
            delta = (date_to_check - escala_profile.data_primeira_folga).days
            
            # Se delta for negativo (data anterior ao início), assumimos trabalho
            if delta < 0:
                return True
            
            # Ciclo de 8 dias (2 folga + 6 trabalho, já que data_primeira_folga marca o início das folgas)
            cycle_pos = delta % 8
            
            # 0 e 1 são folgas (data_primeira_folga e o dia seguinte)
            # 2 a 7 são dias de trabalho
            return cycle_pos >= 2
        
        return True

    def calculate_daily_target(self):
        """Calcula meta diária do analista baseado em lojas pendentes e dias DE TRABALHO restantes"""
        from django.utils import timezone
        from django.db.models import Count
        from datetime import timedelta, datetime
        
        try:
            # Determine today in Local Time
            today = self.date 
            
            # Buscar perfil de escala uma única vez
            try:
                # O acesso reverso escala_perfil pode lançar exceção se não existir
                escala_profile = self.analyst.escala_perfil
            except Exception:
                escala_profile = None

            # 1. Buscar todas as folgas manuais da semana em uma única query
            start_of_week = today - timedelta(days=today.weekday())
            end_of_week = start_of_week + timedelta(days=6)
            
            manual_folgas_week = {}
            if escala_profile:
                folgas_qs = FolgaManual.objects.filter(
                    analista=escala_profile,
                    data__gte=start_of_week,
                    data__lte=end_of_week
                )
                manual_folgas_week = {f.data: f.tipo for f in folgas_qs}

            # Helper local otimizado para não fazer queries
            def check_working_day_optimized(date_to_check):
                # 1. Manual check
                tipo_manual = manual_folgas_week.get(date_to_check)
                if tipo_manual:
                    return tipo_manual == 'trabalho'
                
                # 2. Escala check
                if not escala_profile:
                    return True
                
                if escala_profile.data_primeira_folga:
                    delta = (date_to_check - escala_profile.data_primeira_folga).days
                    if delta < 0: return True
                    return (delta % 8) >= 2
                return True

            # Se HOJE for folga, meta é 0
            if not check_working_day_optimized(today):
                return 0

            assignments = AnalystAssignment.objects.filter(analyst=self.analyst, active=True)
            
            if not assignments.exists():
                return 0
            
            # Calcular início da semana (segunda-feira)
            start_of_week = today - timedelta(days=today.weekday())
            
            # Create timezone-aware datetime for start of the week (Midnight Monday)
            current_tz = timezone.get_current_timezone()
            start_datetime = datetime.combine(start_of_week, datetime.min.time())
            start_datetime = timezone.make_aware(start_datetime, current_tz)
            
            # Calculate total pending audits across all assignments
            total_pending_audits = 0
            
            # Optimize: Get all audits for this analyst for this week in one query
            # Group by store_id
            weekly_audits_qs = StoreAudit.objects.filter(
                analyst=self.analyst,
                created_at__gte=start_datetime
            ).values('store_id').annotate(count=Count('id'))
            
            # Map store_id -> audit_count
            audits_map = {item['store_id']: item['count'] for item in weekly_audits_qs}
            
            for assignment in assignments:
                # How many audits done for this specific store this week?
                store_audits_done = audits_map.get(assignment.store_id, 0)
                
                # How many are remaining based on weekly target?
                remaining = max(0, assignment.weekly_target - store_audits_done)
                
                total_pending_audits += remaining
            
            if total_pending_audits == 0:
                return 0

            # Calcular dias ÚTEIS restantes na semana (Hoje até Domingo)
            # 0=Seg, 1=Ter, ..., 4=Sex, 5=Sab, 6=Dom
            
            working_days_remaining = 0
            # Check today and future days up to Sunday
            # +1 because range is exclusive
            days_to_check = (6 - today.weekday()) + 1 
            
            for i in range(days_to_check):
                date_check = today + timedelta(days=i)
                if check_working_day_optimized(date_check):
                    working_days_remaining += 1
            
            # Garantir divisor mínimo de 1
            divisor = max(1, working_days_remaining)
            
            import math
            # Meta diária = teto(auditorias pendentes / dias úteis restantes) + extra_quota
            # Isso garante que se faltam 5 auditorias e tem 2 dias, faz 3 hoje e 2 amanhã
            daily_target = math.ceil(total_pending_audits / divisor)
            
            # Adicionar a quota extra manual
            daily_target += self.extra_quota

            return int(daily_target)
            
        except Exception as e:
            # Fallback seguro para evitar crash do dashboard
            print(f"Erro ao calcular meta diária: {e}")
            return 5 # Default safe value
    
    def increment_audits(self):
        """Incrementa contador de auditorias realizadas hoje"""
        self.audits_completed += 1
        self.save()
        return not self.is_quota_reached  # Retorna True se ainda pode auditar


# ========================================
# MODELOS PARA CHAT INTERNO
# ========================================

class Conversation(models.Model):
    """Conversa entre dois usuários"""
    participants = models.ManyToManyField(User, related_name='chat_conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Conversa'
        verbose_name_plural = 'Conversas'
    
    def get_other_participant(self, user):
        """Retorna o outro participante da conversa"""
        return self.participants.exclude(id=user.id).first()
    
    def get_last_message(self):
        """Retorna a última mensagem da conversa"""
        return self.messages.order_by('-created_at').first()
    
    def get_unread_count(self, user):
        """Conta mensagens não lidas para um usuário"""
        return self.messages.filter(is_read=False).exclude(sender=user).count()
    
    def __str__(self):
        participants_names = ", ".join([p.get_full_name() or p.username for p in self.participants.all()[:2]])
        return f"Conversa: {participants_names}"


class Message(models.Model):
    """Mensagem em uma conversa"""
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_messages_sent')
    content = models.TextField()
    attachment = models.FileField(upload_to='chat_attachments/', null=True, blank=True)
    file_name = models.CharField(max_length=255, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
            models.Index(fields=['sender', 'is_read']),
        ]
        verbose_name = 'Mensagem'
        verbose_name_plural = 'Mensagens'
    
    def __str__(self):
        return f"{self.sender.username}: {self.content[:50]}..."


class UserOnlineStatus(models.Model):
    """Status online do usuário para o chat"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='chat_online_status')
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Status Online'
        verbose_name_plural = 'Status Online'
    
    def __str__(self):
        status = "Online" if self.is_online else "Offline"
        return f"{self.user.username}: {status}"


# ============================================
# KANBAN BOARD MODELS
# ============================================

class KanbanBoard(models.Model):
    """Quadro Kanban (equivalente a um Board do Trello)"""
    VISIBILITY_CHOICES = [
        ('private', 'Privado'),
        ('team', 'Equipe'),
        ('public', 'Público'),
    ]
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    background_color = models.CharField(max_length=7, default='#0079bf')
    background_image = models.URLField(blank=True)
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='private')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_boards')
    is_archived = models.BooleanField(default=False)
    is_favorite = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Quadro Kanban'
        verbose_name_plural = 'Quadros Kanban'
    
    def __str__(self):
        return self.name


class BoardMembership(models.Model):
    """Membros de um quadro com permissões"""
    ROLE_CHOICES = [
        ('admin', 'Administrador'),
        ('member', 'Membro'),
        ('viewer', 'Visualizador'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='board_memberships')
    board = models.ForeignKey(KanbanBoard, on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    joined_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'board']
        verbose_name = 'Membro do Quadro'
        verbose_name_plural = 'Membros do Quadro'
    
    def __str__(self):
        return f"{self.user.username} - {self.board.name} ({self.role})"


class KanbanList(models.Model):
    """Lista/Coluna dentro de um quadro"""
    board = models.ForeignKey(KanbanBoard, on_delete=models.CASCADE, related_name='lists')
    name = models.CharField(max_length=200)
    position = models.PositiveIntegerField(default=0)
    card_limit = models.PositiveIntegerField(null=True, blank=True)
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['position']
        verbose_name = 'Lista Kanban'
        verbose_name_plural = 'Listas Kanban'
    
    def __str__(self):
        return f"{self.name} ({self.board.name})"


class CardLabel(models.Model):
    """Etiquetas/Labels para cartões"""
    board = models.ForeignKey(KanbanBoard, on_delete=models.CASCADE, related_name='labels')
    name = models.CharField(max_length=50, blank=True)
    color = models.CharField(max_length=7, default='#61bd4f')
    
    class Meta:
        verbose_name = 'Etiqueta'
        verbose_name_plural = 'Etiquetas'
    
    def __str__(self):
        return f"{self.name or 'Sem nome'} ({self.color})"


class KanbanCard(models.Model):
    """Cartão dentro de uma lista"""
    list = models.ForeignKey(KanbanList, on_delete=models.CASCADE, related_name='cards')
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    position = models.PositiveIntegerField(default=0)
    due_date = models.DateTimeField(null=True, blank=True)
    due_complete = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    cover_color = models.CharField(max_length=7, blank=True)
    cover_image = models.URLField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_cards')
    assigned_to = models.ManyToManyField(User, related_name='assigned_cards', blank=True)
    labels = models.ManyToManyField(CardLabel, related_name='cards', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['position']
        verbose_name = 'Cartão Kanban'
        verbose_name_plural = 'Cartões Kanban'
    
    def __str__(self):
        return self.title
    
    @property
    def checklist_progress(self):
        """Retorna progresso dos checklists (completed, total)"""
        items = ChecklistItem.objects.filter(checklist__card=self)
        total = items.count()
        completed = items.filter(is_completed=True).count()
        return {'completed': completed, 'total': total}
    
    @property
    def is_overdue(self):
        """Verifica se o cartão está vencido"""
        from django.utils import timezone
        if self.due_date and not self.due_complete:
            return self.due_date < timezone.now()
        return False


class Checklist(models.Model):
    """Checklist dentro de um cartão"""
    card = models.ForeignKey(KanbanCard, on_delete=models.CASCADE, related_name='checklists')
    title = models.CharField(max_length=200)
    position = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['position']
        verbose_name = 'Checklist'
        verbose_name_plural = 'Checklists'
    
    def __str__(self):
        return self.title


class ChecklistItem(models.Model):
    """Item de um checklist"""
    checklist = models.ForeignKey(Checklist, on_delete=models.CASCADE, related_name='items')
    text = models.CharField(max_length=500)
    is_completed = models.BooleanField(default=False)
    position = models.PositiveIntegerField(default=0)
    due_date = models.DateTimeField(null=True, blank=True)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['position']
        verbose_name = 'Item do Checklist'
        verbose_name_plural = 'Itens do Checklist'
    
    def __str__(self):
        status = "✓" if self.is_completed else "○"
        return f"{status} {self.text}"


class CardComment(models.Model):
    """Comentário em um cartão"""
    card = models.ForeignKey(KanbanCard, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='card_comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Comentário'
        verbose_name_plural = 'Comentários'
    
    def __str__(self):
        return f"{self.author.username}: {self.content[:50]}..."


class CardAttachment(models.Model):
    """Anexo de um cartão"""
    card = models.ForeignKey(KanbanCard, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='kanban_attachments/')
    filename = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'Anexo'
        verbose_name_plural = 'Anexos'
    
    def __str__(self):
        return self.filename


class CardActivity(models.Model):
    """Log de atividades de um cartão"""
    ACTION_CHOICES = [
        ('created', 'Criado'),
        ('moved', 'Movido'),
        ('updated', 'Atualizado'),
        ('commented', 'Comentado'),
        ('assigned', 'Atribuído'),
        ('due_date', 'Data alterada'),
        ('label_added', 'Etiqueta adicionada'),
        ('label_removed', 'Etiqueta removida'),
        ('checklist_added', 'Checklist adicionado'),
        ('checklist_completed', 'Checklist concluído'),
        ('attachment_added', 'Anexo adicionado'),
        ('archived', 'Arquivado'),
    ]
    
    card = models.ForeignKey(KanbanCard, on_delete=models.CASCADE, related_name='activities')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Atividade'
        verbose_name_plural = 'Atividades'
    
    def __str__(self):
        return f"{self.user.username} - {self.action} - {self.card.title}"


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
    nome = models.CharField(max_length=100, verbose_name="Nome da Justificativa")
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

    # Novos campos RHID - Tolerâncias
    tol_clt = models.BooleanField(default=True)
    tol_extra_batida = models.IntegerField(default=5)
    tol_falta_batida = models.IntegerField(default=5)
    limite_extra_diario = models.IntegerField(default=10)
    limite_falta_diario = models.IntegerField(default=10)
    descontar_tol_faltas = models.CharField(max_length=50, default='nunca_desconta', blank=True, null=True)
    descontar_tol_extras = models.CharField(max_length=50, default='nunca_desconta', blank=True, null=True)
    quando_limite_extra = models.CharField(max_length=50, default='considera_tudo', blank=True, null=True)
    quando_limite_falta = models.CharField(max_length=50, default='considera_tudo', blank=True, null=True)

    # Novos campos RHID - DSR
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
