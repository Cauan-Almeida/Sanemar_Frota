// JavaScript para a aba de Veículos no Dashboard

let editingPlaca = null;
let veiculosViewMode = 'card'; // 'card' ou 'lista'
let veiculosCache = []; // Cache dos veículos

// Formatar data (função local para veículos)
function formatarDataVeiculo(isoString) {
    if (!isoString) return '-';
    const d = new Date(isoString);
    return d.toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}

// Toggle entre Card e Lista
function toggleVeiculosView() {
    veiculosViewMode = veiculosViewMode === 'card' ? 'lista' : 'card';
    const btn = document.getElementById('btn-toggle-veiculos-view');
    if (btn) {
        btn.innerHTML = veiculosViewMode === 'card' 
            ? '📋 Visualizar como Lista' 
            : '🎴 Visualizar como Cards';
    }
    renderVeiculos(veiculosCache);
}

// Pesquisar veículos
function pesquisarVeiculos() {
    const searchTerm = document.getElementById('search-veiculos')?.value.toLowerCase() || '';
    
    if (searchTerm.trim() === '') {
        renderVeiculos(veiculosCache);
        return;
    }
    
    const filtered = veiculosCache.filter(v => 
        v.placa.toLowerCase().includes(searchTerm) ||
        (v.modelo && v.modelo.toLowerCase().includes(searchTerm)) ||
        (v.tipo && v.tipo.toLowerCase().includes(searchTerm))
    );
    
    renderVeiculos(filtered);
}

// Carregar veículos
async function loadVeiculosTab() {
    console.log('🚗 loadVeiculosTab() chamada');
    try {
        console.log('📡 Fazendo fetch para /api/veiculos...');
        const res = await fetch('/api/veiculos');
        console.log('📥 Resposta recebida:', res.status, res.statusText);
        if (!res.ok) throw new Error('Erro ao carregar veículos');
        const veiculos = await res.json();
        
        console.log('📦 Veículos carregados:', veiculos.length, 'veículos');
        
        // Guardar no cache
        veiculosCache = veiculos;
        
        // Renderizar
        renderVeiculos(veiculos);
        
    } catch (error) {
        console.error('❌ Erro ao carregar veículos:', error);
        const grid = document.getElementById('veiculos-grid');
        if (grid) {
            grid.innerHTML = '<p class="text-red-500 text-center col-span-full">Erro ao carregar veículos.</p>';
        }
    }
}

// Renderizar veículos (Card ou Lista)
async function renderVeiculos(veiculos) {
    const grid = document.getElementById('veiculos-grid');
    console.log('🎯 Grid encontrado:', grid ? 'SIM' : 'NÃO');
    if (!grid) {
        console.error('❌ Elemento veiculos-grid não encontrado!');
        return;
    }
    
    grid.innerHTML = '';

    if (veiculos.length === 0) {
        grid.innerHTML = '<p class="text-gray-500 text-center col-span-full text-lg">Nenhum veículo encontrado.</p>';
        return;
    }
    
    // Separar ativos e inativos
    let veiculosAtivos = veiculos.filter(v => v.status_ativo !== false);
    const veiculosInativos = veiculos.filter(v => v.status_ativo === false).sort((a, b) => a.placa.localeCompare(b.placa));
    
    // Buscar último abastecimento de cada veículo ativo para ordenar
    console.log('🔄 Buscando últimos abastecimentos para ordenação...');
    const veiculosComData = await Promise.all(veiculosAtivos.map(async (v) => {
        try {
            const res = await fetch(`/api/veiculos/${encodeURIComponent(v.placa)}/refuels?page=1&page_size=1`);
            if (res.ok) {
                const data = await res.json();
                const ultimoAbastecimento = data.items && data.items[0] ? data.items[0].timestamp : null;
                return { ...v, ultimoAbastecimento };
            }
        } catch (e) {
            console.error(`Erro ao buscar último abastecimento de ${v.placa}:`, e);
        }
        return { ...v, ultimoAbastecimento: null };
    }));
    
    // Ordenar por data do último abastecimento (mais recente primeiro)
    veiculosAtivos = veiculosComData.sort((a, b) => {
        // Veículos com abastecimento vêm primeiro
        if (a.ultimoAbastecimento && !b.ultimoAbastecimento) return -1;
        if (!a.ultimoAbastecimento && b.ultimoAbastecimento) return 1;
        
        // Se ambos têm abastecimento, ordena por data (mais recente primeiro)
        if (a.ultimoAbastecimento && b.ultimoAbastecimento) {
            return new Date(b.ultimoAbastecimento) - new Date(a.ultimoAbastecimento);
        }
        
        // Se nenhum tem, ordena por placa
        return a.placa.localeCompare(b.placa);
    });
    
    console.log('✅ Veículos ordenados por último abastecimento');
    
    if (veiculosViewMode === 'card') {
        // Restaurar grid para modo card
        grid.className = 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6';
        await renderVeiculosCards(grid, veiculosAtivos, veiculosInativos);
    } else {
        // Mudar grid para modo lista
        grid.className = 'space-y-2';
        renderVeiculosLista(grid, veiculosAtivos, veiculosInativos);
    }
}

// Renderizar como CARDS
async function renderVeiculosCards(grid, veiculosAtivos, veiculosInativos) {
    // Renderizar ativos
    for (const v of veiculosAtivos) {
        const card = await criarCardVeiculo(v, true);
        grid.appendChild(card);
    }
    
    // Divisor para inativos
    if (veiculosInativos.length > 0) {
        const divisor = document.createElement('div');
        divisor.className = 'col-span-full bg-gray-200 rounded-xl p-4 text-center font-bold text-gray-600 my-4';
        divisor.innerHTML = `📦 VEÍCULOS INATIVOS (${veiculosInativos.length})`;
        grid.appendChild(divisor);
        
        // Renderizar inativos
        for (const v of veiculosInativos) {
            const card = await criarCardVeiculo(v, false);
            grid.appendChild(card);
        }
    }
}

// Criar card de veículo
async function criarCardVeiculo(v, ativo) {
    const placa = v.placa;
    const inativoLabel = ativo ? '' : ' [INATIVO]';
    const inativoClass = ativo ? '' : ' opacity-60';
    
    // Buscar métricas
    let metrics = {};
    try {
        const metricsRes = await fetch(`/api/veiculos/${encodeURIComponent(placa)}/metrics`);
        if (metricsRes.ok) {
            metrics = await metricsRes.json();
        }
    } catch (e) {
        console.error('Erro ao buscar métricas:', e);
    }

    // Buscar últimos abastecimentos
    let refuels = [];
    try {
        const refuelsRes = await fetch(`/api/veiculos/${encodeURIComponent(placa)}/refuels?page=1&page_size=3`);
        if (refuelsRes.ok) {
            const refuelsData = await refuelsRes.json();
            refuels = refuelsData.items || [];
            
            // Ordenar do mais recente para o mais antigo (garantia adicional)
            refuels.sort((a, b) => {
                const getTimestamp = (item) => {
                    const possibleFields = ['timestamp', 'timestampChegada', 'timestampSaida', 'data', 'created_at'];
                    for (const field of possibleFields) {
                        if (item[field]) {
                            const date = new Date(item[field]);
                            if (!isNaN(date.getTime())) {
                                return date.getTime();
                            }
                        }
                    }
                    return 0;
                };
                
                const dateA = getTimestamp(a);
                const dateB = getTimestamp(b);
                return dateB - dateA; // Mais recente primeiro
            });
        }
    } catch (e) {
        console.error('Erro ao buscar abastecimentos:', e);
    }

    const card = document.createElement('div');
    card.className = `bg-white rounded-2xl shadow-xl p-6 hover:shadow-2xl transition-all cursor-pointer${inativoClass}`;
    card.onclick = () => window.location.href = `/veiculos/${encodeURIComponent(placa)}`;
    
    // Botões de documento
    const documentoButtons = v.documento_url
        ? `<div class="flex gap-1">
             <button class="text-lg hover:scale-110 transition-all" onclick="event.stopPropagation(); visualizarDocumentoVeiculo('${v.id}')" title="Ver Documento">
               👁️
             </button>
             <button class="text-lg hover:scale-110 transition-all" onclick="event.stopPropagation(); uploadDocumentoVeiculo('${v.id}', '${placa}')" title="Atualizar Documento">
               🔄
             </button>
           </div>`
        : `<button class="text-lg hover:scale-110 transition-all" onclick="event.stopPropagation(); uploadDocumentoVeiculo('${v.id}', '${placa}')" title="Upload Documento">
             📄
           </button>`;
    
    // Categoria e visibilidade
    const categoriaEmoji = {
        'Base de Itaipuaçu': '📍',
        'Base ETE de Araçatiba': '📍',
        'Sede Sanemar': '📍',
        'Vans': '🚐',
        'Outros': '🚗'
    };
    
    const categoria = v.categoria || 'Outros';
    const visivel = v.visivel_para_motoristas !== false;
    
    // Status badge e botão
    const statusBadge = ativo
        ? '<span class="px-2 py-1 bg-green-100 text-green-700 rounded-full text-xs font-bold">✅ Ativo</span>'
        : '<span class="px-2 py-1 bg-gray-100 text-gray-700 rounded-full text-xs font-bold">⭕ Inativo</span>';
    
    const statusButton = `<button class="text-lg hover:scale-110 transition-all" onclick="event.stopPropagation(); toggleVeiculoStatus('${v.id}', ${!ativo})" title="${ativo ? 'Desativar' : 'Ativar'}">
        ${ativo ? '📦' : '✅'}
    </button>`;
    
    card.innerHTML = `
        <div class="flex items-start justify-between mb-4">
            <div>
                <h3 class="text-2xl font-bold text-gray-800">${placa}${inativoLabel}</h3>
                <p class="text-gray-600">${v.modelo || 'Modelo não informado'}</p>
                <div class="mt-2 flex flex-wrap gap-2">
                    ${statusBadge}
                    <span class="px-2 py-1 bg-blue-100 text-blue-700 rounded-full text-xs font-bold">${categoriaEmoji[categoria]} ${categoria}</span>
                    ${visivel 
                        ? '<span class="px-2 py-1 bg-green-100 text-green-700 rounded-full text-xs font-bold">👁️ Visível</span>'
                        : '<span class="px-2 py-1 bg-amber-100 text-amber-700 rounded-full text-xs font-bold">🔒 Oculto</span>'}
                </div>
            </div>
            <div class="flex gap-2">
                ${statusButton}
                ${documentoButtons}
                <button class="btn-edit-veiculo text-2xl hover:scale-110 transition-all" data-placa="${placa}" onclick="event.stopPropagation(); openEditVeiculo('${placa}')" title="Editar">
                    ⚙️
                </button>
                <button class="btn-delete-veiculo text-2xl hover:scale-110 transition-all" onclick="event.stopPropagation(); excluirVeiculo('${placa}')" title="Excluir">
                    🗑️
                </button>
            </div>
        </div>

        <!-- Métricas Resumidas -->
        <div class="grid grid-cols-2 gap-3 mb-4">
            <div class="bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl p-3 text-white">
                <div class="text-xs opacity-90">Consumo</div>
                <div class="text-xl font-bold">${metrics.km_por_litro_medio ? metrics.km_por_litro_medio.toFixed(2) : '0.00'} km/L</div>
            </div>
            <div class="bg-gradient-to-br from-green-500 to-green-600 rounded-xl p-3 text-white">
                <div class="text-xs opacity-90">Total Litros</div>
                <div class="text-xl font-bold">${metrics.total_litros ? metrics.total_litros.toFixed(0) : '0'} L</div>
            </div>
            <div class="bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl p-3 text-white">
                <div class="text-xs opacity-90">Km Rodados</div>
                <div class="text-xl font-bold">${metrics.km_rodados ? metrics.km_rodados.toFixed(0) : '0'} km</div>
            </div>
            <div class="bg-gradient-to-br from-orange-500 to-orange-600 rounded-xl p-3 text-white">
                <div class="text-xs opacity-90">Odômetro</div>
                <div class="text-xl font-bold">${metrics.ultimo_odometro || '-'}</div>
            </div>
        </div>

        <!-- Últimos Abastecimentos -->
        <div class="border-t pt-4">
            <h4 class="text-sm font-bold text-gray-700 mb-2 flex items-center gap-2">
                <span>⛽</span>
                Últimos Abastecimentos
            </h4>
            ${refuels.length === 0 ? '<p class="text-gray-500 text-sm">Nenhum registro</p>' : `
                <div class="space-y-2">
                    ${refuels.map((r, index) => {
                        // Busca o campo de data em ordem de prioridade
                        const dataAbastecimento = r.timestamp || r.timestampChegada || r.timestampSaida || r.data || r.created_at;
                        
                        let dataFormatada = '-';
                        if (dataAbastecimento) {
                            try {
                                const date = new Date(dataAbastecimento);
                                if (!isNaN(date.getTime())) {
                                    dataFormatada = date.toLocaleDateString('pt-BR', { 
                                        day: '2-digit', 
                                        month: '2-digit', 
                                        year: 'numeric' 
                                    });
                                }
                            } catch (e) {
                                console.error('Erro ao formatar data:', e);
                            }
                        }
                        
                        return `
                        <div class="bg-gray-50 rounded-lg p-3 text-sm ${index === 0 ? 'border-2 border-blue-300 bg-blue-50' : ''}">
                            <div class="flex justify-between items-center mb-2">
                                <div class="flex items-center gap-2">
                                    <span class="font-bold text-blue-600">📅 ${dataFormatada}</span>
                                    ${index === 0 ? '<span class="px-2 py-0.5 bg-blue-500 text-white text-xs rounded-full font-semibold">Mais recente</span>' : ''}
                                </div>
                                <span class="font-bold text-green-600">${r.litros ? parseFloat(r.litros).toFixed(1) + 'L' : '-'}</span>
                            </div>
                            <div class="flex justify-between items-center text-xs text-gray-600">
                                <span class="font-medium">👤 ${r.motorista || 'Não informado'}</span>
                                ${r.odometro ? '<span class="font-medium">🔢 ' + r.odometro + 'km</span>' : '<span></span>'}
                            </div>
                        </div>
                    `}).join('')}
                </div>
            `}
        </div>
    `;
    
    return card;
}

// Renderizar como LISTA
function renderVeiculosLista(grid, veiculosAtivos, veiculosInativos) {
    // Renderizar ativos
    veiculosAtivos.forEach(v => {
        const linha = criarLinhaVeiculo(v, true);
        grid.appendChild(linha);
    });
    
    // Divisor para inativos
    if (veiculosInativos.length > 0) {
        const divisor = document.createElement('div');
        divisor.className = 'bg-gray-200 rounded-xl p-3 text-center font-bold text-gray-600 my-4';
        divisor.innerHTML = `📦 VEÍCULOS INATIVOS (${veiculosInativos.length})`;
        grid.appendChild(divisor);
        
        // Renderizar inativos
        veiculosInativos.forEach(v => {
            const linha = criarLinhaVeiculo(v, false);
            grid.appendChild(linha);
        });
    }
}

// Criar linha de veículo (modo lista)
function criarLinhaVeiculo(v, ativo) {
    const linha = document.createElement('div');
    const inativoLabel = ativo ? '' : ' [INATIVO]';
    const inativoClass = ativo ? '' : ' opacity-60';
    
    linha.className = `bg-white rounded-xl shadow p-4 hover:shadow-lg transition-all flex items-center justify-between cursor-pointer${inativoClass}`;
    linha.onclick = () => window.location.href = `/veiculos/${encodeURIComponent(v.placa)}`;
    
    const statusBadge = ativo
        ? '<span class="px-2 py-1 bg-green-100 text-green-700 rounded-full text-xs font-bold">✅ Ativo</span>'
        : '<span class="px-2 py-1 bg-gray-100 text-gray-700 rounded-full text-xs font-bold">⭕ Inativo</span>';
    
    linha.innerHTML = `
        <div class="flex items-center gap-4 flex-1">
            <div class="text-3xl">🚗</div>
            <div>
                <h3 class="text-lg font-bold text-gray-800">${v.placa}${inativoLabel}</h3>
                <p class="text-sm text-gray-600">${v.modelo || 'Não especificado'} • ${v.tipo || 'Tipo não informado'}</p>
                <div class="mt-1">${statusBadge}</div>
            </div>
        </div>
        <div class="flex gap-2">
            <button class="px-3 py-2 ${ativo ? 'bg-orange-500 hover:bg-orange-600' : 'bg-green-500 hover:bg-green-600'} text-white rounded-lg text-sm font-semibold transition-all" onclick="event.stopPropagation(); toggleVeiculoStatus('${v.id}', ${!ativo})" title="${ativo ? 'Desativar' : 'Ativar'}">
                ${ativo ? '📦' : '✅'}
            </button>
            <button class="px-3 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm font-semibold transition-all" onclick="event.stopPropagation(); openEditVeiculo('${v.placa}')" title="Editar">
                ✏️
            </button>
            <button class="px-3 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg text-sm font-semibold transition-all" onclick="event.stopPropagation(); excluirVeiculo('${v.placa}')" title="Excluir">
                🗑️
            </button>
        </div>
    `;
    
    return linha;
}

// Modal functions
function initVeiculosModal() {
    const modal = document.getElementById('modal-veiculo');
    const modalTitle = document.getElementById('modal-veiculo-title');
    const formVeiculo = document.getElementById('form-veiculo');
    const btnAdd = document.getElementById('btn-add-veiculo');
    const btnCancel = document.getElementById('btn-cancel-veiculo');

    if (!modal || !btnAdd || !btnCancel) return;

    btnAdd.addEventListener('click', () => {
        editingPlaca = null;
        modalTitle.textContent = 'Cadastrar Veículo';
        formVeiculo.reset();
        document.getElementById('input-placa').disabled = false;
        document.getElementById('input-categoria').value = 'Outros';
        document.getElementById('input-categoria-custom').style.display = 'none';
        document.getElementById('input-categoria-custom').value = '';
        document.getElementById('input-visivel').checked = true;
        modal.classList.remove('hidden');
        modal.classList.add('flex');
    });

    btnCancel.addEventListener('click', () => {
        modal.classList.add('hidden');
        modal.classList.remove('flex');
    });

    formVeiculo.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const placa = document.getElementById('input-placa').value.trim().toUpperCase();
        const modelo = document.getElementById('input-modelo').value.trim();
        const media_kmpl = document.getElementById('input-media-kmpl').value;

        if (!placa) {
            if (typeof showToast === 'function') {
                showToast('Informe a placa', 'error');
            } else {
                alert('Informe a placa');
            }
            return;
        }

        try {
            const categoriaSelectEl = document.getElementById('input-categoria');
            const categoriaCustomEl = document.getElementById('input-categoria-custom');
            const visivelEl = document.getElementById('input-visivel');
            
            const categoriaSelect = categoriaSelectEl ? categoriaSelectEl.value : 'Outros';
            const categoriaCustom = categoriaCustomEl ? categoriaCustomEl.value.trim() : '';
            const visivel = visivelEl ? visivelEl.checked : true;
            
            // Validação: se selecionou nova categoria mas não digitou nada
            if (categoriaSelect === '__NOVA__' && !categoriaCustom) {
                if (typeof showToast === 'function') {
                    showToast('Digite o nome da nova categoria', 'error');
                } else {
                    alert('Digite o nome da nova categoria');
                }
                categoriaCustomEl.focus();
                return;
            }
            
            // Se selecionou "Nova categoria", usa o valor digitado
            const categoria = categoriaSelect === '__NOVA__' ? categoriaCustom : categoriaSelect;
            
            console.log('🔵 Dados do formulário:', { placa, modelo, categoria, visivel, categoriaSelect, categoriaCustom });
            
            let payload = { 
                placa, 
                modelo: modelo || '',
                categoria: categoria || 'Outros',
                visivel_para_motoristas: visivel
            };
            if (media_kmpl) payload.media_kmpl = Number(media_kmpl);
            
            console.log('📤 Payload enviado:', payload);

            let res;
            if (editingPlaca) {
                // Atualizar
                res = await fetch(`/api/veiculos/${encodeURIComponent(editingPlaca)}`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
            } else {
                // Criar novo
                res = await fetch('/api/veiculos', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
            }

            const json = await res.json();
            if (res.ok) {
                if (typeof showToast === 'function') {
                    showToast(editingPlaca ? 'Veículo atualizado!' : 'Veículo cadastrado!', 'success');
                } else {
                    alert(editingPlaca ? 'Veículo atualizado!' : 'Veículo cadastrado!');
                }
                modal.classList.add('hidden');
                modal.classList.remove('flex');
                document.getElementById('input-placa').disabled = false;
                loadVeiculosTab();
            } else {
                if (typeof showToast === 'function') {
                    showToast(json.error || 'Erro ao salvar veículo', 'error');
                } else {
                    alert(json.error || 'Erro ao salvar veículo');
                }
            }
        } catch (err) {
            console.error(err);
            if (typeof showToast === 'function') {
                showToast('Erro ao salvar veículo', 'error');
            } else {
                alert('Erro ao salvar veículo');
            }
        }
    });
}

async function openEditVeiculo(placa) {
    editingPlaca = placa;
    const modalTitle = document.getElementById('modal-veiculo-title');
    const modal = document.getElementById('modal-veiculo');
    
    modalTitle.textContent = 'Editar Veículo';
    
    // Buscar dados do veículo
    try {
        const res = await fetch(`/api/veiculos/${encodeURIComponent(placa)}`);
        if (res.ok) {
            const v = await res.json();
            document.getElementById('input-placa').value = v.placa || '';
            document.getElementById('input-placa').disabled = true; // Não pode editar placa
            document.getElementById('input-modelo').value = v.modelo || '';
            document.getElementById('input-media-kmpl').value = v.media_kmpl || '';
            
            // Verificar se categoria é uma das padrões
            const categoriaSelect = document.getElementById('input-categoria');
            const categoriaCustomInput = document.getElementById('input-categoria-custom');
            const categoria = v.categoria || 'Outros';
            
            // Verifica se categoria existe no select
            const optionExists = Array.from(categoriaSelect.options).some(opt => opt.value === categoria);
            
            if (optionExists) {
                categoriaSelect.value = categoria;
                categoriaCustomInput.style.display = 'none';
            } else {
                // Categoria customizada
                categoriaSelect.value = '__NOVA__';
                categoriaCustomInput.value = categoria;
                categoriaCustomInput.style.display = 'block';
            }
            
            document.getElementById('input-visivel').checked = v.visivel_para_motoristas !== false;
            modal.classList.remove('hidden');
            modal.classList.add('flex');
        }
    } catch (e) {
        console.error('Erro ao carregar veículo:', e);
        if (typeof showToast === 'function') {
            showToast('Erro ao carregar dados do veículo', 'error');
        } else {
            alert('Erro ao carregar dados do veículo');
        }
    }
}

// ============================================================================
// DOCUMENTO UPLOAD & VIEW FUNCTIONS
// ============================================================================

// Open upload documento modal
async function uploadDocumentoVeiculo(veiculoId, placa) {
    document.getElementById('upload-doc-veiculo-id').value = veiculoId;
    document.getElementById('upload-doc-veiculo-placa').value = placa;
    
    // Reset file input
    const fileInput = document.getElementById('doc-veiculo-file-input');
    fileInput.value = '';
    
    // Reset drop zone
    document.getElementById('doc-veiculo-drop-zone-content').classList.remove('hidden');
    document.getElementById('doc-veiculo-file-info').classList.add('hidden');
    
    // Check if veiculo already has documento to change modal title
    try {
        const response = await fetch('/api/veiculos');
        const veiculos = await response.json();
        const veiculo = veiculos.find(v => v.id === veiculoId);
        
        const modalTitle = document.querySelector('#modal-upload-doc-veiculo h2');
        const submitBtn = document.getElementById('btn-upload-doc-veiculo');
        
        if (veiculo && veiculo.documento_url) {
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
    document.getElementById('modal-upload-doc-veiculo').classList.remove('hidden');
}

// Close upload documento modal
function fecharModalUploadDocVeiculo() {
    document.getElementById('modal-upload-doc-veiculo').classList.add('hidden');
}

// Open visualizar documento modal
async function visualizarDocumentoVeiculo(veiculoId) {
    try {
        document.getElementById('modal-visualizar-doc-veiculo').classList.remove('hidden');
        
        // Show loading
        document.getElementById('doc-veiculo-viewer-content').innerHTML = `
            <div class="text-center">
                <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
                <p class="mt-4 text-gray-600">Carregando documento...</p>
            </div>
        `;
        
        // Fetch documento URL
        const response = await fetch(`/api/veiculos/${veiculoId}/documento`);
        
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
            document.getElementById('doc-veiculo-viewer-content').innerHTML = `
                <iframe src="${documentoUrl}" class="w-full h-[600px] rounded-lg border-2 border-gray-200"></iframe>
            `;
        } else {
            // Display image
            document.getElementById('doc-veiculo-viewer-content').innerHTML = `
                <img src="${documentoUrl}" alt="Documento" class="max-w-full h-auto rounded-lg shadow-lg mx-auto">
            `;
        }
        
    } catch (error) {
        console.error('Erro ao visualizar documento:', error);
        document.getElementById('doc-veiculo-viewer-content').innerHTML = `
            <div class="text-center text-red-500">
                <svg class="mx-auto h-12 w-12 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
                <p class="mt-4">${error.message}</p>
            </div>
        `;
    }
}

// Close visualizar documento modal
function fecharModalVisualizarDocVeiculo() {
    document.getElementById('modal-visualizar-doc-veiculo').classList.add('hidden');
}

// ============================================================================
// STATUS TOGGLE FUNCTION
// ============================================================================

async function toggleVeiculoStatus(veiculoId, newStatus) {
    try {
        const response = await fetch(`/api/veiculos/${veiculoId}/status`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ status_ativo: newStatus })
        });

        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Erro ao atualizar status');
        }

        if (typeof showToast === 'function') {
            showToast(data.message, 'success');
        }

        // Reload veiculos grid
        await loadVeiculosTab();

    } catch (error) {
        console.error('Erro ao atualizar status:', error);
        if (typeof showToast === 'function') {
            showToast(error.message, 'error');
        }
    }
}

// ============================================================================
// EXCLUIR VEÍCULO FUNCTION
// ============================================================================

async function excluirVeiculo(placa) {
    if (!confirm(`⚠️ Tem certeza que deseja excluir o veículo ${placa}?\n\nEsta ação não pode ser desfeita!`)) {
        return;
    }

    try {
        const response = await fetch(`/api/veiculos/${encodeURIComponent(placa)}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Erro ao excluir veículo');
        }

        if (typeof showToast === 'function') {
            showToast('Veículo excluído com sucesso!', 'success');
        } else {
            alert('Veículo excluído com sucesso!');
        }

        // Reload veiculos grid
        await loadVeiculosTab();

    } catch (error) {
        console.error('Erro ao excluir veículo:', error);
        if (typeof showToast === 'function') {
            showToast(error.message, 'error');
        } else {
            alert(`Erro: ${error.message}`);
        }
    }
}

// Exportar funções para escopo global
window.loadVeiculosTab = loadVeiculosTab;
window.openEditVeiculo = openEditVeiculo;
window.uploadDocumentoVeiculo = uploadDocumentoVeiculo;
window.fecharModalUploadDocVeiculo = fecharModalUploadDocVeiculo;
window.visualizarDocumentoVeiculo = visualizarDocumentoVeiculo;
window.fecharModalVisualizarDocVeiculo = fecharModalVisualizarDocVeiculo;
window.toggleVeiculoStatus = toggleVeiculoStatus;
window.excluirVeiculo = excluirVeiculo;
window.toggleVeiculosView = toggleVeiculosView;
window.pesquisarVeiculos = pesquisarVeiculos;

// Inicializar quando o DOM estiver pronto
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        initVeiculosModal();
    });
} else {
    initVeiculosModal();
}
