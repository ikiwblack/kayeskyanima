def sec_to_ass(t):
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"

def build_ass(timeline, out_path="output/subtitles.ass"):
    styles = []
    events = []

    # ======================
    # HEADER
    # ======================
    header = """[Script Info]
Title: Generated Subtitle
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
"""

    # ======================
    # STYLES PER CHARACTER
    # ======================
    for c in timeline["characters"]:
        styles.append(
            f"Style: {c['id']},Arial,48,{c['color']},&HFFFFFF&,&H000000&,&H64000000&,0,0,0,0,100,100,0,0,1,3,0,2,60,60,80,1"
        )

    # ======================
    # EVENTS
    # ======================
    events_header = """
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    t = 0.0
    for s in timeline["scenes"]:
        start = sec_to_ass(t)
        end = sec_to_ass(t + s["duration"])
        t += s["duration"]

        events.append(
            f"Dialogue: 0,{start},{end},{s['speaker']},,0,0,0,,{s['text']}"
        )

    # ======================
    # WRITE FILE
    # ======================
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(header)
        f.write("\n".join(styles))
        f.write(events_header)
        f.write("\n".join(events))
