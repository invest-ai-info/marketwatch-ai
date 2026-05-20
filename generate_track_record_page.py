"""
generate_track_record_page.py
───────────────────────────────────────
signals-log.json から統計を集計し、track-record.html を生成する。

出力:
- /track-record.html  ... メインの統計ページ
  - 全体勝率・R:R 達成率
  - シグナル種別ブレイクダウン
  - 銘柄ブレイクダウン
  - エクイティカーブ（模擬：等額 $1000 ずつ取引と仮定）
  - 直近 30 件のシグナル詳細テーブル

実取引ログ（my-trades.json）が存在すれば、それも統合表示する（P3.5 用）。
"""
import os
import sys
import json
from datetime import datetime, timezone, timedelta
from collections import defaultdict

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

JST = timezone(timedelta(hours=9))
SIGNALS_LOG_FILE = "signals-log.json"
TRADES_LOG_FILE = "my-trades.json"  # P3.5 用、なくても OK
OUTPUT_FILE = "track-record.html"

# シグナルタイプの日本語ラベル（generate_technical_alerts.py と一致させる）
SIGNAL_LABELS = {
    "rsi_oversold_bounce": "🟢 RSI 過売り反発",
    "rsi_overbought": "🟡 RSI 過買い警戒",
    "macd_golden": "🟢 MACD ゴールデンクロス",
    "macd_dead": "🔴 MACD デッドクロス",
    "ma_golden": "🟢 移動平均ゴールデンクロス",
    "ma_dead": "🔴 移動平均デッドクロス",
    "bb_lower_touch": "🟢 ボリンジャー -2σ タッチ",
    "bb_upper_break": "🟡 ボリンジャー +2σ 突破",
    "high_break": "🟢 直近 20 本高値ブレイク",
    "low_break": "🔴 直近 20 本安値割れ",
}

# R:R リワード倍率（generate_technical_alerts.py の calc_entry_sl_tp と一致）
SL_RR = 1.5   # SL = ATR * 1.5
TP1_RR = 2.0  # TP1 = ATR * 2.0 → R:R 1.33
TP2_RR = 3.0  # TP2 = ATR * 3.0 → R:R 2.0


def load_json(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def calc_stats(entries):
    """確定済みシグナルから勝率・R:R 期待値を計算"""
    closed = [e for e in entries if e.get("outcome") in ("tp1", "tp2", "sl", "expired")]
    if not closed:
        return {
            "total": 0, "wins": 0, "losses": 0, "expired": 0,
            "tp1_count": 0, "tp2_count": 0, "sl_count": 0,
            "win_rate": 0.0, "tp1_rate": 0.0, "tp2_rate": 0.0,
            "expected_R": 0.0, "avg_mfe": 0.0, "avg_mae": 0.0,
        }
    tp1 = sum(1 for e in closed if e["outcome"] == "tp1")
    tp2 = sum(1 for e in closed if e["outcome"] == "tp2")
    sl = sum(1 for e in closed if e["outcome"] == "sl")
    exp = sum(1 for e in closed if e["outcome"] == "expired")
    wins = tp1 + tp2

    # 期待 R（リスク 1 単位あたり何 R の期待値か）
    # tp1 = +1.33R, tp2 = +2.0R, sl = -1.0R, expired = 0R（近似）
    total_r = tp1 * (TP1_RR / SL_RR) + tp2 * (TP2_RR / SL_RR) + sl * (-1.0) + exp * 0
    expected_r = total_r / len(closed) if closed else 0

    mfes = [e["max_favorable_excursion_pct"] for e in closed if e.get("max_favorable_excursion_pct") is not None]
    maes = [e["max_adverse_excursion_pct"] for e in closed if e.get("max_adverse_excursion_pct") is not None]

    return {
        "total": len(closed),
        "wins": wins,
        "losses": sl,
        "expired": exp,
        "tp1_count": tp1,
        "tp2_count": tp2,
        "sl_count": sl,
        "win_rate": wins / len(closed) * 100 if closed else 0,
        "tp1_rate": tp1 / len(closed) * 100 if closed else 0,
        "tp2_rate": tp2 / len(closed) * 100 if closed else 0,
        "expected_R": expected_r,
        "avg_mfe": sum(mfes) / len(mfes) if mfes else 0,
        "avg_mae": sum(maes) / len(maes) if maes else 0,
    }


def group_stats(entries, key_fn):
    """key_fn(entry) でグルーピングして各グループの統計を返す"""
    groups = defaultdict(list)
    for e in entries:
        if e.get("outcome") in ("tp1", "tp2", "sl", "expired"):
            k = key_fn(e)
            if k:
                groups[k].append(e)
    return {k: calc_stats(v) for k, v in groups.items()}


def render_stat_row(label, stats, link=None):
    if stats["total"] == 0:
        return ""
    win_color = "#1a7f37" if stats["win_rate"] >= 60 else "#9a6700" if stats["win_rate"] >= 45 else "#cf222e"
    er_color = "#1a7f37" if stats["expected_R"] > 0.3 else "#9a6700" if stats["expected_R"] > 0 else "#cf222e"
    label_html = f'<a href="{link}" style="color:#0969da;text-decoration:none">{label}</a>' if link else label
    return f"""
    <tr>
      <td>{label_html}</td>
      <td style="text-align:right">{stats['total']}</td>
      <td style="text-align:right;color:{win_color};font-weight:700">{stats['win_rate']:.1f}%</td>
      <td style="text-align:right">{stats['tp1_rate']:.1f}%</td>
      <td style="text-align:right">{stats['tp2_rate']:.1f}%</td>
      <td style="text-align:right">{stats['sl_count']}</td>
      <td style="text-align:right;color:{er_color};font-weight:700">{stats['expected_R']:+.2f}R</td>
    </tr>"""


def render_recent_table(entries, limit=30):
    rows = []
    for e in sorted(entries, key=lambda x: x.get("fired_at", ""), reverse=True)[:limit]:
        outcome = e.get("outcome") or "pending"
        outcome_emoji = {
            "tp1": "✅ TP1", "tp2": "🎯 TP2", "sl": "❌ SL",
            "expired": "⏰ 期限切れ", "no_plan": "—", "pending": "⏳"
        }.get(outcome, outcome)
        outcome_color = {
            "tp1": "#1a7f37", "tp2": "#1a7f37", "sl": "#cf222e",
            "expired": "#6e7781", "no_plan": "#6e7781", "pending": "#9a6700"
        }.get(outcome, "#6e7781")

        fired = e.get("fired_at", "")[:16].replace("T", " ")
        ticker = e.get("ticker", "")
        signal_label = SIGNAL_LABELS.get(e.get("primary_signal", ""), e.get("primary_signal_label", ""))
        direction = e.get("direction", "")
        direction_short = "L" if "ロング" in (direction or "") else "S" if "ショート" in (direction or "") else "-"
        entry = e.get("entry") or 0
        sl = e.get("stop_loss") or 0
        tp1 = e.get("take_profit_1") or 0
        mfe = e.get("max_favorable_excursion_pct")
        mae = e.get("max_adverse_excursion_pct")

        rows.append(f"""
        <tr>
          <td style="white-space:nowrap">{fired}</td>
          <td><b>{ticker}</b></td>
          <td style="font-size:.82rem">{signal_label}</td>
          <td style="text-align:center;font-weight:700;color:{'#1a7f37' if direction_short=='L' else '#cf222e' if direction_short=='S' else '#6e7781'}">{direction_short}</td>
          <td style="text-align:right">{entry:.2f}</td>
          <td style="text-align:right;color:#cf222e">{sl:.2f}</td>
          <td style="text-align:right;color:#1a7f37">{tp1:.2f}</td>
          <td style="text-align:right">{mfe:+.2f}%</td>
          <td style="text-align:right">{mae:+.2f}%</td>
          <td style="color:{outcome_color};font-weight:700;white-space:nowrap">{outcome_emoji}</td>
        </tr>""")
    return "\n".join(rows)


def render_equity_curve_data(entries):
    """Chart.js 用にエクイティ推移を JSON で返す（等額 $1000 / シグナル、R:R 基準）"""
    closed = sorted([e for e in entries if e.get("outcome") in ("tp1", "tp2", "sl", "expired")],
                    key=lambda x: x.get("outcome_resolved_at", ""))
    if not closed:
        return [], []
    risk_per_trade = 100  # 1 シグナル $100 リスク
    labels, values = [], []
    equity = 1000  # 初期残高 $1000
    for e in closed:
        outcome = e.get("outcome")
        if outcome == "tp1":
            equity += risk_per_trade * (TP1_RR / SL_RR)
        elif outcome == "tp2":
            equity += risk_per_trade * (TP2_RR / SL_RR)
        elif outcome == "sl":
            equity -= risk_per_trade
        # expired は 0
        labels.append(e.get("outcome_resolved_at", "")[:10])
        values.append(round(equity, 2))
    return labels, values


def render_my_trades_section(trades):
    """実取引ログがあれば表示。なければプレースホルダ"""
    if not trades:
        return """
      <div style="background:#f6f8fa;border:1px solid #d0d7de;border-radius:10px;padding:24px;margin-bottom:32px;text-align:center">
        <div style="font-size:1rem;color:#57606a;margin-bottom:8px">📒 実取引ログは準備中です</div>
        <div style="font-size:.85rem;color:#6e7781">サラリーマン投資家として AI シグナルをどう活用したか、実際の取引記録を順次公開予定です。</div>
      </div>"""

    # 取引集計
    closed_trades = [t for t in trades if t.get("status") == "closed"]
    open_trades = [t for t in trades if t.get("status") == "open"]
    if closed_trades:
        wins = sum(1 for t in closed_trades if (t.get("pnl_pct") or 0) > 0)
        losses = sum(1 for t in closed_trades if (t.get("pnl_pct") or 0) < 0)
        win_rate = wins / len(closed_trades) * 100 if closed_trades else 0
        total_pnl_pct = sum((t.get("pnl_pct") or 0) for t in closed_trades)
    else:
        wins = losses = 0
        win_rate = 0
        total_pnl_pct = 0

    trade_rows = []
    for t in sorted(trades, key=lambda x: x.get("entry_at", ""), reverse=True)[:30]:
        status = t.get("status", "open")
        status_emoji = "🟢 OPEN" if status == "open" else "✅ CLOSED"
        status_color = "#1a7f37" if status == "open" else "#0969da"
        pnl = t.get("pnl_pct")
        pnl_html = f'<span style="color:{"#1a7f37" if (pnl or 0) > 0 else "#cf222e"};font-weight:700">{pnl:+.2f}%</span>' if pnl is not None else "—"
        trade_rows.append(f"""
        <tr>
          <td style="white-space:nowrap">{(t.get("entry_at","")[:10])}</td>
          <td><b>{t.get("symbol","")}</b></td>
          <td style="text-align:center">{t.get("direction","")[:1]}</td>
          <td style="text-align:right">{t.get("entry_price","-")}</td>
          <td style="text-align:right">{t.get("exit_price","-")}</td>
          <td style="text-align:right">{pnl_html}</td>
          <td style="font-size:.82rem">{t.get("note","")[:30]}</td>
          <td style="color:{status_color};white-space:nowrap">{status_emoji}</td>
        </tr>""")

    return f"""
      <div style="background:linear-gradient(135deg,#ddf4ff,#ffffff);border:1px solid #54aeff;border-radius:12px;padding:24px;margin-bottom:32px">
        <h2 style="font-size:1.2rem;color:#0969da;margin-bottom:12px">💼 実取引ログ（サラリーマン投資家モデル）</h2>
        <p style="font-size:.85rem;color:#57606a;margin-bottom:16px">
          AI シグナルを参考に、平日仕事中に行った実際の取引を記録しています。
          金額はプライバシー保護のため % 表示にしています。
        </p>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-bottom:16px">
          <div style="background:#ffffff;border:1px solid #d0d7de;border-radius:8px;padding:12px;text-align:center">
            <div style="font-size:.75rem;color:#57606a">クローズ済</div>
            <div style="font-size:1.4rem;font-weight:700;color:#1f2328">{len(closed_trades)}</div>
          </div>
          <div style="background:#ffffff;border:1px solid #d0d7de;border-radius:8px;padding:12px;text-align:center">
            <div style="font-size:.75rem;color:#57606a">勝率</div>
            <div style="font-size:1.4rem;font-weight:700;color:{'#1a7f37' if win_rate>=50 else '#cf222e'}">{win_rate:.1f}%</div>
          </div>
          <div style="background:#ffffff;border:1px solid #d0d7de;border-radius:8px;padding:12px;text-align:center">
            <div style="font-size:.75rem;color:#57606a">通算 P&L</div>
            <div style="font-size:1.4rem;font-weight:700;color:{'#1a7f37' if total_pnl_pct>=0 else '#cf222e'}">{total_pnl_pct:+.2f}%</div>
          </div>
          <div style="background:#ffffff;border:1px solid #d0d7de;border-radius:8px;padding:12px;text-align:center">
            <div style="font-size:.75rem;color:#57606a">オープン中</div>
            <div style="font-size:1.4rem;font-weight:700;color:#9a6700">{len(open_trades)}</div>
          </div>
        </div>
        <div style="overflow-x:auto">
        <table style="width:100%;border-collapse:collapse;font-size:.85rem">
          <thead><tr style="background:#f6f8fa;border-bottom:2px solid #d0d7de">
            <th style="padding:8px;text-align:left">日付</th>
            <th style="padding:8px;text-align:left">銘柄</th>
            <th style="padding:8px">L/S</th>
            <th style="padding:8px;text-align:right">エントリー</th>
            <th style="padding:8px;text-align:right">クローズ</th>
            <th style="padding:8px;text-align:right">P&L%</th>
            <th style="padding:8px">メモ</th>
            <th style="padding:8px">状態</th>
          </tr></thead>
          <tbody>{''.join(trade_rows) or '<tr><td colspan="8" style="text-align:center;color:#6e7781;padding:16px">取引記録なし</td></tr>'}</tbody>
        </table>
        </div>
      </div>"""


def build_html(signals, trades):
    overall = calc_stats(signals)
    by_signal = group_stats(signals, lambda e: e.get("primary_signal"))
    by_ticker = group_stats(signals, lambda e: e.get("ticker"))
    by_direction = group_stats(signals, lambda e: e.get("direction"))

    eq_labels, eq_values = render_equity_curve_data(signals)

    # ブレイクダウン表のソート: 勝率降順、最低 3 件以上のみ表示
    def _filtered_sorted(stats_dict, min_total=1):
        return sorted(
            [(k, v) for k, v in stats_dict.items() if v["total"] >= min_total],
            key=lambda x: x[1]["win_rate"], reverse=True,
        )

    signal_rows = "\n".join(
        render_stat_row(SIGNAL_LABELS.get(k, k), v)
        for k, v in _filtered_sorted(by_signal)
    ) or '<tr><td colspan="7" style="text-align:center;color:#6e7781;padding:16px">データ蓄積中</td></tr>'

    ticker_rows = "\n".join(
        render_stat_row(k, v)
        for k, v in _filtered_sorted(by_ticker)
    ) or '<tr><td colspan="7" style="text-align:center;color:#6e7781;padding:16px">データ蓄積中</td></tr>'

    direction_rows = "\n".join(
        render_stat_row(k, v)
        for k, v in _filtered_sorted(by_direction)
    ) or '<tr><td colspan="7" style="text-align:center;color:#6e7781;padding:16px">データ蓄積中</td></tr>'

    recent_rows = render_recent_table(signals, limit=30)
    my_trades_html = render_my_trades_section(trades)
    last_updated = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")

    # サマリーカード
    win_color = "#1a7f37" if overall["win_rate"] >= 60 else "#9a6700" if overall["win_rate"] >= 45 else "#cf222e"
    er_color = "#1a7f37" if overall["expected_R"] > 0.3 else "#9a6700" if overall["expected_R"] > 0 else "#cf222e"

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>📊 シグナル品質トラッキング - MarketWatch AI</title>
  <meta name="description" content="MarketWatch AI が配信する 4H テクニカルシグナルの的中率・期待 R を自動集計。サラリーマン投資家の実取引ログも公開。">
  <link rel="canonical" href="https://marketwatch-jp.com/track-record.html">
  <meta property="og:type" content="website">
  <meta property="og:title" content="📊 シグナル品質トラッキング - MarketWatch AI">
  <meta property="og:description" content="4H テクニカルシグナルの的中率・実取引ログを完全公開。AI 投資の透明性を追求。">
  <meta property="og:url" content="https://marketwatch-jp.com/track-record.html">
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-FMVFEV7Q2E"></script>
  <script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-FMVFEV7Q2E');</script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    *{{margin:0;padding:0;box-sizing:border-box}}
    body{{font-family:'Noto Sans JP','Segoe UI','Hiragino Sans','Yu Gothic',sans-serif;background:#ffffff;color:#1f2328;min-height:100vh;line-height:1.7}}
    header{{background:linear-gradient(135deg,#f6f8fa,#ffffff);border-bottom:1px solid #d0d7de;padding:24px 32px}}
    .header-inner{{max-width:1200px;margin:0 auto}}
    .header-title{{font-size:1.6rem;font-weight:700;background:linear-gradient(90deg,#0969da,#1f6feb);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}
    .header-meta{{font-size:.85rem;color:#57606a;margin-top:4px}}
    main{{max-width:1200px;margin:0 auto;padding:32px 24px}}
    .nav-bar{{display:flex;flex-wrap:wrap;gap:10px;justify-content:center;margin-bottom:32px}}
    .nav-btn{{display:inline-flex;align-items:center;justify-content:center;gap:8px;padding:11px 20px;background:#f6f8fa;border:1px solid #d0d7de;border-radius:10px;color:#57606a;text-decoration:none;font-size:.95rem;font-weight:600;min-width:170px;transition:all .2s}}
    .nav-btn:hover{{border-color:#0969da;color:#0969da}}
    .nav-btn.current{{background:#0969da;border-color:#0969da;color:#fff}}
    .breadcrumb{{font-size:.82rem;color:#57606a;margin-bottom:16px}}
    .breadcrumb a{{color:#0969da;text-decoration:none}}
    .page-header{{background:#f6f8fa;border:1px solid #d0d7de;border-radius:12px;padding:28px 32px;margin-bottom:24px}}
    h1{{font-size:1.8rem;color:#0969da;margin-bottom:8px}}
    h2{{font-size:1.25rem;color:#1f6feb;margin:24px 0 14px}}
    .page-desc{{font-size:.92rem;color:#57606a}}
    .kpi-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;margin-bottom:32px}}
    .kpi-card{{background:#f6f8fa;border:1px solid #d0d7de;border-left:4px solid #0969da;border-radius:10px;padding:18px 22px}}
    .kpi-label{{font-size:.78rem;color:#57606a;letter-spacing:.04em;margin-bottom:6px}}
    .kpi-value{{font-size:1.8rem;font-weight:700;color:#1f2328}}
    .kpi-sub{{font-size:.75rem;color:#6e7781;margin-top:4px}}
    table{{width:100%;border-collapse:collapse;font-size:.88rem;background:#fff;border:1px solid #d0d7de;border-radius:8px;overflow:hidden}}
    table th{{background:#f6f8fa;padding:10px 12px;text-align:left;border-bottom:2px solid #d0d7de;font-size:.82rem;color:#424a53;font-weight:600}}
    table td{{padding:9px 12px;border-bottom:1px solid #eaeef2;color:#1f2328}}
    table tr:last-child td{{border-bottom:none}}
    .scroll-x{{overflow-x:auto;border:1px solid #d0d7de;border-radius:8px}}
    .scroll-x table{{border:none;border-radius:0}}
    .chart-box{{background:#fff;border:1px solid #d0d7de;border-radius:10px;padding:18px;margin-bottom:32px;height:340px}}
    .info-box{{background:#fff8c5;border-left:4px solid #d4a72c;border-radius:6px;padding:14px 18px;margin-bottom:24px;font-size:.85rem;color:#6e5d00}}
    footer{{background:#f6f8fa;border-top:1px solid #d0d7de;padding:20px 32px;text-align:center;font-size:.78rem;color:#6e7781;margin-top:40px}}
    footer a{{color:#0969da;text-decoration:none}}
    @media(max-width:600px){{.nav-bar{{display:grid;grid-template-columns:1fr 1fr;gap:8px}}.nav-btn{{min-width:0;width:100%;padding:10px 8px;font-size:.82rem}}.kpi-value{{font-size:1.4rem}}h1{{font-size:1.4rem}}}}
    body.dark{{background:#0d1117;color:#e6edf3}}
    body.dark header{{background:linear-gradient(135deg,#161b22,#0d1117);border-bottom-color:#30363d}}
    body.dark .header-meta{{color:#8b949e}}
    body.dark .nav-btn{{background:#161b22;border-color:#30363d;color:#8b949e}}
    body.dark .nav-btn:hover{{border-color:#58a6ff;color:#58a6ff}}
    body.dark .page-header{{background:#161b22;border-color:#30363d}}
    body.dark .page-desc{{color:#8b949e}}
    body.dark h1{{color:#79c0ff}}
    body.dark h2{{color:#79c0ff}}
    body.dark .kpi-card{{background:#161b22;border-color:#30363d}}
    body.dark .kpi-label{{color:#8b949e}}
    body.dark .kpi-value{{color:#e6edf3}}
    body.dark table{{background:#161b22;border-color:#30363d}}
    body.dark table th{{background:#0d1117;border-bottom-color:#30363d;color:#c9d1d9}}
    body.dark table td{{border-bottom-color:#21262d;color:#e6edf3}}
    body.dark .scroll-x{{border-color:#30363d}}
    body.dark .chart-box{{background:#161b22;border-color:#30363d}}
    body.dark .info-box{{background:#332700;border-left-color:#d4a72c;color:#f0d774}}
    body.dark footer{{background:#161b22;border-top-color:#30363d;color:#8b949e}}
  </style>
</head>
<body>
<button id="theme-toggle" onclick="toggleTheme()" aria-label="テーマ切替" style="position:fixed;top:16px;right:16px;width:42px;height:42px;border-radius:50%;border:1px solid #d0d7de;background:#fff;cursor:pointer;z-index:9999;box-shadow:0 2px 8px rgba(0,0,0,.1);font-size:18px;display:flex;align-items:center;justify-content:center">🌙</button>
<header>
  <div class="header-inner">
    <div class="header-title">📊 MarketWatch AI</div>
    <div class="header-meta">日本人投資家のためのマーケット情報サイト</div>
  </div>
</header>
<main>
  <nav class="nav-bar">
    <a class="nav-btn" href="index.html">🏠 トップページ</a>
    <a class="nav-btn" href="calendar.html">📅 経済カレンダー</a>
    <a class="nav-btn" href="charts.html">📈 50年チャート</a>
    <a class="nav-btn" href="guides.html">📚 解説記事</a>
    <a class="nav-btn current" href="track-record.html">📊 シグナル成績</a>
    <a class="nav-btn" href="youtube-summary.html">📺 YouTube要約</a>
  </nav>

  <div class="breadcrumb">
    <a href="index.html">ホーム</a> &gt; シグナル品質トラッキング
  </div>

  <div class="page-header">
    <h1>📊 シグナル品質トラッキング</h1>
    <div class="page-desc">
      MarketWatch AI が配信する 4H テクニカルシグナルの的中率・期待 R を自動集計。
      AI シグナルの透明性を追求し、サラリーマン投資家として実際にどう活用しているかを公開しています。
      <span style="color:#6e7781">（最終更新: {last_updated}）</span>
    </div>
  </div>

  <div class="info-box">
    💡 <b>判定ルール</b>: シグナル発火後、ロングなら高値が TP1/TP2 に達したか、安値が SL に達したかをチェック。
    7 日経過してどれもヒットしなければ「期限切れ」。SL/TP は ATR(14) × 1.5/2.0/3.0 で機械算出。
    <b>R:R 期待値</b> は「リスク 1 単位あたり何倍リターンしたか」の指標で、+0.3R 以上が安定。
  </div>

  <h2>📈 全体パフォーマンス</h2>
  <div class="kpi-grid">
    <div class="kpi-card">
      <div class="kpi-label">確定シグナル総数</div>
      <div class="kpi-value">{overall['total']}</div>
      <div class="kpi-sub">うち未確定 {sum(1 for e in signals if not e.get('outcome'))} 件</div>
    </div>
    <div class="kpi-card" style="border-left-color:{win_color}">
      <div class="kpi-label">勝率（TP1+TP2 / 全確定）</div>
      <div class="kpi-value" style="color:{win_color}">{overall['win_rate']:.1f}%</div>
      <div class="kpi-sub">勝ち {overall['wins']} / 負け {overall['losses']} / 期限切れ {overall['expired']}</div>
    </div>
    <div class="kpi-card" style="border-left-color:#1a7f37">
      <div class="kpi-label">TP2 到達率</div>
      <div class="kpi-value" style="color:#1a7f37">{overall['tp2_rate']:.1f}%</div>
      <div class="kpi-sub">R:R 1:2.0 達成</div>
    </div>
    <div class="kpi-card" style="border-left-color:{er_color}">
      <div class="kpi-label">期待 R</div>
      <div class="kpi-value" style="color:{er_color}">{overall['expected_R']:+.2f}R</div>
      <div class="kpi-sub">+0.3R 以上で安定</div>
    </div>
    <div class="kpi-card" style="border-left-color:#1a7f37">
      <div class="kpi-label">平均最大含み益</div>
      <div class="kpi-value" style="color:#1a7f37">{overall['avg_mfe']:+.2f}%</div>
      <div class="kpi-sub">MFE 指標</div>
    </div>
    <div class="kpi-card" style="border-left-color:#cf222e">
      <div class="kpi-label">平均最大含み損</div>
      <div class="kpi-value" style="color:#cf222e">{overall['avg_mae']:+.2f}%</div>
      <div class="kpi-sub">MAE 指標</div>
    </div>
  </div>

  <h2>💹 模擬エクイティカーブ</h2>
  <div class="chart-box">
    <canvas id="equityChart"></canvas>
  </div>

  {my_trades_html}

  <h2>🎯 シグナル種別ブレイクダウン</h2>
  <div class="scroll-x">
  <table>
    <thead><tr>
      <th>シグナル</th><th style="text-align:right">確定数</th><th style="text-align:right">勝率</th>
      <th style="text-align:right">TP1率</th><th style="text-align:right">TP2率</th>
      <th style="text-align:right">SL</th><th style="text-align:right">期待 R</th>
    </tr></thead>
    <tbody>{signal_rows}</tbody>
  </table>
  </div>

  <h2 style="margin-top:24px">🏷️ 銘柄ブレイクダウン</h2>
  <div class="scroll-x">
  <table>
    <thead><tr>
      <th>銘柄</th><th style="text-align:right">確定数</th><th style="text-align:right">勝率</th>
      <th style="text-align:right">TP1率</th><th style="text-align:right">TP2率</th>
      <th style="text-align:right">SL</th><th style="text-align:right">期待 R</th>
    </tr></thead>
    <tbody>{ticker_rows}</tbody>
  </table>
  </div>

  <h2 style="margin-top:24px">📐 方向別ブレイクダウン</h2>
  <div class="scroll-x">
  <table>
    <thead><tr>
      <th>方向</th><th style="text-align:right">確定数</th><th style="text-align:right">勝率</th>
      <th style="text-align:right">TP1率</th><th style="text-align:right">TP2率</th>
      <th style="text-align:right">SL</th><th style="text-align:right">期待 R</th>
    </tr></thead>
    <tbody>{direction_rows}</tbody>
  </table>
  </div>

  <h2 style="margin-top:24px">📒 直近 30 件のシグナル詳細</h2>
  <div class="scroll-x">
  <table style="font-size:.82rem">
    <thead><tr>
      <th>発火時刻</th><th>銘柄</th><th>シグナル</th><th>L/S</th>
      <th style="text-align:right">エントリー</th><th style="text-align:right">SL</th><th style="text-align:right">TP1</th>
      <th style="text-align:right">MFE</th><th style="text-align:right">MAE</th><th>結果</th>
    </tr></thead>
    <tbody>{recent_rows or '<tr><td colspan="10" style="text-align:center;color:#6e7781;padding:16px">シグナル蓄積中（最初の発火を待っています）</td></tr>'}</tbody>
  </table>
  </div>
</main>

<footer>
  <p>© 2026 MarketWatch AI | <a href="about.html">サイトについて</a> | <a href="privacy.html">プライバシーポリシー</a> | <a href="contact.html">お問い合わせ</a></p>
  <p style="margin-top:8px;font-size:.72rem;color:#8b949e">
    本ページの数値は yfinance の価格データを基に機械的に判定したものであり、実際の取引結果を保証するものではありません。
    投資判断は自己責任でお願いします。
  </p>
</footer>

<script>
  // Equity Chart
  const eqLabels = {json.dumps(eq_labels, ensure_ascii=False)};
  const eqValues = {json.dumps(eq_values)};
  if (eqLabels.length > 0) {{
    const ctx = document.getElementById('equityChart').getContext('2d');
    const isDark = document.body.classList.contains('dark');
    new Chart(ctx, {{
      type: 'line',
      data: {{
        labels: eqLabels,
        datasets: [{{
          label: '模擬残高 ($1000 スタート / $100 リスク per シグナル)',
          data: eqValues,
          borderColor: '#0969da',
          backgroundColor: 'rgba(9, 105, 218, 0.1)',
          fill: true,
          tension: 0.2,
          pointRadius: 3,
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{ legend: {{ position: 'top' }} }},
        scales: {{
          y: {{ ticks: {{ callback: v => '$' + v.toLocaleString() }} }}
        }}
      }}
    }});
  }} else {{
    document.querySelector('#equityChart').parentElement.innerHTML =
      '<div style="text-align:center;padding:60px 0;color:#6e7781">確定シグナルが揃ったらここにエクイティカーブが表示されます</div>';
  }}

  // Dark mode toggle
  function toggleTheme(){{
    document.body.classList.toggle('dark');
    localStorage.setItem('theme', document.body.classList.contains('dark') ? 'dark' : 'light');
    document.getElementById('theme-toggle').textContent = document.body.classList.contains('dark') ? '☀️' : '🌙';
  }}
  if (localStorage.getItem('theme') === 'dark') {{
    document.body.classList.add('dark');
    document.getElementById('theme-toggle').textContent = '☀️';
  }}
</script>
</body>
</html>
"""


def main():
    print("📊 track-record.html を生成中...")
    signals = load_json(SIGNALS_LOG_FILE)
    trades = load_json(TRADES_LOG_FILE)
    print(f"  シグナル: {len(signals)} 件、実取引: {len(trades)} 件")

    html = build_html(signals, trades)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    size_kb = os.path.getsize(OUTPUT_FILE) / 1024
    print(f"✅ {OUTPUT_FILE} を生成 ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
