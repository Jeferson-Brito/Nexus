from django import forms
import re
from .models import Complaint, User, Store


class ComplaintForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = [
            'id_ra', 'cpf_cliente', 'nome_cliente',
            'email_cliente', 'telefone', 'loja_cod',
            'origem_contato', 'tipo_reclamacao', 'descricao', 'status', 'analista',
            'data_reclamacao', 'data_resposta', 'nota_satisfacao',
            'volta_fazer_negocio', 'feedback_text'
        ]
        widgets = {
            'id_ra': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Digite o ID da reclamação'
            }),
            'cpf_cliente': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '000.000.000-00'
            }),
            'nome_cliente': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome e Sobrenome'
            }),
            'email_cliente': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'cliente@email.com'
            }),
            'telefone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '(00) 00000-0000'
            }),
            'loja_cod': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Código da loja'
            }),
            'origem_contato': forms.Select(attrs={
                'class': 'form-control'
            }),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'Adicione aqui a reclamação que o cliente fez no Reclame Aqui'
            }),
            'status': forms.Select(attrs={
                'class': 'form-control'
            }),
            'analista': forms.Select(attrs={
                'class': 'form-control'
            }),
            'data_reclamacao': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'class': 'form-control',
                    'type': 'date',
                    'required': True
                }
            ),
            'data_resposta': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'class': 'form-control',
                    'type': 'date'
                }
            ),
            'tipo_reclamacao': forms.Select(attrs={
                'class': 'form-control'
            }),
            'nota_satisfacao': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'max': 10,
                'placeholder': '0 a 10'
            }),
            'volta_fazer_negocio': forms.Select(attrs={
                'class': 'form-control'
            }),
            'feedback_text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Feedback do cliente (opcional)'
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Nome e Sobrenome label
        self.fields['nome_cliente'].label = "Nome e Sobrenome"
        
        # Descrição não obrigatória
        self.fields['descricao'].required = False
        
        # Filtro de analistas: todos os analistas e gestores ativos do sistema
        responsaveis_queryset = User.objects.filter(
            role__in=['analista', 'gestor'], 
            ativo=True
        ).order_by('first_name')
        
        self.fields['analista'].queryset = responsaveis_queryset
        self.fields['analista'].required = True
        self.fields['analista'].empty_label = "Selecione um responsável"
        
        # Campos obrigatórios
        self.fields['telefone'].required = True
        self.fields['tipo_reclamacao'].required = True
        
        # Origem do contato default
        self.fields['origem_contato'].initial = 'RA'
        
        if user and user.is_analista() and user.ativo:
            # Se o próprio usuário for um analista ativo, pré-selecionar ele
            self.fields['analista'].initial = user
    
    def clean_cpf_cliente(self):
        """Remove formatação do CPF antes de salvar (apenas números)"""
        cpf = self.cleaned_data.get('cpf_cliente')
        if cpf:
            # Remove tudo que não é número
            cpf_clean = re.sub(r'\D', '', cpf)
            
            # Validar que tem exatamente 11 dígitos
            if len(cpf_clean) != 11:
                raise forms.ValidationError('CPF deve conter exatamente 11 dígitos.')
            
            return cpf_clean
        return cpf
    
    def clean_nota_satisfacao(self):
        """Validar que a nota está entre 0 e 10"""
        nota = self.cleaned_data.get('nota_satisfacao')
        if nota is not None:
            if nota < 0 or nota > 10:
                raise forms.ValidationError('A nota de satisfação deve estar entre 0 e 10.')
        return nota


class StoreForm(forms.ModelForm):
    class Meta:
        model = Store
        fields = ['code', 'active', 'suspension_reason']
        labels = {
            'code': 'Código da Loja',
            'active': 'Status (Ativa/Suspensa)',
            'suspension_reason': 'Motivo da Suspensão'
        }
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: PB05'}),
            'active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'suspension_reason': forms.Select(attrs={
                'class': 'form-select',
                'id': 'suspensionReasonSelect'
            })
        }

    def clean_code(self):
        code = self.cleaned_data.get('code')
        if code:
            return code.upper().strip()
        return code
    
    def clean(self):
        cleaned_data = super().clean()
        active = cleaned_data.get('active')
        suspension_reason = cleaned_data.get('suspension_reason')
        
        # Se loja está inativa, motivo é obrigatório
        if not active and not suspension_reason:
            self.add_error('suspension_reason', 'Motivo da suspensão é obrigatório para lojas inativas.')
        
        # Se loja está ativa, limpar motivo
        if active:
            cleaned_data['suspension_reason'] = None
        
        return cleaned_data


