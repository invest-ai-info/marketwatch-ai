#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_economic_calendar.py — 米指標の発表日を**一次情報と機械で突き合わせる**。

🚨 なぜ必要か（2026-09-11 事故）:
   米CPI（8月分）を 9/10(木) と載せていたが、BLS 公式は **9/11(金)**。原因は「CPI は火〜木」という
   曜日からの推測。10月分も 11/12 → 正 11/10 で誤っていた。**これは 2026-07-02 に続く2度目**で、
   そのとき作った `check_economic_events()` は曜日ヒューリスティクスだったため拾えなかった。
   🔑 **曜日ルールを足してはいけない**＝正しい金曜(9/11)を弾き、誤った木曜(9/10)を通してしまう。
   日付の正しさは推測では決まらない。**一次情報と突き合わせる以外に本当の再発防止は無い。**

🔑 実行場所が肝:
   Claude セッションのコンテナからは bls.gov が egress 遮断される（CONNECT 403）が、
   **GitHub Actions のランナーからは届く**。だからこの検証は Actions で回す。

やること:
   BLS の公式スケジュール（CPI / Employment Situation）を取得 → 対象月と発表日を抽出 →
   `economic-events.json` と `ECONOMIC_EVENTS_2026`（generate_market_news.py）の日付と突合。
   食い違い・欠落があれば標準出力に出して exit 1（Actions が Issue 化する）。

⚠️ 黙って通さない: ページ構造が変わって解析できなかった場合も **exit 1**（「検証できなかった」を
   「問題なし」と取り違えない）。パースできた行は必ずログに出すので、壊れたらログで分かる。

使い方:
   python verify_economic_calendar.py            # 検証（食い違いがあれば exit 1）
   python verify_economic_calendar.py --debug    # 取得したページの行テキストも出す
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

# BLS の公式スケジュール。指標ごとに (キー, URL, 我々の名前の接頭辞)
SOURCES = [
    ("CPI", "https://www.bls.gov/schedule/news_release/cpi.htm", "米CPI"),
    ("雇用統計", "https://www.bls.gov/schedule/news_release/empsit.htm", "米雇用統計"),
]

MONTHS = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June",
     "July", "August", "September", "October", "November", "December"], start=1)}
MONTH_RE = "|".join(MONTHS)
# 「Friday, September 11, 2026」「September 11, 2026」どちらも拾う
DATE_RE = re.compile(rf"(?:\w+,\s*)?({MONTH_RE})\s+(\d{{1,2}}),\s*(\d{{4}})")
# 参照期間「for August 2026」「August 2026」
REF_RE = re.compile(rf"\b({MONTH_RE})\s+(\d{{4}})\b")


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def rows_of(html_text):
    """<tr> 単位でタグを剥いだテキストにする（表の構造が変わっても行単位なら耐える）。"""
    out = []
    for chunk in re.split(r"<tr\b", html_text, flags=re.I)[1:]:
        chunk = chunk.split("</tr>")[0]
        txt = re.sub(r"<[^>]+>", " | ", chunk)
        txt = re.sub(r"&nbsp;?", " ", txt)
        txt = re.sub(r"\s*\|\s*(\|\s*)+", " | ", txt)
        txt = re.sub(r"[ \t]+", " ", txt).strip(" |\n")
        if txt:
            out.append(txt)
    return out


def parse_schedule(html_text, debug=False):
    """{(年, 対象月): 発表日(date)} を返す。行に参照期間と発表日が両方あるものだけ採る。"""
    found = {}
    for row in rows_of(html_text):
        if debug:
            print(f"      [row] {row[:150]}")
        dates = DATE_RE.findall(row)
        if not dates:
            continue
        # 行の中の「最後の」年月日を発表日とみなし、それ以外の月年を参照期間候補にする
        rel_m, rel_d, rel_y = dates[-1]
        release = dt.date(int(rel_y), MONTHS[rel_m], int(rel_d))
        refs = [(m, y) for (m, y) in REF_RE.findall(row)
                if not (m == rel_m and y == rel_y and f"{m} {rel_d}, {rel_y}" in row)]
        # 参照期間は発表日より前の月のはず
        cands = [(MONTHS[m], int(y)) for (m, y) in refs
                 if dt.date(int(y), MONTHS[m], 1) < dt.date(release.year, release.month, 1)]
        if not cands:
            continue
        mo, yr = cands[-1]
        found[(yr, mo)] = release
    return found


def ours_from_json():
    """economic-events.json から {(年, 対象月, 指標): date} を作る。"""
    path = os.path.join(HERE, "economic-events.json")
    if not os.path.exists(path):
        return {}
    d = json.load(open(path, encoding="utf-8"))
    out = {}
    for e in d.get("events", []):
        name = e.get("name", "")
        m = re.match(r"^米 ?(CPI|雇用統計)（(\d{1,2})月分）", name)
        if not m:
            continue
        when = dt.datetime.fromisoformat(e["datetime"]).astimezone(JST).date()
        out[(when.year if int(m.group(2)) <= when.month else when.year - 1,
             int(m.group(2)), m.group(1))] = when
    return out


def ours_from_master():
    """generate_market_news.py の ECONOMIC_EVENTS_2026 から {(年, 対象月, 指標): date}。"""
    path = os.path.join(HERE, "generate_market_news.py")
    if not os.path.exists(path):
        return {}
    src = open(path, encoding="utf-8").read()
    m = re.search(r"ECONOMIC_EVENTS_2026\s*=\s*\[(.*?)\n\]", src, re.S)
    if not m:
        return {}
    out = {}
    for mo, dy, _c, _i, name in re.findall(
            r'\(\s*(\d+),\s*(\d+),\s*"(\w+)",\s*"(\w+)",\s*"([^"]+)"', m.group(1)):
        k = re.match(r"^米(CPI|雇用統計)（(\d{1,2})月分）", name)
        if not k:
            continue
        rel = dt.date(2026, int(mo), int(dy))
        ref_mo = int(k.group(2))
        out[(rel.year if ref_mo <= rel.month else rel.year - 1, ref_mo, k.group(1))] = rel
    return out


def main():
    ap = argparse.ArgumentParser(description="米指標の発表日を BLS 公式と突き合わせる")
    ap.add_argument("--debug", action="store_true", help="取得ページの行テキストも出す")
    args = ap.parse_args()

    today = dt.datetime.now(JST).date()
    problems, notes = [], []
    js, ms = ours_from_json(), ours_from_master()

    for key, url, prefix in SOURCES:
        print(f"\n■ {key}: {url}")
        try:
            html_text = fetch(url)
        except Exception as e:
            problems.append(f"{key}: 公式スケジュールを取得できない（{type(e).__name__}: {str(e)[:80]}）")
            continue
        sched = parse_schedule(html_text, debug=args.debug)
        if not sched:
            problems.append(f"{key}: ページを解析できず0件（BLS の表の構造が変わった疑い）→ 要修正")
            continue
        for (yr, mo), rel in sorted(sched.items()):
            print(f"   公式: {yr}年{mo}月分 → {rel} ({'月火水木金土日'[rel.weekday()]})")

        for (yr, mo), rel in sorted(sched.items()):
            if rel < today:
                continue                       # 過ぎた回は直しても意味がない
            for label, mine in (("economic-events.json", js), ("ECONOMIC_EVENTS_2026", ms)):
                got = mine.get((yr, mo, key))
                if got is None:
                    notes.append(f"{label}: {yr}年{mo}月分の{prefix}が未登録（公式は {rel}）")
                elif got != rel:
                    problems.append(
                        f"🚨 {label}: {yr}年{mo}月分の{prefix} が {got} になっているが、"
                        f"BLS 公式は {rel}（{'月火水木金土日'[rel.weekday()]}曜）")

    print("\n" + "-" * 50)
    for n in notes:
        print(f"  ℹ️  {n}")
    if problems:
        print(f"\n❌ 食い違い/検証不能 {len(problems)} 件")
        for p in problems:
            print(f"   {p}")
        print("\n→ generate_market_news.py の ECONOMIC_EVENTS_2026 と economic-events.json を"
              "公式の日付に直してください。**曜日から推測しないこと**（2026-09-11 事故）。")
        return 1
    print("✅ 公式スケジュールと一致（今日以降の回）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
