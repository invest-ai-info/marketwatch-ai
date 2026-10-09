# -*- coding: utf-8 -*-
"""J44 高値更新の台帳（highs_ledger.py）のテスト。2026-10-09 新設。

値動きはすべて作り物。確かめること＝①事前登録と定数の一致 ②特徴（更新幅・引けと前の高値・上ヒゲ・倍率・25日線・連騰・日数）
③そのあと（次の日・5日後・始値で窓と寄り→大引け）と区切り ④1日の更新（前の日の一覧も足す・二重にしない・始値を取り直す）
⑤CSV の読み書き ⑥区切りごとの表と md（判定しない・名前つき） ⑦build_jp_highs から安全に呼ぶ・ワークフロー・SYNC 禁忌。

実行:  python tests/test_highs_ledger.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import highs_ledger as L  # noqa: E402


def _bdays(start, n):
    d, out = dt.date.fromisoformat(start), []
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += dt.timedelta(days=1)
    return out


def _bars(n=40, start="2026-08-20", base=100.0, last=None):
    """[(日付, 高値, 安値, 終値, 出来高)]。last＝最後の何本かを {i: (高値, 安値, 終値, 出来高)} で差し替え"""
    out = []
    for i, d in enumerate(_bdays(start, n)):
        c = base + (0.2 if i % 2 else -0.2)
        out.append((d, c + 1.0, c - 1.0, c, 1e5))
    for i, (h, lo, c, v) in (last or {}).items():
        out[i] = (out[i][0], h, lo, c, v)
    return out


def _row(code="9999", day=None, prev=110.0, ext=120.0, pct=0.10, record=True, listed=True, hist_from="2025-12-01",
         prev_date="2026-09-01", akaji=None, name="テスト"):
    return {"code": code, "name": name, "sector": "情報・通信業", "market": "グロース", "akaji": akaji, "price": 115.0,
            "pct": pct, "ext": ext, "prev": prev, "prev_date": prev_date, "turnover": 1.0, "record": record,
            "record_prev": prev, "hist_from": hist_from, "listed": listed}


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## J44 高値更新の台帳" in text and "（読むだけ・判定しない）" in text
    assert L.START == "2026-10-08" and "**2026-10-08 の一覧から**" in text
    assert (L.UP1, L.DOWN1, L.UP5, L.DOWN5, L.AFTER) == (0.01, -0.01, 0.03, -0.03, 5)
    assert "**+1%以上「続伸」・−1%以下「だまし」・その間「横ばい」**" in text and "**+3%以上「続伸」・−3%以下「だまし」" in text
    for words in ("1年未満／1〜3年／3年以上", "+3%未満／+3〜10%／+10%以上", "2倍未満／2〜5倍／5〜10倍／10倍以上",
                  "+10%未満／+10〜20%／+20〜30%／+30%以上", "1%未満／1〜3%／3%以上", "0.3未満／0.3〜0.5／0.5以上",
                  "2日以下／3日／4日以上", "5日未満／5〜20日／20日以上", "1億円未満／1〜10億円／10億円以上", "−1%以下／±1%未満／+1%以上"):
        assert words in text, words
    spec = {col: s for _t, col, s in L.BUCKETS}
    assert [b[1:] for b in spec["age_days"]] == [(0, 365), (365, 1095), (1095, L.INF)]
    assert [b[1:] for b in spec["tv_ratio"]] == [(0, 2), (2, 5), (5, 10), (10, L.INF)]
    assert [b[1:] for b in spec["dev25"]][1:] == [(0.10, 0.20), (0.20, 0.30), (0.30, L.INF)]
    assert [b[1:] for b in spec["breakout"]][1:] == [(0.01, 0.03), (0.03, L.INF)]
    assert "**上場来高値（記録上の最高値＝一覧の record）のケースだけでも、全体・その日の特徴ごと・最近のケースの表を別に出す**" in text
    rec = [b[1] for b in L.RECORD_BUCKETS]
    assert rec[0] == "listed" and "record" not in rec and rec[1:] == [b[1] for b in L.BUCKETS if b[1] != "record"]


def test_features_from_the_row_and_the_day():
    bars = _bars(40, last={39: (120.0, 104.0, 112.0, 1e6)})           # 最後の日：高値120・安値104・終値112・出来高10倍
    day = bars[39][0]
    f = L.features(_row(day=day, prev=110.0, ext=120.0, prev_date="2026-09-01", hist_from="2025-12-01"), day, bars, "年初来")
    assert f["date"] == day and f["code"] == "9999" and f["record"] == 1 and f["listed"] == 1 and f["akaji"] == ""
    assert f["kind"] == L.KIND_LISTED
    assert abs(f["breakout"] - (120 / 110 - 1)) < 1e-9 and abs(f["close_vs_prev"] - (112 / 110 - 1)) < 1e-9
    assert abs(f["wick"] - 0.5) < 1e-9 and f["hi_close"] == 0                         # (120−112)/(120−104)
    assert f["tv_ratio"] > 9 and f["turnover"] > 1 and f["dev25"] > 0.1 and f["streak"] == 1
    assert f["age_days"] == L._days("2025-12-01", day) and f["days_since_prev"] == L._days("2026-09-01", day)
    assert L.features(_row(), "2030-01-01", bars) is None                              # その日の足が無い
    f2 = L.features(_row(prev=None, listed=None, akaji=True), day, bars)
    assert f2["breakout"] is None and f2["listed"] == "" and f2["akaji"] == 1 and f2["kind"] == L.KIND_RECORD
    assert L.features(_row(record=False, listed=None), day, bars)["kind"] == L.KIND_YTD


def test_labels():
    assert L.label(0.01, L.UP1, L.DOWN1) == L.LABEL_UP and L.label(-0.01, L.UP1, L.DOWN1) == L.LABEL_DOWN
    assert L.label(0.009, L.UP1, L.DOWN1) == L.LABEL_FLAT and L.label(None, L.UP1, L.DOWN1) == ""
    assert L.label(-0.03, L.UP5, L.DOWN5) == L.LABEL_DOWN and L.label(0.02, L.UP5, L.DOWN5) == L.LABEL_FLAT


def test_fill_after_next_day_five_days_and_opens():
    bars = _bars(40)
    day = bars[30][0]
    bars[30] = (day, 120.0, 110.0, 115.0, 1e5)
    bars[31] = (bars[31][0], 118.0, 100.0, 103.5, 1e5)                                   # 次の日 −10％・前の高値 110 の下
    case = dict({k: "" for k in L.AFTER_COLS}, date=day, code="9999", prev_high=110.0)
    assert L.fill_after(case, bars[:32]) and case["d1"] == bars[31][0] and case["label1"] == L.LABEL_DOWN
    assert abs(case["cc1"] - (103.5 / 115 - 1)) < 1e-9 and case["below_prev1"] == 1 and abs(case["hi1"] - (118 / 120 - 1)) < 1e-9
    assert case["d5"] == "" and L.needs_open(case, bars[31][0])
    assert L.fill_after(case, bars[:32], {bars[31][0]: 112.0})                          # 始値が取れたら窓と寄り→大引け
    assert abs(case["gap1"] - (112 / 115 - 1)) < 1e-9 and abs(case["oc1"] - (103.5 / 112 - 1)) < 1e-9
    assert not L.needs_open(case, bars[31][0])
    assert L.fill_after(case, bars) and case["d5"] == bars[35][0] and case["label5"] == L.LABEL_DOWN
    assert abs(case["max5"] - (max(b[1] for b in bars[31:36]) / 120 - 1)) < 1e-9
    assert not L.fill_after(case, bars)                                                  # もう埋まっている
    late = dict(case, gap1="", oc1="")
    assert not L.needs_open(late, "2026-12-31")                                          # 取り直す期間を過ぎた


def test_parse_opens_uses_jst_dates():
    t = int(dt.datetime(2026, 10, 9, 0, 0, tzinfo=L.JST).timestamp())
    res = {"timestamp": [t, t + 86400], "indicators": {"quote": [{"open": [100.0, None]}]}}
    assert L.parse_opens(res) == {"2026-10-09": 100.0}


def _day_bars(days, closes, highs=None):
    highs = highs or [c + 1 for c in closes]
    return [(d, h, c - 1, c, 1e5) for d, c, h in zip(days, closes, highs)]


def test_update_adds_both_lists_fills_and_never_duplicates():
    days = _bdays("2026-08-20", 37)                    # 最後の2本＝前の日（D0）と今日（D1）
    d0, d1 = days[-2], days[-1]
    a = _day_bars(days, [100.0] * 35 + [120.0, 110.0])   # A：D0 に高値更新 → D1 に −8.3％（だまし）
    b = _day_bars(days, [100.0] * 36 + [130.0])          # B：D1 に高値更新（まだそのあと無し）
    prev = {"asof": d0, "period": "年初来", "highs": [_row("1111", prev=112.0, ext=121.0, name="エー")]}   # D1 の終値 110 は前の高値 112 の下
    payload = {"asof": d1, "period": "年初来", "highs": [_row("2222", prev=105.0, ext=131.0, name="ビー")]}
    calls = []
    fetch = lambda code: calls.append(code) or {d1: 115.0}  # noqa: E731
    with tempfile.TemporaryDirectory() as tmp:
        csv_p, md_p = os.path.join(tmp, "l.csv"), os.path.join(tmp, "l.md")
        msg = L.update({"1111": a, "2222": b}, payload, prev, fetch, csv_p, md_p, now="x", sleep=0)
        cases = {c["code"]: c for c in L.read_ledger(csv_p)}
        assert set(cases) == {"1111", "2222"} and "今回 +2" in msg and calls == ["1111"]
        A = cases["1111"]
        assert A["date"] == d0 and A["label1"] == L.LABEL_DOWN and A["below_prev1"] == 1
        assert abs(A["gap1"] - (115 / 120 - 1)) < 1e-4 and abs(A["oc1"] - (110 / 115 - 1)) < 1e-4
        assert cases["2222"]["date"] == d1 and cases["2222"]["label1"] == ""
        md = open(md_p, encoding="utf-8").read()
        assert "## A. 年初来高値の更新（全部）" in md and "## B. 上場来高値の更新（記録上の最高値）だけ" in md
        assert md.count("### 全体") == 2 and md.count("### その日の特徴ごと") == 2 and "#### 上場の日からの記録か" in md
        assert "上場来高値（記録上の最高値）** 2件" in md and "上場から" in md and "投資助言ではありません" in md
        assert cases["1111"]["kind"] == L.KIND_LISTED
        assert "1111 エー" in md and "**だまし**" in md                                   # 最近のケースは名前つき
        msg2 = L.update({"1111": a, "2222": b}, payload, prev, fetch, csv_p, md_p, now="x", sleep=0)
        assert "今回 +0" in msg2 and len(L.read_ledger(csv_p)) == 2 and calls == ["1111"]    # 二重にしない・始値は取り直さない
        assert open(csv_p, "rb").read()[:3] == b"\xef\xbb\xbf"                             # Excel 用の BOM
        old = {"asof": "2026-10-01", "highs": [_row("3333")]}                              # START より前の一覧は足さない
        L.update({"1111": a, "2222": b}, payload, old, fetch, csv_p, md_p, now="x", sleep=0)
        assert "3333" not in {c["code"] for c in L.read_ledger(csv_p)}


def test_tables_count_by_bucket():
    cases = [dict({k: "" for k in L.COLS}, date="2026-10-08", code=str(i), age_days=age, record=rec, label1=lab, cc1=cc,
                  market="グロース")
             for i, (age, rec, lab, cc) in enumerate([(100, 1, L.LABEL_DOWN, -0.08), (200, 1, L.LABEL_DOWN, -0.11),
                                                      (5000, 1, L.LABEL_UP, 0.04), (5000, 0, L.LABEL_UP, 0.02)])]
    t = dict(L.tables(cases))
    age = dict(t["上場から"])
    assert age["1年未満"]["n"] == 2 and age["1年未満"]["down"] == 1.0 and age["3年以上"]["up"] == 1.0 and age["1〜3年"]["n"] == 0
    rec = dict(t["上場来の高値か"])
    assert rec["上場来（記録上の最高値）"]["n"] == 3 and rec["年初来だけ"]["n"] == 1
    assert dict(t["市場"])["グロース"]["n"] == 4
    assert L.bucket_of([("a", 0, 1)], "") is None and L.bucket_of({1: "x"}, 1.0) == "x"


def test_builder_calls_the_ledger_safely_and_workflow_commits_it():
    src = open("build_jp_highs.py", encoding="utf-8").read()
    i = src.index("import highs_ledger")
    assert "try:" in src[i - 200:i] and "except Exception" in src[i:i + 400] and "if not dry_run:" in src[i - 900:i]
    wf = open(".github/workflows/jp-highs.yml", encoding="utf-8").read()
    assert "git add highs-ledger.csv highs-ledger.md" in wf and "git add jp-highs.json" in wf
    assert '"highs-ledger.csv", "highs-ledger.md"' in open("check_site_consistency.py", encoding="utf-8").read()


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"✅ {name}")
            except AssertionError as e:
                fails += 1
                print(f"❌ {name}: {e}")
    sys.exit(1 if fails else 0)
