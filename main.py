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

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

CHANNEL_USERNAME = "@tsuos_radio"

ADMINS = {6220077209, 6617998011, 6870150995}
SUPER_ADMIN = 6220077209

COUNTER_FILE = "counter.json"
PENDING_FILE = "pending.json"


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
    return user.first_name or "Anonim"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Xush kelibsiz! TSUOS radiosiga xabar jo‘natishingiz mumkin."
    )


# ================= USER MESSAGE =================

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

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Tasdiqlash✅️", callback_data=f"approve:{counter}"),
            InlineKeyboardButton("Rad etish🚫", callback_data=f"reject:{counter}"),
        ]
    ])

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

    # 🔥 MUHIM QATOR (SEN AYTGANI)
    await update.message.reply_text("Xabar yuborildi📤")


# ================= APPROVE / REJECT =================

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

    if action == "approve":
        await context.bot.send_message(
            chat_id=CHANNEL_USERNAME,
            text=(
                f"Yangi xabar🔔({counter})\n\n"
                f"👤 Yuboruvchi: {data['nickname']}\n\n"
                f"📩 Xabar:\n"
                f"<b>{data['text']}</b>\n\n"
                f"Tasdiqlandi"
            ),
            parse_mode="HTML",
        )
        await context.bot.send_message(data["user_id"], "Tasdiqlandi✅️")
        footer = "Tasdiqlandi"

    else:
        await context.bot.send_message(data["user_id"], "Rad etildi🚫")
        footer = "Rad etildi"

    if admin.id == SUPER_ADMIN:
        footer += f" — by {admin.first_name}"

    await query.edit_message_text(
        query.message.text + f"\n\n{footer}",
        parse_mode="HTML",
    )

    del pending[counter]
    save_json(PENDING_FILE, pending)


def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_user_message))
    app.add_handler(CallbackQueryHandler(handle_decision))
    app.run_polling()


if __name__ == "__main__":
    main()
