import cairosvg

def svg_to_png(svg_string, out_path, w, h):
    cairosvg.svg2png(
        bytestring=svg_string.encode(),
        write_to=out_path,
        output_width=w,
        output_height=h
    )
