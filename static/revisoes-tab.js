// ========================================
// REVISÕES - Gestão de Manutenção Periódica
// ========================================

let revisaoEditandoId = null;

async function loadRevisoesData(filtroPlaca = '', filtroStatus = '') {
    try {
        let url = '/api/revisoes?';
        const params = [];
        if (filtroPlaca) params.push(`placa=${encodeURIComponent(filtroPlaca)}`);
        if (filtroStatus) params.push(`status=${encodeURIComponent(filtroStatus)}`);
        url += params.join('&');
        
        const response = await fetch(url);
        const revisoes = await response.json();
        const tbody = document.getElementById('tabela-revisoes');
        
        if (!tbody) return;
        
        tbody.innerHTML = '';
        
        if (!revisoes || revisoes.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="p-4 text-center text-gray-500">Nenhuma revisão registrada</td></tr>';
            updateRevisoesStats([]); // Atualiza stats com array vazio
            return;
        }
        
        // Atualiza estatísticas
        updateRevisoesStats(revisoes);
        
        revisoes.forEach(revisao => {
            const tr = document.createElement('tr');
            tr.className = 'border-b border-gray-100 hover:bg-purple-50 transition-colors';
            
            // Status badge
            let statusClass = 'bg-green-100 text-green-800';
            let statusText = 'Em dia';
            let statusIcon = '✅';
            
            if (revisao.status === 'atrasada') {
                statusClass = 'bg-red-100 text-red-800';
                statusText = 'Atrasada';
                statusIcon = '🚨';
            } else if (revisao.status === 'proxima') {
                statusClass = 'bg-yellow-100 text-yellow-800';
                statusText = 'Próxima';
                statusIcon = '⚠️';
            }
            
            // Formatar KM restante
            let kmRestanteText = '-';
            if (revisao.km_restante !== undefined) {
                if (revisao.km_restante < 0) {
                    kmRestanteText = `<span class="text-red-600 font-bold">${Math.abs(revisao.km_restante).toLocaleString('pt-BR')} km atrasado</span>`;
                } else {
                    kmRestanteText = `${revisao.km_restante.toLocaleString('pt-BR')} km`;
                }
            }
            
            tr.innerHTML = `
                <td class="p-4">
                    <span class="px-3 py-1 rounded-full text-xs font-semibold ${statusClass}">${statusIcon} ${statusText}</span>
                </td>
                <td class="p-4 font-bold text-gray-900">${revisao.placa || '-'}</td>
                <td class="p-4 text-gray-700">${revisao.tipo_revisao || '-'}</td>
                <td class="p-4 text-gray-700">${revisao.km_revisao ? revisao.km_revisao.toLocaleString('pt-BR') : '-'}</td>
                <td class="p-4 text-gray-700">${revisao.data_revisao ? formatDateShortRevisoes(revisao.data_revisao) : '-'}</td>
                <td class="p-4 font-semibold text-purple-600">${revisao.km_proxima_revisao ? revisao.km_proxima_revisao.toLocaleString('pt-BR') : '-'}</td>
                <td class="p-4 text-sm">${kmRestanteText}</td>
                <td class="p-4">
                    <div class="flex gap-2">
                        <button onclick="editarRevisao('${revisao.id}')" class="px-3 py-1 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm font-semibold transition-all">
                            ✏️
                        </button>
                        <button onclick="deletarRevisao('${revisao.id}', '${revisao.placa}')" class="px-3 py-1 bg-red-500 hover:bg-red-600 text-white rounded-lg text-sm font-semibold transition-all">
                            🗑️
                        </button>
                    </div>
                </td>
            `;
            
            tbody.appendChild(tr);
        });
    } catch (error) {
        console.error('Erro ao carregar revisões:', error);
        const tbody = document.getElementById('tabela-revisoes');
        if (tbody) {
            tbody.innerHTML = '<tr><td colspan="8" class="p-4 text-center text-red-500">Erro ao carregar dados</td></tr>';
        }
    }
}

function updateRevisoesStats(revisoes) {
    const total = revisoes.length;
    const emDia = revisoes.filter(r => r.status === 'em_dia').length;
    const proximas = revisoes.filter(r => r.status === 'proxima').length;
    const atrasadas = revisoes.filter(r => r.status === 'atrasada').length;
    
    const statTotal = document.getElementById('stat-revisoes-total');
    const statEmDia = document.getElementById('stat-revisoes-em-dia');
    const statProximas = document.getElementById('stat-revisoes-proximas');
    const statAtrasadas = document.getElementById('stat-revisoes-atrasadas');
    
    if (statTotal) statTotal.textContent = total;
    if (statEmDia) statEmDia.textContent = emDia;
    if (statProximas) statProximas.textContent = proximas;
    if (statAtrasadas) statAtrasadas.textContent = atrasadas;
}

function formatDateShortRevisoes(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    const day = String(date.getDate()).padStart(2, '0');
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const year = date.getFullYear();
    return `${day}/${month}/${year}`;
}

async function editarRevisao(id) {
    try {
        const response = await fetch('/api/revisoes');
        const revisoes = await response.json();
        const revisao = revisoes.find(r => r.id === id);
        
        if (!revisao) {
            if (window.showToast) showToast('error', 'Revisão não encontrada');
            return;
        }
        
        // Preenche o formulário
        document.getElementById('revisao-id').value = id;
        document.getElementById('revisao-placa').value = revisao.placa || '';
        document.getElementById('revisao-tipo').value = revisao.tipo_revisao || '';
        document.getElementById('revisao-km').value = revisao.km_revisao || '';
        document.getElementById('revisao-data').value = revisao.data_revisao ? revisao.data_revisao.split('T')[0] : '';
        document.getElementById('revisao-km-proxima').value = revisao.km_proxima_revisao || '';
        document.getElementById('revisao-data-proxima').value = revisao.data_proxima_prevista ? revisao.data_proxima_prevista.split('T')[0] : '';
        document.getElementById('revisao-oficina').value = revisao.oficina || '';
        document.getElementById('revisao-valor').value = revisao.valor || '';
        document.getElementById('revisao-observacao').value = revisao.observacao || '';
        
        // Mostra botão cancelar
        document.getElementById('revisao-cancelar').classList.remove('hidden');
        
        // Muda texto do botão submit
        const submitBtn = document.querySelector('#form-revisao button[type="submit"]');
        if (submitBtn) submitBtn.innerHTML = '💾 Atualizar Revisão';
        
        // Scroll para o formulário
        document.getElementById('form-revisao').scrollIntoView({ behavior: 'smooth' });
        
        revisaoEditandoId = id;
    } catch (error) {
        console.error('Erro ao carregar revisão para edição:', error);
        if (window.showToast) showToast('error', 'Erro ao carregar revisão');
    }
}

async function deletarRevisao(id, placa) {
    if (!confirm(`Confirma a exclusão da revisão do veículo ${placa}?`)) return;
    
    try {
        const response = await fetch(`/api/revisoes/${id}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (response.ok) {
            if (window.showToast) showToast('success', 'Revisão deletada com sucesso');
            loadRevisoesData(
                document.getElementById('revisao-filtro-placa').value,
                document.getElementById('revisao-filtro-status').value
            );
        } else {
            if (window.showToast) showToast('error', result.error || 'Erro ao deletar');
        }
    } catch (error) {
        console.error('Erro ao deletar revisão:', error);
        if (window.showToast) showToast('error', 'Erro de conexão');
    }
}

function cancelarEdicaoRevisao() {
    document.getElementById('form-revisao').reset();
    document.getElementById('revisao-id').value = '';
    document.getElementById('revisao-cancelar').classList.add('hidden');
    const submitBtn = document.querySelector('#form-revisao button[type="submit"]');
    if (submitBtn) submitBtn.innerHTML = '➕ Salvar Revisão';
    revisaoEditandoId = null;
}

// Calcular KM próxima revisão automaticamente
function calcularProximaRevisao() {
    const kmRevisaoInput = document.getElementById('revisao-km');
    const tipoRevisaoInput = document.getElementById('revisao-tipo');
    const kmProximaInput = document.getElementById('revisao-km-proxima');
    
    if (!kmRevisaoInput || !tipoRevisaoInput || !kmProximaInput) return;
    
    const kmRevisao = parseInt(kmRevisaoInput.value) || 0;
    const tipoRevisao = tipoRevisaoInput.value.toLowerCase();
    
    // Intervalos padrão
    let intervalo = 10000; // Padrão 10.000 km
    
    if (tipoRevisao.includes('5000') || tipoRevisao.includes('5.000')) {
        intervalo = 5000;
    } else if (tipoRevisao.includes('10000') || tipoRevisao.includes('10.000')) {
        intervalo = 10000;
    } else if (tipoRevisao.includes('20000') || tipoRevisao.includes('20.000')) {
        intervalo = 20000;
    } else if (tipoRevisao.includes('30000') || tipoRevisao.includes('30.000')) {
        intervalo = 30000;
    } else if (tipoRevisao.includes('40000') || tipoRevisao.includes('40.000')) {
        intervalo = 40000;
    } else if (tipoRevisao.includes('50000') || tipoRevisao.includes('50.000')) {
        intervalo = 50000;
    }
    
    // Calcular próxima revisão
    if (kmRevisao > 0) {
        kmProximaInput.value = kmRevisao + intervalo;
    }
}

// ========================================
// INICIALIZAÇÃO
// ========================================

document.addEventListener('DOMContentLoaded', () => {
    // Form Revisão
    const formRevisao = document.getElementById('form-revisao');
    if (formRevisao) {
        formRevisao.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const id = document.getElementById('revisao-id').value;
            const placa = document.getElementById('revisao-placa').value.trim().toUpperCase();
            const tipoRevisao = document.getElementById('revisao-tipo').value.trim();
            const kmRevisao = document.getElementById('revisao-km').value;
            const dataRevisao = document.getElementById('revisao-data').value;
            const kmProxima = document.getElementById('revisao-km-proxima').value;
            const dataProxima = document.getElementById('revisao-data-proxima').value;
            const oficina = document.getElementById('revisao-oficina').value.trim();
            const valor = document.getElementById('revisao-valor').value;
            const observacao = document.getElementById('revisao-observacao').value.trim();
            
            if (!placa || !tipoRevisao || !kmRevisao || !dataRevisao || !kmProxima) {
                if (window.showToast) showToast('error', 'Preencha os campos obrigatórios');
                return;
            }
            
            const data = {
                placa,
                tipo_revisao: tipoRevisao,
                km_revisao: parseInt(kmRevisao),
                data_revisao: new Date(dataRevisao + 'T00:00:00').toISOString(),
                km_proxima_revisao: parseInt(kmProxima),
                data_proxima_prevista: dataProxima ? new Date(dataProxima + 'T00:00:00').toISOString() : null,
                oficina,
                valor: valor ? parseFloat(valor) : null,
                observacao
            };
            
            try {
                let response;
                if (id) {
                    // Atualizar
                    response = await fetch(`/api/revisoes/${id}`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(data)
                    });
                } else {
                    // Criar
                    response = await fetch('/api/revisoes', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(data)
                    });
                }
                
                const result = await response.json();
                
                if (response.ok) {
                    if (window.showToast) showToast('success', result.message);
                    cancelarEdicaoRevisao();
                    loadRevisoesData(
                        document.getElementById('revisao-filtro-placa').value,
                        document.getElementById('revisao-filtro-status').value
                    );
                } else {
                    if (window.showToast) showToast('error', result.error || 'Erro ao salvar');
                }
            } catch (error) {
                console.error('Erro ao salvar revisão:', error);
                if (window.showToast) showToast('error', 'Erro de conexão');
            }
        });
    }
    
    // Botão cancelar revisão
    const btnCancelarRevisao = document.getElementById('revisao-cancelar');
    if (btnCancelarRevisao) {
        btnCancelarRevisao.addEventListener('click', cancelarEdicaoRevisao);
    }
    
    // Filtros de revisão
    const filtroPlacaRevisao = document.getElementById('revisao-filtro-placa');
    const filtroStatusRevisao = document.getElementById('revisao-filtro-status');
    
    if (filtroPlacaRevisao) {
        filtroPlacaRevisao.addEventListener('change', () => {
            loadRevisoesData(filtroPlacaRevisao.value, filtroStatusRevisao.value);
        });
    }
    
    if (filtroStatusRevisao) {
        filtroStatusRevisao.addEventListener('change', () => {
            loadRevisoesData(filtroPlacaRevisao.value, filtroStatusRevisao.value);
        });
    }
    
    // Botão limpar filtros revisão
    const btnLimparFiltrosRevisao = document.getElementById('revisao-limpar-filtros');
    if (btnLimparFiltrosRevisao) {
        btnLimparFiltrosRevisao.addEventListener('click', () => {
            if (filtroPlacaRevisao) filtroPlacaRevisao.value = '';
            if (filtroStatusRevisao) filtroStatusRevisao.value = '';
            loadRevisoesData('', '');
        });
    }
    
    // Auto-calcular próxima revisão
    const revisaoKmInput = document.getElementById('revisao-km');
    const revisaoTipoInput = document.getElementById('revisao-tipo');
    
    if (revisaoKmInput) {
        revisaoKmInput.addEventListener('blur', calcularProximaRevisao);
    }
    
    if (revisaoTipoInput) {
        revisaoTipoInput.addEventListener('blur', calcularProximaRevisao);
    }
    
    // Uppercase automático na placa
    const revisaoPlacaInput = document.getElementById('revisao-placa');
    if (revisaoPlacaInput) {
        revisaoPlacaInput.addEventListener('input', (e) => {
            const pos = e.target.selectionStart;
            e.target.value = e.target.value.toUpperCase();
            try { e.target.setSelectionRange(pos, pos); } catch (err) { /* ignore */ }
        });
    }
});

// Expor funções globalmente
window.loadRevisoesData = loadRevisoesData;
window.editarRevisao = editarRevisao;
window.deletarRevisao = deletarRevisao;
window.cancelarEdicaoRevisao = cancelarEdicaoRevisao;
