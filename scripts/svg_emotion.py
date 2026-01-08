from lxml import etree
import math
from copy import deepcopy

NS = {"svg": "http://www.w3.org/2000/svg"}

# =====================
# GESTURE
# =====================
def apply_gesture(root, gesture, frame, fps):
    if gesture == "raise_hand":
        hands = root.xpath("//*[@id='hand_right']", namespaces=NS)
        if hands:
            hands[0].attrib["transform"] = "rotate(-25 256 250)"

    elif gesture == "walk":
        t = frame / fps
        # Body bobbing
        body = root.xpath("//*[@id='body_group']", namespaces=NS)
        if body:
            y_offset = math.sin(t * 5) * 4
            body[0].attrib["transform"] = f"translate(0 {y_offset})"

        # Leg movement
        leg_l = root.xpath("//*[@id='leg_left']", namespaces=NS)
        leg_r = root.xpath("//*[@id='leg_right']", namespaces=NS)
        if leg_l and leg_r:
            angle = math.sin(t * 5) * 20
            leg_l[0].attrib["transform"] = f"rotate({angle} 256 370)"
            leg_r[0].attrib["transform"] = f"rotate({-angle} 256 370)"

        # Arm swing
        hand_l = root.xpath("//*[@id='hand_left']", namespaces=NS)
        hand_r = root.xpath("//*[@id='hand_right']", namespaces=NS)
        if hand_l and hand_r:
            angle = math.sin(t * 5) * 15
            hand_l[0].attrib["transform"] = f"rotate({-angle} 256 250)"
            hand_r[0].attrib["transform"] = f"rotate({angle} 256 250)"

# =====================
# BLINK
# =====================
def apply_blink(root, frame, fps):
    blink_interval = fps * 4     # tiap ±4 detik
    blink_len = 2                # 2 frame

    blinking = (frame % blink_interval) < blink_len

    for eye_id in ("eye_left", "eye_right"):
        eyes = root.xpath(f"//*[@id='{eye_id}']", namespaces=NS)
        if not eyes:
            continue
        eyes[0].attrib["r"] = "1" if blinking else "6"


# =====================
# HEAD NOD
# =====================
def apply_head_nod(root, frame, fps, emotion):
    heads = root.xpath("//*[@id='head_group']", namespaces=NS)
    if not heads:
        return

    t = frame / fps

    if emotion == "thinking":
        angle = math.sin(t * 1.5) * 6
    elif emotion == "happy":
        angle = math.sin(t * 2.5) * 4
    elif emotion == "angry":
        angle = math.sin(t * 8) * 1.5
    else:
        angle = 0

    heads[0].attrib["transform"] = f"rotate({angle:.2f} 256 180)"


# =====================
# MOUTH (LIP SYNC)
# =====================
def apply_mouth(root, mouth_open):
    mouths = root.xpath("//*[@id='mouth']", namespaces=NS)
    if not mouths:
        return

    base_y = 210
    delta = int(mouth_open * 18)
    mouths[0].attrib["d"] = f"M236 200 Q256 {base_y + delta} 276 200"


# =====================
# MAIN ENTRY
# =====================
def apply_emotion(base_tree, emotion, mouth_open, frame, fps, gesture=None):
    tree = deepcopy(base_tree)
    root = tree.getroot()

    apply_blink(root, frame, fps)
    apply_head_nod(root, frame, fps, emotion)
    apply_mouth(root, mouth_open)

    if gesture:
        apply_gesture(root, gesture, frame, fps)

    return tree
