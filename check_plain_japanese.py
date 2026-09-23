# -*- coding: utf-8 -*-
"""記事の文章が「やさしい日本語」になっているかを検査する（2026-09-23 オーナー指示）。

オーナーの言葉:「初心者でもわかるように噛み砕いて、記号をなるべくなくし、漢字・ひらがな・
カタカナで。RSI などはしょうがないが、カッコで日本語の説明を付ける」。
書き方の決まり（人が読む版）は QUALITY_RUBRIC.md の「やさしい日本語」節。**機械で見られる
ものはここ（RULES）が単一の真実**＝文書に書くだけでは守られないので、公開前に止める。

見るもの: <main>（無ければ <body>）の本文と見出し・表・図（SVG）の文字、そして <title>。
見ないもの: ナビ・ヘッダー・フッター・パンくず・記事メタ行・リンクの文字（関連記事カードに
古い題名が載るため）・広告・メルマガ枠・成績記録の表（signal_lab_tracker.py が出力する機械の表）。

⚠️ 数値はそのまま。signal_lab_verify.py が「50.4%」「205/407」の形で数字を突き合わせるので、
   直すのは言葉だけ（「N=407件」→「407回」、「+0.263R」→「損切り幅の0.26倍」など）。
⚠️ 表の見出しの IS / FWD / OOS は、日本語と一緒なら残してよい（例「検証に使った期間（IS）」）。
   signal_lab_verify.py の期間取り違え検査が見出しのこの文字を目印にしているため。

使い方:
  python check_plain_japanese.py 記事.html            # 指摘を表示。1件でもあれば EXIT=1
  python check_plain_japanese.py --stats a.html b.html # 規則ごとの件数だけ（既存記事の棚卸し用）
"""
import re
import sys
from html.parser import HTMLParser

# ── 規則（名前・パターン・直し方）─────────────────────────────
RULES = [
    ("不等号・比べる記号", re.compile(r"[≤≥≦≧＜＞<>]"), "「以下」「以上」「より上」など言葉で書く"),
    ("かけ算・矢印などの記号", re.compile(r"[×✕→⇒➡±≒≈∧∨]"), "「と」「なので」「その結果」など言葉で書く"),
    ("N=の表記", re.compile(r"(?<![A-Za-z])[NnＮ]\s*[=＝]"), "「407回」のように回数で書く"),
    ("R（損切り幅の単位）", re.compile(r"(?<![A-Za-z])R(?![A-Za-z])"),
     "「損切り幅の0.26倍のもうけ」のように書く"),
    ("プログラム用の名前", re.compile(r"[A-Za-z]+_[A-Za-z0-9_]+|[A-Za-z_]+\s*=\s*[A-Za-z_][A-Za-z0-9_]*|\bTrue\b|\bFalse\b"),
     "書かない（日本語の条件名にする）"),
    ("時間足の略号", re.compile(r"(?<![A-Za-z0-9])\d+\s*[HhDdWw](?![A-Za-z])"), "「4時間足」「日足」と書く"),
    ("分数の表記", None, "「407回中205回」と書く（割合は%のまま残す）"),
    ("専門用語", re.compile(r"反実仮想|交絡|ウィルソン|有意|通過[A-ZＡ-Ｚ]|ロング|ショート|エッジ|サンプル|ホールドアウト"),
     "言い換える（例: 反実仮想検証→シグナルどおりに売買していたらどうなったかの計算／有意→偶然とは言いにくい／"
     "ロング→買い／エッジ→有利さ／サンプル→回数）"),
    ("英字の略語", None, "日本語にする（例: JPY→円、BTC→ビットコイン、SL→損切り、CI→偶然のぶれの幅）"),
    ("用語の説明が無い", None, "初めて出たところに「RSI（相対力指数：…）」のようにカッコで説明を付ける"),
]
_RULE = {name: (pat, fix) for name, pat, fix in RULES}

# そのままでよい英字（言い換えると却って通じない名前）。ここに無い英字は「英字の略語」で指摘する
ALLOWED_ASCII = {
    "RSI", "MACD", "ATR", "VIX", "AI", "FX", "CFD", "ETF", "NISA", "iDeCo", "FOMC", "CPI", "GDP", "PCE",
    "PMI", "ECB", "FRB", "TOPIX", "NY", "MarketWatch", "YouTube", "SNS", "IPO", "PER", "PBR", "ROE", "EPS",
    "REIT", "TOB", "OPEC",
}
# 表の見出しでだけ、日本語と一緒なら残してよい英字（signal_lab_verify の期間取り違え検査の目印）
TH_OK_ASCII = {"IS", "FWD", "OOS"}
# 初めて出たところにカッコの説明が要る用語
NEEDS_PAREN = ["RSI", "MACD", "ATR", "VIX", "ストキャスティクス", "ボリンジャーバンド", "一目均衡表", "ダイバージェンス"]

_ASCII_WORD = re.compile(r"[A-Za-z]{2,}")  # 「RSI30」は RSI として見る
_FRACTION = re.compile(r"(?<![\d.])(\d+)\s*/\s*(\d+)(?![\d.])")
_JA = re.compile(r"[぀-ヿ一-鿿]")

SKIP_TAGS = {"nav", "header", "footer", "script", "style", "noscript", "form", "a", "head", "button"}
SKIP_CLASSES = {"breadcrumb", "meta-line", "mw-ad", "mw-sernav", "s-kinsho-top"}
VOID = {"br", "img", "meta", "link", "input", "hr", "wbr", "source", "col", "area", "base", "embed", "path",
        "rect", "line", "circle", "polyline", "polygon", "ellipse", "stop", "use"}


def _strip_machine_parts(html):
    """機械が出力する部分・定型部分を先に落とす。"""
    # signal_lab_tracker.py table --html の出力（見出しの文字で特定＝routine は編集できない表）
    html = re.sub(r"<table>(?:(?!</table>).)*?前向き現在値\(平均R\).*?</table>", "", html, flags=re.S)
    for marker in ("<!-- ===== MarketWatch 無料メルマガ登録", "<footer"):
        i = html.find(marker)
        if i >= 0:
            html = html[:i]
    return html


class _Extract(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []          # (tag, skip, flags)
        self.segments = []       # (text, flags)

    def _flags(self):
        f = set()
        for tag, _skip, _ in self.stack:
            if tag == "th":
                f.add("th")
            elif tag == "h1":
                f.add("h1")
            elif tag == "svg":
                f.add("svg")
        return f

    def _skipping(self):
        return any(s for _t, s, _ in self.stack)

    def handle_starttag(self, tag, attrs):
        if tag in VOID:
            return
        cls = set((dict(attrs).get("class") or "").split())
        self.stack.append((tag, tag in SKIP_TAGS or bool(cls & SKIP_CLASSES), None))

    def handle_startendtag(self, tag, attrs):
        return

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        if data.strip() and not self._skipping():
            self.segments.append((data, self._flags()))


def extract(html):
    """(title, segments) を返す。segments = [(文字, {"th","h1","svg"} の部分集合)]。"""
    m = re.search(r"<title>(.*?)</title>", html, re.S)
    title = re.sub(r"\s+", " ", m.group(1)).strip() if m else ""
    body = html
    mm = re.search(r"<main[^>]*>(.*)</main>", html, re.S)
    if mm:
        body = mm.group(1)
    else:
        mb = re.search(r"<body[^>]*>(.*)", html, re.S)
        if mb:
            body = mb.group(1)
    p = _Extract()
    p.feed(_strip_machine_parts(body))
    return title, p.segments


def _snip(text, start, end):
    s = re.sub(r"\s+", " ", text[max(0, start - 14):end + 14]).strip()
    return s


def check_text(text, flags, where):
    """1つの文字の塊を検査して [(規則名, 抜粋, 場所)] を返す。"""
    out = []
    for name in ("不等号・比べる記号", "かけ算・矢印などの記号", "N=の表記", "R（損切り幅の単位）",
                 "プログラム用の名前", "時間足の略号", "専門用語"):
        pat = _RULE[name][0]
        for m in pat.finditer(text):
            out.append((name, _snip(text, m.start(), m.end()), where))
    for m in _FRACTION.finditer(text):
        a, b = int(m.group(1)), int(m.group(2))
        if a <= 12 and b <= 31:          # 9/23 のような日付は対象外
            continue
        out.append(("分数の表記", _snip(text, m.start(), m.end()), where))
    code_spans = [m.span() for m in _RULE["プログラム用の名前"][0].finditer(text)]
    for m in _ASCII_WORD.finditer(text):
        w = m.group(0)
        if w in ALLOWED_ASCII or w in ("True", "False"):
            continue
        if any(s <= m.start() < e for s, e in code_spans):   # プログラム名で指摘済み
            continue
        if "th" in flags and w in TH_OK_ASCII and _JA.search(text):
            continue
        out.append(("英字の略語", _snip(text, m.start(), m.end()), where))
    return out


def check_html(html):
    """記事 HTML を検査して [(規則名, 抜粋, 場所)] を返す。"""
    title, segments = extract(html)
    found = []
    if title:
        t = re.sub(r"\s*[-|｜]\s*MarketWatch AI\s*$", "", title)
        found += check_text(t, set(), "題名(title)")
    for text, flags in segments:
        where = "表の見出し" if "th" in flags else "図" if "svg" in flags else "見出し(h1)" if "h1" in flags else "本文"
        found += check_text(text, flags, where)
    # 用語の説明: h1 より後の本文で、その用語が初めて出たところの直後にカッコがあるか
    body = "".join(t for t, f in segments if "h1" not in f and "svg" not in f)
    for term in NEEDS_PAREN:
        i = body.find(term)
        if i < 0:
            continue
        after = body[i + len(term):i + len(term) + 2].lstrip()
        if not after.startswith(("（", "(")):
            found.append(("用語の説明が無い", _snip(body, i, i + len(term)), f"本文（{term} の初出）"))
    return found


def main():
    args = sys.argv[1:]
    stats = "--stats" in args
    files = [a for a in args if not a.startswith("--")]
    if not files:
        print(__doc__)
        return 2
    total = 0
    for path in files:
        with open(path, encoding="utf-8") as f:
            found = check_html(f.read())
        total += len(found)
        if stats:
            counts = {}
            for name, _s, _w in found:
                counts[name] = counts.get(name, 0) + 1
            print(f"{path}\t{len(found)}\t" + " ".join(f"{k}={v}" for k, v in sorted(counts.items(), key=lambda x: -x[1])))
            continue
        print(f"=== やさしい日本語の検査: {path} — 指摘 {len(found)} 件 ===")
        for name, snip, where in found[:80]:
            print(f"  ❌ [{name}] {where}: …{snip}…")
        if len(found) > 80:
            print(f"  … ほか {len(found) - 80} 件")
        seen = []
        for name, _s, _w in found:
            if name not in seen:
                seen.append(name)
        for name in seen:
            print(f"  → {name}: {_RULE[name][1]}")
    if not stats:
        print("EXIT=1（言い換えてから再実行。数値・%・k/n は変えない）" if total else "✅ 指摘なし")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
