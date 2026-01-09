/**
 * Sistema de Toast para feedback visual ao usuário
 * Tipos: success, error, info, warning
 */

// Armazena toasts ativos para evitar duplicação
const activeToasts = new Map();

// Cria o container de toasts se não existir
function createToastContainer() {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            display: flex;
            flex-direction: column;
            gap: 10px;
            pointer-events: none;
        `;
        document.body.appendChild(container);
    }
    return container;
}

/**
 * Exibe um toast na tela
 * @param {string} type - Tipo do toast: 'success', 'error', 'info', 'warning'
 * @param {string} message - Mensagem a ser exibida
 * @param {number} duration - Duração em milissegundos (padrão: 8000)
 */
function showToast(type, message, duration = 8000) {
    // Previne duplicação de toasts idênticos
    const toastKey = `${type}:${message}`;
    if (activeToasts.has(toastKey)) {
        return activeToasts.get(toastKey);
    }
    
    const container = createToastContainer();
    
    // Cria o elemento do toast
    const toast = document.createElement('div');
    toast.className = `toast toast-${type} show`; // Adiciona classe 'show' para opacity: 1
    
    // Define as cores baseado no tipo
    const colors = {
        success: { bg: '#10b981', icon: '✓' },
        error: { bg: '#ef4444', icon: '✕' },
        info: { bg: '#3b82f6', icon: 'ℹ' },
        warning: { bg: '#f59e0b', icon: '⚠' }
    };
    
    const color = colors[type] || colors.info;
    
    toast.style.cssText = `
        background-color: ${color.bg};
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        display: flex;
        align-items: center;
        gap: 10px;
        max-width: 400px;
        pointer-events: auto;
        font-size: 14px;
        font-weight: 500;
        transform: translateX(0);
        transition: all 0.3s ease-out;
    `;
    
    // Adiciona o ícone
    const icon = document.createElement('span');
    icon.textContent = color.icon;
    icon.style.cssText = `
        font-size: 18px;
        font-weight: bold;
        flex-shrink: 0;
    `;
    
    // Adiciona a mensagem
    const messageSpan = document.createElement('span');
    messageSpan.textContent = message;
    messageSpan.style.cssText = `
        flex: 1;
        word-break: break-word;
    `;
    
    // Variável para armazenar o timeout
    let timeoutId = null;
    
    // Botão de fechar
    const closeBtn = document.createElement('button');
    closeBtn.textContent = '×';
    closeBtn.style.cssText = `
        background: none;
        border: none;
        color: white;
        font-size: 20px;
        cursor: pointer;
        padding: 0;
        margin-left: 8px;
        line-height: 1;
        opacity: 0.8;
        transition: opacity 0.2s;
        flex-shrink: 0;
    `;
    closeBtn.onmouseover = () => closeBtn.style.opacity = '1';
    closeBtn.onmouseout = () => closeBtn.style.opacity = '0.8';
    
    closeBtn.onclick = () => {
        if (timeoutId) {
            clearTimeout(timeoutId);
        }
        activeToasts.delete(toastKey);
        removeToast(toast);
    };
    
    toast.appendChild(icon);
    toast.appendChild(messageSpan);
    toast.appendChild(closeBtn);
    
    // Adiciona ao container
    container.appendChild(toast);
    
    // Remove automaticamente após a duração especificada
    timeoutId = setTimeout(() => {
        activeToasts.delete(toastKey);
        removeToast(toast);
    }, duration);
    
    // Registra o toast ativo
    activeToasts.set(toastKey, toast);
    
    return toast;
}

/**
 * Remove um toast da tela com animação
 */
function removeToast(toast) {
    if (!toast || !toast.parentNode) return;
    
    // Previne múltiplas chamadas
    if (toast.dataset.removing === 'true') return;
    toast.dataset.removing = 'true';
    
    toast.style.animation = 'slideOut 0.3s ease-in';
    setTimeout(() => {
        if (toast.parentNode) {
            toast.parentNode.removeChild(toast);
        }
    }, 300);
}

// Adiciona os estilos de animação ao documento
function addToastStyles() {
    if (document.getElementById('toast-styles')) return;
    
    const style = document.createElement('style');
    style.id = 'toast-styles';
    style.textContent = `
        @keyframes slideIn {
            from {
                transform: translateX(400px);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        @keyframes slideOut {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(400px);
                opacity: 0;
            }
        }
        
        @media (max-width: 768px) {
            #toast-container {
                right: 10px;
                left: 10px;
                top: 10px;
            }
            
            .toast {
                max-width: 100% !important;
            }
        }
    `;
    document.head.appendChild(style);
}

// Inicializa os estilos quando o DOM estiver pronto
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', addToastStyles);
} else {
    addToastStyles();
}

// Torna a função global para uso em qualquer lugar
window.showToast = showToast;
