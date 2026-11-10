# -*- coding: utf-8 -*-
"""TDnet の開示 → 次の丸1日の値動き（tdnet_reaction.py・J51・試験）のテスト。2026-11-10 新設。

値段と一覧はすべて作り物。確かめること＝①時刻の区切り（寄り前・場中・引け後）②重複のまとめ（同じ会社・同じ反応の日＝1件・
訂正だけ・種類なし・ETF/投資法人を除く・向き）③直前の値段（引け後＝終値・場中＝開示までに終わった最後の5分足・昼休み・
足が無ければ前の日の終値）④反応・窓・その日の残り・TOPIX との差 ⑤まだ送っていない日の選び方（16:30 より前は待つ・送った日・
開始日・週末）⑥台帳に表題と会社名を置かない・メールには載せる ⑦ワークフロー・SYNC 禁忌・見張り番・事前登録。

実行:  python tests/test_tdnet_reaction.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import tdnet_reaction as R  # noqa: E402

JST = R.JST
DAYS = ["2026-11-06", "2026-11-09", "2026-11-10", "2026-11-11"]


def row(tm, code, title, doc="d", name="テスト"):
    return {"time": tm, "code": code, "name": name, "title": title, "doc": doc, "place": "東"}


def bar(day, hh, mm, o, c):
    return (dt.datetime.fromisoformat(f"{day}T{hh:02d}:{mm:02d}").replace(tzinfo=JST), o, max(o, c), min(o, c), c, 100.0)


def test_slot():
    assert R.slot_of("08:59") == "寄り前"
    assert R.slot_of("09:00") == "場中"
    assert R.slot_of("15:29") == "場中"
    assert R.slot_of("15:30") == "引け後"
    assert R.slot_of("21:00") == "引け後"


def test_group():
    rows = [
        row("15:30", "1111", "2026年3月期 第2四半期決算短信〔日本基準〕(連結)", "a1", "あ社"),
        row("15:30", "1111", "通期業績予想の修正に関するお知らせ", "a2", "あ社"),
        row("16:00", "1111", "2026年3月期 第2四半期決算説明資料", "a3", "あ社"),
        row("15:00", "2222", "（訂正）「2026年3月期 第2四半期決算短信」の一部訂正について", "b1"),
        row("13:00", "3333", "代表取締役の異動に関するお知らせ", "c1"),
        row("08:30", "4444", "業績予想の上方修正に関するお知らせ", "e1"),
        row("15:30", "1306", "ＴＯＰＩＸ連動型上場投資信託 ETF 日々の開示事項", "f1"),
        row("15:30", "8951", "日本ビルファンド投資法人 決算短信", "g1", "日本ビルファンド投資法人"),
    ]
    gs = R.group_rows(rows, "2026-11-10", DAYS, {"a2": ("下方", "")})
    by = {g["code"]: g for g in gs}
    assert set(by) == {"1111", "2222", "3333", "4444"}, by.keys()       # ETF・投資法人は除く
    a = by["1111"]
    assert len(a["docs"]) == 3 and a["tags"] == ["決算", "業績修正"]
    assert a["rev"] == "下方"                                              # PDF の表の向きが表題より先
    assert a["slot"] == "引け後" and a["time"] == "15:30" and a["react_on"] == "2026-11-11"
    assert by["2222"]["tags"] == ["訂正"] and by["2222"]["slot"] == "場中"
    assert by["3333"]["tags"] == ["その他"]
    e = by["4444"]
    assert e["slot"] == "寄り前" and e["react_on"] == "2026-11-10" and e["rev"] == "上方"   # 表題の言葉で向き
    assert R.kind_keys(a) == ["決算", "下方修正"]
    # 反応の日がまだ無い（次の取引日が一覧に無い）
    g2 = R.group_rows([row("15:30", "1111", "決算短信")], "2026-11-11", DAYS)
    assert g2[0]["react_on"] is None


def test_base_and_measure():
    daily = {"2026-11-09": (100, 100), "2026-11-10": (102, 104), "2026-11-11": (110, 112)}
    tx = {"2026-11-09": (400, 400), "2026-11-10": (402, 404), "2026-11-11": (406, 408)}
    b5 = [bar("2026-11-10", 14, 50, 103, 103.5), bar("2026-11-10", 14, 55, 103.5, 105), bar("2026-11-10", 15, 0, 105, 106)]
    t5 = [bar("2026-11-10", 14, 55, 403, 404), bar("2026-11-10", 15, 0, 404, 405)]
    # 場中 15:00 → 14:55 の足の終値 105（15:00 の足は開示の時刻をまたぐ＝使わない）
    assert R.base_price("場中", "2026-11-10", "15:00", daily, b5, DAYS) == (105, "2026-11-10")
    # 昼休み 12:00 → その日の 11:25 までの足（ここでは無い）→ 前の日の終値
    assert R.base_price("場中", "2026-11-10", "12:00", daily, b5, DAYS) == (100, "2026-11-09")
    assert R.base_price("引け後", "2026-11-10", "15:30", daily, b5, DAYS) == (104, "2026-11-10")
    assert R.base_price("寄り前", "2026-11-10", "08:00", daily, b5, DAYS) == (100, "2026-11-09")
    g = {"date": "2026-11-10", "time": "15:00", "slot": "場中", "react_on": "2026-11-11"}
    m = R.measure(g, daily, b5, DAYS, tx, t5)
    assert m["ok"] == 1 and m["base_on"] == "2026-11-10"
    assert abs(m["react"] - (112 / 105 - 1)) < 1e-12
    assert abs(m["rest"] - (104 / 105 - 1)) < 1e-12
    assert abs(m["gap"] - (110 / 104 - 1)) < 1e-12
    assert abs(m["topix"] - (408 / 404 - 1)) < 1e-12
    assert abs(m["ex"] - (m["react"] - m["topix"])) < 1e-12
    g = {"date": "2026-11-10", "time": "16:00", "slot": "引け後", "react_on": "2026-11-11"}
    m = R.measure(g, daily, None, DAYS, tx, None)
    assert abs(m["react"] - (112 / 104 - 1)) < 1e-12 and m["rest"] is None
    # 反応の日の値段が無い・まだ反応の日が無い＝測らない
    assert R.measure(dict(g, react_on="2026-11-12"), daily, None, DAYS, tx, None)["ok"] == 0
    assert R.measure(dict(g, react_on=None), daily, None, DAYS, tx, None)["ok"] == 0


def test_pending():
    tdays = ["2026-11-09", "2026-11-10", "2026-11-11"]
    early = dt.datetime(2026, 11, 11, 16, 0, tzinfo=JST)
    late = dt.datetime(2026, 11, 11, 16, 31, tzinfo=JST)
    assert R.pending_days(early, set(), tdays, start="2026-11-09") == ["2026-11-09"]    # 11/10 の開示は 11/11 16:30 まで待つ
    assert R.pending_days(late, set(), tdays, start="2026-11-09") == ["2026-11-09", "2026-11-10"]
    assert R.pending_days(late, {"2026-11-09"}, tdays, start="2026-11-09") == ["2026-11-10"]
    assert R.pending_days(late, set(), tdays, start="2026-11-10") == ["2026-11-10"]
    sat = dt.datetime(2026, 11, 14, 10, 0, tzinfo=JST)
    assert "2026-11-14" not in R.pending_days(sat, set(), tdays + ["2026-11-12", "2026-11-13", "2026-11-16"], start="2026-11-09")


def _measured_groups():
    rows = [row("15:30", "1111", "業績予想の上方修正に関するお知らせ", "a1", "あいう商事"),
            row("15:30", "2222", "業績予想の下方修正に関するお知らせ", "b1", "かきく工業"),
            row("16:00", "3333", "代表取締役の異動に関するお知らせ", "c1", "さしす電機")]
    gs = R.group_rows(rows, "2026-11-10", DAYS)
    for g, ex in zip(gs, (0.05, -0.04, 0.001)):
        g.update({"ok": 1, "react": ex + 0.01, "topix": 0.01, "ex": ex, "gap": ex / 2, "rest": None, "base_on": "2026-11-10"})
    return gs


def test_mail_and_ledger_privacy():
    gs = _measured_groups()
    subj, body = R.build_mail("2026-11-10", gs, 3)
    assert "11/10（火）" in subj and "11/11（水）" in subj and "3社" in subj
    assert "あいう商事" in body and "業績予想の上方修正" in body       # メールには会社名と表題を載せる
    assert "【上方修正（TOPIX比の大きい順）】" in body and "【下方修正（TOPIX比の小さい順）】" in body
    assert "10社未満（参考・平均だけ）：" in body and "上方修正 1社 +5.0%" in body
    assert "トークンは使わない" in body
    rows = R.ledger_rows(gs)
    assert set(rows[0]) == set(R.COLS[:16])                              # 1週間・1か月はあとから埋める
    flat = " ".join(str(v) for r in rows for v in r.values())
    assert "あいう商事" not in flat and "修正に関する" not in flat      # 台帳には会社名・表題を置かない
    import mail_html
    html = mail_html.to_html(body, subj)
    assert "1111" in html and "あいう商事" in html


def test_run_day_with_fakes():
    tdays = ["2026-11-09", "2026-11-10", "2026-11-11"]

    def fetcher(day):
        return 2, [row("15:30", "1111", "決算短信", "a1"), row("15:30", "1306", "ETF 日々の開示事項", "x")]

    def getter(code, interval, rng):
        if interval == "5m":
            return []
        base = 400.0 if code == "1306" else 100.0
        return [bar("2026-11-09", 9, 0, base, base), bar("2026-11-10", 9, 0, base, base * 1.01),
                bar("2026-11-11", 9, 0, base * 1.02, base * 1.03)]

    groups, n = R.run_day("2026-11-10", tdays, [], getter=getter, fetcher=fetcher, log=lambda *_: None)
    assert n == 1 and len(groups) == 1 and groups[0]["ok"] == 1
    assert abs(groups[0]["ex"]) < 1e-12                                   # 同じ動き＝TOPIX との差 0


def test_main_title():
    g = {"docs": [{"time": "15:30", "title": "転換社債型新株予約権付社債の転換価額の調整", "tags": ["増資・売出し"]},
                  {"time": "15:30", "title": "第2四半期決算短信", "tags": ["決算"]},
                  {"time": "15:30", "title": "株券等に対する公開買付けに関する意見表明", "tags": ["TOB・上場廃止"]}]}
    assert R.main_title(g) == "株券等に対する公開買付けに関する意見表明"
    g["docs"].pop()
    assert R.main_title(g) == "第2四半期決算短信"
    assert R.main_title({"docs": [{"time": "16:00", "title": "人事", "tags": ["その他"]},
                                  {"time": "15:00", "title": "訂正", "tags": ["訂正"]}]}) == "人事"


def _days(start, n):
    out, d = [], dt.date.fromisoformat(start)
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += dt.timedelta(days=1)
    return out


def test_fill_horizons():
    days = _days("2026-11-09", 30)                      # 11/9（月）から30取引日
    R_ = days[1]                                         # 反応の日＝11/10
    ohlc = {d: (100.0 + i, 101.0 + i, 99.0 + i, 100.0 + i) for i, d in enumerate(days)}
    tx = {d: (400.0, 400.0, 400.0, 400.0 * (1 + 0.001 * i)) for i, d in enumerate(days)}
    r = {"ok": "1", "react_on": R_, "react": "0.010000", "topix": "0.000000"}
    base = ohlc[R_][3] / 1.01
    t5, t20 = R.horizon_day(days, R_, 5), R.horizon_day(days, R_, 20)
    assert t5 == days[5] and t20 == days[20]
    # 5日目の引けの前（当日 16:00）＝まだ埋めない
    early = dt.datetime.fromisoformat(f"{t5}T16:00").replace(tzinfo=JST)
    assert not R.needs_fill(dict(r), days, early)
    late = dt.datetime.fromisoformat(f"{t5}T16:31").replace(tzinfo=JST)
    assert R.needs_fill(dict(r), days, late)
    assert R.fill_row(r, days, ohlc, tx, late)
    assert abs(float(r["d5"]) - (ohlc[t5][3] / base - 1)) < 1e-6
    tbase = tx[R_][3]
    assert abs(float(r["ex5"]) - (float(r["d5"]) - (tx[t5][3] / tbase - 1))) < 1e-6
    assert abs(float(r["hi5"]) - (ohlc[t5][1] / base - 1)) < 1e-6        # 1週間で一番高い＝5日目の高値（上げ続ける作り物）
    assert abs(float(r["lo5"]) - (ohlc[R_][2] / base - 1)) < 1e-6
    assert not r.get("d20")                                                # 1か月はまだ
    later = dt.datetime.fromisoformat(f"{t20}T17:00").replace(tzinfo=JST)
    assert R.fill_row(r, days, ohlc, tx, later) and r["d20"]
    assert not R.needs_fill(r, days, later)
    # 取引の無かった日は前の値（5日目が無い）
    o2 = {k: v for k, v in ohlc.items() if k != t5}
    r2 = {"ok": "1", "react_on": R_, "react": "0", "topix": "0"}
    R.fill_row(r2, days, o2, tx, late)
    assert abs(float(r2["d5"]) - (ohlc[days[4]][3] / ohlc[R_][3] - 1)) < 1e-6
    # 反応の日の値段が無い（上場廃止など）＝na・値段が取れなかった回＝空のまま（次の回にもう一度）
    r3 = {"ok": "1", "react_on": R_, "react": "0", "topix": "0"}
    R.fill_row(r3, days, {days[0]: ohlc[days[0]]}, tx, late)
    assert r3["d5"] == "na"
    r4 = {"ok": "1", "react_on": R_, "react": "0", "topix": "0"}
    assert not R.fill_row(r4, days, {}, tx, late) and not r4.get("d5")


def _rows(kind_tag, rev, vals_by_day):
    out = []
    for d, vals in vals_by_day.items():
        for i, v in enumerate(vals):
            out.append({"date": d, "code": f"{i:04d}", "ok": "1", "tags": kind_tag, "rev": rev, "diff": "",
                        "ex": f"{v:.6f}", "ex5": f"{v:.6f}", "ex20": ""})
    return out


def test_judge_rules():
    days = _days("2026-11-11", 40)
    up = _rows("業績修正", "上方", {d: [0.02 + 0.001 * (i % 3), 0.01, 0.03] for i, d in enumerate(days)})   # 120社・40日
    # 判定の日より前は判定しない
    assert R.judge_cell(R.cell_values(up, "上方修正", "ex"), "2027-02-14") is None
    v = R.judge_cell(R.cell_values(up, "上方修正", "ex"), "2027-02-15")
    assert v and v["status"] == "✅ 上向き" and v["n"] == 120 and v["days"] == 40
    # 100社に届かない・開示の日が20日に届かない＝たまり中
    assert R.judge_cell(R.cell_values(up[:99], "上方修正", "ex"), "2027-03-01") is None
    few_days = _rows("業績修正", "上方", {d: [0.02] * 10 for d in days[:12]})
    assert R.judge_cell(R.cell_values(few_days, "上方修正", "ex"), "2027-03-01") is None
    # 前半と後半で向きが逆＝見えない
    mixed = _rows("業績修正", "上方", {d: [0.05 if i < 20 else -0.01] * 3 for i, d in enumerate(days)})
    assert R.judge_cell(R.cell_values(mixed, "上方修正", "ex"), "2027-03-01")["status"] == "✕ 見えない"
    # 平均 0 のまわりでばらつく＝見えない
    noise = _rows("決算", "", {d: ([0.03, 0.01, 0.02] if i % 2 == 0 else [-0.03, -0.01, -0.02]) for i, d in enumerate(days)})
    assert R.judge_cell(R.cell_values(noise, "決算", "ex"), "2027-03-01")["status"] == "✕ 見えない"
    # 開示の日でまとめる＝同じ日の会社が多くても日数で割る
    m, z, g = R.cluster_z([("a", 0.01), ("a", 0.01), ("b", 0.03)])
    assert g == 2 and abs(m - 0.05 / 3) < 1e-12
    assert 3.3 < R.z_crit() < 3.5


def test_trend_build_and_fix():
    days = _days("2026-11-11", 40)
    up = _rows("業績修正", "上方", {d: [0.02 + 0.001 * (i % 3), 0.01, 0.03] for i, d in enumerate(days)})
    early = _rows("業績修正", "上方", {"2026-11-09": [-0.5] * 5})            # 登録より前の開示＝累積には入るが判定には使わない
    tr = R.build_trend(up + early, {}, "2027-02-15")
    c = tr["cells"]["上方修正"]
    assert c["次の日"]["n"] == 125 and c["1か月"]["n"] == 0
    v = tr["verdicts"]["上方修正|次の日"]
    assert v["n"] == 120 and v["status"] == "✅ 上向き"
    # 一度決めた判定は、あとでデータが変わっても変えない
    flipped = [dict(r, ex="-0.100000") for r in up]
    tr2 = R.build_trend(flipped, tr, "2027-03-01")
    assert tr2["verdicts"]["上方修正|次の日"] == v
    lines = "\n".join(R.trend_lines(tr))
    assert "【これまでの傾向" in lines and "上方修正：次の日 " in lines and "判定（1回だけ・固定）" in lines
    gs = _measured_groups()
    subj, body = R.build_mail("2026-11-10", gs, 3, tr)
    assert "【これまでの傾向" in body


def test_wiring():
    wf = open(".github/workflows/tdnet-reaction.yml", encoding="utf-8").read()
    for w in ("python tests/test_tdnet_reaction.py", "python tdnet_reaction.py", "GMAIL_APP_PASSWORD",
              "tdnet-reaction.csv", "tdnet-reaction-days.json", "tdnet-reaction-trend.json", "concurrency", "workflow_dispatch"):
        assert w in wf, w
    import check_site_consistency as C
    for f in ("tdnet-reaction.csv", "tdnet-reaction-days.json", "tdnet-reaction-trend.json"):
        assert f in C.SYNC_FORBIDDEN, f
    assert "tdnet-reaction.yml" in open("check_automation_health.py", encoding="utf-8").read()
    pre = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## J51 " in pre and "tdnet_reaction.py" in pre and "2027-02-15" in pre and "0.05/69" in pre
    assert "tdnet-reaction.yml" in open("RESEARCH_LABS.md", encoding="utf-8").read()


if __name__ == "__main__":
    n = 0
    for k, f in list(globals().items()):
        if k.startswith("test_") and callable(f):
            f()
            n += 1
    print(f"✅ {n} 件 OK")
