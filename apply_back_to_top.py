# -*- coding: utf-8 -*-
"""apply_back_to_top.py — SYNC対象の静的HTMLへ「↑上に戻る」ボタンを冪等注入（2026-07-21）。

背景: 2026-07-20 のUX改善で safe_write()（generate_market_news.py）が生成ページ
（6コア + 週次/月次/自動生成）へ BACK_TO_TOP を一括注入するようになった。
残る「手で書いた静的記事 約75本」への適用がこのツール（fix_mobile_overflow.py と同型）。

設計:
  - マークアップの単一ソース＝generate_market_news.py の BACK_TO_TOP 定数
    （正規表現で抽出して使う＝ここに複製を持たない。定数を更新すれば再実行で全記事が追随）
  - 対象＝SYNC_FILES に登録済みの guide-*.html ＋ guides/about/contact/privacy
    （push されてライブに反映されるものだけ。クラウド生成記事 guide-news-/guide-signal-lab-/
     guide-proverb- 等は SYNC 外＝触らない。ローカル drift を作らないため）
  - 既に id="mw-back-to-top" があれば最新版へ差し替え（変更なしなら何もしない）＝再実行安全

使い方:
  python apply_back_to_top.py --dry-run   # 変更対象だけ表示
  python apply_back_to_top.py             # 注入/差し替え
新記事は publish 前にこのツールを再実行すれば入る（check_site_consistency が欠落を warning）。
"""
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SD = os.path.dirname(os.path.abspath(__file__))
MARKER = 'id="mw-back-to-top"'
EXTRA_PAGES = {"guides.html", "about.html", "contact.html", "privacy.html"}
CLOUD_PREFIXES = ("guide-news-", "guide-signal-lab-", "guide-proverb-",
                  "guide-weekly-", "guide-auto-", "guide-monthly-report-")
# 既存ブロックを丸ごと差し替えるための正規表現（BACK_TO_TOP のコメント囲みに一致）
BLOCK_RE = re.compile(r"<!-- ===== ↑上に戻る.*?/上に戻る ===== -->\n?", re.S)


def load_block():
    """generate_market_news.py の BACK_TO_TOP 定数を抽出（単一ソース）。"""
    with open(os.path.join(SD, "generate_market_news.py"), encoding="utf-8") as f:
        s = f.read()
    m = re.search(r"BACK_TO_TOP = '''(.*?)'''", s, re.S)
    if not m:
        print("❌ generate_market_news.py から BACK_TO_TOP 定数を抽出できない")
        sys.exit(1)
    return m.group(1).strip() + "\n"


def load_sync_files():
    """sync_to_github.py の SYNC_FILES を抽出（check_site_consistency.py と同方式・importしない）。"""
    with open(os.path.join(SD, "sync_to_github.py"), encoding="utf-8") as f:
        s = f.read()
    m = re.search(r"SYNC_FILES\s*=\s*\[(.*?)\n\]", s, re.S)
    if not m:
        print("❌ sync_to_github.py の SYNC_FILES を解析できない")
        sys.exit(1)
    return set(re.findall(r'"([^"]+)"', m.group(1)))


def apply_block(html, block):
    """返り値 (new_html, action)。action= 'update'|'inject'|'same'|'nobody'。"""
    if MARKER in html:
        new = BLOCK_RE.sub(lambda m: block, html, count=1)
        if new.replace("\r\n", "\n") == html.replace("\r\n", "\n"):
            return (html, "same")
        return (new, "update")
    if "</body>" not in html:
        return (html, "nobody")
    return (html.replace("</body>", block + "</body>", 1), "inject")


def main():
    dry = "--dry-run" in sys.argv
    block = load_block()
    sync_files = load_sync_files()
    targets = sorted(
        f for f in sync_files
        if f.endswith(".html")
        and (f.startswith("guide-") or f in EXTRA_PAGES)
        and not f.startswith(CLOUD_PREFIXES)
        and os.path.exists(os.path.join(SD, f))
    )
    updated = injected = same = nobody = 0
    for fn in targets:
        p = os.path.join(SD, fn)
        with open(p, encoding="utf-8") as f:
            html = f.read()
        new, action = apply_block(html, block)
        if action == "nobody":
            nobody += 1
            print(f"  ⚠️ {fn}: </body> が無い、スキップ")
            continue
        if action == "same":
            same += 1
            continue
        if not dry:
            with open(p, "w", encoding="utf-8") as f:
                f.write(new)
        if action == "update":
            updated += 1
        else:
            injected += 1
        if (updated + injected) <= 5 or dry:
            verb = "差し替え" if action == "update" else "注入"
            print(f"  {'[DRY] ' if dry else '✅ '}{fn}: 上に戻るボタンを{verb}")
    print(f"\n{'[DRY-RUN] ' if dry else ''}対象（SYNC入り静的HTML） {len(targets)} / 差し替え {updated} "
          f"/ 新規注入 {injected} / 変更なし {same}"
          + (f" / body無し {nobody}" if nobody else ""))
    if dry:
        print("→ 問題なければ --dry-run を外して再実行。")


if __name__ == "__main__":
    main()
