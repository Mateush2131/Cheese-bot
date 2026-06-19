import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from config import DATABASE_PATH, DEFAULT_PAYMENT_DETAILS, DEFAULT_PROMO_CODE, DEFAULT_PROMO_DISCOUNT

SCHEMA_VERSION = 2


def _ensure_dir() -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_connection():
    _ensure_dir()
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _run_migrations(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL
        )
        """
    )
    row = conn.execute("SELECT MAX(version) AS v FROM schema_migrations").fetchone()
    current = row["v"] or 0

    if current < 1:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                city TEXT,
                is_client TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                country TEXT NOT NULL,
                category TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS favorites (
                user_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                PRIMARY KEY (user_id, product_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS cart_items (
                user_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY (user_id, product_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                customer_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                address TEXT NOT NULL,
                comment TEXT,
                promo_code TEXT,
                total REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'new',
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                product_name TEXT NOT NULL,
                price REAL NOT NULL,
                quantity INTEGER NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id)
            );

            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                author_name TEXT NOT NULL,
                text TEXT NOT NULL,
                admin_reply TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_products_country ON products(country);
            CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
            CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id);
            CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
            """
        )
        conn.execute(
            "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
            (1, datetime.utcnow().isoformat()),
        )

    if current < 2:
        conn.execute("DELETE FROM cart_items")
        conn.execute("DELETE FROM favorites")
        conn.execute("DELETE FROM products")
        conn.executemany(
            "INSERT INTO products (name, description, price, country, category) VALUES (?, ?, ?, ?, ?)",
            PRODUCTS_SEED,
        )
        conn.execute(
            "UPDATE settings SET value = ? WHERE key = 'promo_discount'",
            (str(DEFAULT_PROMO_DISCOUNT),),
        )
        conn.execute(
            "UPDATE orders SET status = 'delivered' WHERE status = 'done'"
        )
        conn.execute(
            "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
            (2, datetime.utcnow().isoformat()),
        )


def init_db() -> None:
    with get_connection() as conn:
        _run_migrations(conn)
        _seed_settings(conn)
        _seed_products(conn)


def _seed_settings(conn: sqlite3.Connection) -> None:
    defaults = {
        "promo_code": DEFAULT_PROMO_CODE,
        "promo_discount": str(DEFAULT_PROMO_DISCOUNT),
        "payment_details": DEFAULT_PAYMENT_DETAILS,
        "admin_ids": "[]",
    }
    for key, value in defaults.items():
        conn.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            (key, value),
        )


PRODUCTS_SEED = [
    # Россия (Алтай)
    ("Зеленодольский", "Алтайский сыр ручной работы", 180, "Россия", "Россия (Алтай)"),
    ("Горный", "Классический алтайский сыр", 180, "Россия", "Россия (Алтай)"),
    ("Покрова Алтая", "Нежный сыр с горного Алтая", 140, "Россия", "Россия (Алтай)"),
    ("Гауда", "Алтайская гауда, выдержанная", 180, "Россия", "Россия (Алтай)"),
    ("Леаус", "Мягкий алтайский сыр", 160, "Россия", "Россия (Алтай)"),
    ("Горный пармезан", "Твёрдый выдержанный сыр с гор", 450, "Россия", "Россия (Алтай)"),
    ("Масло сливочное", "Натуральное сливочное масло", 240, "Россия", "Россия (Алтай)"),
    ("Масло ГХИ", "Топлёное масло ГХИ", 700, "Россия", "Россия (Алтай)"),
    ("Сок облепиховый", "Натуральный облепиховый сок", 350, "Россия", "Россия (Алтай)"),
    ("Беллер Кнолле", "Сыр с травами и специями", 300, "Россия", "Россия (Алтай)"),
    # Италия
    ("Грана падано", "Итальянский твёрдый сыр", 490, "Италия", "Италия"),
    ("Пармеждано Реджано", "Настоящий Parmigiano Reggiano", 590, "Италия", "Италия"),
    ("Пармеждано с трюфелем", "Пармезан с белым трюфелем", 790, "Италия", "Италия"),
    ("Пекорино", "Овечий итальянский сыр", 590, "Италия", "Италия"),
    ("Молитерно Овечий с Трюфелем", "Овечий сыр с трюфелем", 990, "Италия", "Италия"),
    ("Горгонзола Пиканте/Дольче", "Итальянская голубая плесень", 490, "Италия", "Италия"),
    ("Салями с трюфелем", "Итальянская салями с трюфелем", 890, "Италия", "Италия"),
    ("Трюфельная паста", "Паста из чёрного трюфеля", 990, "Италия", "Италия"),
    # Голландия
    ("Старый Амстердам", "Выдержанный голландский сыр", 690, "Голландия", "Голландия"),
    ("Тартюфо коровий", "Коровий сыр с трюфелем", 590, "Голландия", "Голландия"),
    ("Тартюфо козий", "Козий сыр с трюфелем", 690, "Голландия", "Голландия"),
    ("Фрико Козий сыр", "Голландский козий сыр", 490, "Голландия", "Голландия"),
    ("Козий ХО", "Выдержанный козий сыр", 590, "Голландия", "Голландия"),
    ("Маасдам", "Голландский сыр с «глазками»", 290, "Голландия", "Голландия"),
    ("Базирон Три перца", "Сыр с тремя видами перца", 590, "Голландия", "Голландия"),
    ("Базирон Доппио", "Двойной крем-базирон", 690, "Голландия", "Голландия"),
    ("Боерен Тротс Трюфель мед козий", "Козий сыр с трюфелем и мёдом", 690, "Голландия", "Голландия"),
    ("Боерен Тротс Трюфель медь", "Сыр с трюфелем и медью", 790, "Голландия", "Голландия"),
    ("Боерен Тротс лесные грибы", "Сыр с лесными грибами", 690, "Голландия", "Голландия"),
    # Испания
    ("Манчего овечий", "Испанский овечий сыр", 590, "Испания", "Испания"),
    ("Манчего Овечий с трюфелем", "Манчего с белым трюфелем", 690, "Испания", "Испания"),
    ("Хамон серано 9мес", "Хамон серано, выдержка 9 месяцев", 590, "Испания", "Испания"),
    ("Хамон иберико", "Хамон иберико, премиум", 890, "Испания", "Испания"),
    ("Оливки", "Маслины/оливки, ассорти", 290, "Испания", "Испания"),
    # Германия
    ("Монтаньола", "Немецкий сыр с плесенью", 690, "Германия", "Германия"),
    ("ДорБлю", "Голубой сыр Dorblu", 390, "Германия", "Германия"),
    ("Камбацола", "Мягкий сыр с белой плесенью", 690, "Германия", "Германия"),
    ("Сент Агюр", "Голубой французско-немецкий сыр", 690, "Германия", "Германия"),
    ("Бри/камамбер", "Мягкий сыр бри или камамбер", 600, "Германия", "Германия"),
    # Англия
    ("Чедр", "Классический английский чеддер", 590, "Англия", "Англия"),
    ("Ильчестер Десертный", "Английский десертный сыр", 590, "Англия", "Англия"),
    # Франция
    ("Бри Франция", "Классический французский бри", 390, "Франция", "Франция"),
    ("Бри с трюфелем", "Бри с белым трюфелем", 690, "Франция", "Франция"),
    # Норвегия
    ("Норвежский завтрак/Брюност", "Карамельный коричневый сыр", 590, "Норвегия", "Норвегия"),
    # Польша
    ("Бри Польша", "Польский мягкий сыр бри", 350, "Польша", "Польша"),
]


def _seed_products(conn: sqlite3.Connection) -> None:
    count = conn.execute("SELECT COUNT(*) AS c FROM products").fetchone()["c"]
    if count > 0:
        return
    conn.executemany(
        "INSERT INTO products (name, description, price, country, category) VALUES (?, ?, ?, ?, ?)",
        PRODUCTS_SEED,
    )


# ── Users ──────────────────────────────────────────────────────────────────

def get_or_create_user(
    telegram_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
) -> dict:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        ).fetchone()
        if row:
            return dict(row)
        conn.execute(
            """INSERT INTO users (telegram_id, username, first_name, last_name, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (telegram_id, username, first_name, last_name, datetime.utcnow().isoformat()),
        )
        row = conn.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        ).fetchone()
        return dict(row)


def update_user(telegram_id: int, **fields) -> None:
    if not fields:
        return
    cols = ", ".join(f"{k} = ?" for k in fields)
    vals = list(fields.values()) + [telegram_id]
    with get_connection() as conn:
        conn.execute(f"UPDATE users SET {cols} WHERE telegram_id = ?", vals)


def get_user_by_telegram_id(telegram_id: int) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        ).fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: int) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None


def get_all_users(limit: int = 100, offset: int = 0, city: Optional[str] = None) -> list[dict]:
    with get_connection() as conn:
        if city:
            rows = conn.execute(
                "SELECT * FROM users WHERE city LIKE ? ORDER BY id DESC LIMIT ? OFFSET ?",
                (f"%{city}%", limit, offset),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM users ORDER BY id DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        return [dict(r) for r in rows]


def count_users() -> int:
    with get_connection() as conn:
        return conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]


def get_all_telegram_ids() -> list[int]:
    with get_connection() as conn:
        rows = conn.execute("SELECT telegram_id FROM users").fetchall()
        return [r["telegram_id"] for r in rows]


# ── Products ─────────────────────────────────────────────────────────────────

def get_products(
    country: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
) -> list[dict]:
    query = "SELECT * FROM products WHERE 1=1"
    params: list[Any] = []
    if country:
        query += " AND country = ?"
        params.append(country)
    if category:
        query += " AND category = ?"
        params.append(category)
    if search:
        query += " AND name LIKE ?"
        params.append(f"%{search}%")
    query += " ORDER BY country, category, name"
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def get_product(product_id: int) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        return dict(row) if row else None


def get_countries() -> list[str]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT country FROM products ORDER BY country"
        ).fetchall()
        return [r["country"] for r in rows]


def get_categories(country: Optional[str] = None) -> list[str]:
    with get_connection() as conn:
        if country:
            rows = conn.execute(
                "SELECT DISTINCT category FROM products WHERE country = ? ORDER BY category",
                (country,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT DISTINCT category FROM products ORDER BY category"
            ).fetchall()
        return [r["category"] for r in rows]


# ── Favorites ──────────────────────────────────────────────────────────────

def get_favorites(user_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT p.* FROM products p
               JOIN favorites f ON f.product_id = p.id
               WHERE f.user_id = ? ORDER BY p.name""",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_favorite_ids(user_id: int) -> set[int]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT product_id FROM favorites WHERE user_id = ?", (user_id,)
        ).fetchall()
        return {r["product_id"] for r in rows}


def toggle_favorite(user_id: int, product_id: int) -> bool:
    with get_connection() as conn:
        exists = conn.execute(
            "SELECT 1 FROM favorites WHERE user_id = ? AND product_id = ?",
            (user_id, product_id),
        ).fetchone()
        if exists:
            conn.execute(
                "DELETE FROM favorites WHERE user_id = ? AND product_id = ?",
                (user_id, product_id),
            )
            return False
        conn.execute(
            "INSERT INTO favorites (user_id, product_id) VALUES (?, ?)",
            (user_id, product_id),
        )
        return True


# ── Cart ─────────────────────────────────────────────────────────────────────

def get_cart(user_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT p.*, c.quantity FROM products p
               JOIN cart_items c ON c.product_id = p.id
               WHERE c.user_id = ? ORDER BY p.name""",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def set_cart_item(user_id: int, product_id: int, quantity: int) -> None:
    with get_connection() as conn:
        if quantity <= 0:
            conn.execute(
                "DELETE FROM cart_items WHERE user_id = ? AND product_id = ?",
                (user_id, product_id),
            )
        else:
            conn.execute(
                """INSERT INTO cart_items (user_id, product_id, quantity) VALUES (?, ?, ?)
                   ON CONFLICT(user_id, product_id) DO UPDATE SET quantity = excluded.quantity""",
                (user_id, product_id, quantity),
            )


def clear_cart(user_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM cart_items WHERE user_id = ?", (user_id,))


# ── Orders ───────────────────────────────────────────────────────────────────

def create_order(
    user_id: int,
    customer_name: str,
    phone: str,
    address: str,
    comment: str,
    promo_code: str,
    items: list[dict],
    total: float,
) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO orders
               (user_id, customer_name, phone, address, comment, promo_code, total, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'new', ?)""",
            (
                user_id,
                customer_name,
                phone,
                address,
                comment,
                promo_code,
                total,
                datetime.utcnow().isoformat(),
            ),
        )
        order_id = cur.lastrowid
        for item in items:
            conn.execute(
                """INSERT INTO order_items
                   (order_id, product_id, product_name, price, quantity)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    order_id,
                    item["product_id"],
                    item["name"],
                    item["price"],
                    item["quantity"],
                ),
            )
        conn.execute("DELETE FROM cart_items WHERE user_id = ?", (user_id,))
        return order_id


def get_orders_by_user(user_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_all_orders(limit: int = 50, offset: int = 0, status: Optional[str] = None) -> list[dict]:
    with get_connection() as conn:
        if status:
            rows = conn.execute(
                """SELECT o.*, u.first_name, u.username, u.telegram_id
                   FROM orders o JOIN users u ON u.id = o.user_id
                   WHERE o.status = ? ORDER BY o.created_at DESC LIMIT ? OFFSET ?""",
                (status, limit, offset),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT o.*, u.first_name, u.username, u.telegram_id
                   FROM orders o JOIN users u ON u.id = o.user_id
                   ORDER BY o.created_at DESC LIMIT ? OFFSET ?""",
                (limit, offset),
            ).fetchall()
        return [dict(r) for r in rows]


def get_order(order_id: int) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            """SELECT o.*, u.first_name, u.username, u.telegram_id
               FROM orders o JOIN users u ON u.id = o.user_id
               WHERE o.id = ?""",
            (order_id,),
        ).fetchone()
        return dict(row) if row else None


def get_order_items(order_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM order_items WHERE order_id = ?", (order_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def update_order_status(order_id: int, status: str) -> None:
    with get_connection() as conn:
        conn.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))


def count_orders() -> int:
    with get_connection() as conn:
        return conn.execute("SELECT COUNT(*) AS c FROM orders").fetchone()["c"]


def total_revenue() -> float:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(total), 0) AS s FROM orders WHERE status != 'cancelled'"
        ).fetchone()
        return float(row["s"])


# ── Reviews ──────────────────────────────────────────────────────────────────

def create_review(user_id: int, author_name: str, text: str) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO reviews (user_id, author_name, text, created_at)
               VALUES (?, ?, ?, ?)""",
            (user_id, author_name, text, datetime.utcnow().isoformat()),
        )
        return cur.lastrowid


def get_reviews(limit: int = 50, offset: int = 0) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT r.*, u.telegram_id, u.username
               FROM reviews r JOIN users u ON u.id = r.user_id
               ORDER BY r.created_at DESC LIMIT ? OFFSET ?""",
            (limit, offset),
        ).fetchall()
        return [dict(r) for r in rows]


def get_review(review_id: int) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            """SELECT r.*, u.telegram_id, u.username
               FROM reviews r JOIN users u ON u.id = r.user_id
               WHERE r.id = ?""",
            (review_id,),
        ).fetchone()
        return dict(row) if row else None


def set_review_reply(review_id: int, reply: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE reviews SET admin_reply = ? WHERE id = ?", (reply, review_id)
        )


def count_reviews() -> int:
    with get_connection() as conn:
        return conn.execute("SELECT COUNT(*) AS c FROM reviews").fetchone()["c"]


# ── Settings ─────────────────────────────────────────────────────────────────

def get_setting(key: str, default: str = "") -> str:
    with get_connection() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )


def get_admin_ids() -> list[int]:
    raw = get_setting("admin_ids", "[]")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return []


def add_admin_id(admin_id: int) -> None:
    ids = get_admin_ids()
    if admin_id not in ids:
        ids.append(admin_id)
        set_setting("admin_ids", json.dumps(ids))


def get_stats() -> dict:
    with get_connection() as conn:
        users = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
        users_today = conn.execute(
            "SELECT COUNT(*) AS c FROM users WHERE date(created_at) = date('now')"
        ).fetchone()["c"]
        clients = conn.execute(
            "SELECT COUNT(*) AS c FROM users WHERE is_client = 'yes'"
        ).fetchone()["c"]
        orders = conn.execute("SELECT COUNT(*) AS c FROM orders").fetchone()["c"]
        orders_week = conn.execute(
            "SELECT COUNT(*) AS c FROM orders WHERE created_at >= datetime('now', '-7 days')"
        ).fetchone()["c"]
        orders_month = conn.execute(
            "SELECT COUNT(*) AS c FROM orders WHERE created_at >= datetime('now', '-30 days')"
        ).fetchone()["c"]
        revenue = float(
            conn.execute(
                "SELECT COALESCE(SUM(total), 0) AS s FROM orders WHERE status != 'cancelled'"
            ).fetchone()["s"]
        )
        avg_check = round(revenue / orders, 0) if orders else 0
        conversion = round(clients / users * 100, 1) if users else 0.0
        reviews = conn.execute("SELECT COUNT(*) AS c FROM reviews").fetchone()["c"]

    return {
        "users": users,
        "users_today": users_today,
        "clients": clients,
        "orders": orders,
        "orders_week": orders_week,
        "orders_month": orders_month,
        "revenue": revenue,
        "avg_check": avg_check,
        "conversion": conversion,
        "reviews": reviews,
    }
