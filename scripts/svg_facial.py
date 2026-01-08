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


def apply_head_nod(root, t, emotion):
    head_group = root.xpath("//*[@id='head_group']", namespaces=NS)[0]

    if emotion == "thinking":
        angle = -10 + (t * 20)
    elif emotion == "happy":
        angle = (t * 10)
    else:
        angle = 0

    head_group.attrib["transform"] = f"rotate({angle} 256 180)"
