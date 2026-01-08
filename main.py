import os
import sys
import json
import subprocess

from scripts.analyze_text import analyze
from scripts.validate_timeline import validate_timeline
from scripts.render_frames_pipe import render_all
from scripts.tts_dummy import generate_audio
from scripts.subtitles_ass import build_ass

# =====================
# CONFIG
# =====================
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

MODE = sys.argv[1] if len(sys.argv) > 1 else "render"

# =====================
# LOAD SCRIPT
# =====================
with open("script.txt", encoding="utf-8") as f:
    text = f.read().strip()

if not text:
    raise ValueError("Naskah kosong")

# =====================
# LOAD / ANALYZE TIMELINE
# =====================
if os.path.exists("timeline.json"):
    with open("timeline.json", encoding="utf-8") as f:
        timeline = json.load(f)
else:
    timeline = analyze(text)

errors = validate_timeline(timeline)
if errors:
    raise ValueError("\n".join(errors))

# =====================
# ANALYZE ONLY MODE
# =====================
if MODE == "analyze":
    with open("timeline.json", "w", encoding="utf-8") as f:
        json.dump(timeline, f, indent=2, ensure_ascii=False)
    print("OK")
    sys.exit(0)

# =====================
# AUDIO (TTS)
# =====================
generate_audio(text)

# =====================
# VIDEO (SVG → FFMPEG PIPE)
# =====================
render_all(
    timeline,
    output_video="output/video_noaudio.mp4"
)

# =====================
# SUBTITLE (ASS)
# =====================
build_ass(timeline, "output/subtitles.ass")

# =====================
# MUX AUDIO + SUBTITLE
# =====================
subprocess.run([
    "ffmpeg", "-y",
    "-i", "output/video_noaudio.mp4",
    "-i", "output/audio.wav",
    "-vf", "ass=output/subtitles.ass",
    "-af",
    "acompressor=threshold=-18dB:ratio=3:attack=5:release=200,"
    "loudnorm=I=-16:LRA=11:TP=-1.5",
    "-c:v", "libx264",
    "-pix_fmt", "yuv420p",
    "-c:a", "aac",
    "output/video.mp4"
], check=True)
