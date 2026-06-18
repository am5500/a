import logging
import os

from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from handlers.callback_handler import handle_callback
from handlers.file_handler import handle_file
from handlers.start_handler import handle_start

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

BOT_TOKEN = os.getenv("BOT_TOKEN", "8861695419:AAFMWZ2_jpsjwkbJccl-WdEQt0dWgCHf5Lo")


def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN غير موجود. حدّده في ملف .env")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.add_handler(CallbackQueryHandler(handle_callback))

    print("✅ البوت شغال... (Ctrl+C للإيقاف)")
    app.run_polling()


if __name__ == "__main__":
    main()
