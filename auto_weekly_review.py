# -*- coding: utf-8 -*-
"""
週次振り返り記事 自動下書きスクリプト (C1)
=====================================================
毎週月曜朝（07:00 JST）に「先週のシグナル全件 × 結果 × 学び」を集計し、
guide-weekly-review-YYYY-MM-DD.html として配置する。

データソース:
- signals-log.json: 過去 7 日のシグナル発火履歴
- my-trades.json:   過去 7 日のユーザー実取引
- economic-events.json: 来週の重要指標

使い方:
    python auto_weekly_review.py            # 月曜のみ実行
    python auto_weekly_review.py --force    # 曜日関係なく強制実行

GitHub Actions schedule: 22:00 UTC 日曜 = 07:00 JST 月曜
"""
import os
import sys
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))
SIGNALS_LOG_FILE = "signals-log.json"
TRADES_FILE = "my-trades.json"
EVENTS_FILE = "economic-events.json"
TRACKER_FILE = "signal-lab-tracker.json"  # エッジ番付の元データ（Actions実行時はrepo内に存在）

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


def is_weekend_closed_fire(sig):
    """週末閉場中（土07:00〜月06:00 JST）に発火したシグナルか（BTC=24h市場は対象外）。
    塩漬けデータ発火＝測定アーティファクトのため勝率集計から除外（2026-07-11 オーナー指示）。
    ※generate_track_record_page.py と同一定義（定義を変える時は3か所同時に）"""
    if "BTC" in (sig.get("ticker") or ""):
        return False
    try:
        t = datetime.fromisoformat(sig.get("fired_at", ""))
    except (ValueError, TypeError):
        return False
    wd, hr = t.weekday(), t.hour
    return (wd == 5 and hr >= 7) or wd == 6 or (wd == 0 and hr < 6)


def _parse_iso(s):
    try:
        return datetime.fromisoformat(s) if s else None
    except Exception:
        return None


def summarize_signals(signals, week_start, week_end):
    """過去 1 週間のシグナルを集計"""
    in_week = []
    for s in signals:
        dt = _parse_iso(s.get("fired_at"))
        if dt and week_start <= dt < week_end:
            in_week.append(s)

    by_tf = defaultdict(list)
    for s in in_week:
        by_tf[s.get("timeframe", "?")].append(s)

    closed = [s for s in in_week if s.get("outcome") in ("tp1", "tp2", "sl", "expired")]
    tp1 = sum(1 for s in closed if s.get("outcome") == "tp1")
    tp2 = sum(1 for s in closed if s.get("outcome") == "tp2")
    sl = sum(1 for s in closed if s.get("outcome") == "sl")
    wins = tp1 + tp2
    win_rate = wins / len(closed) * 100 if closed else 0

    # 信頼度別
    by_conf = defaultdict(lambda: {"total": 0, "wins": 0, "sl": 0})
    for s in closed:
        label = (s.get("confidence") or {}).get("label") or "—"
        by_conf[label]["total"] += 1
        if s.get("outcome") in ("tp1", "tp2"):
            by_conf[label]["wins"] += 1
        if s.get("outcome") == "sl":
            by_conf[label]["sl"] += 1

    # 銘柄ベスト/ワースト
    by_ticker = defaultdict(lambda: {"wins": 0, "sl": 0, "name": ""})
    for s in closed:
        tk = s.get("ticker", "?")
        by_ticker[tk]["name"] = s.get("asset_name", tk)
        if s.get("outcome") in ("tp1", "tp2"):
            by_ticker[tk]["wins"] += 1
        elif s.get("outcome") == "sl":
            by_ticker[tk]["sl"] += 1

    return {
        "total": len(in_week),
        "by_tf": {k: len(v) for k, v in by_tf.items()},
        "closed": len(closed),
        "tp1": tp1, "tp2": tp2, "sl": sl,
        "win_rate": round(win_rate, 1),
        "by_conf": dict(by_conf),
        "by_ticker": dict(by_ticker),
        "signals_in_week": in_week,
    }


def summarize_trades(trades, week_start, week_end):
    """過去 1 週間の実取引を集計"""
    in_week = []
    for t in trades:
        # entry_at か exit_at どちらかが週内ならカウント
        e_dt = _parse_iso(t.get("entry_at"))
        x_dt = _parse_iso(t.get("exit_at"))
        if (e_dt and week_start <= e_dt < week_end) or \
           (x_dt and week_start <= x_dt < week_end):
            in_week.append(t)

    closed = [t for t in in_week if t.get("status") == "closed"]
    wins = sum(1 for t in closed if (t.get("pnl_pct") or 0) > 0)
    losses = sum(1 for t in closed if (t.get("pnl_pct") or 0) < 0)
    total_pnl_pct = sum((t.get("pnl_pct") or 0) for t in closed)

    return {
        "total": len(in_week),
        "closed": len(closed),
        "wins": wins,
        "losses": losses,
        "win_rate": round(wins / len(closed) * 100, 1) if closed else 0,
        "total_pnl_pct": round(total_pnl_pct, 2),
        "trades_in_week": closed,
    }


def summarize_banzuke(tracker, week_start, week_end):
    """エッジ番付（signal-lab-tracker.json）の現況と直近1週間の昇進・降格を集計。
    昇降の判定はトラッカーの promoted_at / demoted_at（事前宣言ルールの自動執行）を読むだけで、
    ここでは一切再判定しない。tracker が無い/壊れている場合は None（節ごと非表示）。"""
    hyps = (tracker or {}).get("hypotheses") or []
    if not hyps:
        return None
    ws, we = week_start.date(), week_end.date()

    def _in_week(d):
        try:
            dd = datetime.fromisoformat(d).date() if d else None
        except (ValueError, TypeError):
            return False
        return dd is not None and ws <= dd < we

    makuuchi = [h for h in hyps if h.get("status") == "promoted"]
    juryo = [h for h in hyps if h.get("status") == "tracking" and h.get("holdout_pass")]
    ups = [h for h in hyps if _in_week(h.get("promoted_at"))]
    downs = [h for h in hyps if _in_week(h.get("demoted_at"))]
    return {"n_makuuchi": len(makuuchi), "n_juryo": len(juryo), "n_total": len(hyps),
            "ups": ups, "downs": downs}


def render_banzuke_section(banzuke):
    """「🏆 エッジ番付の変動」節の HTML（banzuke が None なら空文字＝節ごと省略）"""
    if banzuke is None:
        return ""

    def _row(mark, h, date_key):
        kind = "🛡回避ゲート" if h.get("kind") == "gate" else "⚔️エッジ"
        fwd = h.get("forward") or {}
        n = fwd.get("n", "—")
        label = h.get("label") or h.get("id", "?")
        return (f'<tr><td>{mark}</td><td><b>{label}</b></td><td>{kind}</td>'
                f'<td style="white-space:nowrap">{h.get(date_key, "")}</td>'
                f'<td style="text-align:right">{n}</td></tr>')

    rows = [_row("⬆️ 昇進", h, "promoted_at") for h in banzuke["ups"]]
    rows += [_row("⬇️ 降格", h, "demoted_at") for h in banzuke["downs"]]
    if rows:
        table = ('<table><thead><tr><th>変動</th><th>仮説</th><th>型</th><th>判定日</th>'
                 '<th style="text-align:right">前向きN</th></tr></thead>'
                 f'<tbody>{"".join(rows)}</tbody></table>')
    else:
        table = '<p>先週は番付の昇進・降格はありませんでした。</p>'
    return f"""
<h2>🏆 エッジ番付の変動</h2>
<p>検証中の仮説を力士に見立てた公開リーグ「エッジ番付」の先週の動きです。昇進・降格は事前に宣言した統計ルール
（前向き成績の信頼区間チェック）による自動判定で、人間の裁量は入りません。現在の番付は
<a href="track-record.html">📊 シグナル成績</a> の「🏆 エッジ番付」タブで確認できます。</p>
{table}
<div class="info-box">現在の勢力図：幕内（昇格中）{banzuke['n_makuuchi']} 本 ／ 十両（昇格候補）{banzuke['n_juryo']} 本 ／ 全 {banzuke['n_total']} 仮説を追跡中</div>
<p style="font-size:.78rem;color:#6e7781;margin-top:6px;line-height:1.6">⚠️ 番付は過去データの検証結果を整理したものであり、将来の成績を保証するものではありません。特定の売買を推奨するものでもありません。</p>
"""


def next_week_events(events_data, week_end):
    """来週（週末から 7 日）の重要指標を抽出"""
    end = week_end + timedelta(days=7)
    upcoming = []
    for ev in (events_data.get("events") or []):
        dt = _parse_iso(ev.get("datetime"))
        if dt and week_end <= dt < end:
            upcoming.append((dt, ev))
    upcoming.sort(key=lambda x: x[0])
    return upcoming


def ai_lessons(sig_stats, trade_stats, api_key):
    """Gemini で「先週の学び」セクションを生成。失敗時はテンプレ。"""
    if not api_key:
        return _fallback_lessons(sig_stats, trade_stats)
    try:
        import google.generativeai as genai
    except ImportError:
        return _fallback_lessons(sig_stats, trade_stats)
    genai.configure(api_key=api_key)

    # 主要シグナル種別をリストアップ
    sig_types = defaultdict(int)
    for s in sig_stats["signals_in_week"]:
        for t in (s.get("signal_types") or []):
            sig_types[t] += 1

    # 信頼度ごとの勝率を算出して提示（仮説検証の核）
    conf_winrates = {}
    for label, d in sig_stats["by_conf"].items():
        wr = (d["wins"] / d["total"] * 100) if d["total"] else 0
        conf_winrates[label] = f"{d['wins']}/{d['total']} ({wr:.0f}%)"

    # 銘柄ベスト・ワースト
    by_t = sig_stats.get("by_ticker", {})
    top_winner = max(by_t.items(), key=lambda x: x[1]["wins"] - x[1]["sl"], default=(None, None))
    top_loser = min(by_t.items(), key=lambda x: x[1]["wins"] - x[1]["sl"], default=(None, None))

    prompt = f"""あなたは日本人個人投資家（サラリーマン × 4H スイング × MT4）向けの投資メディアの編集者です。
過去 1 週間の AI シグナル成績と実取引データを読み取り、「振り返り記事の核心セクション」を執筆してください。

【シグナル統計】
- 発火数: {sig_stats['total']} 件（4H {sig_stats['by_tf'].get('4h', 0)} / 1H {sig_stats['by_tf'].get('1h', 0)}）
- 確定: {sig_stats['closed']} 件（TP1 {sig_stats['tp1']} / TP2 {sig_stats['tp2']} / SL {sig_stats['sl']}）
- 勝率: {sig_stats['win_rate']}%
- 信頼度別 勝率: {conf_winrates}
- 主要シグナル種別: {dict(sig_types)}
- ベスト銘柄: {top_winner[0] if top_winner[0] else "なし"} (勝-負 = {(top_winner[1] or {{}}).get("wins", 0) - (top_winner[1] or {{}}).get("sl", 0) if top_winner[1] else 0})
- ワースト銘柄: {top_loser[0] if top_loser[0] else "なし"} (勝-負 = {(top_loser[1] or {{}}).get("wins", 0) - (top_loser[1] or {{}}).get("sl", 0) if top_loser[1] else 0})

【実取引】
- 取引数: {trade_stats['closed']} 件 / 勝率: {trade_stats['win_rate']}% / 通算 P&L: {trade_stats['total_pnl_pct']}%

【執筆要件】（必ず守ること）
- 「先週の総評」を 1 段落 (200 字程度): 数値を必ず引用、感想ではなく事実に基づく分析。例「勝率 65% は前週から +5pt 改善、これは HIGH スコアシグナルが 3/3 で TP1 到達したことが寄与」
- 「教訓・改善ポイント」を箇条書き 3 項目: 各項目はデータに基づく具体的なアクション提案。例「・反転検知ありシグナルは全て SL → 来週は完全に見送る」
- 「来週の注意点」を箇条書き 2 項目: 来週の取引判断に直接使える内容

【避けること】
- 抽象的・曖昧な表現（「市場は難しい」など）
- 投資助言（「○○を買え」など。「○○を検討してもよい」までに留める）
- HTML タグ、Markdown 見出し（# など）は使わない

出力はプレーンテキストのみで、3 セクション構成。
"""
    # 週次振り返りは月 4 回のみで重要なので、品質優先で上位モデルから試行
    for model_name in ("gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.5-flash-lite"):
        try:
            model = genai.GenerativeModel(model_name)
            resp = model.generate_content(prompt)
            text = (resp.text or "").strip()
            if text:
                return text
        except Exception:
            continue
    return _fallback_lessons(sig_stats, trade_stats)


def _fallback_lessons(sig_stats, trade_stats):
    """Gemini 失敗時のテンプレ"""
    if sig_stats["closed"] == 0:
        return "今週はまだ確定したシグナルが少なく、振り返り集計には十分なデータがありません。来週以降の蓄積に期待します。"
    win_msg = "良好" if sig_stats["win_rate"] >= 60 else "改善余地あり" if sig_stats["win_rate"] >= 45 else "厳しい結果"
    return f"""先週のシグナル勝率は {sig_stats['win_rate']}% と{win_msg}でした。
確定数 {sig_stats['closed']} 件のうち、TP1 到達が {sig_stats['tp1']} 件、SL ヒットが {sig_stats['sl']} 件。
信頼度スコア HIGH のシグナルがどれだけ勝てているか、引き続き観察していきます。"""


def render_html(today, week_start, week_end, sig_stats, trade_stats, events, lessons_text, banzuke=None):
    """振り返り記事 HTML を組み立て"""
    week_start_str = week_start.strftime("%Y-%m-%d")
    week_end_str = (week_end - timedelta(days=1)).strftime("%Y-%m-%d")
    today_jp = today.strftime("%Y年%m月%d日")

    # 信頼度テーブル
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

    # 銘柄テーブル
    ticker_rows = []
    items = sorted(sig_stats["by_ticker"].items(), key=lambda x: -(x[1]["wins"] - x[1]["sl"]))
    for tk, d in items[:8]:
        net = d["wins"] - d["sl"]
        ticker_rows.append(f'<tr><td><b>{d["name"]}</b> <span style="color:#6e7781">{tk}</span></td>'
                           f'<td style="text-align:right;color:#1a7f37">{d["wins"]}</td>'
                           f'<td style="text-align:right;color:#cf222e">{d["sl"]}</td>'
                           f'<td style="text-align:right;font-weight:700">{net:+d}</td></tr>')
    ticker_html = "\n".join(ticker_rows) or '<tr><td colspan="4" style="text-align:center;color:#6e7781">確定シグナルなし</td></tr>'

    # 取引テーブル
    trade_rows = []
    for t in trade_stats["trades_in_week"]:
        pnl = t.get("pnl_pct") or 0
        color = "#1a7f37" if pnl > 0 else "#cf222e"
        trade_rows.append(f'<tr><td>{(t.get("entry_at","")[:10])}</td>'
                          f'<td><b>{t.get("symbol","")}</b></td>'
                          f'<td>{t.get("direction","")[:1]}</td>'
                          f'<td style="text-align:right;color:{color};font-weight:700">{pnl:+.2f}%</td></tr>')
    trade_html = "\n".join(trade_rows) or '<tr><td colspan="4" style="text-align:center;color:#6e7781">今週は記録された実取引なし</td></tr>'

    # 来週イベント
    event_rows = []
    for dt, ev in events[:12]:
        emoji = "🔴" if ev.get("impact") == "critical" else "🟠"
        event_rows.append(f'<tr><td style="white-space:nowrap">{dt.strftime("%m/%d %H:%M")}</td>'
                          f'<td>{emoji}</td><td>{ev.get("name","")}</td>'
                          f'<td style="color:#6e7781">{ev.get("country","")}</td></tr>')
    event_html = "\n".join(event_rows) or '<tr><td colspan="4" style="text-align:center;color:#6e7781">来週の重要指標は登録なし</td></tr>'

    # 学びテキストを <p> に分割
    lessons_html_parts = []
    for para in lessons_text.split("\n\n"):
        para = para.strip()
        if not para:
            continue
        # 箇条書きは <ul>
        if any(line.lstrip().startswith(("・", "-", "*")) for line in para.splitlines()):
            items = [line.lstrip("・-* ").strip() for line in para.splitlines() if line.strip()]
            lessons_html_parts.append("<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>")
        else:
            lessons_html_parts.append(f"<p>{para}</p>")
    lessons_html = "\n".join(lessons_html_parts)

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="icon" type="image/svg+xml" href="favicon.svg">
  <link rel="icon" type="image/png" sizes="32x32" href="favicon-32.png">
  <link rel="apple-touch-icon" href="apple-touch-icon.png">
<meta name="robots" content="noindex,follow"><!-- 自動生成の週次振り返り：薄ページのためインデックス除外（AdSense低価値対策） -->
<title>📅 週次振り返り（{week_start_str}〜{week_end_str}）｜ MarketWatch AI</title>
<meta name="description" content="先週のシグナル全件・結果・教訓を自動集計。AI トレードの透明性を追求する週次レポート。">
<link rel="canonical" href="https://marketwatch-jp.com/guide-weekly-review-{week_start_str}.html">
<meta property="og:type" content="article">
<meta property="og:title" content="📅 週次振り返り（{week_start_str}〜{week_end_str}）｜ MarketWatch AI">
<meta property="og:description" content="先週のシグナル全件・結果・教訓を自動集計。AI トレードの透明性を追求する週次レポート。">
<meta property="og:url" content="https://marketwatch-jp.com/guide-weekly-review-{week_start_str}.html">
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
.kpi-num.win{{color:#1a7f37}}
.kpi-num.loss{{color:#cf222e}}
.kpi-label{{font-size:.78rem;color:#57606a;margin-top:6px}}
table{{width:100%;border-collapse:collapse;font-size:.9rem;background:#fff;border:1px solid #d0d7de;border-radius:8px;overflow:hidden;margin:14px 0}}
th{{background:#f6f8fa;padding:10px 12px;text-align:left;border-bottom:2px solid #d0d7de;font-size:.82rem;color:#424a53}}
td{{padding:9px 12px;border-bottom:1px solid #eaeef2}}
tr:last-child td{{border-bottom:none}}
.info-box{{background:#ddf4ff;border-left:4px solid #0969da;border-radius:6px;padding:14px 18px;margin:16px 0;font-size:.92rem;color:#1f6feb}}
.warning-box{{background:#fff8c5;border-left:4px solid #9a6700;border-radius:6px;padding:14px 18px;margin:16px 0;font-size:.92rem;color:#9a6700}}
footer{{background:#f6f8fa;border-top:1px solid #d0d7de;padding:20px 32px;text-align:center;font-size:.78rem;color:#6e7781;margin-top:40px}}
footer a{{color:#0969da;text-decoration:none}}
@media(max-width:600px){{.article{{padding:24px 20px}}h1{{font-size:1.35rem}}.nav-bar{{display:grid;grid-template-columns:1fr 1fr}}.nav-btn{{min-width:0;width:100%}}}}
</style>
</head>
<body>
<header><div class="header-inner"><div class="header-title"><svg viewBox="0 0 96 96" style="width:27px;height:27px;vertical-align:-4px;margin-right:2px" aria-hidden="true"><rect x="2" y="2" width="92" height="92" rx="21" fill="#0969da"/><polyline points="16,72 34,50 50,58 70,32" fill="none" stroke="#ffffff" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/><circle cx="74" cy="27" r="10.5" fill="#d92b2b" stroke="#ffffff" stroke-width="4"/></svg> MarketWatch AI</div><div class="header-meta">日本人投資家のためのマーケット情報サイト</div><div style="margin-top:11px;padding-top:11px;border-top:1px solid rgba(128,128,128,.22)"><div style="font-size:1.3rem;font-weight:700;color:#0969da">📚 解説記事</div></div></div></header>
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
<div class="breadcrumb"><a href="index.html">ホーム</a> ＞ <a href="guides.html">解説記事</a> ＞ 週次振り返り {week_start_str}〜{week_end_str}</div>

<article class="article">
<h1>📅 週次振り返り（{week_start_str}〜{week_end_str}）：先週のシグナル全件と教訓</h1>
<div class="meta-line">公開日：{today_jp}（月曜朝 自動更新）／ カテゴリ：週次レポート（自動生成）</div>

<h2>📊 先週の AI シグナル サマリ</h2>
<div class="kpi-grid">
  <div class="kpi"><div class="kpi-num">{sig_stats['total']}</div><div class="kpi-label">シグナル発火 (4H {sig_stats['by_tf'].get('4h', 0)} / 1H {sig_stats['by_tf'].get('1h', 0)})</div></div>
  <div class="kpi"><div class="kpi-num">{sig_stats['closed']}</div><div class="kpi-label">確定済み</div></div>
  <div class="kpi"><div class="kpi-num win">{sig_stats['tp1'] + sig_stats['tp2']}</div><div class="kpi-label">勝ち (TP1+TP2)</div></div>
  <div class="kpi"><div class="kpi-num loss">{sig_stats['sl']}</div><div class="kpi-label">負け (SL)</div></div>
  <div class="kpi"><div class="kpi-num {'win' if sig_stats['win_rate'] >= 50 else 'loss'}">{sig_stats['win_rate']:.1f}%</div><div class="kpi-label">勝率</div></div>
</div>
<p style="font-size:.78rem;color:#6e7781;margin-top:6px;line-height:1.6">⚠️ 上記の勝率は過去 1 週間の機械的なシグナル集計結果であり、将来の取引成績を保証するものではありません。市場閉場中（土07:00〜月06:00 JST・暗号資産を除く）に発火した記録は古いレートに基づくため集計対象外です。本ページは情報提供を目的としており、投資助言ではありません。当サイトは金融商品取引業者ではなく、投資助言・代理業の登録もしていません。</p>

<h2>💯 信頼度別 勝率</h2>
<p>シグナル発火時の「信頼度スコア」（複数シグナル × 環境 × トレンド整合）別の的中率を集計。理想は HIGH > MID > LOW の順序。</p>
<table>
  <thead><tr><th>信頼度</th><th style="text-align:right">確定数</th><th style="text-align:right">勝ち</th><th style="text-align:right">SL</th><th style="text-align:right">勝率</th></tr></thead>
  <tbody>{conf_html}</tbody>
</table>

<h2>🏷️ 銘柄ベスト・ワースト</h2>
<table>
  <thead><tr><th>銘柄</th><th style="text-align:right">勝ち</th><th style="text-align:right">SL</th><th style="text-align:right">差し引き</th></tr></thead>
  <tbody>{ticker_html}</tbody>
</table>
{render_banzuke_section(banzuke)}

<h2>💼 先週の実取引</h2>
<table>
  <thead><tr><th>日付</th><th>銘柄</th><th>方向</th><th style="text-align:right">P&L</th></tr></thead>
  <tbody>{trade_html}</tbody>
</table>
<div class="info-box">確定 {trade_stats['closed']} 件 / 勝率 {trade_stats['win_rate']}% / 通算 {trade_stats['total_pnl_pct']:+.2f}%</div>
<p style="font-size:.78rem;color:#6e7781;margin-top:6px;line-height:1.6">⚠️ 確定数が少ない場合、勝率の統計的信頼性は限定的です。過去の結果は将来の取引成績を保証しません。本ページは情報提供を目的としており、投資助言ではありません。当サイトは金融商品取引業者ではなく、投資助言・代理業の登録もしていません。</p>

<h2>💡 先週の総評と教訓</h2>
{lessons_html}

<h2>📅 来週の注目スケジュール</h2>
<table>
  <thead><tr><th>日時</th><th>重要度</th><th>イベント</th><th>国</th></tr></thead>
  <tbody>{event_html}</tbody>
</table>

<div class="warning-box">
本記事は月曜朝に自動生成された週次レポートです。シグナル統計は signals-log.json と my-trades.json を機械的に集計したもので、実際の投資判断は <a href="track-record.html">📊 シグナル成績ダッシュボード</a> も合わせてご確認ください。投資は自己責任で。
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
    force = "--force" in sys.argv or os.environ.get("FORCE_WEEKLY_REVIEW", "").lower() in ("1", "true", "yes")

    print(f"📅 週次振り返り 自動生成 ({today} {now_jst.strftime('%a')})")

    # 月曜のみ実行（weekday=0）。--force で曜日無視
    if not force and today.weekday() != 0:
        print(f"  - 今日は{['月','火','水','木','金','土','日'][today.weekday()]}曜日、スキップ（月曜のみ実行）")
        return

    # 「先週」= 直近の月曜 00:00 から日曜 24:00（≒ 月曜 00:00）まで
    last_monday = datetime.combine(today - timedelta(days=7), datetime.min.time()).replace(tzinfo=JST)
    this_monday = last_monday + timedelta(days=7)
    print(f"  📆 振り返り対象: {last_monday.date()} 〜 {(this_monday - timedelta(days=1)).date()}")

    filename = f"guide-weekly-review-{last_monday.strftime('%Y-%m-%d')}.html"
    filepath = os.path.join(script_dir, filename)

    if os.path.exists(filepath) and not force:
        print(f"  ⏭️  {filename}: 既存、スキップ（上書きは --force）")
        return

    signals = load_json(SIGNALS_LOG_FILE, [])
    trades = load_json(TRADES_FILE, [])
    events_data = load_json(EVENTS_FILE, {"events": []})
    n_all = len(signals)
    signals = [s for s in signals if not is_weekend_closed_fire(s)]
    print(f"  📒 signals: {len(signals)}（週末閉場中 {n_all - len(signals)} 件除外） / trades: {len(trades)} / events: {len(events_data.get('events') or [])}")

    sig_stats = summarize_signals(signals, last_monday, this_monday)
    trade_stats = summarize_trades(trades, last_monday, this_monday)
    events = next_week_events(events_data, this_monday)
    banzuke = summarize_banzuke(load_json(TRACKER_FILE, {}), last_monday, this_monday)
    print(f"  📊 先週シグナル {sig_stats['total']} / 確定 {sig_stats['closed']} / 勝率 {sig_stats['win_rate']}%"
          + (f" / 番付 幕内{banzuke['n_makuuchi']}・昇降 {len(banzuke['ups'])+len(banzuke['downs'])}件" if banzuke else " / 番付データなし"))

    api_key = os.environ.get("GEMINI_API_KEY", "")
    lessons_text = ai_lessons(sig_stats, trade_stats, api_key)

    html = render_html(today, last_monday, this_monday, sig_stats, trade_stats, events, lessons_text, banzuke)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  ✅ {filename}: 生成完了 ({os.path.getsize(filepath) / 1024:.1f} KB)")

    # GitHub にアップロード（ローカル実行時のみ。Actions 実行時は git push に委譲）
    if os.environ.get("GITHUB_ACTIONS_RUN") == "true":
        print("  ⏭️  GitHub Actions 実行中、API アップロードはスキップ（git push step で同期）")
        return
    try:
        from auto_indicator_preview import _load_gh_config, upload_to_github
        gh_cfg = _load_gh_config(script_dir)
        if gh_cfg is not None:
            upload_to_github(filepath, gh_cfg, repo_path=filename)
        else:
            print("  ⚠️  market-news-config.json 未配置、GitHub アップロードはスキップ（sync_to_github.py 経由で同期可）")
    except ImportError:
        print("  ⚠️  auto_indicator_preview.py のヘルパー未取得、アップロードスキップ")


if __name__ == "__main__":
    main()
