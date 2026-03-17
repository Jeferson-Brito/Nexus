import re
import os

base_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates', 'base.html')

print(f"Examinando includes em {base_path}...")

try:
    with open(base_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Regex para include
    matches = re.finditer(r'{%\s*include\s+[\'"]([^\'"]+)[\'"]', content)
    
    print("\nArquivos incluídos:")
    found = False
    for m in matches:
        found = True
        print(f" - {m.group(1)}")
    
    if not found:
        print("Nenhum include encontrado.")

except Exception as e:
    print(f"Erro: {e}")
