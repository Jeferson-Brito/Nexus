import re
import os

def fix_filters(path):
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return
        
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Fix spaces around | in {{ ... }} and {% ... %}
    # Remove space after |
    content = re.sub(r'\|\s+', '|', content)
    # Remove space before |
    content = re.sub(r'\s+\|', '|', content)
    # Remove space after : in filters
    content = re.sub(r'\|\s*(\w+):\s+', r'|\1:', content)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Filtros corrigidos em {path}!")

fix_filters('templates/core/desempenho.html')
