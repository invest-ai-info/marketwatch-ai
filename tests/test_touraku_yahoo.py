# -*- coding: utf-8 -*-
"""騰落レシオを J-Quants から Yahoo の日足に替えたこと（2026-11-20）の回帰テスト。

守っていること:
  ・上げ下げの数え方（営業日の決め方・前の営業日に足の無い銘柄は数えない・asof より後は数えない）
  ・旧版の J-Quants の数のファイル（source が違う）は、読む側が空として扱う＝J-Quants から来た数は表に出ない
  ・健康度の履歴の騰落の系列は、前の点と混ぜずに置き換える（J-Quants の数の点を残さない）
  ・GitHub 側で J-Quants を呼ばない（ワークフローに鍵が無い・jp-highs.yml が新しいファイルをコミットする）

実行: python -m pytest -q tests/test_touraku_yahoo.py
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import build_touraku_history as T  # noqa: E402
import build_health_history as BH  # noqa: E402


def _read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


def _bars(closes, start=1):
    """[(日付, 高, 安, 終, 出来高)]。日付は 2026-06-01 から1日ずつ（None の日は足が無い）。"""
    out = []
    for i, c in enumerate(closes):
        if c is not None:
            out.append((f"2026-06-{start + i:02d}", c, c, c, 1000.0))
    return out


# ── 数え方 ─────────────────────────────────────────

def test_points_from_bars_counts_up_and_down():
    bars = {"A": _bars([100, 101, 102]), "B": _bars([100, 99, 99]), "C": _bars([100, 100, 103])}
    assert T.points_from_bars(bars) == [["2026-06-02", 1, 1], ["2026-06-03", 2, 0]]


def test_stock_without_bar_on_previous_trading_day_is_not_counted():
    # D は 6/2 に売買が無い＝6/3 は前の営業日の終値が無いので数えない（旧版の J-Quants と同じ）
    bars = {"A": _bars([100, 101, 102]), "B": _bars([100, 99, 98]), "D": _bars([100, None, 150])}
    assert T.points_from_bars(bars) == [["2026-06-02", 1, 1], ["2026-06-03", 1, 1]]


def test_day_with_few_bars_is_not_a_trading_day():
    # 6/4 は1銘柄だけに足がある（Yahoo がまれに休みの日に出す足）＝営業日と見なさない
    bars = {"A": _bars([100, 101, 102, 103]), "B": _bars([100, 99, 98]), "C": _bars([100, 99, 97])}
    pts = T.points_from_bars(bars)
    assert [p[0] for p in pts] == ["2026-06-02", "2026-06-03"]


def test_days_after_asof_are_not_counted():
    bars = {"A": _bars([100, 101, 102]), "B": _bars([100, 99, 98])}
    assert T.points_from_bars(bars, asof="2026-06-02") == [["2026-06-02", 1, 1]]


def test_ratio25_needs_the_full_window():
    pts = [[f"d{i}", 10, 5] for i in range(25)]
    assert T.ratio25(pts[:24]) is None and T.ratio25(pts) == 200.0
    assert T.ratio25([[f"z{i}", 10, 0] for i in range(25)]) is None


# ── 読み書き（旧版の J-Quants の数は読まない） ─────────────────────

def test_old_jquants_file_is_read_as_empty(tmp_path):
    old = tmp_path / "touraku-history.json"
    old.write_text(json.dumps({"updated_at": "2026-11-20", "points": [["2026-11-20", 90, 1443]],
                               "health": {"last_ok": "2026-11-20"}}), encoding="utf-8")   # 旧版＝source が無い
    assert T.load_points(str(old)) == []
    assert not T.is_current(str(old), "2026-11-20")
    old.write_text(json.dumps({"source": "jquants", "points": [["2026-11-20", 1, 2]]}), encoding="utf-8")
    assert T.load_points(str(old)) == []


def test_update_from_bars_replaces_and_needs_25_days(tmp_path):
    path = str(tmp_path / "touraku-history.json")
    few = {"A": _bars([100 + i for i in range(10)]), "B": _bars([100 - i for i in range(10)])}
    assert "書かない" in T.update_from_bars(few, "2026-06-10", path=path)
    assert not os.path.exists(path)                       # 窓に届かない回は書かない（良いファイルを壊さない）
    import datetime as dt
    bars = {}
    for k in range(4):
        cs = [100 + ((i * (k + 1)) % 7) for i in range(30)]
        bars[str(k)] = [(f"2026-{6 + i // 28:02d}-{i % 28 + 1:02d}", c, c, c, 1.0) for i, c in enumerate(cs)]
    msg = T.update_from_bars(bars, "2026-07-02", path=path, now=dt.datetime(2026, 7, 2, 20, tzinfo=T.JST))
    doc = json.load(open(path, encoding="utf-8"))
    assert doc["source"] == T.SOURCE and doc["updated_at"] == "2026-07-02"
    assert doc["points"] == T.points_from_bars(bars, "2026-07-02")[-T.KEEP_POINTS:]
    assert doc["health"]["last_ok"] == doc["points"][-1][0] and "25日騰落レシオ" in msg
    assert T.is_current(path, doc["points"][-1][0])
    assert T.load_points(path) == doc["points"]


# ── 健康度の履歴・健康度ページ ─────────────────────────────

def test_health_series_is_replaced_not_merged():
    doc = BH.empty_history()
    doc["series"]["touraku_ratio"]["points"] = [["2026-06-03", 97.0], ["2026-11-20", 84.4]]   # 旧版の J-Quants の点
    doc = BH.collect(doc, {"touraku_ratio": lambda: [["2026-11-19", 101.0], ["2026-11-20", 99.5]]}, "2026-11-20")
    assert doc["series"]["touraku_ratio"]["points"] == [["2026-11-19", 101.0], ["2026-11-20", 99.5]]
    doc = BH.collect(doc, {"touraku_ratio": lambda: []}, "2026-11-21")       # 元が旧版のまま＝空
    assert doc["series"]["touraku_ratio"]["points"] == []
    # ほかの系列は今までどおり混ぜる
    doc["series"]["vix"]["points"] = [["2026-11-18", 17.0]]
    doc = BH.collect(doc, {"vix": lambda: [["2026-11-19", 18.0]]}, "2026-11-21")
    assert doc["series"]["vix"]["points"] == [["2026-11-18", 17.0], ["2026-11-19", 18.0]]


def test_health_series_reads_only_yahoo_file(tmp_path):
    p = tmp_path / "t.json"
    pts = [[f"2026-06-{i + 1:02d}", 10 + i, 5] for i in range(30)]
    p.write_text(json.dumps({"points": pts}), encoding="utf-8")                       # 旧版（source なし）
    assert BH.fetch_touraku_ratio_series(path=str(p)) == []
    p.write_text(json.dumps({"source": T.SOURCE, "points": pts}), encoding="utf-8")
    s = BH.fetch_touraku_ratio_series(path=str(p))
    assert len(s) == 30 - T.RATIO_WINDOW + 1 and s[-1] == [pts[-1][0], T.ratio25(pts)]


def test_no_jquants_on_the_public_side():
    meta = BH.SERIES_META["touraku_ratio"]
    assert "J-Quants" not in meta["source"] and "JQUANTS" not in meta["pending_hint"]
    assert "Yahoo" in meta["source"]
    gen = _read("generate_market_news.py")
    assert "_touraku_load_points(hist_path)" in gen and "J-Quants集計" not in gen
    assert "api.jquants.com" not in _read("build_touraku_history.py")
    umn = _read(os.path.join(".github", "workflows", "update-market-news.yml"))
    assert "secrets.JQUANTS_API_KEY" not in umn and "python build_touraku_history.py" not in umn
    assert "git add touraku-history.json" in _read(os.path.join(".github", "workflows", "jp-highs.yml"))


# ── 赤字・黒字の印（B） ─────────────────────────────────

def test_no_akaji_in_public_outputs():
    info = json.load(open(os.path.join(ROOT, "jp-stock-info.json"), encoding="utf-8"))
    assert all("akaji" not in v for v in info["stocks"].values())
    assert '"akaji"' not in _read("build_jp_rankings.py").split('"""', 2)[2]
    gen = _read("generate_market_news.py")
    assert "jpr-fin" not in gen and "決算アイコン" not in gen and 'aria-label="赤字"' not in gen
