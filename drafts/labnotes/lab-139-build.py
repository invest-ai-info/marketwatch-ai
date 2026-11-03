import json,sys,re
sys.path.insert(0,'.')
import signal_lab_verify as v
data=json.load(open('signals-log.json',encoding='utf-8-sig'))
ASOF="2026-11-04T06:12:00+09:00"
data,af,_=v.apply_asof(data,v.parse_asof(ASOF),"2026-11-04")
B="2026-07-21"; S={"ma_pos":"above_both","direction":"long"}
C={
"fwd":("FWD：両方の移動平均線の上での買いの勝ち回数",{**S,"fired_from":B}),
"is":("IS：両方の移動平均線の上での買い（登録前・参考）の勝ち回数",{**S,"fired_before":B}),
"long":("FWD：買い全体（対照）の勝ち回数",{"direction":"long","fired_from":B}),
"all":("FWD：全シグナルの勝ち回数",{"fired_from":B}),
"sh":("FWD：両方の移動平均線の上での売り（対照）",{"ma_pos":"above_both","direction":"short","fired_from":B}),
"h1":("FWD：両線の上の買い・1時間足",{**S,"tf":"1h","fired_from":B}),
"h4":("FWD：両線の上の買い・4時間足",{**S,"tf":"4h","fired_from":B}),
"d1":("FWD：両線の上の買い・日足",{**S,"tf":"1d","fired_from":B}),
"idx":("FWD：両線の上の買い・株価指数",{**S,"group":"index","fired_from":B}),
"jpy":("FWD：両線の上の買い・円がらみFX",{**S,"group":"jpy_fx","fired_from":B}),
"ofx":("FWD：両線の上の買い・円がらまないFX",{**S,"group":"other_fx","fired_from":B}),
"met":("FWD：両線の上の買い・金銀",{**S,"group":"metal","fired_from":B}),
"btc":("FWD：両線の上の買い・ビットコイン",{**S,"group":"btc","fired_from":B}),
"oil":("FWD：両線の上の買い・原油",{**S,"group":"oil","fired_from":B}),
"first":("FWD：両線の上の買い・前半（〜8月31日）",{**S,"fired_from":B,"fired_before":"2026-09-01"}),
"second":("FWD：両線の上の買い・後半（9月1日〜）",{**S,"fired_from":"2026-09-01"}),
}
R={}
claims=[]
for key,(lab,f) in C.items():
    k,n=v.compute(data,f); lo,hi=v.wilson(k,n)
    if lo<1: lo,hi=lo*100,hi*100
    R[key]=dict(k=k,n=n,p=100*k/n,lo=lo,hi=hi)
    claims.append({"label":lab,"filter":f,"k":k,"n":n})
json.dump({"article_id":"139","asof":"2026-11-04T06:12:00+09:00","hypothesis_id":"state_maup_long","claims":claims},open('drafts/labnotes/lab-139-claims.json','w'),ensure_ascii=False,indent=1)
def pct(x):return f"{x:.1f}%"
def row(name,key,bold=False,cls=""):
    r=R[key]; p=pct(r['p'])
    if bold: name=f"<strong>{name}</strong>"; p=f"<strong>{p}</strong>"; n=f"<strong>{r['n']:,}回</strong>"
    else: n=f"{r['n']:,}回"
    return f"          <tr><td>{name}</td><td>{r['k']:,}回</td><td>{n}</td><td{cls}>{p}</td><td>{r['lo']:.1f}%〜{r['hi']:.1f}%</td></tr>"
F=R['fwd']
html=open('guide-signal-lab-138.html',encoding='utf-8').read()
pre=html[:html.index('<main class="s-main">')]
post=html[html.index('<!-- 関連記事カード -->'):]
post=re.sub(r'<!-- series-nav:begin -->.*?<!-- series-nav:end -->\n?','',post,flags=re.S)
TITLE=f"移動平均線の上にいるときの買いは、前向き{F['n']}回で勝ちやすい？ 後半は勝率が下がった【研究日誌 #139】"
DESC=f"2本の移動平均線の上にいる場面の買いを、前向き{F['n']}回で再確認。勝った割合{pct(F['p'])}、偶然のぶれを考えた勝率は{F['lo']:.1f}%〜{F['hi']:.1f}%。前半と後半で差が出た理由も整理。研究日誌第139回。"
pre=re.sub(r'<title>.*?</title>',f'<title>{TITLE} - MarketWatch AI</title>',pre,flags=re.S)
pre=re.sub(r'(<meta name="description" content=")[^"]*',r'\g<1>'+DESC,pre)
pre=re.sub(r'(<meta name="keywords" content=")[^"]*',r'\g<1>移動平均線,トレンドの買い,順張り,シグナル研究,前向き検証,研究日誌',pre)
pre=pre.replace('guide-signal-lab-138.html','guide-signal-lab-139.html')
pre=re.sub(r'(<meta property="og:title" content=")[^"]*',r'\g<1>'+TITLE,pre)
pre=re.sub(r'(<meta property="og:description" content=")[^"]*',r'\g<1>'+DESC,pre)
pre=re.sub(r'("headline": ")[^"]*',r'\g<1>'+TITLE,pre)
pre=re.sub(r'("description": ")[^"]*',r'\g<1>'+DESC,pre)
pre=pre.replace('"datePublished": "2026-11-03"','"datePublished": "2026-11-04"').replace('"dateModified": "2026-11-03"','"dateModified": "2026-11-04"')
pre=re.sub(r'<h1>.*?</h1>',f'<h1>{TITLE}</h1>',pre)
pre=re.sub(r'<p class="meta-line">公開：[^<]*</p>','<p class="meta-line">公開：2026年11月4日　前向き期間：2026年7月21日〜　仮説登録日：2026年7月20日</p>',pre)
if 'noindex' not in pre:
    pre=pre.replace('<meta charset="UTF-8">','<meta charset="UTF-8">\n  <meta name="robots" content="noindex,nofollow">',1)
def bar(x,pct_,col,op,lab,sub,bold=False):
    hh=4.4*pct_; y=265-hh; w=' font-weight="bold"' if bold else ''
    return (f'        <rect x="{x}" y="{y:.1f}" width="70" height="{hh:.1f}" fill="{col}" opacity="{op}" rx="3"/>\n'
    f'        <text x="{x+35}" y="{y-5:.1f}" font-size="11" font-family="sans-serif" text-anchor="middle" fill="{col}" font-weight="bold">{pct_:.1f}%</text>\n'
    f'        <text x="{x+35}" y="280" font-size="10" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)"{w}>{lab}</text>\n'
    f'        <text x="{x+35}" y="291" font-size="10" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)">{sub}</text>\n')
G='var(--c-green,#16a34a)'; A='var(--c-accent,#2563eb)'; M='var(--c-muted,#5a6072)'; RD='var(--c-red,#dc2626)'
bars=(bar(80,R['all']['p'],A,.5,'全シグナル',f"{R['all']['n']:,}回")
 +bar(170,R['long']['p'],A,.6,'買い全体',f"{R['long']['n']:,}回")
 +bar(260,F['p'],G,.75,'両線の上の買い',f"{F['n']}回",True)
 +bar(350,R['first']['p'],G,.6,'前半の買い',f"{R['first']['n']}回")
 +bar(440,R['second']['p'],RD,.6,'後半の買い',f"{R['second']['n']}回")
 +bar(530,R['is']['p'],M,.5,'登録前（参考）',f"{R['is']['n']}回"))
ticks=''.join(f'        <line x1="70" y1="{265-4.4*t:.0f}" x2="610" y2="{265-4.4*t:.0f}" stroke="var(--c-border,#e2e6ed)" stroke-width="0.5" stroke-dasharray="3,3"/>\n        <text x="65" y="{265-4.4*t+4:.0f}" font-size="10" font-family="sans-serif" fill="var(--c-muted,#999)" text-anchor="end">{t}%</text>\n' for t in (20,30,40,50))
svg1=f'''      <svg viewBox="0 0 640 310" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="前向きの勝率比較棒グラフ" style="width:100%;max-width:640px;display:block;margin:0 auto">
        <rect width="640" height="310" fill="var(--c-surface,#fff)" rx="6"/>
        <text x="320" y="22" font-size="13" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)">前向き（2026年7月21日以降）の勝率比較</text>
        <line x1="70" y1="40" x2="70" y2="265" stroke="var(--c-border,#e2e6ed)" stroke-width="1"/>
        <line x1="70" y1="265" x2="610" y2="265" stroke="var(--c-border,#e2e6ed)" stroke-width="1"/>
        <text x="65" y="269" font-size="10" font-family="sans-serif" fill="var(--c-muted,#999)" text-anchor="end">0%</text>
{ticks}        <line x1="70" y1="{265-4.4*43:.1f}" x2="610" y2="{265-4.4*43:.1f}" stroke="var(--c-warn,#d97706)" stroke-width="1.5" stroke-dasharray="5,3"/>
        <text x="615" y="{265-4.4*43+3:.1f}" font-size="10" font-family="sans-serif" fill="var(--c-warn,#d97706)">43%</text>
{bars}      </svg>'''
svg2='''      <svg viewBox="0 0 640 300" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="2本の移動平均線の上で買いシグナルが出る瞬間を示す概念図" style="width:100%;max-width:640px;display:block;margin:0 auto">
        <rect width="640" height="300" fill="var(--c-surface,#fff)" rx="6"/>
        <text x="320" y="20" font-size="13" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)">買いシグナルが出る瞬間のイメージ（ローソク足と2本の移動平均線）</text>
        <polyline points="60,220 160,200 260,172 360,150 460,128 560,106" fill="none" stroke="var(--c-muted,#5a6072)" stroke-width="2" stroke-dasharray="6,3"/>
        <text x="566" y="104" font-size="10" font-family="sans-serif" fill="var(--c-muted,#5a6072)">長い線</text>
        <polyline points="60,200 160,176 260,148 360,124 460,100 560,78" fill="none" stroke="var(--c-accent,#2563eb)" stroke-width="2"/>
        <text x="566" y="76" font-size="10" font-family="sans-serif" fill="var(--c-accent,#2563eb)">短い線</text>
        <g stroke="var(--c-green,#16a34a)" stroke-width="1.5"><line x1="110" y1="150" x2="110" y2="190"/><line x1="170" y1="138" x2="170" y2="176"/><line x1="230" y1="124" x2="230" y2="160"/></g>
        <g fill="var(--c-green,#16a34a)"><rect x="102" y="158" width="16" height="22"/><rect x="162" y="146" width="16" height="20"/><rect x="222" y="132" width="16" height="20"/></g>
        <g stroke="var(--c-red,#dc2626)" stroke-width="1.5"><line x1="290" y1="112" x2="290" y2="146"/><line x1="350" y1="106" x2="350" y2="142"/></g>
        <g fill="var(--c-red,#dc2626)"><rect x="282" y="118" width="16" height="18"/><rect x="342" y="112" width="16" height="20"/></g>
        <g stroke="var(--c-green,#16a34a)" stroke-width="1.5"><line x1="410" y1="82" x2="410" y2="120"/></g>
        <g fill="var(--c-green,#16a34a)"><rect x="402" y="90" width="16" height="22"/></g>
        <rect x="394" y="76" width="32" height="50" fill="none" stroke="#d4a017" stroke-width="2" rx="6"/>
        <line x1="410" y1="76" x2="410" y2="46" stroke="#d4a017" stroke-width="1.2"/>
        <text x="250" y="40" font-size="11" font-family="sans-serif" fill="var(--c-muted,#5a6072)">ここでシグナルが出る（2本の線の上で、上向きの足）</text>
        <text x="60" y="262" font-size="11" font-family="sans-serif" fill="var(--c-muted,#5a6072)">条件：値段が、短い線と長い線の両方より上にある</text>
        <text x="320" y="288" font-size="10" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)">※ 概念を示すイメージ図です（実際の値動きではありません）</text>
      </svg>'''
main=f'''<main class="s-main">

  <!-- ① kinsho-v1 免責バナー（3点必須） -->
  <div class="disclaimer-banner s-note" data-disclaimer="kinsho-v1">
    ⚠️ 本記事は情報提供を目的としており、投資助言ではありません。当サイトは金融商品取引業者ではなく、投資助言・代理業の登録もしていません。投資判断はご自身の責任で行ってください。
  </div>

  <!-- 30秒まとめ -->
  <div class="s-summary">
    <div class="s-summary-head">⏱ 30秒でわかる今回のまとめ</div>
    <ul>
      <li>「値段が2本の移動平均線（一定期間の平均値段をつないだ線）の上にあるときの買い」を、前向き（2026年7月21日から）の成績で見ました。</li>
      <li>前向き全体では、<strong>{F['n']}回中{F['k']}回が勝ち</strong>。勝った割合は<strong>{pct(F['p'])}</strong>でした。</li>
      <li>偶然のぶれを考えた勝率は<strong>{F['lo']:.1f}%〜{F['hi']:.1f}%</strong>。勝ち負けがとんとんになる勝率（43%）をまたいでいます。</li>
      <li>比べる相手の買い全体は、<strong>{R['long']['n']:,}回中{R['long']['k']:,}回が勝ち（{pct(R['long']['p'])}）</strong>で、ほぼ同じでした。</li>
      <li>期間を分けると、前半（8月末まで）は<strong>{pct(R['first']['p'])}</strong>、後半（9月以降）は<strong>{pct(R['second']['p'])}</strong>でした。後半は幅の上の端も43%を下回っています。「昇格」は研究のための目印で、売買をすすめるものではありません。</li>
    </ul>
  </div>

  <!-- 1. 今回の問い -->
  <section class="s-section">
    <h2>1. 今日確かめた問い</h2>
    <p>「上がっている流れに乗って買う」のは、昔から知られた考え方です。当サイトでは、値段が短い移動平均線と長い移動平均線のどちらよりも上にあるときの買いを、「両線の上の買い」と呼んで調べています。</p>
    <p>移動平均線は、直近の一定期間の平均の値段をつないだ線です。短い線は25本分、長い線は75本分の平均です。値段が両方の線より上にあれば、上向きの流れにあると見る人が多い、というのがこの考え方の土台です。仮説は2026年7月20日に登録しました。この日より後のデータだけが「前向き」です。</p>
    <div class="s-note">
      <strong>💡 前向きとは</strong><br>
      仮説を登録した後に出たシグナルだけを数えることです。結果を見てから仮説を作っていないので、後付けの「勝てそう」を避けられます。
    </div>
  </section>

  <!-- 2. 調べ方 -->
  <section class="s-section">
    <h2>2. どのようにして調べたか</h2>
    <div class="s-table-wrap">
      <table class="s-table">
        <thead>
          <tr><th>項目</th><th>内容</th></tr>
        </thead>
        <tbody>
          <tr><td>対象</td><td>シグナルが出た時点で、値段が25本と75本の移動平均線の両方より上にある、買いのシグナル（1時間足・4時間足・日足）</td></tr>
          <tr><td>前向きの期間</td><td>2026年7月21日から現在まで</td></tr>
          <tr><td>比べる相手</td><td>同じ期間の買いのシグナル全体と、全シグナル</td></tr>
          <tr><td>勝ちの数え方</td><td>シグナルの時刻の価格で入ったとして、利益確定の水準に先に届けば勝ち、損切りの水準に先に届けば負け（事後の計算で、実際の売買ではありません）</td></tr>
          <tr><td>勝ち負けがとんとんになる勝率</td><td>43%（損切り幅と利益確定幅の比から決まる水準）</td></tr>
        </tbody>
      </table>
    </div>
  </section>

  <!-- 3. 結果 -->
  <section class="s-section">
    <h2>3. 結果</h2>
    <div class="s-table-wrap">
      <table class="s-table">
        <thead>
          <tr><th>区分</th><th>勝ち回数</th><th>全回数</th><th>勝率</th><th>偶然のぶれを考えた勝率</th></tr>
        </thead>
        <tbody>
{row('前向き：両線の上の買い','fwd',True)}
{row('前向き：買いのシグナル全体（対照）','long')}
{row('前向き：全シグナル','all')}
{row('前向き：両線の上の売り（対照）','sh')}
{row('登録前（参考）：両線の上の買い','is')}
        </tbody>
      </table>
    </div>
    <p>表の「登録前」は、2026年7月20日より前のデータ全部です。登録前の勝率（{pct(R['is']['p'])}）は、前向きより低く出ています。</p>
    <p>勝ち負けがとんとんになる勝率は43%です。前向きの幅（{F['lo']:.1f}%〜{F['hi']:.1f}%）は43%をまたいでいて、買い全体（{pct(R['long']['p'])}）や全シグナル（{pct(R['all']['p'])}）ともほぼ同じです。同じ時期の中で、両線の上の買いが特に勝ちやすかったとも、勝ちにくかったとも言えません。</p>
    <p>トラッカーの表は、数える日や対象の決め方が少しちがいます。そのため、回数が十数回ちがって見えます（表の下の「前向きトラッカー」を参照）。トラッカーでは、1回あたりの平均損益は損切り幅のほぼ0倍で、その幅は損切り幅のマイナス0.12倍からプラス0.12倍です。損も得もはっきりしていません。</p>

    <h3>時間足・資産ごとに分けると</h3>
    <p>時間足や資産によって、動き方がちがいます。そこで、前向き{F['n']}回を分けて見ました。回数が少ない区分は、偶然で大きくぶれます。</p>
    <div class="s-table-wrap">
      <table class="s-table">
        <thead>
          <tr><th>区分（両線の上の買い・前向き）</th><th>勝ち回数</th><th>全回数</th><th>勝率</th><th>偶然のぶれを考えた勝率</th></tr>
        </thead>
        <tbody>
{row('1時間足','h1')}
{row('4時間足','h4')}
{row('日足','d1')}
{row('株価指数','idx')}
{row('円がからむ通貨ペア（ドル円など）','jpy')}
{row('円がからまない通貨ペア','ofx')}
{row('金・銀','met')}
{row('ビットコイン','btc')}
{row('原油','oil')}
        </tbody>
      </table>
    </div>
    <p>どの区分も、幅が43%をまたいでいます。なお、上の区分に入らない資産があるため、この表の合計は全体と一致しません。区分を増やして見るほど、偶然で目立つ区分が出やすくなります。ここから「この時間足や資産で使えばよい」と言うことはできません。</p>

    <h3>前半と後半に分けると</h3>
    <div class="s-table-wrap">
      <table class="s-table">
        <thead>
          <tr><th>区分（両線の上の買い・前向き）</th><th>勝ち回数</th><th>全回数</th><th>勝率</th><th>偶然のぶれを考えた勝率</th></tr>
        </thead>
        <tbody>
{row('前半（2026年7月21日〜8月31日）','first')}
{row('後半（2026年9月1日〜現在）','second')}
        </tbody>
      </table>
    </div>
    <p>前半は{pct(R['first']['p'])}で、幅の下の端（{R['first']['lo']:.1f}%）は43%をわずかに上回っています。一方で後半は{pct(R['second']['p'])}で、幅の上の端（{R['second']['hi']:.1f}%）も43%を下回りました。全体で43%前後に見えるのは、前半の良さと後半の悪さが混ざったためです。</p>
    <p>ただし、これは期間を2つに切って比べたものです。切る日を変えれば数字は変わりますし、後半が悪かった理由は、この数字だけではわかりません。9月以降に相場の流れが変わった可能性もあれば、偶然の可能性もあります。</p>
  </section>

  <!-- 4. 図 -->
  <section class="s-section">
    <h2>4. 図で見ると</h2>
    <div class="s-chart">
{svg2}
      <p class="s-chart-note">シグナルは、値段が25本と75本の2本の移動平均線の両方より上にあるときの買いで出ます。図は仕組みを示すイメージで、実際の値動きではありません。</p>
    </div>
    <div class="s-chart">
{svg1}
      <p class="s-chart-note">緑の棒（両線の上の買い全体）は、勝ち負けがとんとんになる43%の線のすぐ近くにあります。前半の棒は線の上、後半の棒は線の下にあり、登録前も線の下です。</p>
    </div>
  </section>

  <!-- 5. 注意 -->
  <section class="s-section">
    <h2>5. 結果を読むときの注意</h2>
    <ul style="padding-left:1.4em;margin-bottom:12px;">
      <li>前半と後半の差は、切る日を決めたあとで比べたものです。別の日で切れば、数字は変わります。</li>
      <li>この仮説は、登録前の一部の期間で確かめたときの成績が良かったため登録しました。表の「登録前」は、登録前のデータ全部を数えたものなので、数字がちがいます。前向きでは、確かめたときほどの成績は出ていません。過去の良さが前向きでも続くとは限らない例です。</li>
      <li>登録前の勝率は低めでした。この期間と前向きで結果がちがうのは、偶然のぶれや、相場の時期の影響かもしれません。</li>
      <li>時間足・資産ごとの表は、区分を増やして見たものです。回数が少ない区分の数字は、偶然で大きく動きます。</li>
      <li>このサイトの判定は、<strong>平均損益の幅の下の端がプラスか</strong>と<strong>同じ時期の全体より良いか</strong>の2つを、2回続けて満たしたときに昇格させます。この仮説は、一度昇格したあと基準を割ったため、研究中に戻しています。次の判定は、トラッカー上の前向きの回数が900回に届いたときです。「昇格」は研究上の目印で、売買をすすめるものではありません。</li>
    </ul>
  </section>

  <!-- 6. まとめ -->
  <section class="s-section">
    <h2>6. まとめ</h2>
    <ul style="padding-left:1.4em;margin-bottom:12px;">
      <li>前向き{F['n']}回で、両線の上の買いは{pct(F['p'])}。勝ち負けがとんとんになる43%を、幅がまたいでいます。</li>
      <li>同じ時期の買い全体（{pct(R['long']['p'])}）とほぼ同じで、特別に勝ちやすい証拠は出ていません。</li>
      <li>前半（{pct(R['first']['p'])}）と後半（{pct(R['second']['p'])}）で差が出ました。後半が悪かった理由は、まだわかっていません。</li>
      <li>結論はまだ出していません。毎日の定点観測で、次の判定を待ちます。</li>
    </ul>
  </section>

  <!-- トラッカー -->
  <section class="s-section">
<!-- MW:TRACKER_TABLE -->
  </section>

'''
open('drafts/draft-signal-lab-139.html','w',encoding='utf-8').write(pre+main+post)
print({k:(r['k'],r['n'],round(r['p'],1)) for k,r in R.items()})
