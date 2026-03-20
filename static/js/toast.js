/**
 * Sistema de Toast Notifications (Premium SweetAlert2)
 * Exibe mensagens animadas no canto inferior direito
 */

function showToast(message, type = 'info') {
    // Se o Swal estiver disponível, usa ele. Caso contrário, tenta showGlobalToast
    if (typeof Swal !== 'undefined') {
        const Toast = Swal.mixin({
            toast: true,
            position: 'bottom-end',
            showConfirmButton: false,
            timer: 4000,
            timerProgressBar: true,
            showClass: {
                popup: 'animate__animated animate__fadeInRight animate__faster'
            },
            hideClass: {
                popup: 'animate__animated animate__fadeOutRight animate__faster'
            },
            customClass: {
                popup: 'swal2-toast-premium'
            },
            didOpen: (toast) => {
                toast.addEventListener('mouseenter', Swal.stopTimer)
                toast.addEventListener('mouseleave', Swal.resumeTimer)
            }
        });

        const typeMap = {
            'success': 'success',
            'error': 'error',
            'danger': 'error',
            'warning': 'warning',
            'info': 'info',
            'debug': 'info'
        };

        const iconMap = {
            'success': 'success',
            'error': 'error',
            'danger': 'error',
            'warning': 'warning',
            'info': 'info'
        };

        Toast.fire({
            icon: iconMap[type] || 'info',
            title: message
        });

    } else {
        console.warn('SweetAlert2 não carregado. Toast:', message);
        // Fallback simples se necessário
        alert(message);
    }
}

// Alias global
window.showToast = showToast;

