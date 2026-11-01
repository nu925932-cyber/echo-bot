import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, 
    ContextTypes, ConversationHandler
)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Твой токен
TOKEN = "9219000330:AAFDyxqZkS1RQ3Qr3ba7WBrgwze2Hy9KwRQ"

# Определяем состояния (шаги опроса)
NAME, AGE, HOBBY = range(3)

# --- Шаг 1: Начало опроса ---
async def start_survey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Очищаем предыдущие данные (если были)
    context.user_data.clear()
    await update.message.reply_text(
        "Привет! Давай познакомимся. Это небольшой опрос.\n"
        "Напиши свое имя (или /cancel, чтобы выйти):"
    )
    return NAME # Переходим в состояние "Ждем имя"

# --- Шаг 2: Получаем имя ---
async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    await update.message.reply_text(f"Приятно познакомиться, {update.message.text}!\nСколько тебе лет?")
    return AGE # Переходим к возрасту

# --- Шаг 3: Получаем возраст ---
async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['age'] = update.message.text
    await update.message.reply_text("Отлично! А какое у тебя хобби?")
    return HOBBY # Переходим к хобби

# --- Шаг 4: Получаем хобби и завершаем ---
async def get_hobby(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['hobby'] = update.message.text
    
    # Формируем сводку из того, что сохранили
    summary = (
        "Спасибо за ответы! Вот что я запомнил:\n\n"
        f"👤 Имя: {context.user_data['name']}\n"
        f"🎂 Возраст: {context.user_data['age']}\n"
        f"🎨 Хобби: {context.user_data['hobby']}\n\n"
        "Хорошего дня! 😊"
    )
    await update.message.reply_text(summary)
    return ConversationHandler.END # Завершаем диалог

# --- Отмена опроса ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Опрос отменен. Если захочешь начать заново, напиши /survey.")
    return ConversationHandler.END # Выходим из диалога

def main():
    application = Application.builder().token(TOKEN).build()

    # Создаем обработчик беседы (FSM)
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("survey", start_survey)], # Начинается с команды /survey
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_age)],
            HOBBY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_hobby)],
        },
        fallbacks=[CommandHandler("cancel", cancel)], # Если написать /cancel на любом шаге
    )

    application.add_handler(conv_handler)

    print("Бот-опросник запущен... Нажми Ctrl+C для остановки.")
    application.run_polling()

if __name__ == '__main__':
    main()