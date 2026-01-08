import os
import sys
import subprocess

from scripts.analyze_text import analyze
from scripts.validate_timeline import validate_timeline
from scripts.render_frames import render_all
from scripts.subtitles import build_srt
from scripts.tts_dummy import generate_audio

os.makedirs("output/frames", exist_ok=True)

MODE = sys.argv[1] if len(sys.argv) > 1 else "render"

with open("script.txt", encoding="utf-8") as f:
    text = f.read()

if not text.strip():
    raise ValueError("Naskah kosong")

# ===== MODE ANALYZE (TANPA RENDER) =====
if MODE == "analyze":
    timeline = analyze(text)

    errors = validate_timeline(timeline)
    if errors:
        raise ValueError("Timeline tidak valid:\n" + "\n".join(errors))

    print("OK")
    sys.exit(0)

# ===== MODE RENDER =====
timeline = analyze(text)

errors = validate_timeline(timeline)
if errors:
    raise ValueError("Timeline tidak valid:\n" + "\n".join(errors))

generate_audio(text)
render_all(timeline)
build_srt(timeline, text)

subprocess.run([
    "ffmpeg", "-y",
    "-framerate", str(timeline["fps"]),
    "-i", "output/frames/frame_%05d.png",
    "-i", "output/audio.wav",
    "-vf", "subtitles=output/subtitles.srt",
    "-c:v", "libx264",
    "-pix_fmt", "yuv420p",
    "output/video.mp4"
], check=True)
