// ============================================================================
// 🔧 SISTEMA DE GESTÃO DE CHAMADOS DE MANUTENÇÃO (REVISÕES)
// ============================================================================
// Sistema completo com LocalStorage para gerenciar chamados de manutenção
// Categorias: Pneu, Revisão, Mecânica, Lataria
// Status: Pendente, Andamento, Resolvido

// --- DADOS INICIAIS (Carregados apenas se não houver no LocalStorage) ---
const initialRevisoesData = [
    {
        id: 1, plate: "STN1C53", km: "53.902", date: "Não informada", driver: "Vinicius", phone: "+55 (21) 96715-3695", requester: "Cauan Almeida",
        title: "Pneu furado / Sem estepe", fullDesc: "O veículo teve um dos pneus furado e, para possibilitar o deslocamento, foi necessário utilizar o estepe. No momento, o veículo encontra-se sem estepe disponível. Solicitamos a manutenção necessária.",
        category: "pneu", mainStatus: "pendente", subStatusLabel: "Falta Levar (AR Estética)", subStatusType: "logistics", location: "Av. Vereador F. Sabino da Costa, 907"
    },
    {
        id: 2, plate: "SNV8D27", km: "35.707", date: "Não informada", driver: "Caique", phone: "+55 (21) 97127-1233", requester: "Cauan Almeida",
        title: "Pneus dianteiros carecas", fullDesc: "Conforme evidenciado nas fotos em anexo, os pneus dianteiros do veículo encontram-se excessivamente desgastados (carecas), comprometendo a segurança na condução. Solicitamos substituição.",
        category: "pneu", mainStatus: "pendente", subStatusLabel: "Aguardando Direcionamento", subStatusType: "action", location: "Av. Vereador F. Sabino da Costa, 907"
    },
    {
        id: 3, plate: "SNV7J27", km: "40.137", date: "Não informada", driver: "Caique", phone: "+55 (21) 97127-1233", requester: "Cauan Almeida",
        title: "Pneu furado / Sem estepe", fullDesc: "O veículo teve um dos pneus furado e foi necessário utilizar o estepe. Encontra-se sem estepe disponível. Solicitamos a manutenção necessária.",
        category: "pneu", mainStatus: "pendente", subStatusLabel: "Aguardando Direcionamento", subStatusType: "action", location: "Av. Vereador F. Sabino da Costa, 907"
    },
    {
        id: 4, plate: "SNW9J82", km: "27.376", date: "Não informada", driver: "Valdsom", phone: "+55 (21) 97004-5508", requester: "Cauan Almeida",
        title: "Pastilhas de Freio", fullDesc: "O veículo apresenta no painel a mensagem de alerta 'verificar pastilhas dos travões'. Solicitamos a averiguação do sistema de freios.",
        category: "mecanica", mainStatus: "pendente", subStatusLabel: "Falta Direcionar (Já solicitado)", subStatusType: "logistics", location: "Av. Vereador F. Sabino da Costa, 907"
    },
    {
        id: 5, plate: "SNX3H03", km: "79.380", date: "15/01/2026", driver: "Amarildo", phone: "+55 (22) 98120-3147", requester: "Cauan Almeida",
        title: "Revisão Preventiva", fullDesc: "A revisão do veículo encontra-se vencida. Solicitamos a realização da revisão preventiva.",
        category: "revisao", mainStatus: "pendente", subStatusLabel: "Aguardando Direcionamento", subStatusType: "action", location: "Av. Vereador F. Sabino da Costa, 907"
    },
    {
        id: 6, plate: "SNW9J72", km: "28.292", date: "10/11/2025", driver: "Felício", phone: "+55 (21) 99753-8575", requester: "Cauan Almeida",
        title: "Revisão Preventiva", fullDesc: "A revisão do veículo encontra-se vencida. Diante disso, solicitamos a realização da manutenção preventiva.",
        category: "revisao", mainStatus: "pendente", subStatusLabel: "Aguardando Direcionamento", subStatusType: "action", location: "Av. Vereador F. Sabino da Costa, 907"
    },
    {
        id: 7, plate: "SNV8E07", km: "45.450", date: "08/01/2026", driver: "Eduardo", phone: "+55 (21) 97472-7661", requester: "Cauan Almeida",
        title: "Revisão Preventiva", fullDesc: "A revisão periódica do veículo encontra-se vencida. Solicitamos a realização da manutenção/revisão do veículo o quanto antes.",
        category: "revisao", mainStatus: "pendente", subStatusLabel: "Aguardando Direcionamento", subStatusType: "action", location: "Av. Vereador F. Sabino da Costa, 907"
    },
    {
        id: 8, plate: "SNX3J73", km: "40.451", date: "08/01/2026", driver: "Pedro Paulo", phone: "+55 (21) 99726-8369", requester: "Cauan Almeida",
        title: "Revisão + Checkup Geral", fullDesc: "Veículo com revisão vencida e apresentando outros problemas. Necessário checkup. Ficou de direcionar com o Fabio da AR Estética e não foi feito.",
        category: "mecanica", mainStatus: "pendente", subStatusLabel: "Pendente Contato (Fábio - AR)", subStatusType: "logistics", location: "Av. Vereador F. Sabino da Costa, 907"
    },
    {
        id: 9, plate: "SNV7H37", km: "37.781", date: "05/11/2025", driver: "Ricardo", phone: "+55 (21) 99775-9417", requester: "Cauan Almeida",
        title: "Tampa Retrovisor Quebrada", fullDesc: "O veículo sofreu um pequeno incidente que resultou na quebra da tampa externa do retrovisor. Solicitamos a troca da tampa.",
        category: "lataria", mainStatus: "pendente", subStatusLabel: "Aguardando Direcionamento", subStatusType: "action", location: "Av. Vereador F. Sabino da Costa, 907"
    },
    {
        id: 10, plate: "SNU1B29", km: "48.511", date: "08/12/2025", driver: "Flávio", phone: "+55 (21) 97130-0718", requester: "Cauan Almeida",
        title: "Revisão Preventiva", fullDesc: "O veículo encontra-se com a revisão vencida. Solicitamos a realização da revisão necessária.",
        category: "revisao", mainStatus: "pendente", subStatusLabel: "Solicitado (Falta Direcionar)", subStatusType: "logistics", location: "Av. Vereador F. Sabino da Costa, 907"
    },
    {
        id: 11, plate: "SNU1B69", km: "32.755", date: "14/01/2026", driver: "Bruno", phone: "+55 (21) 99938-0769", requester: "Cauan Almeida",
        title: "Avaria Lateral Pneu", fullDesc: "O veículo apresentou avaria no pneu, com dano na lateral. Rodando com estepe. Direcionado, o pneu esta na oficina, aguardando resolução desde o dia 14/01/2026.",
        category: "pneu", mainStatus: "andamento", subStatusLabel: "Na Oficina (Desde 14/01)", subStatusType: "wait", location: "Av. Vereador F. Sabino da Costa, 907"
    },
    {
        id: 12, plate: "SNW9B40", km: "36.988", date: "18/12/2025", driver: "Antônio Jorge", phone: "+55 (21) 96743-4766", requester: "Cauan Almeida",
        title: "Troca de 2 Pneus", fullDesc: "Trocou o estepe pelo pneu com a rachadura. O pneu rachado agora está no lugar do estepe. Rodando com estepe e um pneu careca. Aguardando a ASA comprar 2 pneus novos.",
        category: "pneu", mainStatus: "andamento", subStatusLabel: "Aguardando Peça (Compra)", subStatusType: "wait", location: "Av. Vereador F. Sabino da Costa, 907"
    },
    {
        id: 13, plate: "SNW6C90", km: "32.402", date: "Não informada", driver: "Felipe", phone: "+55 (21) 97004-5508", requester: "Cauan Almeida",
        title: "Revisão Preventiva", fullDesc: "A revisão do veículo encontrava-se vencida. Já foi direcionado e resolvido.",
        category: "revisao", mainStatus: "resolvido", subStatusLabel: "Concluído", subStatusType: "done", location: "Av. Vereador F. Sabino da Costa, 907"
    }
];

// --- VARIÁVEIS GLOBAIS ---
let revisoesVehicles = [];
let revisoesCurrentTab = 'pendente';
let revisoesCurrentCategory = 'all';
let revisoesCurrentAprovacao = 'all'; // NOVO: Filtro de aprovação/direcionamento

// Labels de categorias
const revisoesCategoryLabels = {
    'pneu': 'PNEUS', 
    'revisao': 'REVISÃO', 
    'mecanica': 'MECÂNICA', 
    'lataria': 'LATARIA'
};

// --- FUNÇÕES DE DADOS ---

// Carregar dados do LocalStorage ou inicializar
function loadRevisoesData() {
    const stored = localStorage.getItem('fleetData_v1');
    if (stored) {
        try {
            revisoesVehicles = JSON.parse(stored);
        } catch (e) {
            console.error('Erro ao carregar dados de revisões:', e);
            revisoesVehicles = JSON.parse(JSON.stringify(initialRevisoesData));
            saveRevisoesData();
        }
    } else {
        revisoesVehicles = JSON.parse(JSON.stringify(initialRevisoesData));
        saveRevisoesData();
    }
    updateRevisoesCounts();
}

// Salvar dados no LocalStorage
function saveRevisoesData() {
    localStorage.setItem('fleetData_v1', JSON.stringify(revisoesVehicles));
    updateRevisoesCounts();
    applyRevisoesFilters();
}

// Atualizar contadores de status
function updateRevisoesCounts() {
    const pendenteCount = revisoesVehicles.filter(v => v.mainStatus === 'pendente').length;
    const andamentoCount = revisoesVehicles.filter(v => v.mainStatus === 'andamento').length;
    const resolvidoCount = revisoesVehicles.filter(v => v.mainStatus === 'resolvido').length;
    
    const pendenteEl = document.getElementById('revisoes-count-pendente');
    const andamentoEl = document.getElementById('revisoes-count-andamento');
    const resolvidoEl = document.getElementById('revisoes-count-resolvido');
    
    if (pendenteEl) pendenteEl.innerText = pendenteCount;
    if (andamentoEl) andamentoEl.innerText = andamentoCount;
    if (resolvidoEl) resolvidoEl.innerText = resolvidoCount;
}

// --- FUNÇÕES DE FILTROS ---

// Alterar aba principal (Pendente/Andamento/Resolvido)
function setRevisoesMainTab(tab) {
    revisoesCurrentTab = tab;
    ['pendente', 'andamento', 'resolvido'].forEach(t => {
        const btn = document.getElementById(`revisoes-btn-${t}`);
        if (!btn) return;
        
        if (t === tab) {
            btn.classList.remove('text-slate-500', 'hover:bg-slate-50');
            btn.classList.add('text-slate-900', 'bg-slate-100');
            if(t === 'pendente') btn.className = "flex-1 sm:flex-none px-6 py-2 rounded-lg text-sm font-bold bg-white border border-red-200 text-red-700 shadow-sm flex items-center justify-center gap-2 transition-all";
            if(t === 'andamento') btn.className = "flex-1 sm:flex-none px-6 py-2 rounded-lg text-sm font-bold bg-white border border-amber-200 text-amber-700 shadow-sm flex items-center justify-center gap-2 transition-all";
            if(t === 'resolvido') btn.className = "flex-1 sm:flex-none px-6 py-2 rounded-lg text-sm font-bold bg-white border border-green-200 text-green-700 shadow-sm flex items-center justify-center gap-2 transition-all";
        } else {
            btn.className = "flex-1 sm:flex-none px-6 py-2 rounded-lg text-sm font-bold text-slate-400 hover:text-slate-600 hover:bg-slate-50 flex items-center justify-center gap-2 transition-all opacity-70";
        }
    });
    applyRevisoesFilters();
}

// Alterar categoria (Pneu/Revisão/Mecânica/Lataria)
function setRevisoesCategory(cat) {
    revisoesCurrentCategory = cat;
    const categories = ['all', 'pneu', 'revisao', 'mecanica', 'lataria'];
    categories.forEach(c => {
        const btn = document.getElementById(`revisoes-cat-${c}`);
        if (!btn) return;
        
        if (c === cat) {
            btn.classList.remove('border-slate-200', 'bg-white', 'text-slate-600');
            btn.classList.add('border-purple-200', 'bg-purple-50', 'text-purple-700');
        } else {
            btn.classList.add('border-slate-200', 'bg-white', 'text-slate-600');
            btn.classList.remove('border-purple-200', 'bg-purple-50', 'text-purple-700');
        }
    });
    applyRevisoesFilters();
}

// NOVO: Alterar filtro de aprovação/direcionamento
function setRevisoesAprovacao(filtro) {
    revisoesCurrentAprovacao = filtro;
    const filtros = ['all', 'aprovado', 'falta_aprovacao', 'sem_direcionamento', 'direcionado', 'nao_direcionado'];
    const filtrosId = ['all', 'aprovado', 'faltaaprovacao', 'semdirecionamento', 'direcionado', 'naodirecionado'];
    
    filtros.forEach((f, index) => {
        const btn = document.getElementById(`revisoes-apr-${filtrosId[index]}`);
        if (!btn) return;
        
        if (f === filtro) {
            btn.classList.remove('border-slate-200', 'bg-white', 'text-slate-600');
            btn.classList.add('border-blue-200', 'bg-blue-50', 'text-blue-700');
        } else {
            btn.classList.add('border-slate-200', 'bg-white', 'text-slate-600');
            btn.classList.remove('border-blue-200', 'bg-blue-50', 'text-blue-700');
        }
    });
    applyRevisoesFilters();
}

// Aplicar todos os filtros e renderizar lista
function applyRevisoesFilters() {
    const searchInput = document.getElementById('revisoes-searchInput');
    const search = searchInput ? searchInput.value.toLowerCase() : '';
    const container = document.getElementById('revisoes-list-container');
    
    if (!container) return;
    
    container.innerHTML = '';

    const filtered = revisoesVehicles.filter(item => {
        const matchTab = item.mainStatus === revisoesCurrentTab;
        const matchCat = revisoesCurrentCategory === 'all' || item.category === revisoesCurrentCategory;
        
        // NOVO: Filtro de aprovação/direcionamento
        let matchAprovacao = true;
        if (revisoesCurrentAprovacao !== 'all') {
            const aprovacao = item.aprovacao || '';
            const direcionamento = item.direcionamento || '';
            
            if (revisoesCurrentAprovacao === 'aprovado') {
                matchAprovacao = aprovacao === 'aprovado';
            } else if (revisoesCurrentAprovacao === 'falta_aprovacao') {
                matchAprovacao = aprovacao === 'falta_aprovacao';
            } else if (revisoesCurrentAprovacao === 'sem_direcionamento') {
                matchAprovacao = direcionamento === 'sem_direcionamento';
            } else if (revisoesCurrentAprovacao === 'direcionado') {
                matchAprovacao = direcionamento === 'direcionado';
            } else if (revisoesCurrentAprovacao === 'nao_direcionado') {
                matchAprovacao = direcionamento === 'nao_direcionado';
            }
        }
        
        const matchSearch = item.plate.toLowerCase().includes(search) || 
                            item.driver.toLowerCase().includes(search) ||
                            item.title.toLowerCase().includes(search);
        return matchTab && matchCat && matchAprovacao && matchSearch;
    });

    if (filtered.length === 0) {
        container.innerHTML = `
            <div class="text-center py-16 bg-white rounded-xl border border-dashed border-slate-300">
                <i class="fa-regular fa-folder-open text-4xl text-slate-300 mb-3"></i>
                <p class="text-slate-400 font-medium">Nenhum chamado encontrado nesta seção.</p>
            </div>
        `;
        return 0;
    }

    filtered.forEach(item => {
        const catClass = `revisoes-type-${item.category}`;
        const catLabel = revisoesCategoryLabels[item.category] || item.category.toUpperCase();
        const statusBorder = `revisoes-status-border-${item.mainStatus}`;
        
        const dateHtml = item.date && item.date !== "Não informada"
            ? `<span class="text-xs text-slate-400 flex items-center gap-1 bg-slate-100 px-2 py-0.5 rounded-full"><i class="fa-regular fa-calendar"></i> ${item.date}</span>` 
            : '';

        // Botões de ação dinâmicos conforme o status
        let actionButtons = '';
        if(item.mainStatus === 'pendente') {
            actionButtons = `
                <button onclick="changeRevisoesStatus(${item.id}, 'andamento')" class="flex items-center gap-1 px-3 py-1.5 bg-amber-50 text-amber-700 rounded-lg text-xs font-bold hover:bg-amber-100 border border-amber-200 transition-colors">
                    <i class="fa-solid fa-arrow-right"></i> Mover p/ Andamento
                </button>
            `;
        } else if (item.mainStatus === 'andamento') {
            actionButtons = `
                <button onclick="changeRevisoesStatus(${item.id}, 'pendente')" class="flex items-center gap-1 px-3 py-1.5 bg-gray-50 text-gray-600 rounded-lg text-xs font-bold hover:bg-gray-100 border border-gray-200 transition-colors">
                    <i class="fa-solid fa-arrow-left"></i> Voltar
                </button>
                <button onclick="changeRevisoesStatus(${item.id}, 'resolvido')" class="flex items-center gap-1 px-3 py-1.5 bg-green-50 text-green-700 rounded-lg text-xs font-bold hover:bg-green-100 border border-green-200 transition-colors">
                    <i class="fa-solid fa-check"></i> Concluir
                </button>
            `;
        } else {
             actionButtons = `
                <button onclick="changeRevisoesStatus(${item.id}, 'andamento')" class="flex items-center gap-1 px-3 py-1.5 bg-gray-50 text-gray-600 rounded-lg text-xs font-bold hover:bg-gray-100 border border-gray-200 transition-colors">
                    <i class="fa-solid fa-arrow-rotate-left"></i> Reabrir
                </button>
            `;
        }

        const html = `
            <div class="bg-white rounded-xl shadow-sm border border-slate-200 revisoes-card-transition hover:shadow-md overflow-hidden ${statusBorder} group">
                
                <!-- Cabeçalho -->
                <div class="p-4 cursor-pointer relative" onclick="toggleRevisoesDetails(${item.id}, event)">
                    <div class="flex flex-col md:flex-row gap-4 md:items-center justify-between">
                        
                        <!-- Esquerda -->
                        <div class="flex items-start gap-4">
                            <div class="flex flex-col items-center justify-center w-14 h-14 rounded-xl bg-gradient-to-br from-purple-50 to-indigo-50 border-2 border-purple-200 shadow-sm">
                                <i class="fa-solid fa-truck text-purple-600 text-2xl"></i>
                            </div>
                            <div class="flex flex-col">
                                <div class="flex items-center flex-wrap gap-2 mb-1">
                                    <span class="text-xl font-bold text-slate-800 font-mono tracking-tight">${item.plate}</span>
                                    <span class="revisoes-badge ${catClass}">${catLabel}</span>
                                    <span class="text-xs font-bold text-slate-500 bg-slate-100 px-2 py-0.5 rounded border border-slate-200 flex items-center gap-1">
                                        <i class="fa-solid fa-gauge-high text-[10px]"></i> ${item.km} Km
                                    </span>
                                </div>
                                <div class="text-slate-700 font-medium text-sm">${item.title}</div>
                                <div class="text-slate-400 text-xs mt-1 md:hidden">${item.subStatusLabel}</div>
                            </div>
                        </div>

                        <!-- Direita -->
                        <div class="flex items-center justify-between md:justify-end gap-4 w-full md:w-auto">
                            <div class="flex flex-col items-end hidden md:flex">
                                <span class="text-xs font-bold px-2 py-1 rounded bg-slate-50 border border-slate-100 text-slate-600">${item.subStatusLabel}</span>
                                <div class="mt-1">${dateHtml}</div>
                            </div>
                            <div class="w-8 h-8 flex items-center justify-center rounded-full hover:bg-slate-100 transition-colors">
                                <i id="revisoes-chevron-${item.id}" class="fa-solid fa-chevron-down text-slate-400 transition-transform duration-300"></i>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Detalhes -->
                <div id="revisoes-details-${item.id}" class="revisoes-details-content bg-slate-50 border-t border-slate-100"
                    <!-- Barra de Ações -->
                    <div class="bg-white px-5 py-3 border-b border-slate-100 flex flex-wrap gap-2 items-center justify-between">
                        <div class="flex gap-2">
                            ${actionButtons}
                        </div>
                        <div class="flex gap-2">
                            <button onclick="editRevisoesVehicle(${item.id})" class="text-blue-600 hover:bg-blue-50 px-3 py-1.5 rounded-lg text-xs font-bold transition-colors">
                                <i class="fa-solid fa-pen"></i> Editar
                            </button>
                            <button onclick="deleteRevisoesVehicle(${item.id})" class="text-red-400 hover:text-red-600 hover:bg-red-50 px-3 py-1.5 rounded-lg text-xs font-bold transition-colors">
                                <i class="fa-solid fa-trash"></i>
                            </button>
                        </div>
                    </div>

                    <div class="p-5 grid grid-cols-1 md:grid-cols-2 gap-6 text-sm">
                        
                        <!-- Info -->
                        <div class="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
                            <h4 class="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                                <i class="fa-regular fa-id-card"></i> Dados Operacionais
                            </h4>
                            <ul class="space-y-3 text-slate-600">
                                <li class="flex justify-between border-b border-slate-100 pb-2">
                                    <span>Motorista:</span> <span class="font-bold text-slate-800">${item.driver}</span>
                                </li>
                                <li class="flex justify-between border-b border-slate-100 pb-2">
                                    <span>Telefone:</span> <span class="font-medium text-slate-800">${item.phone}</span>
                                </li>
                                <li class="flex justify-between border-b border-slate-100 pb-2">
                                    <span>Solicitante:</span> <span class="font-medium text-slate-800">${item.requester}</span>
                                </li>
                                <li class="block pt-1">
                                    <span class="block text-xs text-slate-400 mb-1">Localização:</span>
                                    <span class="font-medium text-slate-800 leading-snug">${item.location}</span>
                                </li>
                            </ul>
                        </div>

                        <!-- Descrição -->
                        <div>
                            <h4 class="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                                <i class="fa-regular fa-file-lines"></i> Relato Detalhado
                            </h4>
                            <div class="bg-white p-4 rounded-lg border border-slate-200 shadow-sm text-slate-700 leading-relaxed text-justify">
                                ${item.fullDesc}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        container.insertAdjacentHTML('beforeend', html);
    });
    
    return filtered.length;
}

// --- FUNÇÕES DE INTERAÇÃO ---

// Toggle de detalhes do card
function toggleRevisoesDetails(id, event) {
    // Evitar que cliques nos botões disparem o toggle
    if(event.target.tagName === 'BUTTON' || event.target.closest('button')) return;

    const content = document.getElementById(`revisoes-details-${id}`);
    const chevron = document.getElementById(`revisoes-chevron-${id}`);
    
    if (!content || !chevron) return;
    
    if (content.classList.contains('open')) {
        content.classList.remove('open');
        chevron.classList.remove('revisoes-rotate-chevron');
    } else {
        // Fechar outros (Opcional, mas mantém limpo)
        document.querySelectorAll('.revisoes-details-content.open').forEach(el => {
           el.classList.remove('open');
        });
        document.querySelectorAll('.revisoes-rotate-chevron').forEach(el => {
           el.classList.remove('revisoes-rotate-chevron');
        });

        content.classList.add('open');
        chevron.classList.add('revisoes-rotate-chevron');
    }
}

// --- FUNÇÕES DE MODAL ---

// Abrir modal (criar ou editar)
function openRevisoesModal(editId = null) {
    const modal = document.getElementById('revisoes-modal');
    const title = document.getElementById('revisoes-modal-title');
    
    if (!modal) return;

    // Reset form
    document.getElementById('revisoes-form-id').value = '';
    document.getElementById('revisoes-form-plate').value = '';
    document.getElementById('revisoes-form-km').value = '';
    document.getElementById('revisoes-form-driver').value = '';
    document.getElementById('revisoes-form-phone').value = '';
    document.getElementById('revisoes-form-title').value = '';
    document.getElementById('revisoes-form-desc').value = '';
    document.getElementById('revisoes-form-subStatusLabel').value = '';
    document.getElementById('revisoes-form-category').value = 'mecanica';
    document.getElementById('revisoes-form-location').value = 'Av. Vereador F. Sabino da Costa, 907';
    document.getElementById('revisoes-form-date').value = new Date().toLocaleDateString('pt-BR');

    if (editId) {
        title.innerText = "Editar Chamado";
        const item = revisoesVehicles.find(v => v.id === editId);
        if(item) {
            document.getElementById('revisoes-form-id').value = item.id;
            document.getElementById('revisoes-form-plate').value = item.plate;
            document.getElementById('revisoes-form-km').value = item.km;
            document.getElementById('revisoes-form-driver').value = item.driver;
            document.getElementById('revisoes-form-phone').value = item.phone;
            document.getElementById('revisoes-form-title').value = item.title;
            document.getElementById('revisoes-form-desc').value = item.fullDesc;
            document.getElementById('revisoes-form-subStatusLabel').value = item.subStatusLabel;
            document.getElementById('revisoes-form-category').value = item.category;
            document.getElementById('revisoes-form-location').value = item.location;
            document.getElementById('revisoes-form-aprovacao').value = item.aprovacao || '';
            document.getElementById('revisoes-form-direcionamento').value = item.direcionamento || '';
            if(item.date) document.getElementById('revisoes-form-date').value = item.date;
        }
    } else {
        title.innerText = "Novo Chamado";
    }

    modal.classList.remove('opacity-0', 'pointer-events-none');
    document.body.classList.add('revisoes-modal-active');
}

// Fechar modal
function closeRevisoesModal() {
    const modal = document.getElementById('revisoes-modal');
    if (!modal) return;
    
    modal.classList.add('opacity-0', 'pointer-events-none');
    document.body.classList.remove('revisoes-modal-active');
}

// Salvar chamado (criar ou editar)
function saveRevisoesVehicle() {
    const id = document.getElementById('revisoes-form-id').value;
    const plate = document.getElementById('revisoes-form-plate').value.toUpperCase();
    const km = document.getElementById('revisoes-form-km').value;
    
    if(!plate || !km) {
        if (window.showToast) {
            showToast('error', 'Placa e KM são obrigatórios.');
        } else {
            alert("Placa e KM são obrigatórios.");
        }
        return;
    }

    const data = {
        plate: plate,
        km: km,
        driver: document.getElementById('revisoes-form-driver').value,
        phone: document.getElementById('revisoes-form-phone').value,
        title: document.getElementById('revisoes-form-title').value,
        fullDesc: document.getElementById('revisoes-form-desc').value,
        category: document.getElementById('revisoes-form-category').value,
        subStatusLabel: document.getElementById('revisoes-form-subStatusLabel').value || "Aguardando",
        location: document.getElementById('revisoes-form-location').value,
        date: document.getElementById('revisoes-form-date').value,
        aprovacao: document.getElementById('revisoes-form-aprovacao').value || '',
        direcionamento: document.getElementById('revisoes-form-direcionamento').value || '',
        requester: "Usuário do Sistema"
    };

    if (id) {
        // Edit
        const index = revisoesVehicles.findIndex(v => v.id == id);
        if (index > -1) {
            revisoesVehicles[index] = { ...revisoesVehicles[index], ...data };
        }
    } else {
        // Create
        const newId = revisoesVehicles.length > 0 ? Math.max(...revisoesVehicles.map(v => v.id)) + 1 : 1;
        const newVehicle = {
            id: newId,
            ...data,
            mainStatus: 'pendente',
            subStatusType: 'action'
        };
        revisoesVehicles.unshift(newVehicle);
    }

    saveRevisoesData();
    closeRevisoesModal();
    
    if (window.showToast) {
        showToast('success', id ? 'Chamado atualizado!' : 'Chamado criado!');
    }
}

// Editar chamado
function editRevisoesVehicle(id) {
    event.stopPropagation();
    openRevisoesModal(id);
}

// Excluir chamado
function deleteRevisoesVehicle(id) {
    event.stopPropagation();
    if(confirm("Tem certeza que deseja excluir este chamado?")) {
        revisoesVehicles = revisoesVehicles.filter(v => v.id !== id);
        saveRevisoesData();
        
        if (window.showToast) {
            showToast('success', 'Chamado excluído!');
        }
    }
}

// Alterar status do chamado
function changeRevisoesStatus(id, newStatus) {
    event.stopPropagation();
    const index = revisoesVehicles.findIndex(v => v.id === id);
    if (index > -1) {
        revisoesVehicles[index].mainStatus = newStatus;
        
        // Atualizar label/tipo conforme novo status
        if(newStatus === 'andamento') {
            revisoesVehicles[index].subStatusLabel = "Em Andamento";
            revisoesVehicles[index].subStatusType = "wait";
        } else if (newStatus === 'resolvido') {
            revisoesVehicles[index].subStatusLabel = "Concluído";
            revisoesVehicles[index].subStatusType = "done";
        } else {
            revisoesVehicles[index].subStatusLabel = "Reaberto / Pendente";
            revisoesVehicles[index].subStatusType = "action";
        }

        saveRevisoesData();
        
        if (window.showToast) {
            const statusLabels = {
                'pendente': 'Pendente',
                'andamento': 'Em Andamento',
                'resolvido': 'Resolvido'
            };
            showToast('success', `Status alterado para: ${statusLabels[newStatus]}`);
        }
    }
}

// --- INICIALIZAÇÃO ---

// Função para inicializar a aba de revisões quando for aberta
function initRevisoesTab() {
    console.log('🔧 Iniciando aba de revisões...');
    
    // Verificar se container existe
    const container = document.getElementById('revisoes-list-container');
    const revisoesContent = document.getElementById('revisoes-content');
    
    console.log('📋 Verificações:');
    console.log('  - Container revisoes-list-container:', container ? '✅ Existe' : '❌ Não encontrado');
    console.log('  - Content revisoes-content:', revisoesContent ? '✅ Existe' : '❌ Não encontrado');
    console.log('  - Content está visível?', revisoesContent && !revisoesContent.classList.contains('hidden') ? '✅ Sim' : '❌ Não');
    
    // Carregar dados
    loadRevisoesData();
    console.log('📊 Dados carregados:', revisoesVehicles.length, 'chamados');
    
    // Garantir que elementos DOM estejam disponíveis e visíveis
    setTimeout(() => {
        // Ativar aba Pendente
        setRevisoesMainTab('pendente');
        console.log('  - Tab pendente ativada');
        
        // Ativar categoria Todos
        setRevisoesCategory('all');
        console.log('  - Categoria all ativada');
        
        // Forçar aplicação de filtros
        const filteredCount = applyRevisoesFilters();
        console.log('  - Filtros aplicados, cards renderizados:', filteredCount);
        
        console.log('✅ Aba de Revisões PRONTA');
    }, 100);
}

// Expor funções globalmente
window.initRevisoesTab = initRevisoesTab;
window.loadRevisoesData = loadRevisoesData;
window.saveRevisoesData = saveRevisoesData;
window.setRevisoesMainTab = setRevisoesMainTab;
window.setRevisoesCategory = setRevisoesCategory;
window.setRevisoesAprovacao = setRevisoesAprovacao; // NOVO: Exportar função de filtro de aprovação
window.applyRevisoesFilters = applyRevisoesFilters;
window.toggleRevisoesDetails = toggleRevisoesDetails;
window.openRevisoesModal = openRevisoesModal;
window.closeRevisoesModal = closeRevisoesModal;
window.saveRevisoesVehicle = saveRevisoesVehicle;
window.editRevisoesVehicle = editRevisoesVehicle;
window.deleteRevisoesVehicle = deleteRevisoesVehicle;
window.changeRevisoesStatus = changeRevisoesStatus;

console.log('📦 Sistema de Revisões carregado - v2.0');
console.log('✅ Funções exportadas:', {
    initRevisoesTab: typeof window.initRevisoesTab,
    loadRevisoesData: typeof window.loadRevisoesData,
    setRevisoesAprovacao: typeof window.setRevisoesAprovacao,
    applyRevisoesFilters: typeof window.applyRevisoesFilters
});
