import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
path = os.path.join(BASE_DIR, 'templates', 'core', 'desempenho.html')
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("current_period=='6'", "current_period == '6'")
content = content.replace("current_period=='12'", "current_period == '12'")
content = content.replace("current_period=='all'", "current_period == 'all'")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Corrigido com sucesso')
