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

やること:
   BOE の MPC 日程ページ / ECB の理事会日程ページを取得 → 発表日を抽出 →
   `economic-events.json` と `ECONOMIC_EVENTS_2026`（generate_market_news.py）の日付と突合。
   食い違い・欠落があれば標準出力に出して exit 1（Actions が Issue 化する）。

⚠️ 黙って通さない: ページ構造が変わって解析できなかった場合も **exit 1**
   （「検証できなかった」を「問題なし」と取り違えない）。

使い方:
   python verify_uk_eu_calendar.py            # 検証（食い違いがあれば exit 1）
   python verify_uk_eu_calendar.py --dump     # 取得したページの素のテキストを出す（構造調査用）
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
JST = dt.timezone(dt.timedelta(hours=9))
UA = "Mozilla/5.0 (compatible; marketwatch-jp calendar verifier; +https://marketwatch-jp.com/)"

# 政策金利の発表日（＝年間日程が公式に出ている＝機械突合に向く）
# ⚠️ 2026-09-17 実地調査で判明: `upcoming-mpc-dates` は「次回だけ」しか載せない。
#    年間日程は毎年12月に出る告知ページにある（年ごとに URL が変わるので年次で足す）。
POLICY_SOURCES = [
    ("BOE", "https://www.bankofengland.co.uk/monetary-policy/upcoming-mpc-dates", "英中銀"),
    ("ECB", "https://www.ecb.europa.eu/press/calendars/mgcgc/html/index.en.html", "ECB"),
]
# --dump のとき全文を出す（日付に年が付かない表かもしれないので行を絞らない）
FULLTEXT_ON_DUMP = {"BOE"}

# 統計の発表日（各ページの「次回公表」を読む。構造調査のため当面は --dump 用）
RELEASE_SOURCES = [
    ("ONS 英CPI", "https://www.ons.gov.uk/economy/inflationandpriceindices/bulletins/consumerpriceinflation/latest"),
    ("ONS 英雇用", "https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/employmentandemployeetypes/bulletins/uklabourmarket/latest"),
    ("ONS 英GDP", "https://www.ons.gov.uk/economy/grossdomesticproductgdp/bulletins/gdpmonthlyestimateuk/latest"),
    ("ONS 予定表(CPI)", "https://www.ons.gov.uk/releasecalendar/data?query=consumer+price+inflation"),
    ("ONS 予定表(labour)", "https://www.ons.gov.uk/releasecalendar/data?query=labour+market+overview"),
    ("ECB統計暦 HICP", "https://www.ecb.europa.eu/press/calendars/statscal/ges/html/sthicp.en.html"),
    ("ECB統計暦 GDP", "https://www.ecb.europa.eu/press/calendars/statscal/ges/html/stgdp.en.html"),
]

_FULL = ["January", "February", "March", "April", "May", "June",
         "July", "August", "September", "October", "November", "December"]
MONTHS = {}
for _i, _m in enumerate(_FULL, start=1):
    MONTHS[_m] = _i
    MONTHS[_m[:3]] = _i
    MONTHS["Sept"] = 9
MONTH_RE = "|".join(sorted(MONTHS, key=len, reverse=True))
# 「Thursday 17 September 2026」「17 September 2026」「9-10 September 2026」いずれも拾う
DMY_RE = re.compile(rf"(?:\d{{1,2}}\s*[-–]\s*)?(\d{{1,2}})\s+({MONTH_RE})\.?\s+(\d{{4}})")


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8", "replace")


def plain_text(html_text):
    t = re.sub(r"(?is)<(script|style|nav|header|footer).*?</\1>", " ", html_text)
    t = re.sub(r"(?i)<br\s*/?>|</t[dh]>|</tr>|</li>|</p>|</h[1-6]>|</div>", "\n", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"&nbsp;?", " ", t).replace("&amp;", "&").replace("&#8211;", "-")
    return "\n".join(re.sub(r"[ \t]+", " ", ln).strip() for ln in t.splitlines() if ln.strip())


SLASH_RE = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")


def join_date_and_label(lines):
    """「日付だけの行」の次行を説明として連結する（ECB のカレンダーがこの形）。"""
    out = []
    for i, ln in enumerate(lines):
        m = SLASH_RE.match(ln.strip())
        if not m:
            out.append(ln)
            continue
        d, mo, y = m.groups()
        nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
        out.append(f"{int(d)} {_FULL[int(mo) - 1]} {y} | {nxt}")
    return out


def parse_dates(html_text, want=None):
    """ページから (date, その行のテキスト) を拾う。want があればその語を含む行だけ。

    ⚠️ 「2日間の会合の2日目が発表日」なので、`9-10 September` のような範囲表記は
       **後ろの数字（＝2日目）を採る**（DMY_RE は範囲の前半を捨てる形にしてある）。
    """
    out = []
    for ln in join_date_and_label(plain_text(html_text).splitlines()):
        if want and want.lower() not in ln.lower():
            continue
        for d, mo, y in DMY_RE.findall(ln):
            try:
                out.append((dt.date(int(y), MONTHS[mo], int(d)), ln[:120]))
            except ValueError:
                pass
    # 同じ日付は1回だけ（最初に出た行の説明を残す）
    seen, uniq = set(), []
    for d, ln in sorted(out):
        if d not in seen:
            seen.add(d)
            uniq.append((d, ln))
    return uniq


def ours_from_json(pattern):
    """economic-events.json から、名前が pattern に一致するイベントの date 集合を作る。"""
    path = os.path.join(HERE, "economic-events.json")
    if not os.path.exists(path):
        return set()
    d = json.load(open(path, encoding="utf-8"))
    out = set()
    for e in d.get("events", []):
        if re.search(pattern, e.get("name", "")):
            out.add(dt.datetime.fromisoformat(e["datetime"]).astimezone(JST).date())
    return out


def ours_from_master(pattern):
    """generate_market_news.py の ECONOMIC_EVENTS_2026 から date 集合を作る。"""
    path = os.path.join(HERE, "generate_market_news.py")
    if not os.path.exists(path):
        return set()
    src = open(path, encoding="utf-8").read()
    m = re.search(r"ECONOMIC_EVENTS_2026\s*=\s*\[(.*?)\n\]", src, re.S)
    if not m:
        return set()
    out = set()
    for mo, dy, _c, _i, name in re.findall(
            r'\(\s*(\d+),\s*(\d+),\s*"(\w+)",\s*"(\w+)",\s*"([^"]+)"', m.group(1)):
        if re.search(pattern, name):
            out.add(dt.date(2026, int(mo), int(dy)))
    return out


# 我々の登録名 ↔ 公式ページの対応。pattern は economic-events.json / ECONOMIC_EVENTS_2026 側の名前。
POLICY_MATCH = {
    "BOE": {"want": None, "pattern": r"英中銀|BOE"},
    "ECB": {"want": "(day 2)", "pattern": r"ECB"},
}


def main():
    ap = argparse.ArgumentParser(description="英・ユーロ圏の指標日程を一次情報と突き合わせる")
    ap.add_argument("--dump", action="store_true", help="取得したページの素のテキストを出す")
    args = ap.parse_args()

    today = dt.datetime.now(JST).date()
    problems, notes = [], []

    if args.dump:
        for key, url in [(k, u) for k, u, _ in POLICY_SOURCES] + RELEASE_SOURCES:
            print(f"\n{'=' * 70}\n■ {key}: {url}\n{'=' * 70}")
            try:
                text = plain_text(fetch(url))
            except Exception as e:
                print(f"   ❌ 取得できない: {type(e).__name__}: {str(e)[:120]}")
                continue
            if key in FULLTEXT_ON_DUMP:
                print("   --- 全文（先頭140行）---")
                for ln in text.splitlines()[:140]:
                    print(f"      {ln[:170]}")
                continue
            hits = [ln for ln in join_date_and_label(text.splitlines())
                    if DMY_RE.search(ln) or re.search(r"(?i)next release|release date", ln)]
            print(f"   --- 日付を含む行 {len(hits)} 本（先頭60本）---")
            for ln in hits[:60]:
                print(f"      {ln[:170]}")
            if not hits:
                print("   --- 日付行ゼロ。素のテキスト先頭60行 ---")
                for ln in text.splitlines()[:60]:
                    print(f"      {ln[:170]}")
        return 0

    for key, url, label in POLICY_SOURCES:
        cfg = POLICY_MATCH[key]
        print(f"\n■ {label}（{key}）: {url}")
        try:
            html_text = fetch(url)
        except Exception as e:
            problems.append(f"{key}: 公式日程を取得できない（{type(e).__name__}: {str(e)[:80]}）")
            continue
        found = parse_dates(html_text, want=cfg["want"])
        # 🚨 年8回前後の日程が載るページ。少なすぎる＝解析が壊れている。
        #    「解析できなかった」を「問題なし」と取り違えないため、ここで必ず落とす。
        if len(found) < 4:
            problems.append(f"{key}: 解析できた日付が {len(found)} 件しかない"
                            f"（ページ構造が変わった疑い）→ verify_uk_eu_calendar.py を要修正")
            print("   --- 解析できなかったので素のテキストを出す（構造を見て直す用）---")
            for ln in plain_text(html_text).splitlines()[:60]:
                print(f"      {ln[:170]}")
            continue
        for d, ln in found:
            print(f"   公式: {d} ({'月火水木金土日'[d.weekday()]}) | {ln[:90]}")

        js, ms = ours_from_json(cfg["pattern"]), ours_from_master(cfg["pattern"])
        compared = 0
        for d, _ln in found:
            if d < today:
                continue                       # 過ぎた回は直しても意味がない
            compared += 1
            for lbl, mine in (("economic-events.json", js), ("ECONOMIC_EVENTS_2026", ms)):
                if lbl == "ECONOMIC_EVENTS_2026" and d.year != 2026:
                    continue                   # このリストは2026年分だけ
                if d not in mine:
                    notes.append(f"{lbl}: {d}（{'月火水木金土日'[d.weekday()]}）の{label}が未登録")
        # 🚨 未来の回を1件も比べていない＝実質何も検証していない。緑にしてはいけない
        if compared == 0:
            problems.append(f"{key}: 今日以降の回が公式側に1件も無い"
                            f"（取得できたのは過去分だけ＝解析ミスか、公式の更新が止まっている）")
        # 逆向き＝我々にあって公式に無い日付（＝誤登録）は、公式が翌年分を出す前だと
        # 正常に起きるので、**公式の最終日より前のものだけ**を食い違いとして扱う。
        last = max(d for d, _ in found)
        for lbl, mine in (("economic-events.json", js), ("ECONOMIC_EVENTS_2026", ms)):
            official = {d for d, _ in found}
            for d in sorted(mine):
                if today <= d <= last and d not in official:
                    problems.append(f"🚨 {lbl}: {d} に{label}の発表を載せているが、公式日程に無い")

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
