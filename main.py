import os
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

# 🧠 XOTIRA: xabar_id -> user_id
MESSAGE_MAP = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME_TEXT)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    text = update.message.text

    # ===== ADMIN YOZSA =====
    if user.id in ADMIN_IDS:
        # Agar admin reply qilgan bo‘lsa → userga yuboramiz
        if update.message.reply_to_message:
            replied_id = update.message.reply_to_message.message_id
            if replied_id in MESSAGE_MAP:
                target_user_id = MESSAGE_MAP[replied_id]
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=f"📻 TSUOS Radio javobi:\n\n{text}"
                )
                await update.message.reply_text("✅ Javob foydalanuvchiga yuborildi.")
            else:
                await update.message.reply_text("❌ Bu xabarga javob yuborib bo‘lmaydi.")
        else:
            await update.message.reply_text(
                "ℹ️ Foydalanuvchiga javob berish uchun uning xabariga *Reply* qiling.",
                parse_mode="Markdown"
            )
        return  # ❌ admin xabari kanalga ketmaydi

    # ===== FOYDALANUVCHI YOZSA =====
    channel_message = await context.bot.send_message(
        chat_id=CHANNEL_USERNAME,
        text=f"🆕 Yangi xabar\n\n{text}"
    )

    # Xabarni adminlarga yuboramiz (reply qilish uchun)
    for admin_id in ADMIN_IDS:
        sent = await context.bot.send_message(
            chat_id=admin_id,
            text=f"📩 Yangi xabar\n\n{text}"
        )
        # adminlardagi message_id ni user bilan bog‘laymiz
        MESSAGE_MAP[sent.message_id] = user.id

    await update.message.reply_text(SENT_TEXT)


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
