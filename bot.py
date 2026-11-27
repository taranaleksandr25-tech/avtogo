
import os
import json
import aiosqlite

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

from database import DB_NAME, init_db


# Этапы заполнения объявления
FIELDS = [
    ("brand", "Напиши марку автомобиля:"),
    ("model", "Напиши модель:"),
    ("year", "Год выпуска:"),
    ("mileage", "Пробег в километрах:"),
    ("engine", "Объём и мощность двигателя:"),
    ("fuel", "Тип топлива:"),
    ("transmission", "Коробка передач:"),
    ("drive", "Привод:"),
    ("body", "Тип кузова:"),
    ("price", "Цена в рублях:"),
    ("city", "Город и регион:"),
    ("description", "Расскажи об автомобиле:"),
    ("owners_count", "Сколько было владельцев?"),
    ("accidents", "Были ли ДТП? Если да, опиши:"),
    ("painted_parts", "Какие детали окрашивались?"),
    ("phone", "Контактный номер телефона:"),
]

PHOTO_STATE = len(FIELDS)
TEXT_STATES = list(range(len(FIELDS)))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """
            INSERT OR IGNORE INTO users (telegram_id, username)
            VALUES (?, ?)
            """,
            (user.id, user.username)
        )
        await db.commit()

    keyboard = [
        ["🚗 Разместить объявление"],
    ]

    await update.message.reply_text(
        "Привет! Это AvtoGo 🚗\n\n"
        "Авторынок всей России.\n\n"
        "Здесь ты сможешь продавать автомобили "
        "и находить машины для покупки.",
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True
        )
    )


async def add_car(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["car"] = {}
    context.user_data["step"] = 0
    context.user_data["photos"] = []

    await update.message.reply_text(
        "Начинаем размещение автомобиля!\n\n"
        + FIELDS[0][1]
    )

    return TEXT_STATES[0]


async def collect_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data["step"]
    field = FIELDS[step][0]

    context.user_data["car"][field] = update.message.text.strip()

    step += 1
    context.user_data["step"] = step

    if step < len(FIELDS):
        await update.message.reply_text(FIELDS[step][1])
        return TEXT_STATES[step]

    keyboard = [
        ["Готово", "Пропустить"],
    ]

    await update.message.reply_text(
        "Теперь отправь фотографии автомобиля.\n\n"
        "Можно добавить до 10 фотографий.\n"
        "Когда закончишь, нажми «Готово».\n"
        "Если фотографий пока нет, нажми «Пропустить».",
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True
        )
    )

    return PHOTO_STATE


async def collect_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photos = context.user_data["photos"]

    if len(photos) >= 10:
        await update.message.reply_text(
            "Максимум 10 фотографий. Нажми «Готово»."
        )
        return PHOTO_STATE

    photo_id = update.message.photo[-1].file_id
    photos.append(photo_id)

    await update.message.reply_text(
        f"Фото добавлено! Всего: {len(photos)} из 10."
    )

    return PHOTO_STATE


def to_number(value):
    try:
        return int(value.replace(" ", "").replace(",", ""))
    except (ValueError, AttributeError):
        return None


async def finish_car(update: Update, context: ContextTypes.DEFAULT_TYPE):
    car = context.user_data["car"]
    photos = context.user_data["photos"]
    telegram_id = update.effective_user.id

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT id FROM users WHERE telegram_id = ?",
            (telegram_id,)
        )
        user = await cursor.fetchone()

        if not user:
            await update.message.reply_text(
                "Сначала отправь /start."
            )
            return ConversationHandler.END

        await db.execute(
            """
            INSERT INTO cars (
                user_id, brand, model, year, mileage,
                engine, fuel, transmission, drive, body,
                price, city, description, phone,
                owners_count, accidents, painted_parts, photos
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user[0],
                car["brand"],
                car["model"],
                to_number(car["year"]),
                to_number(car["mileage"]),
                car["engine"],
                car["fuel"],
                car["transmission"],
                car["drive"],
                car["body"],
                to_number(car["price"]),
                car["city"],
                car["description"],
                car["phone"],
                to_number(car["owners_count"]),
                car["accidents"],
                car["painted_parts"],
                json.dumps(photos),
            )
        )

        await db.commit()

    await update.message.reply_text(
        "🎉 Объявление сохранено!\n\n"
        f"🚗 {car['brand']} {car['model']}\n"
        f"📅 Год: {car['year']}\n"
        f"🛣 Пробег: {car['mileage']} км\n"
        f"💰 Цена: {car['price']} ₽\n"
        f"📍 Город: {car['city']}\n"
        f"📸 Фотографий: {len(photos)}\n\n"
        "Объявление находится в базе AvtoGo.",
        reply_markup=ReplyKeyboardRemove()
    )

    context.user_data.clear()

    return ConversationHandler.END


async def finish_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "Пропустить":
        context.user_data["photos"] = []

    return await finish_car(update, context)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    await update.message.reply_text(
        "Размещение отменено.",
        reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END


async def post_init(application):
    await init_db()


def main():
    token = os.getenv("BOT_TOKEN")

    if not token:
        raise RuntimeError("Не найден токен BOT_TOKEN")

    app = (
        Application.builder()
        .token(token)
        .post_init(post_init)
        .build()
    )

    conversation = ConversationHandler(
        entry_points=[
            CommandHandler("addcar", add_car),
            MessageHandler(
                filters.Regex("^🚗 Разместить объявление$"),
                add_car
            ),
        ],
        states={
            **{
                state: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        collect_text
                    )
                ]
                for state in TEXT_STATES
            },
            PHOTO_STATE: [
                MessageHandler(
                    filters.PHOTO,
                    collect_photo
                ),
                MessageHandler(
                    filters.Regex("^(Готово|Пропустить)$"),
                    finish_photos
                ),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
        ],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conversation)

    print("AvtoGo запущен!")
    app.run_polling()


if __name__ == "__main__":
    main()
