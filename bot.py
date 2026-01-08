import os
import json
import subprocess

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

# ===== STATE =====
USER_TIMELINE = {}   # chat_id -> timeline dict
USER_STATE = {}      # chat_id -> {"scene": int}

# ===== HELPER =====
async def send_timeline_preview(chat_id, context):
    timeline = USER_TIMELINE[chat_id]

    text = "📝 *Preview Timeline*\n\n"
    for i, s in enumerate(timeline["scenes"]):
        text += f"{i+1}. [{s['emotion']}] {s['text']} ({s['duration']}s)\n"

    keyboard = []
    row = []
    for i in range(len(timeline["scenes"])):
        row.append(
            InlineKeyboardButton(
                f"✏️ Scene {i+1}",
                callback_data=f"scene:{i+1}"
            )
        )
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([
        InlineKeyboardButton("🎬 Render", callback_data="render"),
        InlineKeyboardButton("❌ Batal", callback_data="cancel")
    ])

    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ===== TEXT INPUT (SCRIPT) =====
async def handle_script(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text.strip()

    if not text:
        await update.message.reply_text("❌ Naskah kosong.")
        return

    with open("script.txt", "w", encoding="utf-8") as f:
        f.write(text)

    await update.message.reply_text("🔍 Analisis naskah...")

    try:
        subprocess.run(
            ["python", "main.py", "analyze"],
            check=True,
            capture_output=True,
            text=True
        )
    except subprocess.CalledProcessError as e:
        await update.message.reply_text("❌ Analisis gagal:\n" + e.stderr)
        return

    timeline = json.load(open("timeline.json", encoding="utf-8"))
    USER_TIMELINE[chat_id] = timeline

    await send_timeline_preview(chat_id, context)

# ===== CALLBACK BUTTON =====
async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat.id
    data = query.data
    await query.answer()

    # ===== PILIH SCENE =====
    if data.startswith("scene:"):
        idx = int(data.split(":")[1])
        USER_STATE[chat_id] = {"scene": idx}
        s = USER_TIMELINE[chat_id]["scenes"][idx - 1]

        keyboard = [
            [InlineKeyboardButton("📝 Text", callback_data="edit:text")],
            [InlineKeyboardButton("🎭 Emotion", callback_data="edit:emotion")],
            [InlineKeyboardButton("⏱ Duration", callback_data="edit:duration")],
            [InlineKeyboardButton("⬅️ Kembali", callback_data="back")]
        ]

        await query.edit_message_text(
            f"Edit Scene {idx}:\n\"{s['text']}\"",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # ===== EDIT EMOTION =====
    if data == "edit:emotion":
        keyboard = [
            [
                InlineKeyboardButton("sad", callback_data="emotion:sad"),
                InlineKeyboardButton("happy", callback_data="emotion:happy")
            ],
            [
                InlineKeyboardButton("thinking", callback_data="emotion:thinking"),
                InlineKeyboardButton("neutral", callback_data="emotion:neutral")
            ],
            [InlineKeyboardButton("⬅️ Kembali", callback_data="back")]
        ]
        await query.edit_message_text(
            "Pilih emotion:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if data.startswith("emotion:"):
        emotion = data.split(":")[1]
        idx = USER_STATE[chat_id]["scene"] - 1
        USER_TIMELINE[chat_id]["scenes"][idx]["emotion"] = emotion
        await send_timeline_preview(chat_id, context)
        return

    # ===== EDIT DURATION =====
    if data == "edit:duration":
        keyboard = [
            [
                InlineKeyboardButton("3", callback_data="duration:3"),
                InlineKeyboardButton("4", callback_data="duration:4"),
                InlineKeyboardButton("5", callback_data="duration:5")
            ],
            [
                InlineKeyboardButton("6", callback_data="duration:6"),
                InlineKeyboardButton("7", callback_data="duration:7"),
                InlineKeyboardButton("8", callback_data="duration:8")
            ],
            [InlineKeyboardButton("⬅️ Kembali", callback_data="back")]
        ]
        await query.edit_message_text(
            "Pilih durasi (detik):",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if data.startswith("duration:"):
        dur = int(data.split(":")[1])
        idx = USER_STATE[chat_id]["scene"] - 1
        USER_TIMELINE[chat_id]["scenes"][idx]["duration"] = dur
        await send_timeline_preview(chat_id, context)
        return

    # ===== NAVIGATION =====
    if data == "back":
        await send_timeline_preview(chat_id, context)
        return

    if data == "cancel":
        USER_STATE.pop(chat_id, None)
        USER_TIMELINE.pop(chat_id, None)
        await query.edit_message_text("❌ Dibatalkan.")
        return

    # ===== RENDER =====
    if data == "render":
        json.dump(
            USER_TIMELINE[chat_id],
            open("timeline.json", "w", encoding="utf-8"),
            indent=2,
            ensure_ascii=False
        )

        await query.edit_message_text("🎬 Rendering dimulai...")
        subprocess.run(["python", "main.py", "render"], check=True)

        await context.bot.send_video(
            chat_id=chat_id,
            video=open("output/video.mp4", "rb"),
            caption="✅ Video selesai"
        )

# ===== START BOT =====
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_script))
    app.add_handler(CallbackQueryHandler(on_button))

    app.run_polling()

if __name__ == "__main__":
    main()
