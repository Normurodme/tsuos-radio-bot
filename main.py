import os
import json
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

CHANNEL_USERNAME = "@tsuos_radio"
ADMIN_IDS = [6220077209, 6617998011]

WELCOME_TEXT = "Xush kelibsiz! TSUOS radiosiga xabar jo‘natishingiz mumkin."
SENT_TEXT = "Xabaringiz yuborildi📤."

COUNTER_FILE = "counter.json"

# admin reply uchun: admin_message_id -> user_id
MESSAGE_MAP = {}


# ========= COUNTER =========
def get_next_count():
    if not os.path.exists(COUNTER_FILE):
        data = {"count": 0}
    else:
        with open(COUNTER_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

    data["count"] += 1

    with open(COUNTER_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)

    return data["count"]


# ========= HANDLERS =========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME_TEXT)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user = update.message.from_user
    text = update.message.text

    # ===== ADMIN YOZSA =====
    if user.id in ADMIN_IDS:
        if update.message.reply_to_message:
            replied_id = update.message.reply_to_message.message_id
            if replied_id in MESSAGE_MAP:
                target_user_id = MESSAGE_MAP[replied_id]
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=f"📻 TSUOS Radio javobi:\n\n{text}"
                )
                await update.message.reply_text("✅ Javob foydalanuvchiga yuborildi.")
        return  # admin xabari kanalga ketmaydi

    # ===== FOYDALANUVCHI YOZSA =====
    count = get_next_count()

    # 🔵 KANAL UCHUN:
    # Sarlavha oddiy, xabar BOLD
    channel_text = (
        f"Yangi xabar ({count})\n\n"
        f"*{text}*"
    )

    await context.bot.send_message(
        chat_id=CHANNEL_USERNAME,
        text=channel_text,
        parse_mode="Markdown"
    )

    # 🔐 ADMINLAR UCHUN (kim yuborgani bilan)
    username = f"@{user.username}" if user.username else "yo‘q"
    fullname = f"{user.first_name or ''} {user.last_name or ''}".strip()

    admin_text = (
        f"Yangi xabar ({count})\n\n"
        f"👤 Yuboruvchi: {fullname}\n"
        f"🔗 Username: {username}\n"
        f"🆔 ID: {user.id}\n\n"
        f"📩 Xabar:\n{text}"
    )

    for admin_id in ADMIN_IDS:
        sent = await context.bot.send_message(
            chat_id=admin_id,
            text=admin_text
        )
        MESSAGE_MAP[sent.message_id] = user.id

    await update.message.reply_text(SENT_TEXT)


# ========= RUN =========
def main():
    if not TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN topilmadi")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 TSUOS Radio bot ishga tushdi...")
    app.run_polling()


if __name__ == "__main__":
    main()
