# -*- coding: utf-8 -*-
"""lab-150: 出口の相性ラボ 第7回（日足・MACDゴールデンの買い）。exit-lab.json から claims と下書きを組み立てる。"""
import json, re
ROOT = "/home/user/marketwatch-ai/"
lab = json.load(open(ROOT + "exit-lab.json", encoding="utf-8"))
E, T, S = "macd_golden", "1d", "long"

def cell(group, sl, tp, period="is"):
    for c in lab["cells"]:
        if (c["tf"], c["entry"], c["side"], c["group"], c["sl"], c["tp"], c["period"]) == (T, E, S, group, sl, tp, period):
            return c
    raise KeyError((group, sl, tp, period))

def r2(x): return round(x + 0.0, 2)
claims = []
def add(label, group, sl, tp, field, value, period="is"):
    claims.append({"label": label, "tf": T, "entry": E, "side": S, "group": group, "sl": sl, "tp": tp,
                   "period": period, "field": field, "value": value})

b = cell("all", "atr", "atr2")
add("全18銘柄 基準方式 平均R", "all", "atr", "atr2", "avg", r2(b["avg"]))
add("全18銘柄 基準方式 入口件数", "all", "atr", "atr2", "n_entries", b["n_entries"])
add("全18銘柄 基準方式 確定件数", "all", "atr", "atr2", "n", b["n"])
add("全18銘柄 基準方式 勝率%", "all", "atr", "atr2", "win", round(b["win"] * 100, 1))
for name, sl, tp in (("利確なし", "atr", "none"), ("シャンデリア損切り×真ん中の線利確", "chandelier", "bb_mid")):
    c = cell("all", sl, tp); v = c["vs_base"]
    add(name + " 平均R", "all", sl, tp, "avg", r2(c["avg"]))
    add(name + " vs_base", "all", sl, tp, "vs_base", r2(v["avg"]))
    add(name + " vs_base下限", "all", sl, tp, "vs_base_lo", r2(v["lo"]))
    add(name + " vs_base上限", "all", sl, tp, "vs_base_hi", r2(v["hi"]))
    add(name + " 件数", "all", sl, tp, "n", c["n"])
    add(name + " flag", "all", sl, tp, "flag", bool(c.get("flag")))
add("利確なし 勝率%", "all", "atr", "none", "win", round(cell("all", "atr", "none")["win"] * 100, 1))
for g, nm in (("index", "株価指数"), ("fx", "FX"), ("commodity", "コモディティ"), ("crypto", "ビットコイン")):
    c = cell(g, "atr", "atr2")
    add(nm + " 基準方式 平均R", g, "atr", "atr2", "avg", r2(c["avg"]))
    add(nm + " 基準方式 件数", g, "atr", "atr2", "n", c["n"])
f = cell("all", "atr", "atr2", "fwd")
add("前向き 入口件数", "all", "atr", "atr2", "n_entries", f["n_entries"], "fwd")
add("前向き 確定件数", "all", "atr", "atr2", "n", f["n"], "fwd")
json.dump({"article_id": "150", "exit_lab_asof": lab["asof"], "claims": claims},
          open(ROOT + "drafts/labnotes/lab-150-exit-claims.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump({"article_id": "150", "asof": "2026-11-15T06:13:00+09:00", "claims": []},
          open(ROOT + "drafts/labnotes/lab-150-claims.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

def sg(x):  # 符号つき2桁（U+2212）
    return ("+" if x > 0 else "−" if x < 0 else "") + "%.2f" % abs(x)
cn = {c["label"]: c["value"] for c in claims}
base_avg = cn["全18銘柄 基準方式 平均R"]; N = b["n"]; WIN = round(b["win"] * 100, 1)
no = cell("all", "atr", "none"); sw = cell("all", "chandelier", "bb_mid")
none_avg, none_vs, none_lo, none_hi, none_n = r2(no["avg"]), r2(no["vs_base"]["avg"]), r2(no["vs_base"]["lo"]), r2(no["vs_base"]["hi"]), no["n"]
sw_avg, sw_vs, sw_lo, sw_hi, sw_n = r2(sw["avg"]), r2(sw["vs_base"]["avg"]), r2(sw["vs_base"]["lo"]), r2(sw["vs_base"]["hi"]), sw["n"]
NOWIN = round(no["win"] * 100, 1)
G = {g: cell(g, "atr", "atr2") for g in ("index", "fx", "commodity", "crypto")}
Ga = {g: r2(G[g]["avg"]) for g in G}
fe, fn = f["n_entries"], f["n"]
assert base_avg > 0 and none_vs > 0 and sw_vs < 0 and all(v > 0 for v in Ga.values())

def cls(x): return "plus" if x > 0 else "minus"
TITLE = "日足でMACDがゴールデンクロスしたときの買いは、損切りと利確の組み合わせで結果は変わるか？ %d件で調べた【研究日誌 #150】" % N
DESC = ("日足でMACDの線がシグナル線を下から上へ抜けたときの買いで、損切りと利確の組み合わせを変えると成績が変わるかを%d件で調査。"
        "目立つ組み合わせは0件で、偶然の範囲内。研究日誌第150回。" % N)

tpl = open(ROOT + "drafts/draft-signal-lab-143.html", encoding="utf-8").read()
head_end = tpl.find("</style>")
head = tpl[:head_end]
OLD_T = "日足でMACDがデッドクロスしたときの売りは、損切りと利確の組み合わせで結果は変わるか？ 3616件で調べた【研究日誌 #143】"
OLD_D = "日足でMACDの線がシグナル線を上から下へ抜けたときの売りで、損切りと利確の組み合わせを変えると成績が変わるかを3616件で調査。目立つ組み合わせは0件で、偶然の範囲内。研究日誌第143回。"
assert OLD_T in head and OLD_D in head
head = head.replace(OLD_T, TITLE).replace(OLD_D, DESC)
head = head.replace("guide-signal-lab-143", "guide-signal-lab-150").replace("2026-11-08", "2026-11-15")
head = re.sub(r'(<meta name="keywords" content=")[^"]*', r"\g<1>MACD,ゴールデンクロス,買い,損切り,利確,出口の相性,日足,研究日誌", head)
assert "143" not in head and "デッド" not in head, [l for l in head.split("\n") if "143" in l or "デッド" in l]

M = lambda x: sg(x)
body = f'''</style>
</head>
<body>
<!-- ナビバー -->
<nav class="s-nav" aria-label="サイトナビ">
<div class="s-nav-inner"><div class="s-nav-grid">
<a class="s-nav-btn" href="index.html">🏠 ホーム</a>
<a class="s-nav-btn" href="political-feed.html">🚨 政治速報</a>
<a class="s-nav-btn current" href="track-record.html">🧪 シグナル研究</a>
<a class="s-nav-btn" href="calendar.html">📅 カレンダー</a>
<a class="s-nav-btn" href="guides.html">📚 解説記事</a>
<a class="s-nav-btn" href="guide-investment-books.html">📖 投資本</a>
<a class="s-nav-btn" href="market-health.html">🩺 市場の健康度</a>
<a class="s-nav-btn" href="hot-assets.html">🔥 急騰ランキング</a>
<a class="s-nav-btn" href="charts.html">📈 チャート</a>
<a class="s-nav-btn" href="youtube-summary.html">📺 YouTube要約</a>
</div></div>
</nav>

<!-- ヘッダー -->
<header class="s-hero"><div class="s-hero-inner">
<span class="s-tag">🧪 AIシグナル研究日誌</span>
<h1>{TITLE}</h1>
<p class="meta-line">公開：2026年11月15日 調査期間：2026年9月24日まで 出口の相性ラボ 第7回</p>
</div></header>

<main class="s-main">
<!-- ① kinsho-v1 免責バナー（3点必須） -->
<div class="disclaimer-banner s-note" data-disclaimer="kinsho-v1">
⚠️ この記事は情報提供を目的としています。投資の判断はご自身でお願いします。将来の成績を保証するものではありません。
</div>

<!-- 30秒まとめ -->
<div class="s-summary">
<div class="s-summary-head">⏱ 30秒でわかる今回のまとめ</div>
<ul>
<li>「MACD（短い期間と長い期間の平均の差で勢いを見る指標）の線がシグナル線を下から上へ抜けたら買う（日足のゴールデンクロス）」という入り方で、<strong>損切りと利確の組み合わせを72通り試した</strong>。探索期間（2026年9月24日まで）の{N}件が対象。</li>
<li>いまの方式（ATR（平均的な値動きの幅）の1.5倍で損切り・ATRの2倍で利確）の平均は<strong>損切り幅の{abs(base_avg):.2f}倍の益</strong>で、小さな益だった。</li>
<li>72通りの中に「統計的に目立つ」組み合わせは<strong>0件</strong>。偶然とは言いにくいほど良い（悪い）組み合わせは見つからなかった。</li>
<li>いまの方式より良く見えた組み合わせは「ATRの1.5倍で損切り＋利確を置かない」で、差は損切り幅の{none_vs:.2f}倍の改善。悪く見えた組み合わせは「シャンデリア（高値から一定の幅を追いかける損切り）＋ボリンジャーバンド（統計的なぶれ幅で引いた帯）の真ん中の線で利確」で、差は損切り幅の{abs(sw_vs):.2f}倍の悪化。どちらも旗立ての基準には届かなかった。</li>
<li>資産クラス別では、<strong>4つの分類すべてが益</strong>だった。いちばん大きいのはビットコインの損切り幅の{Ga["crypto"]:.2f}倍（件数が少ない参考値）、いちばん小さいのはFXの{Ga["fx"]:.2f}倍。</li>
<li>前向き（2026年9月25日以降）は入口がまだ{fe}件で、判断できる件数ではない。</li>
</ul>
</div>

<section class="s-section">
<h2>1. 今回の研究について</h2>
<p>日足で、MACD（短い平均と長い平均の差から、値動きの勢いの変わり目を見る指標）の線が、その平均であるシグナル線を下から上へ抜けると、買いのシグナル（ゴールデンクロス）が出ます。このとき、<strong>損切りの置き方と利益確定の場所をどう変えると成績が変わるか</strong>を調べました。買いなので、損切りは入口より下、利確は入口より上に置きます。</p>
<p>「出口の相性ラボ」シリーズの第7回です。第1回（ボリンジャーバンド下限タッチの買い）、第2回（高値ブレイクの買い）、第3回（安値ブレイクの売り）、第4回（移動平均線のデッドクロスの売り）、第5回（移動平均線のゴールデンクロスの買い）、第6回（MACDのデッドクロスの売り）に続き、日足の入口を順番に調べています。</p>
<p>対象は、2026年9月24日までに記録した日足（1日の足）の入口{N}件です。18銘柄（金・銀・原油・株価指数5本・FX9通貨ペア・ビットコイン）が対象です。</p>
<div class="s-note">
<strong>損益の単位について</strong> 損切りになったときの損を1とした倍数で表します。たとえば「損切り幅の{abs(base_avg):.2f}倍の益」なら、1回あたり平均で、損切り幅の{abs(base_avg):.2f}倍だけ勝っている計算になります。
</div>
<div class="s-chart">
<svg viewBox="0 0 700 320" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="MACDのゴールデンクロスの買いと損切り・利確の概念図" style="width:100%;max-width:700px;display:block;margin:0 auto">
<rect width="700" height="320" fill="var(--c-surface,#fff)" rx="6"/>
<text x="350" y="20" font-size="13" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)">MACDのゴールデンクロスの買い：入口と損切り・利確の置き方（概念図）</text>
<line x1="60" y1="90" x2="60" y2="130" stroke="var(--c-muted,#999)" stroke-width="1"/><rect x="51" y="96" width="18" height="26" fill="var(--c-red,#dc2626)" opacity=".75"/>
<line x1="115" y1="100" x2="115" y2="138" stroke="var(--c-muted,#999)" stroke-width="1"/><rect x="106" y="108" width="18" height="24" fill="var(--c-red,#dc2626)" opacity=".75"/>
<line x1="170" y1="112" x2="170" y2="148" stroke="var(--c-muted,#999)" stroke-width="1"/><rect x="161" y="120" width="18" height="22" fill="var(--c-red,#dc2626)" opacity=".75"/>
<line x1="225" y1="120" x2="225" y2="155" stroke="var(--c-muted,#999)" stroke-width="1"/><rect x="216" y="128" width="18" height="22" fill="var(--c-red,#dc2626)" opacity=".75"/>
<line x1="280" y1="118" x2="280" y2="158" stroke="var(--c-muted,#999)" stroke-width="1"/><rect x="271" y="128" width="18" height="20" fill="var(--c-green,#16a34a)" opacity=".75"/>
<line x1="335" y1="112" x2="335" y2="150" stroke="var(--c-muted,#999)" stroke-width="1"/><rect x="326" y="118" width="18" height="24" fill="var(--c-green,#16a34a)" opacity=".75"/>
<line x1="390" y1="104" x2="390" y2="142" stroke="var(--c-muted,#999)" stroke-width="1"/><rect x="381" y="110" width="18" height="24" fill="var(--c-green,#16a34a)" opacity=".75"/>
<line x1="445" y1="90" x2="445" y2="132" stroke="var(--c-muted,#999)" stroke-width="1"/><rect x="436" y="94" width="18" height="30" fill="var(--c-green,#16a34a)" opacity=".75"/>
<rect x="432" y="80" width="26" height="60" fill="none" stroke="#f97316" stroke-width="2.5" rx="2"/>
<line x1="405" y1="210" x2="440" y2="142" stroke="#f97316" stroke-width="1"/>
<text x="120" y="214" font-size="11" font-family="sans-serif" fill="#f97316" font-weight="bold">▲ MACDの線がシグナル線を下から上へ抜けた足＝買いの入口</text>
<line x1="470" y1="134" x2="700" y2="134" stroke="var(--c-red,#dc2626)" stroke-width="1.5" stroke-dasharray="4,3"/>
<text x="474" y="150" font-size="11" font-family="sans-serif" fill="var(--c-red,#dc2626)">🛑 損切り（ATRの1.5倍下・いまの方式）</text>
<line x1="470" y1="54" x2="700" y2="54" stroke="var(--c-green,#16a34a)" stroke-width="1.5" stroke-dasharray="4,3"/>
<text x="474" y="48" font-size="11" font-family="sans-serif" fill="var(--c-green,#16a34a)">✅ 利確（ATRの2倍上・いまの方式）</text>
<line x1="470" y1="76" x2="700" y2="76" stroke="#7c3aed" stroke-width="1.5" stroke-dasharray="4,3"/>
<text x="474" y="70" font-size="11" font-family="sans-serif" fill="#7c3aed">🔵 利確の別案（ボリンジャーの+2σ）</text>
<line x1="40" y1="232" x2="660" y2="232" stroke="var(--c-muted,#ddd)" stroke-width="1"/>
<polyline points="40,262 200,266 330,266 445,260 660,258" fill="none" stroke="var(--c-muted,#7a8092)" stroke-width="2"/>
<polyline points="40,282 200,278 330,270 420,262 445,257 660,238" fill="none" stroke="var(--c-accent,#2563eb)" stroke-width="2"/>
<text x="560" y="232" font-size="11" font-family="sans-serif" fill="var(--c-accent,#2563eb)">MACDの線</text>
<text x="500" y="278" font-size="11" font-family="sans-serif" fill="var(--c-muted,#7a8092)">シグナル線</text>
<text x="46" y="306" font-size="11" font-family="sans-serif" fill="var(--c-muted,#7a8092)">上段：価格のロウソク足　下段：MACD（交差の瞬間が入口）</text>
</svg>
<p class="s-chart-note">※ 概念を示すイメージ図です（実際の値動きではありません）。オレンジ枠が入口のロウソク足。</p>
</div>
</section>

<section class="s-section">
<h2>2. 探索期間（2026年9月24日まで）の結果</h2>
<h3>全18銘柄の数字</h3>
<p>探索期間に記録した入口は{b["n_entries"]}件、そのうち確定したのも<strong>{N}件</strong>です。基準方式（ATRの1.5倍で損切り・ATRの2倍で利確）での平均は<strong>損切り幅の{abs(base_avg):.2f}倍の益</strong>で、勝った割合は<strong>{WIN}%</strong>でした。</p>
<p>損切りの置き方8通りと利確の置き方9通りを掛け合わせて、合計72通りを調べましたが、「統計的に目立つ」と判定された組み合わせは<strong>0件</strong>でした。</p>
<p>目立つかどうかの基準は、癖のない値動きで同じ手順を何度も試しても、偶然で出る「目立つ」組み合わせが平均0.2マス程度になるように決めてあります（旗立て基準：差が損切り幅の0.15倍以上・前後半で同じ向き・多重検定の補正あり）。<strong>目立つ組が1マス程度なら、まだ偶然の可能性があります。</strong></p>
<h3>良く見えた組み合わせと悪く見えた組み合わせ</h3>
<p>組ごとに対象の入口が少しずつ違うので、平均どうしではなく「いまの方式との差」で比べます。件数が100件に届かない組は、数字のぶれが大きすぎるので並べていません。</p>
<div class="s-table-wrap">
<table class="s-table">
<thead><tr><th>損切りの方法</th><th>利確の方法</th><th>平均損益</th><th>基準との差</th><th>差のぶれ幅</th><th>件数</th><th>「目立つ」旗</th></tr></thead>
<tbody>
<tr class="base"><td>ATRの1.5倍（いまの方式）</td><td>ATRの2倍（いまの方式）</td><td class="{cls(base_avg)}">{M(base_avg)}</td><td>基準</td><td>—</td><td>{N}件</td><td>—</td></tr>
<tr><td>ATRの1.5倍</td><td>利確を置かない</td><td class="{cls(none_avg)}">{M(none_avg)}</td><td class="{cls(none_vs)}">{M(none_vs)}</td><td>{M(none_lo)}〜{M(none_hi)}</td><td>{none_n}件</td><td><span class="s-badge s-badge-note">なし</span></td></tr>
<tr><td>シャンデリア（22本の最高値から一定の幅を追いかける損切り）</td><td>ボリンジャーバンドの真ん中の線</td><td class="{cls(sw_avg)}">{M(sw_avg)}</td><td class="{cls(sw_vs)}">{M(sw_vs)}</td><td>{M(sw_lo)}〜{M(sw_hi)}</td><td>{sw_n}件</td><td><span class="s-badge s-badge-note">なし</span></td></tr>
</tbody>
</table>
</div>
<p>差が最も良く見えたのは「ATRの1.5倍で損切り＋利確を置かない」で、いまの方式より損切り幅の{none_vs:.2f}倍良く見えます。ただし差のぶれ幅は{M(none_lo)}〜{M(none_hi)}と広く、0に近い側まで含みます。勝った割合は{NOWIN}%と低く、まれに大きく伸びた取引が平均を押し上げている形です。72通りを同時に比べているので、旗が立つ基準はもっと厳しく、この組み合わせにも旗は立ちませんでした。逆に「シャンデリア＋真ん中の線で利確」は損切り幅の{abs(sw_vs):.2f}倍悪く見えますが、件数が{sw_n}件と少なく、差のぶれ幅も0をまたいでいます。こちらも旗は立ちませんでした。</p>
<div class="s-note">
<strong>組み合わせが多いと、偶然で良く見えるものが出ます。</strong> 今回は72通りを調べたので、本当は差がないのに「良さそう」「悪そう」と出る組み合わせが含まれている可能性があります。前向き（2026年9月25日以降）のデータで確かめることが大切です。
</div>
<div class="s-chart">
<svg viewBox="0 0 640 270" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="組み合わせ別の平均損益の比較（概念図）" style="width:100%;max-width:640px;display:block;margin:0 auto">
<rect width="640" height="270" fill="var(--c-surface,#fff)" rx="6"/>
<text x="320" y="20" font-size="12" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)">平均損益の比較（探索期間・全18銘柄・損切り幅を1とした倍数）</text>
<line x1="100" y1="60.0" x2="600" y2="60.0" stroke="var(--c-muted,#ddd)" stroke-width="1" stroke-dasharray="3,3"/>
<text x="94" y="64.0" font-size="10" font-family="sans-serif" fill="var(--c-muted,#999)" text-anchor="end">+0.5</text>
<line x1="100" y1="144.0" x2="600" y2="144.0" stroke="var(--c-muted,#ddd)" stroke-width="1" stroke-dasharray="3,3"/>
<text x="94" y="148.0" font-size="10" font-family="sans-serif" fill="var(--c-muted,#999)" text-anchor="end">+0.2</text>
<line x1="100" y1="200" x2="600" y2="200" stroke="var(--c-muted,#999)" stroke-width="1"/>
<text x="94" y="204" font-size="10" font-family="sans-serif" fill="var(--c-muted,#999)" text-anchor="end">0</text>
<rect x="145" y="{200 - 280*base_avg:.1f}" width="60" height="{280*base_avg:.1f}" fill="var(--c-accent,#2563eb)" opacity=".75" rx="2"/>
<rect x="255" y="{200 - 280*sw_avg:.1f}" width="60" height="{280*sw_avg:.1f}" fill="var(--c-red,#dc2626)" opacity=".75" rx="2"/>
<rect x="365" y="{200 - 280*none_avg:.1f}" width="60" height="{280*none_avg:.1f}" fill="var(--c-green,#16a34a)" opacity=".75" rx="2"/>
<text x="175" y="216" font-size="10" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#555)">いまの方式</text>
<text x="175" y="244" font-size="11" font-family="sans-serif" text-anchor="middle" fill="var(--c-accent,#2563eb)" font-weight="bold">{M(base_avg)}</text>
<text x="285" y="216" font-size="10" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#555)">シャンデリア損切り</text>
<text x="285" y="228" font-size="10" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#555)">＋真ん中の線</text>
<text x="285" y="244" font-size="11" font-family="sans-serif" text-anchor="middle" fill="var(--c-red,#dc2626)" font-weight="bold">{M(sw_avg)}</text>
<text x="395" y="216" font-size="10" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#555)">ATR損切り</text>
<text x="395" y="228" font-size="10" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#555)">＋利確なし</text>
<text x="395" y="244" font-size="11" font-family="sans-serif" text-anchor="middle" fill="var(--c-green,#16a34a)" font-weight="bold">{M(none_avg)}</text>
<text x="470" y="100" font-size="11" font-family="sans-serif" fill="var(--c-muted,#888)">「目立つ」旗の基準</text>
<text x="470" y="114" font-size="11" font-family="sans-serif" fill="var(--c-muted,#888)">を通った組：0件</text>
</svg>
<p class="s-chart-note">※ 概念を示すイメージ図です（実際の値動きではありません）。値はデータから算出。</p>
</div>
<h3>資産クラス別の結果（基準方式）</h3>
<p>株・FX・コモディティなどは値動きの性格が違うので、分けて見ます。</p>
<div class="s-table-wrap">
<table class="s-table">
<thead><tr><th>資産クラス</th><th>平均損益</th><th>件数</th></tr></thead>
<tbody>
<tr><td>株価指数（日経・米国株（S&amp;P500）・ナスダック・ダウ・英国株指数）</td><td class="{cls(Ga["index"])}">{M(Ga["index"])}</td><td>{G["index"]["n"]}件</td></tr>
<tr><td>FX（9通貨ペア）</td><td class="{cls(Ga["fx"])}">{M(Ga["fx"])}</td><td>{G["fx"]["n"]}件</td></tr>
<tr><td>コモディティ（金・銀・原油）</td><td class="{cls(Ga["commodity"])}">{M(Ga["commodity"])}</td><td>{G["commodity"]["n"]}件</td></tr>
<tr><td>ビットコイン（参考値・1銘柄）</td><td class="{cls(Ga["crypto"])}">{M(Ga["crypto"])}</td><td>{G["crypto"]["n"]}件</td></tr>
<tr class="base"><td>全18銘柄（合計）</td><td class="{cls(base_avg)}">{M(base_avg)}</td><td>{N}件</td></tr>
</tbody>
</table>
</div>
<p>4つの分類すべてがプラスでした。いちばん大きいのはビットコインの損切り幅の{Ga["crypto"]:.2f}倍の益ですが、{G["crypto"]["n"]}件しかないので参考値にとどまります。コモディティ（{M(Ga["commodity"])}）・株価指数（{M(Ga["index"])}）・FX（{M(Ga["fx"])}）が続きます。どれも小さな値で、件数が限られる分類は偶然のぶれも大きくなります。</p>
<div class="s-note">
探索期間のデータであり、前向き（2026年9月25日以降）で確かめるまで結論にはなりません。
</div>
</section>

<section class="s-section">
<h2>3. 前向き（2026年9月25日以降）の検証</h2>
<p>「出口の相性ラボ」の前向き検証は2026年9月25日から始まっています。今回の入口（日足のMACDゴールデンクロスの買い）は、前向きでは入口が<strong>{fe}件</strong>、確定したのは<strong>{fn}件</strong>です。件数が少なすぎるので、数字の良し悪しは判断できません。</p>
<p>前向きとは、結果を見る前に「どの組み合わせを確かめるか」を決めておき、その後に出たシグナルだけを数えるやり方です。探索期間の数字は、過去のデータを後から見た結果なので、偶然の良し悪しが混ざっています。前向きのデータが増えるまで、今回の組み合わせに結論は出しません。</p>
</section>

<section class="s-section">
<h2>4. 前向きトラッカーの現在地（2026年11月15日）</h2>
<p>すべての仮説の前向き結果を一覧しています。これらは「入口の種類」についての仮説で、今回調べた「出口の組み合わせ」とは別の検証です。</p>
<!-- MW:TRACKER_TABLE -->
<p style="font-size:13px;color:var(--c-muted);margin-top:8px">（全件は <a href="track-record.html#tracker">シグナル研究ページ</a> で確認できます）</p>
</section>

<section class="s-section">
<h2>5. まとめ</h2>
<p>今回の結論を正直に伝えます。</p>
<p><strong>探索期間のデータ（{N}件）では、損切りと利確の組み合わせを72通り変えても、統計的に目立つ組み合わせは0件でした。</strong>「ATRの1.5倍で損切り＋利確を置かない」はいまの方式より良く見え、「シャンデリア＋真ん中の線で利確」は悪く見えましたが、72通りを比べた中の偶然の可能性を消せません。</p>
<p>資産クラス別では、MACDのゴールデンクロスの買いは4つの分類すべてで小さな益でした。ただし、これは探索期間（過去のデータを後から見た期間）の数字で、前向きで確かめるまで結論ではありません。</p>
<p>前向きは入口{fe}件・確定{fn}件で、まだ何も言えません。件数がたまったら、また確かめます。</p>
</section>

<section class="s-section">
<h2>関連する解説</h2>
<div class="s-card-grid">
<div class="s-card"><h3><a href="guide-signal-anatomy.html">📊 発火条件の図解カタログ</a></h3><p>移動平均線の交差・高値ブレイク・RSI（値動きの勢いを表す指標）・MACD（勢いの変わり目を見る指標）など、シグナルの発火条件を図で説明しています。今回の「MACDのゴールデンクロス」の仕組みも確認できます。</p></div>
<div class="s-card"><h3><a href="guide-signal-lab-143.html">🧪 研究日誌 #143（第6回 出口の相性）</a></h3><p>MACDのデッドクロスの売りで、損切りと利確の組み合わせを調べた回です。</p></div>
<div class="s-card"><h3><a href="guide-signal-lab-136.html">🧪 研究日誌 #136（第5回 出口の相性）</a></h3><p>移動平均線のゴールデンクロスの買いで、損切りと利確の組み合わせを調べた回です。</p></div>
<div class="s-card"><h3><a href="track-record.html">🧪 シグナル研究のトップページ</a></h3><p>前向きトラッカーの全一覧と、過去の研究日誌をまとめて見られます。</p></div>
</div>
</section>
'''
foot = tpl[tpl.find("  <!-- kinsho-v1 免責 -->"):]
open(ROOT + "drafts/draft-signal-lab-150.html", "w", encoding="utf-8").write(head + body + "\n" + foot)
print("ok", N, base_avg, none_avg, none_vs, sw_avg, sw_vs, Ga, fe, fn)
