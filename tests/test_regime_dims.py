# -*- coding: utf-8 -*-
"""2026-09-26 に足した「環境の相性ラボ」の追跡用の次元（family / adx_band / vix_band / asset_class）と、
トラッカー登録の番人の「反映待ち」猶予のテスト。

動機＝オーナー指示「環境の相性ラボの候補3つをトラッカーに登録して前向きに追跡して」。
境界は regime_lab.py の事前登録（2026-09-25）と同じ＝以後変えないことをここで固定する。

実行:  python tests/test_regime_dims.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_spec = importlib.util.spec_from_file_location("signal_lab_verify", os.path.join(ROOT, "signal_lab_verify.py"))
V = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(V)


def _sig(primary, direction, adx=None, vix=None, ticker="USDJPY=X", tf="1d"):
    d = {"primary_signal": primary, "direction": direction, "ticker": ticker, "timeframe": tf}
    if adx is not None:
        d["indicators_at_signal"] = {"adx": adx}
    if vix is not None:
        d["environment"] = {"vix": {"current": vix}}
    return d


L, S = "ロング（買い）", "ショート（売り）"


def test_family_pairs():
    assert V.family_of(_sig("high_break", L)) == "tf"
    assert V.family_of(_sig("low_break", S)) == "tf"
    assert V.family_of(_sig("macd_dead", S)) == "tf"
    assert V.family_of(_sig("macd_dead", L)) is None          # 向きが逆＝どちらの族でもない
    assert V.family_of(_sig("bb_lower_touch", L)) == "mr"
    assert V.family_of(_sig("rsi_oversold_bounce", L)) == "mr"
    assert V.family_of(_sig("support_bounce", L)) is None     # 8つの入口の外
    assert V.family_of(_sig("bb_lower_touch", None)) is None  # 向きなし


def test_family_mr_equals_reversal_long():
    for p in ("bb_lower_touch", "rsi_oversold_bounce", "high_break"):
        for dr in (L, S):
            d = _sig(p, dr)
            assert V.match(d, {"family": "mr"}) == V.match(d, {"reversal_long": True}), (p, dr)


def test_adx_band_boundaries():
    assert V.adx_band_of(_sig("high_break", L, adx=19.99)) == "weak"
    assert V.adx_band_of(_sig("high_break", L, adx=20.0)) == "mid"
    assert V.adx_band_of(_sig("high_break", L, adx=24.99)) == "mid"
    assert V.adx_band_of(_sig("high_break", L, adx=25.0)) == "strong"
    assert V.adx_band_of(_sig("high_break", L)) is None       # 記録なし＝マッチしない


def test_vix_band_boundaries():
    assert V.vix_band_of(_sig("bb_lower_touch", L, vix=14.99)) == "low"
    assert V.vix_band_of(_sig("bb_lower_touch", L, vix=15.0)) == "mid"
    assert V.vix_band_of(_sig("bb_lower_touch", L, vix=24.99)) == "mid"
    assert V.vix_band_of(_sig("bb_lower_touch", L, vix=25.0)) == "high"
    assert V.vix_band_of(_sig("bb_lower_touch", L)) is None


def test_asset_class():
    assert V.asset_class_of(_sig("x", L, ticker="EURUSD=X")) == "fx"
    assert V.asset_class_of(_sig("x", L, ticker="GBPJPY=X")) == "fx"
    assert V.asset_class_of(_sig("x", L, ticker="ES=F")) == "index"
    assert V.asset_class_of(_sig("x", L, ticker="CL=F")) == "commodity"
    assert V.asset_class_of(_sig("x", L, ticker="BTC-USD")) == "crypto"
    assert V.asset_class_of(_sig("x", L, ticker="HG=F")) is None   # 拡張ユニバースは含めない


def test_registered_filters_match_as_intended():
    fx_mr_1d = {"asset_class": "fx", "family": "mr", "tf": "1d"}
    assert V.match(_sig("bb_lower_touch", L, ticker="AUDUSD=X"), fx_mr_1d)
    assert not V.match(_sig("bb_lower_touch", L, ticker="AUDUSD=X", tf="4h"), fx_mr_1d)
    assert not V.match(_sig("bb_lower_touch", L, ticker="ES=F"), fx_mr_1d)
    assert V.match(_sig("macd_golden", L, adx=18), {"family": "tf", "adx_band": "weak"})
    assert not V.match(_sig("macd_golden", L, adx=30), {"family": "tf", "adx_band": "weak"})
    assert V.match(_sig("rsi_oversold_bounce", L, vix=27), {"family": "mr", "vix_band": "high"})


def test_new_keys_are_allowed():
    for k in ("family", "adx_band", "vix_band", "asset_class"):
        assert k in V.ALLOWED_FILTER_KEYS, k


def test_tracker_declares_the_five():
    import signal_lab_tracker as T
    ids = {h["id"] for h in T.REGISTER_2026_09_26["register"]}
    assert ids == {"rl_tf_adx_weak", "rl_tf_adx_strong", "rl_mr_vix_high", "rl_mr_vix_low", "rl_fx_mr_1d"}
    for h in T.REGISTER_2026_09_26["register"]:
        assert set(h["filter"]) <= V.ALLOWED_FILTER_KEYS, h["id"]


def test_registration_is_idempotent():
    # 本物の tracker.json（登録前の状態）に当てる: 1回目で5本だけ増え、2回目は何も変えない
    import json
    import signal_lab_tracker as T
    t = json.load(open(os.path.join(ROOT, "signal-lab-tracker.json"), encoding="utf-8-sig"))
    new_ids = {h["id"] for h in T.REGISTER_2026_09_26["register"] + T.REGISTER_EXIT_2026_09_26["register"]}
    already = new_ids & {h["id"] for h in t["hypotheses"]}
    first = T.apply_holdout_bootstrap(t)
    assert first == len(new_ids - already), first
    assert T.apply_holdout_bootstrap(t) == 0
    assert new_ids <= {h["id"] for h in t["hypotheses"]}


def test_blocked_gate_declared():
    import signal_lab_tracker as T
    (h,) = T.REGISTER_EXIT_2026_09_26["register"]
    assert h["id"] == "rl_tf_blocked" and h["kind"] == "gate" and h["filter"] == {"family": "tf", "blocked": True}
    d = {"primary_signal": "high_break", "direction": "ロング（買い）", "sr_runway": {"blocked": True}}
    assert V.match(d, h["filter"]) and not V.match(dict(d, sr_runway={"blocked": False}), h["filter"])


def test_watcher_grace_for_new_declarations():
    import check_automation_health as H
    absent = [{"id": "old", "registered_at": "2026-09-20"}, {"id": "yday", "registered_at": "2026-09-25"},
              {"id": "today", "registered_at": "2026-09-26"}]
    missing, pending = H.split_missing(absent, dt.date(2026, 9, 26))
    assert missing == ["old"]
    assert pending == ["today", "yday"]
    missing, pending = H.split_missing(absent, dt.date(2026, 9, 28))
    assert missing == ["old", "today", "yday"] and pending == []


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
