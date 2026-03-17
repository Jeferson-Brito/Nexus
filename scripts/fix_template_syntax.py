import re

# Read the file
with open('templates/core/desempenho.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace all instances of current_period=='' with current_period == ''
content = re.sub(r"current_period=='6'", "current_period == '6'", content)
content = re.sub(r"current_period=='12'", "current_period == '12'", content)
content = re.sub(r"current_period=='all'", "current_period == 'all'", content)

# Write back
with open('templates/core/desempenho.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Template fixed successfully!")
