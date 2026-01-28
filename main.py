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
CHANNEL_ID = -1001234567890  # ❗️KANAL ID (REAL RAQAM)

ADMINS = [
    6220077209,  # super admin (kim tasdiqlaganini ko‘radi)
    6617998011,
    6870150995,
]

SUPER_ADMIN = 6220077209

COUNTER_FILE = "counter.json"
PENDING_FILE = "pending.json"

# ========= YORDAMCHI =========
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

# ========= START =========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Xush kelibsiz! TSUOS radiosiga xabar jo‘natishingiz mumkin."
    )

# ========= FOYDALANUVCHI XABARI =========
async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    msg = update.message

    num = next_counter()

    pending = load_json(PENDING_FILE, {})
    pending[str(num)] = {
        "user_id": user.id,
        "username": user.username,
        "nickname": user.first_name,
        "type": msg.effective_attachment.__class__.__name__ if msg.effective_attachment else "text",
        "text": msg.text or msg.caption,
        "file_id": (
            msg.photo[-1].file_id if msg.photo else
            msg.video.file_id if msg.video else
            msg.voice.file_id if msg.voice else
            None
        )
    }
    save_json(PENDING_FILE, pending)

    # FOYDALANUVCHIGA DARHOL JAVOB
    await msg.reply_text("Xabar yuborildi📤")

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Tasdiqlash✅️", callback_data=f"approve:{num}"),
            InlineKeyboardButton("Rad etish🚫", callback_data=f"reject:{num}")
        ]
    ])

    for admin_id in ADMINS:
        text = (
            f"Yangi xabar🔔({num})\n\n"
            f"👤 Yuboruvchi: Nickname\n"
        )

        if admin_id == SUPER_ADMIN:
            text += (
                f"🔗 Username: @{user.username}\n"
                f"🆔 ID: {user.id}\n\n"
            )
        else:
            text += "\n"

        text += f"📩 Xabar:\n<b>{msg.text or msg.caption or 'Media'}</b>"

        if msg.text:
            await context.bot.send_message(
                chat_id=admin_id,
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        elif msg.photo:
            await context.bot.send_photo(
                chat_id=admin_id,
                photo=msg.photo[-1].file_id,
                caption=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        elif msg.video:
            await context.bot.send_video(
                chat_id=admin_id,
                video=msg.video.file_id,
                caption=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        elif msg.voice:
            await context.bot.send_voice(
                chat_id=admin_id,
                voice=msg.voice.file_id,
                caption=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )

# ========= TASDIQLASH / RAD =========
async def handle_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, num = query.data.split(":")
    pending = load_json(PENDING_FILE, {})

    if num not in pending:
        await query.edit_message_text("Bu xabar yopilgan.")
        return

    data = pending[num]
    admin = query.from_user

    # FOYDALANUVCHIGA NATIJA
    if action == "approve":
        await context.bot.send_message(
            chat_id=data["user_id"],
            text="Tasdiqlandi✅️"
        )

        # KANALGA FAQAT XABAR
        if data["type"] == "text":
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=f"Yangi xabar🔔({num})\n\n📩 Xabar:\n<b>{data['text']}</b>",
                parse_mode="HTML"
            )
        elif data["type"] == "PhotoSize":
            await context.bot.send_photo(
                chat_id=CHANNEL_ID,
                photo=data["file_id"],
                caption=f"Yangi xabar🔔({num})\n\n📩 Xabar:\n<b>{data['text']}</b>",
                parse_mode="HTML"
            )
        elif data["type"] == "Video":
            await context.bot.send_video(
                chat_id=CHANNEL_ID,
                video=data["file_id"],
                caption=f"Yangi xabar🔔({num})\n\n📩 Xabar:\n<b>{data['text']}</b>",
                parse_mode="HTML"
            )
        elif data["type"] == "Voice":
            await context.bot.send_voice(
                chat_id=CHANNEL_ID,
                voice=data["file_id"]
            )

        status = "Tasdiqlandi✅️"

    else:
        await context.bot.send_message(
            chat_id=data["user_id"],
            text="Rad etildi🚫"
        )
        status = "Rad etildi🚫"

    # ADMINLAR UCHUN YOPISH
    for admin_id in ADMINS:
        if admin_id == SUPER_ADMIN:
            await context.bot.send_message(
                chat_id=admin_id,
                text=f"{status} — by {admin.first_name}"
            )
        else:
            await context.bot.send_message(
                chat_id=admin_id,
                text=status
            )

    del pending[num]
    save_json(PENDING_FILE, pending)

# ========= MAIN =========
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_decision))
    app.add_handler(MessageHandler(
        filters.TEXT | filters.PHOTO | filters.VIDEO | filters.VOICE,
        handle_user_message
    ))

    app.run_polling()

if __name__ == "__main__":
    main()
