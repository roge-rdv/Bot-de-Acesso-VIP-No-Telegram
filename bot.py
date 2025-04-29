import logging
from telegram import Update, ChatInviteLink, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, ConversationHandler
import sqlite3
import psycopg2
from psycopg2 import sql
from datetime import datetime, timedelta
from time import mktime
import asyncio
import os
import urllib.parse
import random

# Configuração de logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Estados para a conversa
SELECTING_LANGUAGE = 1

# Dicionário de mensagens em diferentes idiomas
translations = {
    'pt': {
        'select_language': 'Por favor, selecione o idioma desejado:',
        'language_set': 'Idioma definido para Português! Use /start para gerar seu link VIP.',
        'link_message': 'Seu link de acesso VIP: {}\nEste link expira em {} minutos.',
        'help_message': '''
Comandos disponíveis:
/start - Gera um link único de acesso VIP
/status - Verifica o status do seu acesso VIP
/help - Mostra esta mensagem de ajuda
/language - Altera o idioma
''',
        'status_active': 'Seu acesso VIP está ativo!\nLink: {}\nTempo restante: {} minutos.',
        'status_expired': 'Seu acesso VIP expirou. Use /start para gerar um novo link.',
        'status_none': 'Você não possui um acesso VIP ativo. Use /start para gerar um link.',
        'expired_message': 'Seu acesso ao grupo VIP expirou! Adquira acesso completo através do @vendasgrupvip_bot ou @f4mosinhasvip_bot'
    },
    'en': {
        'select_language': 'Please select your preferred language:',
        'language_set': 'Language set to English! Use /start to generate your VIP link.',
        'link_message': 'Your VIP access link: {}\nThis link expires in {} minutes.',
        'help_message': '''
Available commands:
/start - Generate a unique VIP access link
/status - Check your VIP access status
/help - Show this help message
/language - Change language
''',
        'status_active': 'Your VIP access is active!\nLink: {}\nTime remaining: {} minutes.',
        'status_expired': 'Your VIP access has expired. Use /start to generate a new link.',
        'status_none': 'You don\'t have an active VIP access. Use /start to generate a link.',
        'expired_message': 'Your access to the VIP group has expired! Get full access through @vipgroupdol_bot or @f4mosinhasvip_bot'
    }
}

# Configuração de banco de dados
def get_db_connection():
    """Estabelece e retorna uma conexão com o banco de dados apropriado (PostgreSQL ou SQLite)"""
    # Verificar se existe DATABASE_URL (Heroku PostgreSQL)
    database_url = os.environ.get("DATABASE_URL")
    
    if database_url:
        logging.info("Conectando ao PostgreSQL...")
        # Ajustar o URL se começar com postgres:// (formato mais antigo do Heroku)
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        
        # Conectar ao PostgreSQL
        conn = psycopg2.connect(database_url, sslmode='require')
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Criar tabela se não existir
        cursor.execute('''CREATE TABLE IF NOT EXISTS invite_links (
            user_id BIGINT PRIMARY KEY,
            invite_link TEXT,
            created_at TIMESTAMP,
            expires_at TIMESTAMP,
            language TEXT DEFAULT 'pt'
        )''')
        
        return conn
    else:
        # Fallback para SQLite (desenvolvimento local)
        logging.info("Conectando ao SQLite...")
        DB_PATH = os.environ.get("DATABASE_PATH", "database.db")
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS invite_links (
            user_id INTEGER PRIMARY KEY,
            invite_link TEXT,
            created_at TIMESTAMP,
            expires_at TIMESTAMP,
            language TEXT DEFAULT 'pt'
        )''')
        conn.commit()
        
        return conn

# Estabelecer conexão com o banco de dados
conn = get_db_connection()
cursor = conn.cursor()

# Função para obter o idioma do usuário
def get_user_language(user_id):
    placeholder = "%s" if isinstance(conn, psycopg2.extensions.connection) else "?"
    cursor.execute(f'SELECT language FROM invite_links WHERE user_id = {placeholder}', (user_id,))
    result = cursor.fetchone()
    if result:
        return result[0]
    return 'pt'  # Idioma padrão: português

# Função para definir o idioma do usuário
def set_user_language(user_id, language):
    placeholder = "%s" if isinstance(conn, psycopg2.extensions.connection) else "?"
    # Verificar se o usuário existe
    cursor.execute(f'SELECT 1 FROM invite_links WHERE user_id = {placeholder}', (user_id,))
    if cursor.fetchone():
        cursor.execute(f'UPDATE invite_links SET language = {placeholder} WHERE user_id = {placeholder}', (language, user_id))
    else:
        cursor.execute(f'INSERT INTO invite_links (user_id, language) VALUES ({placeholder}, {placeholder})', (user_id, language))
    
    if isinstance(conn, sqlite3.Connection):
        conn.commit()

# Comando inicial que pergunta o idioma
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Verifica se o usuário já tem um idioma definido
    language = get_user_language(user_id)
    
    if 'generating_link' in context.user_data and context.user_data['generating_link']:
        # Usuário já escolheu o idioma, gerar link
        await generate_link(update, context)
        return ConversationHandler.END
    
    # Pergunta sobre o idioma
    keyboard = [
        [
            InlineKeyboardButton("Português 🇧🇷", callback_data='language_pt'),
            InlineKeyboardButton("English 🇺🇸", callback_data='language_en')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Por favor, selecione o idioma desejado: / Please select your preferred language:",
        reply_markup=reply_markup
    )
    
    return SELECTING_LANGUAGE

# Callback para a seleção de idioma
async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Extrair o idioma da callback_data
    language = query.data.split('_')[1]
    user_id = query.from_user.id
    
    # Salvar a preferência de idioma
    set_user_language(user_id, language)
    
    # Informar ao usuário
    await query.edit_message_text(translations[language]['language_set'])
    
    # Configurar para gerar link na próxima chamada de /start
    context.user_data['generating_link'] = True
    
    return ConversationHandler.END

# Comando para alterar o idioma
async def change_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("Português 🇧🇷", callback_data='language_pt'),
            InlineKeyboardButton("English 🇺🇸", callback_data='language_en')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Por favor, selecione o idioma desejado: / Please select your preferred language:",
        reply_markup=reply_markup
    )
    
    return SELECTING_LANGUAGE

# Função para gerar link único
async def generate_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = os.environ.get("CHAT_ID", "ID_Chat_VIP")
    expiration_minutes = int(os.environ.get("EXPIRATION_MINUTES", "35"))
    language = get_user_language(user_id)
    
    # Verifica se o usuário já teve um link expirado
    placeholder = "%s" if isinstance(conn, psycopg2.extensions.connection) else "?"
    cursor.execute(f'SELECT expires_at FROM invite_links WHERE user_id = {placeholder}', (user_id,))
    result = cursor.fetchone()
    if result and result[0]:  # Se existe um registro de expires_at
        expires_at = datetime.fromisoformat(result[0]) if isinstance(result[0], str) else result[0]
        if datetime.now() > expires_at:  # Link expirado
            await update.message.reply_text(
                "Seu teste gratuito já expirou. Agora, adquira o acesso VIP completo através do @vendasgrupvip_bot ou @f4mosinhasvip_bot."
                if language == 'pt' else
                "Your free trial has expired. Now, purchase full VIP access through @vipgroupdol_bot or @f4mosinhasvip_bot."
            )
            return

    try:
        # Gera o link de convite
        expiration_time = datetime.now() + timedelta(minutes=expiration_minutes)
        expiration_timestamp = int(mktime(expiration_time.timetuple()))
        
        logging.info(f"Tentando criar link de convite para o chat {chat_id}")
        invite_link = await context.bot.create_chat_invite_link(
            chat_id=chat_id,
            expire_date=expiration_timestamp
        )

        # Armazena no banco de dados
        cursor.execute(
            f'INSERT INTO invite_links (user_id, invite_link, created_at, expires_at, language) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}) '
            f'ON CONFLICT (user_id) DO UPDATE SET invite_link = {placeholder}, created_at = {placeholder}, expires_at = {placeholder}, language = {placeholder}',
            (
                user_id, invite_link.invite_link, datetime.now().isoformat(), expiration_time.isoformat(), language,
                invite_link.invite_link, datetime.now().isoformat(), expiration_time.isoformat(), language
            )
        )
        if isinstance(conn, sqlite3.Connection):
            conn.commit()

        # Envia o link para o usuário
        await update.message.reply_text(
            translations[language]['link_message'].format(invite_link.invite_link, expiration_minutes)
        )
    except Exception as e:
        logging.error(f"Erro ao gerar link de convite: {e}")
        
        error_messages = {
            'pt': (
                "Não foi possível gerar o link de convite. Certifique-se de que:\n"
                "1. O bot é administrador do grupo/canal\n"
                "2. O ID do chat configurado está correto\n"
                "3. O chat não é um chat privado (deve ser grupo, supergrupo ou canal)\n\n"
                "Entre em contato com o administrador do bot."
            ),
            'en': (
                "Could not generate the invite link. Please ensure that:\n"
                "1. The bot is an administrator of the group/channel\n"
                "2. The configured chat ID is correct\n"
                "3. The chat is not a private chat (must be group, supergroup, or channel)\n\n"
                "Contact the bot administrator for assistance."
            )
        }
        
        await update.message.reply_text(error_messages.get(language, error_messages['en']))

# Função para verificar e banir usuários
async def check_and_ban(context: ContextTypes.DEFAULT_TYPE):
    chat_id = os.environ.get("CHAT_ID", "ID_Chat_VIP")
    now = datetime.now()
    logging.info("Iniciando verificação de links expirados...")

    # Busca links expirados
    placeholder = "%s" if isinstance(conn, psycopg2.extensions.connection) else "?"
    cursor.execute(f'SELECT user_id, invite_link, language FROM invite_links WHERE expires_at <= {placeholder} AND invite_link IS NOT NULL', (now.isoformat(),))
    expired_links = cursor.fetchall()

    for user_id, invite_link, language in expired_links:
        try:
            # Banir o usuário
            logging.info(f"Banindo usuário {user_id} e removendo link {invite_link}.")
            await context.bot.ban_chat_member(chat_id=chat_id, user_id=user_id)

            # Enviar mensagem de follow-up no idioma preferido
            await context.bot.send_message(
                chat_id=user_id, 
                text=translations[language]['expired_message']
            )

            # Remover o link do banco de dados (mas manter o idioma)
            cursor.execute(
                f'UPDATE invite_links SET invite_link = NULL, created_at = NULL, expires_at = NULL WHERE user_id = {placeholder}', 
                (user_id,)
            )
            if isinstance(conn, sqlite3.Connection):
                conn.commit()
            logging.info(f"Usuário {user_id} banido e link removido com sucesso.")
        except Exception as e:
            logging.error(f"Erro ao banir usuário {user_id}: {e}")

# Função de ajuda
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    await update.message.reply_text(translations[language]['help_message'])

# Função para verificar o status do acesso
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    # Consulta o banco de dados
    placeholder = "%s" if isinstance(conn, psycopg2.extensions.connection) else "?"
    cursor.execute(f'SELECT invite_link, expires_at FROM invite_links WHERE user_id = {placeholder}', (user_id,))
    result = cursor.fetchone()
    
    if result and result[0] and result[1]:  # Verifica se invite_link e expires_at existem
        invite_link, expires_at = result
        
        # Converter expires_at para string se não for já uma string
        if not isinstance(expires_at, str):
            expires_at = str(expires_at)
            
        expires_at_datetime = datetime.fromisoformat(expires_at)
        time_remaining = expires_at_datetime - datetime.now()
        
        if time_remaining.total_seconds() > 0:
            minutes_remaining = int(time_remaining.total_seconds() / 60)
            await update.message.reply_text(
                translations[language]['status_active'].format(invite_link, minutes_remaining)
            )
        else:
            await update.message.reply_text(translations[language]['status_expired'])
    else:
        await update.message.reply_text(translations[language]['status_none'])

# Mensagens de remarking em diferentes idiomas
remarking_messages = {
    'pt': [
        "🎉 Experimente o nosso grupo VIP gratuitamente! Clique no botão abaixo para acessar o bot de teste.",
        "🚀 Não perca! Teste nosso grupo VIP agora mesmo, é grátis! Clique no botão abaixo.",
        "💎 Descubra o que o grupo VIP tem a oferecer! Teste grátis clicando no botão abaixo."
    ],
    'en': [
        "🎉 Try our VIP group for free! Click the button below to access the test bot.",
        "🚀 Don't miss out! Test our VIP group now for free! Click the button below.",
        "💎 Discover what the VIP group has to offer! Free trial by clicking the button below."
    ],
    'es': [
        "🎉 ¡Prueba nuestro grupo VIP gratis! Haz clic en el botón de abajo para acceder al bot de prueba.",
        "🚀 ¡No te lo pierdas! Prueba nuestro grupo VIP ahora mismo, ¡es gratis! Haz clic en el botón de abajo.",
        "💎 ¡Descubre lo que el grupo VIP tiene para ofrecer! Prueba gratis haciendo clic en el botón de abajo."
    ]
}

# Função de remarking
async def remarking(context: ContextTypes.DEFAULT_TYPE):
    chat_ids = os.environ.get("REMARKING_CHAT_IDS", "id1", "id2").split(",")  # IDs dos grupos cadastrados
    test_bot_username = os.environ.get("TEST_BOT_USERNAME", "Teste1")  # Nome do botão que o bot vai mandar no remarking

    for chat_id in chat_ids:
        try:
            # Seleciona um idioma e uma mensagem aleatória
            language = random.choice(list(remarking_messages.keys()))
            message = random.choice(remarking_messages[language])

            # Cria o botão para acessar o bot de teste
            keyboard = [[InlineKeyboardButton("🤖 Bot de Teste / Test Bot", url=f"https://t.me/{test_bot_username}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Envia a mensagem para o grupo
            await context.bot.send_message(chat_id=chat_id, text=message, reply_markup=reply_markup)
            logging.info(f"Mensagem de remarking enviada para o grupo {chat_id} em {language}.")
        except Exception as e:
            logging.error(f"Erro ao enviar mensagem de remarking para o grupo {chat_id}: {e}")

# Configuração do bot
if __name__ == '__main__':
    # Obtém o token do bot da variável de ambiente ou usa o valor padrão
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "your_bot_token_here")  # Substituir por um placeholder
    
    # Constrói a aplicação
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Define o conversation handler para seleção de idioma
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start), CommandHandler("language", change_language)],
        states={
            SELECTING_LANGUAGE: [CallbackQueryHandler(language_callback, pattern='^language_')],
        },
        fallbacks=[CommandHandler("start", start)],
    )
    
    # Adiciona handlers
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    
    # Configura o job_queue
    job_queue = application.job_queue
    job_queue.run_repeating(check_and_ban, interval=60)
    remarking_interval = int(os.environ.get("REMARKING_INTERVAL_SECONDS", "1200"))  # Intervalo padrão: 10 minutos
    job_queue.run_repeating(remarking, interval=remarking_interval)  # Executa no intervalo configurado
    
    # Inicia o bot
    application.run_polling()
