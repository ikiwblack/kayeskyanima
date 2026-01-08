from lxml import etree

def apply_emotion(svg_path, output_path, emotion):
    tree = etree.parse(svg_path)
    root = tree.getroot()

    ns = {"svg": "http://www.w3.org/2000/svg"}

    mouth = root.xpath("//*[@id='mouth']", namespaces=ns)[0]
    head = root.xpath("//*[@id='head']", namespaces=ns)[0]

    if emotion == "happy":
        mouth.attrib["d"] = "M236 200 Q256 220 276 200"

    elif emotion == "sad":
        mouth.attrib["d"] = "M236 210 Q256 190 276 210"

    elif emotion == "angry":
        mouth.attrib["d"] = "M236 205 L276 205"

    elif emotion == "thinking":
        head.attrib["transform"] = "rotate(-10 256 180)"

    tree.write(output_path)
