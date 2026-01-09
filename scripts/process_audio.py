import os
import subprocess
import wave
from gtts import gTTS
from pydub import AudioSegment

OUTPUT_DIR = "output"
SCENES_DIR = os.path.join(OUTPUT_DIR, "scenes")
os.makedirs(SCENES_DIR, exist_ok=True)

def get_audio_duration(file_path):
    """Mendapatkan durasi file audio WAV."""
    try:
        with wave.open(file_path, 'rb') as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            # Hindari pembagian dengan nol jika rate adalah 0
            if rate == 0:
                return 0
            return frames / float(rate)
    except (wave.Error, FileNotFoundError) as e:
        print(f"Could not read audio duration from {file_path}: {e}")
        return 0

def process_audio_and_update_timeline(timeline, character_map):
    """Membuat file audio untuk setiap adegan menggunakan gTTS, menggabungkannya, dan memperbarui durasi di timeline."""
    updated_scenes = []
    scene_audio_files = []

    for i, scene in enumerate(timeline["scenes"]):
        speaker_id = scene.get("speaker")
        text = scene.get("text", "")
        scene_audio_path = os.path.join(SCENES_DIR, f"scene_{i}.wav")

        if not speaker_id or not text or text == "...":
            duration_sec = scene.get("duration", 0.5) # default silence duration
            silence = AudioSegment.silent(duration=int(duration_sec * 1000))
            silence.export(scene_audio_path, format="wav")
            actual_duration = duration_sec
        else:
            if not character_map.get(speaker_id):
                raise ValueError(f"Detail untuk karakter '{speaker_id}' tidak ditemukan.")

            tts = gTTS(text=text, lang='id', slow=False)
            temp_mp3_path = os.path.join(SCENES_DIR, f"scene_{i}_temp.mp3")
            tts.save(temp_mp3_path)

            try:
                # Muat MP3 ke pydub
                audio = AudioSegment.from_mp3(temp_mp3_path)
                
                # *** PERBAIKAN UTAMA: Dapatkan durasi dari objek pydub di memori ***
                # Ini menghindari ketergantungan pada file WAV yang mungkin gagal dibuat
                actual_duration = len(audio) / 1000.0

                # Lanjutkan untuk mengekspor ke WAV
                audio.export(scene_audio_path, format="wav")

            except Exception as e:
                print(f"Error converting MP3 to WAV or getting duration for scene {i}: {e}")
                # Jika konversi gagal, kita setidaknya punya durasi 0 untuk validasi
                actual_duration = 0
                # Buat file WAV kosong agar proses selanjutnya tidak error karena file tidak ada
                AudioSegment.silent(duration=10).export(scene_audio_path, format="wav")


            finally:
                # Hapus file MP3 sementara
                if os.path.exists(temp_mp3_path):
                    os.remove(temp_mp3_path)
        
        # Jika durasi masih 0 setelah semua upaya, itu adalah masalah.
        if actual_duration <= 0:
            print(f"PERINGATAN: Durasi untuk adegan {i} ('{text[:20]}...') adalah nol atau negatif.")

        scene_audio_files.append(scene_audio_path)
        
        scene["duration"] = round(actual_duration, 2)
        updated_scenes.append(scene)

    timeline["scenes"] = updated_scenes

    concat_list_path = os.path.join(OUTPUT_DIR, "concat_list.txt")
    with open(concat_list_path, "w") as f:
        for file_path in scene_audio_files:
            relative_path = os.path.relpath(file_path, OUTPUT_DIR)
            f.write(f"file '{relative_path}'\n")

    output_audio_path = os.path.join(OUTPUT_DIR, "audio.wav")
    
    try:
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", os.path.basename(concat_list_path),
            "-c", "copy",
            os.path.basename(output_audio_path)
        ], check=True, cwd=OUTPUT_DIR, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print("FFmpeg Error Output:", e.stdout)
        print("FFmpeg Error Stderr:", e.stderr)
        raise

    return timeline
