"""
export_to_csv.py
───────────────────────────────────────
signals-log.json / my-trades.json を CSV にエクスポート。

派生フィールドを自動追加:
- 曜日（月〜日）
- 時間帯（早朝/午前/午後/夕方/夜/深夜）
- 月、週番号
- セッション（東京/欧州/NY）

これで Excel / pandas / Google Sheets での分析が一発で可能になる。
ワークフロー実行ごとに自動更新されるため、いつでも最新データを取得可能。

出力ファイル:
- signals-log.csv  - 全シグナル発火履歴
- my-trades.csv    - 実取引履歴
"""
import os
import sys
import csv
import json
from datetime import datetime, timezone, timedelta

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

JST = timezone(timedelta(hours=9))
SIGNALS_LOG_FILE = "signals-log.json"
TRADES_FILE = "my-trades.json"
SIGNALS_CSV = "signals-log.csv"
TRADES_CSV = "my-trades.csv"

# 曜日マッピング（datetime.weekday(): 0=月 ... 6=日）
WEEKDAY_JP = ["月", "火", "水", "木", "金", "土", "日"]


def get_time_session(hour):
    """JST 時刻を市場セッションにマッピング"""
    if 0 <= hour < 6:
        return "深夜"
    elif 6 <= hour < 9:
        return "早朝"
    elif 9 <= hour < 15:
        return "東京セッション"
    elif 15 <= hour < 17:
        return "欧州オープン"
    elif 17 <= hour < 22:
        return "欧州セッション"
    else:  # 22-24
        return "NY セッション"


def parse_iso(s):
    """ISO 8601 文字列を datetime に。失敗時 None。"""
    if not s:
        return None
    try:
        # +09:00 タイムゾーン込みでパース
        return datetime.fromisoformat(s)
    except Exception:
        return None


def add_derived_fields(dt_iso, prefix=""):
    """日時から曜日・時間帯・月・週番号などを派生フィールドとして返す"""
    dt = parse_iso(dt_iso)
    if dt is None:
        return {
            f"{prefix}曜日": "",
            f"{prefix}時間": "",
            f"{prefix}セッション": "",
            f"{prefix}月": "",
            f"{prefix}週番号": "",
            f"{prefix}日付": "",
        }
    return {
        f"{prefix}曜日": WEEKDAY_JP[dt.weekday()],
        f"{prefix}時間": dt.hour,
        f"{prefix}セッション": get_time_session(dt.hour),
        f"{prefix}月": dt.month,
        f"{prefix}週番号": dt.isocalendar().week,
        f"{prefix}日付": dt.strftime("%Y-%m-%d"),
    }


def export_signals(log):
    """signals-log.json → CSV（派生フィールド付き）"""
    rows = []
    for s in log:
        fired_dt = parse_iso(s.get("fired_at"))
        resolved_dt = parse_iso(s.get("outcome_resolved_at"))

        # 保有時間（hours）を計算
        holding_hours = ""
        if fired_dt and resolved_dt:
            try:
                holding_hours = round((resolved_dt - fired_dt).total_seconds() / 3600.0, 2)
            except Exception:
                pass

        row = {
            "id": s.get("id", ""),
            "fired_at": s.get("fired_at", ""),
            "timeframe": s.get("timeframe", "4h"),
            "ticker": s.get("ticker", ""),
            "asset_name": s.get("asset_name", ""),
            "primary_signal": s.get("primary_signal", ""),
            "primary_signal_label": s.get("primary_signal_label", ""),
            "signal_count": s.get("signal_count", 1),
            "signal_types": ",".join(s.get("signal_types", [])),
            "direction": s.get("direction") or "",
            "entry": s.get("entry") or "",
            "stop_loss": s.get("stop_loss") or "",
            "take_profit_1": s.get("take_profit_1") or "",
            "take_profit_2": s.get("take_profit_2") or "",
            "atr": s.get("atr") or "",
            "sl_pct": s.get("sl_pct") or "",
            "tp1_pct": s.get("tp1_pct") or "",
            "tp2_pct": s.get("tp2_pct") or "",
            "outcome": s.get("outcome") or "",
            "outcome_resolved_at": s.get("outcome_resolved_at") or "",
            "holding_hours": holding_hours,
            "max_favorable_excursion_pct": s.get("max_favorable_excursion_pct") or "",
            "max_adverse_excursion_pct": s.get("max_adverse_excursion_pct") or "",
            "rsi": (s.get("indicators_at_signal") or {}).get("rsi", ""),
            "macd": (s.get("indicators_at_signal") or {}).get("macd", ""),
            "ma25": (s.get("indicators_at_signal") or {}).get("ma25", ""),
            "ma75": (s.get("indicators_at_signal") or {}).get("ma75", ""),
            "news_count": s.get("news_count", 0),
            "ai_narrative": (s.get("ai_narrative") or "").replace("\n", " ").replace("\r", " "),
            "linked_trade_id": s.get("linked_trade_id", ""),
            "pseudo_record": "YES" if s.get("pseudo_record") else "",
        }
        row.update(add_derived_fields(s.get("fired_at"), prefix="発火_"))
        rows.append(row)

    if not rows:
        # ヘッダー行だけ書き出す
        with open(SIGNALS_CSV, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "id", "fired_at", "timeframe", "ticker", "asset_name",
                "primary_signal", "outcome", "発火_曜日", "発火_時間"
            ])
            writer.writeheader()
        return 0

    fieldnames = list(rows[0].keys())
    with open(SIGNALS_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def export_trades(trades):
    """my-trades.json → CSV"""
    rows = []
    for t in trades:
        entry_dt = parse_iso(t.get("entry_at"))
        exit_dt = parse_iso(t.get("exit_at"))
        holding_hours = ""
        if entry_dt and exit_dt:
            try:
                holding_hours = round((exit_dt - entry_dt).total_seconds() / 3600.0, 2)
            except Exception:
                pass

        row = {
            "id": t.get("id", ""),
            "entry_at": t.get("entry_at", ""),
            "exit_at": t.get("exit_at", ""),
            "symbol": t.get("symbol", ""),
            "direction": t.get("direction", ""),
            "entry_price": t.get("entry_price", ""),
            "exit_price": t.get("exit_price", ""),
            "lot": t.get("lot", ""),
            "stop_loss": t.get("stop_loss", ""),
            "take_profit": t.get("take_profit", ""),
            "pnl_pct": t.get("pnl_pct", ""),
            "holding_hours": holding_hours,
            "kind": t.get("kind", ""),
            "status": t.get("status", ""),
            "note": (t.get("note") or "").replace("\n", " ").replace("\r", " "),
        }
        row.update(add_derived_fields(t.get("entry_at"), prefix="エントリー_"))
        row.update(add_derived_fields(t.get("exit_at"), prefix="決済_"))
        rows.append(row)

    if not rows:
        with open(TRADES_CSV, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "id", "entry_at", "exit_at", "symbol", "direction", "pnl_pct"
            ])
            writer.writeheader()
        return 0

    fieldnames = list(rows[0].keys())
    with open(TRADES_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def main():
    print("📤 CSV エクスポート開始")

    # signals-log
    if os.path.exists(SIGNALS_LOG_FILE):
        with open(SIGNALS_LOG_FILE, encoding="utf-8") as f:
            signals = json.load(f)
    else:
        signals = []
    n = export_signals(signals)
    size_kb = os.path.getsize(SIGNALS_CSV) / 1024
    print(f"  ✅ {SIGNALS_CSV}: {n} 件 ({size_kb:.1f} KB)")

    # my-trades
    if os.path.exists(TRADES_FILE):
        with open(TRADES_FILE, encoding="utf-8") as f:
            trades = json.load(f)
    else:
        trades = []
    n = export_trades(trades)
    size_kb = os.path.getsize(TRADES_CSV) / 1024
    print(f"  ✅ {TRADES_CSV}: {n} 件 ({size_kb:.1f} KB)")

    print("📤 CSV エクスポート完了")


if __name__ == "__main__":
    main()
