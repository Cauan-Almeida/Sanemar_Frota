# 👤 Sistema Multi-Usuário e Backup de Arquivos

## 📋 Visão Geral

Implementamos dois sistemas críticos:

1. **Multi-Usuário**: Cada pessoa tem seu próprio login e senha
2. **Backup Automático**: Arquivos (CNH, documentos) são salvos antes de deletar

---

## 👥 Sistema Multi-Usuário

### Tipos de Usuário

| Tipo | Permissões | Onde Acessa |
|------|-----------|-------------|
| **admin** | Tudo (criar usuários, editar, deletar) | Dashboard completo |
| **historico** | Ver e editar histórico de viagens | Página de histórico |
| **operador** | Registrar saídas/chegadas | Página inicial apenas |

### Estrutura no Firestore

**Coleção:** `usuarios`

```json
{
  "username": "joao.silva",
  "password_hash": "$2b$12$XyZ...",  // Bcrypt hash
  "nome_completo": "João Silva",
  "tipo": "admin",  // admin, historico ou operador
  "ativo": true,
  "data_criacao": "2025-11-17T15:30:00-03:00"
}
```

### Como Criar Primeiro Usuário Admin

**Opção 1: Via Firebase Console**
1. Acesse Firebase Console → Firestore
2. Crie coleção `usuarios`
3. Adicione documento com:
```json
{
  "username": "admin",
  "password_hash": "COLE_HASH_AQUI",
  "nome_completo": "Administrador",
  "tipo": "admin",
  "ativo": true,
  "data_criacao": (timestamp atual)
}
```

**Opção 2: Via Python (criar script)**
```python
import bcrypt
password = "suaSenhaSegura123"
salt = bcrypt.gensalt()
hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
print(hashed.decode('utf-8'))
```

### API de Gerenciamento de Usuários

#### Listar Usuários
```http
GET /api/usuarios
Authorization: session (admin)
```

**Resposta:**
```json
[
  {
    "id": "abc123",
    "username": "joao.silva",
    "nome_completo": "João Silva",
    "tipo": "admin",
    "ativo": true,
    "data_criacao": "2025-11-17T15:30:00"
  }
]
```

#### Criar Usuário
```http
POST /api/usuarios
Authorization: session (admin)
Content-Type: application/json

{
  "username": "maria.santos",
  "password": "senha123",
  "nome_completo": "Maria Santos",
  "tipo": "historico"
}
```

#### Atualizar Usuário
```http
PUT /api/usuarios/<id>
Authorization: session (admin)
Content-Type: application/json

{
  "nome_completo": "Maria Santos Silva",
  "tipo": "admin",
  "ativo": true,
  "password": "novaSenha456"  // opcional
}
```

#### Desativar Usuário
```http
DELETE /api/usuarios/<id>
Authorization: session (admin)
```

**Nota:** Não deleta o usuário, apenas marca como `ativo: false`

---

## 💾 Sistema de Backup Automático

### O que é feito backup

Quando você **DELETA**:
- **Motorista** → CNH anexada
- **Veículo** → Documento anexado

### Como funciona

1. **Antes de deletar**, o arquivo é COPIADO para pasta especial
2. **Caminho do backup**: `deleted_backups/{timestamp}_{motivo}/{caminho_original}`
3. **URL do backup** é salva no `audit_log` junto com os dados deletados

### Exemplo

**Original:**
```
motoristas/abc123/cnh_1234567890.pdf
```

**Backup:**
```
deleted_backups/20251117_153045_motorista_deleted/motoristas/abc123/cnh_1234567890.pdf
```

### Estrutura no Audit Log

Quando motorista/veículo é deletado:

```json
{
  "action": "delete",
  "collection": "motoristas",
  "document_id": "abc123",
  "user": "admin",
  "timestamp": "2025-11-17T15:30:45Z",
  "old_data": {
    "nome": "João Silva",
    "cnh_url": "https://...original...",
    "_backups": [
      {
        "tipo": "cnh",
        "url_original": "https://...original...",
        "url_backup": "https://...backup..."
      }
    ]
  }
}
```

### Benefícios

✅ **Nada se perde**: Todos os arquivos ficam salvos  
✅ **Fácil recuperação**: URLs no audit_log permitem baixar  
✅ **Prova jurídica**: Arquivo original preservado  
✅ **Organização**: Backup separado por data e motivo  

---

## 🔐 Segurança

### Senhas

- **Nunca** guardadas em texto plano
- **Hash Bcrypt** com salt aleatório
- **SHA256 fallback** caso bcrypt não esteja instalado

### Auditoria

Todas as ações em usuários são registradas:
- Login de usuário → `audit_log`
- Criação de usuário → `audit_log`
- Atualização de usuário → `audit_log`
- Desativação de usuário → `audit_log`

### Proteção

- ❌ Não pode deletar própria conta
- ❌ Não pode desativar último admin
- ✅ Backup automático antes de qualquer delete
- ✅ Histórico completo de quem fez o quê

---

## 📊 Dados Salvos

### Quando deleta Motorista

```json
{
  "_backups": [
    {
      "tipo": "cnh",
      "url_original": "https://storage.googleapis.com/.../cnh_123.pdf",
      "url_backup": "https://storage.googleapis.com/.../deleted_backups/.../cnh_123.pdf"
    }
  ]
}
```

### Quando deleta Veículo

```json
{
  "_backups": [
    {
      "tipo": "documento",
      "url_original": "https://storage.googleapis.com/.../doc_456.pdf",
      "url_backup": "https://storage.googleapis.com/.../deleted_backups/.../doc_456.pdf"
    }
  ]
}
```

---

## 🎯 Próximos Passos

### Migração

1. **Instalar bcrypt**: `pip install bcrypt`
2. **Criar usuário admin** via Firebase Console
3. **Testar login** com novo usuário
4. **Criar contas** para equipe via dashboard
5. **Remover** variáveis ADMIN_USERNAME/ADMIN_PASSWORD do .env

### Interface Web (TODO)

- [ ] Aba "Usuários" no dashboard (somente admin)
- [ ] Formulário criar/editar usuário
- [ ] Lista de usuários com filtro ativo/inativo
- [ ] Visualizador de backups (listar arquivos deletados)
- [ ] Botão "Restaurar" arquivo de backup

---

## 📝 Exemplos de Uso

### Criar 3 Usuários (Admin, Histórico, Operador)

**1. Admin (você)**
```json
{
  "username": "admin",
  "password": "SuaSenhaSuperSegura2025!",
  "nome_completo": "Seu Nome Completo",
  "tipo": "admin"
}
```

**2. Pessoa do Histórico**
```json
{
  "username": "historico",
  "password": "hist123",
  "nome_completo": "Nome da Pessoa",
  "tipo": "historico"
}
```

**3. Operadores (campo)**
```json
{
  "username": "operador1",
  "password": "oper123",
  "nome_completo": "Operador Um",
  "tipo": "operador"
}
```

### Consultar Backups de um Motorista Deletado

```python
# Busca no audit_log
logs = db.collection('audit_log')\
  .where('action', '==', 'delete')\
  .where('collection', '==', 'motoristas')\
  .order_by('timestamp', direction='DESCENDING')\
  .limit(50)\
  .get()

for log in logs:
    data = log.to_dict()
    if '_backups' in data.get('old_data', {}):
        print(f"Motorista: {data['old_data'].get('nome')}")
        print(f"Backup CNH: {data['old_data']['_backups'][0]['url_backup']}")
```

---

**Status:** ✅ Implementado e funcional  
**Data:** 17/11/2025  
**Requer:** bcrypt (`pip install bcrypt`)  
**Firestore:** Coleções `usuarios` e `audit_log`
