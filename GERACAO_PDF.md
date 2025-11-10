# 📄 SISTEMA DE GERAÇÃO DE PDFs

## ✅ Implementado

### 1. **Excluir Motorista**
- ✅ Botão "Excluir" já existia na página `/motoristas`
- ✅ Rota DELETE já implementada: `/api/motoristas/<id>`
- ✅ Confirmação antes de excluir

---

## 📑 Rotas de PDF Criadas

### 1. `/pdf/motoristas`
**Gera PDF com lista completa de motoristas**

- 📊 Colunas: Nome, Empresa, Função, Viagens Totais
- 🎨 Design: Tabela com cabeçalho roxo
- 📥 Download automático com timestamp

**Como usar:**
- Clique em "📄 Gerar PDF" na página `/motoristas`
- Ou acesse: `http://localhost:5000/pdf/motoristas`

---

### 2. `/pdf/veiculos`
**Gera PDF com lista completa de veículos**

- 📊 Colunas: Placa, Modelo, Km Atual, Média km/L, Total Abastecimentos
- 🎨 Design: Tabela com cabeçalho verde
- 📥 Download automático com timestamp

**Como usar:**
- Clique em "📄 Gerar PDF" na página `/veiculos`
- Ou acesse: `http://localhost:5000/pdf/veiculos`

---

### 3. `/pdf/abastecimentos`
**Gera PDF com histórico de abastecimentos (COM FILTROS)**

- 📊 Colunas: Data, Veículo, Motorista, Litros, Valor, Odômetro, km/L
- 🎨 Design: Tabela em paisagem (landscape) com cabeçalho laranja
- 🔍 **Filtros disponíveis (query params):**
  - `?veiculo=ABC1234` - Apenas um veículo específico
  - `?data_inicio=2025-01-01` - A partir de uma data
  - `?data_fim=2025-12-31` - Até uma data
- 📦 Limite: 500 registros

**Exemplos de uso:**

```
# Todos os abastecimentos
http://localhost:5000/pdf/abastecimentos

# Apenas de um veículo
http://localhost:5000/pdf/abastecimentos?veiculo=ABC1234

# De um período
http://localhost:5000/pdf/abastecimentos?data_inicio=2025-01-01&data_fim=2025-12-31

# Veículo específico em período
http://localhost:5000/pdf/abastecimentos?veiculo=ABC1234&data_inicio=2025-10-01&data_fim=2025-10-31
```

**Botões adicionados:**
- ✅ Na página `/veiculos/<placa>`: botão "📄 PDF" gera PDF daquele veículo

---

### 4. `/pdf/saidas`
**Gera PDF com histórico de saídas (COM FILTROS)**

- 📊 Colunas: Data Saída, Veículo, Motorista, Destino, Status, Data Retorno
- 🎨 Design: Tabela em paisagem com cabeçalho azul
- 🔍 **Filtros disponíveis (query params):**
  - `?veiculo=ABC1234` - Apenas um veículo
  - `?motorista=João` - Apenas um motorista
  - `?status=em_curso` ou `?status=finalizada` - Por status
  - `?data_inicio=2025-01-01` - A partir de uma data
  - `?data_fim=2025-12-31` - Até uma data
- 📦 Limite: 500 registros

**Exemplos de uso:**

```
# Todas as saídas
http://localhost:5000/pdf/saidas

# Apenas em curso
http://localhost:5000/pdf/saidas?status=em_curso

# De um motorista específico
http://localhost:5000/pdf/saidas?motorista=João Silva

# Finalizadas de um veículo em outubro
http://localhost:5000/pdf/saidas?veiculo=ABC1234&status=finalizada&data_inicio=2025-10-01&data_fim=2025-10-31
```

**Botões adicionados:**
- ✅ No dashboard: botão "📄 Gerar PDF" na tabela de histórico

---

## 🎨 Características dos PDFs

### Design Profissional
- ✅ Cabeçalhos coloridos por tipo de relatório
- ✅ Linhas alternadas (zebra) para melhor leitura
- ✅ Fonte Helvetica profissional
- ✅ Logo e informações da empresa
- ✅ Data/hora de geração

### Formato
- 📄 **Retrato (Portrait)**: Motoristas, Veículos
- 🖼️ **Paisagem (Landscape)**: Abastecimentos, Saídas (mais colunas)
- 📏 Tamanho: A4
- 🔢 Paginação automática

### Dados
- ✅ Formatação de datas brasileiras (DD/MM/AAAA)
- ✅ Valores monetários: R$ 0,00
- ✅ Litros com 1 casa decimal: 50.5L
- ✅ km/L com 2 casas decimais: 12.34
- ✅ Status com emojis: ✅ Finalizada / 🚗 Em Curso

---

## 📦 Bibliotecas Instaladas

```txt
reportlab  # Geração de PDFs
Pillow     # Processamento de imagens (dependência)
```

---

## 🎯 Locais dos Botões

### 1. Página de Motoristas (`/motoristas`)
```
[📄 Gerar PDF]  ← Canto superior direito
```

### 2. Página de Veículos (`/veiculos`)
```
[📄 Gerar PDF] [➕ Cadastrar Veículo]
```

### 3. Detalhes do Veículo (`/veiculos/<placa>`)
```
[📄 PDF] [⛽ Abastecer]  ← No header
```

### 4. Dashboard (`/dashboard`)
```
Histórico Recente
[📄 Gerar PDF]  ← Ao lado do título da tabela
```

---

## 🔧 Como Usar

### 1. Instalar dependências (se necessário)
```bash
pip install reportlab Pillow
```

### 2. Reiniciar o servidor
```bash
python app.py
```

### 3. Gerar PDFs
- **Via interface:** Clique nos botões "📄 Gerar PDF"
- **Via URL direta:** Acesse as rotas com filtros

### 4. Exemplos de URLs com filtros

```bash
# PDF de todos os motoristas
http://localhost:5000/pdf/motoristas

# PDF de todos os veículos
http://localhost:5000/pdf/veiculos

# PDF dos abastecimentos do veículo ABC1234
http://localhost:5000/pdf/abastecimentos?veiculo=ABC1234

# PDF das saídas em curso
http://localhost:5000/pdf/saidas?status=em_curso

# PDF das saídas de João Silva em outubro
http://localhost:5000/pdf/saidas?motorista=João Silva&data_inicio=2025-10-01&data_fim=2025-10-31
```

---

## 🚀 Próximas Melhorias (Opcionais)

1. **Logo da empresa nos PDFs**
   - Adicionar `Logo_frota_sanemar.png` no cabeçalho

2. **Totalizadores**
   - Somar totais no rodapé das tabelas
   - Ex: Total de litros, total de km rodados

3. **Gráficos nos PDFs**
   - Incluir gráficos de consumo, viagens, etc.

4. **Exportar para Excel**
   - Criar rotas `/excel/motoristas`, `/excel/veiculos`, etc.
   - Usar biblioteca `openpyxl`

5. **Agendamento de relatórios**
   - Enviar PDFs por e-mail automaticamente
   - Ex: Relatório mensal de abastecimentos

6. **Assinatura digital**
   - Adicionar assinatura eletrônica nos PDFs

---

## ✅ Status: PRONTO PARA USO! 🎉

Todos os PDFs estão funcionando e disponíveis nas páginas.
