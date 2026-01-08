import subprocess
import json
import cairosvg
from io import BytesIO
from PIL import Image
import math
import wave
import numpy as np
import os

from scripts.svg_emotion import apply_emotion

W, H = 1080, 1920

# ======================
# AUDIO ENVELOPE
# ======================
def load_audio_envelope(wav_path, fps):
    with wave.open(wav_path, "rb") as wf:
        raw = wf.readframes(wf.getnframes())
        audio = np.frombuffer(raw, dtype=np.int16)

    audio = audio / max(1, np.max(np.abs(audio)))
    samples_per_frame = int(len(audio) / (wf.getnframes() / wf.getframerate() * fps))

    env = []
    for i in range(0, len(audio), samples_per_frame):
        env.append(float(np.mean(np.abs(audio[i:i+samples_per_frame]))))
    return env


# ======================
# SVG → PIL
# ======================
def svg_to_image(svg_path):
    png = cairosvg.svg2png(url=svg_path, output_width=W, output_height=H)
    return Image.open(BytesIO(png)).convert("RGBA")


# ======================
# RENDER PIPE
# ======================
def render_all(timeline, output_video):
    fps = timeline["fps"]
    env = load_audio_envelope("output/audio.wav", fps)

    ffmpeg = subprocess.Popen([
        "ffmpeg",
        "-y",
        "-f", "rawvideo",
        "-pix_fmt", "rgba",
        "-s", f"{W}x{H}",
        "-r", str(fps),
        "-i", "-",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        output_video
    ], stdin=subprocess.PIPE)

    frame_index = 0

    for scene in timeline["scenes"]:
        frames = int(scene["duration"] * fps)
        bg = svg_to_image(f"assets/backgrounds/{scene.get('bg','neutral')}.svg")

        for i in range(frames):
            frame = bg.copy()

            for char in timeline["characters"]:
                mouth = env[min(frame_index, len(env)-1)] if char["id"] == scene["speaker"] else 0

                tmp_svg = "output/tmp.svg"
                apply_emotion(
                    "assets/character_base.svg",
                    tmp_svg,
                    scene["emotion"],
                    mouth
                )

                char_img = svg_to_image(tmp_svg)
                frame.alpha_composite(char_img, (char["x"], 900))

            ffmpeg.stdin.write(frame.tobytes())
            frame_index += 1

    ffmpeg.stdin.close()
    ffmpeg.wait()
