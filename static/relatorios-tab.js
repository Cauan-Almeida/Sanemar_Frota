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

    // Form Revisões
    const formRevisoes = document.getElementById('form-revisoes');
    if (formRevisoes) {
        formRevisoes.addEventListener('submit', (e) => {
            e.preventDefault();
            const veiculo = document.getElementById('revisoes-veiculo').value.trim();
            const status = document.getElementById('revisoes-status').value;
            
            let url = '/pdf/revisoes?';
            const params = [];
            
            if (veiculo) params.push(`veiculo=${encodeURIComponent(veiculo)}`);
            if (status) params.push(`status=${status}`);
            
            url += params.join('&');
            window.open(url, '_blank');
        });
    }
}

// Inicializar quando o DOM estiver pronto
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initRelatoriosTab);
} else {
    initRelatoriosTab();
}
