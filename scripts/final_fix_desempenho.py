import re
import os

def fix_django_tags(path):
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return
        
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Function to add spaces around operators inside {% ... %}
    def space_operators(match):
        tag_content = match.group(1)
        # Add spaces around ==, !=, <=, >=, <, >
        # First remove any existing spaces to avoid duplication
        tag_content = re.sub(r'\s*([=!<>]=|[<>])\s*', r' \1 ', tag_content)
        # Clean up double spaces
        tag_content = re.sub(r'\s+', ' ', tag_content).strip()
        return f'{{% {tag_content} %}}'

    # Regex to find {% ... %} blocks
    new_content = re.sub(r'\{%\s*(.*?)\s*%\}', space_operators, content)

    # Also fix filters in {{ ... }} tags while we are at it
    def space_filters(match):
        tag_content = match.group(1)
        # Filters should NOT have spaces around | or :
        tag_content = re.sub(r'\s*\|\s*', '|', tag_content)
        tag_content = re.sub(r'\s*:\s*', ':', tag_content)
        return f'{{{{ {tag_content.strip()} }}}}'

    new_content = re.sub(r'\{\{\s*(.*?)\s*\}\}', space_filters, new_content)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"Django tags fixed in {path}!")

fix_django_tags('templates/core/desempenho.html')
