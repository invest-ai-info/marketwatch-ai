import json,sys,re
sys.path.insert(0,'.')
import signal_lab_verify as v
data=json.load(open('signals-log.json',encoding='utf-8-sig'))
ASOF="2026-11-16T06:11:00+09:00"
data,af,_=v.apply_asof(data,v.parse_asof(ASOF),"2026-11-16")
B="2026-06-26"; MID="2026-09-01"; S={"signal":"ma_dead"}
C={
"fwd":("FWD：移動平均のデッドクロスの売りの勝ち回数",{**S,"fired_from":B}),
"sall":("FWD：売り全体（対照）の勝ち回数",{"direction":"short","fired_from":B}),
"all":("FWD：全シグナル（対照）の勝ち回数",{"fired_from":B}),
"is":("IS：デッドクロスの売り（登録前・参考）の勝ち回数",{**S,"fired_before":B}),
"isall":("IS：全シグナル（登録前・参考）の勝ち回数",{"fired_before":B}),
"h1":("FWD：デッドクロスの売り・1時間足",{**S,"tf":"1h","fired_from":B}),
"h4":("FWD：デッドクロスの売り・4時間足",{**S,"tf":"4h","fired_from":B}),
"d1":("FWD：デッドクロスの売り・日足",{**S,"tf":"1d","fired_from":B}),
"ix":("FWD：デッドクロスの売り・株価指数",{**S,"group":"index","fired_from":B}),
"jf":("FWD：デッドクロスの売り・円クロス為替",{**S,"group":"jpy_fx","fired_from":B}),
"of":("FWD：デッドクロスの売り・円がからまない為替",{**S,"group":"other_fx","fired_from":B}),
"mt":("FWD：デッドクロスの売り・金と銀",{**S,"group":"metal","fired_from":B}),
"oi":("FWD：デッドクロスの売り・原油",{**S,"group":"oil","fired_from":B}),
"bt":("FWD：デッドクロスの売り・ビットコイン",{**S,"group":"btc","fired_from":B}),
"first":("FWD：デッドクロスの売り・前半（〜8月31日）",{**S,"fired_from":B,"fired_before":MID}),
"second":("FWD：デッドクロスの売り・後半（9月1日〜）",{**S,"fired_from":MID}),
}
R={}; claims=[]
for key,(lab,f) in C.items():
    k,n=v.compute(data,f); lo,hi=v.wilson(k,n)
    if hi<=1: lo,hi=lo*100,hi*100
    R[key]=dict(k=k,n=n,p=100*k/n,lo=lo,hi=hi)
    claims.append({"label":lab,"filter":f,"k":k,"n":n})
json.dump({"article_id":"151","asof":ASOF,"hypothesis_id":"auto_signal-ma_dead","claims":claims},open('drafts/labnotes/lab-151-claims.json','w'),ensure_ascii=False,indent=1)
def pct(x):return f"{x:.1f}%"
def row(name,key,bold=False):
    r=R[key]; p=pct(r['p'])
    if bold: name=f"<strong>{name}</strong>"; p=f"<strong>{p}</strong>"; n=f"<strong>{r['n']:,}回</strong>"
    else: n=f"{r['n']:,}回"
    return f"          <tr><td>{name}</td><td>{r['k']:,}回</td><td>{n}</td><td>{p}</td><td>{r['lo']:.1f}%〜{r['hi']:.1f}%</td></tr>"
F=R['fwd']
html=open('drafts/draft-signal-lab-149.html',encoding='utf-8').read()
pre=html[:html.index('<main class="s-main">')]
post=html[html.index('<!-- 関連記事カード -->'):]
post=re.sub(r'<!-- series-nav:begin -->.*?<!-- series-nav:end -->\n?','',post,flags=re.S)
TITLE=f"移動平均線のデッドクロスの「売り」は勝ちやすい？ 前向き{F['n']}回で確かめた【研究日誌 #151】"
DESC=f"短い期間の移動平均線が長い期間の線を下へ抜けるデッドクロスの売りを、前向き{F['n']}回で確認。勝った割合{pct(F['p'])}、偶然のぶれを考えた勝率は{F['lo']:.1f}%〜{F['hi']:.1f}%。研究日誌第151回。"
pre=re.sub(r'<title>.*?</title>',f'<title>{TITLE} - MarketWatch AI</title>',pre,flags=re.S)
pre=re.sub(r'(<meta name="description" content=")[^"]*',r'\g<1>'+DESC,pre)
pre=re.sub(r'(<meta name="keywords" content=")[^"]*',r'\g<1>移動平均線,デッドクロス,売りシグナル,シグナル研究,前向き検証,研究日誌',pre)
pre=pre.replace('guide-signal-lab-149.html','guide-signal-lab-151.html')
pre=re.sub(r'(<meta property="og:title" content=")[^"]*',r'\g<1>'+TITLE,pre)
pre=re.sub(r'(<meta property="og:description" content=")[^"]*',r'\g<1>'+DESC,pre)
pre=re.sub(r'("headline": ")[^"]*',r'\g<1>'+TITLE,pre)
pre=re.sub(r'("description": ")[^"]*',r'\g<1>'+DESC,pre)
pre=pre.replace('"datePublished": "2026-11-14"','"datePublished": "2026-11-16"').replace('"dateModified": "2026-11-14"','"dateModified": "2026-11-16"')
pre=re.sub(r'<h1>.*?</h1>',f'<h1>{TITLE}</h1>',pre)
pre=re.sub(r'<p class="meta-line">公開：[^<]*</p>','<p class="meta-line">公開：2026年11月16日　前向き期間：2026年6月26日〜　仮説登録日：2026年6月25日</p>',pre)
K=3.5
def bar(x,pct_,col,op,lab,sub,bold=False):
    hh=K*pct_; y=265-hh; w=' font-weight="bold"' if bold else ''
    return (f'        <rect x="{x}" y="{y:.1f}" width="60" height="{hh:.1f}" fill="{col}" opacity="{op}" rx="3"/>\n'
    f'        <text x="{x+30}" y="{y-5:.1f}" font-size="11" font-family="sans-serif" text-anchor="middle" fill="{col}" font-weight="bold">{pct_:.1f}%</text>\n'
    f'        <text x="{x+30}" y="280" font-size="10" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)"{w}>{lab}</text>\n'
    f'        <text x="{x+30}" y="291" font-size="10" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)">{sub}</text>\n')
A='var(--c-accent,#2563eb)'; M='var(--c-muted,#5a6072)'
bars=(bar(100,R['all']['p'],A,.5,'全シグナル',f"{R['all']['n']:,}回")
 +bar(185,R['sall']['p'],A,.6,'売り全体',f"{R['sall']['n']:,}回")
 +bar(270,F['p'],A,1.0,'デッドクロス',f"{F['n']}回",True)
 +bar(355,R['first']['p'],A,.6,'前半',f"{R['first']['n']}回")
 +bar(440,R['second']['p'],A,.6,'後半',f"{R['second']['n']}回")
 +bar(525,R['is']['p'],M,.5,'登録前',f"{R['is']['n']}回"))
ticks=''.join(f'        <line x1="70" y1="{265-K*t:.0f}" x2="610" y2="{265-K*t:.0f}" stroke="var(--c-border,#e2e6ed)" stroke-width="0.5" stroke-dasharray="3,3"/>\n        <text x="65" y="{265-K*t+4:.0f}" font-size="10" font-family="sans-serif" fill="var(--c-muted,#999)" text-anchor="end">{t}%</text>\n' for t in (20,30,40,50,60))
svg1=f'''      <svg viewBox="0 0 640 310" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="移動平均線のデッドクロスの売りシグナルの勝率比較棒グラフ" style="width:100%;max-width:640px;display:block;margin:0 auto">
        <rect width="640" height="310" fill="var(--c-surface,#fff)" rx="6"/>
        <text x="320" y="22" font-size="13" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)">前向き（2026年6月26日以降）と登録前の勝率比較</text>
        <line x1="70" y1="40" x2="70" y2="265" stroke="var(--c-border,#e2e6ed)" stroke-width="1"/>
        <line x1="70" y1="265" x2="610" y2="265" stroke="var(--c-border,#e2e6ed)" stroke-width="1"/>
        <text x="65" y="269" font-size="10" font-family="sans-serif" fill="var(--c-muted,#999)" text-anchor="end">0%</text>
{ticks}        <line x1="70" y1="{265-K*43:.1f}" x2="610" y2="{265-K*43:.1f}" stroke="var(--c-warn,#d97706)" stroke-width="1.5" stroke-dasharray="5,3"/>
        <text x="615" y="{265-K*43+3:.1f}" font-size="10" font-family="sans-serif" fill="var(--c-warn,#d97706)">43%</text>
{bars}      </svg>'''
svg2='''      <svg viewBox="0 0 640 340" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="移動平均線のデッドクロスで売りのシグナルが出る瞬間と、損切り・利益確定の置き場所を示す概念図" style="width:100%;max-width:640px;display:block;margin:0 auto">
        <rect width="640" height="340" fill="var(--c-surface,#fff)" rx="6"/>
        <text x="320" y="20" font-size="13" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)">デッドクロスで売りのシグナルが出る場面のイメージ</text>
        <polyline points="60,190 150,170 240,150 300,140 350,150 400,175 450,205 500,230" fill="none" stroke="var(--c-accent,#2563eb)" stroke-width="2.5"/>
        <polyline points="60,215 150,200 240,180 300,160 350,152 400,150 450,160 500,172" fill="none" stroke="var(--c-muted,#5a6072)" stroke-width="1.5"/>
        <g stroke="var(--c-green,#16a34a)" stroke-width="1.5"><line x1="100" y1="165" x2="100" y2="195"/><line x1="170" y1="150" x2="170" y2="180"/><line x1="240" y1="130" x2="240" y2="160"/><line x1="300" y1="118" x2="300" y2="150"/></g>
        <g fill="var(--c-green,#16a34a)"><rect x="92" y="172" width="16" height="16"/><rect x="162" y="157" width="16" height="16"/><rect x="232" y="138" width="16" height="16"/><rect x="292" y="126" width="16" height="16"/></g>
        <g stroke="var(--c-red,#dc2626)" stroke-width="1.5"><line x1="360" y1="130" x2="360" y2="168"/><line x1="410" y1="155" x2="410" y2="195"/><line x1="460" y1="185" x2="460" y2="225"/><line x1="510" y1="208" x2="510" y2="248"/></g>
        <g fill="var(--c-red,#dc2626)"><rect x="352" y="138" width="16" height="22"/><rect x="402" y="164" width="16" height="22"/><rect x="452" y="194" width="16" height="22"/><rect x="502" y="216" width="16" height="22"/></g>
        <rect x="340" y="120" width="44" height="64" fill="none" stroke="#d4a017" stroke-width="2" rx="6"/>
        <line x1="384" y1="150" x2="520" y2="132" stroke="var(--c-muted,#5a6072)" stroke-width="1" stroke-dasharray="3,3"/>
        <text x="390" y="112" font-size="11" font-family="sans-serif" fill="var(--c-muted,#5a6072)">ここで売りのシグナル</text>
        <text x="390" y="126" font-size="10" font-family="sans-serif" fill="var(--c-muted,#5a6072)">（太線が細線を下へ抜ける）</text>
        <line x1="370" y1="75" x2="620" y2="75" stroke="var(--c-red,#dc2626)" stroke-width="1.5" stroke-dasharray="6,3"/>
        <text x="380" y="69" font-size="11" font-family="sans-serif" fill="var(--c-red,#dc2626)">損切りの水準（入った値段より上）</text>
        <line x1="370" y1="285" x2="620" y2="285" stroke="var(--c-green,#16a34a)" stroke-width="1.5" stroke-dasharray="6,3"/>
        <text x="380" y="279" font-size="11" font-family="sans-serif" fill="var(--c-green,#16a34a)">利益確定の水準（入った値段より下）</text>
        <text x="40" y="262" font-size="11" font-family="sans-serif" fill="var(--c-accent,#2563eb)">太線＝短い期間の移動平均線</text>
        <text x="40" y="278" font-size="11" font-family="sans-serif" fill="var(--c-muted,#5a6072)">細線＝長い期間の移動平均線</text>
        <text x="320" y="332" font-size="10" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)">※ 概念を示すイメージ図です（実際の値動きではありません）</text>
      </svg>'''
exec(open('drafts/labnotes/lab-151-body.py',encoding='utf-8').read())
open('drafts/draft-signal-lab-151.html','w',encoding='utf-8').write(pre+main+post)
print({k:(r['k'],r['n'],round(r['p'],1)) for k,r in R.items()})
