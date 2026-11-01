import logging
import datetime
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = "9219000330:AAFDyxqZkS1RQ3Qr3ba7WBrgwze2Hy9KwRQ"


reply_keyboard = [
    ['Привет', 'Время'],
    ['Помощь']
]

markup_reply = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=False)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я бот из Задания 2. Теперь я умею работать с кнопками. Выбери действие на клавиатуре внизу 👇",
        reply_markup=markup_reply # Прикрепляем кнопки к сообщению
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Доступные действия:\n"
        "— Кнопки внизу экрана\n"
        "— /menu — показать кнопки под сообщением\n"
        "— /help — это сообщение"
    )

async def handle_reply_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == 'Привет':
        await update.message.reply_text("И тебе привет! 👋")
    elif text == 'Время':
        now = datetime.datetime.now().strftime("%H:%M:%S")
        await update.message.reply_text(f"Сейчас {now}")
    elif text == 'Помощь':
        await help_command(update, context) # Вызываем функцию помощи

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    inline_keyboard = [
        [InlineKeyboardButton("Перейти на сайт", url="https://ya.ru")],
        [InlineKeyboardButton("Поделиться", callback_data="share_action")]
    ]
    markup_inline = InlineKeyboardMarkup(inline_keyboard)
    
    await update.message.reply_text(
        "Это инлайн-меню (кнопки прикреплены прямо к сообщению):", 
        reply_markup=markup_inline
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() # Убирает "часики" с кнопки
    
    if query.data == "share_action":
        # Меняем текст сообщения после нажатия
        await query.edit_message_text(text="Вы нажали 'Поделиться'! 😄")


def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("menu", menu_command))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reply_buttons))
    
    application.add_handler(CallbackQueryHandler(button_callback))

    print("Бот с кнопками запущен... Нажми Ctrl+C для остановки.")
    application.run_polling()

if __name__ == '__main__':
    main()