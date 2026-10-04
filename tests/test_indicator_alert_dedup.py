# -*- coding: utf-8 -*-
"""発表前アラート（「まもなく」メール）の範囲と「1発表1通」のテスト。2026-10-04 新設。

毎時の cron が GitHub に間引かれ1日4〜5回しか動かず、10/2 の米雇用統計の「まもなく」が
届かなかった。ワークフローを他のワークフローの完了に相乗りさせて1日数十回動かすので、
  - 範囲（15〜120分前）に入った最初の回で送る
  - 同じ発表には2通送らない（--sent-file の記録）
  - 記録は発表から時間が経ったら捨てる
をここで固定する。

実行:  python tests/test_indicator_alert_dedup.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import send_indicator_digest as S  # noqa: E402

JST = S.JST
NFP = {"name": "米雇用統計 NFP（9月分）", "datetime": "2026-10-02T21:30:00+09:00",
       "category": "indicator", "affected_assets": ["all"]}
HICP = {"name": "ユーロ圏HICP速報（9月分）", "datetime": "2026-10-02T18:00:00+09:00",
        "category": "indicator", "affected_assets": ["EURUSD=X"]}


class _Events:
    """S.EVENTS を一時ファイルに差し替える。"""
    def __init__(self, events):
        fd, self.path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        json.dump({"events": events}, open(self.path, "w", encoding="utf-8"), ensure_ascii=False)

    def __enter__(self):
        self.old, S.EVENTS = S.EVENTS, self.path
        return self

    def __exit__(self, *a):
        S.EVENTS = self.old
        os.remove(self.path)


def _at(h, m):
    return dt.datetime(2026, 10, 2, h, m, tzinfo=JST)


def test_window_is_15_to_120_minutes():
    with _Events([NFP]):
        assert S.build_alert(_at(19, 29))[0] is None        # 121分前＝まだ
        assert S.build_alert(_at(19, 30))[0]                # 120分前＝送る
        assert S.build_alert(_at(21, 15))[0]                # 15分前＝まだ送る
        assert S.build_alert(_at(21, 16))[0] is None        # 14分前＝もう送らない


def test_10_02_nfp_is_now_covered():
    # 10/2 は 17:24 の次の実行が 0:44 で、旧範囲（45〜105分前）に1回も入らなかった。
    # 相乗りで 20 時台に1回でも動けば届く
    with _Events([NFP]):
        subj, body = S.build_alert(_at(20, 2))
        assert subj and "米雇用統計" in subj and "あと88分" in subj


def test_same_release_is_sent_only_once():
    with _Events([NFP]):
        now = _at(19, 40)
        key = S.event_key(dt.datetime.fromisoformat(NFP["datetime"]), NFP)
        assert [S.event_key(w, e) for w, e in S.alert_targets(now)] == [key]
        sent = {key: "2026-10-02T19:40+09:00"}
        assert S.build_alert(_at(20, 30), sent)[0] is None   # 2回目の回では送らない


def test_other_release_still_alerted_after_first_is_sent():
    with _Events([HICP, NFP]):
        hicp_key = S.event_key(dt.datetime.fromisoformat(HICP["datetime"]), HICP)
        sent = {hicp_key: "2026-10-02T16:10+09:00"}
        subj, _ = S.build_alert(_at(19, 45), sent)
        assert subj and "米雇用統計" in subj


def test_sent_file_round_trip_and_pruning():
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        old = "2026-09-30T21:30|古い発表"
        new = "2026-10-02T21:30|米雇用統計 NFP（9月分）"
        S.save_sent(path, {old: "x", new: "y"})
        got = S.load_sent(path, _at(22, 0))
        assert new in got and old not in got, got    # 発表から36時間を過ぎた記録は捨てる
    finally:
        os.remove(path)


def test_missing_or_broken_sent_file_means_empty():
    assert S.load_sent(None, _at(20, 0)) == {}
    assert S.load_sent("/nonexistent/x.json", _at(20, 0)) == {}
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        open(path, "w").write("{broken")
        assert S.load_sent(path, _at(20, 0)) == {}
    finally:
        os.remove(path)


def test_workflow_is_chained_and_names_match():
    import re
    wf = open(os.path.join(ROOT, ".github", "workflows", "indicator-alert.yml"), encoding="utf-8").read()
    names = re.findall(r'^\s+- "([^"]+)"', wf, re.M)
    assert len(names) >= 4, names
    actual = set()
    for f in os.listdir(os.path.join(ROOT, ".github", "workflows")):
        if f.endswith((".yml", ".yaml")):
            m = re.search(r"^name:\s*(.+)$", open(os.path.join(ROOT, ".github", "workflows", f),
                                                  encoding="utf-8").read(), re.M)
            if m:
                actual.add(m.group(1).strip().strip('"\''))
    missing = [n for n in names if n not in actual]
    assert not missing, f"相乗り先の name が見つからない（ずれると黙って起動しない）: {missing}"
    assert "--sent-file" in wf and "concurrency" in wf


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
