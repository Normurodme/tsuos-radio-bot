import json
import os
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

CHANNEL_ID = -1001234567890  # ⚠️ O'ZINGNIKI BILAN ALMASHTIR

ADMINS = [
    6220077209,  # super admin (hammasini ko'radi)
    6617998011,
    6870150995,
]

SUPER_ADMIN_ID = 6220077209

COUNTER_FILE = "counter.json"

# ================== COUNTER ==================

def load_counter():
    if not os.path.exists(COUNTER_FILE):
        with open(COUNTER_FILE, "w") as f:
            json.dump({"count": 0}, f)
    with open(COUNTER_FILE, "r") as f:
        return json.load(f)["count"]

def save_counter(value):
    with open(COUNTER_FILE, "w") as f:
        json.dump({"count": value}, f)

counter = load_counter()

# ================== XABARLAR HOLATI ==================

messages_state = {}  # msg_id: {status, user_id, admin_msgs}

# ================== /start ==================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Xush kelibsiz! TSUOS radiosiga xabar jo‘natishingiz mumkin."
    )

# ================== USER XABARI ==================

async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global counter
    user = update.effective_user
    message = update.message

    counter += 1
    save_counter(counter)

    # foydalanuvchiga HAR DOIM javob
    await message.reply_text("Xabar yuborildi📤")

    # ADMINLARGA MATN
    def admin_text(full=False):
        text = f"Yangi xabar🔔({counter})\n\n"
        text += f"👤 Yuboruvchi: {user.first_name}\n"
        if full:
            text += f"🔗 Username: @{user.username}\n"
            text += f"🆔 ID: {user.id}\n"
        text += "\n📩 Xabar:\n"
        text += f"<b>{message.text or ''}</b>"
        return text

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Tasdiqlash✅️", callback_data=f"approve:{counter}"),
            InlineKeyboardButton("Rad etish🚫", callback_data=f"reject:{counter}")
        ]
    ])

    admin_message_ids = []

    for admin_id in ADMINS:
        full = admin_id == SUPER_ADMIN_ID
        sent = await context.bot.send_message(
            chat_id=admin_id,
            text=admin_text(full),
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        admin_message_ids.append((admin_id, sent.message_id))

    messages_state[counter] = {
        "status": "pending",
        "user_id": user.id,
        "admin_msgs": admin_message_ids,
    }

# ================== APPROVE / REJECT ==================

async def handle_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, num = query.data.split(":")
    num = int(num)

    if num not in messages_state:
        return

    msg = messages_state[num]

    if msg["status"] != "pending":
        await query.answer("Bu xabar allaqachon yopilgan", show_alert=True)
        return

    admin = query.from_user
    status_text = "Tasdiqlandi✅️" if action == "approve" else "Rad etildi🚫"

    msg["status"] = action

    # foydalanuvchiga xabar
    await context.bot.send_message(
        chat_id=msg["user_id"],
        text=status_text
    )

    # ADMIN XABARLARINI YANGILASH
    for admin_id, message_id in msg["admin_msgs"]:
        suffix = ""
        if admin_id == SUPER_ADMIN_ID:
            suffix = f" — by {admin.first_name}"

        await context.bot.edit_message_text(
            chat_id=admin_id,
            message_id=message_id,
            text=f"{query.message.text}\n\n{status_text}{suffix}",
            parse_mode="HTML"
        )

        # knopkalarni olib tashlash
        await context.bot.edit_message_reply_markup(
            chat_id=admin_id,
            message_id=message_id,
            reply_markup=None
        )

# ================== MAIN ==================

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_user_message))
    app.add_handler(CallbackQueryHandler(handle_decision))

    print("Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
