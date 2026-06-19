import hashlib
import hmac
import json
import logging
from pathlib import Path
from typing import Optional
from urllib.parse import unquote

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import database as db
from config import (
    ADMIN_IDS,
    API_BASE_URL,
    BOT_TOKEN,
    DEFAULT_PROMO_CODE,
    TELEGRAM_CHANNEL,
    TELEGRAM_CHANNEL_URL,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
WEBAPP_DIR = BASE_DIR / "webapp"

app = FastAPI(title="Сырком Shop API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Telegram initData validation ─────────────────────────────────────────────

def validate_init_data(init_data: str) -> Optional[dict]:
    if not init_data:
        return None
    try:
        parsed = {}
        for chunk in init_data.split("&"):
            key, _, val = chunk.partition("=")
            parsed[key] = unquote(val)

        received_hash = parsed.pop("hash", None)
        if not received_hash:
            return None

        data_check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(parsed.items())
        )
        secret_key = hmac.new(
            b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256
        ).digest()
        calculated = hmac.new(
            secret_key, data_check_string.encode(), hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(calculated, received_hash):
            return None

        user_raw = parsed.get("user")
        if user_raw:
            return json.loads(user_raw)
        return {}
    except Exception as e:
        logger.warning("initData validation failed: %s", e)
        return None


def get_user_from_request(request: Request) -> dict:
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    tg_user = validate_init_data(init_data)
    if not tg_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    user = db.get_or_create_user(
        telegram_id=tg_user["id"],
        username=tg_user.get("username"),
        first_name=tg_user.get("first_name"),
        last_name=tg_user.get("last_name"),
    )
    return user


# ── Static files ─────────────────────────────────────────────────────────────

@app.get("/webapp")
async def webapp_index():
    return FileResponse(WEBAPP_DIR / "index.html")


app.mount("/webapp/static", StaticFiles(directory=WEBAPP_DIR), name="static")


# ── API endpoints ────────────────────────────────────────────────────────────

@app.get("/api/profile")
async def api_profile(request: Request):
    user = get_user_from_request(request)
    favorites = db.get_favorites(user["id"])
    orders = db.get_orders_by_user(user["id"])
    return {
        "id": user["id"],
        "telegram_id": user["telegram_id"],
        "first_name": user.get("first_name") or "",
        "username": user.get("username") or "",
        "city": user.get("city") or "",
        "favorites_count": len(favorites),
        "orders_count": len(orders),
    }


@app.get("/api/countries")
async def api_countries():
    return db.get_countries()


@app.get("/api/categories")
async def api_categories(country: Optional[str] = None):
    return db.get_categories(country)


@app.get("/api/products")
async def api_products(
    request: Request,
    country: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
):
    user = get_user_from_request(request)
    products = db.get_products(country=country, category=category, search=search)
    fav_ids = db.get_favorite_ids(user["id"])
    for p in products:
        p["is_favorite"] = p["id"] in fav_ids
    return products


@app.get("/api/products/{product_id}")
async def api_product(product_id: int, request: Request):
    user = get_user_from_request(request)
    product = db.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    fav_ids = db.get_favorite_ids(user["id"])
    product["is_favorite"] = product_id in fav_ids
    return product


@app.get("/api/favorites")
async def api_favorites(request: Request):
    user = get_user_from_request(request)
    favorites = db.get_favorites(user["id"])
    for p in favorites:
        p["is_favorite"] = True
    return favorites


class FavoriteRequest(BaseModel):
    product_id: int


@app.post("/api/favorites/toggle")
async def api_toggle_favorite(body: FavoriteRequest, request: Request):
    user = get_user_from_request(request)
    is_fav = db.toggle_favorite(user["id"], body.product_id)
    return {"is_favorite": is_fav}


@app.get("/api/cart")
async def api_cart(request: Request):
    user = get_user_from_request(request)
    items = db.get_cart(user["id"])
    total = sum(i["price"] * i["quantity"] for i in items)
    return {"items": items, "total": total}


class CartUpdateRequest(BaseModel):
    product_id: int
    quantity: int


@app.post("/api/cart/update")
async def api_cart_update(body: CartUpdateRequest, request: Request):
    user = get_user_from_request(request)
    product = db.get_product(body.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.set_cart_item(user["id"], body.product_id, body.quantity)
    items = db.get_cart(user["id"])
    total = sum(i["price"] * i["quantity"] for i in items)
    return {"items": items, "total": total}


@app.get("/api/orders")
async def api_orders(request: Request):
    user = get_user_from_request(request)
    orders = db.get_orders_by_user(user["id"])
    result = []
    for o in orders:
        items = db.get_order_items(o["id"])
        result.append({**o, "items": items})
    return result


class OrderRequest(BaseModel):
    phone: str
    address: str
    comment: str = ""


def _extract_promo(comment: str) -> str:
    settings_promo = db.get_setting("promo_code", DEFAULT_PROMO_CODE).upper()
    if settings_promo in comment.upper().replace(" ", ""):
        return settings_promo
    return ""


@app.post("/api/orders")
async def api_create_order(body: OrderRequest, request: Request):
    user = get_user_from_request(request)
    cart = db.get_cart(user["id"])
    if not cart:
        raise HTTPException(status_code=400, detail="Cart is empty")

    total = sum(i["price"] * i["quantity"] for i in cart)
    promo_code = _extract_promo(body.comment)
    discount_pct = int(db.get_setting("promo_discount", "5"))

    if promo_code:
        total = total * (1 - discount_pct / 100)

    customer_name = user.get("first_name") or user.get("username") or "Клиент"
    items = [
        {
            "product_id": i["id"],
            "name": i["name"],
            "price": i["price"],
            "quantity": i["quantity"],
        }
        for i in cart
    ]

    order_id = db.create_order(
        user_id=user["id"],
        customer_name=customer_name,
        phone=body.phone,
        address=body.address,
        comment=body.comment,
        promo_code=promo_code,
        items=items,
        total=round(total, 2),
    )

    payment_template = db.get_setting("payment_details", "")
    payment_details = payment_template.replace("{order_id}", str(order_id))

    await _notify_new_order(order_id, user, body, items, round(total, 2), promo_code)

    return {
        "order_id": order_id,
        "total": round(total, 2),
        "payment_details": payment_details,
    }


@app.get("/api/promotions")
async def api_promotions():
    promo = db.get_setting("promo_code", DEFAULT_PROMO_CODE)
    discount = db.get_setting("promo_discount", "5")
    return {
        "channel": TELEGRAM_CHANNEL,
        "channel_url": TELEGRAM_CHANNEL_URL,
        "promotions": [
            {
                "title": f"Промокод {promo}",
                "description": (
                    f"Скидка {discount}% на первый заказ. "
                    "Введите промокод в комментарии при оформлении. "
                    "Действует на всё, кроме наборов."
                ),
            },
            {
                "title": f"Telegram-канал {TELEGRAM_CHANNEL}",
                "description": "Новости, акции и дегустации — подписывайтесь!",
                "link": TELEGRAM_CHANNEL_URL,
            },
            {
                "title": "Дегустации в СПб",
                "description": "Магазин-кафе в центре Санкт-Петербурга — приходите на дегустации!",
            },
        ],
    }


async def _send_telegram(chat_id: int, text: str) -> None:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"})
    except Exception as e:
        logger.error("Failed to send Telegram message to %s: %s", chat_id, e)


async def _notify_new_order(
    order_id: int,
    user: dict,
    body: "OrderRequest",
    items: list,
    total: float,
    promo_code: str,
) -> None:
    from datetime import datetime

    items_lines = "\n".join(
        f"- {i['name']} x{i['quantity']} = {i['price'] * i['quantity']:.0f} ₽"
        for i in items
    )
    username = user.get("username")
    client_line = (
        f"{body.phone}"
        if not username
        else f"@{username}, {body.phone}"
    )
    now = datetime.utcnow().strftime("%d.%m.%Y %H:%M")
    payment = db.get_setting("payment_details", "").replace("{order_id}", str(order_id))

    user_text = (
        f"✅ Ваш заказ №{order_id} принят!\n\n"
        f"🛍️ Товары:\n{items_lines}\n\n"
        f"💰 Итого: {total:,.0f} ₽\n\n"
        f"{payment}\n\n"
        f"📦 Доставка: {body.address}\n\n"
        f"Менеджер свяжется с вами для подтверждения!"
    )
    admin_text = (
        f"📦 <b>НОВЫЙ ЗАКАЗ #{order_id}</b>\n\n"
        f"👤 Клиент: {user.get('first_name') or 'Клиент'} ({client_line})\n"
        f"📍 Адрес: {body.address}\n\n"
        f"🛍️ Товары:\n{items_lines}\n\n"
        f"💰 Итого: {total:,.0f} ₽\n"
        f"💬 Комментарий: {body.comment or '—'}\n"
        f"🎁 Промокод: {promo_code or '—'}\n\n"
        f"📅 {now}"
    )
    await _send_telegram(user["telegram_id"], user_text)
    for admin_id in set(ADMIN_IDS + db.get_admin_ids()):
        await _send_telegram(admin_id, admin_text)


@app.get("/api/health")
async def health():
    return {"status": "ok", "api_base": API_BASE_URL}
