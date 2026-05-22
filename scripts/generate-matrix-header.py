#!/usr/bin/env python3
"""Generate KVBIT Matrix rain GIF with dramatic lightning + thunder."""

from __future__ import annotations

import os
import random
from dataclasses import dataclass, field

from PIL import Image, ImageDraw, ImageFont

W, H = 900, 220
FRAMES = 54
FPS_MS = 85
MATRIX_CHARS = (
    "ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜｦﾝ"
    "ｱｲｳｴｵABCD0123456789<>[]{}|/\\=:*#"
)
COL_W = 16
COLS = W // COL_W
TITLE = "KVBIT"

# Each strike = 6 frames: rumble → build → PEAK → peak2 → fade → afterglow
STRIKES = [8, 24, 40]
STRIKE_CURVE = [0.15, 0.45, 1.0, 0.95, 0.55, 0.2]


@dataclass
class Column:
    y: float
    speed: float
    length: int
    chars: list[str] = field(default_factory=list)

    def reset(self) -> None:
        self.y = random.uniform(-H * 1.2, -40)
        self.speed = random.uniform(7, 15)
        self.length = random.randint(14, 30)
        self.chars = [random.choice(MATRIX_CHARS) for _ in range(self.length)]

    def tick(self) -> None:
        self.y += self.speed
        if random.random() < 0.4:
            self.chars[0] = random.choice(MATRIX_CHARS)
        if random.random() < 0.1 and len(self.chars) > 2:
            self.chars[random.randint(1, 4)] = random.choice(MATRIX_CHARS)
        if self.y - self.length * COL_W > H + 50:
            self.reset()


def load_fonts() -> tuple[ImageFont.FreeTypeFont, ImageFont.FreeTypeFont]:
    for path in (
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/Menlo.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    ):
        if os.path.exists(path):
            return ImageFont.truetype(path, 15), ImageFont.truetype(path, 68)
    d = ImageFont.load_default()
    return d, d


def strike_intensity(frame: int) -> float:
    for start in STRIKES:
        offset = frame - start
        if 0 <= offset < len(STRIKE_CURVE):
            return STRIKE_CURVE[offset]
    return 0.0


def draw_rain(draw: ImageDraw.ImageDraw, columns: list[Column], font: ImageFont.FreeTypeFont, bright: float) -> None:
    boost = int(80 * bright)
    for i, col in enumerate(columns):
        x = i * COL_W + 3
        for j, ch in enumerate(col.chars):
            y = int(col.y - j * COL_W)
            if y < -24 or y > H + 8:
                continue
            if j == 0:
                fill = (min(255, 200 + boost), 255, min(255, 220 + boost))
            elif j == 1:
                fill = (min(255, 100 + boost), 255, min(255, 140 + boost))
            else:
                fade = max(0, 220 - j * 18) + boost
                fill = (0, min(255, int(fade * 0.8)), min(255, int(fade * 0.25)))
            draw.text((x, y), ch, font=font, fill=fill)


def draw_lightning_bolts(draw: ImageDraw.ImageDraw, intensity: float, center_x: int) -> None:
    bolt_count = 5 + int(4 * intensity)
    for _ in range(bolt_count):
        x = center_x + random.randint(-220, 220)
        points = [(x, 0)]
        cy = 0
        while cy < H * 0.95:
            cy += random.randint(20, 42)
            x += random.randint(-28, 28)
            points.append((x, min(cy, H)))
        width = max(2, int(2 + 6 * intensity))
        core = (255, 255, 255)
        glow = (120, 200, 255)
        draw.line(points, fill=glow, width=width + 4)
        draw.line(points, fill=core, width=width)
        for px, py in points[::2]:
            r = int(6 + 8 * intensity)
            draw.ellipse((px - r, py - r, px + r, py + r), fill=(200, 230, 255))


def draw_kvbit(draw: ImageDraw.ImageDraw, font: ImageFont.FreeTypeFont, intensity: float) -> tuple[int, int, int, int]:
    bbox = draw.textbbox((0, 0), TITLE, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx, ty = (W - tw) // 2, (H - th) // 2 - 6

    if intensity >= 0.9:
        layers = [
            (-6, 0, (80, 160, 255)),
            (6, 0, (80, 160, 255)),
            (0, -6, (80, 160, 255)),
            (0, 6, (80, 160, 255)),
            (-3, -3, (180, 220, 255)),
            (3, 3, (180, 220, 255)),
            (0, 0, (255, 255, 255)),
        ]
    elif intensity >= 0.4:
        layers = [
            (-4, 0, (0, 180, 255)),
            (4, 0, (0, 180, 255)),
            (0, 0, (220, 255, 255)),
        ]
    else:
        layers = [
            (-2, 0, (0, 120, 40)),
            (2, 0, (0, 120, 40)),
            (0, 0, (0, 255, 65)),
        ]

    for ox, oy, color in layers:
        draw.text((tx + ox, ty + oy), TITLE, font=font, fill=color)

    return tx, ty, tw, th


def apply_screen_flash(img: Image.Image, intensity: float) -> Image.Image:
    if intensity < 0.35:
        return img
    white = Image.new("RGB", (W, H), (255, 255, 255))
    blend = 0.25 + 0.65 * intensity
    return Image.blend(img, white, blend)


def apply_thunder_shake(img: Image.Image, intensity: float) -> Image.Image:
    if intensity < 0.5:
        return img
    dx = random.randint(-12, 12)
    dy = random.randint(-8, 8)
    canvas = Image.new("RGB", (W, H), (0, 0, 0))
    canvas.paste(img, (dx, dy))
    return canvas


def generate() -> str:
    font_rain, font_title = load_fonts()
    columns = [Column(0, 0, 0) for _ in range(COLS)]
    for col in columns:
        col.reset()
        col.y = random.uniform(-H, H)

    frames: list[Image.Image] = []
    center_x = W // 2

    for f in range(FRAMES):
        for col in columns:
            col.tick()

        intensity = strike_intensity(f)
        img = Image.new("RGB", (W, H), (0, 0, 0))
        draw = ImageDraw.Draw(img)

        draw_rain(draw, columns, font_rain, bright=intensity)
        draw_kvbit(draw, font_title, intensity)

        if intensity > 0.1:
            draw_lightning_bolts(draw, intensity, center_x)

        img = apply_screen_flash(img, intensity)
        img = apply_thunder_shake(img, intensity)
        frames.append(img)

    out = os.path.join(os.path.dirname(__file__), "..", "assets", "kvbit-matrix-rain.gif")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    frames[0].save(
        out,
        save_all=True,
        append_images=frames[1:],
        duration=FPS_MS,
        loop=0,
        optimize=False,
    )
    return out


if __name__ == "__main__":
    path = generate()
    print(f"Generated {path} ({os.path.getsize(path)} bytes)")
