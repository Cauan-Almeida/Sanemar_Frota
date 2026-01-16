# 🔧 Sistema de Manutenção

## Como Ativar o Modo de Manutenção

### Método 1: Via Arquivo `.maintenance`
1. Abra o arquivo `.maintenance` na raiz do projeto
2. Mude o conteúdo de `off` para `on`
3. Salve o arquivo
4. **Não precisa reiniciar o servidor** - detecta automaticamente a cada 30 segundos

### Método 2: Via Endpoint API (Recomendado)
```bash
# Ativar manutenção
curl -X POST http://localhost:5000/api/maintenance/on

# Desativar manutenção
curl -X POST http://localhost:5000/api/maintenance/off

# Verificar status
curl http://localhost:5000/api/maintenance/status
```

### Método 3: Via Terminal Python
```python
# Ativar
python -c "open('.maintenance', 'w').write('on')"

# Desativar
python -c "open('.maintenance', 'w').write('off')"
```

## O que Acontece no Modo de Manutenção

✅ **Usuários veem**: Tela de manutenção bonita informando que o sistema está temporariamente indisponível

❌ **Bloqueado**: 
- Dashboard
- Login
- Todas as rotas normais do sistema

✅ **Permitido**:
- Endpoint de status de manutenção (`/api/maintenance/status`)
- Endpoints de ativação/desativação

## Backup e Reversão no GitHub

### Commits Automáticos
Cada mudança importante cria um commit com:
- **Tag versionada**: `v2.X.Y` (semântico)
- **Descrição detalhada**: O que foi alterado
- **Reversível**: Use `git revert <commit-hash>` para desfazer

### Ver Histórico
```bash
# Ver commits recentes
git log --oneline --graph --all -20

# Ver mudanças de um commit específico
git show <commit-hash>
```

### Reverter Mudanças
```bash
# Reverter último commit (mantém no histórico)
git revert HEAD

# Voltar para um commit específico (cuidado!)
git reset --hard <commit-hash>

# Criar branch de backup antes de mudanças grandes
git checkout -b backup-antes-de-mudar
```

## Boas Práticas

1. **Antes de mexer no servidor real**: Ative a manutenção
2. **Depois de testar**: Desative a manutenção
3. **Commits frequentes**: Cada feature nova = 1 commit
4. **Mensagens claras**: Descreva o que mudou
5. **Tags de versão**: Mudanças grandes recebem tag (v2.1.0, v2.2.0, etc.)
