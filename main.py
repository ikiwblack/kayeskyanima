import os
import sys
import json
import subprocess

# --- Google Cloud Authentication (REMOVED) ---
# This block is no longer necessary as we are switching to gTTS.

from scripts.process_audio import process_audio_and_update_timeline
from scripts.analyze_text import analyze
from scripts.validate_timeline import validate_timeline
from scripts.render_frames_pipe import render_all
from scripts.subtitles_ass import build_ass

OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

MODE = sys.argv[1] if len(sys.argv) > 1 else "render"

# Load script and character definitions
if not os.path.exists("script.txt"):
    raise FileNotFoundError("File script.txt tidak ditemukan. Silakan buat file tersebut dan isi dengan naskah video.")

with open("script.txt", encoding="utf-8") as f:
    text = f.read().strip()
if not text:
    raise ValueError("Naskah kosong")

if not os.path.exists("characters.json"):
    raise FileNotFoundError("File characters.json tidak ditemukan. Jalankan bot untuk memilih karakter.")

# Load characters.json and transform it into a dictionary keyed by character ID
with open("characters.json", encoding="utf-8") as f:
    characters_data = json.load(f)
    characters_map = {char['id']: char for char in characters_data['characters']}

# Get initial timeline from analyzer or file
if os.path.exists("timeline.json") and MODE != "analyze":
    with open("timeline.json", encoding="utf-8") as f:
        timeline = json.load(f)
else:
    # This assumes a default orientation if not run from bot, adjust if necessary
    timeline = analyze(text, '9:16')

# --- SET RENDER RESOLUTION TO 720p (PORTRAIT OR LANDSCAPE) ---
print("🔧 Mengatur resolusi render menjadi 720p.")
original_width = timeline.get('width', 1080)
original_height = timeline.get('height', 1920)

if original_width > original_height:
    # Landscape
    print("   -> Terdeteksi orientasi lanskap. Mengatur ke 1280x720.")
    timeline['width'] = 1280
    timeline['height'] = 720
else:
    # Portrait or square
    print("   -> Terdeteksi orientasi potret. Mengatur ke 720x1280.")
    timeline['width'] = 720
    timeline['height'] = 1280

# Inject character details into the timeline structure for the renderer
timeline["characters"] = characters_data["characters"] # Inject full character list

# If we are in 'analyze' mode (called by the bot), we stop here.
if MODE == "analyze":
    with open("timeline.json", "w", encoding="utf-8") as f:
        json.dump(timeline, f, indent=2, ensure_ascii=False)
    print("Analysis complete. Timeline saved.")
    sys.exit(0)

# --- RENDER MODE --- (Called after user clicks 'Render' in the bot)

print("📢 Menghasilkan audio dan menyinkronkan durasi timeline...")
timeline = process_audio_and_update_timeline(timeline, characters_map)

print("✅ Audio dan durasi berhasil disinkronkan.")

# Validate the timeline AFTER audio processing to ensure durations are set
print("🔍 Memvalidasi timeline akhir...")
errors = validate_timeline(timeline)
if errors:
    # Jika ada error, cetak timeline untuk debugging
    with open("timeline_error_dump.json", "w", encoding="utf-8") as f:
        json.dump(timeline, f, indent=2, ensure_ascii=False)
    print("❌ Timeline tidak valid. Lihat 'timeline_error_dump.json' untuk detailnya.")
    raise ValueError("\n".join(errors))

print("🖼️ Merender frame video...")
render_all(
    timeline=timeline,
    output_video="output/video_noaudio.mp4"
)

print("✍️ Membuat subtitle...")
build_ass(timeline, "output/subtitles.ass")

print("🎬 Menggabungkan semua file...")
subprocess.run([
    "ffmpeg", "-y",
    "-i", "output/video_noaudio.mp4",
    "-i", "output/audio.wav",
    "-vf", "ass=output/subtitles.ass",
    "-c:v", "libx264",
    "-pix_fmt", "yuv420p",
    "-c:a", "aac",
    "output/video.mp4"
], check=True, capture_output=True)

print("✅ RENDER SELESAI")
