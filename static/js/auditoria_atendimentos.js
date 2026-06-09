// ========================================
// AUDITORIA DE ATENDIMENTOS - JAVASCRIPT
// ========================================

function formatDate(dateString) {
    if (!dateString) return '';
    const parts = dateString.split('-');
    if (parts.length === 3) {
        return `${parts[2]}/${parts[1]}/${parts[0]}`;
    }
    return dateString;
}

document.addEventListener('DOMContentLoaded', function () {
    // Estado global
    const state = {
        analistas: [],
        currentPage: 1,
        totalPages: 1,
        filters: {},
        config: null,
        editingId: null,
        currentAnalystId: null,
        currentAnalystFilter: '',
        charts: {
            evolucao: null,
            radar: null,
            geral: null
        }
    };

    // Inicialização
    init();

    function init() {
        console.log('Auditoria Atendimentos JS Loaded - v1.5 - Bugs Fixed');
        setupDefaultDates();
        loadAnalistas();
        loadConfig();
        setupEventListeners();
        setupCriteriosHandlers();

        // Verificar se estamos na visão de analista
        if (document.querySelector('.card-dashboard')) {
            initAnalystView();
        } else if (document.getElementById('chartEvolucaoGeral')) {
            loadExecutiveDashboard();
        }

        // Carregar auditorias na aba ativa ao iniciar (se for a aba lista)
        const listaTabPane = document.getElementById('lista');
        if (listaTabPane && listaTabPane.classList.contains('active')) {
            loadAuditorias(1);
        }
    }

    // ========================================
    // EVENT LISTENERS
    // ========================================

    function setupEventListeners() {
        // Form de cadastro
        const formAuditoria = document.getElementById('formAuditoria');
        if (formAuditoria) {
            formAuditoria.addEventListener('submit', handleSubmitAuditoria);
        }

        // Botão limpar
        const btnLimpar = document.getElementById('btnLimpar');
        if (btnLimpar) {
            btnLimpar.addEventListener('click', resetForm);
        }

        // Upload de imagens individuais por critério
        const criterios = [
            'apresentacao', 'historico', 'entendimento',
            'informacao', 'acordo_espera', 'respeito',
            'portugues', 'finalizacao', 'procedimento'
        ];

        criterios.forEach(criterio => {
            const inputImagem = document.getElementById(`imagem_erro_${criterio}`);
            if (inputImagem) {
                inputImagem.addEventListener('change', (e) => handleImageUpload(e, criterio));
            }
        });

        // Filtros
        const btnFiltros = document.getElementById('btnFiltros');
        if (btnFiltros) {
            btnFiltros.addEventListener('click', toggleFiltros);
        }

        // Filtro Analista
        const btnFiltrarAnalista = document.getElementById('btnFiltrarAnalista');
        if (btnFiltrarAnalista) {
            btnFiltrarAnalista.addEventListener('click', () => {
                // Atualiza os cards de desempenho baseados na data selecionada
                initAnalystView();
                // Atualiza a lista de auditorias
                loadAnalystAudits(state.currentAnalystFilter || '');
            });
        }

        const btnIAAnalista = document.getElementById('btnGerarInsightAnalista');
        if (btnIAAnalista) {
            btnIAAnalista.addEventListener('click', handleGerarInsightAnalyst);
            checkPersistedFeedback();
        }

        const btnAplicarFiltros = document.getElementById('btnAplicarFiltros');
        if (btnAplicarFiltros) {
            btnAplicarFiltros.addEventListener('click', applyFilters);
        }


        // Tabs - carregar dados ao trocar
        const tabs = document.querySelectorAll('#auditoriaTabs button[data-bs-toggle="tab"]');
        tabs.forEach(tab => {
            tab.addEventListener('shown.bs.tab', function (e) {
                const target = e.target.dataset.bsTarget;
                handleTabChange(target);
            });
        });

        // Botão de filtro do modal de analista
        const btnFiltrarModal = document.getElementById('btnFiltrarModalAnalista');
        if (btnFiltrarModal) {
            btnFiltrarModal.addEventListener('click', () => {
                if (state.currentAnalystId) {
                    // Sincronizar com os inputs ocultos para compatibilidade
                    const modalInicio = document.getElementById('modal-data-inicio');
                    const modalFim = document.getElementById('modal-data-fim');
                    if (modalInicio) document.getElementById('filtro_analista_data_inicio').value = modalInicio.value;
                    if (modalFim) document.getElementById('filtro_analista_data_fim').value = modalFim.value;
                    loadModalAnalystAudits(state.currentAnalystId);
                }
            });
        }

        // Verificação de ID de Conversa Duplicado
        const inputIdConversa = document.getElementById('id_conversa');
        if (inputIdConversa) {
            inputIdConversa.addEventListener('blur', function () {
                const id = this.value.trim();
                if (!id) return;

                fetch(`/api/auditoria/check-id/?id=${encodeURIComponent(id)}`)
                    .then(r => r.json())
                    .then(data => {
                        if (data.exists) {
                            Swal.fire({
                                icon: 'warning',
                                title: 'Atenção: ID Duplicado',
                                text: `A conversa "${id}" já possui uma auditoria registrada no sistema.`,
                                confirmButtonText: 'Entendi'
                            });
                        }
                    });
            });
        }

        // Botão Gerar Insight IA
        const btnIA = document.getElementById('btnGerarInsightIA');
        if (btnIA) {
            btnIA.addEventListener('click', handleGerarInsightIA);
        }

        // Botão Copiar Relatório IA
        const btnCopiar = document.getElementById('btnCopiarRelatorio');
        if (btnCopiar) {
            btnCopiar.addEventListener('click', function() {
                const content = document.getElementById('ia-markdown-content').innerText;
                navigator.clipboard.writeText(content).then(() => {
                    this.innerHTML = '<i class="bi bi-check me-1"></i>Copiado!';
                    setTimeout(() => {
                        this.innerHTML = '<i class="bi bi-clipboard me-1"></i>Copiar';
                    }, 2000);
                });
            });
        }
    }

    function setupDefaultDates() {
        const hoje = new Date();
        const primeiroDia = new Date(hoje.getFullYear(), hoje.getMonth(), 1);
        const ultimoDia = new Date(hoje.getFullYear(), hoje.getMonth() + 1, 0);

        const isoPrimeiro = primeiroDia.toISOString().split('T')[0];
        const isoUltimo = ultimoDia.toISOString().split('T')[0];

        const inputsInicio = ['filtro_data_inicio', 'filtro_analista_data_inicio'];
        const inputsFim = ['filtro_data_fim', 'filtro_analista_data_fim'];

        inputsInicio.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.value = isoPrimeiro;
        });

        inputsFim.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.value = isoUltimo;
        });
    }

    function setupCriteriosHandlers() {
        // Handlers para os switches de critérios com melhorias visuais
        const switches = document.querySelectorAll('.criterio-switch');
        switches.forEach(sw => {
            sw.addEventListener('change', function () {
                const erroField = this.dataset.erro;
                const erroContainer = document.getElementById(`${erroField}_container`);
                const criterioItem = this.closest('.criterio-item');

                if (!this.checked) {
                    // Mostrar campo de erro com animação
                    erroContainer.style.display = 'block';
                    document.getElementById(erroField).required = true;

                    // Atualizar classes do card
                    criterioItem.classList.remove('checked');
                    criterioItem.classList.add('unchecked');
                } else {
                    // Ocultar campo de erro
                    erroContainer.style.display = 'none';
                    document.getElementById(erroField).required = false;
                    document.getElementById(erroField).value = '';

                    // Atualizar classes do card
                    criterioItem.classList.remove('unchecked');
                    criterioItem.classList.add('checked');
                }

                // Atualizar preview e contador em tempo real
                updatePreview();
                updateCriteriosCount();
            });
        });
    }

    // Função para atualizar contador de critérios
    function updateCriteriosCount() {
        const switches = document.querySelectorAll('.criterio-switch');
        let aprovados = 0;

        switches.forEach(sw => {
            if (sw.checked) aprovados++;
        });

        const counter = document.getElementById('criterios-count');
        if (counter) {
            counter.textContent = aprovados;

            // Animar mudança
            counter.parentElement.style.transform = 'scale(1.2)';
            setTimeout(() => {
                counter.parentElement.style.transform = 'scale(1)';
            }, 200);
        }
    }

    // ========================================
    // VISAO DO ANALISTA
    // ========================================

    function initAnalystView() {
        var elInicio = document.getElementById('filtro_analista_data_inicio');
        var elFim    = document.getElementById('filtro_analista_data_fim');
        var dataInicio = elInicio ? elInicio.value : '';
        var dataFim    = elFim    ? elFim.value    : '';

        var params = new URLSearchParams({ page: 1, per_page: 200 });
        if (dataInicio) params.set('data_inicio', dataInicio);
        if (dataFim)    params.set('data_fim', dataFim);

        fetch('/api/auditoria/dashboard/?' + params.toString(), { credentials: 'include' })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (!data.success) return;

                function setEl(id, val) {
                    var el = document.getElementById(id);
                    if (el) el.textContent = val;
                }
                var dist = data.distribuicao || {};
                setEl('analyst-total-geral',   data.total_all_time  != null ? data.total_all_time  : 0);
                setEl('analyst-total-periodo', data.total_auditorias != null ? data.total_auditorias : 0);
                setEl('analyst-media-geral',   parseFloat(data.nota_media_geral || 0).toFixed(1) + '/10');
                setEl('count-excelente',       dist.excelente      || 0);
                setEl('count-bom',             dist.bom            || 0);
                setEl('count-regular',         dist.regular        || 0);
                setEl('count-insatisfatorio',  dist.insatisfatorio || 0);

                loadAnalystAudits('');
            })
            .catch(function(err) { console.error('[Analyst View] Erro:', err); });
    }

    function loadAnalystAudits(classificacaoFiltro) {
        var elInicio = document.getElementById('filtro_analista_data_inicio');
        var elFim    = document.getElementById('filtro_analista_data_fim');
        var dataInicio = elInicio ? elInicio.value : '';
        var dataFim    = elFim    ? elFim.value    : '';

        var params = new URLSearchParams({ page: 1, per_page: 100 });
        if (dataInicio)         params.set('data_inicio',   dataInicio);
        if (dataFim)            params.set('data_fim',      dataFim);
        if (classificacaoFiltro) params.set('classificacao', classificacaoFiltro);

        var tbody    = document.getElementById('lista-auditorias-analista');
        var container = document.getElementById('analyst-list-container');

        if (!tbody) return;
        if (container) container.style.display = 'block';

        tbody.innerHTML = '<tr><td colspan="7" class="text-center py-4">'
            + '<div class="spinner-border text-primary" role="status"></div></td></tr>';

        fetch('/api/auditoria/list/?' + params.toString(), { credentials: 'include' })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (!data.success || !data.auditorias || data.auditorias.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="7" class="text-center py-4 text-muted">'
                        + 'Nenhuma auditoria encontrada no periodo.</td></tr>';
                    return;
                }
                tbody.innerHTML = '';
                data.auditorias.forEach(function(aud) {
                    var badgeClass = 'badge-' + aud.classificacao;
                    var dataFmt   = formatDate(aud.data_atendimento);
                    var cienteHtml = '';
                    if (aud.requer_acao) {
                        cienteHtml = aud.ciente_analista
                            ? '<span class="badge bg-success-subtle text-success border border-success'
                              + ' border-opacity-25 ms-1"><i class="bi bi-person-check-fill me-1"></i>Ciente</span>'
                            : '<span class="badge bg-secondary-subtle text-secondary border ms-1">'
                              + '<i class="bi bi-hourglass-split me-1"></i>Pendente</span>';
                    }

                    var tr = document.createElement('tr');
                    tr.style.cursor = 'pointer';
                    (function(audId) {
                        tr.onclick = function(e) { viewDetails(audId, e); };
                    }(aud.id));

                    tr.innerHTML =
                        '<td class="ps-4">' + dataFmt + '</td>'
                        + '<td><code class="text-muted">' + aud.id_conversa + '</code></td>'
                        + '<td><span class="badge bg-secondary">' + aud.tipo_atendimento + '</span></td>'
                        + '<td class="fw-semibold">' + aud.pontuacao + '/9</td>'
                        + '<td class="fw-bold">'     + Number(aud.nota).toFixed(1) + '</td>'
                        + '<td><span class="badge ' + badgeClass + '">' + aud.classificacao_display + '</span>'
                        + cienteHtml + '</td>'
                        + '<td class="text-center pe-4">'
                        + '<button class="btn btn-sm btn-outline-primary" title="Ver detalhes">'
                        + '<i class="bi bi-eye"></i></button></td>';

                    var trDetails = document.createElement('tr');
                    trDetails.id        = 'details-' + aud.id;
                    trDetails.style.display = 'none';
                    trDetails.className = 'details-row';
                    trDetails.innerHTML = '<td colspan="7" class="p-0 border-0">'
                        + '<div class="details-container p-4 bg-light border-bottom shadow-inner"></div></td>';

                    tbody.appendChild(tr);
                    tbody.appendChild(trDetails);
                });
            })
            .catch(function(err) {
                console.error('[Analyst Audits] Erro:', err);
                tbody.innerHTML = '<tr><td colspan="7" class="text-center text-danger py-4">'
                    + 'Erro ao carregar auditorias.</td></tr>';
            });
    }

    window.filterAnalystList = function(classificacao) {
        var labelMap = { excelente: 'Excelente', bom: 'Bom', regular: 'Regular', insatisfatorio: 'Insatisfatorio' };
        var label = document.getElementById('current-filter-label');
        if (label) label.textContent = labelMap[classificacao] || 'Todos';
        state.currentAnalystFilter = classificacao;
        loadAnalystAudits(classificacao);
    };

    function handleGerarInsightAnalyst() {
        var modal = document.getElementById('modalIAAnalista');
        if (!modal) {
            console.error('[IA Insight] Modal #modalIAAnalista nao encontrado.');
            return;
        }
        var bsModal   = new bootstrap.Modal(modal);
        var loadingEl = document.getElementById('ia-loading-analista');
        var resultEl  = document.getElementById('ia-result-analista');

        bsModal.show();
        if (loadingEl) loadingEl.style.display = 'block';
        if (resultEl)  { resultEl.style.display = 'none'; resultEl.innerHTML = ''; }

        var elInicio = document.getElementById('filtro_analista_data_inicio');
        var elFim    = document.getElementById('filtro_analista_data_fim');
        var dataInicio = elInicio ? elInicio.value : '';
        var dataFim    = elFim    ? elFim.value    : '';

        fetch('/api/auditoria/analista/self/ia-insight/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ data_inicio: dataInicio, data_fim: dataFim })
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (loadingEl) loadingEl.style.display = 'none';
            if (resultEl)  resultEl.style.display  = 'block';

            if (data.error) {
                resultEl.innerHTML = '<div class="alert alert-warning">'
                    + '<i class="bi bi-exclamation-triangle me-2"></i>' + data.error + '</div>';
                return;
            }

            var markdown = data.insight_markdown || '';
            if (typeof marked !== 'undefined') {
                resultEl.innerHTML = marked.parse(markdown);
            } else {
                var safe = markdown.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
                resultEl.innerHTML = '<pre style="white-space:pre-wrap;font-family:inherit;">' + safe + '</pre>';
            }

            try { sessionStorage.setItem('brisoft_ia_feedback_analista', markdown); } catch(e) {}
        })
        .catch(function(err) {
            console.error('[IA Insight] Erro:', err);
            if (loadingEl) loadingEl.style.display = 'none';
            if (resultEl) {
                resultEl.style.display = 'block';
                resultEl.innerHTML = '<div class="alert alert-danger">'
                    + '<i class="bi bi-wifi-off me-2"></i>'
                    + 'Erro de conexao ao gerar o feedback. Tente novamente.</div>';
            }
        });
    }

    function checkPersistedFeedback() {
        try {
            var persisted = sessionStorage.getItem('brisoft_ia_feedback_analista');
            var btn = document.getElementById('btnGerarInsightAnalista');
            if (persisted && btn) {
                btn.title = 'Gerar novo feedback (ultimo disponivel na sessao)';
            }
        } catch(e) {}
    }

        // ========================================
    // NAVEGAÇÃO ENTRE ABAS
    // ========================================

    function handleTabChange(target) {
        switch (target) {
            case '#lista':
                loadAuditorias(1);
                break;
            case '#lista-ia':
                window.loadAuditoriasIA(1);
                break;
            case '#ranking':
                loadRanking();
                break;
            case '#analistas':
                loadAnalistasView();
                break;
            case '#config':
                loadConfig();
                break;
        }
    }

    // ========================================
    // CARREGAR DADOS INICIAIS
    // ========================================

    function loadAnalistas() {
        return fetch('/api/auditoria/analistas/', {
            credentials: 'include'
        })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    state.analistas = data.analistas;
                    populateAnalistasSelect();
                } else {
                    console.error('API retornou success=false:', data);
                }
                return data;
            })
            .catch(error => {
                console.error('Erro ao carregar analistas:', error);
            });
    }

    function populateAnalistasSelect() {
        const selects = [
            document.getElementById('analista_auditado_id'),
            document.getElementById('filtro_analista')
        ];

        selects.forEach(select => {
            if (!select) return;

            // Limpar opções anteriores (exceto a primeira)
            while (select.options.length > 1) {
                select.remove(1);
            }

            // Atualizar texto da primeira opção se for o select de cadastro
            if (select.id === 'analista_auditado_id' && select.options.length > 0) {
                select.options[0].text = 'Selecione...';
            }

            state.analistas.forEach(analista => {
                const option = document.createElement('option');
                option.value = analista.id;
                option.textContent = analista.nome_completo;
                select.appendChild(option);
            });
        });
    }

    function loadConfig() {
        fetch('/api/auditoria/config/', {
            credentials: 'include'
        })
            .then(response => response.json())
            .then(data => {
                if (data.success && data.configuracao) {
                    state.config = data.configuracao;
                }
            })
            .catch(error => console.error('Erro ao carregar config:', error));
    }

    // ========================================
    // PREVIEW EM TEMPO REAL
    // ========================================

    function updatePreview() {
        // Contar critérios marcados
        const switches = document.querySelectorAll('.criterio-switch');
        let pontuacao = 0;

        switches.forEach(sw => {
            if (sw.checked) pontuacao++;
        });

        // Calcular nota (0-10)
        const nota = ((pontuacao / 9) * 10).toFixed(1);

        // Calcular percentual
        const percentual = ((pontuacao / 9) * 100).toFixed(0);

        // Determinar classificação e cores
        let classificacao = '';
        let icon = '';
        let gradientBg = '';
        let progressGradient = '';
        let boxShadow = '';

        if (pontuacao === 9) {
            classificacao = 'Excelente';
            icon = 'bi-check-circle-fill';
            gradientBg = 'linear-gradient(135deg, #10b981 0%, #34d399 100%)';
            progressGradient = 'linear-gradient(90deg, #10b981 0%, #34d399 100%)';
            boxShadow = '0 4px 15px rgba(16, 185, 129, 0.3), 0 1px 3px rgba(0,0,0,0.1)';
        } else if (pontuacao >= 7) {
            classificacao = 'Bom';
            icon = 'bi-hand-thumbs-up-fill';
            gradientBg = 'linear-gradient(135deg, #3b82f6 0%, #60a5fa 100%)';
            progressGradient = 'linear-gradient(90deg, #3b82f6 0%, #60a5fa 100%)';
            boxShadow = '0 4px 15px rgba(59, 130, 246, 0.3), 0 1px 3px rgba(0,0,0,0.1)';
        } else if (pontuacao >= 5) {
            classificacao = 'Regular';
            icon = 'bi-exclamation-circle-fill';
            gradientBg = 'linear-gradient(135deg, #f59e0b 0%, #fbbf24 100%)';
            progressGradient = 'linear-gradient(90deg, #f59e0b 0%, #fbbf24 100%)';
            boxShadow = '0 4px 15px rgba(245, 158, 11, 0.3), 0 1px 3px rgba(0,0,0,0.1)';
        } else {
            classificacao = 'Insatisfatório';
            icon = 'bi-x-circle-fill';
            gradientBg = 'linear-gradient(135deg, #ef4444 0%, #f87171 100%)';
            progressGradient = 'linear-gradient(90deg, #ef4444 0%, #f87171 100%)';
            boxShadow = '0 4px 15px rgba(239, 68, 68, 0.3), 0 1px 3px rgba(0,0,0,0.1)';
        }

        // Atualizar percentual
        const percentualEl = document.getElementById('percentual-display');
        if (percentualEl) {
            percentualEl.textContent = percentual;
            percentualEl.style.transform = 'scale(1.1)';
            setTimeout(() => percentualEl.style.transform = 'scale(1)', 200);
        }

        // Atualizar nota
        const notaEl = document.getElementById('nota-display');
        if (notaEl) {
            notaEl.textContent = nota.replace('.', ',');
            notaEl.style.transform = 'scale(1.1)';
            setTimeout(() => notaEl.style.transform = 'scale(1)', 200);
        }

        // Atualizar barra de progresso
        const progressBar = document.getElementById('progresso-bar');
        if (progressBar) {
            progressBar.style.width = percentual + '%';
            progressBar.style.background = progressGradient;
            progressBar.style.boxShadow = boxShadow.replace('0.3', '0.4');
        }

        // Atualizar badge de classificação
        const badge = document.getElementById('classificacao-badge');
        if (badge) {
            badge.innerHTML = `<i class="bi ${icon}"></i><span>${classificacao}</span>`;
            badge.style.background = gradientBg;
            badge.style.boxShadow = boxShadow;
            badge.style.transform = 'scale(1.1)';
            setTimeout(() => badge.style.transform = 'scale(1)', 200);
        }

        // Efeito especial para nota máxima
        if (pontuacao === 9 && window.lastPontuacao !== 9) {
            showCelebration();
        }

        window.lastPontuacao = pontuacao;
    }

    // Função para celebração (nota máxima)
    function showCelebration() {
        const preview = document.getElementById('resultado-preview');
        if (preview) {
            preview.style.animation = 'none';
            setTimeout(() => {
                preview.style.animation = 'pulse 0.5s ease';
            }, 10);
        }
    }

    // ========================================
    // SUBMIT AUDITORIA
    // ========================================

    function handleSubmitAuditoria(e) {
        e.preventDefault();

        const formData = new FormData(e.target);
        const data = {};

        // Coletar dados básicos
        formData.forEach((value, key) => {
            data[key] = value;
        });

        // Tratar explicitamente os checkboxes (switches) para garantir booleanos
        document.querySelectorAll('.criterio-switch').forEach(switchInput => {
            data[switchInput.name] = switchInput.checked;
        });

        // Validar descrições de erro
        const switches = document.querySelectorAll('.criterio-switch:not(:checked)');
        let valid = true;

        switches.forEach(sw => {
            const erroField = sw.dataset.erro;
            const erroValue = document.getElementById(erroField).value.trim();
            if (!erroValue) {
                valid = false;
                document.getElementById(erroField).classList.add('is-invalid');
            }
        });

        if (!valid) {
            Swal.fire({
                icon: 'error',
                title: 'Erro de Validação',
                text: 'Por favor, descreva os erros para todos os critérios não atendidos.',
            });
            return;
        }

        // Enviar para API
        // Enviar para API
        const url = state.editingId ? `/api/auditoria/${state.editingId}/update/` : '/api/auditoria/create/';

        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(data)
        })
            .then(response => response.json())
            .then(result => {
                if (result.success) {
                    Swal.fire({
                        icon: 'success',
                        title: 'Sucesso!',
                        text: state.editingId ? 'Auditoria atualizada com sucesso!' : `Auditoria salva com nota ${result.auditoria.nota.toFixed(1)} - ${result.auditoria.classificacao}`,
                        confirmButtonText: 'OK'
                    }).then(() => {
                        resetForm();
                        // Ir para aba de lista
                        const listaTab = document.querySelector('#lista-tab');
                        if (listaTab) {
                            const tab = new bootstrap.Tab(listaTab);
                            tab.show();
                        }
                    });
                } else {
                    Swal.fire({
                        icon: 'error',
                        title: 'Erro',
                        text: result.error || 'Erro ao salvar auditoria',
                    });
                }
            })
            .catch(error => {
                console.error('Erro:', error);
                Swal.fire({
                    icon: 'error',
                    title: 'Erro',
                    text: 'Erro ao salvar auditoria. Tente novamente.',
                });
            });
    }

    function resetForm() {
        const form = document.getElementById('formAuditoria');
        form.reset();

        // Resetar estado de edição
        state.editingId = null;
        window.lastPontuacao = null;
        const btnSalvar = document.querySelector('#formAuditoria button[type="submit"]');
        if (btnSalvar) btnSalvar.innerHTML = '<i class="bi bi-check-circle me-2"></i>Salvar Auditoria';
        const titulo = document.querySelector('#cadastrar .card-header h5');
        if (titulo) titulo.innerHTML = '<i class="bi bi-plus-circle me-2"></i>Nova Auditoria de Atendimento';

        // Resetar switches para checked e classes dos cards
        const switches = document.querySelectorAll('.criterio-switch');
        switches.forEach(sw => {
            sw.checked = true;
            const erroField = sw.dataset.erro;
            const erroContainer = document.getElementById(`${erroField}_container`);
            const criterioItem = sw.closest('.criterio-item');

            // Resetar classes visuais
            if (criterioItem) {
                criterioItem.classList.remove('unchecked');
                criterioItem.classList.add('checked');
            }

            erroContainer.style.display = 'none';
            document.getElementById(erroField).value = '';
            document.getElementById(erroField).required = false;
        });

        // Resetar data para hoje
        const dataInput = document.getElementById('data_atendimento');
        if (dataInput) {
            dataInput.value = new Date().toISOString().split('T')[0];
        }

        const linkInput = document.getElementById('link_conversa');
        if (linkInput) linkInput.value = '';

        updatePreview();
        updateCriteriosCount();
    }

    // ========================================
    // LISTAGEM DE AUDITORIAS
    // ========================================

    function loadAuditorias(page = 1) {
        const tbody = document.getElementById('lista-auditorias');
        tbody.innerHTML = '<tr><td colspan="8" class="text-center py-4"><div class="spinner-border text-primary"></div></td></tr>';

        const params = new URLSearchParams({
            page: page,
            per_page: 20,
            ...state.filters
        });

        fetch(`/api/auditoria/list/?${params}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    renderAuditorias(data.auditorias);
                    renderPagination(data.page, data.total_pages);
                    state.currentPage = data.page;
                    state.totalPages = data.total_pages;
                }
            })
            .catch(error => {
                console.error('Erro:', error);
                tbody.innerHTML = '<tr><td colspan="8" class="text-center text-danger py-4">Erro ao carregar auditorias</td></tr>';
            });
    }

    function renderAuditorias(auditorias) {
        const tbody = document.getElementById('lista-auditorias');

        if (auditorias.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="text-center py-4 text-muted">Nenhuma auditoria encontrada</td></tr>';
            return;
        }

        tbody.innerHTML = '';

        auditorias.forEach(aud => {
            const tr = document.createElement('tr');
            // Make row clickable
            tr.style.cursor = 'pointer';
            tr.onclick = (e) => viewDetails(aud.id, e);

            if (aud.requer_acao) {
                tr.classList.add('row-alert');
            }

            const badgeClass = `badge-${aud.classificacao}`;
            const dataFormatada = formatDate(aud.data_atendimento);

            tr.innerHTML = `
                <td>${dataFormatada}</td>
                <td>${aud.id_conversa}</td>
                <td><span class="badge bg-secondary">${aud.tipo_atendimento}</span></td>
                <td>${aud.analista_auditado.nome_completo}</td>
                <td>${aud.pontuacao}/9</td>
                <td class="fw-bold">${aud.nota.toFixed(1)}</td>
                <td>
                    <span class="badge ${badgeClass}">${aud.classificacao_display}</span>
                    ${aud.gerado_por_ia ? `<span class="badge ms-1" style="background:linear-gradient(135deg,#6366f1,#8b5cf6);font-size:0.65rem;" title="Auditoria gerada automaticamente pelo Brisoft IA Auditor"><i class="bi bi-robot me-1"></i>IA</span>` : ''}
                    ${aud.requer_acao ? `
                        <i class="bi bi-exclamation-triangle icon-alert ms-2" title="Requer Ação"></i>
                        ${aud.feedback_data
                        ? `<br><small class="text-success"><i class="bi bi-check-circle me-1"></i>Discutido em ${formatDate(aud.feedback_data)}</small>`
                        : `<br><small class="text-danger">Não discutido</small>`
                    }
                        ${aud.ciente_analista
                        ? `<br><small class="text-primary"><i class="bi bi-person-check-fill me-1"></i>Analista Ciente (${formatDate(aud.data_ciente.split('T')[0])})</small>`
                        : `<br><small class="text-muted">Aguardando ciente do analista</small>`
                    }
                    ` : ''}
                </td>
                <td>
                    <button class="btn btn-sm btn-outline-primary" title="Ver detalhes">
                        <i class="bi bi-eye"></i>
                    </button>
                    ${aud.can_edit ? `<button class="btn btn-sm btn-outline-warning ms-1" onclick="editAudit('${aud.id}')" title="Editar">
                        <i class="bi bi-pencil"></i>
                    </button>` : ''}
                    ${aud.can_delete ? `<button class="btn btn-sm btn-outline-danger ms-1" onclick="deleteAudit('${aud.id}')" title="Excluir">
                        <i class="bi bi-trash"></i>
                    </button>` : ''}
                </td>
            `;

            tbody.appendChild(tr);

            // Hidden Details Row (Colspan 8 because of the extra 'Analista' column in main list)
            const trDetails = document.createElement('tr');
            trDetails.id = `details-${aud.id}`;
            trDetails.style.display = 'none';
            trDetails.className = 'details-row';
            trDetails.innerHTML = `
                <td colspan="8" class="p-0 border-0">
                    <div class="details-container p-4 bg-light border-bottom shadow-inner" style="box-shadow: inset 0 2px 4px rgba(0,0,0,0.05);"></div>
                </td>
            `;
            tbody.appendChild(trDetails);
        });
    }

    function renderPagination(currentPage, totalPages) {
        const container = document.getElementById('paginacao');
        if (totalPages <= 1) {
            container.innerHTML = '';
            return;
        }

        let html = '<nav><ul class="pagination pagination-sm mb-0">';

        // Botão anterior
        html += `<li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="loadAuditorias(${currentPage - 1}); return false;">Anterior</a>
        </li>`;

        // Páginas
        for (let i = 1; i <= totalPages; i++) {
            if (i === 1 || i === totalPages || (i >= currentPage - 2 && i <= currentPage + 2)) {
                html += `<li class="page-item ${i === currentPage ? 'active' : ''}">
                    <a class="page-link" href="#" onclick="loadAuditorias(${i}); return false;">${i}</a>
                </li>`;
            } else if (i === currentPage - 3 || i === currentPage + 3) {
                html += '<li class="page-item disabled"><span class="page-link">...</span></li>';
            }
        }

        // Botão próximo
        html += `<li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="loadAuditorias(${currentPage + 1}); return false;">Próximo</a>
        </li>`;

        html += '</ul></nav>';

        container.innerHTML = html;
    }

    // Tornar função global para uso inline
    window.loadAuditorias = loadAuditorias;

    // ========================================
    // DETALHES DA AUDITORIA (ACCORDION)
    // ========================================

    window.viewDetails = function (id, event) {
        // Ignorar cliques em botões de ação (editar/excluir) exceto o próprio botão de ver detalhes
        if (event && event.target) {
            const target = event.target.closest('button');
            if (target && target.getAttribute('onclick') && !target.getAttribute('onclick').includes('viewDetails')) {
                return;
            }
        }

        const detailsRow = document.getElementById(`details-${id}`);
        if (!detailsRow) return;

        // Find the toggle button in the main row to update its icon
        // The main row is the previous sibling of the details row
        const mainRow = detailsRow.previousElementSibling;
        const btn = mainRow ? mainRow.querySelector('button[onclick*="viewDetails"]') : null;
        const icon = btn ? btn.querySelector('i') : null;

        const isHidden = detailsRow.style.display === 'none';

        if (isHidden) {
            detailsRow.style.display = 'table-row';
            if (icon) {
                icon.classList.remove('bi-eye');
                icon.classList.add('bi-eye-slash');
            }

            // Highlight active row
            if (mainRow) mainRow.classList.add('table-active');

            const container = detailsRow.querySelector('.details-container');
            // Only fetch if empty (first time opening)
            if (container.children.length === 0) {
                container.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-primary"></div></div>';

                fetch(`/api/auditoria/${id}/`, { credentials: 'include' })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            renderDetailsContent(data.auditoria, container, id);
                        } else {
                            container.innerHTML = '<div class="alert alert-danger m-3">Erro ao carregar detalhes.</div>';
                        }
                    })
                    .catch(error => {
                        console.error(error);
                        container.innerHTML = '<div class="alert alert-danger m-3">Erro de conexão.</div>';
                    });
            }
        } else {
            detailsRow.style.display = 'none';
            if (icon) {
                icon.classList.remove('bi-eye-slash');
                icon.classList.add('bi-eye');
            }

            // Remove highlight
            if (mainRow) mainRow.classList.remove('table-active');
        }
    };

    function renderDetailsContent(aud, container, id) {
        const dataFormatada = formatDate(aud.data_atendimento);
        const badgeClass = `badge-${aud.classificacao}`;

        let criteriosHTML = '';
        const criterios = [
            { nome: '1. Apresentou-se corretamente?', value: aud.criterios.apresentou_corretamente, erro: aud.criterios.erro_apresentacao, imagem: aud.criterios.imagem_erro_apresentacao },
            { nome: '2. Analisou o histórico?', value: aud.criterios.analisou_historico, erro: aud.criterios.erro_historico, imagem: aud.criterios.imagem_erro_historico },
            { nome: '3. Entendeu a solicitação?', value: aud.criterios.entendeu_solicitacao, erro: aud.criterios.erro_entendimento, imagem: aud.criterios.imagem_erro_entendimento },
            { nome: '4. Informação clara?', value: aud.criterios.informacao_clara, erro: aud.criterios.erro_informacao, imagem: aud.criterios.imagem_erro_informacao },
            { nome: '5. Acordo de espera correto?', value: aud.criterios.acordo_espera, erro: aud.criterios.erro_acordo_espera, imagem: aud.criterios.imagem_erro_acordo_espera },
            { nome: '6. Atendimento respeitoso?', value: aud.criterios.atendimento_respeitoso, erro: aud.criterios.erro_respeito, imagem: aud.criterios.imagem_erro_respeito },
            { nome: '7. Português correto?', value: aud.criterios.portugues_correto, erro: aud.criterios.erro_portugues, imagem: aud.criterios.imagem_erro_portugues },
            { nome: '8. Finalização correta?', value: aud.criterios.finalizacao_correta, erro: aud.criterios.erro_finalizacao, imagem: aud.criterios.imagem_erro_finalizacao },
            { nome: '9. Procedimento correto?', value: aud.criterios.procedimento_correto, erro: aud.criterios.erro_procedimento, imagem: aud.criterios.imagem_erro_procedimento },
        ];

        criterios.forEach(crit => {
            const statusClass = crit.value ? 'success' : 'error';
            const statusIcon = crit.value ? '<i class="bi bi-check-circle text-success"></i>' : '<i class="bi bi-x-circle text-danger"></i>';
            const bgClass = crit.value ? 'bg-success-subtle' : 'bg-danger-subtle';
            const borderClass = crit.value ? 'border-success' : 'border-danger';

            // Prepare error message
            let errorHTML = '';
            if (!crit.value && crit.erro) {
                errorHTML = `<p class="mb-0 mt-2 text-danger p-2 bg-white rounded shadow-sm border border-danger-subtle"><i class="bi bi-exclamation-circle me-1"></i><small><strong>Erro:</strong> ${crit.erro}</small></p>`;
            }

            // Prepare image display
            let imageHTML = '';
            if (!crit.value && crit.imagem) {
                imageHTML = `<div class="mt-2"><a href="${crit.imagem}" target="_blank" title="Abrir imagem em nova guia"><img src="${crit.imagem}" alt="Evidência" class="img-fluid rounded evidence-image shadow-sm" style="max-width: 200px; max-height: 150px; border: 2px solid #dc3545; cursor: pointer;"></a></div>`;
            }

            criteriosHTML += `
                <div class="criterio-detail mb-2 p-3 rounded ${bgClass} border ${borderClass} border-opacity-25">
                    <div class="d-flex align-items-start">
                        <div class="me-3 fs-5">${statusIcon}</div>
                        <div class="flex-grow-1">
                            <strong class="text-dark">${crit.nome}</strong>
                            ${errorHTML}
                            ${imageHTML}
                        </div>
                    </div>
                </div>
            `;
        });

        container.innerHTML = `
            <div class="row mb-4">
                <div class="col-md-5">
                    <h6 class="text-uppercase text-muted small fw-bold mb-3">Resumo da Auditoria</h6>
                    <div class="card border-0 bg-white shadow-sm mb-3">
                        <div class="card-body">
                            <div class="row g-2">
                                <div class="col-6">
                                    <small class="text-muted d-block">Data do Atendimento</small>
                                    <span class="fw-semibold">${dataFormatada}</span>
                                </div>
                                <div class="col-6">
                                    <small class="text-muted d-block">ID Conversa</small>
                                    <div class="d-flex align-items-center">
                                        <span class="fw-semibold text-primary">#${aud.id_conversa}</span>
                                        ${aud.link_conversa ? `<a href="${aud.link_conversa}" target="_blank" class="ms-3 btn btn-sm btn-primary d-inline-flex align-items-center" style="font-size: 0.75rem; border-radius: 20px; padding: 2px 10px; box-shadow: 0 2px 4px rgba(13, 110, 253, 0.25);" title="Abrir conversa"><i class="bi bi-box-arrow-up-right me-1"></i>Ver Conversa</a>` : ''}
                                    </div>
                                </div>
                                <div class="col-6">
                                    <small class="text-muted d-block">Tipo</small>
                                    <span class="badge bg-light text-dark border">${aud.tipo_atendimento}</span>
                                </div>
                                <div class="col-6">
                                    <small class="text-muted d-block">Data Auditoria</small>
                                    <span>${new Date(aud.created_at).toLocaleDateString('pt-BR')}</span>
                                </div>
                                <div class="col-12 mt-2 pt-2 border-top">
                                    <small class="text-muted d-block">Analista</small>
                                    <span class="fw-semibold">${aud.analista_auditado.nome_completo}</span>
                                </div>
                                ${aud.auditor ? `
                                <div class="col-12">
                                    <small class="text-muted d-block">Auditado por</small>
                                    <span>${aud.auditor.nome_completo}</span>
                                </div>` : ''}
                            </div>
                        </div>
                    </div>
                    
                    <div class="row text-center g-2">
                        <div class="col-4">
                            <div class="p-2 bg-white rounded shadow-sm border">
                                <small class="text-muted d-block text-uppercase" style="font-size:0.65rem">Pontuação</small>
                                <span class="h5 mb-0 fw-bold">${aud.pontuacao}/9</span>
                            </div>
                        </div>
                        <div class="col-4">
                            <div class="p-2 bg-white rounded shadow-sm border">
                                <small class="text-muted d-block text-uppercase" style="font-size:0.65rem">Nota</small>
                                <span class="h5 mb-0 fw-bold text-primary">${aud.nota.toFixed(1)}/10</span>
                            </div>
                        </div>
                        <div class="col-4">
                            <div class="p-2 bg-white rounded shadow-sm border">
                                <small class="text-muted d-block text-uppercase" style="font-size:0.65rem">Classificação</small>
                                <span class="badge ${badgeClass} mt-1">${aud.classificacao_display}</span>
                            </div>
                        </div>
                    </div>
                    
                    ${aud.requer_acao ? `
                    <div class="alert ${aud.feedback_data ? 'alert-success' : 'alert-warning'} mt-3 shadow-sm">
                        <div class="d-flex align-items-start">
                            <i class="bi ${aud.feedback_data ? 'bi-check-circle-fill text-success' : 'bi-exclamation-triangle text-warning'} me-2 mt-1"></i>
                            <div class="flex-grow-1">
                                <strong>${aud.feedback_data ? 'Conversa Registrada' : 'Atenção: Requer Discussão'}</strong>
                                ${aud.feedback_data
                    ? `<p class="mb-0 mt-1 small">Discutido por <strong>${aud.feedback_gestor || 'Gestor'}</strong> em <strong>${formatDate(aud.feedback_data)}</strong></p>`
                    : `<p class="mb-0 mt-1 small">Esta auditoria ainda não foi discutida com o analista.</p>`
                }
                            </div>
                            ${aud.can_edit ? `
                            <button class="btn btn-sm ${aud.feedback_data ? 'btn-outline-success' : 'btn-warning'} ms-2" 
                                onclick="registrarFeedback('${aud.id}')" title="Registrar data da conversa">
                                <i class="bi bi-chat-dots"></i>
                            </button>` : ''}
                        </div>
                    </div>
                    
                    ${aud.requer_acao && !aud.can_edit && !aud.ciente_analista ? `
                    <div class="alert alert-info mt-2">
                        <div class="d-flex align-items-center justify-content-between">
                            <span><i class="bi bi-info-circle me-2"></i>Você deve dar o seu ciente sobre esta auditoria:</span>
                            <button class="btn btn-sm btn-primary" onclick="darCiente('${aud.id}')">
                                <i class="bi bi-check-square me-1"></i>Dar Ciente
                            </button>
                        </div>
                    </div>
                    ` : ''}
                    
                    ${aud.ciente_analista ? `
                    <div class="alert alert-light mt-2 border shadow-sm small py-2">
                        <i class="bi bi-info-circle text-primary me-2"></i>
                        Analista deu ciente em <strong>${new Date(aud.data_ciente).toLocaleString('pt-BR')}</strong>
                    </div>
                    ` : ''}
                    ` : ''}
                </div>
                
                <div class="col-md-7">
                    <h6 class="text-uppercase text-muted small fw-bold mb-3">Critérios Avaliados</h6>
                    <div class="criterios-list" style="max-height: 500px; overflow-y: auto; padding-right: 5px;">
                        ${criteriosHTML}
                    </div>
                </div>
            </div>
            
            <div class="d-flex justify-content-end pt-3 border-top">
                <button type="button" class="btn btn-sm btn-outline-secondary me-2" onclick="viewDetails('${aud.id}', event)">
                    <i class="bi bi-eye-slash me-1"></i>Fechar Detalhes
                </button>
                ${aud.can_edit ? `<button type="button" class="btn btn-sm btn-primary" onclick="editAudit('${aud.id}')"><i class="bi bi-pencil me-1"></i>Editar Auditoria</button>` : ''}
            </div>
        `;

        // Salvar referência da auditoria atual para edição
        state.currentAudit = aud;
    }

    window.editAudit = function (id) {
        // Garantir que temos o ID como string
        const auditId = String(id);

        // Se temos a auditoria em cache e é a mesma, usa ela
        if (state.currentAudit && String(state.currentAudit.id) === auditId) {
            populateAndShowEditForm(state.currentAudit);
        } else {
            // Se não, busca do servidor
            fetch(`/api/auditoria/${auditId}/`, { credentials: 'include' })
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        state.currentAudit = data.auditoria;
                        populateAndShowEditForm(data.auditoria);
                    } else {
                        Swal.fire('Erro', 'Não foi possível carregar os dados para edição.', 'error');
                    }
                })
                .catch(err => {
                    console.error(err);
                    Swal.fire('Erro', 'Erro de conexão ao buscar auditoria.', 'error');
                });
        }
    };

    function populateAndShowEditForm(aud) {

        // Fechar modal


        // Preencher formulário
        document.getElementById('data_atendimento').value = aud.data_atendimento.split('T')[0];
        document.getElementById('id_conversa').value = aud.id_conversa;
        const linkInput = document.getElementById('link_conversa');
        if (linkInput) linkInput.value = aud.link_conversa || '';
        document.getElementById('tipo_atendimento').value = aud.tipo_atendimento_key || aud.tipo_atendimento;

        document.getElementById('analista_auditado_id').value = aud.analista_auditado.id;

        // Criterios
        const criterios = aud.criterios;
        for (const [key, value] of Object.entries(criterios)) {
            // Pular campos de erro e imagens no loop principal de switches
            if (key.startsWith('erro_') || key.startsWith('imagem_')) continue;

            const switchInput = document.getElementById(key);
            if (switchInput) {
                switchInput.checked = !!value;
                // Disparar evento para mostrar/ocultar erro
                switchInput.dispatchEvent(new Event('change'));

                if (!value) {
                    const erroField = switchInput.dataset.erro;
                    const erroInput = document.getElementById(erroField);
                    if (erroInput) {
                        erroInput.value = criterios[erroField] || '';
                    }

                    // Se houver imagem de erro, preencher o link oculto
                    const imgKey = 'imagem_' + erroField;
                    const urlInput = document.getElementById(imgKey + '_url');
                    if (urlInput && criterios[imgKey]) {
                        urlInput.value = criterios[imgKey];
                    }
                }
            }
        }

        // Configurar estado de edição
        state.editingId = aud.id;
        const btnSalvar = document.querySelector('#formAuditoria button[type="submit"]');
        if (btnSalvar) btnSalvar.innerHTML = '<i class="bi bi-save me-2"></i>Atualizar Auditoria';
        const titulo = document.querySelector('#cadastrar h5');
        if (titulo) titulo.innerHTML = '<i class="bi bi-pencil me-2"></i>Editando Auditoria #' + aud.id;

        // Ir para aba de cadastro
        const cadastrarTabBtn = document.querySelector('#cadastrar-tab');
        if (cadastrarTabBtn) {
            if (typeof bootstrap !== 'undefined' && bootstrap.Tab) {
                const tab = new bootstrap.Tab(cadastrarTabBtn);
                tab.show();
            } else {
                // Fallback se bootstrap.Tab não estiver pronto
                cadastrarTabBtn.click();
            }
        }

        updatePreview();
    }

    window.deleteAudit = function (id) {
        Swal.fire({
            title: 'Tem certeza?',
            text: "Você não poderá reverter isso!",
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#d33',
            cancelButtonColor: '#3085d6',
            confirmButtonText: 'Sim, excluir!',
            cancelButtonText: 'Cancelar'
        }).then((result) => {
            if (result.isConfirmed) {
                fetch(`/api/auditoria/${id}/delete/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            Swal.fire(
                                'Excluído!',
                                'Auditoria foi excluída.',
                                'success'
                            ).then(() => {
                                // Remover linha visualmente se existir
                                const row = document.querySelector(`button[onclick="deleteAudit('${id}')"]`)?.closest('tr');
                                if (row) row.remove();

                                const modalEl = document.getElementById('modalDetalhes');
                                const modal = bootstrap.Modal.getInstance(modalEl);
                                if (modal) modal.hide();

                                // Recarregar lista apropriada
                                if (document.getElementById('lista-auditorias-analista')) {
                                    // Se estiver na visão de analista
                                    loadAnalystAudits(state.currentAnalystFilter || '');
                                } else {
                                    loadAuditorias(state.currentPage);
                                }
                            });
                        } else {
                            Swal.fire('Erro', data.error || 'Erro ao excluir', 'error');
                        }
                    })
                    .catch(error => {
                        console.error('Erro:', error);
                        Swal.fire('Erro', 'Erro ao excluir auditoria', 'error');
                    });
            }
        });
    };

    // ========================================
    // REGISTRAR FEEDBACK / CONVERSA
    // ========================================

    window.registrarFeedback = function (auditoriaId) {
        Swal.fire({
            title: 'Registrar Conversa',
            html: `
                <p class="text-muted mb-3">Informe a data em que você conversou com o analista sobre este alerta.</p>
                <input type="date" id="swal-feedback-date" class="form-control" 
                    value="${new Date().toISOString().split('T')[0]}" max="${new Date().toISOString().split('T')[0]}">
            `,
            icon: 'info',
            showCancelButton: true,
            confirmButtonText: '<i class="bi bi-check-circle me-1"></i>Salvar',
            cancelButtonText: 'Cancelar',
            confirmButtonColor: '#198754',
            preConfirm: () => {
                const date = document.getElementById('swal-feedback-date').value;
                if (!date) {
                    Swal.showValidationMessage('Por favor, informe a data da conversa.');
                    return false;
                }
                return date;
            }
        }).then((result) => {
            if (result.isConfirmed) {
                fetch(`/api/auditoria/${auditoriaId}/feedback/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: JSON.stringify({ feedback_data: result.value })
                })
                    .then(r => r.json())
                    .then(data => {
                        if (data.success) {
                            Swal.fire({
                                icon: 'success',
                                title: 'Conversa Registrada!',
                                text: `Data: ${formatDate(data.feedback_data)} - por ${data.feedback_gestor}`,
                                timer: 2000,
                                showConfirmButton: false
                            }).then(() => {
                                // Reload the details panel
                                const container = document.querySelector(`#details-${auditoriaId} .details-container`);
                                if (container) {
                                    container.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-primary"></div></div>';
                                    fetch(`/api/auditoria/${auditoriaId}/`, { credentials: 'include' })
                                        .then(r => r.json())
                                        .then(d => {
                                            if (d.success) renderDetailsContent(d.auditoria, container, auditoriaId);
                                        });
                                }
                                loadAuditorias(state.currentPage);
                            });
                        } else {
                            Swal.fire('Erro', data.error || 'Erro ao registrar feedback', 'error');
                        }
                    })
                    .catch(err => Swal.fire('Erro', 'Erro de conexão', 'error'));
            }
        });
    };

    // ========================================
    // RANKING DE ANALISTAS
    // ========================================

    function loadRanking() {
        const container = document.getElementById('ranking-container');
        container.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-primary"></div></div>';

        fetch('/api/auditoria/ranking/')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    renderRanking(data.ranking);
                }
            })
            .catch(error => {
                console.error('Erro:', error);
                container.innerHTML = '<div class="alert alert-danger">Erro ao carregar ranking</div>';
            });
    }

    function renderRanking(ranking) {
        const container = document.getElementById('ranking-container');

        if (ranking.length === 0) {
            container.innerHTML = '<div class="alert alert-info">Nenhuma auditoria registrada ainda</div>';
            return;
        }

        let html = '';
        
        // Pódio para o Top 3
        const top3 = ranking.slice(0, 3);
        if (top3.length > 0) {
            html += '<div class="podium-steps">';
            
            // Reordenar para exibir visualmente como Segundo, Primeiro, Terceiro
            const displayOrder = [];
            if (top3[1]) displayOrder.push({ ...top3[1], podiumClass: 'second', icon: '🥈' });
            if (top3[0]) displayOrder.push({ ...top3[0], podiumClass: 'first', icon: '🏆' });
            if (top3[2]) displayOrder.push({ ...top3[2], podiumClass: 'third', icon: '🥉' });
            
            displayOrder.forEach(item => {
                html += `
                    <div class="podium-step ${item.podiumClass}">
                        <div class="step-platform">
                            <div class="step-badge">${item.icon}</div>
                            <div class="step-name">${item.analista_nome}</div>
                            <div class="step-value">${item.nota_media.toFixed(1)}</div>
                        </div>
                    </div>
                `;
            });
            html += '</div>';
        }

        // Restante do ranking
        const rest = ranking.slice(3);
        if (rest.length > 0) {
            html += '<div class="mt-4"><h6 class="text-muted text-uppercase mb-3 ps-2" style="font-size: 0.8rem; letter-spacing: 1px;">Outros Analistas</h6>';
            rest.forEach(item => {
                html += `
                    <div class="ranking-item">
                        <div class="row align-items-center w-100 m-0">
                            <div class="col-auto ps-0">
                                <div class="posicao-badge">${item.posicao}º</div>
                            </div>
                            <div class="col">
                                <h6 class="mb-1 fw-bold">${item.analista_nome}</h6>
                                <p class="text-muted mb-0" style="font-size: 0.8rem;">
                                    ${item.total_auditorias} auditorias
                                </p>
                            </div>
                            <div class="col-auto text-end">
                                <h6 class="mb-1 text-muted" style="font-size: 0.75rem;">Nota Média</h6>
                                <h5 class="mb-0 text-primary fw-bold">${item.nota_media.toFixed(1)}</h5>
                            </div>
                        </div>
                    </div>
                `;
            });
            html += '</div>';
        }

        container.innerHTML = html;
    }

    // ========================================
    // VISÃO POR ANALISTA
    // ========================================

    function loadAnalistasView() {
        const container = document.getElementById('analistas-container');
        container.innerHTML = '<div class="col-12 text-center py-5"><div class="spinner-border text-primary"></div><p class="text-muted mt-2">Carregando performance dos analistas...</p></div>';

        // Garantir que a lista de analistas existe
        const getAnalistasPromise = state.analistas.length > 0 
            ? Promise.resolve({ success: true, analistas: state.analistas }) 
            : loadAnalistas();

        getAnalistasPromise.then(() => {
            if (state.analistas.length === 0) {
                container.innerHTML = '<div class="col-12 text-center py-5"><i class="bi bi-people display-4 text-muted"></i><p class="text-muted mt-2">Nenhum analista disponível para auditoria.</p></div>';
                return;
            }

            // Carregar estatísticas de todos os analistas em paralelo
            Promise.all(
                state.analistas.map(analista =>
                    fetch(`/api/auditoria/analista/${analista.id}/`)
                        .then(r => r.json())
                )
            )
                .then(results => {
                    renderAnalistasCards(results);
                })
                .catch(error => {
                    console.error('Erro:', error);
                    container.innerHTML = '<div class="col-12"><div class="alert alert-danger">Erro ao carregar dados dos analistas</div></div>';
                });
        });
    }

    function renderAnalistasCards(results) {
        const container = document.getElementById('analistas-container');
        
        if (!results || results.length === 0) {
            container.innerHTML = '<div class="col-12"><div class="empty-state py-5 text-center"><i class="bi bi-people display-1 text-muted"></i><p class="mt-3 text-muted">Nenhum analista encontrado ou erro ao carregar.</p></div></div>';
            return;
        }

        let html = '';

        results.forEach(data => {
            if (!data.success) return;

            const stats = data;
            const alertClass = stats.tem_alertas ? 'has-alert' : '';
            
            // Gerar iniciais do nome
            const nomePartes = stats.analista.nome_completo.trim().split(' ');
            const iniciais = nomePartes.length >= 2 
                ? (nomePartes[0][0] + nomePartes[nomePartes.length - 1][0]).toUpperCase()
                : nomePartes[0].substring(0, 2).toUpperCase();

            // Classe de cor da nota
            const nota = stats.nota_media;
            let notaClass = 'nota-bom';
            if (nota >= 9.5) notaClass = 'nota-excelente';
            else if (nota >= 7) notaClass = 'nota-bom';
            else if (nota >= 5) notaClass = 'nota-regular';
            else if (nota > 0) notaClass = 'nota-insatisf';

            html += `
                <div class="col-md-6 col-lg-4 mb-3">
                    <div class="analista-card ${alertClass}" onclick="showAnalystAudits('${stats.analista.id}', '${stats.analista.nome_completo.replace(/'/g, "\\'")}')">
                        <div class="analista-card-header">
                            <div class="analista-card-avatar">${iniciais}</div>
                            <div class="flex-grow-1 min-width-0">
                                <p class="analista-card-name">${stats.analista.nome_completo}</p>
                                ${stats.tem_alertas ? '<small class="text-danger fw-semibold"><i class="bi bi-exclamation-triangle me-1"></i>Alerta</small>' : '<small class="text-success fw-semibold"><i class="bi bi-check-circle me-1"></i>Sem alertas</small>'}
                            </div>
                            <i class="bi bi-chevron-right text-muted"></i>
                        </div>
                        <div class="analista-card-body">
                            <div class="analista-card-stats">
                                <div class="analista-stat-box">
                                    <span class="stat-num">${stats.total_auditorias}</span>
                                    <span class="stat-lbl">Auditorias</span>
                                </div>
                                <div class="analista-stat-box">
                                    <span class="stat-num ${stats.total_auditorias > 0 ? notaClass : ''}">${stats.total_auditorias > 0 ? stats.nota_media.toFixed(1) : '—'}</span>
                                    <span class="stat-lbl">Nota Média</span>
                                </div>
                                <div class="analista-stat-box">
                                    <span class="stat-num" style="font-size:1rem;">${stats.ultima_auditoria ? formatDate(stats.ultima_auditoria.data.split('T')[0]).substring(0, 5) : '—'}</span>
                                    <span class="stat-lbl">Última</span>
                                </div>
                            </div>
                            ${stats.total_auditorias > 0 ? `
                                <div class="analista-dist-bar">
                                    <div class="dist-label">Distribuição</div>
                                    <div class="analista-dist-pills">
                                        ${stats.distribuicao.excelente > 0 ? `<span class="pill excelente"><i class="bi bi-star-fill"></i>${stats.distribuicao.excelente} Excelente</span>` : ''}
                                        ${stats.distribuicao.bom > 0 ? `<span class="pill bom"><i class="bi bi-hand-thumbs-up-fill"></i>${stats.distribuicao.bom} Bom</span>` : ''}
                                        ${stats.distribuicao.regular > 0 ? `<span class="pill regular"><i class="bi bi-exclamation-circle"></i>${stats.distribuicao.regular} Regular</span>` : ''}
                                        ${stats.distribuicao.insatisfatorio > 0 ? `<span class="pill insatisf"><i class="bi bi-x-circle"></i>${stats.distribuicao.insatisfatorio} Insatisf.</span>` : ''}
                                    </div>
                                </div>
                            ` : '<p class="text-muted text-center mt-2 mb-0 small"><i class="bi bi-inbox me-1"></i>Sem auditorias no período</p>'}
                        </div>
                    </div>
                </div>
            `;
        });

        if (html === '') {
            html = '<div class="col-12"><div class="alert alert-info">Nenhum analista encontrado</div></div>';
        }

        container.innerHTML = html;
    }

    // ========================================
    // MOSTRAR AUDITORIAS DO ANALISTA
    // ========================================

    window.showAnalystAudits = function (analistaId, analistaNome) {
        state.currentAnalystId = analistaId;
        
        // Atualizar título do modal
        document.getElementById('analista-name').textContent = analistaNome;

        // Inicializar datas do modal com o mês atual
        const hoje = new Date();
        const primeiroDia = new Date(hoje.getFullYear(), hoje.getMonth(), 1);
        const ultimoDia = new Date(hoje.getFullYear(), hoje.getMonth() + 1, 0);
        const modalDataInicio = document.getElementById('modal-data-inicio');
        const modalDataFim = document.getElementById('modal-data-fim');
        if (modalDataInicio && !modalDataInicio.value) {
            modalDataInicio.value = primeiroDia.toISOString().split('T')[0];
        }
        if (modalDataFim && !modalDataFim.value) {
            modalDataFim.value = ultimoDia.toISOString().split('T')[0];
        }
        // Sincronizar com inputs ocultos
        if (modalDataInicio) document.getElementById('filtro_analista_data_inicio').value = modalDataInicio.value;
        if (modalDataFim) document.getElementById('filtro_analista_data_fim').value = modalDataFim.value;

        // Resetar Modal UI
        document.getElementById('loading-analista-audits').style.display = 'block';
        document.getElementById('analista-modal-content').style.display = 'none';
        document.getElementById('empty-state-analista').style.display = 'none';
        
        // Resetar IA UI
        document.getElementById('ia-empty-state').style.display = 'block';
        document.getElementById('ia-loading').style.display = 'none';
        document.getElementById('ia-result').style.display = 'none';

        // Voltar para a aba de histórico
        const historyTab = document.getElementById('modal-historico-tab');
        if (historyTab) {
            const bsTab = bootstrap.Tab.getOrCreateInstance(historyTab);
            bsTab.show();
        }

        // Abrir modal
        const modalEl = document.getElementById('modalAnalistaAudits');
        const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
        modal.show();

        // Buscar auditorias do analista
        loadModalAnalystAudits(analistaId);
    };

    // Função separada para carregar auditorias do modal (pode ser reutilizada ao filtrar)
    function loadModalAnalystAudits(analistaId) {
        document.getElementById('loading-analista-audits').style.display = 'block';
        document.getElementById('analista-modal-content').style.display = 'none';
        document.getElementById('empty-state-analista').style.display = 'none';

        const dataInicio = document.getElementById('modal-data-inicio')?.value 
            || document.getElementById('filtro_analista_data_inicio')?.value || '';
        const dataFim = document.getElementById('modal-data-fim')?.value 
            || document.getElementById('filtro_analista_data_fim')?.value || '';

        const params = new URLSearchParams({
            analista_id: analistaId,
            per_page: 50
        });
        if (dataInicio) params.append('data_inicio', dataInicio);
        if (dataFim) params.append('data_fim', dataFim);

        fetch(`/api/auditoria/list/?${params}`, { credentials: 'include' })
            .then(response => response.json())
            .then(data => {
                document.getElementById('loading-analista-audits').style.display = 'none';
                document.getElementById('analista-modal-content').style.display = 'block';

                if (data.success && data.auditorias.length > 0) {
                    renderAnalystAuditsList(data.auditorias);
                    renderAnalystCharts(data.auditorias);
                } else {
                    document.getElementById('lista-auditorias-analista-modal').innerHTML = '';
                    document.getElementById('empty-state-analista').style.display = 'block';
                }
            })
            .catch(error => {
                console.error('Erro ao carregar auditorias:', error);
                document.getElementById('loading-analista-audits').style.display = 'none';
                document.getElementById('analista-modal-content').style.display = 'block';
                document.getElementById('lista-auditorias-analista-modal').innerHTML = 
                    '<tr><td colspan="6" class="text-center text-danger py-4"><i class="bi bi-exclamation-triangle me-2"></i>Erro ao carregar auditorias.</td></tr>';
            });
    }

    function renderAnalystAuditsList(auditorias) {
        const tbody = document.getElementById('lista-auditorias-analista-modal');
        let html = '';

        auditorias.forEach(aud => {
            const badgeClass = `badge-${aud.classificacao}`;
            html += `
                <tr onclick="loadAuditoriaDetail('${aud.id}', event)" style="cursor:pointer">
                    <td>${formatDate(aud.data_atendimento)}</td>
                    <td><code class="text-primary">${aud.id_conversa}</code></td>
                    <td><span class="badge bg-light text-dark border">${aud.tipo_atendimento}</span></td>
                    <td><span class="fw-bold">${aud.nota.toFixed(1)}</span></td>
                    <td><span class="badge ${badgeClass}">${aud.classificacao_display}</span></td>
                    <td>
                        <button class="btn btn-sm btn-outline-primary">
                            <i class="bi bi-eye"></i>
                        </button>
                    </td>
                </tr>
                <tr id="modal-details-${aud.id}" class="details-row" style="display:none">
                    <td colspan="6" class="p-0 border-0">
                        <div class="details-container p-3 bg-light border-bottom shadow-inner"></div>
                    </td>
                </tr>
            `;
        });

        tbody.innerHTML = html;
    }

    window.loadAuditoriaDetail = function (id, event) {
        if (event) event.stopPropagation();
        
        const detailsRow = document.getElementById(`modal-details-${id}`);
        if (!detailsRow) return;

        const mainRow = detailsRow.previousElementSibling;
        const icon = mainRow ? mainRow.querySelector('i.bi-eye, i.bi-eye-slash') : null;

        const isHidden = detailsRow.style.display === 'none';

        if (isHidden) {
            detailsRow.style.display = 'table-row';
            if (icon) {
                icon.classList.remove('bi-eye');
                icon.classList.add('bi-eye-slash');
            }
            
            const container = detailsRow.querySelector('.details-container');
            if (container.children.length === 0) {
                container.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-primary"></div></div>';

                fetch(`/api/auditoria/${id}/`, { credentials: 'include' })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            renderDetailsContent(data.auditoria, container, id);
                        } else {
                            container.innerHTML = '<div class="alert alert-danger m-3">Erro ao carregar detalhes.</div>';
                        }
                    })
                    .catch(error => {
                        console.error(error);
                        container.innerHTML = '<div class="alert alert-danger m-3">Erro de conexão.</div>';
                    });
            }
        } else {
            detailsRow.style.display = 'none';
            if (icon) {
                icon.classList.remove('bi-eye-slash');
                icon.classList.add('bi-eye');
            }
        }
    };

    function renderAnalystCharts(auditorias) {
        // Preparar dados para Gráfico de Evolução (Linha)
        const labels = auditorias.map(a => formatDate(a.data_atendimento)).reverse();
        const notas = auditorias.map(a => a.nota).reverse();

        // Destruir gráficos anteriores se existirem
        if (state.charts.evolucao) state.charts.evolucao.destroy();
        if (state.charts.radar) state.charts.radar.destroy();

        const ctxLine = document.getElementById('chartEvolucaoAnalista').getContext('2d');
        state.charts.evolucao = new Chart(ctxLine, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Nota da Auditoria',
                    data: notas,
                    borderColor: '#4f46e5',
                    backgroundColor: 'rgba(79, 70, 229, 0.05)',
                    fill: true,
                    tension: 0.4,
                    borderWidth: 2,
                    pointRadius: 3,
                    pointBackgroundColor: '#4f46e5'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { 
                        min: 0, 
                        max: 10, 
                        ticks: { stepSize: 2 },
                        grid: { color: '#f1f5f9' }
                    },
                    x: { grid: { display: false } }
                }
            }
        });

        // Preparar dados para Gráfico Radar (Pilares)
        const ctxRadar = document.getElementById('chartRadarAnalista').getContext('2d');
        state.charts.radar = new Chart(ctxRadar, {
            type: 'radar',
            data: {
                labels: ['Apresentação', 'Histórico', 'Entendimento', 'Informação', 'Acordo Espera', 'Respeito', 'Português', 'Finalização', 'Procedimento'],
                datasets: [{
                    label: 'Performance por Pilar',
                    data: [100, 100, 100, 100, 100, 100, 100, 100, 100], // Mock data, ideally calculated from audits
                    backgroundColor: 'rgba(79, 70, 229, 0.2)',
                    borderColor: '#4f46e5',
                    pointBackgroundColor: '#4f46e5',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    r: { 
                        min: 0, 
                        max: 100, 
                        ticks: { display: false, stepSize: 20 },
                        grid: { color: '#e2e8f0' },
                        angleLines: { color: '#e2e8f0' }
                    }
                }
            }
        });
    }

    function handleGerarInsightIA() {
        const btn = document.getElementById('btnGerarInsightIA');
        const emptyState = document.getElementById('ia-empty-state');
        const loading = document.getElementById('ia-loading');
        const result = document.getElementById('ia-result');
        const content = document.getElementById('ia-markdown-content');

        emptyState.style.display = 'none';
        loading.style.display = 'block';

        const dataInicio = document.getElementById('modal-data-inicio')?.value || document.getElementById('filtro_analista_data_inicio').value;
        const dataFim = document.getElementById('modal-data-fim')?.value || document.getElementById('filtro_analista_data_fim').value;

        fetch(`/api/auditoria/analista/${state.currentAnalystId}/ia-insight/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ data_inicio: dataInicio, data_fim: dataFim })
        })
        .then(response => response.json())
        .then(data => {
            loading.style.display = 'none';
            if (data.success) {
                result.style.display = 'block';
                content.innerHTML = data.insight_markdown
                    .replace(/^### (.*$)/gim, '<h4 class="mt-4 mb-3 fw-bold text-dark">$1</h4>')
                    .replace(/\*\*(.*)\*\*/g, '<strong>$1</strong>')
                    .replace(/\n/g, '<br>');
            } else {
                emptyState.style.display = 'block';
                Swal.fire('Erro', data.error || 'Não foi possível gerar a avaliação.', 'error');
            }
        })
        .catch(err => {
            loading.style.display = 'none';
            emptyState.style.display = 'block';
            console.error(err);
        });
    }



    // ========================================
    // FILTROS
    // ========================================

    function toggleFiltros() {
        const panel = document.getElementById('filtrosPanel');
        const collapse = new bootstrap.Collapse(panel, {
            toggle: true
        });
    }

    function applyFilters() {
        const filters = {};

        const analistaId = document.getElementById('filtro_analista').value;
        if (analistaId) filters.analista_id = analistaId;

        const dataInicio = document.getElementById('filtro_data_inicio').value;
        if (dataInicio) filters.data_inicio = dataInicio;

        const dataFim = document.getElementById('filtro_data_fim').value;
        if (dataFim) filters.data_fim = dataFim;

        const tipo = document.getElementById('filtro_tipo').value;
        if (tipo) filters.tipo = tipo;

        const classificacao = document.getElementById('filtro_classificacao').value;
        if (classificacao) filters.classificacao = classificacao;

        const apenasAlertas = document.getElementById('filtro_apenas_alertas').checked;
        if (apenasAlertas) filters.apenas_alertas = 'true';

        state.filters = filters;
        loadAuditorias(1);
    }

    // ========================================
    // CONFIGURAÇÕES
    // ========================================

    function handleSubmitConfig(e) {
        e.preventDefault();

        const percentual = parseFloat(document.getElementById('percentual_minimo').value);

        fetch('/api/auditoria/config/update/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                percentual_minimo_aceitavel: percentual
            })
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    Swal.fire({
                        icon: 'success',
                        title: 'Configuração Salva!',
                        text: `Percentual mínimo atualizado para ${percentual}%`,
                        timer: 2000
                    });
                    state.config = data.configuracao;
                } else {
                    Swal.fire({
                        icon: 'error',
                        title: 'Erro',
                        text: data.error || 'Erro ao salvar configuração'
                    });
                }
            })
            .catch(error => {
                console.error('Erro:', error);
                Swal.fire({
                    icon: 'error',
                    title: 'Erro',
                    text: 'Erro ao salvar configuração'
                });
            });
    }

    // ========================================
    // MUDANÇA DE TABS
    // ========================================

    function handleTabChange(target) {
        switch (target) {
            case '#lista':
                loadAuditorias(1);
                break;
            case '#lista-ia':
                window.loadAuditoriasIA(1);
                break;
            case '#ranking':
                loadRanking();
                break;
            case '#analistas':
                loadAnalistasView();
                break;
            case '#config':
                loadConfig();
                break;
        }
    }

    // ========================================
    // UTILITÁRIOS
    // ========================================

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

    // ========================================
    // VISÃO DO ANALISTA (NOVO)
    // ========================================

    function loadExecutiveDashboard() {
        fetch('/api/auditoria/dashboard/', { credentials: 'include' })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Atualizar KPIs
                    document.getElementById('dash-nota-media').textContent = data.nota_media_geral.toFixed(1);
                    document.getElementById('dash-total-audits').textContent = data.total_auditorias;
                    document.getElementById('dash-total-alerts').textContent = data.total_alertas;
                    
                    const qualidade = data.total_auditorias > 0 
                        ? (((data.distribuicao.excelente + data.distribuicao.bom) / data.total_auditorias) * 100).toFixed(0) 
                        : 0;
                    document.getElementById('dash-qualidade').textContent = qualidade + '%';

                    // Renderizar Gráfico Geral
                    renderGlobalChart(data.evolucao_diaria);
                    
                    // IA Insight (Mockup ou Chamada Real)
                    generateIASummary(data);
                }
            })
            .catch(error => console.error('Erro ao carregar dashboard executivo:', error));
    }

    function renderGlobalChart(evolucao) {
        const ctx = document.getElementById('chartEvolucaoGeral').getContext('2d');
        
        if (state.charts.geral) state.charts.geral.destroy();
        
        const labels = evolucao.map(d => formatDate(d.data));
        const dataPoints = evolucao.map(d => d.nota);

        state.charts.geral = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Nota Média do Departamento',
                    data: dataPoints,
                    borderColor: '#4f46e5',
                    backgroundColor: 'rgba(79, 70, 229, 0.05)',
                    borderWidth: 3,
                    pointRadius: 4,
                    pointBackgroundColor: '#4f46e5',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        min: 0,
                        max: 10,
                        grid: { display: true, color: 'rgba(0,0,0,0.05)' }
                    },
                    x: {
                        grid: { display: false }
                    }
                }
            }
        });
    }

    function generateIASummary(data) {
        const summaryEl = document.getElementById('ia-auditor-summary');
        
        // Simulação de insight inteligente baseado nos dados reais
        const topAnalyst = (data.top_3 && data.top_3[0]) ? data.top_3[0].nome : '—';
        
        // Correção do cálculo para evitar NaN
        const total = data.total_auditorias || 0;
        const alertas = data.total_alertas || 0;
        const alertPerc = total > 0 ? ((alertas / total) * 100).toFixed(0) : 0;
        
        let insight = `Este mês identificamos <strong>${total}</strong> auditorias com nota média de <strong>${data.nota_media_geral.toFixed(1)}</strong>. `;
        
        if (alertPerc > 20) {
            insight += `Observamos um volume de <strong>${alertPerc}%</strong> de alertas. Recomendamos foco em conformidade de processos. `;
        } else {
            insight += `Alta performance: índice de alertas em <strong>${alertPerc}%</strong>. `;
        }
        
        if (topAnalyst !== '—') {
            insight += `Destaque positivo para <strong>${topAnalyst}</strong>.`;
        }
        
        summaryEl.innerHTML = `<p class="mb-0">${insight}</p>`;

        // Gerar Insight de Foco Dinâmico
        const focusEl = document.querySelector('#ia-auditor-summary + div .small.fw-semibold.text-dark');
        if (focusEl && data.falhas_por_criterio && data.falhas_por_criterio.length > 0) {
            const principalFalha = data.falhas_por_criterio[0];
            let acao = '';
            
            // Mapear falhas para ações recomendadas
            const acoes = {
                'apresentou_corretamente': 'Reforçar script de abertura e saudação',
                'analisou_historico': 'Treinar equipe na leitura do histórico de chamados',
                'entendeu_solicitacao': 'Melhorar técnicas de escuta ativa e interpretação',
                'informacao_clara': 'Trabalhar clareza e objetividade nas respostas',
                'acordo_espera': 'Revisar regras de tempo de espera e SLA',
                'atendimento_respeitoso': 'Feedback urgente sobre cordialidade e postura',
                'portugues_correto': 'Oferecer reciclagem de escrita e gramática',
                'finalizacao_correta': 'Padronizar processo de encerramento de tickets',
                'procedimento_correto': 'Revisar fluxos técnicos e manuais de procedimento'
            };
            
            acao = acoes[principalFalha.campo] || `Focar em melhoria no pilar de ${principalFalha.label}`;
            focusEl.textContent = acao;
        } else if (focusEl) {
            focusEl.textContent = "Manter o padrão de excelência atual";
        }
    }

    function initAnalystView() {
        const dataInicio = document.getElementById('filtro_analista_data_inicio')?.value;
        const dataFim = document.getElementById('filtro_analista_data_fim')?.value;
        
        let url = '/api/auditoria/dashboard/';
        if (dataInicio || dataFim) {
            const params = new URLSearchParams();
            if (dataInicio) params.append('data_inicio', dataInicio);
            if (dataFim) params.append('data_fim', dataFim);
            url += '?' + params.toString();
        }

        // Carregar stats para os cards
        fetch(url, { credentials: 'include' })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Preencher Resumo Geral
                    if (document.getElementById('analyst-total-geral')) {
                        document.getElementById('analyst-total-geral').textContent = data.total_all_time || 0;
                        document.getElementById('analyst-total-periodo').textContent = data.total_auditorias || 0;
                        document.getElementById('analyst-media-geral').textContent = data.nota_media_geral ? (data.nota_media_geral.toFixed(1) + '/10') : '0.0/10';
                    }

                    // Preencher Distribuição (Cards coloridos)
                    if (data.distribuicao) {
                        document.getElementById('count-excelente').textContent = data.distribuicao.excelente || 0;
                        document.getElementById('count-bom').textContent = data.distribuicao.bom || 0;
                        document.getElementById('count-regular').textContent = data.distribuicao.regular || 0;
                        document.getElementById('count-insatisfatorio').textContent = data.distribuicao.insatisfatorio || 0;
                    }
                    
                    // Carregar lista completa por padrão (Todas)
                    loadAnalystAudits('');
                    const container = document.getElementById('analyst-list-container');
                    if (container) container.style.display = 'block';
                }
            })
            .catch(error => console.error('Erro ao carregar dashboard analista:', error));
    }

    window.handleGerarInsightAnalyst = function() {
        const modalEl = document.getElementById('modalIAAnalista');
        const loading = document.getElementById('ia-loading-analista');
        const result = document.getElementById('ia-result-analista');
        
        if (!modalEl) return;
        
        const modal = new bootstrap.Modal(modalEl);
        modal.show();
        
        loading.style.display = 'block';
        result.style.display = 'none';
        
        // Obter datas do filtro
        const dataInicio = document.getElementById('filtro_analista_data_inicio')?.value;
        const dataFim = document.getElementById('filtro_analista_data_fim')?.value;
        
        fetch(`/api/auditoria/analista/self/ia-insight/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                data_inicio: dataInicio,
                data_fim: dataFim
            })
        })
        .then(r => r.json())
        .then(data => {
            loading.style.display = 'none';
            if (data.success) {
                result.style.display = 'block';
                const markdown = data.insight_markdown;
                
                // Salvar no sessionStorage para persistência
                sessionStorage.setItem('brisoft_analyst_feedback', markdown);
                
                if (window.marked) {
                    result.innerHTML = marked.parse(markdown);
                } else {
                    result.innerText = markdown;
                }
                
                checkPersistedFeedback();
            } else {
                Swal.fire('Aviso', data.error || 'Erro ao gerar feedback', 'warning');
                modal.hide();
            }
        })
        .catch(err => {
            console.error(err);
            loading.style.display = 'none';
            Swal.fire('Erro', 'Erro de conexão com o servidor', 'error');
            modal.hide();
        });
    }

    function checkPersistedFeedback() {
        const savedFeedback = sessionStorage.getItem('brisoft_analyst_feedback');
        const btnContainer = document.querySelector('#btnGerarInsightAnalista')?.parentElement;
        
        if (savedFeedback && btnContainer) {
            // Se já existe o botão de ver feedback, não duplica
            if (document.getElementById('btnVerFeedbackSalvo')) return;
            
            const btnVer = document.createElement('button');
            btnVer.id = 'btnVerFeedbackSalvo';
            btnVer.className = 'btn btn-outline-primary rounded-pill px-4 fw-bold ms-2';
            btnVer.innerHTML = '<i class="bi bi-eye me-2"></i>Ver Feedback Atual';
            btnVer.onclick = () => {
                const modalEl = document.getElementById('modalIAAnalista');
                const result = document.getElementById('ia-result-analista');
                const loading = document.getElementById('ia-loading-analista');
                
                loading.style.display = 'none';
                result.style.display = 'block';
                
                if (window.marked) {
                    result.innerHTML = marked.parse(savedFeedback);
                } else {
                    result.innerText = savedFeedback;
                }
                
                const modal = new bootstrap.Modal(modalEl);
                modal.show();
            };
            btnContainer.appendChild(btnVer);
        }
    }

    window.filterAnalystList = function (classificacao) {
        console.log('Filtrando analista por:', classificacao);
        const cards = document.querySelectorAll('.card-dashboard');
        
        // Se clicar no que já está selecionado, desseleciona (mostra todos)
        if (state.currentAnalystFilter === classificacao) {
            console.log('Limpando filtro');
            state.currentAnalystFilter = '';
            cards.forEach(c => c.classList.remove('selected'));
        } else {
            state.currentAnalystFilter = classificacao;
            cards.forEach(c => c.classList.remove('selected'));
            
            // Adicionar classe selected ao card clicado
            cards.forEach(card => {
                const attr = card.getAttribute('onclick');
                if (attr && attr.includes(`'${classificacao}'`)) {
                    card.classList.add('selected');
                }
            });
        }

        // Atualizar label
        const map = {
            'excelente': 'Excelente',
            'bom': 'Bom',
            'regular': 'Regular',
            'insatisfatorio': 'Insatisfatório',
            '': 'Todas'
        };
        const label = document.getElementById('current-filter-label');
        if (label) label.textContent = map[state.currentAnalystFilter] || 'Todas';

        // Mostrar container
        const container = document.getElementById('analyst-list-container');
        if (container) {
            container.style.display = 'block';
        }

        console.log('Chamando loadAnalystAudits com:', state.currentAnalystFilter);
        loadAnalystAudits(state.currentAnalystFilter);
    }

    function loadAnalystAudits(classificacao) {
        console.log('Iniciando loadAnalystAudits:', classificacao);
        const tbody = document.getElementById('lista-auditorias-analista');
        if (!tbody) {
            console.error('tbody não encontrado!');
            return;
        }
        tbody.innerHTML = '<tr><td colspan="7" class="text-center py-4"><div class="spinner-border text-primary"></div></td></tr>';

        const params = new URLSearchParams({
            classificacao: classificacao,
            per_page: 50
        });

        const dataInicio = document.getElementById('filtro_analista_data_inicio')?.value;
        const dataFim = document.getElementById('filtro_analista_data_fim')?.value;

        if (dataInicio) params.append('data_inicio', dataInicio);
        if (dataFim) params.append('data_fim', dataFim);

        const url = `/api/auditoria/list/?${params}`;
        console.log('Fetching URL:', url);

        fetch(url, { credentials: 'include' })
            .then(response => response.json())
            .then(data => {
                console.log('Data received:', data);
                if (data.success) {
                    renderAnalystAudits(data.auditorias, tbody);
                } else {
                    console.error('API Error:', data.error);
                }
            })
            .catch(error => {
                console.error('Fetch Error:', error);
                tbody.innerHTML = '<tr><td colspan="7" class="text-center text-danger">Erro ao carregar auditorias</td></tr>';
            });
    }

    function renderAnalystAudits(auditorias, tbody) {
        if (auditorias.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center py-5 text-muted"><i class="bi bi-inbox fs-2 d-block mb-2"></i>Nenhuma auditoria encontrada para este filtro.</td></tr>';
            return;
        }

        tbody.innerHTML = '';
        auditorias.forEach(aud => {
            const tr = document.createElement('tr');
            tr.style.cursor = 'pointer';
            tr.onclick = (e) => viewDetails(aud.id, e);
            if (aud.requer_acao) tr.classList.add('row-alert');

            const badgeClass = `badge-${aud.classificacao}`;
            const dataFormatada = formatDate(aud.data_atendimento);

            tr.innerHTML = `
                <td>${dataFormatada}</td>
                <td>${aud.id_conversa}</td>
                <td><span class="badge bg-secondary">${aud.tipo_atendimento}</span></td>
                <td>${aud.pontuacao}/9</td>
                <td class="fw-bold">${aud.nota.toFixed(1)}/10</td>
                <td>
                    <span class="badge ${badgeClass}">${aud.classificacao_display}</span>
                    ${aud.requer_acao ? '<i class="bi bi-exclamation-triangle icon-alert ms-2"></i>' : ''}
                </td>
                <td>
                    <button class="btn btn-sm btn-outline-primary" title="Ver detalhes">
                        <i class="bi bi-eye"></i>
                    </button>
                </td>
            `;
            tbody.appendChild(tr);

            const trDetails = document.createElement('tr');
            trDetails.id = `details-${aud.id}`;
            trDetails.style.display = 'none';
            trDetails.className = 'details-row';
            trDetails.innerHTML = `
                <td colspan="7" class="p-0 border-0">
                    <div class="details-container p-4 bg-light border-bottom shadow-inner" style="box-shadow: inset 0 2px 4px rgba(0,0,0,0.05);"></div>
                </td>
            `;
            tbody.appendChild(trDetails);
        });
    }


    // ========================================
    // UPLOAD DE IMAGEM DE EVIDÊNCIA
    // ========================================

    function handleImageUpload(event, criterioNome) {
        const file = event.target.files[0];
        if (!file) return;

        // Validar tamanho (5MB)
        if (file.size > 5 * 1024 * 1024) {
            Swal.fire({
                icon: 'warning',
                title: 'Arquivo muito grande',
                text: 'O tamanho máximo permitido é 5MB',
            });
            event.target.value = '';
            return;
        }

        // Mostrar preview
        const reader = new FileReader();
        reader.onload = function (e) {
            const previewContainer = document.getElementById(`preview-${criterioNome}`);
            const previewImg = previewContainer ? previewContainer.querySelector('img') : null;

            if (previewImg && previewContainer) {
                previewImg.src = e.target.result;
                previewContainer.style.display = 'block';
            }

            // TODO: Implementar upload para Supabase Storage
            //'Por enquanto, vamos usar base64 (temporário)
            const hiddenInput = document.getElementById(`imagem_erro_${criterioNome}_url`);
            if (hiddenInput) {
                // TEMPORÁRIO: usando base64 até configurar Supabase
                hiddenInput.value = e.target.result;
            }
        };
        reader.readAsDataURL(file);
    }

    // Função global para remover imagem (chamada por onclick)
    window.removeImage = function (criterioNome) {
        const inputFile = document.getElementById(`imagem_erro_${criterioNome}`);
        const previewContainer = document.getElementById(`preview-${criterioNome}`);
        const hiddenInput = document.getElementById(`imagem_erro_${criterioNome}_url`);

        if (inputFile) inputFile.value = '';
        if (previewContainer) previewContainer.style.display = 'none';
        if (hiddenInput) hiddenInput.value = '';
    };

    // Inicializar preview na carga
    updatePreview();

    // Definir data de hoje como padrão
    const dataInput = document.getElementById('data_atendimento');
    if (dataInput) {
        dataInput.value = new Date().toISOString().split('T')[0];
    }
});
// Registrar Ciente do Analista
window.darCiente = function (id) {
    Swal.fire({
        title: 'Confirmar Ciente',
        text: 'Deseja registrar que você está ciente dos pontos identificados nesta auditoria?',
        icon: 'question',
        showCancelButton: true,
        confirmButtonText: 'Sim, dar ciente',
        cancelButtonText: 'Cancelar'
    }).then((result) => {
        if (result.isConfirmed) {
            fetch(`/api/auditoria/${id}/ciente/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'Content-Type': 'application/json'
                }
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        Swal.fire('Sucesso!', 'Seu ciente foi registrado com sucesso.', 'success')
                            .then(() => {
                                // Recarregar detalhes ou a lista
                                const container = document.querySelector(`#details-${id} .details-container`);
                                if (container) container.innerHTML = '';
                                viewDetails(id);
                                if (typeof initAnalystView === 'function') initAnalystView();
                            });
                    } else {
                        Swal.fire('Erro', data.error || 'Erro ao registrar ciente', 'error');
                    }
                })
                .catch(error => {
                    console.error('Erro:', error);
                    Swal.fire('Erro', 'Ocorreu um erro na comunicação com o servidor', 'error');
                });
        }
    });
};

// ========================================
// FUNÇÃO PARA PREENCHIMENTO AUTOMÁTICO IA
// ========================================
window.preencherAuditoriaIA = async function() {
    const idConversa = document.getElementById('id_conversa').value.trim();
    const tipoAtendimento = document.getElementById('tipo_atendimento').value;
    const analistaId = document.getElementById('analista_auditado_id').value;

    if (!idConversa) {
        Swal.fire('Atenção', 'Por favor, preencha o campo "ID Conversa" primeiro.', 'warning');
        document.getElementById('id_conversa').focus();
        return;
    }

    if (!tipoAtendimento) {
        Swal.fire('Atenção', 'Por favor, selecione o "Tipo" de atendimento (Cliente ou Franqueado).', 'warning');
        document.getElementById('tipo_atendimento').focus();
        return;
    }

    const btn = document.getElementById('btnPreencherIA');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span> IA...';
    btn.disabled = true;

    try {
        const response = await fetch('/api/auditoria/preencher-ia/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            },
            body: JSON.stringify({
                id_conversa: idConversa,
                tipo_atendimento: tipoAtendimento,
                analista_id: analistaId
            })
        });

        const data = await response.json();

        if (data.success) {
            const result = data.ia_data;
            
            // Atualiza os switches e campos de texto
            const updateField = (idSwitch, erroFieldId, status, errorMessage) => {
                const switchEl = document.getElementById(idSwitch);
                if (switchEl) {
                    if (switchEl.checked !== status) {
                        switchEl.click(); // Dispara eventos visuais
                    }
                    if (!status && errorMessage) {
                        const errorTextArea = document.getElementById(erroFieldId);
                        if (errorTextArea) {
                            errorTextArea.value = errorMessage;
                        }
                    } else if (status) {
                        const errorTextArea = document.getElementById(erroFieldId);
                        if (errorTextArea) {
                            errorTextArea.value = "";
                        }
                    }
                }
            };

            updateField('apresentou_corretamente', 'erro_apresentacao', result.apresentou_corretamente, result.erro_apresentacao);
            updateField('analisou_historico', 'erro_historico', result.analisou_historico, result.erro_historico);
            updateField('entendeu_solicitacao', 'erro_entendimento', result.entendeu_solicitacao, result.erro_entendimento);
            updateField('informacao_clara', 'erro_informacao', result.informacao_clara, result.erro_informacao);
            updateField('acordo_espera', 'erro_acordo_espera', result.acordo_espera, result.erro_acordo_espera);
            updateField('atendimento_respeitoso', 'erro_respeito', result.atendimento_respeitoso, result.erro_respeito);
            updateField('portugues_correto', 'erro_portugues', result.portugues_correto, result.erro_portugues);
            // No backend é finalizacao_correta e procedimento_correto, vamos testar os IDs do front
            updateField('finalizou_corretamente', 'erro_finalizacao', result.finalizacao_correta, result.erro_finalizacao);
            updateField('procedimento_correto', 'erro_procedimento', result.procedimento_correto, result.erro_procedimento);

            // Marca o hidden flag que isso foi gerado por IA
            let iaInput = document.getElementById('gerado_por_ia');
            if (!iaInput) {
                iaInput = document.createElement('input');
                iaInput.type = 'hidden';
                iaInput.id = 'gerado_por_ia';
                iaInput.name = 'gerado_por_ia';
                iaInput.value = 'true';
                document.getElementById('formAuditoria').appendChild(iaInput);
            } else {
                iaInput.value = 'true';
            }

            Swal.fire({
                title: 'Sucesso!',
                text: 'Auditoria preenchida com sucesso pela IA! Revise os campos e clique em Salvar.',
                icon: 'success',
                timer: 3000,
                showConfirmButton: false
            });

        } else {
            Swal.fire('Erro', data.error || "Erro ao preencher com IA.", 'error');
        }
    } catch (err) {
        console.error(err);
        Swal.fire('Erro', 'Ocorreu um erro de comunicação com o servidor.', 'error');
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
};

// ========================================
// CARREGAR AUDITORIAS IA (TEMPO REAL)
// ========================================
window.loadAuditoriasIA = function(page = 1) {
    const tbody = document.getElementById('lista-auditorias-ia');
    if (!tbody) return;

    tbody.innerHTML = `
        <tr>
            <td colspan="8" class="text-center py-4">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Carregando...</span>
                </div>
            </td>
        </tr>
    `;

    fetch(`/api/auditoria/list/?gerado_por_ia=true&page=${page}&per_page=20`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                renderAuditoriasIATable(data.auditorias);
                renderPaginacaoIA(data);
            } else {
                tbody.innerHTML = `<tr><td colspan="8" class="text-center text-danger py-4">Erro: ${data.error}</td></tr>`;
            }
        })
        .catch(error => {
            console.error('Erro:', error);
            tbody.innerHTML = `<tr><td colspan="8" class="text-center text-danger py-4">Erro de processamento interno.</td></tr>`;
        });
};

function renderAuditoriasIATable(auditorias) {
    const tbody = document.getElementById('lista-auditorias-ia');
    tbody.innerHTML = '';

    if (!auditorias || auditorias.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center py-5 text-muted">
                    <i class="bi bi-robot fs-1 d-block mb-3" style="opacity: 0.5;"></i>
                    <p class="mb-0">A IA ainda não realizou nenhuma auditoria automática.</p>
                </td>
            </tr>
        `;
        return;
    }

    auditorias.forEach(aud => {
        const tr = document.createElement('tr');
        
        const badgeClass = `badge-${aud.classificacao}`;
        const dataFormatada = typeof formatDate === 'function' ? formatDate(aud.data_atendimento) : aud.data_atendimento;

        tr.innerHTML = `
            <td>${dataFormatada}</td>
            <td>${aud.id_conversa}</td>
            <td><span class="badge bg-secondary">${aud.tipo_atendimento}</span></td>
            <td>${aud.analista_auditado.nome_completo || aud.analista_auditado.username}</td>
            <td>${aud.pontuacao}/9</td>
            <td class="fw-bold text-primary">${Number(aud.nota).toFixed(1)}</td>
            <td>
                <span class="badge ${badgeClass}">${aud.classificacao_display || aud.classificacao.toUpperCase()}</span>
            </td>
            <td>
                <span class="badge" style="background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white; padding: 5px 10px; font-weight: normal;"><i class="bi bi-robot me-1"></i>Automático</span>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function renderPaginacaoIA(data) {
    const container = document.getElementById('paginacao-ia');
    if (!container) return;

    if (!data.total_pages || data.total_pages <= 1) {
        container.innerHTML = '';
        return;
    }

    let html = `
        <span class="text-muted small">Mostrando página ${data.page} de ${data.total_pages}</span>
        <ul class="pagination pagination-sm mb-0">
    `;

    if (data.page > 1) {
        html += `<li class="page-item"><button class="page-link" onclick="window.loadAuditoriasIA(${data.page - 1})">Anterior</button></li>`;
    } else {
        html += `<li class="page-item disabled"><span class="page-link">Anterior</span></li>`;
    }

    if (data.page < data.total_pages) {
        html += `<li class="page-item"><button class="page-link" onclick="window.loadAuditoriasIA(${data.page + 1})">Próxima</button></li>`;
    } else {
        html += `<li class="page-item disabled"><span class="page-link">Próxima</span></li>`;
    }

    html += `</ul>`;
    container.innerHTML = html;
}

window.forcarAuditoriasIA = async function() {
    const btn = document.getElementById('btn-forcar-ia');
    const originalText = btn.innerHTML;
    
    // Mostrar loading
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Processando...';
    btn.disabled = true;

    Swal.fire({
        title: 'Gerando Auditorias',
        text: 'A IA está analisando as conversas mais recentes. Isso pode levar de 30 a 60 segundos...',
        allowOutsideClick: false,
        allowEscapeKey: false,
        didOpen: () => {
            Swal.showLoading();
        }
    });

    try {
        const response = await fetch('/api/auditoria/forcar-ia/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ quantidade: 3 })
        });
        
        const data = await response.json();
        
        if (data.success) {
            if (data.processadas > 0) {
                Swal.fire({
                    icon: 'success',
                    title: 'Auditorias Geradas!',
                    html: `<b>${data.processadas}</b> novas auditorias foram realizadas pela IA com sucesso.<br><br><small class="text-muted">Conversas pendentes na fila: ${data.pendentes_restantes}</small>`,
                    confirmButtonText: 'OK'
                }).then(() => {
                    window.loadAuditoriasIA(1);
                });
            } else {
                Swal.fire({
                    icon: 'info',
                    title: 'Fila Vazia',
                    text: data.message || 'Não há novas sessões para serem auditadas no momento.',
                    confirmButtonText: 'OK'
                });
            }
        } else {
            Swal.fire({
                icon: 'error',
                title: 'Erro',
                text: data.error || 'Ocorreu um erro ao processar as auditorias.',
            });
        }
    } catch (error) {
        console.error('Erro no processamento em lote:', error);
        Swal.fire({
            icon: 'error',
            title: 'Erro de Conexão',
            text: 'O servidor demorou muito para responder ou a conexão falhou.',
        });
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
};
