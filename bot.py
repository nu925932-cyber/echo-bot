import logging
import requests
import uuid
import os
import hashlib
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "9219000330:AAFDyxqZkS1RQ3Qr3ba7WBrgwze2Hy9KwRQ")
GIGACHAT_AUTH_KEY = os.getenv("GIGACHAT_AUTH_KEY", "MDFhMTk5ZmItYzJmNC03ODIzLWJjNzctYWRjNWFjMzBkYzM1OjY3ZmZlNGM4LWU5MDQtNGUzNy04YzZkLTEwODlhYTYxZDk2ZQ==")

CACHE_DIR = "image_cache"
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

# --- GIGACHAT ---
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
        else:
            print(f"Ошибка токена: {response.text}")
            return None
    except Exception as e:
        print(f"Ошибка соединения: {e}")
        return None

def analyze_sentiment(text):
    token = get_gigachat_token()
    if not token:
        return "Ошибка получения токена GigaChat."

    prompt = f"Определи тональность текста: '{text}'. Ответь ровно одним словом: 'позитивная', 'негативная' или 'нейтральная'."

    url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'Bearer {token}'
    }
    payload = {
        "model": "GigaChat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1
    }
    try:
        response = requests.post(url, headers=headers, json=payload, verify=False, timeout=20)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content'].strip()
        else:
            return f"Ошибка API GigaChat: {response.status_code}"
    except Exception as e:
        return f"Ошибка при запросе к ИИ: {e}"

def generate_image(prompt):
    hash_name = hashlib.md5(prompt.encode()).hexdigest()
    file_path = os.path.join(CACHE_DIR, f"{hash_name}.jpg")

    if os.path.exists(file_path):
        return file_path, " (из кэша)"

    url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}?width=512&height=512&nologo=true"
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            with open(file_path, 'wb') as f:
                f.write(response.content)
            return file_path, ""
        else:
            return None, "Ошибка генерации (сервис недоступен)."
    except Exception as e:
        return None, f"Ошибка: {e}"

# --- TELEGRAM ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я умею две вещи:\n"
        "1. Анализировать тональность (просто напиши любой текст).\n"
        "2. Генерировать картинки (используй /imagine <описание>).\n\n"
        "Пример: /imagine кот в космосе"
    )

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
    user_text = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    sentiment = analyze_sentiment(user_text)
    
    await update.message.reply_text(f"Анализ тональности: {sentiment}")

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("imagine", imagine_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Бот запущен...")
    application.run_polling()

if __name__ == '__main__':
    main()