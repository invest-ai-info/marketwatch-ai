import json,sys,re
sys.path.insert(0,'.')
import signal_lab_verify as v
data=json.load(open('signals-log.json',encoding='utf-8-sig'))
ASOF="2026-11-17T06:11:00+09:00"
data,af,_=v.apply_asof(data,v.parse_asof(ASOF),"2026-11-17")
B="2026-06-17"; MID="2026-09-01"; S={"signal":"rsi_oversold_bounce"}
C={
"fwd":("FWD：売られすぎからの反発の買いの勝ち回数",{**S,"fired_from":B}),
"lall":("FWD：買い全体（対照）の勝ち回数",{"direction":"long","fired_from":B}),
"all":("FWD：全シグナル（対照）の勝ち回数",{"fired_from":B}),
"is":("IS：売られすぎからの反発の買い（登録前・参考）の勝ち回数",{**S,"fired_before":B}),
"h1":("FWD：売られすぎ反発の買い・1時間足",{**S,"tf":"1h","fired_from":B}),
"h4":("FWD：売られすぎ反発の買い・4時間足",{**S,"tf":"4h","fired_from":B}),
"d1":("FWD：売られすぎ反発の買い・日足",{**S,"tf":"1d","fired_from":B}),
"ix":("FWD：売られすぎ反発の買い・株価指数",{**S,"group":"index","fired_from":B}),
"jf":("FWD：売られすぎ反発の買い・円クロス為替",{**S,"group":"jpy_fx","fired_from":B}),
"of":("FWD：売られすぎ反発の買い・円がからまない為替",{**S,"group":"other_fx","fired_from":B}),
"mt":("FWD：売られすぎ反発の買い・金と銀",{**S,"group":"metal","fired_from":B}),
"oi":("FWD：売られすぎ反発の買い・原油",{**S,"group":"oil","fired_from":B}),
"bt":("FWD：売られすぎ反発の買い・ビットコイン",{**S,"group":"btc","fired_from":B}),
"first":("FWD：売られすぎ反発の買い・前半（〜8月31日）",{**S,"fired_from":B,"fired_before":MID}),
"second":("FWD：売られすぎ反発の買い・後半（9月1日〜）",{**S,"fired_from":MID}),
}
R={}; claims=[]
for key,(lab,f) in C.items():
    k,n=v.compute(data,f); lo,hi=v.wilson(k,n)
    if hi<=1: lo,hi=lo*100,hi*100
    R[key]=dict(k=k,n=n,p=100*k/n,lo=lo,hi=hi)
    claims.append({"label":lab,"filter":f,"k":k,"n":n})
json.dump({"article_id":"152","asof":ASOF,"hypothesis_id":"rsi_oversold_edge","claims":claims},open('drafts/labnotes/lab-152-claims.json','w'),ensure_ascii=False,indent=1)
def pct(x):return f"{x:.1f}%"
def row(name,key,bold=False):
    r=R[key]; p=pct(r['p'])
    if bold: name=f"<strong>{name}</strong>"; p=f"<strong>{p}</strong>"; n=f"<strong>{r['n']:,}回</strong>"
    else: n=f"{r['n']:,}回"
    return f"          <tr><td>{name}</td><td>{r['k']:,}回</td><td>{n}</td><td>{p}</td><td>{r['lo']:.1f}%〜{r['hi']:.1f}%</td></tr>"
F=R['fwd']
html=open('drafts/draft-signal-lab-151.html',encoding='utf-8').read()
pre=html[:html.index('<main class="s-main">')]
post=html[html.index('<!-- 関連記事カード -->'):]
post=re.sub(r'<!-- series-nav:begin -->.*?<!-- series-nav:end -->\n?','',post,flags=re.S)
TITLE=f"売られすぎからの反発の買いは勝ちやすい？ 前向き{F['n']}回、判定まであと少し【研究日誌 #152】"
DESC=f"RSIが売られすぎの水準から戻ったときの買いを、前向き{F['n']}回で確認。勝った割合{pct(F['p'])}、偶然のぶれを考えた勝率は{F['lo']:.1f}%〜{F['hi']:.1f}%。研究日誌第152回。"
pre=re.sub(r'<title>.*?</title>',f'<title>{TITLE} - MarketWatch AI</title>',pre,flags=re.S)
pre=re.sub(r'(<meta name="description" content=")[^"]*',r'\g<1>'+DESC,pre)
pre=re.sub(r'(<meta name="keywords" content=")[^"]*',r'\g<1>RSI,売られすぎ,買いシグナル,シグナル研究,前向き検証,研究日誌',pre)
pre=pre.replace('guide-signal-lab-149.html','guide-signal-lab-152.html')
pre=re.sub(r'(<meta property="og:title" content=")[^"]*',r'\g<1>'+TITLE,pre)
pre=re.sub(r'(<meta property="og:description" content=")[^"]*',r'\g<1>'+DESC,pre)
pre=re.sub(r'("headline": ")[^"]*',r'\g<1>'+TITLE,pre)
pre=re.sub(r'("description": ")[^"]*',r'\g<1>'+DESC,pre)
pre=pre.replace('"datePublished": "2026-11-16"','"datePublished": "2026-11-17"').replace('"dateModified": "2026-11-16"','"dateModified": "2026-11-17"')
pre=re.sub(r'<h1>.*?</h1>',f'<h1>{TITLE}</h1>',pre)
pre=re.sub(r'<p class="meta-line">公開：[^<]*</p>','<p class="meta-line">公開：2026年11月17日　前向き期間：2026年6月17日〜　仮説登録日：2026年6月16日</p>',pre)
K=3.5
def bar(x,pct_,col,op,lab,sub,bold=False):
    hh=K*pct_; y=265-hh; w=' font-weight="bold"' if bold else ''
    return (f'        <rect x="{x}" y="{y:.1f}" width="60" height="{hh:.1f}" fill="{col}" opacity="{op}" rx="3"/>\n'
    f'        <text x="{x+30}" y="{y-5:.1f}" font-size="11" font-family="sans-serif" text-anchor="middle" fill="{col}" font-weight="bold">{pct_:.1f}%</text>\n'
    f'        <text x="{x+30}" y="280" font-size="10" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)"{w}>{lab}</text>\n'
    f'        <text x="{x+30}" y="291" font-size="10" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)">{sub}</text>\n')
A='var(--c-accent,#2563eb)'; M='var(--c-muted,#5a6072)'
bars=(bar(100,R['all']['p'],A,.5,'全シグナル',f"{R['all']['n']:,}回")
 +bar(185,R['lall']['p'],A,.6,'買い全体',f"{R['lall']['n']:,}回")
 +bar(270,F['p'],A,1.0,'売られすぎ反発',f"{F['n']}回",True)
 +bar(355,R['first']['p'],A,.6,'前半',f"{R['first']['n']}回")
 +bar(440,R['second']['p'],A,.6,'後半',f"{R['second']['n']}回")
 +bar(525,R['is']['p'],M,.5,'登録前',f"{R['is']['n']}回"))
ticks=''.join(f'        <line x1="70" y1="{265-K*t:.0f}" x2="610" y2="{265-K*t:.0f}" stroke="var(--c-border,#e2e6ed)" stroke-width="0.5" stroke-dasharray="3,3"/>\n        <text x="65" y="{265-K*t+4:.0f}" font-size="10" font-family="sans-serif" fill="var(--c-muted,#999)" text-anchor="end">{t}%</text>\n' for t in (20,30,40,50,60))
svg1=f'''      <svg viewBox="0 0 640 310" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="売られすぎからの反発の買いシグナルの勝率比較棒グラフ" style="width:100%;max-width:640px;display:block;margin:0 auto">
        <rect width="640" height="310" fill="var(--c-surface,#fff)" rx="6"/>
        <text x="320" y="22" font-size="13" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)">前向き（2026年6月26日以降）と登録前の勝率比較</text>
        <line x1="70" y1="40" x2="70" y2="265" stroke="var(--c-border,#e2e6ed)" stroke-width="1"/>
        <line x1="70" y1="265" x2="610" y2="265" stroke="var(--c-border,#e2e6ed)" stroke-width="1"/>
        <text x="65" y="269" font-size="10" font-family="sans-serif" fill="var(--c-muted,#999)" text-anchor="end">0%</text>
{ticks}        <line x1="70" y1="{265-K*43:.1f}" x2="610" y2="{265-K*43:.1f}" stroke="var(--c-warn,#d97706)" stroke-width="1.5" stroke-dasharray="5,3"/>
        <text x="615" y="{265-K*43+3:.1f}" font-size="10" font-family="sans-serif" fill="var(--c-warn,#d97706)">43%</text>
{bars}      </svg>'''
svg2='''      <svg viewBox="0 0 640 340" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="RSIが売られすぎの水準から戻って買いのシグナルが出る瞬間と、損切り・利益確定の置き場所を示す概念図" style="width:100%;max-width:640px;display:block;margin:0 auto">
        <rect width="640" height="340" fill="var(--c-surface,#fff)" rx="6"/>
        <text x="320" y="20" font-size="13" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)">売られすぎから反発して買いのシグナルが出る場面のイメージ</text>
        <g stroke="var(--c-red,#dc2626)" stroke-width="1.5"><line x1="80" y1="55" x2="80" y2="95"/><line x1="130" y1="75" x2="130" y2="115"/><line x1="180" y1="95" x2="180" y2="135"/><line x1="230" y1="120" x2="230" y2="160"/><line x1="280" y1="140" x2="280" y2="182"/></g>
        <g fill="var(--c-red,#dc2626)"><rect x="72" y="62" width="16" height="24"/><rect x="122" y="82" width="16" height="24"/><rect x="172" y="102" width="16" height="24"/><rect x="222" y="128" width="16" height="24"/><rect x="272" y="150" width="16" height="24"/></g>
        <g stroke="var(--c-green,#16a34a)" stroke-width="1.5"><line x1="330" y1="135" x2="330" y2="180"/><line x1="380" y1="120" x2="380" y2="160"/><line x1="430" y1="105" x2="430" y2="145"/><line x1="480" y1="95" x2="480" y2="132"/></g>
        <g fill="var(--c-green,#16a34a)"><rect x="322" y="145" width="16" height="26"/><rect x="372" y="128" width="16" height="24"/><rect x="422" y="112" width="16" height="24"/><rect x="472" y="102" width="16" height="22"/></g>
        <rect x="310" y="125" width="40" height="64" fill="none" stroke="#d4a017" stroke-width="2" rx="6"/>
        <text x="352" y="122" font-size="11" font-family="sans-serif" fill="var(--c-muted,#5a6072)">ここで買いのシグナル</text>
        <line x1="300" y1="212" x2="600" y2="212" stroke="var(--c-red,#dc2626)" stroke-width="1.5" stroke-dasharray="6,3"/>
        <text x="300" y="206" font-size="11" font-family="sans-serif" fill="var(--c-red,#dc2626)">損切りの水準（入った値段より下）</text>
        <line x1="400" y1="62" x2="620" y2="62" stroke="var(--c-green,#16a34a)" stroke-width="1.5" stroke-dasharray="6,3"/>
        <text x="408" y="56" font-size="11" font-family="sans-serif" fill="var(--c-green,#16a34a)">利益確定の水準（入った値段より上）</text>
        <line x1="60" y1="285" x2="620" y2="285" stroke="var(--c-warn,#d97706)" stroke-width="1" stroke-dasharray="4,3"/>
        <text x="62" y="281" font-size="10" font-family="sans-serif" fill="var(--c-warn,#d97706)">RSIの30の線（売られすぎの目安）</text>
        <polyline points="80,255 130,262 180,272 230,285 280,296 330,288 380,272 430,258 480,248" fill="none" stroke="var(--c-accent,#2563eb)" stroke-width="2.5"/>
        <text x="420" y="306" font-size="11" font-family="sans-serif" fill="var(--c-accent,#2563eb)">下段の線＝RSI</text>
        <text x="420" y="320" font-size="10" font-family="sans-serif" fill="var(--c-muted,#5a6072)">30を下回ったあと、上へ戻る</text>
        <text x="320" y="332" font-size="10" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)">※ 概念を示すイメージ図です（実際の値動きではありません）</text>
      </svg>'''
exec(open('drafts/labnotes/lab-152-body.py',encoding='utf-8').read())
open('drafts/draft-signal-lab-152.html','w',encoding='utf-8').write(pre+main+post)
print({k:(r['k'],r['n'],round(r['p'],1)) for k,r in R.items()})
