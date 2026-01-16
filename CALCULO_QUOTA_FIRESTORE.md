# 📊 Cálculo de Quota do Firestore - 4 PCs Simultâneos

## 🎯 Cenário de Uso

**4 computadores** usando o sistema simultaneamente durante todo o dia de trabalho:
- **PC 1:** Dashboard (registro de saídas/chegadas)
- **PC 2:** Dashboard (monitoria em tempo real)
- **PC 3:** Histórico (consultas frequentes)
- **PC 4:** Dashboard/Relatórios (gestão)

**Horário de uso:** 8h às 18h (10 horas/dia) × 22 dias úteis = **220 horas/mês**

---

## 📈 Estimativa de Operações por PC (POR DIA)

### PC 1: Dashboard - Registro Ativo (Operador)
- Carga inicial do dashboard: **50 leituras** (cache 5min)
- Listener em tempo real (em curso): **5-10 leituras/hora** × 10h = **100 leituras/dia**
- Registros de saída/chegada: **20 saídas × 2 writes** = **40 escritas/dia**
- Atualizações de dashboard após registro: **20 × 50 leituras** = **1.000 leituras/dia**
- Cache expirações (5min): **12/hora × 10h × 50** = **600 leituras/dia**

**TOTAL PC1/DIA:**
- Leituras: 1.750
- Escritas: 40

### PC 2: Dashboard - Monitoria (Supervisor)
- Carga inicial: **50 leituras**
- Listener em tempo real: **100 leituras/dia** (atualiza quando PC1 registra)
- Atualizações de dashboard: **20 × 50** = **1.000 leituras/dia**
- Cache expirações: **600 leituras/dia**

**TOTAL PC2/DIA:**
- Leituras: 1.750
- Escritas: 0

### PC 3: Histórico - Consultas (Administração)
- Carga inicial do mês: **500 leituras** (1 vez ao abrir)
- Listener em tempo real: **50 leituras/dia** (apenas em curso)
- Navegação entre meses: **5 × 500** = **2.500 leituras/dia**
- Filtros adicionais: **10 × 50** = **500 leituras/dia**
- Cache expirações: **3 × 500** = **1.500 leituras/dia**

**TOTAL PC3/DIA:**
- Leituras: 5.050
- Escritas: 0

### PC 4: Dashboard/Relatórios - Gestão
- Carga inicial: **50 leituras**
- Relatórios/gráficos: **5 × 200** = **1.000 leituras/dia**
- Consultas esporádicas: **500 leituras/dia**
- Cache expirações: **600 leituras/dia**

**TOTAL PC4/DIA:**
- Leituras: 2.150
- Escritas: 0

---

## 🧮 Total Diário (4 PCs)

### Leituras por Dia
```
PC1: 1.750
PC2: 1.750
PC3: 5.050
PC4: 2.150
─────────────
TOTAL: 10.700 leituras/dia
```

### Escritas por Dia
```
PC1: 40 (saídas/chegadas)
PC2: 0
PC3: 0
PC4: 0
─────────────
TOTAL: 40 escritas/dia
```

---

## 💰 Plano Gratuito do Firestore (Firebase Spark)

### ⚠️ LIMITE DIÁRIO (CRÍTICO!)
```
🚨 Leituras: 50.000/DIA
🚨 Escritas: 20.000/DIA
🚨 Deletes: 20.000/DIA
```

### Comparação com o Uso Real DIÁRIO

| Operação | Uso Real/Dia | Limite/Dia | % Utilizado | Margem | Status |
|----------|--------------|------------|-------------|---------|---------|
| **Leituras** | 10.700 | 50.000 | **21,4%** | 39.300 | ✅ OK |
| **Escritas** | 40 | 20.000 | **0,2%** | 19.960 | ✅ OK |
| **Deletes** | 2-5 | 20.000 | **0,025%** | 19.995 | ✅ OK |

---

## ⚠️ Análise de Risco: Dias de Pico

### Cenário Normal (22 dias/mês)
```
10.700 leituras/dia
✅ 21,4% do limite diário
✅ Sobram 78,6% (39.300 leituras)
```

### Cenário de Pico (Dia com Muito Movimento)
**Exemplo:** Segunda-feira após feriado, muitas consultas ao histórico

```
PC1: 2.000 leituras
PC2: 2.000 leituras
PC3: 8.000 leituras (muito histórico)
PC4: 3.000 leituras
─────────────────────
TOTAL: 15.000 leituras/dia
```

**Análise:**
- **30% do limite diário** ✅
- Ainda sobram 35.000 leituras
- **Status:** Tranquilo!

### Cenário EXTREMO (Máximo Teórico)
**Exemplo:** Auditoria, todos consultando histórico intensamente

```
PC1: 3.000 leituras
PC2: 3.000 leituras
PC3: 15.000 leituras (auditoria completa)
PC4: 5.000 leituras (relatórios)
─────────────────────
TOTAL: 26.000 leituras/dia
```

**Análise:**
- **52% do limite diário** ✅
- Ainda sobram 24.000 leituras
- **Status:** OK, mas usar com cuidado!

---

## 📊 Resumo Mensal (Para Contexto)

```
Dias úteis: 22 dias/mês
Leituras médias: 10.700/dia × 22 = 235.400/mês
Escritas médias: 40/dia × 22 = 880/mês
```

**Importante:** O Firebase conta por **DIA**, não por mês!
- Reset diário: **00:00 UTC** (21:00 hora local BR)
- Cada dia tem limite independente de 50.000 leituras

---

## 🎉 Conclusão: **VAI DAR, MAS COM ATENÇÃO!**

### ✅ Pontos Positivos
- **21,4% do limite diário** em uso normal
- Cache de 5 minutos economiza ~70% das leituras
- Listener focado (só em curso) economiza ~95%
- Margem de segurança: **78,6% livres**

### ⚠️ Pontos de Atenção
1. **Dias de pico podem chegar a 30-50% do limite**
2. **Não deixar múltiplas abas abertas** (cada aba = 1 PC)
3. **Fechar navegadores ao final do dia**
4. **Evitar F5 constante** (respeite o cache de 5min)

### 🚨 Quando se Preocupar
- Se passar de **35.000 leituras/dia** (70% do limite)
- Se tiver mais de **6 PCs simultâneos**
- Se desabilitar o cache (nunca faça isso!)

---

## 📈 Capacidade Máxima

### Quantos PCs simultâneos o sistema aguenta?

**Cálculo:**
```
Limite diário: 50.000 leituras
Uso por PC: ~2.700 leituras/dia (média)
Capacidade: 50.000 ÷ 2.700 = ~18 PCs
```

**Resposta:** Até **18 PCs simultâneos** no pior caso

Com otimizações e cache:
- **Uso normal:** Até 20-25 PCs
- **Uso leve:** Até 30 PCs

---

## 💡 Dicas para Economizar Quota

### 1. **Respeite o Cache (Crítico!)**
```javascript
// Cache de 5 minutos está configurado
// NÃO faça F5 constante!
```
**Economia:** ~70% das leituras

### 2. **Feche Abas Não Usadas**
- Cada aba aberta = 1 PC contando
- Listener continua ativo em segundo plano
- **Regra:** 1 pessoa = 1 aba aberta

### 3. **Evite Navegação Excessiva Entre Meses**
- O histórico já mostra o mês inteiro (500 registros)
- Só mude de mês quando realmente necessário
**Economia:** ~50% no PC3

### 4. **Use Filtros Específicos**
- Filtrar por data/veículo usa menos leituras que carregar tudo
- Exemplo: filtrar 1 dia = 10-20 leituras vs. mês todo = 500

---

## 🔍 Como Monitorar o Uso Real

### Firebase Console
1. Acesse: https://console.firebase.google.com
2. Vá em "Firestore Database" → "Usage"
3. Selecione **"Daily" (Diário)** no gráfico
4. Observe o consumo de cada dia

### Alertas Recomendados
Configure no Firebase:
- **⚠️ Alerta aos 35.000 leituras/dia** (70%)
- **🚨 Alerta aos 45.000 leituras/dia** (90%)

### Gráfico Esperado
```
Seg  Ter  Qua  Qui  Sex  Sáb  Dom
████ ████ ████ ████ ████ ▓▓▓▓ ░░░░
11k  10k  12k  10k  11k  3k   1k
```
- **Dias úteis:** 10-12k leituras
- **Fim de semana:** 1-3k leituras
- **Limite:** 50k/dia ─────────────────

---

## 🎯 Resposta Final

### Pergunta: "4 PCs simultâneos, vai dar considerando o limite diário de 50k?"

**RESPOSTA: SIM, VAI DAR TRANQUILAMENTE!**

✅ **Uso diário:** 10.700 leituras (21,4% do limite)
✅ **Margem de segurança:** 39.300 leituras livres (78,6%)
✅ **Dias de pico:** Até 26.000 leituras (52% do limite)
✅ **Capacidade máxima:** Até 18-20 PCs simultâneos

### Recomendações
1. ✅ Use normalmente com 4-6 PCs
2. ✅ Monitore o consumo diário no Firebase
3. ⚠️ Evite F5 constante (respeite o cache)
4. ⚠️ Feche abas não usadas ao fim do dia
5. 🚨 Configure alertas aos 70% do limite

### Zero Risco de Estouro
Com as otimizações implementadas (cache, listener focado, COUNT otimizado), é **praticamente impossível** estourar o limite diário com uso normal.

---

**Data do cálculo:** 08/01/2026  
**Versão do sistema:** v12.0  
**Limite considerado:** 50.000 leituras/DIA

---

## 📊 Otimizações Implementadas que Ajudam

### 1. **Cache Inteligente (5 minutos)**
- Dashboard: ~160 leituras economizadas a cada 5min
- Histórico: ~500 leituras economizadas a cada 5min
- **Economia:** ~60-70% das leituras

### 2. **Listener Focado**
- Apenas veículos **em curso** (5-10 docs)
- Não monitora toda a coleção
- **Economia:** ~95% comparado com listener global

### 3. **COUNT Otimizado**
- 1 leitura para contar ao invés de baixar todos documentos
- **Economia:** ~99% em contagens

### 4. **Limit de 500 por Mês**
- Carrega apenas o necessário
- Paginação visual se precisar
- **Economia:** ~80% em meses com muitos registros

---

## 🚨 Monitoramento Recomendado

### Como Verificar o Uso Real

1. **Firebase Console:**
   - Acesse: https://console.firebase.google.com
   - Vá em "Firestore Database" → "Usage"
   - Verifique gráficos de leituras/escritas

2. **Alertas Sugeridos:**
   - Configure alerta aos **70% do limite** (1.050.000 leituras/mês)
   - Receba email se aproximar do limite

3. **Picos de Uso:**
   - Dias com muitas consultas: pode chegar a 15.000 leituras/dia
   - Ainda assim, dentro do limite de 50.000/dia

---

## 📈 Projeções de Crescimento

### Se Dobrar o Uso (8 PCs)
```
Leituras: 468.600/mês (31,2% do limite) ✅
Escritas: 1.760/mês (0,3% do limite) ✅
```
**Status:** Ainda tranquilo!

### Se Triplicar o Uso (12 PCs)
```
Leituras: 702.900/mês (46,9% do limite) ✅
Escritas: 2.640/mês (0,44% do limite) ✅
```
**Status:** Com folga!

### Limite Teórico (Quando Precisaria Pagar)
```
Leituras: >1.500.000/mês
Isso daria com ~25-30 PCs simultâneos
```

---

## 💡 Dicas para Economizar Ainda Mais (Opcional)

### 1. Aumentar Tempo de Cache
```javascript
// De 5 minutos para 10 minutos
historico_cache['expires'] = time.time() + 600  // 10min
```
**Economia adicional:** ~30%

### 2. Lazy Loading no Histórico
- Carregar 100 registros iniciais
- "Carregar mais" sob demanda
**Economia adicional:** ~40% em meses grandes

### 3. Desabilitar Listener em Monitores Inativos
- Detecta inatividade após 30min
- Pausa listener automaticamente
**Economia adicional:** ~20% em PCs ociosos

---

## ✅ Resposta Final

### Pergunta: "4 PCs simultâneos, vai dar?"

**RESPOSTA: SIM, VAI DAR COM FOLGA!**

- ✅ Usa apenas 15,6% do limite gratuito
- ✅ Sobram 84,4% da quota
- ✅ Poderia ter até 25 PCs simultâneos
- ✅ Sistema otimizado com cache inteligente
- ✅ Zero custo mensal previsto

### Recomendação
**Não precisa se preocupar!** O sistema está super otimizado e vai rodar tranquilamente no plano gratuito do Firebase com 4, 6 ou até 10 PCs simultâneos.

---

## 📞 Suporte

Se quiser monitorar o uso real:
1. Acesse Firebase Console
2. Vá em "Usage" no Firestore
3. Configure alertas aos 70% do limite

**Data do cálculo:** 07/01/2026  
**Versão do sistema:** v12.0
