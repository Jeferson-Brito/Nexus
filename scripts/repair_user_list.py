import re

path = 'templates/core/user_list.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Unified broken {% ... \n endif %} tags
# We search for {% followed by something, then a newline, then some spaces, then endif %}
pattern = r'\{% (.*?) \n\s+endif %\}'
def unify_tag(match):
    return f'{{% \1 endif %}}'

# Actually, let's be more specific for the one that broke
new_content = re.sub(r'\{% if (.*?) %\}selected\{%\s+endif %\}', r'{% if \1 %}selected{% endif %}', content, flags=re.DOTALL)

# Also fix the specific multi-line case seen in view_file
new_content = re.sub(r'selected\{%\n\s+endif %\}', r'selected{% endif %}', new_content)

if new_content != content:
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Correcoes aplicadas com sucesso!")
else:
    # Try a more aggressive regex if the above didn't work
    new_content = re.sub(r'\{%(.*?)%\}\n\s+', r'{%\1%}', content)
    if new_content != content:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Correcoes agressivas aplicadas!")
    else:
        print("Nenhuma inconsistencia encontrada.")
