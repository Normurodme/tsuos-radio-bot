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

# ========= SOZLAMALAR =========
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

CHANNEL_USERNAME = "@tsuos_radio"
ADMIN_IDS = [6220077209, 6617998011]

WELCOME_TEXT = "Xush kelibsiz! TSUOS radiosiga xabar jo‘natishingiz mumkin."
WAIT_TEXT = "⏳ Xabaringiz moderator tomonidan tekshirilmoqda."
SENT_TEXT = "Xabaringiz yuborildi📤."

COUNTER_FILE = "counter.json"
BANNED_FILE = "banned.json"

# pending_id -> data
PENDING = {}
# admin_message_id -> user_id (reply uchun)
MESSAGE_MAP = {}

# ========= YORDAMCHI =========
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

# ========= BAN =========
def is_banned(user_id: int) -> bool:
    banned = load_json(BANNED_FILE, [])
    return user_id in banned

def ban_user(user_id: int):
    banned = load_json(BANNED_FILE, [])
    if user_id not in banned:
        banned.append(user_id)
        save_json(BANNED_FILE, banned)

# ========= COMMANDS =========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME_TEXT)

async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id not in ADMIN_IDS:
        return

    # reply orqali
    if update.message.reply_to_message:
        target_id = MESSAGE_MAP.get(update.message.reply_to_message.message_id)
        if target_id:
            ban_user(target_id)
            await update.message.reply_text("🚫 Foydalanuvchi ban qilindi.")
        else:
            await update.message.reply_text("❌ User topilmadi.")
        return

    # ID orqali
    if context.args:
        try:
            ban_user(int(context.args[0]))
            await update.message.reply_text("🚫 Foydalanuvchi ban qilindi.")
        except:
            await update.message.reply_text("❌ Noto‘g‘ri ID.")

# ========= MESSAGE =========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user = update.message.from_user

    # BAN
    if is_banned(user.id):
        return

    # ===== ADMIN REPLY =====
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
        return

    # ===== FOYDALANUVCHI =====
    count = get_next_count()
    header = f"Yangi xabar🔔({count})"

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Tasdiqlash✅️", callback_data=f"approve:{count}"),
            InlineKeyboardButton("Rad etish🚫", callback_data=f"reject:{count}"),
        ]
    ])

    PENDING[count] = {
        "user_id": user.id,
        "username": f"@{user.username}" if user.username else "(username yo‘q)",
        "text": update.message.text,
        "photo": update.message.photo[-1].file_id if update.message.photo else None,
        "video": update.message.video.file_id if update.message.video else None,
        "voice": update.message.voice.file_id if update.message.voice else None,
        "header": header,
    }

    admin_text = (
        f"{header}\n\n"
        f"👤 Yuboruvchi: {PENDING[count]['username']}\n"
        f"🆔 ID: {user.id}\n\n"
        f"📩 Xabar:\n{update.message.text or '[Media]'}"
    )

    for admin_id in ADMIN_IDS:
        sent = await context.bot.send_message(
            chat_id=admin_id,
            text=admin_text,
            reply_markup=keyboard
        )
        MESSAGE_MAP[sent.message_id] = user.id

    await update.message.reply_text(WAIT_TEXT)

# ========= BUTTONS =========
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id not in ADMIN_IDS:
        return

    action, msg_id = query.data.split(":")
    msg_id = int(msg_id)

    if msg_id not in PENDING:
        await query.edit_message_text("❌ Bu xabar yopilgan.")
        return

    data = PENDING.pop(msg_id)

    if action == "approve":
        if data["text"]:
            await context.bot.send_message(
                chat_id=CHANNEL_USERNAME,
                text=f"{data['header']}\n\n*{data['text']}*",
                parse_mode="Markdown"
            )
        elif data["photo"]:
            await context.bot.send_photo(CHANNEL_USERNAME, data["photo"], caption=data["header"])
        elif data["video"]:
            await context.bot.send_video(CHANNEL_USERNAME, data["video"], caption=data["header"])
        elif data["voice"]:
            await context.bot.send_voice(CHANNEL_USERNAME, data["voice"], caption=data["header"])

        await query.edit_message_text("✅ Kanalga joylandi.")

    elif action == "reject":
        await query.edit_message_text("🚫 Xabar rad etildi.")

# ========= RUN =========
def main():
    if not TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN topilmadi")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ban", ban_command))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_buttons))

    print("🤖 TSUOS Radio bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
