import re
import os

path = 'templates/core/desempenho.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Extract all script blocks
# This regex will find all <script...</script> blocks
scripts = re.findall(r'<script.*?>.*?</script>', content, re.DOTALL)

# 2. Remove them from the current content
new_content = re.sub(r'<script.*?>.*?</script>', '', content, flags=re.DOTALL)

# 3. Ensure {% endblock %} is present and split correctly
# Assume the last {% endblock %} is the end of block content
parts = new_content.rsplit('{% endblock %}', 1)
if len(parts) == 2:
    # Reassemble: content + endblock content + start block scripts + scripts + endblock scripts
    final_content = parts[0] + '{% endblock %}\n\n{% block scripts %}\n' + '\n'.join(scripts) + '\n{% endblock %}'
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(final_content)
    print("Scripts movidos para o bloco scripts com sucesso!")
else:
    print("Nao foi possivel encontrar o final do bloco content.")
Header
