import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Это AvtoGo 🚗\n\n"
        "Авторынок всей России.\n"
        "Скоро здесь можно будет размещать объявления "
        "и искать автомобили."
    )


def main():
    token = os.getenv("BOT_TOKEN")

    if not token:
        raise RuntimeError("Не найден токен BOT_TOKEN")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))

    print("AvtoGo запущен!")
    app.run_polling()


if __name__ == "__main__":
    main()