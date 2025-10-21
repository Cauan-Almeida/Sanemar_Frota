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

    // Atualiza os dados a cada 30 segundos
    setInterval(() => {
        loadDashboardData(viagensPorVeiculoChart, viagensPorMotoristaChart, viagensPorVeiculoChartTotal, viagensPorMotoristaChartTotal);
        loadHistoricoData();
    }, 30000);

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
            } else if (tab === 'veiculos') {
                loadVeiculosData();
            }
            dataLoaded.add(tab);
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

    // Set initial tab
    switchTab('dashboard');

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
    try {
        // Se o filtro de mês estiver presente, adiciona ao query string
        const filtroMesEl = document.getElementById('filtro-mes');
        let url = '/api/dashboard_stats';
        if (filtroMesEl && filtroMesEl.value) {
            const month = filtroMesEl.value; // formato YYYY-MM
            const params = new URLSearchParams({ month });
            url = `${url}?${params.toString()}`;
        }

        const response = await fetch(url);
        const stats = await response.json();
        if (stats.error) throw new Error(stats.error);

        updateStatCards(stats);
        updateChartData(viagensPorVeiculoChart, stats.chart_viagens_por_veiculo);
        updateChartData(viagensPorMotoristaChart, stats.chart_viagens_por_motorista);
        // Atualiza charts de totais se presentes
        if (viagensPorVeiculoChartTotal && stats.chart_viagens_por_veiculo_total) {
            updateChartData(viagensPorVeiculoChartTotal, stats.chart_viagens_por_veiculo_total);
        }
        if (viagensPorMotoristaChartTotal && stats.chart_viagens_por_motorista_total) {
            updateChartData(viagensPorMotoristaChartTotal, stats.chart_viagens_por_motorista_total);
        }

        // Atualiza os gráficos de abastecimento (pie charts) a partir de /api/refuels/summary
        try {
            // Include month param for refuels summary when dashboard month filter is set
            const filtroMesEl = document.getElementById('filtro-mes');
            let refuelsUrl = '/api/refuels/summary';
            if (filtroMesEl && filtroMesEl.value) {
                const paramsRef = new URLSearchParams({ month: filtroMesEl.value });
                refuelsUrl = `${refuelsUrl}?${paramsRef.toString()}`;
            }
            const resp = await fetch(refuelsUrl);
            if (resp.ok) {
                const summary = await resp.json();
                const total = summary.per_vehicle_total || { labels: [], data: [] };
                const month = summary.per_vehicle_month || { labels: [], data: [] };

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
            // Força recarregar os charts imediatamente ao trocar o mês
            // Recupera as instâncias de chart já criadas (assumimos que as variáveis no escopo global existem)
            if (window.viagensChartsInitialized) {
                loadDashboardData(window.viagensPorVeiculoChartInstance, window.viagensPorMotoristaChartInstance, window.viagensPorVeiculoChartTotalInstance, window.viagensPorMotoristaChartTotalInstance);
            } else {
                // Caso não globals, apenas recarrega a página para simplificar
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
            } else {
                location.reload();
            }
        });
    }
});

async function loadHistoricoData() {
    const data = document.getElementById('filtro-data').value;
    const placa = document.getElementById('filtro-placa').value;
    const motorista = document.getElementById('filtro-motorista').value;

    const params = new URLSearchParams({ data, placa, motorista });

    try {
        const response = await fetch(`/api/historico?${params.toString()}`);
        const historico = await response.json();
        populateHistoryTable(historico);
    } catch (error) {
        console.error('Erro ao carregar histórico:', error);
    }
}

async function loadMotoristasData() {
    try {
        const response = await fetch('/api/motoristas');
        const motoristas = await response.json();
        const tabelaBody = document.getElementById('tabela-motoristas');
        tabelaBody.innerHTML = '';
        motoristas.forEach(motorista => {
            const tr = document.createElement('tr');
            tr.className = 'cursor-pointer hover:bg-gray-100';
            tr.innerHTML = `
                <td class="p-3">${motorista.nome}</td>
                <td class="p-3">${motorista.status}</td>
                <td class="p-3">${formatarData(motorista.dataCadastro)}</td>
            `;
            tr.addEventListener('click', () => {
                window.location.href = `/motorista/${motorista.nome}`;
            });
            tabelaBody.appendChild(tr);
        });
    } catch (error) {
        console.error('Erro ao carregar motoristas:', error);
    }
}

async function loadVeiculosData() {
    try {
        const response = await fetch('/api/veiculos');
        const veiculos = await response.json();
        const tabelaBody = document.getElementById('tabela-veiculos');
        tabelaBody.innerHTML = '';
        veiculos.forEach(veiculo => {
            const tr = document.createElement('tr');
            tr.className = 'cursor-pointer hover:bg-gray-100';
            tr.innerHTML = `
                <td class="p-3">${veiculo.placa}</td>
                <td class="p-3">${formatarData(veiculo.dataCadastro)}</td>
            `;
            tr.addEventListener('click', () => {
                window.location.href = `/veiculo/${veiculo.placa}`;
            });
            tabelaBody.appendChild(tr);
        });
    } catch (error) {
        console.error('Erro ao carregar veículos:', error);
    }
}

function updateStatCards(stats) {
    document.getElementById('stat-viagens-em-curso').textContent = stats.viagens_em_curso || '0';
    document.getElementById('stat-viagens-hoje').textContent = stats.viagens_hoje || '0';
    document.getElementById('stat-total-horas-na-rua').textContent = stats.total_horas_na_rua || '00:00';
    
    const motoristaDoMesEl = document.getElementById('stat-motorista-do-mes');
    if (stats.motorista_do_mes && stats.motorista_do_mes.nome !== 'N/A') {
        motoristaDoMesEl.innerHTML = `${stats.motorista_do_mes.nome} <span class="text-base font-normal text-gray-500">(${stats.motorista_do_mes.viagens} viagens)</span>`;
    } else {
        motoristaDoMesEl.textContent = 'N/A';
    }

    const veiculoDoMesEl = document.getElementById('stat-veiculo-do-mes');
    if (stats.veiculo_do_mes && stats.veiculo_do_mes.placa !== 'N/A') {
        veiculoDoMesEl.innerHTML = `${stats.veiculo_do_mes.placa} <span class="text-base font-normal text-gray-500">(${stats.veiculo_do_mes.viagens} viagens)</span>`;
    } else {
        veiculoDoMesEl.textContent = 'N/A';
    }
}

function populateHistoryTable(historico) {
    const tabelaBody = document.getElementById('tabela-historico');
    if (!tabelaBody) return;

    tabelaBody.innerHTML = '';

    if (!historico || historico.length === 0) {
        tabelaBody.innerHTML = '<tr><td colspan="7" class="text-center p-4">Nenhum registro encontrado.</td></tr>';
        return;
    }

    historico.forEach(item => {
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

        tabelaBody.appendChild(tr);
    });
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