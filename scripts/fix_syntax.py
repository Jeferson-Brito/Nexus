
import os

file_path = r'c:\Users\jeffe\Documents\Sites\Nexus\templates\base.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix space in default: 0
new_content = content.replace('|default: 0', '|default:0')

if content != new_content:
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("SUCCESS: File fixed.")
else:
    print("WARNING: No changes made. Searching for other variations...")
    # Try with different spacing
    import re
    new_content = re.sub(r'\|default:\s+', '|default:', content)
    if content != new_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("SUCCESS: File fixed (regex).")
    else:
        print("ERROR: Could not find any malformed default filter.")
