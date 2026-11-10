import json,sys,re
sys.path.insert(0,'.')
import signal_lab_verify as v
data=json.load(open('signals-log.json',encoding='utf-8-sig'))
ASOF="2026-11-11T06:12:00+09:00"
data,af,_=v.apply_asof(data,v.parse_asof(ASOF),"2026-11-11")
B="2026-06-23"; MID="2026-09-01"; S={"trend":"上昇","reversal_long":True}
C={
"fwd":("FWD：上昇トレンド中の逆張りの買いの勝ち回数",{**S,"fired_from":B}),
"long":("FWD：買い全体（対照）の勝ち回数",{"direction":"long","fired_from":B}),
"all":("FWD：全シグナル（対照）の勝ち回数",{"fired_from":B}),
"upl":("FWD：上昇トレンドの買い全体（対照）の勝ち回数",{"trend":"上昇","direction":"long","fired_from":B}),
"rev":("FWD：逆張りの買い全体（対照）の勝ち回数",{"reversal_long":True,"fired_from":B}),
"is":("IS：上昇トレンド中の逆張りの買い（登録前・参考）の勝ち回数",{**S,"fired_before":B}),
"islong":("IS：買い全体（登録前・参考）の勝ち回数",{"direction":"long","fired_before":B}),
"h1":("FWD：上昇トレンド中の逆張りの買い・1時間足",{**S,"tf":"1h","fired_from":B}),
"h4":("FWD：上昇トレンド中の逆張りの買い・4時間足",{**S,"tf":"4h","fired_from":B}),
"d1":("FWD：上昇トレンド中の逆張りの買い・日足",{**S,"tf":"1d","fired_from":B}),
"idx":("FWD：上昇トレンド中の逆張りの買い・株価指数",{**S,"group":"index","fired_from":B}),
"jpy":("FWD：上昇トレンド中の逆張りの買い・円がらみFX",{**S,"group":"jpy_fx","fired_from":B}),
"ofx":("FWD：上昇トレンド中の逆張りの買い・円がらまないFX",{**S,"group":"other_fx","fired_from":B}),
"met":("FWD：上昇トレンド中の逆張りの買い・金銀",{**S,"group":"metal","fired_from":B}),
"btc":("FWD：上昇トレンド中の逆張りの買い・ビットコイン",{**S,"group":"btc","fired_from":B}),
"oil":("FWD：上昇トレンド中の逆張りの買い・原油",{**S,"group":"oil","fired_from":B}),
"first":("FWD：上昇トレンド中の逆張りの買い・前半（〜8月31日）",{**S,"fired_from":B,"fired_before":MID}),
"second":("FWD：上昇トレンド中の逆張りの買い・後半（9月1日〜）",{**S,"fired_from":MID}),
}
R={}; claims=[]
for key,(lab,f) in C.items():
    k,n=v.compute(data,f); lo,hi=v.wilson(k,n)
    if hi<=1: lo,hi=lo*100,hi*100
    R[key]=dict(k=k,n=n,p=100*k/n,lo=lo,hi=hi)
    claims.append({"label":lab,"filter":f,"k":k,"n":n})
json.dump({"article_id":"146","asof":ASOF,"hypothesis_id":"auto_reversal_long-True_trend-上昇","claims":claims},open('drafts/labnotes/lab-146-claims.json','w'),ensure_ascii=False,indent=1)
def pct(x):return f"{x:.1f}%"
def row(name,key,bold=False):
    r=R[key]; p=pct(r['p'])
    if bold: name=f"<strong>{name}</strong>"; p=f"<strong>{p}</strong>"; n=f"<strong>{r['n']:,}回</strong>"
    else: n=f"{r['n']:,}回"
    return f"          <tr><td>{name}</td><td>{r['k']:,}回</td><td>{n}</td><td>{p}</td><td>{r['lo']:.1f}%〜{r['hi']:.1f}%</td></tr>"
F=R['fwd']
html=open('drafts/draft-signal-lab-145.html',encoding='utf-8').read()
pre=html[:html.index('<main class="s-main">')]
post=html[html.index('<!-- 関連記事カード -->'):]
post=re.sub(r'<!-- series-nav:begin -->.*?<!-- series-nav:end -->\n?','',post,flags=re.S)
TITLE=f"上がっている途中の下げを買うシグナルは勝ちやすい？ 前向き{F['n']}回で確かめた【研究日誌 #146】"
DESC=f"上昇トレンドの途中で、下がったところの反発をねらう買いのシグナルを、前向き{F['n']}回で確認。勝った割合{pct(F['p'])}、偶然のぶれを考えた勝率は{F['lo']:.1f}%〜{F['hi']:.1f}%。登録前との比較も整理。研究日誌第146回。"
pre=re.sub(r'<title>.*?</title>',f'<title>{TITLE} - MarketWatch AI</title>',pre,flags=re.S)
pre=re.sub(r'(<meta name="description" content=")[^"]*',r'\g<1>'+DESC,pre)
pre=re.sub(r'(<meta name="keywords" content=")[^"]*',r'\g<1>上昇トレンド,逆張り,押し目買い,シグナル研究,前向き検証,研究日誌',pre)
pre=pre.replace('guide-signal-lab-145.html','guide-signal-lab-146.html')
pre=re.sub(r'(<meta property="og:title" content=")[^"]*',r'\g<1>'+TITLE,pre)
pre=re.sub(r'(<meta property="og:description" content=")[^"]*',r'\g<1>'+DESC,pre)
pre=re.sub(r'("headline": ")[^"]*',r'\g<1>'+TITLE,pre)
pre=re.sub(r'("description": ")[^"]*',r'\g<1>'+DESC,pre)
pre=pre.replace('"datePublished": "2026-11-10"','"datePublished": "2026-11-11"').replace('"dateModified": "2026-11-10"','"dateModified": "2026-11-11"')
pre=re.sub(r'<h1>.*?</h1>',f'<h1>{TITLE}</h1>',pre)
pre=re.sub(r'<p class="meta-line">公開：[^<]*</p>','<p class="meta-line">公開：2026年11月11日　前向き期間：2026年6月23日〜　仮説登録日：2026年6月22日</p>',pre)
K=4.0
def bar(x,pct_,col,op,lab,sub,bold=False):
    hh=K*pct_; y=265-hh; w=' font-weight="bold"' if bold else ''
    return (f'        <rect x="{x}" y="{y:.1f}" width="60" height="{hh:.1f}" fill="{col}" opacity="{op}" rx="3"/>\n'
    f'        <text x="{x+30}" y="{y-5:.1f}" font-size="11" font-family="sans-serif" text-anchor="middle" fill="{col}" font-weight="bold">{pct_:.1f}%</text>\n'
    f'        <text x="{x+30}" y="280" font-size="10" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)"{w}>{lab}</text>\n'
    f'        <text x="{x+30}" y="291" font-size="10" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)">{sub}</text>\n')
G='var(--c-green,#16a34a)'; A='var(--c-accent,#2563eb)'; M='var(--c-muted,#5a6072)'
bars=(bar(85,R['all']['p'],A,.5,'全シグナル',f"{R['all']['n']:,}回")
 +bar(160,R['long']['p'],A,.6,'買い全体',f"{R['long']['n']:,}回")
 +bar(235,R['rev']['p'],A,.7,'逆張りの買い',f"{R['rev']['n']:,}回")
 +bar(310,F['p'],G,.75,'上昇中の逆張り',f"{F['n']}回",True)
 +bar(385,R['first']['p'],G,.6,'前半',f"{R['first']['n']}回")
 +bar(460,R['second']['p'],G,.6,'後半',f"{R['second']['n']}回")
 +bar(535,R['is']['p'],M,.5,'登録前',f"{R['is']['n']}回"))
ticks=''.join(f'        <line x1="70" y1="{265-K*t:.0f}" x2="610" y2="{265-K*t:.0f}" stroke="var(--c-border,#e2e6ed)" stroke-width="0.5" stroke-dasharray="3,3"/>\n        <text x="65" y="{265-K*t+4:.0f}" font-size="10" font-family="sans-serif" fill="var(--c-muted,#999)" text-anchor="end">{t}%</text>\n' for t in (20,30,40,50))
svg1=f'''      <svg viewBox="0 0 640 310" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="上昇トレンド中の逆張りの買いの勝率比較棒グラフ" style="width:100%;max-width:640px;display:block;margin:0 auto">
        <rect width="640" height="310" fill="var(--c-surface,#fff)" rx="6"/>
        <text x="320" y="22" font-size="13" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)">前向き（2026年6月23日以降）と登録前の勝率比較</text>
        <line x1="70" y1="40" x2="70" y2="265" stroke="var(--c-border,#e2e6ed)" stroke-width="1"/>
        <line x1="70" y1="265" x2="610" y2="265" stroke="var(--c-border,#e2e6ed)" stroke-width="1"/>
        <text x="65" y="269" font-size="10" font-family="sans-serif" fill="var(--c-muted,#999)" text-anchor="end">0%</text>
{ticks}        <line x1="70" y1="{265-K*43:.1f}" x2="610" y2="{265-K*43:.1f}" stroke="var(--c-warn,#d97706)" stroke-width="1.5" stroke-dasharray="5,3"/>
        <text x="615" y="{265-K*43+3:.1f}" font-size="10" font-family="sans-serif" fill="var(--c-warn,#d97706)">43%</text>
{bars}      </svg>'''
svg2='''      <svg viewBox="0 0 640 300" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="上昇トレンドの途中の下げから反発する瞬間を示す概念図" style="width:100%;max-width:640px;display:block;margin:0 auto">
        <rect width="640" height="300" fill="var(--c-surface,#fff)" rx="6"/>
        <text x="320" y="20" font-size="13" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)">シグナルが出る瞬間のイメージ（上がっている途中の下げ）</text>
        <text x="20" y="44" font-size="10" font-family="sans-serif" fill="var(--c-muted,#5a6072)">値段</text>
        <polyline points="70,230 640,70" fill="none" stroke="var(--c-accent,#2563eb)" stroke-width="1.5" stroke-dasharray="6,3" opacity="0.6"/>
        <text x="420" y="66" font-size="11" font-family="sans-serif" fill="var(--c-accent,#2563eb)">全体は上向き（上昇トレンド）</text>
        <g stroke="var(--c-green,#16a34a)" stroke-width="1.5"><line x1="100" y1="196" x2="100" y2="236"/><line x1="160" y1="178" x2="160" y2="216"/><line x1="220" y1="158" x2="220" y2="198"/></g>
        <g fill="var(--c-green,#16a34a)"><rect x="92" y="204" width="16" height="24"/><rect x="152" y="186" width="16" height="24"/><rect x="212" y="166" width="16" height="24"/></g>
        <g stroke="var(--c-red,#dc2626)" stroke-width="1.5"><line x1="280" y1="150" x2="280" y2="196"/><line x1="340" y1="166" x2="340" y2="214"/></g>
        <g fill="var(--c-red,#dc2626)"><rect x="272" y="158" width="16" height="28"/><rect x="332" y="174" width="16" height="30"/></g>
        <g stroke="var(--c-green,#16a34a)" stroke-width="1.5"><line x1="400" y1="150" x2="400" y2="204"/><line x1="460" y1="120" x2="460" y2="170"/><line x1="520" y1="104" x2="520" y2="146"/></g>
        <g fill="var(--c-green,#16a34a)"><rect x="392" y="160" width="16" height="34"/><rect x="452" y="128" width="16" height="34"/><rect x="512" y="112" width="16" height="26"/></g>
        <rect x="384" y="144" width="32" height="66" fill="none" stroke="#d4a017" stroke-width="2" rx="6"/>
        <line x1="400" y1="144" x2="400" y2="96" stroke="#d4a017" stroke-width="1.2"/>
        <text x="270" y="90" font-size="11" font-family="sans-serif" fill="var(--c-muted,#5a6072)">ここでシグナルが出る（下げのあとの最初の上向き1本）</text>
        <text x="260" y="232" font-size="11" font-family="sans-serif" fill="var(--c-muted,#5a6072)">一時的な下げ</text>
        <line x1="300" y1="222" x2="300" y2="204" stroke="var(--c-muted,#5a6072)" stroke-width="1"/>
        <text x="320" y="294" font-size="10" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)">※ 概念を示すイメージ図です（実際の値動きではありません）</text>
      </svg>'''
exec(open('drafts/labnotes/lab-146-body.py',encoding='utf-8').read())
open('drafts/draft-signal-lab-146.html','w',encoding='utf-8').write(pre+main+post)
print({k:(r['k'],r['n'],round(r['p'],1)) for k,r in R.items()})
