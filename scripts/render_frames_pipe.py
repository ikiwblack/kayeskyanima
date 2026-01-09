import os
import json
import random
import subprocess
from tqdm import tqdm
from PIL import Image
from cairosvg import svg2png

# --- Konstanta Animasi ---
BLINK_INTERVAL_SECONDS = 3.5  # Rata-rata waktu antar kedipan
BLINK_DURATION_FRAMES = 3   # Durasi kedipan dalam frame (sekitar 0.125 detik pada 24 fps)
FPS = 24

def svg_to_pil(svg_string, width, height):
    # Fungsi utilitas untuk merender SVG ke gambar PIL
    png_data = svg2png(bytestring=svg_string.encode('utf-8'), output_width=width, output_height=height)
    temp_dir = "temp"
    os.makedirs(temp_dir, exist_ok=True)
    temp_png_path = os.path.join(temp_dir, f"temp_char_{random.randint(1,10000)}.png")
    with open(temp_png_path, "wb") as f:
        f.write(png_data)
    img = Image.open(temp_png_path).convert("RGBA")
    os.remove(temp_png_path) # Langsung hapus setelah dimuat
    return img

def render_all(timeline, output_video):
    W, H = timeline["width"], timeline["height"]

    # 1. Muat data karakter ke dalam peta untuk akses mudah
    char_data_map = {char["id"]: char for char in timeline["characters"]}

    # 2. Render latar belakang sekali saja
    background_img = None
    if timeline.get("background") and os.path.exists(timeline["background"]):
        with open(timeline["background"], "r", encoding='utf-8') as f:
            bg_svg_string = f.read()
        background_img = svg_to_pil(bg_svg_string, W, H)
    else:
        print("⚠️ Latar belakang tidak ditemukan. Menggunakan latar belakang hitam.")

    # Setup FFmpeg pipe
    command = [
        'ffmpeg', '-y', '-f', 'rawvideo', '-vcodec', 'rawvideo',
        '-s', f'{W}x{H}', '-pix_fmt', 'rgba', '-r', str(FPS), '-i', '-',
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', output_video
    ]
    pipe = subprocess.Popen(command, stdin=subprocess.PIPE)

    # --- Inisialisasi State Animasi ---
    total_duration = sum(s.get("duration", 0) for s in timeline["scenes"])
    pbar = tqdm(total=total_duration, unit="s", desc="🎥 Merender Video")
    
    last_positions = {}
    blink_schedules = {} # Jadwal kedipan untuk setiap karakter
    global_frame_index = 0

    for scene in timeline["scenes"]:
        num_frames = int(scene["duration"] * FPS)
        if num_frames == 0:
            continue

        speaker_id = scene.get("speaker")
        char_data = char_data_map.get(speaker_id)
        
        # --- Logika Pemilihan SVG Berdasarkan Emosi ---
        char_svg_string = None
        if char_data:
            emotion = scene.get("emotion", "neutral")
            svg_paths = char_data.get("svgs", {})
            svg_path = svg_paths.get(emotion, svg_paths.get("default"))
            if svg_path and os.path.exists(svg_path):
                with open(svg_path, "r", encoding='utf-8') as f:
                    char_svg_string = f.read()
            else:
                print(f"⚠️ SVG untuk {speaker_id} (emosi: {emotion}) tidak ditemukan di '{svg_path}'")

        # --- Atur Posisi Karakter ---
        if speaker_id and speaker_id not in last_positions:
            pos_x_random = int(W * random.uniform(0.15, 0.85))
            last_positions[speaker_id] = pos_x_random
        pos_x = last_positions.get(speaker_id, W // 2)

        # --- Atur Jadwal Kedipan ---
        if speaker_id and speaker_id not in blink_schedules:
            first_blink_delay = random.uniform(0.5, BLINK_INTERVAL_SECONDS) * FPS
            blink_schedules[speaker_id] = global_frame_index + int(first_blink_delay)

        # --- Loop Per Frame untuk Adegan Ini ---
        for i in range(num_frames):
            frame = background_img.copy() if background_img else Image.new("RGBA", (W, H), (0, 0, 0, 255))

            if char_svg_string:
                modified_svg = char_svg_string

                # Animasi 1: Gerak Mulut
                is_mouth_open = (i % 8) < 4
                if is_mouth_open:
                    modified_svg = modified_svg.replace('id="mouth"', 'id="mouth" style="transform: scaleY(1);"')
                else:
                    modified_svg = modified_svg.replace('id="mouth"', 'id="mouth" style="transform: scaleY(0.1); transform-origin: center;"')

                # Animasi 2: Berkedip
                if speaker_id in blink_schedules and global_frame_index >= blink_schedules[speaker_id]:
                    if global_frame_index < blink_schedules[speaker_id] + BLINK_DURATION_FRAMES:
                        modified_svg = modified_svg.replace('id="eyes"', 'id="eyes" style="transform: scaleY(0.05); transform-origin: center;"')
                    else:
                        next_blink_delay = random.uniform(BLINK_INTERVAL_SECONDS * 0.5, BLINK_INTERVAL_SECONDS * 1.5) * FPS
                        blink_schedules[speaker_id] = global_frame_index + int(next_blink_delay)

                # --- PENYESUAIAN UKURAN KARAKTER ---
                # Ukuran lebar karakter sekarang 30% dari lebar layar agar muat lebih banyak.
                # Aspek rasio asli (200x300) dipertahankan untuk menghindari distorsi.
                char_render_w = int(W * 0.3)
                char_render_h = int(char_render_w * 1.5)  # Mempertahankan rasio 2:3 (lebar*1.5 = tinggi)

                # Render SVG yang sudah dimodifikasi dengan ukuran baru yang proporsional
                char_img = svg_to_pil(modified_svg, char_render_w, char_render_h)

                # Tempel karakter ke frame
                pos_y = H - char_img.size[1] - int(H * 0.05)  # Posisi Y sedikit di atas bagian bawah
                final_pos_x = pos_x - char_img.size[0] // 2

                # Pastikan karakter tidak keluar dari layar
                final_pos_x = max(0, min(final_pos_x, W - char_img.size[0]))

                frame.paste(char_img, (final_pos_x, pos_y), char_img)

            pipe.stdin.write(frame.tobytes())
            global_frame_index += 1

        pbar.update(scene["duration"])

    # --- Finalisasi ---
    pbar.close()
    pipe.stdin.close()
    pipe.wait()
    if os.path.exists("temp"):
        import shutil
        shutil.rmtree("temp")
    print("✅ Rendering video tanpa audio selesai.")
