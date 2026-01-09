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
            audio = np.frombuffer(wf.readframes(n_frames), dtype=np.int16)

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
    """Merender seluruh timeline animasi menjadi file video."""
    W, H = timeline.get("width", 1080), timeline.get("height", 1920)
    fps = timeline.get("fps", 12)

    # Memuat amplop audio untuk animasi mulut
    envelope = load_audio_envelope("output/audio.wav", fps)

    # Memuat semua pohon SVG karakter ke dalam memori untuk efisiensi
    character_svg_trees = {}
    for char in timeline.get("characters", []):
        svg_path = char.get("svg")
        if not svg_path or not os.path.exists(svg_path):
            raise FileNotFoundError(f"File SVG '{svg_path}' untuk karakter '{char.get('id')}' tidak ditemukan.")
        character_svg_trees[char["id"]] = etree.parse(svg_path)

    # Menyiapkan proses FFmpeg
    ffmpeg_process = subprocess.Popen([
        "ffmpeg", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgba",
        "-s", f"{W}x{H}",
        "-r", str(fps),
        "-i", "-",  # Membaca frame dari stdin
        "-i", "output/audio.wav", # Menambahkan audio yang sudah digabungkan
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-strict", "experimental",
        "-shortest", # Selesaikan encoding saat stream terpendek (audio/video) selesai
        output_video
    ], stdin=subprocess.PIPE)

    total_frames = sum(int(s.get("duration", 0) * fps) for s in timeline.get("scenes", []))
    frame_idx = 0

    for scene in timeline.get("scenes", []):
        # Logika untuk background (jika ada)
        # bg_img = ... (bisa ditambahkan nanti)
        
        scene_frames = int(scene.get("duration", 0) * fps)

        for _ in range(scene_frames):
            if frame_idx >= total_frames: continue

            # Frame dasar adalah gambar transparan
            frame = Image.new("RGBA", (W, H), (0, 0, 0, 0))

            for char_in_scene in timeline["characters"]:
                char_id = char_in_scene["id"]
                base_tree = character_svg_trees[char_id]

                # Tentukan apakah karakter sedang berbicara
                is_speaking = char_id == scene.get("speaker")
                mouth_openness = envelope[min(frame_idx, len(envelope) - 1)] if is_speaking else 0.0

                # Terapkan emosi dan gerakan ke SVG
                char_tree = apply_emotion(
                    base_tree=base_tree,
                    emotion=scene.get("emotion", "neutral"),
                    mouth_open=mouth_openness,
                    frame=frame_idx, fps=fps,
                    gesture=scene.get("gesture")
                )
                
                # Render SVG yang telah dimodifikasi menjadi gambar
                char_img = svg_tree_to_image(char_tree, W, H)

                # Gabungkan gambar karakter ke frame utama
                # Posisi x diambil langsung dari timeline
                x_pos = char_in_scene.get("x", 0) - (char_img.width // 2)
                y_pos = H - char_img.height # Asumsi karakter di bagian bawah
                
                frame.paste(char_img, (x_pos, y_pos), char_img) # Menggunakan paste untuk transparansi

            # Tulis frame ke FFmpeg
            ffmpeg_process.stdin.write(frame.tobytes())
            frame_idx += 1

    # Tutup proses FFmpeg
    ffmpeg_process.stdin.close()
    ffmpeg_process.wait()
