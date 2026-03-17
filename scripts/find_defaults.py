import re
import os
import sys

base_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates', 'core', 'verificacao_lojas.html')
output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'defaults_verificacao.txt')

print(f"Examinando {base_path}...")

try:
    with open(base_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    with open(output_path, 'w', encoding='utf-8') as out:
        # Procurar por "|default"
        matches = re.finditer(r'\|default', content)
        
        out.write(f"Ocorrências de '|default' em {base_path}:\n\n")
        
        count = 0
        for m in matches:
            count += 1
            line_num = content[:m.start()].count('\n') + 1
            start = max(0, m.start() - 50)
            end = min(len(content), m.end() + 50)
            snippet = content[start:end].replace('\n', ' ')
            out.write(f"Linha {line_num}: ...{snippet}...\n")
            
        out.write(f"\nTotal: {count} ocorrências.\n")
        
    print(f"Resultado salvo em {output_path}")

except Exception as e:
    print(f"Erro: {e}")
