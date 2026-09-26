# -*- coding: utf-8 -*-
"""サイト共通の枠を全ページへ冪等に敷く（2026-09-23 オーナー判断
「残りのページも同じようなレイアウトで」＝共通の枠だけ。中身はそのまま）。

  ① ナビ11ボタンをパソコン幅（900px〜）で 6＋5 の2段に
     （<style data-mw-frame> を </head> 直前へ。広告枠の上下 40px＝トップと同じ間隔もここ）
  ② 解説記事のヘッダーをサイト標準（ロゴ＋サイト説明＋区分名）に揃える
  ③ 解説記事のナビを 11 ボタン標準に揃える（ボタン抜け・独自ラベル・独自 <nav> を置換）

🔑 update-market-news.yml が毎回 --all で回す。クラウドの記事レーン（news / signal-lab 等）は
   毎日 AI にヘッダーとナビを書かせるので形が揺れる（実測 2026-09-23: 解説記事 495本中
   ヘッダー187本・ナビ282本が標準外。166本は「🏦 大量保有報告」抜けの10ボタン）。
   公開時に1回直すだけでは必ず腐る＝inject_ads / apply_series_nav と同じく毎回かける。
🔑 生成スクリプトが作るページ（トップ・カレンダー等・シグナル成績・YouTube要約・政治発言・
   週次/月次レポート・指標プレビュー）は各スクリプトが FRAME_STYLE_TAG を import して
   </head> 直前に置く＝このファイルが枠の単一の真実。
⚠️ 触るのは <head> の末尾・サイトヘッダー・サイトナビだけ。本文・記事メタ行には触らない。
⚠️ 記事の見出し（<h1>）を含む <header> はサイトヘッダーではない（記事の表紙）ので残す。

使い方:
  python apply_site_frame.py                 # dry-run（--all と同じ対象）
  python apply_site_frame.py --all           # guide-*.html と STATIC_PAGES に適用
  python apply_site_frame.py --files a.html  # 指定ページに適用（guide 以外は ① だけ）
"""
import glob
import os
import re
import sys

LOGO_SVG = ('<svg viewBox="0 0 96 96" style="width:27px;height:27px;vertical-align:-4px;margin-right:2px" '
            'aria-hidden="true"><rect x="2" y="2" width="92" height="92" rx="21" fill="#1E3A6E"/>'
            '<polyline points="16,72 34,50 50,58 70,32" fill="none" stroke="#ffffff" stroke-width="7" '
            'stroke-linecap="round" stroke-linejoin="round"/><circle cx="74" cy="27" r="10.5" fill="#E8A317" '
            'stroke="#ffffff" stroke-width="4"/></svg>')
TAGLINE = "日本人投資家のためのマーケット情報サイト"
SEC_OPEN = ('<div style="margin-top:11px;padding-top:11px;border-top:1px solid rgba(128,128,128,.22)">'
            '<div style="font-size:1.3rem;font-weight:700;color:#1E3A6E">')

NAV_BUTTONS = [
    ("index.html", "🏠 トップページ"),
    ("political-feed.html", "🚨 政治発言ライブ"),
    ("track-record.html", "🧪 シグナル研究"),   # 2026-09-26 オーナー判断「シグナル成績」→研究を主軸に
    ("calendar.html", "📅 経済カレンダー"),
    ("guides.html", "📚 解説記事"),
    ("guide-investment-books.html", "📖 投資本"),
    ("holdings.html", "🏦 大量保有報告"),
    ("market-health.html", "🩺 市場健康度"),
    ("hot-assets.html", "🔥 出来高急増"),
    ("charts.html", "📈 150年チャート"),
    ("youtube-summary.html", "📺 YouTube要約"),
]
_CORE_HREFS = {h for h, _ in NAV_BUTTONS}
DEFAULT_CURRENT = "guides.html"
SELF_CURRENT = {"guide-investment-books.html": "guide-investment-books.html"}
SECTION_DEFAULT = "📚 解説記事"
SECTION_BY_PREFIX = [
    ("guide-company-", "🔬 数字で見る、話題の企業"),
    ("guide-new-books", "📖 投資本 新刊ウォッチ"),
    ("guide-investment-books", "📖 投資本"),
]
# 生成スクリプトを持たない静的ページ（① だけかける。ヘッダーとナビは各ページのもの）
STATIC_PAGES = ["guides.html", "about.html", "contact.html", "privacy.html", "holdings.html"]
THEME_BTN_STYLE = ("position:fixed;top:16px;right:16px;width:42px;height:42px;border-radius:50%;"
                   "border:1px solid #d0d7de;background:#fff;cursor:pointer;z-index:9999;"
                   "box-shadow:0 2px 8px rgba(0,0,0,.1);font-size:18px;display:flex;align-items:center;"
                   "justify-content:center")

# ── ① 枠の CSS ───────────────────────────────────────────────
_BTN_2ROW = ("box-sizing:border-box;flex:0 0 calc((100% - 50px)/6);min-width:0;padding:11px 8px;"
             "font-size:.9rem;white-space:nowrap")
# トップ（generate_market_news）もこれを使う。スマホの2列は各ページの既存 @media のまま
NAV_2ROW_CSS = ("@media(min-width:900px){.nav-bar{display:flex;flex-wrap:wrap;justify-content:center;"
                "max-width:1140px;gap:10px}.nav-bar .nav-btn{" + _BTN_2ROW + "}}")
# ③ で置き換えたナビ（class に mwf-nav）は、ページ側の CSS が標準と違っても同じ見た目になるよう
# 標準の .nav-bar / .nav-btn をここで持つ（独自ページの `nav a{...}` 等より強い指定にしてある）
_N = "nav.nav-bar.mwf-nav"
_B = _N + " a.nav-btn"
MWF_NAV_CSS = (
    _N + "{display:flex;flex-wrap:wrap;gap:10px;justify-content:center;max-width:1000px;margin:0 auto 28px;"
    "padding:0;background:none;border:0;box-shadow:none;position:static;box-sizing:border-box}"
    "body>" + _N + "{margin-top:24px;padding:0 16px}"
    + _B + "{box-sizing:border-box;display:inline-flex;align-items:center;justify-content:center;gap:8px;"
    "padding:11px 20px;background:#f6f8fa;border:1px solid #d0d7de;border-radius:10px;color:#57606a;text-decoration:none;"
    "font-size:.95rem;font-weight:600;line-height:1.4;margin:0;transition:all .2s;min-width:170px}"
    + _B + ":hover{border-color:#0969da;color:#0969da}"
    + _B + ".current{background:#1E3A6E;border-color:#1E3A6E;color:#fff}"
    "@media(max-width:700px){" + _N + "{display:grid;grid-template-columns:1fr 1fr;gap:8px}"
    + _B + "{min-width:0;width:100%;padding:10px 8px;font-size:.82rem}}"
    "@media(min-width:900px){" + _N + "{max-width:1140px}" + _B + "{" + _BTN_2ROW + "}}"
    "body.dark " + _B + "{background:#161b22;border-color:#30363d;color:#8b949e}"
    "body.dark " + _B + ":hover{border-color:#58a6ff;color:#58a6ff}"
    "body.dark " + _B + ".current{background:#2C4F8F;border-color:#58a6ff;color:#fff}"
)
# ② で置き換えたヘッダー（data-mw-frame 付き）も同じ考え方で標準の見た目を持たせる
_H = "header[data-mw-frame]"
MWF_HEADER_CSS = (
    _H + "{box-sizing:border-box;display:block;background:linear-gradient(135deg,#f6f8fa,#fff);"
    "border-bottom:1px solid #d0d7de;padding:24px 32px;margin:0;text-align:left;position:static;box-shadow:none;color:#1f2328}"
    + _H + " .header-inner{display:block;max-width:1200px;margin:0 auto;padding:0}"
    + _H + " .header-title{font-size:1.6rem;font-weight:700;line-height:1.3;max-width:none;margin:0;padding:0;"
    "background:linear-gradient(90deg,#1E3A6E,#2C4F8F);-webkit-background-clip:text;"
    "-webkit-text-fill-color:transparent;background-clip:text}"
    + _H + " .header-meta{font-size:.85rem;color:#57606a;margin:4px 0 0}"
    "@media(max-width:700px){" + _H + "{padding:18px 20px}}"
    "body.dark " + _H + "{background:linear-gradient(135deg,#161b22,#0d1117);border-bottom-color:#30363d}"
    "body.dark " + _H + " .header-meta{color:#8b949e}"
)
# 広告枠の上下（inject_ads の .mw-ad は 32px。トップの .ad-gap と同じ 40px に）
AD_GAP_CSS = "div.mw-ad{margin-top:40px;margin-bottom:40px}"

FRAME_CSS = NAV_2ROW_CSS + MWF_NAV_CSS + MWF_HEADER_CSS + AD_GAP_CSS
FRAME_STYLE_TAG = "<style data-mw-frame>" + FRAME_CSS + "</style>"

_STYLE_RE = re.compile(r"<style data-mw-frame>.*?</style>", re.S)
_HEADER_RE = re.compile(r"<header(?=[\s>])[^>]*>.*?</header>", re.S)
_NAV_RE = re.compile(r"(?P<indent>[ \t]*)<nav(?=[\s>])[^>]*>.*?</nav>", re.S)
_BODY_RE = re.compile(r"<body[^>]*>")
_SITE_HEADER_MARKS = ("MarketWatch", 'rx="21" fill="#1E3A6E"', "header-title", "header-meta")
_BUTTON_RE = re.compile(r"<button\b[^>]*theme-toggle[^>]*>.*?</button>|<button\b[^>]*>.*?</button>", re.S)


def section_for(name):
    for prefix, label in SECTION_BY_PREFIX:
        if name.startswith(prefix):
            return label
    return SECTION_DEFAULT


def build_header(section):
    return ("<header data-mw-frame>\n"
            '  <div class="header-inner">\n'
            f'    <div class="header-title">{LOGO_SVG} MarketWatch AI</div>\n'
            f'    <div class="header-meta">{TAGLINE}</div>\n'
            f"    {SEC_OPEN}{section}</div></div>\n"
            "  </div>\n"
            "</header>")


def build_nav(indent, current=DEFAULT_CURRENT, cls="nav-bar mwf-nav"):
    lines = [f'{indent}<nav class="{cls}">']
    for href, label in NAV_BUTTONS:
        c = "nav-btn current" if href == current else "nav-btn"
        lines.append(f'{indent}  <a class="{c}" href="{href}">{label}</a>')
    lines.append(f"{indent}</nav>")
    return "\n".join(lines)


def is_std_header(block):
    return (LOGO_SVG in block and TAGLINE in block and SEC_OPEN in block
            and 'class="header-title"' in block and "<button" not in block and "<nav" not in block)


def _core_links(block):
    hrefs = re.findall(r'href="(?:\.\./|/)?([^"#?]+)"', block)
    return {h for h in hrefs if h in _CORE_HREFS}


def apply_style(text):
    """① 枠の <style> を </head> 直前に1つだけ置く（中身が古ければ差し替え）。"""
    m = _STYLE_RE.search(text)
    if m:
        return text if m.group(0) == FRAME_STYLE_TAG else text[:m.start()] + FRAME_STYLE_TAG + text[m.end():]
    # </head> の無い記事がある（signal-lab #029 は </head> も <body> も無い）。その時は本文の手前に置く
    for mark in ("</head>", "<body", "<header", "<main"):
        i = text.find(mark)
        if i >= 0:
            return text[:i] + FRAME_STYLE_TAG + "\n" + text[i:]
    return text


def apply_header(text, name):
    """② サイトヘッダーを標準形に。記事の表紙（<h1> 入り）の <header> は対象外。"""
    site = None
    for m in _HEADER_RE.finditer(text):
        blk = m.group(0)
        # ロゴの図形だけで社名の文字が無いヘッダーもある（signal-lab の独自版）ので目印を複数見る
        if "<h1" not in blk and any(k in blk for k in _SITE_HEADER_MARKS):
            site = m
            break
    new = build_header(section_for(name))
    if site is None:
        b = _BODY_RE.search(text)
        if not b:
            return text, None
        return text[:b.end()] + "\n" + new + text[b.end():], "insert"
    blk = site.group(0)
    if is_std_header(blk):
        return text, None
    # ヘッダー内にあったテーマ切替ボタンは、標準ページと同じ右上固定のボタンとして残す
    keep = ""
    bm = re.search(r"<button\b[^>]*theme-toggle[^>]*>.*?</button>", blk, re.S)
    if bm:
        btn = re.sub(r'\sstyle="[^"]*"', "", bm.group(0), count=1)
        keep = btn.replace("<button", f'<button style="{THEME_BTN_STYLE}"', 1) + "\n"
    return text[:site.start()] + keep + new + text[site.end():], "replace"


def apply_nav(text, name):
    """③ サイトナビ（class="nav-bar"、または主要ページへのリンクを6つ以上持つ最初の <nav>）を
    11 ボタン標準に。シリーズ内移動（mw-sernav）・パンくず・目次の <nav> は条件に当たらない。"""
    current = SELF_CURRENT.get(name, DEFAULT_CURRENT)
    for m in _NAV_RE.finditer(text):
        blk = m.group(0)
        opening = blk[:blk.find(">") + 1]
        if not re.search(r'class="(?:[^"]*\s)?nav-bar[\s"]', opening) and len(_core_links(blk)) < 6:
            continue
        indent = m.group("indent")
        if blk in (build_nav(indent, current, "nav-bar"), build_nav(indent, current)):
            return text, None
        return text[:m.start()] + build_nav(indent, current) + text[m.end():], "replace"
    return text, "missing"


def process(text, name):
    notes = []
    out = apply_style(text)
    if name.startswith("guide-"):
        out, h = apply_header(out, name)
        if h:
            notes.append(f"header:{h}")
        out, n = apply_nav(out, name)
        if n:
            notes.append(f"nav:{n}")
        # ヘッダーの前にナビが来ていたら（独自ページ）順序を入れ替える
        hi, ni = out.find("<header data-mw-frame>"), out.find('<nav class="nav-bar mwf-nav">')
        if 0 <= ni < hi:
            notes.append("order:nav-before-header")
    return out, notes


def main():
    args = sys.argv[1:]
    apply = "--all" in args or "--files" in args
    if "--files" in args:
        files = args[args.index("--files") + 1:]
    else:
        files = sorted(glob.glob("guide-*.html")) + [p for p in STATIC_PAGES if os.path.exists(p)]
    changed, counts = [], {}
    for path in files:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        out, notes = process(text, path)
        for n in notes:
            counts[n] = counts.get(n, 0) + 1
        if out != text:
            changed.append((path, notes))
            if apply:
                with open(path, "w", encoding="utf-8", newline="") as f:
                    f.write(out)
    mode = "APPLIED" if apply else "DRY-RUN"
    print(f"[{mode}] files={len(files)} changed={len(changed)} " +
          " ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    for p, notes in changed[:15]:
        print("  ~", p, ",".join(notes))
    if len(changed) > 15:
        print(f"  … ほか {len(changed) - 15} 本")


if __name__ == "__main__":
    main()
