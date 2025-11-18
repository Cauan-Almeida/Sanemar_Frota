/**
 * Dashboard Real-Time Updates usando Firebase onSnapshot
 * Atualiza automaticamente quando há mudanças no Firestore
 */

// Aguarda o Firebase estar pronto
function waitForFirebase() {
    return new Promise((resolve) => {
        if (window.firestoreDb && window.firestoreModules) {
            resolve();
        } else {
            const interval = setInterval(() => {
                if (window.firestoreDb && window.firestoreModules) {
                    clearInterval(interval);
                    resolve();
                }
            }, 100);
        }
    });
}

// Variáveis globais para unsubscribe
let unsubscribeSaidas = null;
let unsubscribeMotoristas = null;
let unsubscribeVeiculos = null;

/**
 * Inicia os listeners em tempo real
 */
async function initRealtimeListeners() {
    await waitForFirebase();
    
    const db = window.firestoreDb;
    const { collection, onSnapshot, query, orderBy, limit, where } = window.firestoreModules;

    console.log('🔴 Iniciando listeners em tempo real...');

    // 1. Listener APENAS para Veículos EM CURSO (otimizado - 5-10 docs)
    // ✅ AGORA TAMBÉM ATUALIZA O DASHBOARD automaticamente quando há mudanças
    try {
        const saidasQuery = query(
            collection(db, 'saidas'),
            where('status', '==', 'em_curso')  // ✅ APENAS em curso (5-10 docs)
        );

        let isFirstSnapshot = true; // Ignora o snapshot inicial (carga da página)

        unsubscribeSaidas = onSnapshot(saidasQuery, async (snapshot) => {
            console.log('📊 Atualização em veículos EM CURSO:', snapshot.docChanges().length, 'mudanças');
            
            // Atualiza contador de veículos em curso
            const statEmCurso = document.getElementById('stat-viagens-em-curso');
            if (statEmCurso) {
                statEmCurso.textContent = snapshot.size;
            }

            // Verifica se houve MUDANÇAS (não apenas leitura inicial)
            let houveNovaOuChegada = false;

            snapshot.docChanges().forEach((change) => {
                const data = change.doc.data();
                
                if (change.type === 'added' && !isFirstSnapshot) {
                    // Nova saída registrada
                    houveNovaOuChegada = true;
                    if (window.showToast) {
                        showToast('info', `Nova saída: ${data.veiculo} - ${data.motorista}`, 3000);
                    }
                } else if (change.type === 'removed') {
                    // Chegada registrada (removido de em_curso)
                    houveNovaOuChegada = true;
                    if (window.showToast) {
                        showToast('success', `Chegada registrada: ${data.veiculo}`, 3000);
                    }
                }
            });

            // ✅ ATUALIZA O DASHBOARD automaticamente se houve nova saída/chegada
            if (houveNovaOuChegada) {
                console.log('🔄 Atualizando dashboard automaticamente...');
                
                // Limpa o cache no backend
                try {
                    await fetch('/api/dashboard_cache/clear', { method: 'POST' });
                    
                    // Recarrega os dados do dashboard
                    if (window.viagensChartsInitialized && typeof loadDashboardData === 'function') {
                        await loadDashboardData(
                            window.viagensPorVeiculoChartInstance,
                            window.viagensPorMotoristaChartInstance,
                            window.viagensPorVeiculoChartTotalInstance,
                            window.viagensPorMotoristaChartTotalInstance
                        );
                    }
                    
                    // DESABILITADO: Recarregar histórico causa bugs nas tabs
                    // O histórico já é carregado no DOMContentLoaded
                    // if (typeof loadHistoricoData === 'function') {
                    //     await loadHistoricoData();
                    // }
                    
                    console.log('✅ Dashboard atualizado automaticamente!');
                } catch (error) {
                    console.error('❌ Erro ao atualizar dashboard:', error);
                }
            }

            isFirstSnapshot = false; // Marca que o primeiro snapshot já passou
        }, (error) => {
            console.error('❌ Erro no listener de saidas:', error);
        });

        console.log('✅ Listener de veículos em curso ativo (com auto-atualização do dashboard)');
    } catch (error) {
        console.error('❌ Erro ao criar listener de saidas:', error);
    }

    // 2. DESABILITADO: Listener para HISTÓRICO (causava loop infinito de recálculos)
    // O histórico é carregado manualmente via /api/historico quando necessário
    // Atualizar em tempo real aqui forçava recálculo constante do dashboard
    console.log('ℹ️ Listener de histórico desabilitado (otimização - evita loop)');

    // 3. DESABILITADO: Listener de HOJE (causava queries desnecessárias no Firestore)
    // O card HOJE é atualizado automaticamente quando o cache expira (5 min)
    // ou quando o usuário registra nova saída/chegada (cache invalidado)
    console.log('ℹ️ Listener de viagens HOJE desabilitado (economia de leituras)');

    // 3. DESABILITADO - Listener para Motoristas (não é necessário em tempo real)
    // Motoristas são carregados sob demanda quando o usuário abre a página
    console.log('ℹ️ Listener de motoristas desabilitado (otimização)');

    // 3. DESABILITADO - Listener para Veículos (não é necessário em tempo real)
    // Veículos são carregados sob demanda quando o usuário abre a página
    console.log('ℹ️ Listener de veículos desabilitado (otimização)');

    // Indicador visual de que o tempo real está ativo
    createRealtimeIndicator();
}

/**
 * Para todos os listeners (útil para cleanup)
 */
function stopRealtimeListeners() {
    if (unsubscribeSaidas) {
        unsubscribeSaidas();
        unsubscribeSaidas = null;
        console.log('🔴 Listener de saídas desativado');
    }
    if (unsubscribeMotoristas) {
        unsubscribeMotoristas();
        unsubscribeMotoristas = null;
        console.log('🔴 Listener de motoristas desativado');
    }
    if (unsubscribeVeiculos) {
        unsubscribeVeiculos();
        unsubscribeVeiculos = null;
        console.log('🔴 Listener de veículos desativado');
    }
}

/**
 * Cria um indicador visual de que o tempo real está ativo
 */
function createRealtimeIndicator() {
    // Remove indicador anterior se existir
    const existing = document.getElementById('realtime-indicator');
    if (existing) existing.remove();

    const indicator = document.createElement('div');
    indicator.id = 'realtime-indicator';
    indicator.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: #10b981;
        color: white;
        padding: 8px 16px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        display: flex;
        align-items: center;
        gap: 8px;
        z-index: 1000;
        animation: fadeIn 0.3s ease-in;
    `;

    // Pulsating dot
    const dot = document.createElement('span');
    dot.style.cssText = `
        width: 8px;
        height: 8px;
        background: white;
        border-radius: 50%;
        display: inline-block;
        animation: pulse 2s ease-in-out infinite;
    `;

    indicator.appendChild(dot);
    indicator.appendChild(document.createTextNode('Tempo Real Ativo'));

    // Adiciona CSS da animação
    if (!document.getElementById('realtime-animations')) {
        const style = document.createElement('style');
        style.id = 'realtime-animations';
        style.textContent = `
            @keyframes pulse {
                0%, 100% { opacity: 1; transform: scale(1); }
                50% { opacity: 0.5; transform: scale(0.8); }
            }
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }
        `;
        document.head.appendChild(style);
    }

    document.body.appendChild(indicator);

    // Remove após 5 segundos
    setTimeout(() => {
        indicator.style.animation = 'fadeOut 0.3s ease-out';
        setTimeout(() => indicator.remove(), 300);
    }, 5000);
}

// Cleanup ao sair da página
window.addEventListener('beforeunload', () => {
    stopRealtimeListeners();
});

// Inicia os listeners quando o DOM estiver pronto e o Firebase inicializado
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        // Aguarda um pouco para garantir que o dashboard.js já inicializou
        setTimeout(initRealtimeListeners, 1000);
    });
} else {
    setTimeout(initRealtimeListeners, 1000);
}

// Exporta para uso global
window.initRealtimeListeners = initRealtimeListeners;
window.stopRealtimeListeners = stopRealtimeListeners;
