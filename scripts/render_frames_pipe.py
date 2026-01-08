import subprocess
import cairosvg
from io import BytesIO
from PIL import Image
import wave
import numpy as np
import tempfile
import os

from scripts.svg_emotion import apply_emotion

W, H = 1080, 1920

# =====================
# AUDIO ENVELOPE
# =====================
def load_audio_envelope(wav_path, fps):
    with wave.open(wav_path, "rb") as wf:
        sr = wf.getframerate()
        audio = np.frombuffer(
            wf.readframes(wf.getnframes()),
            dtype=np.int16
        )

    max_val = np.max(np.abs(audio))
    audio = audio / max_val if max_val > 0 else audio.astype(np.float32)

    samples_per_frame = int(sr / fps)
    envelope = []

    for i in range(0, len(audio), samples_per_frame):
        chunk = audio[i:i + samples_per_frame]
        envelope.append(float(np.mean(np.abs(chunk))) if len(chunk) else 0.0)

    return envelope


def svg_to_image(svg_path):
    png = cairosvg.svg2png(
        url=svg_path,
        output_width=W,
        output_height=H
    )
    return Image.open(BytesIO(png)).convert("RGBA")


# =====================
# RENDER CORE
# =====================
def render_all(timeline, output_video):
    fps = timeline["fps"]
    envelope = load_audio_envelope("output/audio.wav", fps)

    ffmpeg = subprocess.Popen([
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-pix_fmt", "rgba",
        "-s", f"{W}x{H}",
        "-r", str(fps),
        "-i", "-",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        output_video
    ], stdin=subprocess.PIPE)

    frame_idx = 0

    with tempfile.TemporaryDirectory() as tmpdir:
        for scene in timeline["scenes"]:
            bg = svg_to_image(
                f"assets/backgrounds/{scene.get('bg','neutral')}.svg"
            )
            frames = int(scene["duration"] * fps)

            for i in range(frames):
                frame = bg.copy()

                for char in timeline["characters"]:
                    mouth = (
                        envelope[min(frame_idx, len(envelope)-1)]
                        if char["id"] == scene["speaker"]
                        else 0.0
                    )

                    tmp_svg = os.path.join(
                        tmpdir, f"{char['id']}.svg"
                    )

                    apply_emotion(
                        "assets/character_base.svg",
                        tmp_svg,
                        scene["emotion"],
                        mouth
                    )

                    char_img = svg_to_image(tmp_svg)
                    frame.alpha_composite(
                        char_img, (char["x"], 900)
                    )

                ffmpeg.stdin.write(frame.tobytes())
                frame_idx += 1

    ffmpeg.stdin.close()
    ffmpeg.wait()
