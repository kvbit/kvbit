#!/usr/bin/env python3
"""Generate KVBIT header GIF — Machine/Finch style ASCII + thunder transitions."""

from __future__ import annotations

import os
import random
from dataclasses import dataclass, field

from PIL import Image, ImageDraw, ImageFont

W, H = 900, 240
FRAMES = 60
FPS_MS = 90

# Finch / Machine palette
BG = (10, 14, 20)
RAIN_HEAD = (180, 220, 255)
RAIN_MID = (90, 150, 200)
RAIN_TAIL = (35, 55, 75)
ASCII_IDLE = (88, 166, 255)
ASCII_GLOW = (45, 100, 160)
ASCII_GLITCH = (140, 200, 255)
FLASH_WHITE = (255, 255, 255)

ASCII_KVBIT = [
    "██╗  ██╗██╗   ██╗██████╗ ██╗████████╗",
    "██║ ██╔╝██║   ██║██╔══██╗██║╚══██╔══╝",
    "█████╔╝ ██║   ██║██████╔╝██║   ██║",
    "██╔═██╗ ╚██╗ ██╔╝██╔══██╗██║   ██║",
    "██║  ██╗ ╚████╔╝ ██████╔╝██║   ██║",
    "╚═╝  ╚═╝  ╚═══╝  ╚═════╝ ╚═╝   ╚═╝",
]

STREAM_CHARS = "01アイウエオカキクケコ0123456789ABCDEF#[]{}|/\\<>"

# strike start frame → 7-frame transition curve
STRIKES = [10, 30, 48]
# idle → rumble → charge → FLASH → hold → decay → settle
STRIKE_CURVE = [0.0, 0.2, 0.5, 1.0, 0.85, 0.45, 0.15]

COL_W = 14
COLS = W // COL_W


@dataclass
class Column:
    y: float
    speed: float
    length: int
    chars: list[str] = field(default_factory=list)

    def reset(self) -> None:
        self.y = random.uniform(-H, -20)
        self.speed = random.uniform(5, 11)
        self.length = random.randint(10, 22)
        self.chars = [random.choice(STREAM_CHARS) for _ in range(self.length)]

    def tick(self) -> None:
        self.y += self.speed
        if random.random() < 0.3:
            self.chars[0] = random.choice(STREAM_CHARS)
        if self.y - self.length * COL_W > H + 30:
            self.reset()


def load_fonts() -> tuple[ImageFont.FreeTypeFont, ImageFont.FreeTypeFont, ImageFont.FreeTypeFont]:
    for path in (
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    ):
        if os.path.exists(path):
            return (
                ImageFont.truetype(path, 12),
                ImageFont.truetype(path, 11),
                ImageFont.truetype(path, 9),
            )
    d = ImageFont.load_default()
    return d, d, d


def strike_state(frame: int) -> tuple[float, str]:
    for start in STRIKES:
        offset = frame - start
        if 0 <= offset < len(STRIKE_CURVE):
            intensity = STRIKE_CURVE[offset]
            names = ["idle", "rumble", "charge", "flash", "hold", "decay", "settle"]
            return intensity, names[offset]
    return 0.0, "idle"


def scramble_line(line: str, rate: float) -> str:
    if rate <= 0:
        return line
    chars = list(line)
    for i, ch in enumerate(chars):
        if ch != " " and random.random() < rate * 0.35:
            chars[i] = random.choice(STREAM_CHARS)
    return "".join(chars)


def draw_machine_rain(draw: ImageDraw.ImageDraw, columns: list[Column], font: ImageFont.FreeTypeFont, boost: float) -> None:
    for i, col in enumerate(columns):
        x = i * COL_W + 2
        for j, ch in enumerate(col.chars):
            y = int(col.y - j * COL_W)
            if y < -20 or y > H:
                continue
            if j == 0:
                fill = RAIN_HEAD
            elif j < 3:
                fill = RAIN_MID
            else:
                t = max(0, 1 - j * 0.08)
                fill = (
                    int(RAIN_TAIL[0] + (RAIN_MID[0] - RAIN_TAIL[0]) * t * (1 + boost)),
                    int(RAIN_TAIL[1] + (RAIN_MID[1] - RAIN_TAIL[1]) * t * (1 + boost)),
                    int(RAIN_TAIL[2] + (RAIN_MID[2] - RAIN_TAIL[2]) * t * (1 + boost)),
                )
            draw.text((x, y), ch, font=font, fill=fill)


def draw_machine_iris(draw: ImageDraw.ImageDraw, alpha: float) -> None:
    if alpha <= 0:
        return
    cx, cy = W // 2, H // 2
    r = 72
    color = (int(40 * alpha), int(70 * alpha), int(110 * alpha))
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=color, width=1)
    draw.ellipse((cx - r // 2, cy - r // 2, cx + r // 2, cy + r // 2), outline=color, width=1)


def draw_scanlines(img: Image.Image, intensity: float) -> Image.Image:
    if intensity < 0.35:
        return img
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    step = 4
    alpha = int(40 + 80 * intensity)
    for y in range(0, H, step):
        od.line([(0, y), (W, y)], fill=(120, 180, 255, alpha), width=1)
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def draw_ascii_kvbit(
    draw: ImageDraw.ImageDraw,
    font: ImageFont.FreeTypeFont,
    intensity: float,
    phase: str,
) -> tuple[int, int, int, int]:
    line_h = 15
    block_w = max(len(line) for line in ASCII_KVBIT) * 7
    start_x = (W - block_w) // 2
    start_y = (H - len(ASCII_KVBIT) * line_h) // 2

    scramble = 0.0
    if phase in ("charge", "flash"):
        scramble = 0.4 + 0.5 * intensity
    elif phase == "hold":
        scramble = 0.25

    # transition layers
    layers: list[tuple[int, int, tuple[int, int, int]]] = []

    if phase == "rumble":
        layers = [(-2, 0, ASCII_GLOW), (2, 0, ASCII_GLOW), (0, 0, ASCII_IDLE)]
    elif phase == "charge":
        layers = [(-4, 0, ASCII_GLITCH), (4, 0, ASCII_GLITCH), (-2, 1, ASCII_GLOW), (0, 0, ASCII_IDLE)]
    elif phase in ("flash", "hold"):
        layers = [
            (-6, 0, (60, 120, 200)),
            (6, 0, (60, 120, 200)),
            (-3, -2, (200, 230, 255)),
            (3, 2, (200, 230, 255)),
            (0, 0, FLASH_WHITE),
        ]
    elif phase == "decay":
        layers = [(-2, 0, ASCII_GLITCH), (0, 0, (220, 240, 255)), (0, 0, ASCII_IDLE)]
    elif phase == "settle":
        layers = [(0, 0, (120, 190, 255)), (0, 0, ASCII_IDLE)]
    else:
        layers = [(-1, 0, ASCII_GLOW), (0, 0, ASCII_IDLE)]

    for ox, oy, color in layers:
        for i, line in enumerate(ASCII_KVBIT):
            text = scramble_line(line, scramble) if color == FLASH_WHITE or phase in ("flash", "charge", "hold") else line
            draw.text(
                (start_x + ox, start_y + i * line_h + oy),
                text,
                font=font,
                fill=color,
            )

    return start_x, start_y, block_w, len(ASCII_KVBIT) * line_h


def draw_finch_bolts(draw: ImageDraw.ImageDraw, intensity: float, cx: int, cy: int) -> None:
    if intensity < 0.4:
        return
    for _ in range(3 + int(3 * intensity)):
        x = cx + random.randint(-200, 200)
        points = [(x, 0)]
        py = 0
        while py < H:
            py += random.randint(22, 38)
            x += random.randint(-20, 20)
            points.append((x, min(py, H)))
        w = max(2, int(2 + 4 * intensity))
        draw.line(points, fill=(70, 130, 200), width=w + 3)
        draw.line(points, fill=(220, 240, 255), width=w)


def apply_flash(img: Image.Image, intensity: float, phase: str) -> Image.Image:
    if phase not in ("flash", "hold", "charge") or intensity < 0.45:
        return img
    white = Image.new("RGB", (W, H), (230, 240, 255))
    blend = 0.15 + 0.55 * intensity if phase == "flash" else 0.1 + 0.35 * intensity
    return Image.blend(img, white, blend)


def apply_shake(img: Image.Image, intensity: float, phase: str) -> Image.Image:
    if phase not in ("flash", "hold", "rumble") or intensity < 0.5:
        return img
    dx = random.randint(-10, 10) if phase == "flash" else random.randint(-5, 5)
    dy = random.randint(-6, 6) if phase == "flash" else random.randint(-3, 3)
    out = Image.new("RGB", (W, H), BG)
    out.paste(img, (dx, dy))
    return out


def draw_hud(draw: ImageDraw.ImageDraw, font_sm: ImageFont.FreeTypeFont, phase: str) -> None:
    label = "THE MACHINE · ADMIN MODE DISABLED"
    draw.text((14, 10), label, font=font_sm, fill=(55, 75, 95))
    if phase in ("charge", "flash", "hold"):
        draw.text((14, 24), ">> SIGNAL INTERRUPT", font=font_sm, fill=(140, 190, 230))


def generate() -> str:
    font_rain, font_ascii, font_sm = load_fonts()
    columns = [Column(0, 0, 0) for _ in range(COLS)]
    for col in columns:
        col.reset()
        col.y = random.uniform(-H, 0)

    frames: list[Image.Image] = []
    cx, cy = W // 2, H // 2

    for f in range(FRAMES):
        for col in columns:
            col.tick()

        intensity, phase = strike_state(f)
        img = Image.new("RGB", (W, H), BG)
        draw = ImageDraw.Draw(img)

        draw_machine_iris(draw, 0.35 + 0.4 * intensity)
        draw_machine_rain(draw, columns, font_rain, boost=intensity * 0.5)
        draw_hud(draw, font_sm, phase)
        draw_ascii_kvbit(draw, font_ascii, intensity, phase)

        if intensity > 0.35:
            draw_finch_bolts(draw, intensity, cx, cy)

        img = draw_scanlines(img, intensity)
        img = apply_flash(img, intensity, phase)
        img = apply_shake(img, intensity, phase)
        frames.append(img)

    out = os.path.join(os.path.dirname(__file__), "..", "assets", "kvbit-thunder-header.gif")
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
