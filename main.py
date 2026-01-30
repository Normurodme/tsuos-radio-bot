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

COUNTER_FILE = "counter.json"
BANNED_FILE = "banned.json"

# pending_id -> {payload, admin_messages, texts}
PENDING = {}

# admin_message_id -> user_id
MESSAGE_MAP = {}

# ========= JSON =========
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
def is_banned(user_id):
    banned = load_json(BANNED_FILE, [])
    return user_id in banned

def ban_user(user_id):
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
        target = MESSAGE_MAP.get(update.message.reply_to_message.message_id)
        if target:
            ban_user(target)
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
            mid = update.message.reply_to_message.message_id
            if mid in MESSAGE_MAP:
                await context.bot.send_message(
                    chat_id=MESSAGE_MAP[mid],
                    text=f"📻 TSUOS Radio javobi:\n\n{update.message.text}"
                )
                await update.message.reply_text("✅ Javob yuborildi.")
        return

    # ===== USER CONFIRM =====
    await update.message.reply_text("Xabar jo'natildi📤")

    count = get_next_count()
    header = f"Yangi xabar🔔({count})"

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Tasdiqlash✅️", callback_data=f"approve:{count}"),
            InlineKeyboardButton("Rad etish🚫", callback_data=f"reject:{count}")
        ]
    ])

    nickname = user.first_name or "Anonim"
    username = f"@{user.username}" if user.username else "(username yo‘q)"

    admin_text_simple = (
        f"{header}\n\n"
        f"👤 Yuboruvchi: {nickname}\n\n"
        f"📩 Xabar:\n{update.message.text}"
    )

    admin_text_full = (
        f"{header}\n\n"
        f"👤 Yuboruvchi: {nickname}\n"
        f"🔗 Username: {username}\n"
        f"🆔 ID: {user.id}\n\n"
        f"📩 Xabar:\n{update.message.text}"
    )

    PENDING[count] = {
        "payload": {
            "user_id": user.id,
            "text": update.message.text,
            "header": header
        },
        "admin_messages": {},
        "texts": {
            "simple": admin_text_simple,
            "full": admin_text_full
        }
    }

    for admin_id in ADMIN_IDS:
        text = admin_text_full if admin_id == OWNER_ID else admin_text_simple
        sent = await context.bot.send_message(
            chat_id=admin_id,
            text=text,
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

    action, cid = query.data.split(":")
    cid = int(cid)

    if cid not in PENDING:
        return

    entry = PENDING[cid]  # ❗️ POP EMAS
    payload = entry["payload"]
    admin_msgs = entry["admin_messages"]
    texts = entry["texts"]

    # USER NOTIFY
    if action == "approve":
        await context.bot.send_message(payload["user_id"], "Tasdiqlandi✅️")
    else:
        await context.bot.send_message(payload["user_id"], "Rad etildi🚫")

    # CHANNEL (YUBORUVCHISIZ)
    if action == "approve":
        await context.bot.send_message(
            chat_id=CHANNEL_USERNAME,
            text=f"{payload['header']}\n\n📩 Xabar:\n*{payload['text']}*",
            parse_mode="Markdown"
        )

    # STATUS + BUTTON REMOVE (HAMMA ADMINGA, O‘ZI BOSHGANGA HAM)
    for aid, mid in admin_msgs.items():
        base = texts["full"] if aid == OWNER_ID else texts["simple"]

        if action == "approve":
            status = "\n\nTasdiqlandi✅️"
        else:
            status = "\n\nRad etildi🚫"

        if aid == OWNER_ID:
            status += f" — by {query.from_user.first_name}"

        try:
            await context.bot.edit_message_text(
                chat_id=aid,
                message_id=mid,
                text=base + status
            )
            await context.bot.edit_message_reply_markup(
                chat_id=aid,
                message_id=mid,
                reply_markup=None
            )
        except:
            pass

    # ❗️ ENDI O‘CHIRILADI
    PENDING.pop(cid)

# ========= RUN =========
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ban", ban_command))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    print("🤖 TSUOS Radio bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
