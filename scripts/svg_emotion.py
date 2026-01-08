from lxml import etree
import math

NS = {"svg": "http://www.w3.org/2000/svg"}

def clamp(v, lo, hi):
    return max(lo, min(v, hi))

def apply_emotion(
    svg_in: str,
    svg_out: str,
    emotion: str,
    mouth_open: float,
    frame: int = 0,
    fps: int = 24
):
    tree = etree.parse(svg_in)
    root = tree.getroot()

    # =========================
    # EYE BLINK (REAL)
    # =========================
    eyes_open = root.xpath("//*[@id='eyes_open']", namespaces=NS)
    eyes_closed = root.xpath("//*[@id='eyes_closed']", namespaces=NS)

    # Blink every 3–5 seconds
    blink_interval = fps * 4
    blink_len = 3  # frames

    blinking = (frame % blink_interval) < blink_len

    if eyes_open and eyes_closed:
        eyes_open[0].attrib["display"] = "none" if blinking else "inline"
        eyes_closed[0].attrib["display"] = "inline" if blinking else "none"

    # Emotion modifier
    if emotion == "sad" and eyes_open:
        eyes_open[0].attrib["transform"] = "scale(1 0.85)"

    # =========================
    # MOUTH LIP SYNC (IMPROVED)
    # =========================
    mouth = root.xpath("//*[@id='mouth']", namespaces=NS)
    if mouth:
        m = clamp(mouth_open, 0.0, 1.0)

        # Non-linear (natural speech)
        eased = math.sqrt(m)

        base_y = 210
        max_open = 24
        y = base_y + int(eased * max_open)

        mouth[0].attrib["d"] = f"M236 200 Q256 {y} 276 200"

    tree.write(svg_out, encoding="utf-8", xml_declaration=True)
