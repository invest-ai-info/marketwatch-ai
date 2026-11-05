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

🆕 2026-11-05 段階2＝新しい枠（環境変数 FRAME_V2=1 のときだけ・既定はオフ＝今の枠のまま1バイトも変えない）
  解説記事に、新しいトップ（generate_market_news.build_home_v2）と同じ小さなヘッダー（ロゴとサイト名の1行）と
  横1列のナビ（6項目＋「もっと見る」）をかけ、ナビをヘッダーの直後へ移す。上部の免責は数も文面もそのままで、
  見た目だけ小さく落ち着かせる（FRAME_V2_STYLE_TAG）。オンでもオフでも前の形・新しい形のどちらの
  ヘッダーとナビもサイトの枠として見つけて置き換える＝スイッチを切れば次の実行で前の形に戻る。
  トップのロゴとナビの並びの単一の真実もここ（LOGO_V2_SVG・NAV_V2・NAV_V2_MORE。generate_market_news が import）。

使い方:
  python apply_site_frame.py                 # dry-run（--all と同じ対象）
  python apply_site_frame.py --all           # guide-*.html と STATIC_PAGES に適用
  python apply_site_frame.py --files a.html  # 指定ページに適用（guide 以外は ① だけ）
  FRAME_V2=1 python apply_site_frame.py --all  # 新しい枠で適用（guide-*.html だけ。ほかは今と同じ）
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
# 🆕 2026-10-23 オーナー判断「マーケットウォッチAIの名前は残しつつ、2段目に『AI投資×行動経済学』」。
#   ロゴの行の直下（サイト説明 TAGLINE の上）に置く。言葉や色を変えるときはここだけ直す
#   （生成スクリプトは SUBBRAND_HTML を import。記事と STATIC_PAGES は apply_subbrand が毎回そろえる）
SUBBRAND = "AI投資×行動経済学"
SUBBRAND_HTML = f'<div class="mw-subbrand">{SUBBRAND}</div>'
# 🆕 2026-11-05 オーナー決定＝サイト名を「時短投資ラボ」へ（旧名は他社の登録商標と重なる）。ここが単一の真実。
#    process() が毎回 rename_site をかける＝クラウドの記事レーンが旧名で書いても次の update-market-news で直る。
#    替えるのは旧名の完全一致だけ＝ドメイン・メルマガの目印（固定の検査が見る）・通信の名乗りは触らない。
#    ⚠️ ドメインの移転は別の作業。生成スクリプトの旧名は check_site_consistency が止める
SITE_NAME = "時短投資ラボ"
OLD_SITE_NAME = "MarketWatch AI"
_JP = "぀-ヿ一-鿿"
# 日本語に隣り合う半角スペースは詰める。「旧名 ○○」「旧名「○○」」は案内なので残す
_RENAME_RE = re.compile(rf"(?:(?<=[{_JP}、。）]) )?(?<!旧名 )(?<!旧名「){re.escape(OLD_SITE_NAME)}(?: (?=[{_JP}]))?")
_RENAME_PAIRS = (
    (f"{OLD_SITE_NAME}（マーケットウォッチAI）", f"{SITE_NAME}（じたんとうしラボ）"),
    (f"{OLD_SITE_NAME}. All", f"{SITE_NAME} All"),
    (f"{OLD_SITE_NAME}. 本サイト", f"{SITE_NAME}。本サイト"),
    (f"{OLD_SITE_NAME} シグナル", f"{SITE_NAME}のシグナル"),
    (',MarketWatch">', f',{SITE_NAME}">'),  # 検索用キーワードの末尾
)
# 題名の末尾のサイト名を外す。移行中は新旧どちらも来る
SITE_SUFFIX_RE = re.compile(r"\s*[-|｜]\s*(?:" + re.escape(OLD_SITE_NAME) + "|" + SITE_NAME + r")\s*$")
_BRAND_END = f"</svg> {SITE_NAME}</div>"  # ロゴの行の終わり（ここ以外に現れない）
_SUBBRAND_RE = re.compile(re.escape(_BRAND_END) + r"(?!\s*" + re.escape(SUBBRAND_HTML) + ")")
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
# 2段目（ロゴの点と同じ金色の系統。明るい画面は白地で読める濃さ・暗い画面はロゴの点の色そのもの）
SUBBRAND_CSS = (".mw-subbrand{font-size:1.02rem;font-weight:700;letter-spacing:.05em;line-height:1.4;"
                "margin:1px 0 0 35px;color:#9A6700;-webkit-text-fill-color:currentColor;background:none}"
                "body.dark .mw-subbrand{color:#E8A317}"
                "@media(max-width:700px){.mw-subbrand{font-size:.95rem}}")
# 狭い画面でロゴの文字が右上の固定ボタン（🔍 site-search.js＝右から 62〜108px・🌙）に重ならない大きさに縮める。
# 2026-10-23 実測（幅360px）：文字の右端 263〜275px／🔍の左端 254〜258px。文字の幅≒7.9px×文字の大きさ・
# 左の余白とロゴの絵で 61px → 右端を（画面幅−116px）に収める式。400px より広い画面では重ならないので触らない
BRAND_FIT_CSS = ("@media(max-width:400px){header div:has(+ .mw-subbrand)"
                 "{font-size:max(1.1rem,min(1.6rem,calc((100vw - 180px) / 7.9)))!important}}")

FRAME_CSS = NAV_2ROW_CSS + MWF_NAV_CSS + MWF_HEADER_CSS + AD_GAP_CSS + SUBBRAND_CSS + BRAND_FIT_CSS
FRAME_STYLE_TAG = "<style data-mw-frame>" + FRAME_CSS + "</style>"

# ── 新しい枠（段階2・FRAME_V2=1 のときだけ記事にかける）──────────────
# ロゴ（トップの見出しと同じ絵。色は下の --brand・--bg で決まる）
LOGO_V2_SVG = ('<svg viewBox="0 0 32 32" aria-hidden="true"><rect width="32" height="32" rx="8" fill="var(--brand)"/>'
               '<path d="M6.5 22.5l6-6.5 4.5 3.5 8.5-9.5" fill="none" stroke="var(--bg)" stroke-width="2.6" '
               'stroke-linecap="round" stroke-linejoin="round"/><circle cx="25.5" cy="10" r="2.3" fill="var(--bg)"/></svg>')
# ナビ（上の6つ）と「もっと見る」の小さな一覧。絵文字は付けない。トップ（HOME_V2_NAV／HOME_V2_MORE）も記事もこの並び
NAV_V2 = [
    ("index.html", "ホーム"),
    ("guide-how-we-research.html", "はじめての方へ"),
    ("guides.html", "解説記事"),
    ("track-record.html", "検証の結果"),
    ("market-health.html", "市場データ"),
    ("calendar.html", "経済カレンダー"),
]
NAV_V2_MORE = [
    ("political-feed.html", "政治発言ライブ"),
    ("hot-assets.html", "出来高急増"),
    ("charts.html", "150年チャート"),
    ("holdings.html", "大量保有報告"),
    ("guide-investment-books.html", "投資本"),
    ("youtube-summary.html", "YouTube要約"),
    ("research-list.html", "検証中リスト"),
    # 計算ツール6本の並びは記事一覧の「計算ツール」欄が単一の真実（check_tools_strip が見張る）＝そこへ案内する
    ("guides.html#cat-tools", "計算ツール"),
]
# 色はトップの HOME_V2_CSS（:root と body.dark）と同じ値。記事の CSS と混ざらないよう枠の要素の中だけで定義する
# （tests/test_site_frame_v2.py がトップの値と突き合わせる）
V2_LIGHT = (("bg", "#ffffff"), ("surface", "#f5f8fc"), ("line", "#dbe3ee"), ("ink", "#1b2433"),
            ("muted", "#526075"), ("brand", "#1766d6"), ("chip", "#edf2f9"), ("t-blue", "#eaf3ff"))
V2_DARK = (("bg", "#0e141c"), ("surface", "#151d28"), ("line", "#283444"), ("ink", "#e7edf5"),
           ("muted", "#a1adbd"), ("brand", "#5b9dff"), ("chip", "#1b2533"), ("t-blue", "#13233a"))


def _vars(pairs):
    return ";".join(f"--{k}:{v}" for k, v in pairs)


def _imp(decls):
    """宣言を全部 !important にする。記事ごとに CSS が違う（AI が書いた header{…}・nav a{…}・li{…}・
    details{…}・dark 用の !important 入りの予備など）ので、新しい枠の見た目は記事側に負けないようにする。"""
    return ";".join(d + "!important" for d in decls.split(";") if d)


_HV = "header[data-mw-frame][data-v2]"
_NV = "nav.nav-bar.mwf-nav.mwf-v2"
_AV = _NV + " a.nav-btn"
_SV = _NV + " .mwf-more>summary"
_LIV = _NV + " .mwf-more li"
_FONT_V2 = "'Noto Sans JP','Hiragino Sans','Yu Gothic',system-ui,sans-serif"
FRAME_V2_CSS = (
    f"{_HV},{_NV}{{{_vars(V2_LIGHT)}}}"
    f"body.dark {_HV},body.dark {_NV}{{{_vars(V2_DARK)}}}"
    # ヘッダー＝ロゴとサイト名の1行。右上に固定で浮く 🔍（右から 62〜108px）と 🌙 の分だけ右を空け、
    # 行の高さの真ん中をボタンの真ん中（上から 37px・スマホ 34px）に合わせる
    + _HV + "{" + _imp("box-sizing:border-box;display:block;position:static;margin:0;padding:8px 16px 0;"
                       "background:var(--bg);border:0;box-shadow:none;color:var(--ink);text-align:left;"
                       f"font:400 16px/1.5 {_FONT_V2}") + "}"
    + _HV + " .mwf-hd-in{" + _imp("display:flex;align-items:center;max-width:1080px;min-height:58px;"
                                  "margin:0 auto;padding:0 112px 0 0") + "}"
    + _HV + " a.mwf-logo{" + _imp("display:inline-flex;align-items:center;gap:10px;color:var(--ink);"
                                  "-webkit-text-fill-color:currentColor;background:none;font-size:19px;font-weight:700;"
                                  "letter-spacing:.02em;line-height:1.3;text-decoration:none") + "}"
    + _HV + " a.mwf-logo svg{" + _imp("display:block;flex:none;width:30px;height:30px;max-width:none;margin:0") + "}"
    # ナビ＝横1列（入りきらない幅では横にスクロール）＋右端に「もっと見る」
    + _NV + "{" + _imp("box-sizing:border-box;display:block;position:relative;z-index:50;width:auto;max-width:none;"
                       "margin:0;padding:0 16px 8px;background:var(--bg);border:0;border-bottom:1px solid var(--line);"
                       f"border-radius:0;box-shadow:none;font:400 16px/1.5 {_FONT_V2}") + "}"
    + _NV + " .mwf-in{" + _imp("display:flex;align-items:flex-start;gap:4px;max-width:1080px;margin:0 auto;padding:0") + "}"
    + _NV + " .mwf-row{" + _imp("display:flex;flex-wrap:nowrap;gap:4px;flex:1 1 auto;min-width:0;margin:0 0 0 -4px;"
                                "padding:0;overflow-x:auto;scrollbar-width:none") + "}"
    + _NV + " .mwf-row::-webkit-scrollbar{display:none}"
    + _AV + "," + _SV + "{" + _imp("box-sizing:border-box;display:block;flex:none;width:auto;min-width:0;height:auto;"
                                   "margin:0;padding:6px 12px;border:0;border-radius:8px;background:none;box-shadow:none;"
                                   "transform:none;transition:none;color:var(--ink);font-size:14.5px;font-weight:500;"
                                   "line-height:1.75;white-space:nowrap;text-align:left;text-decoration:none") + "}"
    + _AV + ":hover," + _SV + ":hover{" + _imp("background:var(--surface);color:var(--ink);text-decoration:none") + "}"
    + _AV + ".current{" + _imp("background:var(--t-blue);color:var(--brand);font-weight:700") + "}"
    + _NV + " .mwf-more{" + _imp("position:relative;flex:none;margin:0;padding:0;border:0;background:none") + "}"
    + _SV + "{" + _imp("list-style:none;cursor:pointer;color:var(--muted)") + "}"
    + _SV + "::-webkit-details-marker{display:none}"
    + _SV + "::before," + _SV + "::after{" + _imp("content:none;display:none") + "}"
    + _NV + " .mwf-more[open]>summary{" + _imp("background:var(--chip);color:var(--ink)") + "}"
    + _NV + " .mwf-more ul{" + _imp("position:absolute;right:0;top:calc(100% + 6px);z-index:60;min-width:200px;"
                                    "margin:0;padding:6px;list-style:none;background:var(--bg);border:1px solid var(--line);"
                                    "border-radius:12px;box-shadow:0 8px 24px rgba(15,30,60,.16)") + "}"
    + _LIV + "{" + _imp("display:block;margin:0;padding:0;border:0;background:none;list-style:none;font-size:inherit") + "}"
    + _LIV + "::before," + _LIV + "::after{" + _imp("content:none;display:none") + "}"
    + _LIV + " a.nav-btn{" + _imp("padding:8px 12px") + "}"
    + "@media(max-width:640px){" + _AV + "," + _SV + "{" + _imp("padding:9px 12px") + "}}"
    + "@media(max-width:600px){" + _HV + "{" + _imp("padding-top:5px") + "}}"
)
# 「もっと見る」の中に今のページがあるとき（投資本のページ）は、閉じていても札の色でわかるようにする。
# :has() を知らないブラウザでは規則ごと読み飛ばされるので、上とは別の規則にしてある
FRAME_V2_CSS += _NV + " .mwf-more:has(a.current)>summary{" + _imp("color:var(--brand);font-weight:700") + "}"
# 上部の免責（位置で見て最初の h1 より前にあるもの）を小さく落ち着いた見た目に。数と文面は変えない・隠さない。
# 2026-11-05 実測（記事667本）: h1 より前の免責は全部「h1 の兄弟」か「h1 を含む要素の兄弟」で、
# h1 より後ろ（本文末・フッター）の免責にはこの条件に当たるものが無い＝下の :has(~ h1,~ * h1) で過不足なく選べる。
# ⚠️ 選び方に「kinsho-v1」の文字を書かない（免責の有無・数を文字で数える検査が CSS の分まで数えてしまう）
_DTV = ":is([data-disclaimer],.disclaimer-banner):has(~ h1,~ * h1)"
_L2, _D2 = dict(V2_LIGHT), dict(V2_DARK)
FRAME_V2_DISCLAIMER_CSS = (
    _DTV + "{" + _imp(f"box-sizing:border-box;margin:0 0 16px;padding:8px 12px;border:1px solid {_L2['line']};"
                      f"border-radius:8px;background:{_L2['surface']};box-shadow:none;color:{_L2['muted']};"
                      "font-size:.85rem;font-weight:400;line-height:1.65;text-align:left") + "}"  # 2026-11-05 コンプラ点検＝公開日の行と同じ大きさ（ページで一番小さい字にしない）
    + _DTV + " :is(p,span,strong,b,em,small){" + _imp("font-size:inherit;color:inherit") + "}"
    + _DTV + " p{" + _imp("margin:0") + "}" + _DTV + " p+p{" + _imp("margin-top:.35em") + "}"
    + _DTV + " :is(strong,b){" + _imp("font-weight:700") + "}"  # 「投資の判断はご自身の責任で」の太字を残す
    + "body.dark " + _DTV + "{" + _imp(f"background:{_D2['surface']};border-color:{_D2['line']};color:{_D2['muted']}") + "}"
)
FRAME_V2_STYLE_TAG = "<style data-mw-frame-v2>" + FRAME_V2_CSS + FRAME_V2_DISCLAIMER_CSS + "</style>"
# ナビの中に置く小さな動き（ナビと一緒に消える）:
#  ・スマホの幅で今のページの項目（記事なら3つ目の「解説記事」）が右に切れるときは、見える所まで横に送る
#  ・「もっと見る」を外側のクリックと Esc で閉じる（トップの HOME_V2_JS と同じ動き）
NAV_V2_JS = ("<script>(function(){var n=document.currentScript&&document.currentScript.parentNode;if(!n)return;"
             "var d=n.querySelector('.mwf-more'),r=n.querySelector('.mwf-row'),c=r&&r.querySelector('a.current');"
             "function f(){if(!c)return;var a=r.getBoundingClientRect(),b=c.getBoundingClientRect();"
             "if(b.right>a.right)r.scrollLeft+=b.right-a.right+8}f();window.addEventListener('load',f);if(!d)return;"
             "document.addEventListener('click',function(e){if(d.open&&!d.contains(e.target))d.open=false});"
             "document.addEventListener('keydown',function(e){if(e.key==='Escape'&&d.open)d.open=false})})();</script>")

_STYLE_RE = re.compile(r"<style data-mw-frame>.*?</style>", re.S)
_STYLE_V2_RE = re.compile(r"<style data-mw-frame-v2>.*?</style>", re.S)
_HEADER_RE = re.compile(r"<header(?=[\s>])[^>]*>.*?</header>", re.S)
_NAV_RE = re.compile(r"(?P<indent>[ \t]*)<nav(?=[\s>])[^>]*>.*?</nav>", re.S)
_BODY_RE = re.compile(r"<body[^>]*>")
_SITE_HEADER_MARKS = (SITE_NAME, "MarketWatch", 'rx="21" fill="#1E3A6E"', "header-title", "header-meta")
_BUTTON_RE = re.compile(r"<button\b[^>]*theme-toggle[^>]*>.*?</button>|<button\b[^>]*>.*?</button>", re.S)


def section_for(name):
    for prefix, label in SECTION_BY_PREFIX:
        if name.startswith(prefix):
            return label
    return SECTION_DEFAULT


def build_header(section):
    return ("<header data-mw-frame>\n"
            '  <div class="header-inner">\n'
            f'    <div class="header-title">{LOGO_SVG} {SITE_NAME}</div>{SUBBRAND_HTML}\n'
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


def frame_v2_enabled():
    """新しい枠のスイッチ。環境変数 FRAME_V2=1 のときだけ（トップの HOME_V2 と同じ決め方）。"""
    return os.environ.get("FRAME_V2", "").strip() == "1"


def build_header_v2():
    return ("<header data-mw-frame data-v2>\n"
            '  <div class="mwf-hd-in">\n'
            f'    <a class="mwf-logo" href="index.html">{LOGO_V2_SVG}{SITE_NAME}</a>\n'
            "  </div>\n"
            "</header>")


def build_nav_v2(current=DEFAULT_CURRENT):
    """横1列のナビ（6項目）と「もっと見る」。リンクの class は nav-btn のまま
    （check_site_consistency の NAV_LINKS の検査と、ほかの道具の見つけ方がそのまま使える）。"""
    def link(href, label):
        if href == current:
            return f'<a class="nav-btn current" href="{href}" aria-current="page">{label}</a>'
        return f'<a class="nav-btn" href="{href}">{label}</a>'
    row = "\n".join(f"      {link(h, t)}" for h, t in NAV_V2)
    more = "\n".join(f"        <li>{link(h, t)}</li>" for h, t in NAV_V2_MORE)
    return ('<nav class="nav-bar mwf-nav mwf-v2" aria-label="メイン">\n'
            '  <div class="mwf-in">\n'
            '    <div class="mwf-row">\n'
            f"{row}\n"
            "    </div>\n"
            '    <details class="mwf-more"><summary>もっと見る ▾</summary>\n'
            "      <ul>\n"
            f"{more}\n"
            "      </ul>\n"
            "    </details>\n"
            "  </div>\n"
            f"  {NAV_V2_JS}\n"
            "</nav>")


def is_std_header(block):
    return (LOGO_SVG in block and TAGLINE in block and SEC_OPEN in block and SUBBRAND_HTML in block
            and 'class="header-title"' in block and "<button" not in block and "<nav" not in block)


def rename_site(text):
    """旧サイト名を新しい名前へ。冪等。ドメインやメルマガの目印などは変えない（SITE_NAME の注記）。"""
    for old, new in _RENAME_PAIRS:
        text = text.replace(old, new)
    return _RENAME_RE.sub(SITE_NAME, text)


def apply_subbrand(text):
    """ロゴの行の直後に2段目（SUBBRAND_HTML）を1つだけ置く。冪等。手書きヘッダーの静的ページ用。"""
    return _SUBBRAND_RE.sub(lambda m: m.group(0) + SUBBRAND_HTML, text)


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


def apply_style_v2(text, v2):
    """新しい枠の <style> を、オンなら ① の <style> の直後に1つだけ置き、オフなら取り除く。
    オフで新しい枠の <style> が無いページ（今の全ページ）は何も変わらない。"""
    want = FRAME_V2_STYLE_TAG if v2 else ""
    m = _STYLE_RE.search(text)
    if v2 and m and text[m.end():m.end() + len(want)] == want and len(_STYLE_V2_RE.findall(text)) == 1:
        return text
    out = _STYLE_V2_RE.sub("", text)
    if v2:
        m = _STYLE_RE.search(out)
        if m:
            out = out[:m.end()] + want + out[m.end():]
    return out


def _find_site_header(text):
    for m in _HEADER_RE.finditer(text):
        blk = m.group(0)
        # ロゴの図形だけで社名の文字が無いヘッダーもある（signal-lab の独自版）ので目印を複数見る
        if "<h1" not in blk and any(k in blk for k in _SITE_HEADER_MARKS):
            return m
    return None


def apply_header(text, name, v2=False):
    """② サイトヘッダーを標準形（v2 なら新しい形）に。記事の表紙（<h1> 入り）の <header> は対象外。
    前の形・新しい形のどちらのサイトヘッダーも見つける（新しい形はサイト名を持つ）。"""
    site = _find_site_header(text)
    new = build_header_v2() if v2 else build_header(section_for(name))
    if site is None:
        b = _BODY_RE.search(text)
        if not b:
            return text, None
        return text[:b.end()] + "\n" + new + text[b.end():], "insert"
    blk = site.group(0)
    if (blk == new) if v2 else is_std_header(blk):
        return text, None
    # ヘッダー内にあったテーマ切替ボタンは、標準ページと同じ右上固定のボタンとして残す
    keep = ""
    bm = re.search(r"<button\b[^>]*theme-toggle[^>]*>.*?</button>", blk, re.S)
    if bm:
        btn = re.sub(r'\sstyle="[^"]*"', "", bm.group(0), count=1)
        keep = btn.replace("<button", f'<button style="{THEME_BTN_STYLE}"', 1) + "\n"
    return text[:site.start()] + keep + new + text[site.end():], "replace"


def _find_site_nav(text):
    for m in _NAV_RE.finditer(text):
        blk = m.group(0)
        opening = blk[:blk.find(">") + 1]
        if re.search(r'class="(?:[^"]*\s)?nav-bar[\s"]', opening) or len(_core_links(blk)) >= 6:
            return m
    return None


def apply_nav(text, name):
    """③ サイトナビ（class="nav-bar"、または主要ページへのリンクを6つ以上持つ最初の <nav>）を
    11 ボタン標準に。シリーズ内移動（mw-sernav）・パンくず・目次の <nav> は条件に当たらない。
    新しい形のナビ（class に nav-bar）も同じ条件で見つかる＝その場で前の形に戻る。"""
    current = SELF_CURRENT.get(name, DEFAULT_CURRENT)
    m = _find_site_nav(text)
    if m is None:
        return text, "missing"
    blk = m.group(0)
    indent = m.group("indent")
    if blk in (build_nav(indent, current, "nav-bar"), build_nav(indent, current)):
        return text, None
    return text[:m.start()] + build_nav(indent, current) + text[m.end():], "replace"


def apply_nav_v2(text, name):
    """③ の新しい形。サイトナビ（前の形・新しい形のどちらでも）を取り除き、新しい形をサイトヘッダー
    （build_header_v2）の直後に置く。ナビが無いページには足す。ヘッダーが無ければ（<body> の無い記事）その場で置き換える。"""
    current = SELF_CURRENT.get(name, DEFAULT_CURRENT)
    new = build_nav_v2(current)
    head = build_header_v2()
    hi = text.find(head)
    m = _find_site_nav(text)
    if hi < 0:
        if m is None:
            return text, "missing"
        if m.group(0) == new:
            return text, None
        return text[:m.start()] + new + text[m.end():], "replace"
    anchor = hi + len(head)
    if m is not None and m.start() == anchor + 1 and text[anchor] == "\n" and m.group(0) == new:
        return text, None
    note = "insert"
    if m is not None:
        note = "replace" if m.start() == anchor + 1 else "move"
        s, e = m.start(), m.end()
        if s > 0 and text[s - 1] == "\n":   # ナビだけの行は行ごと消す（空行を増やさない）
            s -= 1
        text = text[:s] + text[e:]
        if s < anchor:
            anchor -= e - s
    return text[:anchor] + "\n" + new + text[anchor:], note


def process(text, name, v2=None):
    """v2=None なら環境変数 FRAME_V2 で決める（frame_v2_enabled）。新しい形は guide-*.html だけ。"""
    if v2 is None:
        v2 = frame_v2_enabled()
    guide = name.startswith("guide-")
    notes = []
    out = rename_site(text)  # 先に替える＝2段目の位置決めとヘッダーの判定は新しい名前で見る
    if out != text:
        notes.append("rename")
    out = apply_style(out)
    st = apply_style_v2(out, v2 and guide)
    if st != out:
        notes.append("style:v2" if v2 and guide else "style:v2-removed")
        out = st
    sub = apply_subbrand(out)
    if sub != out:
        notes.append("subbrand")
        out = sub
    if guide:
        out, h = apply_header(out, name, v2)
        if h:
            notes.append(f"header:{h}")
        out, n = (apply_nav_v2 if v2 else apply_nav)(out, name)
        if n:
            notes.append(f"nav:{n}")
        # ヘッダーの前にナビが来ていたら（独自ページ）順序を入れ替える
        hi, ni = out.find("<header data-mw-frame>"), out.find('<nav class="nav-bar mwf-nav">')
        if not v2 and 0 <= ni < hi:
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
    v2 = frame_v2_enabled()
    for path in files:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        out, notes = process(text, path, v2)
        for n in notes:
            counts[n] = counts.get(n, 0) + 1
        if out != text:
            changed.append((path, notes))
            if apply:
                with open(path, "w", encoding="utf-8", newline="") as f:
                    f.write(out)
    mode = "APPLIED" if apply else "DRY-RUN"
    print(f"[{mode}]{' frame=v2' if v2 else ''} files={len(files)} changed={len(changed)} " +
          " ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    for p, notes in changed[:15]:
        print("  ~", p, ",".join(notes))
    if len(changed) > 15:
        print(f"  … ほか {len(changed) - 15} 本")


if __name__ == "__main__":
    main()
