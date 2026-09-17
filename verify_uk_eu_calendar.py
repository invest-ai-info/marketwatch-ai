#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_uk_eu_calendar.py — 英・ユーロ圏の重要指標の発表日を**一次情報と機械で突き合わせる**。

🚨 なぜ必要か（2026-09-17 オーナー指摘）:
   カレンダーが米国と日本にほぼ偏っており、**英中銀(BOE)の政策金利発表が1件も載っていなかった**。
   2026-09-17（木）はその BOE 発表日だったのに、サイトのカレンダーは無言だった。
   監視18銘柄には GBPJPY / GBPUSD / EURJPY / EURUSD / EURAUD / GBPAUD / ^FTSE が入っている＝
   **英・ユーロの金融政策は「他所の話」ではなく、うちの主力銘柄を直接動かす**。

🔑 実行場所が肝（verify_economic_calendar.py と同じ）:
   Claude セッションのコンテナからは bankofengland.co.uk / ecb.europa.eu / ons.gov.uk が
   egress 遮断される（接続不可）が、**GitHub Actions のランナーからは届く**。
   だからこの検証は Actions で回す。

🚨 曜日や前例から推測しない（2026-09-11 の米CPI事故の教訓）。
   「BOEは木曜」「ECBは木曜」は経験則にすぎず、**正しさは一次情報との突合でしか決まらない**。

⚠️ **検証するのは日付だけで、時刻は検証していない。**
   時刻は各機関の定例公表時刻（BOE 12:00 ロンドン／ECB 14:15 CET／ONS 07:00 ロンドン／
   Eurostat 速報 11:00 CET）を JST に換算して `economic-events.json` の note に書いてある。
   日付が動けばここで捕まるが、公表時刻の変更は捕まらない＝**note の換算式を人が年1回見直す**。

やること:
   ① BOE の MPC 日程 / ECB 理事会日程（＝年間日程が公式に出ている）
   ② ONS 各速報の「Next release」（＝公式に確定しているのは**次回1件だけ**）
   を取得して `economic-events.json` / `ECONOMIC_EVENTS_2026` と突合。
   食い違い・欠落・解析不能があれば標準出力に出して exit 1（Actions が Issue 化する）。

⚠️ 黙って通さない: ページ構造が変わって解析できなかった場合も **exit 1**
   （「検証できなかった」を「問題なし」と取り違えない）。

使い方:
   python verify_uk_eu_calendar.py            # 検証（食い違いがあれば exit 1）
   python verify_uk_eu_calendar.py --dump     # 取得したページの素のテキストを出す（構造調査用）
"""
import argparse
import datetime as dt
import gzip
import json
import os
import re
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
JST = dt.timezone(dt.timedelta(hours=9))
UA = "Mozilla/5.0 (compatible; marketwatch-jp calendar verifier; +https://marketwatch-jp.com/)"
# 「未登録」を指摘する範囲（これ以上先はカレンダーに載せなくてよい）
HORIZON = dt.timedelta(days=460)

BOE_URL = "https://www.bankofengland.co.uk/monetary-policy/upcoming-mpc-dates"
ECB_URL = "https://www.ecb.europa.eu/press/calendars/mgcgc/html/index.en.html"

# ONS は各速報ページの「Next release」だけが確定日程。key → (URL, 我々の登録名の正規表現)
ONS_SOURCES = [
    ("英CPI", "https://www.ons.gov.uk/economy/inflationandpriceindices/bulletins/"
              "consumerpriceinflation/latest", r"^英CPI"),
    ("英雇用統計", "https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/"
                   "employmentandemployeetypes/bulletins/uklabourmarket/latest", r"^英雇用統計"),
    ("英GDP（月次）", "https://www.ons.gov.uk/economy/grossdomesticproductgdp/bulletins/"
                      "gdpmonthlyestimateuk/latest", r"^英GDP（月次"),
]

_FULL = ["January", "February", "March", "April", "May", "June",
         "July", "August", "September", "October", "November", "December"]
MONTHS = {}
for _i, _m in enumerate(_FULL, start=1):
    MONTHS[_m] = _i
    MONTHS[_m[:3]] = _i
MONTHS["Sept"] = 9
MONTH_RE = "|".join(sorted(MONTHS, key=len, reverse=True))
DMY_RE = re.compile(rf"(\d{{1,2}})\s+({MONTH_RE})\.?\s+(\d{{4}})")
# 🚨 BOE の表は**年を書かない**（「Thursday 5 November」だけ）。年は見出しから拾う。
#    これに気づかず年付きの日付だけ探していて、調査1回目は日程を1件も取れなかった。
BOE_YEAR_RE = re.compile(r"^(\d{4})\s+(?:confirmed|provisional)\s+dates", re.I)
BOE_DAY_RE = re.compile(rf"^\w+day\s+(\d{{1,2}})\s+({MONTH_RE})$")
SLASH_RE = re.compile(r"^(\d{2})/(\d{2})/(\d{4})")


def fetch(url, _retry=1):
    """⚠️ 2026-09-17: 短時間に何度も叩いた回で **BLS がバイナリ（gzip/空バイト）を返し**、
    解析0件→「構造が変わった」と誤警報して Issue を立てた。番人が狼少年になるのが一番まずい。
    そこで ①非圧縮を要求し ②それでも gzip なら展開し ③1回だけ間を置いて再試行する。"""
    req = urllib.request.Request(
        url, headers={"User-Agent": UA, "Accept": "text/html", "Accept-Encoding": "identity"})
    with urllib.request.urlopen(req, timeout=40) as r:
        raw = r.read()
    if r.headers.get("Content-Encoding") == "gzip" or raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    text = raw.decode("utf-8", "replace")
    if ("\x00" in text[:2000] or len(text) < 500) and _retry:
        time.sleep(5)
        return fetch(url, _retry=0)
    return text


def plain_text(html_text):
    t = re.sub(r"(?is)<(script|style|nav|header|footer).*?</\1>", " ", html_text)
    t = re.sub(r"(?i)<br\s*/?>|</t[dh]>|</tr>|</li>|</p>|</h[1-6]>|</div>", "\n", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"&nbsp;?", " ", t).replace("&amp;", "&").replace("&#8211;", "-")
    return "\n".join(re.sub(r"[ \t]+", " ", ln).strip() for ln in t.splitlines() if ln.strip())


def parse_boe(text):
    """BOE の MPC 日程を返す。見出しの年＋「Thursday 5 November」形式の行を組み合わせる。"""
    out, year = [], None
    for ln in text.splitlines():
        m = BOE_YEAR_RE.match(ln)
        if m:
            year = int(m.group(1))
            continue
        m = BOE_DAY_RE.match(ln)
        if m and year:
            out.append(dt.date(year, MONTHS[m.group(2)], int(m.group(1))))
    return sorted(set(out))


def parse_ecb(text):
    """ECB 理事会の**金融政策会合の2日目（＝発表日）**を返す。

    ページは「30/09/2026」の行と説明の行が分かれているので、次行を見て判定する。
    """
    out, lines = [], text.splitlines()
    for i, ln in enumerate(lines):
        m = SLASH_RE.match(ln.strip())
        if not m:
            continue
        label = lines[i + 1].strip().lower() if i + 1 < len(lines) else ""
        if "monetary policy meeting" not in label or "(day 2)" not in label:
            continue
        d, mo, y = m.groups()
        out.append(dt.date(int(y), int(mo), int(d)))
    return sorted(set(out))


def parse_ons_next(text):
    """ONS 速報ページの「Next release:」の直後にある日付を返す（無ければ None）。"""
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        if ln.strip().lower().startswith("next release"):
            for nxt in lines[i:i + 3]:
                m = DMY_RE.search(nxt)
                if m:
                    return dt.date(int(m.group(3)), MONTHS[m.group(2)], int(m.group(1)))
    return None


def ours_from_json(pattern):
    path = os.path.join(HERE, "economic-events.json")
    if not os.path.exists(path):
        return set()
    d = json.load(open(path, encoding="utf-8"))
    return {dt.datetime.fromisoformat(e["datetime"]).astimezone(JST).date()
            for e in d.get("events", []) if re.search(pattern, e.get("name", ""))}


def ours_from_master(pattern):
    path = os.path.join(HERE, "generate_market_news.py")
    if not os.path.exists(path):
        return set()
    src = open(path, encoding="utf-8").read()
    m = re.search(r"ECONOMIC_EVENTS_2026\s*=\s*\[(.*?)\n\]", src, re.S)
    if not m:
        return set()
    return {dt.date(2026, int(mo), int(dy))
            for mo, dy, _c, _i, name in re.findall(
                r'\(\s*(\d+),\s*(\d+),\s*"(\w+)",\s*"(\w+)",\s*"([^"]+)"', m.group(1))
            if re.search(pattern, name)}


def wd(d):
    return "月火水木金土日"[d.weekday()]


def check_policy(key, url, label, parse, pattern, today, problems, notes):
    print(f"\n■ {label}（{key}）: {url}")
    try:
        text = plain_text(fetch(url))
    except Exception as e:
        problems.append(f"{key}: 公式日程を取得できない（{type(e).__name__}: {str(e)[:80]}）")
        return
    found = parse(text)
    # 🚨 年8回前後の日程が載るページ。少なすぎる＝解析が壊れている。
    #    「解析できなかった」を「問題なし」と取り違えないため、ここで必ず落とす。
    if len(found) < 4:
        problems.append(f"{key}: 解析できた日付が {len(found)} 件しかない"
                        f"（ページ構造が変わった疑い）→ verify_uk_eu_calendar.py を要修正")
        print("   --- 解析できなかったので素のテキストを出す（構造を見て直す用）---")
        for ln in text.splitlines()[:70]:
            print(f"      {ln[:170]}")
        return
    for d in found:
        print(f"   公式: {d} ({wd(d)})")

    js, ms = ours_from_json(pattern), ours_from_master(pattern)
    # ⚠️ 「未登録」の指摘は HORIZON までに限る。ECB は2年半先まで日程を公開しており、
    #    そこまで全部要求すると毎週 ℹ️ が大量に出続けて**本当の指摘が埋もれる**。
    #    食い違い（🚨）の検査は期間を絞らない＝誤りは先の年でも必ず捕まえる。
    future = [d for d in found if today <= d <= today + HORIZON]
    # 🚨 未来の回を1件も比べていない＝実質何も検証していない。緑にしてはいけない
    if not future:
        problems.append(f"{key}: 今日から{HORIZON.days}日以内の回が公式側に1件も無い"
                        f"（解析ミスか、公式の更新停止）")
        return
    for d in future:
        if d not in js:
            notes.append(f"economic-events.json: {d}（{wd(d)}）の{label}が未登録")
        if d.year == 2026 and d not in ms:
            notes.append(f"ECONOMIC_EVENTS_2026: {d}（{wd(d)}）の{label}が未登録")
    # 逆向き＝我々にあって公式に無い日付（＝誤登録）。ただし公式が先の年をまだ出していない
    # 期間は正常に起きるので、**公式の最終日より前のものだけ**を食い違いとして扱う。
    last, official = max(found), set(found)
    for lbl, mine in (("economic-events.json", js), ("ECONOMIC_EVENTS_2026", ms)):
        for d in sorted(mine):
            if today <= d <= last and d not in official:
                problems.append(f"🚨 {lbl}: {d} に{label}の発表を載せているが、公式日程に無い")


def main():
    ap = argparse.ArgumentParser(description="英・ユーロ圏の指標日程を一次情報と突き合わせる")
    ap.add_argument("--dump", action="store_true", help="取得したページの素のテキストを出す")
    args = ap.parse_args()

    today = dt.datetime.now(JST).date()
    problems, notes = [], []

    if args.dump:
        for key, url in [("BOE", BOE_URL), ("ECB", ECB_URL)] + [(k, u) for k, u, _ in ONS_SOURCES]:
            print(f"\n{'=' * 70}\n■ {key}: {url}\n{'=' * 70}")
            try:
                for ln in plain_text(fetch(url)).splitlines()[:140]:
                    print(f"   {ln[:170]}")
            except Exception as e:
                print(f"   ❌ 取得できない: {type(e).__name__}: {str(e)[:120]}")
        return 0

    check_policy("BOE", BOE_URL, "英中銀 政策金利発表", parse_boe,
                 r"英中銀", today, problems, notes)
    check_policy("ECB", ECB_URL, "ECB 政策金利発表", parse_ecb,
                 r"ECB", today, problems, notes)

    for key, url, pattern in ONS_SOURCES:
        print(f"\n■ {key}（ONS）: {url}")
        try:
            nxt = parse_ons_next(plain_text(fetch(url)))
        except Exception as e:
            problems.append(f"{key}: ONS を取得できない（{type(e).__name__}: {str(e)[:80]}）")
            continue
        if not nxt:
            problems.append(f"{key}: ONS の「Next release」を読み取れない"
                            f"（ページ構造が変わった疑い）→ verify_uk_eu_calendar.py を要修正")
            continue
        print(f"   公式 次回: {nxt} ({wd(nxt)})")
        if nxt < today:
            problems.append(f"{key}: ONS の次回公表日 {nxt} が過去になっている"
                            f"（公式の更新が止まっているか、取得先が違う）")
            continue
        if nxt not in ours_from_json(pattern):
            notes.append(f"economic-events.json: {nxt}（{wd(nxt)}）の{key}が未登録")
        if nxt.year == 2026 and nxt not in ours_from_master(pattern):
            notes.append(f"ECONOMIC_EVENTS_2026: {nxt}（{wd(nxt)}）の{key}が未登録")

    print("\n" + "-" * 50)
    for n in notes:
        print(f"  ℹ️  {n}")
    if problems:
        print(f"\n❌ 食い違い/検証不能 {len(problems)} 件")
        for p in problems:
            print(f"   {p}")
        print("\n→ generate_market_news.py の ECONOMIC_EVENTS_2026 と economic-events.json を"
              "公式の日付に直してください。**曜日から推測しないこと**。")
        return 1
    print("✅ 公式日程と一致（今日以降の回）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
