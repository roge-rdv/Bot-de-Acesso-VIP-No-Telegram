# Bot de Acesso VIP no Telegram

Este bot gera links de convite temporários para grupos VIP do Telegram e remove automaticamente os usuários após o término do acesso.

## Funcionalidades

- Geração de links de convite únicos para grupos VIP.
- Remoção automática de usuários quando o acesso expira.
- Suporte a múltiplos idiomas (Português, Inglês, Espanhol).
- Mensagens periódicas de remarketing para engajar usuários.

## Configuração

### Pré-requisitos

- Python 3.11 ou superior
- Token do Bot do Telegram (obtido no [BotFather](https://t.me/BotFather))
- Banco de dados PostgreSQL ou SQLite
- Opcional: MongoDB (se preferir)

### Instalação

1. Clone o repositório:
   ```bash
   https://github.com/devRogi/Bot-de-Acesso-VIP-no-Telegram.git
   cd Bot-de-Acesso-VIP-no-Telegram
   ```

2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure as variáveis de ambiente:
   Crie um arquivo `.env` ou exporte as variáveis diretamente:
   ```bash
   BOT_TOKEN=seu_token_do_bot
   CHAT_ID=id_do_seu_grupo
   EXPIRATION_MINUTES=30
   REMARKING_INTERVAL_SECONDS=1200
   DATABASE_URL=sua_url_do_banco  # Para PostgreSQL
   DATABASE_PATH=database.db      # Para SQLite
   ```

4. Execute o bot:
   ```bash
   python bot.py
   ```

## Implantação

### Implantação no Heroku

1. Instale o [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli).
2. Faça login no Heroku:
   ```bash
   heroku login
   ```
3. Crie um novo aplicativo no Heroku:
   ```bash
   heroku create nome-do-seu-app
   ```
4. Adicione as variáveis de ambiente:
   ```bash
   heroku config:set BOT_TOKEN=seu_token_do_bot
   heroku config:set CHAT_ID=id_do_seu_grupo
   heroku config:set EXPIRATION_MINUTES=30
   heroku config:set REMARKING_INTERVAL_SECONDS=1200
   ```
5. Envie o código para o Heroku:
   ```bash
   git push heroku master
   ```
6. Escale o worker:
   ```bash
   heroku ps:scale worker=1
   ```

## Variáveis de Ambiente

- `BOT_TOKEN`: Token do bot do Telegram obtido no BotFather.
- `CHAT_ID`: ID do grupo/canal VIP.
- `EXPIRATION_MINUTES`: Duração (em minutos) para a validade do link de convite.
- `REMARKING_CHAT_IDS`: IDs dos grupos cadastrados para o remarking
- `REMARKING_INTERVAL_SECONDS`: Intervalo (em segundos) para envio de mensagens de remarketing.
- `DATABASE_URL`: URL do banco de dados PostgreSQL (opcional).
- `DATABASE_PATH`: Caminho para o arquivo do banco de dados SQLite (opcional).

## Comandos

- `/start` - Gera um link único de acesso VIP.
- `/status` - Verifica o status do seu acesso VIP.
- `/help` - Mostra a mensagem de ajuda.
- `/language` - Altera o idioma.

## Licença

Este projeto está licenciado sob a Licença MIT. Veja o arquivo LICENSE para mais detalhes.
