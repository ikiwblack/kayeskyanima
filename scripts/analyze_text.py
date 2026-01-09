import os
import json
import re
from scripts.cache import load_cached_timeline, save_cached_timeline

# Peta dari Bahasa Indonesia (dalam naskah) ke kata kunci internal sistem
EMOTION_MAP = {
    "marah": "angry",
    "sedih": "sad",
    "senang": "happy",
    "berpikir": "thinking",
    "terkejut": "surprised",
    "netral": "neutral",
}

def load_character_definitions():
    """Memuat definisi karakter dari characters.json."""
    try:
        with open('characters.json', 'r', encoding='utf-8') as f:
            return json.load(f)["characters"]
    except FileNotFoundError:
        raise ValueError("File characters.json tidak ditemukan. Harap buat file konfigurasi karakter.")
    except json.JSONDecodeError:
        raise ValueError("File characters.json tidak valid.")

def parse_script(text: str, all_chars_map: dict) -> (list, list):
    """Menganalisis naskah untuk menemukan karakter, emosi, dan dialog."""
    active_char_ids = set()
    scenes = []
    # Regex ini menangkap: 1. Pembicara, 2. Emosi (opsional), 3. Dialog
    # Format: Pembicara: (Emosi) Dialog
    line_regex = re.compile(r'^([^:]+):\s*(?:\(([^)]+)\))?\s*(.*)$')

    for line in text.strip().split('\n'):
        match = line_regex.match(line.strip())
        if not match:
            continue
        
        speaker_id, emotion_tag, dialog = match.groups()
        speaker_id = speaker_id.strip()

        if speaker_id in all_chars_map:
            active_char_ids.add(speaker_id)
            
            # Tentukan emosi
            current_emotion = "neutral" # Default
            if emotion_tag:
                # Cari emosi di peta, jika tidak ditemukan, tetap netral
                current_emotion = EMOTION_MAP.get(emotion_tag.strip().lower(), "neutral")

            # Tambahkan adegan ke daftar
            scenes.append({
                "speaker": speaker_id, 
                "text": dialog.strip(),
                "emotion": current_emotion,
                "duration": 3 # Durasi placeholder, akan di-override oleh process_audio
            })

    if not active_char_ids:
        raise ValueError("Tidak ada karakter yang valid ditemukan dalam naskah. Pastikan formatnya 'Karakter: dialog'.")

    active_characters = [char for char_id, char in all_chars_map.items() if char_id in active_char_ids]
    return active_characters, scenes

def assign_positions(characters: list, width: int) -> list:
    """Menetapkan posisi 'x' untuk setiap karakter secara merata."""
    num_chars = len(characters)
    for i, char in enumerate(characters):
        char['x'] = int(width * (i + 1) / (num_chars + 1))
    return characters

def analyze(text: str, orientation: str = "9:16") -> dict:
    """Menganalisis naskah dengan arsitektur berbasis aturan untuk emosi dan dialog."""
    # Kunci cache diperbarui untuk mencerminkan logika parsing emosi baru
    cache_key = f"deterministic_v4_emotion::{orientation}::{text}"
    cached = load_cached_timeline(cache_key)
    if cached:
        return cached

    width, height = (1920, 1080) if orientation == "16:9" else (1080, 1920)

    all_character_defs = load_character_definitions()
    all_chars_map = {char['id']: char for char in all_character_defs}

    active_characters, scenes = parse_script(text, all_chars_map)

    positioned_characters = assign_positions(active_characters, width)

    timeline = {
        "width": width,
        "height": height,
        "fps": 12,
        "characters": positioned_characters,
        "scenes": scenes
    }

    save_cached_timeline(cache_key, timeline)
    return timeline
