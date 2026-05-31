# -*- coding: utf-8 -*-
"""
generate_stock_chart.py
───────────────────────────────────────
個別銘柄解説記事に挿入する「過去 N 年の終値チャート (Chart.js)」HTML を生成。

使い方:
    # 単独実行（指定銘柄のチャート HTML を標準出力）
    python generate_stock_chart.py NVDA "NVIDIA" --currency "$" --years 3

    # モジュールとして
    from generate_stock_chart import build_chart_section_html
    html = build_chart_section_html("9984.T", "ソフトバンクグループ", "¥", years=3)

設計:
- yfinance で過去 N 年の日足データ取得
- 期間統計（最安値・最高値・上昇率）を表示
- Chart.js (CDN) でレスポンシブな線グラフ
- HTML をそのまま既存記事に貼り付け可能（独立した <section> ブロック）
"""
import os
import sys
import json
from datetime import datetime, timedelta, timezone

# GitHub Actions のランナーは UTC で動くため、素の datetime.now() は UTC を返す。
# 日本時間で扱うため JST を明示する（"JST" 表示の時刻が 9 時間ズレる事故を防ぐ）。
JST = timezone(timedelta(hours=9))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def _ticker_to_stooq(ticker):
    """yfinance ticker を Stooq の symbol に変換"""
    t = ticker.upper()
    if t.endswith(".T"):
        # 日本株: 7203.T → 7203.jp
        return t[:-2].lower() + ".jp"
    if t.endswith("=X"):
        # FX: USDJPY=X → usdjpy
        return t[:-2].lower()
    if t.endswith("=F"):
        # 商品先物: GC=F → gc.f
        return t[:-2].lower() + ".f"
    if t.endswith("-USD"):
        # 暗号: BTC-USD → btcusd
        return t.lower().replace("-", "")
    # 米株: NVDA → nvda.us
    return t.lower() + ".us"


def fetch_chart_data(ticker, years=3):
    """Stooq の無料 CSV API で過去 N 年の日足データを取得（SSL 問題少ない、登録不要）

    優先: Stooq → フォールバック: yfinance（Actions 上で動作）
    """
    import urllib.request

    # === Stooq 試行 ===
    stooq_symbol = _ticker_to_stooq(ticker)
    url = f"https://stooq.com/q/d/l/?s={stooq_symbol}&i=d"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; MarketWatch/1.0)"})
        with urllib.request.urlopen(req, timeout=30) as r:
            text = r.read().decode("utf-8", "replace")
        # CSV: Date,Open,High,Low,Close,Volume
        lines = text.strip().splitlines()
        if len(lines) < 30:
            raise ValueError(f"Stooq data too short ({len(lines)} lines)")
        cutoff = datetime.now(JST).replace(tzinfo=None) - timedelta(days=int(365 * years))
        data = []
        for line in lines[1:]:  # 1 行目はヘッダ
            parts = line.split(",")
            if len(parts) < 5:
                continue
            try:
                d = datetime.strptime(parts[0], "%Y-%m-%d")
                if d < cutoff:
                    continue
                close = float(parts[4])
                if close > 0:
                    data.append({
                        "date": parts[0],
                        "close": round(close, 4),
                    })
            except (ValueError, IndexError):
                continue
        if len(data) >= 30:
            print(f"  ✅ Stooq から {len(data)} 件取得 ({ticker} → {stooq_symbol})")
            return data
        else:
            print(f"  ⚠️ Stooq データ少なすぎ ({len(data)} 件) → yfinance フォールバック")
    except Exception as e:
        print(f"  ⚠️ Stooq 取得失敗 ({ticker}): {type(e).__name__}: {str(e)[:60]} → yfinance フォールバック")

    # === yfinance フォールバック（Actions 上では動く）===
    try:
        import yfinance as yf
        import pandas as pd
    except ImportError:
        print("  ⚠️ yfinance / pandas 未インストール、フォールバック失敗")
        return None

    end = datetime.now(JST).replace(tzinfo=None)
    start = end - timedelta(days=int(365 * years) + 30)
    try:
        df = yf.download(ticker, start=start, end=end, interval="1d", progress=False, auto_adjust=True)
    except Exception as e:
        print(f"  ⚠️ yfinance 取得失敗: {type(e).__name__}: {str(e)[:80]}")
        return None
    if df is None or df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    data = []
    for date, row in df.iterrows():
        try:
            close = float(row["Close"])
            if close > 0:
                data.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "close": round(close, 4),
                })
        except (ValueError, TypeError):
            continue
    return data


def build_tradingview_section_html(symbol, asset_name, range_label="36M"):
    """TradingView 埋込みウィジェットでチャートセクションを生成（SSL 問題なし、自動更新）

    Args:
        symbol: TradingView 形式のシンボル (例: "NASDAQ:NVDA", "TYO:9984", "OANDA:USDJPY")
        asset_name: 表示名
        range_label: チャート期間 ("36M" = 3 年、"60M" = 5 年、"ALL" = 全期間)

    返値: HTML ブロック（外部 iframe 不要、純粋な埋込み）
    """
    import json as _json
    config = {
        "autosize": True,
        "symbol": symbol,
        "interval": "D",
        "timezone": "Asia/Tokyo",
        "theme": "light",
        "style": "2",   # 線グラフ
        "locale": "ja",
        "range": range_label,
        "hide_top_toolbar": True,
        "hide_legend": False,
        "save_image": False,
        "studies": [],
        "support_host": "https://www.tradingview.com",
    }
    config_json = _json.dumps(config, ensure_ascii=False)

    return f"""
<h2>📈 過去 3 年のチャート（日足）</h2>
<p style="font-size:.9rem;color:#57606a;margin-bottom:14px">
  TradingView による {asset_name} のチャート。「いつから上昇トレンドが始まったか」「現在は高値圏か」を視覚的に把握できます。カーソルで日付・価格を確認可能、自動的に毎日更新されます。
</p>
<div class="tradingview-widget-container" style="height:450px;width:100%;background:#fff;border:1px solid #d0d7de;border-radius:10px;padding:12px;margin:14px 0">
  <div class="tradingview-widget-container__widget" style="height:100%;width:100%"></div>
  <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
  {config_json}
  </script>
</div>
<p style="font-size:.78rem;color:#6e7781;margin-top:8px">
  💡 チャート出典: <a href="https://www.tradingview.com/symbols/{symbol.replace(':', '-')}/" target="_blank" rel="noopener">TradingView</a> (リアルタイム自動更新)。シンボル: <code>{symbol}</code>
</p>
"""


def build_chart_section_html(ticker, asset_name, currency="$", years=3, chart_id=None):
    """記事に挿入する「📈 過去 N 年のチャート」セクション HTML を生成（旧版、Chart.js 静的データ）

    返値: 完全な HTML ブロック（<h2> + 統計 + <canvas> + <script>）
    """
    data = fetch_chart_data(ticker, years=years)
    if not data or len(data) < 30:
        return f"""
<h2>📈 過去 {years} 年のチャート（日足）</h2>
<div style="background:#fff8c5;border:1px solid #9a6700;border-radius:8px;padding:18px;color:#9a6700">
  ⚠️ {asset_name} ({ticker}) のチャートデータを取得できませんでした。後日再取得します。
</div>
"""

    # 統計算出
    closes = [d["close"] for d in data]
    dates = [d["date"] for d in data]
    low = min(closes)
    high = max(closes)
    first = closes[0]
    last = closes[-1]
    change_pct = (last - first) / first * 100 if first > 0 else 0
    low_idx = closes.index(low)
    high_idx = closes.index(high)

    # チャート ID（重複防止のため ticker から安全な ID 生成）
    if chart_id is None:
        safe_id = ticker.replace("=", "").replace(".", "").replace("-", "").replace("/", "")
        chart_id = f"chart-{safe_id}"

    # 通貨単位フォーマット
    def fmt(v):
        if currency == "¥":
            return f"¥{v:,.0f}"
        return f"{currency}{v:,.2f}"

    change_color = "#1a7f37" if change_pct >= 0 else "#cf222e"

    return f"""
<h2>📈 過去 {years} 年のチャート（日足）</h2>
<p style="font-size:.9rem;color:#57606a;margin-bottom:14px">
  「いつから上昇トレンドが始まったか」「現在は高値圏か」を視覚的に把握できます。ホバーで日付・価格を確認できます。
</p>
<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:16px">
  <div style="background:#f6f8fa;border:1px solid #d0d7de;border-radius:8px;padding:12px;text-align:center">
    <div style="font-size:.72rem;color:#57606a">期間</div>
    <div style="font-size:.85rem;font-weight:600;color:#1f2328">{dates[0]} 〜<br>{dates[-1]}</div>
  </div>
  <div style="background:#f6f8fa;border:1px solid #d0d7de;border-radius:8px;padding:12px;text-align:center">
    <div style="font-size:.72rem;color:#57606a">期間最安値</div>
    <div style="font-size:1.05rem;font-weight:700;color:#cf222e">{fmt(low)}</div>
    <div style="font-size:.7rem;color:#6e7781">{dates[low_idx]}</div>
  </div>
  <div style="background:#f6f8fa;border:1px solid #d0d7de;border-radius:8px;padding:12px;text-align:center">
    <div style="font-size:.72rem;color:#57606a">期間最高値</div>
    <div style="font-size:1.05rem;font-weight:700;color:#1a7f37">{fmt(high)}</div>
    <div style="font-size:.7rem;color:#6e7781">{dates[high_idx]}</div>
  </div>
  <div style="background:#f6f8fa;border:1px solid #d0d7de;border-radius:8px;padding:12px;text-align:center">
    <div style="font-size:.72rem;color:#57606a">現在値</div>
    <div style="font-size:1.05rem;font-weight:700;color:#0969da">{fmt(last)}</div>
  </div>
  <div style="background:#f6f8fa;border:1px solid #d0d7de;border-radius:8px;padding:12px;text-align:center">
    <div style="font-size:.72rem;color:#57606a">期間上昇率</div>
    <div style="font-size:1.25rem;font-weight:800;color:{change_color}">{change_pct:+.1f}%</div>
  </div>
</div>
<div style="background:#fff;border:1px solid #d0d7de;border-radius:10px;padding:18px;height:380px;margin:12px 0">
  <canvas id="{chart_id}"></canvas>
</div>
<p style="font-size:.78rem;color:#6e7781;margin-top:8px">
  💡 データ出典: Yahoo Finance (yfinance)、ティッカー <code>{ticker}</code>。最終取得: {datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")}
</p>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script>
(function() {{
  var ctx = document.getElementById('{chart_id}');
  if (!ctx) return;
  new Chart(ctx.getContext('2d'), {{
    type: 'line',
    data: {{
      labels: {json.dumps(dates)},
      datasets: [{{
        label: '{asset_name} 終値',
        data: {json.dumps(closes)},
        borderColor: '#0969da',
        backgroundColor: 'rgba(9,105,218,0.08)',
        fill: true,
        tension: 0.2,
        pointRadius: 0,
        pointHoverRadius: 5,
        borderWidth: 2,
      }}]
    }},
    options: {{
      responsive: true,
      maintainAspectRatio: false,
      interaction: {{ mode: 'index', intersect: false }},
      plugins: {{
        legend: {{ display: false }},
        tooltip: {{
          callbacks: {{
            label: function(ctx) {{
              var v = ctx.parsed.y;
              return '{asset_name}: ' + ('{currency}' === '¥' ? '¥' + Math.round(v).toLocaleString() : '{currency}' + v.toLocaleString('en-US', {{minimumFractionDigits: 2, maximumFractionDigits: 2}}));
            }}
          }}
        }}
      }},
      scales: {{
        x: {{
          ticks: {{ maxTicksLimit: 10, autoSkip: true }},
          grid: {{ color: 'rgba(0,0,0,0.04)' }}
        }},
        y: {{
          ticks: {{
            callback: function(v) {{
              return ('{currency}' === '¥') ? '¥' + Math.round(v).toLocaleString() : '{currency}' + v.toLocaleString();
            }}
          }},
          grid: {{ color: 'rgba(0,0,0,0.04)' }}
        }}
      }}
    }}
  }});
}})();
</script>
"""


def main():
    import argparse
    parser = argparse.ArgumentParser(description="個別銘柄チャート HTML 生成")
    parser.add_argument("ticker", help="ティッカー (例: NVDA, 9984.T, GC=F)")
    parser.add_argument("asset_name", help="表示名 (例: NVIDIA, ソフトバンクグループ)")
    parser.add_argument("--currency", default="$", help="通貨記号 ($ / ¥)")
    parser.add_argument("--years", type=int, default=3, help="過去何年分")
    parser.add_argument("--output", help="出力ファイル (省略時は stdout)")
    args = parser.parse_args()

    html = build_chart_section_html(args.ticker, args.asset_name, args.currency, args.years)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"✅ {args.output} に保存 ({len(html)} 文字)")
    else:
        print(html)


if __name__ == "__main__":
    main()
