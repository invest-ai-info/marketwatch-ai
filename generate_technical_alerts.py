"""
generate_technical_alerts.py — 4H テクニカル分析 → メールアラート

GitHub Actions から 4 時間ごとに呼ばれる。
複数銘柄の 4H 足チャートを取得し、テクニカル指標を計算 → シグナル判定。
発火したら Gemini で解説生成 → Gmail SMTP でメール送信。
同じシグナルを連投しないよう履歴を JSON 保存。
"""
import os
import sys
import json
import smtplib
import urllib.request
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate

import yfinance as yf
import pandas as pd
import numpy as np

# Windows コンソール (cp932) でも絵文字を出せるようにする
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

JST = timezone(timedelta(hours=9))

# ─────────────────────────────────────────────
# 対象銘柄
# (ティッカー, 表示名, 通貨記号, 価格小数桁)
# ─────────────────────────────────────────────
SYMBOLS = [
    # (ticker, name, currency, decimals, cooldown_hours_4h)
    # cooldown_hours_4h: 同銘柄・同シグナルの連投防止期間（4H ワークフロー用）
    # 1H ワークフローは別途 4h 固定（main 内のロジック）

    # ── コモディティ / 株価指数 / 暗号資産 ──
    ("GC=F",     "ゴールド先物",         "$", 2, 12),
    ("SI=F",     "銀 先物",              "$", 3, 12),   # 🆕 ゴールドと連動、よりボラ大
    ("CL=F",     "原油 WTI 先物",        "$", 2, 24),  # ニュース感応度高、往復ビンタ多発のため長めに
    ("NKD=F",    "日経 225 先物 (CME)",  "",  0, 12),
    ("BTC-USD",  "ビットコイン",         "$", 0, 12),

    # ── 🆕 米欧株価指数（先物中心、24h 取引） ──
    ("ES=F",     "S&P500 先物",          "$", 2, 12),   # 🆕 米国株主要指数
    ("NQ=F",     "Nasdaq 100 先物",      "$", 2, 12),   # 🆕 AI / ハイテク
    ("YM=F",     "ダウ 30 先物",         "$", 0, 12),   # 🆕 米国伝統大型株
    ("^FTSE",    "UK100 (FTSE 100)",     "£", 2, 12),   # 🆕 英国主要指数

    # ── FX: USD/JPY（介入リスクで長めの cooldown） ──
    ("USDJPY=X", "ドル円",               "¥", 3, 18),

    # ── FX: JPY クロス（介入リスクで長めの cooldown） ──
    ("EURJPY=X", "ユーロ円",             "¥", 3, 18),
    ("GBPJPY=X", "ポンド円",             "¥", 3, 18),
    ("AUDJPY=X", "豪ドル円",             "¥", 3, 18),

    # ── FX: ドルストレート ──
    ("EURUSD=X", "ユーロドル",           "",  5, 12),
    ("GBPUSD=X", "ポンドドル",           "",  5, 12),

    # ── FX: AUD クロス（コモディティ・中国景気連動） ──
    # ※ AUD/JPY（オージー円）は上の「JPY クロス」セクションに含む
    ("AUDUSD=X", "豪ドル米ドル（オージードル）",   "",  5, 12),
    ("EURAUD=X", "ユーロ/豪ドル（ユーロオージー）", "",  5, 12),
    ("GBPAUD=X", "ポンド/豪ドル（ポンドオージー）", "",  5, 12),
]

ALERT_HISTORY_FILE = "technical-alerts-history.json"
ALERT_COOLDOWN_HOURS = 12  # 同じ銘柄・同じシグナルは 12 時間連投しない
SIGNALS_LOG_FILE = "signals-log.json"  # 全シグナル発火記録（track-record 用）
ECONOMIC_EVENTS_FILE = "economic-events.json"  # 重要指標カレンダー


# ─────────────────────────────────────────────
# 価格データ取得（timeframe で 1h or 4h 切替）
# ─────────────────────────────────────────────
def fetch_data(symbol, timeframe="4h", days=30):
    """yfinance で 1h 足を取得。timeframe='4h' の場合はリサンプル、'1h' はそのまま。"""
    try:
        df = yf.download(symbol, period=f"{days}d", interval="1h", progress=False, auto_adjust=True)
        if df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        if timeframe == "4h":
            agg = {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}
            df = df.resample("4h").agg(agg).dropna(subset=["Close"])
        # "1h" の場合は何もしない（既に 1h）
        return df
    except Exception as e:
        print(f"  ⚠️ {symbol} データ取得失敗 ({timeframe}): {type(e).__name__}: {str(e)[:80]}")
        return None


# 後方互換のためのエイリアス（旧名称を残す）
def fetch_4h_data(symbol, days=30):
    return fetch_data(symbol, timeframe="4h", days=days)


# ─────────────────────────────────────────────
# テクニカル指標
# ─────────────────────────────────────────────
def calc_rsi(close, period=14):
    delta = close.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    avg_up = up.ewm(alpha=1/period, adjust=False).mean()
    avg_down = down.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_up / avg_down
    return 100 - (100 / (1 + rs))


def calc_macd(close, fast=12, slow=26, signal=9):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    sig = macd.ewm(span=signal, adjust=False).mean()
    hist = macd - sig
    return macd, sig, hist


def calc_bbands(close, period=20, std=2):
    sma = close.rolling(period).mean()
    sd = close.rolling(period).std()
    return sma + std * sd, sma, sma - std * sd


def calc_atr(high, low, close, period=14):
    """ATR (Average True Range) — ボラティリティ指標。
    SL/TP の幅を決めるのに使う。4H 足の自然な揺れを定量化。"""
    prev_close = close.shift(1)
    tr = pd.concat([
        (high - low),
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1/period, adjust=False).mean()


# ─────────────────────────────────────────────
# 🆕 2026-05-28: ADX + Choppiness Index（市況判定の本物指標）
# Step C で実装。signals-log に記録するが、当面はフィルタには使わない
# （N=139 検証では擬似指標で十分機能したため、本物指標は次回検証用）
# ─────────────────────────────────────────────
def adx_choppiness(high, low, close, period=14):
    """ADX (トレンド強度) + Choppiness Index (レンジ判定) を計算。
    返り値: (adx_series, choppiness_series)
    ADX ≥ 25 → トレンド、< 20 → レンジ
    Choppiness > 61.8 → レンジ、< 38.2 → トレンド
    """
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/period, adjust=False).mean()

    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    plus_di = 100 * pd.Series(plus_dm, index=high.index).ewm(alpha=1/period, adjust=False).mean() / atr
    minus_di = 100 * pd.Series(minus_dm, index=high.index).ewm(alpha=1/period, adjust=False).mean() / atr
    dx = (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan) * 100
    adx = dx.ewm(alpha=1/period, adjust=False).mean()

    tr_sum = tr.rolling(period).sum()
    high_n = high.rolling(period).max()
    low_n = low.rolling(period).min()
    range_n = (high_n - low_n).replace(0, np.nan)
    chop = 100 * np.log10(tr_sum / range_n) / np.log10(period)

    return adx, chop


def classify_regime(adx_val, chop_val, ma_dev_pct, ma_dir):
    """市況判定: range / trend_up / trend_down
    本物の ADX/Choppiness があれば優先、なければ MA 乖離率にフォールバック。
    検証 (N=139): MA 乖離率「大」区分で勝率 48.6% / レンジ区分で勝率 29%
    """
    # 本物の ADX/Choppiness 優先
    if adx_val is not None and not pd.isna(adx_val) and chop_val is not None and not pd.isna(chop_val):
        if adx_val >= 25 and chop_val < 38.2:
            return "trend_up" if ma_dir == "up" else "trend_down"
        if adx_val < 20 and chop_val > 61.8:
            return "range"
    # フォールバック: MA 乖離率（既存 indicators から計算可能）
    # 中央値 0.170% を閾値に
    if ma_dev_pct >= 0.17:
        return "trend_up" if ma_dir == "up" else "trend_down"
    return "range"


# ─────────────────────────────────────────────
# 🆕 2026-05-28: モメンタムスコア（Step A）
# 「人気・モメンタムが出ている銘柄を動的に拾う」設計の中核。
# 銘柄ブラックリストではなく動的判定でフィルタする。
# 検証 (N=139): 新案F の閾値で N=29 残・勝率 55.2%（vs 現状 32.4%）
# ─────────────────────────────────────────────
def calc_momentum_score(entry, direction, indicators):
    """既存 indicators から計算可能なモメンタムスコア（yfinance 不要）。
    direction: "long" / "short" or 日本語表記
    返り値 dict or None（欠損時）
    """
    if entry is None or direction is None or not indicators:
        return None
    dsign = 1 if (direction == "long" or "ロング" in str(direction) or "買い" in str(direction)) else -1
    ma25 = indicators.get("ma25")
    ma75 = indicators.get("ma75")
    rh = indicators.get("recent_high")
    rl = indicators.get("recent_low")
    if not all([ma25, ma75, rh, rl, entry]) or ma75 == 0 or rh == rl:
        return None
    ma_ratio = (ma25 - ma75) / ma75 * 100
    entry_vs_ma25 = (entry - ma25) / ma25 * 100
    range_pos = (entry - rl) / (rh - rl)
    score = (ma_ratio + entry_vs_ma25 + (range_pos - 0.5)) * dsign
    return {
        "score": round(score, 3),
        "ma_ratio_pct": round(ma_ratio, 3),
        "entry_vs_ma25_pct": round(entry_vs_ma25, 3),
        "entry_vs_ma25_signed": round(entry_vs_ma25 * dsign, 3),
        "range_pos": round(range_pos, 3),
        "direction_sign": dsign,
    }


def passes_momentum_filter(entry, direction, indicators):
    """新案F: entry_vs_ma25 × dsign > 0.5 OR score >= 1.0
    バックテスト (N=139): N=29 残、勝率 55.2%（現状 32.4%）。
    指標欠損時は安全側で False（メール送信スキップ、記録は残す）。
    返り値: (passes: bool, reason: str, momentum_dict: dict or None)
    """
    m = calc_momentum_score(entry, direction, indicators)
    if m is None:
        return False, "指標欠損のため安全側でスキップ", None
    if m["entry_vs_ma25_signed"] > 0.5:
        return True, f"entry vs MA25 {m['entry_vs_ma25_signed']:+.2f}% で順方向強", m
    if m["score"] >= 1.0:
        return True, f"momentum_score {m['score']:+.2f} で閾値超え", m
    return False, f"momentum 不足 (score={m['score']:+.2f}, entry_vs_ma25={m['entry_vs_ma25_signed']:+.2f}%)", m


# ─────────────────────────────────────────────
# 🆕 2026-05-28: チャートパターン認識 P1（自前ロジック、scipy 不要）
# ダブルトップ / ダブルボトム / 三角持ち合い を検出。
# ダブルトップ/ボトムは「反転型」のため、メイン側でモメンタムフィルタをバイパスする。
# ─────────────────────────────────────────────
def find_local_extrema(values, mode='peak', distance=5, min_prominence_pct=0.003):
    """ローカル極値（ピーク or 谷）を検出。scipy.signal.find_peaks の簡易版。
    mode: 'peak'（極大）or 'trough'（極小）
    distance: 検出する極値の最小間隔（バー数）
    min_prominence_pct: 周囲との値差の最小相対値（ノイズ除去用、0.3% デフォルト）
    返り値: インデックスのリスト
    """
    if values is None or len(values) < 3:
        return []
    arr = np.asarray(values, dtype=float)
    sign = 1 if mode == 'peak' else -1
    signed = arr * sign
    extrema = []
    for i in range(1, len(signed) - 1):
        if signed[i] > signed[i - 1] and signed[i] > signed[i + 1]:
            # prominence チェック（周囲 distance 内の最低値との差）
            if min_prominence_pct > 0 and abs(arr[i]) > 0:
                lo = max(0, i - distance)
                hi = min(len(signed), i + distance + 1)
                local_min = signed[lo:hi].min()
                if (signed[i] - local_min) / abs(arr[i]) < min_prominence_pct:
                    continue
            # 直前の極値から distance 以上離れているか
            if not extrema or i - extrema[-1] >= distance:
                extrema.append(i)
            elif signed[i] > signed[extrema[-1]]:
                # より高い極値なら置換
                extrema[-1] = i
    return extrema


def detect_double_top(highs, closes, lookback=40, tolerance_pct=0.5,
                       neckline_drop_pct=2.0, distance=4):
    """ダブルトップ検出（反転型シグナル）。
    条件:
      1. lookback 本以内に 2 つの高値ピークが close
      2. 2 つのピーク高値の差が tolerance_pct（%）以内
      3. 間の谷が両ピークから neckline_drop_pct（%）以上下
      4. 現在 close がネックライン（谷の最低値）を下抜け
    返り値: dict or None
    """
    if len(highs) < lookback + 5:
        return None
    recent_h = highs.iloc[-lookback:].values
    peaks = find_local_extrema(recent_h, mode='peak', distance=distance)
    if len(peaks) < 2:
        return None
    p1, p2 = peaks[-2], peaks[-1]
    h1, h2 = float(recent_h[p1]), float(recent_h[p2])
    if max(h1, h2) <= 0:
        return None
    # 2 つのピーク高値の近接判定
    diff_pct = abs(h1 - h2) / max(h1, h2) * 100
    if diff_pct > tolerance_pct:
        return None
    # 間の谷（ネックライン）
    neckline = float(recent_h[p1:p2 + 1].min())
    drop_pct = (min(h1, h2) - neckline) / min(h1, h2) * 100
    if drop_pct < neckline_drop_pct:
        return None
    # 現 close がネックライン下抜けしているか
    cur_close = float(closes.iloc[-1])
    if cur_close >= neckline:
        return None
    return {
        "peak1_value": round(h1, 5),
        "peak2_value": round(h2, 5),
        "neckline": round(neckline, 5),
        "peak_diff_pct": round(diff_pct, 3),
        "breakout_pct": round((cur_close - neckline) / neckline * 100, 3),
        "bars_apart": int(p2 - p1),
    }


def detect_double_bottom(lows, closes, lookback=40, tolerance_pct=0.5,
                          neckline_rise_pct=2.0, distance=4):
    """ダブルボトム検出（反転型シグナル）。detect_double_top の対称。"""
    if len(lows) < lookback + 5:
        return None
    recent_l = lows.iloc[-lookback:].values
    troughs = find_local_extrema(recent_l, mode='trough', distance=distance)
    if len(troughs) < 2:
        return None
    t1, t2 = troughs[-2], troughs[-1]
    l1, l2 = float(recent_l[t1]), float(recent_l[t2])
    if max(l1, l2) <= 0:
        return None
    diff_pct = abs(l1 - l2) / max(l1, l2) * 100
    if diff_pct > tolerance_pct:
        return None
    neckline = float(recent_l[t1:t2 + 1].max())
    rise_pct = (neckline - max(l1, l2)) / max(l1, l2) * 100
    if rise_pct < neckline_rise_pct:
        return None
    cur_close = float(closes.iloc[-1])
    if cur_close <= neckline:
        return None
    return {
        "trough1_value": round(l1, 5),
        "trough2_value": round(l2, 5),
        "neckline": round(neckline, 5),
        "trough_diff_pct": round(diff_pct, 3),
        "breakout_pct": round((cur_close - neckline) / neckline * 100, 3),
        "bars_apart": int(t2 - t1),
    }


def detect_first_pullback(highs, lows, closes, signals_log_recent, ticker, timeframe,
                            direction, ma25_cur, ma75_cur, now_jst,
                            pullback_window=15, retest_tolerance_pct=0.3,
                            min_overshoot_pct=1.0, ma_dev_gate_pct=0.5):
    """ブレイク後の初押し検出（順張りシグナル、long/short 兼用）。
    バックテスト N=10 で勝率 40%（単体）、+逆方向シグナルなし → 50%、+overshoot ≥1% → 100% (N=3)
    サンプル不足のため当面 email_silent=True で記録のみ。N=20-30 で評価。

    direction: "long" / "short"
    signals_log_recent: 同 ticker, 同 timeframe の直近シグナルリスト
    返り値: dict or None
    """
    if len(closes) < pullback_window + 5:
        return None
    if direction not in ("long", "short"):
        return None
    if ma75_cur is None or ma75_cur == 0:
        return None

    # トレンドゲート（MA 乖離率 ≥ 0.5%）
    ma_dev_pct = abs(ma25_cur - ma75_cur) / ma75_cur * 100
    if ma_dev_pct < ma_dev_gate_pct:
        return None
    # 順張り方向のみ
    ma_dir_up = ma25_cur > ma75_cur
    if direction == "long" and not ma_dir_up:
        return None
    if direction == "short" and ma_dir_up:
        return None

    # signals_log_recent から、ブレイクシグナル (high_break / low_break) を探す
    if not signals_log_recent:
        return None
    target_break_type = "high_break" if direction == "long" else "low_break"
    timeframe_hours = 4 if timeframe == "4h" else 1
    window_hours = pullback_window * timeframe_hours

    breakout_signal = None
    for s in reversed(signals_log_recent):  # 新しい順
        if s.get("ticker") != ticker or s.get("timeframe") != timeframe:
            continue
        sig_types = s.get("signal_types", [])
        if target_break_type not in sig_types:
            continue
        # 経過時間チェック
        try:
            fired = datetime.fromisoformat(s["fired_at"])
            if fired.tzinfo is None:
                fired = fired.replace(tzinfo=JST)
            hours_ago = (now_jst - fired).total_seconds() / 3600.0
        except Exception:
            continue
        if hours_ago > window_hours:
            break  # これより古いブレイクは対象外
        if hours_ago < timeframe_hours * 0.5:
            continue  # 直前すぎ（ブレイク即発火を避ける）
        breakout_signal = s
        break  # 直近のブレイクを採用

    if not breakout_signal:
        return None

    # 旧レジ/旧サポ（ブレイク時の recent_high / recent_low）
    ind_at_break = breakout_signal.get("indicators_at_signal", {})
    if direction == "long":
        old_level = ind_at_break.get("recent_high")
    else:
        old_level = ind_at_break.get("recent_low")
    if not old_level or old_level <= 0:
        return None

    # ブレイク後の overshoot 確認（直近 pullback_window 本の最高値 or 最安値）
    recent_h = float(highs.iloc[-pullback_window:].max())
    recent_l = float(lows.iloc[-pullback_window:].min())
    if direction == "long":
        overshoot_pct = (recent_h - old_level) / old_level * 100
    else:
        overshoot_pct = (old_level - recent_l) / old_level * 100
    if overshoot_pct < min_overshoot_pct:
        return None

    # 現 close が旧レジ/旧サポ付近に戻ってきたか
    cur_close = float(closes.iloc[-1])
    distance_pct = abs(cur_close - old_level) / old_level * 100
    if distance_pct > retest_tolerance_pct:
        return None

    # 直近 3 本でロールリバーサル成立しているか（ロング: 旧レジを大きく下抜けていない）
    if direction == "long":
        recent_min_low = float(lows.iloc[-3:].min())
        if recent_min_low < old_level * (1 - retest_tolerance_pct / 100 * 1.5):
            return None
    else:
        recent_max_high = float(highs.iloc[-3:].max())
        if recent_max_high > old_level * (1 + retest_tolerance_pct / 100 * 1.5):
            return None

    # 二重発火防止: ブレイク以降、first_pullback がまだ発火していないか
    try:
        break_fired = datetime.fromisoformat(breakout_signal["fired_at"])
        if break_fired.tzinfo is None:
            break_fired = break_fired.replace(tzinfo=JST)
    except Exception:
        break_fired = None
    target_pb_type = "first_pullback_long" if direction == "long" else "first_pullback_short"
    if break_fired:
        for s in signals_log_recent:
            if s.get("ticker") != ticker or s.get("timeframe") != timeframe:
                continue
            if target_pb_type not in s.get("signal_types", []):
                continue
            try:
                pb_fired = datetime.fromisoformat(s["fired_at"])
                if pb_fired.tzinfo is None:
                    pb_fired = pb_fired.replace(tzinfo=JST)
                if pb_fired > break_fired:
                    return None  # 既に発火済み
            except Exception:
                continue

    # 逆方向シグナルなしチェック（ブレイク以降、反対方向のシグナルが出ていないか）
    opposite_break_type = "low_break" if direction == "long" else "high_break"
    if break_fired:
        for s in signals_log_recent:
            if s.get("ticker") != ticker or s.get("timeframe") != timeframe:
                continue
            try:
                s_fired = datetime.fromisoformat(s["fired_at"])
                if s_fired.tzinfo is None:
                    s_fired = s_fired.replace(tzinfo=JST)
                if s_fired <= break_fired:
                    continue
            except Exception:
                continue
            if opposite_break_type in s.get("signal_types", []):
                return None  # 逆方向ブレイク出てるのでロールリバーサル無効

    # hours_since_break を安全に計算
    try:
        _bf = datetime.fromisoformat(breakout_signal["fired_at"])
        if _bf.tzinfo is None:
            _bf = _bf.replace(tzinfo=JST)
        hours_since_break = round((now_jst - _bf).total_seconds() / 3600, 1)
    except Exception:
        hours_since_break = None

    return {
        "old_level": round(old_level, 5),
        "current_close": round(cur_close, 5),
        "distance_pct": round(distance_pct, 3),
        "overshoot_pct": round(overshoot_pct, 2),
        "ma_dev_pct": round(ma_dev_pct, 3),
        "breakout_fired_at": breakout_signal["fired_at"],
        "hours_since_break": hours_since_break,
        "regime_at_signal": "trend_up" if direction == "long" else "trend_down",
    }


def detect_triangle_squeeze(highs, lows, bb_up_series, bb_low_series, lookback=20,
                              bb_width_ratio_threshold=0.7):
    """三角持ち合い（シンメトリカル）検出。中立シグナル（ブレイク待ち）。
    条件:
      1. 直近 lookback 本の高値の傾きが負（高値切り下げ）
      2. 直近 lookback 本の安値の傾きが正（安値切り上げ）
      3. BB 幅が直近平均の 70% 以下に収縮
    """
    if len(highs) < lookback + 5:
        return None
    recent_h = highs.iloc[-lookback:].values
    recent_l = lows.iloc[-lookback:].values
    x = np.arange(lookback, dtype=float)
    try:
        h_slope = float(np.polyfit(x, recent_h, 1)[0])
        l_slope = float(np.polyfit(x, recent_l, 1)[0])
    except (np.linalg.LinAlgError, ValueError):
        return None
    if not (h_slope < 0 and l_slope > 0):
        return None
    # BB 幅縮小チェック
    cur_bb_width = float(bb_up_series.iloc[-1] - bb_low_series.iloc[-1])
    avg_bb_width = float((bb_up_series.iloc[-lookback:] - bb_low_series.iloc[-lookback:]).mean())
    if avg_bb_width <= 0:
        return None
    bb_width_ratio = cur_bb_width / avg_bb_width
    if bb_width_ratio > bb_width_ratio_threshold:
        return None
    return {
        "h_slope": round(h_slope, 6),
        "l_slope": round(l_slope, 6),
        "bb_width_ratio": round(bb_width_ratio, 3),
        "lookback": lookback,
    }


# ─────────────────────────────────────────────
# SL/TP をシグナル方向と ATR から算出
# ─────────────────────────────────────────────
def calc_entry_sl_tp(current_price, atr_value, direction):
    """ATR ベースで参考エントリー・SL・TP を算出。
    direction: "long" or "short"
    R:R = 1:1.3（TP1）, 1:2.0（TP2）
    SL 幅 = ATR × 1.5（4H 足の自然な揺れの 1.5 倍）"""
    sl_dist = atr_value * 1.5
    tp1_dist = atr_value * 2.0
    tp2_dist = atr_value * 3.0
    if direction == "long":
        return {
            "direction": "ロング（買い）",
            "entry": current_price,
            "stop_loss": current_price - sl_dist,
            "take_profit_1": current_price + tp1_dist,
            "take_profit_2": current_price + tp2_dist,
            "sl_pct": -(sl_dist / current_price) * 100,
            "tp1_pct": (tp1_dist / current_price) * 100,
            "tp2_pct": (tp2_dist / current_price) * 100,
            "atr": atr_value,
        }
    else:  # short
        return {
            "direction": "ショート（売り）",
            "entry": current_price,
            "stop_loss": current_price + sl_dist,
            "take_profit_1": current_price - tp1_dist,
            "take_profit_2": current_price - tp2_dist,
            "sl_pct": (sl_dist / current_price) * 100,
            "tp1_pct": -(tp1_dist / current_price) * 100,
            "tp2_pct": -(tp2_dist / current_price) * 100,
            "atr": atr_value,
        }


def determine_direction(signals):
    """発火シグナル群から総合的にロング/ショート/中立を判定。
    buy 多数 → long、sell 多数 → short、その他 → None"""
    buy_count = sum(1 for s in signals if s["severity"] == "buy")
    sell_count = sum(1 for s in signals if s["severity"] == "sell")
    if buy_count > sell_count:
        return "long"
    elif sell_count > buy_count:
        return "short"
    else:
        return None  # warn のみ等 → ポジション提案なし


# ─────────────────────────────────────────────
# シグナル判定（4H 足の最新バーを評価）
# 返り値: list of dict [{type, severity, label, detail}, ...]
# ─────────────────────────────────────────────
def detect_fib_pullback(high, low, close, atr_cur, fundamental_bias,
                        lookback=40, gp_lo=0.50, gp_hi=0.66, min_impulse_atr=3.0):
    """🆕 2026-06-01 ファンダ整合フィボ押し目（ゴールデンポケット 50〜61.8%）検出。
    fundamental_bias='BULLISH'→押し目買い(long)、'BEARISH'→戻り売り(short)、その他→None。
    直近の上昇(下降)インパルスの 50〜61.8% リトレースに現値が到達したら発火（ファンダ方向と一致時のみ）。
    インパルスは ≥3×ATR を要求し、ノイズの小さな押しは除外。モメンタムフィルタはメイン側でバイパス。"""
    if fundamental_bias not in ("BULLISH", "BEARISH"):
        return None
    if atr_cur is None or atr_cur <= 0:
        return None
    if close is None or len(close) < lookback + 2:
        return None
    h = [float(x) for x in high.iloc[-lookback:]]
    l = [float(x) for x in low.iloc[-lookback:]]
    price = float(close.iloc[-1])
    last = lookback - 1

    if fundamental_bias == "BULLISH":
        ih = max(range(lookback), key=lambda i: h[i])   # スイング高値の位置
        if ih < 5 or ih > last - 1:                      # 高値の後に押し（バー）が必要
            return None
        swing_high = h[ih]
        swing_low = min(l[:ih])                          # 高値より前の最安値＝インパルス起点
        impulse = swing_high - swing_low
        if impulse <= 0 or impulse < min_impulse_atr * atr_cur:
            return None
        if not (swing_low < price < swing_high):
            return None
        retr = (swing_high - price) / impulse
        if not (gp_lo <= retr <= gp_hi):
            return None
        direction = "long"
        fib_500 = swing_high - 0.500 * impulse
        fib_618 = swing_high - 0.618 * impulse
    else:  # BEARISH
        il = min(range(lookback), key=lambda i: l[i])    # スイング安値の位置
        if il < 5 or il > last - 1:
            return None
        swing_low = l[il]
        swing_high = max(h[:il])                          # 安値より前の最高値＝下降インパルス起点
        impulse = swing_high - swing_low
        if impulse <= 0 or impulse < min_impulse_atr * atr_cur:
            return None
        if not (swing_low < price < swing_high):
            return None
        retr = (price - swing_low) / impulse
        if not (gp_lo <= retr <= gp_hi):
            return None
        direction = "short"
        fib_500 = swing_low + 0.500 * impulse
        fib_618 = swing_low + 0.618 * impulse

    return {
        "direction": direction,
        "fib_pct": "61.8%" if retr >= 0.559 else "50%",
        "retr_pct": round(retr * 100, 1),
        "swing_high": round(swing_high, 4),
        "swing_low": round(swing_low, 4),
        "fib_500": round(fib_500, 4),
        "fib_618": round(fib_618, 4),
        "price": round(price, 4),
        "impulse_atr": round(impulse / atr_cur, 1),
    }


def detect_signals(df_4h, signals_log_recent=None, ticker=None, timeframe="4h", now_jst=None,
                   fundamental_bias=None):
    """
    signals_log_recent: 同 ticker, 同 timeframe の直近シグナルリスト（初押し検出用、オプショナル）
    ticker / timeframe / now_jst: 初押し検出用コンテキスト
    fundamental_bias: 'BULLISH'/'BEARISH'/None（フィボ押し目シグナルのファンダゲート）
    """
    if df_4h is None or len(df_4h) < 30:
        return []
    close = df_4h["Close"]
    high = df_4h["High"]
    low = df_4h["Low"]
    signals = []

    rsi = calc_rsi(close)
    macd, sig_line, hist = calc_macd(close)
    bb_up, bb_mid, bb_low = calc_bbands(close)
    ma25 = close.rolling(25).mean()
    ma75 = close.rolling(75).mean()
    atr = calc_atr(high, low, close)
    # 🆕 2026-05-28: ADX / Choppiness Index（市況判定の本物指標、当面は記録のみ）
    adx_series, chop_series = adx_choppiness(high, low, close)

    cur = close.iloc[-1]
    prev = close.iloc[-2]
    rsi_cur = rsi.iloc[-1]
    rsi_prev = rsi.iloc[-2]
    macd_cur, macd_prev = macd.iloc[-1], macd.iloc[-2]
    sig_cur, sig_prev = sig_line.iloc[-1], sig_line.iloc[-2]
    bb_low_cur = bb_low.iloc[-1]
    bb_up_cur = bb_up.iloc[-1]
    ma25_cur, ma25_prev = ma25.iloc[-1], ma25.iloc[-2]
    ma75_cur, ma75_prev = ma75.iloc[-1], ma75.iloc[-2]

    # RSI 過売り反発（30 割れ → 上昇）
    if rsi_prev < 30 and rsi_cur > rsi_prev and rsi_cur < 50:
        signals.append({
            "type": "rsi_oversold_bounce",
            "severity": "buy",
            "label": "🟢 RSI 過売り反発（押し目買い候補）",
            "detail": f"RSI {rsi_prev:.1f} → {rsi_cur:.1f}、過売りから反発開始",
        })

    # RSI 過買い警戒（70 突破）
    if rsi_prev <= 70 and rsi_cur > 70:
        signals.append({
            "type": "rsi_overbought",
            "severity": "warn",
            "label": "🟡 RSI 過買い（利確検討）",
            "detail": f"RSI {rsi_prev:.1f} → {rsi_cur:.1f}、過熱感",
        })

    # MACD ゴールデンクロス
    if macd_prev <= sig_prev and macd_cur > sig_cur:
        signals.append({
            "type": "macd_golden",
            "severity": "buy",
            "label": "🟢 MACD ゴールデンクロス（短期上昇転換）",
            "detail": f"MACD {macd_cur:.4f} がシグナル線を上抜け",
        })

    # MACD デッドクロス
    if macd_prev >= sig_prev and macd_cur < sig_cur:
        signals.append({
            "type": "macd_dead",
            "severity": "sell",
            "label": "🔴 MACD デッドクロス（短期下降転換）",
            "detail": f"MACD {macd_cur:.4f} がシグナル線を下抜け",
        })

    # MA ゴールデンクロス（25 > 75）
    if ma25_prev <= ma75_prev and ma25_cur > ma75_cur:
        signals.append({
            "type": "ma_golden",
            "severity": "buy",
            "label": "🟢 移動平均ゴールデンクロス（中期上昇入り）",
            "detail": f"25MA が 75MA を上抜け",
        })

    # MA デッドクロス
    if ma25_prev >= ma75_prev and ma25_cur < ma75_cur:
        signals.append({
            "type": "ma_dead",
            "severity": "sell",
            "label": "🔴 移動平均デッドクロス（中期下降入り）",
            "detail": f"25MA が 75MA を下抜け",
        })

    # 🆕 2026-05-28: BB 内の位置（0=下端、1=上端）を計算
    bb_width = bb_up_cur - bb_low_cur
    bb_pos = (cur - bb_low_cur) / bb_width if bb_width > 0 else 0.5

    # ボリンジャー -2σ タッチ（反発期待）
    # 🆕 2026-05-28: bb_pos < 0.3 必須（検証で 35% が上半分で発火、勝率 13% のバグ修正）
    if low.iloc[-1] <= bb_low_cur and cur > low.iloc[-1] and bb_pos < 0.3:
        signals.append({
            "type": "bb_lower_touch",
            "severity": "buy",
            "label": "🟢 ボリンジャー -2σ タッチ（反発期待）",
            "detail": f"-2σ ({bb_low_cur:.2f}) に接触後、反発の兆し（BB 位置 {bb_pos:.2f}）",
        })

    # ボリンジャー +2σ 突破（過熱）
    # 🆕 2026-05-28: bb_pos > 0.7 必須（バグ対称、過熱判定の精度向上）
    if cur > bb_up_cur and prev <= bb_up_cur and bb_pos > 0.7:
        signals.append({
            "type": "bb_upper_break",
            "severity": "warn",
            "label": "🟡 ボリンジャー +2σ 突破（過熱注意）",
            "detail": f"+2σ ({bb_up_cur:.2f}) を上抜け（BB 位置 {bb_pos:.2f}）",
        })

    # 直近 20 本高値ブレイク
    recent_high = high.iloc[-21:-1].max()
    if cur > recent_high:
        signals.append({
            "type": "high_break",
            "severity": "buy",
            "label": "🟢 直近 20 本高値ブレイク（トレンド継続）",
            "detail": f"直近高値 {recent_high:.2f} を上抜け",
        })

    # 直近 20 本安値割れ
    recent_low = low.iloc[-21:-1].min()
    if cur < recent_low:
        signals.append({
            "type": "low_break",
            "severity": "sell",
            "label": "🔴 直近 20 本安値割れ（損切りライン）",
            "detail": f"直近安値 {recent_low:.2f} を下抜け",
        })

    # 🆕 2026-05-28: チャートパターン認識 P1（ダブルトップ / ダブルボトム / 三角持ち合い）
    # ダブルトップ/ボトムは反転型シグナル → メイン側でモメンタムフィルタをバイパス
    dt = detect_double_top(high, close, lookback=40)
    if dt:
        signals.append({
            "type": "double_top",
            "severity": "sell",
            "label": "🔴 ダブルトップ完成（ネックライン割れ）",
            "detail": (
                f"2 高値 {dt['peak1_value']:.4f}/{dt['peak2_value']:.4f}（差 {dt['peak_diff_pct']:.2f}%）、"
                f"ネックライン {dt['neckline']:.4f} 下抜け {dt['breakout_pct']:+.2f}%"
            ),
            "is_reversal_pattern": True,
            "pattern_data": dt,
        })

    db = detect_double_bottom(low, close, lookback=40)
    if db:
        signals.append({
            "type": "double_bottom",
            "severity": "buy",
            "label": "🟢 ダブルボトム完成（ネックライン突破）",
            "detail": (
                f"2 安値 {db['trough1_value']:.4f}/{db['trough2_value']:.4f}（差 {db['trough_diff_pct']:.2f}%）、"
                f"ネックライン {db['neckline']:.4f} 上抜け {db['breakout_pct']:+.2f}%"
            ),
            "is_reversal_pattern": True,
            "pattern_data": db,
        })

    ts = detect_triangle_squeeze(high, low, bb_up, bb_low, lookback=20)
    if ts:
        signals.append({
            "type": "triangle_squeeze",
            "severity": "warn",
            "label": "🟡 三角持ち合い収束中（ブレイク待ち）",
            "detail": (
                f"高値傾き {ts['h_slope']:+.4f}、安値傾き {ts['l_slope']:+.4f}、"
                f"BB 幅比 {ts['bb_width_ratio']:.2f}（収束）"
            ),
            "is_reversal_pattern": False,
            "pattern_data": ts,
        })

    # 🆕 2026-05-28: 初押しシグナル（順張り、ブレイク後の初回戻り）
    # signals_log_recent が渡された場合のみ判定。サンプル不足のため email_silent=True で記録のみ
    # バックテスト: 基本条件 N=10 で 40%、+overshoot=1% で N=3 で 100%（小サンプル注意）
    if signals_log_recent is not None and ticker and now_jst:
        for direction in ("long", "short"):
            fp = detect_first_pullback(
                high, low, close, signals_log_recent, ticker, timeframe,
                direction, ma25_cur, ma75_cur, now_jst,
                pullback_window=15, retest_tolerance_pct=0.3,
                min_overshoot_pct=1.0, ma_dev_gate_pct=0.5,
            )
            if fp:
                # 体制ラベル（バックテストでトレンド地合いの方が勝率良い）
                regime_label = "トレンド継続" if abs(fp["ma_dev_pct"]) >= 1.0 else "弱トレンド"
                signal_type = "first_pullback_long" if direction == "long" else "first_pullback_short"
                emoji = "🟢" if direction == "long" else "🔴"
                arrow = "上抜け" if direction == "long" else "下抜け"
                signals.append({
                    "type": signal_type,
                    "severity": "buy" if direction == "long" else "sell",
                    "label": f"{emoji} 初押し（{regime_label}・ブレイク後 {fp['hours_since_break']:.0f}h で旧{'レジ' if direction == 'long' else 'サポ'}リテスト）",
                    "detail": (
                        f"ブレイク後 {fp['overshoot_pct']:+.2f}% {arrow}、現在価格 {fp['current_close']:.4f} が"
                        f"旧水準 {fp['old_level']:.4f} に戻り（距離 {fp['distance_pct']:.2f}%）、"
                        f"MA 乖離 {fp['ma_dev_pct']:+.3f}%"
                    ),
                    "is_reversal_pattern": False,
                    "email_silent": True,  # 🚫 N=20-30 まで蓄積、メール送信は当面 OFF
                    "pattern_data": fp,
                })

    # 🆕 2026-06-01: ファンダ整合フィボ押し目（ゴールデンポケット 50-61.8%・両方向・メールON）
    #   fundamental-context の方向（強気/弱気・HIGH/MID確信度のみ main 側で渡す）と一致する押し目で発火。
    #   押し目は短期モメンタムに逆らうため、メイン側で bypass_momentum によりフィルタをバイパスする。
    if fundamental_bias in ("BULLISH", "BEARISH"):
        fbk = detect_fib_pullback(high, low, close, atr.iloc[-1], fundamental_bias)
        if fbk:
            _is_long = fbk["direction"] == "long"
            signals.append({
                "type": "fib_pullback_long" if _is_long else "fib_pullback_short",
                "severity": "buy" if _is_long else "sell",
                "label": (f"{'🟢' if _is_long else '🔴'} ファンダ{'強気' if _is_long else '弱気'}×フィボ{fbk['fib_pct']}"
                          f"{'押し目（押し目買い候補）' if _is_long else '戻り（戻り売り候補）'}"),
                "detail": (
                    f"{'上昇' if _is_long else '下降'}インパルス {fbk['swing_low']}〜{fbk['swing_high']}"
                    f"（{fbk['impulse_atr']}×ATR）の {fbk['fib_pct']}（戻し {fbk['retr_pct']}%）に到達。"
                    f"現値 {fbk['price']}／フィボ 50%={fbk['fib_500']}・61.8%={fbk['fib_618']}。"
                    f"ファンダ方向（{fundamental_bias}）と整合の押し目。"
                ),
                "is_reversal_pattern": False,
                "bypass_momentum": True,
                "pattern_data": fbk,
            })

    # 🆕 2026-05-28: 市況判定（ADX/Choppiness + MA 乖離率フォールバック）
    adx_cur = float(adx_series.iloc[-1]) if not pd.isna(adx_series.iloc[-1]) else None
    chop_cur = float(chop_series.iloc[-1]) if not pd.isna(chop_series.iloc[-1]) else None
    ma_dev_pct = abs(ma25_cur - ma75_cur) / ma75_cur * 100 if ma75_cur else 0.0
    ma_dir = "up" if ma25_cur > ma75_cur else "down"
    regime = classify_regime(adx_cur, chop_cur, ma_dev_pct, ma_dir)

    return signals, {
        "price": cur,
        "rsi": rsi_cur,
        "macd": macd_cur,
        "macd_sig": sig_cur,
        "bb_up": bb_up_cur,
        "bb_low": bb_low_cur,
        "ma25": ma25_cur,
        "ma75": ma75_cur,
        "recent_high": recent_high,
        "recent_low": recent_low,
        "atr": float(atr.iloc[-1]) if not pd.isna(atr.iloc[-1]) else 0.0,
        # 🆕 2026-05-28
        "adx": adx_cur,
        "chop": chop_cur,
        "ma_dev_pct": round(ma_dev_pct, 4),
        "ma_dir": ma_dir,
        "regime": regime,
    }


# ─────────────────────────────────────────────
# yfinance でティッカー関連ニュースを取得（ファンダ参考用）
# ─────────────────────────────────────────────
def fetch_ticker_news(ticker, max_items=5):
    """ティッカー関連の直近ニュース見出しを取得"""
    try:
        news = yf.Ticker(ticker).news or []
    except Exception as e:
        print(f"    ⚠️ {ticker} news 取得失敗: {type(e).__name__}: {str(e)[:60]}")
        return []
    titles = []
    for n in news[:max_items * 2]:  # 余分に取って fall back 可能性に備える
        # yfinance 新旧フォーマット両対応
        content = n.get("content", n)
        title = content.get("title", "") or n.get("title", "")
        if title and title not in titles:
            titles.append(title)
        if len(titles) >= max_items:
            break
    return titles


# ─────────────────────────────────────────────
# 🆕 通貨強弱分析（Currency Strength Index）
# ─────────────────────────────────────────────
# FX ペアと通貨の対応マップ（pair: (base, quote)）
# 例: EURJPY=X は base=EUR, quote=JPY → EUR/JPY 上昇 = EUR 強・JPY 弱
FX_PAIR_MAP = {
    "USDJPY=X": ("USD", "JPY"),
    "EURJPY=X": ("EUR", "JPY"),
    "GBPJPY=X": ("GBP", "JPY"),
    "AUDJPY=X": ("AUD", "JPY"),
    "EURUSD=X": ("EUR", "USD"),
    "GBPUSD=X": ("GBP", "USD"),
    "AUDUSD=X": ("AUD", "USD"),
    "EURAUD=X": ("EUR", "AUD"),
    "GBPAUD=X": ("GBP", "AUD"),
}


def calc_pair_change_24h(ticker, period="3d"):
    """指定 FX ペアの 24h 変動率（%）を計算"""
    try:
        df = yf.download(ticker, period=period, interval="1h", progress=False, auto_adjust=True)
        if df.empty or len(df) < 24:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        # 直近 24 本前と最新の比較
        latest = float(df["Close"].iloc[-1])
        prev = float(df["Close"].iloc[-24])
        if prev == 0:
            return None
        return round((latest - prev) / prev * 100, 3)
    except Exception:
        return None


def calc_currency_strength():
    """全 FX ペアの 24h 変動率から、各通貨（USD/EUR/GBP/JPY/AUD）の総合強弱を算出。
    返り値: {USD: +0.42, EUR: -0.10, ...} 単位は %"""
    pair_changes = {}
    for pair_ticker in FX_PAIR_MAP.keys():
        ch = calc_pair_change_24h(pair_ticker)
        if ch is not None:
            pair_changes[pair_ticker] = ch

    if not pair_changes:
        return None

    # 各通貨に対して、base のときは +変動率、quote のときは -変動率を集計
    currency_scores = {"USD": [], "EUR": [], "GBP": [], "JPY": [], "AUD": []}
    for pair, change in pair_changes.items():
        base, quote = FX_PAIR_MAP[pair]
        if base in currency_scores:
            currency_scores[base].append(change)
        if quote in currency_scores:
            currency_scores[quote].append(-change)  # 後者は逆相関

    # 平均
    result = {}
    for cur, scores in currency_scores.items():
        if scores:
            result[cur] = round(sum(scores) / len(scores), 3)
        else:
            result[cur] = None

    return result


def format_currency_strength(strength):
    """通貨強弱を文字列で整形（ランキング表示用）"""
    if not strength:
        return ""
    # None でないもののみソート
    valid = [(c, v) for c, v in strength.items() if v is not None]
    valid.sort(key=lambda x: -x[1])
    rank_emoji = ["🥇", "🥈", "🥉", "4位", "5位"]
    lines = ["【💪 通貨強弱（24h）】"]
    for i, (cur, val) in enumerate(valid):
        emoji = rank_emoji[i] if i < len(rank_emoji) else f"{i+1}位"
        marker = ""
        if i == 0 and val > 0.3:
            marker = "  ⭐ 強い"
        elif i == len(valid) - 1 and val < -0.3:
            marker = "  ⚠️ 弱い"
        lines.append(f"  {emoji} {cur}  {val:+.2f}%{marker}")
    return "\n".join(lines) + "\n"


# ─────────────────────────────────────────────
# 🆕 2026-05-29 Phase1: トップダウン層（Layer0 リスク環境 / Layer1 方向バイアス）
# 記録のみ。メール挙動・発火判断は一切変えない。検証用フィールドを signals-log に追加するだけ。
# 詳細仕様: SIGNAL_REDESIGN.md
# ─────────────────────────────────────────────

# Layer1 資産分類（リスク資産＝オンで強気、安全資産＝オフで強気）
RISK_ASSETS = {"ES=F", "NQ=F", "YM=F", "NKD=F", "^FTSE", "BTC-USD", "CL=F"}
SAFE_ASSETS = {"GC=F"}  # 金。円・ドルは FX 側（通貨強弱）で扱う


def fetch_5d_return(ticker):
    """直近約5営業日リターン(%)。Layer0 の金vs株比較用。失敗時 None。"""
    try:
        df = yf.download(ticker, period="7d", interval="1d", progress=False, auto_adjust=True)
        if df is None or df.empty or len(df) < 2:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        c = df["Close"].dropna()
        if len(c) < 2 or float(c.iloc[0]) == 0:
            return None
        return round((float(c.iloc[-1]) - float(c.iloc[0])) / float(c.iloc[0]) * 100, 2)
    except Exception:
        return None


def assess_risk_regime(currency_strength, vix):
    """Layer0: リスクオン/オフを合成スコアで判定（市場共通スナップショット、1回/run）。
    入力は既存の通貨強弱 + VIX + 金/株5日リターン。危機KWは Layer3(env) で別途処理。
    返り値: {regime: RISK_ON/NEUTRAL/RISK_OFF, score: int, factors: [str]}"""
    score = 0
    factors = []
    # 1. VIX 水準・方向
    if vix and vix.get("current") is not None:
        v = vix["current"]
        if v < 15:
            score += 2; factors.append(f"VIX {v} <15 (+2)")
        elif v <= 20:
            factors.append(f"VIX {v} 中立 (0)")
        elif v <= 25:
            score -= 1; factors.append(f"VIX {v} 高 (-1)")
        else:
            score -= 2; factors.append(f"VIX {v} >25 (-2)")
        ch = vix.get("change_24h_pct")
        if ch is not None and ch >= 20:
            score -= 1; factors.append(f"VIX急騰 +{ch}% (-1)")
    # 2. 通貨強弱（豪ドル=リスクオン通貨 / 円・ドル=安全通貨）
    if currency_strength:
        aud = currency_strength.get("AUD")
        safe = [x for x in (currency_strength.get("JPY"), currency_strength.get("USD")) if x is not None]
        if aud is not None and safe:
            diff = aud - (sum(safe) / len(safe))
            if diff >= 0.10:
                score += 1; factors.append(f"豪ドル優位 (+1)")
            elif diff <= -0.10:
                score -= 1; factors.append(f"円・ドル優位 (-1)")
    # 3. 金 vs 株（5日リターン差、株優位=オン / 金優位=オフ）
    gold = fetch_5d_return("GC=F")
    eq = fetch_5d_return("ES=F")
    if gold is not None and eq is not None:
        d = eq - gold
        if d >= 1.0:
            score += 1; factors.append(f"株>金 5d {d:+.1f}pt (+1)")
        elif d <= -1.0:
            score -= 1; factors.append(f"金>株 5d {d:+.1f}pt (-1)")
    if score >= 2:
        regime = "RISK_ON"
    elif score <= -2:
        regime = "RISK_OFF"
    else:
        regime = "NEUTRAL"
    return {"regime": regime, "score": score, "factors": factors}


def assess_directional_bias(ticker, regime, signal_direction):
    """Layer1: その銘柄で許可される方向と、発火シグナルが一致しているか（記録のみ）。
    signal_direction: 'long'/'short'/'neutral'
    返り値: {asset_class, regime, allowed, signal_direction, aligned}
      aligned=True  → バイアスと一致（本稼働時は通過候補）
      aligned=False → バイアス逆行（本稼働時は抑制候補）
      aligned=None  → FX/中立など Phase1 では判定保留"""
    if ticker in RISK_ASSETS:
        acls = "risk"
    elif ticker in SAFE_ASSETS:
        acls = "safe"
    elif ticker in FX_PAIR_MAP:
        acls = "fx"
    else:
        acls = "other"

    allowed = None
    if regime == "RISK_ON":
        if acls == "risk":
            allowed = "long"
        elif acls == "safe":
            allowed = "short_or_neutral"
    elif regime == "RISK_OFF":
        if acls == "risk":
            allowed = "short"
        elif acls == "safe":
            allowed = "long"
    # FX と NEUTRAL は通貨強弱/上位足準拠（既存 fx_alignment / trend_alignment が担当）→ Phase1 は保留

    aligned = None
    if allowed in ("long", "short") and signal_direction in ("long", "short"):
        aligned = (allowed == signal_direction)

    return {
        "asset_class": acls,
        "regime": regime,
        "allowed": allowed,
        "signal_direction": signal_direction,
        "aligned": aligned,
    }


# 🆕 2026-05-29 L2: ファンダ・ブリーフィング（fundamental-context.json）連携
# Claude の多サブエージェント・ブリーフィングが生成した信頼度検証済みの方向観を読み込み、
# Layer0/1 の「厚い」入力として使う。当面は記録のみ（発火には未使用）。不在/鮮度切れは None。
FUNDAMENTAL_CONTEXT_FILE = "fundamental-context.json"


def load_fundamental_context(max_age_hours=30):
    """fundamental-context.json を読み込む。鮮度切れ/不在/壊れは None を返す（計算regimeにフォールバック）。"""
    try:
        with open(FUNDAMENTAL_CONTEXT_FILE, encoding="utf-8") as f:
            ctx = json.load(f)
    except Exception:
        return None
    gen = ctx.get("generated_at")
    gdt = None
    if gen:
        try:
            gdt = datetime.fromisoformat(gen)
        except Exception:
            try:
                gdt = datetime.strptime(gen, "%Y-%m-%d")
            except Exception:
                gdt = None
    if gdt is not None:
        if gdt.tzinfo is None:
            gdt = gdt.replace(tzinfo=JST)
        age_h = (datetime.now(JST) - gdt).total_seconds() / 3600
        if age_h > max_age_hours:
            print(f"  ⚠️ fundamental-context.json 鮮度切れ（{age_h:.0f}h 前）→ 計算 regime にフォールバック")
            return None
    # 資産バイアス lookup（FX の =X を除去して正規化: USDJPY=X ⇔ USDJPY）
    ctx["_bias_map"] = {
        (a.get("ticker") or "").replace("=X", ""): a
        for a in ctx.get("assets", []) if a.get("ticker")
    }
    return ctx


def briefing_bias_for(ctx, ticker):
    """ブリーフィングから該当銘柄の資産エントリを返す（無ければ None）。"""
    if not ctx:
        return None
    return ctx.get("_bias_map", {}).get((ticker or "").replace("=X", ""))


def evaluate_currency_strength_alignment(ticker, position_direction, strength):
    """シグナルが通貨強弱とアラインしているか判定。
    例: AUDJPY ロング → AUD 強 + JPY 弱 なら "順張り"、逆なら "逆張り"
    返り値: dict {aligned: True/False/None, explanation, suggested_direction}"""
    if not strength or ticker not in FX_PAIR_MAP or not position_direction:
        return None
    base, quote = FX_PAIR_MAP[ticker]
    base_str = strength.get(base)
    quote_str = strength.get(quote)
    if base_str is None or quote_str is None:
        return None

    # 強弱差
    strength_diff = base_str - quote_str  # 正なら base 強 = ペア上昇圧力
    current_sign = _direction_str_to_sign(position_direction)

    if abs(strength_diff) < 0.2:
        return {
            "aligned": None,
            "explanation": f"💪 {base}/{quote} 強弱差は小さい（{strength_diff:+.2f}%、中立）",
            "suggested_direction": None,
        }

    expected_sign = 1 if strength_diff > 0 else -1  # 強弱差から想定方向
    aligned = expected_sign == current_sign

    if aligned:
        explanation = (f"✅ {base} {'強' if base_str > 0 else '弱'}（{base_str:+.2f}%）× "
                       f"{quote} {'強' if quote_str > 0 else '弱'}（{quote_str:+.2f}%）"
                       f" → 通貨強弱もシグナル方向と一致（複合順張り）")
    else:
        explanation = (f"⚠️ {base} {'強' if base_str > 0 else '弱'}（{base_str:+.2f}%）× "
                       f"{quote} {'強' if quote_str > 0 else '弱'}（{quote_str:+.2f}%）"
                       f" → 通貨強弱はシグナルと逆方向（複合逆張りで要警戒）")

    return {
        "aligned": aligned,
        "explanation": explanation,
        "strength_diff": round(strength_diff, 3),
        "base_strength": base_str,
        "quote_strength": quote_str,
    }


# ─────────────────────────────────────────────
# 🆕 AUD ペア専用 中国情勢フォーカス
# ─────────────────────────────────────────────
def fetch_china_market_data():
    """上海総合・ハンセン指数の現状と 24h 変動を取得"""
    indices = {
        "000001.SS": "上海総合指数",
        "^HSI": "香港ハンセン指数",
    }
    result = {}
    for ticker, name in indices.items():
        try:
            df = yf.download(ticker, period="5d", interval="1d", progress=False, auto_adjust=True)
            if df.empty or len(df) < 2:
                continue
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            latest = float(df["Close"].iloc[-1])
            prev = float(df["Close"].iloc[-2])
            change_pct = (latest - prev) / prev * 100 if prev else 0
            result[ticker] = {
                "name": name,
                "current": round(latest, 2),
                "change_pct": round(change_pct, 2),
            }
        except Exception as e:
            print(f"    ⚠️ {ticker} 取得失敗: {type(e).__name__}: {str(e)[:60]}")
            continue
    return result


def fetch_china_news(api_key, max_items=5):
    """中国関連ニュースを取得（^HSI と上海関連ティッカーから）"""
    titles = []
    seen = set()
    for ticker in ("^HSI", "000001.SS"):
        try:
            news = yf.Ticker(ticker).news or []
            for n in news[:max_items * 2]:
                content = n.get("content", n)
                title = content.get("title", "") or n.get("title", "")
                if title and title not in seen:
                    titles.append(title)
                    seen.add(title)
                if len(titles) >= max_items:
                    break
        except Exception:
            continue
        if len(titles) >= max_items:
            break
    # 日本語翻訳
    if titles and api_key:
        titles = translate_titles_to_jp(titles, api_key)
    return titles


def build_china_context_for_aud(ticker, api_key):
    """AUD ペアの場合のみ中国コンテキストを構築。AUD ペアでなければ None。"""
    if ticker not in ("AUDJPY=X", "AUDUSD=X", "EURAUD=X", "GBPAUD=X"):
        return None
    print(f"    🇨🇳 AUD ペアのため中国情勢を取得中...")
    market = fetch_china_market_data()
    news = fetch_china_news(api_key, max_items=5)
    return {"market": market, "news": news}


# ─────────────────────────────────────────────
# 🆕 往復ビンタ防止 — シグナル反転検知
# ─────────────────────────────────────────────
REVERSAL_LOOKBACK_HOURS = 12  # 直近 N 時間以内に反対方向シグナルがあったら反転候補と判定


def _direction_str_to_sign(direction):
    """方向文字列 → +1 (long), -1 (short), 0 (中立/不明)"""
    if not direction:
        return 0
    if "ロング" in direction or "long" in direction.lower() or "buy" in direction.lower():
        return 1
    if "ショート" in direction or "short" in direction.lower() or "sell" in direction.lower():
        return -1
    return 0


def detect_reversal(signals_log, ticker, timeframe, current_direction, now_jst):
    """直近 12h 以内に反対方向のシグナルが同銘柄・同時間軸で発火していたか判定。
    返り値: {is_reversal, previous_signal, hours_since_prev, prev_direction}"""
    if not current_direction:
        return {"is_reversal": False, "previous_signal": None, "hours_since_prev": None, "prev_direction": None}

    current_sign = _direction_str_to_sign(current_direction)
    if current_sign == 0:
        return {"is_reversal": False, "previous_signal": None, "hours_since_prev": None, "prev_direction": None}

    # 同銘柄 + 同 timeframe + 直近 N 時間以内のシグナルを抽出
    candidates = []
    for entry in signals_log:
        if entry.get("ticker") != ticker:
            continue
        if entry.get("timeframe", "4h") != timeframe:
            continue
        prev_dir = entry.get("direction")
        if not prev_dir:
            continue
        try:
            fired_at = datetime.fromisoformat(entry["fired_at"])
            hours_ago = (now_jst - fired_at).total_seconds() / 3600.0
            if 0 <= hours_ago <= REVERSAL_LOOKBACK_HOURS:
                candidates.append((hours_ago, entry))
        except Exception:
            continue

    if not candidates:
        return {"is_reversal": False, "previous_signal": None, "hours_since_prev": None, "prev_direction": None}

    # 最も最近のシグナルを取得
    candidates.sort(key=lambda x: x[0])
    hours_ago, prev_entry = candidates[0]
    prev_sign = _direction_str_to_sign(prev_entry.get("direction"))

    # 反対方向なら反転判定
    if prev_sign != 0 and prev_sign != current_sign:
        return {
            "is_reversal": True,
            "previous_signal": {
                "id": prev_entry.get("id"),
                "fired_at": prev_entry.get("fired_at"),
                "primary_signal_label": prev_entry.get("primary_signal_label"),
                "entry": prev_entry.get("entry"),
                "outcome": prev_entry.get("outcome"),
            },
            "hours_since_prev": round(hours_ago, 1),
            "prev_direction": prev_entry.get("direction"),
        }
    return {"is_reversal": False, "previous_signal": None, "hours_since_prev": None, "prev_direction": None}


# ─────────────────────────────────────────────
# 🆕 マルチタイムフレーム整合性チェック
# ─────────────────────────────────────────────
def check_trend_alignment(ticker, current_direction, current_timeframe):
    """現在のシグナル方向と上位時間軸のトレンドが一致しているか確認。
    1H シグナル → 4H トレンド、4H シグナル → 日足トレンドを参照。
    返り値: {aligned, higher_tf, higher_tf_trend, explanation}"""
    if not current_direction:
        return {"aligned": None, "higher_tf": None, "higher_tf_trend": None, "explanation": ""}

    current_sign = _direction_str_to_sign(current_direction)
    if current_sign == 0:
        return {"aligned": None, "higher_tf": None, "higher_tf_trend": None, "explanation": ""}

    # 上位時間軸を決定
    if current_timeframe == "1h":
        higher_tf, higher_interval, days = "4H", "1h", 40  # 4H = 1h を resample
    elif current_timeframe == "4h":
        higher_tf, higher_interval, days = "日足", "1d", 200
    else:
        return {"aligned": None, "higher_tf": None, "higher_tf_trend": None, "explanation": ""}

    try:
        df = yf.download(ticker, period=f"{days}d", interval=higher_interval, progress=False, auto_adjust=True)
        if df.empty or len(df) < 80:
            return {"aligned": None, "higher_tf": higher_tf, "higher_tf_trend": None,
                    "explanation": f"{higher_tf} データ不足"}
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # 4H 用の場合は 1h → 4h リサンプル
        if higher_tf == "4H":
            agg = {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}
            df = df.resample("4h").agg(agg).dropna(subset=["Close"])

        close = df["Close"]
        ma25 = close.rolling(25).mean()
        ma75 = close.rolling(75).mean()

        ma25_now = float(ma25.iloc[-1])
        ma75_now = float(ma75.iloc[-1])
        ma25_prev = float(ma25.iloc[-5]) if len(ma25) >= 5 else ma25_now
        ma25_slope_up = ma25_now > ma25_prev

        # トレンド判定: MA25 > MA75 かつ MA25 上昇 → 上昇トレンド
        if ma25_now > ma75_now and ma25_slope_up:
            trend = "上昇"
            trend_sign = 1
        elif ma25_now < ma75_now and not ma25_slope_up:
            trend = "下降"
            trend_sign = -1
        else:
            trend = "中立・もみあい"
            trend_sign = 0

        if trend_sign == 0:
            aligned = None  # トレンドが中立なら判定不能
        else:
            aligned = (trend_sign == current_sign)

        if aligned is True:
            explanation = f"✅ {higher_tf} {trend}トレンド継続中、シグナル方向と一致（順張り）"
        elif aligned is False:
            explanation = f"⚠️ {higher_tf} {trend}トレンドに対しシグナルは逆方向（逆張り、要警戒）"
        else:
            explanation = f"〜 {higher_tf} はもみあい、トレンド判定不能（中立）"

        return {
            "aligned": aligned,
            "higher_tf": higher_tf,
            "higher_tf_trend": trend,
            "ma25": round(ma25_now, 4),
            "ma75": round(ma75_now, 4),
            "explanation": explanation,
        }
    except Exception as e:
        print(f"    ⚠️ {higher_tf} 整合性チェック失敗: {type(e).__name__}: {str(e)[:60]}")
        return {"aligned": None, "higher_tf": higher_tf, "higher_tf_trend": None,
                "explanation": f"{higher_tf} 取得失敗"}


# ─────────────────────────────────────────────
# 🆕 環境警戒システム — 取引推奨度 A〜D を算定
# ─────────────────────────────────────────────
def load_economic_events():
    """economic-events.json をロード"""
    if not os.path.exists(ECONOMIC_EVENTS_FILE):
        return {"events": [], "crisis_keywords": {"japanese": [], "english": []}}
    try:
        with open(ECONOMIC_EVENTS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"  ⚠️ {ECONOMIC_EVENTS_FILE} 読み込み失敗: {e}")
        return {"events": [], "crisis_keywords": {"japanese": [], "english": []}}


def check_upcoming_events(ticker, now_jst, events_data):
    """ticker に関係する直近イベントを取得（重要指標のみ、市場休場は除外）。
    返り値: list of {name, hours_until, impact}（近い順）"""
    relevant = []
    for ev in events_data.get("events", []):
        # 市場休場は別関数 (check_market_holidays) で扱うので除外
        if ev.get("category") == "market_holiday":
            continue
        try:
            ev_dt = datetime.fromisoformat(ev["datetime"])
        except Exception:
            continue
        hours_until = (ev_dt - now_jst).total_seconds() / 3600.0
        # 過去イベントは無視、48 時間より先も無視
        if hours_until < 0 or hours_until > 48:
            continue
        # 影響銘柄チェック
        affected = ev.get("affected_assets", ["all"])
        if "all" not in affected and ticker not in affected:
            continue
        relevant.append({
            "name": ev["name"],
            "hours_until": round(hours_until, 1),
            "impact": ev.get("impact", "high"),
            "datetime": ev["datetime"],
        })
    return sorted(relevant, key=lambda x: x["hours_until"])


def check_market_holidays(ticker, now_jst, events_data):
    """ticker に関係する直近 / 当日の市場休場を取得。
    返り値: dict {
        "today_holidays": [当日が休場の市場のリスト],
        "upcoming_holidays": [48h 以内の休場リスト（当日含まず）],
        "is_today_holiday": bool,  # ticker にとって今日が休場か
    }
    """
    today_date = now_jst.date()
    today_holidays = []
    upcoming = []
    for ev in events_data.get("events", []):
        if ev.get("category") != "market_holiday":
            continue
        try:
            ev_dt = datetime.fromisoformat(ev["datetime"])
        except Exception:
            continue

        # 影響銘柄チェック
        affected = ev.get("affected_assets", ["all"])
        if "all" not in affected and ticker not in affected:
            continue

        hours_until = (ev_dt - now_jst).total_seconds() / 3600.0
        ev_date = ev_dt.date()
        item = {
            "name": ev["name"],
            "hours_until": round(hours_until, 1),
            "country": ev.get("country", "?"),
            "note": ev.get("note", ""),
            "datetime": ev["datetime"],
        }
        if ev_date == today_date:
            today_holidays.append(item)
        elif 0 < hours_until <= 48:
            upcoming.append(item)

    return {
        "today_holidays": today_holidays,
        "upcoming_holidays": sorted(upcoming, key=lambda x: x["hours_until"]),
        "is_today_holiday": len(today_holidays) > 0,
    }


def fetch_vix_data():
    """現在 VIX と 30 日平均 VIX を取得"""
    try:
        df = yf.download("^VIX", period="35d", interval="1d", progress=False, auto_adjust=True)
        if df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        current = float(df["Close"].iloc[-1])
        avg30 = float(df["Close"].iloc[-30:].mean())
        prev_24h = float(df["Close"].iloc[-2]) if len(df) >= 2 else current
        change_24h_pct = (current - prev_24h) / prev_24h * 100 if prev_24h else 0
        return {
            "current": round(current, 2),
            "avg_30d": round(avg30, 2),
            "change_24h_pct": round(change_24h_pct, 2),
        }
    except Exception as e:
        print(f"  ⚠️ VIX 取得失敗: {type(e).__name__}: {str(e)[:60]}")
        return None


def calc_atr_regime(df, current_atr):
    """ATR の現在値 vs 過去 30 日平均 ATR の倍率を計算"""
    try:
        atr_series = calc_atr(df["High"], df["Low"], df["Close"])
        # 直近 30 本の平均（4H なら約 5 日分、1H なら 30 時間分）
        avg_atr = float(atr_series.iloc[-60:-1].mean())  # 最新は除く
        if avg_atr <= 0:
            return None
        ratio = current_atr / avg_atr
        # レジーム分類
        if ratio < 1.5:
            regime, label = "normal", "🟢 平常"
        elif ratio < 2.0:
            regime, label = "elevated", "🟡 やや高ボラ"
        elif ratio < 3.0:
            regime, label = "high", "🟠 高ボラ"
        elif ratio < 4.0:
            regime, label = "extreme", "🔴 異常ボラ"
        else:
            regime, label = "crisis", "⚫ 極端ボラ"
        return {
            "current_atr": round(current_atr, 4),
            "avg_atr_30d": round(avg_atr, 4),
            "ratio": round(ratio, 2),
            "regime": regime,
            "label": label,
        }
    except Exception as e:
        print(f"  ⚠️ ATR レジーム計算失敗: {e}")
        return None


def check_crisis_keywords(news_titles, crisis_keywords):
    """ニュースに危機キーワードが何件含まれるか"""
    if not news_titles:
        return {"hit_count": 0, "matched_keywords": [], "matched_titles": []}
    all_kw = (crisis_keywords.get("japanese", []) + crisis_keywords.get("english", []))
    matched_kw = set()
    matched_titles = []
    for title in news_titles:
        if not title:
            continue
        for kw in all_kw:
            if kw and kw.lower() in title.lower():
                matched_kw.add(kw)
                matched_titles.append(title[:80])
                break  # 1 タイトル 1 マッチで十分
    return {
        "hit_count": len(matched_titles),
        "matched_keywords": list(matched_kw),
        "matched_titles": matched_titles[:5],
    }


def recommend_position_size(atr_ratio, env_score):
    """ATR 倍率と環境スコアからポジションサイズ係数（0.0〜1.0）を返す"""
    if env_score == "D":
        return {"factor": 0.0, "label": "取引非推奨", "color": "#cf222e"}
    if atr_ratio is None:
        atr_ratio = 1.0

    if atr_ratio < 1.5:
        factor = 1.00
    elif atr_ratio < 2.0:
        factor = 0.70
    elif atr_ratio < 3.0:
        factor = 0.40
    elif atr_ratio < 4.0:
        factor = 0.15
    else:
        factor = 0.0  # 極端ボラは強制ゼロ

    # 環境スコアでさらに調整
    if env_score == "C":
        factor = factor * 0.5
    elif env_score == "B":
        factor = factor * 0.75
    # A はそのまま

    if factor <= 0.01:
        return {"factor": 0.0, "label": "取引非推奨", "color": "#cf222e"}
    elif factor < 0.30:
        return {"factor": round(factor, 2), "label": "サイズ大幅縮小", "color": "#9a6700"}
    elif factor < 0.70:
        return {"factor": round(factor, 2), "label": "サイズ縮小推奨", "color": "#9a6700"}
    else:
        return {"factor": round(factor, 2), "label": "通常運用", "color": "#1a7f37"}


# ATR レジーム別の歴史的事例（参考表示用）
HISTORICAL_REGIMES = {
    "normal": "通常相場",
    "elevated": "CPI 発表当日 / 中規模指標前後の典型水準",
    "high": "為替介入観測 / 主要会合直後 / 突発ニュース",
    "extreme": "2022 年 BoJ 介入 / SVB 破綻時 / 大幅利上げサプライズ級",
    "crisis": "ウクライナ侵攻初日 / コロナショック級の異常事態",
}


def _build_currency_strength_block(strength, fx_alignment):
    """メール本文用の通貨強弱ブロック（FX ペア時のみ表示）"""
    if not strength:
        return ""
    block = format_currency_strength(strength)
    if fx_alignment:
        block += "\n" + fx_alignment["explanation"] + "\n"
    return block + "\n"


def _build_china_block(china_ctx):
    """AUD ペア専用：中国情勢ブロック"""
    if not china_ctx:
        return ""
    lines = ["【🇨🇳 中国情勢（AUD ペア専用フォーカス）】"]

    market = china_ctx.get("market") or {}
    for ticker, data in market.items():
        ch = data["change_pct"]
        emoji = "🟢" if ch > 0 else "🔴" if ch < 0 else "⚪"
        lines.append(f"  {emoji} {data['name']}: {data['current']:,.2f}（前日比 {ch:+.2f}%）")

    news = china_ctx.get("news") or []
    if news:
        lines.append("")
        lines.append("📰 中国関連ニュース:")
        for t in news[:5]:
            lines.append(f"  - {t[:100]}")

    # AUD 解釈ヒント
    avg_change = 0
    cnt = 0
    for data in market.values():
        avg_change += data["change_pct"]
        cnt += 1
    if cnt > 0:
        avg_change /= cnt
        if avg_change > 0.5:
            lines.append("\n💡 中国市場は堅調 → AUD 上値追い風の可能性")
        elif avg_change < -0.5:
            lines.append("\n💡 中国市場は軟調 → AUD 上値抑制要因。AUD ロングは慎重に")
        else:
            lines.append("\n💡 中国市場は中立、AUD への影響は限定的")

    return "\n".join(lines) + "\n\n"


def _build_whipsaw_block(reversal, trend_align):
    """メール本文用のシグナル反転・トレンド整合性ブロックを構築"""
    has_reversal = reversal and reversal.get("is_reversal")
    has_trend = trend_align and trend_align.get("aligned") is not None

    if not has_reversal and not has_trend:
        return ""

    lines = []
    lines.append("【🔄 シグナル品質チェック】")

    if has_reversal:
        prev = reversal["previous_signal"]
        prev_dir = reversal["prev_direction"]
        prev_outcome = prev.get("outcome")
        outcome_label = {"tp1": "✅ TP1 到達済", "tp2": "🎯 TP2 到達済", "sl": "❌ SL ヒット済",
                         "expired": "⏰ 期限切れ", None: "⏳ 未確定"}.get(prev_outcome, "—")
        lines.append("")
        lines.append(f"⚠️ 往復ビンタ警戒: {reversal['hours_since_prev']}h 前に反対方向シグナル")
        lines.append(f"  前回: {prev_dir} ({prev.get('primary_signal_label', '')})")
        lines.append(f"       エントリー価格 {prev.get('entry')}, 結果: {outcome_label}")
        lines.append(f"")
        lines.append(f"  💡 同銘柄でロング/ショートが短期間に切り替わる相場は、")
        lines.append(f"     ニュース・地政学要因による短期混乱の典型パターン。")
        lines.append(f"     ⚠️ 往復で損失拡大しやすいので、ポジションサイズ縮小 or 見送り推奨。")

    if has_trend:
        lines.append("")
        if trend_align["aligned"] is True:
            lines.append(f"✅ {trend_align['explanation']}")
            lines.append(f"  → 信頼度: ⭐⭐⭐ HIGH（上位時間軸トレンドに乗る順張りシグナル）")
        elif trend_align["aligned"] is False:
            lines.append(f"⚠️ {trend_align['explanation']}")
            lines.append(f"  → 信頼度: ⭐ LOW（逆張りシグナルは反発時のみ機能。慎重に）")
        else:
            lines.append(f"〜 {trend_align['explanation']}")

    return "\n".join(lines) + "\n\n"


def _build_confidence_block(confidence):
    """メール本文用の信頼度スコアブロックを構築 (B2)"""
    if not confidence:
        return ""
    lines = []
    lines.append(f"【💯 信頼度: {confidence['stars']} {confidence['label']} (スコア {confidence['score']:+d})】")
    for f in confidence["factors"]:
        lines.append(f"  ・{f}")
    if confidence["label"] == "HIGH":
        lines.append("  → 強いシグナル。複数要因が一致しており、優先的に検討する価値あり。")
    elif confidence["label"] == "MID":
        lines.append("  → 中程度のシグナル。他の判断材料と組み合わせて判断を。")
    else:
        lines.append("  → 弱いシグナル。単独要因のみ／不利な要因あり。慎重に。")
    return "\n".join(lines) + "\n\n"


def _build_environment_block(env, currency="", decimals=2):
    """メール本文用の環境警戒ブロックを構築"""
    lines = []
    lines.append("【🛡️ 環境警戒】")
    lines.append(f"取引推奨度: {env['env_score']} {env['score_label']}")

    size = env["size_recommendation"]
    if size["factor"] <= 0.01:
        lines.append(f"📐 推奨ポジションサイズ: 🚫 取引非推奨（環境悪化のため見送り）")
    else:
        pct = int(size["factor"] * 100)
        lines.append(f"📐 推奨ポジションサイズ: 通常の {pct}% ({size['label']})")
        lines.append(f"   例: 通常 0.10 lot → {0.10 * size['factor']:.3f} lot 推奨")

    # 警告詳細
    if env["warnings"]:
        lines.append("")
        lines.append("⚠️ 検知された要因:")
        for w in env["warnings"]:
            lines.append(f"  {w}")

    # 市場休場（当日 + 直近 48h）
    mh = env.get("market_holidays") or {}
    if mh.get("today_holidays") or mh.get("upcoming_holidays"):
        lines.append("")
        lines.append("🏖️ 市場休場:")
        for h in mh.get("today_holidays", []):
            lines.append(f"  🏖️ 当日: {h['name']}")
            if h.get("note"):
                lines.append(f"     📝 {h['note']}")
        for h in mh.get("upcoming_holidays", []):
            lines.append(f"  ⏳ {h['hours_until']:.1f}h 後: {h['name']}")

    # 重要指標
    if env["upcoming_events"]:
        lines.append("")
        lines.append("📅 直近の重要指標（48h 以内）:")
        for ev in env["upcoming_events"]:
            impact_emoji = "🔴" if ev["impact"] == "critical" else "🟠"
            lines.append(f"  {impact_emoji} {ev['name']} まで {ev['hours_until']:.1f}h")

    # VIX
    if env["vix"]:
        v = env["vix"]
        lines.append("")
        lines.append(f"📊 VIX: {v['current']}（30 日平均 {v['avg_30d']}, 24h {v['change_24h_pct']:+.1f}%）")

    # ATR レジーム
    if env["atr_regime"]:
        a = env["atr_regime"]
        lines.append(f"⚡ ATR: {currency}{a['current_atr']:.{decimals}f}（通常の {a['ratio']}x = {a['label']}）")
        if env["historical_reference"]:
            lines.append(f"   📚 同水準の過去事例: {env['historical_reference']}")

    # 危機キーワード
    crisis = env["crisis_news"]
    if crisis["hit_count"] >= 1:
        lines.append("")
        lines.append(f"🚨 危機キーワード検知: {crisis['hit_count']} 件")
        for t in crisis["matched_titles"][:3]:
            lines.append(f"  - {t}")

    return "\n".join(lines) + "\n"


def check_environment(ticker, now_jst, df, current_atr, news_titles, events_data):
    """総合環境チェック。各項目の検知結果と統合スコアを返す。
    返り値: dict with upcoming_events, market_holidays, vix, atr_regime, crisis_news, env_score, size_rec, warnings
    """
    upcoming = check_upcoming_events(ticker, now_jst, events_data)
    market_holidays = check_market_holidays(ticker, now_jst, events_data)
    vix = fetch_vix_data()
    atr_regime = calc_atr_regime(df, current_atr) if current_atr > 0 else None
    crisis = check_crisis_keywords(news_titles, events_data.get("crisis_keywords", {}))

    # スコア判定
    warnings = []
    danger_count = 0

    # 0. 市場休場（今日が休場 = ボラ低下・流動性減少）
    if market_holidays["is_today_holiday"]:
        # 影響国を集約してメッセージに
        countries = sorted(set(h["country"] for h in market_holidays["today_holidays"]))
        countries_label = "・".join(countries)
        warnings.append(f"🏖️ 当日 {countries_label} 市場休場（ボラ低下、薄商い）")
        danger_count += 1  # env_score を 1 段階下げる効果
    # 翌日の休場（24h 以内）も警告のみ（スコアは下げない）
    elif market_holidays["upcoming_holidays"]:
        nearest_h = market_holidays["upcoming_holidays"][0]
        if nearest_h["hours_until"] <= 24:
            warnings.append(f"🏖️ {nearest_h['hours_until']:.0f}h 後に {nearest_h['country']} 市場休場予定")

    # 1. 重要指標近接（最重要）
    nearest_event = upcoming[0] if upcoming else None
    if nearest_event:
        h = nearest_event["hours_until"]
        if h <= 6:
            warnings.append(f"🚫 重要指標まで {h:.1f}h: {nearest_event['name']}")
            danger_count += 2  # 致命的
        elif h <= 24:
            warnings.append(f"🟡 重要指標まで {h:.1f}h: {nearest_event['name']}")
            danger_count += 1

    # 2. VIX レベル
    if vix:
        if vix["current"] >= 30:
            warnings.append(f"🚫 VIX {vix['current']} 極度の恐怖")
            danger_count += 2
        elif vix["current"] >= 25:
            warnings.append(f"🟠 VIX {vix['current']} 高水準")
            danger_count += 1
        if vix["change_24h_pct"] >= 20:
            warnings.append(f"🟠 VIX 24h +{vix['change_24h_pct']:.1f}% 急騰")
            danger_count += 1

    # 3. ATR レジーム
    if atr_regime:
        if atr_regime["regime"] == "crisis":
            warnings.append(f"🚫 ATR {atr_regime['ratio']}x 極端ボラ（過去戦争・パンデミック級）")
            danger_count += 3  # 即取引禁止級
        elif atr_regime["regime"] == "extreme":
            warnings.append(f"🔴 ATR {atr_regime['ratio']}x 異常ボラ")
            danger_count += 2
        elif atr_regime["regime"] == "high":
            warnings.append(f"🟠 ATR {atr_regime['ratio']}x 高ボラ")
            danger_count += 1

    # 4. 危機キーワード
    if crisis["hit_count"] >= 3:
        warnings.append(f"🚫 危機キーワード {crisis['hit_count']} 件: {','.join(crisis['matched_keywords'][:3])}")
        danger_count += 2
    elif crisis["hit_count"] >= 1:
        warnings.append(f"🟡 危機キーワード {crisis['hit_count']} 件: {','.join(crisis['matched_keywords'][:3])}")
        danger_count += 1

    # スコア決定
    if danger_count >= 3:
        env_score = "D"
        score_label = "🚫 取引禁止"
    elif danger_count == 2:
        env_score = "C"
        score_label = "🔴 非推奨"
    elif danger_count == 1:
        env_score = "B"
        score_label = "🟡 警戒"
    else:
        env_score = "A"
        score_label = "🟢 平常"

    atr_ratio = atr_regime["ratio"] if atr_regime else 1.0
    size_rec = recommend_position_size(atr_ratio, env_score)

    # 歴史的参照
    history_ref = ""
    if atr_regime and atr_regime["regime"] in ("extreme", "crisis"):
        history_ref = HISTORICAL_REGIMES.get(atr_regime["regime"], "")

    return {
        "env_score": env_score,
        "score_label": score_label,
        "warnings": warnings,
        "danger_count": danger_count,
        "upcoming_events": upcoming[:3],
        "market_holidays": market_holidays,
        "vix": vix,
        "atr_regime": atr_regime,
        "crisis_news": crisis,
        "size_recommendation": size_rec,
        "historical_reference": history_ref,
    }


# ─────────────────────────────────────────────
# Gemini でニュース見出しを日本語に一括翻訳（バッチ 1 リクエスト）
# 既に日本語のタイトルはスキップ。失敗時は原文をそのまま返す。
# ─────────────────────────────────────────────
import re as _re_ja_check
_HAS_JA_RE = _re_ja_check.compile(r'[぀-ヿ一-鿿]')


def translate_titles_to_jp(titles, api_key):
    """ニュース見出し配列を Gemini で一括翻訳。失敗時は原文配列を返す。"""
    if not titles or not api_key:
        return titles or []
    # 既に日本語のものは原文キープ、英語のもののみ翻訳対象
    targets = []
    for i, t in enumerate(titles):
        if t and not _HAS_JA_RE.search(t):
            targets.append((i, t))
    if not targets:
        return titles  # 全部日本語 → 何もしない

    try:
        import google.generativeai as genai
    except ImportError:
        return titles
    genai.configure(api_key=api_key)

    numbered = "\n".join([f"{i+1}. {t}" for i, (_, t) in enumerate(targets)])
    prompt = f"""次の英語ニュース見出しを、それぞれ日本語に翻訳してください。
ニュアンスを保ち、投資家が読みやすい自然な日本語にしてください。
固有名詞（企業名・人名・通貨）はそのまま英字でも、カタカナでも、文脈に応じて選んでください。

【入力】
{numbered}

【出力フォーマット】（番号付きの行のみ。前置きや解説は不要）
1. 翻訳結果
2. 翻訳結果
...
"""
    text = ""
    for model_name in ("gemini-2.0-flash-lite", "gemini-2.5-flash-lite", "gemini-2.0-flash"):
        try:
            model = genai.GenerativeModel(model_name)
            resp = model.generate_content(prompt)
            text = (resp.text or "").strip()
            if text:
                break
        except Exception:
            continue
    if not text:
        return titles  # 全モデル失敗 → 原文

    # 番号付き行をパース
    translations = {}
    for line in text.splitlines():
        m = _re_ja_check.match(r'^\s*(\d+)[.\)]\s*(.+)$', line.strip())
        if m:
            n = int(m.group(1)) - 1  # 0-indexed in targets
            if 0 <= n < len(targets):
                translations[targets[n][0]] = m.group(2).strip()

    # 結合：翻訳できたものは差し替え、できなかったものは原文
    result = list(titles)
    for orig_idx, jp_text in translations.items():
        result[orig_idx] = jp_text
    return result


# ─────────────────────────────────────────────
# Gemini で「なぜこのシグナルか」の解説生成（テクニカル + ニュース）
# ─────────────────────────────────────────────
def generate_ai_narrative(asset_name, current_price_str, signals, indicators, news_titles, position_plan, api_key, timeframe="4h",
                            currency_strength=None, fx_alignment=None, china_ctx=None):
    """SL/TP は固定値（ATR 算出済）を渡し、AI には「なぜこの水準が妥当か」の解説のみさせる。"""
    if not api_key:
        return ""
    try:
        import google.generativeai as genai
    except ImportError:
        return ""
    genai.configure(api_key=api_key)
    signal_lines = "\n".join([f"- {s['label']}（{s['detail']}）" for s in signals])
    # 直近ニュースをプロンプトに含める（あれば）
    if news_titles:
        news_section = "\n\n【直近の関連ニュース見出し（ファンダメンタル参考）】\n" + "\n".join([f"- {t[:120]}" for t in news_titles])
    else:
        news_section = ""

    # timeframe ごとの想定保有期間
    if timeframe == "1h":
        tf_label = "1H 足"
        hold_label = "短期スキャル〜デイトレ（数時間〜1 日保有）"
    else:
        tf_label = "4H 足"
        hold_label = "4H スイング（1〜5 日保有）"

    # ポジションプラン（数値は AI に判断させず固定値で渡す）
    if position_plan:
        plan_section = f"""

【参考ポジションプラン（ATR ベースで算出済、AI は数値を変更しないこと）】
- 方向: {position_plan['direction']}
- エントリー: {position_plan['entry']:.2f}
- ストップロス: {position_plan['stop_loss']:.2f}（{position_plan['sl_pct']:+.2f}%）
- 利確 ①: {position_plan['take_profit_1']:.2f}（{position_plan['tp1_pct']:+.2f}%）
- 利確 ②: {position_plan['take_profit_2']:.2f}（{position_plan['tp2_pct']:+.2f}%）
- SL 根拠: ATR(14) = {position_plan['atr']:.2f} × 1.5
- 想定時間軸: {hold_label}"""
    else:
        plan_section = "\n\n【参考ポジションプラン】方向感が定まらないため今回は提示なし（様子見推奨）"

    # 🆕 通貨強弱セクション
    currency_section = ""
    if currency_strength:
        valid = [(c, v) for c, v in currency_strength.items() if v is not None]
        valid.sort(key=lambda x: -x[1])
        ranking = " > ".join([f"{c}({v:+.2f}%)" for c, v in valid])
        currency_section = f"\n\n【通貨強弱（24h）】\n{ranking}"
        if fx_alignment and fx_alignment.get("aligned") is not None:
            currency_section += f"\n→ {fx_alignment['explanation']}"

    # 🆕 中国情勢セクション（AUD ペア専用）
    china_section = ""
    if china_ctx:
        market_lines = []
        for tk, d in (china_ctx.get("market") or {}).items():
            market_lines.append(f"- {d['name']}: {d['current']:,.2f}（前日比 {d['change_pct']:+.2f}%）")
        market_block = "\n".join(market_lines) if market_lines else "（取得失敗）"
        news_lines = "\n".join([f"- {t[:100]}" for t in (china_ctx.get("news") or [])[:5]])
        china_section = f"""

【🇨🇳 中国情勢（AUD ペア専用フォーカス／重要：AUD は中国景気依存通貨）】
{market_block}
{news_lines if news_lines else '（中国関連ニュース取得失敗）'}

【⚠️ 解説時の注意】
このペアは AUD を含むため、中国景気が AUD の方向性に強く影響する。
中国市場が軟調なら AUD の上値抑制要因、堅調なら追い風になる点を解説に必ず織り込むこと。"""

    prompt = f"""あなたは日本人個人投資家向けのテクニカル + ファンダメンタル アナリストです。
{asset_name}（現在 {current_price_str}）の {tf_label} チャートで以下のシグナルが発火しました。
**SL/TP の数値は既に ATR ベースで算出済み**なので、その数値を変更せず、「なぜこの方向感・この水準が妥当か」をテクニカルとファンダの両面から解説してください。

【発火シグナル（テクニカル）】
{signal_lines}

【テクニカル指標】
- RSI: {indicators['rsi']:.1f}
- MACD: {indicators['macd']:.4f} / シグナル: {indicators['macd_sig']:.4f}
- 25MA: {indicators['ma25']:.2f} / 75MA: {indicators['ma75']:.2f}
- ボリンジャー: -2σ {indicators['bb_low']:.2f} / +2σ {indicators['bb_up']:.2f}
- 直近 20 本: 高値 {indicators['recent_high']:.2f} / 安値 {indicators['recent_low']:.2f}
- ATR(14): {indicators.get('atr', 0):.2f}（1 本の平均的な値動き）
{plan_section}{currency_section}{china_section}
{news_section}

【出力フォーマット】（プレーンテキスト、{350 if china_ctx else 250} 字以内）
2〜4 文。テクニカル要因（なぜこの方向か）とファンダ要因（ニュース材料との整合性）の両方に触れる。
通貨強弱情報がある場合は、それと方向感が一致しているかも 1 文触れる。
{('AUD ペアなので中国景気の影響を必ず 1 文触れること。' if china_ctx else '')}
**SL/TP の数値は出さない（既に上で確定済み）**、代わりに「シナリオが崩れる条件（=SL に到達する展開）」を 1 つだけ言及する。
ニュースに該当する材料がなければ「足元のニュース材料は限定的」と書く。"""

    for model_name in ("gemini-2.0-flash-lite", "gemini-2.5-flash-lite", "gemini-2.0-flash"):
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            text = (response.text or "").strip()
            if text:
                return text.replace("\n", " ")[:600]
        except Exception:
            continue
    return ""


# ─────────────────────────────────────────────
# Gmail SMTP でメール送信
# ─────────────────────────────────────────────
def send_email(subject, body, sender, password, recipient):
    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg.attach(MIMEText(body, "plain", "utf-8"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as server:
        server.login(sender, password)
        server.sendmail(sender, [recipient], msg.as_string())


# ─────────────────────────────────────────────
# 履歴管理（連投防止）
# ─────────────────────────────────────────────
def load_history():
    if not os.path.exists(ALERT_HISTORY_FILE):
        return {}
    try:
        with open(ALERT_HISTORY_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


# ─────────────────────────────────────────────
# 🆕 信頼度スコア（B2）— 複数シグナル × 環境 × 整合性を統合
# ─────────────────────────────────────────────
def calc_confidence_score(fresh_signals, env, trend_align, reversal, fx_alignment):
    """シグナル発火時の信頼度を 3 段階（HIGH/MID/LOW）で算出

    スコアリング:
      + シグナル数 (1-3 シグナル併発): 各 +1 ポイント (max +3)
      + 環境スコア: A=+2 / B=+1 / C=0 / D=-2
      + トレンド整合: aligned=true → +2 / false → -1 / null → 0
      + 反転検知: あり → -2 / なし → 0
      + FX 強弱整合 (FX のみ): aligned=true → +1 / false → -1 / null → 0

    閾値:
      score >= 5  → ⭐⭐⭐ HIGH（強）
      2 <= score < 5 → ⭐⭐ MID（中）
      score < 2  → ⭐ LOW（弱）
    """
    factors = []
    score = 0

    # 複数シグナル併発
    n = min(len(fresh_signals or []), 3)
    score += n
    factors.append(f"シグナル {n} 種併発 (+{n})")

    # 環境スコア
    env_score = (env or {}).get("env_score")
    env_pts = {"A": 2, "B": 1, "C": 0, "D": -2}.get(env_score, 0)
    score += env_pts
    if env_pts != 0:
        factors.append(f"環境 {env_score} ({env_pts:+d})")

    # トレンド整合
    aligned = (trend_align or {}).get("aligned")
    if aligned is True:
        score += 2
        factors.append("上位足トレンド順張り (+2)")
    elif aligned is False:
        score -= 1
        factors.append("上位足トレンド逆張り (-1)")

    # 反転検知
    if reversal and reversal.get("is_reversal"):
        score -= 2
        factors.append("反転検知あり (-2)")

    # FX 強弱整合 (FX シグナルのみ)
    fx_aligned = (fx_alignment or {}).get("aligned")
    if fx_aligned is True:
        score += 1
        factors.append("FX 強弱順張り (+1)")
    elif fx_aligned is False:
        score -= 1
        factors.append("FX 強弱逆張り (-1)")

    # ラベル判定
    if score >= 5:
        label = "HIGH"
        stars = "⭐⭐⭐"
    elif score >= 2:
        label = "MID"
        stars = "⭐⭐"
    else:
        label = "LOW"
        stars = "⭐"

    return {
        "score": score,
        "label": label,
        "stars": stars,
        "factors": factors,
    }


# ─────────────────────────────────────────────
# シグナルログ（track-record 用） — 全発火を JSON に蓄積
# ─────────────────────────────────────────────
def load_signals_log():
    if not os.path.exists(SIGNALS_LOG_FILE):
        return []
    try:
        with open(SIGNALS_LOG_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_signals_log(log):
    try:
        with open(SIGNALS_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(log, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ シグナルログ保存失敗: {e}")


def compute_sr_runway(position_plan, indicators):
    """発火時点の recent_high/recent_low（＝そのシグナルの時間足の直近スイング高安＝S/R）と
    entry/TP1 から、runway（TP到達前に S/R が進路を塞ぐか）と S/R整合（サポ近接ロング/レジ近接
    ショート）を算出して記録する。
    ※ 2026-06-03 追加。【記録のみ】＝発火・メール・信頼度には一切使わない。signals-log に蓄積し、
       blocked（TP前にS/Rが挟まる）取引の実勝率を前向きに検証するためのタグ。
       過去データ集計では blocked 27.7%/−0.337R vs clear 44.3%/+0.110R（look-ahead無し）。"""
    if not position_plan:
        return None
    try:
        e = float(position_plan.get("entry"))
        tp1 = float(position_plan.get("take_profit_1"))
        atr = float(position_plan.get("atr") or indicators.get("atr") or 0)
        rh = float(indicators.get("recent_high") or 0)
        rl = float(indicators.get("recent_low") or 0)
    except (TypeError, ValueError):
        return None
    if e <= 0 or tp1 <= 0 or atr <= 0 or rh <= 0 or rl <= 0:
        return None
    d = str(position_plan.get("direction", ""))
    is_long = ("ロング" in d) or ("買" in d)
    is_short = ("ショート" in d) or ("売" in d)
    blocked, block_frac = False, None
    if is_long and e < rh < tp1:
        blocked, block_frac = True, round((rh - e) / (tp1 - e), 3)
    elif is_short and tp1 < rl < e:
        blocked, block_frac = True, round((e - rl) / (e - tp1), 3)
    d_sup_atr = round((e - rl) / atr, 3) if rl < e else None  # entry→直近安値(サポ)距離 ATR
    d_res_atr = round((rh - e) / atr, 3) if rh > e else None  # 直近高値(レジ)→entry距離 ATR
    if is_long:
        aligned = d_sup_atr is not None and 0 <= d_sup_atr <= 1.0
    elif is_short:
        aligned = d_res_atr is not None and 0 <= d_res_atr <= 1.0
    else:
        aligned = None
    return {
        "blocked": blocked,        # entry→TP1 の間に直近S/Rが挟まる（runway阻害＝過去集計で不利）
        "block_frac": block_frac,  # 阻害位置（0=entry,1=TP1）。小さいほど早く塞ぐ＝より不利
        "aligned": aligned,        # サポ近接ロング/レジ近接ショート（≤1ATR）
        "d_sup_atr": d_sup_atr,
        "d_res_atr": d_res_atr,
    }


def compute_selection_tier(position_plan, indicators, sr, primary_signal):
    """選別タグ（quality_tier）。【記録のみ】＝発火・メール・信頼度には一切使わない。
    過去304件の集計に基づく前向き検証用：
      - avoid（飛びつき買い / ma_goldenロング / runway阻害 のいずれか）を除くと −0.012R→+0.224R（件数は半分維持）
      - elite（runwayクリア ∩ レンジregime）は +0.833R / 勝率70% / ✅安定
      - good（サポ整合 or レンジregime）は +0.4R 前後 / ✅安定
    tier 別の実Rが avoid<neutral<good<elite の順に並ぶかをライブで確認してから、発火/信頼度への昇格を判断する。"""
    if not position_plan:
        return None
    ind = indicators or {}
    d = str(position_plan.get("direction", ""))
    is_long = ("ロング" in d) or ("買" in d)
    try:
        e = float(position_plan.get("entry") or 0)
        a25 = float(ind.get("ma25") or 0)
        a75 = float(ind.get("ma75") or 0)
    except (TypeError, ValueError):
        e = a25 = a75 = 0
    chasing = is_long and e > 0 and a25 > 0 and a75 > 0 and e > a25 and e > a75  # 飛びつき買い
    ma_golden_long = is_long and str(primary_signal or "").startswith("ma_golden")
    blocked = bool(sr and sr.get("blocked") is True)
    clear = bool(sr and sr.get("blocked") is False)
    aligned = bool(sr and sr.get("aligned") is True)
    regime = ind.get("regime")
    range_regime = (regime == "range")
    if chasing or ma_golden_long or blocked:
        tier = "avoid"
    elif clear and range_regime:
        tier = "elite"
    elif aligned or range_regime:
        tier = "good"
    else:
        tier = "neutral"
    return {
        "tier": tier,                       # avoid / neutral / good / elite（前向き検証用の選別ランク）
        "veto_chasing": chasing,            # 飛びつき買い（価格>MA25&MA75のロング、過去 −0.29R）
        "veto_ma_golden_long": ma_golden_long,  # ma_goldenロング（過去 12%/−0.69R）
        "veto_runway_blocked": blocked,     # runway阻害（過去 −0.337R）
        "aligned": aligned,                 # サポ近接ロング/レジ近接ショート
        "regime": regime,                   # range で勝ちやすい傾向（4h足のみ記録）
    }


def build_signal_log_entry(ticker, name, fresh_signals, indicators, position_plan,
                            news_titles, narrative, fired_at_iso, timeframe="4h"):
    """1 アラート発火を構造化レコードに整形"""
    primary = fresh_signals[0]
    # ID: 例 "GC=F_4h_20260520_2130" / "GC=F_1h_20260520_2130"
    dt_compact = datetime.fromisoformat(fired_at_iso).strftime("%Y%m%d_%H%M")
    record_id = f"{ticker}_{timeframe}_{dt_compact}"

    # S/R runway ＋ 選別タグ（いずれも【記録のみ】＝発火・メール・信頼度には不使用）
    sr_runway = compute_sr_runway(position_plan, indicators)
    selection = compute_selection_tier(position_plan, indicators, sr_runway, primary["type"])

    entry = {
        "id": record_id,
        "fired_at": fired_at_iso,
        "timeframe": timeframe,
        "ticker": ticker,
        "asset_name": name,
        "signal_types": [s["type"] for s in fresh_signals],
        "primary_signal": primary["type"],
        "primary_signal_label": primary["label"],
        "signal_count": len(fresh_signals),

        # ポジションプラン（ATR 算出）
        "direction": position_plan["direction"] if position_plan else None,
        "entry": position_plan["entry"] if position_plan else indicators["price"],
        "stop_loss": position_plan["stop_loss"] if position_plan else None,
        "take_profit_1": position_plan["take_profit_1"] if position_plan else None,
        "take_profit_2": position_plan["take_profit_2"] if position_plan else None,
        "atr": position_plan["atr"] if position_plan else indicators.get("atr", 0),
        "sl_pct": position_plan["sl_pct"] if position_plan else None,
        "tp1_pct": position_plan["tp1_pct"] if position_plan else None,
        "tp2_pct": position_plan["tp2_pct"] if position_plan else None,

        # 指標スナップショット
        "indicators_at_signal": {
            "rsi": round(float(indicators.get("rsi", 0)), 2),
            "macd": round(float(indicators.get("macd", 0)), 4),
            "macd_sig": round(float(indicators.get("macd_sig", 0)), 4),
            # 🆕 2026-05-28: MA は丸め桁を 4 桁に拡張（FX で同値化バグ回避）
            "ma25": round(float(indicators.get("ma25", 0)), 4),
            "ma75": round(float(indicators.get("ma75", 0)), 4),
            "bb_low": round(float(indicators.get("bb_low", 0)), 4),
            "bb_up": round(float(indicators.get("bb_up", 0)), 4),
            "recent_high": round(float(indicators.get("recent_high", 0)), 4),
            "recent_low": round(float(indicators.get("recent_low", 0)), 4),
            # 🆕 2026-05-28: ADX / Choppiness / 市況判定（Step C: 記録のみ、当面フィルタには使わない）
            "adx": round(float(indicators["adx"]), 2) if indicators.get("adx") is not None else None,
            "chop": round(float(indicators["chop"]), 2) if indicators.get("chop") is not None else None,
            "ma_dev_pct": indicators.get("ma_dev_pct"),
            "ma_dir": indicators.get("ma_dir"),
            "regime": indicators.get("regime"),
        },

        # 🆕 2026-06-03: S/R runway ＋ 選別(quality_tier) タグ（記録のみ・発火/メール/信頼度は不変）。
        # TP前にS/Rが挟まる取引(blocked)・tier別の実勝率を前向き検証するためのデータ蓄積。
        "sr_runway": sr_runway,
        "selection": selection,

        # ファンダ
        "news_count": len(news_titles or []),
        "news_titles": (news_titles or [])[:5],

        # AI 解説
        "ai_narrative": narrative or "",

        # 結果（後で evaluate_signal_outcomes.py が更新）
        "outcome": None,                 # "tp1" / "tp2" / "sl" / "expired" / null
        "outcome_resolved_at": None,
        "hit_tp1_at": None,
        "hit_tp2_at": None,
        "hit_sl_at": None,
        "max_favorable_excursion_pct": None,  # 最大含み益 %
        "max_adverse_excursion_pct": None,    # 最大含み損 %
    }
    return entry


def save_history(history):
    try:
        with open(ALERT_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ 履歴保存失敗: {e}")


def should_alert(history, symbol, signal_type, cooldown_hours=ALERT_COOLDOWN_HOURS):
    key = f"{symbol}:{signal_type}"
    last_iso = history.get(key)
    if not last_iso:
        return True
    try:
        last = datetime.fromisoformat(last_iso)
        if last.tzinfo is None:
            last = last.replace(tzinfo=JST)
        age = (datetime.now(JST) - last).total_seconds() / 3600.0
        return age >= cooldown_hours
    except Exception:
        return True


# ─────────────────────────────────────────────
# メイン
# ─────────────────────────────────────────────
def main():
    global ALERT_HISTORY_FILE  # timeframe で履歴ファイル名を切り替えるため

    # CLI 引数パース（簡易）
    import argparse
    parser = argparse.ArgumentParser(description="Technical signal alert generator")
    parser.add_argument("--timeframe", choices=["1h", "4h"], default="4h",
                        help="分析する時間軸（1h or 4h、デフォルト 4h）")
    parser.add_argument("--no-email", action="store_true",
                        help="メール送信を無効化（データ収集のみ）")
    args = parser.parse_args()
    timeframe = args.timeframe
    no_email = args.no_email

    gmail_user = os.environ.get("GMAIL_USER")
    gmail_password = os.environ.get("GMAIL_APP_PASSWORD")
    recipient = os.environ.get("ALERT_RECIPIENT") or gmail_user
    gemini_key = os.environ.get("GEMINI_API_KEY")

    if not no_email and (not gmail_user or not gmail_password):
        print("❌ GMAIL_USER / GMAIL_APP_PASSWORD が未設定です（--no-email なら不要）")
        sys.exit(1)

    # timeframe ごとに別ファイルでクールダウン管理
    history_file = "technical-alerts-history.json" if timeframe == "4h" else f"technical-alerts-history-{timeframe}.json"
    # 1H はクールダウンを短く（4H の 12h → 1H なら 4h）
    cooldown_hours = ALERT_COOLDOWN_HOURS if timeframe == "4h" else 4

    print(f"📡 {len(SYMBOLS)} 銘柄の {timeframe.upper()} 足チャート分析を開始 "
          f"(email={'OFF' if no_email else 'ON'}, cooldown={cooldown_hours}h)")

    # 履歴ロード（timeframe ごとに別ファイル）
    _orig_history_file = ALERT_HISTORY_FILE
    ALERT_HISTORY_FILE = history_file
    history = load_history()
    ALERT_HISTORY_FILE = _orig_history_file  # グローバル復元

    signals_log = load_signals_log()
    economic_events_data = load_economic_events()
    # 🆕 通貨強弱を 1 回だけ取得（全銘柄で共有）
    print("💪 通貨強弱（24h）を取得中...")
    currency_strength = calc_currency_strength()
    if currency_strength:
        sorted_strength = sorted([(c, v) for c, v in currency_strength.items() if v is not None],
                                  key=lambda x: -x[1])
        ranking = " > ".join([f"{c}({v:+.2f}%)" for c, v in sorted_strength])
        print(f"  📊 {ranking}")
    # 🆕 2026-05-29 Phase1: Layer0 リスク環境を 1 回だけ判定（市場共通スナップショット、記録のみ）
    print("🧭 リスク環境（Layer0）を判定中...")
    _vix_snapshot = fetch_vix_data()
    risk_regime = assess_risk_regime(currency_strength, _vix_snapshot)
    print(f"  🧭 リスク環境: {risk_regime['regime']} (score={risk_regime['score']}) | {' / '.join(risk_regime['factors'])}")
    # 🆕 2026-05-29 L2: ファンダ・ブリーフィングを 1 回読み込み（あれば Layer0/1 の主入力。記録のみ）
    fundamental_ctx = load_fundamental_context()
    if fundamental_ctx:
        _br = fundamental_ctx.get("risk_regime", {})
        print(f"  📰 ブリーフィング採用: regime={_br.get('regime')} ({_br.get('confidence')}) "
              f"generated={fundamental_ctx.get('generated_at')} / 資産 {len(fundamental_ctx.get('_bias_map', {}))} 件")
    else:
        print("  📰 ブリーフィングなし → 計算 regime のみ")
    total_signals = 0
    sent_emails = 0
    now_jst = datetime.now(JST)
    now_jst_str = now_jst.strftime("%Y-%m-%d %H:%M JST")
    now_iso = now_jst.isoformat(timespec="seconds")

    for ticker, name, currency, decimals, asset_cooldown_4h in SYMBOLS:
        # 銘柄別クールダウン: 4H ワークフローは銘柄ごと、1H ワークフローは一律 4h
        effective_cooldown = asset_cooldown_4h if timeframe == "4h" else cooldown_hours
        print(f"\n  📊 {name} ({ticker})")
        df = fetch_data(ticker, timeframe=timeframe)
        if df is None or len(df) < 30:
            print(f"    ⏭️ データ不足、スキップ")
            continue
        # 🆕 2026-05-28: 同 ticker/timeframe の直近シグナルを抽出して detect_signals に渡す（初押し検出用）
        # pullback_window=15 本 × timeframe + バッファ
        recent_lookback_hours = 15 * (4 if timeframe == "4h" else 1) + 12
        signals_log_recent = []
        for s in signals_log:
            if s.get("ticker") != ticker or s.get("timeframe") != timeframe:
                continue
            try:
                f_at = datetime.fromisoformat(s["fired_at"])
                if f_at.tzinfo is None:
                    f_at = f_at.replace(tzinfo=JST)
                if (now_jst - f_at).total_seconds() / 3600 <= recent_lookback_hours:
                    signals_log_recent.append(s)
            except Exception:
                continue

        # 🆕 2026-06-01: フィボ押し目シグナル用のファンダ方向（確信度 HIGH/MID のみ採用＝選別的）
        _fb_entry = briefing_bias_for(fundamental_ctx, ticker)
        _ticker_bias = _fb_entry.get("bias") if (_fb_entry and _fb_entry.get("conviction") in ("HIGH", "MID")) else None
        signals, indicators = detect_signals(
            df, signals_log_recent=signals_log_recent,
            ticker=ticker, timeframe=timeframe, now_jst=now_jst,
            fundamental_bias=_ticker_bias,
        )
        if not signals:
            print(f"    ✅ シグナルなし（現値 {currency}{indicators['price']:.{decimals}f}）")
            continue

        # 連投フィルタ（timeframe + 銘柄別クールダウン）
        fresh_signals = [s for s in signals if should_alert(history, ticker, s["type"], cooldown_hours=effective_cooldown)]
        if not fresh_signals:
            print(f"    ⏭️ {len(signals)} シグナル検出も、全てクールダウン中")
            continue

        total_signals += len(fresh_signals)
        price_str = f"{currency}{indicators['price']:.{decimals}f}"
        print(f"    🚨 新規シグナル {len(fresh_signals)} 件 [{timeframe.upper()}]: {[s['type'] for s in fresh_signals]}")

        # 🆕 2026-05-28: フィルタ初期化（メール送信判定、signals-log は常に残す）
        filter_send_email = True
        filter_block_reason = None

        # 🆕 2026-05-28: Step B - ma_golden 単独シグナルは無条件で送信スキップ
        # 検証 (N=11) で 0 勝。複合発火時は他シグナルが主導なので問題なし。
        if len(fresh_signals) == 1 and fresh_signals[0]["type"] == "ma_golden":
            filter_send_email = False
            filter_block_reason = "ma_golden 単独は過去 N=11 で 0 勝のため送信スキップ"
            print(f"    🚫 フィルタ: {filter_block_reason}")

        # 🆕 2026-05-28: 全シグナルが email_silent（初押し等の蓄積期間中シグナル）ならメール送信スキップ
        if filter_send_email and all(s.get("email_silent") for s in fresh_signals):
            filter_send_email = False
            silent_types = [s["type"] for s in fresh_signals]
            filter_block_reason = f"全シグナルが内部ログ専用 (email_silent): {silent_types}"
            print(f"    🔕 フィルタ: {filter_block_reason}")

        # ファンダメンタル：ティッカー関連ニュースを取得 → 日本語に翻訳
        news_titles_en = fetch_ticker_news(ticker, max_items=5)
        if news_titles_en:
            print(f"    📰 関連ニュース {len(news_titles_en)} 件 → 日本語翻訳")
            news_titles = translate_titles_to_jp(news_titles_en, gemini_key)
            ja_count = sum(1 for t in news_titles if any('぀' <= c <= '鿿' for c in (t or '')))
            print(f"    🌐 翻訳結果: {ja_count}/{len(news_titles)} 件が日本語化")
        else:
            news_titles = []

        # 🆕 環境警戒チェック（取引推奨度 A〜D 判定）
        env = check_environment(ticker, now_jst, df, indicators.get("atr", 0.0), news_titles, economic_events_data)
        print(f"    🛡️ 環境スコア: {env['env_score']} {env['score_label']} "
              f"| サイズ係数: {env['size_recommendation']['factor']:.2f} "
              f"({env['size_recommendation']['label']})")
        for w in env["warnings"]:
            print(f"       {w}")

        # ポジションプラン算出（ATR ベース、4H スイング想定）
        direction = determine_direction(fresh_signals)
        atr_val = indicators.get("atr", 0.0)
        position_plan = None
        if direction and atr_val > 0:
            position_plan = calc_entry_sl_tp(indicators["price"], atr_val, direction)
            print(f"    📐 ポジションプラン: {position_plan['direction']} "
                  f"SL={position_plan['stop_loss']:.{decimals}f} "
                  f"TP1={position_plan['take_profit_1']:.{decimals}f} "
                  f"(ATR={atr_val:.{decimals}f})")

        # 🆕 2026-05-28: Step A - モメンタムフィルタ（新案F）
        # entry_vs_ma25 × dsign > 0.5 OR momentum_score >= 1.0 でメール送信
        # バックテスト (N=139): 件数 1/4、勝率 32%→55%
        # 🆕 P1: 反転型パターン（double_top / double_bottom）はモメンタムと逆方向のため、
        #       フィルタをバイパスする（転換時点ではモメンタムがまだ逆を向いている）
        momentum_info = None
        has_reversal_pattern = any(s.get("is_reversal_pattern") or s.get("bypass_momentum") for s in fresh_signals)
        if filter_send_email and position_plan and has_reversal_pattern:
            # 反転型パターン / フィボ押し目（bypass_momentum）はモメンタムと逆方向のため、フィルタをバイパス
            momentum_info = calc_momentum_score(position_plan["entry"], direction, indicators)
            pattern_types = [s["type"] for s in fresh_signals if (s.get("is_reversal_pattern") or s.get("bypass_momentum"))]
            print(f"    🔄 反転型/押し目パターン検出 ({', '.join(pattern_types)}): モメンタムフィルタをバイパス")
        elif filter_send_email and position_plan:
            passed, reason, momentum_info = passes_momentum_filter(
                position_plan["entry"], direction, indicators
            )
            if not passed:
                filter_send_email = False
                filter_block_reason = f"モメンタム不足: {reason}"
                print(f"    🚫 フィルタ: {filter_block_reason}")
            else:
                print(f"    ✅ モメンタム通過: {reason}")
        elif filter_send_email and not position_plan:
            # 方向感なし（warn のみ等）→ メール送信スキップ
            filter_send_email = False
            filter_block_reason = "方向感なし（warn のみのシグナル）"
            print(f"    🚫 フィルタ: {filter_block_reason}")

        # 🆕 シグナル反転検知（往復ビンタ防止）
        position_direction = position_plan["direction"] if position_plan else None
        reversal = detect_reversal(signals_log, ticker, timeframe, position_direction, now_jst)
        if reversal["is_reversal"]:
            prev = reversal["previous_signal"]
            print(f"    🔄 反転検知: {reversal['hours_since_prev']}h 前に反対方向シグナル "
                  f"({prev.get('primary_signal_label', '')[:30]})")

        # 🆕 マルチタイムフレーム整合性チェック
        trend_align = check_trend_alignment(ticker, position_direction, timeframe) if position_direction else None
        if trend_align and trend_align.get("aligned") is not None:
            print(f"    📊 {trend_align['explanation']}")

        # 🆕 通貨強弱との整合性チェック（FX ペアのみ）
        fx_alignment = None
        if ticker in FX_PAIR_MAP and position_direction:
            fx_alignment = evaluate_currency_strength_alignment(ticker, position_direction, currency_strength)
            if fx_alignment and fx_alignment.get("aligned") is not None:
                print(f"    💪 {fx_alignment['explanation']}")

        # 🆕 AUD ペア専用：中国情勢取得
        china_ctx = build_china_context_for_aud(ticker, gemini_key)
        if china_ctx and china_ctx.get("market"):
            for tk, d in china_ctx["market"].items():
                print(f"       {d['name']}: {d['current']:,.2f} ({d['change_pct']:+.2f}%)")

        # Gemini 解説（テクニカル + ファンダ + 確定済プラン + 通貨強弱 + 中国コンテキストを渡す）
        narrative = generate_ai_narrative(
            name, price_str, fresh_signals, indicators, news_titles, position_plan,
            gemini_key, timeframe=timeframe,
            currency_strength=currency_strength, fx_alignment=fx_alignment,
            china_ctx=china_ctx,
        )

        # メール本文構築
        signal_block = "\n".join([f"- {s['label']}\n  {s['detail']}" for s in fresh_signals])
        news_block = ""
        if news_titles:
            news_block = "\n\n【参考にした直近ニュース】\n" + "\n".join([f"- {t}" for t in news_titles])

        # timeframe ごとの想定保有期間
        if timeframe == "1h":
            tf_label_display = "1H"
            hold_label_display = "数時間〜1 日（短期）"
        else:
            tf_label_display = "4H"
            hold_label_display = "1〜5 日（スイング）"

        # ポジションプラン表示ブロック
        if position_plan:
            plan_block = f"""【参考ポジションプラン】（{tf_label_display} 想定 / 保有 {hold_label_display}）
- 方向: {position_plan['direction']}
- エントリー: {currency}{position_plan['entry']:.{decimals}f}
- ストップロス: {currency}{position_plan['stop_loss']:.{decimals}f}（{position_plan['sl_pct']:+.2f}%）
- 利確 ①: {currency}{position_plan['take_profit_1']:.{decimals}f}（{position_plan['tp1_pct']:+.2f}% / R:R 1:1.3）
- 利確 ②: {currency}{position_plan['take_profit_2']:.{decimals}f}（{position_plan['tp2_pct']:+.2f}% / R:R 1:2.0）

📊 SL 根拠: ATR(14) = {currency}{position_plan['atr']:.{decimals}f} × 1.5
        （{tf_label_display} 足 1 本の自然な値動きの 1.5 倍 = 通常のヒゲでは刈られない幅）
"""
        else:
            plan_block = """【参考ポジションプラン】
- 方向感が定まらないシグナル構成のため、今回は数値プランなし（様子見推奨）
"""

        # 🆕 B2: 信頼度スコア算出（body / subject で参照するため事前に計算）
        confidence = calc_confidence_score(fresh_signals, env, trend_align, reversal, fx_alignment)

        body = f"""━━━━━━━━━━━━━━━━━━━━━
{name}（{ticker}）
現在価格: {price_str}
判定時刻: {now_jst_str}
時間足: {tf_label_display} / 想定保有: {hold_label_display}
━━━━━━━━━━━━━━━━━━━━━

【発火シグナル】
{signal_block}

{_build_currency_strength_block(currency_strength, fx_alignment) if ticker in FX_PAIR_MAP else ''}{_build_china_block(china_ctx)}{_build_whipsaw_block(reversal, trend_align)}{_build_confidence_block(confidence)}{_build_environment_block(env, currency, decimals)}
{plan_block}
【AI 解説（テクニカル + ファンダメンタル）】
{narrative or '（解説の生成に失敗）'}

【テクニカル指標】
- RSI: {indicators['rsi']:.1f}
- MACD: {indicators['macd']:.4f}（シグナル {indicators['macd_sig']:.4f}）
- 25MA: {indicators['ma25']:.{decimals}f} / 75MA: {indicators['ma75']:.{decimals}f}
- ボリンジャー: -2σ {indicators['bb_low']:.{decimals}f} / +2σ {indicators['bb_up']:.{decimals}f}
- 直近 20 本: 高値 {indicators['recent_high']:.{decimals}f} / 安値 {indicators['recent_low']:.{decimals}f}
- ATR(14): {currency}{indicators.get('atr', 0):.{decimals}f}（1 本の平均的な値動き幅）
{news_block}

━━━━━━━━━━━━━━━━━━━━━
⚠️ AI による参考シグナルです。
   SL/TP は ATR ベースの機械算出値であり、ニュース・需給は反映していません。
   投資判断は自己責任で行ってください。
━━━━━━━━━━━━━━━━━━━━━
MarketWatch AI Alerts
"""

        # 主シグナルから件名を組み立て（環境警告プレフィックス付）
        # R2: スマホ件名表示で切れないよう、コンパクト化（目安 50 文字以内）
        primary = fresh_signals[0]
        emoji = {"buy": "🟢", "sell": "🔴", "warn": "🟡"}.get(primary["severity"], "📊")
        # 件名プレフィックス: D=🚫 / C=⛔ / B=⚠️ / A= (なし)
        env_prefix = {"D": "🚫 ", "C": "⛔ ", "B": "⚠️ "}.get(env["env_score"], "")
        # 反転タグ
        reversal_tag = "🔄 " if reversal and reversal.get("is_reversal") else ""
        # R2: トレンドタグを矢印 1 文字に短縮（順張り ↑ / 逆張り ↓）
        trend_tag = ""
        if trend_align and trend_align.get("aligned") is True:
            trend_tag = " ↑"
        elif trend_align and trend_align.get("aligned") is False:
            trend_tag = " ↓"

        # B2: 信頼度タグ
        conf_tag = f" {confidence['stars']}"

        # 🆕 H2: 当日市場休場タグ（薄商い警告）
        holiday_tag = ""
        mh = env.get("market_holidays") or {}
        if mh.get("today_holidays"):
            countries = sorted(set(h["country"] for h in mh["today_holidays"]))
            holiday_tag = f" 🏖️{'/'.join(countries)}休"

        # R2: 「シグナル:」ラベルを省略してコンパクト化
        sig_label = primary['label'].split('（')[0].strip()
        subject = f"{reversal_tag}{env_prefix}{emoji} {name} {tf_label_display} {sig_label}{trend_tag}{conf_tag}{holiday_tag}"
        # 重要指標が 24h 以内ならその名前も件名に（R2: 「まで」「発表」「（X月）」を削除）
        if env["upcoming_events"]:
            nearest = env["upcoming_events"][0]
            if nearest["hours_until"] <= 24:
                import re as _re_short
                short_name = nearest['name']
                short_name = _re_short.sub(r'発表', '', short_name)
                short_name = _re_short.sub(r'（[^）]*）', '', short_name)
                short_name = short_name.strip()
                if len(short_name) > 12:
                    short_name = short_name[:12]
                subject += f" /{short_name} {nearest['hours_until']:.0f}h"

        # 送信（--no-email 時は完全スキップ、フィルタで弾かれた場合もスキップ）
        # 🆕 2026-05-28: filter_send_email が False なら記録のみでメール送信せず
        email_sent = False
        if no_email:
            print(f"    🔇 メール送信スキップ（--no-email モード、データ収集のみ）")
            # 履歴更新（クールダウン目的）はメール送らなくても必要
            for s in fresh_signals:
                history[f"{ticker}:{s['type']}"] = datetime.now(JST).isoformat(timespec="seconds")
        elif not filter_send_email:
            print(f"    🔇 メール送信スキップ（{filter_block_reason}、ログには記録）")
            # クールダウン履歴は更新（連投防止のため）
            for s in fresh_signals:
                history[f"{ticker}:{s['type']}"] = datetime.now(JST).isoformat(timespec="seconds")
        else:
            try:
                send_email(subject, body, gmail_user, gmail_password, recipient)
                print(f"    📧 メール送信完了: {recipient}")
                sent_emails += 1
                email_sent = True
                for s in fresh_signals:
                    history[f"{ticker}:{s['type']}"] = datetime.now(JST).isoformat(timespec="seconds")
            except Exception as e:
                print(f"    ❌ メール送信失敗: {type(e).__name__}: {str(e)[:80]}")

        # シグナルログに記録（メール送信成否・モードに関わらず、シグナル発火事実は残す）
        log_entry = build_signal_log_entry(
            ticker=ticker, name=name, fresh_signals=fresh_signals,
            indicators=indicators, position_plan=position_plan,
            news_titles=news_titles, narrative=narrative,
            fired_at_iso=now_iso, timeframe=timeframe,
        )
        log_entry["email_sent"] = email_sent
        # 🆕 往復ビンタ防止データを記録
        log_entry["whipsaw_check"] = {
            "is_reversal": reversal.get("is_reversal") if reversal else False,
            "hours_since_prev": reversal.get("hours_since_prev") if reversal else None,
            "prev_direction": reversal.get("prev_direction") if reversal else None,
            "prev_signal_id": (reversal.get("previous_signal") or {}).get("id") if reversal else None,
        }
        log_entry["trend_alignment"] = {
            "aligned": trend_align.get("aligned") if trend_align else None,
            "higher_tf": trend_align.get("higher_tf") if trend_align else None,
            "higher_tf_trend": trend_align.get("higher_tf_trend") if trend_align else None,
            "explanation": trend_align.get("explanation") if trend_align else "",
        }
        # 🆕 通貨強弱データを記録（全銘柄共通スナップショット）
        log_entry["currency_strength"] = currency_strength
        # 🆕 2026-05-29 Phase1: トップダウン層を記録（記録のみ・発火には未使用、検証用）
        _dir = log_entry.get("direction", "")
        _sigdir = "long" if "ロング" in _dir else ("short" if "ショート" in _dir else "neutral")
        log_entry["risk_regime"] = risk_regime
        log_entry["directional_bias"] = assess_directional_bias(ticker, risk_regime["regime"], _sigdir)
        # 🆕 2026-05-29 L2: ブリーフィング由来の方向観との一致を記録（記録のみ・発火未使用）
        _fb = briefing_bias_for(fundamental_ctx, ticker)
        _brief_bias = _fb.get("bias") if _fb else None  # BULLISH / BEARISH / NEUTRAL
        _brief_allowed = {"BULLISH": "long", "BEARISH": "short"}.get(_brief_bias)
        _brief_aligned = (_brief_allowed == _sigdir) if (_brief_allowed and _sigdir in ("long", "short")) else None
        log_entry["fundamental_context"] = {
            "available": fundamental_ctx is not None,
            "source": "briefing" if fundamental_ctx else "computed",
            "briefing_generated_at": fundamental_ctx.get("generated_at") if fundamental_ctx else None,
            "regime": (fundamental_ctx.get("risk_regime", {}).get("regime") if fundamental_ctx else risk_regime["regime"]),
            "regime_confidence": (fundamental_ctx.get("risk_regime", {}).get("confidence") if fundamental_ctx else None),
            "asset_bias": _brief_bias,
            "asset_conviction": (_fb.get("conviction") if _fb else None),
            "signal_direction": _sigdir,
            "bias_aligned": _brief_aligned,
        }
        # 🆕 FX 整合性データ（FX ペアのみ）
        log_entry["fx_alignment"] = fx_alignment
        # 🆕 中国コンテキスト（AUD ペアのみ）
        log_entry["china_context"] = china_ctx
        # 🆕 B2: 信頼度スコアを記録
        log_entry["confidence"] = confidence
        # 🆕 2026-05-28: モメンタムフィルタ判定とスコアを記録（次回検証用）
        log_entry["momentum_filter"] = {
            "passed": filter_send_email,
            "reason": filter_block_reason if not filter_send_email else "通過",
            "score": momentum_info["score"] if momentum_info else None,
            "entry_vs_ma25_signed": momentum_info["entry_vs_ma25_signed"] if momentum_info else None,
            "range_pos": momentum_info["range_pos"] if momentum_info else None,
            "ma_ratio_pct": momentum_info["ma_ratio_pct"] if momentum_info else None,
        }
        # 🆕 環境警戒データを記録（明日の集計タブ用）
        log_entry["environment"] = {
            "env_score": env["env_score"],
            "score_label": env["score_label"],
            "size_factor": env["size_recommendation"]["factor"],
            "size_label": env["size_recommendation"]["label"],
            "warnings": env["warnings"],
            "danger_count": env["danger_count"],
            "upcoming_events": env["upcoming_events"],
            "vix": env["vix"],
            "atr_regime": env["atr_regime"],
            "crisis_news": env["crisis_news"],
        }
        signals_log.append(log_entry)
        print(f"    📒 シグナルログに記録: id={log_entry['id']} env={env['env_score']}")

    # 履歴保存（timeframe 別ファイル）
    _orig_for_save = ALERT_HISTORY_FILE
    ALERT_HISTORY_FILE = history_file
    save_history(history)
    ALERT_HISTORY_FILE = _orig_for_save

    save_signals_log(signals_log)
    print(f"\n━━━━━━━━━━━━━━━━━━━━━")
    print(f"完了 [{timeframe.upper()}]: 新規シグナル {total_signals} 件 / "
          f"メール {sent_emails} 通送信 / ログ累計 {len(signals_log)} 件")


if __name__ == "__main__":
    main()
