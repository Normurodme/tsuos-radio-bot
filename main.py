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

ADMINS = {
    6220077209,  # super admin (hammasini ko‘radi)
    6617998011,
    6870150995,
}

SUPER_ADMIN = 6220077209

COUNTER_FILE = "counter.json"
PENDING_FILE = "pending.json"

# ================== YORDAMCHI FUNKSIYALAR ==================

def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def next_counter():
    data = load_json(COUNTER_FILE, {"count": 0})
    data["count"] += 1
    save_json(COUNTER_FILE, data)
    return data["count"]

def get_nickname(user):
    if user.first_name:
        return user.first_name
    return "Anonim"

# ================== /start ==================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Xush kelibsiz! TSUOS radiosiga xabar jo‘natishingiz mumkin."
    )

# ================== FOYDALANUVCHI XABARI ==================

async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    counter = next_counter()
    nickname = get_nickname(user)

    pending = load_json(PENDING_FILE, {})

    pending[str(counter)] = {
        "user_id": user.id,
        "username": user.username,
        "nickname": nickname,
        "text": update.message.text,
    }

    save_json(PENDING_FILE, pending)

    # tugmalar
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Tasdiqlash✅️", callback_data=f"approve:{counter}"),
                InlineKeyboardButton("Rad etish🚫", callback_data=f"reject:{counter}"),
            ]
        ]
    )

    # adminlarga yuborish
    for admin_id in ADMINS:
        if admin_id == SUPER_ADMIN:
            text = (
                f"Yangi xabar🔔({counter})\n\n"
                f"👤 Yuboruvchi: {nickname}\n"
                f"🔗 Username: @{user.username}\n"
                f"🆔 ID: {user.id}\n\n"
                f"📩 Xabar:\n"
                f"<b>{update.message.text}</b>"
            )
        else:
            text = (
                f"Yangi xabar🔔({counter})\n\n"
                f"👤 Yuboruvchi: {nickname}\n\n"
                f"📩 Xabar:\n"
                f"<b>{update.message.text}</b>"
            )

        await context.bot.send_message(
            chat_id=admin_id,
            text=text,
            parse_mode="HTML",
            reply_markup=keyboard,
        )

    # ✅ MUHIM: foydalanuvchiga darhol javob
    await update.message.reply_text("Xabar yuborildi📤")

# ================== TASDIQLASH / RAD ETISH ==================

async def handle_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, counter = query.data.split(":")
    admin = query.from_user

    pending = load_json(PENDING_FILE, {})

    if counter not in pending:
        await query.edit_message_text("Bu xabar allaqachon yopilgan.")
        return

    data = pending[counter]
    nickname = data["nickname"]

    if action == "approve":
        text = (
            f"Yangi xabar🔔({counter})\n\n"
            f"👤 Yuboruvchi: {nickname}\n\n"
            f"📩 Xabar:\n"
            f"<b>{data['text']}</b>\n\n"
            f"Tasdiqlandi"
        )
        await context.bot.send_message(
            chat_id=CHANNEL_USERNAME,
            text=text,
            parse_mode="HTML",
        )

        await context.bot.send_message(
            chat_id=data["user_id"],
            text="Tasdiqlandi✅️",
        )

        if admin.id == SUPER_ADMIN:
            footer = f"\n\nTasdiqlandi — by {admin.first_name}"
        else:
            footer = "\n\nTasdiqlandi"

    else:
        await context.bot.send_message(
            chat_id=data["user_id"],
            text="Rad etildi🚫",
        )

        if admin.id == SUPER_ADMIN:
            footer = f"\n\nRad etildi — by {admin.first_name}"
        else:
            footer = "\n\nRad etildi"

    # adminlarda xabarni yopish
    await query.edit_message_text(
        query.message.text + footer,
        parse_mode="HTML",
    )

    del pending[counter]
    save_json(PENDING_FILE, pending)

# ================== MAIN ==================

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_user_message))
    app.add_handler(CallbackQueryHandler(handle_decision))

    app.run_polling()

if __name__ == "__main__":
    main()
