import os
import math
from PIL import Image

from scripts.svg_emotion import apply_emotion
from scripts.svg_gesture import apply_gesture
from scripts.render_svg import svg_to_png

FPS = 12
W, H = 1080, 1920

os.makedirs("output/frames", exist_ok=True)

def motion_y(i, frames, emotion):
    t = i / frames
    if emotion == "happy":
        return int(math.sin(t * 6) * 20)
    if emotion == "sad":
        return int(t * 15)
    return 0

def render_scene(scene, start_frame):
    frames = int(scene["duration"] * FPS)
    emotion = scene.get("emotion", "neutral")
    gesture = scene.get("gesture", "idle")

    for i in range(frames):
        idx = start_frame + i
        t = i / frames

        svg_emotion = f"output/tmp_emotion_{idx}.svg"
        svg_final = f"output/tmp_final_{idx}.svg"
        png_char = f"output/tmp_char_{idx}.png"
        png_out = f"output/frames/frame_{idx:05d}.png"

        # 1. Emotion + facial (blink, nod)
        apply_emotion(
            "assets/character_base.svg",
            svg_emotion,
            emotion,
            t
        )

        # 2. Gesture (arm pose)
        apply_gesture(
            svg_emotion,
            svg_final,
            gesture
        )

        # 3. SVG → PNG character
        svg_to_png(svg_final, png_char)

        # 4. Composite ke background + motion
        char = Image.open(png_char).convert("RGBA")
        bg = Image.new("RGBA", (W, H), (255, 255, 255, 255))

        y = motion_y(i, frames, emotion)
        bg.paste(char, (284, 720 + y), char)
        bg.save(png_out)

    return start_frame + frames

def render_all(timeline):
    frame = 0
    for scene in timeline["scenes"]:
        frame = render_scene(scene, frame)
