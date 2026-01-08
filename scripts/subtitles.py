def sec(t):
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h:02}:{m:02}:{s:06.3f}".replace(".", ",")

def build_srt(timeline, text):
    lines = text.split(".")
    t = 0
    srt = []
    i = 1

    for scene, line in zip(timeline["scenes"], lines):
        srt.append(f"""{i}
{sec(t)} --> {sec(t + scene["duration"])}
{line.strip()}
""")
        t += scene["duration"]
        i += 1

    open("output/subtitles.srt", "w").write("\n".join(srt))
