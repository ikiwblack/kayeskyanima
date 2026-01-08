import os
import math
from PIL import Image

from scripts.svg_emotion import apply_emotion
from scripts.render_svg import svg_to_png

FPS = 12
W, H = 1080, 1920

os.makedirs("output/frames", exist_ok=True)

def motion(i, frames, emotion):
    t = i / frames
    if emotion == "happy":
        return int(math.sin(t * 6) * 20)
    if emotion == "sad":
        return int(t * 15)
    return 0

def render_scene(scene, start_frame):
    frames = int(scene["duration"] * FPS)

    for i in range(frames):
        idx = start_frame + i

        svg_temp = f"output/tmp_{idx}.svg"
        png_out = f"output/frames/frame_{idx:05d}.png"

        # Apply emotion to SVG
        apply_emotion(
            "assets/character_base.svg",
            svg_temp,
            scene["emotion"]
        )

        # Render SVG → PNG
        svg_to_png(svg_temp, png_out)

        # Apply motion (Y shift)
        img = Image.open(png_out).convert("RGBA")
        bg = Image.new("RGBA", (W, H), (255, 255, 255, 255))

        y = motion(i, frames, scene["emotion"])
        bg.paste(img, (284, 700 + y), img)
        bg.save(png_out)

    return start_frame + frames

def render_all(timeline):
    frame = 0
    for scene in timeline["scenes"]:
        frame = render_scene(scene, frame)
