"""
inject_newsletter.py — 無料メルマガ登録フォームを静的ページ
（guide-*.html + guides.html）の <footer> 直前に冪等注入する保守ツール。

設計:
  - フォーム本体は generate_market_news.NEWSLETTER_FORM を「単一ソース」として再利用。
    （6コアページは safe_write() が自動注入。本スクリプトは静的ページ用の横展開。）
  - 冪等: 既に "mw-newsletter" を含むファイルはスキップ。
  - <footer> が無いファイルは触らずに警告。
  - 追加のみ（既存内容は削らない）。LF で書き出し。

使い方:
  python inject_newsletter.py --dry-run   # 変更内容を確認（書き込まない）
  python inject_newsletter.py             # 実行

※ フォーム文言を将来変えた場合、6コアは自動反映されるが静的ページは
   本スクリプトの再実行が必要（冪等なので何度流してもOK）。
"""
import sys
import os
import glob
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import generate_market_news as g  # noqa: E402

FORM = g.NEWSLETTER_FORM
MARKER = "mw-newsletter"
START = "<!-- ===== MarketWatch 無料メルマガ登録"
END = "<!-- ===== /無料メルマガ登録 ===== -->"


def targets():
    files = sorted(glob.glob(os.path.join(HERE, "guide-*.html")))
    guides_index = os.path.join(HERE, "guides.html")
    if os.path.exists(guides_index):
        files.append(guides_index)
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--update", action="store_true",
                    help="既にフォームがあるページの文言を最新のNEWSLETTER_FORMに置換する")
    args = ap.parse_args()

    injected = updated = skipped_present = skipped_nofooter = unchanged = 0
    for path in targets():
        name = os.path.basename(path)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        if MARKER in content:
            if args.update:
                i, j = content.find(START), content.find(END)
                if i == -1 or j == -1:
                    print(f"  WARN {name}: フォーム境界コメントが見つからず置換できない")
                    skipped_present += 1
                    continue
                new_content = content[:i] + FORM.strip() + content[j + len(END):]
                if new_content == content:
                    unchanged += 1
                    continue
                updated += 1
                if args.dry_run:
                    print(f"  [dry] update -> {name}")
                else:
                    with open(path, "w", encoding="utf-8", newline="\n") as f:
                        f.write(new_content)
                    print(f"  UPD  {name}")
            else:
                skipped_present += 1
            continue
        if "<footer" not in content:
            skipped_nofooter += 1
            print(f"  WARN {name}: <footer> が無い -> スキップ")
            continue
        new_content = content.replace("<footer", FORM + "<footer", 1)
        injected += 1
        if args.dry_run:
            print(f"  [dry] inject -> {name}")
        else:
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(new_content)
            print(f"  OK   {name}")

    print("-" * 32)
    head = "DRY-RUN " if args.dry_run else ""
    print(f"{head}injected={injected} / updated={updated} / unchanged={unchanged} / already={skipped_present} / no-footer={skipped_nofooter}")


if __name__ == "__main__":
    main()
