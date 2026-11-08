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
WEATHER_KEY = "4ee297316240a67c0cf64f0db5614abe"
EXCHANGE_KEY = "3a1a3d4043130373a818e7ff" # Твой ключ от ExchangeRate-API

user_histories = {}

# --- ПОГОДА ---
def get_weather(city):
    # Словарь для перевода популярных городов
    city_map = {
        "москва": "Moscow",
        "питер": "Saint Petersburg",
        "санкт-петербург": "Saint Petersburg",
        "якутск": "Yakutsk",
        "новосибирск": "Novosibirsk",
        "екатеринбург": "Yekaterinburg",
        "казань": "Kazan"
    }
    
    # Переводим, если есть в словаре, иначе оставляем как есть
    city_en = city_map.get(city.lower(), city)
    
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city_en}&appid={WEATHER_KEY}&units=metric&lang=ru"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return f"Погода в {city}: {data['main']['temp']}°C, {data['weather'][0]['description']}"
        return "Город не найден. Попробуй написать на английском (например, Moscow)."
    except:
        return "Ошибка погоды."

# --- ВАЛЮТА ---
def get_rate(base, target):
    url = f"https://v6.exchangerate-api.com/v6/{EXCHANGE_KEY}/pair/{base}/{target}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data['result'] == 'success':
                return f"Курс {base} к {target}: {data['conversion_rate']}"
        return "Ошибка получения курса."
    except:
        return "Ошибка соединения с банком."

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
        return None, "Ошибка."
    except:
        return None, "Ошибка соединения."

# --- GIGACHAT ---
def get_gigachat_token():
    url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    headers = {'Content-Type': 'application/x-www-form-urlencoded', 'Accept': 'application/json',
               'RqUID': str(uuid.uuid4()), 'Authorization': f'Basic {GIGACHAT_AUTH_KEY}'}
    try:
        response = requests.post(url, headers=headers, data={'scope': 'GIGACHAT_API_PERS'}, verify=False, timeout=15)
        if response.status_code == 200: return response.json().get('access_token')
        return None
    except: return None

def ask_gigachat(user_id, text):
    token = get_gigachat_token()
    if not token: return "Ошибка ИИ."
    if user_id not in user_histories: user_histories[user_id] = []
    user_histories[user_id].append({"role": "user", "content": text})
    if len(user_histories[user_id]) > 5: user_histories[user_id] = user_histories[user_id][-5:]
    url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'Authorization': f'Bearer {token}'}
    payload = {"model": "GigaChat", "messages": user_histories[user_id], "temperature": 0.7}
    try:
        response = requests.post(url, headers=headers, json=payload, verify=False, timeout=20)
        if response.status_code == 200:
            answer = response.json()['choices'][0]['message']['content']
            user_histories[user_id].append({"role": "assistant", "content": answer})
            return answer
        return "Ошибка API ИИ."
    except Exception as e: return f"Ошибка: {e}"

# --- ЛОГИКА ОБРАБОТКИ ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    text_lower = text.lower()
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    # 1. Погода
    if "погода" in text_lower:
        words = text.split()
        city = words[-1] if len(words) > 1 else "Москва"
        await update.message.reply_text(get_weather(city))
        return

    # 2. ВАЛЮТА (проверка на ключевые слова)
    if any(word in text_lower for word in ["курс", "доллар", "евро", "рубль", "валют"]):
        # Пытаемся понять, какие валюты нужны
        base, target = "USD", "RUB" # По умолчанию
        if "eur" in text_lower or "евро" in text_lower: base = "EUR"
        if "usd" in text_lower or "доллар" in text_lower: base = "USD"
        
        # Если просят "рубль к доллару", меняем местами
        if "рубл" in text_lower and ("к" in text_lower or "в" in text_lower):
            base, target = target, base
            
        await update.message.reply_text(get_rate(base, target))
        return

    # 3. Рисование
        # 3. Рисование
    if any(word in text_lower for word in ["нарисуй", "картинку", "фото", "сделай"]):
        # Очищаем запрос от команд
        prompt = text
        for word in ["нарисуй", "картинку", "фото", "сделай", "пожалуйста"]:
            prompt = prompt.replace(word, "")
        prompt = prompt.strip()
        
        if not prompt: 
            prompt = text
        
        # Добавляем стиль, чтобы рисовало нормально
        full_prompt = f"{prompt}, realistic, high quality, 4k"
        
        msg = await update.message.reply_text("🎨 Рисую...")
        file_path, cache_msg = generate_image(full_prompt)
        
        if file_path:
            with open(file_path, 'rb') as photo:
                await update.message.reply_photo(photo=photo, caption=f"Запрос: {prompt}{cache_msg}")
            await msg.delete()
        else:
            await msg.edit_text("Не смог нарисовать.")
        return

    # 4. ИИ
    answer = ask_gigachat(user_id, text)
    await update.message.reply_text(answer)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я умный бот. Я умею:\n"
        "— Болтать на любые темы\n"
        "— Узнавать погоду (напиши 'погода в Москве')\n"
        "— Узнавать курсы валют (напиши 'курс доллара')\n"
        "— Рисовать картинки (напиши 'нарисуй кота')\n"
        "— Забывать контекст (/clear)"
    )

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_histories[update.effective_user.id] = []
    await update.message.reply_text("История очищена.")

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("clear", clear))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Умный бот запущен...")
    application.run_polling()

if __name__ == '__main__':
    main()