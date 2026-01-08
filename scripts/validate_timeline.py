ALLOWED_EMOTIONS = {"neutral", "sad", "happy", "thinking", "angry"}

def validate_timeline(timeline):
    errors = []

    if not isinstance(timeline, dict):
        errors.append("Timeline bukan object JSON")

    if "fps" not in timeline:
        errors.append("Field 'fps' tidak ada")

    if "scenes" not in timeline:
        errors.append("Field 'scenes' tidak ada")

    scenes = timeline.get("scenes", [])
    if not isinstance(scenes, list) or not scenes:
        errors.append("Scenes kosong atau bukan list")

    for i, scene in enumerate(scenes):
        if "text" not in scene:
            errors.append(f"Scene {i+1}: text tidak ada")

        if scene.get("emotion") not in ALLOWED_EMOTIONS:
            errors.append(
                f"Scene {i+1}: emotion tidak valid ({scene.get('emotion')})"
            )

        d = scene.get("duration")
        if not isinstance(d, (int, float)) or d < 2 or d > 8:
            errors.append(
                f"Scene {i+1}: durasi tidak valid ({d})"
            )

    return errors
