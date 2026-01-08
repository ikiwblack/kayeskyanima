import subprocess
import cairosvg
from io import BytesIO
from PIL import Image
import wave
import numpy as np
from lxml import etree

from scripts.svg_emotion import apply_emotion

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


# =====================
# SVG → PIL IMAGE
# =====================
def svg_tree_to_image(tree, width, height):
    png = cairosvg.svg2png(
        bytestring=etree.tostring(tree),
        output_width=width,
        output_height=height
    )
    return Image.open(BytesIO(png)).convert("RGBA")


# =====================
# RENDER CORE
# =====================
def render_all(timeline, characters_map, output_video):
    W = timeline.get("width", 1080)
    H = timeline.get("height", 1920)
    fps = timeline["fps"]

    # Determine adaptive scale factor based on number of characters
    num_chars = len(timeline.get("characters", []))
    if num_chars == 2:
        scale_factor = 0.55  # Slightly smaller for 2 characters
    elif num_chars >= 3:
        scale_factor = 0.5   # Even smaller for 3+ characters
    else:
        scale_factor = 0.6   # Default size for 1 character

    envelope = load_audio_envelope("output/audio.wav", fps)

    character_svgs = {}
    for char_id, char_info in characters_map.items():
        char_type = char_info["type"]
        svg_path = f"assets/characters/{char_type}.svg"
        if char_type not in character_svgs:
            character_svgs[char_type] = etree.parse(svg_path)

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
        bg_tree = etree.parse(f"assets/backgrounds/{scene.get('bg', 'neutral')}.svg")
        bg_tree.getroot().set("width", str(W))
        bg_tree.getroot().set("height", str(H))
        bg_img = svg_tree_to_image(bg_tree, W, H)

        frames = int(scene["duration"] * fps)

        for _ in range(frames):
            frame = bg_img.copy()

            for char_in_scene in timeline["characters"]:
                char_id = char_in_scene["id"]
                char_type = characters_map[char_id]["type"]
                base_tree = character_svgs[char_type]

                mouth = (
                    envelope[min(frame_idx, len(envelope) - 1)]
                    if char_id == scene["speaker"]
                    else 0.0
                )

                char_tree = apply_emotion(
                    base_tree=base_tree,
                    emotion=scene["emotion"],
                    mouth_open=mouth,
                    frame=frame_idx,
                    fps=fps,
                    gesture=scene.get("gesture")
                )
                
                # Scale character based on video height and number of characters
                char_height = int(H * scale_factor)
                char_width = int(char_height * (512/512)) # Preserve aspect ratio
                
                char_img_resized = cairosvg.svg2png(
                    bytestring=etree.tostring(char_tree),
                    output_width=char_width,
                    output_height=char_height
                )
                char_img = Image.open(BytesIO(char_img_resized)).convert("RGBA")

                y_pos = H - char_height + int(H * 0.05)
                x_pos = char_in_scene["x"]

                frame.alpha_composite(char_img, (x_pos, y_pos))

            ffmpeg.stdin.write(frame.tobytes())
            frame_idx += 1

    ffmpeg.stdin.close()
    ffmpeg.wait()
