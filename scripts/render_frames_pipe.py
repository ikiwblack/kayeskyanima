import os
import json
import random
import subprocess
from tqdm import tqdm
from PIL import Image
from cairosvg import svg2png
import math

# --- Konstanta Animasi ---
BLINK_INTERVAL_SECONDS = 3.5
BLINK_DURATION_FRAMES = 3
FPS = 24

def svg_to_pil(svg_string, width, height):
    """Fungsi utilitas untuk merender SVG ke gambar PIL."""
    # Menghindari error jika width/height adalah nol atau negatif
    if width <= 0 or height <= 0:
        width, height = 1, 1 # Fallback ke ukuran minimal
        
    png_data = svg2png(bytestring=svg_string.encode('utf-8'), output_width=int(width), output_height=int(height))
    temp_dir = "temp"
    os.makedirs(temp_dir, exist_ok=True)
    temp_png_path = os.path.join(temp_dir, f"temp_char_{random.randint(1,10000)}.png")
    with open(temp_png_path, "wb") as f:
        f.write(png_data)
    img = Image.open(temp_png_path).convert("RGBA")
    os.remove(temp_png_path)
    return img

def find_current_scene(timeline, global_frame_index):
    """Menemukan adegan yang sedang berlangsung berdasarkan indeks frame global."""
    accumulated_frames = 0
    for scene in timeline["scenes"]:
        num_frames = int(scene["duration"] * FPS)
        if global_frame_index < accumulated_frames + num_frames:
            # Mengembalikan adegan dan indeks frame lokal di dalam adegan itu
            local_frame_index = global_frame_index - accumulated_frames
            return scene, local_frame_index
        accumulated_frames += num_frames
    return timeline["scenes"][-1], global_frame_index - (accumulated_frames - int(timeline["scenes"][-1]["duration"]*FPS)) # Fallback ke adegan terakhir

def render_all(timeline, output_video):
    W, H = timeline["width"], timeline["height"]

    # 1. SETUP AWAL
    char_data_map = {char["id"]: char for char in timeline["characters"]}
    
    # --- BARU: Muat semua string SVG default dari semua karakter ---
    char_svg_strings = {}
    for char_id, char_data in char_data_map.items():
        svg_path = char_data.get("svgs", {}).get("default")
        if svg_path and os.path.exists(svg_path):
            with open(svg_path, "r", encoding='utf-8') as f:
                char_svg_strings[char_id] = f.read()
        else:
            print(f"⚠️ SVG default untuk {char_id} tidak ditemukan di '{svg_path}'. Karakter ini mungkin tidak muncul.")

    # --- BARU: Tentukan posisi X yang tetap dan terdistribusi untuk SEMUA karakter ---
    character_positions = {}
    num_chars = len(char_data_map)
    slot_width = W / max(1, num_chars) # Hindari pembagian dengan nol
    for i, char_id in enumerate(char_data_map.keys()):
        # Tentukan posisi acak di dalam "slot" yang telah ditentukan untuk setiap karakter
        slot_start = i * slot_width
        # Beri sedikit ruang agar tidak terlalu mepet ke tepi slot
        random_pos_in_slot = random.uniform(slot_start + slot_width * 0.15, slot_start + slot_width * 0.85)
        character_positions[char_id] = int(random_pos_in_slot)

    # --- BARU: Inisialisasi jadwal kedipan untuk SEMUA karakter ---
    blink_schedules = {}
    for char_id in char_data_map.keys():
        first_blink_delay = random.uniform(0.5, BLINK_INTERVAL_SECONDS) * FPS
        blink_schedules[char_id] = int(first_blink_delay)

    # 2. SETUP VIDEO & RENDER
    command = [
        'ffmpeg', '-y', '-f', 'rawvideo', '-vcodec', 'rawvideo',
        '-s', f'{W}x{H}', '-pix_fmt', 'rgba', '-r', str(FPS), '-i', '-',
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', output_video
    ]
    pipe = subprocess.Popen(command, stdin=subprocess.PIPE)

    # Render latar belakang sekali
    background_img = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    if timeline.get("background") and os.path.exists(timeline["background"]):
        with open(timeline["background"], "r", encoding='utf-8') as f:
            bg_svg_string = f.read()
        background_img = svg_to_pil(bg_svg_string, W, H)
    else:
        print("⚠️ Latar belakang tidak ditemukan. Menggunakan latar belakang hitam.")
    
    total_frames = sum(int(s.get("duration", 0) * FPS) for s in timeline["scenes"])
    
    # 3. LOOP FRAME-BY-FRAME UTAMA
    for global_frame_index in tqdm(range(total_frames), desc="🎥 Merender Video"):
        
        frame = background_img.copy()
        current_scene, local_frame_index = find_current_scene(timeline, global_frame_index)
        speaker_id = current_scene.get("speaker")

        # --- BARU: Loop melalui SEMUA karakter untuk digambar di setiap frame ---
        for char_id, char_data in char_data_map.items():
            
            is_speaker = (char_id == speaker_id)
            svg_to_render = None

            # Tentukan SVG mana yang akan digunakan: emosi untuk pembicara, default untuk pendengar
            if is_speaker:
                emotion = current_scene.get("emotion", "neutral")
                svg_path = char_data.get("svgs", {}).get(emotion, char_data.get("svgs", {}).get("default"))
                if svg_path and os.path.exists(svg_path):
                    with open(svg_path, "r", encoding='utf-8') as f:
                        svg_to_render = f.read()
                else:
                    print(f"⚠️ SVG untuk {char_id} (emosi: {emotion}) tidak ditemukan!")
                    svg_to_render = char_svg_strings.get(char_id) # Fallback ke default
            else:
                svg_to_render = char_svg_strings.get(char_id)

            if not svg_to_render:
                continue # Lanjut ke karakter berikutnya jika tidak ada SVG

            modified_svg = svg_to_render
            
            # --- Terapkan Animasi ---
            
            # 1. Animasi Mulut (HANYA untuk pembicara)
            if is_speaker:
                is_mouth_open = (local_frame_index % 8) < 4
                if is_mouth_open:
                    modified_svg = modified_svg.replace('id="mouth"', 'id="mouth" style="transform: scaleY(1);"')
                else:
                    modified_svg = modified_svg.replace('id="mouth"', 'id="mouth" style="transform: scaleY(0.1); transform-origin: center;"')
            else:
                # Pastikan mulut pendengar selalu tertutup
                modified_svg = modified_svg.replace('id="mouth"', 'id="mouth" style="transform: scaleY(0.1); transform-origin: center;"')

            # 2. Animasi Kedipan (untuk SEMUA karakter)
            if global_frame_index >= blink_schedules[char_id]:
                if global_frame_index < blink_schedules[char_id] + BLINK_DURATION_FRAMES:
                    modified_svg = modified_svg.replace('id="eyes"', 'id="eyes" style="transform: scaleY(0.05); transform-origin: center;"')
                else:
                    next_blink_delay = random.uniform(BLINK_INTERVAL_SECONDS * 0.5, BLINK_INTERVAL_SECONDS * 1.5) * FPS
                    blink_schedules[char_id] = global_frame_index + int(next_blink_delay)

            # --- Render & Tempel Karakter ---
            char_render_w = int(W * 0.3)
            char_render_h = int(char_render_w * 1.5)
            
            char_img = svg_to_pil(modified_svg, char_render_w, char_render_h)
            
            pos_x = character_positions[char_id]
            pos_y = H - char_img.size[1] - int(H * 0.05)
            final_pos_x = pos_x - char_img.size[0] // 2
            final_pos_x = max(0, min(final_pos_x, W - char_img.size[0]))
            
            frame.paste(char_img, (final_pos_x, pos_y), char_img)

        # Tulis frame yang sudah lengkap ke FFmpeg
        pipe.stdin.write(frame.tobytes())

    # 4. FINALISASI
    pipe.stdin.close()
    pipe.wait()
    if os.path.exists("temp"):
        import shutil
        shutil.rmtree("temp")
    print("✅ Rendering video percakapan selesai.")

