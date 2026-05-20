"""
evaluate_signal_outcomes.py
───────────────────────────────────────
signals-log.json の未確定シグナルについて、yfinance で発火時刻以降の価格を取得し
SL / TP1 / TP2 のどれに先にヒットしたかを判定する。

判定ルール:
- ロング: 高値が TP1/TP2 に達したか、安値が SL に達したか
- ショート: 安値が TP1/TP2 に達したか、高値が SL に達したか
- 7 日経過してどれもヒットしなければ "expired"
- 先に到達した方を採用（同一バー内なら SL を優先＝最悪ケース）

MFE (Max Favorable Excursion) / MAE (Max Adverse Excursion) も計算して記録。

GitHub Actions の technical-alerts ワークフローに後続ステップとして組み込む想定。
"""
import os
import sys
import json
from datetime import datetime, timezone, timedelta

import yfinance as yf
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

JST = timezone(timedelta(hours=9))
SIGNALS_LOG_FILE = "signals-log.json"
EXPIRY_DAYS = 7  # シグナル発火から 7 日経って未到達なら expired


def load_log():
    if not os.path.exists(SIGNALS_LOG_FILE):
        print(f"⚠️ {SIGNALS_LOG_FILE} が存在しません")
        return []
    with open(SIGNALS_LOG_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_log(log):
    with open(SIGNALS_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


def fetch_prices_since(ticker, start_dt_utc, interval="1h"):
    """発火時刻から現在までの 1H 足を取得"""
    try:
        # yfinance は naive datetime を渡すと UTC として扱う
        df = yf.download(
            ticker,
            start=start_dt_utc.strftime("%Y-%m-%d"),
            interval=interval,
            progress=False,
            auto_adjust=True,
        )
        if df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        # 発火時刻以降のみ
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")
        df = df[df.index >= start_dt_utc]
        return df
    except Exception as e:
        print(f"  ⚠️ {ticker} 価格取得失敗: {type(e).__name__}: {str(e)[:80]}")
        return None


def evaluate_one(entry, now_jst):
    """1 シグナルの結果を判定。entry を破壊的に更新し、変更があれば True を返す"""
    if entry.get("outcome"):
        return False  # 既に確定済み

    if entry.get("direction") not in ("ロング（買い）", "ショート（売り）"):
        # 方向プランなしのシグナルは判定対象外
        if entry.get("outcome") is None:
            entry["outcome"] = "no_plan"
            entry["outcome_resolved_at"] = now_jst.isoformat(timespec="seconds")
            return True
        return False

    is_long = entry["direction"] == "ロング（買い）"
    fired_at = datetime.fromisoformat(entry["fired_at"])
    fired_at_utc = fired_at.astimezone(timezone.utc)
    age_hours = (now_jst - fired_at).total_seconds() / 3600.0

    df = fetch_prices_since(entry["ticker"], fired_at_utc)
    if df is None or df.empty:
        return False  # 価格データなし、次回再判定

    entry_price = entry["entry"]
    sl = entry["stop_loss"]
    tp1 = entry["take_profit_1"]
    tp2 = entry["take_profit_2"]

    hit_sl_at = None
    hit_tp1_at = None
    hit_tp2_at = None

    # 各バーを時系列で走査
    for ts, row in df.iterrows():
        bar_high = float(row["High"])
        bar_low = float(row["Low"])

        if is_long:
            # SL: low が SL 以下
            if hit_sl_at is None and bar_low <= sl:
                hit_sl_at = ts.isoformat()
            # TP1: high が TP1 以上
            if hit_tp1_at is None and bar_high >= tp1:
                hit_tp1_at = ts.isoformat()
            # TP2: high が TP2 以上
            if hit_tp2_at is None and bar_high >= tp2:
                hit_tp2_at = ts.isoformat()
        else:  # short
            if hit_sl_at is None and bar_high >= sl:
                hit_sl_at = ts.isoformat()
            if hit_tp1_at is None and bar_low <= tp1:
                hit_tp1_at = ts.isoformat()
            if hit_tp2_at is None and bar_low <= tp2:
                hit_tp2_at = ts.isoformat()

        # 早期確定: SL も TP も発生したら判定可能
        if hit_sl_at and hit_tp2_at:
            break

    # MFE / MAE 計算（含み益・含み損の最大値、entry 起点の %）
    if is_long:
        max_price = float(df["High"].max())
        min_price = float(df["Low"].min())
        mfe_pct = (max_price - entry_price) / entry_price * 100
        mae_pct = (min_price - entry_price) / entry_price * 100
    else:
        max_price = float(df["High"].max())
        min_price = float(df["Low"].min())
        mfe_pct = (entry_price - min_price) / entry_price * 100  # ショートは下げが利益
        mae_pct = (entry_price - max_price) / entry_price * 100  # 上げが損失

    entry["max_favorable_excursion_pct"] = round(mfe_pct, 3)
    entry["max_adverse_excursion_pct"] = round(mae_pct, 3)

    # 判定優先順: 同一バー内なら SL を優先（最悪シナリオを採用）
    # → SL のタイムスタンプが TP より早ければ SL、TP の方が早ければ TP
    # → 同時の場合は SL（保守的判定）
    outcome = None
    resolved_at = None

    # SL ヒット時刻と TP1/TP2 ヒット時刻を比較
    def _to_ts(s):
        return datetime.fromisoformat(s) if s else None

    sl_ts = _to_ts(hit_sl_at)
    tp1_ts = _to_ts(hit_tp1_at)
    tp2_ts = _to_ts(hit_tp2_at)

    # まず、最も早く起きたヒットを特定
    candidates = []
    if sl_ts:
        candidates.append(("sl", sl_ts))
    if tp1_ts:
        candidates.append(("tp1", tp1_ts))
    if tp2_ts:
        candidates.append(("tp2", tp2_ts))

    if candidates:
        # 最も早いものを採用。同時刻なら SL を優先
        candidates.sort(key=lambda x: (x[1], 0 if x[0] == "sl" else 1))
        outcome, resolved_at_ts = candidates[0]
        resolved_at = resolved_at_ts.isoformat()
    elif age_hours >= EXPIRY_DAYS * 24:
        outcome = "expired"
        resolved_at = now_jst.isoformat(timespec="seconds")

    if outcome:
        entry["outcome"] = outcome
        entry["outcome_resolved_at"] = resolved_at
        entry["hit_sl_at"] = hit_sl_at
        entry["hit_tp1_at"] = hit_tp1_at
        entry["hit_tp2_at"] = hit_tp2_at
        print(f"  ✅ {entry['id']}: {outcome.upper()} @ {resolved_at} "
              f"(MFE {mfe_pct:+.2f}%, MAE {mae_pct:+.2f}%)")
        return True
    else:
        print(f"  ⏳ {entry['id']}: 未確定（経過 {age_hours:.1f}h, "
              f"MFE {mfe_pct:+.2f}%, MAE {mae_pct:+.2f}%）")
        # MFE/MAE は変動するので毎回更新
        return True


def main():
    print("📊 シグナル結果判定スクリプト開始")
    log = load_log()
    if not log:
        print("⏭️ シグナルログが空です。判定対象なし")
        return

    now_jst = datetime.now(JST)
    pending = [e for e in log if not e.get("outcome")]
    resolved_count = sum(1 for e in log if e.get("outcome") and e.get("outcome") != "no_plan")
    print(f"  全シグナル: {len(log)} 件 / 確定済: {resolved_count} / 未確定: {len(pending)}")

    if not pending:
        print("✅ すべて確定済み")
        return

    updates = 0
    for entry in pending:
        if evaluate_one(entry, now_jst):
            updates += 1

    save_log(log)
    print(f"\n💾 {updates} 件のレコードを更新")

    # サマリ統計
    new_resolved = sum(1 for e in log
                       if e.get("outcome") and e.get("outcome") not in (None, "no_plan"))
    new_pending = sum(1 for e in log if not e.get("outcome"))
    print(f"📈 確定済: {new_resolved} / 未確定: {new_pending}")


if __name__ == "__main__":
    main()
