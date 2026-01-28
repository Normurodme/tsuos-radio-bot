import os
import json
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ================== SOZLAMALAR ==================
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

CHANNEL_USERNAME = "@tsuos_radio"

OWNER_ID = 6220077209
ADMIN_IDS = [
    6220077209,
    6617998011,
    6870150995,
]

WELCOME_TEXT = "Xush kelibsiz! TSUOS radiosiga xabar jo‘natishingiz mumkin."
WAIT_TEXT = "Xabar yuborildi📤"

COUNTER_FILE = "counter.json"

# pending_id -> data
PENDING = {}

# admin_message_id -> user_id (reply uchun)
MESSAGE_MAP = {}

# ================== YORDAMCHI ==================
def load_json(file, default):
    if not os.path.exists(file):
        with open(file, "w", encoding="utf-8") as f:
            json.dump(default, f)
        return default
    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f)

# ================== COUNTER ==================
def get_next_count():
    data = load_json(COUNTER_FILE, {"count": 0})
    data["count"] += 1
    save_json(COUNTER_FILE, data)
    return data["count"]

# ================== START ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME_TEXT)

# ================== USER MESSAGE ==================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user = update.message.from_user

    # -------- ADMIN REPLY --------
    if user.id in ADMIN_IDS and update.message.reply_to_message:
        replied_id = update.message.reply_to_message.message_id
        if replied_id in MESSAGE_MAP:
            await context.bot.send_message(
                chat_id=MESSAGE_MAP[replied_id],
                text=f"📻 TSUOS Radio javobi:\n\n{update.message.text}"
            )
        return

    # -------- FOYDALANUVCHI --------
    count = get_next_count()
    header = f"Yangi xabar🔔({count})"

    username = f"@{user.username}" if user.username else "(username yo‘q)"
    user_text = update.message.text or ""

    admin_text = (
        f"{header}\n\n"
        f"👤 Yuboruvchi: {username}\n"
        f"🆔 ID: {user.id}\n\n"
        f"📩 Xabar:\n<b>{user_text}</b>"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Tasdiqlash✅️", callback_data=f"approve:{count}"),
            InlineKeyboardButton("Rad etish🚫", callback_data=f"reject:{count}"),
        ]
    ])

    PENDING[count] = {
        "user_id": user.id,
        "username": username,
        "text": user_text,
        "header": header,
        "admin_messages": {},
    }

    for admin_id in ADMIN_IDS:
        sent = await context.bot.send_message(
            chat_id=admin_id,
            text=admin_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        PENDING[count]["admin_messages"][admin_id] = sent.message_id
        MESSAGE_MAP[sent.message_id] = user.id

    # USERGA JAVOB
    await update.message.reply_text(WAIT_TEXT)

# ================== BUTTONS ==================
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    admin_id = query.from_user.id
    if admin_id not in ADMIN_IDS:
        return

    action, msg_id = query.data.split(":")
    msg_id = int(msg_id)

    if msg_id not in PENDING:
        return

    data = PENDING.pop(msg_id)
    admin_name = query.from_user.first_name

    if action == "approve":
        status_owner = f"\n\nTasdiqlandi — by {admin_name}"
        status_other = "\n\nTasdiqlandi"

        # Kanalga yuborish
        await context.bot.send_message(
            chat_id=CHANNEL_USERNAME,
            text=f"{data['header']}\n\n*{data['text']}*",
            parse_mode="Markdown"
        )

        # Foydalanuvchiga xabar
        await context.bot.send_message(
            chat_id=data["user_id"],
            text="Tasdiqlandi✅️"
        )

    else:
        status_owner = f"\n\nRad etildi — by {admin_name}"
        status_other = "\n\nRad etildi"

        # Foydalanuvchiga xabar
        await context.bot.send_message(
            chat_id=data["user_id"],
            text="Rad etildi🚫"
        )

    # -------- BARCHA ADMINLARDA XABARNI SAQLAB QOLISH --------
    base_text = (
        f"{data['header']}\n\n"
        f"👤 Yuboruvchi: {data['username']}\n"
        f"🆔 ID: {data['user_id']}\n\n"
        f"📩 Xabar:\n<b>{data['text']}</b>"
    )

    for aid, mid in data["admin_messages"].items():
        try:
            await context.bot.edit_message_text(
                chat_id=aid,
                message_id=mid,
                text=base_text + (status_owner if aid == OWNER_ID else status_other),
                parse_mode="HTML"
            )
        except:
            pass

# ================== RUN ==================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_buttons))

    print("🤖 TSUOS Radio bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
