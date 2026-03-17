import re
import os

path = 'templates/core/desempenho.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add DataLabels plugin script
# I'll add it before the script tag
if 'chartjs-plugin-datalabels' not in content:
    content = content.replace('<script>', '<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0"></script>\n<script>')

# 2. Register the plugin
if 'Chart.register(ChartDataLabels)' not in content:
    content = content.replace('let tmeChart, npsChart, chatsChart;', 'let tmeChart, npsChart, chatsChart;\n    Chart.register(ChartDataLabels);')

# 3. Update TME Chart options
# - Remove Y-axis
# - Add datalabels config
tme_old = """                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function (value) {
                                return secondsToHms(value);
                            }
                        }
                    }
                }"""
tme_new = """                scales: {
                    y: {
                        display: false,
                        beginAtZero: true
                    }
                },
                plugins: {
                    legend: { display: false },
                    datalabels: {
                        align: 'top',
                        anchor: 'end',
                        color: '#f59e0b',
                        font: { weight: 'bold', size: 11 },
                        formatter: (value) => secondsToHms(value)
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                return 'TME: ' + secondsToHms(context.raw);
                            }
                        }
                    }
                }"""
# Using regex to replace to be safer with whitespace
content = re.sub(r'scales:\s*{\s*y:\s*{\s*beginAtZero:\s*true,\s*ticks:\s*{\s*callback:\s*function\s*\(value\)\s*{\s*return\s*secondsToHms\(value\);\s*}\s*}\s*}\s*}', 
                 'scales: { y: { display: false, beginAtZero: true } }', content)

# Update the plugins block for TME
content = content.replace("""                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                return 'TME: ' + secondsToHms(context.raw);
                            }
                        }
                    }
                },""", """                plugins: {
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
                            label: function (context) {
                                return 'TME: ' + secondsToHms(context.raw);
                            }
                        }
                    }
                },""")

# 4. Update NPS Chart options
nps_old = """                scales: {
                    y: { beginAtZero: true, max: 5 }
                }"""
nps_new = """                scales: {
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
                }"""
content = content.replace(nps_old, nps_new)

# 5. Update Chats Chart options
chats_old = """                scales: {
                    y: { beginAtZero: true }
                }"""
chats_new = """                scales: {
                    y: { display: false, beginAtZero: true }
                },
                plugins: {
                    legend: { display: false },
                    datalabels: {
                        align: 'top',
                        anchor: 'end',
                        color: '#7c3aed',
                        font: { weight: 'bold', size: 11 }
                    }
                }"""
content = content.replace(chats_old, chats_new)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Graficos personalizados com sucesso!")
Header
