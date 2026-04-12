"""
毎朝マーケットニュース自動生成スクリプト
yfinance で価格データを取得し index.html を生成する
"""

import yfinance as yf
from datetime import datetime, timezone, timedelta
import html

JST = timezone(timedelta(hours=9))

def get_price(ticker_symbol):
    """終値・前日比を取得"""
    try:
        t = yf.Ticker(ticker_symbol)
        hist = t.history(period="2d")
        if len(hist) < 2:
            return None, None, None
        prev_close = hist["Close"].iloc[-2]
        last_close = hist["Close"].iloc[-1]
        change_pct = (last_close - prev_close) / prev_close * 100
        return last_close, prev_close, change_pct
    except Exception:
        return None, None, None

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
    ups = sum(1 for c in changes if c and c > 0)
    downs = sum(1 for c in changes if c and c < 0)
    if ups > downs:
        label, color, emoji = "やや強気", "#238636", "📈"
    elif downs > ups:
        label, color, emoji = "やや弱気", "#da3633", "📉"
    else:
        label, color, emoji = "中立", "#9e6a03", "➡️"
    return label, color, emoji

def build_html(data, now_jst):
    date_str = now_jst.strftime("%Y年%-m月%-d日")
    time_str = now_jst.strftime("%Y年%-m月%-d日 %H:%M JST")

    nk, nk_prev, nk_chg   = data["nikkei"]
    sp, sp_prev, sp_chg   = data["sp500"]
    usdjpy, _, fx1_chg    = data["usdjpy"]
    eurjpy, _, fx2_chg    = data["eurjpy"]
    oil, _, oil_chg       = data["oil"]
    gold, _, gold_chg     = data["gold"]
    btc, _, btc_chg       = data["btc"]
    eth, _, eth_chg       = data["eth"]

    label, badge_color, emoji = sentiment([nk_chg, sp_chg, btc_chg, gold_chg])

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>マーケットニュース - {date_str}</title>
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
    .sentiment-badge{{background:{badge_color};color:#fff;font-weight:700;font-size:.9rem;padding:6px 16px;border-radius:20px;white-space:nowrap}}
    .sentiment-text{{color:#7ee787;font-size:.95rem;line-height:1.6}}
    .section-title{{font-size:1.1rem;font-weight:600;color:#8b949e;text-transform:uppercase;letter-spacing:.08em;margin-bottom:16px}}
    .cards-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:20px;margin-bottom:32px}}
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
    footer{{background:#161b22;border-top:1px solid #30363d;padding:20px 32px;text-align:center;font-size:.78rem;color:#6e7681}}
    footer a{{color:#58a6ff;text-decoration:none}}
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
  <div class="sentiment-banner">
    <div class="sentiment-badge">{emoji} {label}</div>
    <div class="sentiment-text">
      日経平均 {fmt_price(nk, 0, suffix='円')} / S&amp;P500 {fmt_price(sp, 2)} /
      USD/JPY {fmt_price(usdjpy, 2, suffix='円')} / BTC {fmt_price(btc, 0, prefix='$')} /
      金 {fmt_price(gold, 2, prefix='$', suffix='/oz')}
    </div>
  </div>

  <p class="section-title">カテゴリ別マーケット動向</p>
  <div class="cards-grid">

    <div class="card">
      <div class="card-header">
        <div class="card-icon icon-stocks">🗾</div>
        <div><div class="card-title">株式市場</div><div class="card-subtitle">日本株・米国株</div></div>
      </div>
      <div class="price-row">
        <span class="price-label">日経平均</span>
        <span class="price-value">{fmt_price(nk, 0, suffix='円')} {fmt_change(nk_chg)}</span>
      </div>
      <div class="price-row">
        <span class="price-label">S&amp;P500</span>
        <span class="price-value">{fmt_price(sp, 2)} {fmt_change(sp_chg)}</span>
      </div>
      <div class="card-summary">前日比をもとにした自動集計データです。</div>
    </div>

    <div class="card">
      <div class="card-header">
        <div class="card-icon icon-fx">💱</div>
        <div><div class="card-title">為替（FX）</div><div class="card-subtitle">ドル円・ユーロ円</div></div>
      </div>
      <div class="price-row">
        <span class="price-label">USD/JPY</span>
        <span class="price-value">{fmt_price(usdjpy, 2, suffix='円')} {fmt_change(fx1_chg)}</span>
      </div>
      <div class="price-row">
        <span class="price-label">EUR/JPY</span>
        <span class="price-value">{fmt_price(eurjpy, 2, suffix='円')} {fmt_change(fx2_chg)}</span>
      </div>
      <div class="card-summary">前日比をもとにした自動集計データです。</div>
    </div>

    <div class="card">
      <div class="card-header">
        <div class="card-icon icon-cmd">🛢️</div>
        <div><div class="card-title">コモディティ</div><div class="card-subtitle">原油・金</div></div>
      </div>
      <div class="price-row">
        <span class="price-label">WTI原油</span>
        <span class="price-value">{fmt_price(oil, 2, prefix='$', suffix='/bbl')} {fmt_change(oil_chg)}</span>
      </div>
      <div class="price-row">
        <span class="price-label">金（スポット）</span>
        <span class="price-value">{fmt_price(gold, 2, prefix='$', suffix='/oz')} {fmt_change(gold_chg)}</span>
      </div>
      <div class="card-summary">前日比をもとにした自動集計データです。</div>
    </div>

    <div class="card">
      <div class="card-header">
        <div class="card-icon icon-crypto">₿</div>
        <div><div class="card-title">暗号資産</div><div class="card-subtitle">BTC・ETH</div></div>
      </div>
      <div class="price-row">
        <span class="price-label">Bitcoin (BTC)</span>
        <span class="price-value">{fmt_price(btc, 0, prefix='$')} {fmt_change(btc_chg)}</span>
      </div>
      <div class="price-row">
        <span class="price-label">Ethereum (ETH)</span>
        <span class="price-value">{fmt_price(eth, 2, prefix='$')} {fmt_change(eth_chg)}</span>
      </div>
      <div class="card-summary">前日比をもとにした自動集計データです。</div>
    </div>

  </div>
</main>
<footer>
  <p>データソース: Yahoo Finance (yfinance) &nbsp;|&nbsp;
  <a href="https://invest-ai-info.github.io/marketwatch-ai/">GitHub Pages</a> &nbsp;|&nbsp;
  本データは自動取得・表示であり、投資助言ではありません。</p>
</footer>
</body>
</html>"""

def main():
    now_jst = datetime.now(JST)
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
    content = build_html(data, now_jst)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ index.html を生成しました ({now_jst.strftime('%Y-%m-%d %H:%M JST')})")

if __name__ == "__main__":
    main()
