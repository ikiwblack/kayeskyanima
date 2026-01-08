import os
import subprocess
from telegram.ext import Application, MessageHandler, filters

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN belum diset")

async def handle_text(update, context):
    user_text = update.message.text

    await update.message.reply_text("⏳ Menganalisis naskah...")

    with open("script.txt", "w", encoding="utf-8") as f:
        f.write(user_text)

    try:
        subprocess.run(
            ["python", "main.py"],
            capture_output=True,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr or e.stdout or "Unknown error"

        # Batasi panjang error agar tidak spam Telegram
        error_msg = error_msg[-3500:]

        await update.message.reply_text(
            "❌ Gagal memproses video:\n\n" + error_msg
        )
        return

    await update.message.reply_video(
        video=open("output/video.mp4", "rb"),
        caption="✅ Video berhasil dibuat"
    )

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == "__main__":
    main()
