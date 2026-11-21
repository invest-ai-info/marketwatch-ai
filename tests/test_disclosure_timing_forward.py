# -*- coding: utf-8 -*-
"""J52F（disclosure_timing_forward.py・入るタイミングの前向き）のテスト。2026-11-17 新設。

値段はすべて作り物。確かめること＝①出来事の選び方（11/18 以降・上方/下方修正・J51 で測れたもの）②場中の値段（10:00・後場寄り）
③引けの道（取引の無い日は前の値・いちばん新しい日が空なら止める・確定前は入れない）④入る E1〜E8 と出る X0/X5/X20 の日の数え方
⑤押し目・戻り待ち（来なければ入らない）⑥1回だけの判定（件数・日数・向き・前半後半）⑦値段を置かない ⑧ワークフロー・SYNC 禁忌・登録。

実行:  python tests/test_disclosure_timing_forward.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import disclosure_timing_forward as F  # noqa: E402

JST = F.JST


def _days(start, n):
    out, d = [], dt.date.fromisoformat(start)
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += dt.timedelta(days=1)
    return out


def _bar(day, hh, mm, o, c, v=1000.0):
    return (dt.datetime.fromisoformat(f"{day}T{hh:02d}:{mm:02d}").replace(tzinfo=JST), o, max(o, c), min(o, c), c, v)


def test_events():
    rows = [
        {"date": "2026-11-17", "code": "1111", "ok": "1", "react_on": "2026-11-18", "time": "15:30", "tags": "業績修正", "rev": "上方", "diff": ""},
        {"date": "2026-11-18", "code": "2222", "ok": "1", "react_on": "2026-11-19", "time": "15:30", "tags": "決算|業績修正", "rev": "上方", "diff": ""},
        {"date": "2026-11-18", "code": "3333", "ok": "1", "react_on": "2026-11-19", "time": "15:00", "tags": "業績修正", "rev": "下方", "diff": ""},
        {"date": "2026-11-18", "code": "4444", "ok": "1", "react_on": "2026-11-19", "time": "15:30", "tags": "決算", "rev": "", "diff": ""},
        {"date": "2026-11-18", "code": "5555", "ok": "0", "react_on": "2026-11-19", "time": "15:30", "tags": "業績修正", "rev": "上方", "diff": ""},
        {"date": "2026-11-18", "code": "6666", "ok": "1", "react_on": "2026-11-19", "time": "15:30", "tags": "業績修正", "rev": "不明", "diff": ""},
    ]
    ev = F.events_from_ledger(rows)
    assert [(e["code"], e["kind"]) for e in ev] == [("2222", "U"), ("3333", "D")]   # 登録より前・決算だけ・測れない・不明は入れない


def test_intraday_and_path():
    b5 = [_bar("2026-11-19", 9, 0, 100, 101), _bar("2026-11-19", 9, 55, 102, 103), _bar("2026-11-19", 10, 0, 104, 104),
          _bar("2026-11-19", 11, 25, 105, 105), _bar("2026-11-19", 12, 30, 106, 106), _bar("2026-11-18", 10, 0, 1, 1)]
    assert F.intraday(b5, "2026-11-19") == (100, 104, 106)
    assert F.intraday([], "2026-11-19") == (None, None, None)
    days = _days("2026-11-18", 6)                        # 11/18〜11/25
    m = {d: (100.0 + i, 100.0 + i, 1000.0) for i, d in enumerate(days)}
    del m[days[2]]                                        # 取引の無い日＝前の値
    now = dt.datetime.fromisoformat(f"{days[-1]}T17:00").replace(tzinfo=JST)
    path = F.closes_path(m, days, days[1], now)
    assert path == [101.0, 101.0, 103.0, 104.0, 105.0]
    del m[days[-1]]                                       # 夜中にいちばん新しい日が空＝そこで止める
    assert F.closes_path(m, days, days[1], now) == [101.0, 101.0, 103.0, 104.0]
    early = dt.datetime.fromisoformat(f"{days[-1]}T15:00").replace(tzinfo=JST)
    m[days[-1]] = (110.0, 110.0, 1.0)
    assert len(F.closes_path(m, days, days[1], early)) == 4  # 確定前の日は入れない


def _row(kind, closes, o=(1.0, 1.02, 1.01, 1.03), tc=None, to=(1.0, 1.0, 1.0, 1.0), date="2026-11-18"):
    tc = tc or [1.0] * len(closes)
    def j(xs):
        return ";".join("" if x is None else f"{x:.5f}" for x in xs)
    return {"date": date, "kind": kind, "ok": "1", "o": j(o), "c": j(closes), "to": j(to), "tc": j(tc)}


def test_entries_and_exits():
    closes = [1.0 + 0.01 * k for k in range(31)]          # 毎日 +1%（寄りを 1 とした比）
    r = _row("U", closes)
    assert abs(F.cell_return(r, "E1", "X0") - 0.0) < 1e-9                         # 寄り→その日の引け（c0＝1.00）
    assert abs(F.cell_return(r, "E1", "X5") - (closes[4] - 1)) < 1e-9             # 寄りで入る＝入った日を1日目＝5日目の引け
    assert abs(F.cell_return(r, "E2", "X5") - (closes[5] / closes[0] - 1)) < 1e-9  # 引けで入る＝次の日を1日目
    assert abs(F.cell_return(r, "E3", "X20") - (closes[20] / 1.02 - 1)) < 1e-9    # R+1 の寄り＝k=1 → 1+19
    assert abs(F.cell_return(r, "E5", "X20") - (closes[24] / closes[4] - 1)) < 1e-9
    assert abs(F.cell_return(r, "E7", "X0") - (closes[0] / 1.01 - 1)) < 1e-9      # 10:00 → その日の引け
    assert abs(F.cell_return(r, "E8", "X5") - (closes[4] / 1.03 - 1)) < 1e-9
    # TOPIX を引く
    r2 = _row("U", closes, tc=[1.0 + 0.005 * k for k in range(31)])
    assert abs(F.cell_return(r2, "E1", "X5") - ((closes[4] - 1) - 0.02)) < 1e-9
    # まだ出られない（道が短い）
    assert F.cell_return(_row("U", closes[:5]), "E1", "X20") is None
    # 場中の値段が無い
    assert F.cell_return(_row("U", closes, o=(1.0, 1.02, None, None)), "E7", "X0") is None


def test_pullback():
    up = _row("U", [1.05, 1.04, 1.02, 0.99, 1.00, 1.01, 1.02, 1.03, 1.04, 1.05, 1.06] + [1.06] * 20)
    p = F.entry_point(up, "E6")
    assert p[2] == 3 and abs(p[0] - 0.99) < 1e-9                                 # 初めて寄り以下になった日の引け
    never = _row("U", [1.05] * 31)
    assert F.entry_point(never, "E6") == ("none",) and F.cell_return(never, "E6", "X5") is None
    dn = _row("D", [0.95, 0.97, 1.01] + [1.0] * 28)
    assert F.entry_point(dn, "E6")[2] == 2                                        # 下方修正は寄り以上に戻った日
    assert F.entry_point(_row("U", [1.05, 1.04]), "E6") is None                    # 10日たっていない＝まだ決めない


def test_judge_once():
    days = _days("2026-11-18", 45)
    rows = []
    for i, d in enumerate(days):
        for j in range(7):
            g = 0.01 + 0.002 * ((i + j) % 3)
            rows.append(_row("U", [1.0] + [1.0 + g] * 30, date=d))
    out = F.judge(rows, "2027-03-01")
    v = out["U|E1|X5"]
    assert v["n"] == 315 and v["days"] == 45 and v["status"] == "✅ 買い"
    assert "status" not in out["D|E1|X5"] and out["D|E1|X5"]["n"] == 0
    few = F.judge(rows[:250], "2027-03-01")["U|E1|X5"]
    assert "status" not in few                                                    # 300件に届かない＝判定しない
    flat = [_row("U", [1.0] + [1.0 + (0.01 if i % 2 else -0.01)] * 30, date=d) for i, d in enumerate(days) for _ in range(7)]
    assert F.judge(flat, "2027-03-01")["U|E1|X5"]["status"] == "✕ 見えない"


def test_update_row_keeps_no_prices():
    days = _days("2026-11-18", 8)
    R = days[1]
    daily = {d: (1000.0 + i, 1000.0 + i, 2e6) for i, d in enumerate(days)}
    tx = {d: (400.0, 400.0 + i, 1.0) for i, d in enumerate(days)}
    b5 = [_bar(R, 9, 0, 1001, 1002), _bar(R, 10, 0, 1010, 1011), _bar(R, 12, 30, 1020, 1021)]
    t5 = [_bar(R, 9, 0, 400, 400), _bar(R, 10, 0, 401, 401), _bar(R, 12, 30, 402, 402)]
    row = {"date": days[0], "code": "1111", "kind": "U", "time": "15:30", "react_on": R}
    now = dt.datetime.fromisoformat(f"{days[-1]}T17:00").replace(tzinfo=JST)
    F.update_row(row, days, daily, tx, b5, t5, now)
    assert row["ok"] == "1" and row["intra"] == "1" and row["tv_prev"] == "20.00"
    assert row["o"].split(";")[0] == "1.00000" and "1001" not in row["o"] and "1010" not in row["c"]   # 比だけ
    assert abs(float(row["o"].split(";")[2]) - 1010 / 1001) < 1e-5
    thin = dict(row)
    daily2 = {d: (v[0], v[1], 10.0) for d, v in daily.items()}                     # 売買代金が1億円に届かない
    F.update_row(thin, days, daily2, tx, b5, t5, now)
    assert thin["ok"] == "0"


def test_wiring():
    wf = open(".github/workflows/tdnet-reaction.yml", encoding="utf-8").read()
    assert "python tests/test_disclosure_timing_forward.py && python disclosure_timing_forward.py" in wf
    assert "disclosure-timing-forward.csv disclosure-timing-forward.json" in wf
    import check_site_consistency as C
    for f in ("disclosure-timing-forward.csv", "disclosure-timing-forward.json"):
        assert f in C.SYNC_FORBIDDEN, f
    pre = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## J52 " in pre and "disclosure_timing_forward.py" in pre and "2026-11-18" in pre
    assert len(F.CELLS) * len(F.KINDS) == 34
    assert "disclosure_timing_forward.py" in open("RESEARCH_LABS.md", encoding="utf-8").read()


def test_z_need_is_the_stricter_reading():
    """2026-11-21 オーナー決定：登録の文「0.05/34（両側・約3.4）」の食い違いは、きびしい方の「約3.4」＝z 3.376"""
    assert abs(F.Z_NEED - 3.376) < 0.001
    days = _days("2026-11-18", 45)
    rows = [_row("U", [1.0] + [1.0 + 0.01 + 0.002 * ((i + j) % 3)] * 30, date=d) for i, d in enumerate(days) for j in range(7)]
    assert F.judge(rows, "2027-03-01")["U|E1|X5"]["z_need"] == round(F.Z_NEED, 3)
    sec = open("PILLAR_PREREG.md", encoding="utf-8").read().split("## J52 ", 1)[1].split("\n## ", 1)[0]
    assert "z 3.376" in sec and "2026-11-21・オーナー決定" in sec


if __name__ == "__main__":
    n = 0
    for k, f in list(globals().items()):
        if k.startswith("test_") and callable(f):
            f()
            n += 1
    print(f"✅ {n} 件 OK")
