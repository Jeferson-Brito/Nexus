import re

path = 'templates/core/desempenho.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update TME Label
content = content.replace('<label for="kpiTme">TME (segundos)</label>', '<label for="kpiTme">TME (0:00:00)</label>')

# 2. Update TME Input
content = content.replace('<input type="number" id="kpiTme" placeholder="Ex: 120" min="0">', '<input type="text" id="kpiTme" placeholder="Ex: 0:02:00">')

# 3. Update NPS Label
content = content.replace('<label for="kpiNps">NPS (0-10)</label>', '<label for="kpiNps">NPS (0-5)</label>')

# 4. Update NPS Input
content = content.replace('<input type="number" id="kpiNps" placeholder="Ex: 8.5" step="0.01" min="0" max="10">', '<input type="number" id="kpiNps" placeholder="Ex: 4.5" step="0.01" min="0" max="5">')

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Modal de desempenho atualizado com sucesso!")
