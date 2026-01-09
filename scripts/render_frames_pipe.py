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
        print(f"Peringatan: File audio tidak ditemukan di {wav_path}. Animasi mulut akan dinonaktifkan.")
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
        print(f"Error saat memuat amplop audio: {e}")
        return []

# =====================
# SVG -> PIL IMAGE
# =====================
def svg_tree_to_image(tree):
    """FIX: Mengonversi pohon lxml SVG menjadi gambar PIL menggunakan ukuran aslinya."""
    # Hapus parameter width/height untuk membiarkan cairosvg menggunakan ukuran intrinsik SVG
    png_data = cairosvg.svg2png(
        bytestring=etree.tostring(tree)
    )
    return Image.open(BytesIO(png_data)).convert("RGBA")

# =====================
# RENDER CORE
# =====================
def render_all(timeline, output_video):
    """Merender seluruh timeline animasi, dengan perbaikan untuk latar belakang dan penumpukan."""
    W, H = timeline.get("width", 1080), timeline.get("height", 1920)
    fps = timeline.get("fps", 12)

    envelope = load_audio_envelope("output/audio.wav", fps)
    
    # --- FIX: Muat Latar Belakang ---
    background_img = None
    # Coba cari path latar belakang dari karakter pertama sebagai fallback
    if timeline.get("characters") and timeline["characters"][0].get("background"):
        bg_path = timeline["characters"][0]["background"]
        if os.path.exists(bg_path):
            background_img = Image.open(bg_path).convert("RGBA").resize((W, H))
        else:
            print(f"Peringatan: File latar belakang '{bg_path}' tidak ditemukan.")

    # Jika tidak ada latar belakang, buat latar belakang hitam solid
    if not background_img:
        background_img = Image.new("RGBA", (W, H), (0, 0, 0, 255))

    # Muat semua pohon SVG dasar sekali
    character_svg_trees = {}
    for char in timeline.get("characters", []):
        svg_path = char.get("svg")
        if not svg_path or not os.path.exists(svg_path):
            raise FileNotFoundError(f"File SVG '{svg_path}' untuk karakter '{char.get('id')}' tidak ditemukan.")
        character_svg_trees[char["id"]] = etree.parse(svg_path)

    command = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", output_video
    ]
    
    ffmpeg_process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

    frame_idx = 0
    total_frames = sum(int(s.get("duration", 0) * fps) for s in timeline.get("scenes", []))
    character_image_cache = {}

    try:
        for scene_idx, scene in enumerate(timeline.get("scenes", [])):
            scene_frames = int(scene.get("duration", 0) * fps)
            print(f"Merender Scene {scene_idx + 1}/{len(timeline.get('scenes', []))} ({scene_frames} frames)")

            for _ in range(scene_frames):
                if frame_idx >= total_frames: continue
                
                # --- FIX: Mulai dengan salinan gambar latar belakang ---
                frame = background_img.copy()
                
                # Loop melalui semua karakter untuk menempatkan mereka di panggung
                for char_in_scene in timeline["characters"]:
                    char_id = char_in_scene["id"]
                    
                    is_speaking = char_id == scene.get("speaker")
                    emotion = scene.get("emotion", "neutral") if is_speaking else "neutral"
                    gesture = scene.get("gesture")
                    mouth_openness = envelope[min(frame_idx, len(envelope) - 1)] if is_speaking and envelope else 0.0
                    mouth_discrete = round(mouth_openness, 1)

                    cache_key = (char_id, emotion, gesture, mouth_discrete)

                    if cache_key in character_image_cache:
                        char_img = character_image_cache[cache_key]
                    else:
                        base_tree = character_svg_trees[char_id]
                        char_tree = apply_emotion(
                            base_tree=base_tree, emotion=emotion, mouth_open=mouth_openness,
                            frame=frame_idx, fps=fps, gesture=gesture
                        )
                        
                        # --- FIX: Render SVG dengan ukuran aslinya ---
                        char_img = svg_tree_to_image(char_tree)
                        character_image_cache[cache_key] = char_img

                    # --- LOGIKA PENEMPATAN YANG SEKARANG BERFUNGSI ---
                    # Pusatkan karakter pada koordinat x-nya
                    x_pos = char_in_scene.get("x", W // 2) - (char_img.width // 2)
                    # Tempatkan bagian bawah karakter di bagian bawah layar (atau pada y jika ditentukan)
                    y_pos = char_in_scene.get("y", H - char_img.height)
                    frame.paste(char_img, (x_pos, y_pos), char_img)

                ffmpeg_process.stdin.write(frame.tobytes())
                frame_idx += 1
        
        print(f"\nSelesai menulis semua {frame_idx} frames.")

    finally:
        stdout_data, stderr_data = ffmpeg_process.communicate()
        if ffmpeg_process.returncode != 0:
            print("\n--- FFMPEG ERROR LOG ---")
            print(stderr_data.decode('utf-8', errors='ignore'))
            raise RuntimeError(f"FFmpeg gagal dengan kode keluar {ffmpeg_process.returncode}.")
        else:
            print("\nProses FFmpeg berhasil diselesaikan.")
