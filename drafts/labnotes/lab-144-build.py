import json,sys,re
sys.path.insert(0,'.')
import signal_lab_verify as v
data=json.load(open('signals-log.json',encoding='utf-8-sig'))
ASOF="2026-11-09T06:12:00+09:00"
data,af,_=v.apply_asof(data,v.parse_asof(ASOF),"2026-11-09")
B="2026-06-23"; S={"signal":"low_break"}; MID="2026-09-16"
C={
"fwd":("FWD：安値ブレイクの売りの勝ち回数",{**S,"fired_from":B}),
"short":("FWD：売りのシグナル全体（対照）の勝ち回数",{"direction":"short","fired_from":B}),
"all":("FWD：全シグナルの勝ち回数",{"fired_from":B}),
"is":("IS：安値ブレイク（登録前・参考）の勝ち回数",{**S,"fired_before":B}),
"isshort":("IS：売りのシグナル全体（登録前・参考）の勝ち回数",{"direction":"short","fired_before":B}),
"h1":("FWD：安値ブレイク・1時間足",{**S,"tf":"1h","fired_from":B}),
"h4":("FWD：安値ブレイク・4時間足",{**S,"tf":"4h","fired_from":B}),
"idx":("FWD：安値ブレイク・株価指数",{**S,"asset_class":"index","fired_from":B}),
"fx":("FWD：安値ブレイク・FX",{**S,"asset_class":"fx","fired_from":B}),
"com":("FWD：安値ブレイク・金銀原油",{**S,"asset_class":"commodity","fired_from":B}),
"btc":("FWD：安値ブレイク・ビットコイン",{**S,"asset_class":"crypto","fired_from":B}),
"first":("FWD：安値ブレイク・前半（〜9月15日）",{**S,"fired_from":B,"fired_before":MID}),
"second":("FWD：安値ブレイク・後半（9月16日〜）",{**S,"fired_from":MID}),
}
R={}; claims=[]
for key,(lab,f) in C.items():
    k,n=v.compute(data,f); lo,hi=v.wilson(k,n)
    if lo<1: lo,hi=lo*100,hi*100
    R[key]=dict(k=k,n=n,p=100*k/n,lo=lo,hi=hi)
    claims.append({"label":lab,"filter":f,"k":k,"n":n})
json.dump({"article_id":"144","asof":ASOF,"hypothesis_id":"auto_signal-low_break","claims":claims},open('drafts/labnotes/lab-144-claims.json','w'),ensure_ascii=False,indent=1)
def pct(x):return f"{x:.1f}%"
def row(name,key,bold=False):
    r=R[key]; p=pct(r['p'])
    if bold: name=f"<strong>{name}</strong>"; p=f"<strong>{p}</strong>"; n=f"<strong>{r['n']:,}回</strong>"
    else: n=f"{r['n']:,}回"
    return f"          <tr><td>{name}</td><td>{r['k']:,}回</td><td>{n}</td><td>{p}</td><td>{r['lo']:.1f}%〜{r['hi']:.1f}%</td></tr>"
F=R['fwd']
html=open('drafts/draft-signal-lab-142.html',encoding='utf-8').read()
pre=html[:html.index('<main class="s-main">')]
post=html[html.index('<!-- 関連記事カード -->'):]
post=re.sub(r'<!-- series-nav:begin -->.*?<!-- series-nav:end -->\n?','',post,flags=re.S)
TITLE=f"安値を割り込んだときの売りは、前向き{F['n']}回でも勝ちにくい？ 登録前の悪い成績は続かなかった【研究日誌 #144】"
DESC=f"直近の安値を割り込んで出る「安値ブレイク」の売りを、前向き{F['n']}回で確認。勝った割合{pct(F['p'])}、偶然のぶれを考えた勝率は{F['lo']:.1f}%〜{F['hi']:.1f}%。登録前の成績との比較も整理。研究日誌第144回。"
pre=re.sub(r'<title>.*?</title>',f'<title>{TITLE} - MarketWatch AI</title>',pre,flags=re.S)
pre=re.sub(r'(<meta name="description" content=")[^"]*',r'\g<1>'+DESC,pre)
pre=re.sub(r'(<meta name="keywords" content=")[^"]*',r'\g<1>安値ブレイク,売り,シグナル研究,前向き検証,研究日誌',pre)
pre=pre.replace('guide-signal-lab-142.html','guide-signal-lab-144.html')
pre=re.sub(r'(<meta property="og:title" content=")[^"]*',r'\g<1>'+TITLE,pre)
pre=re.sub(r'(<meta property="og:description" content=")[^"]*',r'\g<1>'+DESC,pre)
pre=re.sub(r'("headline": ")[^"]*',r'\g<1>'+TITLE,pre)
pre=re.sub(r'("description": ")[^"]*',r'\g<1>'+DESC,pre)
pre=pre.replace('"datePublished": "2026-11-07"','"datePublished": "2026-11-09"').replace('"dateModified": "2026-11-07"','"dateModified": "2026-11-09"')
pre=re.sub(r'<h1>.*?</h1>',f'<h1>{TITLE}</h1>',pre)
pre=re.sub(r'<p class="meta-line">公開：[^<]*</p>','<p class="meta-line">公開：2026年11月9日　前向き期間：2026年6月23日〜　仮説登録日：2026年6月22日</p>',pre)
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
bars=(bar(85,R['all']['p'],A,.5,'全シグナル',f"{R['all']['n']:,}回")
 +bar(160,R['short']['p'],A,.6,'売り全体',f"{R['short']['n']:,}回")
 +bar(235,F['p'],G,.75,'安値ブレイク',f"{F['n']}回",True)
 +bar(310,R['first']['p'],G,.6,'前半',f"{R['first']['n']}回")
 +bar(385,R['second']['p'],G,.6,'後半',f"{R['second']['n']}回")
 +bar(460,R['is']['p'],M,.5,'登録前',f"{R['is']['n']}回")
 +bar(535,R['isshort']['p'],M,.4,'登録前(売り全体)',f"{R['isshort']['n']}回"))
ticks=''.join(f'        <line x1="70" y1="{265-K*t:.0f}" x2="610" y2="{265-K*t:.0f}" stroke="var(--c-border,#e2e6ed)" stroke-width="0.5" stroke-dasharray="3,3"/>\n        <text x="65" y="{265-K*t+4:.0f}" font-size="10" font-family="sans-serif" fill="var(--c-muted,#999)" text-anchor="end">{t}%</text>\n' for t in (20,30,40,50))
svg1=f'''      <svg viewBox="0 0 640 310" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="安値ブレイクの勝率比較棒グラフ" style="width:100%;max-width:640px;display:block;margin:0 auto">
        <rect width="640" height="310" fill="var(--c-surface,#fff)" rx="6"/>
        <text x="320" y="22" font-size="13" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)">前向き（2026年6月23日以降）と登録前の勝率比較</text>
        <line x1="70" y1="40" x2="70" y2="265" stroke="var(--c-border,#e2e6ed)" stroke-width="1"/>
        <line x1="70" y1="265" x2="610" y2="265" stroke="var(--c-border,#e2e6ed)" stroke-width="1"/>
        <text x="65" y="269" font-size="10" font-family="sans-serif" fill="var(--c-muted,#999)" text-anchor="end">0%</text>
{ticks}        <line x1="70" y1="{265-K*43:.1f}" x2="610" y2="{265-K*43:.1f}" stroke="var(--c-warn,#d97706)" stroke-width="1.5" stroke-dasharray="5,3"/>
        <text x="615" y="{265-K*43+3:.1f}" font-size="10" font-family="sans-serif" fill="var(--c-warn,#d97706)">43%</text>
{bars}      </svg>'''
svg2='''      <svg viewBox="0 0 640 300" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="直近の安値を値段が割り込む瞬間を示す概念チャート" style="width:100%;max-width:640px;display:block;margin:0 auto">
        <rect width="640" height="300" fill="var(--c-surface,#fff)" rx="6"/>
        <text x="320" y="20" font-size="13" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)">「安値ブレイク」が出る瞬間のイメージ</text>
        <line x1="60" y1="190" x2="500" y2="190" stroke="var(--c-warn,#d97706)" stroke-width="1.5" stroke-dasharray="6,3"/>
        <text x="506" y="194" font-size="10" font-family="sans-serif" fill="var(--c-warn,#d97706)">直前20本の安値</text>
        <g stroke="var(--c-green,#16a34a)" stroke-width="1.5"><line x1="100" y1="110" x2="100" y2="170"/><line x1="150" y1="130" x2="150" y2="190"/><line x1="200" y1="120" x2="200" y2="185"/><line x1="250" y1="140" x2="250" y2="195"/><line x1="300" y1="125" x2="300" y2="192"/><line x1="350" y1="145" x2="350" y2="200"/></g>
        <g fill="var(--c-green,#16a34a)"><rect x="92" y="125" width="16" height="30"/><rect x="142" y="145" width="16" height="30"/><rect x="192" y="135" width="16" height="32"/><rect x="242" y="155" width="16" height="28"/><rect x="292" y="140" width="16" height="34"/><rect x="342" y="160" width="16" height="28"/></g>
        <g stroke="var(--c-red,#dc2626)" stroke-width="1.5"><line x1="420" y1="165" x2="420" y2="235"/></g>
        <g fill="var(--c-red,#dc2626)"><rect x="412" y="175" width="16" height="50"/></g>
        <rect x="404" y="159" width="32" height="82" fill="none" stroke="#d4a017" stroke-width="2" rx="6"/>
        <line x1="436" y1="241" x2="470" y2="262" stroke="#d4a017" stroke-width="1.2"/>
        <text x="400" y="278" font-size="11" font-family="sans-serif" fill="var(--c-muted,#5a6072)">安値を割り込んでシグナルが出る</text>
        <text x="60" y="48" font-size="11" font-family="sans-serif" fill="var(--c-muted,#5a6072)">条件：直前の20本の足でいちばん低い価格を、いまの価格が下回る</text>
        <text x="320" y="294" font-size="10" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)">※ 概念を示すイメージ図です（実際の値動きではありません）</text>
      </svg>'''
exec(open('drafts/labnotes/lab-144-body.py',encoding='utf-8').read())
open('drafts/draft-signal-lab-144.html','w',encoding='utf-8').write(pre+main+post)
print({k:(r['k'],r['n'],round(r['p'],1)) for k,r in R.items()})
