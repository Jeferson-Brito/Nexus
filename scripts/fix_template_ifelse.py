#!/usr/bin/env python3
"""Script to fix broken Django if/else template tag in store_audit_form.html"""

# Read the file
file_path = r"templates\core\store_audit_form.html"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# The broken pattern
broken_pattern = """Última Auditoria: {% if last_audit.has_irregularities %}Irregular{% else
                                        %}Conforme{% endif %}"""

# The fixed version (single line)
fixed_pattern = """Última Auditoria: {% if last_audit.has_irregularities %}Irregular{% else %}Conforme{% endif %}"""

# Replace
if broken_pattern in content:
    content = content.replace(broken_pattern, fixed_pattern)
    print("✓ Found and fixed broken if/else template tag!")
    
    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✓ File saved: {file_path}")
else:
    print("✗ Exact pattern not found, trying line-by-line fix...")
    
    lines = content.split('\n')
    fixed = False
    
    for i in range(len(lines) - 1):
        # Look for the broken pattern across two lines
        if 'Irregular{% else' in lines[i] and '%}Conforme{% endif %}' in lines[i+1]:
            print(f"✓ Found broken pattern at lines {i+1}-{i+2}")
            
            # Extract the parts
            line1 = lines[i].rstrip()
            line2_content = lines[i+1].strip()
            
            # Merge them
            if line1.endswith('{% else'):
                lines[i] = line1 + ' %}Conforme{% endif %}'
                lines[i+1] = ''  # Clear the second line
                fixed = True
                break
    
    if fixed:
        content = '\n'.join(lines)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✓ File saved: {file_path}")
    else:
        print("✗ Could not find pattern to fix")
