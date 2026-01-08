import os
import subprocess
from telegram.ext import (
    Application, MessageHandler, CommandHandler,
    filters
)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN belum diset")

USER_STATE = {}  # chat_id → "WAIT_CONFIRM"

async def handle_text(update, context):
    chat_id = update.effective_chat.id
    text = update.message.text.strip().lower()

    # ===== KONFIRMASI =====
    if USER_STATE.get(chat_id) == "WAIT_CONFIRM":
        if text in ("ya", "yes", "ok"):
            await update.message.reply_text("🎬 Rendering dimulai...")
            USER_STATE.pop(chat_id, None)

            try:
                subprocess.run(
                    ["python", "main.py", "render"],
                    capture_output=True,
                    text=True,
                    check=True
                )
            except subprocess.CalledProcessError as e:
                err = e.stderr or e.stdout or "Unknown error"
                await update.message.reply_text("❌ Gagal render:\n" + err[-3000:])
                return

            await update.message.reply_video(
                video=open("output/video.mp4", "rb"),
                caption="✅ Video selesai"
            )
            return

        if text in ("batal", "cancel", "no"):
            USER_STATE.pop(chat_id, None)
            await update.message.reply_text("❌ Proses dibatalkan.")
            return

        await update.message.reply_text("Ketik **YA** untuk lanjut atau **BATAL**.")
        return

    # ===== TAHAP ANALYZE =====
    await update.message.reply_text("🔍 Menganalisis naskah...")

    with open("script.txt", "w", encoding="utf-8") as f:
        f.write(update.message.text)

    try:
        subprocess.run(
            ["python", "main.py", "analyze"],
            capture_output=True,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        err = e.stderr or e.stdout or "Unknown error"
        await update.message.reply_text("❌ Analisis gagal:\n" + err[-3000:])
        return

    # ===== PREVIEW TIMELINE =====
    import json
    timeline = json.load(open("timeline.json"))

    preview = "\n".join(
        f"{i+1}. [{s['emotion']}] {s['text']} ({s['duration']}s)"
        for i, s in enumerate(timeline["scenes"])
    )

    await update.message.reply_text(
        "📝 **Preview Timeline:**\n\n"
        + preview
        + "\n\nKetik **YA** untuk render atau **BATAL**."
    )

    USER_STATE[chat_id] = "WAIT_CONFIRM"

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == "__main__":
    main()
