import re
import json

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
            "emotion": "neutral",
            "text": "",
            "duration": 0 # Durasi akan dihitung nanti setelah audio dibuat
        }

        # Baris pertama bisa berupa metadata atau dialog
        first_line = lines[0].strip()

        # Cek metadata [SPEAKER: emotion]
        metadata_match = re.match(r"\[(.*?)\]", first_line)
        dialog_lines = lines

        if metadata_match:
            metadata_content = metadata_match.group(1)
            dialog_lines = lines[1:] # Dialog dimulai dari baris kedua
            
            parts = [p.strip() for p in metadata_content.split(':')]
            # FIX: Hapus .upper() untuk mempertahankan casing yang sama persis dengan yang ada di naskah
            scene["speaker"] = parts[0]
            if len(parts) > 1:
                scene["emotion"] = parts[1].lower()

        # Gabungkan sisa baris menjadi teks dialog
        dialog = " ".join(line.strip() for line in dialog_lines).strip()
        
        # Jika speaker belum disetel dari metadata, coba tebak dari dialog (misal, NAMA: "Halo")
        if not scene["speaker"] and ':' in dialog:
            # FIX: Ubah regex agar tidak case-sensitive dan cocok dengan ID karakter
            speaker_match = re.match(r"([a-zA-Z0-9_]+):\s*", dialog)
            if speaker_match:
                # FIX: Hapus .upper()
                scene["speaker"] = speaker_match.group(1)
                # Hapus "NAMA: " dari teks dialog yang sebenarnya
                dialog = dialog[len(speaker_match.group(0)):].strip()

        scene["text"] = dialog if dialog else "..."
        
        # Jika tidak ada teks sama sekali, atur durasi default untuk jeda
        if not dialog:
            scene["duration"] = 0.5

        timeline["scenes"].append(scene)

    return timeline
