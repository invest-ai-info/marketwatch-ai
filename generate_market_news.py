"""
毎朝マーケットニュース自動生成スクリプト（歴史的イベント年表付き）
yfinance で価格データ取得、Chart.js でチャート表示
"""

import yfinance as yf
import json
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))

# ─────────────────────────────────────────
# 歴史的イベントデータ（1971〜）
# ─────────────────────────────────────────
HISTORICAL_EVENTS = [
    {"date": "1971-08", "label": "ニクソンショック",       "desc": "米ドルと金の兌換停止。変動相場制へ移行。ドル円が急落し360円台から100円台への長期円高が始まった。",           "assets": ["usdjpy", "gold"]},
    {"date": "1973-11", "label": "第一次オイルショック",   "desc": "OAPEC原油禁輸。原油価格が約4倍に急騰。世界的インフレと株安を引き起こした。",                            "assets": ["nikkei", "sp500", "gold"]},
    {"date": "1979-02", "label": "第二次オイルショック",   "desc": "イラン革命で原油供給が激減。原油価格が再び急騰し世界経済を直撃した。",                                   "assets": ["nikkei", "sp500", "gold"]},
    {"date": "1985-09", "label": "プラザ合意",             "desc": "G5がドル高是正で合意。ドル円が240円台から120円台へと急落する大規模な円高が進行した。",                    "assets": ["usdjpy", "nikkei"]},
    {"date": "1987-10", "label": "ブラックマンデー",       "desc": "ニューヨーク株式市場で1日に22.6%の暴落。世界同時株安となり日経平均も翌日約15%下落した。",               "assets": ["nikkei", "sp500"]},
    {"date": "1990-01", "label": "日本バブル崩壊",         "desc": "日経平均が38,915円のピークから急落開始。失われた30年の始まりとなった歴史的な大暴落。",                    "assets": ["nikkei"]},
    {"date": "1995-01", "label": "阪神大震災・円高",       "desc": "阪神淡路大震災後に円が急騰し1ドル=79円台の史上最高値を記録。日経平均も急落した。",                        "assets": ["nikkei", "usdjpy"]},
    {"date": "1997-07", "label": "アジア通貨危機",         "desc": "タイバーツ暴落から始まったアジア通貨危機が日本の金融機関にも波及。山一証券など相次いで破綻した。",          "assets": ["nikkei", "usdjpy"]},
    {"date": "1998-08", "label": "ロシア財政危機/LTCM",   "desc": "ロシアがデフォルト宣言。ヘッジファンドLTCM破綻。世界的な信用収縮とドル安・円高が加速した。",              "assets": ["nikkei", "sp500", "usdjpy"]},
    {"date": "2000-03", "label": "ITバブル崩壊",           "desc": "NASDAQが5,048の最高値から急落。ITバブルが崩壊し2002年まで世界的な株安が続いた。",                       "assets": ["nikkei", "sp500"]},
    {"date": "2001-09", "label": "9.11テロ",               "desc": "米同時多発テロ。ニューヨーク市場が1週間閉鎖。再開後に株価が急落し金が安全資産として買われた。",            "assets": ["nikkei", "sp500", "gold"]},
    {"date": "2003-03", "label": "イラク戦争",             "desc": "米英軍がイラク侵攻を開始。地政学リスクが高まり原油・金価格が乱高下した。",                               "assets": ["gold", "nikkei"]},
    {"date": "2008-09", "label": "リーマンショック",       "desc": "リーマン・ブラザーズ経営破綻で世界金融危機が勃発。日経平均はピークから約60%、S&P500は約57%下落した。",   "assets": ["nikkei", "sp500", "usdjpy", "gold"]},
    {"date": "2010-05", "label": "欧州債務危機",           "desc": "ギリシャ財政危機が欧州全体に波及。ユーロが急落し世界的なリスクオフの動きが強まった。",                    "assets": ["nikkei", "sp500", "gold"]},
    {"date": "2011-03", "label": "東日本大震災",           "desc": "東日本大震災・福島原発事故。日経平均が約20%急落し円が急騰。一時1ドル=76円台の超円高を記録した。",        "assets": ["nikkei", "usdjpy"]},
    {"date": "2013-04", "label": "アベノミクス/異次元緩和","desc": "日銀が異次元金融緩和を発表。円安・株高が一気に加速し日経平均は約2年で倍増した。",                        "assets": ["nikkei", "usdjpy"]},
    {"date": "2015-08", "label": "チャイナショック",       "desc": "中国株式市場の急落が世界に波及。VIX指数が急騰し日経平均は1週間で約11%下落した。",                        "assets": ["nikkei", "sp500"]},
    {"date": "2016-06", "label": "Brexit国民投票",         "desc": "英国がEU離脱を決定。ポンドが急落し世界株安・円高が進行。市場の想定外の結果に衝撃が走った。",             "assets": ["nikkei", "sp500", "gold"]},
    {"date": "2016-11", "label": "トランプ大統領当選",     "desc": "トランプ当選後に「トランプラリー」が発生。米株・ドル高・日本株が大きく上昇した。",                        "assets": ["nikkei", "sp500", "usdjpy"]},
    {"date": "2018-12", "label": "米中貿易戦争",           "desc": "米中貿易摩擦が激化。S&P500が年末にかけて約20%急落し世界の株式市場が動揺した。",                          "assets": ["nikkei", "sp500"]},
    {"date": "2020-02", "label": "コロナショック",         "desc": "新型コロナパンデミック宣言。世界の株式市場が約1ヶ月で30〜40%急落。史上最速の弱気相場入りとなった。",      "assets": ["nikkei", "sp500", "usdjpy", "gold"]},
    {"date": "2022-02", "label": "ロシア・ウクライナ侵攻", "desc": "ロシアがウクライナに軍事侵攻。原油・天然ガス・金価格が急騰し世界的なインフレ加速の引き金となった。",       "assets": ["nikkei", "sp500", "gold"]},
    {"date": "2022-03", "label": "FRB急速利上げ開始",     "desc": "FRBがゼロ金利政策を終了し急速な利上げを開始。債券・株式が同時下落し円は対ドルで30年ぶりの円安に。",      "assets": ["nikkei", "sp500", "usdjpy", "gold"]},
    {"date": "2023-03", "label": "SVB破綻",               "desc": "シリコンバレーバンク破綻。米地銀への信用不安が拡大。金が安全資産として急騰した。",                        "assets": ["nikkei", "sp500", "gold"]},
    {"date": "2024-08", "label": "日経平均歴史的暴落",     "desc": "日経平均が1日で-4,451円（-12.4%）の歴史的暴落。円キャリートレード巻き戻しで円が急騰した。",              "assets": ["nikkei", "usdjpy"]},
]

# ─────────────────────────────────────────
# データ取得関数
# ─────────────────────────────────────────
def get_price(ticker_symbol):
    try:
        t = yf.Ticker(ticker_symbol)
        hist = t.history(period="2d")
        if len(hist) < 2:
            return None, None, None
        prev = hist["Close"].iloc[-2]
        last = hist["Close"].iloc[-1]
        return last, prev, (last - prev) / prev * 100
    except Exception:
        return None, None, None

def get_historical_monthly(ticker, start="1975-01-01"):
    try:
        t = yf.Ticker(ticker)
        hist = t.history(start=start)
        if hist.empty:
            return [], []
        monthly = hist["Close"].resample("ME").last().dropna()
        dates  = [d.strftime("%Y-%m") for d in monthly.index]
        prices = [round(float(v), 2) for v in monthly.values]
        return dates, prices
    except Exception:
        return [], []

def fmt_price(val, decimals=2, prefix="", suffix=""):
    if val is None:
        return "N/A"
    return f"{prefix}{val:,.{decimals}f}{suffix}"

def fmt_change(pct):
    if pct is None:
        return ""
    sign = "▲" if pct >= 0 else "▼"
    cls  = "up" if pct >= 0 else "down"
    return f'<span class="{cls} price-change">{sign}{abs(pct):.2f}%</span>'

def sentiment(changes):
    ups   = sum(1 for c in changes if c and c > 0)
    downs = sum(1 for c in changes if c and c < 0)
    if ups > downs:
        return "やや強気", "#238636", "📈"
    elif downs > ups:
        return "やや弱気", "#da3633", "📉"
    return "中立", "#9e6a03", "➡️"

def build_annotations(asset_key, dates):
    """指定アセットに関するイベントのChart.jsアノテーションを生成"""
    anns = {}
    date_set = set(dates)
    for i, ev in enumerate(HISTORICAL_EVENTS):
        if asset_key not in ev["assets"]:
            continue
        # 月次データに含まれる最近の月を探す
        ev_date = ev["date"]
        # 対応する月かそれ以降の最初の月を探す
        target = next((d for d in dates if d >= ev_date), None)
        if target is None:
            continue
        key = f"ev{i}"
        anns[key] = {
            "type": "line",
            "xMin": target,
            "xMax": target,
            "borderColor": "rgba(255, 193, 7, 0.7)",
            "borderWidth": 1.5,
            "borderDash": [4, 3],
            "label": {
                "content": ev["label"],
                "display": False,
                "backgroundColor": "rgba(30,30,40,0.95)",
                "color": "#ffd700",
                "font": {"size": 11},
                "padding": 6,
                "position": "start",
            },
            "enter": {"label": {"display": True}},
            "leave": {"label": {"display": False}},
        }
    return anns

# ─────────────────────────────────────────
# HTML生成
# ─────────────────────────────────────────
def build_html(data, hist, now_jst):
    date_str = now_jst.strftime("%Y年%-m月%-d日")
    time_str = now_jst.strftime("%Y年%-m月%-d日 %H:%M JST")

    nk,  _, nk_chg  = data["nikkei"]
    sp,  _, sp_chg  = data["sp500"]
    fx,  _, fx_chg  = data["usdjpy"]
    efx, _, efx_chg = data["eurjpy"]
    oil, _, oil_chg = data["oil"]
    gld, _, gld_chg = data["gold"]
    btc, _, btc_chg = data["btc"]
    eth, _, eth_chg = data["eth"]

    label, badge_color, emoji = sentiment([nk_chg, sp_chg, btc_chg, gld_chg])

    # 歴史チャートデータをJSON化
    nk_dates,  nk_prices  = hist["nikkei"]
    sp_dates,  sp_prices  = hist["sp500"]
    fx_dates,  fx_prices  = hist["usdjpy"]
    gld_dates, gld_prices = hist["gold"]

    # アノテーション
    nk_ann  = json.dumps(build_annotations("nikkei", nk_dates),  ensure_ascii=False)
    sp_ann  = json.dumps(build_annotations("sp500",  sp_dates),  ensure_ascii=False)
    fx_ann  = json.dumps(build_annotations("usdjpy", fx_dates),  ensure_ascii=False)
    gld_ann = json.dumps(build_annotations("gold",   gld_dates), ensure_ascii=False)

    # イベント一覧テーブル行を生成
    event_rows = ""
    for ev in sorted(HISTORICAL_EVENTS, key=lambda x: x["date"], reverse=True):
        asset_badges = ""
        map_ = {"nikkei": "日経", "sp500": "S&P", "usdjpy": "ドル円", "gold": "金"}
        for a in ev["assets"]:
            asset_badges += f'<span class="badge">{map_.get(a, a)}</span>'
        event_rows += f"""
        <tr>
          <td class="ev-date">{ev["date"]}</td>
          <td class="ev-label">{ev["label"]}</td>
          <td>{asset_badges}</td>
          <td class="ev-desc">{ev["desc"]}</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>マーケットニュース - {date_str}</title>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/chartjs-plugin-annotation/3.0.1/chartjs-plugin-annotation.min.js"></script>
  <style>
    *{{margin:0;padding:0;box-sizing:border-box}}
    body{{font-family:'Segoe UI','Hiragino Sans','Yu Gothic',sans-serif;background:#0d1117;color:#e6edf3;min-height:100vh}}
    header{{background:linear-gradient(135deg,#161b22,#1c2128);border-bottom:1px solid #30363d;padding:24px 32px}}
    .header-inner{{max-width:1200px;margin:0 auto;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px}}
    .header-title{{font-size:1.6rem;font-weight:700;background:linear-gradient(90deg,#58a6ff,#79c0ff);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}
    .header-meta{{font-size:.85rem;color:#8b949e}}
    .header-meta span{{color:#58a6ff;font-weight:600}}
    main{{max-width:1200px;margin:0 auto;padding:32px 24px}}
    .sentiment-banner{{background:linear-gradient(135deg,#1c2f1c,#162416);border:1px solid #2ea043;border-radius:12px;padding:20px 28px;margin-bottom:32px;display:flex;align-items:center;gap:16px;flex-wrap:wrap}}
    .sentiment-badge{{color:#fff;font-weight:700;font-size:.9rem;padding:6px 16px;border-radius:20px;white-space:nowrap;background:{badge_color}}}
    .sentiment-text{{color:#7ee787;font-size:.95rem;line-height:1.6}}
    .section-title{{font-size:1.1rem;font-weight:600;color:#8b949e;text-transform:uppercase;letter-spacing:.08em;margin-bottom:16px}}
    .cards-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:20px;margin-bottom:40px}}
    .card{{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:20px;transition:border-color .2s}}
    .card:hover{{border-color:#58a6ff}}
    .card-header{{display:flex;align-items:center;gap:10px;margin-bottom:14px}}
    .card-icon{{width:36px;height:36px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:1.1rem}}
    .icon-stocks{{background:#1a3a5c}}.icon-fx{{background:#3a2a1a}}.icon-cmd{{background:#2a1a3a}}.icon-crypto{{background:#1a3a2a}}
    .card-title{{font-weight:700;font-size:1rem;color:#e6edf3}}
    .card-subtitle{{font-size:.75rem;color:#8b949e}}
    .price-row{{display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid #21262d}}
    .price-row:last-of-type{{border-bottom:none}}
    .price-label{{font-size:.85rem;color:#8b949e}}
    .price-value{{font-size:.95rem;font-weight:600;color:#e6edf3}}
    .price-change{{font-size:.8rem;margin-left:4px}}
    .up{{color:#3fb950}}.down{{color:#f85149}}
    .card-summary{{margin-top:14px;padding-top:14px;border-top:1px solid #21262d;font-size:.82rem;color:#8b949e;line-height:1.65}}
    /* チャートセクション */
    .chart-section{{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:24px;margin-bottom:24px}}
    .chart-title{{font-size:1rem;font-weight:700;color:#e6edf3;margin-bottom:4px}}
    .chart-subtitle{{font-size:.78rem;color:#8b949e;margin-bottom:16px}}
    .chart-hint{{font-size:.75rem;color:#ffd700;margin-bottom:12px}}
    .chart-wrap{{position:relative;height:280px}}
    /* イベントテーブル */
    .event-section{{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:24px;margin-bottom:32px;overflow-x:auto}}
    table{{width:100%;border-collapse:collapse;font-size:.83rem}}
    th{{text-align:left;padding:10px 12px;border-bottom:2px solid #30363d;color:#8b949e;font-weight:600;white-space:nowrap}}
    td{{padding:10px 12px;border-bottom:1px solid #21262d;vertical-align:top;line-height:1.5}}
    tr:hover td{{background:#1c2128}}
    .ev-date{{color:#58a6ff;white-space:nowrap;font-weight:600}}
    .ev-label{{font-weight:700;color:#e6edf3;white-space:nowrap}}
    .ev-desc{{color:#8b949e;font-size:.8rem}}
    .badge{{display:inline-block;background:#21262d;color:#79c0ff;border:1px solid #30363d;border-radius:4px;padding:2px 6px;font-size:.72rem;margin:2px 2px 2px 0;white-space:nowrap}}
    footer{{background:#161b22;border-top:1px solid #30363d;padding:20px 32px;text-align:center;font-size:.78rem;color:#6e7681}}
    footer a{{color:#58a6ff;text-decoration:none}}
    @media(max-width:600px){{.header-inner{{flex-direction:column}}.sentiment-banner{{flex-direction:column}}}}
  </style>
</head>
<body>
<header>
  <div class="header-inner">
    <div>
      <div class="header-title">📊 マーケットニュース</div>
      <div class="header-meta">最終更新: <span>{time_str}</span></div>
    </div>
    <div class="header-meta">GitHub Actions 自動更新</div>
  </div>
</header>
<main>

  <!-- センチメント -->
  <div class="sentiment-banner">
    <div class="sentiment-badge">{emoji} {label}</div>
    <div class="sentiment-text">
      日経平均 {fmt_price(nk, 0, suffix='円')} / S&amp;P500 {fmt_price(sp, 2)} /
      USD/JPY {fmt_price(fx, 2, suffix='円')} / BTC {fmt_price(btc, 0, prefix='$')} /
      金 {fmt_price(gld, 2, prefix='$', suffix='/oz')}
    </div>
  </div>

  <!-- 今日のカード -->
  <p class="section-title">本日のマーケット</p>
  <div class="cards-grid">
    <div class="card">
      <div class="card-header">
        <div class="card-icon icon-stocks">🗾</div>
        <div><div class="card-title">株式市場</div><div class="card-subtitle">日本株・米国株</div></div>
      </div>
      <div class="price-row"><span class="price-label">日経平均</span><span class="price-value">{fmt_price(nk, 0, suffix='円')} {fmt_change(nk_chg)}</span></div>
      <div class="price-row"><span class="price-label">S&amp;P500</span><span class="price-value">{fmt_price(sp, 2)} {fmt_change(sp_chg)}</span></div>
    </div>
    <div class="card">
      <div class="card-header">
        <div class="card-icon icon-fx">💱</div>
        <div><div class="card-title">為替（FX）</div><div class="card-subtitle">ドル円・ユーロ円</div></div>
      </div>
      <div class="price-row"><span class="price-label">USD/JPY</span><span class="price-value">{fmt_price(fx, 2, suffix='円')} {fmt_change(fx_chg)}</span></div>
      <div class="price-row"><span class="price-label">EUR/JPY</span><span class="price-value">{fmt_price(efx, 2, suffix='円')} {fmt_change(efx_chg)}</span></div>
    </div>
    <div class="card">
      <div class="card-header">
        <div class="card-icon icon-cmd">🛢️</div>
        <div><div class="card-title">コモディティ</div><div class="card-subtitle">原油・金</div></div>
      </div>
      <div class="price-row"><span class="price-label">WTI原油</span><span class="price-value">{fmt_price(oil, 2, prefix='$', suffix='/bbl')} {fmt_change(oil_chg)}</span></div>
      <div class="price-row"><span class="price-label">金（スポット）</span><span class="price-value">{fmt_price(gld, 2, prefix='$', suffix='/oz')} {fmt_change(gld_chg)}</span></div>
    </div>
    <div class="card">
      <div class="card-header">
        <div class="card-icon icon-crypto">₿</div>
        <div><div class="card-title">暗号資産</div><div class="card-subtitle">BTC・ETH</div></div>
      </div>
      <div class="price-row"><span class="price-label">Bitcoin (BTC)</span><span class="price-value">{fmt_price(btc, 0, prefix='$')} {fmt_change(btc_chg)}</span></div>
      <div class="price-row"><span class="price-label">Ethereum (ETH)</span><span class="price-value">{fmt_price(eth, 2, prefix='$')} {fmt_change(eth_chg)}</span></div>
    </div>
  </div>

  <!-- 歴史チャート -->
  <p class="section-title">📈 50年価格チャート（歴史的イベント付き）</p>

  <div class="chart-section">
    <div class="chart-title">株式市場 — 日経平均 / S&amp;P500</div>
    <div class="chart-subtitle">月次終値（左軸: 日経平均円、右軸: S&amp;P500ポイント）</div>
    <div class="chart-hint">💡 点線マーカーにカーソルを当てるとイベント名が表示されます</div>
    <div class="chart-wrap"><canvas id="chartStocks"></canvas></div>
  </div>

  <div class="chart-section">
    <div class="chart-title">為替 — USD/JPY（ドル円）</div>
    <div class="chart-subtitle">月次終値（円/ドル）</div>
    <div class="chart-hint">💡 点線マーカーにカーソルを当てるとイベント名が表示されます</div>
    <div class="chart-wrap"><canvas id="chartFX"></canvas></div>
  </div>

  <div class="chart-section">
    <div class="chart-title">ゴールド — 金価格（スポット/先物）</div>
    <div class="chart-subtitle">月次終値（USD/oz）</div>
    <div class="chart-hint">💡 点線マーカーにカーソルを当てるとイベント名が表示されます</div>
    <div class="chart-wrap"><canvas id="chartGold"></canvas></div>
  </div>

  <!-- イベント一覧 -->
  <p class="section-title">📋 歴史的イベント一覧</p>
  <div class="event-section">
    <table>
      <thead><tr><th>年月</th><th>イベント</th><th>関連資産</th><th>概要</th></tr></thead>
      <tbody>{event_rows}</tbody>
    </table>
  </div>

</main>
<footer>
  <p>データソース: Yahoo Finance (yfinance) &nbsp;|&nbsp;
  <a href="https://invest-ai-info.github.io/marketwatch-ai/">GitHub Pages</a> &nbsp;|&nbsp;
  本データは自動取得・表示であり、投資助言ではありません。</p>
</footer>

<script>
const NK_DATES  = {json.dumps(nk_dates)};
const NK_PRICES = {json.dumps(nk_prices)};
const SP_DATES  = {json.dumps(sp_dates)};
const SP_PRICES = {json.dumps(sp_prices)};
const FX_DATES  = {json.dumps(fx_dates)};
const FX_PRICES = {json.dumps(fx_prices)};
const GLD_DATES  = {json.dumps(gld_dates)};
const GLD_PRICES = {json.dumps(gld_prices)};

const NK_ANN  = {nk_ann};
const SP_ANN  = {sp_ann};
const FX_ANN  = {fx_ann};
const GLD_ANN = {gld_ann};

const gridColor  = 'rgba(48,54,61,0.8)';
const labelColor = '#8b949e';

function makeChart(id, datasets, annotations, yLabels) {{
  const ctx = document.getElementById(id).getContext('2d');
  const scales = {{}};
  datasets.forEach((ds, i) => {{
    const axId = 'y' + i;
    ds.yAxisID = axId;
    scales[axId] = {{
      position: i === 0 ? 'left' : 'right',
      grid: {{ color: i === 0 ? gridColor : 'transparent', drawBorder: false }},
      ticks: {{ color: labelColor, font: {{ size: 10 }}, maxTicksLimit: 6,
        callback: v => yLabels[i] ? yLabels[i](v) : v }},
      title: {{ display: false }},
    }};
  }});
  scales['x'] = {{
    ticks: {{ color: labelColor, font: {{ size: 10 }}, maxTicksLimit: 12,
      callback: function(val, idx) {{
        const lbl = this.getLabelForValue(val);
        return lbl && lbl.endsWith('-01') ? lbl.substring(0,4) : '';
      }}
    }},
    grid: {{ color: gridColor, drawBorder: false }},
  }};
  return new Chart(ctx, {{
    type: 'line',
    data: {{ labels: datasets[0].dates, datasets }},
    options: {{
      responsive: true, maintainAspectRatio: false,
      interaction: {{ mode: 'index', intersect: false }},
      plugins: {{
        legend: {{ labels: {{ color: '#e6edf3', font: {{ size: 12 }} }} }},
        tooltip: {{ backgroundColor: 'rgba(22,27,34,0.95)', titleColor: '#58a6ff',
                    bodyColor: '#e6edf3', borderColor: '#30363d', borderWidth: 1 }},
        annotation: {{ annotations }},
      }},
      scales,
      elements: {{ point: {{ radius: 0, hoverRadius: 4 }}, line: {{ tension: 0.2 }} }},
    }}
  }});
}}

// 株式チャート（日経 + S&P500）
const mergedDates = [...new Set([...NK_DATES, ...SP_DATES])].sort();
const nkMap = Object.fromEntries(NK_DATES.map((d,i) => [d, NK_PRICES[i]]));
const spMap = Object.fromEntries(SP_DATES.map((d,i) => [d, SP_PRICES[i]]));
makeChart('chartStocks', [
  {{ label: '日経平均（円）', dates: NK_DATES, data: NK_PRICES,
     borderColor: '#58a6ff', backgroundColor: 'rgba(88,166,255,0.08)',
     borderWidth: 1.5, fill: true }},
  {{ label: 'S&P500', dates: SP_DATES, data: SP_PRICES,
     borderColor: '#3fb950', backgroundColor: 'rgba(63,185,80,0.06)',
     borderWidth: 1.5, fill: true }},
], Object.assign({{}}, NK_ANN, SP_ANN),
[v => v.toLocaleString()+'円', v => v.toLocaleString()]);

// 為替チャート
makeChart('chartFX', [
  {{ label: 'USD/JPY（円）', dates: FX_DATES, data: FX_PRICES,
     borderColor: '#f0883e', backgroundColor: 'rgba(240,136,62,0.08)',
     borderWidth: 1.5, fill: true }},
], FX_ANN, [v => v.toFixed(1)+'円']);

// 金チャート
makeChart('chartGold', [
  {{ label: '金価格（USD/oz）', dates: GLD_DATES, data: GLD_PRICES,
     borderColor: '#ffd700', backgroundColor: 'rgba(255,215,0,0.08)',
     borderWidth: 1.5, fill: true }},
], GLD_ANN, [v => '$'+v.toLocaleString()]);
</script>
</body>
</html>"""


# ─────────────────────────────────────────
# メイン
# ─────────────────────────────────────────
def main():
    now_jst = datetime.now(JST)
    print("📡 現在価格を取得中...")
    data = {
        "nikkei": get_price("^N225"),
        "sp500":  get_price("^GSPC"),
        "usdjpy": get_price("JPY=X"),
        "eurjpy": get_price("EURJPY=X"),
        "oil":    get_price("CL=F"),
        "gold":   get_price("GC=F"),
        "btc":    get_price("BTC-USD"),
        "eth":    get_price("ETH-USD"),
    }
    print("📊 歴史的価格データを取得中（50年分）...")
    hist = {
        "nikkei": get_historical_monthly("^N225",  "1975-01-01"),
        "sp500":  get_historical_monthly("^GSPC",  "1975-01-01"),
        "usdjpy": get_historical_monthly("JPY=X",  "1975-01-01"),
        "gold":   get_historical_monthly("GC=F",   "1975-01-01"),
    }
    print("🖊️  HTML生成中...")
    content = build_html(data, hist, now_jst)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ index.html 生成完了 ({now_jst.strftime('%Y-%m-%d %H:%M JST')})")

if __name__ == "__main__":
    main()
