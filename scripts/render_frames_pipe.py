import subprocess
import cairosvg
from io import BytesIO
from PIL import Image
import wave
import numpy as np

from scripts.svg_emotion import apply_emotion

W, H = 1080, 1920

def load_audio_envelope(wav_path, fps):
    with wave.open(wav_path, "rb") as wf:
        audio = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
    audio = audio / max(1, abs(audio).max())
    samples = int(len(audio) / (wf.getnframes() / wf.getframerate() * fps))
    return [float(abs(audio[i:i+samples]).mean()) for i in range(0, len(audio), samples)]

def svg_to_image(svg_path):
    png = cairosvg.svg2png(url=svg_path, output_width=W, output_height=H)
    return Image.open(BytesIO(png)).convert("RGBA")

def render_all(timeline, output_video):
    fps = timeline["fps"]
    env = load_audio_envelope("output/audio.wav", fps)

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

    for scene in timeline["scenes"]:
        bg = svg_to_image(f"assets/backgrounds/{scene.get('bg','neutral')}.svg")
        frames = int(scene["duration"] * fps)

        for _ in range(frames):
            frame = bg.copy()
            for char in timeline["characters"]:
                mouth = env[min(frame_idx, len(env)-1)] if char["id"] == scene["speaker"] else 0
                apply_emotion(
                    "assets/character_base.svg",
                    "output/tmp.svg",
                    scene["emotion"],
                    mouth
                )
                char_img = svg_to_image("output/tmp.svg")
                frame.alpha_composite(char_img, (char["x"], 900))
            ffmpeg.stdin.write(frame.tobytes())
            frame_idx += 1

    ffmpeg.stdin.close()
    ffmpeg.wait()
