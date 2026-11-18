import math, os
from PIL import Image, ImageDraw

out_dir = os.environ.get("OMNIMEDIA_OUT_DIR", ".")
os.makedirs(out_dir, exist_ok=True)

def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def lerp_rgb(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

BG_TOP, BG_BOTTOM = hex_rgb("#05060b"), hex_rgb("#120926")
CARD_2, ACCENT, ACCENT_SOFT = hex_rgb("#171a26"), hex_rgb("#8b5cf6"), hex_rgb("#c4b5fd")
CYAN, TEXT = hex_rgb("#22d3ee"), hex_rgb("#eceef6")

def render_icon(size=1024):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    grad = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    for y in range(size):
        gd.line([(0, y), (size, y)], fill=lerp_rgb(BG_TOP, BG_BOTTOM, y / float(size - 1)) + (255,))
    mask = Image.new("L", (size, size), 0)
    pad = int(size * 0.03)
    ImageDraw.Draw(mask).rounded_rectangle([pad, pad, size - pad, size - pad], radius=int(size * 0.22), fill=255)
    img.paste(grad, (0, 0), mask)
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([pad, pad, size - pad, size - pad], radius=int(size * 0.22), outline=lerp_rgb(ACCENT, CYAN, 0.35) + (180,), width=int(size * 0.012))
    cx, cy = size // 2, int(size * 0.39)
    for idx, (rf, al, wf) in enumerate([(0.28, 145, 0.012), (0.215, 220, 0.016)]):
        r = int(size * rf)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=lerp_rgb(CYAN, ACCENT_SOFT, idx * 0.7) + (al,), width=max(2, int(size * wf)))
    br, bc = int(size * 0.148), int(size * 0.076)
    draw.rounded_rectangle([cx - br, cy - br, cx + br, cy + br], radius=bc, fill=CARD_2 + (255,), outline=ACCENT + (255,), width=int(size * 0.018))
    draw.polygon([(cx - int(size * 0.042), cy - int(size * 0.070)), (cx - int(size * 0.042), cy + int(size * 0.070)), (cx + int(size * 0.074), cy)], fill=TEXT + (255,))
    nb, bw, gp = 11, int(size * 0.038), int(size * 0.024)
    x0, eq_cy = cx - (nb * bw + (nb - 1) * gp) // 2, int(size * 0.81)
    for i in range(nb):
        x = x0 + i * (bw + gp)
        w = (0.5 + 0.5 * math.sin(1.45 * 3.2 + i * 0.8)) * (0.6 + 0.4 * math.sin(1.45 * 1.3 + i))
        h = int(size * (0.042 + 0.125 * w))
        draw.rounded_rectangle([x, eq_cy - h // 2, x + bw, eq_cy + h // 2], radius=bw // 2, fill=lerp_rgb(CYAN, ACCENT, i / float(nb - 1)) + (255,))
    return img.resize((512, 512), Image.Resampling.LANCZOS)

if __name__ == "__main__":
    ic = render_icon(1024)
    ic.save(os.path.join(out_dir, "icon.png"), "PNG")
    ps = Image.new("RGBA", (720, 720), BG_TOP + (255,))
    ic360 = ic.resize((360, 360), Image.Resampling.LANCZOS)
    ps.paste(ic360, (180, 180), ic360)
    ps.save(os.path.join(out_dir, "presplash.png"), "PNG")
    ic.save(os.path.join(out_dir, "app_icon.ico"), "ICO", sizes=[(256,256),(128,128),(64,64),(48,48),(32,32),(16,16)])
