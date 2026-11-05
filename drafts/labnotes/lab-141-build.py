import json,sys,re
sys.path.insert(0,'.')
import signal_lab_verify as v
data=json.load(open('signals-log.json',encoding='utf-8-sig'))
ASOF="2026-11-06T06:12:00+09:00"
data,af,_=v.apply_asof(data,v.parse_asof(ASOF),"2026-11-06")
B="2026-09-27"; S={"family":"tf","blocked":True}; N={"family":"tf","blocked":False}
C={
"fwd":("FWD：順張り・利確の手前に壁ありの勝ち回数",{**S,"fired_from":B}),
"nowall":("FWD：順張り・壁なし（対照）の勝ち回数",{**N,"fired_from":B}),
"tf":("FWD：順張り全体（対照）の勝ち回数",{"family":"tf","fired_from":B}),
"all":("FWD：全シグナルの勝ち回数",{"fired_from":B}),
"is":("IS：順張り・壁あり（登録前・参考）の勝ち回数",{**S,"fired_before":B}),
"isno":("IS：順張り・壁なし（登録前・参考）の勝ち回数",{**N,"fired_before":B}),
"h1":("FWD：壁あり・1時間足",{**S,"tf":"1h","fired_from":B}),
"h4":("FWD：壁あり・4時間足",{**S,"tf":"4h","fired_from":B}),
"idx":("FWD：壁あり・株価指数",{**S,"asset_class":"index","fired_from":B}),
"fx":("FWD：壁あり・FX",{**S,"asset_class":"fx","fired_from":B}),
"com":("FWD：壁あり・金銀原油",{**S,"asset_class":"commodity","fired_from":B}),
"btc":("FWD：壁あり・ビットコイン",{**S,"asset_class":"crypto","fired_from":B}),
"long":("FWD：壁あり・買い",{**S,"direction":"long","fired_from":B}),
"short":("FWD：壁あり・売り",{**S,"direction":"short","fired_from":B}),
"first":("FWD：壁あり・前半（〜10月16日）",{**S,"fired_from":B,"fired_before":"2026-10-17"}),
"second":("FWD：壁あり・後半（10月17日〜）",{**S,"fired_from":"2026-10-17"}),
}
R={}; claims=[]
for key,(lab,f) in C.items():
    k,n=v.compute(data,f); lo,hi=v.wilson(k,n)
    if lo<1: lo,hi=lo*100,hi*100
    R[key]=dict(k=k,n=n,p=100*k/n,lo=lo,hi=hi)
    claims.append({"label":lab,"filter":f,"k":k,"n":n})
json.dump({"article_id":"141","asof":ASOF,"hypothesis_id":"rl_tf_blocked","claims":claims},open('drafts/labnotes/lab-141-claims.json','w'),ensure_ascii=False,indent=1)
def pct(x):return f"{x:.1f}%"
def row(name,key,bold=False):
    r=R[key]; p=pct(r['p'])
    if bold: name=f"<strong>{name}</strong>"; p=f"<strong>{p}</strong>"; n=f"<strong>{r['n']:,}回</strong>"
    else: n=f"{r['n']:,}回"
    return f"          <tr><td>{name}</td><td>{r['k']:,}回</td><td>{n}</td><td>{p}</td><td>{r['lo']:.1f}%〜{r['hi']:.1f}%</td></tr>"
F=R['fwd']
html=open('guide-signal-lab-140.html',encoding='utf-8').read()
pre=html[:html.index('<main class="s-main">')]
post=html[html.index('<!-- 関連記事カード -->'):]
post=re.sub(r'<!-- series-nav:begin -->.*?<!-- series-nav:end -->\n?','',post,flags=re.S)
TITLE=f"順張りのシグナルで、利確の手前に壁があると勝ちにくい？ 前向き{F['n']}回で確かめた【研究日誌 #141】"
DESC=f"高値ブレイクなどの順張りで、利益確定の水準の手前に直近の高値（壁）があるシグナルを前向き{F['n']}回で確認。勝った割合{pct(F['p'])}、偶然のぶれを考えた勝率は{F['lo']:.1f}%〜{F['hi']:.1f}%。壁がない場合との比較も整理。研究日誌第141回。"
pre=re.sub(r'<title>.*?</title>',f'<title>{TITLE} - MarketWatch AI</title>',pre,flags=re.S)
pre=re.sub(r'(<meta name="description" content=")[^"]*',r'\g<1>'+DESC,pre)
pre=re.sub(r'(<meta name="keywords" content=")[^"]*',r'\g<1>順張り,壁,利確,高値ブレイク,シグナル研究,前向き検証,研究日誌',pre)
pre=pre.replace('guide-signal-lab-140.html','guide-signal-lab-141.html')
pre=re.sub(r'(<meta property="og:title" content=")[^"]*',r'\g<1>'+TITLE,pre)
pre=re.sub(r'(<meta property="og:description" content=")[^"]*',r'\g<1>'+DESC,pre)
pre=re.sub(r'("headline": ")[^"]*',r'\g<1>'+TITLE,pre)
pre=re.sub(r'("description": ")[^"]*',r'\g<1>'+DESC,pre)
pre=pre.replace('"datePublished": "2026-11-05"','"datePublished": "2026-11-06"').replace('"dateModified": "2026-11-05"','"dateModified": "2026-11-06"')
pre=re.sub(r'<h1>.*?</h1>',f'<h1>{TITLE}</h1>',pre)
pre=re.sub(r'<p class="meta-line">公開：[^<]*</p>','<p class="meta-line">公開：2026年11月6日　前向き期間：2026年9月27日〜　仮説登録日：2026年9月26日</p>',pre)
if 'noindex' not in pre:
    pre=pre.replace('<meta charset="UTF-8">','<meta charset="UTF-8">\n  <meta name="robots" content="noindex,nofollow">',1)
K=4.0
def bar(x,pct_,col,op,lab,sub,bold=False):
    hh=K*pct_; y=265-hh; w=' font-weight="bold"' if bold else ''
    return (f'        <rect x="{x}" y="{y:.1f}" width="60" height="{hh:.1f}" fill="{col}" opacity="{op}" rx="3"/>\n'
    f'        <text x="{x+30}" y="{y-5:.1f}" font-size="11" font-family="sans-serif" text-anchor="middle" fill="{col}" font-weight="bold">{pct_:.1f}%</text>\n'
    f'        <text x="{x+30}" y="280" font-size="10" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)"{w}>{lab}</text>\n'
    f'        <text x="{x+30}" y="291" font-size="10" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)">{sub}</text>\n')
G='var(--c-green,#16a34a)'; A='var(--c-accent,#2563eb)'; M='var(--c-muted,#5a6072)'; RD='var(--c-red,#dc2626)'
bars=(bar(85,R['all']['p'],A,.5,'全シグナル',f"{R['all']['n']:,}回")
 +bar(160,R['tf']['p'],A,.6,'順張り全体',f"{R['tf']['n']:,}回")
 +bar(235,R['nowall']['p'],A,.75,'壁なし',f"{R['nowall']['n']}回")
 +bar(310,F['p'],G,.75,'壁あり',f"{F['n']}回",True)
 +bar(385,R['first']['p'],G,.6,'壁あり前半',f"{R['first']['n']}回")
 +bar(460,R['second']['p'],G,.6,'壁あり後半',f"{R['second']['n']}回")
 +bar(535,R['is']['p'],M,.5,'登録前(壁あり)',f"{R['is']['n']}回"))
ticks=''.join(f'        <line x1="70" y1="{265-K*t:.0f}" x2="610" y2="{265-K*t:.0f}" stroke="var(--c-border,#e2e6ed)" stroke-width="0.5" stroke-dasharray="3,3"/>\n        <text x="65" y="{265-K*t+4:.0f}" font-size="10" font-family="sans-serif" fill="var(--c-muted,#999)" text-anchor="end">{t}%</text>\n' for t in (20,30,40,50))
svg1=f'''      <svg viewBox="0 0 640 310" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="前向きの勝率比較棒グラフ" style="width:100%;max-width:640px;display:block;margin:0 auto">
        <rect width="640" height="310" fill="var(--c-surface,#fff)" rx="6"/>
        <text x="320" y="22" font-size="13" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)">前向き（2026年9月27日以降）の勝率比較</text>
        <line x1="70" y1="40" x2="70" y2="265" stroke="var(--c-border,#e2e6ed)" stroke-width="1"/>
        <line x1="70" y1="265" x2="610" y2="265" stroke="var(--c-border,#e2e6ed)" stroke-width="1"/>
        <text x="65" y="269" font-size="10" font-family="sans-serif" fill="var(--c-muted,#999)" text-anchor="end">0%</text>
{ticks}        <line x1="70" y1="{265-K*43:.1f}" x2="610" y2="{265-K*43:.1f}" stroke="var(--c-warn,#d97706)" stroke-width="1.5" stroke-dasharray="5,3"/>
        <text x="615" y="{265-K*43+3:.1f}" font-size="10" font-family="sans-serif" fill="var(--c-warn,#d97706)">43%</text>
{bars}      </svg>'''
svg2='''      <svg viewBox="0 0 640 300" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="入った価格と利益確定の水準の間に直近の高値がある場面を示す概念図" style="width:100%;max-width:640px;display:block;margin:0 auto">
        <rect width="640" height="300" fill="var(--c-surface,#fff)" rx="6"/>
        <text x="320" y="20" font-size="13" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)">利益確定の水準の手前に「壁」がある場面のイメージ</text>
        <line x1="60" y1="190" x2="520" y2="190" stroke="var(--c-accent,#2563eb)" stroke-width="1.2" stroke-dasharray="4,3"/>
        <text x="526" y="194" font-size="10" font-family="sans-serif" fill="var(--c-accent,#2563eb)">入った価格</text>
        <line x1="60" y1="130" x2="520" y2="130" stroke="var(--c-warn,#d97706)" stroke-width="1.5" stroke-dasharray="6,3"/>
        <text x="526" y="134" font-size="10" font-family="sans-serif" fill="var(--c-warn,#d97706)">壁（直近の高値）</text>
        <line x1="60" y1="90" x2="520" y2="90" stroke="var(--c-green,#16a34a)" stroke-width="1.2" stroke-dasharray="4,3"/>
        <text x="526" y="94" font-size="10" font-family="sans-serif" fill="var(--c-green,#16a34a)">利益確定の水準</text>
        <g stroke="var(--c-green,#16a34a)" stroke-width="1.5"><line x1="100" y1="210" x2="100" y2="250"/><line x1="160" y1="196" x2="160" y2="238"/><line x1="220" y1="182" x2="220" y2="222"/><line x1="280" y1="170" x2="280" y2="208"/><line x1="340" y1="176" x2="340" y2="212"/><line x1="400" y1="170" x2="400" y2="204"/></g>
        <g fill="var(--c-green,#16a34a)"><rect x="92" y="218" width="16" height="24"/><rect x="152" y="204" width="16" height="26"/><rect x="212" y="190" width="16" height="24"/><rect x="272" y="178" width="16" height="22"/><rect x="332" y="184" width="16" height="22"/><rect x="392" y="178" width="16" height="20"/></g>
        <g stroke="var(--c-green,#16a34a)" stroke-width="1.5"><line x1="460" y1="150" x2="460" y2="200"/></g>
        <g fill="var(--c-green,#16a34a)"><rect x="452" y="160" width="16" height="30"/></g>
        <rect x="444" y="144" width="32" height="62" fill="none" stroke="#d4a017" stroke-width="2" rx="6"/>
        <line x1="476" y1="206" x2="500" y2="244" stroke="#d4a017" stroke-width="1.2"/>
        <text x="454" y="262" font-size="11" font-family="sans-serif" fill="var(--c-muted,#5a6072)">ここでシグナルが出る</text>
        <text x="60" y="48" font-size="11" font-family="sans-serif" fill="var(--c-muted,#5a6072)">条件：入った価格から利益確定の水準までの間に、直近の高値がある</text>
        <text x="320" y="292" font-size="10" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)">※ 概念を示すイメージ図です（実際の値動きではありません）</text>
      </svg>'''
exec(open('drafts/labnotes/lab-141-body.py',encoding='utf-8').read())
open('drafts/draft-signal-lab-141.html','w',encoding='utf-8').write(pre+main+post)
print({k:(r['k'],r['n'],round(r['p'],1)) for k,r in R.items()})
