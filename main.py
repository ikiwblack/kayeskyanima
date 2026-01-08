import os
import sys
import json
import subprocess

# --- Google Cloud Authentication ---
# On Railway, the GOOGLE_CREDENTIALS_JSON secret is set as an environment variable.
# The google-cloud-texttospeech library needs to find these credentials in a file.
# This code block writes the content of the environment variable to a temporary
# file and then sets the GOOGLE_APPLICATION_CREDENTIALS environment variable
# to point to that file.
if "GOOGLE_CREDENTIALS_JSON" in os.environ:
    creds_json_str = os.environ["GOOGLE_CREDENTIALS_JSON"]
    creds_path = "/tmp/google_creds.json"
    with open(creds_path, "w") as f:
        f.write(creds_json_str)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path
# --- End of Authentication Block ---

# Import a new module for audio processing that we will create
from scripts.process_audio import process_audio_and_update_timeline
from scripts.analyze_text import analyze
from scripts.validate_timeline import validate_timeline
from scripts.render_frames_pipe import render_all
from scripts.subtitles_ass import build_ass

OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

MODE = sys.argv[1] if len(sys.argv) > 1 else "render"

# Load script and character definitions
with open("script.txt", encoding="utf-8") as f:
    text = f.read().strip()
if not text:
    raise ValueError("Naskah kosong")

if not os.path.exists("characters.json"):
    raise FileNotFoundError("File characters.json tidak ditemukan. Jalankan bot untuk memilih karakter.")

with open("characters.json", encoding="utf-8") as f:
    characters_map = json.load(f)

# Get initial timeline from analyzer or file
# Note: In the bot flow, `analyze` is always called first.
if os.path.exists("timeline.json") and MODE != "analyze":
    with open("timeline.json", encoding="utf-8") as f:
        timeline = json.load(f)
else:
    timeline = analyze(text)

# Inject character *type* into the timeline structure for the renderer
for char_data in timeline.get("characters", []):
    char_id = char_data.get("id")
    if char_id in characters_map:
        char_data["type"] = characters_map[char_id]["type"]

# Validate the basic structure
errors = validate_timeline(timeline)
if errors:
    # In case of validation errors, raise them to be caught by the bot
    raise ValueError("\n".join(errors))

# If we are in 'analyze' mode (called by the bot), we stop here.
# The bot gets the timeline and waits for user confirmation.
if MODE == "analyze":
    with open("timeline.json", "w", encoding="utf-8") as f:
        json.dump(timeline, f, indent=2, ensure_ascii=False)
    print("Analysis complete. Timeline saved.")
    sys.exit(0)

# --- RENDER MODE --- (Called after user clicks 'Render' in the bot)

print("📢 Menghasilkan audio dan menyinkronkan durasi timeline...")
# This function will generate audio for each scene using the correct voice,
# get the real duration, update the timeline with it, and create a final audio.wav
updated_timeline = process_audio_and_update_timeline(timeline, characters_map)

print("🖼️ Merender frame video...")
# The renderer now gets the character map to know which SVG to load (e.g., 'Kakek.svg')
render_all(
    timeline=updated_timeline,
    characters_map=characters_map,
    output_video="output/video_noaudio.mp4"
)

print("✍️ Membuat subtitle...")
# Subtitles are built with the final, accurate durations
build_ass(updated_timeline, "output/subtitles.ass")

print("🎬 Menggabungkan semua file...")
# The final command combines the visuals, the single concatenated audio track, and subtitles
subprocess.run([
    "ffmpeg", "-y",
    "-i", "output/video_noaudio.mp4",
    "-i", "output/audio.wav", # The single audio track from process_audio
    "-vf", "ass=output/subtitles.ass",
    "-af",
    "acompressor=threshold=-18dB:ratio=3:attack=5:release=200,",
    "loudnorm=I=-16:LRA=11:TP=-1.5",
    "-c:v", "libx264",
    "-pix_fmt", "yuv420p",
    "-c:a", "aac",
    "output/video.mp4"
], check=True, capture_output=True)

print("✅ RENDER SELESAI")
