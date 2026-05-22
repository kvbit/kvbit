#!/usr/bin/env python3
"""Generate KVBIT Matrix rain header GIF with lightning bursts."""

from __future__ import annotations

import math
import os
import random
from dataclasses import dataclass, field

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 900, 220
FRAMES = 48
FPS_MS = 70
MATRIX_CHARS = (
    "ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜｦﾝ"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789"
    "+<>[]{}|/\\=:*#@$"
)
COL_W = 16
COLS = W // COL_W
TITLE = "KVBIT"


@dataclass
class Column:
    y: float
    speed: float
    length: int
    chars: list[str] = field(default_factory=list)

    def reset(self) -> None:
        self.y = random.uniform(-H * 1.2, -40)
        self.speed = random.uniform(6, 14)
        self.length = random.randint(12, 28)
        self.chars = [random.choice(MATRIX_CHARS) for _ in range(self.length)]

    def tick(self) -> None:
        self.y += self.speed
        if random.random() < 0.35:
            self.chars[0] = random.choice(MATRIX_CHARS)
        if random.random() < 0.08 and len(self.chars) > 2:
            idx = random.randint(1, min(4, len(self.chars) - 1))
            self.chars[idx] = random.choice(MATRIX_CHARS)
        if self.y - self.length * COL_W > H + 40:
            self.reset()


def load_fonts() -> tuple[ImageFont.FreeTypeFont, ImageFont.FreeTypeFont]:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/Menlo.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return (
                ImageFont.truetype(path, 15),
                ImageFont.truetype(path, 64),
            )
    default = ImageFont.load_default()
    return default, default


def lightning_schedule(frame: int) -> float:
    """Return lightning intensity 0..1 for this frame."""
    strikes = {6: 1.0, 7: 0.85, 8: 0.35, 22: 0.9, 23: 1.0, 24: 0.5, 38: 0.95, 39: 0.7}
    return strikes.get(frame, 0.0)


def draw_bolt(draw: ImageDraw.ImageDraw, x: int, intensity: float) -> None:
    if intensity < 0.2:
        return
    y = 0
    points = [(x, y)]
    segments = random.randint(5, 8)
    for _ in range(segments):
        y += random.randint(18, 36)
        x += random.randint(-22, 22)
        points.append((x, min(y, H)))
    color = (220, 245, 255, int(220 * intensity))
    width = max(1, int(3 * intensity))
    draw.line(points, fill=color[:3], width=width)
    for px, py in points:
        draw.ellipse((px - 4, py - 4, px + 4, py + 4), fill=(180, 220, 255))


def draw_rain(draw: ImageDraw.ImageDraw, columns: list[Column], font: ImageFont.FreeTypeFont) -> None:
    for i, col in enumerate(columns):
        x = i * COL_W + 3
        for j, ch in enumerate(col.chars):
            y = int(col.y - j * COL_W)
            if y < -24 or y > H + 8:
                continue
            if j == 0:
                fill = (220, 255, 230)
            elif j == 1:
                fill = (140, 255, 160)
            else:
                fade = max(0, 255 - j * 20)
                fill = (0, int(fade * 0.75), int(fade * 0.2))
            draw.text((x, y), ch, font=font, fill=fill)


def draw_kvbit(
    base: Image.Image,
    draw: ImageDraw.ImageDraw,
    font: ImageFont.FreeTypeFont,
    intensity: float,
) -> None:
    bbox = draw.textbbox((0, 0), TITLE, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx, ty = (W - tw) // 2, (H - th) // 2 - 6

    if intensity > 0.05:
        flash = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        fdraw = ImageDraw.Draw(flash)
        alpha = int(90 + 140 * intensity)
        fdraw.rectangle((0, 0, W, H), fill=(210, 235, 255, alpha))
        for _ in range(int(4 * intensity) + 1):
            bx = random.randint(tx - 40, tx + tw + 40)
            draw_bolt(fdraw, bx, intensity)
        base.alpha_composite(flash)

    if intensity > 0.6:
        core = (255, 255, 255)
        glow = (120, 220, 255)
        outline = (200, 240, 255)
    elif intensity > 0.25:
        core = (210, 255, 240)
        glow = (0, 200, 90)
        outline = (80, 255, 140)
    else:
        core = (0, 255, 70)
        glow = (0, 90, 30)
        outline = (0, 160, 50)

    for ox, oy, col in [
        (-3, 0, outline),
        (3, 0, outline),
        (0, -3, outline),
        (0, 3, outline),
        (-2, -2, glow),
        (2, 2, glow),
    ]:
        draw.text((tx + ox, ty + oy), TITLE, font=font, fill=col)

    draw.text((tx, ty), TITLE, font=font, fill=core)


def add_thunder_shake(img: Image.Image, intensity: float) -> Image.Image:
    if intensity < 0.5:
        return img
    offset = random.randint(-3, 3)
    shaken = Image.new("RGB", (W, H), (0, 0, 0))
    shaken.paste(img, (offset, random.randint(-2, 2)))
    return shaken


def generate() -> str:
    font_rain, font_title = load_fonts()
    columns = [Column(0, 0, 0) for _ in range(COLS)]
    for col in columns:
        col.reset()
        col.y = random.uniform(-H, H)

    frames: list[Image.Image] = []
    for f in range(FRAMES):
        for col in columns:
            col.tick()

        intensity = lightning_schedule(f)
        img = Image.new("RGBA", (W, H), (0, 0, 0, 255))
        draw = ImageDraw.Draw(img)
        draw_rain(draw, columns, font_rain)
        draw_kvbit(img, draw, font_title, intensity)

        rgb = img.convert("RGB")
        rgb = add_thunder_shake(rgb, intensity)
        if intensity > 0.7:
            rgb = rgb.filter(ImageFilter.GaussianBlur(radius=0.6))
        frames.append(rgb)

    os.makedirs(os.path.join(os.path.dirname(__file__), "..", "assets"), exist_ok=True)
    out = os.path.join(os.path.dirname(__file__), "..", "assets", "kvbit-matrix-rain.gif")
    frames[0].save(
        out,
        save_all=True,
        append_images=frames[1:],
        duration=FPS_MS,
        loop=0,
        optimize=True,
    )
    return out


if __name__ == "__main__":
    path = generate()
    print(f"Generated {path} ({os.path.getsize(path)} bytes)")
