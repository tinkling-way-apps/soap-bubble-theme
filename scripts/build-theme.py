#!/usr/bin/env python3
"""Generate the nine Soap Bubble themes from the Soap Dish Purple source.
Soap Dish Purple の原本から Soap Bubble の 9 テーマを生成する。

Usage / 使い方:
    python3 scripts/build-theme.py

Soap Dish rotates the purple hue band of the whole file to one hue per variant. Soap Bubble rotates
it to a different hue per UI zone instead. Six zones (title bar, tab strip, panel, side bar,
activity bar, status bar) take the six rainbow colors (red, orange, yellow, green, blue, violet),
while the editor in the middle fades to a warm off-white (the Cream recipe). Bracket pairs and
indent guides get the same six colors. The six themes differ only in where the colors land: each
one shifts the colors one zone along, and is named after the color of its title bar.

Three special variants paint every frame zone with one color instead: Gold (gold frame, Cream
editor), Grayscale Light (everything in the hue band desaturated) and Grayscale Dark (desaturated,
then the lightness of the whole file flipped, shadows excepted, turning the light source dark).

Replacement is textual, comments included, so the JSONC layout of the source is preserved. The
script ends by parsing every output and checking the zone hues, and fails loudly if anything is off.

Soap Dish はファイル全体の紫の色相帯を、色ごとに 1 つの色相へ回す。Soap Bubble は UI の領域ごとに
別の色相へ回す。6 つの領域(タイトルバー・タブ列・パネル・サイドバー・アクティビティバー・
ステータスバー)に虹の 6 色(赤・橙・黄・緑・青・紫)を当て、真ん中のエディタは Cream のレシピで
暖かみのある灰白に薄める。括弧の対とインデントガイドにも同じ 6 色を当てる。6 テーマの違いは
色の置き場所だけで、1 テーマごとに色が領域を 1 つずつずれ、タイトルバーの色で名前を付ける。

特別バリエーション 3 本は虹ではなく枠の全領域を 1 色で塗る。Gold(金の枠と Cream のエディタ)、
Grayscale Light(色相帯の色をすべて無彩色に)、Grayscale Dark(無彩色にした上で、影を除いて
ファイル全体の明度を反転し、ライトの原本をダークにする)。

置換はコメント行も含めてテキストのまま行い、原本の JSONC の体裁を保つ。最後に全出力を解析して
領域ごとの色相を検査し、ずれていれば異常終了する。
"""
from __future__ import annotations

import colorsys
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "source" / "purple-color-theme.json"
THEMES = ROOT / "themes"

EXTENSION_NAME = "Soap Bubble"

# Hue of the source accent #422eb0; deltas are measured from here
# 原本のアクセント色 #422eb0 の色相。ここを基準に差分を取る
BASE_HUE = 249
# Only colors in this hue band are rotated (purplish backgrounds, borders, grays, accent)
# この色相帯に入る色だけを回転させる(紫がかった背景・境界・灰色・アクセント)
TINT_RANGE = (235, 262)
PALE_FROM = 0.6

# The six rainbow colors: name -> (hue, saturation scale for light colors). Saturation differs per
# color because some hues (orange, yellow) look washed out at the same saturation as others.
# 虹の 6 色: 名前 → (色相, 明るい色の彩度倍率)。橙や黄は同じ彩度だと薄く見えるので色ごとに変える
COLORS: dict[str, tuple[int, float]] = {
    "Red": (350, 2.4),
    "Orange": (22, 3.0),
    "Yellow": (45, 3.0),
    "Green": (150, 2.0),
    "Blue": (200, 2.6),
    "Violet": (262, 2.0),
}
COLOR_NAMES = list(COLORS)

# Frame colors used only by the special variants; a saturation scale of 0 grays the zone completely
# 特別バリエーション専用の枠色。彩度倍率 0 でその領域は完全な無彩色になる
COLORS["Gold"] = (42, 3.0)
COLORS["Gray"] = (0, 0.0)

# The six frame zones in the order the colors travel, and the shade (0–1) of each zone. Shade pulls
# the light rotated colors toward black; it belongs to the zone, not the color, because the source
# zones differ in how pale they are (the status bar is the palest, the title bar the deepest).
# 枠の 6 領域(色が巡る順)と、領域ごとの濃さ(0〜1)。濃さは回転対象の明るい色を黒へ寄せる。
# 原本の領域ごとの淡さが違う(ステータスバーが最も淡く、タイトルバーが最も濃い)ので、
# 濃さは色ではなく領域の属性にしている
ZONE_ORDER = ["title", "tabs", "panel", "side", "activity", "status"]
ZONE_SHADE: dict[str, float] = {
    "title": 0.10,
    "tabs": 0.18,
    "panel": 0.20,
    "side": 0.20,
    "activity": 0.16,
    "status": 0.26,
}
# The editor zone: everything no frame zone claims, and tokenColors. (hue, saturation, paleness)
# エディタ領域: どの枠領域にも属さないキーと tokenColors。(色相, 彩度倍率, 淡さ)
EDITOR = (40, 0.35, 0.3)  # the Cream recipe / Soap Dish Cream のレシピ
GRAY_EDITOR = (0, 0.0, 0.3)  # the Cream recipe without the warmth / Cream のレシピから暖色を抜いたもの

# The special variants: (name, file id, frame color, editor recipe, dark?). They paint every frame
# zone with the one color; the grayscales desaturate the editor too, and the dark one flips the
# lightness of every color in the file (shadows excepted), turning the light source into a dark theme.
# 特別バリエーション: (テーマ名, ファイル ID, 枠色, エディタのレシピ, ダークか)。枠の全領域を
# その 1 色で塗る。Grayscale はエディタも無彩色にし、Dark はさらに全色の明度を反転して(影は除く)
# ライトの原本をダークテーマにする
SPECIALS: list[tuple[str, str, str, tuple[int, float, float], bool]] = [
    ("Gold", "gold", "Gold", EDITOR, False),
    ("Grayscale Light", "grayscale-light", "Gray", GRAY_EDITOR, False),
    ("Grayscale Dark", "grayscale-dark", "Gray", GRAY_EDITOR, True),
]

# The dark flip: l -> FLOOR + (1 - l) * RANGE. Symmetric around 0.5, with a small floor so that
# pure white lands on a dark gray rather than black. Hue and saturation are kept.
# 明度反転: l → FLOOR + (1 - l) * RANGE。0.5 を中心に対称で、純白が黒ではなく暗い灰に
# 落ちるよう下駄を履かせる。色相と彩度は保つ
DARK_FLIP_FLOOR = 0.05
DARK_FLIP_RANGE = 0.90

# In the frame zones the color's saturation scale and the zone's shade apply to the light colors
# (backgrounds, borders). The dark colors of those zones (icons, text, accents) get these milder
# values instead, and are pulled a little toward black so they still read on a vivid ground.
# 枠の領域では、色の彩度倍率と領域の濃さは明るい色(地・境界)に掛かる。濃い色(アイコン・文字・
# アクセント)にはこちらの控えめな値を使い、鮮やかな地の上でも読めるよう少し黒へ寄せる
DARK_SAT_SCALE = 1.2
DARK_SHADE = 0.18

# First segment of a workbench color key -> zone
# ワークベンチ色キーの先頭セグメント → 領域
ZONE_OF_PREFIX: dict[str, str] = {
    "titleBar": "title",
    "commandCenter": "title",
    "menubar": "title",
    "editorGroupHeader": "tabs",
    "tab": "tabs",
    "breadcrumb": "tabs",
    "breadcrumbPicker": "tabs",
    "activityBar": "activity",
    "activityBarBadge": "activity",
    "activityBarTop": "activity",
    "activityErrorBadge": "activity",
    "activityWarningBadge": "activity",
    "profileBadge": "activity",
    "sideBar": "side",
    "sideBarSectionHeader": "side",
    "sideBarStickyScroll": "side",
    "sideBarTitle": "side",
    "sideBarActivityBarTop": "side",
    "list": "side",
    "listFilterWidget": "side",
    "tree": "side",
    "panel": "panel",
    "panelInput": "panel",
    "panelSection": "panel",
    "panelSectionHeader": "panel",
    "panelStickyScroll": "panel",
    "panelTitle": "panel",
    "panelTitleBadge": "panel",
    "terminal": "panel",
    "terminalCursor": "panel",
    "terminalCommandDecoration": "panel",
    "terminalCommandGuide": "panel",
    "terminalOverviewRuler": "panel",
    "terminalStickyScroll": "panel",
    "terminalStickyScrollHover": "panel",
    "terminalSymbolIcon": "panel",
    "debugConsole": "panel",
    "debugConsoleInputIcon": "panel",
    "debugToolBar": "panel",
    "statusBar": "status",
    "statusBarItem": "status",
}

# Six rainbow colors for bracket pairs and indent guides, taken from the fixed syntax palette so
# they match the rest of the theme: red, orange, amber, green, blue, purple.
# 括弧の対とインデントガイドに使う虹 6 色。テーマの固定構文色から取り、他と馴染ませる:
# 赤・橙・琥珀・緑・青・紫
RAINBOW = ["#d12525", "#b96000", "#c08403", "#008b17", "#0076c5", "#7522d3"]

OVERRIDES: dict[str, str] = {}
for i, c in enumerate(RAINBOW, start=1):
    OVERRIDES[f"editorBracketHighlight.foreground{i}"] = c
    OVERRIDES[f"editorBracketPairGuide.activeBackground{i}"] = c + "cc"
    OVERRIDES[f"editorBracketPairGuide.background{i}"] = c + "4d"
    OVERRIDES[f"editorIndentGuide.activeBackground{i}"] = c + "e6"
    OVERRIDES[f"editorIndentGuide.background{i}"] = c + "66"

# Which key proves each zone in the check at the end, and the hue tolerance
# 最後の検査で領域ごとに見るキーと、色相の許容差
ZONE_PROBES: dict[str, str] = {
    "title": "titleBar.activeBackground",
    "tabs": "tab.inactiveBackground",
    "panel": "panel.background",
    "side": "sideBar.background",
    "activity": "activityBar.background",
    "status": "statusBar.background",
}
EDITOR_PROBE = "editor.background"
HUE_TOLERANCE = 3

HEX_RE = re.compile(r"#([0-9a-fA-F]{6})([0-9a-fA-F]{2})?\b")
KEY_RE = re.compile(r'^\s*(?://\s*)?"([A-Za-z0-9.]+)"\s*:')
NAME_RE = re.compile(r'("name":\s*")[^"]*(")')
TYPE_RE = re.compile(r'("type":\s*")light(")')

Variant = tuple[str, str, dict[str, str], tuple[int, float, float], bool]


def variants() -> list[Variant]:
    """(variant name, file id, zone -> color name, editor recipe, dark?) for the six shifts
    followed by the three special variants.
    6 つのずらしと特別バリエーション 3 本の (テーマ名, ファイル ID, 領域 → 色名, エディタのレシピ, ダークか)"""
    out: list[Variant] = []
    for shift in range(len(COLOR_NAMES)):
        mapping = {zone: COLOR_NAMES[(i + shift) % len(COLOR_NAMES)] for i, zone in enumerate(ZONE_ORDER)}
        name = mapping["title"]  # named after the title bar / タイトルバーの色で名付ける
        out.append((name, name.lower(), mapping, EDITOR, False))
    for name, file_id, color, editor, dark in SPECIALS:
        out.append((name, file_id, {zone: color for zone in ZONE_ORDER}, editor, dark))
    return out


def hex_to_hls(rgb_hex: str) -> tuple[float, float, float]:
    r, g, b = (int(rgb_hex[i : i + 2], 16) / 255 for i in (0, 2, 4))
    return colorsys.rgb_to_hls(r, g, b)


def rotate_hex(rgb_hex: str, hue: int, sat_scale: float, pale: float, shade: float, frame: bool) -> str:
    h, l, s = hex_to_hls(rgb_hex)
    src_hue = h * 360
    if s == 0 or not (TINT_RANGE[0] <= src_hue <= TINT_RANGE[1]):
        return rgb_hex
    h2 = ((src_hue + hue - BASE_HUE) % 360) / 360
    if l >= PALE_FROM:
        s2 = min(1.0, s * sat_scale)
        l2 = l + (1 - l) * pale
        l2 = l2 * (1 - shade)
    elif frame:
        # min() so the achromatic variants (scale 0) gray the dark colors too
        # min() にしてあるのは、無彩色のバリエーション(倍率 0)で濃い色も灰にするため
        s2 = min(1.0, s * min(sat_scale, DARK_SAT_SCALE))
        l2 = l * (1 - DARK_SHADE)
    else:
        s2 = min(1.0, s * sat_scale)
        l2 = l
    r2, g2, b2 = colorsys.hls_to_rgb(h2, l2, s2)
    out = "".join(f"{round(c * 255):02x}" for c in (r2, g2, b2))
    return out.upper() if rgb_hex.isupper() else out


def flip_hex(rgb_hex: str) -> str:
    """Flip the lightness for the dark variant, keeping hue and saturation.
    ダーク版のために明度を反転する。色相と彩度は保つ"""
    h, l, s = hex_to_hls(rgb_hex)
    r, g, b = colorsys.hls_to_rgb(h, DARK_FLIP_FLOOR + (1 - l) * DARK_FLIP_RANGE, s)
    out = "".join(f"{round(c * 255):02x}" for c in (r, g, b))
    return out.upper() if rgb_hex.isupper() else out


def effective_overrides(dark: bool) -> dict[str, str]:
    """The rainbow keys, lightness-flipped for the dark variant.
    虹のキー。ダーク版では明度を反転した値になる"""
    if not dark:
        return OVERRIDES
    return {k: "#" + flip_hex(v[1:7]) + v[7:] for k, v in OVERRIDES.items()}


def zone_of_line(line: str, in_colors: bool) -> str:
    if not in_colors:
        return "editor"
    m = KEY_RE.match(line)
    if not m:
        return "editor"
    return ZONE_OF_PREFIX.get(m.group(1).split(".")[0], "editor")


def rotate_line(line: str, zone: str, mapping: dict[str, str], editor: tuple[int, float, float], dark: bool) -> str:
    if zone == "editor":
        hue, sat_scale, pale = editor
        shade, frame = 0.0, False
    else:
        hue, sat_scale = COLORS[mapping[zone]]
        pale, shade, frame = 0.0, ZONE_SHADE[zone], True
    # Shadows stay dark even in the dark variant; flipping them would turn them into glows
    # 影はダーク版でも暗いまま。反転すると光って見えてしまう
    key_m = KEY_RE.match(line)
    flip = dark and not (key_m and "shadow" in key_m.group(1).lower())

    def repl(m: re.Match) -> str:
        out = rotate_hex(m.group(1), hue, sat_scale, pale, shade, frame)
        if flip:
            out = flip_hex(out)
        return "#" + out + (m.group(2) or "")

    return HEX_RE.sub(repl, line)


def build(source: str, name: str, mapping: dict[str, str], editor: tuple[int, float, float], dark: bool) -> str:
    overrides = effective_overrides(dark)
    lines = source.splitlines(keepends=True)
    out: list[str] = []
    in_colors = False
    colors_open = -1
    seen: set[str] = set()
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('"colors"'):
            in_colors = True
            out.append(line)
            colors_open = len(out)
            continue
        if in_colors and stripped.startswith('"tokenColors"'):
            in_colors = False
        if in_colors:
            m = KEY_RE.match(line)
            key = m.group(1) if m else None
            if key in overrides:
                # Replace the line (active or commented out) with the rainbow value
                # その行(有効でもコメントアウトでも)を虹の値に差し替える
                indent = line[: len(line) - len(line.lstrip())]
                out.append(f'{indent}"{key}": "{overrides[key]}",\n')
                seen.add(key)
                continue
        out.append(rotate_line(line, zone_of_line(line, in_colors), mapping, editor, dark))

    # Keys the source never mentions go right after "colors": {
    # 原本に無いキーは "colors": { の直後に足す
    if colors_open < 0:
        raise SystemExit("source has no \"colors\" section / 原本に colors が無い")
    missing = [f'\t\t"{k}": "{v}",\n' for k, v in overrides.items() if k not in seen]
    out[colors_open:colors_open] = missing

    body = "".join(out)
    body = NAME_RE.sub(lambda m: f"{m.group(1)}{EXTENSION_NAME}: {name}{m.group(2)}", body, count=1)
    if dark:
        body = TYPE_RE.sub(r"\1dark\2", body, count=1)
    return body


# --- verification / 検査 ------------------------------------------------------

def parse_jsonc(text: str) -> dict:
    """Strip // comments and trailing commas, then json.loads.
    // コメントと末尾カンマを取り除いて json.loads する"""
    no_comments = re.sub(r"^\s*//.*$", "", text, flags=re.M)
    no_trailing = re.sub(r",(\s*[}\]])", r"\1", no_comments)
    return json.loads(no_trailing)


def hue_of(rgb_hex: str) -> float:
    return hex_to_hls(rgb_hex.lstrip("#")[:6])[0] * 360


def expect_hue(source_hex: str, target_hue: int) -> float:
    # The probe color sits near, not exactly on, BASE_HUE; expect its own hue plus the rotation
    # 検査する色は基準色相のそばにあるだけなので、その色の色相に回転量を足した値を期待する
    return (hue_of(source_hex) + target_hue - BASE_HUE) % 360


def hue_diff(a: float, b: float) -> float:
    return min(abs(a - b), 360 - abs(a - b))


def check_probe(got_hex: str, source_hex: str, hue: int, sat_scale: float, label: str) -> list[str]:
    """Achromatic zones (scale 0) are checked by saturation, colored ones by hue; the dark flip
    keeps hue, so the same check serves both light and dark variants.
    無彩色の領域(倍率 0)は彩度で、有彩色は色相で検査する。明度反転は色相を保つので、
    ライトとダークで同じ検査が使える"""
    h, _, s = hex_to_hls(got_hex.lstrip("#")[:6])
    if sat_scale == 0:
        if s > 0.02:
            return [f"{label} saturation {s:.2f} is not 0"]
        return []
    want = expect_hue(source_hex, hue)
    if hue_diff(h * 360, want) > HUE_TOLERANCE:
        return [f"{label} hue {h * 360:.0f} is not {want:.0f}"]
    return []


def verify(body: str, source_colors: dict, name: str, mapping: dict[str, str],
           editor: tuple[int, float, float], dark: bool) -> list[str]:
    problems: list[str] = []
    data = parse_jsonc(body)
    colors = data["colors"]
    if data.get("name") != f"{EXTENSION_NAME}: {name}":
        problems.append(f"name is {data.get('name')!r}")
    want_type = "dark" if dark else "light"
    if data.get("type") != want_type:
        problems.append(f"type is {data.get('type')!r}, expected {want_type}")
    for key, value in effective_overrides(dark).items():
        if colors.get(key) != value:
            problems.append(f"{key} = {colors.get(key)!r}, expected {value}")
    for zone, key in ZONE_PROBES.items():
        hue, sat_scale = COLORS[mapping[zone]]
        problems += check_probe(colors[key], source_colors[key], hue, sat_scale, f"{key} ({zone} = {mapping[zone]})")
    problems += check_probe(colors[EDITOR_PROBE], source_colors[EDITOR_PROBE], editor[0], editor[1], EDITOR_PROBE)
    bg_l = hex_to_hls(colors[EDITOR_PROBE].lstrip("#")[:6])[1]
    if dark and bg_l > 0.35:
        problems.append(f"{EDITOR_PROBE} lightness {bg_l:.2f} is not dark")
    if not dark and bg_l < 0.6:
        problems.append(f"{EDITOR_PROBE} lightness {bg_l:.2f} is not light")
    for key, value in colors.items():
        if not re.fullmatch(r"#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?", value):
            problems.append(f"{key} has a malformed color {value!r}")
    return problems


def main() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    source_colors = parse_jsonc(source)["colors"]
    THEMES.mkdir(parents=True, exist_ok=True)
    failed = False
    for name, file_id, mapping, editor, dark in variants():
        body = build(source, name, mapping, editor, dark)
        out = THEMES / f"{file_id}-color-theme.json"
        out.write_text(body, encoding="utf-8")
        colors = parse_jsonc(body)["colors"]
        cells = "  ".join(f"{zone}={mapping[zone][:1]}{colors[key]}" for zone, key in ZONE_PROBES.items())
        print(f"wrote {out.relative_to(ROOT)}  {cells}")
        problems = verify(body, source_colors, name, mapping, editor, dark)
        if problems:
            failed = True
            print(f"  verification failed / 検査に失敗 ({name}):", file=sys.stderr)
            for p in problems:
                print(f"  - {p}", file=sys.stderr)
    if failed:
        sys.exit(1)
    n = len(variants())
    print(f"verified {n} themes: {len(OVERRIDES)} rainbow keys and {len(ZONE_PROBES) + 1} zone checks each OK")


if __name__ == "__main__":
    main()
