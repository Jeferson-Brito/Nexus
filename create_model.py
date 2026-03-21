with open("core/models.py", "a", encoding="utf-8") as f:
    f.write("""
class VisualColunaApuracao(models.Model):
    \"\"\"Layouts personalizados de colunas para a tela de Apuração de Ponto\"\"\"
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
""")
print("VisualColunaApuracao model added to core/models.py")
