# 🔧 Como Ativar o Modo de Manutenção

## No Servidor RENDER (Produção) - Versão GRATUITA

### ⭐ Opção 1: Via Arquivo .maintenance no Git (Mais Fácil para Render Free)

1. **No seu computador**, crie o arquivo `.maintenance`:
```bash
echo "maintenance" > .maintenance
```

2. **Faça commit e push:**
```bash
git add .maintenance
git commit -m "Ativar modo de manutenção"
git push origin main
```

3. O Render fará deploy automático (demora ~2-3 minutos) e o modo de manutenção será ativado

4. **Para desativar**, altere o conteúdo para "off":
```bash
echo "off" > .maintenance
git add .maintenance
git commit -m "Desativar modo de manutenção"
git push origin main
```

### Opção 2: Usar Variável de Ambiente no Render

1. Acesse o painel do Render: https://dashboard.render.com
2. Clique no seu serviço "frota-sanemar"
3. Vá em **Environment** 
4. Adicione uma nova variável:
   - **Key:** `MAINTENANCE_MODE`
   - **Value:** `true`
5. Clique em **Save Changes** - O Render reiniciará automaticamente

6. Para desativar:
   - Mude o **Value** para `false` ou delete a variável
   - Salve novamente

**Nota:** Esta opção requer modificação no código Python para ler a variável de ambiente.

### ⚠️ Opção 3 NÃO FUNCIONA no Render Free

A opção de usar Shell do Render NÃO está disponível no plano gratuito.

---

## Comportamento do Modo de Manutenção

Quando ativo:
- ✅ Todos os usuários são redirecionados para `/maintenance`
- ✅ Aparece uma tela bonita com animações informando sobre a manutenção
- ✅ As rotas `/api/maintenance/*` continuam funcionando (para você gerenciar)
- ❌ Nenhuma outra página ou API funciona

Quando desativado:
- ✅ Sistema volta ao normal
- ✅ Todos conseguem acessar

## Testando Localmente

1. Criar arquivo:
```bash
echo "maintenance" > .maintenance
```

2. Iniciar servidor:
```bash
python app.py
```

3. Acessar http://localhost:5000 - verá a tela de manutenção

4. Para desativar:
```bash
echo "off" > .maintenance
```

5. Recarregar a página - sistema volta ao normal

## Notas Importantes

⚠️ **ATENÇÃO:**
- O arquivo `.maintenance` não deve estar no `.gitignore` se você quiser usar a Opção 3
- No Render, o arquivo `.maintenance` será recriado a cada deploy se você fizer commit dele
- A melhor prática é usar a Opção 1 (Shell do Render) para controle rápido sem precisar fazer deploy
