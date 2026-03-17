/**
 * Script Principal do Tablet (Kiosk) de Ponto
 */

// Estado da Aplicação
const appState = {
    cpf: '',
    colaboradorId: null,
    tipoPonto: null,
    fotoBase64: null,
    videoStream: null
};

// Elementos da UI
const elCpfInput = document.getElementById('cpf-input');
const elCpfDisplay = document.getElementById('cpf-display');
const stepCpf = document.getElementById('step-cpf');
const stepTipo = document.getElementById('step-tipo');
const stepCamera = document.getElementById('step-camera');
const userAvatar = document.getElementById('user-avatar');
const userAvatarFallback = document.getElementById('user-avatar-fallback');
const userName = document.getElementById('user-name');
const userDept = document.getElementById('user-dept');
const cameraStream = document.getElementById('camera-stream');
const cameraLoading = document.getElementById('camera-loading');
const btnFullscreen = document.getElementById('btn-fullscreen');
const relogioKiosk = document.getElementById('relogio-kiosk');
const dataKiosk = document.getElementById('data-kiosk');

// ==========================================
// RELÓGIO
// ==========================================
function updateClock() {
    const now = new Date();
    
    // Hora
    const hh = String(now.getHours()).padStart(2, '0');
    const mm = String(now.getMinutes()).padStart(2, '0');
    const ss = String(now.getSeconds()).padStart(2, '0');
    relogioKiosk.textContent = `${hh}:${mm}:${ss}`;
    
    // Data
    const options = { weekday: 'short', day: '2-digit', month: 'long', year: 'numeric' };
    dataKiosk.textContent = now.toLocaleDateString('pt-BR', options);
}

setInterval(updateClock, 1000);
updateClock();

// ==========================================
// KIOSK MODE / FULLSCREEN
// ==========================================
btnFullscreen.addEventListener('click', () => {
    if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().catch(err => {
            console.warn(`Erro ao forçar fullscreen: ${err.message}`);
        });
    } else {
        if (document.exitFullscreen) {
            document.exitFullscreen();
        }
    }
});

// Bloqueio de tecla (F5, Ctrl+R, etc) para kiosk
document.addEventListener('keydown', (e) => {
    // Permite debug se precisar (ex: F12), mas em prod bloqueia tudo
    // Bloquear recarregar e voltar
    if (e.key === 'F5' || (e.ctrlKey && e.key === 'r') || (e.altKey && e.key === 'ArrowLeft')) {
        e.preventDefault();
    }
});


// ==========================================
// ETAPA 1: NUMPAD E CPF
// ==========================================
document.querySelectorAll('.numpad-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        // Obter som de click se quiser (opcional)
        
        const val = btn.getAttribute('data-val');
        
        if (val) {
            // Número
            if (appState.cpf.length < 6) {
                appState.cpf += val;
                updateCpfDisplay();
            }
        } else if (btn.id === 'btn-backspace') {
            appState.cpf = appState.cpf.slice(0, -1);
            updateCpfDisplay();
        } else if (btn.id === 'btn-clear') {
            appState.cpf = '';
            updateCpfDisplay();
        }
        
        // Auto-submit se chegar a 6 dígitos
        if (appState.cpf.length === 6) {
            buscarColaborador(appState.cpf);
        }
    });
});

function updateCpfDisplay() {
    elCpfInput.value = appState.cpf;
    
    // Mascara bonita
    let formatted = '';
    for(let i=0; i<6; i++) {
        if (i < appState.cpf.length) {
            formatted += appState.cpf[i] + ' ';
        } else {
            formatted += '• ';
        }
    }
    elCpfDisplay.textContent = formatted.trim();
}

async function buscarColaborador(cpf6) {
    Swal.fire({
        title: 'Buscando...',
        text: 'Aguarde um momento',
        allowOutsideClick: false,
        didOpen: () => Swal.showLoading(),
        customClass: { popup: 'kiosk-swal' }
    });
    
    try {
        const response = await fetch('/api/ponto/buscar-colaborador/', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({cpf_iniciais: cpf6})
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            Swal.fire({
                icon: 'error',
                title: 'Ops!',
                text: data.erro || 'Colaborador não encontrado.',
                customClass: { popup: 'kiosk-swal' },
                timer: 3000,
                showConfirmButton: false
            });
            appState.cpf = '';
            updateCpfDisplay();
            return;
        }
        
        // Colaborador encontrado
        Swal.close();
        appState.colaboradorId = data.id;
        
        // Preencher info na UI
        userName.textContent = data.nome;
        userDept.textContent = `${data.cargo} • ${data.departamento}`;
        
        if (data.foto_url) {
            userAvatar.src = data.foto_url;
            userAvatar.classList.remove('hidden');
            userAvatarFallback.classList.add('hidden');
        } else {
            userAvatar.classList.add('hidden');
            userAvatarFallback.classList.remove('hidden');
            // Initials Fallback
            const names = data.nome.split(' ');
            let ini = names[0][0].toUpperCase();
            if (names.length > 1) ini += names[names.length-1][0].toUpperCase();
            userAvatarFallback.textContent = ini;
        }
        
        // Avançar etapa
        stepCpf.classList.add('hidden');
        stepTipo.classList.remove('hidden');
        
    } catch (err) {
        console.error(err);
        Swal.fire({
            icon: 'error',
            title: 'Erro de conexão',
            text: 'Verifique a rede do tablet.',
            customClass: { popup: 'kiosk-swal' }
        });
        appState.cpf = '';
        updateCpfDisplay();
    }
}


// ==========================================
// ETAPA 2: ESCOLHA DE TIPO
// ==========================================
document.querySelectorAll('.type-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        appState.tipoPonto = btn.getAttribute('data-type');
        stepTipo.classList.add('hidden');
        stepCamera.classList.remove('hidden');
        startCamera();
    });
});


// ==========================================
// ETAPA 3: CÂMERA E REGISTRO
// ==========================================
async function startCamera() {
    cameraLoading.classList.remove('hidden');
    
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ 
            video: { facingMode: "user", width: { ideal: 720 }, height: { ideal: 1280 } },
            audio: false 
        });
        
        appState.videoStream = stream;
        cameraStream.srcObject = stream;
        
        cameraStream.onloadedmetadata = () => {
            cameraLoading.classList.add('hidden');
            
            // Tira foto automaticamente após 3 segundos
            let countdown = 3;
            const inst = document.getElementById('camera-instruction');
            inst.textContent = `Registrando em ${countdown}... Olhe para a câmera`;
            inst.classList.add('text-blue-400');
            
            const timer = setInterval(() => {
                countdown--;
                if(countdown > 0) {
                    inst.textContent = `Registrando em ${countdown}... Olhe para a câmera`;
                } else {
                    clearInterval(timer);
                    inst.textContent = "Fotografando...";
                    takePhotoAndSubmit();
                }
            }, 1000);
        };
        
    } catch (err) {
        console.error("Camera error:", err);
        cameraLoading.classList.add('hidden');
        Swal.fire({
            icon: 'warning',
            title: 'Câmera inacessível!',
            text: 'O registro será feito sem foto. (Verifique as permissões)',
            customClass: { popup: 'kiosk-swal' },
            confirmButtonText: 'Continuar'
        }).then(() => {
            // Tenta enviar sem foto
            submitRegistro(null);
        });
    }
}

function stopCamera() {
    if (appState.videoStream) {
        appState.videoStream.getTracks().forEach(track => track.stop());
        appState.videoStream = null;
    }
}

function takePhotoAndSubmit() {
    // Criar um canvas para capturar a frame
    const canvas = document.createElement('canvas');
    canvas.width = cameraStream.videoWidth;
    canvas.height = cameraStream.videoHeight;
    const ctx = canvas.getContext('2d');
    
    // Como a câmera está espelhada (-scale-x-100 via CSS), precisamos espelhar no canvas tbm 
    // ou apenas salvar do jeito normal. Vamos salvar do jeito normal.
    ctx.drawImage(cameraStream, 0, 0, canvas.width, canvas.height);
    
    // Obter jpeg base64 qualidade reduzida (0.7) para economizar banda/DB (embora vá pra S3/disco)
    const base64Photo = canvas.toDataURL('image/jpeg', 0.6);
    
    submitRegistro(base64Photo);
}

async function submitRegistro(fotoBase64) {
    Swal.fire({
        title: 'Registrando...',
        allowOutsideClick: false,
        didOpen: () => Swal.showLoading(),
        customClass: { popup: 'kiosk-swal' }
    });
    
    try {
        const payload = {
            colaborador_id: appState.colaboradorId,
            tipo: appState.tipoPonto,
            origem: 'tablet',
            foto_base64: fotoBase64
        };
        
        const response = await fetch('/api/ponto/registrar/', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            stopCamera();
            Swal.fire({
                icon: 'error',
                title: 'Gravação Falhou',
                text: data.erro || 'Erro desconhecido',
                customClass: { popup: 'kiosk-swal' },
                timer: 4000,
                showConfirmButton: false
            }).then(() => resetKiosk());
            return;
        }
        
        // Sucesso
        stopCamera();
        
        // Formatar sucesso
        Swal.fire({
            icon: 'success',
            title: 'Ponto Registrado!',
            html: `
                <div class="text-xl mt-4">
                    <span class="block">${userName.textContent}</span>
                    <span class="block font-bold text-blue-400 text-3xl mt-2">${data.hora}</span>
                    <span class="block text-slate-400 text-sm mt-1">${data.tipo}</span>
                </div>
            `,
            customClass: { popup: 'kiosk-swal' },
            timer: 5000,
            timerProgressBar: true,
            showConfirmButton: false
        }).then(() => {
            resetKiosk();
        });
        
    } catch (err) {
        console.error(err);
        stopCamera();
        Swal.fire({
            icon: 'error',
            title: 'Erro de conexão',
            text: 'Tente novamente.',
            customClass: { popup: 'kiosk-swal' }
        }).then(() => resetKiosk());
    }
}


// ==========================================
// RESET GLOBAL
// ==========================================
function resetKiosk() {
    stopCamera();
    appState.cpf = '';
    appState.colaboradorId = null;
    appState.tipoPonto = null;
    appState.fotoBase64 = null;
    
    updateCpfDisplay();
    
    stepCamera.classList.add('hidden');
    stepTipo.classList.add('hidden');
    stepCpf.classList.remove('hidden');
    
    document.getElementById('camera-instruction').textContent = "Aguardando...";
}

// Iniciar
updateCpfDisplay();
