#!/usr/bin/env python3
"""KVBIT header GIF — Machine style: KVBIT + 10 status lines via thunder transitions."""

from __future__ import annotations

import os
import random
from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFont

W, H = 800, 200
FPS_MS = 80
KVBIT_HOLD = 4
TRANS_LEN = 4
ALT_HOLD = 5

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

# 10 Machine / Finch status screens
ALT_SCREENS = [
    [">> THE MACHINE", "   STATUS :: ONLINE", "   ADMIN MODE :: DISABLED"],
    [">> STAY RELEVANT", "   IRRELEVANT LIST :: FILTERING", "   RELEVANT QUEUE  :: ROUTING"],
    [">> SIGNAL ACQUIRED", "   SUBJECT :: YOU", "   VERDICT :: RELEVANT"],
    [">> NODE STATUS", "   LOCATION :: OFF-GRID", "   DISCLOSURE :: MINIMAL"],
    [">> THREAT MODEL", "   POSTURE :: HOSTILE", "   TRUST :: ZERO"],
    [">> DATA FEED", "   NOISE :: DISCARDED", "   SIGNAL :: RETAINED"],
    [">> OPERATOR LOG", "   UPTIME :: CONTINUOUS", "   ENCRYPTION :: ON"],
    [">> SURVEILLANCE", "   COVERAGE :: TOTAL", "   ACCESS :: DENIED"],
    [">> MISSION FILE", "   SEE EVERYTHING", "   KEEP WHAT MATTERS"],
    [">> TRANSMISSION", "   YOU ARE NOT ALONE", "   ACT AS IF YOU ARE"],
]

STREAM_CHARS = "01アイウエオカキクケコ0123456789ABCDEF#[]{}|/\\<>"
COL_W = 14
COLS = W // COL_W
TRANS_PHASES = ["rumble", "charge", "flash", "peak", "flash", "decay", "settle"]


def build_segments() -> tuple[list[tuple], int]:
    """Build timeline: KVBIT → 10 alts (thunder between each) → KVBIT."""
    segments: list[tuple] = []
    t = 0

    segments.append(("kvbit", t, t + KVBIT_HOLD))
    t += KVBIT_HOLD

    for i in range(len(ALT_SCREENS)):
        if i == 0:
            segments.append(("trans", t, t + TRANS_LEN, "kvbit", "alt", i, None))
        else:
            segments.append(("trans", t, t + TRANS_LEN, "alt", "alt", i, i - 1))
        t += TRANS_LEN
        segments.append(("alt", t, t + ALT_HOLD, i))
        t += ALT_HOLD

    last = len(ALT_SCREENS) - 1
    segments.append(("trans", t, t + TRANS_LEN, "alt", "kvbit", last, last))
    t += TRANS_LEN
    segments.append(("kvbit", t, t + KVBIT_HOLD))
    t += KVBIT_HOLD

    return segments, t


SEGMENTS, FRAMES = build_segments()


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
    alt_from_index: int | None
    alt_from_alpha: float
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
                ImageFont.truetype(path, 15),
            )
    d = ImageFont.load_default()
    return d, d, d


def _trans_alphas(step: int, t: float, src: str, dst: str) -> tuple[float, float, float]:
    """Return kvbit_a, alt_to_a, alt_from_a."""
    if src == "kvbit" and dst == "alt":
        if step <= 2:
            return 1.0 - t * 1.3, 0.0, 0.0
        if step <= 4:
            return max(0.0, 0.4 - t), min(1.0, (t - 0.35) * 2.5), 0.0
        return 0.0, min(1.0, t * 1.2), 0.0

    if src == "alt" and dst == "alt":
        if step <= 2:
            return 0.0, 0.0, 1.0 - t * 1.2
        if step <= 4:
            return 0.0, min(1.0, (t - 0.3) * 2.2), max(0.0, 0.5 - t)
        return 0.0, 1.0, 0.0

    # alt → kvbit
    if step <= 2:
        return min(1.0, t * 0.6), 0.0, 1.0 - t * 1.2
    if step <= 4:
        return min(1.0, (t - 0.25) * 2), 0.0, max(0.0, 1.0 - t * 1.4)
    return 1.0, 0.0, 0.0


def parse_scene(frame: int) -> Scene:
    for seg in SEGMENTS:
        kind, start, end = seg[0], seg[1], seg[2]
        if not (start <= frame < end):
            continue

        if kind == "kvbit":
            return Scene(1.0, 0.0, 0, None, 0.0, 0.0, "idle", False)

        if kind == "alt":
            idx = seg[3]
            return Scene(0.0, 1.0, idx, None, 0.0, 0.0, "idle", False)

        src, dst, to_idx = seg[3], seg[4], seg[5]
        from_idx = seg[6] if len(seg) > 6 else None
        t = (frame - start) / max(1, end - start - 1)
        step = min(int(t * len(TRANS_PHASES)), len(TRANS_PHASES) - 1)
        phase = TRANS_PHASES[step]
        intensity = [0.2, 0.5, 0.9, 1.0, 0.9, 0.5, 0.2][step]

        kv, to_a, from_a = _trans_alphas(step, t, src, dst)
        kv = max(0.0, min(1.0, kv))
        to_a = max(0.0, min(1.0, to_a))
        from_a = max(0.0, min(1.0, from_a))

        if dst == "alt":
            return Scene(kv, to_a, to_idx, from_idx if src == "alt" else None, from_a if src == "alt" else 0.0, intensity, phase, True)

        # alt → kvbit
        return Scene(kv, 0.0, from_idx or 0, from_idx, from_a, intensity, phase, True)

    return Scene(1.0, 0.0, 0, None, 0.0, 0.0, "idle", False)


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
    r = 72
    c = (int(35 * strength), int(60 * strength), int(95 * strength))
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=c, width=1)
    draw.ellipse((cx - 36, cy - 36, cx + 36, cy + 36), outline=c, width=1)


def draw_kvbit(draw: ImageDraw.ImageDraw, font: ImageFont.FreeTypeFont, alpha: float, scene: Scene) -> None:
    if alpha <= 0.02:
        return
    line_h = 15
    block_w = max(len(ln) for ln in ASCII_KVBIT) * 7
    sx = (W - block_w) // 2
    sy = (H - len(ASCII_KVBIT) * line_h) // 2
    scramble = 0.6 * scene.intensity if scene.phase in ("charge", "flash", "peak") else 0.0
    if scene.phase in ("flash", "peak"):
        layers = [(-4, 0, (70, 130, 200)), (4, 0, (70, 130, 200)), (0, 0, FLASH_WHITE)]
    elif scene.phase in ("charge", "rumble"):
        layers = [(-3, 0, ASCII_GLITCH), (3, 0, ASCII_GLITCH), (0, 0, ASCII_IDLE)]
    else:
        layers = [(-1, 0, ASCII_GLOW), (0, 0, ASCII_IDLE)]
    for ox, oy, base in layers:
        color = tuple(int(c * alpha) for c in base)
        for i, line in enumerate(ASCII_KVBIT):
            draw.text((sx + ox, sy + i * line_h + oy), scramble_line(line, scramble), font=font, fill=color)


def draw_alt_screen(
    draw: ImageDraw.ImageDraw,
    font: ImageFont.FreeTypeFont,
    lines: list[str],
    alpha: float,
    scene: Scene,
) -> None:
    if alpha <= 0.02:
        return
    line_h = 24
    block_h = len(lines) * line_h
    sy = (H - block_h) // 2 + 6
    scramble = 0.5 * scene.intensity if scene.phase in ("charge", "flash", "peak") else 0.0
    if scene.phase in ("flash", "peak"):
        layers = [(0, 0, FLASH_WHITE)]
    elif scene.phase in ("charge", "rumble"):
        layers = [(-2, 0, ASCII_GLITCH), (2, 0, ASCII_GLITCH), (0, 0, ALT_TEXT)]
    else:
        layers = [(0, 0, ALT_TEXT)]
    for ox, oy, base in layers:
        color = tuple(int(c * alpha) for c in base)
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
        x = cx + random.randint(-220, 220)
        pts = [(x, 0)]
        py = 0
        while py < H:
            py += random.randint(22, 38)
            x += random.randint(-22, 22)
            pts.append((x, min(py, H)))
        w = max(2, int(2 + 5 * intensity))
        draw.line(pts, fill=(60, 110, 180), width=w + 3)
        draw.line(pts, fill=(235, 245, 255), width=w)


def draw_hud(draw: ImageDraw.ImageDraw, font: ImageFont.FreeTypeFont, scene: Scene) -> None:
    draw.text((12, 8), "THE MACHINE · SURVEILLANCE NODE", font=font, fill=(50, 68, 88))
    if scene.hud_alert:
        draw.text((12, 22), ">> SIGNAL INTERRUPT — REROUTING", font=font, fill=(130, 180, 220))


def post_process(img: Image.Image, scene: Scene) -> Image.Image:
    if scene.intensity >= 0.45 and scene.phase in ("charge", "flash", "peak"):
        flash = Image.new("RGB", (W, H), (225, 235, 245))
        img = Image.blend(img, flash, 0.12 + 0.5 * scene.intensity)
    if scene.intensity >= 0.5 and scene.phase in ("flash", "peak", "rumble"):
        dx = random.randint(-10, 10) if scene.phase == "peak" else random.randint(-4, 4)
        dy = random.randint(-6, 6) if scene.phase == "peak" else random.randint(-2, 2)
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

    print(f"Timeline: {FRAMES} frames, {len(ALT_SCREENS)} status screens")
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
        if scene.alt_from_index is not None and scene.alt_from_alpha > 0:
            draw_alt_screen(draw, font_alt, ALT_SCREENS[scene.alt_from_index], scene.alt_from_alpha, scene)
        if scene.alt_alpha > 0:
            draw_alt_screen(draw, font_alt, ALT_SCREENS[scene.alt_index], scene.alt_alpha, scene)
        draw_bolts(draw, scene.intensity)
        frames.append(post_process(img, scene))

    # Global palette keeps size reasonable for GitHub profile embedding
    palette_ref = frames[0].quantize(colors=128, method=Image.Quantize.MEDIANCUT)
    quantized = [f.quantize(palette=palette_ref, dither=Image.Dither.FLOYDSTEINBERG) for f in frames]

    out = os.path.join(os.path.dirname(__file__), "..", "assets", "kvbit-thunder-header.gif")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    quantized[0].save(
        out,
        save_all=True,
        append_images=quantized[1:],
        duration=FPS_MS,
        loop=0,
        optimize=True,
        disposal=2,
    )
    return out


if __name__ == "__main__":
    p = generate()
    print(f"Generated {p} ({os.path.getsize(p)} bytes)")
