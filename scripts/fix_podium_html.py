import re

# Read the file
with open('templates/core/desempenho.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the itemsHtml section in renderPodiumCard with stepsHtml
old_pattern = r'''        let itemsHtml = '';
        topList\.forEach\(\(item, index\) => \{
            const positionClass = positionClasses\[index\] \|\| '';
            const medal = medals\[index\] \|\| `\$\{index \+ 1\}º`;
            
            let valueDisplay = '';
            if \(metricType === 'tme'\) \{
                valueDisplay = secondsToHms\(item\.value\);
            \} else if \(metricType === 'nps'\) \{
                valueDisplay = item\.value\.toFixed\(2\);
            \} else \{
                valueDisplay = item\.value;
            \}

            itemsHtml \+= `
                <div class="podium-item">
                    <div class="podium-position \$\{positionClass\}">
                        \$\{medal\}
                    </div>
                    <div class="podium-info">
                        <div class="podium-name">\$\{item\.analista_nome\}</div>
                        <div class="podium-value">\$\{valueDisplay\}</div>
                    </div>
                </div>
            `;
        \}\);

        return `
            <div class="podium-card">
                <div class="podium-card-header">
                    <i class="bi \$\{iconClass\}" style="color: \$\{iconColor\};"></i>
                    <h4>\$\{title\}</h4>
                </div>
                \$\{itemsHtml\}
            </div>
        `;'''

new_code = '''        let stepsHtml = '';
        topList.forEach((item, index) => {
            const positionClass = positionClasses[index] || '';
            const medal = medals[index] || `${index + 1}º`;
            
            let valueDisplay = '';
            if (metricType === 'tme') {
                valueDisplay = secondsToHms(item.value);
            } else if (metricType === 'nps') {
                valueDisplay = item.value.toFixed(2);
            } else {
                valueDisplay = item.value;
            }

            stepsHtml += `
                <div class="podium-step ${positionClass}">
                    <div class="step-platform">
                        <div class="step-badge">
                            ${medal}
                        </div>
                        <div class="step-name">${item.analista_nome}</div>
                        <div class="step-value">${valueDisplay}</div>
                    </div>
                </div>
            `;
        });

        return `
            <div class="podium-card">
                <div class="podium-card-header">
                    <i class="bi ${iconClass}" style="color: ${iconColor};"></i>
                    <h4>${title}</h4>
                </div>
                <div class="podium-steps">
                    ${stepsHtml}
                </div>
            </div>
        `;'''

# Use regex to find and replace
content = re.sub(old_pattern, new_code, content, flags=re.DOTALL)

# Write back
with open('templates/core/desempenho.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Podium HTML structure fixed successfully!")
