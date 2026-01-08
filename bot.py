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

# Import the analyze function directly
from scripts.analyze_text import analyze

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

# ===== STATE =====
USER_STATE = {}

# ===== CHARACTERS & VOICE MAPPING =====
CHARACTERS = ["Pria", "Wanita", "Kakek", "Nenek", "Anak Pria", "Anak Wanita"]
VOICE_MAP = {
    "Pria": "id-ID-Standard-B",
    "Wanita": "id-ID-Standard-A",
    "Kakek": "id-ID-Wavenet-B",
    "Nenek": "id-ID-Wavenet-A",
    "Anak Pria": "id-ID-Standard-C",
    "Anak Wanita": "id-ID-Standard-D",
}
# ==================================

# ===== HELPER =====
async def send_timeline_preview(chat_id, context):
    state = USER_STATE.get(chat_id, {})
    timeline = state.get("timeline")
    if not timeline:
        return

    text = "📝 *Preview Timeline*\n\n"
    for i, s in enumerate(timeline["scenes"]):
        char_id = s['speaker']
        char_type = next((c['type'] for c in timeline['characters'] if c['id'] == char_id), 'Unknown')
        text += f"{i+1}. ({char_type}) [{s['emotion']}] {s['text']} ({s['duration']}s)\n"

    keyboard = []
    scene_buttons = [InlineKeyboardButton(f"✏️ Scene {i+1}", callback_data=f"scene:{i+1}") for i in range(len(timeline["scenes"]))]
    for i in range(0, len(scene_buttons), 2):
        keyboard.append(scene_buttons[i:i+2])

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

async def ask_for_character_type(chat_id, context, char_index, is_edit=False):
    char_name = chr(ord('A') + char_index)
    text = f"Pilih karakter untuk *Pembicara {char_name}*:"
    keyboard = [[InlineKeyboardButton(c, callback_data=f"select_char:{c}")] for c in CHARACTERS]
    
    if is_edit:
        await context.bot.edit_message_text(chat_id=chat_id, message_id=context.message_id, text=text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

# ===== TEXT INPUT (SCRIPT) =====
async def handle_script(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text.strip()
    if not text:
        await update.message.reply_text("❌ Naskah kosong.")
        return

    USER_STATE[chat_id] = {"script": text, "step": "char_count", "chars": []}

    keyboard = [[
        InlineKeyboardButton("1", callback_data="count_char:1"),
        InlineKeyboardButton("2", callback_data="count_char:2"),
        InlineKeyboardButton("3", callback_data="count_char:3"),
    ]]
    await update.message.reply_text(
        "Berapa banyak karakter dalam naskah ini?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ===== CALLBACK BUTTON =====
async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    chat_id = query.message.chat.id
    message_id = query.message.message_id
    data = query.data
    
    state = USER_STATE.get(chat_id)
    if not state:
        await query.edit_message_text("❌ Sesi tidak ditemukan. Silakan kirim ulang naskah Anda.")
        return

    step = state.get("step")

    if data.startswith("count_char:"):
        if step != "char_count": return
        
        count = int(data.split(":")[1])
        state["char_count"] = count
        state["step"] = "select_char"
        await ask_for_character_type(chat_id, query.message, char_index=0, is_edit=True)

    elif data.startswith("select_char:"):
        if step != "select_char": return

        char_type = data.split(":")[1]
        state["chars"].append(char_type)
        
        next_char_index = len(state["chars"])
        if next_char_index < state["char_count"]:
            await ask_for_character_type(chat_id, query.message, char_index=next_char_index, is_edit=True)
        else:
            state["step"] = "select_orientation"
            keyboard = [[
                InlineKeyboardButton("Portrait (9:16)", callback_data="orientation:9:16"),
                InlineKeyboardButton("Landscape (16:9)", callback_data="orientation:16:9"),
            ]]
            await query.edit_message_text(
                "Pilih orientasi video:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    elif data.startswith("orientation:"):
        if step != "select_orientation": return

        orientation = data.split(":")[1]
        state["orientation"] = orientation
        await query.edit_message_text("✅ Pengaturan selesai. Menganalisis naskah...")

        try:
            timeline = analyze(state["script"], state["orientation"])
            state["timeline"] = timeline

            char_map = {}
            for i, c_type in enumerate(state["chars"]):
                char_id = chr(ord('a') + i)
                char_map[char_id] = {"type": c_type, "voice": VOICE_MAP.get(c_type)}
            
            # Inject character types into the timeline
            for char_data in timeline.get("characters", []):
                char_id = char_data.get("id")
                if char_id in char_map:
                    char_data["type"] = char_map[char_id]["type"]

            with open("characters.json", "w", encoding="utf-8") as f:
                json.dump(char_map, f, indent=2)

            state["step"] = "edit"
            await query.delete_message()
            await send_timeline_preview(chat_id, context)

        except Exception as e:
            await context.bot.send_message(chat_id, f"❌ Analisis gagal: {e}")

    elif step == "edit":
        if data.startswith("scene:"):
            state["scene_idx"] = int(data.split(":")[1]) - 1
            scene = state["timeline"]["scenes"][state["scene_idx"]]
            keyboard = [
                [InlineKeyboardButton("🎭 Emotion", callback_data="edit:emotion")],
                [InlineKeyboardButton("⏱ Duration", callback_data="edit:duration")],
                [InlineKeyboardButton("⬅️ Kembali", callback_data="back")]
            ]
            await query.edit_message_text(f"Edit Scene {state['scene_idx']+1}:\n\"{scene['text']}\"", reply_markup=InlineKeyboardMarkup(keyboard))
        
        elif data == "edit:emotion":
            keyboard = [[InlineKeyboardButton(e, callback_data=f"emotion:{e}")] for e in ["sad", "happy", "thinking", "neutral", "angry", "surprised"]]
            keyboard.append([InlineKeyboardButton("⬅️ Kembali", callback_data="back")])
            await query.edit_message_text("Pilih emotion:", reply_markup=InlineKeyboardMarkup(keyboard))

        elif data.startswith("emotion:"):
            emotion = data.split(':')[1]
            state["timeline"]['scenes'][state['scene_idx']]['emotion'] = emotion
            await query.delete_message()
            await send_timeline_preview(chat_id, context)

        elif data == "edit:duration":
            keyboard = [[InlineKeyboardButton(str(d), callback_data=f"duration:{d}") for d in range(3, 7)]]
            keyboard.append([InlineKeyboardButton("⬅️ Kembali", callback_data="back")])
            await query.edit_message_text("Pilih durasi (detik):", reply_markup=InlineKeyboardMarkup(keyboard))

        elif data.startswith("duration:"):
            dur = int(data.split(':')[1])
            state["timeline"]['scenes'][state['scene_idx']]['duration'] = dur
            await query.delete_message()
            await send_timeline_preview(chat_id, context)

        elif data == "back":
            await query.delete_message()
            await send_timeline_preview(chat_id, context)

        elif data == "cancel":
            USER_STATE.pop(chat_id, None)
            await query.edit_message_text("❌ Dibatalkan.")

        elif data == "render":
            await query.edit_message_text("🎬 Rendering dimulai...")
            # Save final timeline and script for the rendering process
            with open("timeline.json", "w", encoding="utf-8") as f:
                json.dump(state["timeline"], f, indent=2, ensure_ascii=False)
            with open("script.txt", "w", encoding="utf-8") as f:
                f.write(state["script"])

            try:
                subprocess.run(["python", "main.py", "render"], check=True, capture_output=True, text=True)
                await context.bot.send_video(chat_id=chat_id, video=open("output/video.mp4", "rb"), caption="✅ Video selesai")
                USER_STATE.pop(chat_id, None)
            except subprocess.CalledProcessError as e:
                await context.bot.send_message(chat_id, f"❌ Render gagal:\n{e.stderr}")


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_script))
    app.add_handler(CallbackQueryHandler(on_button))
    app.run_polling()

if __name__ == "__main__":
    main()
