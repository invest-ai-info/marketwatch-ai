"""recount_compare（別の書き方での数え直しの突き合わせ）のテスト。pytest 不要・pytest でも動く。

  PYTHONUTF8=1 python tests/test_recount_compare.py
"""
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import recheck_status as S  # noqa: E402
import recount_compare as R  # noqa: E402


def _rows(n):
    out = []
    for i in range(n):
        d = f"2026-01-{5 + i:02d}"
        out.append({"study": "S", "market": "fx", "symbol": "USDJPY", "side": 1,
                    "entry_time": f"{d}T10:00Z", "exit_time": f"{d}T11:00Z",
                    "entry_price": 150.0 + i * 0.37, "exit_price": 150.21 + i * 0.41,
                    "unit": "pips", "gross": 21.5 + i, "cost": 0.5, "net": 21.0 + i, "exit_reason": "tp"})
    return out


def _extra():
    return dict(_rows(1)[0], entry_time="2026-02-02T10:00Z", exit_time="2026-02-02T11:00Z")


def _event(symbol, date, flag, outcome):
    return {"study": "E", "market": "jp", "symbol": symbol, "date": date, "flag": flag,
            "outcome": outcome, "unit": "pct"}


def _root():
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "recheck"))
    return d


def _walk(o):
    if isinstance(o, dict):
        for v in o.values():
            yield from _walk(v)
    elif isinstance(o, (list, tuple)):
        for v in o:
            yield from _walk(v)
    else:
        yield o


def _has_value(o, values):
    return any(isinstance(v, float) and any(abs(v - x) < 1e-9 for x in values) for v in _walk(o))


def _raises(exc, fn, *a, **kw):
    try:
        fn(*a, **kw)
    except exc:
        return
    raise AssertionError(f"{exc.__name__} が出なかった")


def test_same_lists_agree():
    c = R.compare(_rows(5), _rows(5))
    assert c.matched == 5 and not c.mismatches


def test_cp_off_by_one_is_caught():                # CP：突き合わせの番号の誤り
    o = _rows(5)
    r = [dict(x, exit_price=o[(i + 1) % 5]["exit_price"]) for i, x in enumerate(o)]
    assert sum(m.what == "differs" for m in R.compare(o, r).mismatches) == 5


def test_tolerances():
    o = _rows(1)
    r = [dict(o[0], net=o[0]["net"] + 0.09, exit_price=o[0]["exit_price"] * (1 + 5e-7))]
    assert R.compare(o, r).matched == 1
    r = [dict(o[0], net=o[0]["net"] + 0.2)]
    assert R.compare(o, r).matched == 0
    p = [dict(o[0], unit="pct", net=1.0)]
    assert R.compare(p, [dict(p[0], net=1.009)]).matched == 1
    assert R.compare(p, [dict(p[0], net=1.02)]).matched == 0


def test_exit_reason_and_time_differences():
    o = _rows(1)
    assert R.compare(o, [dict(o[0], exit_reason="sl")]).mismatches[0].fields == ["exit_reason"]
    assert R.compare(o, [dict(o[0], exit_time="2026-01-05T11:05Z")]).mismatches[0].fields == ["exit_time"]


def test_missing_and_extra_rows():
    whats = sorted(m.what for m in R.compare(_rows(3), _rows(3)[1:] + [_extra()]).mismatches)
    assert whats == ["only_original", "only_recount"]


def test_time_zones_are_aligned():
    o = _rows(1)
    r = [dict(o[0], entry_time="2026-01-05T19:00+09:00", exit_time="2026-01-05T20:00+09:00")]
    assert R.compare(o, r).matched == 1


def test_data_version_needs_different_inputs():
    o, r = _rows(10), _rows(10)   # 外せるのは元の件数の10%まで＝10件中1件
    r[1] = dict(r[1], net=r[1]["net"] + 5)
    key = list(R.key_of(o[1], "trade"))
    same = [{"key": key, "category": "data_version", "note": "", "evidence": {"orig_input": 1.0, "recount_input": 1.0}}]
    _raises(R.RecountError, R.finalize, "S", o, r, "trade", same, [], [], _root())
    diff = [{"key": key, "category": "data_version", "note": "取り直した足",
             "evidence": {"orig_input": 150.111, "recount_input": 150.113}}]
    root = _root()
    rec = R.finalize("S", o, r, "trade", diff, [], [], root)
    assert rec["excluded_data_version"] == 1 and rec["agreement"] == 1.0 and S.recheck_ok("S", root)


def test_refuses_unexplained_and_opened_original():
    o, r = _rows(2), _rows(2)
    r[0] = dict(r[0], net=99.0)
    _raises(R.RecountError, R.finalize, "S", o, r, "trade", [], [], [], _root())
    fixed_later = [{"key": list(R.key_of(o[0], "trade")), "category": "original_error", "note": "直した"}]
    _raises(R.RecountError, R.finalize, "S", o, r, "trade", fixed_later, [], [], _root())   # 説明しても直していなければ通らない
    _raises(R.RecountError, R.finalize, "S", o, o, "trade", [], ["research\\oikawa\\oj5_lab.py"],
            ["research/oikawa/oj5_lab.py"], _root())


def test_breakdown_counts_past_explanations():
    o = _rows(2)
    ex = [{"key": list(R.key_of(o[0], "trade")), "category": "recount_error", "note": "数え直し側の境目"},
          {"key": list(R.key_of(o[1], "trade")), "category": "ambiguous_rule", "note": "良く見えない側の読み"}]
    rec = R.finalize("S", o, o, "trade", ex, ["recheck/S/recount.py"], [], _root())
    assert rec["breakdown"] == {"ambiguous_rule": 1, "recount_error": 1}


def test_record_has_no_prices_and_is_append_only():
    root, o = _root(), _rows(3)
    R.finalize("S", o, o, "trade", [], [], [], root)
    R.finalize("S", o, o, "trade", [], [], [], root)
    rec = S.load_store("records", root)["S"]
    assert rec["agreement"] == 1.0 and "previous" in rec
    assert not _has_value(rec, {x["entry_price"] for x in o} | {x["exit_price"] for x in o})


def test_zero_rows_never_pass():
    _raises(R.RecountError, R.finalize, "S", [], [], "trade", [], [], [], _root())


def test_events_matched_by_symbol_date_flag():
    e = [_event("7203.T", "2026-01-05", "C", 1.2)]
    assert R.compare(e, e, kind="event").matched == 1
    assert R.compare(e, [_event("7203.T", "2026-01-05", "B", 1.2)], kind="event").matched == 0
    assert R.compare(e, [_event("7203.T", "2026-01-05", "C", 1.5)], kind="event").mismatches[0].fields == ["outcome"]


def test_cli_writes_only_with_flag():
    import csv
    d = _root()
    o = _rows(3)
    for name in ("o.csv", "r.csv"):
        with open(os.path.join(d, name), "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(o[0]))
            w.writeheader()
            w.writerows(o)
    a = [os.path.join(d, "o.csv"), os.path.join(d, "r.csv"), "--study", "C", "--root", d]
    assert R.main(a) == 0 and not S.load_store("records", d)
    assert R.main(a + ["--write"]) == 0 and S.recheck_ok("C", d)


def test_too_many_data_version_rows_are_refused():
    o, r = _rows(20), _rows(20)
    ex = []
    for i in range(1, 20):
        r[i] = dict(r[i], net=r[i]["net"] + 5)
        ex.append({"key": list(R.key_of(o[i], "trade")), "category": "data_version", "note": "",
                   "evidence": {"orig_input": 1.0, "recount_input": 1.1}})
    _raises(R.RecountError, R.finalize, "S", o, r, "trade", ex, [], [], _root())


if __name__ == "__main__":
    n = 0
    for k, fn in list(globals().items()):
        if k.startswith("test_") and callable(fn):
            fn()
            n += 1
    print(f"ok {n}")
