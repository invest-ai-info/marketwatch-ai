# -*- coding: utf-8 -*-
"""「数字で見る、話題の企業」の候補の並べ方（build_edinet_yuho.pick_candidates）のテスト。2026-10-04 新設。

旧版は「回数の多い順・同じ回数なら最近載った順」の上位15社だけを候補にしたため、話題の真っ最中の会社
ばかりが残り、ルーティンが手順書の「中3営業日」で全部はじいて日本株が全滅した（10/3。条件を満たす会社は23社あった）。
毎日1本以上（2026-10-04 オーナー指示）にするにあたり、
  - 熱が冷めた会社（直近3回のランキング日に載っていない）を先に並べる
  - cooled / last_seen を候補に付ける（ルーティンが営業日を数え直さない＝9/26 の連休の数え間違いの再発防止）
  - 本レーンで90日以内に書いた会社は入れない
をここで固定する。

実行:  python tests/test_company_candidates.py     （pytest 不要。pytest でも動く）
"""
import datetime
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import build_edinet_yuho as B  # noqa: E402


def _ap(**codes):
    """code=日付のリスト から appearances を作る。"""
    return {c: {"name": c, "dates": {d: "hot" for d in ds}} for c, ds in codes.items()}


# ランキングがあった日（東証の営業日）。9/21〜23 は連休でランキングが無い
DAYS = ["2026-09-17", "2026-09-18", "2026-09-24", "2026-09-25"]


def test_cooled_first_even_with_fewer_appearances():
    ap = _ap(HOT6=["2026-09-17", "2026-09-18", "2026-09-24", "2026-09-25"],   # 最終 9/25＝熱い
             COOL2=["2026-09-16", "2026-09-17"])                              # 最終 9/17＝冷めた
    c = B.pick_candidates(ap, {})
    assert [x["code"] for x in c] == ["COOL2", "HOT6"], c
    assert c[0]["cooled"] is True and c[1]["cooled"] is False
    assert c[0]["last_seen"] == "2026-09-17"


def test_holiday_counted_by_ranking_days_not_weekdays():
    # 9/26 の実例: 最終 9/18 の会社は、曜日だけで数えると中3営業日を満たして見えるが、
    # 連休でランキングが無い日を除くと 9/24・9/25 の2営業日しかあいていない＝まだ熱い
    ap = _ap(K6525=["2026-09-17", "2026-09-18"], F3563=["2026-09-16", "2026-09-17"],
             X=["2026-09-24", "2026-09-25"])
    c = {x["code"]: x for x in B.pick_candidates(ap, {})}
    assert c["K6525"]["cooled"] is False, c["K6525"]
    assert c["F3563"]["cooled"] is True, c["F3563"]


def test_recently_covered_companies_are_excluded():
    ap = _ap(A3563=["2026-09-10", "2026-09-11"], B4588=["2026-09-10", "2026-09-11"])
    c = B.pick_candidates(ap, {}, covered={"A3563"})
    assert [x["code"] for x in c] == ["B4588"], c


def test_single_appearance_is_not_a_candidate_and_fallback_still_works():
    ap = _ap(ONE=["2026-09-25"])
    c = B.pick_candidates(ap, {"asof": "2026-09-25", "hot": [{"code": "9999", "name": "x"}]})
    assert len(c) == 1 and c[0]["fallback"] is True and c[0]["cooled"] is False, c


def test_max_candidates_keeps_cooled_ones():
    ap = {}
    for i in range(30):   # 30社が熱い（回数が多い）
        ap[f"H{i:02d}"] = {"name": "h", "dates": {d: "hot" for d in DAYS}}
    for i in range(5):    # 5社が冷めている（回数は少ない）
        ap[f"C{i}"] = {"name": "c", "dates": {"2026-09-10": "hot", "2026-09-11": "hot"}}
    c = B.pick_candidates(ap, {})
    assert len(c) == B.MAX_CANDIDATES
    assert [x["code"] for x in c[:5]] == ["C4", "C3", "C2", "C1", "C0"] or all(x["cooled"] for x in c[:5])
    assert sum(x["cooled"] for x in c) == 5


def test_covered_codes_reads_date_published_within_90_days():
    tmp = tempfile.mkdtemp()
    try:
        def page(name, date):
            with open(os.path.join(tmp, name), "w", encoding="utf-8") as f:
                f.write(f'<script type="application/ld+json">{{"datePublished": "{date}"}}</script>')
        page("guide-company-3563-foodandlife.html", "2026-09-26")
        page("guide-company-285a-kioxia.html", "2026-08-01")
        page("guide-company-7203-toyota.html", "2026-05-01")     # 90日より前
        got = B.covered_codes(datetime.date(2026, 10, 4), root=tmp)
        assert got == {"3563", "285A"}, got
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


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
