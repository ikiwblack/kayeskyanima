from lxml import etree

NS = {"svg": "http://www.w3.org/2000/svg"}

def apply_blink(root, frame, fps):
    # blink tiap 3–5 detik
    blink_interval = fps * 4
    blink_len = 2  # frame

    blinking = (frame % blink_interval) < blink_len

    for eye_id in ("eye_left", "eye_right"):
        eyes = root.xpath(f"//*[@id='{eye_id}']", namespaces=NS)
        if not eyes:
            continue

        # circle eye: kecil = nutup
        eyes[0].attrib["r"] = "1" if blinking else "6"


import math

def apply_head_nod(root, frame, fps, emotion):
    heads = root.xpath("//*[@id='head_group']", namespaces=NS)
    if not heads:
        return

    t = frame / fps

    if emotion == "thinking":
        angle = math.sin(t * 1.5) * 6
    elif emotion == "happy":
        angle = math.sin(t * 2.5) * 4
    else:
        angle = 0

    heads[0].attrib["transform"] = f"rotate({angle:.2f} 256 180)"
