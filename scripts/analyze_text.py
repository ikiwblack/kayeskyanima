import re
import json

# Definisikan pemetaan emosi dari Bahasa Indonesia ke Bahasa Inggris
EMOTION_MAP = {
    "marah": "angry",
    "sedih": "sad",
    "senang": "happy",
    "berpikir": "thinking",
    "terkejut": "surprised",
    "netral": "neutral",
    "bersemangat": "happy", # Alias untuk senang
}

def analyze(text: str, aspect_ratio: str):
    """Menganalisis naskah mentah menjadi struktur timeline dasar tanpa menyertakan data karakter."""
    
    # Menentukan resolusi berdasarkan rasio aspek
    width, height = (1920, 1080) if aspect_ratio == '16:9' else (1080, 1920)

    timeline = {
        "width": width,
        "height": height,
        "fps": 12,
        "scenes": [],
        # Kunci "characters" sengaja DIHILANGKAN.
        # main.py sekarang bertanggung jawab penuh untuk memasukkan data karakter dari characters.json.
    }

    scenes_data = text.strip().split("\n\n")
    
    for scene_str in scenes_data:
        lines = scene_str.strip().split('\n')
        if not lines:
            continue

        scene = {
            "speaker": None,
            "emotion": "neutral", # Default emotion
            "text": "",
            "duration": 0
        }

        first_line = lines[0].strip()

        metadata_match = re.match(r"\[(.*?)\]", first_line)
        dialog_lines = lines

        if metadata_match:
            metadata_content = metadata_match.group(1)
            dialog_lines = lines[1:]
            
            parts = [p.strip() for p in metadata_content.split(':')]
            scene["speaker"] = parts[0] # Pertahankan casing asli
            
            if len(parts) > 1:
                # Ambil emosi dalam bahasa Indonesia dan terjemahkan
                user_emotion = parts[1].lower()
                # Gunakan pemetaan untuk mendapatkan emosi internal (Inggris), default ke 'neutral' jika tidak ditemukan
                scene["emotion"] = EMOTION_MAP.get(user_emotion, "neutral")

        dialog = " ".join(line.strip() for line in dialog_lines).strip()
        
        if not scene["speaker"] and ':' in dialog:
            speaker_match = re.match(r"([a-zA-Z0-9_]+):\s*", dialog)
            if speaker_match:
                scene["speaker"] = speaker_match.group(1)
                dialog = dialog[len(speaker_match.group(0)):].strip()

        scene["text"] = dialog if dialog else "..."
        
        if not dialog:
            scene["duration"] = 0.5

        timeline["scenes"].append(scene)

    return timeline
