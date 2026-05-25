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

🆕 SL ヒット時には Gemini が「敗因分析」を自動生成して loss_analysis に保存。

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


# ─────────────────────────────────────────────
# 敗因分析（SL ヒット時のみ呼ばれる）
# ─────────────────────────────────────────────
def get_vix_change(start_dt_utc, end_dt_iso):
    """シグナル発火から SL ヒットまでの VIX 変動率を計算"""
    try:
        end_dt = datetime.fromisoformat(end_dt_iso)
        end_utc = end_dt.astimezone(timezone.utc)
        df = yf.download("^VIX",
                         start=start_dt_utc.strftime("%Y-%m-%d"),
                         end=(end_utc + timedelta(days=1)).strftime("%Y-%m-%d"),
                         interval="1h", progress=False, auto_adjust=True)
        if df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")
        df_start = df[df.index >= start_dt_utc]
        df_end = df[df.index <= end_utc]
        if df_start.empty or df_end.empty:
            return None
        vix_start = float(df_start["Close"].iloc[0])
        vix_end = float(df_end["Close"].iloc[-1])
        return {
            "start": round(vix_start, 2),
            "end": round(vix_end, 2),
            "change_pct": round((vix_end - vix_start) / vix_start * 100, 2),
        }
    except Exception as e:
        print(f"    ⚠️ VIX 取得失敗: {type(e).__name__}: {str(e)[:60]}")
        return None


def get_news_during_holding(ticker, start_iso, end_iso, max_items=8):
    """保有期間中の関連ニュース見出しを取得（yfinance の最新ニュースから date でフィルタ）"""
    try:
        news = yf.Ticker(ticker).news or []
    except Exception:
        return []
    try:
        start_dt = datetime.fromisoformat(start_iso)
        end_dt = datetime.fromisoformat(end_iso)
    except Exception:
        return []
    titles = []
    for n in news:
        content = n.get("content", n)
        title = content.get("title", "") or n.get("title", "")
        # 発行時刻を取得
        pub_str = content.get("pubDate") or n.get("providerPublishTime") or n.get("displayTime")
        try:
            if isinstance(pub_str, (int, float)):
                pub_dt = datetime.fromtimestamp(pub_str, tz=timezone.utc)
            else:
                pub_dt = datetime.fromisoformat(str(pub_str).replace("Z", "+00:00"))
            # 期間内チェック
            if start_dt <= pub_dt.astimezone(JST) <= end_dt and title:
                titles.append(title)
        except Exception:
            # 発行時刻が取れないものは含める（直近ニュースの可能性高）
            if title and title not in titles:
                titles.append(title)
        if len(titles) >= max_items:
            break
    return titles[:max_items]


def translate_titles_to_jp_quick(titles, api_key):
    """ニュース見出しを日本語に翻訳（generate_technical_alerts.py と同じ実装の縮小版）"""
    if not titles or not api_key:
        return titles or []
    import re
    has_ja = re.compile(r'[぀-ヿ一-鿿]')
    targets = [(i, t) for i, t in enumerate(titles) if t and not has_ja.search(t)]
    if not targets:
        return titles
    try:
        import google.generativeai as genai
    except ImportError:
        return titles
    genai.configure(api_key=api_key)
    numbered = "\n".join([f"{i+1}. {t}" for i, (_, t) in enumerate(targets)])
    prompt = f"次の英語ニュース見出しを日本語に翻訳。番号付き行のみ出力:\n{numbered}"
    text = ""
    for m in ("gemini-2.0-flash-lite", "gemini-2.5-flash-lite", "gemini-2.0-flash"):
        try:
            text = (genai.GenerativeModel(m).generate_content(prompt).text or "").strip()
            if text:
                break
        except Exception:
            continue
    if not text:
        return titles
    translations = {}
    for line in text.splitlines():
        m = re.match(r'^\s*(\d+)[.\)]\s*(.+)$', line.strip())
        if m:
            n = int(m.group(1)) - 1
            if 0 <= n < len(targets):
                translations[targets[n][0]] = m.group(2).strip()
    result = list(titles)
    for orig_idx, jp in translations.items():
        result[orig_idx] = jp
    return result


def analyze_loss_with_ai(entry, sl_ts_iso, news_titles, vix_data, api_key):
    """Gemini で敗因を 5 カテゴリ + 詳細 + 教訓で分析。
    JSON 構造で返す: {primary_category, primary_cause, ai_diagnosis, lesson, category_tag}"""
    if not api_key:
        return None
    try:
        import google.generativeai as genai
    except ImportError:
        return None
    genai.configure(api_key=api_key)

    fired_at = entry.get("fired_at", "")
    indicators = entry.get("indicators_at_signal", {})
    direction = entry.get("direction", "")
    asset = entry.get("asset_name", "")
    timeframe = entry.get("timeframe", "4h")
    entry_price = entry.get("entry")
    sl_price = entry.get("stop_loss")
    atr = entry.get("atr", 0)
    original_narrative = entry.get("ai_narrative", "")

    news_section = ""
    if news_titles:
        news_section = "\n\n【保有期間中の関連ニュース】\n" + "\n".join([f"- {t[:140]}" for t in news_titles[:6]])

    vix_section = ""
    if vix_data:
        vix_section = f"\n\n【VIX 変動】{vix_data['start']} → {vix_data['end']}（{vix_data['change_pct']:+.1f}%）"

    prompt = f"""あなたは日本人個人投資家向けのトレード分析アナリストです。
以下のシグナル経由のトレードが SL（ストップロス）にヒットしました。
**「なぜ失敗したのか」を客観的に分析**してください。シグナルを批判する目的ではなく、次回への教訓を抽出するためです。

【トレード詳細】
- 銘柄: {asset}
- 時間軸: {timeframe.upper()}
- 方向: {direction}
- エントリー: {entry_price} @ {fired_at}
- SL ヒット: {sl_price} @ {sl_ts_iso}
- ATR(14): {atr:.2f}

【シグナル発火時の指標】
- RSI: {indicators.get('rsi', 'N/A')}
- MACD: {indicators.get('macd', 'N/A')}
- 25MA: {indicators.get('ma25', 'N/A')}
- 75MA: {indicators.get('ma75', 'N/A')}

【シグナル発火時の AI 解説（参考）】
{original_narrative[:300]}
{vix_section}
{news_section}

【出力フォーマット】（純粋な JSON のみ。前置きや コードフェンス不要）
{{
  "primary_category": "テクニカル悪化 / ファンダメンタル / 地政学・突発 / ボラ拡大 / シグナル品質 のいずれか",
  "primary_cause": "1 文で具体的な敗因（30 字以内）",
  "ai_diagnosis": "詳細解説 (200 字以内)。データに基づいて何が起きたかを説明",
  "lesson": "次回への教訓 (80 字以内)。実行可能な改善案",
  "category_tag": "短いラベル (10 字以内、例: イベント・リスクオフ / トレンド逆行 / ボラ爆発 / 弱シグナル)"
}}"""

    text = ""
    for model_name in ("gemini-2.5-flash-lite", "gemini-2.0-flash-lite", "gemini-2.5-flash"):
        try:
            model = genai.GenerativeModel(model_name)
            resp = model.generate_content(prompt)
            text = (resp.text or "").strip()
            if text:
                break
        except Exception:
            continue
    if not text:
        return None

    # JSON 抽出（コードフェンスがあれば除去）
    text = text.strip()
    if text.startswith("```"):
        # ```json ... ``` をはぎ取る
        text = text.split("```", 2)[1] if "```" in text else text
        if text.startswith("json"):
            text = text[4:].strip()
    try:
        result = json.loads(text)
        return result
    except Exception as e:
        print(f"    ⚠️ AI 敗因分析の JSON パース失敗: {e}; 生応答先頭: {text[:80]}")
        return {"raw_response": text[:500]}


def analyze_win_with_ai(entry, win_ts_iso, outcome_label, news_titles, vix_data, api_key):
    """🆕 R4: TP1/TP2 到達時に Gemini で勝因を 5 カテゴリ + 詳細 + 教訓で分析。
    JSON 構造で返す: {primary_category, primary_cause, ai_diagnosis, lesson, category_tag, repeatable}"""
    if not api_key:
        return None
    try:
        import google.generativeai as genai
    except ImportError:
        return None
    genai.configure(api_key=api_key)

    fired_at = entry.get("fired_at", "")
    indicators = entry.get("indicators_at_signal", {})
    direction = entry.get("direction", "")
    asset = entry.get("asset_name", "")
    timeframe = entry.get("timeframe", "4h")
    entry_price = entry.get("entry")
    target_price = entry.get("take_profit_1") if outcome_label == "tp1" else entry.get("take_profit_2")
    atr = entry.get("atr", 0)
    original_narrative = entry.get("ai_narrative", "")
    confidence = entry.get("confidence") or {}
    env = entry.get("environment") or {}
    trend_align = entry.get("trend_alignment") or {}
    whipsaw = entry.get("whipsaw_check") or {}

    news_section = ""
    if news_titles:
        news_section = "\n\n【保有期間中の関連ニュース】\n" + "\n".join([f"- {t[:140]}" for t in news_titles[:6]])

    vix_section = ""
    if vix_data:
        vix_section = f"\n\n【VIX 変動】{vix_data['start']} → {vix_data['end']}（{vix_data['change_pct']:+.1f}%）"

    # 信頼度・環境・整合性データ
    context_lines = []
    if confidence.get("label"):
        context_lines.append(f"信頼度スコア: {confidence.get('label')} ({confidence.get('score', '?')})")
    if env.get("env_score"):
        context_lines.append(f"環境スコア: {env.get('env_score')} {env.get('score_label', '')}")
    if trend_align.get("aligned") is not None:
        align_str = "順張り (上位足整合)" if trend_align.get("aligned") else "逆張り (上位足逆)"
        context_lines.append(f"マルチTF整合: {align_str}")
    if whipsaw.get("is_reversal"):
        context_lines.append("反転検知: あり (往復ビンタ警告下でのトレード)")
    context_section = ""
    if context_lines:
        context_section = "\n\n【シグナル発火時の付加コンテキスト】\n" + "\n".join([f"- {c}" for c in context_lines])

    prompt = f"""あなたは日本人個人投資家向けのトレード分析アナリストです。
以下のシグナル経由のトレードが {outcome_label.upper()}（利確）に到達して成功しました。
**「なぜ成功したのか」を客観的に分析**してください。次回も同じ条件で積極的にエントリーする / サイズを上げるべきかの判断材料を抽出するためです。

【トレード詳細】
- 銘柄: {asset}
- 時間軸: {timeframe.upper()}
- 方向: {direction}
- エントリー: {entry_price} @ {fired_at}
- {outcome_label.upper()} 到達: {target_price} @ {win_ts_iso}
- ATR(14): {atr:.2f}

【シグナル発火時の指標】
- RSI: {indicators.get('rsi', 'N/A')}
- MACD: {indicators.get('macd', 'N/A')}
- 25MA: {indicators.get('ma25', 'N/A')}
- 75MA: {indicators.get('ma75', 'N/A')}

【シグナル発火時の AI 解説（参考）】
{original_narrative[:300]}
{context_section}{vix_section}{news_section}

【出力フォーマット】（純粋な JSON のみ。前置きや コードフェンス不要）
{{
  "primary_category": "テクニカル順当 / トレンド継続 / 環境追い風 / 信頼度高の的中 / マルチTF整合 のいずれか",
  "primary_cause": "1 文で具体的な勝因（30 字以内）",
  "ai_diagnosis": "詳細解説 (200 字以内)。データに基づいて何が機能したかを説明",
  "lesson": "次回への教訓 (80 字以内)。同条件再現時のアクション提案",
  "category_tag": "短いラベル (10 字以内、例: 順張り高精度 / イベント追い風 / 信頼度的中 / ボラ穏当)",
  "repeatable": "high/medium/low のいずれか。同じ条件が再現した時の期待値が高いほど high"
}}"""

    text = ""
    for model_name in ("gemini-2.5-flash-lite", "gemini-2.0-flash-lite", "gemini-2.5-flash"):
        try:
            model = genai.GenerativeModel(model_name)
            resp = model.generate_content(prompt)
            text = (resp.text or "").strip()
            if text:
                break
        except Exception:
            continue
    if not text:
        return None

    # JSON 抽出
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1] if "```" in text else text
        if text.startswith("json"):
            text = text[4:].strip()
    try:
        result = json.loads(text)
        return result
    except Exception as e:
        print(f"    ⚠️ AI 勝因分析の JSON パース失敗: {e}; 生応答先頭: {text[:80]}")
        return {"raw_response": text[:500]}


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

        # 🆕 SL ヒット時のみ AI 敗因分析を実行
        if outcome == "sl":
            gemini_key = os.environ.get("GEMINI_API_KEY")
            if gemini_key:
                print(f"    🔬 SL ヒット → AI 敗因分析を実行中...")
                # 1) VIX 変動取得
                vix_data = get_vix_change(fired_at_utc, resolved_at)
                # 2) 保有期間中のニュース取得 → 日本語翻訳
                news_en = get_news_during_holding(entry["ticker"], entry["fired_at"], resolved_at)
                news_jp = translate_titles_to_jp_quick(news_en, gemini_key) if news_en else []
                # 3) AI 分析
                analysis = analyze_loss_with_ai(entry, resolved_at, news_jp, vix_data, gemini_key)
                entry["loss_analysis"] = {
                    "vix_data": vix_data,
                    "news_during_holding": news_jp,
                    "ai_result": analysis or {"error": "AI 分析失敗"},
                }
                if analysis and "primary_category" in analysis:
                    print(f"    📋 敗因カテゴリ: {analysis.get('primary_category')} | "
                          f"{analysis.get('primary_cause', '')[:50]}")
                    print(f"    💡 教訓: {analysis.get('lesson', '')[:60]}")
            else:
                print(f"    ⚠️ GEMINI_API_KEY 未設定、敗因分析スキップ")

        # 🆕 R4: TP1/TP2 到達時に AI 勝因分析を実行（敗因分析の対称）
        if outcome in ("tp1", "tp2"):
            gemini_key = os.environ.get("GEMINI_API_KEY")
            if gemini_key:
                print(f"    ✨ {outcome.upper()} 到達 → AI 勝因分析を実行中...")
                vix_data = get_vix_change(fired_at_utc, resolved_at)
                news_en = get_news_during_holding(entry["ticker"], entry["fired_at"], resolved_at)
                news_jp = translate_titles_to_jp_quick(news_en, gemini_key) if news_en else []
                win_analysis = analyze_win_with_ai(entry, resolved_at, outcome, news_jp, vix_data, gemini_key)
                entry["win_analysis"] = {
                    "vix_data": vix_data,
                    "news_during_holding": news_jp,
                    "ai_result": win_analysis or {"error": "AI 分析失敗"},
                }
                if win_analysis and "primary_category" in win_analysis:
                    print(f"    🌟 勝因カテゴリ: {win_analysis.get('primary_category')} | "
                          f"{win_analysis.get('primary_cause', '')[:50]}")
                    print(f"    💡 教訓: {win_analysis.get('lesson', '')[:60]}")
                    print(f"    🔁 再現性: {win_analysis.get('repeatable', '?')}")
            else:
                print(f"    ⚠️ GEMINI_API_KEY 未設定、勝因分析スキップ")

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
