"""Build icon.png and icon.ico from the Clawd sprite with crisp integer scaling, plus the phone home screen icons
(apple-touch-icon.png, icon-192.png, icon-512.png) on the game's dark background."""
from PIL import Image

from clawd_catch import BODY, CLAWD, LEGS, NIGHT

ROWS = BODY + LEGS[0]
SIZES = [16, 24, 32, 48, 64, 128, 256]


def render(size, background=None, fill=1.0):
    """Draw the sprite at the largest whole-pixel scale that fits, centered.
    fill below 1 leaves a margin (phones crop home screen icons into rounded shapes)."""
    cols, rows = len(ROWS[0]), len(ROWS)
    scale = max(1, (int(size * fill) - 2) // cols)  # leave a little breathing room
    img = Image.new("RGBA", (size, size), (*background, 255) if background else (0, 0, 0, 0))
    ox = (size - cols * scale) // 2
    oy = (size - rows * scale) // 2
    for r, row in enumerate(ROWS):
        for c, ch in enumerate(row):
            if ch == ".":
                continue
            color = NIGHT if ch == "E" else CLAWD
            x, y = ox + c * scale, oy + r * scale
            img.paste((*color, 255), (x, y, x + scale, y + scale))
    return img


if __name__ == "__main__":
    frames = [render(s) for s in SIZES]
    frames[-1].save("icon.ico", sizes=[(s, s) for s in SIZES], append_images=frames[:-1])
    render(64).save("icon.png")
    render(180, NIGHT, 0.7).save("apple-touch-icon.png")
    render(192, NIGHT, 0.6).save("icon-192.png")
    render(512, NIGHT, 0.6).save("icon-512.png")
