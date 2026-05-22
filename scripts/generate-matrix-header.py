#!/usr/bin/env python3
"""KVBIT header GIF — Machine style: KVBIT <-> status lines via thunder transitions."""

from __future__ import annotations

import os
import random
from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFont

W, H = 900, 240
FRAMES = 78
FPS_MS = 95

BG = (10, 14, 20)
RAIN_HEAD = (180, 220, 255)
RAIN_MID = (90, 150, 200)
RAIN_TAIL = (35, 55, 75)
ASCII_IDLE = (88, 166, 255)
ASCII_GLOW = (45, 100, 160)
ASCII_GLITCH = (140, 200, 255)
FLASH_WHITE = (255, 255, 255)
ALT_TEXT = (160, 210, 245)

ASCII_KVBIT = [
    "██╗  ██╗██╗   ██╗██████╗ ██╗████████╗",
    "██║ ██╔╝██║   ██║██╔══██╗██║╚══██╔══╝",
    "█████╔╝ ██║   ██║██████╔╝██║   ██║",
    "██╔═██╗ ╚██╗ ██╔╝██╔══██╗██║   ██║",
    "██║  ██╗ ╚████╔╝ ██████╔╝██║   ██║",
    "╚═╝  ╚═╝  ╚═══╝  ╚═════╝ ╚═╝   ╚═╝",
]

# Machine status screens shown between KVBIT appearances
ALT_SCREENS = [
    [
        ">> THE MACHINE",
        "   STATUS :: ONLINE",
        "   ADMIN MODE :: DISABLED",
    ],
    [
        ">> STAY RELEVANT",
        "   IRRELEVANT LIST :: FILTERING",
        "   RELEVANT QUEUE  :: ROUTING",
    ],
]

STREAM_CHARS = "01アイウエオカキクケコ0123456789ABCDEF#[]{}|/\\<>"
COL_W = 14
COLS = W // COL_W

# Timeline: hold → transition(7) → hold → transition → ...
# [0,10) KVBIT
# [10,17) T→ALT1
# [17,28) ALT1
# [28,35) T→KVBIT
# [35,46) KVBIT
# [46,53) T→ALT2
# [53,64) ALT2
# [64,71) T→KVBIT
# [71,78) KVBIT tail

SEGMENTS = [
    ("kvbit", 0, 10),
    ("trans", 10, 17, "kvbit", "alt", 0),
    ("alt", 17, 28, 0),
    ("trans", 28, 35, "alt", "kvbit", 0),
    ("kvbit", 35, 46),
    ("trans", 46, 53, "kvbit", "alt", 1),
    ("alt", 53, 64, 1),
    ("trans", 64, 71, "alt", "kvbit", 1),
    ("kvbit", 71, 78),
]

TRANS_PHASES = ["rumble", "charge", "flash", "peak", "flash", "decay", "settle"]


@dataclass
class Column:
    y: float
    speed: float
    length: int
    chars: list[str]

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


@dataclass
class Scene:
    kvbit_alpha: float
    alt_alpha: float
    alt_index: int
    intensity: float
    phase: str
    hud_alert: bool


def load_fonts() -> tuple[ImageFont.FreeTypeFont, ImageFont.FreeTypeFont, ImageFont.FreeTypeFont]:
    for path in (
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    ):
        if os.path.exists(path):
            return (
                ImageFont.truetype(path, 12),
                ImageFont.truetype(path, 11),
                ImageFont.truetype(path, 16),
            )
    d = ImageFont.load_default()
    return d, d, d


def parse_scene(frame: int) -> Scene:
    for seg in SEGMENTS:
        kind = seg[0]
        start, end = seg[1], seg[2]
        if not (start <= frame < end):
            continue

        if kind == "kvbit":
            return Scene(1.0, 0.0, 0, 0.0, "idle", False)

        if kind == "alt":
            alt_idx = seg[3]
            return Scene(0.0, 1.0, alt_idx, 0.0, "idle", False)

        # transition
        _, _, _, src, dst, alt_idx = seg
        t = (frame - start) / (end - start)
        step = min(int(t * len(TRANS_PHASES)), len(TRANS_PHASES) - 1)
        phase = TRANS_PHASES[step]
        intensity = [0.2, 0.5, 0.9, 1.0, 0.9, 0.5, 0.2][step]

        if src == "kvbit" and dst == "alt":
            # KVBIT fades out, alt fades in after flash
            if step <= 2:
                kv, alt = 1.0 - t * 1.4, 0.0
            elif step <= 4:
                kv, alt = max(0, 0.3 - t), min(1.0, (t - 0.4) * 2)
            else:
                kv, alt = 0.0, min(1.0, t * 1.2)
        else:
            # alt → kvbit
            if step <= 2:
                kv, alt = min(1.0, t * 0.5), 1.0
            elif step <= 4:
                kv, alt = min(1.0, (t - 0.3) * 2), max(0, 1.0 - t * 1.5)
            else:
                kv, alt = 1.0, 0.0

        kv = max(0.0, min(1.0, kv))
        alt = max(0.0, min(1.0, alt))
        return Scene(kv, alt, alt_idx, intensity, phase, True)

    return Scene(1.0, 0.0, 0, 0.0, "idle", False)


def scramble_line(line: str, rate: float) -> str:
    if rate <= 0:
        return line
    out = list(line)
    for i, ch in enumerate(out):
        if ch.strip() and random.random() < rate * 0.4:
            out[i] = random.choice(STREAM_CHARS)
    return "".join(out)


def draw_rain(draw: ImageDraw.ImageDraw, columns: list[Column], font: ImageFont.FreeTypeFont, boost: float) -> None:
    for i, col in enumerate(columns):
        x = i * COL_W + 2
        for j, ch in enumerate(col.chars):
            y = int(col.y - j * COL_W)
            if y < -20 or y > H:
                continue
            fill = RAIN_HEAD if j == 0 else RAIN_MID if j < 3 else RAIN_TAIL
            if boost > 0 and j < 5:
                fill = tuple(min(255, c + int(40 * boost)) for c in fill)
            draw.text((x, y), ch, font=font, fill=fill)


def draw_iris(draw: ImageDraw.ImageDraw, strength: float) -> None:
    cx, cy = W // 2, H // 2
    r = 78
    c = (int(35 * strength), int(60 * strength), int(95 * strength))
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=c, width=1)
    draw.ellipse((cx - 40, cy - 40, cx + 40, cy + 40), outline=c, width=1)


def draw_kvbit(
    draw: ImageDraw.ImageDraw,
    font: ImageFont.FreeTypeFont,
    alpha: float,
    scene: Scene,
) -> None:
    if alpha <= 0.02:
        return

    line_h = 15
    block_w = max(len(ln) for ln in ASCII_KVBIT) * 7
    sx = (W - block_w) // 2
    sy = (H - len(ASCII_KVBIT) * line_h) // 2
    scramble = 0.6 * scene.intensity if scene.phase in ("charge", "flash", "peak") else 0.0

    if scene.phase in ("flash", "peak") and alpha > 0.3:
        color = FLASH_WHITE
        layers = [(-4, 0, (70, 130, 200)), (4, 0, (70, 130, 200)), (0, 0, FLASH_WHITE)]
    elif scene.phase in ("charge", "rumble"):
        layers = [(-3, 0, ASCII_GLITCH), (3, 0, ASCII_GLITCH), (0, 0, ASCII_IDLE)]
    else:
        layers = [(-1, 0, ASCII_GLOW), (0, 0, ASCII_IDLE)]

    for ox, oy, base_color in layers:
        fade = int(255 * alpha)
        color = tuple(int(c * fade / 255) for c in base_color)
        for i, line in enumerate(ASCII_KVBIT):
            txt = scramble_line(line, scramble)
            draw.text((sx + ox, sy + i * line_h + oy), txt, font=font, fill=color)


def draw_alt_screen(
    draw: ImageDraw.ImageDraw,
    font: ImageFont.FreeTypeFont,
    lines: list[str],
    alpha: float,
    scene: Scene,
) -> None:
    if alpha <= 0.02:
        return

    line_h = 26
    block_h = len(lines) * line_h
    sy = (H - block_h) // 2 + 8
    scramble = 0.5 * scene.intensity if scene.phase in ("charge", "flash", "peak") else 0.0

    if scene.phase in ("flash", "peak"):
        color = FLASH_WHITE
        layers = [(0, 0, FLASH_WHITE)]
    elif scene.phase in ("charge", "rumble"):
        layers = [(-2, 0, ASCII_GLITCH), (2, 0, ASCII_GLITCH), (0, 0, ALT_TEXT)]
    else:
        layers = [(0, 0, ALT_TEXT)]

    for ox, oy, base in layers:
        fade = int(255 * alpha)
        color = tuple(int(c * fade / 255) for c in base)
        for i, line in enumerate(lines):
            txt = scramble_line(line, scramble)
            bbox = draw.textbbox((0, 0), txt, font=font)
            tw = bbox[2] - bbox[0]
            draw.text(((W - tw) // 2 + ox, sy + i * line_h + oy), txt, font=font, fill=color)


def draw_bolts(draw: ImageDraw.ImageDraw, intensity: float) -> None:
    if intensity < 0.35:
        return
    cx = W // 2
    for _ in range(2 + int(4 * intensity)):
        x = cx + random.randint(-240, 240)
        pts = [(x, 0)]
        py = 0
        while py < H:
            py += random.randint(24, 40)
            x += random.randint(-24, 24)
            pts.append((x, min(py, H)))
        w = max(2, int(2 + 5 * intensity))
        draw.line(pts, fill=(60, 110, 180), width=w + 3)
        draw.line(pts, fill=(235, 245, 255), width=w)


def draw_hud(draw: ImageDraw.ImageDraw, font: ImageFont.FreeTypeFont, scene: Scene) -> None:
    draw.text((14, 10), "THE MACHINE · SURVEILLANCE NODE", font=font, fill=(50, 68, 88))
    if scene.hud_alert:
        draw.text((14, 26), ">> SIGNAL INTERRUPT — REROUTING", font=font, fill=(130, 180, 220))


def post_process(img: Image.Image, scene: Scene) -> Image.Image:
    if scene.intensity >= 0.45 and scene.phase in ("charge", "flash", "peak"):
        flash = Image.new("RGB", (W, H), (225, 235, 245))
        blend = 0.12 + 0.5 * scene.intensity
        img = Image.blend(img, flash, blend)

    if scene.intensity >= 0.5 and scene.phase in ("flash", "peak", "rumble"):
        dx = random.randint(-11, 11) if scene.phase == "peak" else random.randint(-5, 5)
        dy = random.randint(-7, 7) if scene.phase == "peak" else random.randint(-3, 3)
        shaken = Image.new("RGB", (W, H), BG)
        shaken.paste(img, (dx, dy))
        img = shaken

    if scene.intensity >= 0.35:
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        a = int(35 + 70 * scene.intensity)
        for y in range(0, H, 4):
            od.line([(0, y), (W, y)], fill=(100, 160, 220, a))
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    return img


def generate() -> str:
    font_rain, font_ascii, font_alt = load_fonts()
    columns = [Column(0.0, 0.0, 0, []) for _ in range(COLS)]
    for c in columns:
        c.reset()

    frames: list[Image.Image] = []
    for f in range(FRAMES):
        for c in columns:
            c.tick()

        scene = parse_scene(f)
        img = Image.new("RGB", (W, H), BG)
        draw = ImageDraw.Draw(img)

        draw_iris(draw, 0.3 + scene.intensity * 0.5)
        draw_rain(draw, columns, font_rain, scene.intensity * 0.6)
        draw_hud(draw, font_alt, scene)

        if scene.kvbit_alpha > 0:
            draw_kvbit(draw, font_ascii, scene.kvbit_alpha, scene)
        if scene.alt_alpha > 0:
            draw_alt_screen(draw, font_alt, ALT_SCREENS[scene.alt_index], scene.alt_alpha, scene)

        draw_bolts(draw, scene.intensity)

        frames.append(post_process(img, scene))

    out = os.path.join(os.path.dirname(__file__), "..", "assets", "kvbit-thunder-header.gif")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=FPS_MS, loop=0)
    return out


if __name__ == "__main__":
    p = generate()
    print(f"Generated {p} ({os.path.getsize(p)} bytes)")
