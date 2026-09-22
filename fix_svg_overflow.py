# -*- coding: utf-8 -*-
"""fix_svg_overflow.py — 右にはみ出す <text> は **viewBox の幅を広げて** 収める。

🔑 x をずらす方式は捨てた（2026-09-22 実測）:
   ① 文字列長が変わる置換を前から当てると2件目以降の位置がずれてタグが壊れる
   ② ずらすと図の中身と衝突し、text_overlap / occlusion が新たに赤くなる
   viewBox を広げれば **要素同士の相対位置は一切変わらない**ので衝突しない。
⚠️ viewBox の原点は動かさない。オラクルは viewBox="0 0 W H" にしか一致しないため、
   原点を変えると検査対象から外れてしまう＝ゲート破りになる。
   左へはみ出すもの（長い中央寄せキャプション等）はこの方式では直せないので触らない。
"""
import io,re,sys,glob
sys.path.insert(0,'.')
import signal_lab_verify as slv
MARGIN=6.0

def fix(path, apply=False):
    s=io.open(path,encoding='utf-8').read()
    edits=[]   # (開始, 終了, 新テキスト)
    for m in re.finditer(r'<svg[^>]*viewBox="0 0 ([\d.]+) ([\d.]+)"(.*?)</svg>', s, re.S):
        W=float(m.group(1)); H=m.group(2); body=m.group(3)
        need=W; left_bad=False
        # 回転/縦書きの <text> は横幅の判定に使わない（オラクルが transform を見ないため、
        # 横に長いボックスとして誤計算される。これを混ぜると幅を無駄に広げてしまう）
        for x0,y0,x1,y1,t,pos in slv._svg_text_boxes(body, with_pos=True):
            tm=re.match(r'<text\b([^>]*)>', body[pos:])
            attrs=tm.group(1) if tm else ""
            if 'rotate(' in attrs or 'writing-mode' in attrs:
                continue
            if x0 < -2: left_bad=True
            if x1 > W+2: need=max(need, x1+MARGIN)
        if need<=W or left_bad:      # 広げる必要なし／左はみ出しは別対応
            continue
        vb_m=re.search(r'viewBox="0 0 [\d.]+ [\d.]+"', s[m.start():m.start(3)])
        a=m.start()+vb_m.start(); b=m.start()+vb_m.end()
        edits.append((a,b,f'viewBox="0 0 {need:g} {H}"', W, need))
    if not edits: return []
    out=s
    for a,b,new,_,_ in sorted(edits, key=lambda e:-e[0]):   # 後ろから当てる＝位置がずれない
        out=out[:a]+new+out[b:]
    if apply: io.open(path,'w',encoding='utf-8',newline='\n').write(out)
    return [(o,n) for _,_,_,o,n in edits]

apply = sys.argv[1]=='--apply'
tot=0
for f in sorted(glob.glob('guide-*.html')):
    r=fix(f, apply)
    if r:
        print(f"{'OK  ' if apply else '[dry]'} {f}: " + " / ".join(f"幅 {o:g}→{n:g}" for o,n in r))
        tot+=len(r)
print(f"---- {'適用' if apply else 'DRY-RUN'}: {tot}個のSVG")
