# Bot de Gestão de Frota para WhatsApp

Esta é uma aplicação backend em Python (Flask) que funciona como um webhook para um bot de WhatsApp, permitindo o registro de saídas e chegadas de veículos em um banco de dados Firebase Firestore.

## Funcionalidades

- Recebe mensagens do WhatsApp via webhook.
- Processa comandos de `Saida` e `Chegada`.
- Valida e registra motoristas e veículos.
- Cria e atualiza registros de viagem no Firestore.
- Envia respostas de confirmação.

## Pré-requisitos

- Python 3.7+
- Uma conta do Google Cloud com o Firestore ativado.
- Um arquivo de chave de serviço (JSON) do Firebase.
- Uma conta de WhatsApp Business API configurada para enviar webhooks.

## Como Configurar e Executar

1.  **Clone o repositório:**
    ```bash
    git clone <url-do-repositorio>
    cd <nome-do-repositorio>
    ```

2.  **Crie um ambiente virtual e instale as dependências:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # No Windows: venv\Scripts\activate
    pip install -r requirements.txt
    ```

3.  **Configure as Credenciais do Firebase:**
    - Baixe o arquivo JSON da sua chave de serviço do Firebase.
    - Abra o arquivo `.env`.
    - Altere a linha `GOOGLE_APPLICATION_CREDENTIALS` para o **caminho absoluto** do seu arquivo JSON.
    ```
    GOOGLE_APPLICATION_CREDENTIALS="C:/Users/SeuUsuario/caminho/para/o/arquivo.json"
    ```

4.  **Execute a aplicação:**
    ```bash
    flask run
    ```
    O servidor estará rodando em `http://127.0.0.1:5000`.

5.  **Exponha seu servidor local para a Internet:**
    - Use uma ferramenta como o `ngrok` para criar um túnel público para o seu servidor local.
    ```bash
    ngrok http 5000
    ```
    - O ngrok fornecerá uma URL pública (ex: `https://abcdef123456.ngrok.io`).

6.  **Configure o Webhook do WhatsApp:**
    - No painel do seu provedor de API do WhatsApp, configure o webhook de mensagens para apontar para a sua URL pública do ngrok, no endpoint `/webhook`.
    - Exemplo: `https://abcdef123456.ngrok.io/webhook`

Agora, qualquer mensagem enviada para o seu número do WhatsApp será processada pela sua aplicação.
