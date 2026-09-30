# -*- coding: utf-8 -*-
"""自動売買（AT1〜AT3）の道具のテスト：build_signals_recent.py・ea_bridge.py・ea_ledger.py。2026-09-30 新設。

データはすべて作り物（ネットワークに出ない）。確かめること＝①事前登録と定数の一致 ②直近の合図の写し（4時間足・7日・向き）
③EA へ渡すファイル（銘柄名の対応・発表の時刻を UTC に・休場や低い重要度は除く・メールで届いた合図だけ・UTF-16・書きかけを残さない）
④EA の記録の数え方（2本に分けた注文をまとめる・費用込みの R・登録日より前は数えない・30回ごとの区切り・300回でストップ・1000回で判定・判定は変えない）
⑤検証済みリスト・昇格リストに R の単位で載る ⑥見張り番と5分足の報告 ⑦ワークフローと SYNC禁忌。

実行:  python tests/test_ea_tools.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import build_signals_recent as B  # noqa: E402
import ea_bridge as E  # noqa: E402
import ea_ledger as L  # noqa: E402
import promotion_list as P  # noqa: E402
import verified_list as V  # noqa: E402

UTC = dt.timezone.utc
JST = dt.timezone(dt.timedelta(hours=9))
NOW = dt.datetime(2026, 10, 1, 6, 0, tzinfo=UTC)


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    i = text.find("\n## AT ")
    sec = text[i:text.find("\n## ", i + 1)]
    for s in ("**60分前〜30分後**", "**−3%**", "0.25 を超える", "**90分より後**", "ATR×0.5", "`research/ea/`",
              "`signals-recent.json`", "`auto-forward.json`", "`ea_bridge.py`", "`ea_ledger.py`", "2026-10-01 以降",
              "**300回以上で幅がまるごと0より下＝ストップ**", "**1000回で判定**", "30回ごと", "**デモ口座だけ**",
              "G3 に当たる", "日本時間 15:00〜17:59", "**日本時間 18:00**", "金曜 15:00"):
        assert s in sec, s
    assert (L.FWD_START, L.STEP, L.STOP_MIN, L.GOAL) == ("2026-10-01", 30, 300, 1000)
    assert (B.KEEP_DAYS, B.TF) == (7, "4h") and E.IMPACTS == ("high", "critical")
    assert len(J_sha()) == 64


def J_sha():
    import screen_judge as J
    return J.section_sha256(head=L.SECTION)


def _sig(sid, fired, tf="4h", direction="ロング（買い）", email=True, watch="w1", promoted=None, ticker="GBPJPY=X"):
    return {"id": sid, "fired_at": fired, "timeframe": tf, "ticker": ticker, "direction": direction, "primary_signal": "x",
            "entry": 200.0, "stop_loss": 199.0, "take_profit_1": 201.3, "take_profit_2": 202.0, "atr": 0.67,
            "email_sent": email, "watch_hit": watch if email else None, "promoted_hit": promoted, "outcome": None,
            "ai_narrative": "長い文"}


def test_signals_recent():
    assert (B.direction("ロング（買い）"), B.direction("ショート（売り）"), B.direction(None)) == (1, -1, None)
    sigs = [_sig("a", "2026-09-30T14:47:00+09:00"), _sig("b", "2026-09-20T14:47:00+09:00"),
            _sig("c", "2026-09-30T15:00:00+09:00", tf="1h"), _sig("d", "2026-09-30T13:00:00+09:00", direction=None),
            _sig("e", "2026-09-29T09:00:00+09:00", direction="ショート（売り）")]
    rows = B.build(sigs, NOW)
    assert [r["id"] for r in rows] == ["e", "a"] and rows[0]["dir"] == -1 and "ai_narrative" not in rows[0]


def test_symbol_map_and_events():
    assert E.map_symbol("GBPJPY=X") == "GBPJPY" and E.map_symbol("GBPJPY=X", ".m") == "GBPJPY.m"
    assert E.map_symbol("NKD=F") is None and E.map_symbol("NKD=F", extra={"NKD=F": "JP225"}) == "JP225"
    evs = [{"name": "米雇用統計, NFP", "datetime": "2026-10-02T21:30+09:00", "impact": "critical", "affected_assets": ["all"], "country": "US"},
           {"name": "英 CPI", "datetime": "2026-10-01T15:00+09:00", "impact": "high", "affected_assets": ["GBPJPY=X", "^FTSE"], "country": "UK"},
           {"name": "休場", "datetime": "2026-10-02T09:00+09:00", "impact": "high", "affected_assets": ["NKD=F"], "country": "JP", "category": "market_holiday"},
           {"name": "小さい", "datetime": "2026-10-02T09:00+09:00", "impact": "medium", "affected_assets": ["all"], "country": "JP"},
           {"name": "遠い", "datetime": "2026-12-02T09:00+09:00", "impact": "high", "affected_assets": ["all"], "country": "JP"},
           {"name": "過ぎた", "datetime": "2026-10-01T10:00+09:00", "impact": "high", "affected_assets": ["all"], "country": "JP"}]
    rows, unmapped = E.events_rows(evs, NOW)
    assert [r[1] for r in rows] == ["英 CPI", "米雇用統計・ NFP"]
    uk, us = rows
    assert uk[0] == int(dt.datetime(2026, 10, 1, 6, 0, tzinfo=UTC).timestamp())      # 日本時間15:00＝UTC 06:00
    assert (uk[3], uk[4]) == ("GBP", "GBPJPY") and unmapped == {"^FTSE"}
    assert (us[3], us[4]) == ("USD", "*")


def test_orders_and_files():
    recent = {"signals": [dict(_sig("a", "2026-10-01T14:00:00+09:00"), dir=1),
                          dict(_sig("b", "2026-10-01T13:00:00+09:00", promoted="p1", watch=None), dir=-1),
                          dict(_sig("c", "2026-10-01T12:00:00+09:00", email=False), dir=1),
                          dict(_sig("d", "2026-09-29T12:00:00+09:00"), dir=1),
                          dict(_sig("e", "2026-10-01T14:00:00+09:00", ticker="NKD=F"), dir=1),
                          dict(_sig("f", "2026-10-01T14:00:00+09:00", tf="1h"), dir=1)]}
    rows, unmapped = E.orders_rows(recent, NOW)
    assert [(r[0], r[3], r[-1]) for r in rows] == [("b", -1, "promoted"), ("a", 1, "watch")] and unmapped == {"NKD=F"}
    assert float(rows[1][4]) == 200.0 and rows[1][2] == "GBPJPY"
    d = tempfile.mkdtemp()
    ev, orders, un = E.run(d, [], recent, NOW)
    assert sorted(os.listdir(d)) == ["mw_bridge_status.csv", "mw_events.csv", "mw_orders.csv"]   # 書きかけ（.tmp）を残さない
    raw = open(os.path.join(d, "mw_orders.csv"), "rb").read()
    assert raw[:2] == b"\xff\xfe" and raw.decode("utf-16").splitlines()[0] == ",".join(E.OR_HEAD)
    got = L.read_csv(os.path.join(d, "mw_orders.csv"))                              # 同じ読み方で読み戻せる
    assert [g["id"] for g in got] == ["b", "a"] and got[0]["kind"] == "promoted"


def _write_log(path, head, rows, utf16=True):
    text = "\r\n".join(",".join(str(c) for c in r) for r in [head] + rows) + "\r\n"
    open(path, "wb").write(text.encode("utf-16" if utf16 else "utf-8"))


SWING_HEAD = ["plan", "legs", "kind", "status", "ticket", "signal_utc", "seen_utc", "open_utc", "close_utc", "symbol", "dir",
              "signal_price", "fill", "spread", "lots", "risk", "balance", "sl", "tp", "close_price", "profit", "commission",
              "swap", "reason"]


def _swing(n, r_each, start=dt.datetime(2026, 10, 1, 1, tzinfo=UTC), legs=2, prefix="S"):
    """n 回の注文（2本に分けて建てる）。1回の R ＝ r_each(k)（手数料と費用込みで合うように分ける）"""
    rows = []
    for k in range(n):
        t = int((start + dt.timedelta(hours=8 * k)).timestamp())
        risk = 1000.0
        money = r_each(k) * risk
        for leg in range(legs):
            rows.append([f"{prefix}{k}", legs, "watch", "filled", f"{prefix}T{k}-{leg}", t, t + 600, t + 620, t + 9000, "GBPJPY", 1,
                         200, 200.01, 0.02, 0.05, risk, 100000, 199, 201, 200.5, money / legs + 1.0, -0.5, -0.5, "tp"])
    return rows


def test_plans_r_and_open_legs():
    rows = [dict(zip(SWING_HEAD, map(str, r))) for r in _swing(3, lambda k: [0.5, -1.0, 2.0][k])]
    rows = rows[:-1]                                                    # 3回目は1本だけ閉じた＝まだ開いている
    ps, still_open = L.plans(rows, "signal_utc")
    assert [round(p["r"], 6) for p in ps] == [0.5, -1.0] and still_open == 1
    assert ps[0]["delay_min"] == 10.0 and ps[0]["date"] == "2026-10-01"


def test_at3_checkpoints_and_verdicts():
    good = [dict(zip(SWING_HEAD, map(str, r))) for r in _swing(1010, lambda k: 0.4 + (1 if (k // 3) % 2 else -1) * 0.5)]
    old = [dict(zip(SWING_HEAD, map(str, r))) for r in _swing(5, lambda k: 9.0, start=dt.datetime(2026, 9, 20, tzinfo=UTC), prefix="OLD")]
    skip = [dict(zip(SWING_HEAD, map(str, ["X1", 2, "watch", "skipped", "", int(NOW.timestamp()), "", "", "", "GBPJPY", 1,
                                            "", "", "", "", "", "", "", "", "", "", "", "", "90分より後"])))]
    out = L.build_at3(old + good + skip, today="2027-06-01", now="x")
    assert out["summary"]["n"] == 1010 and out["skipped"] == {"90分より後": 1}           # 登録日より前の5回は数えない
    v = out["verdicts"]["AT3"]
    assert v["status"] == "plus" and v["n"] == 1000 and v["lo"] > 0 and out["unit"] == "R"
    assert out["checkpoints"][0]["n"] == 30 and out["checkpoints"][-1]["n"] == 990
    assert all("r" in t and "d" in t and t["c"] == "AT3" for t in out["trades"])
    assert "profit" not in json.dumps(out) and "balance" not in json.dumps(out)          # 金額は書かない
    frozen = L.build_at3(old + good[:600] + skip, prev=out, today="2027-07-01", now="x")
    assert frozen["verdicts"]["AT3"] == v                                                 # 判定は変えない
    bad = [dict(zip(SWING_HEAD, map(str, r))) for r in _swing(330, lambda k: -0.4 + (1 if (k // 3) % 2 else -1) * 0.5)]
    s = L.build_at3(bad, today="2027-01-01", now="x")["verdicts"]["AT3"]
    assert s["status"] == "stop" and s["n"] == 300 and s["hi"] < 0                       # 300回の区切りでストップ
    few = L.build_at3(bad[:200], today="2027-01-01", now="x")
    assert not few["verdicts"] and [c["label"] for c in few["checkpoints"]][-1] in ("stop", "unknown")


def test_lists_show_at3_in_r():
    bad = [dict(zip(SWING_HEAD, map(str, r))) for r in _swing(330, lambda k: -0.4 + (1 if (k // 3) % 2 else -1) * 0.5)]
    d = tempfile.mkdtemp()
    p = os.path.join(d, "auto-forward.json")
    json.dump(L.build_at3(bad, today="2027-01-01", now="x"), open(p, "w", encoding="utf-8"), ensure_ascii=False)
    stop, plus, watching = V.collect([(p, "AT3 デモ", "")])
    assert [r["id"] for r in stop] == ["AT3"] and not watching
    txt = V.render(stop, plus, watching, now="x")
    assert "| AT3 |" in txt and "R |" in txt and "％ |" not in txt.split("## ⏹")[1].split("## ✅")[0]
    running = [dict(zip(SWING_HEAD, map(str, r))) for r in _swing(40, lambda k: 0.1)]
    json.dump(L.build_at3(running, today="2026-11-01", now="x"), open(p, "w", encoding="utf-8"), ensure_ascii=False)
    stop, plus, watching = V.collect([(p, "AT3 デモ", "")])
    assert not stop and watching[0]["n"] == 40 and "AT3 " in V.render(stop, plus, watching, now="x")
    fr = {"src": "x", "sec": "", "id": "AT3", "title": "デモ", "goal": 1000, "n": 1000, "unit": "R",
          "v": {"status": "plus", "decided_on": "2027-06-01", "n": 1000, "mean": 0.12, "lo": 0.03, "hi": 0.2}}
    assert "+0.120R" in P.render([fr], [], now="x")
    assert ("auto-forward.json", "AT3 4時間足のメールの合図をデモ口座で自動に建てる（前向き・手元の MT4）", "") in V.SOURCES


def test_guard_and_scalp_reports():
    g = [{"utc": "1", "rule": "G4", "ticket": "11", "symbol": "GBPJPY", "action": "flag", "mode": "observe", "price": "1",
          "lots": "0.1", "profit": "-500", "detail": "would_close"},
         {"utc": "2", "rule": "G4", "ticket": "11", "symbol": "GBPJPY", "action": "final", "mode": "observe", "price": "1",
          "lots": "0.1", "profit": "-3000", "detail": ""},
         {"utc": "3", "rule": "G1", "ticket": "12", "symbol": "USDJPY", "action": "set_sl", "mode": "enforce", "price": "1",
          "lots": "0.1", "profit": "0", "detail": ""}]
    md, pairs = L.guard_report(g)
    assert pairs == [{"rule": "G4", "ticket": "11", "at_flag": -500.0, "final": -3000.0}] and "G4：1件・差の合計 +2,500" in md
    head = ["plan", "legs", "ticket", "open_utc", "close_utc", "symbol", "dir", "planned", "fill", "spread", "lots", "risk",
            "balance", "sl", "close_price", "profit", "commission", "swap", "reason"]
    t0 = int(dt.datetime(2026, 10, 1, 6, 30, tzinfo=UTC).timestamp())                # 日本時間 15:30
    rows = []
    for k in range(60):
        r = 0.3 if k % 2 else -0.2
        rows.append(dict(zip(head, map(str, [f"P{k}", 1, f"T{k}", t0 + 86400 * k, t0 + 86400 * k + 1800, "GBPJPY", 1,
                                                 200.0, 200.02, 0.02, 0.1, 1000, 100000, 199.5, 200.3, r * 1000, 0, 0, "tp"]))))
    md2, cps = L.scalp_report(rows)
    assert [c["n"] for c in cps] == [30, 60] and "日本時間 15時台：60回" in md2 and "+0.02000" in md2


def test_read_csv_encodings():
    d = tempfile.mkdtemp()
    for utf16 in (True, False):
        p = os.path.join(d, f"x{utf16}.csv")
        _write_log(p, ["a", "b"], [[1, "日本語"]], utf16=utf16)
        assert L.read_csv(p) == [{"a": "1", "b": "日本語"}]
    assert L.read_csv(os.path.join(d, "none.csv")) == []


def test_workflow_and_sync():
    wf = open(".github/workflows/technical-alerts.yml", encoding="utf-8").read()
    assert "python build_signals_recent.py || true" in wf and "track-record.html signals-recent.json" in wf
    assert wf.index("python export_to_csv.py") < wf.index("python build_signals_recent.py")
    assert "'auto-forward.json'" in open(".github/workflows/research-lists.yml", encoding="utf-8").read()   # 届いたらリストを組み立て直す
    import check_site_consistency as C
    assert "signals-recent.json" in C.SYNC_FORBIDDEN and "auto-forward.json" not in C.SYNC_FORBIDDEN
    assert not [f for f in os.listdir(".") if f.lower().endswith((".mq4", ".mq5", ".ex4", ".ex5"))]   # EA はリポジトリに入れない


if __name__ == "__main__":
    fails = 0
    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for name, fn in tests:
        try:
            fn()
            print(f"  ✅ {name}")
        except AssertionError as e:
            fails += 1
            print(f"  ❌ {name}: {e}")
    print(f"--- {len(tests) - fails}/{len(tests)} 合格 ---")
    sys.exit(1 if fails else 0)
