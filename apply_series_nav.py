#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""apply_series_nav.py — 連続シリーズ記事の末尾に「前の記事／次の記事」ボタンを冪等に敷く。

読者要望（2026-09-05・メール）＝「シリーズを遡るたび一覧ページに戻るのが不便。
記事下部に前後へ移動するボタンが欲しい」。

設計（unify_navbar.py / apply_logo.py と同じ「決定論ツールで一括更新」型）:
  - 並び順は記事HTMLの JSON-LD `datePublished`（同日はファイル名）。人が順番を管理しない。
  - 差し込み位置は `</main>` の直前（無い記事は `<footer` の直前）。
  - `<!-- series-nav:begin -->` 〜 `<!-- series-nav:end -->` で挟み、再実行時は丸ごと置換＝冪等。
  - 既定は dry-run。書き込みは `--apply`。

⚠️ 手で記事に前後リンクを書かないこと。毎日の自動公開でシリーズ末尾が伸びるため、
   「前の記事」だけでなく **1つ前の記事の「次の記事」も貼り替える**必要がある＝人手では必ず腐る。
   update-market-news.yml が毎回 `--apply` して commit するので、公開から数時間で自動的に整う。
"""
import argparse
import glob
import html
import os
import re
import sys

# ── シリーズ定義（key, ファイル glob, 表示名, 一覧ページ, 連番から除くファイル）
SERIES = [
    {
        "key": "signal-lab",
        "glob": "guide-signal-lab-*.html",
        "label": "AIシグナル研究日誌",
        # guides.html 内の該当カテゴリまで飛ばす（この見出しだけ専用セクションがある）
        "index": "guides.html#cat-lab",
        "exclude": set(),
    },
    {
        "key": "proverb",
        "glob": "guide-proverb-*.html",
        "label": "投資格言から学ぼう",
        # 総集編（全48回の総目次）がそのままシリーズの一覧ページになる
        "index": "guide-proverb-series-index.html",
        "exclude": {"guide-proverb-series-index.html"},
    },
    {
        "key": "scam",
        "glob": "guide-scam-*.html",
        "label": "投資詐欺から身を守る",
        "index": "guides.html",
        "exclude": set(),
    },
    {
        "key": "tse",
        "glob": "guide-tse-*.html",
        "label": "東証のしくみ",
        "index": "guides.html",
        "exclude": set(),
    },
    {
        "key": "news",
        "glob": "guide-news-*.html",
        "label": "今日のニュース",
        "index": "guides.html",
        "exclude": set(),
    },
]

# 記事の途中（関連記事の直前）に置かれている「📚 解説記事一覧に戻る →」ボタン。
# 2026-09-05 オーナー指摘＝シリーズ内の移動を先に見せ、サイト全体の一覧へ戻るのは最後にしたい。
# 対象232本のうち64本が持っており、全64本が下の1形だけ（実測）。ブロックの末尾へ移設する。
BACK_BTN_MARK = "📚 解説記事一覧に戻る →"
BACK_BTN_RE = re.compile(
    r'\n*[ \t]*<div[^>]*>\s*<a [^>]*>' + re.escape(BACK_BTN_MARK) + r'</a>\s*</div>\n?', re.S)
BACK_BTN_HTML = (
    '      <div style="text-align:center;margin:18px 0 0">\n'
    '        <a href="guides.html" style="display:inline-block;padding:12px 28px;background:#ffffff;'
    'border:1px solid #0969da;border-radius:8px;color:#1f6feb;text-decoration:none;font-weight:600;'
    'font-size:.95rem">' + BACK_BTN_MARK + '</a>\n'
    '      </div>')

BEGIN = "<!-- series-nav:begin -->"
END = "<!-- series-nav:end -->"
BLOCK_RE = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END) + r"\n?", re.S)

TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S | re.I)
DATE_RE = re.compile(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})')
SITE_SUFFIX = re.compile(r"\s*[-|｜]\s*MarketWatch AI\s*$")

STYLE = """<style>
.mw-sernav{max-width:900px;margin:28px auto 0;padding:0 16px}
.mw-sernav-h{font-size:14px;font-weight:700;color:#2C4F8F;margin-bottom:10px}
.mw-sernav-row{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.mw-sernav-btn{display:flex;flex-direction:column;gap:4px;padding:12px 14px;border:1px solid #dfe3e8;border-radius:10px;background:#fff;text-decoration:none;color:#1a1a1a}
.mw-sernav-btn:hover{border-color:#2C4F8F;box-shadow:0 2px 8px rgba(44,79,143,.12)}
.mw-sernav-btn.next{text-align:right}
.mw-sernav-dir{font-size:12px;color:#6b7280;font-weight:600}
.mw-sernav-t{font-size:13.5px;line-height:1.5;font-weight:600;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.mw-sernav-btn.is-off{opacity:.45;background:#f6f7f9;pointer-events:none}
.mw-sernav-idx{margin-top:10px;text-align:center;font-size:12.5px;color:#6b7280}
.mw-sernav-idx a{color:#2C4F8F;font-weight:600}
@media(max-width:520px){.mw-sernav-row{grid-template-columns:1fr}.mw-sernav-btn.next{text-align:left}}
body.dark .mw-sernav-h{color:#58a6ff}
body.dark .mw-sernav-btn{background:#161b22;border-color:#30363d;color:#e6edf3}
body.dark .mw-sernav-btn.is-off{background:#0d1117}
body.dark .mw-sernav-dir,body.dark .mw-sernav-idx{color:#8b949e}
body.dark .mw-sernav-idx a{color:#58a6ff}
</style>"""


def doc_title(text):
    """<head> の <title>（＝文書内で最初の title。SVG の <title> より必ず前にある）を返す。"""
    m = TITLE_RE.search(text)
    if not m:
        return ""
    t = html.unescape(m.group(1)).strip()
    t = re.sub(r"\s+", " ", t)
    return SITE_SUFFIX.sub("", t).strip()


def doc_date(text):
    m = DATE_RE.search(text)
    return m.group(1) if m else ""


def collect(series, root):
    """シリーズの記事を (日付, ファイル名) 昇順で返す。日付が取れない記事は除外。"""
    items = []
    for path in sorted(glob.glob(os.path.join(root, series["glob"]))):
        name = os.path.basename(path)
        if name in series["exclude"]:
            continue
        text = read(path)
        date = doc_date(text)
        if not date:
            continue
        items.append({"file": name, "path": path, "date": date, "title": doc_title(text) or name})
    items.sort(key=lambda a: (a["date"], a["file"]))
    return items


def button(kind, item):
    """kind='prev'|'next'。item が None なら押せないダミー（左右の型崩れ防止）。"""
    label = "← 前の記事" if kind == "prev" else "次の記事 →"
    if item is None:
        tail = "これが最初の記事です" if kind == "prev" else "これが最新の記事です"
        return (f'      <span class="mw-sernav-btn {kind} is-off" aria-hidden="true">\n'
                f'        <span class="mw-sernav-dir">{label}</span>\n'
                f'        <span class="mw-sernav-t">{tail}</span>\n'
                f'      </span>')
    return (f'      <a class="mw-sernav-btn {kind}" href="{item["file"]}" rel="{kind}">\n'
            f'        <span class="mw-sernav-dir">{label}</span>\n'
            f'        <span class="mw-sernav-t">{html.escape(item["title"])}</span>\n'
            f'      </a>')


def build_block(series, prev_item, next_item, has_back_btn):
    """has_back_btn＝その記事が「解説記事一覧に戻る」ボタンを持っていたか（末尾へ移設する）。"""
    parts = [
        BEGIN,
        STYLE,
        f'    <nav class="mw-sernav" aria-label="{html.escape(series["label"])}のシリーズ内移動">',
        f'      <div class="mw-sernav-h">📚 {html.escape(series["label"])}</div>',
        '      <div class="mw-sernav-row">',
        button("prev", prev_item),
        button("next", next_item),
        "      </div>",
    ]
    # 一覧リンクが guides.html そのものなら、下の「解説記事一覧に戻る」と行き先が同じ＝二重に出さない
    if not (has_back_btn and series["index"] == "guides.html"):
        parts.append(
            f'      <div class="mw-sernav-idx"><a href="{series["index"]}">シリーズの記事一覧を見る →</a></div>')
    parts.append("    </nav>")
    if has_back_btn:
        parts.append(BACK_BTN_HTML)
    parts += [END, ""]
    return "\n".join(parts)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def write(path, text):
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def apply_block(text, series, prev_item, next_item):
    """既存ブロックがあれば置換、無ければ </main>（無ければ <footer）の直前に挿入。"""
    # ⚠️ 判定はブロック除去より前に行う（2回目以降はボタンがブロックの中にいるため）
    has_back_btn = BACK_BTN_MARK in text
    text = BLOCK_RE.sub("", text)
    text = BACK_BTN_RE.sub("\n", text)
    block = build_block(series, prev_item, next_item, has_back_btn)
    # 記事の骨格は3世代ある。新しい順に見て、最初に見つかった閉じ位置の直前へ入れる
    for anchor in ("</main>", "</div><!-- /container -->", "<footer"):
        i = text.find(anchor)
        if i != -1:
            return text[:i] + block + text[i:], None
    return text, "差し込み位置（</main> も <footer> も）が見つからない"


def run(root, keys, do_apply, log=print):
    changed, skipped, errors = [], [], []
    for series in SERIES:
        if keys and series["key"] not in keys:
            continue
        items = collect(series, root)
        if len(items) < 2:
            log(f"⏭️  {series['key']}: 記事が {len(items)} 本しかないので前後リンク不要")
            continue
        log(f"📚 {series['key']}（{series['label']}）: {len(items)} 本")
        for n, item in enumerate(items):
            prev_item = items[n - 1] if n > 0 else None
            next_item = items[n + 1] if n < len(items) - 1 else None
            before = read(item["path"])
            after, err = apply_block(before, series, prev_item, next_item)
            if err:
                errors.append(f"{item['file']}: {err}")
                continue
            if after == before:
                skipped.append(item["file"])
                continue
            changed.append(item["file"])
            if do_apply:
                write(item["path"], after)
    return changed, skipped, errors


def main():
    ap = argparse.ArgumentParser(description="連続シリーズ記事に前後移動ボタンを敷く（既定 dry-run）")
    ap.add_argument("--apply", action="store_true", help="実際に書き込む")
    ap.add_argument("--series", default="", help="対象を絞る（カンマ区切り: " +
                    ",".join(s["key"] for s in SERIES) + "）")
    ap.add_argument("--root", default=os.path.dirname(os.path.abspath(__file__)))
    args = ap.parse_args()

    keys = [k.strip() for k in args.series.split(",") if k.strip()]
    unknown = [k for k in keys if k not in {s["key"] for s in SERIES}]
    if unknown:
        print(f"❌ 未知のシリーズ: {', '.join(unknown)}")
        return 2

    changed, skipped, errors = run(args.root, keys, args.apply)
    print(f"\n{'✅ 更新' if args.apply else '📝 更新予定'}: {len(changed)} 本 / 変更なし: {len(skipped)} 本")
    for f in changed[:20]:
        print(f"   - {f}")
    if len(changed) > 20:
        print(f"   … 他 {len(changed) - 20} 本")
    if errors:
        print(f"\n❌ エラー {len(errors)} 件")
        for e in errors:
            print(f"   - {e}")
        return 1
    if changed and not args.apply:
        print("\n書き込むには --apply を付けて再実行してください。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
