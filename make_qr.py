"""Builds qr-code.png: a QR code that opens the phone version, with Clawd in the middle and the name underneath.

    .venv\\Scripts\\pip install "qrcode[pil]"     (once)
    .venv\\Scripts\\python make_qr.py
"""
import qrcode
from PIL import Image, ImageDraw, ImageFont

from clawd_catch import BODY, CLAWD, LEGS, NIGHT

URL = "https://jacobhh3.github.io/block-catch/"
BOX = 16  # pixels per QR square

qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=BOX, border=4)  # H: still scans with the logo on top
qr.add_data(URL)
code = qr.make_image(fill_color=NIGHT, back_color="white").convert("RGB")
size = code.size[0]

# Clawd on a white patch in the middle, covering well under the 30% that H correction can recover
rows = BODY + LEGS[0]
px = BOX * 7 // len(rows[0]) + 1
sprite_w, sprite_h = len(rows[0]) * px, len(rows) * px
pad = BOX
patch = Image.new("RGB", (sprite_w + 2 * pad, sprite_h + 2 * pad), "white")
draw = ImageDraw.Draw(patch)
for r, row in enumerate(rows):
    for c, ch in enumerate(row):
        if ch != ".":
            x, y = pad + c * px, pad + r * px
            draw.rectangle((x, y, x + px - 1, y + px - 1), fill=NIGHT if ch == "E" else CLAWD)
code.paste(patch, ((size - patch.width) // 2, (size - patch.height) // 2))

# name and link underneath
font_big = ImageFont.truetype("Silkscreen-Bold.ttf", 64)
font_small = ImageFont.truetype("Silkscreen-Bold.ttf", 22)
out = Image.new("RGB", (size, size + 150), "white")
out.paste(code, (0, 0))
draw = ImageDraw.Draw(out)
draw.text((size / 2, size + 20), "BLOCK CATCH", font=font_big, fill=CLAWD, anchor="mt")
draw.text((size / 2, size + 104), URL.removeprefix("https://"), font=font_small, fill=NIGHT, anchor="mt")
out.save("qr-code.png")
print(f"qr-code.png  {out.size[0]}x{out.size[1]}")
