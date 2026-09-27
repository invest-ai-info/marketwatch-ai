# -*- coding: utf-8 -*-
"""新しい柱・第1波（pillar_lab.py）のテスト。2026-09-27 新設（オーナー決定「投資の成績を上げることを一番の目標に」）。

値動きはすべて作り物（ネットワークに出ない）。確かめること＝物差しが事前登録（PILLAR_PREREG.md）どおりか、
仕込んだ効果を見つけ・仕込まない効果を見つけないか、日程の一次情報の読み取りが正しいか。

実行:  python tests/test_pillar_lab.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import hashlib
import math
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import pillar_lab as P  # noqa: E402

D = dt.date
GW_2026 = {D(2026, 5, 4), D(2026, 5, 5), D(2026, 5, 6)}


def _hourly(start_utc, hours, price=150.0, step=None):
    """作り物の1時間足（UTC）。step(i, ts) で各足の値動き（対数・始値→終値）を決める"""
    idx = pd.date_range(start_utc, periods=hours, freq="h", tz="UTC")
    o, c, p = [], [], price
    for i, ts in enumerate(idx):
        r = step(i, ts) if step else 0.0
        o.append(p)
        p = p * math.exp(r)
        c.append(p)
    return pd.DataFrame({"Open": o, "High": np.maximum(o, c), "Low": np.minimum(o, c), "Close": c}, index=idx)


# ── 事前登録と定数が食い違っていないか ──

def test_prereg_numbers_match_the_code():
    text = open(P.PREREG, encoding="utf-8").read()
    assert P.A1_SPLIT == "2026-08-01" and "8月1日から" in text
    assert P.A1_MIN_N == 100 and "100件未満" in text
    assert P.B1_COST_YEN == 0.003 and "0.3銭" in text
    assert P.B2_SHOCK_RATIO == 2.0 and "2倍以上" in text
    assert P.B1_PRE == (7, 10) and "7時の足の始値 → 9時の足の終値（＝10時）" in text
    assert P.B1_POST == (10, 15) and "10時の足の始値 → 14時の足の終値（＝15時）" in text
    assert P.EVENT_TIME_ET == {"fomc": (14, 0), "cpi": (8, 30), "nfp": (8, 30)}
    assert P.B4W_LAG_DAYS == 8 and "8日後" in text and P.B4W_HOLD == 5 and "5本後" in text
    assert P.B4W_SPLIT == "2025-01-01" and "2025年1月1日から" in text
    assert P.B4W_WINDOW == 52 and "直前52週" in text and P.B4W_MIN_HIST == 26 and "26週以上" in text
    assert P.B4W_TAIL == 0.2 and "上位2割" in text and P.B4W_MIN_N == 100
    assert P.prereg_sha256() == hashlib.sha256(open(P.PREREG, "rb").read()).hexdigest()


# ── B1 ゴトー日 ──

def test_gotobi_moves_to_previous_business_day():
    g = P.gotobi_dates(D(2026, 5, 1), D(2026, 5, 31), GW_2026)
    # 5日は連休（3日日曜・4〜6日祝）→ 1日（金）。10日は日曜→8日。31日は日曜→29日（月末）
    assert sorted(g) == [D(2026, 5, 1), D(2026, 5, 8), D(2026, 5, 15), D(2026, 5, 20), D(2026, 5, 25), D(2026, 5, 29)]
    assert g[D(2026, 5, 29)] == "月末" and g[D(2026, 5, 1)] == "5・10日"
    # 12月31日は銀行の休み → 30日（水）が月末のゴトー日
    assert D(2026, 12, 30) in P.gotobi_dates(D(2026, 12, 1), D(2026, 12, 31), set())
    assert not P.jp_business_day(D(2027, 1, 2), set())


def test_session_return_is_7_to_10_jst():
    # 2026-09-24（木）の日本時間 7:00 = 前日 22:00 UTC。7時・8時・9時の足で各 +0.1% → 約 +30 bps
    def step(i, ts):
        h = ts.tz_convert(P.JST).hour
        return 0.001 if h in (7, 8, 9) else 0.0
    bars = _hourly("2026-09-23 12:00", 30, step=step)
    pre, _ = P.session_return(bars, D(2026, 9, 24), *P.B1_PRE)
    assert abs(pre - 30.0) < 1e-6
    post, _ = P.session_return(bars, D(2026, 9, 24), *P.B1_POST)
    assert abs(post) < 1e-9
    assert P.session_return(bars, D(2026, 9, 26), *P.B1_PRE) is None      # 足が無い日は数えない


def _b1_rows(effect, n=420, seed=1):
    rng = np.random.default_rng(seed)
    rows, d = [], D(2024, 10, 1)
    while len(rows) < n:
        if d.weekday() < 5:
            g = d.day in (5, 10, 15, 20, 25)
            rows.append({"date": d.isoformat(), "gotobi": g, "kind": "5・10日" if g else None,
                         "pre": (effect if g else 0.0) + rng.normal(0, 3), "post": rng.normal(0, 3), "cost": 0.2})
        d += dt.timedelta(days=1)
    return rows


def test_b1_finds_a_planted_effect_and_not_a_missing_one():
    assert P.b1_stats(_b1_rows(4.0))["verdict"] == "今も残っている"
    r = P.b1_stats(_b1_rows(0.0))
    assert r["verdict"] == "見えない（偶然の範囲）"
    assert r["pre"]["net"] < r["pre"]["mean_a"]                         # 費用を引いている
    assert P.b1_stats(_b1_rows(-4.0))["verdict"] == "逆向き"


def test_b1_effect_smaller_than_cost_is_not_counted():
    rows = _b1_rows(4.0)
    for x in rows:
        x["cost"] = 10.0                                                # 費用が効果より大きい
    assert P.b1_stats(rows)["verdict"] == "見えない（偶然の範囲）"


# ── A1 AIの見立て ──

def test_a1_samples_weekday_mornings_only():
    t = lambda s: dt.datetime.fromisoformat(s)  # noqa: E731
    briefs = [(t("2026-09-25T06:07:00+09:00"), {"X": ("BULLISH", "MID")}),   # 金 朝
              (t("2026-09-25T06:30:00+09:00"), {"X": ("BEARISH", "MID")}),   # 同じ朝の2便目＝使わない
              (t("2026-09-25T15:10:00+09:00"), {"X": ("BEARISH", "MID")}),   # 夕方＝使わない
              (t("2026-09-26T06:07:00+09:00"), {"X": ("BULLISH", "MID")}),   # 土＝使わない
              (t("2026-09-28T06:07:00+09:00"), {"X": ("BULLISH", "MID")}),   # 月 朝
              (t("2026-09-29T06:07:00+09:00"), {"X": ("BULLISH", "MID")})]
    assert [x[0].day for x in P.a1_samples(briefs, "24h")] == [25, 28, 29]
    assert [x[0].day for x in P.a1_samples(briefs, "1w")] == [25, 28]       # 週の最初の平日の朝


def test_window_return_enters_after_the_briefing():
    bars = _hourly("2026-09-24 12:00", 72, step=lambda i, ts: 0.001)
    t0 = dt.datetime(2026, 9, 25, 6, 7, tzinfo=P.JST)                          # 21:07 UTC → 22:00 の足から
    lr = P.window_return(bars, t0, 24)
    assert abs(lr - 0.024) < 1e-9                                              # 24本分
    assert P.window_return(bars, dt.datetime(2026, 9, 30, tzinfo=P.JST), 24) is None


def _a1_rows(effect, n_days=90, seed=2):
    rng = np.random.default_rng(seed)
    rows, d = [], D(2026, 6, 1)
    for _ in range(n_days):
        while d.weekday() >= 5:
            d += dt.timedelta(days=1)
        for tk in ("A", "B", "C"):
            s = int(rng.choice([1, -1]))
            raw = effect * s + rng.normal(0, 1)
            rows.append({"ticker": tk, "date": d.isoformat(), "sign": s, "conv": "MID", "z": s * raw, "raw": raw})
        d += dt.timedelta(days=1)
    return rows


def test_a1_judges_contrarian_forward_and_nothing():
    assert P.a1_stats(_a1_rows(-0.6), n_perm=300)["verdict"] == "逆指標の兆し"
    assert P.a1_stats(_a1_rows(+0.6), n_perm=300)["verdict"] == "順指標の兆し"
    assert P.a1_stats(_a1_rows(0.0), n_perm=300)["verdict"] == "差なし（偶然の範囲）"
    assert P.a1_stats(_a1_rows(-0.6, n_days=20), n_perm=300)["verdict"] == "件数不足"   # 60件
    r = P.a1_stats(_a1_rows(-0.6), n_perm=300)
    assert r["n_early"] and r["n_late"] and r["early"] < 0 and r["late"] < 0


def test_yf_ticker():
    assert P.yf_ticker("USDJPY") == "USDJPY=X" and P.yf_ticker("NKD=F") == "NKD=F" and P.yf_ticker("BTC-USD") == "BTC-USD"


# ── B2 発表の日程（一次情報の読み取り）と前後の値動き ──

FOMC_HTML = """
<h4>2025 FOMC Meetings</h4>
<div class="row fomc-meeting"><div class="fomc-meeting__month col-xs-5"><strong>January</strong></div>
<div class="fomc-meeting__date col-xs-4">28-29</div>
<a href="/newsevents/pressreleases/monetary20250129a.htm">HTML</a></div>
<div class="fomc-meeting--shaded row fomc-meeting"><div class="fomc-meeting--shaded fomc-meeting__month col-xs-5"><strong>March</strong></div>
<div class="fomc-meeting__date col-xs-4">18-19*</div>
<a href="/newsevents/pressreleases/monetary20250319a.htm">HTML</a></div>
<div class="row fomc-meeting"><div class="fomc-meeting__month col-xs-5"><strong>August</strong></div>
<div class="fomc-meeting__date col-xs-4">22 (notation vote)</div>
<a href="/newsevents/pressreleases/monetary20250822a.htm">HTML</a></div>
<div class="row fomc-meeting"><div class="fomc-meeting__month col-xs-5"><strong>December</strong></div>
<div class="fomc-meeting__date col-xs-4">9-10*</div></div>
"""


def test_parse_fomc_takes_scheduled_statements_only():
    assert P.parse_fomc(FOMC_HTML) == [D(2025, 1, 29), D(2025, 3, 19)]   # 持ち回り・声明の無い先の会合は除く


def test_parse_bls_reads_dates_from_archive_links():
    html = ('<a href="/news.release/archives/cpi_09112026.htm">Aug</a>'
            '<a href="/news.release/archives/cpi_08122026.htm">Jul</a>'
            '<a href="/news.release/archives/empsit_09042026.htm">x</a>')
    assert P.parse_bls(html, "cpi") == [D(2026, 8, 12), D(2026, 9, 11)]
    assert P.parse_bls(html, "empsit") == [D(2026, 9, 4)]


def test_b2_finds_a_planted_pre_fomc_rise_and_big_reaction():
    events = [D(2025, 1, 29) + dt.timedelta(days=7 * k) for k in range(20)]   # 水曜・20回

    def step(i, ts):
        et = ts.tz_convert(P.ET)
        for d in events:
            T = pd.Timestamp(dt.datetime(d.year, d.month, d.day, 14, 0, tzinfo=P.ET))
            if T - pd.Timedelta(hours=24) <= ts < T:
                return 0.0002                                      # 前24時間で 約 +48 bps
            if T <= ts < T + pd.Timedelta(hours=2):
                return 0.004 if (et.day % 2) else -0.004           # 直後に大きく動く
        return 0.00005 if i % 2 else -0.00005
    bars = _hourly("2025-01-01 00:00", 24 * 170, step=step)
    out = P.b2_study({"ES=F": bars}, {"fomc": events}, D(2026, 1, 1))
    f = out["fomc_eq"]
    assert f["n_events"] == 20 and f["mean"] > 40 and f["verdict"] == "FOMC前の上昇が今も見える"
    assert out["ratio"]["fomc"]["ES=F"]["ratio"] > P.B2_SHOCK_RATIO and out["shock"]["fomc"] == ["ES=F"]


def test_b2_nothing_planted_is_not_seen():
    events = [D(2025, 1, 29) + dt.timedelta(days=7 * k) for k in range(20)]
    rng = np.random.default_rng(5)
    noise = rng.normal(0, 0.001, 24 * 170)
    bars = _hourly("2025-01-01 00:00", 24 * 170, step=lambda i, ts: noise[i])
    out = P.b2_study({"ES=F": bars}, {"fomc": events}, D(2026, 1, 1))
    assert out["fomc_eq"]["verdict"] == "見えない"


def test_b4_file_kind_and_csv_shape():
    assert P.file_kind(b"\xd0\xcf\x11\xe0rest") == "xls" and P.file_kind(b"PK\x03\x04") == "xlsx"
    assert P.file_kind(b"<!DOCTYPE html><html>") == "html"
    raw = "日付,通貨ペア,売建玉,買建玉\n2026/09/25,USD/JPY,100,300\n2026/09/24,USD/JPY,110,290\n".encode("cp932")
    s = P.summarize_table(raw, P.file_kind(raw))
    assert s["kind"] == "text" and s["rows"] == 3 and s["head"][0][2] == "売建玉" and s["tail"][-1][3] == "290"


def _weekly_sheet(weeks, pairs=("USD/JPY", "EUR/USD", "CHF/JPY"), seed=3, crowd=None):
    """為替売買動向（週次）と同じ形の表（1行目にペア名・次に 日付/売り/買い・次に date/sell/buy）"""
    rng = np.random.default_rng(seed)
    head1 = ["nan"] + [x for p in pairs for x in (p, "nan")]
    head2 = ["日付"] + ["売り", "買い"] * len(pairs)
    head3 = ["date"] + ["sell", "buy"] * len(pairs)
    rows = [head1, head2, head3]
    for k, d in enumerate(weeks):
        r = [d.strftime("%m/%d/%Y")]
        for p in pairs:
            share = crowd(p, k) if crowd else 0.5 + 0.1 * rng.normal()
            r += [str(1000 * (1 - share)), str(1000 * share)]
        rows.append(r)
    return pd.DataFrame(rows)


def test_parse_weekly_sellbuy_and_signals():
    weeks = [D(2023, 1, 3) + dt.timedelta(days=7 * k) for k in range(60)]
    parsed = P.parse_weekly_sellbuy(_weekly_sheet(weeks))
    assert sorted(parsed) == ["CHF/JPY", "EUR/USD", "USD/JPY"] and len(parsed["USD/JPY"]) == 60
    d, sell, buy = parsed["USD/JPY"][0]
    assert d == D(2023, 1, 3) and abs(sell + buy - 1000) < 1e-6
    # 買いの割合がどんどん増える＝毎週「過去最高」→ 27週目から毎週 −1（買いに偏り＝下を予想）
    ser = [(w, 1000 - (400 + k), 400 + k) for k, w in enumerate(weeks)]
    sig = P.b4w_signals(ser)
    assert len(sig) == 60 - P.B4W_MIN_HIST and all(s == -1 for _, s in sig) and sig[0][0] == weeks[P.B4W_MIN_HIST]


def _b4w_data(effect, n_weeks=200, seed=4):
    """週ごとに偏りをランダムに作り、effect>0 なら「偏りの逆」に値が動く作り物の日足"""
    rng = np.random.default_rng(seed)
    weeks = [D(2022, 11, 1) + dt.timedelta(days=7 * k) for k in range(n_weeks)]
    pairs = P.B4W_MAIN
    share = {p: rng.uniform(0.3, 0.7, n_weeks) for p in pairs}
    sheet = _weekly_sheet(weeks, pairs=pairs, crowd=lambda p, k: share[p][k])
    parsed = P.parse_weekly_sellbuy(sheet)
    days = pd.bdate_range("2022-06-01", "2026-12-31")
    daily_by = {}
    for p in pairs:
        sig = dict(P.b4w_signals(parsed[p]))
        drift = np.zeros(len(days))
        for d, s in sig.items():                       # 入る日（8日後）から5本の間だけ、予想の向きに動かす
            i0 = int(np.searchsorted(days.values, np.datetime64(d + dt.timedelta(days=P.B4W_LAG_DAYS))))
            drift[i0 + 1:i0 + 1 + P.B4W_HOLD] += effect * s
        r = rng.normal(0, 0.005, len(days)) + drift
        daily_by[p] = pd.DataFrame({"Open": 100.0, "Close": 100 * np.exp(np.cumsum(r))}, index=days)
    return parsed, daily_by


def test_b4w_finds_planted_contrarian_and_not_nothing():
    parsed, daily = _b4w_data(0.004)
    r = P.b4w_stats(P.b4w_rows(parsed, daily))
    assert r["n"] >= P.B4W_MIN_N and r["verdict"] == "個人の逆張りの兆し", (r["n"], r["verdict"], r.get("mean"))
    parsed, daily = _b4w_data(0.0)
    assert P.b4w_stats(P.b4w_rows(parsed, daily))["verdict"] == "差なし（偶然の範囲）"
    parsed, daily = _b4w_data(-0.004)
    assert P.b4w_stats(P.b4w_rows(parsed, daily))["verdict"] == "個人と同じ向きの兆し"


def test_b4w_entry_waits_eight_days():
    parsed, daily = _b4w_data(0.0, n_weeks=40)
    rows = P.b4w_rows(parsed, daily)
    first_sig = P.b4w_signals(parsed["USD/JPY"])[0][0]
    first_row = min(r["date"] for r in rows if r["ticker"] == "USD/JPY")
    assert first_row >= (first_sig + dt.timedelta(days=P.B4W_LAG_DAYS)).isoformat()


def test_render_md_runs_on_partial_results():
    res = {"generated_at": "2026-09-27T12:00+09:00", "prereg_sha256": "ab" * 32,
           "a1": {"error": "x"}, "b1": {P.B1_TICKER: {"error": "値動きを取得できず"}},
           "b2": {"fomc_eq": {"verdict": "見えない", "n_events": 0}, "sources": {"fomc": "ok"}, "ratio": {}},
           "b4": [{"url": "u", "ok": False, "error": "e"}],
           "b4_files": {"files": [{"url": "f", "ok": True, "kind": "text", "rows": 3}], "archive": {"003-20250925": {"status": 404}}}}
    md = P.render_md(res)
    assert "投資助言ではありません" in md and "B4" in md and "計算できず" in md and "003-20250925=404" in md


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
