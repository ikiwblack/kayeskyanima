import os
import json
import re
from scripts.cache import load_cached_timeline, save_cached_timeline


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
    """Menganalisis naskah untuk menemukan karakter yang aktif dan membuat adegan dasar."""
    active_char_ids = set()
    scenes = []
    for line in text.strip().split('\n'):
        match = re.match(r'^(.*?):\s*(.*)$', line)
        if not match:
            continue
        
        speaker_id, dialog = match.groups()
        if speaker_id in all_chars_map:
            active_char_ids.add(speaker_id)
            # Menambahkan nilai default untuk emotion dan duration secara langsung
            scenes.append({
                "speaker": speaker_id, 
                "text": dialog.strip(),
                "emotion": "neutral", # Emosi default
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
        # Menetapkan posisi x di tengah berdasarkan jumlah karakter
        char['x'] = int(width * (i + 1) / (num_chars + 1))
    return characters

def analyze(text: str, orientation: str = "9:16") -> dict:
    """Menganalisis naskah dengan arsitektur berbasis aturan 100% deterministik."""
    # Kunci cache diubah untuk mencerminkan versi logika baru ini
    cache_key = f"deterministic_v3::{orientation}::{text}"
    cached = load_cached_timeline(cache_key)
    if cached:
        return cached

    # Tentukan dimensi
    width, height = (1920, 1080) if orientation == "16:9" else (1080, 1920)

    # 1. Muat semua definisi karakter
    all_character_defs = load_character_definitions()
    all_chars_map = {char['id']: char for char in all_character_defs}

    # 2. Parse naskah untuk membuat adegan yang sudah diperkaya dengan nilai default
    active_characters, scenes = parse_script(text, all_chars_map)

    # 3. Tetapkan posisi horizontal untuk karakter aktif
    positioned_characters = assign_positions(active_characters, width)

    # 4. Bangun timeline final (tidak ada lagi langkah AI)
    timeline = {
        "width": width,
        "height": height,
        "fps": 12,
        "characters": positioned_characters,
        "scenes": scenes
    }

    save_cached_timeline(cache_key, timeline)
    return timeline
