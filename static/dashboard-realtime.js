/**
 * Dashboard Real-Time Updates usando Firebase onSnapshot
 * Atualiza automaticamente quando há mudanças no Firestore
 * ⚠️ PROTEÇÃO: Desliga listeners após 5min de inatividade para economizar quota
 */

// Controle de inatividade
let lastActivityTime = Date.now();
let inactivityCheckInterval = null;
const INACTIVITY_TIMEOUT = 5 * 60 * 1000; // 5 minutos
let listenersActive = false;

// Atualiza timestamp de atividade
function updateActivity() {
    lastActivityTime = Date.now();
    if (!listenersActive) {
        console.log('🔄 Usuário ativo - reativando listeners...');
        initRealtimeListeners();
    }
}

// Monitora atividade do usuário
function startActivityMonitor() {
    // Eventos gerais
    ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'].forEach(event => {
        document.addEventListener(event, updateActivity, { passive: true });
    });
    
    // ✅ Eventos específicos para formulários (reativa instantâneo ao focar input)
    ['focus', 'input', 'change'].forEach(event => {
        document.addEventListener(event, updateActivity, true); // useCapture=true para pegar em inputs
    });
    
    console.log('👁️ Monitor de atividade iniciado');
}

// Verifica inatividade a cada 1 minuto
function checkInactivity() {
    const inactiveTime = Date.now() - lastActivityTime;
    if (inactiveTime > INACTIVITY_TIMEOUT && listenersActive) {
        console.warn('⚠️ Inatividade detectada - desligando listeners Firebase para economizar quota');
        stopRealtimeListeners();
    }
}

// Para todos os listeners
function stopRealtimeListeners() {
    if (unsubscribeSaidas) {
        unsubscribeSaidas();
        unsubscribeSaidas = null;
    }
    if (unsubscribeHistorico) {
        unsubscribeHistorico();
        unsubscribeHistorico = null;
    }
    if (unsubscribeMotoristas) {
        unsubscribeMotoristas();
        unsubscribeMotoristas = null;
    }
    if (unsubscribeVeiculos) {
        unsubscribeVeiculos();
        unsubscribeVeiculos = null;
    }
    listenersActive = false;
    console.log('🔴 Listeners desligados');
}

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
let unsubscribeHistorico = null;
let unsubscribeMotoristas = null;
let unsubscribeVeiculos = null;

/**
 * Inicia os listeners em tempo real
 */
async function initRealtimeListeners() {
    await waitForFirebase();
    
    const db = window.firestoreDb;
    const { collection, onSnapshot, query, orderBy, limit, where } = window.firestoreModules;

    // Se já estão ativos, não recria
    if (listenersActive) {
        console.log('➡️ Listeners já estão ativos');
        return;
    }

    console.log('🔴 Iniciando listeners em tempo real...');
    listenersActive = true;

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
            
            // ✅ SEMPRE atualiza o contador (mesmo no primeiro snapshot)
            const statEmCurso = document.getElementById('stat-viagens-em-curso');
            if (statEmCurso) {
                statEmCurso.textContent = snapshot.size;
                console.log(`✅ Contador EM CURSO atualizado: ${snapshot.size}`);
            } else {
                console.error('❌ Elemento stat-viagens-em-curso não encontrado!');
            }

            // Verifica se houve MUDANÇAS (não apenas leitura inicial)
            let houveNovaOuChegada = false;

            snapshot.docChanges().forEach((change) => {
                const data = change.doc.data();
                
                if (change.type === 'added' && !isFirstSnapshot) {
                    // Nova saída registrada
                    houveNovaOuChegada = true;
                    if (window.showToast) {
                        showToast('info', `Nova saída: ${data.veiculo} - ${data.motorista}`);
                    }
                } else if (change.type === 'removed') {
                    // Chegada registrada (removido de em_curso)
                    houveNovaOuChegada = true;
                    if (window.showToast) {
                        showToast('success', `Chegada registrada: ${data.veiculo}`);
                    }
                }
            });

            // ✅ ATUALIZA O DASHBOARD automaticamente se houve nova saída/chegada
            if (houveNovaOuChegada) {
                console.log('🔄 Atualizando dashboard automaticamente...');
                
                try {
                    // ✅ LIMPA O CACHE IMEDIATAMENTE (força atualização)
                    await fetch('/api/dashboard_cache/clear', { method: 'POST' });
                    
                    // ✅ PEQUENO DELAY para dar tempo do backend processar
                    await new Promise(resolve => setTimeout(resolve, 500));
                    
                    // Recarrega os dados do dashboard (gráficos e cards)
                    if (window.viagensChartsInitialized && typeof loadDashboardData === 'function') {
                        await loadDashboardData(
                            window.viagensPorVeiculoChartInstance,
                            window.viagensPorMotoristaChartInstance,
                            window.viagensPorVeiculoChartTotalInstance,
                            window.viagensPorMotoristaChartTotalInstance
                        );
                    }
                    
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

    // 2. Listener para HISTÓRICO (APENAS do mês visível na tela)
    try {
        // ✅ Listener dinâmico - recria quando o mês muda
        window.recriarListenerHistorico = () => {
            // Limpa listener antigo
            if (unsubscribeHistorico) {
                unsubscribeHistorico();
            }
            
            // Pega mês/ano visíveis na tela
            const dashboardFiltroMes = document.getElementById('dashboard-filtro-mes');
            const dashboardFiltroAno = document.getElementById('dashboard-filtro-ano');
            
            if (!dashboardFiltroMes || !dashboardFiltroAno) {
                console.log('⚠️ Filtros de mês não encontrados, listener de histórico não criado');
                return;
            }
            
            const mes = parseInt(dashboardFiltroMes.value) || new Date().getMonth() + 1;
            const ano = parseInt(dashboardFiltroAno.value) || new Date().getFullYear();
            
            // Calcula período do mês
            const startDate = new Date(ano, mes - 1, 1); // Primeiro dia do mês
            const endDate = new Date(ano, mes, 0, 23, 59, 59); // Último dia do mês
            
            console.log(`🔍 Criando listener para histórico de ${mes}/${ano}`);
            
            const historicoQuery = query(
                collection(db, 'saidas'),
                where('timestampSaida', '>=', startDate),
                where('timestampSaida', '<=', endDate),
                orderBy('timestampSaida', 'desc')
            );

            let isFirstHistoricoSnapshot = true;

            unsubscribeHistorico = onSnapshot(historicoQuery, async (snapshot) => {
                const changes = snapshot.docChanges();
                console.log(`📋 [HISTÓRICO ${mes}/${ano}] ${changes.length} mudanças detectadas`);
                
                // Ignora o snapshot inicial (primeira carga)
                if (isFirstHistoricoSnapshot) {
                    isFirstHistoricoSnapshot = false;
                    console.log(`📊 Histórico inicial: ${snapshot.size} registros`);
                    return;
                }

                // Log detalhado
                let houveAlteracao = false;
                changes.forEach(change => {
                    const veiculo = change.doc.data().veiculo;
                    if (change.type === 'added') {
                        console.log(`➕ Nova saída (${mes}/${ano}): ${veiculo}`);
                        houveAlteracao = true;
                    } else if (change.type === 'modified') {
                        console.log(`✏️ Editado (${mes}/${ano}): ${veiculo}`);
                        houveAlteracao = true;
                    } else if (change.type === 'removed') {
                        console.log(`🗑️ Removido (${mes}/${ano}): ${veiculo}`);
                        houveAlteracao = true;
                    }
                });

                // Recarrega histórico
                if (houveAlteracao) {
                    console.log('🔄 Recarregando histórico...');
                    if (typeof loadHistoricoData === 'function') {
                        try {
                            await loadHistoricoData();
                            console.log('✅ Histórico atualizado!');
                        } catch (err) {
                            console.error('❌ Erro loadHistoricoData:', err);
                        }
                    } else {
                        console.error('❌ loadHistoricoData NÃO EXISTE!');
                    }
                }
            }, (error) => {
                console.error('❌ Erro listener histórico:', error);
            });

            console.log(`✅ Listener de histórico ATIVO (${mes}/${ano})`);
        };
        
        // Cria o listener inicial
        window.recriarListenerHistorico();
        
    } catch (error) {
        console.error('❌ Erro ao criar listener de histórico:', error);
    }

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
    
    // ⚠️ Inicia monitoramento de inatividade
    if (!inactivityCheckInterval) {
        startActivityMonitor();
        inactivityCheckInterval = setInterval(checkInactivity, 60000); // Verifica a cada 1 minuto
        console.log('👁️ Monitor de inatividade ativado (5min timeout)');
    }
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
    if (unsubscribeHistorico) {
        unsubscribeHistorico();
        unsubscribeHistorico = null;
        console.log('🔴 Listener de histórico desativado');
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
