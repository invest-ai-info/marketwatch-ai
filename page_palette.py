# -*- coding: utf-8 -*-
"""記事以外のページの部品の色をトップの色にそろえ、暗い表示を足す（2026-11-21 オーナー「部品の色をそろえる」「暗い表示を足す」）。

対象＝`apply_site_frame.V2_PAGES` のうち、自分の暗い表示を持たないページ（カレンダー・市場健康度・出来高急増など10本・
`apply_site_frame.has_own_dark` が False）。暗い表示を持つページ（シグナル研究・解説記事の一覧など）には何もしない。

やり方（**元の CSS は書き換えない**）：ページ自身の <style>（data-mw-* の付いた枠・部品の <style> は除く）と、
HTML に直接書かれた色（style="…"）を読み、`</body>` の直前に <style data-mw-palette> を1つ置く。冪等（前の分を消して作り直す）。
  ① 明るい表示＝ページ自身の CSS の色を、トップの色（`TOP_LIGHT`＝generate_market_news.HOME_V2_CSS の :root と同じ値）に
     いちばん近い役目で置き換える（灰色→地・枠・文字・薄い文字／青→ブランド／緑→上げ／赤→下げ／淡い地→トップの淡い4色）。
     紫・桃・茶など役目の無い色はそのまま。HTML に直接書かれた色（データで決まる色＝濃さに意味がある）は明るい表示では触らない
  ② 暗い表示（body.dark）＝①の色をトップの暗い色（`TOP_DARK`）へ。トップの色に当たらない色と HTML に直接書かれた色は、
     役目（地・文字・枠）ごとに明るさを連続に移す（濃さの順は保つ）。グラフ（canvas）は白い地のまま（JavaScript の色を変えないため）
スイッチ＝`ON`（1行）／環境変数 PALETTE=0/1。オフにすると次の生成・`apply_site_frame.py --all` で <style data-mw-palette> が消える。
テスト＝tests/test_page_palette.py
"""
import colorsys
import os
import re

ON = True

# トップの色（generate_market_news.HOME_V2_CSS の :root と body.dark＝テストが突き合わせる）
TOP_LIGHT = {"bg": "#ffffff", "surface": "#f5f8fc", "line": "#dbe3ee", "ink": "#1b2433", "muted": "#526075",
             "faint": "#7b879a", "brand": "#1766d6", "link": "#1263cc", "up": "#16884a", "down": "#d9363e",
             "chip": "#edf2f9", "teal": "#0b8f82", "amber": "#c97a00", "coral": "#e0493f",
             "t-blue": "#eaf3ff", "t-teal": "#e4f6f2", "t-amber": "#fff3dc", "t-coral": "#fdecea"}
TOP_DARK = {"bg": "#0e141c", "surface": "#151d28", "line": "#283444", "ink": "#e7edf5", "muted": "#a1adbd",
            "faint": "#7f8b9b", "brand": "#5b9dff", "link": "#7fb2ff", "up": "#4cc77a", "down": "#ff7a72",
            "chip": "#1b2533", "teal": "#3cc7b8", "amber": "#f0b24a", "coral": "#ff7a6e",
            "t-blue": "#13233a", "t-teal": "#102c2a", "t-amber": "#2e2410", "t-coral": "#351c1b"}
_TOKEN_OF = {v: k for k, v in TOP_LIGHT.items()}

_STYLE_RE = re.compile(r"<style([^>]*)>(.*?)</style>", re.S)
_PALETTE_RE = re.compile(r"\n?<style data-mw-palette>.*?</style>", re.S)
_COLOR_RE = re.compile(r"#[0-9a-fA-F]{8}\b|#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3,4}\b|rgba?\([^)]*\)|\b(?:white|black)\b")
_WIDGET_SEL_RE = re.compile(r"mw-ad|mw-newsletter|back-to-top|ss-|theme-toggle|body\.dark")
_SKIP_PROPS = ("box-shadow", "text-shadow", "filter", "transition", "animation", "mask")


def enabled():
    v = os.environ.get("PALETTE")
    if v in ("0", "1"):
        return v == "1"
    return ON


# ── 色 ──
def parse(c):
    """'#abc'・'#aabbcc'・'#aabbccdd'・'rgb(…)'・'rgba(…)'・'white'・'black' → (r, g, b, a)（0〜255・a は 0〜1）。読めなければ None"""
    c = c.strip().lower()
    if c == "white":
        return 255, 255, 255, 1.0
    if c == "black":
        return 0, 0, 0, 1.0
    if c.startswith("#"):
        h = c[1:]
        if len(h) in (3, 4):
            h = "".join(ch * 2 for ch in h)
        if len(h) not in (6, 8):
            return None
        a = int(h[6:8], 16) / 255 if len(h) == 8 else 1.0
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a
    m = re.match(r"rgba?\(\s*([\d.]+)[\s,]+([\d.]+)[\s,]+([\d.]+)(?:\s*[,/]\s*([\d.]+%?))?\s*\)", c)
    if not m:
        return None
    a = m.group(4)
    a = 1.0 if a is None else (float(a[:-1]) / 100 if a.endswith("%") else float(a))
    return int(float(m.group(1))), int(float(m.group(2))), int(float(m.group(3))), a


def fmt(r, g, b, a=1.0):
    r, g, b = (max(0, min(255, int(round(x)))) for x in (r, g, b))
    if a >= 0.999:
        return f"#{r:02x}{g:02x}{b:02x}"
    return f"rgba({r},{g},{b},{round(a, 3):g})"


def hls(r, g, b):
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    return h * 360, l, s


def from_hls(h, l, s):
    r, g, b = colorsys.hls_to_rgb((h % 360) / 360, max(0.0, min(1.0, l)), max(0.0, min(1.0, s)))
    return r * 255, g * 255, b * 255


def _neutral(rgb, l):
    """灰色か。HLS の彩度は白に近い色で大きく出る（#f8fafc＝0.38）ので、色の幅（いちばん強い色 − いちばん弱い色）で見る。
    明るい色はわずかな幅でも淡い色に見えるので基準を小さく（0.06）、中くらい・暗い色は青みの灰色（slate）を灰色に（0.17）"""
    chroma = (max(rgb) - min(rgb)) / 255
    return chroma < (0.06 if l >= 0.80 else 0.17)


def light_token(rgb, role):
    """明るい表示の役目（TOP_LIGHT のキー）。役目の無い色（紫・桃・茶など）は None＝そのまま"""
    hexc = fmt(*rgb)
    if hexc in _TOKEN_OF:                                 # トップの色はそのまま（何度かけても同じ）
        return _TOKEN_OF[hexc]
    h, l, s = hls(*rgb)
    if _neutral(rgb, l) or l < 0.22:
        if l >= 0.985:
            return "bg"
        if l >= 0.935:
            return "surface"
        if l >= 0.80:
            return "line"
        if l >= 0.55:
            return "faint"
        if l >= 0.30:
            return "muted"
        return "ink"
    if l >= 0.80:                                         # 淡い色＝地なら淡い4色・枠なら枠の色・文字ならそのまま
        if role == "border":
            return "line"
        if role == "text":
            return None
        if 190 <= h < 300:
            return "t-blue"
        if 80 <= h < 190:
            return "t-teal"
        if 20 <= h < 80:
            return "t-amber"
        return "t-coral"
    if 190 <= h < 250:
        return "link" if role == "text" else "brand"
    if 90 <= h < 170:
        return "up"
    if 170 <= h < 190:
        return "teal"
    if 20 <= h < 70 and l >= 0.30:
        return "amber"
    if h >= 345 or h < 15:
        return "down"
    return None


def to_light(c, role):
    p = parse(c)
    if p is None:
        return c
    r, g, b, a = p
    if role == "text" and (r, g, b) == (255, 255, 255):
        return c                                          # ボタンの上の白い文字はそのまま
    t = light_token((r, g, b), role)
    if t is None:
        return c
    rr, gg, bb, _ = parse(TOP_LIGHT[t])
    return fmt(rr, gg, bb, a)


def to_dark(c, role):
    """明るい表示の色（①のあと）→ 暗い表示の色。トップの色はトップの暗い色へ、それ以外は役目ごとに明るさを移す"""
    p = parse(c)
    if p is None:
        return c
    r, g, b, a = p
    hexc = fmt(r, g, b)
    tok = _TOKEN_OF.get(hexc)
    if role == "text":
        if (r, g, b) == (255, 255, 255):
            return c
        if tok in ("brand", "link"):
            tok = "link"
        if tok and tok not in ("bg", "surface", "chip", "line") and not tok.startswith("t-"):
            return fmt(*parse(TOP_DARK[tok])[:3], a)
    elif role == "bg":
        if tok in ("bg", "surface"):
            return fmt(*parse(TOP_DARK["surface"])[:3], a)
        if tok in ("chip", "line") or (tok or "").startswith("t-"):
            return fmt(*parse(TOP_DARK[tok])[:3], a)
        if tok in ("brand", "link", "up", "down", "teal", "amber", "coral"):
            return c                                      # ボタン・バッジの濃い地はそのまま（白い文字が読める）
    elif role == "border":
        if tok in ("line", "chip", "surface", "bg") or (tok or "").startswith("t-"):
            return fmt(*parse(TOP_DARK["line"])[:3], a)
        if tok and tok in TOP_DARK:
            return fmt(*parse(TOP_DARK[tok])[:3], a)
    h, l, s = hls(r, g, b)
    if role == "text":
        if l > 0.62:
            return c
        nl, ns = 0.93 - l * 0.45, min(s, 0.8)
    elif role == "bg":
        if l < 0.5:
            return c                                      # 濃い地（ボタン・今日の印）はそのまま
        nl, ns = 0.085 + (1 - l) * 0.55, min(s, 0.45)
    else:
        nl, ns = (0.13 + (1 - l) * 0.6, min(s, 0.35)) if l >= 0.6 else (0.38 + (0.6 - l) * 0.3, min(s, 0.6))
    return fmt(*from_hls(h, nl, ns), a)


def role_of(prop):
    p = prop.strip().lower()
    if p.startswith("background"):
        return "bg"
    if p.startswith("border") or p.startswith("outline") or p.startswith("column-rule"):
        return "border"
    if p in ("color", "fill", "stroke", "caret-color", "text-decoration-color", "-webkit-text-fill-color"):
        return "text"
    return None


def map_value(value, role, fn):
    return _COLOR_RE.sub(lambda m: fn(m.group(0), role), value)


# ── CSS を読む ──
def _rules(css):
    """平らな規則と @media の中の規則 → [(前置き, セレクタ, 宣言)]。前置き＝'' か '@media …'。@keyframes 等は飛ばす"""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    out, i, n = [], 0, len(css)
    while i < n:
        j = css.find("{", i)
        if j < 0:
            break
        head = css[i:j].strip()
        if head.startswith("@media") or head.startswith("@supports"):
            depth, k = 1, j + 1
            while k < n and depth:
                depth += {"{": 1, "}": -1}.get(css[k], 0)
                k += 1
            for _, sel, body in _rules(css[j + 1:k - 1]):
                out.append((head, sel, body))
            i = k
            continue
        k = css.find("}", j)
        if k < 0:
            break
        if not head.startswith("@"):
            out.append(("", head, css[j + 1:k]))
        else:                                             # @keyframes・@font-face＝中身ごと飛ばす
            depth, k2 = 1, j + 1
            while k2 < n and depth:
                depth += {"{": 1, "}": -1}.get(css[k2], 0)
                k2 += 1
            k = k2 - 1
        i = k + 1
    return out


def _decls(body):
    return [(p.strip(), v.strip()) for p, _, v in (d.partition(":") for d in body.split(";")) if _ and p.strip()]


def _dark_sel(sel):
    out = []
    for s in sel.split(","):
        s = s.strip()
        if not s:
            continue
        if s in (":root", "html"):
            out.append("body.dark")
        elif re.match(r"html\s+body\b", s):
            out.append(re.sub(r"^html\s+body", "html body.dark", s))
        elif re.match(r"body\b", s):
            out.append("body.dark" + s[4:])
        elif re.match(r"html\b", s):
            out.append("html body.dark" + s[4:] if s[4:5] in (" ", ">") else "body.dark")
        else:
            out.append("body.dark " + s)
    return ",".join(out)


def own_css(text):
    """ページ自身の CSS（data-mw-* の付いた <style> は除く）"""
    return "\n".join(m.group(2) for m in _STYLE_RE.finditer(text) if "data-mw" not in m.group(1))


def css_layers(css):
    """→ (明るい表示の規則, 暗い表示の規則)。変わる宣言だけを書く"""
    light, dark = [], []
    for media, sel, body in _rules(css):
        if _WIDGET_SEL_RE.search(sel):
            continue
        lt, dk = [], []
        for prop, val in _decls(body):
            role = role_of(prop)
            if role is None or prop.lower().startswith(_SKIP_PROPS) or not _COLOR_RE.search(val):
                continue
            imp = " !important" if "!important" in val else ""
            v = val.replace("!important", "").strip()
            lv = map_value(v, role, to_light)
            dv = map_value(lv, role, to_dark)
            if lv != v:
                lt.append(f"{prop}:{lv}{imp}")
            if dv != lv:
                dk.append(f"{prop}:{dv}{imp}")
        for acc, items, s in ((light, lt, sel), (dark, dk, _dark_sel(sel))):
            if items:
                rule = f"{s}{{{';'.join(items)}}}"
                acc.append(f"{media}{{{rule}}}" if media else rule)
    return light, dark


_INLINE_RE = re.compile(r'\sstyle="([^"]*)"')


def inline_dark(text):
    """HTML に直接書かれた色 → 暗い表示の上書き（属性の文字で選ぶ・!important）。同じ結果はまとめる"""
    body = text.split("<body", 1)[1] if "<body" in text else text
    groups = {}
    for m in _INLINE_RE.finditer(body):
        for d in m.group(1).split(";"):
            prop, _, val = d.partition(":")
            role = role_of(prop)
            if not _ or role is None or not _COLOR_RE.search(val):
                continue
            dv = map_value(val.strip(), role, to_dark)
            if dv == val.strip():
                continue
            raw = d.strip()
            esc = raw.replace("\\", "\\\\").replace('"', '\\"')
            sels = (f'body.dark [style^="{esc}"]', f'body.dark [style*=";{esc}"]', f'body.dark [style*="; {esc}"]')
            groups.setdefault(f"{prop.strip()}:{dv}!important", set()).update(sels)
    return [f"{','.join(sorted(s))}{{{k}}}" for k, s in sorted(groups.items())]


# 暗い表示の土台（ページ側に body.dark が無いので、地・文字・見出し・リンク・フッター・入力欄をトップの暗い色に）
BASE_DARK = (
    f"body.dark{{background:{TOP_DARK['bg']};color:{TOP_DARK['ink']}}}"
    f"body.dark main,body.dark .container{{color:{TOP_DARK['ink']}}}"
    f"body.dark h1,body.dark h2,body.dark h3,body.dark h4{{color:{TOP_DARK['ink']}}}"
    f"body.dark a{{color:{TOP_DARK['link']}}}"
    f"body.dark footer{{background:{TOP_DARK['bg']};border-top-color:{TOP_DARK['line']};color:{TOP_DARK['muted']}}}"
    f"body.dark footer a{{color:{TOP_DARK['muted']}}}"
    f"body.dark .breadcrumb{{color:{TOP_DARK['muted']}}}"
    f"body.dark input,body.dark select,body.dark textarea{{background:{TOP_DARK['surface']};color:{TOP_DARK['ink']};"
    f"border-color:{TOP_DARK['line']}}}"
    "body.dark main canvas{background:#ffffff;border-radius:8px}"      # グラフの色は JavaScript の中＝白い地のまま
)


def build(text):
    """→ <style data-mw-palette>…</style>（置くものが無ければ ''）"""
    light, dark = css_layers(own_css(text))
    dark += inline_dark(text)
    css = "".join(light) + BASE_DARK + "".join(dark)
    return f"<style data-mw-palette>{css}</style>"


def strip(text):
    return _PALETTE_RE.sub("", text)


def apply(text, on=True):
    """<style data-mw-palette> を </body> の直前に1つ（on=False なら取り除くだけ）。冪等"""
    base = strip(text)
    if not on:
        return base
    tag = build(base)
    i = base.rfind("</body>")
    if i < 0:
        return base
    return base[:i] + "\n" + tag + base[i:]                 # 改行は前に（strip が "\n<style…>" ごと消す＝元に戻る）
