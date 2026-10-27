import re,json,sys
sys.path.insert(0,'.')
import signal_lab_verify as v
raw={r['label']:r for r in json.load(open('drafts/labnotes/lab-132-raw.json'))}
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
src=open('drafts/draft-signal-lab-131.html',encoding='utf-8').read()
head=src[:src.index('<main class="s-main">')]
tail=src[src.index('  <!-- 関連記事カード -->'):]
TITLE='円がからまない通貨ペアの買いは、前向きでも勝ちにくい？ 938回で確かめた現在地【研究日誌 #132】'
DESC='ユーロドル・ポンドドルなど、円がからまない通貨ペアの買いシグナルを、登録後の前向き938回で確認。勝った割合は40.8%、偶然のぶれを考えた幅は37.7%〜44.0%でした。'
head=re.sub(r'<title>.*?</title>',f'<title>{TITLE} - MarketWatch AI</title>',head)
head=re.sub(r'(<meta name="description" content=")[^"]*"',r'\g<1>'+DESC+'"',head)
head=re.sub(r'(<meta name="keywords" content=")[^"]*"',r'\g<1>通貨ペア,買い,シグナル研究,前向き検証,研究日誌"',head)
head=re.sub(r'(<meta property="og:title" content=")[^"]*"',r'\g<1>'+TITLE+'"',head)
head=re.sub(r'(<meta property="og:description" content=")[^"]*"',r'\g<1>'+DESC+'"',head)
head=re.sub(r'("headline": ")[^"]*"',r'\g<1>'+TITLE+'"',head)
head=re.sub(r'("description": ")[^"]*"',r'\g<1>'+DESC+'"',head)
head=head.replace('2026-10-27','2026-10-28').replace('guide-signal-lab-131','guide-signal-lab-132')
head=re.sub(r'<h1>.*?</h1>',f'<h1>{TITLE}</h1>',head)
head=re.sub(r'<p class="meta-line">公開：.*?</p>','<p class="meta-line">公開：2026年10月28日　前向き期間：2026年6月20日〜公開日まで　仮説登録日：2026年6月19日</p>',head)

bars=[("登録前","196回",pc('IS:その他FXの買い'),'var(--c-red,#dc2626)',0.55),
      ("登録後(前向き)","938回",pc('FWD:その他FXの買い'),'var(--c-accent,#2563eb)',0.85),
      ("買い全体(対照)","3349回",pc('FWD:買い全体'),'var(--c-accent,#2563eb)',0.35),
      ("円がらみの買い(対照)","720回",pc('FWD:円がからむFXの買い'),'var(--c-accent,#2563eb)',0.35),
      ("豪ドル米ドル","167回",pc('FWD:その他FXの買い AUDUSD=X'),'var(--c-green,#16a34a)',0.6),
      ("ユーロ豪ドル","226回",pc('FWD:その他FXの買い EURAUD=X'),'var(--c-red,#dc2626)',0.45)]
bs=''
for n,(lab,cnt,p,col,op) in enumerate(bars):
    x=90+n*85; h=3.6*p; y=265-h
    bs+=f'''        <rect x="{x}" y="{y:.1f}" width="60" height="{h:.1f}" fill="{col}" opacity="{op}" rx="3"/>
        <text x="{x+30}" y="{y-5:.1f}" font-size="11" font-family="sans-serif" text-anchor="middle" fill="{col}" font-weight="bold">{p}%</text>
        <text x="{x+30}" y="280" font-size="10" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)">{lab}</text>
        <text x="{x+30}" y="291" font-size="10" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)">{cnt}</text>
'''
t1=table(row('登録前の期間','IS:その他FXの買い')+row('登録後の前向き','FWD:その他FXの買い',True)+row('全期間（登録前と登録後の合計）','全期間:その他FXの買い')+row('対照：前向きの買いシグナル全体','FWD:買い全体')+row('対照：前向きの円がからむ通貨ペアの買い','FWD:円がからむFXの買い')+row('対照：前向きの円がからまない通貨ペアの売り','FWD:その他FXの売り')+row('対照：前向きの全シグナル','FWD:全シグナル'))
t2=table(row('上昇の流れ','FWD:その他FXの買い 上昇')+row('もみあい','FWD:その他FXの買い 中立・もみあい')+row('下降の流れ','FWD:その他FXの買い 下降'))
t3=table(row('1時間足','FWD:その他FXの買い 1h')+row('4時間足','FWD:その他FXの買い 4h')+row('日足（回数が少ない）','FWD:その他FXの買い 1d'))
t4=table(row('ユーロドル','FWD:その他FXの買い EURUSD=X')+row('ポンドドル','FWD:その他FXの買い GBPUSD=X')+row('豪ドル米ドル','FWD:その他FXの買い AUDUSD=X')+row('ユーロ豪ドル','FWD:その他FXの買い EURAUD=X')+row('ポンド豪ドル','FWD:その他FXの買い GBPAUD=X'))
body=f'''<main class="s-main">

  <!-- ① kinsho-v1 免責バナー（3点必須） -->
  <div class="disclaimer-banner s-note" data-disclaimer="kinsho-v1">
    ⚠️ 本記事は情報提供を目的としており、投資助言ではありません。当サイトは金融商品取引業者ではなく、投資助言・代理業の登録もしていません。投資判断はご自身の責任で行ってください。
  </div>

  <!-- 30秒まとめ -->
  <div class="s-summary">
    <div class="s-summary-head">⏱ 30秒でわかる今回のまとめ</div>
    <ul>
      <li>ユーロドルやポンドドルなど、円がからまない通貨ペアで出る「買い」シグナルを、登録後の前向きで確かめ直しました。</li>
      <li>前向き（2026年6月20日から）では、<strong>938回中383回が勝ち</strong>。勝った割合は<strong>40.8%</strong>でした。</li>
      <li>勝ち負けがとんとんになる勝率（43%）を下回っていますが、偶然のぶれを考えた幅は<strong>37.7%〜44.0%</strong>で、43%をまたいでいます。「負けやすい」とまでは言えません。</li>
      <li>登録前の196回は<strong>33.7%</strong>で、さらに低い数字でした。</li>
      <li>通貨ペア別では、豪ドル米ドルが<strong>45.5%</strong>、ユーロ豪ドルが<strong>35.4%</strong>と差がありましたが、見比べる数が多く、まだ結論は出せません。</li>
    </ul>
  </div>

  <!-- 1. 今回の問い -->
  <section class="s-section">
    <h2>1. 今日確かめた問い</h2>
    <p>このサイトは、円がからまない通貨ペア（ユーロドル・ポンドドル・豪ドル米ドル・ユーロ豪ドル・ポンド豪ドル）で出る買いシグナルを記録しています。買いシグナルは、値段が上がりそうな形になったときに出ます。</p>
    <p>「円がからまない通貨ペアの買いは、勝ちにくいのでは」という疑いを、2026年6月19日に仮説として登録しました。それより後に出たシグナルだけを数えるのが「前向き」です。回数が938回まで増えたので、現在地を確かめます。</p>
    <div class="s-note">
      <strong>💡 前向きとは</strong><br>
      仮説を登録した後に出たシグナルだけを数えることです。結果を見てから仮説を作っていないので、後付けの「勝てそう」を避けられます。
    </div>
  </section>

  <!-- 2. 調べ方 -->
  <section class="s-section">
    <h2>2. どのようにして調べたか</h2>
    <ul style="padding-left:1.4em;margin-bottom:12px;">
      <li>対象は、このサイトが記録している、円がからまない通貨ペアの買いシグナルです。結果が出たもの（利益確定か損切りに達したもの）だけを数えます。</li>
      <li>「勝ち」は、利益確定の目標に先に達したことです。損切りに先に達したら負けです。</li>
      <li>勝ち負けがとんとんになる勝率は43%です。損切り幅と利益確定幅の比から決まります。</li>
      <li>「偶然のぶれを考えた幅」は、統計でよく使われる計算で出しています。回数が少ないほど幅が広くなります。</li>
      <li>仮説を登録した日より前の記録は「登録前の期間」、後の記録は「登録後の前向き」として分けて数えます。</li>
    </ul>
  </section>

  <!-- 3. 結果 -->
  <section class="s-section">
    <h2>3. 結果</h2>
{t1}    <p>前向きの買いは938回で40.8%でした。とんとんの43%を下回っています。ただし、偶然のぶれの幅（37.7%〜44.0%）は43%をまたぐので、「負けやすい」と言い切れる段階ではありません。買いシグナル全体（42.7%）や円がからむ通貨ペアの買い（43.3%）と比べると、いくらか低めです。なお、これらの対照の中にも、このシグナル自体がふくまれている場合があります。</p>
    <p>登録前の196回は33.7%で、登録後より低い数字でした。どちらの期間でも、とんとんの43%には届いていません。</p>
    <h3>流れ別に見ると（前向きのみ）</h3>
{t2}    <p>3つの流れの差は小さく、偶然のぶれの幅は重なっています。下降の流れ（39.0%）がいちばん低いものの、流れによる違いは、今のところ読み取れません。</p>
    <h3>時間足別に見ると（前向きのみ）</h3>
{t3}    <p>1時間足は43.5%と、とんとんの近くです。4時間足は37.4%で低めでした。日足は44回しかなく、数字は参考になりません。足による差が本物かどうかは、まだ言えません。</p>
    <h3>通貨ペア別に見ると（前向きのみ）</h3>
{t4}    <p>豪ドル米ドル（45.5%）とポンドドル（44.7%）は43%を上回り、ユーロ豪ドル（35.4%）とユーロドル（36.8%）は下回りました。通貨ペアごとに5つ見ているので、偶然で良く見える・悪く見えるペアが混ざる可能性があります。特定の通貨ペアの買いが合う、合わない、という意味ではありません。</p>
    <p>トラッカーは登録日の当日から数えるため、記事の回数（938回）とトラッカーの回数（948回）は10回ずれます。トラッカーでは、1回あたりの平均損益は損切り幅の約0.04倍の損で、その幅はマイナス0.15倍からプラス0.06倍です。幅が0をまたぐので、まだ判定は出ていません。</p>
  </section>

  <!-- 4. 図 -->
  <section class="s-section">
    <h2>4. 図で見ると</h2>
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
      <svg viewBox="0 0 640 310" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="円がからまない通貨ペアの買いの勝率比較棒グラフ" style="width:100%;max-width:640px;display:block;margin:0 auto">
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
      <p class="s-chart-note">登録後の前向き（左から2本目）は43%の線の少し下で、登録前（左端）はさらに下でした。通貨ペア別の棒は回数が少なく、差が本物とは言えません。</p>
    </div>
  </section>

  <!-- 5. 注意 -->
  <section class="s-section">
    <h2>5. 結果を読むときの注意</h2>
    <ul style="padding-left:1.4em;margin-bottom:12px;">
      <li>この仮説は「円がからまない通貨ペアの買いは負けやすい」かを確かめる形で登録しました。前向きの数字は疑いの向きに近いものの、平均損益の幅が0をまたいでおり、確定はしていません。</li>
      <li>登録前の196回（33.7%）と登録後の938回（40.8%）で、勝った割合に差があります。期間によって姿が変わる可能性があり、今の数字が続くとは限りません。</li>
      <li>流れ別・時間足別・通貨ペア別の表は、見比べるために並べたものです。区分を多く見るほど、偶然で良く見える区分が混ざります。</li>
      <li>ユーロドルとユーロ豪ドルなど、同じ通貨が入った通貨ペアには、同じ相場の動きで同時にシグナルが出ることがあります。回数のわりに、独立した場面の数は少ない可能性があります。</li>
      <li>勝った割合が低いことは、今後も負けることを意味しません。この記事は売買をすすめるものではありません。</li>
    </ul>
  </section>

  <!-- 6. まとめ -->
  <section class="s-section">
    <h2>6. まとめ</h2>
    <ul style="padding-left:1.4em;margin-bottom:12px;">
      <li>前向き938回で、円がからまない通貨ペアの買いは40.8%。とんとんの43%を下回りましたが、偶然のぶれの幅（37.7%〜44.0%）は43%をまたいでいます。</li>
      <li>登録前の196回は33.7%で、どちらの期間もとんとんには届いていません。</li>
      <li>通貨ペア別では、豪ドル米ドルが45.5%、ユーロ豪ドルが35.4%でしたが、見比べる数が多く結論は出せません。</li>
      <li>結論は出さず、毎日の定点観測で見守ります。</li>
    </ul>
  </section>

  <!-- トラッカー -->
  <section class="s-section">
<!-- MW:TRACKER_TABLE -->
  </section>

'''
open('drafts/draft-signal-lab-132.html','w',encoding='utf-8').write(head+body+tail)
json.dump({"article_id":"132","asof":"2026-10-28T06:15:30+09:00","hypothesis_id":"auto_direction-long_group-other_fx","claims":list(raw.values())},open('drafts/labnotes/lab-132-claims.json','w'),ensure_ascii=False,indent=1)
