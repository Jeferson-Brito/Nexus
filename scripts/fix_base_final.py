
file_path = r'c:\Users\jeffe\Documents\Sites\CSHub\templates\base.html'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Line 200 is index 199 (0-indexed)
# Let's inspect line 199 and 200 to be sure
print(f"Index 199: {lines[199]!r}")
# Ideally it matches the span
# I will search for the specific line containing "Men Desempenho" or "Desempenho do Time"
found_i = -1
for i, line in enumerate(lines):
    if "Desempenho do Time" in line:
        found_i = i
        print(f"Found at index {i}: {line!r}")
        break

if found_i != -1:
    # Rewrite it cleanly
    # <span class="link-text">{% if user.role == 'analista' %}Meu Desempenho{% else %}Desempenho do Time{% endif %}</span>
    # Ensure correct indentation (looks like 16 spaces?)
    
    current_indent = lines[found_i][:lines[found_i].find('<')]
    if not current_indent.strip(): # if it's all whitespace
        pass
    else:
        current_indent = '                ' # 16 spaces default

    new_line = current_indent + '<span class="link-text">{% if user.role == "analista" %}Meu Desempenho{% else %}Desempenho do Time{% endif %}</span>\n'
    
    # Check if lines[found_i+1] is a stray endif?
    next_line = lines[found_i+1]
    if 'endif' in next_line and 'if' not in next_line and 'url' not in next_line:
         print(f"Next line looks like stray endif: {next_line!r}. REMOVING IT.")
         del lines[found_i+1]
    
    lines[found_i] = new_line
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print("Fixed.")
else:
    print("Line not found!")
