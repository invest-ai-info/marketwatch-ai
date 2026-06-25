#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""inject_site_search.py — 全ページ横断検索 (site-search.js) の <script> タグを
静的 HTML に冪等注入する。

対象:
  - 公開記事 guide-*.html
  - guides.html / about.html / contact.html / privacy.html

除外（理由）:
  - cron/routine が生成する 9 ページ（6 コア + youtube/track-record/political-feed）
    → 生成元スクリプト側で <script> を emit 済み。ローカル注入すると再生成で消える上、
      SYNC 禁忌（ローカルから push 不可）なので触らない。
  - drafts/ 配下（noindex の下書き）… glob "guide-*.html" は drafts/ を拾わない
  - 先頭が "_" の作業用ファイル（_draft*/_pub*/_preview* 等）

冪等: 既に "site-search.js" を含むファイルはスキップ。

使い方:
  python inject_site_search.py           # ドライラン（変更内容を表示するだけ）
  python inject_site_search.py --apply   # 実際に書き込む
"""
import sys
import glob
import os

TAG = '<script src="site-search.js" defer></script>'

NAMED = ["guides.html", "about.html", "contact.html", "privacy.html"]

# 生成ページ（生成元で対応済み・SYNC 禁忌）→ ローカル注入しない
# guides.html は専用の「ページ内フィルタ」を持つため floating 検索は載せない（二重回避）
EXCLUDE = {
    "index.html", "calendar.html", "charts.html", "vix.html",
    "market-health.html", "hot-assets.html",
    "youtube-summary.html", "track-record.html", "political-feed.html",
    "guides.html",
}


def targets():
    files = set(glob.glob("guide-*.html"))
    for f in NAMED:
        if os.path.exists(f):
            files.add(f)
    out = []
    for f in sorted(files):
        base = os.path.basename(f)
        if base in EXCLUDE:
            continue
        if base.startswith("_"):
            continue
        out.append(f)
    return out


def main():
    apply = "--apply" in sys.argv
    changed, skipped, no_body = [], [], []

    for f in targets():
        with open(f, encoding="utf-8") as fh:
            html = fh.read()
        if "site-search.js" in html:
            skipped.append(f)
            continue
        idx = html.rfind("</body>")
        if idx == -1:
            no_body.append(f)
            continue
        new = html[:idx] + TAG + "\n" + html[idx:]
        if apply:
            with open(f, "w", encoding="utf-8") as fh:
                fh.write(new)
        changed.append(f)

    mode = "適用" if apply else "ドライラン"
    print(f"[{mode}] 対象 {len(targets())} 件 / 注入 {len(changed)} / "
          f"スキップ(既存) {len(skipped)} / </body>無し {len(no_body)}")
    for f in changed:
        print(f"  + {f}")
    if no_body:
        print("  ⚠️ </body> が見つからない（手動確認）:")
        for f in no_body:
            print(f"    - {f}")
    if not apply and changed:
        print("\n→ 問題なければ `python inject_site_search.py --apply` で書き込み。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
