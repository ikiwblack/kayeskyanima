import os
import subprocess
from google.cloud import texttospeech
import wave

OUTPUT_DIR = "output"
SCENES_DIR = os.path.join(OUTPUT_DIR, "scenes")
os.makedirs(SCENES_DIR, exist_ok=True)

def get_audio_duration(file_path):
    """Mendapatkan durasi file audio WAV."""
    try:
        with wave.open(file_path, 'rb') as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            return frames / float(rate)
    except wave.Error as e:
        print(f"Could not read audio duration from {file_path}: {e}")
        return 0

def process_audio_and_update_timeline(timeline, character_map):
    """Membuat file audio untuk setiap adegan, menggabungkannya, dan memperbarui durasi di timeline."""
    client = texttospeech.TextToSpeechClient()
    updated_scenes = []
    scene_audio_files = []

    # Langkah 1 & 2: Buat audio per adegan & dapatkan durasi akurat
    for i, scene in enumerate(timeline["scenes"]):
        speaker_id = scene.get("speaker")
        text = scene.get("text", "")

        if not speaker_id or not text or text == "...":
            duration_sec = scene.get("duration", 0.5) # default silence duration
            scene_audio_path = os.path.join(SCENES_DIR, f"scene_{i}_silence.wav")
            from pydub import AudioSegment
            silence = AudioSegment.silent(duration=int(duration_sec * 1000))
            silence.export(scene_audio_path, format="wav")
            actual_duration = duration_sec
        else:
            character_details = character_map.get(speaker_id)
            if not character_details:
                raise ValueError(f"Detail untuk karakter '{speaker_id}' tidak ditemukan di timeline.")

            voice_name = character_details.get("voice")
            if not voice_name:
                raise ValueError(f"Voice ID tidak ditemukan untuk karakter '{speaker_id}' di characters.json.")

            synthesis_input = texttospeech.SynthesisInput(text=text)
            voice_params = texttospeech.VoiceSelectionParams(language_code="id-ID", name=voice_name)
            audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.LINEAR16)

            response = client.synthesize_speech(
                input=synthesis_input, voice=voice_params, audio_config=audio_config
            )

            scene_audio_path = os.path.join(SCENES_DIR, f"scene_{i}.wav")
            with open(scene_audio_path, "wb") as out:
                out.write(response.audio_content)
            
            actual_duration = get_audio_duration(scene_audio_path)

        scene_audio_files.append(scene_audio_path)
        
        # Langkah 3: Perbarui durasi adegan dengan durasi audio yang sebenarnya
        scene["duration"] = round(actual_duration, 2)
        updated_scenes.append(scene)

    timeline["scenes"] = updated_scenes

    # Langkah 4: Gabungkan semua file audio menjadi satu file audio utama
    concat_list_path = os.path.join(OUTPUT_DIR, "concat_list.txt")
    with open(concat_list_path, "w") as f:
        for file_path in scene_audio_files:
            f.write(f"file '{os.path.join('..', file_path)}'\n")

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
        print("FFmpeg Error:", e.stderr)
        raise

    return timeline
