from __future__ import annotations

from PIL import Image


def fit_center_square(img: Image.Image, size: int) -> Image.Image:
    """
    Return a size x size RGB image, preserving aspect ratio, centered, with crop as needed.
    """
    if img.mode != "RGB":
        img = img.convert("RGB")

    w, h = img.size
    if w == 0 or h == 0:
        return Image.new("RGB", (size, size), (0, 0, 0))

    scale = max(size / w, size / h)
    nw, nh = int(round(w * scale)), int(round(h * scale))
    resized = img.resize((nw, nh), resample=Image.BICUBIC)

    left = (nw - size) // 2
    top = (nh - size) // 2
    return resized.crop((left, top, left + size, top + size))


def to_rgb565_bytes(img_rgb: Image.Image) -> bytes:
    """
    Convert an RGB Pillow image to packed big-endian RGB565 bytes (2 bytes per pixel).
    """
    if img_rgb.mode != "RGB":
        img_rgb = img_rgb.convert("RGB")

    # Pillow gives bytes in RGBRGB...
    raw = img_rgb.tobytes()
    out = bytearray(len(raw) // 3 * 2)

    j = 0
    for i in range(0, len(raw), 3):
        r = raw[i]
        g = raw[i + 1]
        b = raw[i + 2]
        rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
        out[j] = (rgb565 >> 8) & 0xFF
        out[j + 1] = rgb565 & 0xFF
        j += 2

    return bytes(out)

