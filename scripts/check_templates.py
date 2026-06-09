import os
import re

base_dir = r"c:\Users\Dell G15\Documents\Sites\Brisoft"
views_dir = os.path.join(base_dir, 'core', 'views')
api_dir = os.path.join(base_dir, 'core', 'api')
templates_dir = os.path.join(base_dir, 'templates')

template_pattern = re.compile(r"render\([^,]+,\s*['\"]([^'\"]+)['\"]")
missing_templates = []

def check_dir(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    matches = template_pattern.findall(content)
                    for match in matches:
                        template_path = os.path.join(templates_dir, match)
                        if not os.path.exists(template_path):
                            missing_templates.append((filepath, match))

check_dir(views_dir)
check_dir(api_dir)

if missing_templates:
    print("Missing templates found:")
    for filepath, template in missing_templates:
        print(f"File: {filepath} refers to missing template: {template}")
else:
    print("All template references are valid.")
