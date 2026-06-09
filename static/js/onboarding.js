/**
 * Sistema de Onboarding (Tutorial Interativo) - GRS Hub
 * Utiliza a biblioteca driver.js
 */

document.addEventListener('DOMContentLoaded', function () {
    // Só inicia se o usuário estiver logado e NÃO tiver visto o tutorial ainda
    if (typeof userHasSeenTutorial !== 'undefined' && !userHasSeenTutorial && currentUserId !== 0) {
        initOnboardingPrompt();
    }
});

function initOnboardingPrompt() {
    Swal.fire({
        title: 'Bem-vindo ao GRS Hub!',
        text: 'Deseja fazer um tour rápido pelo sistema para conhecer as principais funções?',
        icon: 'info',
        showCancelButton: true,
        confirmButtonText: 'Sim, vamos lá!',
        cancelButtonText: 'Agora não',
        reverseButtons: true,
        confirmButtonColor: '#3b82f6',
    }).then((result) => {
        if (result.isConfirmed) {
            startOnboardingTour();
        } else {
            // Se o usuário recusar, marcamos como visto para não incomodar mais
            markTutorialAsSeen();
        }
    });
}

function startOnboardingTour() {
    const driver = window.driver.js.driver;

    const tourSteps = getStepsByDepartment(userDepartmentName);

    const driverObj = driver({
        showProgress: true,
        nextBtnText: 'Próximo —›',
        prevBtnText: '‹— Anterior',
        doneBtnText: 'Finalizar',
        allowClose: true, // Permite pular/fechar a qualquer momento
        overlayColor: 'rgba(0, 0, 0, 0.75)',
        onDeselected: (element, step, { config, state }) => {
            // Se o usuário fechar o tutorial antes de terminar
            if (state.activeIndex === undefined) {
                // Tutorial cancelado ou finalizado
            }
        },
        onDestroyed: () => {
            // Sempre marcar como visto ao terminar ou fechar
            markTutorialAsSeen();
        },
        steps: tourSteps
    });

    driverObj.drive();
}

/**
 * Define os passos do tutorial com base no departamento do usuário
 */
function getStepsByDepartment(dept) {
    const baseSteps = [
        {
            element: '#sidebar',
            popover: {
                title: 'Menu Lateral',
                description: 'Este é o seu centro de navegação. Aqui você acessa todas as ferramentas do GRS Hub.',
                position: 'right'
            }
        },
        {
            element: '.sidebar-header',
            popover: {
                title: 'Logotipo e Recolhimento',
                description: 'Você pode clicar na seta para recolher o menu e ganhar mais espaço na tela.',
                position: 'right'
            }
        }
    ];

    let deptSteps = [];

    if (dept === 'Reclame Aqui') {
        deptSteps = [
            {
                element: 'a[href*="dashboard"]',
                popover: {
                    title: 'Dashboard Reclame Aqui',
                    description: 'Acompanhe em tempo real os indicadores de desempenho, metas e volume de reclamações.',
                    position: 'right'
                }
            },
            {
                element: 'a[href*="complaint_list"]',
                popover: {
                    title: 'Gestão de Reclamações',
                    description: 'Aqui você visualiza, edita e cria novas reclamações vindas do Reclame Aqui.',
                    position: 'right'
                }
            },
            {
                element: 'a[href*="reports"]',
                popover: {
                    title: 'Relatórios de CS',
                    description: 'Gere relatórios detalhados para análise de tendências e performance da equipe.',
                    position: 'right'
                }
            }
        ];
    } else if (dept === 'NRS Suporte') {
        deptSteps = [
            {
                element: 'a[href*="escala"]',
                popover: {
                    title: 'Escala de Plantão',
                    description: 'Visualize quem está de plantão e gerencie os horários da equipe NRS.',
                    position: 'right'
                }
            },
            {
                element: 'a[href*="quadro"]',
                popover: {
                    title: 'Quadro Kanban',
                    description: 'Organize suas tarefas diárias arrastando os cartões entre as colunas.',
                    position: 'right'
                }
            },
            {
                element: 'a[href*="verificacao-lojas"]',
                popover: {
                    title: 'Verificação de Lojas',
                    description: 'Realize auditorias e acompanhe o status técnico das unidades.',
                    position: 'right'
                }
            },
            {
                element: 'a[href*="desempenho"]',
                popover: {
                    title: 'Métricas de Desempenho',
                    description: 'Acompanhe seus KPIs e o ranking de produtividade do suporte.',
                    position: 'right'
                }
            }
        ];
    } else {
        // Geral / Admin
        deptSteps = [
            {
                element: 'a[href*="user_list"]',
                popover: {
                    title: 'Gestão de Usuários',
                    description: 'Como administrador, você pode gerenciar todos os usuários e permissões do sistema.',
                    position: 'right'
                }
            }
        ];
    }

    const finalSteps = [
        {
            element: '.sidebar-user',
            popover: {
                title: 'Seu Perfil',
                description: 'Aqui você acessa suas configurações e pode sair do sistema com segurança.',
                position: 'top'
            }
        },
        {
            element: '#chatWidgetBubble',
            popover: {
                title: 'Chat Interno',
                description: 'Fale com qualquer colega do sistema em tempo real por aqui!',
                position: 'left'
            }
        }
    ];

    // Combinar os passos, filtrando apenas os elementos que existem na página atual
    return [...baseSteps, ...deptSteps, ...finalSteps].filter(step => {
        if (typeof step.element === 'string') {
            return document.querySelector(step.element) !== null;
        }
        return true;
    });
}

/**
 * Envia uma requisição para o servidor marcando o tutorial como visto
 */
function markTutorialAsSeen() {
    fetch('/api/user/complete-tutorial/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        }
    }).then(response => {
        if (response.ok) {
            console.log('Tutorial marcado como visto.');
        }
    }).catch(error => {
        console.error('Erro ao marcar tutorial como visto:', error);
    });
}

/**
 * Helper para pegar CSRF Token
 */
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
