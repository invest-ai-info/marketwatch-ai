# -*- coding: utf-8 -*-
"""
monthly_calendar_reminder.py
───────────────────────────────────────
毎月 25 日朝に「来月の主要経済指標」を Gemini で取得し、
economic-events.json に追加すべき項目をメールで通知する。

設計思想:
- 市場休場は generate_market_holidays.py で自動補充されるので対象外
- ここでは重要指標（FOMC, 雇用統計, CPI, PCE, 日銀, ECB, BOE 等）にフォーカス
- Gemini に「来月の主要指標スケジュール」を JSON 形式で生成させる
- メール本文にコピペ可能な JSON 形式で提示
- ユーザーが内容確認のうえ economic-events.json に追加

使い方:
    python monthly_calendar_reminder.py            # 通常実行
    python monthly_calendar_reminder.py --no-email # メール送信なし（テスト用）

GitHub Actions: 毎月 25 日 00:13 UTC = 09:13 JST 25 日
"""
import os
import sys
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

JST = timezone(timedelta(hours=9))


def ask_gemini_for_calendar(year, month, api_key):
    """Gemini に来月の主要経済指標スケジュールを尋ねる"""
    if not api_key:
        return None
    try:
        import google.generativeai as genai
    except ImportError:
        return None
    genai.configure(api_key=api_key)

    prompt = f"""日本人個人投資家向けに、{year}年{month}月の主要経済指標スケジュールを教えてください。

【対象国・指標】
- 米国: FOMC、雇用統計（NFP）、CPI、PCE デフレーター、GDP、PPI、小売売上高
- 日本: 日銀金融政策決定会合、植田総裁会見
- EU: ECB 政策金利、ラガルド総裁会見
- 英国: BOE 政策金利、ベイリー総裁会見
- 中国: CPI、PMI、貿易収支
- OPEC: 月次会合

【出力フォーマット】
以下のように1行1イベントで出力してください（時刻は JST、ISO8601 形式）:

YYYY-MM-DDTHH:MM:00+09:00 | impact | 国 | イベント名 | note

例:
2026-07-30T03:00:00+09:00 | critical | US | FOMC 政策金利発表（7月） | 7/29 18:00 EDT
2026-07-04T21:30:00+09:00 | critical | US | 米雇用統計 6 月 NFP | 第 1 金曜 8:30 EDT

【ルール】
- 確実に発表される指標のみ（不確実な日付は除外）
- 重要度: critical = FOMC/雇用統計/CPI/日銀、high = それ以外
- 日付は WebSearch で確認できる確定情報のみ
- 出力は表データのみ、前置きや解説は不要"""

    text = ""
    for model_name in ("gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.0-flash-lite"):
        try:
            model = genai.GenerativeModel(model_name)
            resp = model.generate_content(prompt)
            text = (resp.text or "").strip()
            if text:
                return text
        except Exception:
            continue
    return None


def build_json_template(events_text):
    """Gemini 出力をパースして JSON テンプレを生成"""
    json_lines = []
    for line in events_text.splitlines():
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 4:
            continue
        try:
            dt_str = parts[0]
            impact = parts[1]
            country = parts[2]
            name = parts[3]
            note = parts[4] if len(parts) > 4 else ""
            # 影響銘柄を国別に推定
            affected_map = {
                "US": '["all"]',
                "EU": '["EURUSD=X", "EURJPY=X", "EURAUD=X"]',
                "UK": '["GBPUSD=X", "GBPJPY=X", "GBPAUD=X"]',
                "JP": '["NKD=F", "USDJPY=X"]',
                "CN": '["NKD=F", "CL=F", "AUDJPY=X"]',
                "OPEC": '["CL=F"]',
            }
            affected = affected_map.get(country, '["all"]')

            json_lines.append(
                f'    {{\n'
                f'      "name": "{name}",\n'
                f'      "datetime": "{dt_str}",\n'
                f'      "impact": "{impact}",\n'
                f'      "affected_assets": {affected},\n'
                f'      "country": "{country}",\n'
                f'      "note": "{note}"\n'
                f'    }},'
            )
        except Exception:
            continue
    return "\n".join(json_lines)


def send_reminder_email(year, month, raw_text, json_template):
    """リマインダーメールを送信"""
    sender = os.environ.get("GMAIL_USER", "")
    password = os.environ.get("GMAIL_APP_PASSWORD", "")
    recipient = os.environ.get("ALERT_RECIPIENT", "")
    if not (sender and password and recipient):
        print("  ⚠️ メール認証情報未設定、送信スキップ")
        return False

    subject = f"📅 [リマインダー] {year}年{month}月 経済指標カレンダー追加お願い"

    body_lines = [
        "━━━━━━━━━━━━━━━━━━━━━",
        f"📅 経済指標カレンダー月次リマインダー",
        f"{year}年{month}月の主要経済指標を economic-events.json に追加してください。",
        "━━━━━━━━━━━━━━━━━━━━━",
        "",
        "🤖 Gemini が生成した候補リスト:",
        "",
        raw_text or "(Gemini 取得失敗、手動で WebSearch してください)",
        "",
        "━━━━━━━━━━━━━━━━━━━━━",
        "📋 economic-events.json に貼り付け可能な JSON 形式:",
        "",
    ]
    if json_template:
        body_lines.append(json_template)
    else:
        body_lines.append("(変換失敗、上記の生データから手動で JSON 化してください)")

    body_lines.extend([
        "",
        "━━━━━━━━━━━━━━━━━━━━━",
        "💡 やること:",
        "  1. 上記の日時を WebSearch で再確認（Gemini が間違える可能性あり）",
        "  2. economic-events.json の events 配列に追加",
        "  3. sync_to_github.py で push",
        "",
        "ℹ️ なお、市場休場日は generate_market_holidays.py が自動で追加します。",
        "  ここでは「重要指標（FOMC・雇用統計・CPI・日銀等）」のみ手動メンテです。",
        "━━━━━━━━━━━━━━━━━━━━━",
        "MarketWatch AI Calendar Reminder",
    ])

    body = "\n".join(body_lines)

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as server:
            server.login(sender, password)
            server.sendmail(sender, [recipient], msg.as_string())
        print(f"  📧 リマインダーメール送信完了: {recipient}")
        return True
    except Exception as e:
        print(f"  ❌ メール送信失敗: {type(e).__name__}: {str(e)[:80]}")
        return False


def main():
    now_jst = datetime.now(JST)
    today = now_jst.date()
    no_email = "--no-email" in sys.argv

    # 翌月を計算
    if today.month == 12:
        target_year, target_month = today.year + 1, 1
    else:
        target_year, target_month = today.year, today.month + 1

    print(f"📅 経済指標カレンダー月次リマインダー ({today} → 翌月 {target_year}-{target_month:02d})")

    api_key = os.environ.get("GEMINI_API_KEY", "")
    print(f"  🤖 Gemini に {target_year}-{target_month:02d} 主要指標を問合せ中...")

    raw_text = ask_gemini_for_calendar(target_year, target_month, api_key)
    if not raw_text:
        print(f"  ⚠️ Gemini 取得失敗、フォールバックメッセージで送信")
        raw_text = f"(Gemini API 取得失敗。WebSearch で「{target_year}年{target_month}月 FOMC 雇用統計 CPI 日銀」を検索して手動追加してください)"

    print(f"  ✅ Gemini から {len(raw_text)} 文字取得")
    json_template = build_json_template(raw_text)

    if no_email:
        print(f"  🔇 メール送信スキップ (--no-email)")
        print()
        print("=== 取得した raw text ===")
        print(raw_text[:1500])
        print()
        print("=== JSON テンプレート（先頭 800 文字） ===")
        print(json_template[:800])
        return

    send_reminder_email(target_year, target_month, raw_text, json_template)


if __name__ == "__main__":
    main()
