"""recheck_status（検算の記録の読み書き）のテスト。pytest 不要・pytest でも動く。

  PYTHONUTF8=1 python tests/test_recheck_status.py
"""
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import recheck_status as S  # noqa: E402


def _root(stores=None):
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "recheck"))
    for kind, body in (stores or {}).items():
        with open(os.path.join(d, "recheck", f"{kind}.json"), "w", encoding="utf-8") as f:
            json.dump(body, f, ensure_ascii=False)
    return d


def _root_raw(rel, text):
    d = tempfile.mkdtemp()
    p = os.path.join(d, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)
    return d


def test_go_live_is_fixed():
    assert S.GO_LIVE == "2026-11-27"


def test_waiting_only_after_go_live():
    r = _root({})
    assert not S.is_waiting("x", "2026-11-07", r, go_live="2026-11-27")
    assert not S.is_waiting("x", None, r, go_live="2026-11-27")
    assert S.is_waiting("x", "2026-11-27", r, go_live="2026-11-27")


def test_record_with_full_agreement_releases():
    r = _root({"records": {"x": {"n_orig": 10, "matched": 10, "agreement": 1.0}}})
    assert S.recheck_ok("x", r)
    assert not S.is_waiting("x", "2026-12-01", r, go_live="2026-11-27")


def test_zero_rows_or_partial_agreement_is_not_ok():
    r = _root({"records": {"a": {"n_orig": 0, "agreement": 1.0}, "b": {"n_orig": 5, "agreement": 0.8}}})
    assert not S.recheck_ok("a", r)
    assert not S.recheck_ok("b", r)
    assert not S.entry_ok(None)


def test_boundaries_found_by_mutate_check():     # mutate_check が見つけた、テストが気づかなかった壊し方
    assert not S.entry_ok({"agreement": 1.0})                  # 件数の欄が無い記録は通さない
    assert S.entry_ok({"n_orig": 1, "agreement": 1.0})         # 1件ちょうどは通す
    r = _root({})
    assert S.is_waiting("x", "2026-12-05", r, go_live="2026-12-01")
    assert not S.is_waiting("x", "2026-11-30", r, go_live="2026-12-01")   # GO_LIVE と違う日を渡しても効く


def test_broken_store_reads_as_empty():
    r = _root_raw("recheck/records.json", "{壊れた")
    assert S.load_store("records", r) == {}
    assert not S.recheck_ok("x", r)


def test_put_keeps_previous_and_safe_names():
    r = _root({})
    S.put("records", "J4F/F 1", {"agreement": 0.5}, r)
    S.put("records", "J4F/F 1", {"agreement": 1.0}, r)
    e = S.load_store("records", r)["J4F_F_1"]
    assert e["agreement"] == 1.0
    assert e["previous"][0]["agreement"] == 0.5


def test_local_only_is_read_on_top():
    r = _root({"records": {"x": {"n_orig": 3, "agreement": 0.5}}})
    S.put("records", "x", {"n_orig": 3, "agreement": 1.0}, r, local_only=True)
    assert os.path.exists(os.path.join(r, "research", "recheck", "records.json"))
    assert S.recheck_ok("x", r)


def test_audit_by_fingerprint():
    fp = "ab12cd34ef56" + "0" * 52
    r = _root({"audits": {"X1": {"fingerprint": fp, "errors": 0}}})
    assert S.audit_by_fingerprint("ab12cd34ef56", r)["errors"] == 0
    assert S.audit_by_fingerprint("ffffffffffff", r) is None


def test_written_with_lf():
    r = _root({})
    S.put("audits", "y", {"errors": 0}, r)
    with open(S.store_path("audits", r), "rb") as f:
        assert b"\r\n" not in f.read()


def test_old_fingerprint_found_after_reaudit():
    r = _root({})
    S.put("audits", "OJ9", {"fingerprint": "aaaaaaaaaaaa" + "0" * 52, "errors": 0}, r)
    S.put("audits", "OJ9", {"fingerprint": "bbbbbbbbbbbb" + "0" * 52, "errors": 0}, r)
    assert S.audit_by_fingerprint("aaaaaaaaaaaa", r) is not None


def test_safe_keeps_japanese_so_live_pair_differs():   # tracker の実在の2つ（上昇・下降）がぶつからない
    assert S.safe("auto_reversal_long-True_trend-上昇") != S.safe("auto_reversal_long-True_trend-下降")


def test_data_version_share_is_limited():
    assert not S.entry_ok({"n_orig": 20, "matched": 1, "agreement": 1.0, "excluded_data_version": 19})
    assert S.entry_ok({"n_orig": 20, "matched": 18, "agreement": 1.0, "excluded_data_version": 2})


def test_default_root_is_the_repo_folder():
    assert S.store_path("audits") == os.path.join(ROOT, "recheck", "audits.json")


if __name__ == "__main__":
    n = 0
    for k, fn in list(globals().items()):
        if k.startswith("test_") and callable(fn):
            fn()
            n += 1
    print(f"ok {n}")
