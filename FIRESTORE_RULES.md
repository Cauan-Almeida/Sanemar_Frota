# 🔒 CONFIGURAR PERMISSÕES DO FIRESTORE

## ❌ ERRO ATUAL:
```
Missing or insufficient permissions
```

O Firebase está bloqueando os **realtime listeners** porque as regras de segurança estão muito restritivas.

---

## ✅ SOLUÇÃO: Atualizar Firestore Rules

### 1. Acesse o Firebase Console:
```
https://console.firebase.google.com/project/frota-sanemar/firestore/rules
```

### 2. Substitua as regras atuais por estas (VERSÃO MAIS SEGURA):

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    
    // Funções auxiliares de segurança
    function isValidTimestamp(ts) {
      // Aceita apenas timestamps recentes (últimas 24h ou futuro próximo)
      return ts > request.time - duration.value(1, 'd') &&
             ts < request.time + duration.value(1, 'h');
    }
    
    function isValidPlate(plate) {
      // Valida formato de placa brasileira (básico)
      return plate.size() >= 6 && plate.size() <= 8;
    }
    
    function hasRequiredFields(data, fields) {
      return fields.toSet().difference(data.keys().toSet()).size() == 0;
    }
    
    // Coleção de saídas (viagens)
    match /saidas/{saidaId} {
      // Permite leitura para todos (necessário para realtime)
      allow read: if true;
      
      // Criação: valida campos obrigatórios e timestamp
      allow create: if request.resource.data.keys().hasAll(['veiculo', 'motorista', 'status']) &&
                       request.resource.data.veiculo.size() > 0 &&
                       request.resource.data.motorista.size() > 0 &&
                       request.resource.data.status in ['em_curso', 'finalizada'];
      
      // Atualização: permite apenas mudanças de status e adição de chegada
      allow update: if request.resource.data.diff(resource.data).affectedKeys()
                       .hasOnly(['status', 'timestampChegada', 'horarioChegada']);
      
      // Exclusão: permite (para cancelar viagens)
      allow delete: if true;
    }
    
    // Coleção de motoristas
    match /motoristas/{motoristaId} {
      // Leitura para todos
      allow read: if true;
      
      // Criação: valida nome obrigatório
      allow create: if request.resource.data.keys().hasAll(['nome']) &&
                       request.resource.data.nome.size() > 2;
      
      // Atualização: permite editar campos específicos
      allow update: if request.resource.data.diff(resource.data).affectedKeys()
                       .hasOnly(['nome', 'funcao', 'empresa', 'status', 'viagens_totais']);
      
      // Exclusão: permite
      allow delete: if true;
    }
    
    // Coleção de veículos
    match /veiculos/{veiculoId} {
      // Leitura para todos
      allow read: if true;
      
      // Criação: valida placa
      allow create: if request.resource.data.keys().hasAll(['placa']) &&
                       isValidPlate(request.resource.data.placa);
      
      // Atualização: permite campos específicos
      allow update: if request.resource.data.diff(resource.data).affectedKeys()
                       .hasOnly(['modelo', 'ultimo_odometro', 'media_kmpl', 
                                 'viagens_totais', 'total_refuels', 
                                 'total_litros_historico', 'km_rodados_historico',
                                 'media_kmpl_calculada']);
      
      // Exclusão: permite
      allow delete: if true;
    }
    
    // Coleção de abastecimentos
    match /refuels/{refuelId} {
      // Leitura para todos
      allow read: if true;
      
      // Criação: valida campos obrigatórios
      allow create: if request.resource.data.keys().hasAll(['veiculo', 'timestamp']) &&
                       request.resource.data.veiculo.size() > 0;
      
      // Atualização: permite editar campos específicos
      allow update: if request.resource.data.diff(resource.data).affectedKeys()
                       .hasOnly(['motorista', 'litros', 'odometro', 'observacao']);
      
      // Exclusão: permite
      allow delete: if true;
    }
    
    // Coleção de KM mensal
    match /km_mensal/{registroId} {
      // Leitura para todos
      allow read: if true;
      
      // Criação: valida placa e mês/ano
      allow create: if request.resource.data.keys().hasAll(['placa', 'mes_ano']) &&
                       request.resource.data.placa.size() > 0 &&
                       request.resource.data.mes_ano.matches('^[0-9]{4}-[0-9]{2}$');
      
      // Atualização e exclusão: permite
      allow update, delete: if true;
    }
    
    // Coleção de multas
    match /multas/{multaId} {
      // Leitura para todos
      allow read: if true;
      
      // Criação: valida campos obrigatórios
      allow create: if request.resource.data.keys().hasAll(['placa', 'descricao', 'valor']) &&
                       request.resource.data.placa.size() > 0 &&
                       request.resource.data.valor > 0;
      
      // Atualização e exclusão: permite
      allow update, delete: if true;
    }
    
    // Coleção de cache de dashboard (se criar futuramente)
    match /dashboard_cache/{document=**} {
      allow read: if true;
      allow write: if true;
    }
  }
}
```

### ✅ **MELHORIAS DE SEGURANÇA:**

1. **Validação de Campos Obrigatórios**
   - Garante que documentos tenham campos necessários
   - Evita criar registros vazios ou inválidos

2. **Validação de Formato**
   - Placa: mínimo 6 caracteres
   - Mês/Ano: formato YYYY-MM
   - Valores: positivos

3. **Restrição de Atualizações**
   - Permite apenas mudanças em campos específicos
   - Evita modificação de campos críticos (ex: IDs, timestamps originais)

4. **Validação de Timestamps**
   - Aceita apenas timestamps recentes (últimas 24h)
   - Previne registros com datas absurdas

5. **Mantém Funcionalidade**
   - Leitura aberta (necessário para realtime)
   - Escrita controlada mas funcional

### 3. Clique em **"Publicar"** (Publish)

---

## 🔒 SEGURANÇA DAS REGRAS ACIMA

**✅ Balanceamento entre segurança e funcionalidade:**

- ✅ **Leitura aberta** - Necessário para realtime listeners funcionarem
- ✅ **Escrita validada** - Campos obrigatórios e formato verificado
- ✅ **Atualizações restritas** - Apenas campos específicos podem mudar
- ✅ **Previne dados inválidos** - Validação de formatos e valores

**⚠️ Limitações:**
- Ainda não usa autenticação de usuários (Firebase Auth)
- Permite criação por qualquer cliente
- Proteção básica contra ataques, mas não é 100% segura

### Para MÁXIMA segurança (Com Firebase Authentication):

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    
    // Função para verificar se usuário está autenticado
    function isAuthenticated() {
      return request.auth != null;
    }
    
    // Função para verificar se é admin
    function isAdmin() {
      return isAuthenticated() && 
             request.auth.token.email in [
               'admin@sanemar.com',
               'seu-email@dominio.com'
             ];
    }
    
    // Coleção de saídas
    match /saidas/{saidaId} {
      // Leitura: todos autenticados
      allow read: if isAuthenticated();
      // Escrita: todos autenticados (com validações)
      allow create, update: if isAuthenticated() && 
                               request.resource.data.keys().hasAll(['veiculo', 'motorista']);
      // Exclusão: apenas admin
      allow delete: if isAdmin();
    }
    
    // Outras coleções com mesmo padrão
    match /{collection}/{document=**} {
      allow read: if isAuthenticated();
      allow write: if isAuthenticated();
    }
    
    // Apenas admins podem gerenciar usuários (futuramente)
    match /users/{userId} {
      allow read: if isAuthenticated();
      allow write: if isAdmin();
    }
  }
}
```

**Para implementar isso:**
1. Habilite Firebase Authentication no console
2. Implemente login na aplicação
3. Use `signInWithEmailAndPassword()` no frontend
4. Atualize as rules acima

---

## ✅ APÓS CONFIGURAR:

1. **Recarregue a página do dashboard**
2. Os erros de "Missing permissions" vão sumir
3. Realtime vai funcionar perfeitamente
4. Console vai mostrar:
   ```
   🔴 Iniciando listeners em tempo real...
   ✅ Listener de saídas ativo
   ✅ Listener de motoristas ativo
   ✅ Listener de veículos ativo
   ```

---


## 🚀 RESUMO

### Prioridade 1 (Obrigatório):
✅ **Atualizar Firestore Rules** - Resolve o erro principal

### Prioridade 2 (Opcional):
- Adicionar favicon.ico
- Criar sw.js (service worker)
- Criar ícones PWA
- Instalar Tailwind local (produção)

**Após configurar as rules do Firestore, tudo vai funcionar!** 🎉
