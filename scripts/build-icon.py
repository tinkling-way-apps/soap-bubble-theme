#!/usr/bin/env python3
"""Draw the extension icon images/icon.png with the standard library only.
拡張のアイコン images/icon.png を標準ライブラリだけで描く。

Usage / 使い方:
    python3 scripts/build-icon.py

One soap bubble on the theme's off-white ground, filled with six sectors in the frame colors of the
Red theme (red, orange, yellow, green, blue, violet, clockwise from the top), whitened toward the
center like a taut film, with a highlight top-left and a soft shadow below. Shapes are tested with
plain arithmetic and anti-aliased by 3×3 supersampling, so no image library is needed.

テーマの灰白の地に石けんの泡がひとつ。Red テーマの枠の 6 色(上から時計回りに赤・橙・黄・緑・青・紫)の
扇で塗り、張った膜のように中心へ向かって白く、左上に光、下に薄い影。図形はすべて数式で判定し、
3×3 のスーパーサンプリングでアンチエイリアスを付けて PNG に書き出す。
"""
from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "images" / "icon.png"

SIZE = 256
SS = 3  # samples per pixel edge / 1 ピクセルあたりの縦横サンプル数

BG = "#edebe8"  # editor.background of the themes / テーマのエディタ地色
# Frame backgrounds of the Red theme, in rainbow order / Red テーマの枠の地色、虹の順
SECTORS = ["#ec6c88", "#fb9569", "#fac768", "#7ae1a7", "#7bd2f2", "#8e71de"]

# Bubble geometry / 泡の寸法
CX, CY, R = 128, 132, 94
# Where the first sector starts, in turns clockwise from the right (0.75 = straight up)
# 最初の扇の始点。右から時計回りに測った周の割合(0.75 で真上)
SECTOR_START = 0.75

Color = tuple[float, float, float]


def hex_rgb(h: str) -> Color:
    return tuple(int(h[i : i + 2], 16) for i in (1, 3, 5))  # type: ignore[return-value]


def mix(c: Color, to: float, amount: float) -> Color:
    """Blend toward white (to=255) or black (to=0) / 白または黒へ寄せる"""
    return tuple(v * (1 - amount) + to * amount for v in c)  # type: ignore[return-value]


def in_round_rect(x: float, y: float, x0: float, y0: float, x1: float, y1: float, r: float) -> bool:
    cx = min(max(x, x0 + r), x1 - r)
    cy = min(max(y, y0 + r), y1 - r)
    return (x - cx) ** 2 + (y - cy) ** 2 <= r * r


def in_ellipse(x: float, y: float, cx: float, cy: float, rx: float, ry: float) -> bool:
    return ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1


def sample(x: float, y: float) -> Color | None:
    """Color of one sample point, None outside the rounded square (transparent).
    1 サンプル点の色。背景の角丸四角の外なら None(透明)"""
    if not in_round_rect(x, y, 0, 0, SIZE, SIZE, 56):
        return None
    color = hex_rgb(BG)

    # Soft shadow under the bubble / 泡の下の薄い影
    if in_ellipse(x, y, CX + 2, CY + R + 8, R * 0.7, 9):
        color = mix(color, 0, 0.08)

    d = math.hypot(x - CX, y - CY)
    if d > R:
        return color

    # Sector by angle / 角度で扇を選ぶ
    turn = (math.atan2(y - CY, x - CX) / (2 * math.pi) + SECTOR_START) % 1.0
    color = hex_rgb(SECTORS[int(turn * len(SECTORS)) % len(SECTORS)])
    # Whiter toward the center (the taut film), a touch darker at the very rim
    # 中心ほど白く(張った膜)、縁ぎりぎりは少し濃く
    color = mix(color, 255, 0.35 * (1 - d / R) ** 1.5)
    if d > R - 6:
        color = mix(color, 0, 0.12 * (d - (R - 6)) / 6)
    # Highlight top-left / 左上の光
    if in_ellipse(x, y, CX - R * 0.40, CY - R * 0.44, R * 0.24, R * 0.14):
        color = mix(color, 255, 0.8)
    return color


def render() -> bytes:
    rows = []
    step = 1 / SS
    for py in range(SIZE):
        row = bytearray([0])  # filter type None / フィルタ種別: None
        for px in range(SIZE):
            acc = [0.0, 0.0, 0.0]
            cover = 0
            for sy in range(SS):
                for sx in range(SS):
                    c = sample(px + (sx + 0.5) * step, py + (sy + 0.5) * step)
                    if c is None:
                        continue
                    cover += 1
                    acc[0] += c[0]
                    acc[1] += c[1]
                    acc[2] += c[2]
            n = SS * SS
            if cover == 0:
                row += bytes((0, 0, 0, 0))
            else:
                row += bytes((round(acc[0] / cover), round(acc[1] / cover), round(acc[2] / cover), round(255 * cover / n)))
        rows.append(bytes(row))
    return b"".join(rows)


def write_png(path: Path, raw: bytes) -> None:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0)  # 8-bit RGBA
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)


if __name__ == "__main__":
    write_png(OUT, render())
    print(f"wrote {OUT.relative_to(ROOT)} ({SIZE}x{SIZE})")
