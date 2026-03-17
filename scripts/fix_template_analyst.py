#!/usr/bin/env python3
"""Script to fix broken Django template tag in store_audit_form.html"""

import sys

# Read the file
file_path = r"templates\core\store_audit_form.html"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# The broken pattern spans multiple lines
broken_pattern = """por <strong>{{
                                            last_audit.analyst.get_full_name|default:last_audit.analyst.username
                                            }}</strong>"""

# The fixed version (single line)
fixed_pattern = """por <strong>{{ last_audit.analyst.get_full_name|default:last_audit.analyst.username }}</strong>"""

# Replace
if broken_pattern in content:
    content = content.replace(broken_pattern, fixed_pattern)
    print("✓ Found and fixed broken template tag!")
    
    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✓ File saved: {file_path}")
    sys.exit(0)
else:
    print("✗ Broken pattern not found in file")
    print("Searching for variations...")
    
    # Try to find any occurrence  
    if "last_audit.analyst.get_full_name" in content:
        print("✓ Found 'last_audit.analyst.get_full_name' in file")
        
        # Show context
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            if 'last_audit.analyst.get_full_name' in line:
                print(f"\nLine {i}: {line[:100]}...")
                if i > 1:
                    print(f"Line {i-1}: {lines[i-2][:100]}...")
                if i < len(lines):
                    print(f"Line {i+1}: {lines[i][:100]}...")
    else:
        print("✗ Pattern not found at all")
    
    sys.exit(1)
