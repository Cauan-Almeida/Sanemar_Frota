// ========================================
// KM MENSAL - Gestão de Quilometragem
// ========================================

let kmEditandoId = null;

async function loadKmMensalData(filtroPlaca = '') {
    try {
        let url = '/api/km-mensal';
        if (filtroPlaca) {
            url += `?placa=${encodeURIComponent(filtroPlaca)}`;
        }
        
        const response = await fetch(url);
        const registros = await response.json();
        const tbody = document.getElementById('tabela-km-mensal');
        
        if (!tbody) return;
        
        tbody.innerHTML = '';
        
        if (!registros || registros.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="p-4 text-center text-gray-500">Nenhum registro de KM encontrado</td></tr>';
            return;
        }
        
        // Buscar revisões para adicionar alertas
        let revisoes = [];
        try {
            const revisoesResponse = await fetch('/api/revisoes');
            if (revisoesResponse.ok) {
                revisoes = await revisoesResponse.json();
            }
        } catch (e) {
            console.log('Não foi possível carregar revisões para alertas');
        }
        
        registros.forEach(reg => {
            const tr = document.createElement('tr');
            tr.className = 'border-b border-gray-100 hover:bg-blue-50 transition-colors';
            
            const kmValor = reg.km_valor !== null && reg.km_valor !== undefined ? reg.km_valor : '-';
            const mesAnoFormatado = reg.mes_ano ? formatMesAno(reg.mes_ano) : '-';
            
            // Verificar se há revisão próxima ou atrasada para este veículo
            let alertaRevisao = '';
            const revisoesVeiculo = revisoes.filter(r => r.placa === reg.placa);
            for (const revisao of revisoesVeiculo) {
                if (revisao.status === 'atrasada') {
                    alertaRevisao = '<span class="ml-2 px-2 py-1 bg-red-100 text-red-800 text-xs rounded-full font-semibold">🚨 Revisão Atrasada</span>';
                    break;
                } else if (revisao.status === 'proxima' && !alertaRevisao) {
                    alertaRevisao = '<span class="ml-2 px-2 py-1 bg-yellow-100 text-yellow-800 text-xs rounded-full font-semibold">⚠️ Revisão Próxima</span>';
                }
            }
            
            tr.innerHTML = `
                <td class="p-4 font-bold text-gray-900">${reg.placa || '-'}${alertaRevisao}</td>
                <td class="p-4 text-gray-700">${mesAnoFormatado}</td>
                <td class="p-4 font-semibold text-blue-600">${kmValor !== '-' ? kmValor.toLocaleString('pt-BR') + ' km' : '-'}</td>
                <td class="p-4 text-gray-600 text-sm">${reg.observacao || '-'}</td>
                <td class="p-4">
                    <div class="flex gap-2">
                        <button onclick="editarKm('${reg.id}')" class="px-3 py-1 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm font-semibold transition-all">
                            ✏️ Editar
                        </button>
                        <button onclick="deletarKm('${reg.id}', '${reg.placa}', '${mesAnoFormatado}')" class="px-3 py-1 bg-red-500 hover:bg-red-600 text-white rounded-lg text-sm font-semibold transition-all">
                            🗑️
                        </button>
                    </div>
                </td>
            `;
            
            tbody.appendChild(tr);
        });
    } catch (error) {
        console.error('Erro ao carregar KM mensal:', error);
        const tbody = document.getElementById('tabela-km-mensal');
        if (tbody) {
            tbody.innerHTML = '<tr><td colspan="7" class="p-4 text-center text-red-500">Erro ao carregar dados</td></tr>';
        }
    }
}

function formatMesAno(mesAno) {
    if (!mesAno) return '-';
    const [ano, mes] = mesAno.split('-');
    const meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
    return `${meses[parseInt(mes) - 1]}/${ano}`;
}

async function editarKm(id) {
    try {
        const response = await fetch('/api/km-mensal');
        const registros = await response.json();
        const registro = registros.find(r => r.id === id);
        
        if (!registro) {
            if (window.showToast) showToast('error', 'Registro não encontrado');
            return;
        }
        
        // Preenche o formulário
        document.getElementById('km-id').value = id;
        document.getElementById('km-placa').value = registro.placa || '';
        document.getElementById('km-mes-ano').value = registro.mes_ano || '';
        document.getElementById('km-valor').value = registro.km_valor !== null ? registro.km_valor : '';
        document.getElementById('km-observacao').value = registro.observacao || '';
        
        // Mostra botão cancelar
        document.getElementById('km-cancelar').classList.remove('hidden');
        
        // Muda texto do botão submit
        const submitBtn = document.querySelector('#form-km-mensal button[type="submit"]');
        if (submitBtn) submitBtn.innerHTML = '💾 Atualizar Registro';
        
        // Scroll para o formulário
        document.getElementById('form-km-mensal').scrollIntoView({ behavior: 'smooth' });
        
        kmEditandoId = id;
    } catch (error) {
        console.error('Erro ao carregar registro para edição:', error);
        if (window.showToast) showToast('error', 'Erro ao carregar registro');
    }
}

async function deletarKm(id, placa, mesAno) {
    if (!confirm(`Confirma a exclusão do registro de ${placa} - ${mesAno}?`)) return;
    
    try {
        const response = await fetch(`/api/km-mensal/${id}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (response.ok) {
            if (window.showToast) showToast('success', 'Registro deletado com sucesso');
            loadKmMensalData(document.getElementById('km-filtro-placa').value);
        } else {
            if (window.showToast) showToast('error', result.error || 'Erro ao deletar');
        }
    } catch (error) {
        console.error('Erro ao deletar KM:', error);
        if (window.showToast) showToast('error', 'Erro de conexão');
    }
}

function cancelarEdicaoKm() {
    document.getElementById('form-km-mensal').reset();
    document.getElementById('km-id').value = '';
    document.getElementById('km-cancelar').classList.add('hidden');
    const submitBtn = document.querySelector('#form-km-mensal button[type="submit"]');
    if (submitBtn) submitBtn.innerHTML = '➕ Salvar Registro';
    kmEditandoId = null;
}

// ========================================
// MULTAS - Gestão de Infrações
// ========================================

let multaEditandoId = null;

async function loadMultasData(filtroPlaca = '', filtroStatus = '') {
    try {
        let url = '/api/multas?';
        const params = [];
        if (filtroPlaca) params.push(`placa=${encodeURIComponent(filtroPlaca)}`);
        if (filtroStatus) params.push(`status=${encodeURIComponent(filtroStatus)}`);
        url += params.join('&');
        
        const response = await fetch(url);
        const multas = await response.json();
        const tbody = document.getElementById('tabela-multas');
        
        if (!tbody) return;
        
        tbody.innerHTML = '';
        
        if (!multas || multas.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="p-4 text-center text-gray-500">Nenhuma multa registrada</td></tr>';
            updateMultasStats([]); // Atualiza stats com array vazio
            return;
        }
        
        // Atualiza estatísticas
        updateMultasStats(multas);
        
        multas.forEach(multa => {
            const tr = document.createElement('tr');
            tr.className = 'border-b border-gray-100 hover:bg-red-50 transition-colors';
            
            // Status badge
            let statusClass = 'bg-yellow-100 text-yellow-800';
            let statusText = 'Pendente';
            if (multa.status === 'paga') {
                statusClass = 'bg-green-100 text-green-800';
                statusText = 'Paga';
            } else if (multa.status === 'contestada') {
                statusClass = 'bg-blue-100 text-blue-800';
                statusText = 'Contestada';
            }
            
            // Verifica se está vencida
            const hoje = new Date();
            const vencimento = multa.data_vencimento ? new Date(multa.data_vencimento) : null;
            const vencida = vencimento && vencimento < hoje && multa.status === 'pendente';
            
            // Botões de documento
            const documentoButtons = multa.documento_url
                ? `<div class="flex gap-1">
                     <button onclick="visualizarDocumentoMulta('${multa.id}')" class="px-2 py-1 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg text-xs font-semibold transition-all" title="Ver Documento">
                       👁️ Ver
                     </button>
                     <button onclick="uploadDocumentoMulta('${multa.id}', '${multa.placa}')" class="px-2 py-1 bg-orange-500 hover:bg-orange-600 text-white rounded-lg text-xs font-semibold transition-all" title="Atualizar Documento">
                       🔄 Trocar
                     </button>
                   </div>`
                : `<button onclick="uploadDocumentoMulta('${multa.id}', '${multa.placa}')" class="px-2 py-1 bg-purple-500 hover:bg-purple-600 text-white rounded-lg text-xs font-semibold transition-all" title="Upload Documento">
                     � Upload
                   </button>`;
            
            tr.innerHTML = `
                <td class="p-4">
                    <span class="px-3 py-1 rounded-full text-xs font-semibold ${statusClass}">${statusText}</span>
                    ${vencida ? '<span class="block mt-1 text-xs text-red-600 font-bold">⏰ VENCIDA</span>' : ''}
                </td>
                <td class="p-4 font-bold text-gray-900">${multa.placa || '-'}</td>
                <td class="p-4 text-gray-700">${multa.descricao || '-'}</td>
                <td class="p-4 font-semibold text-red-600">R$ ${multa.valor ? multa.valor.toFixed(2).replace('.', ',') : '0,00'}</td>
                <td class="p-4 text-gray-700">${multa.data_vencimento ? formatDateShort(multa.data_vencimento) : '-'}</td>
                <td class="p-4 text-gray-600 text-sm">${multa.motorista || '-'}</td>
                <td class="p-4">
                    <div class="flex gap-2 items-center">
                        ${documentoButtons}
                        <button onclick="editarMulta('${multa.id}')" class="px-3 py-1 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm font-semibold transition-all">
                            ✏️
                        </button>
                        <button onclick="deletarMulta('${multa.id}', '${multa.placa}')" class="px-3 py-1 bg-red-500 hover:bg-red-600 text-white rounded-lg text-sm font-semibold transition-all">
                            🗑️
                        </button>
                    </div>
                </td>
            `;
            
            tbody.appendChild(tr);
        });
    } catch (error) {
        console.error('Erro ao carregar multas:', error);
        const tbody = document.getElementById('tabela-multas');
        if (tbody) {
            tbody.innerHTML = '<tr><td colspan="7" class="p-4 text-center text-red-500">Erro ao carregar dados</td></tr>';
        }
    }
}

function updateMultasStats(multas) {
    const total = multas.length;
    const pendentes = multas.filter(m => m.status === 'pendente').length;
    const pagas = multas.filter(m => m.status === 'paga').length;
    const valorTotal = multas.reduce((sum, m) => sum + (m.valor || 0), 0);
    
    const statTotal = document.getElementById('stat-multas-total');
    const statPendentes = document.getElementById('stat-multas-pendentes');
    const statPagas = document.getElementById('stat-multas-pagas');
    const statValorTotal = document.getElementById('stat-multas-valor-total');
    
    if (statTotal) statTotal.textContent = total;
    if (statPendentes) statPendentes.textContent = pendentes;
    if (statPagas) statPagas.textContent = pagas;
    if (statValorTotal) statValorTotal.textContent = `R$ ${valorTotal.toFixed(2).replace('.', ',')}`;
}

function formatDateShort(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    const day = String(date.getDate()).padStart(2, '0');
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const year = date.getFullYear();
    return `${day}/${month}/${year}`;
}

async function editarMulta(id) {
    try {
        const response = await fetch('/api/multas');
        const multas = await response.json();
        const multa = multas.find(m => m.id === id);
        
        if (!multa) {
            if (window.showToast) showToast('error', 'Multa não encontrada');
            return;
        }
        
        // Preenche o formulário
        document.getElementById('multa-id').value = id;
        document.getElementById('multa-placa').value = multa.placa || '';
        document.getElementById('multa-descricao').value = multa.descricao || '';
        document.getElementById('multa-valor').value = multa.valor || '';
        document.getElementById('multa-data-infracao').value = multa.data_infracao ? multa.data_infracao.split('T')[0] : '';
        document.getElementById('multa-data-vencimento').value = multa.data_vencimento ? multa.data_vencimento.split('T')[0] : '';
        document.getElementById('multa-status').value = multa.status || 'pendente';
        document.getElementById('multa-motorista').value = multa.motorista || '';
        document.getElementById('multa-local').value = multa.local || '';
        document.getElementById('multa-observacao').value = multa.observacao || '';
        
        // Mostra botão cancelar
        document.getElementById('multa-cancelar').classList.remove('hidden');
        
        // Muda texto do botão submit
        const submitBtn = document.querySelector('#form-multa button[type="submit"]');
        if (submitBtn) submitBtn.innerHTML = '💾 Atualizar Multa';
        
        // Scroll para o formulário
        document.getElementById('form-multa').scrollIntoView({ behavior: 'smooth' });
        
        multaEditandoId = id;
    } catch (error) {
        console.error('Erro ao carregar multa para edição:', error);
        if (window.showToast) showToast('error', 'Erro ao carregar multa');
    }
}

async function deletarMulta(id, placa) {
    if (!confirm(`Confirma a exclusão da multa do veículo ${placa}?`)) return;
    
    try {
        const response = await fetch(`/api/multas/${id}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (response.ok) {
            if (window.showToast) showToast('success', 'Multa deletada com sucesso');
            loadMultasData(
                document.getElementById('multa-filtro-placa').value,
                document.getElementById('multa-filtro-status').value
            );
        } else {
            if (window.showToast) showToast('error', result.error || 'Erro ao deletar');
        }
    } catch (error) {
        console.error('Erro ao deletar multa:', error);
        if (window.showToast) showToast('error', 'Erro de conexão');
    }
}

function cancelarEdicaoMulta() {
    document.getElementById('form-multa').reset();
    document.getElementById('multa-id').value = '';
    document.getElementById('multa-cancelar').classList.add('hidden');
    const submitBtn = document.querySelector('#form-multa button[type="submit"]');
    if (submitBtn) submitBtn.innerHTML = '➕ Salvar Multa';
    multaEditandoId = null;
}

// ========================================
// INICIALIZAÇÃO
// ========================================

document.addEventListener('DOMContentLoaded', () => {
    // Form KM Mensal
    const formKm = document.getElementById('form-km-mensal');
    if (formKm) {
        formKm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const id = document.getElementById('km-id').value;
            const placa = document.getElementById('km-placa').value.trim().toUpperCase();
            const mesAno = document.getElementById('km-mes-ano').value;
            const kmValor = document.getElementById('km-valor').value;
            const observacao = document.getElementById('km-observacao').value.trim();
            
            if (!placa || !mesAno || !kmValor) {
                if (window.showToast) showToast('error', 'Preencha placa, mês/ano e KM');
                return;
            }
            
            const data = {
                placa,
                mes_ano: mesAno,
                km_valor: parseInt(kmValor),
                observacao
            };
            
            try {
                let response;
                if (id) {
                    // Atualizar
                    response = await fetch(`/api/km-mensal/${id}`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(data)
                    });
                } else {
                    // Criar ou atualizar se já existir (UPSERT)
                    response = await fetch('/api/km-mensal', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(data)
                    });
                }
                
                const result = await response.json();
                
                if (response.ok) {
                    if (window.showToast) showToast('success', result.message);
                    cancelarEdicaoKm();
                    loadKmMensalData(document.getElementById('km-filtro-placa').value);
                } else {
                    if (window.showToast) showToast('error', result.error || 'Erro ao salvar');
                }
            } catch (error) {
                console.error('Erro ao salvar KM:', error);
                if (window.showToast) showToast('error', 'Erro de conexão');
            }
        });
    }
    
    // Botão cancelar KM
    const btnCancelarKm = document.getElementById('km-cancelar');
    if (btnCancelarKm) {
        btnCancelarKm.addEventListener('click', cancelarEdicaoKm);
    }
    
    // Filtro de placa KM
    const filtroPlacaKm = document.getElementById('km-filtro-placa');
    if (filtroPlacaKm) {
        filtroPlacaKm.addEventListener('change', () => {
            loadKmMensalData(filtroPlacaKm.value);
        });
    }
    
    // Form Multa
    const formMulta = document.getElementById('form-multa');
    if (formMulta) {
        formMulta.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const id = document.getElementById('multa-id').value;
            const placa = document.getElementById('multa-placa').value.trim().toUpperCase();
            const descricao = document.getElementById('multa-descricao').value.trim();
            const valor = document.getElementById('multa-valor').value;
            const dataInfracao = document.getElementById('multa-data-infracao').value;
            const dataVencimento = document.getElementById('multa-data-vencimento').value;
            const status = document.getElementById('multa-status').value;
            const motorista = document.getElementById('multa-motorista').value.trim();
            const local = document.getElementById('multa-local').value.trim();
            const observacao = document.getElementById('multa-observacao').value.trim();
            
            if (!placa || !descricao || !dataVencimento || !valor) {
                if (window.showToast) showToast('error', 'Preencha os campos obrigatórios');
                return;
            }
            
            const data = {
                placa,
                descricao,
                valor: parseFloat(valor),
                data_infracao: dataInfracao ? new Date(dataInfracao + 'T00:00:00').toISOString() : null,
                data_vencimento: new Date(dataVencimento + 'T00:00:00').toISOString(),
                status,
                motorista,
                local,
                observacao
            };
            
            try {
                let response;
                if (id) {
                    // Atualizar
                    response = await fetch(`/api/multas/${id}`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(data)
                    });
                } else {
                    // Criar
                    response = await fetch('/api/multas', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(data)
                    });
                }
                
                const result = await response.json();
                
                if (response.ok) {
                    if (window.showToast) showToast('success', result.message);
                    cancelarEdicaoMulta();
                    loadMultasData(
                        document.getElementById('multa-filtro-placa').value,
                        document.getElementById('multa-filtro-status').value
                    );
                } else {
                    if (window.showToast) showToast('error', result.error || 'Erro ao salvar');
                }
            } catch (error) {
                console.error('Erro ao salvar multa:', error);
                if (window.showToast) showToast('error', 'Erro de conexão');
            }
        });
    }
    
    // Botão cancelar multa
    const btnCancelarMulta = document.getElementById('multa-cancelar');
    if (btnCancelarMulta) {
        btnCancelarMulta.addEventListener('click', cancelarEdicaoMulta);
    }
    
    // Filtros de multa
    const filtroPlacaMulta = document.getElementById('multa-filtro-placa');
    const filtroStatusMulta = document.getElementById('multa-filtro-status');
    
    if (filtroPlacaMulta) {
        filtroPlacaMulta.addEventListener('change', () => {
            loadMultasData(filtroPlacaMulta.value, filtroStatusMulta.value);
        });
    }
    
    if (filtroStatusMulta) {
        filtroStatusMulta.addEventListener('change', () => {
            loadMultasData(filtroPlacaMulta.value, filtroStatusMulta.value);
        });
    }
    
    // Botão limpar filtros multa
    const btnLimparFiltrosMulta = document.getElementById('multa-limpar-filtros');
    if (btnLimparFiltrosMulta) {
        btnLimparFiltrosMulta.addEventListener('click', () => {
            if (filtroPlacaMulta) filtroPlacaMulta.value = '';
            if (filtroStatusMulta) filtroStatusMulta.value = '';
            loadMultasData('', '');
        });
    }
    
    // Preenche datalists de veículos
    async function loadVeiculosDatalist() {
        try {
            const res = await fetch('/api/veiculos');
            if (!res.ok) return;
            const veiculos = await res.json();
            
            const datalistKm = document.getElementById('veiculos-list-km');
            const datalistMulta = document.getElementById('veiculos-list-multa');
            const selectKm = document.getElementById('km-filtro-placa');
            const selectMulta = document.getElementById('multa-filtro-placa');
            
            veiculos.forEach(v => {
                const placa = v.placa || v;
                if (datalistKm) {
                    const opt = document.createElement('option');
                    opt.value = placa;
                    datalistKm.appendChild(opt);
                }
                if (datalistMulta) {
                    const opt = document.createElement('option');
                    opt.value = placa;
                    datalistMulta.appendChild(opt);
                }
                if (selectKm) {
                    const opt = document.createElement('option');
                    opt.value = placa;
                    opt.textContent = placa;
                    selectKm.appendChild(opt);
                }
                if (selectMulta) {
                    const opt = document.createElement('option');
                    opt.value = placa;
                    opt.textContent = placa;
                    selectMulta.appendChild(opt);
                }
            });
        } catch (e) {
            console.error('Erro ao carregar veículos:', e);
        }
    }
    
    // Preenche datalists de motoristas
    async function loadMotoristasDatalistMulta() {
        try {
            const res = await fetch('/api/motoristas');
            if (!res.ok) return;
            const motoristas = await res.json();
            const datalist = document.getElementById('motoristas-list-multa');
            if (!datalist) return;
            
            motoristas.forEach(m => {
                const nome = m.nome || m;
                const opt = document.createElement('option');
                opt.value = nome;
                datalist.appendChild(opt);
            });
        } catch (e) {
            console.error('Erro ao carregar motoristas:', e);
        }
    }
    
    loadVeiculosDatalist();
    loadMotoristasDatalistMulta();
    
    // Uppercase automático nas placas
    const kmPlacaInput = document.getElementById('km-placa');
    if (kmPlacaInput) {
        kmPlacaInput.addEventListener('input', (e) => {
            const pos = e.target.selectionStart;
            e.target.value = e.target.value.toUpperCase();
            try { e.target.setSelectionRange(pos, pos); } catch (err) { /* ignore */ }
        });
    }
    
    const multaPlacaInput = document.getElementById('multa-placa');
    if (multaPlacaInput) {
        multaPlacaInput.addEventListener('input', (e) => {
            const pos = e.target.selectionStart;
            e.target.value = e.target.value.toUpperCase();
            try { e.target.setSelectionRange(pos, pos); } catch (err) { /* ignore */ }
        });
    }
    
    // Botão de toggle de visualização KM
    const btnToggleKmView = document.getElementById('btn-toggle-km-view');
    if (btnToggleKmView) {
        btnToggleKmView.addEventListener('click', toggleKmView);
    }
});

// ============================================================================
// DOCUMENTO MULTA UPLOAD & VIEW FUNCTIONS
// ============================================================================

async function uploadDocumentoMulta(multaId, placa) {
    document.getElementById('upload-doc-multa-id').value = multaId;
    document.getElementById('upload-doc-multa-placa').value = placa;
    
    // Reset file input
    const fileInput = document.getElementById('doc-multa-file-input');
    fileInput.value = '';
    
    // Reset drop zone
    document.getElementById('doc-multa-drop-zone-content').classList.remove('hidden');
    document.getElementById('doc-multa-file-info').classList.add('hidden');
    
    // Check if multa already has documento to change modal title
    try {
        const response = await fetch('/api/multas');
        const multas = await response.json();
        const multa = multas.find(m => m.id === multaId);
        
        const modalTitle = document.querySelector('#modal-upload-doc-multa h2');
        const submitBtn = document.getElementById('btn-upload-doc-multa');
        
        if (multa && multa.documento_url) {
            modalTitle.textContent = '🔄 Atualizar Documento';
            submitBtn.textContent = '🔄 Atualizar Documento';
        } else {
            modalTitle.textContent = '📄 Upload Documento';
            submitBtn.textContent = '📤 Enviar Documento';
        }
    } catch (error) {
        console.error('Erro ao verificar documento:', error);
    }
    
    // Show modal
    document.getElementById('modal-upload-doc-multa').classList.remove('hidden');
}

function fecharModalUploadDocMulta() {
    document.getElementById('modal-upload-doc-multa').classList.add('hidden');
}

async function visualizarDocumentoMulta(multaId) {
    try {
        document.getElementById('modal-visualizar-doc-multa').classList.remove('hidden');
        
        // Show loading
        document.getElementById('doc-multa-viewer-content').innerHTML = `
            <div class="text-center">
                <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-red-600 mx-auto"></div>
                <p class="mt-4 text-gray-600">Carregando documento...</p>
            </div>
        `;
        
        // Fetch documento URL
        const response = await fetch(`/api/multas/${multaId}/documento`);
        
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || 'Erro ao carregar documento');
        }
        
        const data = await response.json();
        const documentoUrl = data.documento_url;
        
        // Determine file type
        const isPDF = documentoUrl.toLowerCase().includes('.pdf');
        
        if (isPDF) {
            // Display PDF in iframe
            document.getElementById('doc-multa-viewer-content').innerHTML = `
                <iframe src="${documentoUrl}" class="w-full h-[600px] rounded-lg border-2 border-gray-200"></iframe>
            `;
        } else {
            // Display image
            document.getElementById('doc-multa-viewer-content').innerHTML = `
                <img src="${documentoUrl}" alt="Documento da Multa" class="max-w-full h-auto rounded-lg shadow-lg mx-auto">
            `;
        }
        
    } catch (error) {
        console.error('Erro ao visualizar documento:', error);
        document.getElementById('doc-multa-viewer-content').innerHTML = `
            <div class="text-center text-red-500">
                <svg class="mx-auto h-12 w-12 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
                <p class="mt-4">${error.message}</p>
            </div>
        `;
    }
}

function fecharModalVisualizarDocMulta() {
    document.getElementById('modal-visualizar-doc-multa').classList.add('hidden');
}

// ============================================================================
// VISUALIZAÇÃO PLANILHA - KM Mensal
// ============================================================================

let currentKmView = 'tabela'; // 'tabela' ou 'planilha'
let currentKmAno = new Date().getFullYear(); // Ano atual da planilha

async function loadKmPlanilhaData(ano = currentKmAno) {
    currentKmAno = ano; // Atualizar ano atual
    
    try {
        // Buscar APENAS registros do ano especificado (otimização)
        const response = await fetch(`/api/km-mensal?ano=${ano}`);
        const registros = await response.json();
        
        // Buscar revisões para alertas
        let revisoes = [];
        try {
            const revisoesResponse = await fetch('/api/revisoes');
            if (revisoesResponse.ok) {
                revisoes = await revisoesResponse.json();
            }
        } catch (e) {
            console.log('Não foi possível carregar revisões');
        }
        
        // Organizar dados por veículo e mês
        // Usar apenas veículos que aparecem nos registros de KM
        const dadosPorVeiculo = {};
        const meses = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12'];
        
        // Extrair placas únicas dos registros de KM (incluir campo ativo/inativo)
        const placasInfo = {};
        registros.forEach(r => {
            if (r.placa && !placasInfo[r.placa]) {
                placasInfo[r.placa] = {
                    ativo: r.ativo !== false // Se não tem o campo, assume como ativo
                };
            }
        });
        
        const placasUnicas = Object.keys(placasInfo);
        
        // Inicializar estrutura apenas para veículos com registros
        placasUnicas.forEach(placa => {
            dadosPorVeiculo[placa] = {
                placa: placa,
                ativo: placasInfo[placa].ativo,
                meses: {},
                ultimoKm: 0
            };
            meses.forEach(mes => {
                dadosPorVeiculo[placa].meses[mes] = null;
            });
        });
        
        // Preencher com dados reais - MOSTRAR KM_VALOR (odômetro do mês)
        registros.forEach(reg => {
            if (!reg.mes_ano || !reg.placa) return;
            const [anoReg, mesReg] = reg.mes_ano.split('-');
            if (parseInt(anoReg) === parseInt(ano) && dadosPorVeiculo[reg.placa]) {
                dadosPorVeiculo[reg.placa].meses[mesReg] = {
                    km_atual: reg.km_valor || 0, // Odômetro do mês
                    id: reg.id,
                    mes_ano: reg.mes_ano
                };
                // Atualizar último KM conhecido
                if (reg.km_valor && reg.km_valor > dadosPorVeiculo[reg.placa].ultimoKm) {
                    dadosPorVeiculo[reg.placa].ultimoKm = reg.km_valor;
                }
            }
        });
        
        // Gerar HTML da planilha
        const container = document.getElementById('km-planilha-container');
        if (!container) return;
        
        // Adicionar navegador de ano
        let html = `
            <div class="flex items-center justify-between mb-4 p-4 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-xl text-white">
                <button onclick="navegarAno(-1)" class="px-4 py-2 bg-white bg-opacity-20 hover:bg-opacity-30 rounded-lg font-semibold transition-all flex items-center gap-2">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path></svg>
                    ${ano - 1}
                </button>
                <div class="text-center">
                    <h3 class="text-2xl font-bold">Ano: ${ano}</h3>
                    <p class="text-sm text-blue-100">KM Atual por Mês</p>
                </div>
                <button onclick="navegarAno(1)" class="px-4 py-2 bg-white bg-opacity-20 hover:bg-opacity-30 rounded-lg font-semibold transition-all flex items-center gap-2">
                    ${ano + 1}
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path></svg>
                </button>
            </div>
        `;
        
        html += '<table class="w-full text-sm border-collapse" id="tabela-planilha-km">';
        
        // Cabeçalho
        html += '<thead class="bg-gradient-to-r from-blue-500 to-cyan-500 text-white sticky top-0">';
        html += '<tr>';
        html += '<th class="p-3 border border-gray-300 font-bold text-left min-w-[120px]">Veículo/Placa</th>';
        meses.forEach((mes, idx) => {
            const nomeMes = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'][idx];
            html += `<th class="p-3 border border-gray-300 font-bold text-center min-w-[100px]">${nomeMes}/${ano.toString().substr(-2)}</th>`;
        });
        html += '<th class="p-3 border border-gray-300 font-bold text-center min-w-[120px] bg-blue-600">Último KM</th>';
        html += '<th class="p-3 border border-gray-300 font-bold text-center min-w-[80px] bg-blue-600 no-print">Ações</th>';
        html += '</tr>';
        html += '</thead>';
        
        // Corpo - Separar veículos ativos e inativos
        html += '<tbody>';
        
        // Ordenar veículos alfabeticamente
        const veiculosOrdenados = Object.values(dadosPorVeiculo).sort((a, b) => a.placa.localeCompare(b.placa));
        const veiculosAtivos = veiculosOrdenados.filter(v => v.ativo);
        const veiculosInativos = veiculosOrdenados.filter(v => !v.ativo);
        
        // Renderizar veículos ativos
        veiculosAtivos.forEach(veiculo => {
            html += renderLinhaVeiculoPlanilha(veiculo, meses, ano, revisoes);
        });
        
        // Divisor para veículos inativos
        if (veiculosInativos.length > 0) {
            html += `
                <tr class="bg-gray-200">
                    <td colspan="${meses.length + 3}" class="p-3 text-center font-bold text-gray-600">
                        📦 VEÍCULOS INATIVOS (${veiculosInativos.length})
                    </td>
                </tr>
            `;
            
            // Renderizar veículos inativos
            veiculosInativos.forEach(veiculo => {
                html += renderLinhaVeiculoPlanilha(veiculo, meses, ano, revisoes, true);
            });
        }
        
        html += '</tbody>';
        html += '</table>';
        
        container.innerHTML = html;
        
    } catch (error) {
        console.error('Erro ao carregar planilha de KM:', error);
        const container = document.getElementById('km-planilha-container');
        if (container) {
            container.innerHTML = '<div class="p-8 text-center text-red-500">Erro ao carregar dados da planilha</div>';
        }
    }
}

// Função auxiliar para renderizar linha de veículo
function renderLinhaVeiculoPlanilha(veiculo, meses, ano, revisoes, inativo = false) {
    // Verificar se há alerta de revisão
    const revisoesVeiculo = revisoes.filter(r => r.placa === veiculo.placa);
    let alertaRevisao = '';
    let alertaClass = '';
    for (const revisao of revisoesVeiculo) {
        if (revisao.status === 'atrasada') {
            alertaRevisao = ' 🚨';
            alertaClass = ' bg-red-50';
            break;
        } else if (revisao.status === 'proxima' && !alertaRevisao) {
            alertaRevisao = ' ⚠️';
            alertaClass = ' bg-yellow-50';
        }
    }
    
    const inativoClass = inativo ? ' opacity-60' : '';
    const inativoLabel = inativo ? ' [INATIVO]' : '';
    
    let html = `<tr class="hover:bg-blue-50 transition-colors${alertaClass}${inativoClass}">`;
    html += `<td class="p-3 border border-gray-300 font-bold text-gray-900 bg-blue-50">${veiculo.placa}${alertaRevisao}${inativoLabel}</td>`;
    
    meses.forEach((mes, idx) => {
        const dado = veiculo.meses[mes];
        const mesAnoKey = `${ano}-${mes}`;
        
        if (dado && dado.km_atual) {
            // Mostrar KM atual (km_valor)
            html += `<td class="p-2 border border-gray-300 text-center font-semibold text-blue-600 cursor-pointer hover:bg-blue-100 editable-cell" 
                     onclick="editarCelula('${veiculo.placa}', '${mesAnoKey}', ${dado.km_atual}, '${dado.id || ''}')" 
                     title="Clique para editar - KM: ${dado.km_atual?.toLocaleString('pt-BR') || '-'}">${dado.km_atual.toLocaleString('pt-BR')}</td>`;
        } else {
            html += `<td class="p-2 border border-gray-300 text-center text-gray-400 cursor-pointer hover:bg-green-50 editable-cell" 
                     onclick="editarCelula('${veiculo.placa}', '${mesAnoKey}', null, '')" 
                     title="Clique para adicionar KM">+</td>`;
        }
    });
    
    html += `<td class="p-3 border border-gray-300 text-center font-bold text-blue-700 bg-blue-100">${veiculo.ultimoKm.toLocaleString('pt-BR')}</td>`;
    html += `<td class="p-2 border border-gray-300 text-center no-print">
                <div class="flex gap-1 justify-center">
                    <button onclick="toggleVeiculoStatus('${veiculo.placa}', ${!veiculo.ativo})" 
                            class="px-2 py-1 ${veiculo.ativo ? 'bg-orange-500 hover:bg-orange-600' : 'bg-green-500 hover:bg-green-600'} text-white rounded text-xs" 
                            title="${veiculo.ativo ? 'Desativar' : 'Ativar'} veículo">
                        ${veiculo.ativo ? '📦' : '✅'}
                    </button>
                    <button onclick="removerVeiculoPlanilha('${veiculo.placa}')" 
                            class="px-2 py-1 bg-red-500 hover:bg-red-600 text-white rounded text-xs" 
                            title="Remover veículo permanentemente">
                        🗑️
                    </button>
                </div>
             </td>`;
    html += '</tr>';
    
    return html;
}

// Navegar entre anos
function navegarAno(direcao) {
    currentKmAno += direcao;
    loadKmPlanilhaData(currentKmAno);
}

// Editar célula da planilha - Agora edita KM FINAL diretamente
async function editarCelula(placa, mesAno, kmAtual, registroId) {
    const kmNovo = prompt(`Editar KM de ${placa} em ${mesAno}\n\nDigite o KM (odômetro) do mês:`, kmAtual || '');
    
    if (kmNovo === null) return; // Cancelou
    
    const kmNum = parseInt(kmNovo) || 0;
    
    const data = {
        placa: placa,
        mes_ano: mesAno,
        km_valor: kmNum,
        observacao: ''
    };
    
    try {
        let response;
        if (!registroId) {
            // Criar novo registro
            response = await fetch('/api/km-mensal', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
        } else {
            // Atualizar registro existente
            response = await fetch(`/api/km-mensal/${registroId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ km_valor: kmNum })
            });
        }
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Erro ao salvar registro');
        }
        
        if (window.showToast) showToast('success', 'KM registrado com sucesso!');
        loadKmPlanilhaData(currentKmAno);
    } catch (error) {
        console.error('Erro:', error);
        if (window.showToast) showToast('error', error.message || 'Erro ao registrar KM');
    }
}

// Ativar/Desativar veículo na planilha
async function toggleVeiculoStatus(placa, novoStatus) {
    const acao = novoStatus ? 'ativar' : 'desativar';
    
    if (!confirm(`Deseja realmente ${acao} o veículo ${placa}?\n\n${novoStatus ? 'O veículo voltará para a lista ativa.' : 'O veículo será movido para a lista de inativos, mas os dados serão mantidos.'}`)) {
        return;
    }
    
    try {
        // Atualizar todos os registros de KM deste veículo com o novo status
        const response = await fetch('/api/km-mensal');
        const registros = await response.json();
        const registrosVeiculo = registros.filter(r => r.placa === placa);
        
        // Atualizar cada registro
        const promises = registrosVeiculo.map(reg => 
            fetch(`/api/km-mensal/${reg.id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ativo: novoStatus })
            })
        );
        
        await Promise.all(promises);
        
        if (window.showToast) showToast('success', `Veículo ${placa} ${novoStatus ? 'ativado' : 'desativado'} com sucesso!`);
        loadKmPlanilhaData(currentKmAno);
    } catch (error) {
        console.error('Erro ao alterar status do veículo:', error);
        if (window.showToast) showToast('error', 'Erro ao alterar status do veículo');
    }
}

// Adicionar novo veículo na planilha
async function adicionarVeiculoPlanilha() {
    const placa = prompt('Digite a PLACA do veículo:');
    
    if (!placa) return;
    
    const placaNorm = placa.trim().toUpperCase();
    
    if (!placaNorm) {
        if (window.showToast) showToast('error', 'Placa inválida');
        return;
    }
    
    // Verificar se já existe
    const response = await fetch('/api/km-mensal');
    const registros = await response.json();
    
    const jaExiste = registros.some(r => r.placa === placaNorm);
    
    if (jaExiste) {
        if (window.showToast) showToast('info', 'Este veículo já possui registros');
        return;
    }
    
    // Criar primeiro registro do mês atual
    const hoje = new Date();
    const mesAno = `${hoje.getFullYear()}-${String(hoje.getMonth() + 1).padStart(2, '0')}`;
    
    const data = {
        placa: placaNorm,
        mes_ano: mesAno,
        km_valor: 0,
        observacao: 'Veículo adicionado'
    };
    
    try {
        const createResponse = await fetch('/api/km-mensal', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        if (createResponse.ok) {
            if (window.showToast) showToast('success', `Veículo ${placaNorm} adicionado!`);
            loadKmPlanilhaData(hoje.getFullYear());
        } else {
            if (window.showToast) showToast('error', 'Erro ao adicionar veículo');
        }
    } catch (error) {
        console.error('Erro:', error);
        if (window.showToast) showToast('error', 'Erro de conexão');
    }
}

// Remover veículo da planilha
async function removerVeiculoPlanilha(placa) {
    if (!confirm(`Deseja remover todos os registros do veículo ${placa}?`)) return;
    
    try {
        const response = await fetch('/api/km-mensal');
        const registros = await response.json();
        
        const registrosVeiculo = registros.filter(r => r.placa === placa);
        
        // Deletar todos os registros deste veículo
        for (const reg of registrosVeiculo) {
            await fetch(`/api/km-mensal/${reg.id}`, { method: 'DELETE' });
        }
        
        if (window.showToast) showToast('success', `Veículo ${placa} removido!`);
        
        const ano = document.getElementById('planilha-ano')?.value || new Date().getFullYear();
        loadKmPlanilhaData(parseInt(ano));
        
    } catch (error) {
        console.error('Erro:', error);
        if (window.showToast) showToast('error', 'Erro ao remover veículo');
    }
}

// Imprimir planilha
function imprimirPlanilha() {
    // Criar nova janela com estilos de impressão
    const printWindow = window.open('', '_blank');
    const tabela = document.getElementById('tabela-planilha-km');
    
    if (!tabela) {
        if (window.showToast) showToast('error', 'Nenhuma planilha para imprimir');
        return;
    }
    
    const ano = document.getElementById('planilha-ano')?.value || new Date().getFullYear();
    
    printWindow.document.write(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>KM Mensal - ${ano}</title>
            <style>
                @media print {
                    @page { size: landscape; margin: 1cm; }
                    body { font-family: Arial, sans-serif; }
                    table { width: 100%; border-collapse: collapse; font-size: 10px; }
                    th, td { border: 1px solid #000; padding: 4px; text-align: center; }
                    th { background-color: #2563eb !important; color: white !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
                    .bg-blue-50 { background-color: #eff6ff !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
                    .bg-blue-100 { background-color: #dbeafe !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
                    .no-print { display: none !important; }
                }
                body { font-family: Arial, sans-serif; margin: 20px; }
                h1 { text-align: center; color: #1e40af; }
                table { width: 100%; border-collapse: collapse; margin-top: 20px; }
                th, td { border: 1px solid #333; padding: 8px; text-align: center; }
                th { background-color: #2563eb; color: white; }
                .bg-blue-50 { background-color: #eff6ff; }
                .bg-blue-100 { background-color: #dbeafe; }
                .no-print { display: none; }
            </style>
        </head>
        <body>
            <h1>Controle de Quilometragem Mensal - ${ano}</h1>
            <p style="text-align: center; color: #666;">Gerado em: ${new Date().toLocaleString('pt-BR')}</p>
            ${tabela.outerHTML}
            <script>
                window.onload = function() {
                    setTimeout(function() {
                        window.print();
                        window.close();
                    }, 250);
                };
            </script>
        </body>
        </html>
    `);
    
    printWindow.document.close();
}

function toggleKmView() {
    const tabelaView = document.getElementById('km-tabela-view');
    const planilhaView = document.getElementById('km-planilha-view');
    const toggleBtn = document.getElementById('btn-toggle-km-view');
    
    if (currentKmView === 'tabela') {
        // Mudar para planilha
        tabelaView.classList.add('hidden');
        planilhaView.classList.remove('hidden');
        toggleBtn.innerHTML = '📝 Visualização Tabela';
        currentKmView = 'planilha';
        
        // Preencher select de anos
        const selectAno = document.getElementById('planilha-ano');
        if (selectAno && selectAno.options.length === 0) {
            const anoAtual = new Date().getFullYear();
            for (let ano = anoAtual; ano >= 2020; ano--) {
                const option = document.createElement('option');
                option.value = ano;
                option.textContent = ano;
                if (ano === anoAtual) option.selected = true;
                selectAno.appendChild(option);
            }
            
            // Event listener para mudança de ano
            selectAno.addEventListener('change', (e) => {
                loadKmPlanilhaData(parseInt(e.target.value));
            });
        }
        
        // Carregar dados da planilha
        const ano = document.getElementById('planilha-ano')?.value || new Date().getFullYear();
        loadKmPlanilhaData(parseInt(ano));
        
    } else {
        // Mudar para tabela
        planilhaView.classList.add('hidden');
        tabelaView.classList.remove('hidden');
        toggleBtn.innerHTML = '📋 Visualização Planilha';
        currentKmView = 'tabela';
    }
}

// Expor funções globalmente
window.loadKmMensalData = loadKmMensalData;
window.loadMultasData = loadMultasData;
window.editarKm = editarKm;
window.deletarKm = deletarKm;
window.editarMulta = editarMulta;
window.deletarMulta = deletarMulta;
window.uploadDocumentoMulta = uploadDocumentoMulta;
window.fecharModalUploadDocMulta = fecharModalUploadDocMulta;
window.visualizarDocumentoMulta = visualizarDocumentoMulta;
window.fecharModalVisualizarDocMulta = fecharModalVisualizarDocMulta;
window.toggleKmView = toggleKmView;
window.loadKmPlanilhaData = loadKmPlanilhaData;
window.navegarAno = navegarAno;
window.editarCelula = editarCelula;
window.toggleVeiculoStatus = toggleVeiculoStatus;
window.adicionarVeiculoPlanilha = adicionarVeiculoPlanilha;
window.removerVeiculoPlanilha = removerVeiculoPlanilha;
window.imprimirPlanilha = imprimirPlanilha;
