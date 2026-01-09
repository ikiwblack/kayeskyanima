import os
import math
import json
from tqdm import tqdm
from PIL import Image
import numpy as np
from cairosvg import svg2png
import subprocess

# Fungsi untuk mengonversi SVG ke PNG dengan ukuran yang diinginkan
def svg_to_pil(svg_string, width, height):
    # Ukuran yang diinginkan bisa lebih besar untuk kualitas yang lebih baik saat penskalaan
    png_data = svg2png(bytestring=svg_string.encode('utf-8'), output_width=width, output_height=height)
    # Buat direktori sementara jika belum ada
    if not os.path.exists("temp"):
        os.makedirs("temp")
    temp_png_path = "temp/temp_char.png"
    with open(temp_png_path, "wb") as f:
        f.write(png_data)
    return Image.open(temp_png_path).convert("RGBA")

# Fungsi untuk merender semua frame
def render_all(timeline, output_video):
    W, H = timeline["width"], timeline["height"]

    # Muat semua SVG karakter ke dalam memori untuk efisiensi
    char_svgs = {}
    for char in timeline["characters"]:
        with open(char["svg"], "r", encoding='utf-8') as f:
            char_svgs[char["id"]] = f.read()

    # FIX: Muat gambar latar belakang dari timeline
    background_img = None
    if timeline.get("background") and os.path.exists(timeline["background"]):
        print(f"🖼️ Memuat latar belakang dari: {timeline['background']}")
        with open(timeline["background"], "r", encoding='utf-8') as f:
            bg_svg_string = f.read()
        # Render latar belakang sekali dengan resolusi penuh
        background_img = svg_to_pil(bg_svg_string, W, H)
    else:
        print("⚠️ Latar belakang tidak ditemukan atau tidak ditentukan. Menggunakan latar belakang hitam.")

    # Mulai proses rendering dengan FFmpeg
    command = [
        'ffmpeg',
        '-y',  # Timpa file output jika ada
        '-f', 'rawvideo',
        '-vcodec', 'rawvideo',
        '-s', f'{W}x{H}',  # Ukuran frame
        '-pix_fmt', 'rgba', # Format pixel
        '-r', '24',  # Frame rate
        '-i', '-',  # Input dari stdin
        '-c:v', 'libx264',
        '-pix_fmt', 'yuv420p',
        '-crf', '18', # Kualitas (lower is better)
        output_video
    ]
    pipe = subprocess.Popen(command, stdin=subprocess.PIPE)

    total_duration = sum(s["duration"] for s in timeline["scenes"])
    pbar = tqdm(total=total_duration, unit="s", desc="🎥 Merender Video")

    current_time = 0
    for scene in timeline["scenes"]:
        num_frames = int(scene["duration"] * 24) # 24 fps
        if num_frames == 0:
            continue

        speaker_id = scene.get("speaker")
        char_svg_string = char_svgs.get(speaker_id)

        for i in range(num_frames):
            # Buat frame dasar
            if background_img:
                frame = background_img.copy()
            else:
                frame = Image.new("RGBA", (W, H), (0, 0, 0, 255)) # Latar hitam jika tidak ada

            # Jika ada pembicara di adegan ini, gambar karakternya
            if char_svg_string:
                # Logika animasi sederhana (gerak mulut)
                # Buka-tutup mulut setiap 4 frame
                is_mouth_open = (i % 8) < 4
                
                # Modifikasi SVG untuk animasi mulut
                if is_mouth_open:
                    modified_svg = char_svg_string.replace('id="mouth"', 'id="mouth" style="transform: scaleY(1);"')
                else:
                    modified_svg = char_svg_string.replace('id="mouth"', 'id="mouth" style="transform: scaleY(0.1); transform-origin: center;"')

                # Render karakter SVG ke gambar PIL
                # Render dengan resolusi yang sesuai untuk mempertahankan kualitas
                char_img = svg_to_pil(modified_svg, int(W * 0.8), int(H * 0.8)) 

                # Tempel karakter ke tengah frame
                char_w, char_h = char_img.size
                pos_x = (W - char_w) // 2
                pos_y = (H - char_h) // 2
                frame.paste(char_img, (pos_x, pos_y), char_img) # Gunakan alpha mask dari char_img

            # Tulis frame ke pipa FFmpeg
            pipe.stdin.write(frame.tobytes())

        pbar.update(scene["duration"])
        current_time += scene["duration"]

    pbar.close()
    pipe.stdin.close()
    pipe.wait()
    print("✅ Rendering video tanpa audio selesai.")
