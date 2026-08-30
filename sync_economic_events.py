"""economic-events.json の「経済指標」エントリを generate_market_news.py の
ECONOMIC_EVENTS_2026 から生成する（台帳の二重管理を解消する）。

── なぜ要るのか（2026-08-30 に判明した事故） ──
economic-events.json の指標は **2026-07-31 を最後に2か月ゼロ**だった。原因は
monthly-calendar-reminder.yml が「来月の指標を Gemini で取得してメールを送る」だけで、
JSON へ書くのは人手（`_update_policy` の「月初に当月分を手動更新」）だったため。
7月末で転記が止まり、しかもワークフローはメールを送れば success なので
automation-health からは正常に見えていた（＝weekly-levels と同じ死角）。

実害はシグナル側。generate_technical_alerts.py はこの JSON を見て
「🚫 重要指標まで X h」を出すので、8月は指標発表24時間前に出た **113本**の
シグナルに警告が付かなかった（うち12本は発表0.6時間前）。

読者向けの calendar.html は別系統（ECONOMIC_EVENTS_2026）で作られており無事だった。
＝**同じ情報の台帳が2つあり、片方だけ死んでいた**。本スクリプトは前者を後者から
生成することで、手動転記の工程そのものを無くす。

── 設計上の約束 ──
1. **時刻を創作しない。** 発表時刻・impact・affected_assets は、economic-events.json に
   実在する検証済みエントリ（2026-05〜07 の29件）から抽出した先例だけを使う。
   先例の無い種類（ISM・全国CPI・日銀短観・中国GDP・FOMC/日銀の1日目）は**足さない**。
2. **時刻は現地時間で持ち、tz 変換で JST にする。** 米指標は夏時間で1時間ずれる
   （1月の記述は「日本時間22:30」だが6〜7月の実データは21:30）。手計算しない。
3. **既存エントリは触らない。** 追加のみ・冪等。市場休場（category=market_holiday、
   generate_market_holidays.py が自動補充）にも一切手を出さない。
4. **突き合わせできる月は突き合わせる。** 両方の台帳にデータがある月で不一致が出たら
   標準出力に警告を出す（黙って上書きしない）。2026-06 の ECB と日銀で既知の不一致あり。
"""
import datetime as dt
import io
import json
import os
import re
import sys
import zoneinfo

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE_PY = os.path.join(HERE, "generate_market_news.py")
TARGET_JSON = os.path.join(HERE, "economic-events.json")

JST = zoneinfo.ZoneInfo("Asia/Tokyo")
NY = zoneinfo.ZoneInfo("America/New_York")
LONDON = zoneinfo.ZoneInfo("Europe/London")
FRANKFURT = zoneinfo.ZoneInfo("Europe/Berlin")
SHANGHAI = zoneinfo.ZoneInfo("Asia/Shanghai")

# 種類ごとの発表条件。すべて economic-events.json の既存29件から抽出した実績値。
#   pattern    : ECONOMIC_EVENTS_2026 の name に対する照合
#   local_time : 発表元の現地時刻（tz 変換で JST にする＝夏時間を取り違えない）
#   day_offset : 現地日から見た開催日のズレ（FOMC は現地14:00＝翌日 JST になるが
#                これは tz 変換が吸収するので 0。ここは開催日そのものの補正用）
#   impact / assets / country : 既存エントリの値をそのまま踏襲
RULES = [
    # ── 米国（8:30 ET 発表群）──
    dict(pattern=r"米雇用統計",      tz=NY, local_time=(8, 30),  impact="critical",
         assets=["all"], country="US", label="米雇用統計 NFP", json_pattern=r"米雇用統計"),
    dict(pattern=r"米CPI",           tz=NY, local_time=(8, 30),  impact="critical",
         assets=["all"], country="US", label="米 CPI", json_pattern=r"^米 ?CPI"),
    dict(pattern=r"^PPI|米PPI",      tz=NY, local_time=(8, 30),  impact="high",
         assets=["all"], country="US", label="米 PPI", json_pattern=r"米 ?PPI"),
    dict(pattern=r"小売売上高",      tz=NY, local_time=(8, 30),  impact="high",
         assets=["all"], country="US", label="米小売売上高", json_pattern=r"小売売上高"),
    dict(pattern=r"米GDP",           tz=NY, local_time=(8, 30),  impact="high",
         assets=["all"], country="US", label="米 GDP", json_pattern=r"米 ?GDP"),
    dict(pattern=r"PCEデフレーター", tz=NY, local_time=(8, 30),  impact="high",
         assets=["all"], country="US", label="米 PCE デフレーター", json_pattern=r"PCE"),
    # ── 政策金利（現地14:00 ET → JST では翌日未明。tz変換が日跨ぎを処理する）──
    dict(pattern=r"FOMC（結果発表）", tz=NY, local_time=(14, 0), impact="critical",
         assets=["all"], country="US", label="FOMC 政策金利発表", json_pattern=r"FOMC"),
    # ── 欧州・英国・日本・中国 ──
    dict(pattern=r"ECB理事会",       tz=FRANKFURT, local_time=(14, 15), impact="high",
         assets=["all"], country="EU", label="ECB 政策金利発表", json_pattern=r"ECB"),
    dict(pattern=r"日銀会合（結果発表）", tz=JST, local_time=(12, 0), impact="critical",
         assets=["NKD=F", "USDJPY=X"], country="JP", label="日銀金融政策決定会合", json_pattern=r"日銀"),
    dict(pattern=r"中国CPI",         tz=SHANGHAI, local_time=(9, 30), impact="high",
         assets=["NKD=F", "CL=F"], country="CN", label="中国 CPI", json_pattern=r"中国 ?CPI"),
]

# 先例が無いので**足さない**種類（黙って落とさず、実行時に一覧を出す）
NO_PRECEDENT = [
    r"ISM", r"全国CPI", r"日銀短観", r"中国GDP",
    r"FOMC（1日目）", r"日銀金融政策決定会合（1日目）",
]


def load_source_rows():
    """generate_market_news.py の ECONOMIC_EVENTS_2026 を読む（import しない＝副作用回避）。"""
    s = io.open(SOURCE_PY, encoding="utf-8").read()
    m = re.search(r"ECONOMIC_EVENTS_2026\s*=\s*\[(.*?)\n\]", s, re.S)
    if not m:
        raise SystemExit("❌ ECONOMIC_EVENTS_2026 が見つからない（定義が動いた？）")
    rows = re.findall(
        r"\(\s*(\d+)\s*,\s*(\d+)\s*,\s*\"(\w+)\"\s*,\s*\"(\w+)\"\s*,\s*\"([^\"]+)\"\s*,\s*\"([^\"]*)\"",
        m.group(1))
    if not rows:
        raise SystemExit("❌ ECONOMIC_EVENTS_2026 を1件も解釈できなかった（書式が変わった？）")
    return [(int(a), int(b), c, d, e, f) for a, b, c, d, e, f in rows]


def match_rule(name):
    for r in RULES:
        if re.search(r["pattern"], name):
            return r
    return None


def is_known_skip(name):
    return any(re.search(p, name) for p in NO_PRECEDENT)


def build_entry(year, month, day, rule, name):
    hh, mm = rule["local_time"]
    local = dt.datetime(year, month, day, hh, mm, tzinfo=rule["tz"])
    jst = local.astimezone(JST)
    # 既存の命名（「米 PCE デフレーター（5月）」等）に合わせ、元の括弧書きだけを引き継ぐ
    suffix = ""
    mm_ = re.search(r"（([^）]*)）", name)
    if mm_:
        suffix = f"（{mm_.group(1)}）"
    return {
        "name": f"{rule['label']}{suffix}",
        "datetime": jst.isoformat(timespec="minutes"),
        "impact": rule["impact"],
        "affected_assets": list(rule["assets"]),
        "country": rule["country"],
        "category": "economic_indicator",
        "note": f"sync_economic_events.py が ECONOMIC_EVENTS_2026 から生成"
                f"（現地 {local.strftime('%H:%M %Z')}）",
    }


def main():
    year = int(os.environ.get("EVENTS_YEAR", "2026"))
    apply_changes = "--write" in sys.argv

    data = json.load(open(TARGET_JSON, encoding="utf-8"))
    existing = data["events"]
    existing_ind = [e for e in existing if e.get("category") != "market_holiday"]
    # 既存の (日付, 種類ラベル) を索引化＝同じ日の同じ指標は二重に足さない
    # 既存エントリを RULES に写像する。名前の表記ゆれ（「米雇用統計 6 月 NFP」等）が
    # あるので文字列一致ではなく json_pattern で当てる。
    def rule_of_existing(nm):
        for r in RULES:
            if re.search(r["json_pattern"], nm):
                return r["label"]
        return None

    have = set()
    have_month_label = {}
    for e in existing_ind:
        lab = rule_of_existing(e["name"])
        if not lab:
            continue
        have.add((e["datetime"][:10], lab))
        have_month_label.setdefault((e["datetime"][:7], lab), e["datetime"][:16])

    # シグナルの事前警告が用途なので、過ぎたイベントは足さない（履歴の水増しを避ける）。
    # 7日の猶予＝当日/前日ぶんを取りこぼさない。
    cutoff = (dt.datetime.now(JST) - dt.timedelta(days=7)).isoformat(timespec="minutes")

    added, skipped_no_precedent, conflicts, already, past = [], [], [], 0, 0
    for month, day, _country, _imp, name, _desc in load_source_rows():
        rule = match_rule(name)
        if rule is None:
            if is_known_skip(name):
                skipped_no_precedent.append(f"{month}/{day:02d} {name}")
            else:
                skipped_no_precedent.append(f"{month}/{day:02d} {name}  ⚠️未分類")
            continue
        entry = build_entry(year, month, day, rule, name)
        key = (entry["datetime"][:10], rule["label"])
        # 既存台帳に同じ月・同じ種類があるなら、日付が合うかを突き合わせる
        prev = have_month_label.get((entry["datetime"][:7], rule["label"]))
        if prev and prev[:10] != entry["datetime"][:10]:
            conflicts.append((rule["label"], prev, entry["datetime"][:16]))
            continue          # ← 不一致は黙って上書きしない。人が判断する
        if key in have or prev:
            already += 1
            continue
        if entry["datetime"] < cutoff:
            past += 1
            continue
        added.append(entry)

    print(f"ECONOMIC_EVENTS_2026: {len(load_source_rows())} 行")
    print(f"  既に economic-events.json にある: {already} 件")
    print(f"  過ぎたイベント（足さない）      : {past} 件")
    print(f"  先例が無いので足さない          : {len(skipped_no_precedent)} 件")
    for s in skipped_no_precedent:
        print(f"      - {s}")
    if conflicts:
        print(f"  ⚠️ 2つの台帳で日付が食い違う    : {len(conflicts)} 件（どちらも採用しない）")
        for label, a, b in conflicts:
            print(f"      - {label}: economic-events.json={a} / ECONOMIC_EVENTS_2026={b}")
    print(f"  追加する                        : {len(added)} 件")
    for e in sorted(added, key=lambda x: x["datetime"]):
        print(f"      + {e['datetime'][:16]} [{e['impact']:8s}] {e['name']}")

    if not apply_changes:
        print("\n（--write を付けると書き込みます。いまは何も変更していません）")
        return
    if not added:
        print("\n変更なし。")
        return
    data["events"] = sorted(existing + added, key=lambda x: x["datetime"])
    with open(TARGET_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"\n✅ economic-events.json に {len(added)} 件を追加（合計 {len(data['events'])} 件）")


if __name__ == "__main__":
    main()
