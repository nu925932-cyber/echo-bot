import logging
import requests
import uuid
import json
import datetime
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- ТВОИ КЛЮЧИ ---
TELEGRAM_TOKEN = "9219000330:AAFDyxqZkS1RQ3Qr3ba7WBrgwze2Hy9KwRQ"
GIGACHAT_AUTH_KEY = "MDFhMTk5ZmItYzJmNC03ODIzLWJjNzctYWRjNWFjMzBkYzM1OjY3ZmZlNGM4LWU5MDQtNGUzNy04YzZkLTEwODlhYTYxZDk2ZQ==" # Твой длинный ключ MDF...

# --- ИНСТРУМЕНТЫ (ФУНКЦИИ) ---
def get_weather(city):
    # Имитация погоды (как в задании)
    weather_data = {
        "москва": "Солнечно, +25°C",
        "санкт-петербург": "Дождливо, +15°C",
        "новосибирск": "Облачно, +10°C"
    }
    return weather_data.get(city.lower(), "Нет данных о погоде для этого города.")

def get_current_time(timezone="UTC"):
    # Получаем текущее время
    now = datetime.datetime.now().strftime("%H:%M:%S")
    return f"Текущее время ({timezone}): {now}"

def calculate(expression):
    try:
        # Очень простой калькулятор (безопасный)
        allowed_chars = "0123456789+-*/(). "
        if not all(c in allowed_chars for c in expression):
            return "Ошибка: недопустимые символы в выражении."
        result = eval(expression)
        return f"Результат: {result}"
    except Exception as e:
        return f"Ошибка вычисления: {e}"

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
    response = requests.post(url, headers=headers, data=payload, verify=False)
    if response.status_code == 200:
        return response.json().get('access_token')
    return None

def ask_gigachat_with_tools(question):
    token = get_gigachat_token()
    if not token:
        return "Ошибка токена."

    # Системный промпт, который учит ИИ пользоваться инструментами
    system_prompt = (
        "Ты — умный ассистент с доступом к инструментам. "
        "Если пользователь просит погоду, время или вычисления, ты ДОЛЖЕН ответить ТОЛЬКО JSON-объектом, без лишнего текста.\n"
        "Доступные инструменты:\n"
        "1. get_weather(city) - узнать погоду.\n"
        "2. get_current_time(timezone) - узнать время.\n"
        "3. calculate(expression) - вычислить математическое выражение.\n\n"
        "Пример ответа: {\"tool\": \"get_weather\", \"args\": {\"city\": \"Москва\"}}\n"
        "Если инструмент не нужен, просто ответь текстом."
    )

    url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'Bearer {token}'
    }
    
    payload = {
        "model": "GigaChat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ],
        "temperature": 0.1
    }

    response = requests.post(url, headers=headers, json=payload, verify=False)
    if response.status_code == 200:
        answer = response.json()['choices'][0]['message']['content']
        
        # Пытаемся распарсить JSON (если ИИ решил вызвать инструмент)
        try:
            # Ищем JSON в ответе (иногда ИИ добавляет лишние символы)
            start = answer.find('{')
            end = answer.rfind('}') + 1
            if start != -1 and end != 0:
                json_str = answer[start:end]
                data = json.loads(json_str)
                
                tool_name = data.get("tool")
                args = data.get("args", {})
                
                # ВЫПОЛНЯЕМ ИНСТРУМЕНТ
                if tool_name == "get_weather":
                    result = get_weather(args.get("city", ""))
                elif tool_name == "get_current_time":
                    result = get_current_time(args.get("timezone", "UTC"))
                elif tool_name == "calculate":
                    result = calculate(args.get("expression", ""))
                else:
                    result = "Неизвестный инструмент."
                
                # Возвращаем результат пользователю
                return f"🛠 Использован инструмент: {tool_name}\nРезультат: {result}"
            else:
                # Если JSON не найден, просто возвращаем ответ ИИ
                return answer
        except json.JSONDecodeError:
            return answer
    else:
        return "Ошибка при запросе к ИИ."

# --- TELEGRAM ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я агентный бот. Я умею:\n"
        "🌤 Узнавать погоду (например: 'Какая погода в Москве?')\n"
        "⏰ Говорить время (например: 'Сколько сейчас времени?')\n"
        "🧮 Считать (например: 'Сколько будет 2+2*2?')\n"
        "Просто напиши мне запрос!"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    answer = ask_gigachat_with_tools(update.message.text)
    await update.message.reply_text(answer)

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Агентный бот запущен...")
    application.run_polling()

if __name__ == '__main__':
    main()