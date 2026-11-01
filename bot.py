import logging
import datetime
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Твои ключи напрямую (без .env)
TOKEN = "9219000330:AAFDyxqZkS1RQ3Qr3ba7WBrgwze2Hy9KwRQ"
WEATHER_KEY = "4ee297316240a67c0cf64f0db5614abe"
EXCHANGE_KEY = "3a1a3d4043130373a818e7ff"

# --- КЭШИРОВАНИЕ (храним данные 5 минут) ---
cache = {}
CACHE_TIME = 300 # 5 минут в секундах

def get_from_cache(key):
    if key in cache:
        data, timestamp = cache[key]
        if datetime.datetime.now().timestamp() - timestamp < CACHE_TIME:
            return data
    return None

def save_to_cache(key, data):
    cache[key] = (data, datetime.datetime.now().timestamp())

# --- ФУНКЦИИ ПОГОДЫ И ВАЛЮТ ---
def get_weather(city):
    cached_weather = get_from_cache(f"weather_{city}")
    if cached_weather:
        return cached_weather, " (из кэша)"

    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_KEY}&units=metric&lang=ru"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        temp = data['main']['temp']
        desc = data['weather'][0]['description']
        result = f"Погода в {city}: {temp}°C, {desc}"
        save_to_cache(f"weather_{city}", result)
        return result, ""
    else:
        return "Не удалось найти город. Проверь название.", ""

def get_rate(base, target):
    cached_rate = get_from_cache(f"rate_{base}_{target}")
    if cached_rate:
        return cached_rate, " (из кэша)"

    url = f"https://v6.exchangerate-api.com/v6/{EXCHANGE_KEY}/pair/{base}/{target}"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        if data['result'] == 'success':
            rate = data['conversion_rate']
            result = f"Курс {base} к {target}: {rate}"
            save_to_cache(f"rate_{base}_{target}", result)
            return result, ""
        else:
            return "Ошибка API (проверь ключ)", ""
    else:
        return "Сервис курсов валют недоступен.", ""

# --- ОБРАБОТЧИКИ КОМАНД ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я умею узнавать погоду и курсы валют.\n\n"
        "Команды:\n"
        "/weather <город> - погода (пример: /weather Москва)\n"
        "/rate <валюта1> <валюта2> - курс (пример: /rate USD RUB)\n"
        "Всё кэшируется на 5 минут, чтобы не перегружать сервисы."
    )

async def weather_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Напиши город после команды. Пример: /weather Москва")
        return
    
    city = " ".join(context.args)
    result, cache_msg = get_weather(city)
    await update.message.reply_text(result + cache_msg)

async def rate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Напиши две валюты. Пример: /rate USD RUB")
        return
    
    base = context.args[0].upper()
    target = context.args[1].upper()
    result, cache_msg = get_rate(base, target)
    await update.message.reply_text(result + cache_msg)

# --- ИНЛАЙН-КНОПКИ ДЛЯ БЫСТРОГО ВЫБОРА ---
async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    inline_keyboard = [
        [InlineKeyboardButton("Погода в Москве", callback_data="weather_Moscow")],
        [InlineKeyboardButton("Курс USD/RUB", callback_data="rate_USD_RUB")],
        [InlineKeyboardButton("Курс EUR/RUB", callback_data="rate_EUR_RUB")]
    ]
    markup_inline = InlineKeyboardMarkup(inline_keyboard)
    await update.message.reply_text("Быстрый выбор:", reply_markup=markup_inline)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data.startswith("weather_"):
        city = data.split("_")[1]
        result, cache_msg = get_weather(city)
        await query.edit_message_text(text=result + cache_msg)
    elif data.startswith("rate_"):
        _, base, target = data.split("_")
        result, cache_msg = get_rate(base, target)
        await query.edit_message_text(text=result + cache_msg)

def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CommandHandler("weather", weather_command))
    application.add_handler(CommandHandler("rate", rate_command))
    application.add_handler(CallbackQueryHandler(button_callback))

    print("Бот с погодой и валютой запущен... Нажми Ctrl+C для остановки.")
    application.run_polling()

if __name__ == '__main__':
    main()