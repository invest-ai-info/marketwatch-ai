# -*- coding: utf-8 -*-
"""jp_bars.py（研究ラボ共通の値段の置き場）のテスト。2026-10-06 夜 新設。

値段はすべて作り物（ネットワークに出ない）。確かめること＝①銘柄を台に漏れなく重ならず配る ②1台分を詰めて、まとめて、読み戻すと
Yahoo から取ったのと同じ形・同じ値（float32 の精度）になる ③置き場に無い銘柄・足は Yahoo から取る・取れなかった記録は None
④一覧は置き場の一覧 ⑤ワークフロー（8台で取る→まとめる→actions/cache）とラボが置き場を読むこと。

実行:  python tests/test_jp_bars.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import json
import os
import sys
import tempfile

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import jp_bars as J  # noqa: E402
import pillar_lab as P  # noqa: E402


def _fake(code, interval, rng):
    if code.startswith("X"):
        return None                                   # 取れない銘柄
    base = int(code[-2:])
    t0 = dt.datetime(2026, 9, 1, 9, 0, tzinfo=P.JST)
    step = {"1d": dt.timedelta(days=1), "60m": dt.timedelta(hours=1), "5m": dt.timedelta(minutes=5)}[interval]
    n = {"1d": 5, "60m": 4, "5m": 3}[interval]
    return [(t0 + k * step, 100.5 + base + k, 101.25 + base + k, 99.75 + base + k, 100.0 + base + k, 1234567.0 * (k + 1))
            for k in range(n)]


def test_shards_cover_all_codes_once():
    codes = [f"{1000 + i}" for i in range(37)]
    parts = [J.shard_codes(codes, s, 8) for s in range(8)]
    flat = [c for p in parts for c in p]
    assert sorted(flat) == sorted(codes) and len(flat) == len(set(flat)) and max(map(len, parts)) - min(map(len, parts)) <= 1


def test_pack_merge_and_read_back_same_rows():
    codes = ["1301", "1332", "X999", "7203"]
    p0 = J.fetch_shard(J.shard_codes(codes, 0, 2), fetch=_fake, pause=0)
    p1 = J.fetch_shard(J.shard_codes(codes, 1, 2), fetch=_fake, pause=0)
    meta = {"built_at": "2026-10-06T23:00+09:00", "list_date": "2026-09-30",
            "stocks": {c: {"name": "x"} for c in codes}}
    out = J.merge([p0, p1], meta)
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "jp-bars.npz")
        np.savez_compressed(path, **out)
        b = J.Bars(path)
        for code in ("1301", "1332", "7203"):
            for iv in ("1d", "60m", "5m"):
                got, want = b.fetch(code, iv, "5y", live=lambda *a: 1 / 0), _fake(code, iv, "5y")
                assert [r[0] for r in got] == [r[0] for r in want]
                assert np.allclose([r[1:] for r in got], [r[1:] for r in want], rtol=1e-6)
        assert b.fetch("X999", "1d", "5y", live=lambda *a: 1 / 0) is None    # 取れなかった記録＝Yahoo に取りに行かない
        assert b.fetch("9999", "1d", "5y", live=lambda c, i, r: [("live", c, i)]) == [("live", "9999", "1d")]   # 置き場に無い銘柄
        assert b.fetch("1301", "1wk", "5y", live=lambda c, i, r: "live-1wk") == "live-1wk"                      # 置き場に無い足
        assert b.live == 2 and b.missing["1d"] == ["X999"]
        b.meta["built_at"] = "2026-09-05T12:00+09:00"                     # 作った日から数えて範囲を切る
        assert len(b.fetch("1301", "1d", "2d", live=lambda *a: 1 / 0)) == 2 and len(b.fetch("1301", "1d", "max", live=lambda *a: 1 / 0)) == 5


def test_daily_uses_max_and_falls_back_when_bars_are_not_daily():
    def fake(code, interval, rng):
        t0 = dt.datetime(2006, 1, 4, 9, 0, tzinfo=P.JST)
        if interval == "1d" and rng == "max" and code == "1301":          # 月ごとの足が返った＝日足ではない
            return [(t0 + dt.timedelta(days=30 * k), 1, 1, 1, 1, 1) for k in range(12)]
        return _fake(code, interval, rng)
    out = J.fetch_shard(["1301", "7203"], fetch=fake, pause=0)
    assert J.SPECS[0] == ("1d", ("max", "10y")) and json.loads(out["fallback"])["1d"] == ["1301"]
    merged = J.merge([out], {"built_at": "2026-10-07T12:00+09:00", "specs": {"1d": ["max", "10y"]}})
    assert json.loads(merged["fallback"])["1d"] == ["1301"]
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "jp-bars.npz")
        np.savez_compressed(path, **merged)
        b = J.Bars(path)
        assert b.fallback["1d"] == ["1301"] and len(b.fetch("7203", "1d", "max", live=lambda *a: 1 / 0)) == 5
    assert J.daily_ok(_fake("1301", "1d", "max")) and not J.daily_ok([(dt.datetime(2006, 1, 1) + dt.timedelta(days=30 * k),) for k in range(5)])


def test_fetcher_and_universe_use_the_store_when_present():
    codes = ["1301", "7203"]
    out = J.merge([J.fetch_shard(codes, fetch=_fake, pause=0)],
                  {"built_at": "b", "list_date": "2026-09-30", "stocks": {"1301": {"name": "a"}, "7203": {"name": "b"}}})
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "jp-bars.npz")
        np.savez_compressed(path, **out)
        J._BARS = None
        f = J.fetcher(path)
        assert f("1301", "1d", "5y") and J.load_universe(path) == ({"1301": {"name": "a"}, "7203": {"name": "b"}}, "2026-09-30")
        assert J.info(path)["n_codes"] == 2
        J._BARS = None
    assert J.fetcher(os.path.join(ROOT, "no-such-dir", "x.npz")) is J.Y.fetch_chart
    J._BARS = None


def test_workflow_and_labs_read_the_store():
    wf = open(".github/workflows/jp-bars-cache.yml", encoding="utf-8").read().replace("python -u ", "python ")
    assert "python jp_bars.py fetch --shard" in wf and "python jp_bars.py merge" in wf
    assert "actions/cache/save@v4" in wf and "jp-bars-" in wf and "shard: [0, 1, 2, 3, 4, 5, 6, 7]" in wf
    for lab, w in (("gap_lab.py", "gap-lab.yml"), ("lows_trap_lab.py", "lows-trap-lab.yml"), ("highs_trap_small.py", "highs-trap-small.yml")):
        assert "jp_bars.fetcher()" in open(lab, encoding="utf-8").read(), lab
        y = open(f".github/workflows/{w}", encoding="utf-8").read()
        assert "actions/cache/restore@v4" in y and "restore-keys: jp-bars-" in y, w
    lint = open("check_site_consistency.py", encoding="utf-8").read()
    assert '"jp-bars/"' in lint or "jp-bars" in lint


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
