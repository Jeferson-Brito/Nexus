import re

path = 'templates/core/user_form.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern to find {% ... %} even if they span multiple lines
# We want to replace internal newlines and multiple spaces with a single space
def unify_django_tag(match):
    tag = match.group(0)
    # Remove newlines and extra spaces inside the tag
    unified = re.sub(r'\s+', ' ', tag)
    # Ensure spaces around ==
    unified = re.sub(r'(\w|[\'\"]|\|)==', r'\1 ==', unified)
    unified = re.sub(r'==(\w|[\'\"]|\|)', r'== \1', unified)
    return unified

# Find all {% ... %} blocks
new_content = re.sub(r'\{%.*?%\}', unify_django_tag, content, flags=re.DOTALL)

if new_content != content:
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Tags unificadas com sucesso no user_form.html!")
else:
    print("Nenhuma inconsistencia de múltiplas linhas encontrada.")
