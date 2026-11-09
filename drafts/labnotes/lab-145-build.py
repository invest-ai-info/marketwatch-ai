import json,sys,re
sys.path.insert(0,'.')
import signal_lab_verify as v
data=json.load(open('signals-log.json',encoding='utf-8-sig'))
ASOF="2026-11-10T06:12:00+09:00"
data,af,_=v.apply_asof(data,v.parse_asof(ASOF),"2026-11-10")
B="2026-09-28"; S={"signal":"rsi_oversold_bounce","tf":"4h"}; MID="2026-10-20"
C={
"fwd":("FWD：売られすぎ反発・4時間足の勝ち回数",{**S,"fired_from":B}),
"long4":("FWD：4時間足の買い全体（対照）の勝ち回数",{"tf":"4h","direction":"long","fired_from":B}),
"all4":("FWD：4時間足の全シグナル（対照）の勝ち回数",{"tf":"4h","fired_from":B}),
"is":("IS：売られすぎ反発・4時間足（登録前・参考）の勝ち回数",{**S,"fired_before":B}),
"islong4":("IS：4時間足の買い全体（登録前・参考）の勝ち回数",{"tf":"4h","direction":"long","fired_before":B}),
"idx":("FWD：売られすぎ反発・4時間足・株価指数",{**S,"group":"index","fired_from":B}),
"jpy":("FWD：売られすぎ反発・4時間足・円がらみFX",{**S,"group":"jpy_fx","fired_from":B}),
"ofx":("FWD：売られすぎ反発・4時間足・円がらまないFX",{**S,"group":"other_fx","fired_from":B}),
"met":("FWD：売られすぎ反発・4時間足・金銀",{**S,"group":"metal","fired_from":B}),
"btc":("FWD：売られすぎ反発・4時間足・ビットコイン",{**S,"group":"btc","fired_from":B}),
"oil":("FWD：売られすぎ反発・4時間足・原油",{**S,"group":"oil","fired_from":B}),
"first":("FWD：売られすぎ反発・4時間足・前半（〜10月19日）",{**S,"fired_from":B,"fired_before":MID}),
"second":("FWD：売られすぎ反発・4時間足・後半（10月20日〜）",{**S,"fired_from":MID}),
}
R={}; claims=[]
for key,(lab,f) in C.items():
    k,n=v.compute(data,f); lo,hi=v.wilson(k,n)
    if lo<1: lo,hi=lo*100,hi*100
    R[key]=dict(k=k,n=n,p=100*k/n,lo=lo,hi=hi)
    claims.append({"label":lab,"filter":f,"k":k,"n":n})
json.dump({"article_id":"145","asof":ASOF,"hypothesis_id":"rsi_oversold_4h","claims":claims},open('drafts/labnotes/lab-145-claims.json','w'),ensure_ascii=False,indent=1)
def pct(x):return f"{x:.1f}%"
def row(name,key,bold=False):
    r=R[key]; p=pct(r['p'])
    if bold: name=f"<strong>{name}</strong>"; p=f"<strong>{p}</strong>"; n=f"<strong>{r['n']:,}回</strong>"
    else: n=f"{r['n']:,}回"
    return f"          <tr><td>{name}</td><td>{r['k']:,}回</td><td>{n}</td><td>{p}</td><td>{r['lo']:.1f}%〜{r['hi']:.1f}%</td></tr>"
F=R['fwd']
html=open('drafts/draft-signal-lab-144.html',encoding='utf-8').read()
pre=html[:html.index('<main class="s-main">')]
post=html[html.index('<!-- 関連記事カード -->'):]
post=re.sub(r'<!-- series-nav:begin -->.*?<!-- series-nav:end -->\n?','',post,flags=re.S)
TITLE=f"売られすぎからの反発の買い（4時間足）は、前向き{F['n']}回でも勝ちやすい？ 登録前の高さは小さくなった【研究日誌 #145】"
DESC=f"RSI（相対力指数）が売られすぎから戻る場面の買いのうち、4時間足だけを前向き{F['n']}回で確認。勝った割合{pct(F['p'])}、偶然のぶれを考えた勝率は{F['lo']:.1f}%〜{F['hi']:.1f}%。登録前との比較も整理。研究日誌第145回。"
pre=re.sub(r'<title>.*?</title>',f'<title>{TITLE} - MarketWatch AI</title>',pre,flags=re.S)
pre=re.sub(r'(<meta name="description" content=")[^"]*',r'\g<1>'+DESC,pre)
pre=re.sub(r'(<meta name="keywords" content=")[^"]*',r'\g<1>RSI,売られすぎ,4時間足,シグナル研究,前向き検証,研究日誌',pre)
pre=pre.replace('guide-signal-lab-144.html','guide-signal-lab-145.html')
pre=re.sub(r'(<meta property="og:title" content=")[^"]*',r'\g<1>'+TITLE,pre)
pre=re.sub(r'(<meta property="og:description" content=")[^"]*',r'\g<1>'+DESC,pre)
pre=re.sub(r'("headline": ")[^"]*',r'\g<1>'+TITLE,pre)
pre=re.sub(r'("description": ")[^"]*',r'\g<1>'+DESC,pre)
pre=pre.replace('"datePublished": "2026-11-09"','"datePublished": "2026-11-10"').replace('"dateModified": "2026-11-09"','"dateModified": "2026-11-10"')
pre=re.sub(r'<h1>.*?</h1>',f'<h1>{TITLE}</h1>',pre)
pre=re.sub(r'<p class="meta-line">公開：[^<]*</p>','<p class="meta-line">公開：2026年11月10日　前向き期間：2026年9月28日〜　仮説登録日：2026年9月27日</p>',pre)
if 'noindex' not in pre:
    pre=pre.replace('<meta charset="UTF-8">','<meta charset="UTF-8">\n  <meta name="robots" content="noindex,nofollow">',1)
K=4.0
def bar(x,pct_,col,op,lab,sub,bold=False):
    hh=K*pct_; y=265-hh; w=' font-weight="bold"' if bold else ''
    return (f'        <rect x="{x}" y="{y:.1f}" width="60" height="{hh:.1f}" fill="{col}" opacity="{op}" rx="3"/>\n'
    f'        <text x="{x+30}" y="{y-5:.1f}" font-size="11" font-family="sans-serif" text-anchor="middle" fill="{col}" font-weight="bold">{pct_:.1f}%</text>\n'
    f'        <text x="{x+30}" y="280" font-size="10" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)"{w}>{lab}</text>\n'
    f'        <text x="{x+30}" y="291" font-size="10" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)">{sub}</text>\n')
G='var(--c-green,#16a34a)'; A='var(--c-accent,#2563eb)'; M='var(--c-muted,#5a6072)'
bars=(bar(85,R['all4']['p'],A,.5,'4時間足全体',f"{R['all4']['n']:,}回")
 +bar(160,R['long4']['p'],A,.6,'4時間足買い',f"{R['long4']['n']:,}回")
 +bar(235,F['p'],G,.75,'売られすぎ反発',f"{F['n']}回",True)
 +bar(310,R['first']['p'],G,.6,'前半',f"{R['first']['n']}回")
 +bar(385,R['second']['p'],G,.6,'後半',f"{R['second']['n']}回")
 +bar(460,R['is']['p'],M,.5,'登録前',f"{R['is']['n']}回")
 +bar(535,R['islong4']['p'],M,.4,'登録前(買い)',f"{R['islong4']['n']:,}回"))
ticks=''.join(f'        <line x1="70" y1="{265-K*t:.0f}" x2="610" y2="{265-K*t:.0f}" stroke="var(--c-border,#e2e6ed)" stroke-width="0.5" stroke-dasharray="3,3"/>\n        <text x="65" y="{265-K*t+4:.0f}" font-size="10" font-family="sans-serif" fill="var(--c-muted,#999)" text-anchor="end">{t}%</text>\n' for t in (20,30,40,50))
svg1=f'''      <svg viewBox="0 0 640 310" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="4時間足の売られすぎ反発の勝率比較棒グラフ" style="width:100%;max-width:640px;display:block;margin:0 auto">
        <rect width="640" height="310" fill="var(--c-surface,#fff)" rx="6"/>
        <text x="320" y="22" font-size="13" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)">前向き（2026年9月28日以降）と登録前の勝率比較</text>
        <line x1="70" y1="40" x2="70" y2="265" stroke="var(--c-border,#e2e6ed)" stroke-width="1"/>
        <line x1="70" y1="265" x2="610" y2="265" stroke="var(--c-border,#e2e6ed)" stroke-width="1"/>
        <text x="65" y="269" font-size="10" font-family="sans-serif" fill="var(--c-muted,#999)" text-anchor="end">0%</text>
{ticks}        <line x1="70" y1="{265-K*43:.1f}" x2="610" y2="{265-K*43:.1f}" stroke="var(--c-warn,#d97706)" stroke-width="1.5" stroke-dasharray="5,3"/>
        <text x="615" y="{265-K*43+3:.1f}" font-size="10" font-family="sans-serif" fill="var(--c-warn,#d97706)">43%</text>
{bars}      </svg>'''
svg2='''      <svg viewBox="0 0 640 300" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="売られすぎからの反発シグナルが出る瞬間を示す概念図" style="width:100%;max-width:640px;display:block;margin:0 auto">
        <rect width="640" height="300" fill="var(--c-surface,#fff)" rx="6"/>
        <text x="320" y="20" font-size="13" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)">シグナルが出る瞬間のイメージ（ローソク足とRSI）</text>
        <text x="20" y="42" font-size="10" font-family="sans-serif" fill="var(--c-muted,#5a6072)">値段</text>
        <line x1="60" y1="170" x2="600" y2="170" stroke="var(--c-border,#e2e6ed)" stroke-width="1"/>
        <g stroke="var(--c-red,#dc2626)" stroke-width="1.5"><line x1="100" y1="50" x2="100" y2="90"/><line x1="160" y1="68" x2="160" y2="108"/><line x1="220" y1="86" x2="220" y2="126"/><line x1="280" y1="104" x2="280" y2="148"/></g>
        <g fill="var(--c-red,#dc2626)"><rect x="92" y="56" width="16" height="26"/><rect x="152" y="74" width="16" height="26"/><rect x="212" y="92" width="16" height="26"/><rect x="272" y="110" width="16" height="30"/></g>
        <g stroke="var(--c-green,#16a34a)" stroke-width="1.5"><line x1="340" y1="112" x2="340" y2="160"/><line x1="400" y1="104" x2="400" y2="140"/><line x1="460" y1="92" x2="460" y2="126"/></g>
        <g fill="var(--c-green,#16a34a)"><rect x="332" y="124" width="16" height="26"/><rect x="392" y="112" width="16" height="22"/><rect x="452" y="100" width="16" height="20"/></g>
        <rect x="324" y="106" width="32" height="60" fill="none" stroke="#d4a017" stroke-width="2" rx="6"/>
        <line x1="340" y1="106" x2="340" y2="46" stroke="#d4a017" stroke-width="1.2"/>
        <text x="300" y="40" font-size="11" font-family="sans-serif" fill="var(--c-muted,#5a6072)">ここでシグナルが出る（上向きの最初の1本）</text>
        <text x="20" y="196" font-size="10" font-family="sans-serif" fill="var(--c-muted,#5a6072)">RSI</text>
        <line x1="60" y1="260" x2="600" y2="260" stroke="var(--c-border,#e2e6ed)" stroke-width="1"/>
        <line x1="60" y1="236" x2="600" y2="236" stroke="var(--c-warn,#d97706)" stroke-width="1" stroke-dasharray="5,3"/>
        <text x="604" y="240" font-size="10" font-family="sans-serif" fill="var(--c-warn,#d97706)">30</text>
        <polyline points="100,200 160,214 220,226 280,243 340,240 400,230 460,220" fill="none" stroke="var(--c-accent,#2563eb)" stroke-width="2"/>
        <circle cx="280" cy="243" r="4" fill="var(--c-accent,#2563eb)"/>
        <text x="150" y="278" font-size="11" font-family="sans-serif" fill="var(--c-muted,#5a6072)">1本前：RSIが30を下回る（売られすぎ）</text>
        <circle cx="340" cy="240" r="4" fill="#d4a017"/>
        <text x="352" y="256" font-size="11" font-family="sans-serif" fill="var(--c-muted,#5a6072)">今の1本：RSIが前より上がる</text>
        <text x="320" y="294" font-size="10" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)">※ 概念を示すイメージ図です（実際の値動きではありません）</text>
      </svg>'''
exec(open('drafts/labnotes/lab-145-body.py',encoding='utf-8').read())
open('drafts/draft-signal-lab-145.html','w',encoding='utf-8').write(pre+main+post)
print({k:(r['k'],r['n'],round(r['p'],1)) for k,r in R.items()})
