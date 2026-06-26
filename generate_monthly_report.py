# -*- coding: utf-8 -*-
"""
マンスリー成績レポート 自動生成スクリプト (C3)
=====================================================
毎月 1 日朝に「先月の AI トレード成績書」を集計し、
guide-monthly-report-YYYY-MM.html として配置する。

データソース:
- signals-log.json: 先月のシグナル発火履歴
- my-trades.json:   先月のユーザー実取引

使い方:
    python generate_monthly_report.py            # 月初 (1〜3 日) のみ実行
    python generate_monthly_report.py --force    # 日付関係なく強制実行

GitHub Actions schedule: 毎月 1 日 00:23 UTC = 09:23 JST
"""
import os
import sys
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))
SIGNALS_LOG_FILE = "signals-log.json"
TRADES_FILE = "my-trades.json"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _parse_iso(s):
    try:
        return datetime.fromisoformat(s) if s else None
    except Exception:
        return None


def month_range(target_year, target_month):
    """指定年月の (開始日時, 翌月初日時) を JST で返す"""
    start = datetime(target_year, target_month, 1, tzinfo=JST)
    if target_month == 12:
        end = datetime(target_year + 1, 1, 1, tzinfo=JST)
    else:
        end = datetime(target_year, target_month + 1, 1, tzinfo=JST)
    return start, end


def summarize_signals(signals, month_start, month_end):
    in_month = [s for s in signals
                if (dt := _parse_iso(s.get("fired_at"))) and month_start <= dt < month_end]

    by_tf = defaultdict(list)
    for s in in_month:
        by_tf[s.get("timeframe", "?")].append(s)

    closed = [s for s in in_month if s.get("outcome") in ("tp1", "tp2", "sl", "expired")]
    tp1 = sum(1 for s in closed if s.get("outcome") == "tp1")
    tp2 = sum(1 for s in closed if s.get("outcome") == "tp2")
    sl = sum(1 for s in closed if s.get("outcome") == "sl")
    exp = sum(1 for s in closed if s.get("outcome") == "expired")
    wins = tp1 + tp2
    win_rate = wins / len(closed) * 100 if closed else 0

    # 期待 R: tp1=+1.33R, tp2=+2.0R, sl=-1.0R, expired=0
    expected_r = (tp1 * 1.33 + tp2 * 2.0 + sl * -1.0) / len(closed) if closed else 0

    # 信頼度別
    by_conf = defaultdict(lambda: {"total": 0, "wins": 0, "sl": 0})
    for s in closed:
        label = (s.get("confidence") or {}).get("label") or "—"
        by_conf[label]["total"] += 1
        if s.get("outcome") in ("tp1", "tp2"):
            by_conf[label]["wins"] += 1
        if s.get("outcome") == "sl":
            by_conf[label]["sl"] += 1

    # 環境スコア別
    by_env = defaultdict(lambda: {"total": 0, "wins": 0, "sl": 0})
    for s in closed:
        label = (s.get("environment") or {}).get("env_score") or "—"
        by_env[label]["total"] += 1
        if s.get("outcome") in ("tp1", "tp2"):
            by_env[label]["wins"] += 1
        if s.get("outcome") == "sl":
            by_env[label]["sl"] += 1

    # 銘柄別
    by_ticker = defaultdict(lambda: {"wins": 0, "sl": 0, "total": 0, "name": ""})
    for s in closed:
        tk = s.get("ticker", "?")
        by_ticker[tk]["name"] = s.get("asset_name", tk)
        by_ticker[tk]["total"] += 1
        if s.get("outcome") in ("tp1", "tp2"):
            by_ticker[tk]["wins"] += 1
        elif s.get("outcome") == "sl":
            by_ticker[tk]["sl"] += 1

    return {
        "total": len(in_month),
        "by_tf": {k: len(v) for k, v in by_tf.items()},
        "closed": len(closed),
        "tp1": tp1, "tp2": tp2, "sl": sl, "expired": exp,
        "win_rate": round(win_rate, 1),
        "expected_r": round(expected_r, 2),
        "by_conf": dict(by_conf),
        "by_env": dict(by_env),
        "by_ticker": dict(by_ticker),
    }


def summarize_trades(trades, month_start, month_end):
    in_month = []
    for t in trades:
        e_dt = _parse_iso(t.get("entry_at"))
        x_dt = _parse_iso(t.get("exit_at"))
        if (e_dt and month_start <= e_dt < month_end) or \
           (x_dt and month_start <= x_dt < month_end):
            in_month.append(t)

    closed = [t for t in in_month if t.get("status") == "closed"]
    wins = sum(1 for t in closed if (t.get("pnl_pct") or 0) > 0)
    losses = sum(1 for t in closed if (t.get("pnl_pct") or 0) < 0)
    total_pnl_pct = sum((t.get("pnl_pct") or 0) for t in closed)
    best = max(closed, key=lambda t: t.get("pnl_pct") or 0, default=None)
    worst = min(closed, key=lambda t: t.get("pnl_pct") or 0, default=None)

    return {
        "total": len(in_month),
        "closed": len(closed),
        "wins": wins,
        "losses": losses,
        "win_rate": round(wins / len(closed) * 100, 1) if closed else 0,
        "total_pnl_pct": round(total_pnl_pct, 2),
        "best": best, "worst": worst,
        "trades": closed,
    }


def ai_summary(year, month, sig_stats, trade_stats, api_key):
    """Gemini で「今月の総評」を生成"""
    if not api_key:
        return _fallback_summary(sig_stats, trade_stats)
    try:
        import google.generativeai as genai
    except ImportError:
        return _fallback_summary(sig_stats, trade_stats)
    genai.configure(api_key=api_key)

    # 信頼度・環境スコアごとの勝率
    conf_wr = {k: f"{v['wins']}/{v['total']} ({(v['wins']/v['total']*100):.0f}%)" if v['total'] else "0/0" for k, v in sig_stats["by_conf"].items()}
    env_wr = {k: f"{v['wins']}/{v['total']} ({(v['wins']/v['total']*100):.0f}%)" if v['total'] else "0/0" for k, v in sig_stats["by_env"].items()}
    # ベスト/ワースト銘柄
    by_t = sig_stats.get("by_ticker", {})
    top_winner = max(by_t.items(), key=lambda x: x[1]["wins"] - x[1]["sl"], default=(None, None))
    top_loser = min(by_t.items(), key=lambda x: x[1]["wins"] - x[1]["sl"], default=(None, None))

    prompt = f"""あなたは日本人個人投資家（サラリーマン × 4H スイング × MT4）向けの投資メディア編集長です。
{year}年{month}月の AI シグナルと実取引データから、月次成績レポートの中核セクションを執筆してください。

【シグナル統計】
- 発火数: {sig_stats['total']} 件（4H {sig_stats['by_tf'].get('4h', 0)} / 1H {sig_stats['by_tf'].get('1h', 0)}）
- 確定: {sig_stats['closed']} 件（TP1 {sig_stats['tp1']} / TP2 {sig_stats['tp2']} / SL {sig_stats['sl']} / 期限切れ {sig_stats['expired']}）
- 月間勝率: {sig_stats['win_rate']}% / 期待 R: {sig_stats['expected_r']}
- 信頼度別 勝率: {conf_wr}
- 環境スコア別 勝率: {env_wr}
- ベスト銘柄: {top_winner[0] if top_winner[0] else "なし"}（勝-負 = {(top_winner[1] or {{}}).get("wins", 0) - (top_winner[1] or {{}}).get("sl", 0) if top_winner[1] else 0}）
- ワースト銘柄: {top_loser[0] if top_loser[0] else "なし"}（勝-負 = {(top_loser[1] or {{}}).get("wins", 0) - (top_loser[1] or {{}}).get("sl", 0) if top_loser[1] else 0}）

【実取引】
- 取引数: {trade_stats['closed']} 件 / 勝率: {trade_stats['win_rate']}% / 通算 P&L: {trade_stats['total_pnl_pct']}%

【執筆要件】（必ず守る）
- 「今月のハイライト」を 1 段落 (200-250 字): 数値を必ず引用、定量的な発見を最低 2 つ含める。例「{month}月は HIGH スコア勝率 {{HIGH_WR}} が MID {{MID_WR}} を 20pt 上回り、信頼度スコアの予測力が確認された月となった」
- 「データから見えた示唆」を箇条書き 3-4 項目: それぞれデータ根拠を明示。例「・環境 A スコアは {{env_a_wr}} の勝率 → 経済イベント無い時の優位性を確認」
- 「来月の改善ポイント」を箇条書き 2-3 項目: 具体的なアクション提案。例「・LOW スコアシグナルは {{low_wr}} なので、来月は完全に見送り、HIGH のみエントリー」

【避けること】
- 抽象的な感想（「市場は不安定だった」など）
- 投資助言の断定（「○○を買え」）。「○○を検討する価値あり」までに留める
- HTML / Markdown
- 数値を引用しない一般論

出力はプレーンテキスト、3 セクション構成。
"""
    # マンスリーは月 1 回の最重要レポートなので、品質優先で上位モデルから試行
    for model_name in ("gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.5-flash-lite"):
        try:
            model = genai.GenerativeModel(model_name)
            resp = model.generate_content(prompt)
            text = (resp.text or "").strip()
            if text:
                return text
        except Exception:
            continue
    return _fallback_summary(sig_stats, trade_stats)


def _fallback_summary(sig_stats, trade_stats):
    if sig_stats["closed"] == 0:
        return "今月は確定したシグナルが少なく、月次集計に十分なデータがありません。来月以降の蓄積に期待します。"
    return f"""今月のシグナル勝率は {sig_stats['win_rate']}%、期待 R は {sig_stats['expected_r']:+.2f}R でした。
確定 {sig_stats['closed']} 件のうち、TP1 {sig_stats['tp1']} / TP2 {sig_stats['tp2']} / SL {sig_stats['sl']}。
実取引は {trade_stats['closed']} 件・勝率 {trade_stats['win_rate']}%・通算 {trade_stats['total_pnl_pct']:+.2f}% でした。"""


def render_html(year, month, today, sig_stats, trade_stats, summary_text):
    month_str = f"{year}-{month:02d}"
    today_jp = today.strftime("%Y年%m月%d日")

    # 信頼度
    conf_rows = []
    for label in ("HIGH", "MID", "LOW"):
        d = sig_stats["by_conf"].get(label)
        if d and d["total"]:
            wr = d["wins"] / d["total"] * 100
            color = "#1a7f37" if wr >= 60 else "#9a6700" if wr >= 45 else "#cf222e"
            conf_rows.append(f'<tr><td><b>{label}</b></td><td style="text-align:right">{d["total"]}</td>'
                             f'<td style="text-align:right">{d["wins"]}</td>'
                             f'<td style="text-align:right">{d["sl"]}</td>'
                             f'<td style="text-align:right;color:{color};font-weight:700">{wr:.1f}%</td></tr>')
    conf_html = "\n".join(conf_rows) or '<tr><td colspan="5" style="text-align:center;color:#6e7781">データなし</td></tr>'

    # 環境スコア
    env_rows = []
    for label in ("A", "B", "C", "D"):
        d = sig_stats["by_env"].get(label)
        if d and d["total"]:
            wr = d["wins"] / d["total"] * 100
            color = "#1a7f37" if wr >= 60 else "#9a6700" if wr >= 45 else "#cf222e"
            env_rows.append(f'<tr><td><b>{label}</b></td><td style="text-align:right">{d["total"]}</td>'
                            f'<td style="text-align:right">{d["wins"]}</td>'
                            f'<td style="text-align:right">{d["sl"]}</td>'
                            f'<td style="text-align:right;color:{color};font-weight:700">{wr:.1f}%</td></tr>')
    env_html = "\n".join(env_rows) or '<tr><td colspan="5" style="text-align:center;color:#6e7781">データなし</td></tr>'

    # 銘柄ランキング
    ticker_rows = []
    items = sorted(sig_stats["by_ticker"].items(), key=lambda x: -(x[1]["wins"] - x[1]["sl"]))
    for tk, d in items[:10]:
        wr = d["wins"] / d["total"] * 100 if d["total"] else 0
        color = "#1a7f37" if wr >= 60 else "#9a6700" if wr >= 45 else "#cf222e"
        ticker_rows.append(f'<tr><td><b>{d["name"]}</b> <span style="color:#6e7781;font-size:.85em">{tk}</span></td>'
                           f'<td style="text-align:right">{d["total"]}</td>'
                           f'<td style="text-align:right;color:#1a7f37">{d["wins"]}</td>'
                           f'<td style="text-align:right;color:#cf222e">{d["sl"]}</td>'
                           f'<td style="text-align:right;color:{color};font-weight:700">{wr:.1f}%</td></tr>')
    ticker_html = "\n".join(ticker_rows) or '<tr><td colspan="5" style="text-align:center;color:#6e7781">確定シグナルなし</td></tr>'

    # 実取引ベスト/ワースト
    best_html = "—"
    worst_html = "—"
    if trade_stats["best"]:
        b = trade_stats["best"]
        best_html = f'<b>{b.get("symbol")}</b> ({b.get("direction","")[:1]}): <span style="color:#1a7f37;font-weight:700">{b.get("pnl_pct"):+.2f}%</span>'
    if trade_stats["worst"]:
        w = trade_stats["worst"]
        worst_html = f'<b>{w.get("symbol")}</b> ({w.get("direction","")[:1]}): <span style="color:#cf222e;font-weight:700">{w.get("pnl_pct"):+.2f}%</span>'

    # 総評を HTML 化
    summary_parts = []
    for para in summary_text.split("\n\n"):
        para = para.strip()
        if not para:
            continue
        if any(line.lstrip().startswith(("・", "-", "*")) for line in para.splitlines()):
            items = [line.lstrip("・-* ").strip() for line in para.splitlines() if line.strip()]
            summary_parts.append("<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>")
        else:
            summary_parts.append(f"<p>{para}</p>")
    summary_html = "\n".join(summary_parts)

    pnl_color = "#1a7f37" if trade_stats["total_pnl_pct"] >= 0 else "#cf222e"
    wr_color = "#1a7f37" if sig_stats["win_rate"] >= 60 else "#9a6700" if sig_stats["win_rate"] >= 45 else "#cf222e"

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex,follow"><!-- 自動生成の月次成績レポート：インデックス除外（AdSense低価値対策） -->
<title>📊 {year}年{month}月 AI トレード成績レポート｜MarketWatch AI</title>
<meta name="description" content="{year}年{month}月の MarketWatch AI シグナル成績を完全公開。月間勝率・期待 R・信頼度別・環境スコア別・銘柄別を集計、実取引と AI 総評。">
<link rel="canonical" href="https://marketwatch-jp.com/guide-monthly-report-{month_str}.html">
<meta property="og:type" content="article">
<meta property="og:title" content="📊 {year}年{month}月 AI トレード成績レポート｜MarketWatch AI">
<meta property="og:description" content="{year}年{month}月の MarketWatch AI シグナル成績を完全公開。月間勝率・期待 R・信頼度別・環境スコア別・銘柄別を集計、実取引と AI 総評。">
<meta property="og:url" content="https://marketwatch-jp.com/guide-monthly-report-{month_str}.html">
<meta property="og:site_name" content="MarketWatch AI">
<meta property="og:locale" content="ja_JP">
<meta property="og:image" content="https://marketwatch-jp.com/12_feature_market_health.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="https://marketwatch-jp.com/12_feature_market_health.png">
<script async src="https://www.googletagmanager.com/gtag/js?id=G-FMVFEV7Q2E"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-FMVFEV7Q2E');</script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Noto Sans JP','Segoe UI','Hiragino Sans',sans-serif;background:#fff;color:#1f2328;line-height:1.85}}
header{{background:linear-gradient(135deg,#f6f8fa,#fff);border-bottom:1px solid #d0d7de;padding:24px 32px}}
.header-inner{{max-width:1200px;margin:0 auto}}
.header-title{{font-size:1.6rem;font-weight:700;background:linear-gradient(90deg,#0969da,#1f6feb);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}
.header-meta{{font-size:.85rem;color:#57606a;margin-top:4px}}
main{{max-width:1100px;margin:0 auto;padding:32px 24px}}
.nav-bar{{display:flex;flex-wrap:wrap;gap:10px;justify-content:center;max-width:1000px;margin:0 auto 32px}}
.nav-btn{{padding:11px 20px;background:#f6f8fa;border:1px solid #d0d7de;border-radius:10px;color:#57606a;text-decoration:none;font-size:.95rem;font-weight:600;min-width:170px;text-align:center;display:inline-flex;align-items:center;justify-content:center;gap:8px}}
.nav-btn.current{{background:#0969da;border-color:#0969da;color:#fff}}
.breadcrumb{{font-size:.82rem;color:#57606a;margin-bottom:16px}}
.breadcrumb a{{color:#0969da;text-decoration:none}}
.article{{background:#f6f8fa;border:1px solid #d0d7de;border-radius:12px;padding:36px 40px}}
h1{{font-size:1.85rem;color:#0969da;margin-bottom:8px;line-height:1.4}}
.meta-line{{font-size:.85rem;color:#57606a;margin-bottom:28px;padding-bottom:18px;border-bottom:1px solid #d0d7de}}
h2{{font-size:1.3rem;color:#1f6feb;margin-top:32px;margin-bottom:14px;padding-bottom:8px;border-bottom:2px solid #d0d7de}}
p{{font-size:.97rem;color:#424a53;margin-bottom:16px}}
ul{{margin:10px 0 18px 28px;color:#424a53}}
li{{margin-bottom:8px}}
.kpi-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px;margin:18px 0 28px}}
.kpi{{background:#fff;border:1px solid #d0d7de;border-left:4px solid #0969da;border-radius:10px;padding:18px;text-align:center}}
.kpi-num{{font-size:1.8rem;font-weight:800;color:#0969da}}
.kpi-num.up{{color:#1a7f37}}
.kpi-num.down{{color:#cf222e}}
.kpi-label{{font-size:.78rem;color:#57606a;margin-top:6px}}
table{{width:100%;border-collapse:collapse;font-size:.9rem;background:#fff;border:1px solid #d0d7de;border-radius:8px;overflow:hidden;margin:14px 0}}
th{{background:#f6f8fa;padding:10px 12px;text-align:left;border-bottom:2px solid #d0d7de;font-size:.82rem;color:#424a53}}
td{{padding:9px 12px;border-bottom:1px solid #eaeef2}}
tr:last-child td{{border-bottom:none}}
.info-box{{background:#ddf4ff;border-left:4px solid #0969da;border-radius:6px;padding:14px 18px;margin:16px 0;font-size:.92rem;color:#1f6feb}}
.warning-box{{background:#fff8c5;border-left:4px solid #9a6700;border-radius:6px;padding:14px 18px;margin:16px 0;font-size:.92rem;color:#9a6700}}
footer{{background:#f6f8fa;border-top:1px solid #d0d7de;padding:20px 32px;text-align:center;font-size:.78rem;color:#6e7781;margin-top:40px}}
footer a{{color:#0969da;text-decoration:none}}
@media(max-width:600px){{.article{{padding:24px 20px}}h1{{font-size:1.4rem}}.nav-bar{{display:grid;grid-template-columns:1fr 1fr}}.nav-btn{{min-width:0;width:100%}}}}
</style>
</head>
<body>
<header><div class="header-inner"><div class="header-title">📊 MarketWatch AI</div><div class="header-meta">日本人投資家のためのマーケット情報サイト</div><div style="margin-top:11px;padding-top:11px;border-top:1px solid rgba(128,128,128,.22)"><div style="font-size:1.3rem;font-weight:700;color:#0969da">📚 解説記事</div></div></div></header>
<main>
<nav class="nav-bar">
  <a class="nav-btn" href="index.html">🏠 トップページ</a>
  <a class="nav-btn" href="political-feed.html">🚨 政治発言ライブ</a>
  <a class="nav-btn" href="track-record.html">📊 シグナル成績</a>
  <a class="nav-btn" href="calendar.html">📅 経済カレンダー</a>
  <a class="nav-btn current" href="guides.html">📚 解説記事</a>
  <a class="nav-btn" href="guide-investment-books.html">📖 投資本</a>
  <a class="nav-btn" href="market-health.html">🩺 市場健康度</a>
  <a class="nav-btn" href="hot-assets.html">🔥 出来高急増</a>
  <a class="nav-btn" href="charts.html">📈 50年チャート</a>
  <a class="nav-btn" href="youtube-summary.html">📺 YouTube要約</a>
</nav>
<div class="breadcrumb"><a href="index.html">ホーム</a> ＞ <a href="guides.html">解説記事</a> ＞ {year}年{month}月 成績レポート</div>

<article class="article">
<h1>📊 {year}年{month}月 AI トレード成績レポート</h1>
<div class="meta-line">公開日：{today_jp}（月初 1 日 自動更新）／ カテゴリ：月次レポート（自動生成）</div>

<h2>🎯 月間 KPI サマリ</h2>
<div class="kpi-grid">
  <div class="kpi"><div class="kpi-num">{sig_stats['total']}</div><div class="kpi-label">シグナル発火（4H {sig_stats['by_tf'].get('4h', 0)} / 1H {sig_stats['by_tf'].get('1h', 0)}）</div></div>
  <div class="kpi"><div class="kpi-num">{sig_stats['closed']}</div><div class="kpi-label">確定 (TP1+TP2+SL+期限切れ)</div></div>
  <div class="kpi"><div class="kpi-num up">{sig_stats['tp1'] + sig_stats['tp2']}</div><div class="kpi-label">勝ち</div></div>
  <div class="kpi"><div class="kpi-num down">{sig_stats['sl']}</div><div class="kpi-label">SL ヒット</div></div>
  <div class="kpi"><div class="kpi-num" style="color:{wr_color}">{sig_stats['win_rate']:.1f}%</div><div class="kpi-label">月間勝率</div></div>
  <div class="kpi"><div class="kpi-num" style="color:{'#1a7f37' if sig_stats['expected_r'] > 0 else '#cf222e'}">{sig_stats['expected_r']:+.2f}R</div><div class="kpi-label">期待 R</div></div>
</div>

<h2>💼 実取引 サマリ</h2>
<div class="kpi-grid">
  <div class="kpi"><div class="kpi-num">{trade_stats['closed']}</div><div class="kpi-label">クローズ取引</div></div>
  <div class="kpi"><div class="kpi-num up">{trade_stats['wins']}</div><div class="kpi-label">勝ち</div></div>
  <div class="kpi"><div class="kpi-num down">{trade_stats['losses']}</div><div class="kpi-label">負け</div></div>
  <div class="kpi"><div class="kpi-num" style="color:{wr_color}">{trade_stats['win_rate']:.1f}%</div><div class="kpi-label">実取引勝率</div></div>
  <div class="kpi"><div class="kpi-num" style="color:{pnl_color}">{trade_stats['total_pnl_pct']:+.2f}%</div><div class="kpi-label">通算 P&L</div></div>
</div>
<p>🥇 ベスト取引: {best_html}　／　🥶 ワースト取引: {worst_html}</p>

<h2>💯 信頼度スコア別 勝率</h2>
<table>
  <thead><tr><th>信頼度</th><th style="text-align:right">確定数</th><th style="text-align:right">勝ち</th><th style="text-align:right">SL</th><th style="text-align:right">勝率</th></tr></thead>
  <tbody>{conf_html}</tbody>
</table>

<h2>🛡️ 環境警戒スコア別 勝率</h2>
<table>
  <thead><tr><th>スコア</th><th style="text-align:right">確定数</th><th style="text-align:right">勝ち</th><th style="text-align:right">SL</th><th style="text-align:right">勝率</th></tr></thead>
  <tbody>{env_html}</tbody>
</table>

<h2>🏷️ 銘柄別 成績ランキング</h2>
<table>
  <thead><tr><th>銘柄</th><th style="text-align:right">確定数</th><th style="text-align:right">勝ち</th><th style="text-align:right">SL</th><th style="text-align:right">勝率</th></tr></thead>
  <tbody>{ticker_html}</tbody>
</table>

<h2>📝 AI 総評</h2>
{summary_html}

<div class="info-box">
本レポートは <a href="track-record.html">📊 シグナル成績ダッシュボード</a> と同じデータソース（signals-log.json + my-trades.json）から月次集計したものです。詳細な日別・時間帯別分析はダッシュボード側でご確認ください。
</div>

<div class="warning-box">
本記事は月初 1 日朝に自動生成される月次レポートです。集計値は機械的に算出したもので、SL/TP は ATR ベース機械算出値です。投資判断は自己責任で行ってください。
</div>

</article>
</main>
<footer>© 2026 MarketWatch AI ｜ <a href="index.html">トップに戻る</a><p data-disclaimer="kinsho-v1" style="margin-top:10px;padding-top:10px;border-top:1px dashed #d0d7de;font-size:.78rem;color:#6e7781;line-height:1.6">⚠️ <b>当サイトは金融商品取引業者ではなく、投資助言・代理業の登録もしていません。</b> 本サイトの情報は投資助言ではなく、投資判断はご自身の責任で行ってください。</p>
</footer>
<script src="site-search.js" defer></script>
</body>
</html>
"""


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    now_jst = datetime.now(JST)
    today = now_jst.date()
    force = "--force" in sys.argv or os.environ.get("FORCE_MONTHLY_REPORT", "").lower() in ("1", "true", "yes")

    print(f"📊 マンスリー成績レポート 自動生成 ({today})")

    # 月初 1〜3 日のみ実行（GitHub Actions の遅延考慮）
    if not force and today.day > 3:
        print(f"  - 今日は {today.day} 日、スキップ（月初 1〜3 日のみ実行 / --force で強制実行）")
        return

    # 「先月」を算出（today が 6/1 なら 5/1 〜 5/31）
    if today.month == 1:
        target_year, target_month = today.year - 1, 12
    else:
        target_year, target_month = today.year, today.month - 1
    month_start, month_end = month_range(target_year, target_month)
    print(f"  📆 対象月: {target_year}-{target_month:02d}")

    filename = f"guide-monthly-report-{target_year}-{target_month:02d}.html"
    filepath = os.path.join(script_dir, filename)

    if os.path.exists(filepath) and not force:
        print(f"  ⏭️  {filename}: 既存、スキップ（上書きは --force）")
        return

    signals = load_json(SIGNALS_LOG_FILE, [])
    trades = load_json(TRADES_FILE, [])

    sig_stats = summarize_signals(signals, month_start, month_end)
    trade_stats = summarize_trades(trades, month_start, month_end)
    print(f"  📊 シグナル {sig_stats['total']} / 確定 {sig_stats['closed']} / 勝率 {sig_stats['win_rate']}% / 実取引 {trade_stats['closed']} / P&L {trade_stats['total_pnl_pct']}%")

    api_key = os.environ.get("GEMINI_API_KEY", "")
    summary_text = ai_summary(target_year, target_month, sig_stats, trade_stats, api_key)

    html = render_html(target_year, target_month, today, sig_stats, trade_stats, summary_text)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  ✅ {filename}: 生成完了 ({os.path.getsize(filepath) / 1024:.1f} KB)")

    # GitHub にアップロード（ローカル実行時のみ）
    if os.environ.get("GITHUB_ACTIONS_RUN") == "true":
        print("  ⏭️  GitHub Actions 実行中、API アップロードはスキップ（git push step で同期）")
        return
    try:
        from auto_indicator_preview import _load_gh_config, upload_to_github
        gh_cfg = _load_gh_config(script_dir)
        if gh_cfg is not None:
            upload_to_github(filepath, gh_cfg, repo_path=filename)
    except ImportError:
        print("  ⚠️  auto_indicator_preview.py 未取得、アップロードスキップ")


if __name__ == "__main__":
    main()
