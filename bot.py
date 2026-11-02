import logging
import requests
import uuid
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- ТВОИ КЛЮЧИ ---
TELEGRAM_TOKEN = "9219000330:AAFDyxqZkS1RQ3Qr3ba7WBrgwze2Hy9KwRQ"
GIGACHAT_CLIENT_ID = "01a199fb-c2f4-7823-bc77-adc5ac30dc35"
GIGACHAT_AUTH_KEY = "MDFhMTk5ZmItYzJmNC03ODIzLWJjNzctYWRjNWFjMzBkYzM1OjY3ZmZlNGM4LWU5MDQtNGUzNy04YzZkLTEwODlhYTYxZDk2ZQ==" # Твой длинный ключ MDF...

DOCS_FILE = "docs.txt"

def find_relevant_context(query):
    if not os.path.exists(DOCS_FILE):
        return "Файл с документацией не найден."

    with open(DOCS_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Разбиваем вопрос на слова и берем только те, что длиннее 3 букв
    query_words = [word.strip("?,.!").lower() for word in query.split() if len(word) > 3]
    
    relevant_lines = []
    for line in lines:
        line_lower = line.lower()
        # Ищем вхождения слов (простой поиск по подстроке)
        if any(word in line_lower for word in query_words):
            relevant_lines.append(line.strip())

    if not relevant_lines:
        return None

    return "\n".join(relevant_lines[:3])

def get_gigachat_token():
    url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
        'RqUID': str(uuid.uuid4()),
        'Authorization': f'Basic {GIGACHAT_AUTH_KEY}'
    }
    payload = {'scope': 'GIGACHAT_API_PERS'}
    response = requests.post(url, headers=headers, data=payload, verify=False)
    if response.status_code == 200:
        return response.json().get('access_token')
    return None

def ask_gigachat_with_rag(question):
    context = find_relevant_context(question)
    
    if not context:
        return "Я не нашел информации об этом в файле docs.txt."

    prompt = (
        f"Ответь на вопрос, используя ТОЛЬКО этот текст:\n{context}\n\n"
        f"Вопрос: {question}"
    )

    token = get_gigachat_token()
    if not token:
        return "Ошибка токена."

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

    response = requests.post(url, headers=headers, json=payload, verify=False)
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    else:
        return "Ошибка при запросе к ИИ."

# --- TELEGRAM ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я RAG-бот. Я отвечаю на вопросы, опираясь на файл docs.txt.\n"
        "Спроси меня что-нибудь про Python или GigaChat."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    answer = ask_gigachat_with_rag(update.message.text)
    
    answer += "\n\n📄 *Источник: docs.txt*"
    
    await update.message.reply_text(answer, parse_mode='Markdown')

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("RAG-бот запущен...")
    application.run_polling()

if __name__ == '__main__':
    main()