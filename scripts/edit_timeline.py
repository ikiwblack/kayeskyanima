def edit_scene(timeline: dict, index: int, field: str, value: str):
    scenes = timeline["scenes"]

    if index < 1 or index > len(scenes):
        raise ValueError("Index scene tidak valid")

    scene = scenes[index - 1]

    if field == "duration":
        scene[field] = int(value)
    elif field in ("text", "emotion"):
        scene[field] = value
    else:
        raise ValueError("Field tidak dikenali")

    return timeline
