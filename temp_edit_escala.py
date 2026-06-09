"""
Script para corrigir o segundo bloco <script> no escala.html.
Substitui referências diretas às variáveis do primeiro bloco por window._escala.
"""

path = r'c:\Users\jeferson\Documents\Sites\Brisoft\templates\core\escala.html'

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

marker_start = '<script>\n    // ========================================\n    // JORNADAS TEMP'
marker_end = '</script>\n{% endblock %}'

idx_start = content.find(marker_start)
idx_end = content.find(marker_end)

if idx_start == -1:
    print("ERRO: Não encontrou o início do segundo script block!")
    exit(1)
if idx_end == -1:
    print("ERRO: Não encontrou o fim do segundo script block!")
    exit(1)

print(f"Segundo bloco encontrado: pos {idx_start} até {idx_end}")

new_script = '''<script>
    // ========================================
    // JORNADAS TEMPORÁRIAS (SUB-TAB CONFIG)
    // ========================================
    let allJornadas = [];
    let currentPageJornadas = 1;
    let deleteJornadaId = null;

    function switchConfigTab(tab) {
        const tabModelos = document.getElementById('tabModelos');
        const tabJornadasTemp = document.getElementById('tabJornadasTemp');
        const contentModelos = document.getElementById('tabContentModelos');
        const contentJornadasTemp = document.getElementById('tabContentJornadasTemp');
        
        if (!tabModelos || !tabJornadasTemp || !contentModelos || !contentJornadasTemp) return;

        if (tab === 'modelos') {
            tabModelos.classList.add('btn-primary', 'active');
            tabModelos.classList.remove('btn-light', 'border');
            tabJornadasTemp.classList.add('btn-light', 'border');
            tabJornadasTemp.classList.remove('btn-primary', 'active');
            contentModelos.style.display = 'block';
            contentJornadasTemp.style.display = 'none';
        } else {
            tabJornadasTemp.classList.add('btn-primary', 'active');
            tabJornadasTemp.classList.remove('btn-light', 'border');
            tabModelos.classList.add('btn-light', 'border');
            tabModelos.classList.remove('btn-primary', 'active');
            contentModelos.style.display = 'none';
            contentJornadasTemp.style.display = 'block';
            loadJornadasTempData();
            loadJornadasTempFormOptions();
        }
    }

    async function loadJornadasTempData() {
        try {
            const _rascunhoId = window._escala ? window._escala.rascunhoId : null;
            const _escalaTipo = window._escala ? window._escala.escalaTipo : 'operacional';
            const params = _rascunhoId ? `?rascunho_id=${_rascunhoId}` : `?escala_tipo=${_escalaTipo}`;
            const response = await fetch(`/api/escala/jornadas-temp/${params}`);
            allJornadas = await response.json();
            renderJornadasTemp();
        } catch (e) {
            console.error('Erro ao carregar jornadas temporárias:', e);
            const tbody = document.getElementById('jornadasTbody');
            const _isAdmin = window._escala ? window._escala.isAdmin : false;
            if (tbody) tbody.innerHTML = `<tr><td colspan="${_isAdmin ? 6 : 5}" class="text-center py-5 text-danger">Erro ao carregar jornadas.</td></tr>`;
        }
    }

    function loadJornadasTempFormOptions() {
        const _analistas = window._escala ? window._escala.analistas : [];
        const _turnos = window._escala ? window._escala.turnos : [];

        const selAnalista = document.getElementById('jornadaAnalista');
        if (selAnalista) {
            selAnalista.innerHTML = '<option value="">Selecione...</option>' + 
                _analistas.map(a => `<option value="${a.id}">${a.nome}</option>`).join('');
        }

        const selTurno = document.getElementById('jornadaTurno');
        if (selTurno) {
            selTurno.innerHTML = '<option value="">Selecione...</option>' + 
                _turnos.map(t => `<option value="${t.id}">${t.nome}</option>`).join('');
        }
    }

    function formatDateBr(dateStr) {
        if (!dateStr) return '\u2014';
        const [y, m, d] = dateStr.split('-');
        return `${d}/${m}/${y}`;
    }

    function renderJornadasTemp() {
        const tbody = document.getElementById('jornadasTbody');
        if (!tbody) return;

        const _isAdmin = window._escala ? window._escala.isAdmin : false;

        const q = (document.getElementById('jornadasSearchInput').value || '').toLowerCase();
        const filtered = allJornadas.filter(j =>
            (j.analista_nome || '').toLowerCase().includes(q) ||
            (j.turno_temp_nome || '').toLowerCase().includes(q) ||
            (j.motivo || '').toLowerCase().includes(q)
        );

        const pp = parseInt(document.getElementById('jornadasPerPageSelect').value) || 10;
        const total = filtered.length;
        const totalPag = Math.max(1, Math.ceil(total / pp));
        if (currentPageJornadas > totalPag) currentPageJornadas = totalPag;

        const inicio = (currentPageJornadas - 1) * pp;
        const pagina = filtered.slice(inicio, inicio + pp);

        const info = document.getElementById('jornadasPaginacaoInfo');
        if (info) {
            if (total === 0) info.textContent = '0 registros';
            else info.textContent = `${inicio + 1} a ${Math.min(inicio + pp, total)} de ${total}`;
        }

        renderJornadasPaginacao(totalPag);

        if (pagina.length === 0) {
            tbody.innerHTML = `<tr><td colspan="${_isAdmin ? 6 : 5}" class="text-center py-5 text-muted">Nenhuma jornada encontrada.</td></tr>`;
        } else {
            tbody.innerHTML = pagina.map(j => `
            <tr>
                <td class="px-4 fw-semibold">${j.analista_nome}</td>
                <td>
                    <div class="turno-badge" style="background-color: ${j.turno_temp_cor || '#2563eb'}">
                        ${j.turno_temp_nome}
                    </div>
                </td>
                <td class="small text-muted"><i class="fa-solid fa-calendar-days me-1"></i> ${formatDateBr(j.data_inicio)} a ${formatDateBr(j.data_fim)}</td>
                <td class="small">${j.motivo || '\u2014'}</td>
                <td class="text-center">
                    <span class="status-badge status-${j.status}">${j.status.toUpperCase()}</span>
                </td>
                ${_isAdmin ? `
                <td class="text-end pe-4">
                    <button class="btn btn-sm btn-light border me-1" onclick="openModalJornadaEdit('${j.id}')" style="border-radius: 6px;">
                        <i class="fa-solid fa-pen-to-square text-primary"></i>
                    </button>
                    <button class="btn btn-sm btn-light border" onclick="openModalJornadaDelete('${j.id}', '${j.analista_nome} para ${j.turno_temp_nome}')" style="border-radius: 6px;">
                        <i class="fa-solid fa-trash text-danger"></i>
                    </button>
                </td>
                ` : ''}
            </tr>
        `).join('');
        }
    }

    function renderJornadasPaginacao(total) {
        const ul = document.getElementById('jornadasPaginacaoControles');
        if (!ul) return;
        ul.innerHTML = '';

        const prev = document.createElement('li');
        prev.className = `page-item ${currentPageJornadas === 1 ? 'disabled' : ''}`;
        prev.innerHTML = `<button class="page-link" ${currentPageJornadas === 1 ? 'disabled' : ''}>\u2039</button>`;
        prev.querySelector('button').onclick = () => { if (currentPageJornadas > 1) { currentPageJornadas--; renderJornadasTemp(); } };
        ul.appendChild(prev);

        for (let p = 1; p <= total; p++) {
            const li = document.createElement('li');
            li.className = `page-item ${p === currentPageJornadas ? 'active' : ''}`;
            li.innerHTML = `<button class="page-link">${p}</button>`;
            const pg = p;
            li.querySelector('button').onclick = () => { currentPageJornadas = pg; renderJornadasTemp(); };
            ul.appendChild(li);
        }

        const next = document.createElement('li');
        next.className = `page-item ${currentPageJornadas === total ? 'disabled' : ''}`;
        next.innerHTML = `<button class="page-link" ${currentPageJornadas === total ? 'disabled' : ''}>\u203a</button>`;
        next.querySelector('button').onclick = () => { if (currentPageJornadas < total) { currentPageJornadas++; renderJornadasTemp(); } };
        ul.appendChild(next);
    }

    function openModalJornadaEdit(id) {
        const form = document.getElementById('formJornadaTemp');
        if (form) form.reset();
        loadJornadasTempFormOptions();

        if (id) {
            document.getElementById('modalJornadaTempTitle').textContent = 'Editar Jornada Temporária';
            const j = allJornadas.find(x => x.id === id);
            if (j) {
                document.getElementById('jornadaTempId').value = j.id;
                document.getElementById('jornadaAnalista').value = j.analista_id;
                document.getElementById('jornadaTurno').value = j.turno_temp_id;
                document.getElementById('jornadaInicio').value = j.data_inicio;
                document.getElementById('jornadaFim').value = j.data_fim;
                document.getElementById('jornadaStatus').value = j.status;
                document.getElementById('jornadaMotivo').value = j.motivo;
            }
        } else {
            document.getElementById('modalJornadaTempTitle').textContent = 'Nova Jornada Temporária';
            document.getElementById('jornadaTempId').value = '';
            document.getElementById('jornadaStatus').value = 'ativo';
        }
        new bootstrap.Modal(document.getElementById('modalJornadaTemp')).show();
    }

    async function saveJornadaTemp() {
        const id = document.getElementById('jornadaTempId').value;
        const analista_id = document.getElementById('jornadaAnalista').value;
        const turno_temp_id = document.getElementById('jornadaTurno').value;
        const data_inicio = document.getElementById('jornadaInicio').value;
        const data_fim = document.getElementById('jornadaFim').value;
        const status = document.getElementById('jornadaStatus').value;
        const motivo = document.getElementById('jornadaMotivo').value;

        if (!analista_id || !turno_temp_id || !data_inicio || !data_fim || !motivo) {
            showToast('Preencha todos os campos obrigatórios.', 'warning');
            return;
        }

        const _rascunhoId = window._escala ? window._escala.rascunhoId : null;
        const _csrfToken = window._escala ? window._escala.csrfToken : '';

        const payload = {
            id: id || undefined,
            analista_id,
            turno_temp_id,
            data_inicio,
            data_fim,
            status,
            motivo,
            rascunho_id: _rascunhoId || undefined
        };

        try {
            const response = await fetch('/api/escala/jornadas-temp/save/', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'X-CSRFToken': _csrfToken 
                },
                body: JSON.stringify(payload)
            });
            const data = await response.json();
            if (data.success) {
                bootstrap.Modal.getInstance(document.getElementById('modalJornadaTemp')).hide();
                showToast('Jornada temporária salva com sucesso!', 'success');
                loadJornadasTempData();
                if (typeof initEscala === 'function') {
                    initEscala();
                } else {
                    location.reload();
                }
            } else {
                showToast(data.error, 'error');
            }
        } catch (e) {
            console.error(e);
            showToast('Erro ao salvar a jornada temporária.', 'error');
        }
    }

    function openModalJornadaDelete(id, info) {
        deleteJornadaId = id;
        document.getElementById('deleteJornadaTempInfo').textContent = info;
        new bootstrap.Modal(document.getElementById('modalJornadaTempDelete')).show();
    }

    async function confirmJornadaDelete() {
        if (!deleteJornadaId) return;
        const _csrfToken = window._escala ? window._escala.csrfToken : '';
        try {
            const response = await fetch(`/api/escala/jornadas-temp/${deleteJornadaId}/delete/`, {
                method: 'DELETE',
                headers: { 'X-CSRFToken': _csrfToken }
            });
            const data = await response.json();
            bootstrap.Modal.getInstance(document.getElementById('modalJornadaTempDelete')).hide();
            if (data.success) {
                showToast('Jornada temporária excluída!', 'success');
                loadJornadasTempData();
                if (typeof initEscala === 'function') {
                    initEscala();
                } else {
                    location.reload();
                }
            } else {
                showToast(data.error || 'Erro ao excluir.', 'error');
            }
        } catch (e) {
            console.error(e);
            showToast('Erro ao excluir jornada temporária.', 'error');
        }
    }
</script>'''

new_content = content[:idx_start] + new_script + content[idx_end + len('</script>'):]

with open(path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("OK! Arquivo salvo com sucesso.")
print(f"Tamanho original: {len(content)} bytes")
print(f"Tamanho novo: {len(new_content)} bytes")
