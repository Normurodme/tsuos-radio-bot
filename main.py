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

# ========= SOZLAMALAR =========
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

CHANNEL_USERNAME = "@tsuos_radio"
ADMIN_IDS = [6220077209, 6617998011]

WELCOME_TEXT = "Xush kelibsiz! TSUOS radiosiga xabar jo‘natishingiz mumkin."
SENT_TEXT = "Xabaringiz yuborildi📤."

COUNTER_FILE = "counter.json"
BANNED_FILE = "banned.json"

# admin reply: admin_message_id -> user_id
MESSAGE_MAP = {}


# ========= JSON YORDAMCHI =========
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


# ========= COUNTER =========
def get_next_count():
    data = load_json(COUNTER_FILE, {"count": 0})
    data["count"] += 1
    save_json(COUNTER_FILE, data)
    return data["count"]


# ========= BAN / UNBAN =========
def is_banned(user_id: int) -> bool:
    banned = load_json(BANNED_FILE, [])
    return user_id in banned


def ban_user(user_id: int):
    banned = load_json(BANNED_FILE, [])
    if user_id not in banned:
        banned.append(user_id)
        save_json(BANNED_FILE, banned)


def unban_user(user_id: int):
    banned = load_json(BANNED_FILE, [])
    if user_id in banned:
        banned.remove(user_id)
        save_json(BANNED_FILE, banned)


# ========= COMMANDS =========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME_TEXT)


async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id not in ADMIN_IDS:
        return

    if update.message.reply_to_message:
        target_id = MESSAGE_MAP.get(update.message.reply_to_message.message_id)
        if target_id:
            ban_user(target_id)
            await update.message.reply_text("🚫 Foydalanuvchi ban qilindi.")
        else:
            await update.message.reply_text("❌ User topilmadi.")
        return

    if context.args:
        try:
            ban_user(int(context.args[0]))
            await update.message.reply_text("🚫 Foydalanuvchi ban qilindi.")
        except:
            await update.message.reply_text("❌ Noto‘g‘ri ID.")


async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id not in ADMIN_IDS:
        return

    if update.message.reply_to_message:
        target_id = MESSAGE_MAP.get(update.message.reply_to_message.message_id)
        if target_id:
            unban_user(target_id)
            await update.message.reply_text("✅ Foydalanuvchi unban qilindi.")
        else:
            await update.message.reply_text("❌ User topilmadi.")
        return

    if context.args:
        try:
            unban_user(int(context.args[0]))
            await update.message.reply_text("✅ Foydalanuvchi unban qilindi.")
        except:
            await update.message.reply_text("❌ Noto‘g‘ri ID.")


# ========= MESSAGE =========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user = update.message.from_user

    # BAN tekshirish
    if is_banned(user.id):
        return

    # ========= ADMIN =========
    if user.id in ADMIN_IDS:
        if update.message.reply_to_message:
            replied_id = update.message.reply_to_message.message_id
            if replied_id in MESSAGE_MAP:
                target_user_id = MESSAGE_MAP[replied_id]
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=f"📻 TSUOS Radio javobi:\n\n{update.message.text}"
                )
                await update.message.reply_text("✅ Javob yuborildi.")
        return  # admin yozuvi kanalga ketmaydi

    # ========= FOYDALANUVCHI =========
    count = get_next_count()
    header = f"Yangi xabar🔔({count})"

    # 🔹 MATN
    if update.message.text:
        await context.bot.send_message(
            chat_id=CHANNEL_USERNAME,
            text=f"{header}\n\n*{update.message.text}*",
            parse_mode="Markdown"
        )

    # 🔹 RASM
    elif update.message.photo:
        await context.bot.send_photo(
            chat_id=CHANNEL_USERNAME,
            photo=update.message.photo[-1].file_id,
            caption=header
        )

    # 🔹 VIDEO
    elif update.message.video:
        await context.bot.send_video(
            chat_id=CHANNEL_USERNAME,
            video=update.message.video.file_id,
            caption=header
        )

    # 🔹 OVOZLI
    elif update.message.voice:
        await context.bot.send_voice(
            chat_id=CHANNEL_USERNAME,
            voice=update.message.voice.file_id,
            caption=header
        )

    else:
        return

    # ADMINLARGA YUBORISH
    username = f"@{user.username}" if user.username else "(username yo‘q)"
    admin_text = (
        f"{header}\n\n"
        f"👤 Yuboruvchi: {username}\n"
        f"🆔 ID: {user.id}\n\n"
        f"📩 Xabar:\n{update.message.text or '[Media]'}"
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
    app.add_handler(CommandHandler("ban", ban_command))
    app.add_handler(CommandHandler("unban", unban_command))
    app.add_handler(
        MessageHandler(
            filters.TEXT | filters.PHOTO | filters.VIDEO | filters.VOICE,
            handle_message
        )
    )

    print("🤖 TSUOS Radio bot ishga tushdi...")
    app.run_polling()


if __name__ == "__main__":
    main()
