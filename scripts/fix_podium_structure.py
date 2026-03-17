import re

# Read the file
with open('templates/core/desempenho.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find and replace line by line
in_function = False
for i, line in enumerate(lines):
    # Change itemsHtml to stepsHtml
    if 'let itemsHtml' in line:
        lines[i] = line.replace('itemsHtml', 'stepsHtml')
    elif 'itemsHtml +=' in line:
        lines[i] = line.replace('itemsHtml', 'stepsHtml')
    # Change podium-item to podium-step
    elif 'class="podium-item"' in line:
        lines[i] = line.replace('class="podium-item"', 'class="podium-step ${positionClass}"')
    # Change podium-position to step-badge
    elif 'class="podium-position ${positionClass}"' in line:
        lines[i] = line.replace('class="podium-position ${positionClass}"', 'class="step-badge"')
    # Change podium-info to step-platform
    elif 'class="podium-info"' in line:
        lines[i] = line.replace('class="podium-info"', 'class="step-platform"')
    # Change podium-name to step-name
    elif 'class="podium-name"' in line:
        lines[i] = line.replace('class="podium-name"', 'class="step-name"')
    # Change podium-value to step-value  
    elif 'class="podium-value"' in line:
        lines[i] = line.replace('class="podium-value"', 'class="step-value"')
    # Change ${itemsHtml} to ${stepsHtml} wrapped in podium-steps
    elif '${itemsHtml}' in line:
        indent = line[:len(line) - len(line.lstrip())]
        lines[i] = f'{indent}<div class="podium-steps">\n'
        lines.insert(i+1, f'{indent}    ${{stepsHtml}}\n')
        lines.insert(i+2, f'{indent}</div>\n')

# Write back
with open('templates/core/desempenho.html', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Podium HTML structure converted successfully!")
