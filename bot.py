
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
from scripts.validate_timeline import validate_timeline

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ["TELEGRAM_TOKEN"]

# Daftar emosi yang di-hardcode untuk konsistensi
AVAILABLE_EMOTIONS = ["neutral", "sad", "happy", "thinking", "angry", "surprised"]

# ===== STATE =====
USER_STATE = {}

# ===== HELPER =====
async def send_timeline_preview(chat_id, context):
    state = USER_STATE.get(chat_id, {})
    timeline = state.get("timeline")
    if not timeline:
        return

    text = "📝 *Preview Timeline*\n\n"
    for i, s in enumerate(timeline["scenes"]):
        char_id = s['speaker']
        # Ambil detail karakter langsung dari timeline
        char_details = next((c for c in timeline['characters'] if c['id'] == char_id), None)
        char_name = char_details['id'] if char_details else 'Unknown'
        text += f"{i+1}. ({char_name}) [{s.get('emotion','neutral')}] {s['text']} ({s.get('duration','auto')}s)\n"

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

# ===== COMMAND HANDLERS =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mengirim pesan selamat datang saat perintah /start dikeluarkan."""
    await update.message.reply_text(
        "👋 Halo! Saya adalah bot pembuat video Anima.\n\n"
        "Kirimkan saya naskah Anda untuk memulai. Formatnya:\n"
        "`NamaKarakter: Dialog baris pertama`\n"
        "`NamaKarakterLain: Dialog baris kedua`\n\n"
        "Contoh:\n"
        "`Kakek: Halo, Nek.`\n"
        "`Nenek: Halo juga, Kek.`\n\n"
        "Untuk daftar karakter yang tersedia, gunakan perintah /characters.\n"
        "Untuk daftar emosi yang bisa digunakan, gunakan perintah /emotion."
    )

async def emotion_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menampilkan daftar emosi yang tersedia."""
    emotion_text = "🎭 *Daftar Emosi Tersedia*\n\nAnda bisa menggunakan emosi berikut saat mengedit sebuah adegan:\n"
    for emotion in AVAILABLE_EMOTIONS:
        emotion_text += f"- `{emotion}`\n"
    
    await update.message.reply_text(emotion_text, parse_mode="Markdown")
    
async def characters_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Membaca characters.json dan menampilkan daftar karakter yang tersedia."""
    try:
        with open('characters.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            characters = data.get("characters", [])
            if not characters:
                await update.message.reply_text("Tidak ada karakter yang didefinisikan dalam `characters.json`.")
                return

            char_text = "👥 *Daftar Karakter Tersedia*\n\nAnda bisa menggunakan nama-nama (ID) berikut dalam naskah Anda:\n"
            for char in characters:
                char_text += f"- `{char['id']}`\n"
            
            await update.message.reply_text(char_text, parse_mode="Markdown")

    except FileNotFoundError:
        await update.message.reply_text("File `characters.json` tidak ditemukan.")
    except json.JSONDecodeError:
        await update.message.reply_text("Gagal membaca file `characters.json`. Format tidak valid.")
        

# ===== TEXT INPUT (SCRIPT) =====
async def handle_script(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text.strip()
    if not text:
        await update.message.reply_text("❌ Naskah kosong.")
        return

    USER_STATE[chat_id] = {"script": text, "step": "select_orientation"}
    await update.message.reply_text("Pilih orientasi video:", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("Portrait (9:16)", callback_data="orientation:9:16")],
        [InlineKeyboardButton("Landscape (16:9)", callback_data="orientation:16:9")],
    ]))

# ===== CALLBACK BUTTON =====
async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    chat_id = query.message.chat.id
    data = query.data
    state = USER_STATE.get(chat_id)

    if not state:
        await query.edit_message_text("❌ Sesi tidak ditemukan. Silakan kirim ulang naskah Anda.")
        return

    step = state.get("step")

    try:
        if data.startswith("orientation:") and step == "select_orientation":
            orientation = data.split(":")[1]
            state["orientation"] = orientation
            await query.edit_message_text("✅ Orientasi dipilih. Menganalisis naskah...")

            try:
                timeline = analyze(state["script"], state["orientation"])
                state["timeline"] = timeline
                state["step"] = "edit"
                await query.delete_message()
                await send_timeline_preview(chat_id, context)
            except Exception as e:
                logger.error(f"Analysis failed for chat {chat_id}: {e}", exc_info=True)
                await query.edit_message_text(f"❌ Analisis gagal: {e}\n\nPastikan naskah Anda menggunakan karakter yang valid (cek /characters) dan formatnya benar.")
                USER_STATE.pop(chat_id, None)

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
                keyboard = [[InlineKeyboardButton(e, callback_data=f"emotion:{e}")] for e in AVAILABLE_EMOTIONS]
                keyboard.append([InlineKeyboardButton("⬅️ Kembali", callback_data="back")])
                await query.edit_message_text("Pilih emotion:", reply_markup=InlineKeyboardMarkup(keyboard))

            elif data.startswith("emotion:"):
                emotion = data.split(':')[1]
                state["timeline"]['scenes'][state['scene_idx']]['emotion'] = emotion
                await query.delete_message()
                await send_timeline_preview(chat_id, context)

            elif data == "edit:duration":
                # Durasi sekarang tidak bisa diubah karena akan di-override oleh audio
                await context.bot.answer_callback_query(query.id, "Durasi diatur secara otomatis oleh audio dan tidak bisa diubah manual.", show_alert=True)

            elif data == "back":
                await query.delete_message()
                await send_timeline_preview(chat_id, context)

            elif data == "cancel":
                USER_STATE.pop(chat_id, None)
                await query.edit_message_text("❌ Dibatalkan.")

            elif data == "render":
                await query.edit_message_text("⏳ *Rendering video...*\nIni mungkin memakan waktu beberapa menit.", parse_mode="Markdown")
                
                # Simpan timeline final ke file untuk di-debug jika perlu
                with open("timeline.json", "w", encoding="utf-8") as f:
                    json.dump(state["timeline"], f, indent=2, ensure_ascii=False)

                try:
                    # Panggil main.py dengan argumen render
                    process = subprocess.run(
                        ["python", "main.py", "render"], 
                        check=True, capture_output=True, text=True, encoding='utf-8'
                    )
                    logger.info(f"Render successful for chat {chat_id}: {process.stdout}")
                    await query.edit_message_text("✅ Render selesai! Mengirim video...")
                    await context.bot.send_video(chat_id=chat_id, video=open("output/video.mp4", "rb"), caption="Video Anda sudah jadi!")
                except subprocess.CalledProcessError as e:
                    logger.error(f"Render failed for chat {chat_id}: STDERR: {e.stderr} STDOUT: {e.stdout}")
                    await context.bot.send_message(chat_id, f"❌ Render gagal.\nLogs:\n{e.stderr[-1000:]}") # Kirim 1000 karakter terakhir dari error
                finally:
                     USER_STATE.pop(chat_id, None)
    
    except Exception as e:
        logger.error(f"An error occurred in on_button for chat {chat_id}: {e}", exc_info=True)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"❌ Terjadi kesalahan tak terduga. Proses telah dihentikan. Silakan coba lagi."
        )
        USER_STATE.pop(chat_id, None) # Hapus state jika ada error

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("emotion", emotion_list))
    app.add_handler(CommandHandler("characters", characters_list))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_script))
    app.add_handler(CallbackQueryHandler(on_button))
    app.run_polling()

if __name__ == "__main__":
    main()
