
import os
import json
import subprocess
import logging

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

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ["TELEGRAM_TOKEN"]

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

async def ask_for_character_type(chat_id, message, char_index, is_edit=False):
    char_name = chr(ord('A') + char_index)
    text = f"Pilih karakter untuk *Pembicara {char_name}*:"
    keyboard = [[InlineKeyboardButton(c, callback_data=f"select_char:{c}")] for c in CHARACTERS]
    
    if is_edit:
        try:
            await message.edit_text(text=text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception: # Fallback if message not found or not modified
            await message.chat.send_message(text=text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await message.chat.send_message(text=text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

# ===== COMMAND HANDLERS =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a welcome message when the /start command is issued."""
    await update.message.reply_text(
        "👋 Halo! Saya adalah bot pembuat video Anima.\n\n"
        "Kirimkan saya naskah Anda untuk memulai, dan saya akan memandu Anda melalui prosesnya. "
        "Cukup ketik atau tempel teks Anda langsung di obrolan ini."
    )

# ===== TEXT INPUT (SCRIPT) =====
async def handle_script(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text.strip()
    if not text:
        await update.message.reply_text("❌ Naskah kosong.")
        return

    USER_STATE[chat_id] = {"script": text}
    await update.message.reply_text("Pilih orientasi video:", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("Portrait (9:16)", callback_data="orientation:9:16")],
        [InlineKeyboardButton("Landscape (16:9)", callback_data="orientation:16:9")],
    ]))
    USER_STATE[chat_id]["step"] = "select_orientation"

# ===== CALLBACK BUTTON =====
async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    chat_id = query.message.chat.id

    try:
        data = query.data
        state = USER_STATE.get(chat_id)

        if not state:
            await query.edit_message_text("❌ Sesi tidak ditemukan. Silakan kirim ulang naskah Anda.")
            return

        step = state.get("step")

        if data.startswith("orientation:"):
            if step != "select_orientation": return

            orientation = data.split(":")[1]
            state["orientation"] = orientation
            await query.edit_message_text("✅ Orientasi dipilih. Menganalisis naskah dengan AI...")

            try:
                timeline = analyze(state["script"], state["orientation"])
                
                if "characters" in timeline and timeline["characters"]:
                    state["timeline"] = timeline
                    state["char_count"] = len(timeline["characters"])
                    state["chars"] = []
                    state["step"] = "select_char_auto"
                    
                    all_types_present = all("type" in char and char["type"] for char in timeline["characters"])
                    
                    if all_types_present:
                        await query.delete_message()
                        await send_timeline_preview(chat_id, context)
                        state["step"] = "edit"
                    else:
                        await ask_for_character_type(chat_id, query.message, char_index=0, is_edit=True)

                else:
                    raise ValueError("No characters found")

            except Exception:
                state["step"] = "char_count_manual"
                keyboard = [[
                    InlineKeyboardButton("1", callback_data="count_char:1"),
                    InlineKeyboardButton("2", callback_data="count_char:2"),
                    InlineKeyboardButton("3", callback_data="count_char:3"),
                ]]
                await query.edit_message_text(
                    "AI tidak dapat menentukan jumlah karakter. Berapa banyak karakter dalam naskah?",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )

        elif data.startswith("count_char:"):
            if step != "char_count_manual": return
            
            count = int(data.split(":")[1])
            state["char_count"] = count
            state["chars"] = []
            state["step"] = "select_char_manual"
            await ask_for_character_type(chat_id, query.message, char_index=0, is_edit=True)

        elif data.startswith("select_char:"):
            if step not in ["select_char_auto", "select_char_manual"]: return

            char_type = data.split(":")[1]
            state["chars"].append(char_type)
            
            next_char_index = len(state["chars"])
            if next_char_index < state["char_count"]:
                await ask_for_character_type(chat_id, query.message, char_index=next_char_index, is_edit=True)
            else:
                await query.edit_message_text("✅ Pengaturan selesai. Finalisasi timeline...")
                
                if "timeline" not in state:
                     state["timeline"] = analyze(state["script"], state["orientation"])

                char_map = {}
                for i, c_type in enumerate(state["chars"]):
                    char_id_str = chr(ord('a') + i)
                    char_map[char_id_str] = {"type": c_type, "voice": VOICE_MAP.get(c_type)}
                
                if "characters" not in state["timeline"]:
                    state["timeline"]["characters"] = []

                for i, c_type in enumerate(state["chars"]):
                     char_id_str = chr(ord('a') + i)
                     existing_char = next((c for c in state["timeline"]["characters"] if c.get("id") == char_id_str), None)
                     if existing_char:
                         existing_char["type"] = c_type
                     else:
                         state["timeline"]["characters"].append({"id": char_id_str, "type": c_type, "x": 400 + i*1000})

                with open("characters.json", "w", encoding="utf-8") as f:
                    json.dump(char_map, f, indent=2)

                state["step"] = "edit"
                await query.delete_message()
                await send_timeline_preview(chat_id, context)
                
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
                keyboard = [[InlineKeyboardButton(str(d), callback_data=f"duration:{d}")] for d in range(3, 7)]
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
                with open("timeline.json", "w", encoding="utf-8") as f:
                    json.dump(state["timeline"], f, indent=2, ensure_ascii=False)
                with open("script.txt", "w", encoding="utf-8") as f:
                    f.write(state["script"])

                try:
                    subprocess.run(["python", "main.py", "render"], check=True, capture_output=True, text=True)
                    await context.bot.send_video(chat_id=chat_id, video=open("output/video.mp4", "rb"), caption="✅ Video selesai")
                    USER_STATE.pop(chat_id, None)
                except subprocess.CalledProcessError as e:
                    logger.error(f"Render failed: {e.stderr}")
                    await context.bot.send_message(chat_id, f"❌ Render gagal:\n{e.stderr}")
    
    except Exception as e:
        logger.error(f"An error occurred in on_button: {e}", exc_info=True)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"❌ Terjadi kesalahan tak terduga. Saya telah memberitahu developer."
        )


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_script))
    app.add_handler(CallbackQueryHandler(on_button))
    app.run_polling()

if __name__ == "__main__":
    main()
