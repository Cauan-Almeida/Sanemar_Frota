// JavaScript para a aba de Usuários no Dashboard

let usuariosCache = [];

// Carrega lista de usuários
async function loadUsuariosData() {
    try {
        const response = await fetch('/api/usuarios');
        const usuarios = await response.json();
        
        // Guardar no cache
        usuariosCache = usuarios;
        
        // Renderizar
        renderUsuarios(usuarios);
        
    } catch (error) {
        console.error('Erro ao carregar usuários:', error);
        const tabelaBody = document.getElementById('tabela-usuarios');
        if (tabelaBody) {
            tabelaBody.innerHTML = '<tr><td colspan="6" class="p-4 text-center text-red-500">Erro ao carregar dados</td></tr>';
        }
    }
}

function renderUsuarios(usuarios) {
    const tabelaBody = document.getElementById('tabela-usuarios');
    if (!tabelaBody) return;
    
    tabelaBody.innerHTML = '';
    
    if (usuarios.length === 0) {
        tabelaBody.innerHTML = '<tr><td colspan="6" class="p-4 text-center text-gray-500">Nenhum usuário encontrado</td></tr>';
        return;
    }
    
    // Separar ativos e inativos
    const usuariosAtivos = usuarios.filter(u => u.ativo !== false).sort((a, b) => a.nome_completo.localeCompare(b.nome_completo));
    const usuariosInativos = usuarios.filter(u => u.ativo === false).sort((a, b) => a.nome_completo.localeCompare(b.nome_completo));
    
    // Renderizar usuários ativos
    usuariosAtivos.forEach(usuario => {
        tabelaBody.appendChild(criarLinhaUsuario(usuario, true));
    });
    
    // Adicionar divisor se houver inativos
    if (usuariosInativos.length > 0) {
        const divisorTr = document.createElement('tr');
        divisorTr.className = 'bg-gray-200';
        divisorTr.innerHTML = `
            <td colspan="6" class="p-3 text-center font-bold text-gray-600">
                📦 USUÁRIOS INATIVOS (${usuariosInativos.length})
            </td>
        `;
        tabelaBody.appendChild(divisorTr);
        
        // Renderizar usuários inativos
        usuariosInativos.forEach(usuario => {
            tabelaBody.appendChild(criarLinhaUsuario(usuario, false));
        });
    }
}

function criarLinhaUsuario(usuario, ativo) {
    const tr = document.createElement('tr');
    tr.className = `border-b border-gray-100 hover:bg-indigo-50 transition-colors ${ativo ? '' : 'opacity-60'}`;
    
    const inativoLabel = ativo ? '' : ' [INATIVO]';
    
    // Tipo badge
    const tipoBadges = {
        'admin': '<span class="px-3 py-1 bg-red-100 text-red-700 rounded-full text-xs font-bold">🔑 Admin</span>',
        'historico': '<span class="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-xs font-bold">📊 Histórico</span>',
        'operador': '<span class="px-3 py-1 bg-green-100 text-green-700 rounded-full text-xs font-bold">👤 Operador</span>'
    };
    const tipoBadge = tipoBadges[usuario.tipo] || tipoBadges['operador'];
    
    // Status badge
    const statusBadge = ativo
        ? '<span class="px-3 py-1 bg-green-100 text-green-700 rounded-full text-xs font-bold">✅ Ativo</span>'
        : '<span class="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-xs font-bold">⭕ Inativo</span>';
    
    // Data de cadastro
    const dataCadastro = usuario.data_criacao ? new Date(usuario.data_criacao).toLocaleDateString('pt-BR') : '-';
    
    tr.innerHTML = `
        <td class="p-4 font-semibold text-gray-900">${usuario.nome_completo}${inativoLabel}</td>
        <td class="p-4 text-gray-700">${usuario.username}</td>
        <td class="p-4">${tipoBadge}</td>
        <td class="p-4">${statusBadge}</td>
        <td class="p-4 text-gray-600 text-sm">${dataCadastro}</td>
        <td class="p-4 flex gap-2">
            <button onclick="editarUsuario('${usuario.id}')" class="px-3 py-1 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm font-semibold transition-all" title="Editar">
                ✏️
            </button>
            <button onclick="resetarSenhaUsuario('${usuario.id}', '${usuario.username}')" class="px-3 py-1 bg-orange-500 hover:bg-orange-600 text-white rounded-lg text-sm font-semibold transition-all" title="Resetar Senha">
                🔐
            </button>
            <button onclick="toggleStatusUsuario('${usuario.id}', ${!ativo})" class="px-3 py-1 ${ativo ? 'bg-yellow-500 hover:bg-yellow-600' : 'bg-green-500 hover:bg-green-600'} text-white rounded-lg text-sm font-semibold transition-all" title="${ativo ? 'Desativar' : 'Ativar'}">
                ${ativo ? '📦' : '✅'}
            </button>
        </td>
    `;
    
    return tr;
}

// Pesquisar usuários
function pesquisarUsuarios() {
    const searchTerm = document.getElementById('search-usuarios')?.value.toLowerCase() || '';
    
    if (!usuariosCache || usuariosCache.length === 0) {
        console.warn('Cache de usuários vazio');
        return;
    }
    
    if (searchTerm.trim() === '') {
        renderUsuarios(usuariosCache);
        return;
    }
    
    const filtered = usuariosCache.filter(u => 
        (u.nome_completo && u.nome_completo.toLowerCase().includes(searchTerm)) ||
        (u.username && u.username.toLowerCase().includes(searchTerm)) ||
        (u.tipo && u.tipo.toLowerCase().includes(searchTerm))
    );
    
    renderUsuarios(filtered);
}

// Editar usuário
async function editarUsuario(id) {
    try {
        const usuario = usuariosCache.find(u => u.id === id);
        
        if (!usuario) {
            if (window.showToast) showToast('error', 'Usuário não encontrado');
            return;
        }
        
        // Preenche o formulário
        document.getElementById('usuario-username').value = usuario.username || '';
        document.getElementById('usuario-username').disabled = true; // Não pode mudar username
        document.getElementById('usuario-nome-completo').value = usuario.nome_completo || '';
        document.getElementById('usuario-password').value = ''; // Deixa vazio - só preenche se quiser trocar
        document.getElementById('usuario-password').required = false;
        document.getElementById('usuario-tipo').value = usuario.tipo || 'operador';
        
        // Adiciona campo hidden com ID
        let hiddenId = document.getElementById('usuario-id-edit');
        if (!hiddenId) {
            hiddenId = document.createElement('input');
            hiddenId.type = 'hidden';
            hiddenId.id = 'usuario-id-edit';
            document.getElementById('form-usuario').appendChild(hiddenId);
        }
        hiddenId.value = id;
        
        // Muda botão de submit
        const submitBtn = document.querySelector('#form-usuario button[type="submit"]');
        submitBtn.textContent = '💾 Atualizar Usuário';
        
        // Scroll para o formulário
        document.querySelector('#form-usuario').scrollIntoView({ behavior: 'smooth' });
        
    } catch (error) {
        console.error('Erro ao editar usuário:', error);
        if (window.showToast) showToast('error', 'Erro ao carregar dados do usuário');
    }
}

// Resetar senha
async function resetarSenhaUsuario(id, username) {
    const novaSenha = prompt(`Digite a nova senha para o usuário "${username}":`);
    
    if (!novaSenha) return;
    
    if (novaSenha.length < 6) {
        if (window.showToast) showToast('error', 'Senha deve ter no mínimo 6 caracteres');
        return;
    }
    
    if (!confirm(`Tem certeza que deseja resetar a senha de "${username}"?`)) return;
    
    try {
        const res = await fetch(`/api/usuarios/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password: novaSenha })
        });
        
        const result = await res.json();
        
        if (res.ok) {
            if (window.showToast) showToast('success', 'Senha resetada com sucesso');
        } else {
            if (window.showToast) showToast('error', result.error || 'Erro ao resetar senha');
        }
    } catch (error) {
        console.error('Erro ao resetar senha:', error);
        if (window.showToast) showToast('error', 'Erro de conexão');
    }
}

// Toggle status ativo/inativo
async function toggleStatusUsuario(id, novoStatus) {
    const usuario = usuariosCache.find(u => u.id === id);
    const acao = novoStatus ? 'ativar' : 'desativar';
    
    if (!confirm(`Tem certeza que deseja ${acao} o usuário "${usuario.username}"?`)) return;
    
    try {
        const res = await fetch(`/api/usuarios/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ativo: novoStatus })
        });
        
        const result = await res.json();
        
        if (res.ok) {
            if (window.showToast) showToast('success', `Usuário ${novoStatus ? 'ativado' : 'desativado'} com sucesso`);
            await loadUsuariosData();
        } else {
            if (window.showToast) showToast('error', result.error || 'Erro ao atualizar status');
        }
    } catch (error) {
        console.error('Erro ao atualizar status:', error);
        if (window.showToast) showToast('error', 'Erro de conexão');
    }
}

// Form handling
document.addEventListener('DOMContentLoaded', () => {
    const formUsuario = document.getElementById('form-usuario');
    if (formUsuario) {
        formUsuario.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const username = document.getElementById('usuario-username').value.trim();
            const nomeCompleto = document.getElementById('usuario-nome-completo').value.trim();
            const password = document.getElementById('usuario-password').value.trim();
            const tipo = document.getElementById('usuario-tipo').value;
            const hiddenId = document.getElementById('usuario-id-edit');
            const editandoId = hiddenId ? hiddenId.value : '';
            
            if (!username || !nomeCompleto || !tipo) {
                if (window.showToast) showToast('error', 'Preencha todos os campos obrigatórios');
                return;
            }
            
            if (!editandoId && !password) {
                if (window.showToast) showToast('error', 'Senha é obrigatória para novo usuário');
                return;
            }
            
            if (password && password.length < 6) {
                if (window.showToast) showToast('error', 'Senha deve ter no mínimo 6 caracteres');
                return;
            }
            
            try {
                let res;
                const payload = {
                    username,
                    nome_completo: nomeCompleto,
                    tipo
                };
                
                if (password) {
                    payload.password = password;
                }
                
                if (editandoId) {
                    // Atualizar
                    res = await fetch(`/api/usuarios/${editandoId}`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload)
                    });
                } else {
                    // Criar
                    res = await fetch('/api/usuarios', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload)
                    });
                }
                
                const result = await res.json();
                
                if (res.ok) {
                    if (window.showToast) showToast('success', editandoId ? 'Usuário atualizado com sucesso' : 'Usuário cadastrado com sucesso');
                    
                    // Limpa formulário
                    formUsuario.reset();
                    document.getElementById('usuario-username').disabled = false;
                    document.getElementById('usuario-password').required = true;
                    if (hiddenId) hiddenId.remove();
                    
                    const submitBtn = formUsuario.querySelector('button[type="submit"]');
                    submitBtn.textContent = '➕ Cadastrar Usuário';
                    
                    // Recarrega lista
                    await loadUsuariosData();
                } else {
                    if (window.showToast) showToast('error', result.error || 'Erro ao salvar usuário');
                }
            } catch (error) {
                console.error('Erro ao salvar usuário:', error);
                if (window.showToast) showToast('error', 'Erro de conexão');
            }
        });
    }
    
    // Carrega usuários quando a aba for aberta
    const usuariosTab = document.querySelector('[data-tab="usuarios"]');
    if (usuariosTab) {
        usuariosTab.addEventListener('click', () => {
            if (usuariosCache.length === 0) {
                loadUsuariosData();
            }
        });
    }
});

// Inicializar quando o DOM estiver pronto
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        // Já inicializado acima
    });
} else {
    // DOM já está pronto
    console.log('✅ Módulo de usuários carregado');
}
