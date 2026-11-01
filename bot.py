import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = "9219000330:AAFDyxqZkS1RQ3Qr3ba7WBrgwze2Hy9KwRQ"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я эхо-бот. Напиши мне что-нибудь, и я повторю.\n"
        "Используй /help, чтобы увидеть команды."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Доступные команды:\n"
        "/start - Начать сначала\n"
        "/help - Показать это сообщение\n"
        "Или просто напиши текст, и я его повторю."
    )

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(update.message.text)

def main():

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    print("Бот запущен... Нажми Ctrl+C для остановки.")
    application.run_polling()

if __name__ == '__main__':
    main()