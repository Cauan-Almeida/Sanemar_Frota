// JavaScript para a aba de Relatórios no Dashboard

function initRelatoriosTab() {
    // Form Abastecimentos
    const formAbast = document.getElementById('form-abastecimentos');
    if (formAbast) {
        formAbast.addEventListener('submit', (e) => {
            e.preventDefault();
            const veiculo = document.getElementById('abast-veiculo').value.trim();
            const dataInicio = document.getElementById('abast-data-inicio').value;
            const dataFim = document.getElementById('abast-data-fim').value;
            
            let url = '/pdf/abastecimentos?';
            const params = [];
            
            if (veiculo) params.push(`veiculo=${encodeURIComponent(veiculo)}`);
            if (dataInicio) params.push(`data_inicio=${dataInicio}T00:00:00`);
            if (dataFim) params.push(`data_fim=${dataFim}T23:59:59`);
            
            url += params.join('&');
            window.open(url, '_blank');
        });
    }

    // Form Saídas
    const formSaidas = document.getElementById('form-saidas');
    if (formSaidas) {
        formSaidas.addEventListener('submit', (e) => {
            e.preventDefault();
            const veiculo = document.getElementById('saidas-veiculo').value.trim();
            const motorista = document.getElementById('saidas-motorista').value.trim();
            const status = document.getElementById('saidas-status').value;
            const dataInicio = document.getElementById('saidas-data-inicio').value;
            const dataFim = document.getElementById('saidas-data-fim').value;
            
            let url = '/pdf/saidas?';
            const params = [];
            
            if (veiculo) params.push(`veiculo=${encodeURIComponent(veiculo)}`);
            if (motorista) params.push(`motorista=${encodeURIComponent(motorista)}`);
            if (status) params.push(`status=${status}`);
            if (dataInicio) params.push(`data_inicio=${dataInicio}T00:00:00`);
            if (dataFim) params.push(`data_fim=${dataFim}T23:59:59`);
            
            url += params.join('&');
            window.open(url, '_blank');
        });
    }

    // Form PDF Veículos
    const formPdfVeiculos = document.getElementById('form-pdf-veiculos');
    if (formPdfVeiculos) {
        formPdfVeiculos.addEventListener('submit', (e) => {
            e.preventDefault();
            const status = document.getElementById('select-pdf-veiculos-status').value;
            let url = `/pdf/veiculos?status=${status}`;
            window.open(url, '_blank');
        });
    }

    // Form Multas
    const formMultas = document.getElementById('form-multas');
    if (formMultas) {
        formMultas.addEventListener('submit', (e) => {
            e.preventDefault();
            const veiculo = document.getElementById('multas-veiculo').value.trim();
            const status = document.getElementById('multas-status').value;
            const dataInicio = document.getElementById('multas-data-inicio').value;
            const dataFim = document.getElementById('multas-data-fim').value;
            
            let url = '/pdf/multas?';
            const params = [];
            
            if (veiculo) params.push(`veiculo=${encodeURIComponent(veiculo)}`);
            if (status) params.push(`status=${status}`);
            if (dataInicio) params.push(`data_inicio=${dataInicio}T00:00:00`);
            if (dataFim) params.push(`data_fim=${dataFim}T23:59:59`);
            
            url += params.join('&');
            window.open(url, '_blank');
        });
    }

    // Form Revisões/Chamados
    const formRevisoes = document.getElementById('form-revisoes');
    if (formRevisoes) {
        formRevisoes.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            // Pega dados do LocalStorage (onde os chamados estão salvos)
            const stored = localStorage.getItem('fleetData_v1');
            
            let chamados = [];
            
            if (stored) {
                try {
                    chamados = JSON.parse(stored);
                } catch (e) {
                    console.error('[PDF] Erro ao carregar dados:', e);
                    alert('Erro ao carregar dados dos chamados');
                    return;
                }
            } else {
                alert('Nenhum chamado encontrado. Verifique se há dados na aba Revisões.');
                return;
            }
            
            // Aplicar filtros localmente
            const placaInput = document.getElementById('revisoes-placa');
            const statusInput = document.getElementById('revisoes-status-chamado');
            const categoriaInput = document.getElementById('revisoes-categoria');
            const aprovacaoInput = document.getElementById('revisoes-aprovacao');
            const direcionamentoInput = document.getElementById('revisoes-direcionamento');
            
            const placa = placaInput ? placaInput.value.trim().toUpperCase() : '';
            const status = statusInput ? statusInput.value : '';
            const categoria = categoriaInput ? categoriaInput.value : '';
            const aprovacao = aprovacaoInput ? aprovacaoInput.value : '';
            const direcionamento = direcionamentoInput ? direcionamentoInput.value : '';
            
            // Filtra chamados
            let chamadosFiltrados = chamados;
            
            if (placa) {
                chamadosFiltrados = chamadosFiltrados.filter(c => c.plate && c.plate.toUpperCase().includes(placa));
            }
            if (status) {
                // Se for 'pendente-andamento', aceita pendente OU em andamento
                if (status === 'pendente-andamento') {
                    chamadosFiltrados = chamadosFiltrados.filter(c => 
                        c.mainStatus === 'pendente' || c.mainStatus === 'andamento'
                    );
                } else {
                    chamadosFiltrados = chamadosFiltrados.filter(c => c.mainStatus === status);
                }
            }
            if (categoria) {
                chamadosFiltrados = chamadosFiltrados.filter(c => c.category === categoria);
            }
            if (aprovacao) {
                chamadosFiltrados = chamadosFiltrados.filter(c => c.aprovacao === aprovacao);
            }
            if (direcionamento) {
                chamadosFiltrados = chamadosFiltrados.filter(c => c.direcionamento === direcionamento);
            }
            
            // Envia via POST para gerar PDF
            try {
                const response = await fetch('/pdf/revisoes', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ chamados: chamadosFiltrados })
                });
                
                if (response.ok) {
                    // Baixa o PDF
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `chamados_manutencao_${new Date().toISOString().slice(0,10)}.pdf`;
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                } else {
                    const error = await response.json();
                    alert('Erro ao gerar PDF: ' + (error.error || 'Erro desconhecido'));
                }
            } catch (error) {
                console.error('Erro ao gerar PDF:', error);
                alert('Erro ao gerar PDF: ' + error.message);
            }
        });
    }
}

// Inicializar quando o DOM estiver pronto
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initRelatoriosTab);
} else {
    initRelatoriosTab();
}
