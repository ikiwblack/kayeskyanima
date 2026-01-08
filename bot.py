import os
import subprocess
from telegram.ext import Application, MessageHandler, filters

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

async def handle_text(update, context):
    text = update.message.text

    await update.message.reply_text("⏳ Memproses naskah...")

    # Simpan naskah
    with open("script.txt", "w", encoding="utf-8") as f:
        f.write(text)

    # Jalankan pipeline utama
    subprocess.run(["python", "main.py"], check=True)

    # Kirim video
    await update.message.reply_video(
        video=open("output/video.mp4", "rb"),
        caption="✅ Video selesai"
    )

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == "__main__":
    main()
