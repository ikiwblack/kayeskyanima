import os
import subprocess
from google.cloud import texttospeech
from pydub import AudioSegment
import wave

OUTPUT_DIR = "output"
SCENES_DIR = os.path.join(OUTPUT_DIR, "scenes")
os.makedirs(SCENES_DIR, exist_ok=True)

# Map character types to default voice names
DEFAULT_VOICES_BY_TYPE = {
    "Pria": "id-ID-Standard-B",
    "Wanita": "id-ID-Standard-A",
    "Kakek": "id-ID-Wavenet-B",
    "Nenek": "id-ID-Wavenet-A",
    "Anak Pria": "id-ID-Standard-C",
    "Anak Wanita": "id-ID-Standard-D",
}
DEFAULT_VOICE = "id-ID-Standard-A" # Fallback

def get_audio_duration(file_path):
    with wave.open(file_path, 'rb') as wf:
        return wf.getnframes() / float(wf.getframerate())

def process_audio_and_update_timeline(timeline, characters_map):
    client = texttospeech.TextToSpeechClient()
    updated_scenes = []
    scene_audio_files = []

    # Step 1 & 2: Generate audio per scene & get duration
    for i, scene in enumerate(timeline["scenes"]):
        char_id = scene["speaker"]
        char_info = characters_map.get(char_id)
        if not char_info:
            raise ValueError(f"Character ID '{char_id}' not found in characters.json")

        # Get voice based on character type
        char_type = char_info.get("type")
        voice_name = DEFAULT_VOICES_BY_TYPE.get(char_type, DEFAULT_VOICE)

        synthesis_input = texttospeech.SynthesisInput(text=scene["text"])
        voice = texttospeech.VoiceSelectionParams(
            language_code="id-ID", name=voice_name
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16
        )

        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )

        scene_audio_path = os.path.join(SCENES_DIR, f"scene_{i}.wav")
        with open(scene_audio_path, "wb") as out:
            out.write(response.audio_content)
        scene_audio_files.append(scene_audio_path)

        # Step 3: Get accurate duration and update scene
        duration = get_audio_duration(scene_audio_path)
        scene["duration"] = round(duration, 2)
        updated_scenes.append(scene)

    timeline["scenes"] = updated_scenes

    # Step 4: Concatenate all audio files into one
    concat_list_path = os.path.join(OUTPUT_DIR, "concat_list.txt")
    with open(concat_list_path, "w") as f:
        for file_path in scene_audio_files:
            # Path must be relative to the cwd of the ffmpeg command
            f.write(f"file '{os.path.join('scenes', os.path.basename(file_path))}'\n")

    output_audio_path = os.path.join(OUTPUT_DIR, "audio.wav")
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_list_path,
        "-c", "copy",
        output_audio_path
    ], check=True, cwd=OUTPUT_DIR) # Run from the output directory

    return timeline
