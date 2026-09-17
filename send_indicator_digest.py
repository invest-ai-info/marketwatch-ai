#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""send_indicator_digest.py — 今日の重要指標を朝いちでメールする。

🚨 なぜ必要か（2026-09-17 の実損）:
   オーナーが英中銀の政策金利発表の **27分前**にポンド円を3枚建て、発表の3秒後に
   まとめて手仕舞って -2,370円。当日の損失の約半分がこの1回だった。
   `MY_TRADING_RULES.md` §2「重要指標を持ち越さない」に真正面から反しているが、
   **機械が止める仕組みが無かった**＝環境警戒スコアは*シグナルが出たときのメール*の
   中身でしか届かず、手動の発注は誰も見ていない。

   そこで「シグナルが出たら知らせる」ではなく **「今日これがある」を毎朝先に渡す**。
   判断の直前ではなく、**ポジションを持つ前に**目に入るのが肝。

やること:
   `economic-events.json` を読み、今日〜今後7日の指標を JST で一覧にしてメールする。
   ⚠️ 市場休場（category=market_holiday）は別扱いで末尾にまとめる（本題を埋めないため）。

件名で状態がわかるようにする（開かなくても判断できるのが良いメール）:
   🚨 今日ある / 📅 今日は無いが7日以内にある / ⚪ 7日以内に無い

使い方:
   python send_indicator_digest.py            # 送信
   python send_indicator_digest.py --dry-run  # 本文を表示するだけ（送らない）
"""
import argparse
import datetime as dt
import json
import os
import smtplib
import sys
from email.mime.text import MIMEText

HERE = os.path.dirname(os.path.abspath(__file__))
JST = dt.timezone(dt.timedelta(hours=9))
EVENTS = os.path.join(HERE, "economic-events.json")
HORIZON_DAYS = 7

# 監視18銘柄の表示名（affected_assets をそのまま出すと読めないので）
TICKER_JA = {
    "all": "全銘柄", "USDJPY=X": "ドル円", "EURJPY=X": "ユーロ円", "GBPJPY=X": "ポンド円",
    "AUDJPY=X": "豪ドル円", "EURUSD=X": "ユーロドル", "GBPUSD=X": "ポンドドル",
    "AUDUSD=X": "豪ドル", "EURAUD=X": "ユーロ豪ドル", "GBPAUD=X": "ポンド豪ドル",
    "NKD=F": "日経", "ES=F": "S&P500", "NQ=F": "ナスダック", "YM=F": "ダウ",
    "^FTSE": "英FTSE", "GC=F": "金", "SI=F": "銀", "CL=F": "原油", "BTC-USD": "ビットコイン",
}
WD = "月火水木金土日"


def load_events(now):
    """(指標, 休場) を (日時, イベント) の昇順タプルで返す。"""
    if not os.path.exists(EVENTS):
        raise SystemExit(f"❌ {EVENTS} が無い")
    data = json.load(open(EVENTS, encoding="utf-8"))
    ind, hol = [], []
    limit = now + dt.timedelta(days=HORIZON_DAYS)
    for e in data.get("events", []):
        try:
            when = dt.datetime.fromisoformat(e["datetime"]).astimezone(JST)
        except Exception:
            continue
        if when < now or when > limit:
            continue
        (hol if e.get("category") == "market_holiday" else ind).append((when, e))
    ind.sort(key=lambda x: x[0])
    hol.sort(key=lambda x: x[0])
    return ind, hol


def assets_ja(e):
    a = e.get("affected_assets", ["all"])
    if "all" in a:
        return "全銘柄"
    return " / ".join(TICKER_JA.get(t, t) for t in a)


def build(now):
    ind, hol = load_events(now)
    today = now.date()
    today_ev = [(w, e) for w, e in ind if w.date() == today]

    if today_ev:
        head = today_ev[0]
        subject = (f"🚨 今日 重要指標{len(today_ev)}件 — "
                   f"{head[0]:%H:%M} {head[1]['name']}")
    elif ind:
        subject = f"📅 今日は重要指標なし（次は {ind[0][0]:%m/%d %H:%M} {ind[0][1]['name']}）"
    else:
        subject = f"⚪ 今後{HORIZON_DAYS}日に重要指標なし"

    L = ["━━━━━━━━━━━━━━━━━━━━━",
         f"📅 {now:%Y-%m-%d (%a)} の重要指標",
         "━━━━━━━━━━━━━━━━━━━━━", ""]

    if today_ev:
        L.append("【今日】")
        for w, e in today_ev:
            left = (w - now).total_seconds() / 3600
            mark = "🚫" if 0 <= left <= 6 else "🟡"
            L.append(f"  {mark} {w:%H:%M}（あと{left:.1f}h）  {e['name']}")
            L.append(f"       影響: {assets_ja(e)}")
        L.append("")
        # 🔑 ここが本題。ルールを毎朝そのまま渡す（覚えている前提にしない）
        L += ["  ⚠️ MY_TRADING_RULES §2:",
              "     発表の数時間前〜は新規を建てない。持つならロット半減 or 手仕舞い。",
              "     （2026-09-17: 英中銀の27分前に建てて当日損失の約半分を出した）", ""]
    else:
        L += ["【今日】", "  重要指標の予定なし", ""]

    rest = [(w, e) for w, e in ind if w.date() != today]
    if rest:
        L.append(f"【今後{HORIZON_DAYS}日】")
        for w, e in rest:
            L.append(f"  {w:%m/%d}({WD[w.weekday()]}) {w:%H:%M}  {e['name']}")
            L.append(f"       影響: {assets_ja(e)}")
        L.append("")

    if hol:
        L.append("【市場休場】")
        for w, e in hol:
            L.append(f"  {w:%m/%d}({WD[w.weekday()]})  {e['name']}")
        L.append("")

    L += ["━━━━━━━━━━━━━━━━━━━━━",
          "※ 日付は各国の公式日程と毎週突合しています（verify-calendar.yml）。",
          "※ 時刻は各機関の定例公表時刻を JST に換算したもので、日付ほどの検証はしていません。",
          "※ これは自分用の確認メールであり投資助言ではありません。"]
    return subject, "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description="今日の重要指標を朝いちでメールする")
    ap.add_argument("--dry-run", action="store_true", help="送信せず本文を表示するだけ")
    args = ap.parse_args()

    now = dt.datetime.now(JST)
    subject, body = build(now)

    if args.dry_run:
        print(f"Subject: {subject}\n")
        print(body)
        return 0

    sender = os.environ.get("GMAIL_USER", "")
    password = os.environ.get("GMAIL_APP_PASSWORD", "")
    recipient = os.environ.get("ALERT_RECIPIENT", "") or sender
    if not sender or not password:
        # ⚠️ 未設定は「異常」ではなく「この環境では送らない」＝ワークフローを赤くしない
        print("  ⚠️ GMAIL_USER / GMAIL_APP_PASSWORD 未設定＝送信スキップ")
        print(f"Subject: {subject}\n{body}")
        return 0

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as server:
        server.login(sender, password)
        server.send_message(msg)
    print(f"✅ 送信しました: {subject}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
