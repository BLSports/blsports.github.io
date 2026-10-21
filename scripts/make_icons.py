"""Erzeugt die App-Icons (iPhone-Homescreen, Android, Favicon) nach icons/.

Einmalig auszuführen; die PNGs liegen danach im Repo:
    python scripts/make_icons.py
"""
import math
import os

from PIL import Image, ImageDraw, ImageFilter

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "icons")

BRAND = (14, 59, 44)       # --brand
BRAND2 = (24, 104, 74)     # etwas heller als --brand2 fuer den Verlauf
ACCENT = (47, 191, 134)    # --accent (dunkel)
WHITE = (255, 255, 255)


def radial_bg(n):
    """Radialer Verlauf wie im Kopfbereich der Seite (Licht oben rechts)."""
    img = Image.new("RGB", (n, n), BRAND)
    px = img.load()
    cx, cy, rmax = n * 0.78, n * 0.12, n * 1.15
    for y in range(n):
        for x in range(n):
            t = min(1.0, math.hypot(x - cx, y - cy) / rmax)
            t = t * t * (3 - 2 * t)
            px[x, y] = tuple(round(BRAND2[i] * (1 - t) + BRAND[i] * t) for i in range(3))
    return img


def draw_icon(n, safe=1.0):
    """safe < 1 verkleinert das Motiv (Android-"maskable": Inhalt in 80 %-Kreis)."""
    s = 4  # Supersampling fuer glatte Kanten
    N = n * s
    img = radial_bg(n).resize((N, N), Image.BICUBIC).convert("RGBA")
    c = N / 2
    R = N * 0.36 * safe

    # Radar-Schwenk (Kegel mit Verlauf)
    sweep = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sweep)
    start = -90 + 25
    for k in range(60):
        a = int(110 * (k / 60) ** 2)
        sd.pieslice([c - R, c - R, c + R, c + R], start + k, start + k + 1.5, fill=ACCENT + (a,))
    img = Image.alpha_composite(img, sweep)

    ov = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    w = max(2, round(N * 0.012 * safe))
    for f, alpha in ((1.0, 240), (0.68, 120), (0.36, 90)):
        r = R * f
        d.ellipse([c - r, c - r, c + r, c + r], outline=WHITE + (alpha,), width=w)
    d.line([c - R, c, c + R, c], fill=WHITE + (45,), width=max(1, w // 2))
    d.line([c, c - R, c, c + R], fill=WHITE + (45,), width=max(1, w // 2))

    # Leitstrahl
    ang = math.radians(start + 60)
    d.line([c, c, c + R * math.cos(ang), c + R * math.sin(ang)], fill=ACCENT + (255,), width=w * 2)

    img = Image.alpha_composite(img, ov)

    # Ziel-Blip mit Glow (= das "Value"-Spiel auf dem Radar)
    bx, by = c + R * 0.55 * math.cos(math.radians(-38)), c + R * 0.55 * math.sin(math.radians(-38))
    glow = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    gr = R * 0.2
    ImageDraw.Draw(glow).ellipse([bx - gr, by - gr, bx + gr, by + gr], fill=(242, 182, 50, 170))
    glow = glow.filter(ImageFilter.GaussianBlur(N * 0.025))
    img = Image.alpha_composite(img, glow)
    d = ImageDraw.Draw(img)
    br = R * 0.085
    d.ellipse([bx - br, by - br, bx + br, by + br], fill=(255, 214, 102, 255))

    # Zentrum
    cr = R * 0.07
    d.ellipse([c - cr, c - cr, c + cr, c + cr], fill=WHITE + (255,))

    return img.resize((n, n), Image.LANCZOS).convert("RGB")


def main():
    os.makedirs(OUT, exist_ok=True)
    targets = {
        "apple-touch-icon.png": (180, 1.0),
        "icon-192.png": (192, 1.0),
        "icon-512.png": (512, 1.0),
        "icon-maskable-512.png": (512, 0.8),
        "favicon-32.png": (32, 1.15),
    }
    for name, (n, safe) in targets.items():
        draw_icon(n, safe).save(os.path.join(OUT, name), optimize=True)
        print("OK ->", os.path.join("icons", name))


if __name__ == "__main__":
    main()
