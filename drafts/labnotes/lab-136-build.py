# -*- coding: utf-8 -*-
"""lab-136: 出口の相性ラボ 第5回（日足・MAゴールデンの買い）。exit-lab.json から claims と下書きを組み立てる。"""
import json, re
ROOT = "/home/user/marketwatch-ai/"
lab = json.load(open(ROOT + "exit-lab.json", encoding="utf-8"))
E, T, S = "ma_golden", "1d", "long"

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
for name, sl, tp in (("利確なし", "atr", "none"), ("25本線割れ損切り×直近高値利確", "ma", "swing")):
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
json.dump({"article_id": "136", "exit_lab_asof": lab["asof"], "claims": claims},
          open(ROOT + "drafts/labnotes/lab-136-exit-claims.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump({"article_id": "136", "asof": "2026-11-01T06:14:00+09:00", "claims": []},
          open(ROOT + "drafts/labnotes/lab-136-claims.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

def sg(x):  # 符号つき2桁（U+2212）
    return ("＋" if False else ("+" if x > 0 else "−" if x < 0 else "")) + "%.2f" % abs(x)
cn = {c["label"]: c["value"] for c in claims}
base_avg = cn["全18銘柄 基準方式 平均R"]; N = b["n"]; WIN = round(b["win"] * 100, 1)
no = cell("all", "atr", "none"); sw = cell("all", "ma", "swing")
none_avg, none_vs, none_lo, none_hi, none_n = r2(no["avg"]), r2(no["vs_base"]["avg"]), r2(no["vs_base"]["lo"]), r2(no["vs_base"]["hi"]), no["n"]
sw_avg, sw_vs, sw_lo, sw_hi, sw_n = r2(sw["avg"]), r2(sw["vs_base"]["avg"]), r2(sw["vs_base"]["lo"]), r2(sw["vs_base"]["hi"]), sw["n"]
NOWIN = round(no["win"] * 100, 1)
G = {g: cell(g, "atr", "atr2") for g in ("index", "fx", "commodity", "crypto")}
Ga = {g: r2(G[g]["avg"]) for g in G}
fe, fn = f["n_entries"], f["n"]

def cls(x): return "plus" if x > 0 else "minus"
TITLE = "日足で移動平均線のゴールデンクロスの買いをするとき、損切りと利確の組み合わせで結果は変わるか？ %d件で調べた【研究日誌 #136】" % N
DESC = ("日足で25本線が75本線を下から上へ抜けたときの買いで、損切りと利確の組み合わせを変えると成績が変わるかを%d件で調査。"
        "目立つ組み合わせは0件で、偶然の範囲内。研究日誌第136回。" % N)

tpl = open(ROOT + "drafts/draft-signal-lab-129.html", encoding="utf-8").read()
head_end = tpl.find("</style>")
head = tpl[:head_end]
head = head.replace("129", "136").replace("2026-10-25", "2026-11-01")
old_title = "日足で移動平均線のデッドクロスの売りをするとき、損切りと利確の組み合わせで結果は変わるか？ 724件で調べた【研究日誌 #129】"
head = head.replace(old_title.replace("129", "136"), TITLE)
head = re.sub(r'(<meta name="description" content=")[^"]*', r"\g<1>" + DESC, head)
head = re.sub(r'(<meta property="og:description" content=")[^"]*', r"\g<1>" + DESC, head)
head = re.sub(r'("description": ")[^"]*', r"\g<1>" + DESC, head)
head = re.sub(r'(<meta name="keywords" content=")[^"]*', r"\g<1>移動平均線,ゴールデンクロス,買い,損切り,利確,出口の相性,日足,研究日誌", head)
assert "デッドクロス" not in head and "724" not in head, head[:3000]

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
<p class="meta-line">公開：2026年11月1日 調査期間：2026年9月24日まで 出口の相性ラボ 第5回</p>
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
<li>「25本線が75本線を下から上へ抜けたら買う（日足のゴールデンクロス）」という入り方で、<strong>損切りと利確の組み合わせを72通り試した</strong>。探索期間（2026年9月24日まで）の{N}件が対象。</li>
<li>いまの方式（ATR（平均的な値動きの幅）の1.5倍で損切り・ATRの2倍で利確）の平均は<strong>損切り幅の{abs(base_avg):.2f}倍の損</strong>で、ほぼ収支ゼロだった。</li>
<li>72通りの中に「統計的に目立つ」組み合わせは<strong>0件</strong>。偶然とは言いにくいほど良い（悪い）組み合わせは見つからなかった。</li>
<li>いまの方式より良く見えた組み合わせは「利確を置かない」で、差は損切り幅の{none_vs:.2f}倍。ただしぶれ幅が大きく、0をまたいでいる。悪く見えた組み合わせは「25本線割れで損切り＋直近の高値で利確」で、差は損切り幅の{abs(sw_vs):.2f}倍の悪化。どちらも旗立ての基準には届かなかった。</li>
<li>資産クラス別では、<strong>FXだけが損切り幅の{abs(Ga["fx"]):.2f}倍の損</strong>で、株価指数・コモディティ・ビットコインはプラスだった。</li>
<li>前向き（2026年9月25日以降）は入口がまだ{fe}件で、判断できる件数ではない。</li>
</ul>
</div>

<section class="s-section">
<h2>1. 今回の研究について</h2>
<p>日足で、短い平均線（25本線）が長い平均線（75本線）を下から上へ抜けると、買いのシグナル（ゴールデンクロス）が出ます。このとき、<strong>損切りの置き方と利益確定の場所をどう変えると成績が変わるか</strong>を調べました。</p>
<p>「出口の相性ラボ」シリーズの第5回です。第1回（ボリンジャーバンド（統計的なぶれ幅で引いた帯）下限タッチの買い）、第2回（高値ブレイクの買い）、第3回（安値ブレイクの売り）、第4回（デッドクロスの売り）に続き、日足の入口を順番に調べています。</p>
<p>対象は、2026年9月24日までに記録した日足（1日の足）の入口{N}件です。18銘柄（金・銀・原油・株価指数5本・FX9通貨ペア・ビットコイン）が対象です。</p>
<div class="s-note">
<strong>損益の単位について</strong> 損切りになったときの損を1とした倍数で表します。たとえば「損切り幅の{abs(base_avg):.2f}倍の損」なら、1回あたり平均で、損切り幅の{abs(base_avg):.2f}倍だけ負けている計算になります。
</div>
<div class="s-chart">
<svg viewBox="0 0 700 320" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="移動平均線のゴールデンクロスの買いと損切り・利確の概念図" style="width:100%;max-width:700px;display:block;margin:0 auto">
<rect width="700" height="320" fill="var(--c-surface,#fff)" rx="6"/>
<text x="350" y="22" font-size="13" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)">ゴールデンクロスの買い：入口と損切り・利確の置き方（概念図）</text>
<polyline points="40,190 300,185 660,130" fill="none" stroke="var(--c-muted,#7a8092)" stroke-width="2"/>
<polyline points="40,250 200,228 380,183 660,80" fill="none" stroke="var(--c-accent,#2563eb)" stroke-width="2"/>
<text x="46" y="280" font-size="11" font-family="sans-serif" fill="var(--c-accent,#2563eb)">25本線（短い平均線）</text>
<text x="46" y="176" font-size="11" font-family="sans-serif" fill="var(--c-muted,#7a8092)">75本線（長い平均線）</text>
<line x1="60" y1="232" x2="60" y2="262" stroke="var(--c-muted,#999)" stroke-width="1"/><rect x="51" y="240" width="18" height="16" fill="var(--c-red,#dc2626)" opacity=".75"/>
<line x1="115" y1="226" x2="115" y2="256" stroke="var(--c-muted,#999)" stroke-width="1"/><rect x="106" y="236" width="18" height="10" fill="var(--c-green,#16a34a)" opacity=".75"/>
<line x1="170" y1="224" x2="170" y2="252" stroke="var(--c-muted,#999)" stroke-width="1"/><rect x="161" y="232" width="18" height="14" fill="var(--c-red,#dc2626)" opacity=".75"/>
<line x1="225" y1="210" x2="225" y2="238" stroke="var(--c-muted,#999)" stroke-width="1"/><rect x="216" y="216" width="18" height="12" fill="var(--c-green,#16a34a)" opacity=".75"/>
<line x1="280" y1="198" x2="280" y2="224" stroke="var(--c-muted,#999)" stroke-width="1"/><rect x="271" y="204" width="18" height="14" fill="var(--c-green,#16a34a)" opacity=".75"/>
<line x1="335" y1="184" x2="335" y2="208" stroke="var(--c-muted,#999)" stroke-width="1"/><rect x="326" y="190" width="18" height="6" fill="var(--c-red,#dc2626)" opacity=".75"/>
<line x1="390" y1="166" x2="390" y2="194" stroke="var(--c-muted,#999)" stroke-width="1"/><rect x="381" y="172" width="18" height="16" fill="var(--c-green,#16a34a)" opacity=".75"/>
<line x1="445" y1="128" x2="445" y2="172" stroke="var(--c-muted,#999)" stroke-width="1"/><rect x="436" y="136" width="18" height="28" fill="var(--c-green,#16a34a)" opacity=".75"/>
<rect x="432" y="122" width="26" height="56" fill="none" stroke="#f97316" stroke-width="2.5" rx="2"/>
<line x1="405" y1="288" x2="440" y2="182" stroke="#f97316" stroke-width="1"/>
<text x="150" y="300" font-size="11" font-family="sans-serif" fill="#f97316" font-weight="bold">▲ 25本線が75本線を下から上へ抜けた足＝買いの入口</text>
<line x1="470" y1="178" x2="700" y2="178" stroke="var(--c-red,#dc2626)" stroke-width="1.5" stroke-dasharray="4,3"/>
<text x="474" y="196" font-size="11" font-family="sans-serif" fill="var(--c-red,#dc2626)">🛑 損切り（ATRの1.5倍下・いまの方式）</text>
<line x1="470" y1="100" x2="700" y2="100" stroke="var(--c-green,#16a34a)" stroke-width="1.5" stroke-dasharray="4,3"/>
<text x="474" y="95" font-size="11" font-family="sans-serif" fill="var(--c-green,#16a34a)">✅ 利確（ATRの2倍上・いまの方式）</text>
<line x1="470" y1="56" x2="700" y2="56" stroke="#7c3aed" stroke-width="1.5" stroke-dasharray="4,3"/>
<text x="474" y="51" font-size="11" font-family="sans-serif" fill="#7c3aed">🔵 利確の別案（ボリンジャーバンド+2σ）</text>
</svg>
<p class="s-chart-note">※ 概念を示すイメージ図です（実際の値動きではありません）。オレンジ枠が入口のロウソク足。</p>
</div>
</section>

<section class="s-section">
<h2>2. 探索期間（2026年9月24日まで）の結果</h2>
<h3>全18銘柄の数字</h3>
<p>探索期間に記録した入口は{b["n_entries"]}件、そのうち確定したのも<strong>{N}件</strong>です。基準方式（ATRの1.5倍で損切り・ATRの2倍で利確）での平均は<strong>損切り幅の{abs(base_avg):.2f}倍の損</strong>で、勝った割合は<strong>{WIN}%</strong>でした。</p>
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
<tr><td>25本線を終値で割ったら</td><td>直近20本の高値（節目）</td><td class="{cls(sw_avg)}">{M(sw_avg)}</td><td class="{cls(sw_vs)}">{M(sw_vs)}</td><td>{M(sw_lo)}〜{M(sw_hi)}</td><td>{sw_n}件</td><td><span class="s-badge s-badge-note">なし</span></td></tr>
</tbody>
</table>
</div>
<p>「利確を置かない」は、いまの方式より損切り幅の{none_vs:.2f}倍良く見えます。ただし、勝った割合は{NOWIN}%と低く、たまに大きく伸びた取引が平均を引き上げている形です。差のぶれ幅は{M(none_lo)}〜{M(none_hi)}と広く、0をまたいでいるので、偶然の可能性を消せません。逆に「25本線割れで損切り＋直近の高値で利確」は損切り幅の{abs(sw_vs):.2f}倍悪く見えますが、こちらも0をまたいでいます。どちらも「目立つ」旗は立ちませんでした。</p>
<div class="s-note">
<strong>組み合わせが多いと、偶然で良く見えるものが出ます。</strong> 今回は72通りを調べたので、本当は差がないのに「良さそう」と出る組み合わせが含まれている可能性があります。前向き（2026年9月25日以降）のデータで確かめることが大切です。
</div>
<div class="s-chart">
<svg viewBox="0 0 640 270" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="組み合わせ別の平均損益の比較（概念図）" style="width:100%;max-width:640px;display:block;margin:0 auto">
<rect width="640" height="270" fill="var(--c-surface,#fff)" rx="6"/>
<text x="320" y="20" font-size="12" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#5a6072)">平均損益の比較（探索期間・全18銘柄・損切り幅を1とした倍数）</text>
<line x1="100" y1="82.0" x2="600" y2="82.0" stroke="var(--c-muted,#ddd)" stroke-width="1" stroke-dasharray="3,3"/>
<text x="94" y="86.0" font-size="10" font-family="sans-serif" fill="var(--c-muted,#999)" text-anchor="end">+0.6</text>
<line x1="100" y1="118.0" x2="600" y2="118.0" stroke="var(--c-muted,#ddd)" stroke-width="1" stroke-dasharray="3,3"/>
<text x="94" y="122.0" font-size="10" font-family="sans-serif" fill="var(--c-muted,#999)" text-anchor="end">+0.4</text>
<line x1="100" y1="154.0" x2="600" y2="154.0" stroke="var(--c-muted,#ddd)" stroke-width="1" stroke-dasharray="3,3"/>
<text x="94" y="158.0" font-size="10" font-family="sans-serif" fill="var(--c-muted,#999)" text-anchor="end">+0.2</text>
<line x1="100" y1="190" x2="600" y2="190" stroke="var(--c-muted,#999)" stroke-width="1"/>
<text x="94" y="194" font-size="10" font-family="sans-serif" fill="var(--c-muted,#999)" text-anchor="end">0</text>
<rect x="145" y="{190 - 180*max(base_avg,0):.1f}" width="60" height="{max(abs(base_avg)*180,1):.1f}" fill="var(--c-accent,#2563eb)" opacity=".75" rx="2"/>
<rect x="255" y="{190 - 180*none_avg:.1f}" width="60" height="{180*none_avg:.1f}" fill="var(--c-green,#16a34a)" opacity=".75" rx="2"/>
<rect x="365" y="190" width="60" height="{abs(sw_avg)*180:.1f}" fill="var(--c-red,#dc2626)" opacity=".75" rx="2"/>
<text x="175" y="220" font-size="10" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#555)">いまの方式</text>
<text x="175" y="236" font-size="11" font-family="sans-serif" text-anchor="middle" fill="var(--c-red,#dc2626)" font-weight="bold">{M(base_avg)}</text>
<text x="285" y="220" font-size="10" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#555)">ATR損切り＋利確なし</text>
<text x="285" y="236" font-size="11" font-family="sans-serif" text-anchor="middle" fill="var(--c-green,#16a34a)" font-weight="bold">{M(none_avg)}</text>
<text x="395" y="220" font-size="10" font-family="sans-serif" text-anchor="middle" fill="var(--c-muted,#555)">25本線割れ＋高値利確</text>
<text x="395" y="236" font-size="11" font-family="sans-serif" text-anchor="middle" fill="var(--c-red,#dc2626)" font-weight="bold">{M(sw_avg)}</text>
<text x="470" y="60" font-size="11" font-family="sans-serif" fill="var(--c-muted,#888)">「目立つ」旗の基準</text>
<text x="470" y="74" font-size="11" font-family="sans-serif" fill="var(--c-muted,#888)">を通った組：0件</text>
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
<p><strong>FXだけが損切り幅の{abs(Ga["fx"]):.2f}倍の損</strong>で、コモディティ（{M(Ga["commodity"])}）・ビットコイン（{M(Ga["crypto"])}）・株価指数（{M(Ga["index"])}）はプラスでした。ビットコインは{G["crypto"]["n"]}件しかないので参考値にとどまります。資産クラス別の「目立つ」基準は、件数200以上かつ差が損切り幅の0.25倍以上とさらに厳しくしてあります。今回は、どのクラスにも目立つ組み合わせはありませんでした。</p>
<div class="s-note">
探索期間のデータであり、前向き（2026年9月25日以降）で確かめるまで結論にはなりません。
</div>
</section>

<section class="s-section">
<h2>3. 前向き（2026年9月25日以降）の検証</h2>
<p>「出口の相性ラボ」の前向き検証は2026年9月25日から始まっています。今回の入口（日足のゴールデンクロスの買い）は、前向きでは入口が<strong>{fe}件</strong>、確定したのは<strong>{fn}件</strong>です。件数が少なすぎるので、数字の良し悪しは判断できません。</p>
<p>前向きとは、結果を見る前に「どの組み合わせを確かめるか」を決めておき、その後に出たシグナルだけを数えるやり方です。探索期間の数字は、過去のデータを後から見た結果なので、偶然の良し悪しが混ざっています。前向きのデータが増えるまで、今回の組み合わせに結論は出しません。</p>
</section>

<section class="s-section">
<h2>4. 前向きトラッカーの現在地（2026年11月1日）</h2>
<p>すべての仮説の前向き結果を一覧しています。これらは「入口の種類」についての仮説で、今回調べた「出口の組み合わせ」とは別の検証です。</p>
<!-- MW:TRACKER_TABLE -->
<p style="font-size:13px;color:var(--c-muted);margin-top:8px">（全件は <a href="track-record.html#tracker">シグナル研究ページ</a> で確認できます）</p>
</section>

<section class="s-section">
<h2>5. まとめ</h2>
<p>今回の結論を正直に伝えます。</p>
<p><strong>探索期間のデータ（{N}件）では、損切りと利確の組み合わせを72通り変えても、統計的に目立つ組み合わせは0件でした。</strong>「利確を置かない」はいまの方式より良く見えましたが、ぶれ幅が0をまたいでおり、偶然の可能性を消せません。</p>
<p>資産クラス別では、FXのゴールデンクロスの買いだけが損切り幅の{abs(Ga["fx"]):.2f}倍の損でした。ただし、これは探索期間（過去のデータを後から見た期間）の数字で、前向きで確かめるまで結論ではありません。</p>
<p>前向きは入口{fe}件・確定{fn}件で、まだ何も言えません。件数がたまったら、また確かめます。</p>
</section>

<section class="s-section">
<h2>関連する解説</h2>
<div class="s-card-grid">
<div class="s-card"><h3><a href="guide-signal-anatomy.html">📊 発火条件の図解カタログ</a></h3><p>移動平均線の交差・高値ブレイク・RSI（値動きの勢いを表す指標）・MACD（勢いの変わり目を見る指標）など、シグナルの発火条件を図で説明しています。今回の「ゴールデンクロス」の仕組みも確認できます。</p></div>
<div class="s-card"><h3><a href="guide-signal-lab-129.html">🧪 研究日誌 #129（第4回 出口の相性）</a></h3><p>デッドクロスの売りで、損切りと利確の組み合わせを調べた回です。</p></div>
<div class="s-card"><h3><a href="guide-signal-lab-117.html">🧪 研究日誌 #117（第2回 出口の相性）</a></h3><p>高値ブレイクの買いで、損切りと利確の組み合わせを調べた回です。</p></div>
<div class="s-card"><h3><a href="track-record.html">🧪 シグナル研究のトップページ</a></h3><p>前向きトラッカーの全一覧と、過去の研究日誌をまとめて見られます。</p></div>
</div>
</section>
'''
foot = tpl[tpl.find("  <!-- kinsho-v1 免責 -->"):]
open(ROOT + "drafts/draft-signal-lab-136.html", "w", encoding="utf-8").write(head + body + "\n" + foot)
print("ok", N, base_avg, none_avg, none_vs, sw_avg, sw_vs, Ga, fe, fn)
