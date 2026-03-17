import re
import os

path = 'templates/core/desempenho.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

new_render_charts = """    function renderCharts() {
        const labels = kpisData.map(k => k.label);
        const tmeValues = kpisData.map(k => k.tme);
        const npsValues = kpisData.map(k => k.nps);
        const chatsValues = kpisData.map(k => k.chats);

        const commonOptions = {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { display: false, beginAtZero: true }
            }
        };

        // TME Chart
        const tmeCtx = document.getElementById('tmeChart').getContext('2d');
        tmeChart = new Chart(tmeCtx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'TME',
                    data: tmeValues,
                    borderColor: '#f59e0b',
                    backgroundColor: 'rgba(245, 158, 11, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                ...commonOptions,
                plugins: {
                    legend: { display: false },
                    datalabels: {
                        align: 'top',
                        anchor: 'end',
                        color: '#b45309',
                        font: { weight: 'bold', size: 11 },
                        formatter: (value) => secondsToHms(value)
                    },
                    tooltip: {
                        callbacks: {
                            label: (context) => 'TME: ' + secondsToHms(context.raw)
                        }
                    }
                }
            }
        });

        // NPS Chart
        const npsCtx = document.getElementById('npsChart').getContext('2d');
        npsChart = new Chart(npsCtx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'NPS',
                    data: npsValues,
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                ...commonOptions,
                scales: {
                    y: { display: false, beginAtZero: true, max: 5.5 }
                },
                plugins: {
                    legend: { display: false },
                    datalabels: {
                        align: 'top',
                        anchor: 'end',
                        color: '#059669',
                        font: { weight: 'bold', size: 11 },
                        formatter: (value) => value ? value.toFixed(2) : ''
                    }
                }
            }
        });

        // Chats Chart
        const chatsCtx = document.getElementById('chatsChart').getContext('2d');
        chatsChart = new Chart(chatsCtx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Chats',
                    data: chatsValues,
                    borderColor: '#8b5cf6',
                    backgroundColor: 'rgba(139, 92, 246, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                ...commonOptions,
                plugins: {
                    legend: { display: false },
                    datalabels: {
                        align: 'top',
                        anchor: 'end',
                        color: '#7c3aed',
                        font: { weight: 'bold', size: 11 }
                    }
                }
            }
        });
    }"""

# Replace the entire renderCharts function
# I'll use a regex that matches from 'function renderCharts()' to the next function or end of script
content = re.sub(r'function renderCharts\(\) {.*?function renderTable\(\)', new_render_charts + '\n\n    function renderTable()', content, flags=re.DOTALL)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Funcao renderCharts reconstruida com sucesso!")
Header
