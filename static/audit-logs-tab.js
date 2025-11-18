// ==========================================
// 🔍 GERENCIAMENTO DE LOGS DE AUDITORIA
// ==========================================

/**
 * Carrega logs de auditoria com filtros aplicados
 */
async function loadAuditLogs() {
    const tabelaBody = document.getElementById('tabela-audit-logs');
    if (!tabelaBody) return;

    // Mostra carregando
    tabelaBody.innerHTML = '<tr><td colspan="6" class="p-4 text-center text-gray-500">🔄 Carregando logs...</td></tr>';

    try {
        // Pega filtros
        const userFilter = document.getElementById('audit-filter-user')?.value.trim() || '';
        const actionFilter = document.getElementById('audit-filter-action')?.value || '';
        const collectionFilter = document.getElementById('audit-filter-collection')?.value || '';

        // Monta query string
        const params = new URLSearchParams();
        if (userFilter) params.append('user', userFilter);
        if (actionFilter) params.append('action', actionFilter);
        if (collectionFilter) params.append('collection', collectionFilter);
        params.append('limit', '50'); // Últimos 50 logs para economizar quota

        const response = await fetch(`/api/audit-logs?${params.toString()}`);
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Erro ao carregar logs');
        }

        const logs = await response.json();

        if (logs.length === 0) {
            tabelaBody.innerHTML = '<tr><td colspan="6" class="p-4 text-center text-gray-500">Nenhum log encontrado com os filtros aplicados.</td></tr>';
            return;
        }

        // Renderiza logs
        tabelaBody.innerHTML = logs.map(log => {
            const timestamp = log.timestamp ? formatTimestamp(log.timestamp) : 'N/A';
            const user = log.user || 'Sistema';
            const action = getActionBadge(log.action);
            const collection = log.collection || 'N/A';
            const docId = log.document_id || 'N/A';
            const details = formatLogDetails(log);

            return `
                <tr class="border-b border-gray-100 hover:bg-blue-50 transition-all">
                    <td class="p-4 text-sm text-gray-700">
                        ${timestamp}
                    </td>
                    <td class="p-4">
                        <span class="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-sm font-semibold">
                            👤 ${user}
                        </span>
                    </td>
                    <td class="p-4">
                        ${action}
                    </td>
                    <td class="p-4">
                        <span class="px-3 py-1 bg-indigo-100 text-indigo-700 rounded-full text-sm font-semibold">
                            📂 ${collection}
                        </span>
                    </td>
                    <td class="p-4 text-sm text-gray-600 font-mono">
                        ${docId.substring(0, 12)}...
                    </td>
                    <td class="p-4">
                        <button onclick='showLogDetails(${JSON.stringify(log).replace(/'/g, "&apos;")})' 
                                class="text-blue-600 hover:text-blue-800 font-semibold text-sm">
                            Ver Detalhes →
                        </button>
                    </td>
                </tr>
            `;
        }).join('');

    } catch (error) {
        console.error('Erro ao carregar logs:', error);
        tabelaBody.innerHTML = `<tr><td colspan="6" class="p-4 text-center text-red-600">❌ ${error.message}</td></tr>`;
    }
}

/**
 * Retorna badge HTML para cada tipo de ação
 */
function getActionBadge(action) {
    const badges = {
        'create': '<span class="px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm font-semibold">✅ Criação</span>',
        'update': '<span class="px-3 py-1 bg-yellow-100 text-yellow-700 rounded-full text-sm font-semibold">✏️ Atualização</span>',
        'delete': '<span class="px-3 py-1 bg-red-100 text-red-700 rounded-full text-sm font-semibold">🗑️ Exclusão</span>',
        'deactivate': '<span class="px-3 py-1 bg-orange-100 text-orange-700 rounded-full text-sm font-semibold">🔒 Desativação</span>'
    };
    return badges[action] || `<span class="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-sm font-semibold">${action}</span>`;
}

/**
 * Formata timestamp do Firestore
 */
function formatTimestamp(timestamp) {
    if (!timestamp) return 'N/A';
    
    // Se for string ISO
    if (typeof timestamp === 'string') {
        const date = new Date(timestamp);
        return date.toLocaleString('pt-BR');
    }
    
    // Se for objeto Firestore Timestamp
    if (timestamp._seconds) {
        const date = new Date(timestamp._seconds * 1000);
        return date.toLocaleString('pt-BR');
    }
    
    // Se for timestamp em milissegundos
    if (typeof timestamp === 'number') {
        const date = new Date(timestamp);
        return date.toLocaleString('pt-BR');
    }
    
    return 'N/A';
}

/**
 * Formata os detalhes do log de forma resumida
 */
function formatLogDetails(log) {
    const parts = [];
    
    if (log.old_data) {
        parts.push('Dados Anteriores');
    }
    if (log.new_data) {
        parts.push('Dados Novos');
    }
    
    return parts.join(' → ') || 'Sem detalhes';
}

/**
 * Mostra detalhes completos de um log em modal
 */
function showLogDetails(log) {
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4';
    modal.onclick = (e) => {
        if (e.target === modal) modal.remove();
    };
    
    const content = document.createElement('div');
    content.className = 'bg-white rounded-2xl shadow-2xl max-w-3xl w-full max-h-[80vh] overflow-auto p-8';
    content.onclick = (e) => e.stopPropagation();
    
    content.innerHTML = `
        <div class="flex justify-between items-start mb-6">
            <h2 class="text-2xl font-bold text-gray-800">🔍 Detalhes do Log</h2>
            <button onclick="this.closest('.fixed').remove()" 
                    class="text-gray-500 hover:text-gray-700 text-2xl font-bold">×</button>
        </div>
        
        <div class="space-y-4">
            <div class="bg-blue-50 p-4 rounded-xl">
                <h3 class="font-bold text-blue-900 mb-2">📅 Informações Gerais</h3>
                <div class="grid grid-cols-2 gap-4 text-sm">
                    <div>
                        <span class="font-semibold text-gray-700">Data/Hora:</span>
                        <p class="text-gray-600">${formatTimestamp(log.timestamp)}</p>
                    </div>
                    <div>
                        <span class="font-semibold text-gray-700">Usuário:</span>
                        <p class="text-gray-600">${log.user || 'Sistema'}</p>
                    </div>
                    <div>
                        <span class="font-semibold text-gray-700">Ação:</span>
                        <p class="text-gray-600">${log.action}</p>
                    </div>
                    <div>
                        <span class="font-semibold text-gray-700">Coleção:</span>
                        <p class="text-gray-600">${log.collection}</p>
                    </div>
                    <div class="col-span-2">
                        <span class="font-semibold text-gray-700">ID do Documento:</span>
                        <p class="text-gray-600 font-mono text-xs">${log.document_id || 'N/A'}</p>
                    </div>
                </div>
            </div>
            
            ${log.old_data ? `
            <div class="bg-red-50 p-4 rounded-xl">
                <h3 class="font-bold text-red-900 mb-2">📋 Dados Anteriores</h3>
                <pre class="bg-white p-3 rounded-lg text-xs overflow-auto max-h-64">${JSON.stringify(log.old_data, null, 2)}</pre>
            </div>
            ` : ''}
            
            ${log.new_data ? `
            <div class="bg-green-50 p-4 rounded-xl">
                <h3 class="font-bold text-green-900 mb-2">📋 Dados Novos</h3>
                <pre class="bg-white p-3 rounded-lg text-xs overflow-auto max-h-64">${JSON.stringify(log.new_data, null, 2)}</pre>
            </div>
            ` : ''}
            
            ${!log.old_data && !log.new_data ? `
            <div class="bg-gray-50 p-4 rounded-xl text-center">
                <p class="text-gray-500">Nenhum detalhe adicional disponível</p>
            </div>
            ` : ''}
        </div>
        
        <div class="mt-6 flex justify-end">
            <button onclick="this.closest('.fixed').remove()" 
                    class="px-6 py-3 bg-gray-300 hover:bg-gray-400 rounded-xl font-bold transition-all">
                Fechar
            </button>
        </div>
    `;
    
    modal.appendChild(content);
    document.body.appendChild(modal);
}

// Auto-carrega logs quando a aba for aberta
document.addEventListener('DOMContentLoaded', () => {
    // Observer para detectar quando a aba de audit logs for aberta
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            if (mutation.target.id === 'audit-logs-content' && !mutation.target.classList.contains('hidden')) {
                loadAuditLogs();
            }
        });
    });
    
    const auditLogsContent = document.getElementById('audit-logs-content');
    if (auditLogsContent) {
        observer.observe(auditLogsContent, { attributes: true, attributeFilter: ['class'] });
    }
});
