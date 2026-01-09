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
# RENDER CORE (WITH CACHING)
# =====================
def render_all(timeline, output_video):
    """Merender seluruh timeline animasi, dengan caching untuk gambar karakter."""
    W, H = timeline.get("width", 720), timeline.get("height", 1280)
    fps = timeline.get("fps", 12)

    envelope = load_audio_envelope("output/audio.wav", fps)
    
    # Muat semua pohon SVG dasar sekali
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
        "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", output_video
    ]
    
    print(f"Starting FFmpeg with command: {' '.join(command)}")
    ffmpeg_process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

    frame_idx = 0
    total_frames = sum(int(s.get("duration", 0) * fps) for s in timeline.get("scenes", []))
    
    # Inisialisasi cache untuk gambar karakter yang sudah dirender
    character_image_cache = {}

    try:
        for scene_idx, scene in enumerate(timeline.get("scenes", [])):
            scene_frames = int(scene.get("duration", 0) * fps)
            print(f"Rendering Scene {scene_idx + 1}/{len(timeline.get('scenes', []))} ({scene_frames} frames)")

            for _ in range(scene_frames):
                if frame_idx >= total_frames: continue
                
                # Buat frame kosong
                frame = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                
                # Loop melalui semua karakter yang ADA dalam timeline (bukan hanya yang di scene)
                for char_in_scene in timeline["characters"]:
                    char_id = char_in_scene["id"]
                    
                    # Tentukan status karakter untuk frame ini
                    is_speaking = char_id == scene.get("speaker")
                    emotion = scene.get("emotion", "neutral")
                    gesture = scene.get("gesture")
                    mouth_openness = envelope[min(frame_idx, len(envelope) - 1)] if is_speaking and envelope else 0.0
                    
                    # Discretize mouth openness to improve caching
                    # Round to nearest 0.1, for example. Adjust if needed.
                    mouth_discrete = round(mouth_openness, 1)

                    # Buat kunci cache berdasarkan status visual karakter
                    cache_key = (char_id, emotion, gesture, mouth_discrete)

                    # --- LOGIKA CACHING ---
                    if cache_key in character_image_cache:
                        # Cache Hit: Gunakan gambar yang sudah ada
                        char_img = character_image_cache[cache_key]
                    else:
                        # Cache Miss: Render gambar baru dan simpan di cache
                        base_tree = character_svg_trees[char_id]
                        
                        char_tree = apply_emotion(
                            base_tree=base_tree,
                            emotion=emotion,
                            mouth_open=mouth_openness, # Gunakan nilai asli untuk render
                            frame=frame_idx, 
                            fps=fps,
                            gesture=gesture
                        )
                        
                        # Render SVG ke gambar PIL
                        char_img = svg_tree_to_image(char_tree, W, H)
                        # Simpan di cache
                        character_image_cache[cache_key] = char_img

                    # Tempel gambar karakter ke frame
                    x_pos = char_in_scene.get("x", 0) - (char_img.width // 2)
                    y_pos = H - char_img.height
                    frame.paste(char_img, (x_pos, y_pos), char_img)

                # Kirim frame ke FFmpeg
                ffmpeg_process.stdin.write(frame.tobytes())
                frame_idx += 1
        
        print(f"\nFinished writing all {frame_idx} frames.")
        print(f"Cache Summary: Created {len(character_image_cache)} unique character images.")

    except BrokenPipeError:
        print("\n!!! BrokenPipeError: FFmpeg process terminated unexpectedly. !!!")
        print("This usually means ffmpeg encountered an error and closed the stream.")
        pass
    
    except Exception as e:
        print(f"\n!!! An unexpected error occurred during frame writing: {e} !!!")
        raise

    finally:
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
