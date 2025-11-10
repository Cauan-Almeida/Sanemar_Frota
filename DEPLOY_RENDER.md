# 🚀 GUIA DE DEPLOY - RENDER.COM (100% GRATUITO)

## ⏱️ Tempo total: 10 minutos

---

## 📋 PASSO 1: PREPARAR GITHUB (2 min)

### 1.1 Commit e Push das mudanças:
```bash
git add .
git commit -m "Adiciona configuração para Render + health check"
git push origin main
```

### 1.2 Verificar se está no GitHub:
- Acesse: https://github.com/Cauan-Almeida/Sanemar_Frota
- Verifique se tem o arquivo `render.yaml` na raiz

---

## 🌐 PASSO 2: DEPLOY NO RENDER (3 min)

### 2.1 Criar conta no Render:
1. Acesse: https://render.com
2. Clique em **"Get Started"**
3. Login com **GitHub** (autorize o acesso)

### 2.2 Criar novo Web Service:
1. No Dashboard, clique **"New +"**
2. Selecione **"Web Service"**
3. Conecte seu repositório: **Sanemar_Frota**
4. Render detecta `render.yaml` automaticamente ✅

### 2.3 Configurar variáveis de ambiente:
1. Na página do serviço, vá em **"Environment"**
2. Clique **"Add Environment Variable"**
3. Adicione as variáveis:

```
SECRET_KEY = frota-sanemar-secret-key-2025-super-segura
ADMIN_USERNAME = admin
ADMIN_PASSWORD = sanemar2025
HISTORICO_USERNAME = historico
HISTORICO_PASSWORD = historico123
```

4. **IMPORTANTE:** Firebase Credentials
   - Copie o conteúdo de `firebase-credentials.json`
   - Crie variável: `GOOGLE_APPLICATION_CREDENTIALS_JSON`
   - Cole o JSON completo como valor

### 2.4 Deploy automático:
- Render faz build automaticamente
- Aguarde 3-5 minutos
- URL final: `https://frota-sanemar.onrender.com`

---

## 🔔 PASSO 3: CONFIGURAR UPTIMEROBOT (5 min)

### 3.1 Criar conta:
1. Acesse: https://uptimerobot.com
2. Clique **"Free Sign Up"**
3. Confirme email

### 3.2 Criar monitor:
1. No Dashboard, clique **"Add New Monitor"**
2. Configure:
   - **Monitor Type:** HTTP(s)
   - **Friendly Name:** Frota Sanemar
   - **URL:** `https://frota-sanemar.onrender.com/health`
   - **Monitoring Interval:** 5 minutes
   - **Monitor Timeout:** 30 seconds

3. Clique **"Create Monitor"**

### 3.3 Verificar:
- Em 5 minutos, UptimeRobot faz primeiro ping
- Status deve ficar **"Up"** (verde)
- Servidor agora NUNCA dorme! 🎉

---

## ✅ PASSO 4: VERIFICAÇÃO FINAL

### 4.1 Testar aplicação:
1. Acesse: `https://frota-sanemar.onrender.com`
2. Faça login
3. Teste Dashboard
4. Teste Histórico
5. Registre uma saída de teste

### 4.2 Verificar health check:
```bash
curl https://frota-sanemar.onrender.com/health
```

Deve retornar:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-10T...",
  "service": "Frota Sanemar"
}
```

---

## 🎯 RESULTADO FINAL:

✅ **Deploy automático** no Git push
✅ **SSL/HTTPS** automático
✅ **Servidor 24/7** (nunca dorme)
✅ **100% gratuito** para sempre
✅ **Aguenta 10+ usuários simultâneos**
✅ **512MB RAM** suficiente
✅ **Logs em tempo real** no painel Render

---

## 📊 MONITORAMENTO:

### Render Dashboard:
- **Logs:** Render > Logs (tempo real)
- **Métricas:** CPU, RAM, Requests
- **Deploys:** Histórico de deploys

### UptimeRobot Dashboard:
- **Uptime:** % de disponibilidade
- **Response time:** Latência média
- **Incidents:** Histórico de quedas

---

## 🔧 TROUBLESHOOTING:

### Problema: Build falhou
**Solução:** Verifique se `requirements.txt` está completo:
```bash
pip freeze > requirements.txt
git add requirements.txt
git commit -m "Atualiza requirements.txt"
git push
```

### Problema: Firebase não conecta
**Solução:** Variável de ambiente JSON mal formatada
1. Render > Environment
2. Edite `GOOGLE_APPLICATION_CREDENTIALS_JSON`
3. Cole JSON **sem quebras de linha manualmente** (use minify)

### Problema: Servidor lento
**Solução:** Cold start normal (primeira vez)
- Após 30-60s, velocidade normaliza
- UptimeRobot previne cold starts subsequentes

---

## 🆘 SUPORTE:

- **Render Docs:** https://render.com/docs
- **UptimeRobot FAQ:** https://blog.uptimerobot.com/faq/
- **GitHub Issues:** Reportar problemas no repositório

---

## 🎉 PRONTO!

Seu sistema está online, gratuito e funcionando 24/7!

**URL Produção:** https://frota-sanemar.onrender.com
**Custo mensal:** R$ 0,00 ✅
**Limite de tempo:** Ilimitado ✅
