#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_au_calendar.py — 豪州の重要指標の発表日を**一次情報と機械で突き合わせる**。

🚨 なぜ必要か（2026-11-12 オーナー決定）:
   監視18銘柄のうち4つが豪ドルのペア（AUDJPY / AUDUSD / EURAUD / GBPAUD）なのに、カレンダーに
   豪州の指標が1つも無く、豪中銀の発表の前でも環境警戒スコアが鳴らなかった。同じ日に
   豪中銀の金利・豪雇用統計・豪CPI を足したので、その日付が公式とずれていないかをここで見張る
   （米＝verify_economic_calendar.py／英・ユーロ圏＝verify_uk_eu_calendar.py と同じ考え方）。

🚨 曜日や前例から推測しない（2026-09-11 の米CPI事故の教訓）。正しさは一次情報との突合でしか決まらない。
   ⚠️ MT5 の経済カレンダーも元にしない（豪中銀の時刻が1時間遅い回があった）。

⚠️ **検証するのは日付だけで、時刻は検証していない。**
   時刻は定例の公表時刻（豪中銀 14:30 シドニー時間＝2日間の会合の2日目／豪統計局 11:30）を
   sync_economic_events.py の RULES が日本時間に換算している。公表時刻の変更はここでは捕まらない。

やること:
   ① 豪中銀（RBA）の年間の会合日程 … 金融政策の会合は2日間。**2日目が発表日**
   ② 豪統計局（ABS）の雇用統計・CPI のページの「Future releases」（＝公式に出ている次の数回）
   を取得して `economic-events.json` / `ECONOMIC_EVENTS_2026` と突合。
   次のどれかで exit 1（Actions が Issue 化する）:
     - 公式に無い日付を載せている（誤登録）
     - 21日以内（NEAR）の公式の発表が economic-events.json に無い（＝発表の前にカレンダーが黙る）
     - ページを取得できない・読み取れない（「検証できなかった」を「問題なし」と取り違えない）
   もっと先の未登録は ℹ️ で知らせるだけ（月次の取り込みで足される分があるため）。

使い方:
   python verify_au_calendar.py            # 検証（食い違いがあれば exit 1）
   python verify_au_calendar.py --dump     # 取得したページの素のテキストを出す（構造調査用）
"""
import argparse
import datetime as dt
import re
import sys

from verify_uk_eu_calendar import HORIZON, JST, MONTH_RE, MONTHS, fetch, ours_from_json, ours_from_master, plain_text, wd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

NEAR = 21                       # これ以内の公式の発表が台帳に無ければ「問題」（週1回の見張りで発表の前に気づける長さ）
ME = "verify_au_calendar.py"
RBA_URL = "https://www.rba.gov.au/schedules-events/board-meeting-schedules.html"
ABS_SOURCES = [
    ("豪雇用統計", "https://www.abs.gov.au/statistics/labour/employment-and-unemployment/"
                   "labour-force-australia/latest-release", r"^豪雇用統計"),
    ("豪CPI", "https://www.abs.gov.au/statistics/economy/price-indexes-and-inflation/"
              "consumer-price-index-australia/latest-release", r"^豪CPI"),
]
RBA_PATTERN = r"豪中銀"

DASH = r"(?:&ndash;|&#8211;|–|—|-)"
RBA_YEAR_RE = re.compile(r"^Board meeting schedules\s+(\d{4})$", re.I)
# 金融政策の会合は「2–3 February」＝2日間。決済システムの会合は「5 March」＝1日だけ（拾わない）
RBA_TWO_DAY_RE = re.compile(rf"^(\d{{1,2}})\s*{DASH}\s*(\d{{1,2}})\s+({MONTH_RE})$")
RBA_CROSS_MONTH_RE = re.compile(rf"^(\d{{1,2}})\s+({MONTH_RE})\s*{DASH}\s*(\d{{1,2}})\s+({MONTH_RE})$")
ABS_NEXT_RE = re.compile(r"Next Release\s+(\d{1,2})/(\d{1,2})/(\d{4})", re.I)


def parse_rba(text):
    """豪中銀の金融政策の会合の**2日目（＝発表日）**を返す。年は見出し「Board meeting schedules 2026」から拾う"""
    out, year = [], None
    for ln in text.splitlines():
        ln = ln.strip()
        m = RBA_YEAR_RE.match(ln)
        if m:
            year = int(m.group(1))
            continue
        if not year:
            continue
        m = RBA_TWO_DAY_RE.match(ln)
        if m:
            out.append(dt.date(year, MONTHS[m.group(3)], int(m.group(2))))
            continue
        m = RBA_CROSS_MONTH_RE.match(ln)
        if m:
            out.append(dt.date(year, MONTHS[m.group(4)], int(m.group(3))))
    return sorted(set(out))


def parse_abs_next(text):
    """豪統計局のページの「Next Release 19/11/2026」（日/月/年）をぜんぶ返す"""
    out = set()
    for d, mo, y in ABS_NEXT_RE.findall(text):
        try:
            out.add(dt.date(int(y), int(mo), int(d)))
        except ValueError:
            pass
    return sorted(out)


def judge(label, found, js, ms, today, problems, notes):
    """公式の日付 found と、台帳 js（economic-events.json）・元の表 ms（ECONOMIC_EVENTS_2026）を突き合わせる"""
    future = [d for d in found if today <= d <= today + HORIZON]
    if not future:
        problems.append(f"{label}: 今日以降の公式の日付を1件も読み取れない（解析ミスか、公式の更新停止）→ {ME} を確認")
        return
    for d in future:
        days = (d - today).days
        if d not in js:
            if days <= NEAR:
                problems.append(f"🚨 economic-events.json: {d}（{wd(d)}）の{label}が未登録（あと{days}日）"
                                f"＝発表の前にカレンダーが黙る → ECONOMIC_EVENTS に足して monthly-calendar-reminder.yml を手動実行")
            else:
                notes.append(f"economic-events.json: {d}（{wd(d)}）の{label}が未登録")
        if d.year == 2026 and d not in ms:
            notes.append(f"ECONOMIC_EVENTS_2026: {d}（{wd(d)}）の{label}が未登録")
    # 逆向き＝うちにあって公式に無い日付（＝誤登録）。公式がまだ出していない先の期間は正常なので、公式の最終日までだけ見る
    last, official = max(found), set(found)
    for where, mine in (("economic-events.json", js), ("ECONOMIC_EVENTS_2026", ms)):
        for d in sorted(mine):
            if today <= d <= last and d not in official:
                problems.append(f"🚨 {where}: {d}（{wd(d)}）に{label}を載せているが、公式の日程に無い")


def main():
    ap = argparse.ArgumentParser(description="豪州の指標日程を一次情報と突き合わせる")
    ap.add_argument("--dump", action="store_true", help="取得したページの素のテキストを出す")
    args = ap.parse_args()
    today = dt.datetime.now(JST).date()
    problems, notes = [], []
    sources = [("豪中銀 政策金利発表", RBA_URL, RBA_PATTERN, parse_rba, 4)] + [(k, u, p, parse_abs_next, 1) for k, u, p in ABS_SOURCES]

    if args.dump:
        for label, url, _p, _f, _n in sources:
            print(f"\n{'=' * 70}\n■ {label}: {url}\n{'=' * 70}")
            try:
                for ln in plain_text(fetch(url)).splitlines()[:120]:
                    print(f"   {ln[:170]}")
            except Exception as e:  # noqa: BLE001
                print(f"   ❌ 取得できない: {type(e).__name__}: {str(e)[:120]}")
        return 0

    for label, url, pattern, parse, need in sources:
        print(f"\n■ {label}: {url}")
        try:
            text = plain_text(fetch(url))
        except Exception as e:  # noqa: BLE001
            problems.append(f"{label}: 公式のページを取得できない（{type(e).__name__}: {str(e)[:80]}）")
            continue
        found = parse(text)
        if len(found) < need:
            problems.append(f"{label}: 読み取れた日付が {len(found)} 件しかない（ページ構造が変わった疑い）→ {ME} を要修正")
            print("   --- 読み取れなかったので素のテキストを出す（構造を見て直す用）---")
            for ln in text.splitlines()[:60]:
                print(f"      {ln[:170]}")
            continue
        for d in found:
            if d >= today:
                print(f"   公式: {d} ({wd(d)})")
        judge(label, found, ours_from_json(pattern), ours_from_master(pattern), today, problems, notes)

    print("\n" + "-" * 50)
    for n in notes:
        print(f"  ℹ️  {n}")
    if problems:
        print(f"\n❌ 食い違い/検証不能 {len(problems)} 件")
        for p in problems:
            print(f"   {p}")
        print("\n→ generate_market_news.py の ECONOMIC_EVENTS_2026 を公式の日付に直し、monthly-calendar-reminder.yml を"
              "手動実行してください（economic-events.json は GitHub 側で作る）。**曜日から推測しないこと**。")
        return 1
    print("✅ 豪州：公式日程と一致（今日以降の回）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
