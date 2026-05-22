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
    ("GC=F",     "ゴールド先物",         "$", 2, 12),
    ("CL=F",     "原油 WTI 先物",        "$", 2, 24),  # ニュース感応度高、往復ビンタ多発のため長めに
    ("NKD=F",    "日経 225 先物 (CME)",  "",  0, 12),
    ("USDJPY=X", "ドル円",               "¥", 3, 18),  # 介入リスク考慮で長めに
    ("BTC-USD",  "ビットコイン",         "$", 0, 12),
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
def detect_signals(df_4h):
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

    # ボリンジャー -2σ タッチ（反発期待）
    if low.iloc[-1] <= bb_low_cur and cur > low.iloc[-1]:
        signals.append({
            "type": "bb_lower_touch",
            "severity": "buy",
            "label": "🟢 ボリンジャー -2σ タッチ（反発期待）",
            "detail": f"-2σ ({bb_low_cur:.2f}) に接触後、反発の兆し",
        })

    # ボリンジャー +2σ 突破（過熱）
    if cur > bb_up_cur and prev <= bb_up_cur:
        signals.append({
            "type": "bb_upper_break",
            "severity": "warn",
            "label": "🟡 ボリンジャー +2σ 突破（過熱注意）",
            "detail": f"+2σ ({bb_up_cur:.2f}) を上抜け",
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
    """ticker に関係する直近イベントを取得。
    返り値: list of {name, hours_until, impact}（近い順）"""
    relevant = []
    for ev in events_data.get("events", []):
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
    返り値: dict with upcoming_events, vix, atr_regime, crisis_news, env_score, size_rec, warnings
    """
    upcoming = check_upcoming_events(ticker, now_jst, events_data)
    vix = fetch_vix_data()
    atr_regime = calc_atr_regime(df, current_atr) if current_atr > 0 else None
    crisis = check_crisis_keywords(news_titles, events_data.get("crisis_keywords", {}))

    # スコア判定
    warnings = []
    danger_count = 0

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
def generate_ai_narrative(asset_name, current_price_str, signals, indicators, news_titles, position_plan, api_key, timeframe="4h"):
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
{plan_section}
{news_section}

【出力フォーマット】（プレーンテキスト、250 字以内）
2〜3 文。テクニカル要因（なぜこの方向か）とファンダ要因（ニュース材料との整合性）の両方に触れる。
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


def build_signal_log_entry(ticker, name, fresh_signals, indicators, position_plan,
                            news_titles, narrative, fired_at_iso, timeframe="4h"):
    """1 アラート発火を構造化レコードに整形"""
    primary = fresh_signals[0]
    # ID: 例 "GC=F_4h_20260520_2130" / "GC=F_1h_20260520_2130"
    dt_compact = datetime.fromisoformat(fired_at_iso).strftime("%Y%m%d_%H%M")
    record_id = f"{ticker}_{timeframe}_{dt_compact}"

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
            "ma25": round(float(indicators.get("ma25", 0)), 2),
            "ma75": round(float(indicators.get("ma75", 0)), 2),
            "bb_low": round(float(indicators.get("bb_low", 0)), 2),
            "bb_up": round(float(indicators.get("bb_up", 0)), 2),
            "recent_high": round(float(indicators.get("recent_high", 0)), 2),
            "recent_low": round(float(indicators.get("recent_low", 0)), 2),
        },

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
        signals, indicators = detect_signals(df)
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

        # Gemini 解説（テクニカル + ファンダ + 確定済プランを渡す）
        narrative = generate_ai_narrative(name, price_str, fresh_signals, indicators, news_titles, position_plan, gemini_key, timeframe=timeframe)

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

        body = f"""━━━━━━━━━━━━━━━━━━━━━
{name}（{ticker}）
現在価格: {price_str}
判定時刻: {now_jst_str}
時間足: {tf_label_display} / 想定保有: {hold_label_display}
━━━━━━━━━━━━━━━━━━━━━

【発火シグナル】
{signal_block}

{_build_whipsaw_block(reversal, trend_align)}{_build_environment_block(env, currency, decimals)}
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
        primary = fresh_signals[0]
        emoji = {"buy": "🟢", "sell": "🔴", "warn": "🟡"}.get(primary["severity"], "📊")
        # 件名プレフィックス: D=🚫 / C=⛔ / B=⚠️ / A= (なし)
        env_prefix = {"D": "🚫 ", "C": "⛔ ", "B": "⚠️ "}.get(env["env_score"], "")
        # 🆕 反転・トレンドタグ
        reversal_tag = "🔄 " if reversal and reversal.get("is_reversal") else ""
        trend_tag = ""
        if trend_align and trend_align.get("aligned") is True:
            trend_tag = " [✅順張り]"
        elif trend_align and trend_align.get("aligned") is False:
            trend_tag = " [⚠️逆張り]"

        subject = f"{reversal_tag}{env_prefix}{emoji} {name} {tf_label_display} シグナル: {primary['label'].split('（')[0].strip()}{trend_tag}"
        # 重要指標が 24h 以内ならその名前も件名に
        if env["upcoming_events"]:
            nearest = env["upcoming_events"][0]
            if nearest["hours_until"] <= 24:
                subject += f" / {nearest['name']}まで {nearest['hours_until']:.0f}h"

        # 送信（--no-email 時は完全スキップ）
        email_sent = False
        if no_email:
            print(f"    🔇 メール送信スキップ（--no-email モード、データ収集のみ）")
            # 履歴更新（クールダウン目的）はメール送らなくても必要
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
