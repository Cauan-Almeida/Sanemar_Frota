# 🔄 Sistema de Versionamento Automático

## Como Funciona

O sistema agora detecta **automaticamente** quando você faz mudanças no código e **força** todos os usuários a atualizarem, **incluindo quem tem o app instalado na área de trabalho**.

## 📝 Como Forçar Atualização para TODOS os Usuários

### **PASSO 1: Aumentar a Versão**

Quando você fizer **QUALQUER mudança** no código (HTML, CSS, JS), abra o arquivo `sw.js` e mude este número:

```javascript
const APP_VERSION = 'v9.0'; // <<< MUDE AQUI (ex: v10.0, v11.0, etc)
```

### **PASSO 2: Salvar e Reiniciar o Servidor**

1. Salve o arquivo `sw.js`
2. Pare o servidor Flask (Ctrl+C)
3. Inicie novamente: `python app.py`

### **PASSO 3: Aguardar Atualização Automática**

Os usuários verão **automaticamente** um toast verde:

```
🔄 Nova versão disponível!
   Toque para atualizar
```

- **Mobile**: Toast aparece no canto inferior direito
- **Desktop**: Toast aparece e recarrega sozinho em 8-10 segundos
- **PWA Instalado**: Também recebe a atualização!

## 🎯 Quando Aumentar a Versão

✅ **SEMPRE que mexer em**:
- HTML (templates)
- CSS (styles)
- JavaScript (qualquer .js)
- Correções de bugs
- Novas funcionalidades

❌ **NÃO precisa aumentar quando**:
- Mudar apenas Python (backend)
- Alterar apenas banco de dados

## 📊 Histórico de Versões

| Versão | Data | Mudança |
|--------|------|---------|
| v9.0   | 18/11/2025 | Sistema de cards mobile + auto-update |
| v8.0   | 18/11/2025 | Connection monitor |
| v7.0   | Anterior | Cache otimizado |

## 🔧 Troubleshooting

### Usuário não recebeu atualização?

1. Verifique se aumentou a versão no `sw.js`
2. Peça para o usuário **fechar TODAS as abas** do sistema
3. Peça para **reabrir** - o SW detectará automaticamente

### Como testar localmente?

1. Abra em **aba anônima**
2. Mude a versão
3. Recarregue - deve aparecer o toast

## 💡 Dica Pro

Adicione um comentário sempre que mudar a versão:

```javascript
const APP_VERSION = 'v10.0'; // Corrigiu bug no histórico - 18/11/2025
```

Isso ajuda a rastrear o que mudou em cada versão!
