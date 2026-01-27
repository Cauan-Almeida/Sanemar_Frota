# 🔒 Segurança e Proteção de Rotas - Sistema de Frota Sanemar

## ✅ Todas as Rotas Protegidas

### Rotas Públicas (Sem Autenticação)
- `/login` - Página de login
- `/maintenance` - Página de manutenção
- `/sw.js` - Service Worker
- `/health` - Health check para monitoramento
- `/api/maintenance/status` - Status do modo de manutenção

### Rotas Administrativas (requerem login como `admin`)
Todas as rotas abaixo exigem `@requires_auth` (usuário admin):

#### Páginas Principais
- `/dashboard` - Dashboard administrativo
- `/motoristas` - Gestão de motoristas
- `/revisoes` - Gestão de revisões e chamados de manutenção
- `/veiculos` - Gestão de veículos
- `/motorista/<nome>` - Detalhes de motorista específico
- `/veiculo/<placa>` - Detalhes de veículo específico

#### APIs de Operação
- `/api/saida` (POST) - Registrar saída de veículo
- `/api/chegada` (POST) - Registrar chegada de veículo
- `/api/abastecimento` (POST) - Registrar abastecimento
- `/api/cancelar` (POST) - Cancelar viagem em curso
- `/api/veiculos_em_curso` (GET) - Listar veículos em curso

#### APIs de Gestão de Dados
- `/api/usuarios` (GET, POST) - Gerenciar usuários
- `/api/usuarios/<user_id>` (PUT, DELETE) - Editar/excluir usuário
- `/api/audit-logs` (GET) - Logs de auditoria
- `/api/motoristas` (GET, POST) - Gerenciar motoristas
- `/api/motoristas/<motorista_id>` (PUT, DELETE) - Editar/excluir motorista
- `/api/motoristas/<motorista_id>/upload-cnh` (POST) - Upload de CNH
- `/api/motoristas/<motorista_id>/cnh` (GET) - Ver CNH
- `/api/motoristas/<motorista_id>/status` (PATCH) - Alterar status motorista
- `/api/veiculos` (GET, POST) - Gerenciar veículos
- `/api/veiculos/<placa>` (GET, PATCH, DELETE) - Editar/excluir veículo
- `/api/veiculos/<placa>/metrics` (GET) - Métricas do veículo
- `/api/veiculos/<veiculo_id>/upload-documento` (POST) - Upload documento veículo
- `/api/veiculos/<veiculo_id>/documento` (GET) - Ver documento veículo
- `/api/veiculos/<veiculo_id>/status` (PATCH) - Alterar status veículo
- `/api/veiculos/refuels` (POST) - Registrar abastecimento
- `/api/veiculos/<placa>/refuels` (GET) - Histórico de abastecimentos
- `/api/refuels/<refuel_id>` (PATCH, DELETE) - Editar/excluir abastecimento
- `/api/refuels/summary` (GET) - Resumo de abastecimentos
- `/api/saidas/<saida_id>` (PATCH, DELETE) - Editar/excluir saída
- `/api/saidas/<saida_id>/atualizar-rapido` (PATCH) - Atualização rápida
- `/api/dashboard_stats` (GET) - Estatísticas do dashboard
- `/api/dashboard_cache/clear` (POST) - Limpar cache
- `/api/dashboard_realtime` (GET) - Dados em tempo real
- `/api/km-mensal` (GET, POST) - Gerenciar KM mensal
- `/api/km-mensal/<registro_id>` (PUT, DELETE) - Editar/excluir KM
- `/api/multas` (GET, POST) - Gerenciar multas
- `/api/multas/<multa_id>` (PUT, DELETE) - Editar/excluir multa
- `/api/multas/<multa_id>/upload-documento` (POST) - Upload documento multa
- `/api/multas/<multa_id>/documento` (GET) - Ver documento multa
- `/api/revisoes` (GET, POST) - Gerenciar revisões
- `/api/revisoes/<revisao_id>` (GET, PUT, DELETE) - Editar/excluir revisão

#### APIs de Relatórios PDF (requerem autenticação)
- `/pdf/motoristas` - PDF de motoristas
- `/pdf/veiculos` - PDF de veículos
- `/pdf/abastecimentos` - PDF de abastecimentos
- `/pdf/saidas` - PDF de saídas/viagens
- `/pdf/multas` - PDF de multas
- `/pdf/revisoes` - PDF de revisões (com filtros)
- `/pdf/km-mensal` - PDF de KM mensal

### Rotas de Histórico (requerem login como `historico` ou `admin`)
- `/historico` - Página de histórico (somente leitura)
- `/api/historico` (GET) - API de histórico

## 🚫 Acesso Negado

Todas as tentativas de acessar rotas protegidas sem autenticação resultarão em:
- **Redirecionamento automático para `/login`**
- A URL original será preservada para redirecionar após login bem-sucedido

### Exemplo de Proteção

```python
@app.route('/dashboard')
@requires_auth  # Decorator que verifica se usuário está autenticado
def dashboard():
    if not FIRESTORE_AVAILABLE:
        return render_template('maintenance.html'), 503
    return render_template('dashboard.html')
```

## 🔐 Tipos de Usuários

### 1. Admin (`admin`)
- **Acesso total** a todas as funcionalidades
- Pode criar, editar e excluir registros
- Acesso aos logs de auditoria
- Gestão de usuários

### 2. Histórico (`historico`)
- **Acesso somente leitura** ao histórico de viagens
- Pode visualizar relatórios
- Não pode modificar dados

### 3. Operador (`operador`)
- **Acesso limitado** apenas à página inicial (`/`)
- Pode registrar saídas e chegadas de veículos
- Não tem acesso ao dashboard administrativo

## 📊 Sistema de Revisões

### Acesso à Página de Revisões
1. **Via Dashboard**: Clicar no menu lateral "Controle Operacional" > "Revisões"
2. **Via URL Direta**: Acessar `/revisoes` (somente autenticados)

### Funcionalidades
- ✅ Cadastro de chamados de manutenção
- ✅ Gestão de status (Pendente, Andamento, Resolvido)
- ✅ Filtros por categoria (Pneu, Revisão, Mecânica, Lataria)
- ✅ Edição e exclusão de chamados
- ✅ Geração de PDF com filtros

### Gerar PDF de Revisões
```
GET /pdf/revisoes
Query Parameters:
  - veiculo: filtrar por placa (opcional)
  - status: filtrar por status - em_dia, proxima, atrasada (opcional)

Exemplo:
/pdf/revisoes?veiculo=ABC1234&status=atrasada
```

## 🛡️ Segurança Adicional

### Modo de Manutenção
O sistema possui um modo de manutenção que bloqueia TODAS as rotas exceto:
- `/maintenance` - Página de manutenção
- `/api/maintenance/off` - Para desativar o modo
- Arquivos estáticos (`/static/`)

### Service Worker
- Implementado para cache offline
- Detecta automaticamente novas versões
- Força atualização quando nova versão está disponível

### Logs de Auditoria
Todas as ações são registradas:
- Quem fez (usuário)
- O que fez (create, update, delete)
- Quando (timestamp)
- Onde (coleção e documento)
- Dados antes e depois (para rollback)

## ✅ Checklist de Segurança

- [x] Todas as rotas administrativas protegidas
- [x] Todas as APIs protegidas
- [x] Rota de histórico com autenticação separada
- [x] Sistema de sessões implementado
- [x] Logout funcional
- [x] Redirecionamento após login
- [x] Proteção contra acesso direto a templates
- [x] Logs de auditoria para rastreabilidade
- [x] Modo de manutenção para emergências
- [x] Páginas de revisões protegidas e funcionais

## 🚀 Como Acessar o Sistema

1. **Acesse**: `https://seu-dominio.com/login`
2. **Entre com suas credenciais**:
   - Admin: acesso total
   - Histórico: somente relatórios
   - Operador: apenas lançamentos
3. **Será redirecionado** para a área correspondente ao seu tipo de usuário

---

**⚠️ IMPORTANTE**: Nunca compartilhe suas credenciais. Todas as ações são registradas nos logs de auditoria.

**Última atualização**: 27 de Janeiro de 2026
