import re

# Read the file
with open('templates/core/desempenho.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the renderPodiumCard function
old_function = r'''    function renderPodiumCard\(title, topList, metricType, iconClass, iconColor\) \{[\s\S]*?\n        \};\n    \}'''

new_function = '''    function renderPodiumCard(title, topList, metricType, iconClass, iconColor) {
        if (!topList || topList.length === 0) {
            return `
                <div class="podium-card">
                    <div class="podium-card-header">
                        <i class="bi ${iconClass}" style="color: ${iconColor};"></i>
                        <h4>${title}</h4>
                    </div>
                    <div class="podium-empty">
                        Sem dados disponíveis
                    </div>
                </div>
            `;
        }

        const positionClasses = ['first', 'second', 'third'];
        const medals = ['🥇', '🥈', '🥉'];

        let stepsHtml = '';
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
        `;
    }

    // Confetti celebration function
    function celebrateWithConfetti() {
        const duration = 3 * 1000;
        const animationEnd = Date.now() + duration;
        const defaults = { startVelocity: 30, spread: 360, ticks: 60, zIndex: 9999 };

        function randomInRange(min, max) {
            return Math.random() * (max - min) + min;
        }

        const interval = setInterval(function() {
            const timeLeft = animationEnd - Date.now();

            if (timeLeft <= 0) {
                return clearInterval(interval);
            }

            const particleCount = 50 * (timeLeft / duration);
            
            // Fire from left and right sides
            confetti(Object.assign({}, defaults, {
                particleCount,
                origin: { x: randomInRange(0.1, 0.3), y: Math.random() - 0.2 }
            }));
            confetti(Object.assign({}, defaults, {
                particleCount,
                origin: { x: randomInRange(0.7, 0.9), y: Math.random() - 0.2 }
            }));
        }, 250);
    }'''

content = re.sub(old_function, new_function, content, flags=re.MULTILINE)

# Add confetti call to renderPodium function
content = re.sub(
    r'(container\.innerHTML = html;)\n(\s+)\}',
    r'\1\n\2    \n\2    // Trigger confetti animation\n\2    celebrateWithConfetti();\n\2}',
    content
)

# Write back
with open('templates/core/desempenho.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Podium redesigned successfully with confetti!")
