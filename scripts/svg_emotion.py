from lxml import etree

NS = {"svg": "http://www.w3.org/2000/svg"}

def apply_emotion(svg_in, svg_out, emotion, mouth_open=0.0):
    tree = etree.parse(svg_in)
    root = tree.getroot()

    # ===== EYE BLINK =====
    eyes = root.xpath("//*[@id='eyes']", namespaces=NS)
    if eyes:
        eyes[0].attrib["opacity"] = "0.2" if emotion == "sad" else "1"

    # ===== MOUTH OPEN (LIP SYNC) =====
    mouth = root.xpath("//*[@id='mouth']", namespaces=NS)
    if mouth:
        base = 210
        delta = int(mouth_open * 18)
        mouth[0].attrib["d"] = f"M236 200 Q256 {base + delta} 276 200"

    tree.write(svg_out)
