def sec_to_ass(t):
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"

def escape_ass(text: str) -> str:
    return (
        text.replace("\\", r"\\")
            .replace("{", r"\{")
            .replace("}", r"\}")
    )

def build_ass(timeline, out_path="output/subtitles.ass"):
    # Resolusi PlayRes disesuaikan dengan timeline
    W, H = timeline.get("width", 1080), timeline.get("height", 1920)
    header = f"""[Script Info]
Title: Generated Subtitle
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
"""

    styles = []
    for c in timeline["characters"]:
        # FIX: Tingkatkan ukuran font dari 48 -> 96 dan margin vertikal dari 80 -> 120
        styles.append(
            f"Style: {c['id']},Arial,96,{c['color']},&HFFFFFF&,&H000000&,&H64000000&,0,0,0,0,100,100,0,0,1,3,0,2,60,60,120,1"
        )

    events_header = """

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    events = []
    t = 0.0
    for s in timeline["scenes"]:
        start = sec_to_ass(t)
        end = sec_to_ass(t + s["duration"])
        t += s["duration"]

        text = escape_ass(s["text"])

        # Gunakan alignment 2 (tengah bawah) dan style yang sesuai
        events.append(
            f"Dialogue: 0,{start},{end},{s['speaker']},,0,0,0,,{text}"
        )

    # Pastikan direktori output ada
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(header)
        f.write("\n".join(styles))
        f.write(events_header)
        f.write("\n".join(events))
import os
