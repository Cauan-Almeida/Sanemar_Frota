# 🔍 Como Encontrar e Remover Footer Duplicado no Mobile

## Passo 1: Identificar o Elemento

**No celular, abra o Dashboard e execute este código no console:**

1. Abra o site no Chrome mobile
2. Acesse: `chrome://inspect`
3. Ative "Remote Debugging"
4. No console, cole este código:

```javascript
// Encontra elementos fixos ou absolutos
const fixed = Array.from(document.querySelectorAll('*')).filter(el => {
    const style = window.getComputedStyle(el);
    const position = style.position;
    const bottom = style.bottom;
    const zIndex = style.zIndex;
    
    if ((position === 'fixed' || position === 'absolute') && 
        (bottom === '0px' || bottom === '0')) {
        console.log('🔴 Elemento encontrado:', {
            tag: el.tagName,
            id: el.id,
            classes: el.className,
            position: position,
            bottom: bottom,
            zIndex: zIndex,
            html: el.outerHTML.substring(0, 200)
        });
        return true;
    }
    return false;
});

console.log(`\n📊 Total de elementos fixos no bottom: ${fixed.length}`);
fixed.forEach((el, i) => {
    el.style.border = '3px solid red';
    el.setAttribute('data-debug-id', `footer-${i}`);
});
```

## Passo 2: Remover o Duplicado

Depois de identificar qual elemento está duplicado (terá borda vermelha), me informe:
- O **ID** do elemento
- As **classes CSS**
- Uma captura de tela se possível

## Possíveis Culpados

Baseado no código, os elementos que podem estar duplicados são:

1. **Botão Hamburger** (linha 576 do dashboard.html)
   - ID: `hamburger-btn`
   - Classe: `hamburger-btn`

2. **Botão Open Sidebar** (linha 585 do dashboard.html)
   - ID: `open-sidebar`
   - Deve estar escondido (`hidden`)

3. **Algum elemento de navegação mobile** em um dos arquivos JS:
   - `/static/dashboard.js`
   - `/static/dashboard-realtime.js`
   - `/static/veiculos-tab.js`
   - `/static/km-multas.js`
   - `/static/revisoes-tab.js`

## Solução Temporária (Testar)

Cole este código no console para esconder elementos duplicados:

```javascript
// Remove elementos duplicados com mesmo ID
const ids = {};
document.querySelectorAll('[id]').forEach(el => {
    if (ids[el.id]) {
        console.log('🗑️ Removendo duplicata:', el.id);
        el.remove();
    } else {
        ids[el.id] = el;
    }
});
```

## Me Envie

Após executar o Passo 1, me envie:
1. O log do console (print)
2. Print da tela com os elementos com borda vermelha
3. Qual dos elementos está duplicado

Assim posso remover o código correto!
