# -*- coding: utf-8 -*-
"""build_jp_rankings.py の「書かずに次の回へ委ねる」判定のテスト。2026-09-25 新設。

jp-rankings.yml を routine の push でも起動するようにした（cron が約5時間遅れていたため）ので、
起動時刻がこちらの管理外になった。場中に走っても途中の値を「終値」として書かないことを固定する。

実行:  python tests/test_build_jp_rankings.py     （pytest 不要。pytest でも動く）
"""
import datetime
import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_spec = importlib.util.spec_from_file_location("build_jp_rankings", os.path.join(ROOT, "build_jp_rankings.py"))
B = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(B)

JST = datetime.timezone(datetime.timedelta(hours=9))


def _at(hh, mm, day=25):
    return datetime.datetime(2026, 9, day, hh, mm, tzinfo=JST)


def test_unsettled_during_session():
    # 場中・大引け直後に取れた当日バーは書かない
    assert B.is_unsettled("2026-09-25", _at(11, 0))
    assert B.is_unsettled("2026-09-25", _at(15, 45))


def test_settled_after_close():
    # routine の push（17:48〜 / 19:09〜）と遅れた cron（21〜23時台）は書く
    assert not B.is_unsettled("2026-09-25", _at(16, 0))
    assert not B.is_unsettled("2026-09-25", _at(17, 50))
    assert not B.is_unsettled("2026-09-25", _at(21, 58))


def test_previous_day_bar_is_not_unsettled():
    # 朝の sns の回（07:10）は前営業日のバー＝確定済み。巻き戻しかどうかは is_regression が見る
    assert not B.is_unsettled("2026-09-24", _at(7, 10))
    assert not B.is_unsettled("", _at(11, 0))


def test_regression_guard_unchanged():
    assert B.is_regression("2026-09-24", "2026-09-25")
    assert not B.is_regression("2026-09-25", "2026-09-25")
    assert not B.is_regression("2026-09-25", "")


def test_modal_date_prefers_majority_then_newer():
    assert B.modal_date(["2026-09-25", "2026-09-25", "2026-09-24"]) == "2026-09-25"
    assert B.modal_date(["2026-09-24", "2026-09-25"]) == "2026-09-25"
    assert B.modal_date([]) == ""


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"ok   {name}")
            except AssertionError as e:
                fails += 1
                print(f"FAIL {name}: {e}")
    print(f"{'全件緑' if not fails else f'{fails}件失敗'}")
    sys.exit(1 if fails else 0)
