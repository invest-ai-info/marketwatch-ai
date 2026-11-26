"""result_audit（ありえない数字の点検）のテスト。pytest 不要・pytest でも動く。

  PYTHONUTF8=1 python tests/test_result_audit.py

過去に結果を見たあとで見つかった測り間違いの型を、作った見本のデータで1つずつ当てる（設計書 5.2）。
"""
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import recheck_status as S  # noqa: E402
import result_audit as A  # noqa: E402


# ---------- 見本を作る小さな助け ----------
def _trade(**kw):
    t = {
        "study": "T", "market": "fx", "symbol": "USDJPY", "side": 1,
        "signal_time": "2026-01-05T09:55Z", "entry_time": "2026-01-05T10:00Z", "exit_time": "2026-01-05T11:00Z",
        "entry_price": 150.0, "exit_price": 150.2, "stop_price": 149.8,
        "unit": "pips", "gross": 20.5, "cost": 0.5, "net": 20.0, "r": 1.0,
        "exit_reason": "tp", "period": "A",
    }
    t.update(kw)
    return t


def _event(symbol, date, flag="C", outcome=1.0, market="jp"):
    return {"study": "E", "market": market, "symbol": symbol, "date": date, "flag": flag,
            "outcome": outcome, "unit": "pct", "period": "A"}


def _find(fs, name):
    for f in fs:
        if f.check == name or f.check.startswith(name + "-"):
            return f
    return None


def _root():
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "recheck"))
    return d


def _walk(o):
    if isinstance(o, dict):
        for k, v in o.items():
            yield ("key", k)
            yield from _walk(v)
    elif isinstance(o, (list, tuple)):
        for v in o:
            yield from _walk(v)
    else:
        yield ("value", o)


def _has_key(o, names):
    return any(t == "key" and str(k).lower() in names for t, k in _walk(o))


def _has_value(o, values):
    vals = [v for t, v in _walk(o) if t == "value" and isinstance(v, float)]
    return any(abs(v - x) < 1e-9 for v in vals for x in values)


def _raises(exc, fn, *a, **kw):
    try:
        fn(*a, **kw)
    except exc:
        return
    raise AssertionError(f"{exc.__name__} が出なかった")


# ---------- 形 ----------
def test_naive_time_is_rejected():
    assert any("時間帯" in m for m in A.check_rows([_trade(entry_time="2026-11-26 09:00")], "trade"))


def test_bad_market_side_unit_are_rejected():
    msgs = A.check_rows([_trade(market="forex", side=2, unit="yen")], "trade")
    assert len(msgs) == 3


def test_required_fields_missing():
    t = _trade()
    t.pop("exit_time")
    assert any("exit_time" in m for m in A.check_rows([t], "trade"))


def test_to_utc():
    assert A.to_utc("2026-11-26T09:00+09:00").isoformat() == "2026-11-26T00:00:00+00:00"
    _raises(ValueError, A.to_utc, "2026-11-26 09:00")


def test_bad_format_stops_audit_with_one_error():
    fs = A.audit([_trade(entry_time="2026-11-26 09:00")], A.Context())
    assert len(fs) == 1 and fs[0].check == "FORMAT" and fs[0].level == "error"


# ---------- A1 時刻の順 ----------
def test_a1_exit_before_entry():
    f = _find(A.audit([_trade(entry_time="2026-01-05T10:00Z", exit_time="2026-01-05T09:00Z")], A.Context()), "A1")
    assert f.level == "error" and f.examples == [0]


def test_a1_entry_before_signal():
    assert _find(A.audit([_trade(signal_time="2026-01-05T10:05Z", entry_time="2026-01-05T10:00Z")], A.Context()), "A1")


def test_a1_clean():
    assert not _find(A.audit([_trade()], A.Context()), "A1")


# ---------- A8 重複・重なり ----------
def test_a8_duplicate_and_overlap():
    t = _trade()
    assert _find(A.audit([t, dict(t)], A.Context()), "A8").level == "error"
    a = _trade(entry_time="2026-01-05T10:00Z", exit_time="2026-01-05T12:00Z")
    b = _trade(entry_time="2026-01-05T11:00Z", exit_time="2026-01-05T13:00Z", symbol="EURJPY")
    assert _find(A.audit([a, b], A.Context(one_at_a_time=True)), "A8")
    assert not _find(A.audit([a, b], A.Context()), "A8")


# ---------- A9 休みの日 ----------
def test_a9_saturday_holiday_friday():
    sat = _trade(entry_time="2026-01-10T03:00Z", exit_time="2026-01-10T04:00Z")
    assert _find(A.audit([sat], A.Context()), "A9")
    fri = _trade(entry_time="2026-01-09T01:00Z", exit_time="2026-01-09T02:00Z")   # 東京の金曜 10時
    assert _find(A.audit([fri], A.Context(no_friday=True)), "A9")
    assert not _find(A.audit([fri], A.Context()), "A9")
    hol = _trade(market="jp", symbol="7203.T", unit="pct",
                 entry_time="2026-01-05T00:00Z", exit_time="2026-01-05T06:00Z")
    assert _find(A.audit([hol], A.Context(holidays={"jp": ["2026-01-05"]})), "A9")


def test_a9_crypto_trades_on_saturday():
    sat = _trade(market="crypto", symbol="BTC-USD", unit="pct",
                 entry_time="2026-01-10T03:00Z", exit_time="2026-01-10T04:00Z")
    assert not _find(A.audit([sat], A.Context()), "A9")


# ---------- A10 データの抜け ----------
def test_oj5_c_missing_seven_percent_is_error():
    assert _find(A.audit([_trade()], A.Context(missing_ratio=0.07)), "A10").level == "error"
    assert not _find(A.audit([_trade()], A.Context(missing_ratio=0.02)), "A10")


# ---------- 目印の形 ----------
def test_event_duplicate_and_weekend():
    e = _event("7203.T", "2026-01-05")
    assert _find(A.audit([e, dict(e)], A.Context(kind="event")), "A8")
    assert _find(A.audit([_event("7203.T", "2026-01-10")], A.Context(kind="event")), "A9")


# ---------- 要約・漏らさない ----------
def test_empty_list_is_clean():
    s = A.summarize([], A.Context(), A.audit([], A.Context()))
    assert s["n_rows"] == 0 and s["errors"] == 0


def test_missing_optional_fields_are_skipped():
    t = _trade()
    t.pop("signal_time")
    t.pop("stop_price")
    s = A.summarize([t], A.Context(), A.audit([t], A.Context()))
    assert "A1-signal" in s["checks_skipped"]
    assert "A10" in s["checks_skipped"]       # 抜けの割合を渡していない


def test_summary_never_shows_pnl():
    rows = [_trade(net=v, gross=v + 0.5, cost=0.5, entry_time=f"2026-01-0{i + 5}T10:00Z",
                   exit_time=f"2026-01-0{i + 5}T11:00Z", signal_time=f"2026-01-0{i + 5}T09:55Z")
            for i, v in enumerate((3.0, -1.0, 7.25))]
    s = A.summarize(rows, A.Context(), A.audit(rows, A.Context()))
    assert not _has_key(s, {"sum", "mean", "avg", "win", "win_rate", "pf", "total", "pnl"})
    assert not _has_value(s, {9.25, 9.25 / 3, 2 / 3})


def test_fingerprint_changes_with_rows():
    a = A.summarize([_trade()], A.Context(), [])
    b = A.summarize([_trade(net=19.0)], A.Context(), [])
    assert len(a["fingerprint"]) == 64 and a["fingerprint"] != b["fingerprint"]


# ---------- 関門 ----------
def test_gate_records_then_refuses_errors():
    r = _root()
    _raises(A.AuditError, A.gate, [_trade(entry_time="2026-01-05T10:00Z", exit_time="2026-01-05T09:00Z")],
            A.Context(), "T", r)
    assert S.load_store("audits", r)["T"]["errors"] == 1


def test_gate_passes_clean_list():
    r = _root()
    s = A.gate([_trade()], A.Context(missing_ratio=0.0), "T2", r)
    assert s["errors"] == 0 and S.load_store("audits", r)["T2"]["fingerprint"] == s["fingerprint"]


def test_cli_exit_codes():
    import csv
    d = _root()
    p = os.path.join(d, "rows.csv")
    rows = [_trade(), _trade(entry_time="2026-01-06T10:00Z", exit_time="2026-01-06T09:00Z",
                             signal_time="2026-01-06T09:55Z")]
    with open(p, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    assert A.main([p, "--study", "CLI", "--root", d]) == 1
    assert A.main([p, "--study", "CLI", "--root", d, "--dry"]) == 1
    with open(p, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerow(rows[0])
    assert A.main([p, "--study", "CLI", "--root", d]) == 0


# ---------- 作業3：A2〜A7・G1 と過去の型の見本 ----------
from datetime import date, timedelta  # noqa: E402


def _weekdays(y, m_from=1, m_to=12):
    d, out = date(y, m_from, 1), []
    end = date(y + 1, 1, 1) if m_to == 12 else date(y, m_to + 1, 1)
    while d < end:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def _at(d, hour, minutes=0):
    return f"{d.isoformat()}T{hour:02d}:{minutes:02d}Z"


def _per_year(counts, first_months=12):
    rows, years = [], sorted(counts)
    for y in years:
        days = _weekdays(y, 13 - first_months, 12) if y == years[0] else _weekdays(y)
        for i in range(counts[y]):
            d, h = days[i % len(days)], 1 + (i // len(days)) % 20
            rows.append(_trade(signal_time=_at(d, h), entry_time=_at(d, h, 5), exit_time=_at(d, h, 30)))
    return rows


def _jp(symbol, price, i):
    d = _weekdays(2026)[i]
    return _trade(market="jp", symbol=symbol, unit="pct", entry_price=price, exit_price=price * 1.01,
                  stop_price=None, signal_time=None, gross=1.0, cost=0.1, net=0.9, r=None,
                  entry_time=_at(d, 0, 5), exit_time=_at(d, 5))


def _rollover_fixture():
    rows, days = [], _weekdays(2026, 1, 3)
    for i in range(40):
        d = days[i]
        if i % 5 == 0:   # 8件：NY17時（冬＝UTC 22時）をまたぐ
            rows.append(_trade(signal_time=_at(d, 20), entry_time=_at(d, 20, 5), exit_time=_at(d, 23),
                               gross=50.5, cost=0.5, net=50.0, r=2.5))
        else:
            rows.append(_trade(signal_time=_at(d, 10), entry_time=_at(d, 10, 5), exit_time=_at(d, 11),
                               gross=-0.5, cost=0.5, net=-1.0, r=-0.05))
    return rows


def _bucket_fixture():
    rows, days = [], _weekdays(2026, 1, 3)
    for i in range(40):
        d, sym, side = days[i], ("USDJPY", "EURJPY")[i % 2], (1, -1)[(i // 2) % 2]
        if i % 5 == 0:   # 8件：東京の朝（UTC 0〜3時）だけが利益を持つ
            rows.append(_trade(symbol=sym, side=side, signal_time=_at(d, 1), entry_time=_at(d, 1, 5),
                               exit_time=_at(d, 2), gross=50.5, cost=0.5, net=50.0, r=2.5))
        else:
            h = (8, 12, 16)[i % 3]
            rows.append(_trade(symbol=sym, side=side, signal_time=_at(d, h), entry_time=_at(d, h, 5),
                               exit_time=_at(d, h + 1), gross=-0.5, cost=0.5, net=-1.0, r=-0.05))
    return rows


def _single_symbol_fixture():
    rows, days = [], _weekdays(2026, 1, 3)
    for i in range(40):
        d, h = days[i], (1, 5, 9, 13, 17, 21)[i % 6]
        net = 3.0 if i % 2 else -1.0
        rows.append(_trade(signal_time=_at(d, h), entry_time=_at(d, h, 5), exit_time=_at(d, h, 50),
                           gross=net + 0.5, cost=0.5, net=net, r=net / 20))
    return rows


def test_rv_one_sided_stop_check():                # RV：損切りの確かめが片側だけ＝1回で -694R
    assert _find(A.audit([_trade(r=-694.0, stop_price=150.0)], A.Context()), "A2").level == "error"


def test_a2_normal_loss_is_fine():
    assert not _find(A.audit([_trade(r=-1.1)], A.Context()), "A2")


def test_weekend_gap_allows_double():
    t = _trade(signal_time="2026-01-09T19:55Z", entry_time="2026-01-09T20:00Z", exit_time="2026-01-12T01:00Z", r=-5.0)
    assert not _find(A.audit([t], A.Context()), "A2")
    t2 = dict(t, entry_time="2026-01-12T01:00Z", exit_time="2026-01-12T03:00Z", signal_time="2026-01-12T00:55Z")
    assert _find(A.audit([t2], A.Context()), "A2")


def test_rollover_bar_stop_allows_wider_loss():   # 較正：金曜の引けの切り替わりの足の損切り（CP-F の6件）
    fri = _trade(signal_time="2017-12-01T20:55Z", entry_time="2017-12-01T21:00Z", exit_time="2017-12-01T22:00Z", r=-7.15)
    assert not _find(A.audit([fri], A.Context()), "A2")
    mon = dict(fri, signal_time="2017-12-04T09:55Z", entry_time="2017-12-04T10:00Z", exit_time="2017-12-04T11:00Z")
    assert _find(A.audit([mon], A.Context()), "A2")


def test_brexit_day_move_is_real():               # 較正：2016-06-24 のポンド円 -6.2%（本物の大きな動き）
    t = _trade(symbol="GBPJPY", side=1, signal_time="2016-06-24T09:55Z", entry_time="2016-06-24T10:00Z",
               exit_time="2016-06-27T11:27Z", entry_price=143.196, exit_price=134.298, r=-2.0,
               gross=-889.3, cost=0.5, net=-889.8)
    assert not _find(A.audit([t], A.Context()), "A3")


def test_r1_fake_yahoo_jump():                     # R1：Yahoo の偽の値で +947.9%
    t = _trade(market="jp", symbol="9999.T", unit="pct", entry_price=100.0, exit_price=1047.9,
               signal_time=None, stop_price=None, r=None, gross=947.9, cost=0.1, net=947.8,
               entry_time="2026-01-05T00:00Z", exit_time="2026-01-05T06:00Z")
    assert _find(A.audit([t], A.Context()), "A3").level == "error"


def test_fx_pips_without_prices():
    t = _trade(gross=1500.5, cost=0.5, net=1500.0)
    t.pop("entry_price")
    t.pop("exit_price")
    assert _find(A.audit([t], A.Context()), "A3")


def test_ten_times_price_is_caught():              # R1：1306.T の10倍ずれ
    rows = [_jp("1306.T", 2000.0 + i, i) for i in range(9)] + [_jp("1306.T", 20000.0, 9)]
    assert _find(A.audit(rows, A.Context()), "A3").examples == [9]


def test_st_cost_negative_and_not_adding_up():    # ST ラウンド1：費用の計算の誤り
    assert _find(A.audit([_trade(cost=-0.3, gross=1.0, net=1.3)], A.Context()), "A4")
    assert _find(A.audit([_trade(cost=0.3, gross=1.0, net=2.0)], A.Context()), "A4")
    assert _find(A.audit([_trade(cost=0.1, gross=1.0, net=0.9)], A.Context(min_cost=0.3)), "A4")
    assert not _find(A.audit([_trade()], A.Context()), "A4")


def test_st_rollover_concentration_warns_by_name_only():   # ST ラウンド1：NY17時の切り替わりの偽の利益
    f = _find(A.audit(_rollover_fixture(), A.Context()), "A5")
    assert f and f.level == "warning" and "NY17時" in f.note
    assert not any(c.isdigit() for c in f.note.replace("NY17時", ""))


def test_m1_year_jump_warns():                     # M1：MT5 の欠陥データで回数が3〜4倍
    assert _find(A.audit(_per_year({2020: 100, 2021: 100, 2022: 380}), A.Context()), "A6").level == "warning"


def test_partial_years_are_scaled():
    assert not _find(A.audit(_per_year({2020: 25, 2021: 100, 2022: 100}, first_months=3), A.Context()), "A6")


def test_a7_names_bucket_and_skips_single_symbol():
    f = _find(A.audit(_bucket_fixture(), A.Context()), "A7")
    assert f and f.level == "warning" and "東京の朝" in f.note
    assert not any(c.isdigit() for c in f.note)
    assert not _find(A.audit(_single_symbol_fixture(), A.Context()), "A7")


def test_g1_too_good_is_flag_not_error():
    days = _weekdays(2026, 1, 3)
    rows = [_trade(signal_time=_at(days[i], 10), entry_time=_at(days[i], 10, 5), exit_time=_at(days[i], 11),
                   gross=2.5, cost=0.5, net=2.0, r=2.0) for i in range(40)]
    f = _find(A.audit(rows, A.Context()), "G1")
    assert f and f.level == "flag" and not any(c.isdigit() for c in f.note)
    assert "G1" in A.summarize(rows, A.Context(), A.audit(rows, A.Context()))["flags"]


def test_split_in_events_is_caught_and_events_skip_trade_checks():   # Yahoo の株式分割の直しもれ
    ev = [_event("7203.T", "2026-01-05", outcome=-80.0)]
    fs = A.audit(ev, A.Context(kind="event"))
    assert _find(fs, "A3") and not _find(fs, "A2") and not _find(fs, "A5")


def test_warning_needs_a_reason_to_pass_the_gate():
    rows, r = _per_year({2020: 100, 2021: 100, 2022: 380}), _root()
    _raises(A.AuditError, A.gate, rows, A.Context(missing_ratio=0.0), "W", r)
    s = A.gate(rows, A.Context(missing_ratio=0.0), "W", r, waivers={"A6": "2022年から足が細かくなった（登録に書いた）"})
    assert s["warnings"] == 1 and S.load_store("audits", r)["W"]["waivers"]["A6"]


# ---------- 全体の読み直しで見つかった所（最後の確かめ）----------
def test_overnight_weekday_trade_keeps_normal_limit():   # ふつうの夜をまたぐだけでは損の上限を広げない
    t = _trade(signal_time="2026-01-06T19:55Z", entry_time="2026-01-06T20:00Z", exit_time="2026-01-07T02:00Z", r=-8.0)
    assert _find(A.audit([t], A.Context()), "A2")


def test_nan_and_inf_are_rejected():
    assert any("数でない" in m or "有限" in m for m in A.check_rows([_trade(net=float("nan"))], "trade"))
    assert any("数でない" in m or "有限" in m for m in A.check_rows([_trade(r=float("inf"))], "trade"))


def _jp_hold(e, x, d0, d1):
    return _trade(market="jp", symbol="7777.T", unit="pct", entry_price=e, exit_price=x, signal_time=None,
                  stop_price=None, r=None, gross=None, cost=None, net=round(100 * (x / e - 1), 4),
                  entry_time=f"{d0}T00:05Z", exit_time=f"{d1}T06:00Z")


def test_meiko_split_shape_is_caught():          # 1→2 の分割の直しもれ（-47.8%）
    assert _find(A.audit([_jp_hold(2000.0, 1044.0, "2026-01-05", "2026-01-06")], A.Context()), "A3")
    assert _find(A.audit([_jp_hold(2000.0, 1010.0, "2026-01-05", "2026-01-09")], A.Context()), "A3")
    assert not _find(A.audit([_jp_hold(1000.0, 2000.0, "2026-01-05", "2026-03-30")], A.Context()), "A3")
    assert _find(A.audit([_event("7777.T", "2026-01-05", outcome=-47.8)], A.Context(kind="event")), "A3")


def test_gate_marks_passed_only_when_clean():
    r = _root()
    assert A.gate([_trade()], A.Context(), "P1", r)["passed"] is True
    _raises(A.AuditError, A.gate, _per_year({2020: 100, 2021: 100, 2022: 380}), A.Context(), "P2", r)
    rec = S.load_store("audits", r)["P2"]
    assert rec["errors"] == 0 and rec["passed"] is False


if __name__ == "__main__":
    n = 0
    for k, fn in list(globals().items()):
        if k.startswith("test_") and callable(fn):
            fn()
            n += 1
    print(f"ok {n}")
