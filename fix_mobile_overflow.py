# -*- coding: utf-8 -*-
"""fix_mobile_overflow.py — 全 guide-*.html に「スマホ横はみ出し防止」CSSを冪等注入（2026-06-20）。

スマホで記事が右にはみ出す（初見の人がコンテンツを見落とす）問題の恒久対策。
各記事の </head> 直前に <style id="mw-mobile-fit"> を1回だけ挿入する（再実行しても二重化しない）。

効果:
  ① 長い英単語/URL/数字を折り返す（overflow-wrap）＝はみ出しの主因を解消
  ② 広い表は「表の中だけ」横スクロール（ページ全体は動かない）
  ③ 画像/SVG/iframe を画面幅に収める
  ④ スマホ（≤600px）で本文を少し小さく・余白を詰めて1行に収まりやすく
  ⑤ ページ全体の横スクロールを停止（最終防壁）

使い方:
  python fix_mobile_overflow.py --dry-run   # 変更対象だけ表示
  python fix_mobile_overflow.py             # 注入
新記事にもこのツールを再実行すれば自動で入る（check_site_consistency が欠落を warning）。
"""
import os
import sys
import glob

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SD = os.path.dirname(os.path.abspath(__file__))
MARKER = 'id="mw-mobile-fit"'

BLOCK = """<style id="mw-mobile-fit">
/* 📱 スマホ横はみ出し防止（fix_mobile_overflow.py が注入）: 長い語の折り返し・広い表は表内スクロール・媒体縮小・ページ横スクロール停止 */
html,body{overflow-x:hidden}
.article,main,section,header,footer{max-width:100%}
*{overflow-wrap:anywhere}
img,svg,iframe,video{max-width:100%!important;height:auto}
pre,code{white-space:pre-wrap;overflow-wrap:anywhere}
@media(max-width:600px){
  body{font-size:.92rem;line-height:1.8}
  .article{padding:18px 14px}
  h1{font-size:1.3rem;line-height:1.42}
  h2{font-size:1.12rem}
  /* 広い表はスマホ時だけ「表の中だけ」横スクロール（PC表示は変えない） */
  table{display:block;width:100%;overflow-x:auto;-webkit-overflow-scrolling:touch;font-size:.82rem}
  .meta-line,.chart-cap,.disclaimer,.related-card-desc{font-size:.76rem}
}
</style>
"""


def main():
    dry = "--dry-run" in sys.argv
    files = sorted(os.path.basename(p) for p in glob.glob(os.path.join(SD, "guide-*.html")))
    done = skip = nohead = 0
    for fn in files:
        p = os.path.join(SD, fn)
        with open(p, encoding="utf-8") as f:
            html = f.read()
        if MARKER in html:
            skip += 1
            continue
        if "</head>" not in html:
            nohead += 1
            print(f"  ⚠️ {fn}: </head> が無い、スキップ")
            continue
        new = html.replace("</head>", BLOCK + "</head>", 1)
        if not dry:
            with open(p, "w", encoding="utf-8") as f:
                f.write(new)
        done += 1
        if done <= 3 or dry:
            print(f"  {'[DRY] ' if dry else '✅ '}{fn}: モバイル最適化CSSを注入")
    print(f"\n{'[DRY-RUN] ' if dry else ''}対象 guide記事 {len(files)} / 注入 {done} / 既に有り {skip}"
          + (f" / head無し {nohead}" if nohead else ""))
    if dry:
        print("→ 問題なければ --dry-run を外して再実行。")


if __name__ == "__main__":
    main()
