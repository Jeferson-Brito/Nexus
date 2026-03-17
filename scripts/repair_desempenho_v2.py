import re
import os

def fix_template_spacing(path):
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return
        
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Pattern to find {% ... %} blocks
    def fix_tag(match):
        tag = match.group(0)
        # Ensure space around == inside {% ... %}
        # Special care for common patterns like selected_analista_id==analista.id
        tag = re.sub(r'(\w|[\'\"]|\|)==', r'\1 ==', tag)
        tag = re.sub(r'==(\w|[\'\"]|\|)', r'== \1', tag)
        # Also handle !=, >=, <= if they exist without spaces
        tag = re.sub(r'(\w|[\'\"]|\|)!=', r'\1 !=', tag)
        tag = re.sub(r'!=(\w|[\'\"]|\|)', r'!= \1', tag)
        return tag

    new_content = re.sub(r'\{%.*?%\}', fix_tag, content, flags=re.DOTALL)

    if new_content != content:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Correcoes aplicadas ao {path}!")
    else:
        print(f"Nenhuma inconsistencia encontrada no {path}.")

# Target files
fix_template_spacing('templates/core/desempenho.html')
