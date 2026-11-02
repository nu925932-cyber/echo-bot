import logging
import requests
import uuid
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- ТВОИ КЛЮЧИ ---
TELEGRAM_TOKEN = "9219000330:AAFDyxqZkS1RQ3Qr3ba7WBrgwze2Hy9KwRQ"
GIGACHAT_CLIENT_ID = "01a199fb-c2f4-7823-bc77-adc5ac30dc35" # Твой Client ID
GIGACHAT_AUTH_KEY = "MDFhMTk5ZmItYzJmNC03ODIzLWJjNzctYWRjNWFjMzBkYzM1OjY3ZmZlNGM4LWU5MDQtNGUzNy04YzZkLTEwODlhYTYxZDk2ZQ==" # Твой длинный ключ

# --- ХРАНИЛИЩЕ ИСТОРИИ (для контекста) ---
# В задании просят хранить последние 5 сообщений. Мы храним в памяти.
user_histories = {}

def get_gigachat_token():
    """Получаем временный Access Token для GigaChat"""
    url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
        'RqUID': str(uuid.uuid4()),
        'Authorization': f'Basic {GIGACHAT_AUTH_KEY}' # Используем Authorization Key
    }
    payload = {'scope': 'GIGACHAT_API_PERS'}
    
    # Отключаем проверку SSL для тестов (у Сбера бывают проблемы с сертификатами)
    response = requests.post(url, headers=headers, data=payload, verify=False)
    
    if response.status_code == 200:
        return response.json().get('access_token')
    else:
        print(f"Ошибка получения токена: {response.text}")
        return None

def ask_gigachat(user_id, message):
    """Отправляем сообщение в GigaChat и получаем ответ"""
    token = get_gigachat_token()
    if not token:
        return "Не удалось получить токен доступа. Проверь ключи."

    url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'Bearer {token}'
    }
    
    # Формируем историю сообщений (контекст)
    if user_id not in user_histories:
        user_histories[user_id] = []
    
    # Добавляем новое сообщение пользователя
    user_histories[user_id].append({"role": "user", "content": message})
    
    # Оставляем только последние 5 сообщений (как в задании)
    if len(user_histories[user_id]) > 5:
        user_histories[user_id] = user_histories[user_id][-5:]

    payload = {
        "model": "GigaChat",
        "messages": user_histories[user_id],
        "temperature": 0.7,
        "max_tokens": 500
    }

    response = requests.post(url, headers=headers, json=payload, verify=False)
    
    if response.status_code == 200:
        answer = response.json()['choices'][0]['message']['content']
        # Добавляем ответ бота в историю
        user_histories[user_id].append({"role": "assistant", "content": answer})
        return answer
    else:
        return f"Ошибка API: {response.status_code}"

# --- ОБРАБОТЧИКИ TELEGRAM ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я умный бот на базе GigaChat.\n"
        "Просто напиши мне что-нибудь, и я отвечу.\n"
        "Команда /clear очистит историю нашего диалога."
    )

async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_histories:
        user_histories[user_id] = []
    await update.message.reply_text("🧹 История диалога очищена. Давай начнем с чистого листа!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text
    
    # Показываем статус "печатает", пока ждем ответ от ИИ
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    # Получаем ответ от нейросети
    answer = ask_gigachat(user_id, user_text)
    
    # Отправляем пользователю
    await update.message.reply_text(answer)

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("clear", clear_history))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Умный бот с GigaChat запущен... Нажми Ctrl+C для остановки.")
    application.run_polling()

if __name__ == '__main__':
    main()