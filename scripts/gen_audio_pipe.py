
import os
import json
from gtts import gTTS
from mutagen.mp3 import MP3
from tqdm import tqdm
import shutil

# --- Konfigurasi ---
INPUT_TIMELINE = "timeline.json"
OUTPUT_DIR = "output"
AUDIO_DIR = os.path.join(OUTPUT_DIR, "audio")
OUTPUT_TIMELINE = os.path.join(OUTPUT_DIR, "timeline.json")

# --- Logika Utama ---

# 0. Hapus direktori output lama untuk memastikan proses yang bersih
if os.path.exists(OUTPUT_DIR):
    shutil.rmtree(OUTPUT_DIR)
    print(f"🧹 Direktori '{OUTPUT_DIR}' lama telah dihapus.")

# 1. Pastikan direktori output ada
os.makedirs(AUDIO_DIR, exist_ok=True)
print(f"📂 Direktori output baru dibuat di '{OUTPUT_DIR}'.")

# 2. Baca file timeline input
try:
    with open(INPUT_TIMELINE, 'r', encoding='utf-8') as f:
        timeline = json.load(f)
except FileNotFoundError:
    print(f"❌ FATAL ERROR: File '{INPUT_TIMELINE}' tidak ditemukan. Proses dihentikan.")
    # Hentikan eksekusi jika timeline tidak ada
    exit()

print("🔊 Memulai proses pembuatan audio dan pengukuran durasi...")

# 3. Iterasi melalui setiap adegan untuk membuat audio dan mendapatkan durasi
updated_scenes = []
for i, scene in enumerate(tqdm(timeline["scenes"], desc="💬 Mensintesis Audio")):
    line_text = scene.get("line")
    scene_id = f"scene_{i+1}"
    
    new_scene = scene.copy()

    if line_text and line_text.strip():
        try:
            audio_path = os.path.join(AUDIO_DIR, f"{scene_id}.mp3")
            
            # Buat audio menggunakan gTTS (Google Text-to-Speech)
            tts = gTTS(text=line_text, lang='id', slow=False)
            tts.save(audio_path)

            # Ukur durasi audio menggunakan mutagen
            audio_info = MP3(audio_path)
            duration_seconds = audio_info.info.length
            
            new_scene["duration"] = duration_seconds
            new_scene["audio_path"] = audio_path

        except Exception as e:
            print(f"⚠️  Gagal membuat audio untuk adegan {i+1}: {e}")
            new_scene["duration"] = scene.get("duration", 0) # Default ke 0 jika gagal
    else:
        # Jika tidak ada dialog, gunakan durasi yang ada atau default ke 1 detik untuk jeda
        new_scene["duration"] = scene.get("duration", 1.0)
    
    updated_scenes.append(new_scene)

# 4. Buat objek timeline baru dengan data yang telah diperbarui
output_timeline_data = timeline.copy() # Salin semua data asli (width, height, dll)
output_timeline_data["scenes"] = updated_scenes # Ganti hanya adegan

# 5. Tulis data timeline yang baru ke output/timeline.json
with open(OUTPUT_TIMELINE, 'w', encoding='utf-8') as f:
    json.dump(output_timeline_data, f, indent=4, ensure_ascii=False)

print(f"✅ Proses selesai.")
print(f"🎶 File-file audio telah dibuat di direktori '{AUDIO_DIR}'.")
print(f"⏱️  Timeline dengan data durasi akurat telah disimpan di '{OUTPUT_TIMELINE}'.")
