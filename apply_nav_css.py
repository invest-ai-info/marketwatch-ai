# -*- coding: utf-8 -*-
"""apply_nav_css.py — 記事ページのナビCSSを標準形へ冪等正規化（2026-07-21）。

背景: unify_navbar.py の統一はナビ HTML のみで、CSS は対象外だった。
クラウド自動公開レーン（guide-news-*/guide-signal-lab-*）のテンプレが古い CSS を
自己増殖し、`.nav-bar` の max-width:1000px 欠落で広い画面でボタンが 8+2 に崩れていた
（手描き記事は max-width あり＝常に 5+5 の整列）。

設計:
  - ナビ記事CSSの標準形＝このファイルの STD_* 定数（単一ソース。変更したら再実行で全記事追随）
  - 対象＝ローカルの全 guide-*.html（クラウド生成記事も含む＝一回限りの修復。
    以後の新規クラウド記事は publish_article.py が公開時に normalize_nav_css() を通すため
    ここを再実行しなくても標準形で出る）
  - 直すのは3点だけ（冪等・非該当はそのまま）:
      1. `.nav-bar{display:flex...}` → max-width:1000px;margin:0 auto 32px 入りの標準形
      2. `.nav-btn{...padding:11px 20px...}`（基本ルール）→ inline-flex/transition 入りの標準形
      3. `.nav-btn:hover` が無ければ基本ルール直後に追加
    ※ モバイル用 `.nav-btn{min-width:0...}`・`body.dark .nav-btn`・`.nav-btn.current` は不変

使い方:
  python apply_nav_css.py --dry-run   # 変更対象だけ表示
  python apply_nav_css.py             # 正規化を適用
"""
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SD = os.path.dirname(os.path.abspath(__file__))

STD_NAVBAR = (".nav-bar{display:flex;flex-wrap:wrap;gap:10px;justify-content:center;"
              "max-width:1000px;margin:0 auto 32px}")
STD_NAVBTN = (".nav-btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;"
              "padding:11px 20px;background:#f6f8fa;border:1px solid #d0d7de;border-radius:10px;"
              "color:#57606a;text-decoration:none;font-size:.95rem;font-weight:600;"
              "transition:all .2s;min-width:170px}")
STD_HOVER = ".nav-btn:hover{border-color:#0969da;color:#0969da}"

# flex のナビ枠ルール（メディアクエリ内の display:grid ルールには一致しない）
RE_NAVBAR = re.compile(r"\.nav-bar\{display:flex[^}]*\}")
# 基本ボタンルール（padding:11px 20px を含むものだけ＝モバイル/ダーク/current は
# その padding を持たないため不一致。セレクタ前置詞の有無では区別しない）
RE_NAVBTN = re.compile(r"\.nav-btn\{[^}]*padding:11px 20px[^}]*\}")


def normalize_nav_css(html):
    """返り値 (new_html, fixes)。fixes は適用した修正名のリスト（空なら変更なし）。"""
    fixes = []
    m = RE_NAVBAR.search(html)
    if m and m.group(0) != STD_NAVBAR:
        html = html[:m.start()] + STD_NAVBAR + html[m.end():]
        fixes.append("nav-bar")
    m = RE_NAVBTN.search(html)
    if m:
        if m.group(0) != STD_NAVBTN:
            html = html[:m.start()] + STD_NAVBTN + html[m.end():]
            fixes.append("nav-btn")
        if ".nav-btn:hover" not in html:
            m2 = RE_NAVBTN.search(html)  # 置換後の位置を取り直す
            html = html[:m2.end()] + "\n    " + STD_HOVER + html[m2.end():]
            fixes.append("hover")
    return html, fixes


def main():
    dry = "--dry-run" in sys.argv
    targets = sorted(f for f in os.listdir(SD)
                     if f.startswith("guide-") and f.endswith(".html"))
    changed = same = 0
    for fn in targets:
        p = os.path.join(SD, fn)
        with open(p, encoding="utf-8") as f:
            html = f.read()
        new, fixes = normalize_nav_css(html)
        if not fixes:
            same += 1
            continue
        if not dry:
            with open(p, "w", encoding="utf-8") as f:
                f.write(new)
        changed += 1
        if changed <= 8 or dry:
            print(f"  {'[DRY] ' if dry else '✅ '}{fn}: {'+'.join(fixes)}")
    print(f"\n{'[DRY-RUN] ' if dry else ''}対象 {len(targets)} / 正規化 {changed} / 変更なし {same}")
    if dry:
        print("→ 問題なければ --dry-run を外して再実行。")


if __name__ == "__main__":
    main()
