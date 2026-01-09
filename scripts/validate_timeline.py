ALLOWED_EMOTIONS = {"neutral", "sad", "happy", "thinking", "angry", "surprised"}

def validate_timeline(timeline: dict):
    errors = []

    if "fps" not in timeline:
        errors.append("fps tidak ada")

    scenes = timeline.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        errors.append("scenes kosong")

    for i, s in enumerate(scenes or []):
        if "text" not in s:
            errors.append(f"Scene {i+1}: text kosong")
        if s.get("emotion") not in ALLOWED_EMOTIONS:
            errors.append(f"Scene {i+1}: emotion tidak valid")
        d = s.get("duration")
        # Melonggarkan aturan validasi: durasi hanya perlu angka non-negatif.
        if not isinstance(d, (int, float)) or d < 0:
            # Diubah untuk memberikan output debug yang lebih detail
            errors.append(f"Scene {i+1}: durasi tidak valid (nilai: {repr(d)}, tipe: {type(d).__name__})")

    return errors
