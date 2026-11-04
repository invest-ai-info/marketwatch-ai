import json,sys,re
sys.path.insert(0,'.')
import signal_lab_verify as v
data=json.load(open('signals-log.json',encoding='utf-8-sig'))
ASOF="2026-11-05T06:12:00+09:00"
data,af,_=v.apply_asof(data,v.parse_asof(ASOF),"2026-11-05")
B="2026-09-28"; S={"trend":"下降","reversal_long":True}
C={
"fwd":("FWD：下降トレンド中の逆張り買いの勝ち回数",{**S,"fired_from":B}),
"is":("IS：下降トレンド中の逆張り買い（登録前・参考）の勝ち回数",{**S,"fired_before":B}),
"long":("FWD：買い全体（対照）の勝ち回数",{"direction":"long","fired_from":B}),
"all":("FWD：全シグナルの勝ち回数",{"fired_from":B}),
"rev":("FWD：逆張り買い全体・トレンドは問わない（対照）",{"reversal_long":True,"fired_from":B}),
"dn":("FWD：下降トレンド中の買い全体（対照）",{"trend":"下降","direction":"long","fired_from":B}),
"h1":("FWD：下降中の逆張り買い・1時間足",{**S,"tf":"1h","fired_from":B}),
"h4":("FWD：下降中の逆張り買い・4時間足",{**S,"tf":"4h","fired_from":B}),
"d1":("FWD：下降中の逆張り買い・日足",{**S,"tf":"1d","fired_from":B}),
"idx":("FWD：下降中の逆張り買い・株価指数",{**S,"group":"index","fired_from":B}),
"jpy":("FWD：下降中の逆張り買い・円がらみFX",{**S,"group":"jpy_fx","fired_from":B}),
"ofx":("FWD：下降中の逆張り買い・円がらまないFX",{**S,"group":"other_fx","fired_from":B}),
"met":("FWD：下降中の逆張り買い・金銀",{**S,"group":"metal","fired_from":B}),
"first":("FWD：下降中の逆張り買い・前半（〜10月16日）",{**S,"fired_from":B,"fired_before":"2026-10-17"}),
"second":("FWD：下降中の逆張り買い・後半（10月17日〜）",{**S,"fired_from":"2026-10-17"}),
}
R={}; claims=[]
for key,(lab,f) in C.items():
    k,n=v.compute(data,f); lo,hi=v.wilson(k,n)
    if lo<1: lo,hi=lo*100,hi*100
    R[key]=dict(k=k,n=n,p=100*k/n,lo=lo,hi=hi)
    claims.append({"label":lab,"filter":f,"k":k,"n":n})
json.dump({"article_id":"140","asof":ASOF,"hypothesis_id":"auto_reversal_long-True_trend-下降__flip","claims":claims},open('drafts/labnotes/lab-140-claims.json','w'),ensure_ascii=False,indent=1)
def pct(x):return f"{x:.1f}%"
def row(name,key,bold=False):
    r=R[key]; p=pct(r['p'])
    if bold: name=f"<strong>{name}</strong>"; p=f"<strong>{p}</strong>"; n=f"<strong>{r['n']:,}回</strong>"
    else: n=f"{r['n']:,}回"
    return f"          <tr><td>{name}</td><td>{r['k']:,}回</td><td>{n}</td><td>{p}</td><td>{r['lo']:.1f}%〜{r['hi']:.1f}%</td></tr>"
F=R['fwd']
html=open('guide-signal-lab-139.html',encoding='utf-8').read()
pre=html[:html.index('<main class="s-main">')]
post=html[html.index('<!-- 関連記事カード -->'):]
post=re.sub(r'<!-- series-nav:begin -->.*?<!-- series-nav:end -->\n?','',post,flags=re.S)
TITLE=f"下降トレンド中の逆張り買いは、前向き{F['n']}回でも勝ちやすい？ 登録前の好成績は続かなかった【研究日誌 #140】"
DESC=f"下がり続けている最中に、反発をねらって買うシグナルを前向き{F['n']}回で確認。勝った割合{pct(F['p'])}、偶然のぶれを考えた勝率は{F['lo']:.1f}%〜{F['hi']:.1f}%。登録前の好成績が続いたかを整理。研究日誌第140回。"
pre=re.sub(r'<title>.*?</title>',f'<title>{TITLE} - MarketWatch AI</title>',pre,flags=re.S)
pre=re.sub(r'(<meta name="description" content=")[^"]*',r'\g<1>'+DESC,pre)
pre=re.sub(r'(<meta name="keywords" content=")[^"]*',r'\g<1>下降トレンド,逆張り,反発,シグナル研究,前向き検証,研究日誌',pre)
pre=pre.replace('guide-signal-lab-139.html','guide-signal-lab-140.html')
pre=re.sub(r'(<meta property="og:title" content=")[^"]*',r'\g<1>'+TITLE,pre)
pre=re.sub(r'(<meta property="og:description" content=")[^"]*',r'\g<1>'+DESC,pre)
pre=re.sub(r'("headline": ")[^"]*',r'\g<1>'+TITLE,pre)
pre=re.sub(r'("description": ")[^"]*',r'\g<1>'+DESC,pre)
pre=pre.replace('"datePublished": "2026-11-04"','"datePublished": "2026-11-05"').replace('"dateModified": "2026-11-04"','"dateModified": "2026-11-05"')
pre=re.sub(r'<h1>.*?</h1>',f'<h1>{TITLE}</h1>',pre)
pre=re.sub(r'<p class="meta-line">公開：[^<]*</p>','<p class="meta-line">公開：2026年11月5日　前向き期間：2026年9月28日〜　仮説登録日：2026年9月27日</p>',pre)
if 'noindex' not in pre:
    pre=pre.replace('<meta charset="UTF-8">','<meta charset="UTF-8">\n  <meta name="robots" content="noindex,nofollow">',1)
K=4.0
def bar(x,pct_,col,op,lab,sub,bold=False):
    hh=K*pct_; y=265-hh; w=' font-weight="bold"' if bold else ''
    return (f'        <rect x="{x}" y="{y:.1f}" width="70" height="{hh:.1f}" fill="{col}" opacity="{op}" rx="3"/>\n'
    f'        <text x="{x+35}" y="{y-5:.1f}" font-size="11" font-family="sans-serif" text-anchor="middle" fill="{col}" font-weight="bold">{pct_:.1f}%</text>\n'
    f'        <text x="{x+35}" y="280" font-size="10" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)"{w}>{lab}</text>\n'
    f'        <text x="{x+35}" y="291" font-size="10" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)">{sub}</text>\n')
G='var(--c-green,#16a34a)'; A='var(--c-accent,#2563eb)'; M='var(--c-muted,#5a6072)'; RD='var(--c-red,#dc2626)'
bars=(bar(80,R['all']['p'],A,.5,'全シグナル',f"{R['all']['n']:,}回")
 +bar(170,R['long']['p'],A,.6,'買い全体',f"{R['long']['n']:,}回")
 +bar(260,F['p'],G,.75,'下降中の逆張り買い',f"{F['n']}回",True)
 +bar(350,R['first']['p'],G,.6,'前半の買い',f"{R['first']['n']}回")
 +bar(440,R['second']['p'],RD,.6,'後半の買い',f"{R['second']['n']}回")
 +bar(530,R['is']['p'],M,.5,'登録前（参考）',f"{R['is']['n']}回"))
ticks=''.join(f'        <line x1="70" y1="{265-K*t:.0f}" x2="610" y2="{265-K*t:.0f}" stroke="var(--c-border,#e2e6ed)" stroke-width="0.5" stroke-dasharray="3,3"/>\n        <text x="65" y="{265-K*t+4:.0f}" font-size="10" font-family="sans-serif" fill="var(--c-muted,#999)" text-anchor="end">{t}%</text>\n' for t in (20,30,40,50))
svg1=f'''      <svg viewBox="0 0 640 310" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="前向きの勝率比較棒グラフ" style="width:100%;max-width:640px;display:block;margin:0 auto">
        <rect width="640" height="310" fill="var(--c-surface,#fff)" rx="6"/>
        <text x="320" y="22" font-size="13" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)">前向き（2026年9月28日以降）の勝率比較</text>
        <line x1="70" y1="40" x2="70" y2="265" stroke="var(--c-border,#e2e6ed)" stroke-width="1"/>
        <line x1="70" y1="265" x2="610" y2="265" stroke="var(--c-border,#e2e6ed)" stroke-width="1"/>
        <text x="65" y="269" font-size="10" font-family="sans-serif" fill="var(--c-muted,#999)" text-anchor="end">0%</text>
{ticks}        <line x1="70" y1="{265-K*43:.1f}" x2="610" y2="{265-K*43:.1f}" stroke="var(--c-warn,#d97706)" stroke-width="1.5" stroke-dasharray="5,3"/>
        <text x="615" y="{265-K*43+3:.1f}" font-size="10" font-family="sans-serif" fill="var(--c-warn,#d97706)">43%</text>
{bars}      </svg>'''
svg2='''      <svg viewBox="0 0 640 300" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="下がり続ける流れの中で反発の足が出る瞬間を示す概念図" style="width:100%;max-width:640px;display:block;margin:0 auto">
        <rect width="640" height="300" fill="var(--c-surface,#fff)" rx="6"/>
        <text x="320" y="20" font-size="13" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)">下がり続ける流れの中で、反発の足が出る瞬間のイメージ</text>
        <polyline points="60,70 160,92 260,118 360,144 460,168 560,188" fill="none" stroke="var(--c-muted,#5a6072)" stroke-width="2" stroke-dasharray="6,3"/>
        <text x="566" y="206" font-size="10" font-family="sans-serif" fill="var(--c-muted,#5a6072)">長い線</text>
        <polyline points="60,92 160,118 260,146 360,172 460,198 560,220" fill="none" stroke="var(--c-accent,#2563eb)" stroke-width="2"/>
        <text x="566" y="236" font-size="10" font-family="sans-serif" fill="var(--c-accent,#2563eb)">短い線</text>
        <g stroke="var(--c-red,#dc2626)" stroke-width="1.5"><line x1="110" y1="90" x2="110" y2="130"/><line x1="170" y1="112" x2="170" y2="152"/><line x1="230" y1="138" x2="230" y2="176"/><line x1="290" y1="160" x2="290" y2="198"/><line x1="350" y1="184" x2="350" y2="222"/></g>
        <g fill="var(--c-red,#dc2626)"><rect x="102" y="98" width="16" height="22"/><rect x="162" y="120" width="16" height="22"/><rect x="222" y="146" width="16" height="20"/><rect x="282" y="168" width="16" height="20"/><rect x="342" y="192" width="16" height="20"/></g>
        <g stroke="var(--c-green,#16a34a)" stroke-width="1.5"><line x1="410" y1="196" x2="410" y2="244"/></g>
        <g fill="var(--c-green,#16a34a)"><rect x="402" y="204" width="16" height="22"/></g>
        <rect x="394" y="190" width="32" height="60" fill="none" stroke="#d4a017" stroke-width="2" rx="6"/>
        <line x1="426" y1="250" x2="470" y2="268" stroke="#d4a017" stroke-width="1.2"/>
        <text x="474" y="272" font-size="11" font-family="sans-serif" fill="var(--c-muted,#5a6072)">ここでシグナルが出る</text>
        <text x="60" y="48" font-size="11" font-family="sans-serif" fill="var(--c-muted,#5a6072)">条件：下がる流れの中で、下ひげの長い反発の足が出る</text>
        <text x="320" y="292" font-size="10" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)">※ 概念を示すイメージ図です（実際の値動きではありません）</text>
      </svg>'''
exec(open('drafts/labnotes/lab-140-body.py',encoding='utf-8').read())
open('drafts/draft-signal-lab-140.html','w',encoding='utf-8').write(pre+main+post)
print({k:(r['k'],r['n'],round(r['p'],1)) for k,r in R.items()})
