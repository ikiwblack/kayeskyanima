import os
import sys
import json
import subprocess
import shutil
from gtts import gTTS

# --- Persiapan Awal ---
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Memeriksa apakah ffmpeg & ffprobe terinstal
if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
    raise RuntimeError("ffmpeg dan ffprobe tidak ditemukan. Harap instal FFmpeg dan pastikan berada di PATH sistem Anda.")

MODE = sys.argv[1] if len(sys.argv) > 1 else "render"

# --- Memuat File Sumber ---
if not os.path.exists("script.txt"):
    raise FileNotFoundError("File script.txt tidak ditemukan.")
with open("script.txt", encoding="utf-8") as f:
    text = f.read().strip()
if not text:
    raise ValueError("Naskah kosong")

if not os.path.exists("characters.json"):
    raise FileNotFoundError("File characters.json tidak ditemukan.")
with open("characters.json", encoding="utf-8") as f:
    characters_data = json.load(f)
characters_map = {char['id']: char for char in characters_data['characters']}

# --- Analisis atau Muat Timeline ---
if os.path.exists("timeline.json") and MODE != "analyze":
    with open("timeline.json", encoding="utf-8") as f:
        timeline = json.load(f)
else:
    from scripts.analyze_text import analyze
    # Default ke 9:16 jika tidak ada, tapi ini biasanya di-override oleh bot
    timeline = analyze(text, '9:16') 

# --- Atur Resolusi & Latar Belakang ---
print("🔧 Mengatur resolusi, latar belakang, dan karakter...")

# FIX: Logika orientasi diperbaiki untuk membaca nilai dari timeline
orientation = timeline.get('orientation', '9:16')
if orientation == '16:9':
    W, H = 1280, 720
    print(f"   -> Orientasi Lanskap (16:9) terdeteksi. Resolusi diatur ke {W}x{H}.")
else:
    W, H = 720, 1280
    print(f"   -> Orientasi Potret (9:16) terdeteksi. Resolusi diatur ke {W}x{H}.")

timeline['width'] = W
timeline['height'] = H

# FIX: Baca dan injeksi path latar belakang ke timeline
timeline["background"] = characters_data.get("background")
if not timeline["background"]:
    print("   -> PERINGATAN: Tidak ada path latar belakang ditemukan di characters.json!")
else:
    print(f"   -> Latar belakang diatur ke: {timeline['background']}")

# Injeksi detail karakter
timeline["characters"] = characters_data["characters"]

# --- Mode Analisis (Hanya Bot) ---
if MODE == "analyze":
    with open("timeline.json", "w", encoding="utf-8") as f:
        json.dump(timeline, f, indent=2, ensure_ascii=False)
    print("Analisis selesai. Timeline disimpan.")
    sys.exit(0)

# =============================================================================
# --- PEMROSESAN AUDIO DENGAN KONTROL NADA (PITCH) ---
# =============================================================================
print("📢 Menghasilkan audio dengan nada spesifik per karakter...")

processed_wav_files = []
character_pitches = {char_id: data.get("pitch", 1.0) for char_id, data in characters_map.items()}

try:
    for i, scene in enumerate(timeline["scenes"]):
        speaker = scene.get("speaker")
        if not speaker or not scene.get("text"):
            scene["duration"] = 0.0
            continue

        print(f"  - Memproses adegan {i+1}/{len(timeline['scenes'])}: {speaker}...")

        temp_mp3 = os.path.join(OUTPUT_DIR, f"_temp_{i}.mp3")
        tts = gTTS(scene["text"], lang="id", slow=False)
        tts.save(temp_mp3)

        pitch = character_pitches.get(speaker, 1.0)
        temp_wav = os.path.join(OUTPUT_DIR, f"_temp_{i}.wav")

        # FIX: Peningkatan rentang pitch dengan `rubberband` untuk kualitas yang lebih baik
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-i", temp_mp3,
            "-filter:a", f"rubberband=pitch={pitch}",
            temp_wav
        ]
        subprocess.run(ffmpeg_cmd, check=True, capture_output=True)
        processed_wav_files.append(temp_wav)

        ffprobe_cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", temp_wav
        ]
        duration_result = subprocess.run(ffprobe_cmd, check=True, capture_output=True, text=True)
        scene["duration"] = float(duration_result.stdout.strip())

        os.remove(temp_mp3)

    print("  - Menggabungkan semua klip audio...")
    concat_list_path = os.path.join(OUTPUT_DIR, "concat_list.txt")
    with open(concat_list_path, "w", encoding="utf-8") as f:
        for wav_file in processed_wav_files:
            # Path harus relatif terhadap direktori CWD atau absolut
            f.write(f"file '{os.path.join(os.getcwd(), wav_file)}'\n")
    
    final_audio_path = os.path.join(OUTPUT_DIR, "audio.wav")
    concat_cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_list_path, "-c", "copy", final_audio_path
    ]
    # Jalankan dari direktori output untuk memastikan path file relatif benar
    subprocess.run(concat_cmd, check=True, capture_output=True, cwd=OUTPUT_DIR)

    print("✅ Audio dan durasi berhasil disinkronkan.")

finally:
    print("  - Membersihkan file audio sementara...")
    if 'concat_list_path' in locals() and os.path.exists(concat_list_path):
        os.remove(concat_list_path)
    for wav_file in processed_wav_files:
        if os.path.exists(wav_file):
            os.remove(wav_file)

# =============================================================================
# --- VALIDASI & RENDER --- 
# =============================================================================
from scripts.validate_timeline import validate_timeline
from scripts.render_frames_pipe import render_all
from scripts.subtitles_ass import build_ass

print("🔍 Memvalidasi timeline akhir...")
errors = validate_timeline(timeline)
if errors:
    with open("timeline_error_dump.json", "w", encoding="utf-8") as f:
        json.dump(timeline, f, indent=2, ensure_ascii=False)
    raise ValueError("Timeline tidak valid. Lihat 'timeline_error_dump.json'.\n" + "\n".join(errors))

print("🖼️ Merender frame video...")
render_all(timeline=timeline, output_video="output/video_noaudio.mp4")

print("✍️ Membuat subtitle...")
build_ass(timeline, "output/subtitles.ass")

print("🎬 Menggabungkan semua file...")
subprocess.run([
    "ffmpeg", "-y",
    "-i", "output/video_noaudio.mp4",
    "-i", "output/audio.wav",
    "-vf", "ass=output/subtitles.ass",
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
    "output/video.mp4"
], check=True, capture_output=True)

print("✅ RENDER SELESAI")
