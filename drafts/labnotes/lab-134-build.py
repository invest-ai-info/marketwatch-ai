import re,json,sys
sys.path.insert(0,'.')
import signal_lab_verify as v
raw={r['label']:r for r in json.load(open('drafts/labnotes/lab-134-raw.json'))}
def g(l): return raw[l]
def pc(l): r=g(l); return round(100*r['k']/r['n'],1)
def ci(l):
    r=g(l); lo,hi=v.wilson(r['k'],r['n']); return round(lo,1),round(hi,1)
def row(a,l,strong=False):
    r=g(l); lo,hi=ci(l)
    s=lambda t:f'<strong>{t}</strong>' if strong else t
    return f'          <tr><td>{s(a)}</td><td>{r["k"]}回</td><td>{r["n"]}回</td><td>{s(str(pc(l))+"%")}</td><td>{lo}%〜{hi}%</td></tr>\n'
TH='<tr><th>場面</th><th>勝った回数</th><th>回数</th><th>勝った割合</th><th>偶然のぶれの幅（信頼区間）</th></tr>'
def table(rows): return f'''    <div class="s-table-wrap">
      <table class="s-table">
        <thead>
          {TH}
        </thead>
        <tbody>
{rows}        </tbody>
      </table>
    </div>
'''

src=open('drafts/draft-signal-lab-133.html',encoding='utf-8').read()
head=src[:src.index('<main class="s-main">')]
tail=src[src.index('  <!-- 関連記事カード -->'):]
TITLE='金・銀の買いは、前向きでは勝ちにくかった？ 382回で確かめた現在地【研究日誌 #134】'
DESC='金先物・銀先物の買いシグナルを、登録後の前向き382回で確認。勝った割合は43.7%、偶然のぶれを考えた幅は38.8%〜48.7%でした。'
head=re.sub(r'<title>.*?</title>',f'<title>{TITLE} - MarketWatch AI</title>',head)
head=re.sub(r'(<meta name="description" content=")[^"]*"',r'\g<1>'+DESC+'"',head)
head=re.sub(r'(<meta name="keywords" content=")[^"]*"',r'\g<1>金,銀,買い,シグナル研究,前向き検証,研究日誌"',head)
head=re.sub(r'(<meta property="og:title" content=")[^"]*"',r'\g<1>'+TITLE+'"',head)
head=re.sub(r'(<meta property="og:description" content=")[^"]*"',r'\g<1>'+DESC+'"',head)
head=re.sub(r'("headline": ")[^"]*"',r'\g<1>'+TITLE+'"',head)
head=re.sub(r'("description": ")[^"]*"',r'\g<1>'+DESC+'"',head)
head=head.replace('2026-10-29','2026-10-30').replace('guide-signal-lab-133','guide-signal-lab-134')
head=re.sub(r'<h1>.*?</h1>',f'<h1>{TITLE}</h1>',head)
head=re.sub(r'<p class="meta-line">公開：.*?</p>','<p class="meta-line">公開：2026年10月30日　前向き期間：2026年6月18日〜公開日まで　仮説登録日：2026年6月17日</p>',head)
bars=[("登録前","87回",pc('IS:金・銀の買い'),'var(--c-accent,#2563eb)',0.55),
      ("登録後(前向き)","382回",pc('FWD:金・銀の買い'),'var(--c-accent,#2563eb)',0.85),
      ("買い全体(対照)","3457回",pc('FWD:買い全体'),'var(--c-accent,#2563eb)',0.35),
      ("金・銀の売り(対照)","141回",pc('FWD:金・銀の売り'),'var(--c-accent,#2563eb)',0.35),
      ("金先物","182回",pc('FWD:金・銀の買い GC=F'),'var(--c-green,#16a34a)',0.6),
      ("銀先物","200回",pc('FWD:金・銀の買い SI=F'),'var(--c-green,#16a34a)',0.6)]
bs=''
for n,(lab,cnt,p,col,op) in enumerate(bars):
    x=90+n*85; h=3.6*p; y=265-h
    bs+=f"""        <rect x="{x}" y="{y:.1f}" width="60" height="{h:.1f}" fill="{col}" opacity="{op}" rx="3"/>
        <text x="{x+30}" y="{y-5:.1f}" font-size="11" font-family="sans-serif" text-anchor="middle" fill="{col}" font-weight="bold">{p}%</text>
        <text x="{x+30}" y="280" font-size="10" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)">{lab}</text>
        <text x="{x+30}" y="291" font-size="10" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)">{cnt}</text>
"""
t1=table(row('登録前の期間','IS:金・銀の買い')+row('登録後の前向き','FWD:金・銀の買い',True)+row('全期間（登録前と登録後の合計）','全期間:金・銀の買い')+row('対照：前向きの買いシグナル全体','FWD:買い全体')+row('対照：前向きの円がらみ通貨ペアの買い','FWD:円がらみFXの買い')+row('対照：前向きの金・銀の売り','FWD:金・銀の売り')+row('対照：前向きの全シグナル','FWD:全シグナル'))
t2=table(row('上昇の流れ','FWD:金・銀の買い 上昇')+row('もみあい','FWD:金・銀の買い 中立・もみあい')+row('下降の流れ','FWD:金・銀の買い 下降'))
t3=table(row('1時間足','FWD:金・銀の買い 1h')+row('4時間足','FWD:金・銀の買い 4h')+row('日足（回数が少ない）','FWD:金・銀の買い 1d'))
t4=table(row('金先物','FWD:金・銀の買い GC=F')+row('銀先物','FWD:金・銀の買い SI=F'))
fig=f"""    <h2>4. 図で見ると</h2>
    <div class="s-chart">
      <svg viewBox="0 0 640 300" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="値段が移動平均線を上に抜けて買いシグナルが出る場面のイメージ図" style="width:100%;max-width:640px;display:block;margin:0 auto">
        <rect width="640" height="300" fill="var(--c-surface,#fff)" rx="6"/>
        <text x="320" y="20" font-size="13" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)">買いシグナルが出る場面のイメージ（ローソク足と移動平均線）</text>
        <line x1="70" y1="124" x2="70" y2="160" stroke="var(--c-red,#dc2626)" stroke-width="1.5"/><rect x="61" y="130" width="18" height="24" fill="var(--c-red,#dc2626)" opacity=".8" rx="1"/>
        <line x1="122" y1="140" x2="122" y2="176" stroke="var(--c-red,#dc2626)" stroke-width="1.5"/><rect x="113" y="146" width="18" height="24" fill="var(--c-red,#dc2626)" opacity=".8" rx="1"/>
        <line x1="174" y1="156" x2="174" y2="190" stroke="var(--c-red,#dc2626)" stroke-width="1.5"/><rect x="165" y="161" width="18" height="24" fill="var(--c-red,#dc2626)" opacity=".8" rx="1"/>
        <line x1="226" y1="170" x2="226" y2="202" stroke="var(--c-red,#dc2626)" stroke-width="1.5"/><rect x="217" y="176" width="18" height="20" fill="var(--c-red,#dc2626)" opacity=".8" rx="1"/>
        <line x1="278" y1="172" x2="278" y2="198" stroke="var(--c-green,#16a34a)" stroke-width="1.5"/><rect x="269" y="178" width="18" height="16" fill="var(--c-green,#16a34a)" opacity=".8" rx="1"/>
        <line x1="330" y1="162" x2="330" y2="190" stroke="var(--c-green,#16a34a)" stroke-width="1.5"/><rect x="321" y="168" width="18" height="18" fill="var(--c-green,#16a34a)" opacity=".8" rx="1"/>
        <line x1="382" y1="148" x2="382" y2="182" stroke="var(--c-green,#16a34a)" stroke-width="1.5"/><rect x="373" y="154" width="18" height="22" fill="var(--c-green,#16a34a)" opacity=".8" rx="1"/>
        <line x1="434" y1="134" x2="434" y2="166" stroke="var(--c-green,#16a34a)" stroke-width="1.5"/><rect x="425" y="140" width="18" height="20" fill="var(--c-green,#16a34a)" opacity=".8" rx="1"/>
        <polyline points="70,132 122,148 174,163 226,174 278,180 330,180 382,178 434,176" fill="none" stroke="var(--c-accent,#2563eb)" stroke-width="2"/>
        <text x="70" y="108" font-size="10" font-family="sans-serif" fill="var(--c-accent,#2563eb)">青い線＝移動平均線（過去の値段の平均）</text>
        <rect x="366" y="144" width="32" height="44" fill="none" stroke="var(--c-warn,#d97706)" stroke-width="2.5" rx="3"/>
        <line x1="398" y1="148" x2="450" y2="104" stroke="var(--c-muted,#5a6072)" stroke-width="1"/>
        <text x="455" y="102" font-size="11" font-family="sans-serif" fill="var(--c-text,#1a1d27)">ここで買いシグナル</text>
        <text x="455" y="116" font-size="10" font-family="sans-serif" fill="var(--c-muted,#5a6072)">値段が平均線を上に抜けた</text>
        <line x1="478" y1="60" x2="610" y2="60" stroke="var(--c-green,#16a34a)" stroke-width="1" stroke-dasharray="5,3"/>
        <text x="478" y="74" font-size="10" font-family="sans-serif" fill="var(--c-green,#16a34a)">利益確定の目標（上のほう）</text>
        <line x1="478" y1="225" x2="610" y2="225" stroke="var(--c-red,#dc2626)" stroke-width="1" stroke-dasharray="5,3"/>
        <text x="478" y="239" font-size="10" font-family="sans-serif" fill="var(--c-red,#dc2626)">損切り（直近の安値の少し下）</text>
        <text x="70" y="252" font-size="10" font-family="sans-serif" fill="var(--c-muted,#5a6072)">値下がりが続いたあと、勢いが戻る</text>
      </svg>
      <p class="s-chart-note">※ 概念を示すイメージ図です（実際の値動きではありません）。買いシグナルには、ほかに「売られすぎからの反発」などもあります。</p>
    </div>
    <div class="s-chart">
      <svg viewBox="0 0 640 310" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="金・銀の買いの勝率比較棒グラフ" style="width:100%;max-width:640px;display:block;margin:0 auto">
        <rect width="640" height="310" fill="var(--c-surface,#fff)" rx="6"/>
        <text x="320" y="22" font-size="13" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)">勝った割合の比較（点線は損益分岐の43%）</text>
        <line x1="70" y1="40" x2="70" y2="265" stroke="var(--c-border,#e2e6ed)" stroke-width="1"/>
        <line x1="70" y1="265" x2="610" y2="265" stroke="var(--c-border,#e2e6ed)" stroke-width="1"/>
        <line x1="70" y1="193" x2="610" y2="193" stroke="var(--c-border,#e2e6ed)" stroke-width="0.5" stroke-dasharray="3,3"/>
        <line x1="70" y1="121" x2="610" y2="121" stroke="var(--c-border,#e2e6ed)" stroke-width="0.5" stroke-dasharray="3,3"/>
        <line x1="70" y1="49" x2="610" y2="49" stroke="var(--c-border,#e2e6ed)" stroke-width="0.5" stroke-dasharray="3,3"/>
        <text x="65" y="269" font-size="10" font-family="sans-serif" fill="var(--c-muted,#999)" text-anchor="end">0%</text>
        <text x="65" y="197" font-size="10" font-family="sans-serif" fill="var(--c-muted,#999)" text-anchor="end">20%</text>
        <text x="65" y="125" font-size="10" font-family="sans-serif" fill="var(--c-muted,#999)" text-anchor="end">40%</text>
        <text x="65" y="53" font-size="10" font-family="sans-serif" fill="var(--c-muted,#999)" text-anchor="end">60%</text>
        <line x1="70" y1="110.2" x2="610" y2="110.2" stroke="var(--c-warn,#d97706)" stroke-width="1.5" stroke-dasharray="5,3"/>
        <text x="614" y="113" font-size="10" font-family="sans-serif" fill="var(--c-warn,#d97706)">43%</text>
{bs}      </svg>
      <p class="s-chart-note">登録後の前向き（左から2本目）は43%の線のすぐ上でした。登録前（左端）は43%を大きく下回る数字でしたが、87回と回数が限られます。</p>
    </div>
  </section>

"""
body=f"""<main class="s-main">

  <!-- ① kinsho-v1 免責バナー（3点必須） -->
  <div class="disclaimer-banner s-note" data-disclaimer="kinsho-v1">
    ⚠️ 本記事は情報提供を目的としており、投資助言ではありません。当サイトは金融商品取引業者ではなく、投資助言・代理業の登録もしていません。投資判断はご自身の責任で行ってください。
  </div>

  <!-- 30秒まとめ -->
  <div class="s-summary">
    <div class="s-summary-head">⏱ 30秒でわかる今回のまとめ</div>
    <ul>
      <li>金先物・銀先物で出る「買い」シグナルは勝ちにくいのでは、という見方を、登録後の前向きで確かめ直しました。</li>
      <li>前向き（2026年6月18日から）では、<strong>382回中167回が勝ち</strong>。勝った割合は<strong>43.7%</strong>でした。</li>
      <li>勝ち負けがとんとんになる勝率（43%）とほぼ同じです。偶然のぶれを考えた幅は<strong>38.8%〜48.7%</strong>で、43%をまたいでいます。「勝ちにくい」とは確かめられませんでした。</li>
      <li>登録前の87回は<strong>17.2%</strong>と大きく低い数字でしたが、登録後は上がりました。</li>
      <li>金先物は<strong>44.0%</strong>、銀先物は<strong>43.5%</strong>で、ほとんど差はありません。</li>
    </ul>
  </div>

  <!-- 1. 今回の問い -->
  <section class="s-section">
    <h2>1. 今日確かめた問い</h2>
    <p>このサイトは、金先物と銀先物で出る買いシグナルを記録しています。買いシグナルは、値段が上がりそうな形になったときに出ます。</p>
    <p>「金・銀の買いは、勝ち負けがとんとんになる43%を下回るのでは」という見方を、2026年6月17日に仮説として登録しました。それより後に出たシグナルだけを数えるのが「前向き」です。回数が382回まで増えたので、現在地を確かめます。</p>
    <div class="s-note">
      <strong>💡 前向きとは</strong><br>
      仮説を登録した後に出たシグナルだけを数えることです。結果を見てから仮説を作っていないので、後付けの「勝てそう」を避けられます。
    </div>
  </section>

  <!-- 2. 調べ方 -->
  <section class="s-section">
    <h2>2. どのようにして調べたか</h2>
    <ul style="padding-left:1.4em;margin-bottom:12px;">
      <li>対象は、このサイトが記録している、金先物と銀先物の買いシグナルです。結果が出たもの（利益確定か損切りに達したもの）だけを数えます。</li>
      <li>「勝ち」は、利益確定の目標に先に達したことです。損切りに先に達したら負けです。</li>
      <li>勝ち負けがとんとんになる勝率は43%です。損切り幅と利益確定幅の比から決まります。</li>
      <li>「偶然のぶれを考えた幅」は、統計でよく使われる計算で出しています。回数が少ないほど幅が広くなります。</li>
      <li>仮説を登録した日より前の記録は「登録前の期間」、後の記録は「登録後の前向き」として分けて数えます。</li>
    </ul>
  </section>

  <!-- 3. 結果 -->
  <section class="s-section">
    <h2>3. 結果</h2>
{t1}    <p>前向きの買いは382回で43.7%でした。とんとんの43%とほぼ同じで、偶然のぶれの幅（38.8%〜48.7%）は43%をまたぎます。買いシグナル全体（42.7%）や円がらみ通貨ペアの買い（43.6%）と比べても、大きな差はありません。なお、これらの対照の中にも、このシグナル自体がふくまれている場合があります。</p>
    <p>登録前の87回は17.2%と低い数字でした。登録後に上がっており、登録前の低い数字は、そのまま続くものではなかったことになります。登録前の期間は短く、回数も87回ですので、この数字だけで何かを言うことはできません。</p>
    <h3>流れ別に見ると（前向きのみ）</h3>
{t2}    <p>上昇の流れで出た買いは46.3%、下降の流れでは41.6%、もみあいでは44.2%でした。幅の広い区分が重なっていて、差が本物かどうかは言えません。</p>
    <h3>時間足別に見ると（前向きのみ）</h3>
{t3}    <p>1時間足は44.1%、4時間足は44.2%で、ほぼ同じです。日足は29回しかなく、数字は参考になりません。</p>
    <h3>銘柄別に見ると（前向きのみ）</h3>
{t4}    <p>金先物（44.0%）と銀先物（43.5%）は、どちらも43%をわずかに上回りました。差はほとんどありません。</p>
    <p>トラッカーは登録日の当日から数えるため、記事の回数（382回）とトラッカーの回数（383回）は1回ずれます。トラッカーでは、1回あたりの平均損益は損切り幅の約0.02倍の益で、その幅はマイナス0.16倍からプラス0.21倍です。この仮説は「平均損益がマイナス」を確かめる形で登録しましたが、幅は0をまたいでおり、まだ判定は出ていません。</p>
  </section>

  <!-- 4. 図 -->
  <section class="s-section">
{fig}
  <!-- 5. 注意 -->
  <section class="s-section">
    <h2>5. 結果を読むときの注意</h2>
    <ul style="padding-left:1.4em;margin-bottom:12px;">
      <li>この仮説は「金・銀の買いは、とんとんの43%を下回る」かを確かめる形で登録しました。前向きの数字はとんとんとほぼ同じで、平均損益の幅も0をまたいでおり、確定はしていません。</li>
      <li>登録前の87回（17.2%）と登録後の382回（43.7%）で、勝った割合に大きな差があります。期間によって姿が変わる可能性があり、今の数字が続くとは限りません。</li>
      <li>流れ別・時間足別・銘柄別の表は、見比べるために並べたものです。区分を多く見るほど、偶然で良く見える区分が混ざります。</li>
      <li>金と銀は、同じ時期に同じような値動きをすることが多く、同時にシグナルが出ることがあります。回数のわりに、独立した場面の数は少ない可能性があります。</li>
      <li>勝った割合がとんとんに近いことは、今後も同じになることを意味しません。この記事は売買をすすめるものではありません。</li>
    </ul>
  </section>

  <!-- 6. まとめ -->
  <section class="s-section">
    <h2>6. まとめ</h2>
    <ul style="padding-left:1.4em;margin-bottom:12px;">
      <li>前向き382回で、金・銀の買いは43.7%。とんとんの43%とほぼ同じで、偶然のぶれの幅（38.8%〜48.7%）は43%をまたいでいます。</li>
      <li>登録前の87回は17.2%で、登録後は上がりました。</li>
      <li>金先物は44.0%、銀先物は43.5%で、差はほとんどありません。</li>
      <li>結論は出さず、毎日の定点観測で見守ります。</li>
    </ul>
  </section>

  <!-- トラッカー -->
  <section class="s-section">
<!-- MW:TRACKER_TABLE -->
  </section>

"""
open('drafts/draft-signal-lab-134.html','w',encoding='utf-8').write(head+body+tail)
json.dump({"article_id":"134","asof":"2026-10-30T06:15:11+09:00","hypothesis_id":"auto_direction-long_group-metal","claims":list(raw.values())},open('drafts/labnotes/lab-134-claims.json','w'),ensure_ascii=False,indent=1)
