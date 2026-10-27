# Development

[English](#english) | [日本語](#日本語)

## English

**Do not edit the theme files by hand; they are generated.** `source/purple-color-theme.json` is a verbatim copy of
Soap Dish Purple. `scripts/build-theme.py` rotates its purple hue band to a different hue per UI zone and writes the
nine files in `themes/` (the six rainbow shifts plus Gold, Grayscale Light and Grayscale Dark), then parses every
output and checks that the name, the type, the 30 rainbow keys and one probe color per zone (hue, or saturation for
the grayscales) are what the knobs say. It exits non-zero otherwise.

```bash
python3 scripts/build-theme.py      # themes/*-color-theme.json, then verifies them
python3 scripts/build-preview.py    # images/preview-*.png and the images/preview.png sheet
python3 scripts/build-icon.py       # images/icon.png
```

All three use the Python standard library only.

### Knobs in `scripts/build-theme.py`

- `COLORS`: hue and saturation scale per color (Red, Orange, Yellow, Green, Blue, Violet). Saturation differs per
  color because some hues look washed out at the same saturation as others.
- `ZONE_ORDER`: the order the colors travel through the zones (`title`, `tabs`, `panel`, `side`, `activity`,
  `status`). The Red theme assigns the colors to the zones in this order; each further theme shifts by one and is
  named after its title bar. Reorder this to change where the colors land; the other five follow.
- `ZONE_SHADE`: shade (0–1) per zone, pulling the light rotated colors toward black. Shade belongs to the zone,
  not the color, because the source zones differ in how pale they are (the status bar is the palest, the title bar
  the deepest) and the shade evens that out.
- `EDITOR`: hue, saturation scale and paleness for everything no frame zone claims, and for `tokenColors`. It is
  the Soap Dish Cream recipe (40°, ×0.35, paleness 0.3).
- `DARK_SAT_SCALE`, `DARK_SHADE`: the milder knobs for the dark colors of the frame zones (icons, text, accents),
  so they keep reading on a vivid ground.
- `ZONE_OF_PREFIX`: maps the first segment of a workbench color key (`titleBar`, `tab`, `sideBar`, …) to a zone.
  Keys not listed fall into the editor zone.
- `SPECIALS`: the three single-color variants (name, file id, frame color, editor recipe, dark?). Each paints
  every frame zone with one color from `COLORS` (`Gold` at 42°, `Gray` at saturation scale 0, which grays the
  zone completely). The grayscales use `GRAY_EDITOR` (the Cream recipe without the warmth), and the dark one
  flips the lightness of every color in the file with `DARK_FLIP_FLOOR`/`DARK_FLIP_RANGE`
  (`l → FLOOR + (1 − l) × RANGE`), keeping hue and saturation; keys containing `shadow` stay dark.
- `RAINBOW`: the six colors for bracket pairs and indent guides; `OVERRIDES` is built from it. The dark variant
  gets the same colors lightness-flipped.
- Only colors whose hue falls inside `TINT_RANGE` (235°–262° in the source: backgrounds, borders, purplish grays,
  the accent) are rotated. Syntax colors and the semantic reds and greens lie outside the band and never move.

Themes are registered in `package.json` under `contributes.themes`; the file id is the lower-cased color name
(`gold`, `grayscale-light` and `grayscale-dark` for the specials, the last with `"uiTheme": "vs-dark"`).

To pick up a newer Soap Dish Purple, copy it over `source/purple-color-theme.json` and regenerate.

### Trying and packaging

Open this folder in VS Code and press `F5`; edits to `themes/*.json` apply live in the Extension Development Host.
`.vscode/` is git-ignored, so if `F5` does nothing, run `Debug: Start Debugging` from the Command Palette and choose
the extension host. `Developer: Inspect Editor Tokens and Scopes` shows which scope and color a token gets.

```bash
mkdir -p dist
npx --yes @vscode/vsce package --out dist/soap-bubble-0.0.2.vsix
```

Theme files are JSONC: comments and trailing commas are allowed, and a long list of unset keys is left commented
out in each file. Later rules in `tokenColors` win over earlier ones.

### Layout

```
package.json                  # manifest: name, icon, the nine themes
images/
├── icon.png                  # extension icon (generated)
├── preview.png               # all nine at half size (generated, not packaged)
└── preview-<color>.png       # one per theme (generated, not packaged)
themes/<color>-color-theme.json   # nine generated files
source/purple-color-theme.json    # copy of Soap Dish Purple, the input (not packaged)
scripts/
├── build-theme.py            # zone-wise hue rotation, six shifts plus three specials, verification
├── build-preview.py          # draw the previews
└── build-icon.py             # draw images/icon.png
```

## 日本語

**テーマファイルは生成物なので手で編集しない。** `source/purple-color-theme.json` は Soap Dish Purple の写し。
`scripts/build-theme.py` がその紫の色相帯を UI の領域ごとに別の色相へ回して `themes/` の 9 本(虹の 6 つのずらしと
Gold・Grayscale Light・Grayscale Dark)を書き出し、続けて全出力を解析して名前・type・虹の 30 キー・領域ごとの検査色 1 つ
(色相。Grayscale は彩度)がつまみ通りかを確かめる。ずれていれば非ゼロで終了する。

```bash
python3 scripts/build-theme.py      # themes/*-color-theme.json を生成して検査
python3 scripts/build-preview.py    # images/preview-*.png と一覧の images/preview.png
python3 scripts/build-icon.py       # images/icon.png
```

3 つとも Python の標準ライブラリだけで動く。

### `scripts/build-theme.py` のつまみ

- `COLORS`: 色ごとの色相と彩度倍率(Red・Orange・Yellow・Green・Blue・Violet)。橙や黄は同じ彩度だと薄く見えるので色ごとに変えている
- `ZONE_ORDER`: 色が領域(`title`・`tabs`・`panel`・`side`・`activity`・`status`)を巡る順。Red テーマはこの順に色を当て、
  以降のテーマは 1 つずつずらしてタイトルバーの色で名付ける。色の置き場所を変えるにはここを並べ替える。残り 5 つは追従する
- `ZONE_SHADE`: 領域ごとの濃さ(0〜1)。回転対象の明るい色を黒へ寄せる。原本の領域ごとの淡さが違う(ステータスバーが最も淡く、
  タイトルバーが最も濃い)ので、濃さは色ではなく領域の属性にして揃えている
- `EDITOR`: どの枠領域にも属さないキーと `tokenColors` の色相・彩度倍率・淡さ。Soap Dish Cream のレシピ(40°、×0.35、淡さ 0.3)
- `DARK_SAT_SCALE`・`DARK_SHADE`: 枠の領域の濃い色(アイコン・文字・アクセント)向けの控えめなつまみ。鮮やかな地の上でも読めるようにする
- `ZONE_OF_PREFIX`: ワークベンチ色キーの先頭セグメント(`titleBar`・`tab`・`sideBar` など)から領域への対応。載っていないキーは
  エディタ領域に落ちる
- `SPECIALS`: 単色のバリエーション 3 本(テーマ名・ファイル ID・枠色・エディタのレシピ・ダークか)。枠の全領域を `COLORS` の
  1 色で塗る(`Gold` は 42°、`Gray` は彩度倍率 0 で完全な無彩色)。Grayscale のエディタは `GRAY_EDITOR`(Cream のレシピから
  暖色を抜いたもの)。Dark はさらに全色の明度を `DARK_FLIP_FLOOR`・`DARK_FLIP_RANGE`(`l → FLOOR + (1 − l) × RANGE`)で
  反転する。色相と彩度は保ち、キー名に `shadow` を含む色は暗いまま
- `RAINBOW`: 括弧の対とインデントガイドの 6 色。そこから `OVERRIDES` が組み立てられる。Dark では同じ色の明度を反転した値になる
- 回転するのは色相が `TINT_RANGE`(原本の 235°〜262°。背景・境界・紫がかった灰・アクセント)に入る色だけ。構文色と、
  意味を持つ赤や緑は帯の外にあるので動かない

テーマの登録は `package.json` の `contributes.themes`。ファイル ID は色名の小文字(特別バリエーションは `gold`・
`grayscale-light`・`grayscale-dark` で、最後のものだけ `"uiTheme": "vs-dark"`)。

新しい Soap Dish Purple を取り込むなら、`source/purple-color-theme.json` に上書きして再生成する。

### 試す・パッケージする

このフォルダを VS Code で開いて `F5`。拡張機能開発ホストで `themes/*.json` の編集が即時反映される。`.vscode/` は git 管理外なので、
F5 で何も起きなければコマンドパレットから `Debug: Start Debugging` を実行して拡張機能ホストを選ぶ。
`Developer: Inspect Editor Tokens and Scopes` でトークンのスコープと適用色を見られる。

```bash
mkdir -p dist
npx --yes @vscode/vsce package --out dist/soap-bubble-0.0.2.vsix
```

テーマファイルは JSONC で、コメントと末尾カンマが使える。各ファイルには未設定のキーがコメントアウトのまま並んでいる。
`tokenColors` は後に書いたルールが勝つ。

### ファイル構成

```
package.json                  # 拡張のマニフェスト(名前・アイコン・9 テーマの登録)
images/
├── icon.png                  # 拡張アイコン(生成物)
├── preview.png               # 9 テーマを半分の大きさで並べた一覧(生成物、.vsix には含めない)
└── preview-<color>.png       # テーマごとの模式図(生成物、.vsix には含めない)
themes/<color>-color-theme.json   # 生成物 9 本
source/purple-color-theme.json    # Soap Dish Purple の写し。生成の入力(.vsix には含めない)
scripts/
├── build-theme.py            # 領域ごとの色相回転・6 つのずらしと特別バリエーション 3 本・検査
├── build-preview.py          # プレビューを描く
└── build-icon.py             # images/icon.png を描く
```
