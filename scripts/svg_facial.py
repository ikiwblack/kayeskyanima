from lxml import etree

NS = {"svg": "http://www.w3.org/2000/svg"}

def apply_blink(root, t):
    # blink tiap ~2 detik
    if int(t * 10) % 20 == 0:
        for eye_id in ("eye_left", "eye_right"):
            eye = root.xpath(f"//*[@id='{eye_id}']", namespaces=NS)[0]
            eye.attrib["r"] = "1"
    else:
        for eye_id in ("eye_left", "eye_right"):
            eye = root.xpath(f"//*[@id='{eye_id}']", namespaces=NS)[0]
            eye.attrib["r"] = "6"

def apply_head_nod(root, t, emotion):
    head_group = root.xpath("//*[@id='head_group']", namespaces=NS)[0]

    if emotion == "thinking":
        angle = -10 + (t * 20)
    elif emotion == "happy":
        angle = (t * 10)
    else:
        angle = 0

    head_group.attrib["transform"] = f"rotate({angle} 256 180)"
