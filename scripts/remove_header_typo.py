import os

path = 'templates/core/desempenho.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Remove the specific typo " } Header" or just "Header" at ends of lines
# My scripts were adding " Header" at the end of output strings
new_content = content.replace('} Header', '}').replace('Header\n', '\n')

with open(path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Typo 'Header' removido com sucesso!")
Header
