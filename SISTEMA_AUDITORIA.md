# 🔍 Sistema de Auditoria - Frota Sanemar

## Visão Geral

O sistema de auditoria registra **TODAS** as ações realizadas no banco de dados Firestore, criando um histórico completo e imutável de quem fez o quê, quando e como.

## Funcionalidades

### ✅ O que é registrado

Toda vez que alguém:
- **CRIA** um registro (veículo, motorista, saída, etc.)
- **ATUALIZA** um registro existente
- **EXCLUI** um registro

O sistema automaticamente salva:
1. **Quem** fez a ação (usuário logado)
2. **O que** foi feito (create, update, delete)
3. **Quando** foi feito (data/hora exata)
4. **Onde** foi feito (coleção e documento ID)
5. **Dados antes** da modificação (para rollback)
6. **Dados depois** da modificação
7. **IP do usuário** e navegador usado

## Estrutura dos Logs

Cada registro de auditoria na coleção `audit_log` contém:

```json
{
  "action": "update",                    // create, update ou delete
  "collection": "veiculos",              // Qual tabela foi afetada
  "document_id": "abc123xyz",            // ID do documento
  "user": "admin",                       // Quem fez a ação
  "timestamp": "2025-11-17T14:30:00Z",   // Quando aconteceu
  "ip_address": "192.168.1.100",         // IP do usuário
  "user_agent": "Mozilla/5.0...",        // Navegador usado
  "old_data": {                          // Dados ANTES da mudança
    "placa": "SNV8E77",
    "categoria": "Base de Itaipuaçu"
  },
  "new_data": {                          // Dados DEPOIS da mudança
    "categoria": "Comercial"
  }
}
```

## Onde é usado

### Veículos
- ✅ Criar veículo → `POST /api/veiculos`
- ✅ Excluir veículo → `DELETE /api/veiculos/<placa>`

### Motoristas
- ✅ Criar motorista → `POST /api/motoristas`
- ✅ Atualizar motorista → `PUT /api/motoristas/<id>`
- ✅ Excluir motorista → `DELETE /api/motoristas/<id>`

### Saídas
- ✅ Atualizar saída → `PATCH /api/saidas/<id>`
- ✅ Excluir saída → `DELETE /api/saidas/<id>`

## Como funciona

### 1. Função Principal: `log_audit()`

```python
def log_audit(action, collection_name, doc_id, old_data=None, new_data=None, user=None):
    """
    Registra uma ação de auditoria no Firestore.
    
    Args:
        action (str): 'create', 'update', 'delete'
        collection_name (str): Nome da coleção afetada
        doc_id (str): ID do documento afetado
        old_data (dict): Dados antes da modificação
        new_data (dict): Dados depois da modificação
        user (str): Usuário que executou (pega da sessão se None)
    """
```

### 2. Exemplo de Uso

**Antes:**
```python
# Código antigo - SEM auditoria
veiculo_ref.delete()
return jsonify({"message": "Veículo excluído"})
```

**Depois:**
```python
# Código novo - COM auditoria
veiculo_data = veiculo_doc.to_dict()  # Salva dados antigos
log_audit('delete', 'veiculos', veiculo_id, old_data=veiculo_data)
veiculo_ref.delete()
return jsonify({"message": "Veículo excluído"})
```

## Benefícios

### 🛡️ Segurança
- Rastreamento completo de todas as ações
- Impossível apagar sem deixar rastro
- Histórico imutável (logs não podem ser editados)

### 🔎 Investigação
- Descobrir quem deletou/modificou algo
- Ver exatamente o que mudou (antes x depois)
- Timestamp preciso de cada ação

### 📊 Compliance
- Atende requisitos de auditoria
- Prova em processos judiciais
- Histórico para fiscalização

### ⏪ Recuperação
- Dados antigos salvos permitem rollback
- Restaurar informações deletadas por engano
- Desfazer alterações indevidas

## Consultas Úteis

### Ver todas as ações de um usuário
```python
logs = db.collection('audit_log')\
  .where('user', '==', 'admin')\
  .order_by('timestamp', direction='DESCENDING')\
  .limit(100)\
  .get()
```

### Ver quem deletou um veículo
```python
logs = db.collection('audit_log')\
  .where('collection', '==', 'veiculos')\
  .where('action', '==', 'delete')\
  .where('document_id', '==', 'abc123')\
  .get()
```

### Ver todas as mudanças nas últimas 24h
```python
ontem = datetime.now() - timedelta(days=1)
logs = db.collection('audit_log')\
  .where('timestamp', '>', ontem)\
  .order_by('timestamp', direction='DESCENDING')\
  .get()
```

## Notas Importantes

### ⚠️ Não interrompe operações
Se o log de auditoria falhar (ex: Firestore indisponível), o sistema:
- Imprime erro no console
- **NÃO** cancela a operação principal
- Continua executando normalmente

### 💾 Armazenamento
- Logs nunca são deletados automaticamente
- Crescimento: ~1KB por ação
- Estimativa: 1000 ações/dia = ~30MB/mês

### 🔒 Privacidade
- Senhas e dados sensíveis devem ser filtrados
- Função `serialize_doc()` converte datetime para ISO
- IPs e user-agents salvos para rastreamento

## Melhorias Futuras

- [ ] Interface web para visualizar logs
- [ ] Filtros avançados (data, usuário, ação)
- [ ] Exportar relatórios em PDF
- [ ] Alertas de ações suspeitas
- [ ] Rollback automático via interface
- [ ] Retenção de logs (deletar após X meses)

## Implementação Técnica

**Arquivo:** `app.py`  
**Linhas:** 128-193  
**Coleção Firestore:** `audit_log`  
**Rotas afetadas:** Todas as rotas de POST/PUT/DELETE

---

**Data de Implementação:** 17/11/2025  
**Desenvolvedor:** Sistema Frota Sanemar  
**Status:** ✅ Operacional em Produção
