import os
import math
import subprocess
from io import BytesIO
from PIL import Image

import cairosvg

from scripts.svg_emotion import apply_emotion
from scripts.svg_gesture import apply_gesture

# =====================
# CONFIG
# =====================
FPS = 12
W, H = 1080, 1920
CHAR_W = 512
CHAR_H = 512

BG_COLOR = (255, 255, 255, 255)

# =====================
# SVG → PIL IMAGE (MEMORY)
# =====================
def svg_to_image(svg_path):
    png_bytes = cairosvg.svg2png(
        url=svg_path,
        output_width=CHAR_W,
        output_height=CHAR_H
    )
    return Image.open(BytesIO(png_bytes)).convert("RGBA")

# =====================
# MOTION
# =====================
def motion_y(i, frames, emotion):
    t = i / frames
    if emotion == "happy":
        return int(math.sin(t * 6) * 20)
    if emotion == "sad":
        return int(t * 15)
    return 0

# =====================
# MAIN RENDER
# =====================
def render_all(timeline, output_video="output/video.mp4"):
    os.makedirs("output", exist_ok=True)

    total_frames = sum(int(s["duration"] * FPS) for s in timeline["scenes"])

    ffmpeg = subprocess.Popen(
        [
            "ffmpeg",
            "-y",
            "-f", "rawvideo",
            "-pix_fmt", "rgba",
            "-s", f"{W}x{H}",
            "-r", str(FPS),
            "-i", "-",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            output_video
        ],
        stdin=subprocess.PIPE
    )

    frame_index = 0

    for scene in timeline["scenes"]:
        frames = int(scene["duration"] * FPS)
        emotion = scene.get("emotion", "neutral")
        gesture = scene.get("gesture", "idle")

        for i in range(frames):
            t = i / frames

            # ===== SVG PROCESS (IN MEMORY) =====
            svg_emotion = f"/tmp/emotion_{frame_index}.svg"
            svg_final = f"/tmp/final_{frame_index}.svg"

            apply_emotion(
                "assets/character_base.svg",
                svg_emotion,
                emotion,
                t
            )

            apply_gesture(
                svg_emotion,
                svg_final,
                gesture
            )

            char_img = svg_to_image(svg_final)

            # ===== COMPOSITE FRAME =====
            frame = Image.new("RGBA", (W, H), BG_COLOR)

            y = motion_y(i, frames, emotion)
            x_pos = (W - CHAR_W) // 2
            y_pos = 720 + y

            frame.paste(char_img, (x_pos, y_pos), char_img)

            # ===== PIPE TO FFMPEG =====
            ffmpeg.stdin.write(frame.tobytes())
            frame_index += 1

    ffmpeg.stdin.close()
    ffmpeg.wait()
