import os

path = 'templates/base.html'
with open(path, 'rb') as f:
    content = f.read()

# Try to decode
try:
    text = content.decode('utf-8')
except:
    text = content.decode('cp1252')

# Fix double newlines and strip whitespace
lines = [line.strip() for line in text.splitlines() if line.strip() != '']

new_lines = []
skip_tutorial = False

for line in lines:
    # Skip tutorial-related stuff
    if '<!-- Driver.js (Onboarding) -->' in line or 'onboarding.js' in line:
        continue
    if 'const userHasSeenTutorial' in line or 'const userDepartmentName' in line or 'const userRoleName' in line:
        continue
    if 'const currentUserId' in line and (line.endswith(';') or '{{' in line):
        # Fix and keep currentUserId
        new_lines.append('        const currentUserId = {{ user.id|default:0 }};')
        continue
    
    # Check for the corrupted CSS section and restore missing headers
    if 'border-radius: 8px 8px 0 0 !important;' in line:
        # If it seems misplaced (no style tag before it in new_lines)
        has_style = any('<style>' in l for l in new_lines[-10:])
        if not has_style:
            new_lines.append('    <link rel="stylesheet" href="{% static \'css/floating_chat.css\' %}">')
            new_lines.append('    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/easymde/dist/easymde.min.css">')
            new_lines.append('    <script src="https://cdn.jsdelivr.net/npm/easymde/dist/easymde.min.js"></script>')
            new_lines.append('    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/sweetalert2@11/dist/sweetalert2.min.css">')
            new_lines.append('    <script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>')
            new_lines.append('    {% block extra_css %}{% endblock %}')
            new_lines.append('    <style>')
            new_lines.append('        .editor-toolbar {')
    
    new_lines.append(line)

# Final cleanup heuristic: if we opened a style tag and didn't close it properly? 
# The original file had a lot of style/scripts.

with open(path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(new_lines))
