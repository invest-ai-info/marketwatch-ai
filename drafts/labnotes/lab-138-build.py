import json,sys,re
sys.path.insert(0,'.')
import signal_lab_verify as v
data=json.load(open('signals-log.json',encoding='utf-8-sig'))
ASOF="2026-11-03T06:11:00+09:00"
data,af,_=v.apply_asof(data,v.parse_asof(ASOF),"2026-11-03")
B="2026-06-17"; S={"signal":"rsi_oversold_bounce"}
C={ # key:(label,filter)
"fwd":("FWD：売られすぎ反発の勝ち回数",{**S,"fired_from":B}),
"is":("IS：売られすぎ反発（登録前・参考）の勝ち回数",{**S,"fired_before":B}),
"long":("FWD：買い全体（対照）の勝ち回数",{"direction":"long","fired_from":B}),
"all":("FWD：全シグナルの勝ち回数",{"fired_from":B}),
"h1":("FWD：売られすぎ反発・1時間足",{**S,"tf":"1h","fired_from":B}),
"h4":("FWD：売られすぎ反発・4時間足",{**S,"tf":"4h","fired_from":B}),
"d1":("FWD：売られすぎ反発・日足",{**S,"tf":"1d","fired_from":B}),
"idx":("FWD：売られすぎ反発・株価指数",{**S,"group":"index","fired_from":B}),
"jpy":("FWD：売られすぎ反発・円がらみFX",{**S,"group":"jpy_fx","fired_from":B}),
"ofx":("FWD：売られすぎ反発・円がらまないFX",{**S,"group":"other_fx","fired_from":B}),
"met":("FWD：売られすぎ反発・金銀",{**S,"group":"metal","fired_from":B}),
"btc":("FWD：売られすぎ反発・ビットコイン",{**S,"group":"btc","fired_from":B}),
"oil":("FWD：売られすぎ反発・原油",{**S,"group":"oil","fired_from":B}),
"first":("FWD：売られすぎ反発・前半（〜8月31日）",{**S,"fired_from":B,"fired_before":"2026-09-01"}),
"second":("FWD：売られすぎ反発・後半（9月1日〜）",{**S,"fired_from":"2026-09-01"}),
}
R={}
claims=[]
for key,(lab,f) in C.items():
    k,n=v.compute(data,f); lo,hi=v.wilson(k,n)
    if lo<1: lo,hi=lo*100,hi*100
    R[key]=dict(k=k,n=n,p=100*k/n,lo=lo,hi=hi)
    claims.append({"label":lab,"filter":f,"k":k,"n":n})
json.dump({"article_id":"138","asof":"2026-11-03T06:11:00+09:00","hypothesis_id":"rsi_oversold_edge","claims":claims},open('drafts/labnotes/lab-138-claims.json','w'),ensure_ascii=False,indent=1)
def pct(x):return f"{x:.1f}%"
def row(name,key,bold=False,cls=""):
    r=R[key]; p=pct(r['p'])
    if bold: name=f"<strong>{name}</strong>"; p=f"<strong>{p}</strong>"; n=f"<strong>{r['n']:,}回</strong>"
    else: n=f"{r['n']:,}回"
    return f"          <tr><td>{name}</td><td>{r['k']:,}回</td><td>{n}</td><td{cls}>{p}</td><td>{r['lo']:.1f}%〜{r['hi']:.1f}%</td></tr>"
F=R['fwd']
html=open('guide-signal-lab-137.html',encoding='utf-8').read()
pre=html[:html.index('<main class="s-main">')]
post=html[html.index('<!-- 関連記事カード -->'):]
post=re.sub(r'<!-- series-nav:begin -->.*?<!-- series-nav:end -->\n?','',post,flags=re.S)
TITLE=f"売られすぎからの反発の買いは、前向き{F['n']}回でも勝ちやすい？ 判定まであと約40回【研究日誌 #138】"
DESC=f"RSI（相対力指数）が売られすぎの水準から戻った場面の買いを、前向き{F['n']}回で再確認。勝った割合{pct(F['p'])}、偶然のぶれを考えた勝率は{F['lo']:.1f}%〜{F['hi']:.1f}%。研究日誌第138回。"
pre=re.sub(r'<title>.*?</title>',f'<title>{TITLE} - MarketWatch AI</title>',pre,flags=re.S)
pre=re.sub(r'(<meta name="description" content=")[^"]*',r'\g<1>'+DESC,pre)
pre=re.sub(r'(<meta name="keywords" content=")[^"]*',r'\g<1>RSI,売られすぎ,逆張り,シグナル研究,前向き検証,研究日誌',pre)
pre=pre.replace('guide-signal-lab-137.html','guide-signal-lab-138.html')
pre=re.sub(r'(<meta property="og:title" content=")[^"]*',r'\g<1>'+TITLE,pre)
pre=re.sub(r'(<meta property="og:description" content=")[^"]*',r'\g<1>'+DESC,pre)
pre=re.sub(r'("headline": ")[^"]*',r'\g<1>'+TITLE,pre)
pre=re.sub(r'("description": ")[^"]*',r'\g<1>'+DESC,pre)
pre=pre.replace('"datePublished": "2026-11-02"','"datePublished": "2026-11-03"')
pre=re.sub(r'<h1>.*?</h1>',f'<h1>{TITLE}</h1>',pre)
pre=re.sub(r'<p class="meta-line">公開：[^<]*</p>','<p class="meta-line">公開：2026年11月3日　前向き期間：2026年6月17日〜　仮説登録日：2026年6月16日</p>',pre)
if 'noindex' not in pre:
    pre=pre.replace('<meta charset="UTF-8">','<meta charset="UTF-8">\n  <meta name="robots" content="noindex,nofollow">',1)
# 縮尺 y=265-4.4*pct
def bar(x,pct_,col,op,lab,sub,bold=False):
    h=4.4*pct_; y=265-h; w=' font-weight="bold"' if bold else ''
    return (f'        <rect x="{x}" y="{y:.1f}" width="70" height="{h:.1f}" fill="{col}" opacity="{op}" rx="3"/>\n'
    f'        <text x="{x+35}" y="{y-5:.1f}" font-size="11" font-family="sans-serif" text-anchor="middle" fill="{col}" font-weight="bold">{pct_:.1f}%</text>\n'
    f'        <text x="{x+35}" y="280" font-size="10" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)"{w}>{lab}</text>\n'
    f'        <text x="{x+35}" y="291" font-size="10" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)">{sub}</text>\n')
bars=(bar(100,R['all']['p'],'var(--c-accent,#2563eb)',.5,'全シグナル',f"{R['all']['n']:,}回")
 +bar(210,R['long']['p'],'var(--c-accent,#2563eb)',.6,'買い全体',f"{R['long']['n']:,}回")
 +bar(320,F['p'],'var(--c-green,#16a34a)',.75,'売られすぎ反発',f"{F['n']}回",True)
 +bar(430,R['is']['p'],'var(--c-muted,#5a6072)',.5,'登録前（参考）',f"{R['is']['n']}回"))
ticks=''.join(f'        <line x1="70" y1="{265-4.4*t:.0f}" x2="610" y2="{265-4.4*t:.0f}" stroke="var(--c-border,#e2e6ed)" stroke-width="0.5" stroke-dasharray="3,3"/>\n        <text x="65" y="{265-4.4*t+4:.0f}" font-size="10" font-family="sans-serif" fill="var(--c-muted,#999)" text-anchor="end">{t}%</text>\n' for t in (20,30,40,50))
svg1=f'''      <svg viewBox="0 0 640 310" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="前向きの勝率比較棒グラフ" style="width:100%;max-width:640px;display:block;margin:0 auto">
        <rect width="640" height="310" fill="var(--c-surface,#fff)" rx="6"/>
        <text x="320" y="22" font-size="13" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)">前向き（2026年6月17日以降）の勝率比較</text>
        <line x1="70" y1="40" x2="70" y2="265" stroke="var(--c-border,#e2e6ed)" stroke-width="1"/>
        <line x1="70" y1="265" x2="610" y2="265" stroke="var(--c-border,#e2e6ed)" stroke-width="1"/>
        <text x="65" y="269" font-size="10" font-family="sans-serif" fill="var(--c-muted,#999)" text-anchor="end">0%</text>
{ticks}        <line x1="70" y1="{265-4.4*43:.1f}" x2="610" y2="{265-4.4*43:.1f}" stroke="var(--c-warn,#d97706)" stroke-width="1.5" stroke-dasharray="5,3"/>
        <text x="615" y="{265-4.4*43+3:.1f}" font-size="10" font-family="sans-serif" fill="var(--c-warn,#d97706)">43%</text>
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
main=f'''<main class="s-main">

  <!-- ① kinsho-v1 免責バナー（3点必須） -->
  <div class="disclaimer-banner s-note" data-disclaimer="kinsho-v1">
    ⚠️ 本記事は情報提供を目的としており、投資助言ではありません。当サイトは金融商品取引業者ではなく、投資助言・代理業の登録もしていません。投資判断はご自身の責任で行ってください。
  </div>

  <!-- 30秒まとめ -->
  <div class="s-summary">
    <div class="s-summary-head">⏱ 30秒でわかる今回のまとめ</div>
    <ul>
      <li>「RSI（相対力指数）が売られすぎの水準から戻った場面の買い」を、前向き（2026年6月17日から）の成績で見ました。</li>
      <li>前向きでは、<strong>{F['n']}回中{F['k']}回が勝ち</strong>。勝った割合は<strong>{pct(F['p'])}</strong>でした。</li>
      <li>偶然のぶれを考えた勝率は<strong>{F['lo']:.1f}%〜{F['hi']:.1f}%</strong>。勝ち負けがとんとんになる勝率（43%）を、幅の下の端でも上回っています。</li>
      <li>比べる相手の買い全体は、<strong>{R['long']['n']:,}回中{R['long']['k']:,}回が勝ち（{pct(R['long']['p'])}）</strong>で、ほぼ43%でした。</li>
      <li>ただし、まだ「勝ちやすいと確定」とは言えません。昇格の判定は2回続けて条件を満たす決まりで、今は1回目まで進んだところです。次の判定は、前向きが480回に届いたときです。</li>
    </ul>
  </div>

  <!-- 1. 今回の問い -->
  <section class="s-section">
    <h2>1. 今日確かめた問い</h2>
    <p>「売られすぎまで下がったあとの反発」は、昔から知られた買いの考え方です。当サイトでは、この考え方に当てはまるシグナルを「RSI売られすぎからの反発」と呼んでいます。以前の研究日誌でも何度か取り上げました。今回は、前向きの回数が増えたので、いまの現在地を確かめます。</p>
    <p>RSI（相対力指数）は、買われすぎ・売られすぎを0から100で表す指標です。このシグナルは、1本前のローソク足でRSIが30を下回り、今のローソク足でRSIが前より上がった（まだ50未満）ときに、反転の最初の1本で1回だけ出ます。仮説は2026年6月16日に登録しました。この日より後のデータだけが「前向き」です。</p>
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
          <tr><td>対象</td><td>RSI売られすぎからの反発のシグナル（1時間足・4時間足・日足）</td></tr>
          <tr><td>前向きの期間</td><td>2026年6月17日から現在まで</td></tr>
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
{row('前向き：売られすぎからの反発','fwd',True,' class="plus"')}
{row('前向き：買いのシグナル全体（対照）','long')}
{row('前向き：全シグナル','all')}
{row('登録前（参考）：売られすぎからの反発','is')}
        </tbody>
      </table>
    </div>
    <p>表の「登録前」は、2026年6月16日より前のデータです。登録前の勝率（{pct(R['is']['p'])}）は、前向きより低く、幅も広く出ています。</p>
    <p>勝ち負けがとんとんになる勝率は43%です。前向きの幅（{F['lo']:.1f}%〜{F['hi']:.1f}%）は、下の端でも43%を上回っています。買い全体（{pct(R['long']['p'])}）や全シグナル（{pct(R['all']['p'])}）はほぼ43%なので、同じ時期の中では、売られすぎからの反発が高めに出ています。</p>
    <p>トラッカーの表は、登録日の当日も数えます。そのため、回数が数件ちがって見えます（表の下の「前向きトラッカー」を参照）。トラッカーでは、1回あたりの平均損益が損切り幅の0.16倍の利益で、その幅は0.01倍の利益から0.31倍の利益です。幅の下の端はゼロにとても近く、ほんの少しのことでゼロをまたぎます。</p>

    <h3>時間足・資産ごとに分けると</h3>
    <p>時間足や資産によって、動き方がちがいます。そこで、前向き{F['n']}回を分けて見ました。回数が少ない区分は、偶然で大きくぶれます。</p>
    <div class="s-table-wrap">
      <table class="s-table">
        <thead>
          <tr><th>区分（売られすぎからの反発・前向き）</th><th>勝ち回数</th><th>全回数</th><th>勝率</th><th>偶然のぶれを考えた勝率</th></tr>
        </thead>
        <tbody>
{row('1時間足','h1')}
{row('4時間足','h4')}
{row('日足（回数が少ない）','d1')}
{row('株価指数','idx')}
{row('円がからむ通貨ペア（ドル円など）','jpy')}
{row('円がからまない通貨ペア','ofx')}
{row('金・銀','met')}
{row('ビットコイン（回数が少ない）','btc')}
{row('原油（回数が少ない）','oil')}
        </tbody>
      </table>
    </div>
    <p>どの区分も、勝率は43%を上回って出ています。幅の下の端まで43%を上回っているのは日足だけですが、27回しかなく、結論には使えません。区分を増やして見るほど、偶然で目立つ区分が出やすくなります。ここから「この時間足や資産で使えばよい」と言うことはできません。</p>

    <h3>前半と後半に分けると</h3>
    <div class="s-table-wrap">
      <table class="s-table">
        <thead>
          <tr><th>区分（売られすぎからの反発・前向き）</th><th>勝ち回数</th><th>全回数</th><th>勝率</th><th>偶然のぶれを考えた勝率</th></tr>
        </thead>
        <tbody>
{row('前半（2026年6月17日〜8月31日）','first')}
{row('後半（2026年9月1日〜現在）','second')}
        </tbody>
      </table>
    </div>
    <p>後半は勝率が下がり、幅が43%をまたいでいます。前向きの勝率の高さは、前半に偏っていた可能性があります。回数が増えて平均に近づいていくのか、これから確かめます。</p>
  </section>

  <!-- 4. 図 -->
  <section class="s-section">
    <h2>4. 図で見ると</h2>
    <div class="s-chart">
{svg2}
      <p class="s-chart-note">シグナルは、RSIが30を下回ったあと、前の足より上がった最初の1本で出ます。図は仕組みを示すイメージで、実際の値動きではありません。</p>
    </div>
    <div class="s-chart">
{svg1}
      <p class="s-chart-note">緑の棒（売られすぎからの反発）は、損益分岐の43%の線の上にあり、全体や買い全体はほぼ線の位置にあります。登録前は線の下です。</p>
    </div>
  </section>

  <!-- 5. 注意 -->
  <section class="s-section">
    <h2>5. 結果を読むときの注意</h2>
    <ul style="padding-left:1.4em;margin-bottom:12px;">
      <li>後半（9月以降）は勝率が下がり、幅が43%をまたいでいます。全期間の数字の良さが、一時的なものである可能性があります。</li>
      <li>登録前の勝率は低めでした。この期間と前向きで結果がちがうのは、偶然のぶれや、相場の時期の影響かもしれません。</li>
      <li>時間足・資産ごとの表は、区分を増やして見たものです。回数が少ない区分の数字は、偶然で大きく動きます。</li>
      <li>このサイトの判定は、<strong>平均損益の幅の下の端がプラスか</strong>と<strong>同じ時期の全体より良いか</strong>の2つを、2回続けて満たしたときに昇格させます。1回目は通過しています。ただし、幅の下の端はゼロにとても近いので、次の判定で昇格しないこともあります。「昇格」は研究上の目印で、売買をすすめるものではありません。</li>
    </ul>
  </section>

  <!-- 6. まとめ -->
  <section class="s-section">
    <h2>6. まとめ</h2>
    <ul style="padding-left:1.4em;margin-bottom:12px;">
      <li>前向き{F['n']}回で、売られすぎからの反発は{pct(F['p'])}。損益分岐の43%を、幅の下の端（{F['lo']:.1f}%）でも上回っています。</li>
      <li>同じ時期の買い全体（{pct(R['long']['p'])}）より高めですが、後半（9月以降）は{pct(R['second']['p'])}に下がり、幅が43%をまたいでいます。</li>
      <li>時間足・資産ごとの内訳は回数が少なく、まだ結論に使えません。</li>
      <li>結論はまだ出していません。毎日の定点観測で、前向きが480回に届いたときの判定を待ちます。</li>
    </ul>
  </section>

  <!-- トラッカー -->
  <section class="s-section">
<!-- MW:TRACKER_TABLE -->
  </section>

'''
open('drafts/draft-signal-lab-138.html','w',encoding='utf-8').write(pre+main+post)
print({k:(r['k'],r['n'],round(r['p'],1)) for k,r in R.items()})
