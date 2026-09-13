import os
import base64
import secrets
import string
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)

# ---------- Logging ----------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------- Config ----------
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
PORT = int(os.environ.get("PORT", 8080))
RAILWAY_DOMAIN = os.environ.get("RAILWAY_PUBLIC_DOMAIN")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "edutoolb-secret")

if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is not set")

# Conversation states
CHOOSING, TYPING = range(2)

# ---------- Tool Definitions ----------
def word_count(text: str) -> str:
    words = len(text.split())
    chars = len(text)
    chars_no_space = len(text.replace(" ", ""))
    return (
        f"📊 *Word Count Results*\n\n"
        f"Words: `{words}`\n"
        f"Characters (with spaces): `{chars}`\n"
        f"Characters (no spaces): `{chars_no_space}`"
    )

def case_convert(text: str) -> str:
    return (
        f"🔠 *Case Conversion*\n\n"
        f"UPPER: `{text.upper()}`\n"
        f"lower: `{text.lower()}`\n"
        f"Title: `{text.title()}`\n"
        f"Swap: `{text.swapcase()}`"
    )

def base64_encode(text: str) -> str:
    encoded = base64.b64encode(text.encode()).decode()
    return f"🔐 *Base64 Encoded*\n\n`{encoded}`"

def base64_decode(text: str) -> str:
    try:
        decoded = base64.b64decode(text.encode()).decode()
        return f"🔓 *Base64 Decoded*\n\n`{decoded}`"
    except Exception:
        return "❌ Invalid Base64 string. Please check and try again."

def password_generator(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    pwd = "".join(secrets.choice(alphabet) for _ in range(length))
    return f"🔑 *Generated Password*\n\n`{pwd}`\n\n_Length: {length}_"

def unit_converter(text: str) -> str:
    # Format: "10 km to miles" or "100 f to c"
    try:
        parts = text.lower().split()
        value = float(parts[0])
        from_unit = parts[1]
        to_unit = parts[3]

        conversions = {
            ("km", "miles"): value * 0.621371,
            ("miles", "km"): value * 1.60934,
            ("kg", "lbs"): value * 2.20462,
            ("lbs", "kg"): value * 0.453592,
            ("c", "f"): (value * 9 / 5) + 32,
            ("f", "c"): (value - 32) * 5 / 9,
            ("m", "ft"): value * 3.28084,
            ("ft", "m"): value * 0.3048,
        }

        result = conversions.get((from_unit, to_unit))
        if result is None:
            return "❌ Unsupported conversion. Try: `10 km to miles`, `100 f to c`, `5 kg to lbs`"

        return f"📏 *Unit Conversion*\n\n`{value} {from_unit}` = `{round(result, 4)} {to_unit}`"
    except Exception:
        return "❌ Format error. Use: `10 km to miles` or `100 f to c`"

# ---------- Handlers ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [
        [InlineKeyboardButton("📊 Word Counter", callback_data="word_count")],
        [InlineKeyboardButton("🔠 Case Converter", callback_data="case_convert")],
        [InlineKeyboardButton("🔐 Base64 Encode", callback_data="b64_encode")],
        [InlineKeyboardButton("🔓 Base64 Decode", callback_data="b64_decode")],
        [InlineKeyboardButton("🔑 Password Generator", callback_data="password")],
        [InlineKeyboardButton("📏 Unit Converter", callback_data="unit")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 Welcome to *EduToolB*!\n\n"
        "Choose a tool below:",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )
    return CHOOSING

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "password":
        result = password_generator()
        await query.message.reply_text(result, parse_mode="Markdown")
        return CHOOSING

    prompts = {
        "word_count": "✏️ Send me the text to count words and characters.",
        "case_convert": "✏️ Send me the text to convert case.",
        "b64_encode": "✏️ Send me the text to encode in Base64.",
        "b64_decode": "✏️ Send me the Base64 string to decode.",
        "unit": "✏️ Send a conversion like `10 km to miles` or `100 f to c`.",
    }

    context.user_data["tool"] = query.data
    await query.message.reply_text(prompts[query.data], parse_mode="Markdown")
    return TYPING

async def process_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    tool = context.user_data.get("tool")
    text = update.message.text

    if tool == "word_count":
        result = word_count(text)
    elif tool == "case_convert":
        result = case_convert(text)
    elif tool == "b64_encode":
        result = base64_encode(text)
    elif tool == "b64_decode":
        result = base64_decode(text)
    elif tool == "unit":
        result = unit_converter(text)
    else:
        result = "❌ Unknown tool. Send /start to begin again."

    await update.message.reply_text(result, parse_mode="Markdown")

    keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="menu")]]
    await update.message.reply_text(
        "Want another tool?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return CHOOSING

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    return await start(update, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Cancelled. Send /start to begin again.")
    return ConversationHandler.END

# ---------- App Setup ----------
def main():
    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING: [
                CallbackQueryHandler(button_handler),
                CallbackQueryHandler(menu_handler, pattern="^menu$"),
            ],
            TYPING: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_text)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)

    # Webhook setup for Railway
    if RAILWAY_DOMAIN:
        webhook_url = f"https://{RAILWAY_DOMAIN}/{WEBHOOK_SECRET}"
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=WEBHOOK_SECRET,
            webhook_url=webhook_url,
        )
    else:
        # Local fallback (polling)
        app.run_polling()

if __name__ == "__main__":
    main()
