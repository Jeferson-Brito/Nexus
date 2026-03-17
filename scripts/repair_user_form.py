import re

path = 'templates/core/user_form.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix spacing around == in Django tags
def fix_tag(match):
    tag = match.group(0)
    tag = re.sub(r'(\w|[\'\"]|\|)==', r'\1 ==', tag)
    tag = re.sub(r'==(\w|[\'\"]|\|)', r'== \1', tag)
    return tag

new_content = re.sub(r'\{%.*?%\}', fix_tag, content, flags=re.DOTALL)

if new_content != content:
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Correcoes aplicadas ao user_form.html!")
else:
    print("Nenhuma inconsistencia encontrada.")
