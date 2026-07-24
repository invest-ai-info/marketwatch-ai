# -*- coding: utf-8 -*-
"""過去のシグナル研究日誌（guide-signal-lab-*.html）へ「発火条件の図解カタログ」導線を冪等注入。

2026-07-24 新設（オーナー依頼「日誌もチャート図解で説明してほしい」の過去分対応）。
- 挿入位置 = meta-line 直後（記事冒頭で図解カタログへ誘導）
- マーカー id="mw-anatomy-link" で冪等（再実行しても二重挿入しない）
- 数値・本文・SVGには一切触れない（導線ボックス1個の追加のみ）
使い方: python apply_anatomy_link.py [--apply]   （無指定は dry-run）
"""
import glob
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MARKER = 'id="mw-anatomy-link"'
BOX = ('\n    <div id="mw-anatomy-link" class="info-box" style="margin:14px 0 22px">📈 '
       '<a href="guide-signal-anatomy.html"><strong>発火条件をチャートで解剖する図解カタログ</strong></a>'
       ' — この日誌に出てくるシグナル名（RSI過売り反発・−2σタッチ・高値ブレイク等）が'
       'チャートのどの瞬間かを図解で確認できます。</div>')
# meta-line は旧テンプレ=<div>、#44以降の一部=<p>（最初の1個＝記事冒頭のものだけに挿入）
META_RE = re.compile(r'(<div class="meta-line">.*?</div>|<p class="meta-line">.*?</p>)', re.S)


def main():
    apply = "--apply" in sys.argv
    done = skipped = failed = 0
    for fp in sorted(glob.glob(os.path.join(HERE, "guide-signal-lab-*.html"))):
        name = os.path.basename(fp)
        html = io.open(fp, encoding="utf-8").read()
        if MARKER in html:
            skipped += 1
            continue
        m = META_RE.search(html)
        if not m:
            print(f"  ⚠️ {name}: meta-line が見つからずスキップ")
            failed += 1
            continue
        new = html[:m.end()] + BOX + html[m.end():]
        if apply:
            io.open(fp, "w", encoding="utf-8", newline="").write(new)
        done += 1
    mode = "適用" if apply else "dry-run"
    print(f"{mode}: 注入 {done} / 既存スキップ {skipped} / 失敗 {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
