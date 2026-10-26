import re,json
src=open('drafts/draft-signal-lab-130.html',encoding='utf-8').read()
i_main=src.index('<main class="s-main">')
head=src[:i_main]
i_card=src.index('  <!-- 関連記事カード -->')
tail=src[i_card:]
TITLE='株価指数の売りは、前向きでは勝ちやすかった？ 274回で確かめた現在地【研究日誌 #131】'
DESC='日経平均先物・S&amp;P500先物などの売りシグナルを、登録後の前向き274回で確認。勝った割合は49.3%、偶然のぶれを考えた幅は43.4%〜55.2%でした。'
head=re.sub(r'<title>.*?</title>',f'<title>{TITLE} - MarketWatch AI</title>',head)
head=re.sub(r'(<meta name="description" content=")[^"]*"',r'\g<1>'+DESC+'"',head)
head=re.sub(r'(<meta name="keywords" content=")[^"]*"',r'\g<1>株価指数,売り,シグナル研究,前向き検証,研究日誌"',head)
head=re.sub(r'(<meta property="og:title" content=")[^"]*"',r'\g<1>'+TITLE+'"',head)
head=re.sub(r'(<meta property="og:description" content=")[^"]*"',r'\g<1>'+DESC+'"',head)
head=re.sub(r'("headline": ")[^"]*"',r'\g<1>'+TITLE+'"',head)
head=re.sub(r'("description": ")[^"]*"',r'\g<1>'+DESC+'"',head)
head=head.replace('2026-10-26','2026-10-27').replace('guide-signal-lab-130','guide-signal-lab-131')
head=re.sub(r'<h1>.*?</h1>',f'<h1>{TITLE}</h1>',head)
head=re.sub(r'<p class="meta-line">公開：.*?</p>','<p class="meta-line">公開：2026年10月27日　前向き期間：2026年7月1日〜公開日まで　仮説登録日：2026年6月30日</p>',head)

# bar chart geometry: y = 265 - 3.6*pct
bars=[("登録前","65回",27.7,'var(--c-red,#dc2626)',0.55),("登録後(前向き)","274回",49.3,'var(--c-accent,#2563eb)',0.85),
      ("売り全体(対照)","1032回",42.1,'var(--c-accent,#2563eb)',0.35),("指数の買い(対照)","763回",40.8,'var(--c-accent,#2563eb)',0.35),
      ("日経平均先物","73回",58.9,'var(--c-green,#16a34a)',0.6),("英国の株価指数先物","29回",37.9,'var(--c-red,#dc2626)',0.45)]
bs=''
for n,(lab,cnt,p,col,op) in enumerate(bars):
    x=90+n*85; h=3.6*p; y=265-h
    bs+=f'''        <rect x="{x}" y="{y:.1f}" width="60" height="{h:.1f}" fill="{col}" opacity="{op}" rx="3"/>
        <text x="{x+30}" y="{y-5:.1f}" font-size="11" font-family="sans-serif" text-anchor="middle" fill="{col}" font-weight="bold">{p}%</text>
        <text x="{x+30}" y="280" font-size="10" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)">{lab}</text>
        <text x="{x+30}" y="291" font-size="10" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)">{cnt}</text>
'''
def row(a,k,n,p,lo,hi,strong=False):
    s=lambda t:f'<strong>{t}</strong>' if strong else t
    return f'          <tr><td>{s(a)}</td><td>{k}回</td><td>{n}回</td><td>{s(str(p)+"%")}</td><td>{lo}%〜{hi}%</td></tr>\n'
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
t1=table(row('登録前の期間',18,65,27.7,18.3,39.6)+row('登録後の前向き',135,274,49.3,43.4,55.2,True)+row('全期間（登録前と登録後の合計）',153,339,45.1,39.9,50.5)+row('対照：前向きの売りシグナル全体',434,1032,42.1,39.1,45.1)+row('対照：前向きの株価指数の買い',311,763,40.8,37.3,44.3)+row('対照：前向きの全シグナル',1739,4105,42.4,40.9,43.9))
t2=table(row('上昇の流れ',59,118,50.0,41.1,58.9)+row('もみあい',42,91,46.2,36.3,56.3)+row('下降の流れ',34,65,52.3,40.4,64.0))
t3=table(row('1時間足',71,148,48.0,40.1,56.0)+row('4時間足',63,117,53.8,44.8,62.6)+row('日足（回数が少ない）',1,9,11.1,2.0,43.5))
t4=table(row('日経平均先物',43,73,58.9,47.4,69.5)+row('S&amp;P500先物',31,56,55.4,42.4,67.6)+row('ナスダック100先物',26,60,43.3,31.6,55.9)+row('NYダウ先物',24,56,42.9,30.8,55.9)+row('英国の株価指数先物（回数が少なめ）',11,29,37.9,22.7,56.0))
body=f'''<main class="s-main">

  <!-- ① kinsho-v1 免責バナー（3点必須） -->
  <div class="disclaimer-banner s-note" data-disclaimer="kinsho-v1">
    ⚠️ 本記事は情報提供を目的としており、投資助言ではありません。当サイトは金融商品取引業者ではなく、投資助言・代理業の登録もしていません。投資判断はご自身の責任で行ってください。
  </div>

  <!-- 30秒まとめ -->
  <div class="s-summary">
    <div class="s-summary-head">⏱ 30秒でわかる今回のまとめ</div>
    <ul>
      <li>日経平均先物やS&amp;P500先物など、株価指数の「売り」シグナルを、登録後の前向きで確かめ直しました。</li>
      <li>前向き（2026年7月1日から）では、<strong>274回中135回が勝ち</strong>。勝った割合は<strong>49.3%</strong>でした。</li>
      <li>偶然のぶれを考えた勝率は<strong>43.4%〜55.2%</strong>です。勝ち負けがとんとんになる勝率（43%）を、低いほうの端がわずかに上回りました。ただし、1回あたりの損益で見ると、まだ偶然と区別できません。</li>
      <li>登録前の65回は<strong>27.7%</strong>でした。前と後で姿が大きく変わっています。</li>
      <li>銘柄別では、日経平均先物が<strong>58.9%</strong>、英国の株価指数先物が<strong>37.9%</strong>と差がありました。ただし、まだ結論を出せる回数ではありません。</li>
    </ul>
  </div>

  <!-- 1. 今回の問い -->
  <section class="s-section">
    <h2>1. 今日確かめた問い</h2>
    <p>このサイトは、株価指数の先物（日経平均・S&amp;P500・ナスダック100・NYダウ・英国の株価指数）で出る売りシグナルを記録しています。売りシグナルは、値段が下がりそうな形になったときに出ます。</p>
    <p>「株価指数の売りは負けやすいのでは」という疑いを、2026年6月30日に仮説として登録しました。それより後に出たシグナルだけを数えるのが「前向き」です。回数が274回まで増えたので、成績の現在地を確かめます。</p>
    <div class="s-note">
      <strong>💡 前向きとは</strong><br>
      仮説を登録した後に出たシグナルだけを数えることです。結果を見てから仮説を作っていないので、後付けの「勝てそう」を避けられます。
    </div>
  </section>

  <!-- 2. 調べ方 -->
  <section class="s-section">
    <h2>2. どのようにして調べたか</h2>
    <ul style="padding-left:1.4em;margin-bottom:12px;">
      <li>対象は、このサイトが記録している株価指数の売りシグナルです。結果が出たもの（利益確定か損切りに達したもの）だけを数えます。</li>
      <li>「勝ち」は、利益確定の目標に先に達したことです。損切りに先に達したら負けです。</li>
      <li>勝ち負けがとんとんになる勝率は43%です。損切り幅と利益確定幅の比から決まります。</li>
      <li>「偶然のぶれを考えた幅」は、統計でよく使われる計算で出しています。回数が少ないほど幅が広くなります。</li>
      <li>仮説を登録した日より前の記録は「登録前の期間」、後の記録は「登録後の前向き」として分けて数えます。</li>
    </ul>
  </section>

  <!-- 3. 結果 -->
  <section class="s-section">
    <h2>3. 結果</h2>
{t1}    <p>登録前は65回で27.7%と、とんとんの43%をかなり下回っていました。登録後は274回で49.3%です。売りシグナル全体（42.1%）や、株価指数の買い（40.8%）より、数ポイント高い位置にあります。なお、これらの対照の中にも、このシグナル自体がふくまれています。</p>
    <p>登録前と登録後で、これだけ姿が違うことには注意が必要です。どちらが「ふだんの姿」に近いのかは、まだ分かりません。</p>
    <h3>流れ別に見ると（前向きのみ）</h3>
{t2}    <p>3つの流れの差は小さく、どれも偶然のぶれの幅が重なっています。上昇の流れの途中でも、売りは勝った割合がとんとんの43%を上回っていました。流れによる違いは、今のところ読み取れません。どの流れでも、売りが有利だとは言えません。</p>
    <h3>時間足別に見ると（前向きのみ）</h3>
{t3}    <p>1時間足と4時間足は、どちらも回数が100回を超えており、勝った割合は48.0%と53.8%でした。日足は9回しかなく、数字は参考になりません。</p>
    <h3>銘柄別に見ると（前向きのみ）</h3>
{t4}    <p>日経平均先物とS&amp;P500先物は高めで、ナスダック100先物とNYダウ先物は、とんとんの43%の近くでした。英国の株価指数先物は29回と少なく、とんとんを下回っています。銘柄ごとに5つ見ているので、偶然で良く見える銘柄が混ざる可能性があります。銘柄の差が本物かどうかは、まだ言えません。特定の銘柄の売りが合っている、という意味でもありません。</p>
    <p>トラッカーは登録日の当日から数えるため、記事の回数（274回）とトラッカーの回数（275回）は1回ずれます。トラッカーでは、1回あたりの平均損益は損切り幅の0.15倍のもうけで、その幅はマイナス0.02倍からプラス0.31倍です。</p>
  </section>

  <!-- 4. 図 -->
  <section class="s-section">
    <h2>4. 図で見ると</h2>
    <div class="s-chart">
      <svg viewBox="0 0 640 300" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="移動平均線を値段が下に抜けて売りシグナルが出る場面のイメージ図" style="width:100%;max-width:640px;display:block;margin:0 auto">
        <rect width="640" height="300" fill="var(--c-surface,#fff)" rx="6"/>
        <text x="320" y="20" font-size="13" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)">売りシグナルが出る場面のイメージ（ローソク足と移動平均線）</text>
        <line x1="70" y1="185" x2="70" y2="214" stroke="var(--c-green,#16a34a)" stroke-width="1.5"/><rect x="61" y="190" width="18" height="20" fill="var(--c-green,#16a34a)" opacity=".8" rx="1"/>
        <line x1="122" y1="165" x2="122" y2="196" stroke="var(--c-green,#16a34a)" stroke-width="1.5"/><rect x="113" y="170" width="18" height="22" fill="var(--c-green,#16a34a)" opacity=".8" rx="1"/>
        <line x1="174" y1="145" x2="174" y2="176" stroke="var(--c-green,#16a34a)" stroke-width="1.5"/><rect x="165" y="150" width="18" height="22" fill="var(--c-green,#16a34a)" opacity=".8" rx="1"/>
        <line x1="226" y1="127" x2="226" y2="156" stroke="var(--c-green,#16a34a)" stroke-width="1.5"/><rect x="217" y="132" width="18" height="20" fill="var(--c-green,#16a34a)" opacity=".8" rx="1"/>
        <line x1="278" y1="124" x2="278" y2="146" stroke="var(--c-red,#dc2626)" stroke-width="1.5"/><rect x="269" y="132" width="18" height="10" fill="var(--c-red,#dc2626)" opacity=".8" rx="1"/>
        <line x1="330" y1="138" x2="330" y2="160" stroke="var(--c-red,#dc2626)" stroke-width="1.5"/><rect x="321" y="142" width="18" height="14" fill="var(--c-red,#dc2626)" opacity=".8" rx="1"/>
        <line x1="382" y1="154" x2="382" y2="184" stroke="var(--c-red,#dc2626)" stroke-width="1.5"/><rect x="373" y="158" width="18" height="22" fill="var(--c-red,#dc2626)" opacity=".8" rx="1"/>
        <line x1="434" y1="174" x2="434" y2="199" stroke="var(--c-red,#dc2626)" stroke-width="1.5"/><rect x="425" y="178" width="18" height="17" fill="var(--c-red,#dc2626)" opacity=".8" rx="1"/>
        <polyline points="70,206 122,192 174,176 226,160 278,150 330,157 382,164 434,172" fill="none" stroke="var(--c-accent,#2563eb)" stroke-width="2"/>
        <text x="70" y="232" font-size="10" font-family="sans-serif" fill="var(--c-accent,#2563eb)">青い線＝移動平均線（過去の値段の平均）</text>
        <rect x="366" y="148" width="32" height="42" fill="none" stroke="var(--c-warn,#d97706)" stroke-width="2.5" rx="3"/>
        <line x1="398" y1="152" x2="450" y2="104" stroke="var(--c-muted,#5a6072)" stroke-width="1"/>
        <text x="455" y="102" font-size="11" font-family="sans-serif" fill="var(--c-text,#1a1d27)">ここで売りシグナル</text>
        <text x="455" y="116" font-size="10" font-family="sans-serif" fill="var(--c-muted,#5a6072)">値段が平均線を下に抜けた</text>
        <line x1="300" y1="96" x2="600" y2="96" stroke="var(--c-red,#dc2626)" stroke-width="1" stroke-dasharray="5,3" opacity="0"/>
        <line x1="478" y1="140" x2="610" y2="140" stroke="var(--c-red,#dc2626)" stroke-width="1" stroke-dasharray="5,3"/>
        <text x="478" y="154" font-size="10" font-family="sans-serif" fill="var(--c-red,#dc2626)">損切り（直近の高値の少し上）</text>
        <line x1="478" y1="248" x2="610" y2="248" stroke="var(--c-green,#16a34a)" stroke-width="1" stroke-dasharray="5,3"/>
        <text x="478" y="262" font-size="10" font-family="sans-serif" fill="var(--c-green,#16a34a)">利益確定の目標（下のほう）</text>
        <text x="70" y="252" font-size="10" font-family="sans-serif" fill="var(--c-muted,#5a6072)">値上がりが続いたあと、勢いが弱まる</text>
      </svg>
      <p class="s-chart-note">※ 概念を示すイメージ図です（実際の値動きではありません）。売りシグナルには、ほかに「直近の安値の下抜け」などもあります。</p>
    </div>
    <div class="s-chart">
      <svg viewBox="0 0 640 310" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="株価指数の売りの勝率比較棒グラフ" style="width:100%;max-width:640px;display:block;margin:0 auto">
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
      <p class="s-chart-note">登録後の前向き（左から2本目）は43%の線を上回り、登録前（左端）は大きく下回りました。銘柄別の棒は回数が少なく、差が本物とは言えません。</p>
    </div>
  </section>

  <!-- 5. 注意 -->
  <section class="s-section">
    <h2>5. 結果を読むときの注意</h2>
    <ul style="padding-left:1.4em;margin-bottom:12px;">
      <li>この仮説は「株価指数の売りは負けやすい」かを確かめる形で登録しました。今のところ前向きの結果は、その疑いとは逆向きです。ただし、平均損益の幅はまだ0をまたいでいます。</li>
      <li>登録前の65回（27.7%）と、登録後の274回（49.3%）で、勝った割合が大きく違います。期間によって姿が変わる可能性があり、今の数字が続くとは限りません。</li>
      <li>流れ別・時間足別・銘柄別の表は、見比べるために並べたものです。区分を多く見るほど、偶然で良く見える区分が混ざります。</li>
      <li>株価指数の売りシグナルは、同じ相場の動きで複数の銘柄に同時に出ることがあります。回数のわりに、独立した場面の数は少ない可能性があります。</li>
      <li>勝った割合が高いことは、今後も勝てることを意味しません。この記事は売買をすすめるものではありません。</li>
    </ul>
  </section>

  <!-- 6. まとめ -->
  <section class="s-section">
    <h2>6. まとめ</h2>
    <ul style="padding-left:1.4em;margin-bottom:12px;">
      <li>前向き274回で、株価指数の売りは49.3%。とんとんの43%を、幅の低い端（43.4%）がわずかに上回りました。</li>
      <li>登録前の65回は27.7%で、前と後で姿が大きく変わっています。</li>
      <li>銘柄別では、日経平均先物が58.9%、英国の株価指数先物が37.9%でしたが、回数が足りず結論は出せません。</li>
      <li>結論は出さず、毎日の定点観測で見守ります。</li>
    </ul>
  </section>

  <!-- トラッカー -->
  <section class="s-section">
<!-- MW:TRACKER_TABLE -->
  </section>

'''
open('drafts/draft-signal-lab-131.html','w',encoding='utf-8').write(head+body+tail)
claims=[]
B={"group":"index","direction":"short"};FW={"fired_from":"2026-07-01"}
raw=json.load(open('drafts/labnotes/lab-131-raw.json'))
json.dump({"article_id":"131","asof":"2026-10-27T06:12:46+09:00","hypothesis_id":"auto_direction-short_group-index","claims":raw},open('drafts/labnotes/lab-131-claims.json','w'),ensure_ascii=False,indent=1)
