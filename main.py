import json
import os
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# ===== ADMINLAR =====
SUPER_ADMIN = 6220077209
ADMINS = {
    6220077209,
    6617998011,
    6870150995
}

# ===== KANAL =====
CHANNEL_ID = -100XXXXXXXXXX  # ⚠️ o‘zingniki bilan almashtir

# ===== FILES =====
COUNTER_FILE = "counter.json"
BAN_FILE = "banned.json"

pending_messages = {}

# ================== UTILS ==================

def load_json(file, default):
    if not os.path.exists(file):
        return default
    with open(file, "r") as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f)

def next_counter():
    data = load_json(COUNTER_FILE, {"count": 0})
    data["count"] += 1
    save_json(COUNTER_FILE, data)
    return data["count"]

def is_banned(user_id):
    banned = load_json(BAN_FILE, [])
    return user_id in banned

# ================== START ==================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Xush kelibsiz! TSUOS radiosiga xabar jo‘natishingiz mumkin."
    )

# ================== USER MESSAGE ==================

async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user

    if is_banned(user.id):
        return

    # 🔴 MUHIM: HAR DOIM JAVOB
    await update.message.reply_text("Xabar yuborildi📤")

    counter = next_counter()

    username = user.username or "Anonymous"
    nickname = user.first_name or "Anonymous"

    base_text = (
        f"Yangi xabar🔔({counter})\n\n"
        f"👤 Yuboruvchi: {nickname}\n\n"
        f"📩 Xabar:\n"
    )

    admin_extra = (
        f"\n\n🔎 Maxfiy:\n"
        f"@{username}\n"
        f"🆔 ID: {user.id}"
    )

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Tasdiqlash✅", callback_data=f"approve:{counter}"),
            InlineKeyboardButton("Rad etish🚫", callback_data=f"reject:{counter}")
        ]
    ])

    for admin in ADMINS:
        text = base_text
        if admin == SUPER_ADMIN:
            text += admin_extra

        sent = None

        if update.message.text:
            sent = await context.bot.send_message(
                chat_id=admin,
                text=text + f"\n\n<b>{update.message.text}</b>",
                parse_mode="HTML",
                reply_markup=buttons
            )

        elif update.message.photo:
            sent = await context.bot.send_photo(
                chat_id=admin,
                photo=update.message.photo[-1].file_id,
                caption=text,
                reply_markup=buttons
            )

        elif update.message.video:
            sent = await context.bot.send_video(
                chat_id=admin,
                video=update.message.video.file_id,
                caption=text,
                reply_markup=buttons
            )

        elif update.message.voice:
            sent = await context.bot.send_voice(
                chat_id=admin,
                voice=update.message.voice.file_id,
                caption=text,
                reply_markup=buttons
            )

        if sent:
            pending_messages[counter] = {
                "user_id": user.id,
                "user_chat": update.message.chat_id,
                "admin_msgs": pending_messages.get(counter, {}).get("admin_msgs", []) + [(admin, sent.message_id)],
                "status": "pending"
            }

# ================== CALLBACK ==================

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, num = query.data.split(":")
    num = int(num)

    if num not in pending_messages:
        await query.edit_message_text("❌ Bu xabar yopilgan")
        return

    data = pending_messages[num]
    if data["status"] != "pending":
        return

    admin = query.from_user

    if admin.id not in ADMINS:
        return

    if action == "approve":
        data["status"] = "approved"
        status_text = "Tasdiqlandi✅"
    else:
        data["status"] = "rejected"
        status_text = "Rad etildi🚫"

    # Foydalanuvchiga xabar
    await context.bot.send_message(
        chat_id=data["user_chat"],
        text=status_text
    )

    # Kanalga chiqarish (faqat tasdiqlansa)
    if action == "approve":
        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=(
                f"Yangi xabar🔔({num})\n\n"
                f"📩 Xabar:\n"
                f"<b>{query.message.text.split('📩 Xabar:')[-1].strip()}</b>"
            ),
            parse_mode="HTML"
        )

    # Admin xabarlarini yangilash
    for admin_id, msg_id in data["admin_msgs"]:
        text = status_text
        if admin_id == SUPER_ADMIN:
            text += f" — by {admin.first_name}"

        await context.bot.edit_message_reply_markup(
            chat_id=admin_id,
            message_id=msg_id,
            reply_markup=None
        )
        await context.bot.send_message(
            chat_id=admin_id,
            text=text
        )

# ================== BAN ==================

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id not in ADMINS:
        return

    if not update.message.reply_to_message:
        return

    target = update.message.reply_to_message.from_user.id
    banned = load_json(BAN_FILE, [])
    if target not in banned:
        banned.append(target)
        save_json(BAN_FILE, banned)

    await update.message.reply_text("🚫 Foydalanuvchi ban qilindi")

# ================== MAIN ==================

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_user_message))

    app.run_polling()

if __name__ == "__main__":
    main()
