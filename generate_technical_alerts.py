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
    ("GC=F",     "ゴールド先物",         "$", 2),
    ("CL=F",     "原油 WTI 先物",        "$", 2),
    ("NKD=F",    "日経 225 先物 (CME)",  "",  0),
    ("USDJPY=X", "ドル円",               "¥", 3),
    ("BTC-USD",  "ビットコイン",         "$", 0),
]

ALERT_HISTORY_FILE = "technical-alerts-history.json"
ALERT_COOLDOWN_HOURS = 12  # 同じ銘柄・同じシグナルは 12 時間連投しない


# ─────────────────────────────────────────────
# 4H データ取得（yfinance の 1h → 4h リサンプル）
# ─────────────────────────────────────────────
def fetch_4h_data(symbol, days=30):
    """yfinance で 1h 足を取得し 4h にリサンプル"""
    try:
        df = yf.download(symbol, period=f"{days}d", interval="1h", progress=False, auto_adjust=True)
        if df.empty:
            return None
        # MultiIndex 列の場合は単一銘柄なので flatten
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        # 4H リサンプル
        agg = {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}
        df_4h = df.resample("4h").agg(agg).dropna(subset=["Close"])
        return df_4h
    except Exception as e:
        print(f"  ⚠️ {symbol} データ取得失敗: {type(e).__name__}: {str(e)[:80]}")
        return None


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
# Gemini で「なぜこのシグナルか」の解説生成（テクニカル + ニュース）
# ─────────────────────────────────────────────
def generate_ai_narrative(asset_name, current_price_str, signals, indicators, news_titles, api_key):
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

    prompt = f"""あなたは日本人個人投資家向けのテクニカル + ファンダメンタル アナリストです。
{asset_name}（現在 {current_price_str}）の 4H 足チャートで以下のシグナルが発火しました。
テクニカルシグナルと、直近のニュース（ファンダメンタル）の両面から、参考エントリー・ストップ・利確の目安を簡潔に解説してください。

【発火シグナル（テクニカル）】
{signal_lines}

【テクニカル指標】
- RSI: {indicators['rsi']:.1f}
- MACD: {indicators['macd']:.4f} / シグナル: {indicators['macd_sig']:.4f}
- 25MA: {indicators['ma25']:.2f} / 75MA: {indicators['ma75']:.2f}
- ボリンジャー: -2σ {indicators['bb_low']:.2f} / +2σ {indicators['bb_up']:.2f}
- 直近 20 本: 高値 {indicators['recent_high']:.2f} / 安値 {indicators['recent_low']:.2f}
{news_section}

【出力フォーマット】（プレーンテキスト、200 字以内）
2〜3 文。テクニカル要因とファンダ要因の両方に触れる。参考価格は具体的に。「〜の可能性」「〜要注意」など慎重表現。ニュースに該当する材料がなければ「足元のニュース材料は限定的」と書く。"""

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
    gmail_user = os.environ.get("GMAIL_USER")
    gmail_password = os.environ.get("GMAIL_APP_PASSWORD")
    recipient = os.environ.get("ALERT_RECIPIENT") or gmail_user
    gemini_key = os.environ.get("GEMINI_API_KEY")

    if not gmail_user or not gmail_password:
        print("❌ GMAIL_USER / GMAIL_APP_PASSWORD が未設定です")
        sys.exit(1)

    print(f"📡 {len(SYMBOLS)} 銘柄の 4H チャート分析を開始...")
    history = load_history()
    total_signals = 0
    sent_emails = 0
    now_jst_str = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")

    for ticker, name, currency, decimals in SYMBOLS:
        print(f"\n  📊 {name} ({ticker})")
        df = fetch_4h_data(ticker)
        if df is None or len(df) < 30:
            print(f"    ⏭️ データ不足、スキップ")
            continue
        signals, indicators = detect_signals(df)
        if not signals:
            print(f"    ✅ シグナルなし（現値 {currency}{indicators['price']:.{decimals}f}）")
            continue

        # 連投フィルタ
        fresh_signals = [s for s in signals if should_alert(history, ticker, s["type"])]
        if not fresh_signals:
            print(f"    ⏭️ {len(signals)} シグナル検出も、全てクールダウン中")
            continue

        total_signals += len(fresh_signals)
        price_str = f"{currency}{indicators['price']:.{decimals}f}"
        print(f"    🚨 新規シグナル {len(fresh_signals)} 件: {[s['type'] for s in fresh_signals]}")

        # ファンダメンタル：ティッカー関連ニュースを取得
        news_titles = fetch_ticker_news(ticker, max_items=5)
        if news_titles:
            print(f"    📰 関連ニュース {len(news_titles)} 件を Gemini に併せて渡します")

        # Gemini 解説（テクニカル + ファンダ）
        narrative = generate_ai_narrative(name, price_str, fresh_signals, indicators, news_titles, gemini_key)

        # メール本文構築
        signal_block = "\n".join([f"- {s['label']}\n  {s['detail']}" for s in fresh_signals])
        news_block = ""
        if news_titles:
            news_block = "\n\n【参考にした直近ニュース】\n" + "\n".join([f"- {t}" for t in news_titles])
        body = f"""━━━━━━━━━━━━━━━━━━━━━
{name}（{ticker}）
現在価格: {price_str}
判定時刻: {now_jst_str}
時間足: 4H
━━━━━━━━━━━━━━━━━━━━━

【発火シグナル】
{signal_block}

【AI 解説（テクニカル + ファンダメンタル）】
{narrative or '（解説の生成に失敗）'}

【テクニカル指標】
- RSI: {indicators['rsi']:.1f}
- MACD: {indicators['macd']:.4f}（シグナル {indicators['macd_sig']:.4f}）
- 25MA: {indicators['ma25']:.{decimals}f} / 75MA: {indicators['ma75']:.{decimals}f}
- ボリンジャー: -2σ {indicators['bb_low']:.{decimals}f} / +2σ {indicators['bb_up']:.{decimals}f}
- 直近 20 本: 高値 {indicators['recent_high']:.{decimals}f} / 安値 {indicators['recent_low']:.{decimals}f}
{news_block}

━━━━━━━━━━━━━━━━━━━━━
⚠️ AI による参考シグナルです。
   投資判断は自己責任で行ってください。
━━━━━━━━━━━━━━━━━━━━━
MarketWatch AI Alerts
"""

        # 主シグナルから件名を組み立て
        primary = fresh_signals[0]
        emoji = {"buy": "🟢", "sell": "🔴", "warn": "🟡"}.get(primary["severity"], "📊")
        subject = f"{emoji} {name} 4H シグナル: {primary['label'].split('（')[0].strip()}"

        # 送信
        try:
            send_email(subject, body, gmail_user, gmail_password, recipient)
            print(f"    📧 メール送信完了: {recipient}")
            sent_emails += 1
            # 履歴更新
            for s in fresh_signals:
                history[f"{ticker}:{s['type']}"] = datetime.now(JST).isoformat(timespec="seconds")
        except Exception as e:
            print(f"    ❌ メール送信失敗: {type(e).__name__}: {str(e)[:80]}")

    save_history(history)
    print(f"\n━━━━━━━━━━━━━━━━━━━━━")
    print(f"完了: 新規シグナル {total_signals} 件 / メール {sent_emails} 通送信")


if __name__ == "__main__":
    main()
