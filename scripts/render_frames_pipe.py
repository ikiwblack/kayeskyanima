import os
import json
import random
import subprocess
from tqdm import tqdm
from PIL import Image
from cairosvg import svg2png
import sys
import xml.etree.ElementTree as ET

# --- Konstanta Animasi ---
BLINK_INTERVAL_SECONDS = 3.5
BLINK_DURATION_FRAMES = 3
FPS = 24

def set_element_style(svg_content, element_id, style_string):
    """
    Secara aman mengatur atribut style untuk elemen SVG menggunakan parser XML.
    Ini adalah metode yang andal untuk menghindari error `duplicate attribute`.
    """
    try:
        # Daftarkan namespace default untuk menghindari {http://www.w3.org/2000/svg} di tag
        ET.register_namespace("", "http://www.w3.org/2000/svg")
        root = ET.fromstring(svg_content)
        
        # Gunakan findall dengan wildcard namespace untuk menemukan elemen berdasarkan ID
        # Ini lebih kuat daripada mengasumsikan tidak ada namespace
        target_elements = root.findall(f".//*[@id='{element_id}']")
        
        if target_elements:
            # Timpa atau tambahkan atribut style
            target_elements[0].set("style", style_string)
        
        # Kembalikan konten sebagai string
        return ET.tostring(root, encoding='unicode')
    except ET.ParseError as e:
        print(f"XML Parse Error: {e} in SVG content for element {element_id}. Returning original SVG.")
        return svg_content # Kembalikan konten asli jika ada error parsing

def svg_to_pil(svg_string, width, height):
    """Fungsi utilitas untuk merender SVG ke gambar PIL."""
    if width <= 0 or height <= 0:
        width, height = 1, 1
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
            local_frame_index = global_frame_index - accumulated_frames
            return scene, local_frame_index
        accumulated_frames += num_frames
    return timeline["scenes"][-1], global_frame_index - (accumulated_frames - int(timeline["scenes"][-1]["duration"]*FPS))

def render_all(timeline, output_video):
    W, H = timeline["width"], timeline["height"]
    char_data_map = {char["id"]: char for char in timeline["characters"]}
    char_svg_strings = {}
    for char_id, char_data in char_data_map.items():
        svg_path = char_data.get("svgs", {}).get("default")
        if svg_path and os.path.exists(svg_path):
            with open(svg_path, "r", encoding='utf-8') as f:
                char_svg_strings[char_id] = f.read()
        else:
            print(f"⚠️ SVG default untuk {char_id} tidak ditemukan di '{svg_path}'.")

    character_positions = {}
    num_chars = len(char_data_map)
    slot_width = W / max(1, num_chars)
    for i, char_id in enumerate(char_data_map.keys()):
        slot_start = i * slot_width
        random_pos_in_slot = random.uniform(slot_start + slot_width * 0.15, slot_start + slot_width * 0.85)
        character_positions[char_id] = int(random_pos_in_slot)

    blink_schedules = {}
    for char_id in char_data_map.keys():
        first_blink_delay = random.uniform(0.5, BLINK_INTERVAL_SECONDS) * FPS
        blink_schedules[char_id] = int(first_blink_delay)

    command = [
        'ffmpeg', '-y', '-f', 'rawvideo', '-vcodec', 'rawvideo',
        '-s', f'{W}x{H}', '-pix_fmt', 'rgba', '-r', str(FPS), '-i', '-',
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', output_video
    ]
    pipe = subprocess.Popen(command, stdin=subprocess.PIPE)

    background_img = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    if timeline.get("background") and os.path.exists(timeline["background"]):
        with open(timeline["background"], "r", encoding='utf-8') as f:
            bg_svg_string = f.read()
        background_img = svg_to_pil(bg_svg_string, W, H)
    else:
        print("⚠️ Latar belakang tidak ditemukan. Menggunakan latar belakang hitam.")
    
    total_frames = sum(int(s.get("duration", 0) * FPS) for s in timeline["scenes"])
    
    for global_frame_index in tqdm(range(total_frames), desc="🎥 Merender Video"):
        frame = background_img.copy()
        current_scene, local_frame_index = find_current_scene(timeline, global_frame_index)
        speaker_id = current_scene.get("speaker")

        for char_id, char_data in char_data_map.items():
            is_speaker = (char_id == speaker_id)
            svg_to_render = None
            if is_speaker:
                emotion = current_scene.get("emotion", "neutral")
                svg_path = char_data.get("svgs", {}).get(emotion, char_data.get("svgs", {}).get("default"))
                if svg_path and os.path.exists(svg_path):
                    with open(svg_path, "r", encoding='utf-8') as f:
                        svg_to_render = f.read()
                else:
                    print(f"⚠️ SVG untuk {char_id} (emosi: {emotion}) tidak ditemukan!")
                    svg_to_render = char_svg_strings.get(char_id)
            else:
                svg_to_render = char_svg_strings.get(char_id)

            if not svg_to_render:
                continue

            modified_svg = svg_to_render
            
            # --- Terapkan Animasi ---
            
            # 1. Animasi Mulut
            mouth_style = 'transform: scaleY(0.1); transform-origin: center;'
            if is_speaker and (local_frame_index % 8) < 4:
                mouth_style = 'transform: scaleY(1);'
            modified_svg = set_element_style(modified_svg, 'mouth', mouth_style)

            # 2. Animasi Kedipan
            eye_style = 'transform: scaleY(1);' # Default mata terbuka
            is_blinking = global_frame_index >= blink_schedules[char_id] and global_frame_index < blink_schedules[char_id] + BLINK_DURATION_FRAMES
            if is_blinking:
                eye_style = 'transform: scaleY(0.05); transform-origin: center;'
            modified_svg = set_element_style(modified_svg, 'eyes', eye_style)

            # Jadwalkan ulang kedipan setelah selesai
            if global_frame_index >= blink_schedules[char_id] + BLINK_DURATION_FRAMES:
                next_blink_delay = random.uniform(BLINK_INTERVAL_SECONDS * 0.5, BLINK_INTERVAL_SECONDS * 1.5) * FPS
                blink_schedules[char_id] = global_frame_index + int(next_blink_delay)

            char_render_w = int(W * 0.3)
            char_render_h = int(char_render_w * 1.5)
            char_img = svg_to_pil(modified_svg, char_render_w, char_render_h)
            
            pos_x = character_positions[char_id]
            pos_y = H - char_img.size[1] - int(H * 0.05)
            final_pos_x = pos_x - char_img.size[0] // 2
            final_pos_x = max(0, min(final_pos_x, W - char_img.size[0]))
            
            frame.paste(char_img, (final_pos_x, pos_y), char_img)

        pipe.stdin.write(frame.tobytes())

    pipe.stdin.close()
    pipe.wait()
    if os.path.exists("temp"):
        import shutil
        shutil.rmtree("temp")
    print("✅ Rendering video percakapan selesai.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python render_frames_pipe.py <path_to_timeline.json>")
        sys.exit(1)

    timeline_path = sys.argv[1]
    output_video_path = "output.mp4" 

    try:
        with open(timeline_path, 'r', encoding='utf-8') as f:
            timeline_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Timeline file not found at {timeline_path}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {timeline_path}")
        sys.exit(1)

    render_all(timeline_data, output_video_path)
