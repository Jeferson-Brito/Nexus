import re
import os

path = os.path.join('d:\\', 'Sites', 'Nexus', 'templates', 'core', 'verificacao_lojas.html')
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace bare variables with single quotes
content = re.sub(r'openNotifyModal\(\s*(\{\{[^}]+\}\})\s*\)', r"openNotifyModal('\1')", content)
content = re.sub(r'showFullHistory\(\s*(\{\{[^}]+\}\})\s*\)', r"showFullHistory('\1')", content)
content = re.sub(r'showStoreDetails\(\s*(\{\{[^}]+\}\})\s*\)', r"showStoreDetails('\1')", content)
content = re.sub(r'startTimer\(\s*(\{\{[^}]+\}\})\s*\)', r"startTimer('\1')", content)

# Check for ticketModal opening
content = re.sub(r'openTicketModal\(\s*(\{\{[^}]+\}\})\s*\)', r"openTicketModal('\1')", content)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Replaced successfully')
