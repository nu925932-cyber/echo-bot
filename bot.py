import logging
import sqlite3
import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Твой токен
TOKEN = "9219000330:AAFDyxqZkS1RQ3Qr3ba7WBrgwze2Hy9KwRQ"

# Твой Telegram ID (нужен для команды /users)
# Чтобы его узнать, напиши боту @userinfobot в телеграме. Он пришлет твой ID (число).
ADMIN_ID = 8019735392 # <--- ЗАМЕНИ НА СВОЙ ID!

# --- ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            registered_at TEXT
        )
    ''')
    # Таблица истории команд
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            command TEXT,
            timestamp TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    conn.commit()
    conn.close()

# Функция для добавления пользователя (если его нет)
def add_user(user):
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        cursor.execute('''
            INSERT INTO users (id, username, first_name, registered_at) 
            VALUES (?, ?, ?, ?)
        ''', (user.id, user.username, user.first_name, now))
        conn.commit()
    except sqlite3.IntegrityError:
        # Если пользователь уже есть, просто игнорируем ошибку
        pass
    finally:
        conn.close()

# Функция для записи команды в историю
def log_command(user_id, command):
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
        INSERT INTO history (user_id, command, timestamp) 
        VALUES (?, ?, ?)
    ''', (user_id, command, now))
    conn.commit()
    conn.close()

# --- ОБРАБОТЧИКИ КОМАНД ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    add_user(update.effective_user) # Добавляем в БД
    log_command(update.effective_user.id, "/start") # Пишем в историю
    
    await update.message.reply_text(
        "Привет! Я теперь умею запоминать пользователей.\n\n"
        "Команды:\n"
        "/stats - Общая статистика бота\n"
        "/profile - Твоя личная статистика\n"
        "/users - Список всех пользователей (только для админа)"
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    add_user(update.effective_user)
    log_command(update.effective_user.id, "/stats")
    
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    
    # Считаем количество пользователей
    cursor.execute("SELECT COUNT(*) FROM users")
    users_count = cursor.fetchone()[0]
    
    # Считаем количество выполненных команд
    cursor.execute("SELECT COUNT(*) FROM history")
    commands_count = cursor.fetchone()[0]
    
    conn.close()
    
    await update.message.reply_text(
        f"📊 Статистика бота:\n"
        f"👥 Всего пользователей: {users_count}\n"
        f"⚙️ Выполнено команд: {commands_count}"
    )

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user)
    log_command(user.id, "/profile")
    
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    
    # Получаем дату регистрации
    cursor.execute("SELECT registered_at FROM users WHERE id = ?", (user.id,))
    reg_date = cursor.fetchone()[0]
    
    # Считаем сколько команд выполнил именно этот пользователь
    cursor.execute("SELECT COUNT(*) FROM history WHERE user_id = ?", (user.id,))
    my_commands = cursor.fetchone()[0]
    
    conn.close()
    
    await update.message.reply_text(
        f"👤 Твой профиль:\n"
        f"Имя: {user.first_name}\n"
        f"Username: @{user.username if user.username else 'нет'}\n"
        f"Дата регистрации: {reg_date}\n"
        f"Выполнено команд: {my_commands}"
    )

async def users_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    log_command(user.id, "/users")
    
    # Проверка на админа
    if user.id != ADMIN_ID:
        await update.message.reply_text("⛔ У тебя нет прав для этой команды.")
        return
    
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, first_name, username FROM users")
    all_users = cursor.fetchall()
    conn.close()
    
    if not all_users:
        await update.message.reply_text("Пользователей пока нет.")
        return
    
    text = "👥 Список всех пользователей:\n"
    for u in all_users:
        text += f"ID: {u[0]}, Имя: {u[1]}, Ник: @{u[2] if u[2] else 'нет'}\n"
    
    await update.message.reply_text(text)

# Обработчик обычных сообщений (чтобы бот не молчал, если напишешь что-то без команды)
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    add_user(update.effective_user)
    log_command(update.effective_user.id, update.message.text)
    await update.message.reply_text("Я тебя услышал! Напиши /stats или /profile, чтобы проверить базу.")

def main():
    init_db() # Создаем базу при запуске
    
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("profile", profile))
    application.add_handler(CommandHandler("users", users_list))
    
    # Ловим любой текст, чтобы записывать его в историю (для эха)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    print("Бот с базой данных запущен... Нажми Ctrl+C для остановки.")
    application.run_polling()

if __name__ == '__main__':
    main()