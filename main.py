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

OWNER_ID = 6220077209
ADMIN_IDS = [6220077209, 6617998011, 6870150995]

WELCOME_TEXT = "Xush kelibsiz! TSUOS radiosiga xabar jo‘natishingiz mumkin."
WAIT_TEXT = "⏳ Xabaringiz moderator tomonidan tekshirilmoqda."

COUNTER_FILE = "counter.json"
BANNED_FILE = "banned.json"

# pending_id -> {payload, admin_messages}
PENDING = {}

# admin_message_id -> user_id (reply uchun)
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

# ========= MESSAGE =========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user = update.message.from_user

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
    # 1️⃣ HAR DOIM JAVOB
    await update.message.reply_text("Xabar jo'natildi📤")

    count = get_next_count()
    header = f"Yangi xabar🔔({count})"

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Tasdiqlash✅️", callback_data=f"approve:{count}"),
            InlineKeyboardButton("Rad etish🚫", callback_data=f"reject:{count}"),
        ]
    ])

    payload = {
        "user_id": user.id,
        "nickname": user.first_name or "Anonim",
        "username": f"@{user.username}" if user.username else "(username yo‘q)",
        "text": update.message.text,
        "photo": update.message.photo[-1].file_id if update.message.photo else None,
        "video": update.message.video.file_id if update.message.video else None,
        "voice": update.message.voice.file_id if update.message.voice else None,
        "header": header,
    }

    PENDING[count] = {
        "payload": payload,
        "admin_messages": {}
    }

    # 4️⃣ ADMIN FORMAT
    admin_text_simple = (
        f"{header}\n\n"
        f"👤 Yuboruvchi: {payload['nickname']}\n\n"
        f"📩 Xabar:\n{update.message.text or '[Media]'}"
    )

    admin_text_full = (
        f"{header}\n\n"
        f"👤 Yuboruvchi: {payload['nickname']}\n"
        f"🔗 Username: {payload['username']}\n"
        f"🆔 ID: {user.id}\n\n"
        f"📩 Xabar:\n{update.message.text or '[Media]'}"
    )

    for admin_id in ADMIN_IDS:
        text_to_send = admin_text_full if admin_id == OWNER_ID else admin_text_simple

        sent = await context.bot.send_message(
            chat_id=admin_id,
            text=text_to_send,
            reply_markup=keyboard
        )

        PENDING[count]["admin_messages"][admin_id] = sent.message_id
        MESSAGE_MAP[sent.message_id] = user.id

# ========= BUTTONS =========
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    admin_id = query.from_user.id
    if admin_id not in ADMIN_IDS:
        return

    action, msg_id = query.data.split(":")
    msg_id = int(msg_id)

    if msg_id not in PENDING:
        await query.edit_message_text("❌ Bu xabar yopilgan.")
        return

    entry = PENDING.pop(msg_id)
    data = entry["payload"]
    admin_msgs = entry["admin_messages"]

    # 2️⃣ USERGA NATIJA
    if action == "approve":
        await context.bot.send_message(data["user_id"], "Tasdiqlandi✅️")
    else:
        await context.bot.send_message(data["user_id"], "Rad etildi🚫")

    # 🔥 TASDIQLANGANDA KANALGA YUBORISH
    if action == "approve":
        if data["text"]:
            await context.bot.send_message(
                chat_id=CHANNEL_USERNAME,
                text=(
                    f"{data['header']}\n\n"
                    f"👤 Yuboruvchi: {data['nickname']}\n\n"
                    f"📩 Xabar:\n"
                    f"*{data['text']}*"
                ),
                parse_mode="Markdown"
            )
        elif data["photo"]:
            await context.bot.send_photo(
                chat_id=CHANNEL_USERNAME,
                photo=data["photo"],
                caption=f"{data['header']}\n\n👤 Yuboruvchi: {data['nickname']}"
            )
        elif data["video"]:
            await context.bot.send_video(
                chat_id=CHANNEL_USERNAME,
                video=data["video"],
                caption=f"{data['header']}\n\n👤 Yuboruvchi: {data['nickname']}"
            )
        elif data["voice"]:
            await context.bot.send_voice(
                chat_id=CHANNEL_USERNAME,
                voice=data["voice"]
            )

    # 3️⃣ STATUSNI PASTIGA QO‘SHISH
    if action == "approve":
        status_owner = f"\n\nTasdiqlandi✅️ — by {query.from_user.first_name}"
        status_other = "\n\nTasdiqlandi✅️"
    else:
        status_owner = f"\n\nRad etildi🚫 — by {query.from_user.first_name}"
        status_other = "\n\nRad etildi🚫"

    for aid, mid in admin_msgs.items():
        try:
            old_text = query.message.text
            await context.bot.edit_message_text(
                chat_id=aid,
                message_id=mid,
                text=old_text + (status_owner if aid == OWNER_ID else status_other)
            )
            await context.bot.edit_message_reply_markup(
                chat_id=aid,
                message_id=mid,
                reply_markup=None
            )
        except:
            pass

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
