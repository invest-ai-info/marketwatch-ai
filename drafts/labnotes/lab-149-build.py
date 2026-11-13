import json,sys,re
sys.path.insert(0,'.')
import signal_lab_verify as v
data=json.load(open('signals-log.json',encoding='utf-8-sig'))
ASOF="2026-11-14T06:11:00+09:00"
data,af,_=v.apply_asof(data,v.parse_asof(ASOF),"2026-11-14")
B="2026-07-01"; MID="2026-09-01"; S={"group":"index","direction":"short"}
C={
"fwd":("FWD：株価指数の売りの勝ち回数",{**S,"fired_from":B}),
"sall":("FWD：売り全体（対照）の勝ち回数",{"direction":"short","fired_from":B}),
"ilong":("FWD：株価指数の買い（対照）の勝ち回数",{"group":"index","direction":"long","fired_from":B}),
"iall":("FWD：株価指数の全シグナル（対照）の勝ち回数",{"group":"index","fired_from":B}),
"all":("FWD：全シグナル（対照）の勝ち回数",{"fired_from":B}),
"is":("IS：株価指数の売り（登録前・参考）の勝ち回数",{**S,"fired_before":B}),
"isall":("IS：売り全体（登録前・参考）の勝ち回数",{"direction":"short","fired_before":B}),
"h1":("FWD：株価指数の売り・1時間足",{**S,"tf":"1h","fired_from":B}),
"h4":("FWD：株価指数の売り・4時間足",{**S,"tf":"4h","fired_from":B}),
"d1":("FWD：株価指数の売り・日足",{**S,"tf":"1d","fired_from":B}),
"nk":("FWD：株価指数の売り・日経平均先物",{**S,"ticker":"NKD=F","fired_from":B}),
"sp":("FWD：株価指数の売り・S&P500先物",{**S,"ticker":"ES=F","fired_from":B}),
"nq":("FWD：株価指数の売り・ナスダック先物",{**S,"ticker":"NQ=F","fired_from":B}),
"dj":("FWD：株価指数の売り・ダウ先物",{**S,"ticker":"YM=F","fired_from":B}),
"ft":("FWD：株価指数の売り・英国の株価指数",{**S,"ticker":"^FTSE","fired_from":B}),
"first":("FWD：株価指数の売り・前半（〜8月31日）",{**S,"fired_from":B,"fired_before":MID}),
"second":("FWD：株価指数の売り・後半（9月1日〜）",{**S,"fired_from":MID}),
}
R={}; claims=[]
for key,(lab,f) in C.items():
    k,n=v.compute(data,f); lo,hi=v.wilson(k,n)
    if hi<=1: lo,hi=lo*100,hi*100
    R[key]=dict(k=k,n=n,p=100*k/n,lo=lo,hi=hi)
    claims.append({"label":lab,"filter":f,"k":k,"n":n})
json.dump({"article_id":"149","asof":ASOF,"hypothesis_id":"auto_direction-short_group-index","claims":claims},open('drafts/labnotes/lab-149-claims.json','w'),ensure_ascii=False,indent=1)
def pct(x):return f"{x:.1f}%"
def row(name,key,bold=False):
    r=R[key]; p=pct(r['p'])
    if bold: name=f"<strong>{name}</strong>"; p=f"<strong>{p}</strong>"; n=f"<strong>{r['n']:,}回</strong>"
    else: n=f"{r['n']:,}回"
    return f"          <tr><td>{name}</td><td>{r['k']:,}回</td><td>{n}</td><td>{p}</td><td>{r['lo']:.1f}%〜{r['hi']:.1f}%</td></tr>"
F=R['fwd']
html=open('drafts/draft-signal-lab-148.html',encoding='utf-8').read()
pre=html[:html.index('<main class="s-main">')]
post=html[html.index('<!-- 関連記事カード -->'):]
post=re.sub(r'<!-- series-nav:begin -->.*?<!-- series-nav:end -->\n?','',post,flags=re.S)
TITLE=f"株価指数の「売り」シグナルは勝ちやすい？ 前向き{F['n']}回で確かめた【研究日誌 #149】"
DESC=f"日経平均先物やS&P500先物など株価指数で出た売りのシグナルを、前向き{F['n']}回で確認。勝った割合{pct(F['p'])}、偶然のぶれを考えた勝率は{F['lo']:.1f}%〜{F['hi']:.1f}%。研究日誌第149回。"
pre=re.sub(r'<title>.*?</title>',f'<title>{TITLE} - MarketWatch AI</title>',pre,flags=re.S)
pre=re.sub(r'(<meta name="description" content=")[^"]*',r'\g<1>'+DESC,pre)
pre=re.sub(r'(<meta name="keywords" content=")[^"]*',r'\g<1>株価指数,売りシグナル,日経平均先物,シグナル研究,前向き検証,研究日誌',pre)
pre=pre.replace('guide-signal-lab-148.html','guide-signal-lab-149.html')
pre=re.sub(r'(<meta property="og:title" content=")[^"]*',r'\g<1>'+TITLE,pre)
pre=re.sub(r'(<meta property="og:description" content=")[^"]*',r'\g<1>'+DESC,pre)
pre=re.sub(r'("headline": ")[^"]*',r'\g<1>'+TITLE,pre)
pre=re.sub(r'("description": ")[^"]*',r'\g<1>'+DESC,pre)
pre=pre.replace('"datePublished": "2026-11-13"','"datePublished": "2026-11-14"').replace('"dateModified": "2026-11-13"','"dateModified": "2026-11-14"')
pre=re.sub(r'<h1>.*?</h1>',f'<h1>{TITLE}</h1>',pre)
pre=re.sub(r'<p class="meta-line">公開：[^<]*</p>','<p class="meta-line">公開：2026年11月14日　前向き期間：2026年7月1日〜　仮説登録日：2026年6月30日</p>',pre)
K=4.0
def bar(x,pct_,col,op,lab,sub,bold=False):
    hh=K*pct_; y=265-hh; w=' font-weight="bold"' if bold else ''
    return (f'        <rect x="{x}" y="{y:.1f}" width="60" height="{hh:.1f}" fill="{col}" opacity="{op}" rx="3"/>\n'
    f'        <text x="{x+30}" y="{y-5:.1f}" font-size="11" font-family="sans-serif" text-anchor="middle" fill="{col}" font-weight="bold">{pct_:.1f}%</text>\n'
    f'        <text x="{x+30}" y="280" font-size="10" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)"{w}>{lab}</text>\n'
    f'        <text x="{x+30}" y="291" font-size="10" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)">{sub}</text>\n')
A='var(--c-accent,#2563eb)'; M='var(--c-muted,#5a6072)'
bars=(bar(85,R['all']['p'],A,.5,'全シグナル',f"{R['all']['n']:,}回")
 +bar(160,R['sall']['p'],A,.6,'売り全体',f"{R['sall']['n']:,}回")
 +bar(235,R['ilong']['p'],A,.7,'指数の買い',f"{R['ilong']['n']:,}回")
 +bar(310,F['p'],A,1.0,'指数の売り',f"{F['n']}回",True)
 +bar(385,R['first']['p'],A,.6,'前半',f"{R['first']['n']}回")
 +bar(460,R['second']['p'],A,.6,'後半',f"{R['second']['n']}回")
 +bar(535,R['is']['p'],M,.5,'登録前',f"{R['is']['n']}回"))
ticks=''.join(f'        <line x1="70" y1="{265-K*t:.0f}" x2="610" y2="{265-K*t:.0f}" stroke="var(--c-border,#e2e6ed)" stroke-width="0.5" stroke-dasharray="3,3"/>\n        <text x="65" y="{265-K*t+4:.0f}" font-size="10" font-family="sans-serif" fill="var(--c-muted,#999)" text-anchor="end">{t}%</text>\n' for t in (20,30,40,50))
svg1=f'''      <svg viewBox="0 0 640 310" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="株価指数の売りシグナルの勝率比較棒グラフ" style="width:100%;max-width:640px;display:block;margin:0 auto">
        <rect width="640" height="310" fill="var(--c-surface,#fff)" rx="6"/>
        <text x="320" y="22" font-size="13" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)">前向き（2026年7月1日以降）と登録前の勝率比較</text>
        <line x1="70" y1="40" x2="70" y2="265" stroke="var(--c-border,#e2e6ed)" stroke-width="1"/>
        <line x1="70" y1="265" x2="610" y2="265" stroke="var(--c-border,#e2e6ed)" stroke-width="1"/>
        <text x="65" y="269" font-size="10" font-family="sans-serif" fill="var(--c-muted,#999)" text-anchor="end">0%</text>
{ticks}        <line x1="70" y1="{265-K*43:.1f}" x2="610" y2="{265-K*43:.1f}" stroke="var(--c-warn,#d97706)" stroke-width="1.5" stroke-dasharray="5,3"/>
        <text x="615" y="{265-K*43+3:.1f}" font-size="10" font-family="sans-serif" fill="var(--c-warn,#d97706)">43%</text>
{bars}      </svg>'''
svg2='''      <svg viewBox="0 0 640 340" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="株価指数で売りのシグナルが出る瞬間と、損切り・利益確定の置き場所を示す概念図" style="width:100%;max-width:640px;display:block;margin:0 auto">
        <rect width="640" height="340" fill="var(--c-surface,#fff)" rx="6"/>
        <text x="320" y="20" font-size="13" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)">売りのシグナルが出る場面のイメージ（上がったあと勢いが弱まる）</text>
        <g stroke="var(--c-green,#16a34a)" stroke-width="1.5"><line x1="100" y1="230" x2="100" y2="262"/><line x1="150" y1="212" x2="150" y2="244"/><line x1="200" y1="190" x2="200" y2="224"/><line x1="250" y1="168" x2="250" y2="202"/><line x1="300" y1="150" x2="300" y2="184"/></g>
        <g fill="var(--c-green,#16a34a)"><rect x="92" y="238" width="16" height="18"/><rect x="142" y="220" width="16" height="18"/><rect x="192" y="198" width="16" height="20"/><rect x="242" y="176" width="16" height="20"/><rect x="292" y="158" width="16" height="20"/></g>
        <g stroke="var(--c-red,#dc2626)" stroke-width="1.5"><line x1="350" y1="140" x2="350" y2="176"/><line x1="400" y1="152" x2="400" y2="190"/><line x1="450" y1="168" x2="450" y2="206"/><line x1="500" y1="186" x2="500" y2="224"/></g>
        <g fill="var(--c-red,#dc2626)"><rect x="342" y="148" width="16" height="22"/><rect x="392" y="160" width="16" height="22"/><rect x="442" y="176" width="16" height="22"/><rect x="492" y="194" width="16" height="22"/></g>
        <rect x="330" y="132" width="40" height="50" fill="none" stroke="#d4a017" stroke-width="2" rx="6"/>
        <line x1="370" y1="157" x2="540" y2="157" stroke="var(--c-muted,#5a6072)" stroke-width="1" stroke-dasharray="3,3"/>
        <text x="380" y="150" font-size="11" font-family="sans-serif" fill="var(--c-muted,#5a6072)">ここで売りのシグナル（入る場面）</text>
        <line x1="370" y1="104" x2="610" y2="104" stroke="var(--c-red,#dc2626)" stroke-width="1.5" stroke-dasharray="6,3"/>
        <text x="380" y="98" font-size="11" font-family="sans-serif" fill="var(--c-red,#dc2626)">損切りの水準（入った値段より上）</text>
        <line x1="370" y1="258" x2="610" y2="258" stroke="var(--c-green,#16a34a)" stroke-width="1.5" stroke-dasharray="6,3"/>
        <text x="380" y="252" font-size="11" font-family="sans-serif" fill="var(--c-green,#16a34a)">利益確定の水準（入った値段より下）</text>
        <text x="20" y="44" font-size="10" font-family="sans-serif" fill="var(--c-muted,#5a6072)">値段</text>
        <text x="320" y="332" font-size="10" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)">※ 概念を示すイメージ図です（実際の値動きではありません）</text>
      </svg>'''
exec(open('drafts/labnotes/lab-149-body.py',encoding='utf-8').read())
open('drafts/draft-signal-lab-149.html','w',encoding='utf-8').write(pre+main+post)
print({k:(r['k'],r['n'],round(r['p'],1)) for k,r in R.items()})
