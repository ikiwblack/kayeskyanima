import os
import json
import subprocess
from telegram.ext import (
    Application, MessageHandler, CommandHandler, filters
)
from scripts.edit_timeline import edit_scene

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

USER_TIMELINE = {}

async def handle_text(update, context):
    chat_id = update.effective_chat.id
    text = update.message.text

    with open("script.txt", "w", encoding="utf-8") as f:
        f.write(text)

    await update.message.reply_text("🔍 Analisis naskah...")

    try:
        subprocess.run(["python", "main.py", "analyze"],
                       capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        await update.message.reply_text("❌ Analisis gagal:\n" + e.stderr)
        return

    timeline = json.load(open("timeline.json"))
    USER_TIMELINE[chat_id] = timeline

    preview = "\n".join(
        f"{i+1}. [{s['emotion']}] {s['text']} ({s['duration']}s)"
        for i, s in enumerate(timeline["scenes"])
    )

    await update.message.reply_text(
        "📝 PREVIEW TIMELINE:\n\n"
        + preview +
        "\n\nGunakan /edit, /scenes, lalu /render"
    )

async def scenes(update, context):
    t = USER_TIMELINE.get(update.effective_chat.id)
    if not t:
        await update.message.reply_text("Belum ada timeline.")
        return

    msg = "\n".join(
        f"{i+1}. [{s['emotion']}] {s['text']} ({s['duration']}s)"
        for i, s in enumerate(t["scenes"])
    )
    await update.message.reply_text(msg)

async def edit(update, context):
    try:
        idx = int(context.args[0])
        field = context.args[1]
        value = " ".join(context.args[2:])
        USER_TIMELINE[update.effective_chat.id] = edit_scene(
            USER_TIMELINE[update.effective_chat.id], idx, field, value
        )
        await update.message.reply_text("✅ Scene diperbarui")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def render(update, context):
    t = USER_TIMELINE.get(update.effective_chat.id)
    if not t:
        await update.message.reply_text("Tidak ada timeline.")
        return

    json.dump(t, open("timeline.json", "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)

    await update.message.reply_text("🎬 Rendering dimulai...")
    subprocess.run(["python", "main.py", "render"], check=True)

    await update.message.reply_video(
        video=open("output/video.mp4", "rb"),
        caption="✅ Video selesai"
    )

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("scenes", scenes))
    app.add_handler(CommandHandler("edit", edit))
    app.add_handler(CommandHandler("render", render))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == "__main__":
    main()
