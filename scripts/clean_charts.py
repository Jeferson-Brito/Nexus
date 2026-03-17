import re
import os

path = 'templates/core/desempenho.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix NPS Chart config (remove the redundant plugins block)
nps_pattern = re.compile(r'(npsChart = new Chart\(npsCtx, {.*?options: {.*?)(plugins: { legend: { display: false } },)(.*?scales: {.*?y: { display: false, beginAtZero: true, max: 5.5 } },)', re.DOTALL)
content = nps_pattern.sub(r'\1\3', content)

# Fix Chats Chart config
chats_pattern = re.compile(r'(chatsChart = new Chart\(chatsCtx, {.*?options: {.*?)(plugins: { legend: { display: false } },)(.*?scales: {.*?y: { display: false, beginAtZero: true } },)', re.DOTALL)
content = chats_pattern.sub(r'\1\3', content)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Configuracoes dos graficos limpas com sucesso!")
Header
