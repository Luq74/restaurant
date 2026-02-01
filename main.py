import asyncio
import logging
import os
import sys
import sqlite3
import json
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, Dict, Any

# Load environment variables
load_dotenv()

# Configuration
API_TOKEN = os.getenv("API_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
if ADMIN_ID:
    ADMIN_ID = int(ADMIN_ID)
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
WEBHOOK_PATH = "/webhook"

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Initialize Bot
if not API_TOKEN:
    logger.error("API_TOKEN is not set in .env file!")
    # We don't exit here to allow build on Vercel even if env is missing initially
    # sys.exit(1)

bot = Bot(token=API_TOKEN) if API_TOKEN else None
dp = Dispatcher()

# Menu Data
MENU = {
    "Appetizer": [
        {"name": "Salad Segar", "price": 50000, "image": "/static/images/salad_segar.jpg"},
        {"name": "Caesar Salad", "price": 45000, "image": "/static/images/caesar_salad.jpg"},
    ],
    "Main Course": [
        {"name": "Nasi Goreng Kambing", "price": 100000, "image": "/static/images/nasi_goreng_kambing.jpg"},
        {"name": "Mie Goreng Spesial", "price": 100000, "image": "/static/images/mie_goreng_spesial.jpg"},
        {"name": "Steak Sapi", "price": 250000, "image": "/static/images/steak_sapi.jpg"},
        {"name": "Sirloin Steak", "price": 185000, "image": "/static/images/sirloin_steak.jpg"},
    ],
    "Drink": [
        {"name": "Kopi Tubruk", "price": 35000, "image": "/static/images/kopi_tubruk.jpg"},
        {"name": "Iced Coffee Latte", "price": 40000, "image": "/static/images/iced_coffee_latte.jpg"},
    ],
    "Dessert": [
        {"name": "Chocolate Lava Cake", "price": 55000, "image": "/static/images/chocolate_lava_cake.jpg"},
        {"name": "Fruit Platter", "price": 40000, "image": "/static/images/fruit_platter.jpg"},
        {"name": "Tiramisu Cake", "price": 50000, "image": "/static/images/tiramisu_cake.jpg"},
    ]
}

# Database Setup (Note: ephemeral on Serverless)
def init_db():
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS orders
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  user_name TEXT, 
                  order_details TEXT, 
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()
    logger.info("Database initialized.")

def save_order(user_name, order_details):
    try:
        conn = sqlite3.connect('orders.db')
        c = conn.cursor()
        c.execute("INSERT INTO orders (user_name, order_details) VALUES (?, ?)", (user_name, order_details))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to save order to DB: {e}")

# FastAPI App
app = FastAPI()

# Mount Static Files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Bot Handlers
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    logger.info(f"Start command from {message.from_user.full_name} (ID: {message.from_user.id})")
    
    web_app_url = BASE_URL
    
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(
        text="🍽️ BUKA MENU SEKARANG",
        web_app=types.WebAppInfo(url=web_app_url))
    )
    
    await message.answer(
        f"✨ **MERCURE HOTELS BANDUNG NEXA SUPRATMAN**\n\n"
        f"Selamat datang, {message.from_user.full_name}!\n\n"
        "Silakan klik tombol di bawah untuk melihat menu dan memesan makanan:",
        reply_markup=builder.as_markup(resize_keyboard=True),
        parse_mode="Markdown"
    )

def format_order_message(data, source="Web"):
    try:
        customer_name = data.get('customer', 'Tamu')
        table_number = data.get('table', '-')
        items = data.get('items', {})
        total_str = data.get('total', '0')
        
        msg_lines = [
            f"🔔 <b>PESANAN BARU! ({source})</b>",
            f"👤 <b>Nama:</b> {customer_name}",
            f"📍 <b>Meja:</b> {table_number}",
            "",
            "📋 <b>Detail Pesanan:</b>"
        ]
        
        for item_name, details in items.items():
            qty = details.get('qty', 0)
            note = details.get('currentNote', '-')
            if note == "Tanpa catatan" or not note:
                note = "-"
            
            msg_lines.append(f"▫️ <b>{item_name}</b> (x{qty})")
            if note != "-":
                msg_lines.append(f"   <i>Catatan: {note}</i>")
        
        msg_lines.append("")
        msg_lines.append(f"💰 <b>{total_str}</b>")
        
        return "\n".join(msg_lines)
    except Exception as e:
        logger.error(f"Error formatting message: {e}")
        return f"⚠️ Error formatting order: {str(e)}"

@dp.message(F.web_app_data)
async def handle_order(message: types.Message):
    raw_data = message.web_app_data.data
    nama_tamu = message.from_user.full_name
    
    logger.info(f"Order received from {nama_tamu}: {raw_data}")
    
    try:
        data = json.loads(raw_data)
        if 'customer' not in data:
            data['customer'] = nama_tamu
            
        formatted_msg = format_order_message(data, source="Telegram WebApp")
        
        save_order(data.get('customer', nama_tamu), raw_data)
        
        await message.answer(f"✅ Pesanan Anda telah diterima!\n\n{formatted_msg}", parse_mode="HTML")
        
        if ADMIN_ID and bot:
            await bot.send_message(
                chat_id=ADMIN_ID,
                text=formatted_msg,
                parse_mode="HTML"
            )
            
    except json.JSONDecodeError:
        logger.error("Failed to decode JSON data")
        await message.answer("⚠️ Terjadi kesalahan dalam memproses data pesanan.")
    except Exception as e:
        logger.error(f"Error handling order: {e}")
        await message.answer("⚠️ Terjadi kesalahan sistem.")

# Pydantic Models
class OrderRequest(BaseModel):
    customer: str = "Tamu"
    table: str = "-"
    items: Dict[str, Any]
    total: str = "0"

class WaiterRequest(BaseModel):
    nama: str = "Tamu Tanpa Nama"
    table_number: str = "Tidak Disebutkan"

# Routes
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "menu": MENU})

@app.post("/submit_order")
async def submit_order(order: Request):
    # Using Request to handle generic JSON because structure might be dynamic
    try:
        data = await order.json()
        logger.info(f"Received HTTP order: {data}")
        
        formatted_msg = format_order_message(data, source="Browser/Web")
        save_order(data.get('customer', 'Tamu'), json.dumps(data))
        
        if ADMIN_ID and bot:
            await bot.send_message(chat_id=ADMIN_ID, text=formatted_msg, parse_mode="HTML")
            
        return JSONResponse({'status': 'ok', 'message': 'Order processed'})
    except Exception as e:
        logger.error(f"Error in submit_order: {e}")
        return JSONResponse({'status': 'error', 'message': str(e)}, status=500)

@app.post("/call_waiter")
async def call_waiter(req: WaiterRequest):
    try:
        nama_tamu = req.nama
        table_number = req.table_number
        
        logger.info(f"Waiter called by {nama_tamu} at Table {table_number}")
        
        if ADMIN_ID and bot:
            await bot.send_message(
                chat_id=ADMIN_ID,
                text=f"🛎️ **PANGGILAN PELAYAN!**\n\n"
                     f"📍 **Meja:** {table_number}\n"
                     f"👤 **Tamu:** {nama_tamu}\n\n"
                     f"Mohon segera dihampiri.",
                parse_mode="Markdown"
            )
            return JSONResponse({'status': 'ok', 'message': 'Waiter has been notified'})
        else:
            return JSONResponse({'status': 'error', 'message': 'Admin ID not configured'}, status=500)
    except Exception as e:
        logger.error(f"Error calling waiter: {e}")
        return JSONResponse({'status': 'error', 'message': str(e)}, status=500)

@app.post(WEBHOOK_PATH)
async def bot_webhook(update: dict):
    telegram_update = types.Update(**update)
    await dp.feed_update(bot, telegram_update)

@app.on_event("startup")
async def on_startup():
    init_db()
    if bot and BASE_URL:
        webhook_url = f"{BASE_URL}{WEBHOOK_PATH}"
        await bot.set_webhook(webhook_url)
        logger.info(f"Webhook set to {webhook_url}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
