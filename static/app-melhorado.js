// ============================================================================
// SISTEMA ANTI-DUPLICIDADE PARA SAÍDAS DE VEÍCULOS
// Funções auxiliares para prevenir duplicação de motoristas e veículos
// ============================================================================

// ============================================================================
// FUNCIONALIDADES BÁSICAS (substituem app.js)
// ============================================================================

// Botão "Usar Hora Atual"
document.addEventListener('DOMContentLoaded', () => {
    const btnAgora = document.getElementById('btn-agora');
    const saidaHorarioInput = document.getElementById('saida-horario');
    
    if (btnAgora && saidaHorarioInput) {
        btnAgora.addEventListener('click', () => {
            const now = new Date();
            const hours = String(now.getHours()).padStart(2, '0');
            const minutes = String(now.getMinutes()).padStart(2, '0');
            saidaHorarioInput.value = `${hours}:${minutes}`;
        });
    }
    
    // Forçar uppercase no input de placa de SAÍDA
    const veiculoInput = document.getElementById('saida-veiculo');
    if (veiculoInput) {
        veiculoInput.addEventListener('input', (e) => {
            e.target.value = e.target.value.toUpperCase();
        });
    }
    
    // Capitalizar primeira letra do nome do motorista
    const motoristaInput = document.getElementById('saida-motorista');
    if (motoristaInput) {
        motoristaInput.addEventListener('blur', (e) => {
            const value = e.target.value.trim();
            if (value) {
                // Capitaliza cada palavra
                e.target.value = value.split(' ')
                    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
                    .join(' ');
            }
        });
    }
    
    // Forçar uppercase no input de placa de ABASTECIMENTO
    const refuelPlacaInput = document.getElementById('quick-refuel-placa');
    if (refuelPlacaInput) {
        refuelPlacaInput.addEventListener('input', (e) => {
            e.target.value = e.target.value.toUpperCase();
        });
    }
    
    // Capitalizar motorista de ABASTECIMENTO
    const refuelMotoristaInput = document.getElementById('quick-refuel-motorista');
    if (refuelMotoristaInput) {
        refuelMotoristaInput.addEventListener('blur', (e) => {
            const value = e.target.value.trim();
            if (value) {
                e.target.value = value.split(' ')
                    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
                    .join(' ');
            }
        });
    }
    
    console.log('✅ Funcionalidades básicas inicializadas');
});

// ============================================================================
// FUNÇÕES DE NORMALIZAÇÃO
// ============================================================================

/**
 * Normaliza nome de motorista para comparação
 * Remove acentos, converte para lowercase e remove espaços extras
 */
function normalizeMotorista(nome) {
    if (!nome) return '';
    return nome
        .trim()
        .toLowerCase()
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '') // Remove acentos
        .replace(/\s+/g, ' '); // Normaliza espaços
}

/**
 * Normaliza placa para comparação
 */
function normalizePlaca(placa) {
    if (!placa) return '';
    return placa.trim().toUpperCase().replace(/[^A-Z0-9]/g, '');
}

/**
 * Destaca visualmente um veículo em curso na tabela
 */
function highlightVeiculoEmCurso(placa) {
    const row = document.getElementById(`veiculo-${encodeURIComponent(placa)}`);
    if (row) {
        // Adiciona animação de destaque
        row.style.transition = 'all 0.3s ease';
        row.style.backgroundColor = '#FEF3C7'; // Amarelo claro
        row.style.boxShadow = '0 0 20px rgba(251, 191, 36, 0.5)';
        
        // Scroll suave até o elemento
        row.scrollIntoView({ behavior: 'smooth', block: 'center' });
        
        // Remove o destaque após 3 segundos
        setTimeout(() => {
            row.style.backgroundColor = '';
            row.style.boxShadow = '';
        }, 3000);
    }
}

/**
 * Exibe mensagem usando o sistema de toast ou fallback
 */
function exibirMensagem(mensagem, tipo) {
    if (typeof showToast === 'function') {
        showToast(tipo, mensagem);
    } else if (window.showToast) {
        window.showToast(tipo, mensagem);
    } else {
        // Fallback: alert
        alert(mensagem);
    }
}

/**
 * Exibe modal de confirmação customizado para duplicidade de motorista
 */
function confirmarDuplicidadeMotorista(motorista, veiculoEmCurso, horarioSaida) {
    return new Promise((resolve) => {
        const message = 
            `⚠️ ATENÇÃO: POSSÍVEL DUPLICIDADE!\n\n` +
            `O motorista "${motorista}" já está em viagem:\n\n` +
            `🚗 Veículo: ${veiculoEmCurso}\n` +
            `🕐 Horário de Saída: ${horarioSaida}\n\n` +
            `⚠️ Registrar outra saída pode causar duplicidade nos registros!\n\n` +
            `🔍 Verifique se:\n` +
            `  • O motorista já registrou a chegada da viagem anterior\n` +
            `  • É realmente necessário um segundo registro (ex: ajudante)\n` +
            `  • O nome do motorista está correto\n\n` +
            `Deseja CONTINUAR mesmo assim?`;
        
        resolve(confirm(message));
    });
}

/**
 * Valida se há duplicidade de veículo ou motorista antes de registrar saída
 * Retorna objeto com resultado da validação
 */
async function validarDuplicidadeSaida(veiculo, motorista) {
    try {
        // Buscar veículos em curso
        const resp = await fetch('/api/veiculos_em_curso');
        if (!resp.ok) {
            throw new Error('Não foi possível validar veículos em curso.');
        }
        const veiculosEmCurso = await resp.json();
        
        const veiculoNormalizado = normalizePlaca(veiculo);
        const motoristaNormalizado = normalizeMotorista(motorista);
        
        // 🚗 VALIDAÇÃO 1: Verificar VEÍCULO em curso
        const veiculoEmCurso = veiculosEmCurso.find(v => 
            normalizePlaca(v.veiculo) === veiculoNormalizado
        );
        
        if (veiculoEmCurso) {
            return {
                valido: false,
                tipo: 'veiculo',
                mensagem: 
                    `🚫 VEÍCULO JÁ EM USO!\n\n` +
                    `O veículo ${veiculo} já está em curso:\n\n` +
                    `👤 Motorista: ${veiculoEmCurso.motorista}\n` +
                    `🕐 Saída: ${veiculoEmCurso.horarioSaida}\n\n` +
                    `➡️ Registre a CHEGADA primeiro antes de uma nova saída!`,
                veiculoDestaque: veiculoEmCurso.veiculo
            };
        }
        
        // 👤 VALIDAÇÃO 2: Verificar MOTORISTA em curso
        const motoristaEmCurso = veiculosEmCurso.find(v => 
            normalizeMotorista(v.motorista) === motoristaNormalizado
        );
        
        if (motoristaEmCurso) {
            return {
                valido: false,
                tipo: 'motorista',
                mensagem: 'Motorista já em viagem',
                motoristaInfo: {
                    nome: motorista,
                    veiculo: motoristaEmCurso.veiculo,
                    horario: motoristaEmCurso.horarioSaida
                },
                veiculoDestaque: motoristaEmCurso.veiculo,
                requerConfirmacao: true
            };
        }
        
        return { valido: true };
        
    } catch (error) {
        console.error('Erro na validação de duplicidade:', error);
        throw error;
    }
}

// ============================================================================
// INTEGRAÇÃO COM FORMULÁRIO DE SAÍDA (app.js)
// ============================================================================

/**
 * Adiciona validações de duplicidade ao formulário de saída
 * Deve ser chamado após o DOM estar carregado
 */
function adicionarValidacoesDuplicidade() {
    const formSaida = document.getElementById('form-saida');
    if (!formSaida) return;
    
    // Remove listener antigo se existir
    const oldSubmit = formSaida.getAttribute('data-anti-dup-enabled');
    if (oldSubmit === 'true') return;
    
    formSaida.setAttribute('data-anti-dup-enabled', 'true');
    
    // Intercepta o submit
    formSaida.addEventListener('submit', async (event) => {
        event.preventDefault();
        event.stopPropagation();
        
        const formData = new FormData(formSaida);
        const veiculo = formData.get('veiculo')?.trim().toUpperCase();
        const motorista = formData.get('motorista')?.trim();
        const solicitante = formData.get('solicitante')?.trim();
        const trajeto = formData.get('trajeto')?.trim();
        const horario = formData.get('horario') || null;
        
        // Coleta categoria e seção (com suporte a customização)
        const veiculoCategoriaSelect = document.getElementById('saida-veiculo-categoria');
        const veiculoCategoriaCustom = document.getElementById('saida-veiculo-categoria-custom');
        const motoristaSecaoSelect = document.getElementById('saida-motorista-secao');
        const motoristaSecaoCustom = document.getElementById('saida-motorista-secao-custom');
        
        let veiculo_categoria = 'Outros';
        if (veiculoCategoriaSelect) {
            if (veiculoCategoriaSelect.value === '__NOVA__') {
                if (!veiculoCategoriaCustom || !veiculoCategoriaCustom.value.trim()) {
                    exibirMensagem('⚠️ Digite o nome da nova categoria do veículo.', 'error');
                    if (veiculoCategoriaCustom) veiculoCategoriaCustom.focus();
                    return;
                }
                veiculo_categoria = veiculoCategoriaCustom.value.trim();
            } else {
                veiculo_categoria = veiculoCategoriaSelect.value || 'Outros';
            }
        }
        
        let motorista_secao = 'Outros';
        if (motoristaSecaoSelect) {
            if (motoristaSecaoSelect.value === '__NOVA__') {
                if (!motoristaSecaoCustom || !motoristaSecaoCustom.value.trim()) {
                    exibirMensagem('⚠️ Digite o nome da nova seção do motorista.', 'error');
                    if (motoristaSecaoCustom) motoristaSecaoCustom.focus();
                    return;
                }
                motorista_secao = motoristaSecaoCustom.value.trim();
            } else {
                motorista_secao = motoristaSecaoSelect.value || 'Outros';
            }
        }
        
        // Validações básicas
        if (!veiculo) {
            exibirMensagem('⚠️ Informe a placa do veículo.', 'error');
            return;
        }
        
        if (!motorista) {
            exibirMensagem('⚠️ Informe o nome do motorista.', 'error');
            return;
        }
        
        try {
            // === VALIDAÇÃO DE DUPLICIDADE ===
            const validacao = await validarDuplicidadeSaida(veiculo, motorista);
            
            if (!validacao.valido) {
                // Veículo duplicado - BLOQUEIA
                if (validacao.tipo === 'veiculo') {
                    exibirMensagem(validacao.mensagem, 'error');
                    if (validacao.veiculoDestaque) {
                        highlightVeiculoEmCurso(validacao.veiculoDestaque);
                    }
                    return;
                }
                
                // Motorista duplicado - CONFIRMA
                if (validacao.tipo === 'motorista' && validacao.requerConfirmacao) {
                    const info = validacao.motoristaInfo;
                    const confirmar = await confirmarDuplicidadeMotorista(
                        info.nome,
                        info.veiculo,
                        info.horario
                    );
                    
                    if (!confirmar) {
                        exibirMensagem(
                            '❌ Registro cancelado para evitar duplicidade.\n' +
                            'Verifique a viagem em curso antes de tentar novamente.', 
                            'warning'
                        );
                        if (validacao.veiculoDestaque) {
                            highlightVeiculoEmCurso(validacao.veiculoDestaque);
                        }
                        return;
                    }
                    // Se confirmou, continua o registro
                }
            }
            
            // === REGISTRO DA SAÍDA ===
            
            // Confirmação detalhada antes de registrar
            const horarioTexto = horario || 'Agora';
            const confirmed = await showDetailedConfirm({
                title: '🚗 Confirmar Saída',
                type: 'saida',
                data: {
                    placa: veiculo,
                    motorista: motorista,
                    solicitante: solicitante,
                    trajeto: trajeto,
                    horario: horarioTexto
                }
            });
            
            if (!confirmed) {
                exibirMensagem('ℹ️ Registro cancelado', 'info');
                return;
            }
            
            const data = {
                veiculo,
                motorista,
                solicitante,
                trajeto,
                horario,
                veiculo_categoria,
                motorista_secao
            };
            
            const response = await fetch('/api/saida', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            
            const result = await response.json();
            
            if (response.ok) {
                exibirMensagem('✅ ' + result.message, 'success');
                formSaida.reset();
                
                // Atualiza a lista imediatamente + Firebase real-time também vai atualizar
                if (typeof fetchVeiculosEmCurso === 'function') {
                    fetchVeiculosEmCurso();
                }
                console.log('✅ Saída registrada - Lista atualizada');
            } else {
                exibirMensagem('❌ ' + (result.error || 'Erro ao registrar saída'), 'error');
            }
            
        } catch (error) {
            console.error('Erro ao processar saída:', error);
            exibirMensagem(
                '❌ ' + (error.message || 'Erro de conexão com o servidor'), 
                'error'
            );
        }
    }, true); // useCapture = true para interceptar antes
}

/**
 * Adiciona indicador visual de veículos/motoristas em curso nos inputs
 */
function adicionarIndicadoresVisuais() {
    const veiculoInput = document.getElementById('saida-veiculo');
    const motoristaInput = document.getElementById('saida-motorista');
    
    if (veiculoInput) {
        veiculoInput.addEventListener('blur', async () => {
            const veiculo = veiculoInput.value.trim().toUpperCase();
            if (!veiculo) return;
            
            try {
                const resp = await fetch('/api/veiculos_em_curso');
                if (!resp.ok) return;
                const veiculosEmCurso = await resp.json();
                
                const estaEmCurso = veiculosEmCurso.find(v => 
                    normalizePlaca(v.veiculo) === normalizePlaca(veiculo)
                );
                
                if (estaEmCurso) {
                    veiculoInput.style.borderColor = '#DC2626';
                    veiculoInput.style.backgroundColor = '#FEE2E2';
                    veiculoInput.title = `⚠️ Este veículo já está em curso com ${estaEmCurso.motorista}`;
                } else {
                    veiculoInput.style.borderColor = '';
                    veiculoInput.style.backgroundColor = '';
                    veiculoInput.title = '';
                }
            } catch (error) {
                console.error('Erro ao verificar veículo:', error);
            }
        });
    }
    
    if (motoristaInput) {
        motoristaInput.addEventListener('blur', async () => {
            const motorista = motoristaInput.value.trim();
            if (!motorista) return;
            
            try {
                const resp = await fetch('/api/veiculos_em_curso');
                if (!resp.ok) return;
                const veiculosEmCurso = await resp.json();
                
                const estaEmCurso = veiculosEmCurso.find(v => 
                    normalizeMotorista(v.motorista) === normalizeMotorista(motorista)
                );
                
                if (estaEmCurso) {
                    motoristaInput.style.borderColor = '#F59E0B';
                    motoristaInput.style.backgroundColor = '#FEF3C7';
                    motoristaInput.title = `⚠️ Este motorista já está em viagem no veículo ${estaEmCurso.veiculo}`;
                } else {
                    motoristaInput.style.borderColor = '';
                    motoristaInput.style.backgroundColor = '';
                    motoristaInput.title = '';
                }
            } catch (error) {
                console.error('Erro ao verificar motorista:', error);
            }
        });
    }
}

/**
 * Adiciona contador de veículos em curso no topo da página
 */
function adicionarContadorVisuais() {
    const header = document.querySelector('h1');
    if (!header || document.getElementById('contador-em-curso')) return;
    
    const contador = document.createElement('div');
    contador.id = 'contador-em-curso';
    contador.className = 'inline-flex items-center ml-4 px-4 py-2 bg-indigo-100 text-indigo-800 rounded-full text-sm font-semibold';
    contador.innerHTML = '🚗 <span id="total-em-curso">-</span> em curso';
    
    header.appendChild(contador);
    
    // Atualiza periodicamente APENAS se usuário ativo
    let lastUserActivity = Date.now();
    let pollingActive = true;
    
    // Monitora atividade (incluindo focus em inputs)
    ['mousedown', 'keypress', 'click', 'focus', 'input'].forEach(event => {
        document.addEventListener(event, () => {
            lastUserActivity = Date.now();
            if (!pollingActive) {
                pollingActive = true;
                console.log('🔄 Reativando polling');
            }
        }, event === 'focus' || event === 'input' ? true : { passive: true });
    });
    
    setInterval(async () => {
        // Para polling após 5min de inatividade
        if (Date.now() - lastUserActivity > 5 * 60 * 1000) {
            if (pollingActive) {
                pollingActive = false;
                console.warn('⚠️ Polling desligado por inatividade');
            }
            return;
        }
        
        if (!pollingActive) return;
        
        try {
            const resp = await fetch('/api/veiculos_em_curso');
            if (!resp.ok) return;
            const veiculos = await resp.json();
            const total = document.getElementById('total-em-curso');
            if (total) {
                total.textContent = veiculos.length;
            }
        } catch (error) {
            console.error('Erro ao atualizar contador:', error);
        }
    }, 30000); // Aumentado para 30 segundos (era 5)
}

// ============================================================================
// INICIALIZAÇÃO
// ============================================================================

// Aguarda o DOM e o app.js estarem prontos
let tentativas = 0;
const MAX_TENTATIVAS = 20; // 2 segundos (20 × 100ms) - reduzido

function inicializarAntiDuplicidade() {
    // Verifica se app.js já carregou (qualquer função global dele serve)
    const appJsCarregou = typeof showResponseMessage === 'function' || 
                          document.getElementById('form-saida') !== null;
    
    if (!appJsCarregou) {
        tentativas++;
        
        if (tentativas < MAX_TENTATIVAS) {
            if (tentativas === 1 || tentativas % 5 === 0) {
                console.log(`⏳ Aguardando app.js carregar... (${tentativas}/${MAX_TENTATIVAS})`);
            }
            setTimeout(inicializarAntiDuplicidade, 100);
        } else {
            console.warn('⚠️ app.js não carregou em 2 segundos - anti-duplicidade desabilitado');
        }
        return;
    }
    
    console.log('✅ Anti-duplicidade inicializado');
    adicionarValidacoesDuplicidade();
    adicionarIndicadoresVisuais();
    adicionarContadorVisuais();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        setTimeout(inicializarAntiDuplicidade, 200);
    });
} else {
    setTimeout(inicializarAntiDuplicidade, 200);
}

// Exporta funções para uso global
window.validarDuplicidadeSaida = validarDuplicidadeSaida;
window.normalizeMotorista = normalizeMotorista;
window.normalizePlaca = normalizePlaca;
window.highlightVeiculoEmCurso = highlightVeiculoEmCurso;
