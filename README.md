# 🚗 Sistema de Gestão de Frota - Sanemar



Sistema completo de gerenciamento de frota de veículos com controle de saídas/chegadas, motoristas, documentação, abastecimentos, revisões e relatórios em tempo real.



[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)

[![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)](https://flask.palletsprojects.com/)[![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)](https://flask.palletsprojects.com/)

[![Firebase](https://img.shields.io/badge/Firebase-Firestore-orange.svg)](https://firebase.google.com/)[![Firebase](https://img.shields.io/badge/Firebase-Firestore-orange.svg)](https://firebase.google.com/)

[![Status](https://img.shields.io/badge/Status-Produ%C3%A7%C3%A3o-success.svg)]()[![PWA](https://img.shields.io/badge/PWA-Ready-purple.svg)](https://web.dev/progressive-web-apps/)



------



## 📋 Funcionalidades Principais## 📋 Índice



### 🎯 Gestão de Frota- [Visão Geral](#-visão-geral)

- ✅ **Registro de Saídas/Chegadas**: Controle completo de viagens com timestamps automáticos- [Funcionalidades](#-funcionalidades)

- ✅ **Dashboard em Tempo Real**: Visualização automática de viagens ativas e estatísticas- [Tecnologias](#-tecnologias)

- ✅ **Gestão de Motoristas**: Cadastro com CNH, validade e histórico- [Instalação](#-instalação)

- ✅ **Gestão de Veículos**: Documentação completa e controle de revisões- [Configuração](#-configuração)

- ✅ **Histórico Completo**: Busca avançada com filtros por período, motorista e veículo- [Uso](#-uso)

- ✅ **Relatórios em PDF**: Geração automática de relatórios personalizados- [Estrutura do Projeto](#-estrutura-do-projeto)

- [APIs Disponíveis](#-apis-disponíveis)

### ⚡ Recursos Avançados- [Troubleshooting](#-troubleshooting)

- 🚀 **Cache Inteligente (5min)**: Reduz 90% das consultas ao Firebase- [Segurança](#-segurança)

- 🔄 **Auto-Update**: Dashboard atualiza automaticamente em novas saídas/chegadas- [**🚀 Hospedagem Gratuita**](HOSPEDAGEM_GRATUITA.md)

- 🔔 **Notificações Toast**: Feedback visual de todas as operações- [**🔥 Correção de Vazamento**](CORRECAO_VAZAMENTO.md)

- 📱 **PWA**: Funciona offline e pode ser instalado como app

- ⚠️ **Sistema Anti-Duplicidade**: Impede registros duplicados de veículos---

- 🔒 **Autenticação**: Controle de acesso admin e histórico

## 📚 DOCUMENTAÇÃO COMPLETA

---

| Documento | Descrição |

## 🏗️ Arquitetura do Sistema|-----------|-----------|

| [`README.md`](README.md) | ⭐ Documentação principal (este arquivo) |

### Stack Tecnológico| [`INICIO_RAPIDO.md`](INICIO_RAPIDO.md) | 🚀 Guia de início rápido (5 minutos) |

| [`HOSPEDAGEM_GRATUITA.md`](HOSPEDAGEM_GRATUITA.md) | 🆓 Como hospedar SEM CUSTOS |

**Backend**| [`CORRECAO_VAZAMENTO.md`](CORRECAO_VAZAMENTO.md) | 🔥 Otimizações de Firestore (56k → 14k leituras) |

```| [`CHECKLIST_FINAL.md`](CHECKLIST_FINAL.md) | ✅ Checklist de testes e deploy |

Flask (Python 3.11+)| [`FIRESTORE_RULES.md`](FIRESTORE_RULES.md) | 🔒 Regras de segurança do Firebase |

├── Waitress (Servidor Produção)

├── Google Firestore (Database)---

├── Firebase Storage (Arquivos)

└── Cache In-Memory (TTL 5min)## 🎯 Visão Geral

```

Sistema web desenvolvido para a **Sanemar** para controlar e monitorar a frota de veículos em tempo real. O sistema oferece:

**Frontend**

```- ✅ **Registro de Saídas e Chegadas** com timestamp automático

HTML5 + CSS3 + JavaScript- 🚫 **Sistema Anti-Duplicidade** (impede veículo em curso duplicado)

├── Firebase SDK (Real-time)- ⚠️ **Alertas de Motoristas** (avisa se motorista já está em viagem)

├── Service Worker (PWA)- 📊 **Dashboard em Tempo Real** com Firebase

└── Tailwind CSS (Styling)- ⛽ **Controle de Abastecimentos** com cálculo de consumo

```- 👤 **Gestão de Motoristas** com upload de CNH

- 🚙 **Gestão de Veículos** com documentação digital

### Estrutura de Arquivos- 📱 **PWA (Progressive Web App)** funciona offline

```- 🔒 **Sistema de Autenticação** (Admin + Histórico)

Frota_sanemar/

├── app.py                      # Servidor Flask principal---

├── requirements.txt            # Dependências Python

├── render.yaml                 # Config Render.com## ⚡ Funcionalidades

├── .env                        # Variáveis ambiente (não commitado)

├── firebase-credentials.json   # Credenciais (não commitado)### 1. **Controle de Saídas/Chegadas**

│- Registro rápido de saída com veículo, motorista, solicitante

├── templates/                  # Templates HTML- Botão "Usar Hora Atual" para timestamp automático

│   ├── dashboard.html          # Dashboard tempo real- Validação em tempo real (impede duplicidade de veículo)

│   ├── historico.html          # Histórico viagens- Alerta se motorista já estiver em curso

│   ├── motoristas.html         # Gestão motoristas- Registro de chegada com cálculo automático de tempo de viagem

│   ├── veiculos.html           # Gestão veículos- Cancelamento de viagem (remove registro)

│   └── login.html              # Autenticação

│### 2. **Dashboard Interativo**

├── static/                     # Assets estáticos- Estatísticas em tempo real:

│   ├── app.js                  # Lógica principal  - Total de veículos em curso

│   ├── dashboard-realtime.js   # Auto-update  - Total de viagens hoje

│   ├── style.css               # Estilos globais  - Total de horas na rua

│   ├── toast.js                # Notificações- Gráficos de viagens por veículo e motorista

│   └── manifest.json           # PWA config- Histórico completo de viagens

│- Atualização automática (Firebase onSnapshot)

├── scripts/                    # Utilitários

│   └── limpar_banco_dados.py   # Limpeza produção### 3. **Gestão de Motoristas**

│- Cadastro completo (nome, telefone, CPF, CNH, validade)

└── sw.js                       # Service Worker PWA- Upload de foto da CNH

```- Status: Ativo / Inativo / CNH Vencida

- Histórico de viagens por motorista

---- Busca e filtros



## 🚀 Instalação e Configuração### 4. **Gestão de Veículos**

- Cadastro completo (placa, modelo, ano, tipo, cor, RENAVAM)

### Pré-requisitos- Upload de documento do veículo

- Python 3.11+- Controle de abastecimentos por veículo

- Conta Firebase (free tier)- Cálculo de consumo (km/l)

- Git- Histórico de viagens

- KM Mensal e Multas

### Instalação Local

### 5. **Sistema Anti-Duplicidade**

1. **Clone o repositório**- **BLOQUEIO TOTAL**: Veículo já em curso não pode sair novamente

```bash- **ALERTA**: Motorista em viagem gera aviso (pode confirmar)

git clone https://github.com/Cauan-Almeida/Sanemar_Frota.git- Normalização de dados (remove acentos, espaços, case-insensitive)

cd Sanemar_Frota- Destaque visual na tabela (fundo amarelo)

```- Mensagens claras e amigáveis



2. **Crie ambiente virtual**### 6. **PWA & Offline**

```bash- Service Worker v4 otimizado

# Windows- Cache inteligente (estáticos sim, APIs não)

python -m venv venv- Funciona offline (modo de leitura)

venv\Scripts\activate- Instalável no desktop e mobile

- Notificações push (preparado)

# Linux/Mac

python3 -m venv venv---

source venv/bin/activate

```## 🛠️ Tecnologias



3. **Instale dependências**### Backend

```bash- **Python 3.11+**

pip install -r requirements.txt- **Flask** (Web Framework)

```- **Google Cloud Firestore** (Database NoSQL)

- **Firebase Storage** (Armazenamento de arquivos)

4. **Configure Firebase**- **Firebase Admin SDK** (Python)

- **python-dotenv** (Variáveis de ambiente)

Acesse [Firebase Console](https://console.firebase.google.com) e:- **ReportLab** (Geração de PDFs - futuro)

- Crie novo projeto ou use existente- **Pillow** (Manipulação de imagens)

- Ative Firestore Database (modo produção)

- Ative Firebase Storage### Frontend

- Baixe credenciais: **Project Settings → Service Accounts → Generate New Private Key**- **HTML5 + CSS3**

- Salve como `firebase-credentials.json` na raiz do projeto- **JavaScript ES6+ (Vanilla)**

- **Tailwind CSS** (Framework CSS via CDN)

5. **Configure variáveis de ambiente**- **Chart.js** (Gráficos interativos)

- **Firebase SDK** (Client-side para real-time)

Crie arquivo `.env` na raiz:- **Service Worker** (PWA)

```env

SECRET_KEY=sua_chave_secreta_aleatoria_aqui### Infraestrutura

GOOGLE_APPLICATION_CREDENTIALS=firebase-credentials.json- **Firebase Firestore** (Banco de dados)

```- **Firebase Storage** (Arquivos: CNH, documentos)

- **Firebase Hosting** (Opcional - hospedagem)

6. **Execute o servidor**

```bash---

python app.py

```## 📦 Instalação



7. **Acesse o sistema**### 1. **Pré-requisitos**

```- Python 3.11 ou superior

http://localhost:5000- Conta no Google Firebase (gratuita)

```- Git (opcional)



**Credenciais padrão**:### 2. **Clone o Repositório**

- Usuário: `admin````bash

- Senha: `sanemar2024`git clone https://github.com/Cauan-Almeida/Sanemar_Frota.git

cd Sanemar_Frota

---```



## 🌐 Deploy em Produção### 3. **Crie um Ambiente Virtual**

```bash

### Render.com (100% Gratuito)# Windows

python -m venv venv

O sistema está configurado para deploy automático no Render.com.venv\Scripts\activate



**📖 Guia Completo**: Consulte [`DEPLOY_RENDER.md`](DEPLOY_RENDER.md)# Linux/Mac

python3 -m venv venv

**Resumo rápido**:source venv/bin/activate

1. Push código para GitHub```

2. Conecte repositório no Render.com

3. Configure variáveis de ambiente### 4. **Instale as Dependências**

4. Configure UptimeRobot para keep-alive (impede servidor dormir)```bash

5. ✅ Deploy automático em cada pushpip install -r requirements.txt

```

**Resultado**:

- ✅ Hosting gratuito 24/7### 5. **Configure o Firebase**

- ✅ 512MB RAM

- ✅ Auto-deploy no Git push#### a) Crie um projeto no Firebase:

- ✅ HTTPS grátis1. Acesse [Firebase Console](https://console.firebase.google.com/)

- ✅ Custo: **R$ 0,00/mês**2. Clique em "Adicionar projeto"

3. Nomeie como "frota-sanemar" (ou outro nome)

---4. Ative Google Analytics (opcional)



## 📊 Sistema de Cache e Performance#### b) Configure o Firestore:

1. No menu lateral, clique em "Firestore Database"

### Cache Inteligente de 5 Minutos2. Clique em "Criar banco de dados"

3. Escolha "Modo de produção"

**Problema Original**: 11.000+ leituras Firestore/hora  4. Escolha a localização (ex: `southamerica-east1`)

**Solução**: Cache com TTL de 5 minutos  

**Resultado**: 1.200 leituras/hora (**redução de 90%**)#### c) Configure o Storage:

1. No menu lateral, clique em "Storage"

#### Como Funciona2. Clique em "Começar"

3. Aceite as regras padrão

```python

# Cache salva resultados pesados#### d) Obtenha as Credenciais:

dashboard_cache = {1. Vá em "Configurações do Projeto" (ícone de engrenagem)

    'default': {'data': {...}, 'expires': timestamp},2. Aba "Contas de serviço"

    '2025-11': {'data': {...}, 'expires': timestamp}3. Clique em "Gerar nova chave privada"

}4. Salve o arquivo JSON como `firebase-credentials.json` na raiz do projeto



# Invalidação automática em mudanças#### e) Obtenha a Configuração Web:

@app.route('/api/saida', methods=['POST'])1. Na aba "Geral" das configurações

def registrar_saida():2. Role até "Seus apps" → "Aplicativo da Web"

    # ... registra saída3. Se não existir, clique em "Adicionar app" → Web

    dashboard_cache.clear()  # ← Limpa cache4. Copie o objeto `firebaseConfig`

    historico_cache['expires'] = 0  # ← Força recalculo

```### 6. **Configure as Variáveis de Ambiente**



#### Logs de PerformanceCrie um arquivo `.env` na raiz do projeto:

```

✅ Dashboard do CACHE (mês: default) - economia ~160 leituras```env

💾 Dashboard no cache por 5min# Flask

🗑️ Cache invalidado após nova saída/chegadaSECRET_KEY=sua-chave-super-secreta-aqui-mude-isso

```FLASK_ENV=development



### Auto-Update em Tempo Real# Autenticação Admin

ADMIN_USERNAME=admin

Firebase listener otimizado monitora apenas documentos `status='em_curso'` (5-10 docs):ADMIN_PASSWORD=sanemar2025



```javascript# Autenticação Histórico (somente leitura)

// Listener eficiente - só viagens ativasHISTORICO_USERNAME=historico

db.collection('saidas')HISTORICO_PASSWORD=historico123

  .where('status', '==', 'em_curso')

  .onSnapshot(snapshot => {# Firebase (opcional, se não usar credenciais JSON)

    if (mudanca_detectada) {GOOGLE_APPLICATION_CREDENTIALS=./firebase-credentials.json

      clearCache();```

      reloadDashboard();

      showToast('Dashboard atualizado!');### 7. **Configure o Firebase no Frontend**

    }

  });Edite os arquivos abaixo e substitua pelo seu `firebaseConfig`:

```

**`templates/index.html`** (linha ~158):

**Benefícios**:```javascript

- 🎯 Apenas 5-10 docs monitorados (vs 50+ antes)const firebaseConfig = {

- 🎯 Atualização automática (sem F5)    apiKey: "SUA_API_KEY_AQUI",

- 🎯 Notificações em tempo real    authDomain: "seu-projeto.firebaseapp.com",

- 🎯 Previne loops infinitos    projectId: "seu-projeto",

    storageBucket: "seu-projeto.firebasestorage.app",

---    messagingSenderId: "123456789",

    appId: "1:123456789:web:abcdef123456"

## 📈 Consumo Firebase};

```

### Métricas Diárias (Produção com 200+ saídas)

**`templates/dashboard.html`** (linha ~1215):

| Métrica | Consumo | Limite Free | % Usado |```javascript

|---------|---------|-------------|---------|// Mesmo conteúdo acima

| **Leituras** | 27.740/dia | 50.000 | 56% ✅ |```

| **Escritas** | 145/dia | 20.000 | 0.7% ✅ |

| **Storage** | ~500MB | 1GB | 50% ✅ |---

| **Bandwidth** | ~200MB | 10GB | 2% ✅ |

## ▶️ Uso

**💰 Custo mensal**: **R$ 0,00** (dentro do free tier)

### 1. **Inicie o Servidor**

### Otimizações Aplicadas```bash

python app.py

1. ✅ Cache de 5min no dashboard (economiza 160 leituras/request)```

2. ✅ Cache de 5min no histórico (economiza 100 leituras/request)

3. ✅ Listener apenas em `status='em_curso'` (reduz 80% dos documentos)O servidor iniciará em: `http://127.0.0.1:5000`

4. ✅ Invalidação seletiva (só limpa cache quando necessário)

5. ✅ LIMIT 50 em queries grandes (previne overload)### 2. **Acesso**



---#### Login Admin (controle total):

- URL: `http://127.0.0.1:5000/login`

## 🔒 Segurança- Usuário: `admin`

- Senha: `sanemar2025`

### Regras Firestore

#### Login Histórico (somente leitura):

Consulte [`FIRESTORE_RULES.md`](FIRESTORE_RULES.md) para configuração completa.- URL: `http://127.0.0.1:5000/login`

- Usuário: `historico`

**Principais proteções**:- Senha: `historico123`

- ✅ Autenticação obrigatória

- ✅ Validação de campos### 3. **Primeiro Uso**

- ✅ Proteção contra sobrescrita

- ✅ Rate limiting1. **Cadastrar Veículos**: Vá em "Veículos" → Adicionar veículo

2. **Cadastrar Motoristas**: Vá em "Motoristas" → Adicionar motorista

### Boas Práticas3. **Registrar Saída**: Na tela inicial, preencha o formulário

4. **Registrar Chegada**: Clique em "✅ Chegada" na tabela

**❌ NUNCA COMMITE**:5. **Ver Dashboard**: Clique em "Dashboard" no menu

- `firebase-credentials.json`

- `.env`---

- Senhas hardcoded

## 📁 Estrutura do Projeto

**✅ SEMPRE**:

- Use variáveis de ambiente```

- Gere SECRET_KEY aleatóriaFrota_sanemar/

- Configure CORS adequadamente│

- Atualize dependências regularmente├── app.py                      # Backend Flask (3946 linhas)

├── requirements.txt            # Dependências Python

---├── .env                        # Variáveis de ambiente (criar)

├── .gitignore                  # Arquivos ignorados pelo Git

## 📄 Documentação Adicional├── firebase-credentials.json   # Credenciais Firebase (não commitar!)

├── sw.js                       # Service Worker v4 (PWA)

| Arquivo | Descrição |├── README.md                   # Este arquivo

|---------|-----------|├── FIRESTORE_RULES.md          # Regras de segurança do Firestore

| [`DEPLOY_RENDER.md`](DEPLOY_RENDER.md) | 🚀 Deploy em produção (Render.com) |├── GERACAO_PDF.md              # Documentação de PDFs (futuro)

| [`FIRESTORE_RULES.md`](FIRESTORE_RULES.md) | 🔒 Regras de segurança Firebase |│

| [`GERACAO_PDF.md`](GERACAO_PDF.md) | 📄 Sistema de relatórios PDF |├── static/                     # Arquivos estáticos

│   ├── style.css               # Estilos globais

---│   ├── app.js                  # Lógica principal (459 linhas)

│   ├── app-melhorado.js        # Sistema anti-duplicidade (403 linhas)

## 🛠️ Scripts Utilitários│   ├── toast.js                # Sistema de notificações

│   ├── dashboard.js            # Lógica do dashboard

### Limpeza do Banco de Dados│   ├── dashboard-realtime.js   # Firebase real-time (224 linhas)

│   ├── veiculos-tab.js         # Tab de veículos

Remove todos os dados de teste antes de produção:│   ├── km-multas.js            # Tab KM e multas

│   ├── relatorios-tab.js       # Tab de relatórios

```bash│   ├── revisoes-tab.js         # Tab de revisões

cd scripts│   ├── manifest.json           # PWA Manifest

python limpar_banco_dados.py│   ├── Logo_frota_sanemar.png  # Logo principal

# Digite: CONFIRMO│   ├── favicon.ico             # Favicon

# Digite: APAGAR TUDO│   ├── icon-192.png            # Ícone PWA 192x192

```│   └── icon-512.png            # Ícone PWA 512x512

│

**⚠️ ATENÇÃO**: Ação **IRREVERSÍVEL**! Use apenas para limpar dados de teste.├── templates/                  # Templates HTML

│   ├── index.html              # Página principal (registro de saídas)

**O que é deletado**:│   ├── dashboard.html          # Dashboard com estatísticas

- Todas as saídas/viagens│   ├── historico.html          # Histórico de viagens

- Todos os motoristas│   ├── motoristas.html         # Gestão de motoristas

- Todos os veículos│   ├── motorista_detalhes.html # Detalhes de um motorista

- Todos os abastecimentos│   ├── veiculos.html           # Gestão de veículos

- Todas as revisões│   ├── veiculo_detalhes.html   # Detalhes de um veículo

- Arquivos no Storage (CNHs, documentos, etc)│   ├── relatorios.html         # Relatórios (futuro)

│   ├── login.html              # Página de login

---│   └── maintenance.html        # Página de manutenção

│

## 🐛 Troubleshooting├── scripts/                    # Scripts utilitários

│   ├── migrate_*.py            # Scripts de migração

### Problema: `DefaultCredentialsError`│   ├── find_mismatched_saidas.py

**Causa**: Firebase não encontra credenciais  │   ├── fix_mismatched_saidas.py

**Solução**:│   └── restore_from_backups.py

```bash│

# Windows PowerShell└── __pycache__/                # Cache Python (ignorado)

$env:GOOGLE_APPLICATION_CREDENTIALS="C:\caminho\firebase-credentials.json"```



# Linux/Mac---

export GOOGLE_APPLICATION_CREDENTIALS="/caminho/firebase-credentials.json"

```## 🌐 APIs Disponíveis



### Problema: Dashboard não atualiza### Autenticação

**Causa**: Firebase listener não está ativo  - `POST /login` - Login de usuário

**Solução**:- `GET /logout` - Logout

1. Abra console (F12) → Procure por erros Firebase

2. Verifique conexão: `firebase.firestore().collection('saidas').limit(1).get()`### Saídas e Chegadas

3. Use botão refresh manual (🔄) como fallback- `POST /api/saida` - Registrar saída de veículo

- `POST /api/chegada` - Registrar chegada de veículo

### Problema: Excesso de leituras Firebase- `POST /api/cancelar` - Cancelar viagem em curso

**Causa**: Cache desativado ou listener muito amplo  - `GET /api/veiculos_em_curso` - Listar veículos em curso

**Solução**:- `GET /api/historico` - Histórico de viagens

1. Verifique logs: procure por "CACHE" vs "Recalculando"- `PATCH /api/saidas/{id}` - Editar saída

2. Confirme TTL: `cache_ttl = 300` (5min)- `DELETE /api/saidas/{id}` - Deletar saída

3. Verifique query listener: `where('status', '==', 'em_curso')`

### Motoristas

### Problema: Servidor "dorme" no Render- `GET /api/motoristas` - Listar motoristas

**Causa**: Free tier do Render hiberna após 15min inativo  - `POST /api/motoristas` - Criar motorista

**Solução**: Configure UptimeRobot (gratuito):- `PUT /api/motoristas/{id}` - Atualizar motorista

- Crie monitor HTTP(s)- `DELETE /api/motoristas/{id}` - Deletar motorista

- URL: `https://seu-app.onrender.com/health`- `POST /api/motoristas/{id}/upload-cnh` - Upload de CNH

- Intervalo: 5 minutos- `GET /api/motoristas/{id}/cnh` - Download de CNH

- ✅ Servidor nunca dormirá- `PATCH /api/motoristas/{id}/status` - Atualizar status



---### Veículos

- `GET /api/veiculos` - Listar veículos

## 📞 Suporte- `POST /api/veiculos` - Criar veículo

- `GET /api/veiculos/{placa}` - Detalhes do veículo

- **Repositório**: [GitHub - Sanemar_Frota](https://github.com/Cauan-Almeida/Sanemar_Frota)- `PATCH /api/veiculos/{placa}` - Atualizar veículo

- **Issues**: Reporte bugs nas Issues do GitHub- `DELETE /api/veiculos/{placa}` - Deletar veículo

- **Autor**: Cauan Ferreira de Almeida- `POST /api/veiculos/{id}/upload-documento` - Upload de documento

- `GET /api/veiculos/{id}/documento` - Download de documento

---- `PATCH /api/veiculos/{id}/status` - Atualizar status



## 📝 Changelog### Abastecimentos

- `POST /api/veiculos/refuels` - Registrar abastecimento

### v2.0 (Novembro 2025) - **VERSÃO ATUAL**- `GET /api/veiculos/{placa}/refuels` - Listar abastecimentos

- ✅ Sistema de cache inteligente (5min TTL)- `PATCH /api/refuels/{id}` - Editar abastecimento

- ✅ Auto-update em tempo real- `DELETE /api/refuels/{id}` - Deletar abastecimento

- ✅ Redução de 90% nas leituras Firestore- `GET /api/refuels/summary` - Resumo de abastecimentos

- ✅ Deploy automático Render.com- `GET /api/veiculos/{placa}/metrics` - Métricas do veículo

- ✅ Script de limpeza de dados

- ✅ Health check endpoint### Dashboard

- ✅ Documentação completa atualizada- `GET /api/dashboard_stats` - Estatísticas gerais (COM cache)

- ✅ Remoção de arquivos obsoletos- `GET /api/dashboard_realtime` - Estatísticas em tempo real (SEM cache)

- `POST /api/dashboard_cache/clear` - Limpar cache

### v1.0 (Outubro 2024)

- Sistema inicial de gestão de frota### KM e Multas

- Dashboard básico- `GET /api/km-mensal` - Listar registros de KM mensal

- Controle de saídas/chegadas- `POST /api/km-mensal` - Criar registro de KM

- Gestão de motoristas e veículos- `PUT /api/km-mensal/{id}` - Atualizar KM

- `DELETE /api/km-mensal/{id}` - Deletar registro

---

---

## 📄 Licença

## 🐛 Troubleshooting

Este projeto é proprietário e de uso exclusivo da **Sanemar - Saneamento de Maringá**.  

Todos os direitos reservados © 2024-2025.### Problema: Erro "Firestore quota exceeded"

**Solução**: O Firestore gratuito tem limite de 50.000 leituras/dia. Monitore o uso:

---```python

# No app.py, existe proteção automática

<div align="center">FIRESTORE_AVAILABLE = True  # Muda para False em caso de quota

```

**🚗 Desenvolvido por Cauan Ferreira de Almeida**

### Problema: Service Worker não atualiza

Sistema de Gestão de Frota v2.0 | Novembro 2025**Solução**:

1. Abra DevTools (F12)

[![Status](https://img.shields.io/badge/Status-Produ%C3%A7%C3%A3o-success.svg)]()2. Aba "Application" → "Service Workers"

[![Uptime](https://img.shields.io/badge/Uptime-24%2F7-blue.svg)]()3. Clique em "Unregister"

[![Custo](https://img.shields.io/badge/Custo-R%24%200%2C00-brightgreen.svg)]()4. Marque "Update on reload"

5. Pressione Ctrl+Shift+F5 (hard refresh)

</div>

### Problema: Erros de `chrome-extension://`
**Solução**: Service Worker v4 já filtra esses erros. Se persistir:
1. Desabilite extensões do Chrome (MetaMask, etc)
2. Teste em janela anônima (Ctrl+Shift+N)

### Problema: Firebase não inicializa
**Solução**:
1. Verifique `firebase-credentials.json` na raiz
2. Verifique `firebaseConfig` nos HTML files
3. Abra console do navegador (F12) e procure erros
4. Confirme que Firestore e Storage estão ativados no Firebase Console

### Problema: Veículos em curso não aparecem em tempo real
**Solução**:
1. Verifique se Firebase está inicializado (console deve mostrar "🔥 Firebase inicializado")
2. Verifique se listener está ativo (console deve mostrar "✅ Listener de saídas ativo")
3. Verifique regras do Firestore (permissões de leitura)

### Problema: "TypeError: showToast is not a function"
**Solução**: Verifique se `toast.js` está carregado ANTES de `app.js`:
```html
<script src="/static/toast.js" defer></script>
<script src="/static/app.js" defer></script>
```

---

## 🔒 Segurança

### Autenticação
- Sistema de sessões Flask com `session`
- Dois níveis de acesso: Admin (full) e Histórico (read-only)
- Decorators `@requires_auth` e `@requires_auth_historico`

### Credenciais
- **NUNCA** commite `firebase-credentials.json` no Git
- **NUNCA** commite `.env` no Git
- Use `.gitignore` para proteger arquivos sensíveis

### Firestore Rules
Adicione estas regras no Firebase Console → Firestore → Rules:

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Permitir leitura/escrita para usuários autenticados
    match /{document=**} {
      allow read, write: if true; // ⚠️ DESENVOLVIMENTO - mude para produção!
    }
    
    // Para PRODUÇÃO, use:
    // match /saidas/{saida} {
    //   allow read: if request.auth != null;
    //   allow write: if request.auth != null && request.auth.token.admin == true;
    // }
  }
}
```

### Storage Rules
Firebase Console → Storage → Rules:

```javascript
rules_version = '2';
service firebase.storage {
  match /b/{bucket}/o {
    match /motoristas/{motoristaId}/cnh/{fileName} {
      allow read: if request.auth != null;
      allow write: if request.auth != null && request.auth.token.admin == true;
    }
    match /veiculos/{veiculoId}/documento/{fileName} {
      allow read: if request.auth != null;
      allow write: if request.auth != null && request.auth.token.admin == true;
    }
  }
}
```

---

## 🚀 Implantação

### Opção 1: Heroku
```bash
# Instale Heroku CLI
heroku login
heroku create frota-sanemar
git push heroku main
```

### Opção 2: Google Cloud Run
```bash
gcloud run deploy frota-sanemar \
  --source . \
  --platform managed \
  --region southamerica-east1
```

### Opção 3: VPS (DigitalOcean, AWS, etc)
```bash
# Configure um servidor Ubuntu
sudo apt update
sudo apt install python3 python3-pip nginx
pip3 install -r requirements.txt
gunicorn --bind 0.0.0.0:5000 app:app
```

---

## 📊 Monitoramento

### Firebase Quotas
- Console: https://console.firebase.google.com/
- Usage & Billing → Ver detalhes
- Monitore leituras/escritas diárias

### Logs do Flask
```bash
# Ver logs em tempo real
tail -f logs/frota.log

# Ver erros
grep ERROR logs/frota.log
```

---

## 🤝 Contribuindo

1. Fork o projeto
2. Crie uma branch: `git checkout -b feature/nova-funcionalidade`
3. Commit: `git commit -m 'Adiciona nova funcionalidade'`
4. Push: `git push origin feature/nova-funcionalidade`
5. Abra um Pull Request

---

## 📝 Licença

Este projeto é de uso interno da **Sanemar**. Todos os direitos reservados.

---

## 👥 Autores

- **Desenvolvedor Principal**: Cauan Ferreira de Almeida
- **Cliente**: Sanemar - Saneamento de Maringá
- **Ano**: 2024-2025

---

## 📞 Suporte

Para dúvidas ou problemas:
- **Email**: frota@sanemar-sa.com.br
- **GitHub Issues**: https://github.com/Cauan-Almeida/Sanemar_Frota/issues

---

## ✨ Changelog

### v4.0.0 (2025-11-06) - PRIMEIRA IMPLEMENTAÇÃO COMPLETA
- ✅ Service Worker v4 otimizado (sem erros de chrome-extension)
- ✅ Firebase real-time em index.html e dashboard.html
- ✅ Sistema anti-duplicidade completo
- ✅ PWA funcional com cache inteligente
- ✅ Documentação completa
- ✅ Limpeza de arquivos desnecessários
- ✅ Script app-melhorado.js integrado
- ✅ Todas as rotas testadas e funcionais

### v3.0.0 (2024-10)
- Dashboard em tempo real
- Sistema anti-duplicidade
- Upload de CNH e documentos

### v2.0.0 (2024-09)
- Controle de abastecimentos
- KM mensal e multas
- Gestão de motoristas

### v1.0.0 (2024-08)
- Versão inicial
- Registro de saídas/chegadas
- Histórico básico

---

<div align="center">
  <strong>🚗 Desenvolvido por Cauan Ferreira de Almeida</strong>
  <br>
  <sub>Sistema de Controle de Frota - 2024-2025</sub>
</div>
