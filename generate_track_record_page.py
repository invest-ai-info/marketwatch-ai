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

# 曜日マッピング
WEEKDAY_JP = ["月", "火", "水", "木", "金", "土", "日"]


def get_time_session(hour):
    """JST 時刻 → 市場セッション"""
    if 0 <= hour < 6:
        return "深夜 (0-6)"
    elif 6 <= hour < 9:
        return "早朝 (6-9)"
    elif 9 <= hour < 15:
        return "東京 (9-15)"
    elif 15 <= hour < 17:
        return "欧州オープン (15-17)"
    elif 17 <= hour < 22:
        return "欧州 (17-22)"
    else:
        return "NY (22-24)"


SESSION_ORDER = ["深夜 (0-6)", "早朝 (6-9)", "東京 (9-15)", "欧州オープン (15-17)", "欧州 (17-22)", "NY (22-24)"]

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


def _fmt_num(v, decimals=2, suffix=""):
    """None を "—" にフォールバックする数値フォーマッタ"""
    if v is None:
        return "—"
    try:
        return f"{v:.{decimals}f}{suffix}"
    except (ValueError, TypeError):
        return "—"


def _fmt_pct(v, decimals=2):
    """符号付き % フォーマッタ。None は "—" """
    if v is None:
        return "—"
    try:
        return f"{v:+.{decimals}f}%"
    except (ValueError, TypeError):
        return "—"


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
        dir_color = "#1a7f37" if direction_short == "L" else "#cf222e" if direction_short == "S" else "#6e7781"

        rows.append(f"""
        <tr>
          <td style="white-space:nowrap">{fired}</td>
          <td><b>{ticker}</b></td>
          <td style="font-size:.82rem">{signal_label}</td>
          <td style="text-align:center;font-weight:700;color:{dir_color}">{direction_short}</td>
          <td style="text-align:right">{_fmt_num(e.get("entry"))}</td>
          <td style="text-align:right;color:#cf222e">{_fmt_num(e.get("stop_loss"))}</td>
          <td style="text-align:right;color:#1a7f37">{_fmt_num(e.get("take_profit_1"))}</td>
          <td style="text-align:right">{_fmt_pct(e.get("max_favorable_excursion_pct"))}</td>
          <td style="text-align:right">{_fmt_pct(e.get("max_adverse_excursion_pct"))}</td>
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


def build_dashboard_section(signals, tab_id, tab_label, chart_canvas_id):
    """timeframe ごとに同じ構造のダッシュボードセクションを生成"""
    overall = calc_stats(signals)
    by_signal = group_stats(signals, lambda e: e.get("primary_signal"))
    by_ticker = group_stats(signals, lambda e: e.get("ticker"))
    by_direction = group_stats(signals, lambda e: e.get("direction"))

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
        render_stat_row(k, v) for k, v in _filtered_sorted(by_ticker)
    ) or '<tr><td colspan="7" style="text-align:center;color:#6e7781;padding:16px">データ蓄積中</td></tr>'
    direction_rows = "\n".join(
        render_stat_row(k, v) for k, v in _filtered_sorted(by_direction)
    ) or '<tr><td colspan="7" style="text-align:center;color:#6e7781;padding:16px">データ蓄積中</td></tr>'
    recent_rows = render_recent_table(signals, limit=30)

    pending_count = sum(1 for e in signals if not e.get("outcome"))
    win_color = "#1a7f37" if overall["win_rate"] >= 60 else "#9a6700" if overall["win_rate"] >= 45 else "#cf222e"
    er_color = "#1a7f37" if overall["expected_R"] > 0.3 else "#9a6700" if overall["expected_R"] > 0 else "#cf222e"

    return f"""
<div class="tab-pane" id="pane-{tab_id}">
  <h2>📈 全体パフォーマンス（{tab_label}）</h2>
  <div class="kpi-grid">
    <div class="kpi-card">
      <div class="kpi-label">確定シグナル総数</div>
      <div class="kpi-value">{overall['total']}</div>
      <div class="kpi-sub">うち未確定 {pending_count} 件</div>
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
  <div class="chart-box"><canvas id="{chart_canvas_id}"></canvas></div>

  <h2>🎯 シグナル種別ブレイクダウン</h2>
  <div class="scroll-x"><table>
    <thead><tr><th>シグナル</th><th style="text-align:right">確定数</th><th style="text-align:right">勝率</th>
      <th style="text-align:right">TP1率</th><th style="text-align:right">TP2率</th>
      <th style="text-align:right">SL</th><th style="text-align:right">期待 R</th></tr></thead>
    <tbody>{signal_rows}</tbody>
  </table></div>

  <h2 style="margin-top:24px">🏷️ 銘柄ブレイクダウン</h2>
  <div class="scroll-x"><table>
    <thead><tr><th>銘柄</th><th style="text-align:right">確定数</th><th style="text-align:right">勝率</th>
      <th style="text-align:right">TP1率</th><th style="text-align:right">TP2率</th>
      <th style="text-align:right">SL</th><th style="text-align:right">期待 R</th></tr></thead>
    <tbody>{ticker_rows}</tbody>
  </table></div>

  <h2 style="margin-top:24px">📐 方向別ブレイクダウン</h2>
  <div class="scroll-x"><table>
    <thead><tr><th>方向</th><th style="text-align:right">確定数</th><th style="text-align:right">勝率</th>
      <th style="text-align:right">TP1率</th><th style="text-align:right">TP2率</th>
      <th style="text-align:right">SL</th><th style="text-align:right">期待 R</th></tr></thead>
    <tbody>{direction_rows}</tbody>
  </table></div>

  <h2 style="margin-top:24px">📒 直近 30 件のシグナル詳細</h2>
  <div class="scroll-x"><table style="font-size:.82rem">
    <thead><tr>
      <th>発火時刻</th><th>銘柄</th><th>シグナル</th><th>L/S</th>
      <th style="text-align:right">エントリー</th><th style="text-align:right">SL</th><th style="text-align:right">TP1</th>
      <th style="text-align:right">MFE</th><th style="text-align:right">MAE</th><th>結果</th>
    </tr></thead>
    <tbody>{recent_rows or '<tr><td colspan="10" style="text-align:center;color:#6e7781;padding:16px">シグナル蓄積中</td></tr>'}</tbody>
  </table></div>
</div>"""


def _parse_iso(s):
    try:
        return datetime.fromisoformat(s) if s else None
    except Exception:
        return None


def build_analytics_section(signals):
    """曜日別 / 時間帯別 / 月別 / セッション別の勝率分析タブ"""

    def _by_key(signals, key_fn):
        """key_fn(entry) でグルーピング → 各グループで勝率計算"""
        groups = defaultdict(list)
        for e in signals:
            if e.get("outcome") not in ("tp1", "tp2", "sl", "expired"):
                continue
            dt = _parse_iso(e.get("fired_at"))
            if dt is None:
                continue
            k = key_fn(e, dt)
            if k is not None:
                groups[k].append(e)
        return {k: calc_stats(v) for k, v in groups.items()}

    by_weekday = _by_key(signals, lambda e, dt: WEEKDAY_JP[dt.weekday()])
    by_session = _by_key(signals, lambda e, dt: get_time_session(dt.hour))
    by_month = _by_key(signals, lambda e, dt: f"{dt.year}-{dt.month:02d}")
    by_hour = _by_key(signals, lambda e, dt: dt.hour)

    # 曜日テーブル（月→日の固定順）
    weekday_rows = []
    for day in WEEKDAY_JP:
        stats = by_weekday.get(day)
        if stats and stats["total"] > 0:
            weekday_rows.append(render_stat_row(day + "曜", stats))
    weekday_html = "\n".join(weekday_rows) or '<tr><td colspan="7" style="text-align:center;color:#6e7781;padding:16px">データ蓄積中</td></tr>'

    # セッションテーブル（時系列固定順）
    session_rows = []
    for sess in SESSION_ORDER:
        stats = by_session.get(sess)
        if stats and stats["total"] > 0:
            session_rows.append(render_stat_row(sess, stats))
    session_html = "\n".join(session_rows) or '<tr><td colspan="7" style="text-align:center;color:#6e7781;padding:16px">データ蓄積中</td></tr>'

    # 月別テーブル（時系列ソート）
    month_rows = []
    for m in sorted(by_month.keys()):
        stats = by_month[m]
        if stats["total"] > 0:
            month_rows.append(render_stat_row(m, stats))
    month_html = "\n".join(month_rows) or '<tr><td colspan="7" style="text-align:center;color:#6e7781;padding:16px">データ蓄積中</td></tr>'

    # 時間別ヒートマップデータ（0-23 時 × 勝率）
    hour_labels = list(range(24))
    hour_win_rates = []
    hour_counts = []
    for h in hour_labels:
        s = by_hour.get(h)
        if s and s["total"] > 0:
            hour_win_rates.append(round(s["win_rate"], 1))
            hour_counts.append(s["total"])
        else:
            hour_win_rates.append(None)
            hour_counts.append(0)

    return f"""
<div class="tab-pane" id="pane-analytics">
  <h2>📅 曜日別勝率</h2>
  <div class="scroll-x"><table>
    <thead><tr><th>曜日</th><th style="text-align:right">確定数</th><th style="text-align:right">勝率</th>
      <th style="text-align:right">TP1率</th><th style="text-align:right">TP2率</th>
      <th style="text-align:right">SL</th><th style="text-align:right">期待 R</th></tr></thead>
    <tbody>{weekday_html}</tbody>
  </table></div>
  <p style="font-size:.82rem;color:#6e7781;margin-top:8px">
    💡 <b>使い方</b>: 「月曜は勝率高い、金曜は要注意」みたいな傾向が見えてきます。最低 10 件あれば信頼性高。
  </p>

  <h2 style="margin-top:32px">🕐 時間帯（セッション）別勝率</h2>
  <div class="scroll-x"><table>
    <thead><tr><th>セッション</th><th style="text-align:right">確定数</th><th style="text-align:right">勝率</th>
      <th style="text-align:right">TP1率</th><th style="text-align:right">TP2率</th>
      <th style="text-align:right">SL</th><th style="text-align:right">期待 R</th></tr></thead>
    <tbody>{session_html}</tbody>
  </table></div>
  <p style="font-size:.82rem;color:#6e7781;margin-top:8px">
    💡 <b>使い方</b>: 「東京セッションは騙し多い、NY オープンは強い」など、自分の取引時間帯を最適化できます。
  </p>

  <h2 style="margin-top:32px">📊 月別勝率</h2>
  <div class="scroll-x"><table>
    <thead><tr><th>月</th><th style="text-align:right">確定数</th><th style="text-align:right">勝率</th>
      <th style="text-align:right">TP1率</th><th style="text-align:right">TP2率</th>
      <th style="text-align:right">SL</th><th style="text-align:right">期待 R</th></tr></thead>
    <tbody>{month_html}</tbody>
  </table></div>
  <p style="font-size:.82rem;color:#6e7781;margin-top:8px">
    💡 <b>使い方</b>: 月末（例: 12 月）の勝率パターン、長期トレンドの変化が見えます。
  </p>

  <h2 style="margin-top:32px">⏱️ 時間帯ヒートマップ（24 時間）</h2>
  <div class="chart-box" style="height:280px"><canvas id="hourlyChart"></canvas></div>
  <p style="font-size:.82rem;color:#6e7781;margin-top:8px">
    💡 <b>使い方</b>: 1 時間単位で見たいときに。FOMC や ECB の発言時刻周辺で勝率が変動するパターンを発見できます。
  </p>
</div>"""


def build_quality_analysis_section(signals):
    """WS-5 + EW-6 + CS-5 統合：シグナル品質を多面的に分析するタブ

    - WS-5: 往復ビンタ防止（反転検知別 × 勝率、トレンド整合性 × 勝率）
    - EW-6: 環境スコア × 勝率（A/B/C/D、VIX 帯、ATR レジーム）
    - CS-5: 通貨強弱マトリクス（FX のみ、整合性別勝率 + 直近 30 件詳細）
    """

    # === WS-5-A: 反転検知別 ===
    def _reversal_label(e):
        wc = e.get("whipsaw_check") or {}
        if wc.get("is_reversal") is True:
            return "🔄 反転検知あり"
        if wc.get("is_reversal") is False:
            return "✅ 反転なし"
        return None
    reversal_groups = group_stats(signals, _reversal_label)

    # === WS-5-B: マルチタイムフレーム整合性別 ===
    def _trend_label(e):
        return {
            True: "✅ 順張り（上位足と一致）",
            False: "⚠️ 逆張り（上位足と逆）",
            None: "〜 中立・判定不能",
        }.get((e.get("trend_alignment") or {}).get("aligned"))
    trend_groups = group_stats(signals, _trend_label)

    # === B2: 信頼度スコア別 ===
    CONFIDENCE_LABELS = {
        "HIGH": "⭐⭐⭐ HIGH（強）",
        "MID": "⭐⭐ MID（中）",
        "LOW": "⭐ LOW（弱）",
    }
    conf_groups = group_stats(
        signals,
        lambda e: CONFIDENCE_LABELS.get((e.get("confidence") or {}).get("label")),
    )

    # === EW-6-A: 環境スコア別 ===
    env_groups = group_stats(signals, lambda e: (e.get("environment") or {}).get("env_score"))

    # === EW-6-B: VIX 帯別 ===
    def _vix_bucket(e):
        v = ((e.get("environment") or {}).get("vix") or {}).get("current")
        if v is None:
            return None
        if v < 15:
            return "VIX 低 (< 15)"
        elif v < 20:
            return "VIX 平常 (15-20)"
        elif v < 25:
            return "VIX 高め (20-25)"
        elif v < 30:
            return "VIX 警戒 (25-30)"
        else:
            return "VIX 危険 (30+)"
    vix_groups = group_stats(signals, _vix_bucket)

    # === EW-6-C: ATR レジーム別 ===
    ATR_LABELS = {"low": "🟢 低 ATR", "normal": "🟡 通常 ATR", "high": "🟠 高 ATR", "extreme": "🔴 異常 ATR"}
    atr_groups = group_stats(
        signals,
        lambda e: ATR_LABELS.get(((e.get("environment") or {}).get("atr_regime") or {}).get("regime")),
    )

    # === CS-5: 通貨強弱マトリクス（FX のみ） ===
    def _parse_fx_pair(ticker):
        """USDJPY=X → ('USD','JPY'), AUDUSD=X → ('AUD','USD')、それ以外は (None, None)"""
        if not ticker or not ticker.endswith("=X"):
            return None, None
        sym = ticker[:-2]
        if len(sym) != 6:
            return None, None
        return sym[:3], sym[3:]

    closed = [s for s in signals if s.get("outcome") in ("tp1", "tp2", "sl", "expired")]
    fx_rows = []
    for s in closed:
        base, quote = _parse_fx_pair(s.get("ticker", ""))
        if base is None:
            continue
        strengths = s.get("currency_strength") or {}
        base_s = strengths.get(base)
        quote_s = strengths.get(quote)
        if base_s is None or quote_s is None:
            continue
        direction = s.get("direction") or ""
        is_long = ("ロング" in direction) or ("買い" in direction)
        diff = base_s - quote_s
        # ロング = 買い通貨が強く、売り通貨が弱い ⇒ diff > 0 で順張り
        # ショート = 逆
        signed_diff = diff if is_long else -diff
        # 閾値 ±0.05: 現状のシグナル発火時の強弱差は ±0.1 未満が大半のため、
        # ±0.1 だと「中立」に偏る。±0.05 で順張り/逆張りの分離を確保する。
        if signed_diff > 0.05:
            alignment = "順張り"
        elif signed_diff < -0.05:
            alignment = "逆張り"
        else:
            alignment = "中立"
        fx_rows.append({
            "ticker": s.get("ticker"),
            "direction_short": "L" if is_long else "S",
            "base": base, "quote": quote,
            "base_s": base_s, "quote_s": quote_s,
            "diff": diff,
            "alignment": alignment,
            "outcome": s.get("outcome"),
            "fired_at": (s.get("fired_at") or "")[:16].replace("T", " "),
        })

    # CS-5 クロス集計
    fx_align_stats = defaultdict(lambda: defaultdict(int))
    for r in fx_rows:
        fx_align_stats[r["alignment"]][r["outcome"]] += 1

    def _fx_alignment_row(label, counts):
        total = sum(counts.values())
        if total == 0:
            return ""
        tp1 = counts.get("tp1", 0)
        tp2 = counts.get("tp2", 0)
        sl = counts.get("sl", 0)
        wins = tp1 + tp2
        wr = wins / (wins + sl) * 100 if (wins + sl) else 0
        color = "#1a7f37" if wr >= 60 else "#9a6700" if wr >= 45 else "#cf222e"
        return f"""
        <tr>
          <td><b>{label}</b></td>
          <td style="text-align:right">{total}</td>
          <td style="text-align:right">{tp1}</td>
          <td style="text-align:right">{tp2}</td>
          <td style="text-align:right">{sl}</td>
          <td style="text-align:right;color:{color};font-weight:700">{wr:.1f}%</td>
        </tr>"""

    fx_align_html = "\n".join(
        _fx_alignment_row(k, fx_align_stats.get(k, {})) for k in ("順張り", "中立", "逆張り")
    ) or '<tr><td colspan="6" style="text-align:center;color:#6e7781;padding:16px">FX シグナル蓄積中</td></tr>'

    # CS-5 直近 30 件詳細
    fx_detail_rows = []
    for r in sorted(fx_rows, key=lambda x: x["fired_at"], reverse=True)[:30]:
        outcome = r["outcome"] or "—"
        out_emoji = {"tp1": "✅ TP1", "tp2": "🎯 TP2", "sl": "❌ SL", "expired": "⏰ 期限"}.get(outcome, outcome)
        out_color = {"tp1": "#1a7f37", "tp2": "#1a7f37", "sl": "#cf222e", "expired": "#6e7781"}.get(outcome, "#6e7781")
        align_color = {"順張り": "#1a7f37", "逆張り": "#cf222e", "中立": "#6e7781"}.get(r["alignment"], "#6e7781")
        dir_color = "#1a7f37" if r["direction_short"] == "L" else "#cf222e"
        fx_detail_rows.append(f"""
        <tr>
          <td style="white-space:nowrap">{r['fired_at']}</td>
          <td><b>{r['ticker']}</b></td>
          <td style="text-align:center;font-weight:700;color:{dir_color}">{r['direction_short']}</td>
          <td style="text-align:right">{r['base']}: {r['base_s']:+.3f}</td>
          <td style="text-align:right">{r['quote']}: {r['quote_s']:+.3f}</td>
          <td style="text-align:right">{r['diff']:+.3f}</td>
          <td style="color:{align_color};font-weight:700">{r['alignment']}</td>
          <td style="color:{out_color};font-weight:700;white-space:nowrap">{out_emoji}</td>
        </tr>""")

    # 汎用テーブルレンダラ（既存の render_stat_row を流用）
    def _render_groups(groups_dict, key_order=None):
        if key_order:
            keys = [k for k in key_order if k in groups_dict]
        else:
            keys = sorted(
                groups_dict.keys(),
                key=lambda k: -(groups_dict[k].get("win_rate", 0)),
            )
        rows = []
        for k in keys:
            s = groups_dict.get(k)
            if s and s.get("total", 0) > 0:
                rows.append(render_stat_row(k, s))
        return "\n".join(rows) or '<tr><td colspan="7" style="text-align:center;color:#6e7781;padding:16px">データ蓄積中</td></tr>'

    reversal_html = _render_groups(reversal_groups, key_order=["✅ 反転なし", "🔄 反転検知あり"])
    trend_html = _render_groups(
        trend_groups,
        key_order=["✅ 順張り（上位足と一致）", "〜 中立・判定不能", "⚠️ 逆張り（上位足と逆）"],
    )
    conf_html = _render_groups(
        conf_groups,
        key_order=["⭐⭐⭐ HIGH（強）", "⭐⭐ MID（中）", "⭐ LOW（弱）"],
    )
    env_html = _render_groups(env_groups, key_order=["A", "B", "C", "D"])
    vix_html = _render_groups(
        vix_groups,
        key_order=["VIX 低 (< 15)", "VIX 平常 (15-20)", "VIX 高め (20-25)", "VIX 警戒 (25-30)", "VIX 危険 (30+)"],
    )
    atr_html = _render_groups(
        atr_groups,
        key_order=["🟢 低 ATR", "🟡 通常 ATR", "🟠 高 ATR", "🔴 異常 ATR"],
    )

    fx_detail_html = "".join(fx_detail_rows) or \
        '<tr><td colspan="8" style="text-align:center;color:#6e7781;padding:16px">FX シグナル蓄積中</td></tr>'

    return f"""
<div class="tab-pane" id="pane-quality">
  <h2>🔄 往復ビンタ防止：反転検知別 勝率（WS-5）</h2>
  <p style="font-size:.88rem;color:#57606a;margin-bottom:12px">
    💡 直近 12 時間以内に反対方向シグナルが出たケース（反転検知あり）と、なかったケースで実際の勝率に差があるかを検証します。
    反転検知ありの勝率が低ければ「反転後の見送り推奨」が有効である裏付けになります。
  </p>
  <div class="scroll-x"><table>
    <thead><tr><th>反転検知</th><th style="text-align:right">確定数</th><th style="text-align:right">勝率</th>
      <th style="text-align:right">TP1率</th><th style="text-align:right">TP2率</th>
      <th style="text-align:right">SL</th><th style="text-align:right">期待 R</th></tr></thead>
    <tbody>{reversal_html}</tbody>
  </table></div>

  <h2 style="margin-top:32px">📐 マルチタイムフレーム整合性別 勝率（WS-5）</h2>
  <p style="font-size:.88rem;color:#57606a;margin-bottom:12px">
    💡 上位足（4H シグナルなら日足、1H シグナルなら 4H）のトレンドと整合する「順張り」と、逆らう「逆張り」で勝率を比較。
    順張りが 60% を超えれば「上位足整合性チェック」が勝率向上に寄与している証拠です。
  </p>
  <div class="scroll-x"><table>
    <thead><tr><th>整合性</th><th style="text-align:right">確定数</th><th style="text-align:right">勝率</th>
      <th style="text-align:right">TP1率</th><th style="text-align:right">TP2率</th>
      <th style="text-align:right">SL</th><th style="text-align:right">期待 R</th></tr></thead>
    <tbody>{trend_html}</tbody>
  </table></div>

  <h2 style="margin-top:32px">💯 信頼度スコア別 勝率（B2）</h2>
  <p style="font-size:.88rem;color:#57606a;margin-bottom:12px">
    💡 シグナル発火時の信頼度（複数シグナル × 環境 × トレンド整合 × 反転 × FX 強弱を統合）別の勝率を集計。
    HIGH の勝率が LOW より明確に高ければ、信頼度スコアの計算ロジックが機能していることの裏付けになります。
  </p>
  <div class="scroll-x"><table>
    <thead><tr><th>信頼度</th><th style="text-align:right">確定数</th><th style="text-align:right">勝率</th>
      <th style="text-align:right">TP1率</th><th style="text-align:right">TP2率</th>
      <th style="text-align:right">SL</th><th style="text-align:right">期待 R</th></tr></thead>
    <tbody>{conf_html}</tbody>
  </table></div>

  <h2 style="margin-top:32px">🛡️ 環境警戒スコア別 勝率（EW-6）</h2>
  <p style="font-size:.88rem;color:#57606a;margin-bottom:12px">
    💡 環境スコア A（平常）→ D（取引非推奨）の各スコアで実際の勝率を検証。
    理想は <b>A &gt; B &gt; C &gt; D</b> と順序が保たれること。D が高勝率なら「警告閾値が厳しすぎる」可能性も示唆。
  </p>
  <div class="scroll-x"><table>
    <thead><tr><th>スコア</th><th style="text-align:right">確定数</th><th style="text-align:right">勝率</th>
      <th style="text-align:right">TP1率</th><th style="text-align:right">TP2率</th>
      <th style="text-align:right">SL</th><th style="text-align:right">期待 R</th></tr></thead>
    <tbody>{env_html}</tbody>
  </table></div>

  <h2 style="margin-top:32px">📊 VIX 帯別 勝率（EW-6 補足）</h2>
  <p style="font-size:.88rem;color:#57606a;margin-bottom:12px">
    💡 シグナル発火時の VIX レベル別に勝率を集計。VIX 25 超で取引推奨度を下げているのが妥当か検証できます。
  </p>
  <div class="scroll-x"><table>
    <thead><tr><th>VIX 帯</th><th style="text-align:right">確定数</th><th style="text-align:right">勝率</th>
      <th style="text-align:right">TP1率</th><th style="text-align:right">TP2率</th>
      <th style="text-align:right">SL</th><th style="text-align:right">期待 R</th></tr></thead>
    <tbody>{vix_html}</tbody>
  </table></div>

  <h2 style="margin-top:32px">⚡ ATR レジーム別 勝率（EW-6 補足）</h2>
  <p style="font-size:.88rem;color:#57606a;margin-bottom:12px">
    💡 過去 30 日平均との比率で測ったボラ環境別の勝率。3 倍超（異常 ATR）では取引推奨度を最低まで下げているのが妥当か検証。
  </p>
  <div class="scroll-x"><table>
    <thead><tr><th>レジーム</th><th style="text-align:right">確定数</th><th style="text-align:right">勝率</th>
      <th style="text-align:right">TP1率</th><th style="text-align:right">TP2率</th>
      <th style="text-align:right">SL</th><th style="text-align:right">期待 R</th></tr></thead>
    <tbody>{atr_html}</tbody>
  </table></div>

  <h2 style="margin-top:32px">💱 通貨強弱マトリクス（CS-5）</h2>
  <p style="font-size:.88rem;color:#57606a;margin-bottom:12px">
    💡 FX シグナル発火時の通貨強弱と方向の整合性を集計。<br>
    <b>順張り</b>: 強い通貨を買い・弱い通貨を売り（強弱差が ±0.05% を超え方向と一致）<br>
    <b>逆張り</b>: 弱い通貨を買い・強い通貨を売り<br>
    <b>中立</b>: 強弱差が ±0.05% 以内
  </p>
  <div class="scroll-x"><table>
    <thead><tr><th>整合性</th><th style="text-align:right">FX 確定数</th><th style="text-align:right">TP1</th>
      <th style="text-align:right">TP2</th><th style="text-align:right">SL</th><th style="text-align:right">勝率</th></tr></thead>
    <tbody>{fx_align_html}</tbody>
  </table></div>

  <h3 style="margin-top:24px">📒 FX シグナル × 通貨強弱 直近 30 件</h3>
  <div class="scroll-x"><table style="font-size:.82rem">
    <thead><tr>
      <th>発火時刻</th><th>ペア</th><th>L/S</th>
      <th style="text-align:right">買い側 通貨強弱</th><th style="text-align:right">売り側 通貨強弱</th>
      <th style="text-align:right">差</th><th>整合性</th><th>結果</th>
    </tr></thead>
    <tbody>{fx_detail_html}</tbody>
  </table></div>
</div>"""


def build_loss_analysis_section(signals):
    """SL ヒット案件の敗因分析タブ"""
    sl_signals = [
        s for s in signals
        if s.get("outcome") == "sl" and s.get("loss_analysis", {}).get("ai_result")
    ]

    if not sl_signals:
        return """
<div class="tab-pane" id="pane-loss">
  <h2>🔬 敗因分析</h2>
  <div style="background:#f6f8fa;border:1px solid #d0d7de;border-radius:10px;padding:32px;text-align:center;color:#57606a">
    <div style="font-size:1.6rem;margin-bottom:8px">🌱</div>
    <div style="font-size:1rem;margin-bottom:6px">SL ヒット案件が蓄積されるとここに分析が表示されます</div>
    <div style="font-size:.85rem;color:#6e7781">
      SL に達したトレードについて Gemini が「カテゴリ・主要因・詳細・教訓」を自動分析します。<br>
      失敗から学ぶデータベースとして活用できます。
    </div>
  </div>
</div>"""

    # カテゴリ別集計
    cat_counts = defaultdict(int)
    cat_lessons = defaultdict(list)
    for s in sl_signals:
        ai = s.get("loss_analysis", {}).get("ai_result", {})
        cat = ai.get("primary_category") or "未分類"
        cat_counts[cat] += 1
        lesson = ai.get("lesson") or ""
        if lesson:
            cat_lessons[cat].append(lesson)

    # カテゴリ別バーチャート用データ
    cat_labels = list(cat_counts.keys())
    cat_values = [cat_counts[k] for k in cat_labels]

    # カテゴリ別テーブル
    cat_rows = []
    total_sl = len(sl_signals)
    for cat in sorted(cat_counts.keys(), key=lambda k: -cat_counts[k]):
        pct = cat_counts[cat] / total_sl * 100
        sample_lessons = list(set(cat_lessons[cat]))[:2]
        lesson_html = "<br>".join([f"・{l[:60]}" for l in sample_lessons]) if sample_lessons else "—"
        cat_rows.append(f"""
        <tr>
          <td><b>{cat}</b></td>
          <td style="text-align:right">{cat_counts[cat]}</td>
          <td style="text-align:right">{pct:.1f}%</td>
          <td style="font-size:.82rem;color:#424a53">{lesson_html}</td>
        </tr>""")

    # 直近 SL 案件詳細
    detail_cards = []
    for s in sorted(sl_signals, key=lambda x: x.get("outcome_resolved_at", ""), reverse=True)[:10]:
        ai = s.get("loss_analysis", {}).get("ai_result", {})
        vix = s.get("loss_analysis", {}).get("vix_data") or {}
        fired = s.get("fired_at", "")[:16].replace("T", " ")
        resolved = s.get("outcome_resolved_at", "")[:16].replace("T", " ")
        cat = ai.get("primary_category") or "—"
        cause = ai.get("primary_cause") or "—"
        diag = ai.get("ai_diagnosis") or "—"
        lesson = ai.get("lesson") or "—"
        vix_html = ""
        if vix:
            vix_html = f"<span style='font-size:.82rem;color:#cf222e'>VIX: {vix.get('start')} → {vix.get('end')} ({vix.get('change_pct'):+.1f}%)</span>"

        news_html = ""
        news = s.get("loss_analysis", {}).get("news_during_holding") or []
        if news:
            news_html = "<div style='margin-top:10px;font-size:.82rem;color:#57606a'><b>期間中のニュース:</b><ul style='margin:6px 0 0 20px'>" + \
                "".join([f"<li>{n[:100]}</li>" for n in news[:3]]) + "</ul></div>"

        detail_cards.append(f"""
        <div class="loss-card">
          <div style="display:flex;justify-content:space-between;align-items:start;gap:12px;margin-bottom:8px;flex-wrap:wrap">
            <div>
              <span class="loss-cat-tag">{cat}</span>
              <b style="margin-left:8px">{s.get('asset_name')}</b>
              <span style="color:#6e7781;font-size:.85rem;margin-left:6px">({s.get('timeframe','4h').upper()})</span>
            </div>
            <div style="font-size:.78rem;color:#6e7781">
              {fired} → {resolved}
            </div>
          </div>
          <div style="font-weight:600;color:#cf222e;font-size:.95rem;margin-bottom:6px">❌ {cause}</div>
          <div style="font-size:.88rem;color:#424a53;margin-bottom:8px">{diag}</div>
          <div style="background:#fff8c5;border-left:3px solid #d4a72c;padding:8px 12px;font-size:.85rem;color:#6e5d00;margin-bottom:6px">
            💡 <b>教訓:</b> {lesson}
          </div>
          {vix_html}
          {news_html}
        </div>""")

    return f"""
<div class="tab-pane" id="pane-loss">
  <h2>🔬 敗因分析（SL ヒット案件: {total_sl} 件）</h2>
  <p style="font-size:.92rem;color:#57606a;margin-bottom:18px">
    SL に達したトレードについて Gemini が「カテゴリ・主要因・詳細・教訓」を自動分析しています。
    失敗から学ぶデータベースとして活用してください。
  </p>

  <h3 style="margin-top:24px">📊 カテゴリ別分布</h3>
  <div class="chart-box" style="height:280px"><canvas id="lossCategoryChart"></canvas></div>

  <h3 style="margin-top:32px">🏷️ カテゴリ別 集計と教訓</h3>
  <div class="scroll-x"><table>
    <thead><tr>
      <th>カテゴリ</th><th style="text-align:right">件数</th><th style="text-align:right">割合</th><th>主な教訓</th>
    </tr></thead>
    <tbody>{''.join(cat_rows)}</tbody>
  </table></div>

  <h3 style="margin-top:32px">📒 直近 10 件の敗因詳細</h3>
  <div>{''.join(detail_cards)}</div>
</div>"""


def build_html(signals, trades):
    # timeframe ごとに分割
    signals_4h = [s for s in signals if s.get("timeframe", "4h") == "4h"]
    signals_1h = [s for s in signals if s.get("timeframe") == "1h"]

    # 4 タブそれぞれのダッシュボード
    pane_all = build_dashboard_section(signals, "all", "全体", "equityChartAll")
    pane_4h = build_dashboard_section(signals_4h, "4h", "4H 足のみ", "equityChart4h")
    pane_1h = build_dashboard_section(signals_1h, "1h", "1H 足のみ", "equityChart1h")
    pane_analytics = build_analytics_section(signals)
    pane_quality = build_quality_analysis_section(signals)
    pane_loss = build_loss_analysis_section(signals)

    # 敗因カテゴリチャート用データ
    loss_cat_counts = defaultdict(int)
    for s in signals:
        if s.get("outcome") == "sl":
            ai = s.get("loss_analysis", {}).get("ai_result", {}) if s.get("loss_analysis") else {}
            cat = ai.get("primary_category") or "未分類"
            loss_cat_counts[cat] += 1
    loss_cat_labels = list(loss_cat_counts.keys())
    loss_cat_values = [loss_cat_counts[k] for k in loss_cat_labels]

    # 時間帯ヒートマップ用データ（全シグナル対象）
    def _hour_data(sigs):
        bucket = defaultdict(list)
        for e in sigs:
            if e.get("outcome") not in ("tp1", "tp2", "sl", "expired"):
                continue
            dt = _parse_iso(e.get("fired_at"))
            if dt:
                bucket[dt.hour].append(e)
        win_rates = []
        counts = []
        for h in range(24):
            s = calc_stats(bucket.get(h, []))
            win_rates.append(round(s["win_rate"], 1) if s["total"] > 0 else None)
            counts.append(s["total"])
        return win_rates, counts
    hour_win_rates, hour_counts = _hour_data(signals)

    # エクイティカーブ用データ（タブごと）
    eq_all_labels, eq_all_values = render_equity_curve_data(signals)
    eq_4h_labels, eq_4h_values = render_equity_curve_data(signals_4h)
    eq_1h_labels, eq_1h_values = render_equity_curve_data(signals_1h)

    my_trades_html = render_my_trades_section(trades)
    last_updated = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    count_all = len(signals)
    count_4h = len(signals_4h)
    count_1h = len(signals_1h)

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
    .tab-bar{{display:flex;flex-wrap:wrap;gap:8px;margin:24px 0 18px;border-bottom:2px solid #d0d7de;padding-bottom:8px}}
    .tab-btn{{padding:9px 18px;background:#f6f8fa;border:1px solid #d0d7de;border-radius:8px 8px 0 0;font-size:.92rem;font-weight:600;color:#57606a;cursor:pointer;transition:all .15s}}
    .tab-btn:hover{{border-color:#0969da;color:#0969da}}
    .tab-btn.active{{background:#0969da;border-color:#0969da;color:#fff}}
    .tab-pane{{display:none}}
    .tab-pane.active{{display:block}}
    .dl-card{{display:block;background:#f6f8fa;border:1px solid #d0d7de;border-left:5px solid #0969da;border-radius:10px;padding:18px 22px;text-decoration:none;color:#1f2328;transition:all .2s}}
    .dl-card:hover{{border-color:#0969da;transform:translateY(-2px);box-shadow:0 4px 12px rgba(9,105,218,.15)}}
    .dl-card-icon{{font-size:1.8rem;margin-bottom:6px}}
    .dl-card-title{{font-weight:700;color:#0969da;font-size:1rem;margin-bottom:4px}}
    .dl-card-desc{{font-size:.82rem;color:#57606a;line-height:1.5}}
    .loss-card{{background:#ffffff;border:1px solid #d0d7de;border-left:5px solid #cf222e;border-radius:10px;padding:16px 20px;margin:12px 0}}
    .loss-cat-tag{{display:inline-block;background:#ffebe9;color:#cf222e;border:1px solid #cf222e;font-size:.72rem;font-weight:700;padding:3px 10px;border-radius:4px;letter-spacing:.04em}}
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
    body.dark .tab-bar{{border-bottom-color:#30363d}}
    body.dark .tab-btn{{background:#161b22;border-color:#30363d;color:#8b949e}}
    body.dark .tab-btn:hover{{border-color:#58a6ff;color:#58a6ff}}
    body.dark .tab-btn.active{{background:#1f6feb;border-color:#1f6feb;color:#fff}}
    body.dark .dl-card{{background:#161b22;border-color:#30363d;border-left-color:#58a6ff;color:#e6edf3}}
    body.dark .dl-card:hover{{border-color:#58a6ff}}
    body.dark .dl-card-title{{color:#79c0ff}}
    body.dark .dl-card-desc{{color:#8b949e}}
    body.dark .loss-card{{background:#161b22;border-color:#30363d;border-left-color:#cf222e}}
    body.dark .loss-cat-tag{{background:#3c0f10;color:#ff7b72;border-color:#cf222e}}
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
    <a class="nav-btn" href="market-health.html">🩺 市場健康度</a>
    <a class="nav-btn" href="hot-assets.html">🔥 出来高急増</a>
    <a class="nav-btn" href="political-feed.html">🚨 政治発言ライブ</a>
    <a class="nav-btn" href="youtube-summary.html">📺 YouTube要約</a>
    <a class="nav-btn current" href="track-record.html">📊 シグナル成績</a>
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

  {my_trades_html}

  <div class="tab-bar">
    <button class="tab-btn active" data-tab="all">🌐 全体（{count_all}）</button>
    <button class="tab-btn" data-tab="4h">🕓 4H 足（{count_4h}）</button>
    <button class="tab-btn" data-tab="1h">⏱️ 1H 足（{count_1h}）</button>
    <button class="tab-btn" data-tab="analytics">📅 時間・曜日分析</button>
    <button class="tab-btn" data-tab="quality">🧬 シグナル品質分析</button>
    <button class="tab-btn" data-tab="loss">🔬 敗因分析</button>
    <button class="tab-btn" data-tab="data">📥 データダウンロード</button>
  </div>

  {pane_all}
  {pane_4h}
  {pane_1h}
  {pane_analytics}
  {pane_quality}
  {pane_loss}

  <div class="tab-pane" id="pane-data">
    <h2>📥 生データのダウンロード</h2>
    <p style="font-size:.93rem;color:#57606a;margin-bottom:20px">
      シグナルログ・実取引ログの生データを CSV / JSON でダウンロードできます。
      Excel / Google Sheets / Python pandas で自由に分析してください。
      <br>毎回のワークフロー実行で自動更新されています（最終更新: {last_updated}）。
    </p>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px">
      <a href="signals-log.csv" download class="dl-card">
        <div class="dl-card-icon">📊</div>
        <div class="dl-card-title">signals-log.csv</div>
        <div class="dl-card-desc">全シグナル発火履歴（曜日・時間帯フィールド付き）<br>Excel で開くだけで分析可能</div>
      </a>
      <a href="my-trades.csv" download class="dl-card">
        <div class="dl-card-icon">💼</div>
        <div class="dl-card-title">my-trades.csv</div>
        <div class="dl-card-desc">実取引履歴（エントリー曜日・決済曜日フィールド付き）</div>
      </a>
      <a href="signals-log.json" download class="dl-card">
        <div class="dl-card-icon">🗃️</div>
        <div class="dl-card-title">signals-log.json</div>
        <div class="dl-card-desc">構造化生データ。プログラム処理向き</div>
      </a>
      <a href="my-trades.json" download class="dl-card">
        <div class="dl-card-icon">💼</div>
        <div class="dl-card-title">my-trades.json</div>
        <div class="dl-card-desc">実取引 JSON。プログラム処理向き</div>
      </a>
    </div>
    <h3 style="margin-top:32px">📦 月次バックアップ（GitHub Releases）</h3>
    <p style="font-size:.93rem;color:#57606a">
      毎月 1 日に snapshot を Release として公開しています。
      <a href="https://github.com/invest-ai-info/marketwatch-ai/releases" target="_blank" rel="noopener">
        過去のスナップショット一覧 →
      </a>
    </p>
    <h3 style="margin-top:24px">🛠️ 分析テンプレート（pandas）</h3>
    <pre style="background:#f6f8fa;border:1px solid #d0d7de;border-radius:8px;padding:16px;font-size:.85rem;overflow-x:auto"><code>import pandas as pd
df = pd.read_csv("https://marketwatch-jp.com/signals-log.csv")

# 曜日別勝率
df["win"] = df["outcome"].isin(["tp1", "tp2"])
df.groupby("発火_曜日")["win"].mean()

# 銘柄 × 曜日 マトリクス
df.pivot_table(values="win", index="ticker", columns="発火_曜日", aggfunc="mean")

# 月末勝率（毎月最終 3 営業日）
df["fired_at"] = pd.to_datetime(df["fired_at"])
df["is_month_end"] = df["fired_at"].dt.day >= 28
df.groupby("is_month_end")["win"].mean()</code></pre>
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
  // タブ切替
  document.querySelectorAll('.tab-btn').forEach(btn => {{
    btn.addEventListener('click', () => {{
      const target = btn.dataset.tab;
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === target));
      document.querySelectorAll('.tab-pane').forEach(p => p.classList.toggle('active', p.id === `pane-${{target}}`));
      // Chart.js は表示後に resize しないと canvas サイズが 0 のまま
      window.dispatchEvent(new Event('resize'));
    }});
  }});
  // 初期状態：全体タブ active
  document.getElementById('pane-all').classList.add('active');

  // エクイティカーブ生成ヘルパー
  function makeEquityChart(canvasId, labels, values, color) {{
    const el = document.getElementById(canvasId);
    if (!el) return;
    if (labels.length === 0) {{
      el.parentElement.innerHTML =
        '<div style="text-align:center;padding:60px 0;color:#6e7781">確定シグナルが揃ったらエクイティカーブが表示されます</div>';
      return;
    }}
    new Chart(el.getContext('2d'), {{
      type: 'line',
      data: {{
        labels: labels,
        datasets: [{{
          label: '模擬残高 ($1000 スタート / $100 リスク per シグナル)',
          data: values,
          borderColor: color,
          backgroundColor: color + '20',
          fill: true,
          tension: 0.2,
          pointRadius: 3,
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{ legend: {{ position: 'top' }} }},
        scales: {{ y: {{ ticks: {{ callback: v => '$' + v.toLocaleString() }} }} }}
      }}
    }});
  }}

  makeEquityChart('equityChartAll', {json.dumps(eq_all_labels, ensure_ascii=False)}, {json.dumps(eq_all_values)}, '#0969da');
  makeEquityChart('equityChart4h',  {json.dumps(eq_4h_labels, ensure_ascii=False)},  {json.dumps(eq_4h_values)},  '#1a7f37');
  makeEquityChart('equityChart1h',  {json.dumps(eq_1h_labels, ensure_ascii=False)},  {json.dumps(eq_1h_values)},  '#9a6700');

  // 敗因カテゴリチャート
  (function() {{
    const catLabels = {json.dumps(loss_cat_labels, ensure_ascii=False)};
    const catValues = {json.dumps(loss_cat_values)};
    const el = document.getElementById('lossCategoryChart');
    if (!el) return;
    if (catLabels.length === 0) {{
      el.parentElement.innerHTML = '<div style="text-align:center;padding:80px 0;color:#6e7781">SL ヒット案件が蓄積されたらカテゴリ別分布が表示されます</div>';
      return;
    }}
    new Chart(el.getContext('2d'), {{
      type: 'doughnut',
      data: {{
        labels: catLabels,
        datasets: [{{
          data: catValues,
          backgroundColor: ['#cf222e', '#9a6700', '#0969da', '#1f6feb', '#6e7781', '#8250df'],
          borderWidth: 1,
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{ legend: {{ position: 'right' }} }}
      }}
    }});
  }})();

  // 時間帯ヒートマップ
  (function() {{
    const hourLabels = {json.dumps([f"{h:02d}時" for h in range(24)])};
    const hourWinRates = {json.dumps(hour_win_rates)};
    const hourCounts = {json.dumps(hour_counts)};
    const el = document.getElementById('hourlyChart');
    if (!el) return;
    if (hourCounts.every(c => c === 0)) {{
      el.parentElement.innerHTML = '<div style="text-align:center;padding:80px 0;color:#6e7781">確定シグナルが揃ったらヒートマップが表示されます</div>';
      return;
    }}
    new Chart(el.getContext('2d'), {{
      type: 'bar',
      data: {{
        labels: hourLabels,
        datasets: [{{
          label: '勝率 (%)',
          data: hourWinRates,
          backgroundColor: hourWinRates.map(v => v === null ? '#e6e8eb' : v >= 60 ? '#1a7f37' : v >= 45 ? '#9a6700' : '#cf222e'),
          borderColor: '#d0d7de',
          borderWidth: 1,
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
          legend: {{ display: false }},
          tooltip: {{
            callbacks: {{
              afterLabel: ctx => `確定数: ${{hourCounts[ctx.dataIndex]}} 件`
            }}
          }}
        }},
        scales: {{
          y: {{ min: 0, max: 100, ticks: {{ callback: v => v + '%' }} }}
        }}
      }}
    }});
  }})();

  // ダークモードトグル
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
