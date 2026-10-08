# -*- coding: utf-8 -*-
"""
generate_market_holidays.py
───────────────────────────────────────
主要市場休場日（米国 NYSE/Nasdaq、英国 LSE、日本 TSE）を
economic-events.json に重複なくマージする。

設計思想:
- 市場休場は事実情報で確定（連邦祝日・国民の祝日）なのでハードコード
- 2026-2027 年分を完全カバー。東証は 2028 年まで（2026-10-09 追加）。米英の 2028 年は追って追加
- 既存エントリと重複しないように datetime + name でユニーク判定
- 月初 cron で走らせて、常に未来分が補充される状態を維持

使い方:
    python generate_market_holidays.py            # マージ実行（追加分のみ）
    python generate_market_holidays.py --dry-run  # 追加候補を表示するだけ

GitHub Actions: 毎月 1 日 09:00 JST cron で実行
"""
import os
import sys
import json
from datetime import datetime

EVENTS_FILE = "economic-events.json"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ─────────────────────────────────────────────
# 米国 NYSE / Nasdaq 休場日（連邦祝日 10 件/年 + 早仕舞い 2 件）
# 出典: https://www.nyse.com/trade/hours-calendars
# ─────────────────────────────────────────────
US_HOLIDAYS = [
    # 2026
    ("2026-01-01", "🏖️ 米国市場休場（New Year's Day）", "NYSE / Nasdaq 終日休場"),
    ("2026-01-19", "🏖️ 米国市場休場（Martin Luther King Jr. Day）", "NYSE / Nasdaq 終日休場"),
    ("2026-02-16", "🏖️ 米国市場休場（Washington's Birthday）", "NYSE / Nasdaq 終日休場"),
    ("2026-04-03", "🏖️ 米国市場休場（Good Friday）", "NYSE / Nasdaq 終日休場"),
    ("2026-05-25", "🏖️ 米国市場休場（Memorial Day）", "NYSE / Nasdaq 終日休場、ボラ低下＆流動性減少。FX も米国時間は薄商い"),
    ("2026-06-19", "🏖️ 米国市場休場（Juneteenth）", "NYSE / Nasdaq 終日休場。FOMC 翌日のためボラ大の可能性あり、要警戒"),
    ("2026-07-03", "🏖️ 米国市場休場（Independence Day 振替）", "7/4 (土) Independence Day の前倒し。週末ギャップリスクと組合せ要注意"),
    ("2026-09-07", "🏖️ 米国市場休場（Labor Day）", "NYSE / Nasdaq 終日休場。米国時間のボラ急減"),
    ("2026-11-26", "🏖️ 米国市場休場（Thanksgiving）", "NYSE / Nasdaq 終日休場。米国感謝祭、世界的にもボラ激減"),
    ("2026-11-27", "🏖️ 米国市場早仕舞い（Black Friday）", "NYSE / Nasdaq 13:00 ET (03:00 JST 土曜) で早仕舞い。米国時間ほぼ休場"),
    ("2026-12-24", "🏖️ 米国市場早仕舞い（Christmas Eve）", "NYSE / Nasdaq 13:00 ET で早仕舞い。LSE も 12:30 GMT 早仕舞い"),
    ("2026-12-25", "🏖️ 米英市場休場（Christmas Day）", "NYSE / Nasdaq / LSE 全て終日休場。世界的にボラ最低水準"),
    # 2027
    ("2027-01-01", "🏖️ 米国市場休場（New Year's Day）", "NYSE / Nasdaq 終日休場"),
    ("2027-01-18", "🏖️ 米国市場休場（Martin Luther King Jr. Day）", "NYSE / Nasdaq 終日休場"),
    ("2027-02-15", "🏖️ 米国市場休場（Washington's Birthday）", "NYSE / Nasdaq 終日休場"),
    ("2027-03-26", "🏖️ 米国市場休場（Good Friday）", "NYSE / Nasdaq 終日休場"),
    ("2027-05-31", "🏖️ 米国市場休場（Memorial Day）", "NYSE / Nasdaq 終日休場"),
    ("2027-06-18", "🏖️ 米国市場休場（Juneteenth 振替）", "6/19 が土曜のため前倒し休場"),
    ("2027-07-05", "🏖️ 米国市場休場（Independence Day 振替）", "7/4 (日) の振替休場"),
    ("2027-09-06", "🏖️ 米国市場休場（Labor Day）", "NYSE / Nasdaq 終日休場"),
    ("2027-11-25", "🏖️ 米国市場休場（Thanksgiving）", "NYSE / Nasdaq 終日休場"),
    ("2027-11-26", "🏖️ 米国市場早仕舞い（Black Friday）", "NYSE / Nasdaq 13:00 ET で早仕舞い"),
    # ⚠️ 2027-12-23 の早仕舞いは無い（2026-10-05 訂正）。NYSE の公式の休場表（nyse.com/trade/hours-calendars）で、
    #    2027 年の早仕舞いは 11/26（感謝祭の翌日）だけ・12/24（金）がクリスマスの振替休場。旧版は「要確認」のまま載せていた
    ("2027-12-24", "🏖️ 米国市場休場（Christmas Day 振替）", "12/25 が土曜のため前倒し休場"),
]

# ─────────────────────────────────────────────
# 英国 LSE 休場日（Bank Holiday）
# ─────────────────────────────────────────────
UK_HOLIDAYS = [
    # 2026
    ("2026-01-01", "🏖️ 英国市場休場（New Year's Day）", "LSE 終日休場"),
    ("2026-04-03", "🏖️ 英国市場休場（Good Friday）", "LSE 終日休場"),
    ("2026-04-06", "🏖️ 英国市場休場（Easter Monday）", "LSE 終日休場"),
    ("2026-05-04", "🏖️ 英国市場休場（Early May Bank Holiday）", "LSE 終日休場、ポンド系ボラ低下"),
    ("2026-05-25", "🏖️ 英国市場休場（Spring Bank Holiday）", "LSE 終日休場、ポンド系ボラ低下"),
    ("2026-08-31", "🏖️ 英国市場休場（Summer Bank Holiday）", "LSE 終日休場、ポンド系ボラ低下"),
    ("2026-12-28", "🏖️ 英国市場休場（Boxing Day 振替）", "12/26 (土) Boxing Day の振替休場"),
    # 2027
    ("2027-01-01", "🏖️ 英国市場休場（New Year's Day）", "LSE 終日休場"),
    ("2027-03-26", "🏖️ 英国市場休場（Good Friday）", "LSE 終日休場"),
    ("2027-03-29", "🏖️ 英国市場休場（Easter Monday）", "LSE 終日休場"),
    ("2027-05-03", "🏖️ 英国市場休場（Early May Bank Holiday）", "LSE 終日休場、ポンド系ボラ低下"),
    ("2027-05-31", "🏖️ 英国市場休場（Spring Bank Holiday）", "LSE 終日休場、ポンド系ボラ低下"),
    ("2027-08-30", "🏖️ 英国市場休場（Summer Bank Holiday）", "LSE 終日休場、ポンド系ボラ低下"),
    ("2027-12-27", "🏖️ 英国市場休場（Christmas Day 振替）", "12/25 (土) の振替休場"),
    ("2027-12-28", "🏖️ 英国市場休場（Boxing Day 振替）", "12/26 (日) の振替休場"),
]

UK_AFFECTED = ["GBPUSD=X", "GBPJPY=X", "GBPAUD=X", "EURUSD=X", "^FTSE"]

# ─────────────────────────────────────────────
# 日本 TSE 休場日（国民の祝日 + 年末年始）
# ─────────────────────────────────────────────
JP_HOLIDAYS = [
    # 2026
    ("2026-01-01", "🏖️ 日本市場休場（年始 / 元日）", "TSE 年始休場（1/1-1/3）"),
    ("2026-01-02", "🏖️ 日本市場休場（年始）", "TSE 年始休場"),
    ("2026-01-12", "🏖️ 日本市場休場（成人の日）", "第 2 月曜"),
    ("2026-02-11", "🏖️ 日本市場休場（建国記念の日）", ""),
    ("2026-02-23", "🏖️ 日本市場休場（天皇誕生日）", ""),
    ("2026-03-20", "🏖️ 日本市場休場（春分の日）", ""),
    ("2026-04-29", "🏖️ 日本市場休場（昭和の日）", "GW スタート"),
    ("2026-05-04", "🏖️ 日本市場休場（みどりの日）", "GW"),
    ("2026-05-05", "🏖️ 日本市場休場（こどもの日）", "GW"),
    ("2026-05-06", "🏖️ 日本市場休場（憲法記念日 振替）", "GW、5/3 (日) の振替"),
    ("2026-07-20", "🏖️ 日本市場休場（海の日）", "第 3 月曜"),
    ("2026-08-11", "🏖️ 日本市場休場（山の日）", ""),
    ("2026-09-21", "🏖️ 日本市場休場（敬老の日）", "第 3 月曜"),
    ("2026-09-22", "🏖️ 日本市場休場（国民の休日）", "敬老の日と秋分の日に挟まれた休日"),
    ("2026-09-23", "🏖️ 日本市場休場（秋分の日）", "3 連休（9/21-23）、TSE 連休でボラ蓄積→週明け要警戒"),
    ("2026-10-12", "🏖️ 日本市場休場（スポーツの日）", "第 2 月曜"),
    ("2026-11-03", "🏖️ 日本市場休場（文化の日）", ""),
    ("2026-11-23", "🏖️ 日本市場休場（勤労感謝の日）", "11/21-23 3 連休、JPX BCP テストのため祝日取引なし"),
    ("2026-12-31", "🏖️ 日本市場休場（年末 / 大納会後）", "12/31-1/3 まで TSE 休場"),
    # 2027
    ("2027-01-01", "🏖️ 日本市場休場（年始 / 元日）", "TSE 年始休場"),
    # ⚠️ 2027-01-04 は休場でない（2026-10-05 訂正）。東証の休業日は 1/1〜1/3 と 12/31 だけで、1/4（月）は大発会＝取引日。
    #    旧版はここを「年始休場」としていた → RETRACTED で economic-events.json からも取り除く
    ("2027-01-11", "🏖️ 日本市場休場（成人の日）", "第 2 月曜"),
    ("2027-02-11", "🏖️ 日本市場休場（建国記念の日）", ""),
    ("2027-02-23", "🏖️ 日本市場休場（天皇誕生日）", ""),
    ("2027-03-22", "🏖️ 日本市場休場（春分の日 振替）", "3/21 (日) の振替"),
    ("2027-04-29", "🏖️ 日本市場休場（昭和の日）", "GW スタート"),
    ("2027-05-03", "🏖️ 日本市場休場（憲法記念日）", "GW"),
    ("2027-05-04", "🏖️ 日本市場休場（みどりの日）", "GW"),
    ("2027-05-05", "🏖️ 日本市場休場（こどもの日）", "GW"),
    ("2027-07-19", "🏖️ 日本市場休場（海の日）", "第 3 月曜"),
    ("2027-08-11", "🏖️ 日本市場休場（山の日）", ""),
    ("2027-09-20", "🏖️ 日本市場休場（敬老の日）", "第 3 月曜"),
    ("2027-09-23", "🏖️ 日本市場休場（秋分の日）", ""),
    ("2027-10-11", "🏖️ 日本市場休場（スポーツの日）", "第 2 月曜"),
    ("2027-11-03", "🏖️ 日本市場休場（文化の日）", ""),
    ("2027-11-23", "🏖️ 日本市場休場（勤労感謝の日）", ""),
    ("2027-12-31", "🏖️ 日本市場休場（年末 / 大納会後）", "12/31-1/3 まで TSE 休場"),
    # 2028（2026-10-09 オーナー「2028年分の東証の休日日も今のうちに足しておいてください」）
    # ⚠️ 平日に当たる日だけ（1/1 元日＝土・4/29 昭和の日＝土・12/31＝日 はもともと休み）。日曜の祝日が無い＝振替休日なし・
    #    祝日に挟まれた平日も無い＝国民の休日なし（曜日は計算で確かめた・tests/test_market_holidays.py）。
    # ⚠️ 春分の日・秋分の日は前の年（2027年）2月の官報（国立天文台の暦要項）で正式に決まる。下は計算どおりの見込み＝
    #    2027年2月に内閣府の「国民の祝日」の表と照らす。JPX の 2028 年の休業日一覧もまだ出ていない（年末年始は 12/31〜1/3 の決まり）
    ("2028-01-03", "🏖️ 日本市場休場（年始）", "TSE 年始休場（1/1-1/3）・1/4（火）が大発会"),
    ("2028-01-10", "🏖️ 日本市場休場（成人の日）", "第 2 月曜"),
    ("2028-02-11", "🏖️ 日本市場休場（建国記念の日）", ""),
    ("2028-02-23", "🏖️ 日本市場休場（天皇誕生日）", ""),
    ("2028-03-20", "🏖️ 日本市場休場（春分の日）", "見込み（2027年2月の官報で確定）"),
    ("2028-05-03", "🏖️ 日本市場休場（憲法記念日）", "GW（5/3-5/7 の5連休）"),
    ("2028-05-04", "🏖️ 日本市場休場（みどりの日）", "GW"),
    ("2028-05-05", "🏖️ 日本市場休場（こどもの日）", "GW"),
    ("2028-07-17", "🏖️ 日本市場休場（海の日）", "第 3 月曜"),
    ("2028-08-11", "🏖️ 日本市場休場（山の日）", ""),
    ("2028-09-18", "🏖️ 日本市場休場（敬老の日）", "第 3 月曜"),
    ("2028-09-22", "🏖️ 日本市場休場（秋分の日）", "見込み（2027年2月の官報で確定）"),
    ("2028-10-09", "🏖️ 日本市場休場（スポーツの日）", "第 2 月曜"),
    ("2028-11-03", "🏖️ 日本市場休場（文化の日）", ""),
    ("2028-11-23", "🏖️ 日本市場休場（勤労感謝の日）", ""),
]


# 誤って載せてしまい、取り下げたもの。このスクリプトは「足すだけ」なので、一覧から外しても economic-events.json
# には残る。ここに書いたもの（国＋日付の休場）は実行のたびに取り除く（冪等）。tests/test_market_holidays.py が見張る
RETRACTED = [
    {"country": "JP", "date": "2027-01-04", "reason": "東証の休業日は 1/1〜1/3 と 12/31。1/4（月）は大発会＝取引日"},
    {"country": "US", "date": "2027-12-23", "reason": "NYSE の 2027 年の早仕舞いは 11/26 だけ（12/24 は終日休場）"},
]


def prune_retracted(events):
    """→ (残すイベント, 取り除いたイベント)。市場休場（category=market_holiday）のうち RETRACTED の国＋日付だけを外す"""
    bad = {(r["country"], r["date"]) for r in RETRACTED}
    kept, removed = [], []
    for e in events:
        if e.get("category") == "market_holiday" and (e.get("country"), (e.get("datetime") or "")[:10]) in bad:
            removed.append(e)
        else:
            kept.append(e)
    return kept, removed


def build_event(date_str, name, note, country, affected):
    """ハードコードデータから event レコードを生成"""
    return {
        "name": name,
        "datetime": f"{date_str}T09:00:00+09:00",
        "impact": "high" if "早仕舞" in name or "振替" in name else ("critical" if "Thanksgiving" in name or "Christmas Day" in name else "high"),
        "affected_assets": affected,
        "country": country,
        "category": "market_holiday",
        "note": note,
    }


def main():
    dry_run = "--dry-run" in sys.argv

    # 既存 events 読込
    if not os.path.exists(EVENTS_FILE):
        print(f"❌ {EVENTS_FILE} が見つかりません")
        sys.exit(1)
    with open(EVENTS_FILE, encoding="utf-8") as f:
        data = json.load(f)
    existing_events = data.get("events", [])

    # 取り下げたもの（誤って載せた休場）を先に外す
    existing_events, retracted = prune_retracted(existing_events)

    # 既存の (datetime, name) セットで重複判定
    existing_keys = {(e.get("datetime", ""), e.get("name", "")) for e in existing_events}

    # 全候補を作成
    candidates = []
    for date_str, name, note in US_HOLIDAYS:
        candidates.append(build_event(date_str, name, note, "US", ["all"]))
    for date_str, name, note in UK_HOLIDAYS:
        candidates.append(build_event(date_str, name, note, "UK", UK_AFFECTED))
    for date_str, name, note in JP_HOLIDAYS:
        candidates.append(build_event(date_str, name, note, "JP", ["NKD=F"]))

    # 重複していない新規分だけ抽出
    new_events = [ev for ev in candidates if (ev["datetime"], ev["name"]) not in existing_keys]

    print(f"📅 候補総数: {len(candidates)} 件")
    print(f"   既存と重複: {len(candidates) - len(new_events)} 件")
    print(f"   新規追加候補: {len(new_events)} 件")
    print(f"   取り下げて外す: {len(retracted)} 件")
    for ev in retracted:
        print(f"  - {ev['datetime'][:10]} | {ev['name']}")

    if dry_run:
        print()
        print("=== 追加候補（--dry-run） ===")
        for ev in new_events:
            print(f"  {ev['datetime'][:10]} | {ev['name']}")
        return

    if not new_events and not retracted:
        print("✅ 全て登録済み、追加なし")
        return

    # 既存に追加して datetime 昇順にソート
    all_events = existing_events + new_events
    all_events.sort(key=lambda x: x.get("datetime", ""))
    data["events"] = all_events

    with open(EVENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ {EVENTS_FILE} に {len(new_events)} 件追加・{len(retracted)} 件取り下げ（合計 {len(all_events)} 件）")
    for ev in new_events[:20]:
        print(f"  + {ev['datetime'][:10]} | {ev['name']}")
    if len(new_events) > 20:
        print(f"  ... 他 {len(new_events) - 20} 件")


if __name__ == "__main__":
    main()
