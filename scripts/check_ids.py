import re
import sys

with open('templates/core/rh/horarios_form.html', 'r', encoding='utf-8') as f:
    text = f.read()

try:
    html_part, js_part = text.split('<script>', 1)
except ValueError:
    print("Could not split by <script>")
    sys.exit(1)

ids_in_js = set(re.findall(r"getElementById\(['\"]([^'\"]+)['\"]\)", js_part))
missing = []
for el_id in ids_in_js:
    if f'id="{el_id}"' not in html_part and f"id='{el_id}'" not in html_part:
        missing.append(el_id)

print('IDs accessed by JS but not found in HTML:', missing)
