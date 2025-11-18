// ==========================================
// 🌐 MONITOR DE CONEXÃO
// ==========================================
// Detecta quando o usuário fica offline/online
// e mostra avisos visuais no topo da tela

class ConnectionMonitor {
    constructor() {
        this.isOnline = navigator.onLine;
        this.previousState = this.isOnline;
        this.checkInterval = null;
        
        // Elementos DOM
        this.offlineBanner = null;
        this.onlineBanner = null;
        this.statusIndicator = null;
        
        this.init();
    }
    
    init() {
        // Cria elementos HTML
        this.createElements();
        
        // Event Listeners nativos do navegador
        window.addEventListener('online', () => this.handleOnline());
        window.addEventListener('offline', () => this.handleOffline());
        
        // Checa conexão real com backend a cada 10 segundos
        this.startPeriodicCheck();
        
        // Checa estado inicial
        this.checkConnection();
        
        console.log('🌐 Monitor de conexão inicializado');
    }
    
    createElements() {
        // Banner Offline - DISCRETO no topo
        this.offlineBanner = document.createElement('div');
        this.offlineBanner.id = 'offline-banner';
        this.offlineBanner.innerHTML = `
            <span>⚠️ Sem conexão com a internet</span>
        `;
        document.body.prepend(this.offlineBanner);
        
        // Banner Online removido - não mostrar mais reconexão
        
        // Status Badge - DISCRETO no header (substitui ícone flutuante)
        this.statusIndicator = document.createElement('div');
        this.statusIndicator.id = 'connection-status';
        this.statusIndicator.className = 'online';
        this.statusIndicator.innerHTML = '<span class="status-dot"></span><span class="status-text">Online</span>';
        document.body.appendChild(this.statusIndicator);
    }
    
    async checkConnection() {
        try {
            // Usa endpoint simples que não recalcula nada
            // Apenas verifica se backend responde
            const response = await fetch('/static/manifest.json', {
                method: 'GET',
                cache: 'no-cache',
                signal: AbortSignal.timeout(3000) // Timeout de 3s
            });
            
            this.isOnline = response.ok;
        } catch (error) {
            // Qualquer erro = offline
            this.isOnline = false;
        }
        
        // Se estado mudou, atualiza UI
        if (this.isOnline !== this.previousState) {
            if (this.isOnline) {
                this.handleOnline();
            } else {
                this.handleOffline();
            }
        }
        
        this.previousState = this.isOnline;
    }
    
    handleOffline() {
        console.warn('⚠️ Conexão perdida');
        
        // Atualiza indicador
        this.statusIndicator.className = 'offline';
        this.statusIndicator.innerHTML = '<span class="status-dot"></span><span class="status-text">Offline</span>';
        
        // Mostra banner offline
        this.offlineBanner.classList.add('show');
        
        this.isOnline = false;
        this.previousState = false;
    }
    
    handleOnline() {
        // Conexão restabelecida silenciosamente
        
        // Atualiza indicador
        this.statusIndicator.className = 'online';
        this.statusIndicator.innerHTML = '<span class="status-dot"></span><span class="status-text">Online</span>';
        
        // Esconde banner offline
        this.offlineBanner.classList.remove('show');
        
        // Banner online removido - não mostrar mais
        
        this.isOnline = true;
        this.previousState = true;
        
        // NÃO recarrega dashboard - deixa o usuário decidir
    }
    
    startPeriodicCheck() {
        // Checa conexão a cada 30 segundos (aumentado para evitar spam)
        this.checkInterval = setInterval(() => {
            this.checkConnection();
        }, 30000);
    }
    
    // REMOVIDO: showStatusInfo() - não é mais necessário
    
    destroy() {
        // Limpa recursos
        if (this.checkInterval) {
            clearInterval(this.checkInterval);
        }
        
        window.removeEventListener('online', this.handleOnline);
        window.removeEventListener('offline', this.handleOffline);
        
        this.offlineBanner?.remove();
        this.onlineBanner?.remove();
        this.statusIndicator?.remove();
        
        console.log('🌐 Monitor de conexão destruído');
    }
}

// ==========================================
// 🚀 INICIALIZAÇÃO AUTOMÁTICA
// ==========================================
// Inicia monitor quando DOM estiver pronto

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.connectionMonitor = new ConnectionMonitor();
    });
} else {
    window.connectionMonitor = new ConnectionMonitor();
}

// Exporta para uso global
window.ConnectionMonitor = ConnectionMonitor;
