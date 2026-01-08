from lxml import etree

NS = {"svg": "http://www.w3.org/2000/svg"}

def apply_gesture(root, gesture):
    arm_left = root.xpath("//*[@id='arm_left']", namespaces=NS)
    arm_right = root.xpath("//*[@id='arm_right']", namespaces=NS)

    if gesture == "raise_hand" and arm_right:
        arm_right[0].attrib["transform"] = "rotate(-60 327 270)"

    elif gesture == "point" and arm_right:
        arm_right[0].attrib["transform"] = "rotate(-20 327 270)"

    elif gesture == "thinking" and arm_left:
        arm_left[0].attrib["transform"] = "rotate(20 185 270)"

    # idle → tidak set transform
