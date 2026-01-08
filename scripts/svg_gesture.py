from lxml import etree

NS = {"svg": "http://www.w3.org/2000/svg"}

def apply_gesture(svg_path, output_path, gesture):
    tree = etree.parse(svg_path)
    root = tree.getroot()

    arm_left = root.xpath("//*[@id='arm_left']", namespaces=NS)[0]
    arm_right = root.xpath("//*[@id='arm_right']", namespaces=NS)[0]

    if gesture == "raise_hand":
        arm_right.attrib["transform"] = "rotate(-60 327 270)"

    elif gesture == "point":
        arm_right.attrib["transform"] = "rotate(-20 327 270)"

    elif gesture == "thinking":
        arm_left.attrib["transform"] = "rotate(20 185 270)"

    # idle = default (no transform)

    tree.write(output_path)
