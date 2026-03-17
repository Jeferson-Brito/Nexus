import re

# Read the file
with open('templates/core/desempenho.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the location before </script> and add the confetti function if it doesn't exist
if 'function celebrateWithConfetti' not in content:
    # Add the confetti function before the closing script tag
    confetti_function = '''
    // Confetti celebration function
    function celebrateWithConfetti() {
        if (typeof confetti === 'undefined') {
            console.error('Confetti library not loaded');
            return;
        }
        
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
    }
'''
    
    # Insert before the closing script tag
    content = content.replace('</script>\n{% endblock %}', confetti_function + '\n</script>\n{% endblock %}')
    
    # Write back
    with open('templates/core/desempenho.html', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Confetti function added successfully!")
else:
    print("Confetti function already exists!")
