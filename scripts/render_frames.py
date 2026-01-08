from PIL import Image
import os
import math

FPS = 12
W, H = 1080, 1920

def motion(i, frames, emotion):
    t = i / frames
    if emotion == "happy":
        return int(math.sin(t * 6) * 20)
    if emotion == "sad":
        return int(t * 15)
    return 0

def render_scene(scene, start):
    frames = int(scene["duration"] * FPS)
    pose = scene["emotion"] if scene["emotion"] != "neutral" else scene["action"]

    char = Image.open(f"assets/character/{pose}.png").convert("RGBA")
    bg = Image.open("assets/bg/neutral.png").convert("RGBA").resize((W, H))

    for i in range(frames):
        frame = bg.copy()
        y = motion(i, frames, scene["emotion"])
        frame.paste(char, (400, 900 + y), char)
        frame.save(f"output/frames/frame_{start+i:05d}.png")

    return start + frames

def render_all(timeline):
    frame = 0
    for scene in timeline["scenes"]:
        frame = render_scene(scene, frame)
