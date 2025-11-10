# 📖 Guia de Instalação - Sistema de Frota Sanemar

Guia completo passo a passo para instalação e configuração do sistema.

---

## 📋 Requisitos do Sistema

### Software Necessário
- **Python**: 3.11 ou superior
- **Git**: Última versão (opcional, mas recomendado)
- **Navegador**: Chrome, Firefox, Edge ou Safari (última versão)

### Contas Necessárias
- **Conta Google**: Para Firebase Console
- **Conta GitHub**: Para versionamento (opcional)
- **Conta Render.com**: Para deploy em produção (opcional)

---

## 🚀 Instalação Local (Desenvolvimento)

### Passo 1: Clone o Repositório

```bash
# Via HTTPS
git clone https://github.com/Cauan-Almeida/Sanemar_Frota.git

# Via SSH (se configurado)
git clone git@github.com:Cauan-Almeida/Sanemar_Frota.git

# Navegue para a pasta
cd Sanemar_Frota
```

**Sem Git?** Baixe o ZIP:
1. Acesse: https://github.com/Cauan-Almeida/Sanemar_Frota
2. Clique em "Code" → "Download ZIP"
3. Extraia o arquivo

---

### Passo 2: Crie Ambiente Virtual Python

#### Windows (PowerShell)
```powershell
# Crie o ambiente virtual
python -m venv venv

# Ative o ambiente
.\venv\Scripts\Activate.ps1

# Se erro de permissão:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### Windows (CMD)
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

#### Linux/Mac
```bash
python3 -m venv venv
source venv/bin/activate
```

**Verificar ativação**: O prompt deve mostrar `(venv)` no início.

---

### Passo 3: Instale Dependências Python

```bash
pip install -r requirements.txt
```

**Dependências instaladas**:
```
Flask==3.0.0
firebase-admin==6.2.0
google-cloud-firestore==2.13.0
google-cloud-storage==2.10.0
python-dotenv==1.0.0
waitress==2.1.2
Pillow==10.1.0
```

**Problemas comuns**:
- **Erro de SSL**: `pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt`
- **Erro de permissão**: Use `pip install --user -r requirements.txt`
- **Versão Python errada**: Confirme com `python --version` (deve ser 3.11+)

---

### Passo 4: Configure Firebase

#### 4.1 Crie Projeto Firebase

1. Acesse: https://console.firebase.google.com/
2. Clique em **"Adicionar projeto"**
3. Nome do projeto: `frota-sanemar` (ou outro)
4. Desative Google Analytics (opcional)
5. Clique em **"Criar projeto"**

#### 4.2 Ative Firestore Database

1. Menu lateral → **Firestore Database**
2. Clique em **"Criar banco de dados"**
3. Modo: **Produção** (regras podem ser ajustadas depois)
4. Local: **southamerica-east1** (São Paulo)
5. Clique em **"Ativar"**

#### 4.3 Ative Firebase Storage

1. Menu lateral → **Storage**
2. Clique em **"Começar"**
3. Aceite as regras padrão
4. Local: **southamerica-east1**
5. Clique em **"Concluído"**

#### 4.4 Baixe Credenciais do Projeto

1. Menu lateral → ⚙️ **Configurações do projeto**
2. Aba **"Contas de serviço"**
3. Clique em **"Gerar nova chave privada"**
4. Salve o arquivo JSON
5. **Renomeie para**: `firebase-credentials.json`
6. **Mova para a raiz do projeto** (pasta `Frota_sanemar/`)

**⚠️ IMPORTANTE**: NUNCA commite este arquivo no Git!

#### 4.5 Configure Regras de Segurança

**Firestore Rules**:
1. Console Firebase → **Firestore Database** → **Regras**
2. Cole o conteúdo de [`FIRESTORE_RULES.md`](FIRESTORE_RULES.md)
3. Clique em **"Publicar"**

**Storage Rules**:
```javascript
rules_version = '2';
service firebase.storage {
  match /b/{bucket}/o {
    match /{allPaths=**} {
      allow read, write: if request.auth != null;
    }
  }
}
```

---

### Passo 5: Configure Variáveis de Ambiente

Crie arquivo `.env` na raiz do projeto:

```env
# Flask Configuration
SECRET_KEY=gere_uma_chave_secreta_aleatoria_aqui_use_uuid4
FLASK_ENV=development

# Firebase
GOOGLE_APPLICATION_CREDENTIALS=firebase-credentials.json

# Autenticação (altere as senhas!)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=sanemar2024
HISTORICO_USERNAME=historico
HISTORICO_PASSWORD=hist123
```

**Gerar SECRET_KEY aleatória**:
```python
import secrets
print(secrets.token_hex(32))
```

Ou use: https://randomkeygen.com/ (CodeIgniter Encryption Keys)

---

### Passo 6: Configure Firebase no Frontend

Você precisa adicionar a configuração do Firebase nos arquivos HTML.

#### 6.1 Obtenha Config Firebase

1. Console Firebase → ⚙️ **Configurações do projeto**
2. Role até **"Seus apps"**
3. Se não houver app web, clique em **"</> Web"**
4. Registre app: Nome `Frota Sanemar Web`
5. **Copie o objeto `firebaseConfig`**

Exemplo:
```javascript
const firebaseConfig = {
  apiKey: "AIzaSyC...",
  authDomain: "frota-sanemar.firebaseapp.com",
  projectId: "frota-sanemar",
  storageBucket: "frota-sanemar.firebasestorage.app",
  messagingSenderId: "123456789",
  appId: "1:123456789:web:abc123"
};
```

#### 6.2 Atualize os Arquivos HTML

**Arquivo 1**: `templates/dashboard.html` (aproximadamente linha 1215)

Procure por:
```javascript
const firebaseConfig = {
```

Substitua pelo seu `firebaseConfig`.

**Arquivo 2**: `templates/historico.html` (aproximadamente linha 285)

Procure e substitua o mesmo `firebaseConfig`.

**Arquivo 3**: `static/dashboard-realtime.js` (linha 10-20)

Procure e substitua o mesmo `firebaseConfig`.

---

### Passo 7: Execute o Servidor

```bash
python app.py
```

**Saída esperada**:
```
🔥 Firebase inicializado com sucesso!
📦 Firebase Storage inicializado
✅ Servidor rodando em http://127.0.0.1:5000
```

---

### Passo 8: Primeiro Acesso

1. **Abra o navegador**: http://localhost:5000

2. **Faça login**:
   - Usuário: `admin`
   - Senha: `sanemar2024` (ou a que você definiu no `.env`)

3. **Cadastre primeiro motorista**:
   - Menu → **Motoristas**
   - Clique em **"Adicionar Motorista"**
   - Preencha os dados
   - (Opcional) Faça upload da CNH

4. **Cadastre primeiro veículo**:
   - Menu → **Veículos**
   - Clique em **"Adicionar Veículo"**
   - Preencha os dados

5. **Registre primeira saída**:
   - Volte para **Página Inicial**
   - Preencha formulário de saída
   - Clique em **"Registrar Saída"**

6. **Teste o dashboard**:
   - Menu → **Dashboard**
   - Verifique se mostra "1 veículo em curso"
   - Verifique atualização em tempo real

---

## 🌐 Deploy em Produção (Render.com)

Para deploy em produção, siga o guia completo: [`DEPLOY_RENDER.md`](DEPLOY_RENDER.md)

**Resumo**:
1. Faça push do código para GitHub
2. Crie conta no Render.com
3. Conecte repositório
4. Configure variáveis de ambiente
5. Deploy automático!

**Resultado**: Servidor 24/7 gratuito com HTTPS.

---

## 🛠️ Configurações Adicionais

### Alterar Porta do Servidor

**Arquivo**: `app.py` (última linha)

```python
# Padrão: porta 5000
app.run(host='0.0.0.0', port=5000, debug=True)

# Alterar para 8080
app.run(host='0.0.0.0', port=8080, debug=True)
```

### Desativar Debug Mode (Produção)

```python
# Desenvolvimento
app.run(host='0.0.0.0', port=5000, debug=True)

# Produção
app.run(host='0.0.0.0', port=5000, debug=False)
```

### Configurar Logo Personalizada

1. Substitua `static/Logo_frota_sanemar.png` pela sua logo
2. Tamanho recomendado: 200x200px ou 400x400px
3. Formato: PNG com fundo transparente

---

## 🐛 Troubleshooting

### Erro: `ModuleNotFoundError: No module named 'flask'`
**Causa**: Ambiente virtual não ativado ou dependências não instaladas  
**Solução**:
```bash
# 1. Ative o ambiente virtual
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# 2. Instale dependências
pip install -r requirements.txt
```

### Erro: `DefaultCredentialsError`
**Causa**: Firebase credentials não encontradas  
**Solução**:
1. Confirme que `firebase-credentials.json` está na raiz
2. Confirme que `.env` tem: `GOOGLE_APPLICATION_CREDENTIALS=firebase-credentials.json`
3. Teste manualmente:
```bash
$env:GOOGLE_APPLICATION_CREDENTIALS="firebase-credentials.json"  # Windows
export GOOGLE_APPLICATION_CREDENTIALS="firebase-credentials.json"  # Linux
```

### Erro: `Firebase não inicializado`
**Causa**: Config do Firebase incorreta nos arquivos HTML  
**Solução**:
1. Abra Console do navegador (F12)
2. Procure por erros Firebase
3. Verifique se `firebaseConfig` está correto
4. Confirme que `apiKey`, `projectId` etc estão preenchidos

### Erro: `Address already in use`
**Causa**: Porta 5000 já está sendo usada  
**Solução**:
```bash
# Windows - Matar processo na porta 5000
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# Linux/Mac
lsof -ti:5000 | xargs kill -9

# Ou altere a porta no app.py
```

### Problema: Dashboard não atualiza em tempo real
**Causa**: Firebase listener não está ativo  
**Solução**:
1. Abra console (F12)
2. Procure por: `✅ Listener de saídas ativo`
3. Se não aparecer, verifique `firebaseConfig`
4. Teste conexão manualmente:
```javascript
firebase.firestore().collection('saidas').limit(1).get()
  .then(() => console.log('Firebase OK'))
  .catch(err => console.error('Firebase ERROR:', err))
```

---

## 📚 Próximos Passos

Após instalação bem-sucedida:

1. ✅ Leia a documentação completa: [`README.md`](README.md)
2. ✅ Configure regras de segurança: [`FIRESTORE_RULES.md`](FIRESTORE_RULES.md)
3. ✅ Teste todas as funcionalidades
4. ✅ Faça backup das credenciais (`firebase-credentials.json` e `.env`)
5. ✅ Prepare para produção: [`DEPLOY_RENDER.md`](DEPLOY_RENDER.md)

---

## 📞 Suporte

Problemas na instalação?
- **Issues GitHub**: https://github.com/Cauan-Almeida/Sanemar_Frota/issues
- **Documentação Firebase**: https://firebase.google.com/docs
- **Documentação Flask**: https://flask.palletsprojects.com/

---

<div align="center">

**Guia de Instalação v2.0**  
Sistema de Gestão de Frota - Sanemar

</div>
