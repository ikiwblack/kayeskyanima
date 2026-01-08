def sec(t):
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h:02}:{m:02}:{s:06.3f}".replace(".", ",")

def build_srt(timeline, out_path="output/subtitles.srt"):
    t = 0.0
    blocks = []

    for i, scene in enumerate(timeline["scenes"], start=1):
        text = scene.get("text", "").strip()
        if not text:
            continue

        blocks.append(
            f"{i}\n"
            f"{sec(t)} --> {sec(t + scene['duration'])}\n"
            f"{text}\n"
        )
        t += scene["duration"]

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(blocks))
