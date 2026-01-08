from lxml import etree
from scripts.svg_facial import apply_blink, apply_head_nod

NS = {"svg": "http://www.w3.org/2000/svg"}

def apply_emotion(svg_path, output_path, emotion, t=0.0):
    tree = etree.parse(svg_path)
    root = tree.getroot()

    mouth = root.xpath("//*[@id='mouth']", namespaces=NS)[0]

    if emotion == "happy":
        mouth.attrib["d"] = "M236 200 Q256 220 276 200"
    elif emotion == "sad":
        mouth.attrib["d"] = "M236 210 Q256 190 276 210"
    elif emotion == "angry":
        mouth.attrib["d"] = "M236 205 L276 205"

    apply_blink(root, t)
    apply_head_nod(root, t, emotion)

    tree.write(output_path)
