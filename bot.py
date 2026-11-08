import logging
import requests
import uuid
import os
import hashlib
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- КЛЮЧИ ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "9219000330:AAFDyxqZkS1RQ3Qr3ba7WBrgwze2Hy9KwRQ")
GIGACHAT_AUTH_KEY = os.getenv("GIGACHAT_AUTH_KEY", "MDFhMTk5ZmItYzJmNC03ODIzLWJjNzctYWRjNWFjMzBkYzM1OjY3ZmZlNGM4LWU5MDQtNGUzNy04YzZkLTEwODlhYTYxZDk2ZQ==")

# --- ПАМЯТЬ ДЛЯ КАЖДОГО ПОЛЬЗОВАТЕЛЯ ---
user_histories = {}

# --- ПОЛУЧЕНИЕ ТОКЕНА GIGACHAT ---
def get_gigachat_token():
    url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
        'RqUID': str(uuid.uuid4()),
        'Authorization': f'Basic {GIGACHAT_AUTH_KEY}'
    }
    payload = {'scope': 'GIGACHAT_API_PERS'}
    try:
        response = requests.post(url, headers=headers, data=payload, verify=False, timeout=15)
        if response.status_code == 200:
            return response.json().get('access_token')
        return None
    except:
        return None

# --- УМНЫЙ ЧАТ С ИИ ---
def ask_gigachat(user_id, text):
    token = get_gigachat_token()
    if not token:
        return "Ошибка токена."

    # Инициализируем историю для нового пользователя
    if user_id not in user_histories:
        user_histories[user_id] = []
    
    # Добавляем сообщение пользователя
    user_histories[user_id].append({"role": "user", "content": text})
    
    # Оставляем только последние 5 сообщений (как в Задании 7)
    if len(user_histories[user_id]) > 5:
        user_histories[user_id] = user_histories[user_id][-5:]

    url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'Bearer {token}'
    }
    payload = {
        "model": "GigaChat",
        "messages": user_histories[user_id],
        "temperature": 0.7
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, verify=False, timeout=20)
        if response.status_code == 200:
            answer = response.json()['choices'][0]['message']['content']
            # Сохраняем ответ бота в историю, чтобы он помнил контекст
            user_histories[user_id].append({"role": "assistant", "content": answer})
            return answer
        else:
            return "Ошибка API GigaChat."
    except Exception as e:
        return f"Ошибка: {e}"

# --- ГЕНЕРАЦИЯ КАРТИНОК ---
def generate_image(prompt):
    cache_dir = "image_cache"
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
        
    hash_name = hashlib.md5(prompt.encode()).hexdigest()
    file_path = os.path.join(cache_dir, f"{hash_name}.jpg")

    if os.path.exists(file_path):
        return file_path, " (из кэша)"

    url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}?width=512&height=512&nologo=true"
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            with open(file_path, 'wb') as f:
                f.write(response.content)
            return file_path, ""
        return None, "Ошибка генерации."
    except:
        return None, "Ошибка соединения."

# --- ОБРАБОТЧИКИ TELEGRAM ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Теперь я полноценный ИИ-бот. Пиши мне что угодно, и я отвечу как GigaChat.\n"
        "А если хочешь картинку — используй /imagine <описание>."
    )

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_histories:
        user_histories[user_id] = []
    await update.message.reply_text("🧹 История диалога очищена.")

async def imagine_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Напиши описание после команды. Пример: /imagine кот в космосе")
        return
    
    prompt = " ".join(context.args)
    msg = await update.message.reply_text("🎨 Генерирую изображение... Пожалуйста, подожди.")
    
    file_path, cache_msg = generate_image(prompt)
    
    if file_path:
        with open(file_path, 'rb') as photo:
            await update.message.reply_photo(photo=photo, caption=f"Ваш запрос: {prompt}{cache_msg}")
        await msg.delete()
    else:
        await msg.edit_text(f"Не удалось сгенерировать изображение. {cache_msg}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text
    
    # Показываем статус "печатает"
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    # Отправляем в GigaChat
    answer = ask_gigachat(user_id, user_text)
    
    await update.message.reply_text(answer)

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("clear", clear_command))
    application.add_handler(CommandHandler("imagine", imagine_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Умный ИИ-бот запущен...")
    application.run_polling()

if __name__ == '__main__':
    main()