import subprocess
import cairosvg
from io import BytesIO
from PIL import Image
import wave
import numpy as np
from lxml import etree
import os

from scripts.svg_emotion import apply_emotion

# =====================
# AUDIO ENVELOPE
# =====================
def load_audio_envelope(wav_path, fps):
    """Memuat data audio dan membuat 'amplop' volume untuk animasi mulut."""
    if not os.path.exists(wav_path):
        print(f"Warning: Audio file not found at {wav_path}. Mouth animation will be disabled.")
        return []
    
    try:
        with wave.open(wav_path, "rb") as wf:
            sr = wf.getframerate()
            n_frames = wf.getnframes()
            audio = np.frombuffer(wf.getframes(), dtype=np.int16)

        max_val = np.iinfo(np.int16).max
        audio = audio.astype(np.float32) / max_val

        samples_per_frame = int(sr / fps)
        if samples_per_frame == 0: return []

        envelope = [
            float(np.mean(np.abs(chunk)))
            for i in range(0, len(audio), samples_per_frame)
            if len(chunk := audio[i:i + samples_per_frame]) > 0
        ]
        return envelope
    except Exception as e:
        print(f"Error loading audio envelope: {e}")
        return []

# =====================
# SVG -> PIL IMAGE
# =====================
def svg_tree_to_image(tree, width, height):
    """Mengonversi pohon lxml SVG menjadi gambar PIL."""
    png_data = cairosvg.svg2png(
        bytestring=etree.tostring(tree),
        output_width=width,
        output_height=height
    )
    return Image.open(BytesIO(png_data)).convert("RGBA")

# =====================
# RENDER CORE
# =====================
def render_all(timeline, output_video):
    """Merender seluruh timeline animasi, menangkap error dari FFmpeg."""
    W, H = timeline.get("width", 720), timeline.get("height", 1280)
    fps = timeline.get("fps", 12)

    envelope = load_audio_envelope("output/audio.wav", fps)
    
    character_svg_trees = {}
    for char in timeline.get("characters", []):
        svg_path = char.get("svg")
        if not svg_path or not os.path.exists(svg_path):
            alt_path = os.path.join("assets", "characters", os.path.basename(svg_path))
            if os.path.exists(alt_path):
                svg_path = alt_path
            else:
                raise FileNotFoundError(f"File SVG '{svg_path}' untuk karakter '{char.get('id')}' tidak ditemukan.")
        character_svg_trees[char["id"]] = etree.parse(svg_path)

    command = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-pix_fmt", "rgba",
        "-s", f"{W}x{H}",
        "-r", str(fps),
        "-i", "-",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        output_video
    ]
    
    print(f"Starting FFmpeg with command: {' '.join(command)}")
    
    ffmpeg_process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

    frame_idx = 0
    total_frames = sum(int(s.get("duration", 0) * fps) for s in timeline.get("scenes", []))

    try:
        for scene in timeline.get("scenes", []):
            scene_frames = int(scene.get("duration", 0) * fps)
            for _ in range(scene_frames):
                if frame_idx >= total_frames: continue
                
                frame = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                
                for char_in_scene in timeline["characters"]:
                    char_id = char_in_scene["id"]
                    base_tree = character_svg_trees[char_id]
                    
                    is_speaking = char_id == scene.get("speaker")
                    mouth_openness = envelope[min(frame_idx, len(envelope) - 1)] if is_speaking and envelope else 0.0
                    
                    char_tree = apply_emotion(
                        base_tree=base_tree,
                        emotion=scene.get("emotion", "neutral"),
                        mouth_open=mouth_openness,
                        frame=frame_idx,
                        fps=fps,
                        gesture=scene.get("gesture")
                    )
                    
                    char_img = svg_tree_to_image(char_tree, W, H)
                    
                    x_pos = char_in_scene.get("x", 0) - (char_img.width // 2)
                    y_pos = H - char_img.height
                    
                    frame.paste(char_img, (x_pos, y_pos), char_img)

                ffmpeg_process.stdin.write(frame.tobytes())
                frame_idx += 1
        
    except BrokenPipeError:
        print("\n!!! BrokenPipeError: FFmpeg process terminated unexpectedly. !!!")
        print("This usually means ffmpeg encountered an error and closed the stream.")
        pass
    
    except Exception as e:
        print(f"\n!!! An unexpected error occurred during frame writing: {e} !!!")
        raise

    finally:
        # communicate() sends remaining data, waits for process to terminate,
        # and reads stdout/stderr. It also handles closing the pipes.
        stdout_data, stderr_data = ffmpeg_process.communicate()
        
        if ffmpeg_process.returncode != 0:
            print("\n--- FFMPEG ERROR LOG (return code was not 0) ---")
            if stderr_data:
                print(stderr_data.decode('utf-8', errors='ignore'))
            else:
                print("FFmpeg exited with an error, but stderr was empty.")
            print("--------------------------------------------------")
            raise RuntimeError(f"FFmpeg failed with exit code {ffmpeg_process.returncode}. See log above for details.")
        else:
            print("\nFFmpeg process completed successfully.")
