document.addEventListener('DOMContentLoaded', () => {
    // Inicializa os gráficos com um estado vazio
    const viagensPorVeiculoChart = renderChart('viagensPorVeiculoChart', 'bar', 'Nº de Viagens por Veículo', '#4F46E5');
    const viagensPorMotoristaChart = renderChart('viagensPorMotoristaChart', 'pie', 'Nº de Viagens por Motorista', ['#4F46E5', '#10B981', '#F59E0B', '#EF4444', '#6366F1']);

    // Gráficos de totais (se existirem nos templates)
    const viagensPorVeiculoChartTotal = document.getElementById('viagensPorVeiculoChartTotal') ? renderChart('viagensPorVeiculoChartTotal', 'bar', 'Viagens por Veículo (Total)', '#6366F1') : null;
    const viagensPorMotoristaChartTotal = document.getElementById('viagensPorMotoristaChartTotal') ? renderChart('viagensPorMotoristaChartTotal', 'bar', 'Viagens por Motorista (Total)', '#10B981') : null;

    // Expor instâncias para que listeners possam recarregar os dados sem reload
    window.viagensPorVeiculoChartInstance = viagensPorVeiculoChart;
    window.viagensPorMotoristaChartInstance = viagensPorMotoristaChart;
    window.viagensPorVeiculoChartTotalInstance = viagensPorVeiculoChartTotal;
    window.viagensPorMotoristaChartTotalInstance = viagensPorMotoristaChartTotal;
    // refuel pie chart instances
    window.refuelPieTotalInstance = null;
    window.refuelPieMonthInstance = null;
    window.viagensChartsInitialized = true;

    // Carrega os dados iniciais
    loadDashboardData(viagensPorVeiculoChart, viagensPorMotoristaChart, viagensPorVeiculoChartTotal, viagensPorMotoristaChartTotal);
    loadHistoricoData(); // Carrega o histórico inicial

    // ✅ NÃO USA MAIS POLLING - USA REALTIME LISTENERS
    // O arquivo dashboard-realtime.js usa onSnapshot do Firestore
    // que atualiza SOMENTE quando há mudanças (muito mais eficiente)
    // Consumo: ~1 leitura inicial + notificações gratuitas de mudanças

    // Sidebar and Tab functionality
    const openSidebarBtn = document.getElementById('open-sidebar');
    const closeSidebarBtn = document.getElementById('close-sidebar');
    const sidebar = document.getElementById('sidebar');
    const tabLinks = document.querySelectorAll('.tab-link');
    const mainContents = document.querySelectorAll('.main-content');
    const mainTitle = document.getElementById('main-title');
    const dataLoaded = new Set();

    function openSidebar() {
        sidebar.classList.remove('-translate-x-full');
        sidebar.classList.add('translate-x-0');
    }

    function closeSidebar() {
        sidebar.classList.remove('translate-x-0');
        sidebar.classList.add('-translate-x-full');
    }

    if(openSidebarBtn) openSidebarBtn.addEventListener('click', openSidebar);
    if(closeSidebarBtn) closeSidebarBtn.addEventListener('click', closeSidebar);

    function switchTab(tab) {
        mainContents.forEach(content => {
            content.classList.add('hidden');
        });
        document.getElementById(`${tab}-content`).classList.remove('hidden');

        tabLinks.forEach(link => {
            link.classList.remove('bg-gray-700');
            if (link.getAttribute('data-tab') === tab) {
                link.classList.add('bg-gray-700');
            }
        });

        if (!dataLoaded.has(tab)) {
            if (tab === 'motoristas') {
                loadMotoristasData();
            } else if (tab === 'km-mensal') {
                if (window.loadKmMensalData) loadKmMensalData();
            } else if (tab === 'multas') {
                if (window.loadMultasData) loadMultasData();
            } else if (tab === 'revisoes') {
                if (window.loadRevisoesData) loadRevisoesData();
            }
            dataLoaded.add(tab);
        }
        
        // Veículos sempre recarrega (para ter dados atualizados)
        if (tab === 'veiculos') {
            loadVeiculosData();
        }

        // Update main title
        const activeLink = document.querySelector(`.tab-link[data-tab="${tab}"]`);
        mainTitle.textContent = activeLink.textContent.trim();
    }

    tabLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const tab = link.getAttribute('data-tab');
            switchTab(tab);

            if (window.innerWidth < 768) {
                closeSidebar();
            }
        });
    });

    // Set initial tab based on server-side variable or default to 'dashboard'
    const initialTab = document.body.dataset.activeTab || 'dashboard';
    switchTab(initialTab);

    // Filtros do Histórico
    const filtroData = document.getElementById('filtro-data');
    const filtroPlaca = document.getElementById('filtro-placa');
    const filtroMotorista = document.getElementById('filtro-motorista');

    [filtroData, filtroPlaca, filtroMotorista].forEach(input => {
        input.addEventListener('keyup', () => {
            loadHistoricoData();
        });
    });
});

// Parser robusto para vários formatos de timestamp (ISO, dd/mm/YYYY HH:MM, Firestore ts obj, numeric ms)
function parseDateValue(val) {
    if (!val && val !== 0) return null;
    // Firestore timestamp object (seconds)
    if (typeof val === 'object' && val !== null) {
        if (val.seconds) {
            return new Date(val.seconds * 1000);
        }
        if (val._seconds) {
            return new Date(val._seconds * 1000);
        }
    }
    // number (ms)
    if (typeof val === 'number') {
        const d = new Date(val);
        if (!isNaN(d.getTime())) return d;
    }
    if (typeof val === 'string') {
        // try ISO
        let d = new Date(val);
        if (!isNaN(d.getTime())) return d;
        // try dd/mm/YYYY HH:MM
        const m = val.match(/^(\d{2})\/(\d{2})\/(\d{4})\s+(\d{1,2}):(\d{2})$/);
        if (m) {
            const [_, day, month, year, hh, mm] = m;
            return new Date(`${year}-${month}-${day}T${hh.padStart(2,'0')}:${mm}:00`);
        }
        // try YYYY-MM-DD HH:MM
        const m2 = val.match(/^(\d{4})-(\d{2})-(\d{2})\s+(\d{1,2}):(\d{2})$/);
        if (m2) {
            const [_, year, month, day, hh, mm] = m2;
            return new Date(`${year}-${month}-${day}T${hh.padStart(2,'0')}:${mm}:00`);
        }
    }
    return null;
}

const formatarData = (val) => {
    const d = parseDateValue(val);
    if (!d) return '-';
    const dia = String(d.getDate()).padStart(2, '0');
    const mes = String(d.getMonth() + 1).padStart(2, '0');
    const ano = d.getFullYear();
    const horas = String(d.getHours()).padStart(2, '0');
    const minutos = String(d.getMinutes()).padStart(2, '0');
    return `${dia}/${mes}/${ano} ${horas}:${minutos}`;
};

async function loadDashboardData(viagensPorVeiculoChart, viagensPorMotoristaChart, viagensPorVeiculoChartTotal = null, viagensPorMotoristaChartTotal = null) {
    console.log('🚀 loadDashboardData() INICIADA');
    try {
        // Primeiro gráfico: SEMPRE usa filtro de mês
        const filtroMesEl = document.getElementById('filtro-mes');
        const mesAtual = new Date().toISOString().slice(0, 7); // YYYY-MM
        const mesFiltro = (filtroMesEl && filtroMesEl.value) ? filtroMesEl.value : mesAtual;
        console.log('📅 Mês filtrado:', mesFiltro);
        
        // Busca dados do mês (para os 2 primeiros gráficos)
        const urlMes = `/api/dashboard_stats?month=${mesFiltro}`;
        console.log('🌐 Buscando dados do mês:', urlMes);
        const responseMes = await fetch(urlMes);
        const statsMes = await responseMes.json();
        console.log('📦 Resposta do backend (mês):', statsMes);
        if (statsMes.error) throw new Error(statsMes.error);

        // Busca dados totais (para os gráficos "Total Geral")
        const urlTotal = '/api/dashboard_stats'; // SEM filtro de mês
        const responseTotal = await fetch(urlTotal);
        const statsTotal = await responseTotal.json();
        if (statsTotal.error) throw new Error(statsTotal.error);

        // Atualiza cards com dados do mês
        console.log('🎯 Atualizando cards com statsMes:', statsMes);
        updateStatCards(statsMes);
        
        // Primeiros 2 gráficos: dados do mês filtrado
        updateChartData(viagensPorVeiculoChart, statsMes.chart_viagens_por_veiculo);
        updateChartData(viagensPorMotoristaChart, statsMes.chart_viagens_por_motorista);
        
        // Gráficos de totais: dados sem filtro
        if (viagensPorVeiculoChartTotal && statsTotal.chart_viagens_por_veiculo) {
            updateChartData(viagensPorVeiculoChartTotal, statsTotal.chart_viagens_por_veiculo);
        }
        if (viagensPorMotoristaChartTotal && statsTotal.chart_viagens_por_motorista) {
            updateChartData(viagensPorMotoristaChartTotal, statsTotal.chart_viagens_por_motorista);
        }

        // Atualiza os gráficos de abastecimento (pie charts) a partir de /api/refuels/summary
        try {
            // Litros Total: SEM filtro de mês
            const respTotal = await fetch('/api/refuels/summary');
            if (respTotal.ok) {
                const summaryTotal = await respTotal.json();
                const total = summaryTotal.per_vehicle_total || { labels: [], data: [] };
                
                // Litros Mês: COM filtro de mês
                const respMes = await fetch(`/api/refuels/summary?month=${mesFiltro}`);
                const summaryMes = await respMes.json();
                const month = summaryMes.per_vehicle_month || { labels: [], data: [] };

                // Colors: reuse a palette
                const palette = ['#4F46E5','#10B981','#F59E0B','#EF4444','#6366F1','#3B82F6','#8B5CF6','#06B6D4','#F97316','#10B981'];

                // Helper to create or update pie chart
                function upsertPie(instanceName, canvasId, labels, data) {
                    const canvas = document.getElementById(canvasId);
                    if (!canvas) return;
                    const ctx = canvas.getContext('2d');
                    // destroy existing instance if already present to avoid duplication
                    if (window[instanceName]) {
                        try { window[instanceName].destroy(); } catch (e) { /* ignore */ }
                        window[instanceName] = null;
                    }
                    const colors = labels.map((_, i) => palette[i % palette.length]);
                    window[instanceName] = new Chart(ctx, {
                        type: 'pie',
                        data: { labels: labels, datasets: [{ data: data, backgroundColor: colors }] },
                        options: { responsive: true, maintainAspectRatio: false }
                    });
                }

                upsertPie('refuelPieTotalInstance', 'refuelPieTotal', total.labels, total.data);
                upsertPie('refuelPieMonthInstance', 'refuelPieMonth', month.labels, month.data);
            }
        } catch (err) {
            console.error('Erro ao atualizar gráficos de abastecimento:', err);
        }

    } catch (error) {
        console.error("Falha ao carregar dados do dashboard:", error);
        const dashboardContent = document.getElementById('dashboard-content');
        if(dashboardContent) {
            dashboardContent.innerHTML = `<div class="text-center p-8 bg-red-100 text-red-700 rounded-lg"><strong>Erro ao carregar dados:</strong> ${error.message}</div>`;
        }
    }
}

// Listeners para o filtro de mês
document.addEventListener('DOMContentLoaded', () => {
    const filtroMes = document.getElementById('filtro-mes');
    const limparMes = document.getElementById('limpar-mes');

    if (filtroMes) {
        filtroMes.addEventListener('change', () => {
            // Força recarregar os charts E a tabela de histórico ao trocar o mês
            if (window.viagensChartsInitialized) {
                loadDashboardData(window.viagensPorVeiculoChartInstance, window.viagensPorMotoristaChartInstance, window.viagensPorVeiculoChartTotalInstance, window.viagensPorMotoristaChartTotalInstance);
                loadHistoricoDataByMonth(); // ✅ Filtra a tabela também!
            } else {
                location.reload();
            }
        });
    }

    if (limparMes) {
        limparMes.addEventListener('click', (e) => {
            e.preventDefault();
            if (filtroMes) filtroMes.value = '';
            if (window.viagensChartsInitialized) {
                loadDashboardData(window.viagensPorVeiculoChartInstance, window.viagensPorMotoristaChartInstance, window.viagensPorVeiculoChartTotalInstance, window.viagensPorMotoristaChartTotalInstance);
                loadHistoricoData(); // ✅ Limpa o filtro da tabela também!
            } else {
                location.reload();
            }
        });
    }
});

// Função auxiliar para filtrar histórico por mês (usando o filtro-mes)
async function loadHistoricoDataByMonth() {
    const filtroMes = document.getElementById('filtro-mes');
    if (!filtroMes || !filtroMes.value) {
        // Se não há filtro de mês, carrega todos
        return loadHistoricoData();
    }

    const [ano, mes] = filtroMes.value.split('-'); // formato: "2025-09"
    
    try {
        const response = await fetch(`/api/historico`);
        const historico = await response.json();
        
        // Filtra localmente por mês/ano
        const historicoFiltrado = historico.filter(item => {
            const timestampSaida = item.timestampSaida;
            if (!timestampSaida) return false;
            
            const dataSaida = new Date(timestampSaida);
            const itemAno = dataSaida.getFullYear();
            const itemMes = String(dataSaida.getMonth() + 1).padStart(2, '0');
            
            return itemAno === parseInt(ano) && itemMes === mes;
        });
        
        // Atualiza o cache global
        if (window.historicoCache !== undefined) {
            window.historicoCache = historicoFiltrado;
        }
        
        populateHistoryTable(historicoFiltrado);
    } catch (error) {
        console.error('Erro ao carregar histórico por mês:', error);
    }
}

async function loadHistoricoData() {
    const dataEl = document.getElementById('filtro-data');
    const placaEl = document.getElementById('filtro-placa');
    const motoristaEl = document.getElementById('filtro-motorista');
    
    const data = dataEl ? dataEl.value : '';
    const placa = placaEl ? placaEl.value : '';
    const motorista = motoristaEl ? motoristaEl.value : '';

    const params = new URLSearchParams({ data, placa, motorista });

    try {
        console.log('🔄 Carregando histórico da API...');
        const response = await fetch(`/api/historico?${params.toString()}`);
        const historico = await response.json();
        
        console.log('✅ API retornou', historico.length, 'registros');
        console.log('🔍 Primeiro registro da API:', historico[0]);
        console.log('🔑 CHAVES do primeiro registro:', Object.keys(historico[0]));
        console.log('🆔 Primeiro registro tem ID?', historico[0]?.id);
        console.log('📝 Valor do ID:', historico[0]?.id);
        
        // Atualiza o cache global para usar nas funções de editar/excluir
        if (window.historicoCache !== undefined) {
            console.log('💾 Atualizando cache global...');
            window.historicoCache = historico;
            console.log('✅ Cache atualizado com', window.historicoCache.length, 'registros');
            console.log('🔍 Primeiro no cache:', window.historicoCache[0]);
        } else {
            console.error('❌ window.historicoCache NÃO EXISTE!');
        }
        
        populateHistoryTable(historico);
    } catch (error) {
        console.error('Erro ao carregar histórico:', error);
    }
}

async function loadMotoristasData() {
    try {
        const response = await fetch('/api/motoristas');
        const motoristas = await response.json();
        
        // Guardar no cache
        motoristasCache = motoristas;
        
        // Renderizar
        renderMotoristas(motoristas);
        
    } catch (error) {
        console.error('Erro ao carregar motoristas:', error);
        const tabelaBody = document.getElementById('tabela-motoristas');
        if (tabelaBody) {
            tabelaBody.innerHTML = '<tr><td colspan="8" class="p-4 text-center text-red-500">Erro ao carregar dados</td></tr>';
        }
    }
}

// Função auxiliar para criar linha de motorista
function criarLinhaMotorista(motorista, ativo) {
    const tr = document.createElement('tr');
    tr.className = `border-b border-gray-100 hover:bg-indigo-50 transition-colors ${ativo ? '' : 'opacity-60'}`;
    
    // Formata nome para mostrar apenas primeiro e último
    const nomeCompleto = motorista.nome || '-';
    const nomeFormatado = formatarNomeAbreviado(nomeCompleto);
    const inativoLabel = ativo ? '' : ' [INATIVO]';
    
    // Seção badge
    const secao = motorista.secao || 'Outros';
    const secaoBadge = `<span class="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-xs font-bold">👷 ${secao}</span>`;
    
    // Visibilidade badge
    const visivel = motorista.visivel_para_motoristas !== false;
    const visibilidadeBadge = visivel
        ? '<span class="px-3 py-1 bg-emerald-100 text-emerald-700 rounded-full text-xs font-bold">👁️ Visível</span>'
        : '<span class="px-3 py-1 bg-rose-100 text-rose-700 rounded-full text-xs font-bold">🔒 Oculto</span>';
    
    // Status badge
    const statusBadge = ativo
        ? '<span class="px-3 py-1 bg-green-100 text-green-700 rounded-full text-xs font-bold">✅ Ativo</span>'
        : '<span class="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-xs font-bold">⭕ Inativo</span>';
    
    // CNH buttons
    const cnhButtons = motorista.cnh_url
        ? `<div class="flex gap-1">
             <button onclick="visualizarCNH('${motorista.id}')" class="px-2 py-1 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg text-xs font-semibold transition-all" title="Ver CNH">
               👁️
             </button>
             <button onclick="uploadCNH('${motorista.id}', '${motorista.nome}')" class="px-2 py-1 bg-orange-500 hover:bg-orange-600 text-white rounded-lg text-xs font-semibold transition-all" title="Atualizar CNH">
               🔄
             </button>
           </div>`
        : `<button onclick="uploadCNH('${motorista.id}', '${motorista.nome}')" class="px-3 py-1 bg-purple-500 hover:bg-purple-600 text-white rounded-lg text-sm font-semibold transition-all">
             📤 Upload
           </button>`;
    
    tr.innerHTML = `
        <td class="p-4 font-semibold text-gray-900">${nomeFormatado}${inativoLabel}</td>
        <td class="p-4 text-gray-700">${motorista.empresa || '-'}</td>
        <td class="p-4 text-gray-700">${motorista.funcao || '-'}</td>
        <td class="p-4"><div class="flex flex-col gap-1">${secaoBadge}${visibilidadeBadge}</div></td>
        <td class="p-4">${statusBadge}</td>
        <td class="p-4">${cnhButtons}</td>
        <td class="p-4 text-gray-600 text-sm">${formatarData(motorista.dataCadastro)}</td>
        <td class="p-4 flex gap-2">
            <button onclick="toggleStatus('${motorista.id}', ${!ativo})" class="px-3 py-1 ${ativo ? 'bg-yellow-500 hover:bg-yellow-600' : 'bg-green-500 hover:bg-green-600'} text-white rounded-lg text-sm font-semibold transition-all" title="${ativo ? 'Desativar' : 'Ativar'}">
                ${ativo ? '📦' : '✅'}
            </button>
            <button onclick="editarMotorista('${motorista.id}')" class="px-3 py-1 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm font-semibold transition-all">
                ✏️
            </button>
            <button onclick="excluirMotorista('${motorista.id}', '${motorista.nome}')" class="px-3 py-1 bg-red-500 hover:bg-red-600 text-white rounded-lg text-sm font-semibold transition-all">
                🗑️
            </button>
        </td>
    `;
    
    return tr;
}

// Formata nome para mostrar apenas primeiro e último
function formatarNomeAbreviado(nomeCompleto) {
    if (!nomeCompleto || nomeCompleto === '-') return '-';
    
    const partes = nomeCompleto.trim().split(/\s+/);
    if (partes.length === 1) return partes[0]; // Só um nome
    if (partes.length === 2) return nomeCompleto; // Nome e sobrenome
    
    // Primeiro + último nome
    return `${partes[0]} ${partes[partes.length - 1]}`;
}

// Pesquisar motoristas
let motoristasCache = [];

function pesquisarMotoristas() {
    const searchTerm = document.getElementById('search-motoristas')?.value.toLowerCase() || '';
    
    if (!motoristasCache || motoristasCache.length === 0) {
        console.warn('Cache de motoristas vazio');
        return;
    }
    
    if (searchTerm.trim() === '') {
        renderMotoristas(motoristasCache);
        return;
    }
    
    const filtered = motoristasCache.filter(m => 
        (m.nome && m.nome.toLowerCase().includes(searchTerm)) ||
        (m.empresa && m.empresa.toLowerCase().includes(searchTerm)) ||
        (m.funcao && m.funcao.toLowerCase().includes(searchTerm)) ||
        (m.secao && m.secao.toLowerCase().includes(searchTerm))
    );
    
    console.log(`Pesquisa: "${searchTerm}" - ${filtered.length} resultado(s)`);
    renderMotoristas(filtered);
}

function renderMotoristas(motoristas) {
    const tabelaBody = document.getElementById('tabela-motoristas');
    tabelaBody.innerHTML = '';
    
    if (motoristas.length === 0) {
        tabelaBody.innerHTML = '<tr><td colspan="8" class="p-4 text-center text-gray-500">Nenhum motorista encontrado</td></tr>';
        return;
    }
    
    // Separar ativos e inativos
    const motoristasAtivos = motoristas.filter(m => m.status_ativo !== false).sort((a, b) => a.nome.localeCompare(b.nome));
    const motoristasInativos = motoristas.filter(m => m.status_ativo === false).sort((a, b) => a.nome.localeCompare(b.nome));
    
    // Renderizar motoristas ativos
    motoristasAtivos.forEach(motorista => {
        tabelaBody.appendChild(criarLinhaMotorista(motorista, true));
    });
    
    // Adicionar divisor se houver inativos
    if (motoristasInativos.length > 0) {
        const divisorTr = document.createElement('tr');
        divisorTr.className = 'bg-gray-200';
        divisorTr.innerHTML = `
            <td colspan="8" class="p-3 text-center font-bold text-gray-600">
                📦 MOTORISTAS INATIVOS (${motoristasInativos.length})
            </td>
        `;
        tabelaBody.appendChild(divisorTr);
        
        // Renderizar motoristas inativos
        motoristasInativos.forEach(motorista => {
            tabelaBody.appendChild(criarLinhaMotorista(motorista, false));
        });
    }
}

// Função para editar motorista
async function editarMotorista(id) {
    try {
        const response = await fetch('/api/motoristas');
        const motoristas = await response.json();
        const motorista = motoristas.find(m => m.id === id);
        
        if (!motorista) {
            if (window.showToast) showToast('error', 'Motorista não encontrado');
            return;
        }
        
        // Preenche o formulário
        document.getElementById('motorista-nome').value = motorista.nome || '';
        document.getElementById('motorista-empresa').value = motorista.empresa || '';
        document.getElementById('motorista-funcao').value = motorista.funcao || '';
        
        // Preenche seção e visibilidade
        const secaoSelect = document.getElementById('motorista-secao');
        const secaoCustom = document.getElementById('motorista-secao-custom');
        const motoristaSecao = motorista.secao || 'Outros';
        
        // Verifica se a seção é uma das pré-definidas
        const opcoesSecao = ['Base de Itaipuaçu', 'Base ETE de Araçatiba', 'Sede Sanemar', 'Van', 'Outros'];
        if (opcoesSecao.includes(motoristaSecao)) {
            secaoSelect.value = motoristaSecao;
            secaoCustom.style.display = 'none';
            secaoCustom.value = '';
        } else {
            // Seção customizada
            secaoSelect.value = '__NOVA__';
            secaoCustom.style.display = 'block';
            secaoCustom.value = motoristaSecao;
        }
        
        // Preenche visibilidade
        document.getElementById('motorista-visivel').checked = motorista.visivel_para_motoristas !== false;
        
        // Adiciona campo hidden com ID
        let hiddenId = document.getElementById('motorista-id-edit');
        if (!hiddenId) {
            hiddenId = document.createElement('input');
            hiddenId.type = 'hidden';
            hiddenId.id = 'motorista-id-edit';
            document.getElementById('form-motorista').appendChild(hiddenId);
        }
        hiddenId.value = id;
        
        // Muda texto do botão
        const submitBtn = document.querySelector('#form-motorista button[type="submit"]');
        if (submitBtn) submitBtn.innerHTML = '💾 Atualizar Motorista';
        
        // Adiciona botão cancelar se não existir
        let btnCancelar = document.getElementById('motorista-btn-cancelar');
        if (!btnCancelar) {
            btnCancelar = document.createElement('button');
            btnCancelar.type = 'button';
            btnCancelar.id = 'motorista-btn-cancelar';
            btnCancelar.className = 'px-8 py-3 bg-gray-300 hover:bg-gray-400 rounded-xl font-bold shadow-lg transition-all';
            btnCancelar.innerHTML = '❌ Cancelar';
            btnCancelar.addEventListener('click', cancelarEdicaoMotorista);
            submitBtn.parentElement.appendChild(btnCancelar);
        }
        btnCancelar.classList.remove('hidden');
        
        // Scroll para o formulário
        document.getElementById('form-motorista').scrollIntoView({ behavior: 'smooth' });
        
    } catch (error) {
        console.error('Erro ao carregar motorista para edição:', error);
        if (window.showToast) showToast('error', 'Erro ao carregar motorista');
    }
}

function cancelarEdicaoMotorista() {
    document.getElementById('form-motorista').reset();
    const hiddenId = document.getElementById('motorista-id-edit');
    if (hiddenId) hiddenId.value = '';
    
    const submitBtn = document.querySelector('#form-motorista button[type="submit"]');
    if (submitBtn) submitBtn.innerHTML = '➕ Adicionar Motorista';
    
    const btnCancelar = document.getElementById('motorista-btn-cancelar');
    if (btnCancelar) btnCancelar.classList.add('hidden');
}

// Função para excluir motorista
async function excluirMotorista(id, nome) {
    if (!confirm(`Tem certeza que deseja excluir o motorista "${nome}"?`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/motoristas/${id}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            if (window.showToast) showToast('success', 'Motorista excluído com sucesso!');
            loadMotoristasData(); // Recarrega a lista
        } else {
            const data = await response.json();
            if (window.showToast) showToast('error', data.error || 'Erro ao excluir motorista');
        }
    } catch (error) {
        console.error('Erro ao excluir motorista:', error);
        if (window.showToast) showToast('error', 'Erro ao excluir motorista');
    }
}

// ============================================================================
// CNH UPLOAD & VIEW FUNCTIONS
// ============================================================================

// Open upload CNH modal
async function uploadCNH(motoristaId, motoristaNome) {
    document.getElementById('upload-cnh-motorista-id').value = motoristaId;
    document.getElementById('upload-cnh-motorista-nome').value = motoristaNome;
    
    // Reset file input
    const fileInput = document.getElementById('cnh-file-input');
    fileInput.value = '';
    
    // Reset drop zone
    document.getElementById('drop-zone-content').classList.remove('hidden');
    document.getElementById('file-info').classList.add('hidden');
    
    // Check if motorista already has CNH to change modal title
    try {
        const response = await fetch('/api/motoristas');
        const motoristas = await response.json();
        const motorista = motoristas.find(m => m.id === motoristaId);
        
        const modalTitle = document.querySelector('#modal-upload-cnh h2');
        const submitBtn = document.getElementById('btn-upload-cnh');
        
        if (motorista && motorista.cnh_url) {
            modalTitle.textContent = '🔄 Atualizar CNH';
            submitBtn.textContent = '🔄 Atualizar CNH';
        } else {
            modalTitle.textContent = '📄 Upload CNH';
            submitBtn.textContent = '📤 Enviar CNH';
        }
    } catch (error) {
        console.error('Erro ao verificar CNH:', error);
    }
    
    // Show modal
    document.getElementById('modal-upload-cnh').classList.remove('hidden');
}

// Close upload CNH modal
function fecharModalUploadCNH() {
    document.getElementById('modal-upload-cnh').classList.add('hidden');
}

// Open visualizar CNH modal
async function visualizarCNH(motoristaId) {
    try {
        document.getElementById('modal-visualizar-cnh').classList.remove('hidden');
        
        // Show loading
        document.getElementById('cnh-viewer-content').innerHTML = `
            <div class="text-center">
                <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
                <p class="mt-4 text-gray-600">Carregando CNH...</p>
            </div>
        `;
        
        // Fetch CNH URL
        const response = await fetch(`/api/motoristas/${motoristaId}/cnh`);
        
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || 'Erro ao carregar CNH');
        }
        
        const data = await response.json();
        const cnhUrl = data.cnh_url;
        
        // Determine file type
        const isPDF = cnhUrl.toLowerCase().includes('.pdf');
        
        if (isPDF) {
            // Display PDF in iframe
            document.getElementById('cnh-viewer-content').innerHTML = `
                <iframe src="${cnhUrl}" class="w-full h-[600px] rounded-lg border-2 border-gray-200"></iframe>
            `;
        } else {
            // Display image
            document.getElementById('cnh-viewer-content').innerHTML = `
                <img src="${cnhUrl}" alt="CNH" class="max-w-full h-auto rounded-lg shadow-lg mx-auto">
            `;
        }
        
    } catch (error) {
        console.error('Erro ao visualizar CNH:', error);
        document.getElementById('cnh-viewer-content').innerHTML = `
            <div class="text-center text-red-500">
                <svg class="mx-auto h-12 w-12 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
                <p class="mt-4">${error.message}</p>
            </div>
        `;
    }
}

// Close visualizar CNH modal
function fecharModalVisualizarCNH() {
    document.getElementById('modal-visualizar-cnh').classList.add('hidden');
}

// Toggle motorista status
async function toggleStatus(motoristaId, newStatus) {
    try {
        const response = await fetch(`/api/motoristas/${motoristaId}/status`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ status_ativo: newStatus })
        });
        
        if (response.ok) {
            const statusTexto = newStatus ? 'ativo' : 'inativo';
            if (window.showToast) showToast('success', `Motorista marcado como ${statusTexto}!`);
            loadMotoristasData(); // Reload table
        } else {
            const data = await response.json();
            if (window.showToast) showToast('error', data.error || 'Erro ao atualizar status');
        }
    } catch (error) {
        console.error('Erro ao atualizar status:', error);
        if (window.showToast) showToast('error', 'Erro ao atualizar status');
    }
}

// Make functions globally available
window.uploadCNH = uploadCNH;
window.fecharModalUploadCNH = fecharModalUploadCNH;
window.visualizarCNH = visualizarCNH;
window.fecharModalVisualizarCNH = fecharModalVisualizarCNH;
window.toggleStatus = toggleStatus;

// Expor funções globalmente
window.editarMotorista = editarMotorista;
window.excluirMotorista = excluirMotorista;
window.loadMotoristasData = loadMotoristasData;
window.pesquisarMotoristas = pesquisarMotoristas;

async function loadVeiculosData() {
    // Chama a função do veiculos-tab.js para carregar o grid completo
    if (typeof loadVeiculosTab === 'function') {
        loadVeiculosTab();
    }
}

function updateStatCards(stats) {
    // 🐛 DEBUG: Vamos ver o que está chegando
    console.log('🎯 updateStatCards recebeu:', stats);
    console.log('📊 viagens_hoje =', stats.viagens_hoje);
    console.log('📊 viagens_em_curso =', stats.viagens_em_curso);
    
    // Proteção: só atualiza se os elementos existirem
    const emCursoEl = document.getElementById('stat-viagens-em-curso');
    const hojeEl = document.getElementById('stat-viagens-hoje');
    const horasEl = document.getElementById('stat-total-horas-na-rua');
    const motoristaDoMesEl = document.getElementById('stat-motorista-do-mes');
    const veiculoDoMesEl = document.getElementById('stat-veiculo-do-mes');
    
    if (emCursoEl) emCursoEl.textContent = stats.viagens_em_curso || '0';
    if (hojeEl) {
        hojeEl.textContent = stats.viagens_hoje || '0';
        console.log('✅ Card HOJE atualizado para:', hojeEl.textContent);
    }
    if (horasEl) horasEl.textContent = stats.total_horas_na_rua || '00:00';
    
    if (motoristaDoMesEl) {
        if (stats.motorista_do_mes && stats.motorista_do_mes.nome !== 'N/A') {
            motoristaDoMesEl.innerHTML = `${stats.motorista_do_mes.nome} <span class="text-base font-normal text-gray-500">(${stats.motorista_do_mes.viagens} viagens)</span>`;
        } else {
            motoristaDoMesEl.textContent = 'N/A';
        }
    }

    if (veiculoDoMesEl) {
        if (stats.veiculo_do_mes && stats.veiculo_do_mes.placa !== 'N/A') {
            veiculoDoMesEl.innerHTML = `${stats.veiculo_do_mes.placa} <span class="text-base font-normal text-gray-500">(${stats.veiculo_do_mes.viagens} viagens)</span>`;
        } else {
            veiculoDoMesEl.textContent = 'N/A';
        }
    }
}

// ✅ Variáveis globais para gerenciamento de tabs de categoria
window.historicoCompleto = [];
window.categoriaAtiva = 'todos';

function populateHistoryTable(historico) {
    const tabelaBody = document.getElementById('tabela-historico');
    if (!tabelaBody) return;

    // Armazena histórico completo para filtragem por categoria
    window.historicoCompleto = historico || [];

    console.log('📋 Populando tabela com', historico.length, 'registros');
    console.log('🏷️ Categoria ativa:', window.categoriaAtiva);
    console.log('🔍 Primeiro registro:', historico[0]);

    // Agrupa histórico por categoria
    const categorias = {
        'Base de Itaipuaçu': [],
        'Base ETE de Araçatiba': [],
        'Sede Sanemar': [],
        'Vans': [],
        'Comercial': [],
        'Outros': []
    };
    
    historico.forEach(item => {
        let cat = item.categoria || 'Outros';
        // Mescla 'Van' em 'Vans'
        if (cat === 'Van') cat = 'Vans';
        
        if (categorias[cat]) {
            categorias[cat].push(item);
        } else {
            categorias['Outros'].push(item);
        }
    });

    // Atualiza contadores nos botões das tabs
    const totalItems = historico.length;
    document.querySelector('[data-category="todos"] .count-badge').textContent = totalItems;
    document.querySelector('[data-category="Base de Itaipuaçu"] .count-badge').textContent = categorias['Base de Itaipuaçu'].length;
    document.querySelector('[data-category="Base ETE de Araçatiba"] .count-badge').textContent = categorias['Base ETE de Araçatiba'].length;
    document.querySelector('[data-category="Sede Sanemar"] .count-badge').textContent = categorias['Sede Sanemar'].length;
    document.querySelector('[data-category="Vans"] .count-badge').textContent = categorias['Vans'].length;
    document.querySelector('[data-category="Comercial"] .count-badge').textContent = categorias['Comercial'].length;
    document.querySelector('[data-category="Outros"] .count-badge').textContent = categorias['Outros'].length;

    // Filtra por categoria ativa
    let itemsParaMostrar = historico;
    if (window.categoriaAtiva !== 'todos') {
        itemsParaMostrar = categorias[window.categoriaAtiva] || [];
    }

    tabelaBody.innerHTML = '';

    if (itemsParaMostrar.length === 0) {
        tabelaBody.innerHTML = '<tr><td colspan="8" class="text-center p-4">Nenhum registro encontrado nesta categoria.</td></tr>';
        return;
    }

    // Renderiza os itens filtrados (sem headers de categoria)
    itemsParaMostrar.forEach(item => {
        if (!item.id) {
            console.warn('⚠️ Registro SEM ID:', item);
        }
        const tr = document.createElement('tr');

        // Status cell
        const statusTd = document.createElement('td');
        statusTd.className = 'p-3';
        const statusSpan = document.createElement('span');
        statusSpan.className = 'px-2 py-1 rounded-full text-xs font-medium';
        if (item.status === 'em_curso') {
            statusSpan.classList.add('bg-yellow-100', 'text-yellow-800');
            statusSpan.textContent = 'Em Curso';
        } else {
            statusSpan.classList.add('bg-green-100', 'text-green-800');
            statusSpan.textContent = 'Finalizada';
        }
        statusTd.appendChild(statusSpan);
        tr.appendChild(statusTd);

        // Veiculo
        const veiculoTd = document.createElement('td');
        veiculoTd.className = 'p-3';
        veiculoTd.textContent = item.veiculo || '-';
        tr.appendChild(veiculoTd);

        // Motorista
        const motoristaTd = document.createElement('td');
        motoristaTd.className = 'p-3';
        motoristaTd.textContent = item.motorista || '-';
        tr.appendChild(motoristaTd);

        // Solicitante (usar textContent para evitar quebra de layout)
        const solicitanteTd = document.createElement('td');
        solicitanteTd.className = 'p-3';
        solicitanteTd.textContent = item.solicitante || '-';
        tr.appendChild(solicitanteTd);

        // Saida: prioriza horarioSaida (HH:MM) quando fornecido, senão usa timestamp formatado
            const saidaTd = document.createElement('td');
            saidaTd.className = 'p-3';
            const horarioSaida = item.horarioSaida || '';
            const tsSaida = item.timestampSaida || null;
            
            // DEBUG: Ver o que está vindo
            if (tr.rowIndex === 1) { // Só primeira linha
                console.log('🐛 DEBUG Saída:', {
                    horarioSaida,
                    tsSaida,
                    tipoTs: typeof tsSaida,
                    dataParsed: parseDateValue(tsSaida),
                    formatado: formatarData(tsSaida)
                });
            }
            
            const isValidTsSaida = tsSaida && !isNaN(new Date(tsSaida).getTime());
            // Se há timestamp válido, prioriza ele (formata); senão, aceita horarioSaida somente se for HH:MM
            if (isValidTsSaida) {
                saidaTd.textContent = formatarData(tsSaida);
            } else if (horarioSaida && /^\d{1,2}:\d{2}$/.test(horarioSaida)) {
                saidaTd.textContent = horarioSaida;
            } else {
                saidaTd.textContent = '-';
            }
        tr.appendChild(saidaTd);

        // Chegada: prioriza horarioChegada quando fornecido
            const chegadaTd = document.createElement('td');
            chegadaTd.className = 'p-3';
            const horarioChegada = item.horarioChegada || '';
            const tsChegada = item.timestampChegada || null;
            const isValidTsChegada = tsChegada && !isNaN(new Date(tsChegada).getTime());
            if (isValidTsChegada) {
                chegadaTd.textContent = formatarData(tsChegada);
            } else if (horarioChegada && /^\d{1,2}:\d{2}$/.test(horarioChegada)) {
                chegadaTd.textContent = horarioChegada;
            } else {
                chegadaTd.textContent = '-';
            }
        tr.appendChild(chegadaTd);

        // Trajeto
        const trajetoTd = document.createElement('td');
        trajetoTd.className = 'p-3';
        trajetoTd.textContent = item.trajeto || '-';
        tr.appendChild(trajetoTd);

        // Ações (Edit/Delete)
        const acoesTd = document.createElement('td');
        acoesTd.className = 'p-3';
        
        // DEBUG removido para reduzir poluição no console
        
        acoesTd.innerHTML = `
            <div class="flex gap-2">
                <button onclick="editarSaidaDashboard('${item.id}')" class="px-2 py-1 bg-blue-500 hover:bg-blue-600 text-white rounded text-xs font-semibold transition-all" title="Editar">
                    ✏️
                </button>
                <button onclick="excluirSaidaDashboard('${item.id}', '${item.veiculo}', '${item.motorista}')" class="px-2 py-1 bg-red-500 hover:bg-red-600 text-white rounded text-xs font-semibold transition-all" title="Excluir">
                    🗑️
                </button>
            </div>
        `;
        tr.appendChild(acoesTd);

        tabelaBody.appendChild(tr);
    });  // Fecha forEach de items
}

function renderChart(canvasId, type, label, colors) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    return new Chart(ctx, {
        type: type,
        data: {
            labels: [],
            datasets: [{
                label: label,
                data: [],
                backgroundColor: colors,
                borderRadius: type === 'bar' ? 4 : undefined,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: type !== 'bar'
                }
            },
            scales: type === 'bar' ? {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            } : undefined
        }
    });
}

function updateChartData(chart, chartData) {
    if (chart && chartData) {
        chart.data.labels = chartData.labels;
        chart.data.datasets[0].data = chartData.data;
        chart.update();
    }
}

// ==========================================
// 🏷️ GERENCIAMENTO DE TABS DE CATEGORIA
// ==========================================

// Função para trocar de categoria
function trocarCategoria(categoria) {
    console.log('🔄 Trocando para categoria:', categoria);
    
    // Atualiza categoria ativa
    window.categoriaAtiva = categoria;
    
    // Remove active de todas as tabs
    document.querySelectorAll('.historico-category-tab').forEach(t => t.classList.remove('active'));
    
    // Adiciona active na tab clicada
    document.querySelector(`[data-category="${categoria}"]`)?.classList.add('active');
    
    // Re-renderiza a tabela com a categoria filtrada
    populateHistoryTable(window.historicoCompleto);
}