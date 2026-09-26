# -*- coding: utf-8 -*-
"""research_map.py（いま検証中のこと＝研究の地図）の約束ごとのテスト。2026-09-26 新設。

固定すること: 追っている仮説は漏れなく1回ずつ載る／終わった仮説は「終わった検証」へ／登録したがまだ集計に
入っていない仮説も「登録したばかり」で載る（翌朝の集計を待たずに一覧へ）／データが無くてもタブは落ちない／
文字はエスケープする／成績ページにタブと #map の直リンクがある／地図が壊れても成績ページは作れる。

実行:  python tests/test_research_map.py     （pytest 不要。pytest でも動く）
"""
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import check_plain_japanese as C  # noqa: E402
import generate_track_record_page as G  # noqa: E402
import research_map as R  # noqa: E402
import signal_lab_tracker as T  # noqa: E402


def _all_rows(m):
    return [r for th in m["themes"] for r in th["rows"]]


def test_every_live_hypothesis_listed_exactly_once():
    t = json.load(open(R.TRACKER_FILE, encoding="utf-8"))
    m = R.collect()
    ids = [r["id"] for r in _all_rows(m)]
    live = [h["id"] for h in t["hypotheses"] if h.get("status") in ("tracking", "promoted")]
    assert len(ids) == len(set(ids))
    assert set(live) <= set(ids)
    ended = [h for h in t["hypotheses"] if h.get("status") not in ("tracking", "promoted")]
    assert len(m["ended"]) == len(ended)
    assert m["n_active"] == len(ids)


def test_theme_follows_filter_keys():
    assert R.theme_of({"family": "tf", "adx_band": "weak"}) == "env"
    assert R.theme_of({"fbias": "mismatch"}) == "env"
    assert R.theme_of({"rsi_band": "mid", "signal": "bb_lower_touch"}) == "state"
    assert R.theme_of({"family": "tf", "blocked": True}) == "wall"
    assert R.theme_of({"group": "metal", "direction": "long"}) == "basic"


def test_next_checkpoint_matches_tracker_rule():
    h = {"holdout_pass": False, "last_eval_n": 170}
    assert R.next_checkpoint(h) == 240                      # 80 の倍数で次
    h = {"holdout_pass": True, "last_eval_n": 60}
    assert R.next_checkpoint(h) == 90                       # 昇格の候補は 30 ごと
    assert R.next_checkpoint({}) == T.PROMOTE_MIN_N


def test_registered_but_not_yet_counted_is_shown_as_new():
    t = json.load(open(R.TRACKER_FILE, encoding="utf-8"))
    reg = T.REGISTER_ENVPROFILE_2026_09_26["register"]
    ids = {s["id"] for s in reg}
    t2 = dict(t, hypotheses=[h for h in t["hypotheses"] if h.get("id") not in ids])
    pend = {s["id"] for s in R.registered_not_yet_tracked(t2)}
    assert ids <= pend
    # 集計に入った後（同じ id か同じ条件がある）は「登録したばかり」に出さない
    t3 = dict(t2, hypotheses=t2["hypotheses"] + [dict(s, status="tracking") for s in reg])
    assert not ids & {s["id"] for s in R.registered_not_yet_tracked(t3)}
    moved = [dict(s, id=s["id"] + "_x", status="tracking") for s in reg]   # id が違っても条件が同じなら登録済み
    t4 = dict(t2, hypotheses=t2["hypotheses"] + moved)
    assert not ids & {s["id"] for s in R.registered_not_yet_tracked(t4)}


def test_missing_data_does_not_break_the_tab():
    empty = tempfile.mkdtemp()
    html = R.build_pane(root=empty)
    assert 'id="pane-map"' in html and "まだ集計がありません" in html


def test_text_is_escaped():
    m = R.collect()
    m["themes"] = [{"key": "basic", "title": "t", "desc": "d", "rows": [dict(
        _all_rows(R.collect())[0], name="<script>alert(1)</script>", pair_name=None)]}]
    html = R.build_pane(model=m)
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;" in html


def test_track_record_page_has_tab_and_direct_link():
    sig = [s for s in G.load_json(G.SIGNALS_LOG_FILE) if not G.is_weekend_closed_fire(s)][:50]
    html = G.build_html(sig, [], G.load_json(G.TRACKER_FILE) or None)
    assert html.count('data-tab="map"') == 1 and html.count('id="pane-map"') == 1
    assert "location.hash" in html and "hashchange" in html
    assert html.index('data-tab="map"') < html.index('data-tab="banzuke"')


def test_track_record_page_survives_broken_map():
    orig = R.build_pane

    def boom(*a, **k):
        raise RuntimeError("壊れた")
    R.build_pane = boom
    try:
        pane = G.build_research_map_section()
    finally:
        R.build_pane = orig
    assert 'id="pane-map"' in pane and "作れませんでした" in pane


def test_post_hoc_notes_point_at_real_ids_and_are_shown():
    # 注記の id の打ち間違いで注記が黙って消えないように（2026-09-26 法務チェック G3）
    reg = {s["id"] for name in dir(T) if name.isupper() for v in [getattr(T, name)]
           if isinstance(v, dict) and isinstance(v.get("register"), list) for s in v["register"]}
    wall = set((json.load(open(R.WALL_LAB, encoding="utf-8")).get("forward") or {}))
    assert set(R.POST_HOC_NOTES) <= reg | wall
    html = R.build_pane()
    assert "約50の区分を調べて見つかった1つ" in html


def test_wording_avoids_assertive_labels():
    # 法務チェック（2026-09-26）: 断定に読める「確かめられた」「避けたほうがよい」を表示に出さない
    html = R.build_pane()
    assert "確かめられた" not in html and "避けたほうがよい" not in html
    assert R.verdict_plain("確かめられた・効きやすい").startswith("厳しい基準を満たした")
    assert "確かめられた" not in R.verdict_plain("確かめられた・効きにくい")


def test_plain_japanese_only_indicator_names_remain():
    # やさしい日本語の検査で残してよいのは、説明を付けた指標名 ADX だけ（ほかの規則の指摘は 0 件）
    found = C.check_html("<html><head><title>いま検証中のこと</title></head><body><main>"
                         + R.build_pane() + "</main></body></html>")
    others = [f for f in found if not (f[0] == "英字の略語" and "ADX" in f[1])]
    assert not others, others


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
