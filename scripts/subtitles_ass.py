import os

def sec_to_ass(t):
    """Konversi detik ke format waktu ASS (H:MM:SS.cs)."""
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"

def escape_ass(text: str) -> str:
    """Escape karakter khusus untuk format ASS."""
    # Menghindari masalah dengan kurung kurawal yang digunakan untuk tag override ASS
    return text.replace("{", "\\{").replace("}", "\\}")

def build_ass(timeline, out_path="output/subtitles.ass"):
    """
    Membangun file subtitle berformat .ass dari data timeline.
    """
    W, H = timeline.get("width", 720), timeline.get("height", 1280)

    header = f"""[Script Info]
Title: Subtitle Otomatis by Kayeskyanima
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
"""

    styles = []
    # Menentukan ukuran font dan margin berdasarkan orientasi video
    if W > H: # Lanskap (16:9)
        font_size = 48
        vertical_margin = 40
    else: # Potret (9:16)
        font_size = 60
        vertical_margin = 80

    # Membuat style untuk setiap karakter
    for c in timeline["characters"]:
        color_hex = c['color'].lstrip('#')
        r, g, b = color_hex[0:2], color_hex[2:4], color_hex[4:6]
        ass_color = f"&H00{b}{g}{r}".upper()

        styles.append(
            f"Style: {c['id']},Arial,{font_size},{ass_color},&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,0.00,0.00,1,2,1,2,10,10,{vertical_margin},1"
        )

    events_header = """
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    current_time = 0.0
    for scene in timeline["scenes"]:
        if not scene.get("duration") or scene["duration"] <= 0:
            continue

        start_time = sec_to_ass(current_time)
        end_time = sec_to_ass(current_time + scene["duration"])
        
        current_time += scene["duration"]

        processed_text = escape_ass(scene["text"])

        events.append(
            f"Dialogue: 0,{start_time},{end_time},{scene['speaker']},,0,0,0,,{processed_text}"
        )

    output_dir = os.path.dirname(out_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(header)
        f.write("\n".join(styles))
        f.write(events_header)
        f.write("\n".join(events))

    print(f"✅ Subtitle berhasil dibuat di: {out_path}")
