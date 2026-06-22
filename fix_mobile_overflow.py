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
import re
import glob

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SD = os.path.dirname(os.path.abspath(__file__))
MARKER = 'id="mw-mobile-fit"'
# 既存ブロックを丸ごと差し替えるための正規表現（版更新を冪等に行う）。
# style に続く mw-mobile-fit-js の <script> もまとめて一致させる（無い旧版＝style のみも可）。
STYLE_RE = re.compile(
    r'<style id="mw-mobile-fit">.*?</style>'
    r'(?:\s*<script id="mw-mobile-fit-js">.*?</script>)?',
    re.S,
)

BLOCK = """<style id="mw-mobile-fit">
/* 📱 スマホ最適化 v3（fix_mobile_overflow.py が注入）: 数字は桁割れさせない・スマホの表は折り返さず横スクロール＋スクロール誘導・左右余白を圧縮 */
html,body{overflow-x:hidden}
.article,main,section,header,footer{max-width:100%}
*{overflow-wrap:break-word;word-break:normal}
img,svg,iframe,video{max-width:100%!important;height:auto}
pre,code{white-space:pre-wrap;overflow-wrap:break-word}
td strong,td b,th strong{white-space:nowrap}
.mw-scroll-hint{font-size:.72rem;color:#8b949e;margin:2px 2px 14px;text-align:right;font-weight:500}
@media(min-width:601px){.mw-scroll-hint{display:none}}
@media(max-width:600px){
  body{font-size:.9rem;line-height:1.7}
  .article{padding:14px 11px}
  h1{font-size:1.26rem;line-height:1.4}
  h2{font-size:1.08rem}
  /* スマホでは表を無理に収めず「表の中だけ」横スクロール（PC表示は変えない）。セルは折り返さず1行＝数字も説明も縦に割れない */
  table{display:block;width:100%;overflow-x:auto;-webkit-overflow-scrolling:touch;font-size:.8rem}
  th,td{padding-left:6px;padding-right:6px;white-space:nowrap}
  .meta-line,.chart-cap,.disclaimer,.related-card-desc{font-size:.74rem}
}
@media(max-width:380px){
  body{font-size:.86rem}
  .article{padding:12px 8px}
  table{font-size:.76rem}
}
</style>
<script id="mw-mobile-fit-js">
(function(){try{
function mark(){
if(window.innerWidth>600)return;
var ts=document.getElementsByTagName('table');
for(var i=0;i<ts.length;i++){(function(t){
if(t.getAttribute('data-mw-sc'))return;
if(t.scrollWidth-t.clientWidth>4){
t.setAttribute('data-mw-sc','1');
var h=document.createElement('div');
h.className='mw-scroll-hint';
h.textContent='\\u2192 \\u6a2a\\u306b\\u30b9\\u30af\\u30ed\\u30fc\\u30eb\\u3067\\u304d\\u307e\\u3059';
if(t.parentNode)t.parentNode.insertBefore(h,t.nextSibling);
t.addEventListener('scroll',function(){if(t.scrollLeft>8){h.style.display='none';}},{passive:true});
}
})(ts[i]);}
}
if(document.readyState!=='loading'){mark();}else{document.addEventListener('DOMContentLoaded',mark);}
window.addEventListener('resize',mark);
}catch(e){}})();
</script>
"""


def apply_block(html):
    """html に mobile-fit ブロックを反映した新 html を返す。
    既存ブロックがあれば差し替え、無ければ </head> 直前に注入。
    返り値 (new_html, action)。action= 'update'|'inject'|'same'|'nohead'。"""
    if MARKER in html:
        new = STYLE_RE.sub(lambda m: BLOCK.strip(), html, count=1)
        # CRLF/LF だけの差は同一扱い（Windows の text-write 由来の改行差で
        # local(CRLF)↔cloud(LF) が無限に再 PUT し合う ping-pong を防ぐ）
        if new.replace("\r\n", "\n") == html.replace("\r\n", "\n"):
            return (html, "same")
        return (new, "update")
    if "</head>" not in html:
        return (html, "nohead")
    return (html.replace("</head>", BLOCK + "</head>", 1), "inject")


def main():
    dry = "--dry-run" in sys.argv
    files = sorted(os.path.basename(p) for p in glob.glob(os.path.join(SD, "guide-*.html")))
    updated = injected = same = nohead = 0
    for fn in files:
        p = os.path.join(SD, fn)
        with open(p, encoding="utf-8") as f:
            html = f.read()
        new, action = apply_block(html)
        if action == "nohead":
            nohead += 1
            print(f"  ⚠️ {fn}: </head> が無い、スキップ")
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
            print(f"  {'[DRY] ' if dry else '✅ '}{fn}: モバイルCSSを{verb}")
    print(f"\n{'[DRY-RUN] ' if dry else ''}対象 guide記事 {len(files)} / 差し替え {updated} "
          f"/ 新規注入 {injected} / 変更なし {same}"
          + (f" / head無し {nohead}" if nohead else ""))
    if dry:
        print("→ 問題なければ --dry-run を外して再実行。")


if __name__ == "__main__":
    main()
