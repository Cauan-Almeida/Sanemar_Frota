# 🔐 Sistema de Autenticação para Index (Lançamentos)

## 📋 Problema Atual

**Situação:**
- Qualquer pessoa pode acessar `/` e fazer lançamentos
- Qualquer pessoa pode marcar chegada de qualquer veículo
- Não há controle de quem fez cada ação
- Pessoas demitidas ainda têm acesso ao sistema
- Não há rastreabilidade de ações

**Riscos:**
- ❌ Lançamentos duplicados ou incorretos
- ❌ Chegadas marcadas pela pessoa errada
- ❌ Ex-funcionários com acesso total
- ❌ Falta de auditoria (quem fez o quê?)
- ❌ Dados podem ser alterados maliciosamente

---

## 🎯 Objetivos

1. **Autenticação Simples** - Login rápido sem complicação
2. **Sessão Persistente** - Não deslogar durante o expediente
3. **Controle de Acesso** - Bloquear pessoas demitidas
4. **Rastreabilidade** - Saber quem fez cada ação
5. **Profissionalismo** - Sistema confiável e seguro

---

## 💡 Soluções Propostas

### **Opção 1: Login com Usuário/Senha (RECOMENDADO)**

#### Como Funciona:
1. Ao acessar `/`, usuário vê tela de login
2. Digite **usuário** e **senha**
3. Sistema valida no banco (tabela `usuarios`)
4. Cria **sessão persistente** (cookie de 12 horas)
5. Durante o expediente, não pede login novamente
6. Administrador pode **desativar usuários** demitidos

#### Vantagens:
- ✅ Seguro e profissional
- ✅ Já existe tabela de usuários no sistema
- ✅ Fácil gerenciar usuários (aba Usuários no dashboard)
- ✅ Pode rastrear quem fez cada lançamento
- ✅ Cookie persiste por horas (não desconecta)

#### Desvantagens:
- ⚠️ Usuário precisa lembrar senha
- ⚠️ Precisa cadastrar todos os operadores primeiro

#### Implementação:
```python
# app.py - Novo endpoint de login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Valida usuário no Firestore
        user = validate_user(username, password)
        
        if user and user['ativo']:
            session['user_id'] = user['id']
            session['username'] = username
            session['tipo'] = user['tipo']
            session.permanent = True  # Sessão de 12 horas
            return redirect('/')
        else:
            flash('Usuário ou senha incorretos')
    
    return render_template('login.html')

# Proteção na rota principal
@app.route('/')
@requires_auth  # Redireciona para /login se não autenticado
def index():
    username = session.get('username')
    return render_template('index.html', username=username)
```

#### Fluxo de Uso:
```
1. Operador abre navegador → /login
2. Digita "joao.silva" e senha "1234"
3. Sistema valida e cria sessão de 12h
4. Redirecionado para / (lançamentos)
5. Trabalha o dia todo sem deslogar
6. Ao final do dia, fecha navegador
7. No próximo dia, faz login novamente
```

---

### **Opção 2: Login com PIN Rápido**

#### Como Funciona:
1. Cada operador tem **PIN de 4 dígitos**
2. Tela inicial mostra **teclado numérico**
3. Digita PIN → entra no sistema
4. Sessão persistente por 12 horas

#### Vantagens:
- ✅ Login super rápido (4 dígitos)
- ✅ Não precisa lembrar senha complexa
- ✅ Visual pode ser touchscreen-friendly
- ✅ Pode ter botões grandes para tablet

#### Desvantagens:
- ⚠️ Menos seguro (PIN de 4 dígitos)
- ⚠️ Precisa adicionar campo `pin` na tabela usuarios
- ⚠️ Alguém pode ver PIN sendo digitado

#### Implementação:
```html
<!-- Teclado numérico na tela de login -->
<div class="pin-pad">
    <button onclick="addDigit(1)">1</button>
    <button onclick="addDigit(2)">2</button>
    <button onclick="addDigit(3)">3</button>
    ...
    <button onclick="clearPin()">Limpar</button>
    <button onclick="submitPin()">Entrar</button>
</div>
```

---

### **Opção 3: Seleção de Usuário (Sem Senha)**

#### Como Funciona:
1. Tela mostra **lista de operadores ativos**
2. Operador clica no seu nome
3. Entra no sistema sem senha
4. Sistema registra quem está usando

#### Vantagens:
- ✅ Login instantâneo (1 clique)
- ✅ Zero fricção
- ✅ Fácil para quem não sabe tecnologia

#### Desvantagens:
- ❌ ZERO segurança
- ❌ Qualquer pessoa pode entrar como outra
- ❌ Não resolve o problema de confiabilidade
- ❌ NÃO RECOMENDADO para ambiente profissional

---

## 🏆 Recomendação Final: **Opção 1 (Usuário/Senha)**

### Por quê?
1. **Segurança Adequada** - Senha protege contra uso indevido
2. **Sistema Já Existe** - Tabela `usuarios` já tem tudo necessário
3. **Gerenciamento Fácil** - Aba Usuários permite criar/desativar
4. **Profissional** - Padrão da indústria
5. **Rastreável** - Cada ação tem autor identificado

### Campos Necessários na Sessão:
```python
session = {
    'user_id': 'abc123',
    'username': 'joao.silva',
    'nome_completo': 'João da Silva',
    'tipo': 'operador',  # operador, historico, admin
    'ativo': True
}
```

---

## 🔒 Melhorias no Sistema de Chegadas

### Problema:
**Qualquer pessoa pode marcar chegada de qualquer veículo**

### Solução 1: **Confirmação com Nome**
```
Ao clicar "Marcar Chegada":
1. Modal pergunta: "Quem está marcando esta chegada?"
2. Campo de texto: Digite seu nome
3. Sistema compara com session['username']
4. Se bater, permite; se não, bloqueia
```

### Solução 2: **Apenas Motorista ou Admin**
```
Regra de negócio:
- Motorista pode marcar APENAS suas próprias chegadas
- Admin pode marcar qualquer chegada
- Operador NÃO pode marcar chegadas

if (session['tipo'] == 'admin'):
    # Pode tudo
elif (viagem['motorista'] == session['nome_completo']):
    # Motorista pode marcar sua própria chegada
else:
    # Bloqueado
    flash('Você só pode marcar suas próprias chegadas')
```

### Solução 3: **Senha ao Marcar Chegada**
```
Ao clicar "Marcar Chegada":
1. Modal pede: "Digite sua senha para confirmar"
2. Sistema valida senha do usuário logado
3. Só permite se senha estiver correta
```

**Recomendação:** Solução 2 (Apenas Motorista ou Admin) - mais prático e seguro

---

## 📊 Rastreabilidade de Ações

### Adicionar Campo "Criado Por" e "Modificado Por"

```python
# Ao criar lançamento
saida = {
    'veiculo': 'ABC1234',
    'motorista': 'João',
    'criado_por': session['username'],  # ← NOVO
    'criado_em': datetime.now(),
    'modificado_por': None,
    'modificado_em': None
}

# Ao marcar chegada
db.collection('saidas').document(id).update({
    'timestampChegada': datetime.now(),
    'modificado_por': session['username'],  # ← NOVO
    'modificado_em': datetime.now()
})
```

### Exibir no Histórico
```
Registro de Saída:
🚗 SNV8E77 | João Silva | Sanemar → Araçatiba
👤 Lançado por: maria.santos em 27/01/2026 08:15
✅ Chegada por: joao.silva em 27/01/2026 16:30
```

---

## 🛡️ Gerenciamento de Usuários Demitidos

### No Dashboard (Aba Usuários):

#### Botão "Desativar" ao invés de "Excluir"
```python
# Ao invés de deletar:
db.collection('usuarios').document(id).delete()

# Apenas desativa:
db.collection('usuarios').document(id).update({
    'ativo': False,
    'desativado_em': datetime.now(),
    'desativado_por': session['username']
})
```

#### No Login:
```python
if user['ativo'] == False:
    flash('Seu acesso foi desativado. Entre em contato com o administrador.')
    return redirect('/login')
```

#### Vantagens:
- ✅ Histórico de ações preservado (não perde dados)
- ✅ Pode reativar se precisar
- ✅ Bloqueio imediato (não consegue mais logar)

---

## ⏱️ Sessão Persistente (Não Deslogar)

### Configuração no Flask:

```python
# app.py
from datetime import timedelta

app.config['SECRET_KEY'] = 'sua-chave-secreta-aqui'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=12)

@app.route('/login', methods=['POST'])
def login():
    # ... validação ...
    session.permanent = True  # Sessão dura 12 horas
    session['user_id'] = user_id
    return redirect('/')
```

### Como Funciona:
- Login às 07:00 → Sessão expira às 19:00
- Durante o expediente (07:00 - 17:00) → Não desconecta
- Fecha navegador → Sessão persiste (cookie)
- Reabre navegador → Ainda logado

### Logout Manual (opcional):
```html
<!-- Botão no header -->
<a href="/logout">🚪 Sair</a>
```

```python
@app.route('/logout')
def logout():
    session.clear()
    flash('Você saiu do sistema')
    return redirect('/login')
```

---

## 🎨 Interface de Login Proposta

### Design Simples e Profissional:

```
╔════════════════════════════════════╗
║                                    ║
║         🚗 FROTA SANEMAR          ║
║      Sistema de Lançamentos        ║
║                                    ║
║  ┌──────────────────────────────┐ ║
║  │ 👤 Usuário                   │ ║
║  │ [________________]           │ ║
║  │                              │ ║
║  │ 🔒 Senha                     │ ║
║  │ [________________]           │ ║
║  │                              │ ║
║  │    [ 🔐 Entrar ]             │ ║
║  └──────────────────────────────┘ ║
║                                    ║
║   Esqueceu a senha? Fale com o    ║
║        administrador               ║
║                                    ║
╚════════════════════════════════════╝
```

---

## 📝 Resumo da Proposta

### 🟢 O Que Muda:

1. **Tela de Login** no `/` (antes de lançamentos)
2. **Sessão de 12 horas** (não desconecta durante o dia)
3. **Rastreamento** de quem fez cada ação
4. **Botão Desativar** usuários (ao invés de excluir)
5. **Validação** ao marcar chegada (apenas motorista ou admin)

### 🟢 O Que NÃO Muda:

- Dashboard continua igual (já tem autenticação)
- Fluxo de lançamento continua o mesmo
- Banco de dados existente (só adiciona campos)
- Performance do sistema

### 🟢 Benefícios:

- ✅ **Segurança** - Só pessoas autorizadas acessam
- ✅ **Profissionalismo** - Sistema confiável
- ✅ **Rastreabilidade** - Sabe quem fez o quê
- ✅ **Controle** - Remove acesso de demitidos
- ✅ **Auditoria** - Histórico completo de ações

---

## 🚀 Próximos Passos (Quando Decidir Implementar)

1. Criar tela de login (`templates/login_index.html`)
2. Adicionar rota `/login` no `app.py`
3. Proteger rota `/` com `@requires_auth`
4. Adicionar campos `criado_por`, `modificado_por` nas saídas
5. Implementar validação de chegada (motorista ou admin)
6. Adicionar botão "Desativar" na aba Usuários
7. Configurar sessão persistente de 12 horas
8. Testar com usuários reais

---

## ❓ Dúvidas a Resolver

1. **Todos os operadores já têm cadastro na tabela `usuarios`?**
   - Se não, precisa cadastrar antes de implementar

2. **Prefere login com usuário/senha ou PIN?**
   - Recomendo usuário/senha por ser mais seguro

3. **Quer permitir "Esqueci minha senha"?**
   - Ou admin sempre reseta manualmente?

4. **Desativar usuário remove acesso ao Dashboard também?**
   - Sim, o mesmo usuário é usado nos dois lugares

5. **Quer exibir "Logado como: João Silva" no header?**
   - Para lembrar quem está usando o sistema

---

**Versão:** 1.0  
**Data:** Janeiro 2026  
**Status:** 📋 Proposta (não implementado ainda)
