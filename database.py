
import aiosqlite

DB_NAME = "avtogo.db"


async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:

        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                phone TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS cars (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                brand TEXT NOT NULL,
                model TEXT NOT NULL,
                year INTEGER,
                mileage INTEGER,
                engine TEXT,
                fuel TEXT,
                transmission TEXT,
                drive TEXT,
                body TEXT,
                price INTEGER,
                city TEXT,
                description TEXT,
                phone TEXT,
                owners_count INTEGER,
                accidents TEXT,
                painted_parts TEXT,
                photos TEXT,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # Добавляем новые поля в уже существующую базу
        cursor = await db.execute("PRAGMA table_info(cars)")
        existing_columns = [row[1] for row in await cursor.fetchall()]

        new_columns = {
            "owners_count": "INTEGER",
            "accidents": "TEXT",
            "painted_parts": "TEXT",
            "photos": "TEXT"
        }

        for column, column_type in new_columns.items():
            if column not in existing_columns:
                await db.execute(
                    f"ALTER TABLE cars ADD COLUMN {column} {column_type}"
                )

        await db.commit()

    print("База данных AvtoGo готова!")
