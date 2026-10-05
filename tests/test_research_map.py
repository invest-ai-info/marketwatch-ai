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
    html = G.build_html(sig, G.load_json(G.TRACKER_FILE) or None)
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
    wall |= set((json.load(open(R.STOP_LAB, encoding="utf-8")).get("forward") or {}))   # 損切りラボ（4h|mr|A30 など）
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



def _dump(d, name, obj):
    with open(os.path.join(d, name), "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False)


def test_study_lists_read_forward_records_and_drop_judged():
    # 2026-10-01 オーナー「今進めている研究はすべて…研究中一覧、検証中一覧に簡潔に短くまとめて」
    d = tempfile.mkdtemp()
    _dump(d, R.YORI_FWD, {"fwd_start": "2026-09-29", "goal": 1000, "titles": {"F1": "a", "F2": "b"}, "verdicts": {},
                          "trades": [{"c": "F1"}, {"c": "F1"}]})
    _dump(d, R.COMBO_FWD, {"result": {"now": {"n": 3}, "checkpoints": {}}})
    paused = R._ea_paused
    R._ea_paused = lambda root=".": None                                            # 動いているときの表示を確かめる
    try:
        head = R.build_pane(root=d).split("① 定期的に回している研究")[0]
    finally:
        R._ea_paused = paused
    assert "📋 研究中・検証中の一覧" in head and "🧪 検証中" in head and "🔬 研究中" in head
    assert "形1 2回・形2 0回（それぞれ1000回で1回だけ判定）" in head and "3件（次の区切りは50件" in head
    assert "10月31日までに届いた合図を数え、11月8日以降に1回だけ判定" in head   # 記録ができる前から載る
    assert "株主優待" not in head                                                  # データ集めのフォルダが無ければ出さない
    assert "手元だけで進めている研究があります" in head
    for private in ("見張り番", "5分足", "取引の記録から", "MT5", "AT3", "J4F"):   # 個人の取引・記号は出さない
        assert private not in head, private
    # 判定が出たら一覧から外れる
    _dump(d, R.YORI_FWD, {"fwd_start": "2026-09-29", "goal": 1000, "titles": {"F1": "a"}, "verdicts": {"F1": {"status": "stop"}}, "trades": []})
    _dump(d, R.AUTO_FWD, {"kind": "forward", "cut_end": "2026-10-31", "decide_on": "2026-11-08", "summary": {"n": 30},
                          "verdicts": {"AT3": {"status": "stop"}}})
    _dump(d, R.COMBO_FWD, {"result": {"now": {"n": 150}, "checkpoints": {"50": {}, "100": {}, "150": {}}}})
    os.makedirs(os.path.join(d, R.YUTAI_DIR))
    head = R.build_pane(root=d).split("① 定期的に回している研究")[0]
    assert "寄り付き" not in head and "練習用の口座" not in head and "向きだけ残った" not in head
    assert "株主優待のある銘柄の値動き" in head


def test_study_list_shows_progress_from_the_ea_record():
    d = tempfile.mkdtemp()
    _dump(d, R.AUTO_FWD, {"kind": "forward", "fwd_start": "2026-10-01", "cut_end": "2026-10-31", "decide_on": "2026-11-08",
                          "summary": {"n": 12}, "verdicts": {}})
    paused = R._ea_paused
    R._ea_paused = lambda root=".": None
    try:
        assert "12回（10月31日までに届いた合図を数え、11月8日以降に1回だけ判定）" in R.build_pane(root=d)
    finally:
        R._ea_paused = paused
    assert R._ea_dates(ROOT) == ("2026-10-01", "2026-10-31", "2026-11-08")       # ea_ledger.py の決まりと同じ日


def test_paused_ea_study_is_not_shown_as_ongoing():
    # 2026-10-01 夜 オーナー決定で自動で建てる検証は止めている＝「検証中」に出さない（ea_ledger.py の PAUSED_SINCE が単一の真実）
    assert R._ea_paused(ROOT) == "2026-10-01"
    d = tempfile.mkdtemp()
    _dump(d, R.AUTO_FWD, {"kind": "forward", "summary": {"n": 3}, "verdicts": {}})
    assert "練習用の口座" not in R.build_pane(root=d)


def test_month_turn_forward_is_listed_until_both_are_stopped():
    d = tempfile.mkdtemp()
    head = R.build_pane(root=d).split("① 定期的に回している研究")[0]
    assert "株価指数の月末月初（米国・日本）" in head and "2026-10-06 から" in head      # 記録ができる前から載る
    assert "米国 0回・日本 0回" in head and "最初の記録は11月上旬" in head
    _dump(d, R.CAL_FWD, {"section": "R3F", "fwd_start": "2026-10-06", "goal": 36, "verdicts": {"Q3": {"status": "stop"}},
                         "trades": [{"c": "Q1"}, {"c": "Q1"}, {"c": "Q3"}]})
    head = R.build_pane(root=d).split("① 定期的に回している研究")[0]
    assert "株価指数の月末月初（米国）" in head and "米国 2回" in head and "日本" not in head.split("株価指数の月末月初")[1][:40]
    assert "最初の記録は" not in head
    _dump(d, R.CAL_FWD, {"section": "R3F", "fwd_start": "2026-10-06", "goal": 36,
                         "verdicts": {"Q1": {"status": "stop"}, "Q3": {"status": "stop"}}, "trades": []})
    assert "株価指数の月末月初" not in R.build_pane(root=d)


# ── トップの「このサイトがしていること」の帯・はじめての方へ・ナビの名前（2026-09-26 オーナー判断「研究を主軸に」）
def test_research_band_counts_published_journal_and_picks_latest():
    import glob
    import re
    import generate_market_news as M
    n, latest = M._latest_signal_lab()
    pub = []
    for p in glob.glob("guide-signal-lab-*.html"):
        mm = re.match(r"guide-signal-lab-(\d+)\.html$", p)
        if mm and '<meta name="robots" content="noindex' not in open(p, encoding="utf-8").read():
            pub.append((int(mm.group(1)), p))
    assert n == len(pub) and latest[0] == max(pub)[1]
    band = M.build_research_band()
    assert 'href="track-record.html#map"' in band and 'href="guide-how-we-research.html"' in band
    assert "勝率" not in band                      # トップに成績の数字は出さない（法務チェック）


def test_research_band_never_breaks_the_top_page():
    import generate_market_news as M
    orig = R.collect

    def boom(*a, **k):
        raise RuntimeError("壊れた")
    R.collect = boom
    try:
        assert M.build_research_band() == ""
    finally:
        R.collect = orig


def test_start_page_is_linked_ad_free_and_plain():
    import inject_ads as I
    name = "guide-how-we-research.html"
    assert name in I.DENY_EXACT
    assert f'href="{name}"' in open("guides.html", encoding="utf-8").read()
    assert f'href="{name}"' in R.build_pane()
    page = open(name, encoding="utf-8").read()
    assert page.count('data-disclaimer="kinsho-v1"') >= 3
    assert not C.check_html(page), C.check_html(page)


def test_nav_label_for_track_record_is_the_same_everywhere():
    # ナビの名前の単一の真実は apply_site_frame.NAV_BUTTONS。生成スクリプトのナビも同じ名前であること
    import glob
    import re
    import apply_site_frame as F
    label = dict(F.NAV_BUTTONS)["track-record.html"]
    bad = []
    for p in glob.glob("*.py") + ["guides.html", "about.html", "contact.html", "privacy.html", "holdings.html"]:
        for m in re.finditer(r'<a class="nav-btn(?: current)?" href="track-record\.html">([^<]*)</a>',
                             open(p, encoding="utf-8").read()):
            if m.group(1) != label:
                bad.append((p, m.group(1)))
    assert not bad, bad


def test_top_band_title_never_shows_win_rates():
    # 法務チェック（2026-09-26 グレー1）: トップ（広告のあるページ）に研究日誌の題名の勝率を出さない
    import re
    import generate_market_news as M
    cases = {
        "4時間足だけ63.9%で優位？ 時間足の比較【研究日誌 #086】": "研究日誌 #086",
        "株価指数68.6%から38.8%に急落【研究日誌 #100】": "研究日誌 #100",
        "ゴールデンクロスは買いの合図？ 勝率の比較【研究日誌 #008】": "ゴールデンクロスは買いの合図？【研究日誌 #008】",
    }
    for title, want in cases.items():
        assert M.research_band_title(title) == want, (title, M.research_band_title(title))
    import glob
    for p in glob.glob("guide-signal-lab-*.html"):
        t = re.search(r"<title>(.*?)</title>", open(p, encoding="utf-8").read(), re.S)
        if t:
            shown = M.research_band_title(t.group(1), p)
            assert not re.search(r"\d+(?:\.\d+)?\s*[%％]|勝率|ポイント", shown), (p, shown)


def test_track_record_hides_ai_lessons_and_repeatability():
    # 法務チェック（2026-09-26 黒）: AI が書いた「教訓」「再現性」は公開ページに出さない（データは残す）
    sig = [s for s in G.load_json(G.SIGNALS_LOG_FILE) if not G.is_weekend_closed_fire(s)]
    pane = G.build_outcome_analysis_section(sig)
    for w in ("教訓", "再現性", "積極的", "サイズアップ"):
        assert w not in pane, w

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
