# -*- coding: utf-8 -*-
"""signal_lab_verify.py に 2026-09-24 に足した3検査（期間の区切り・期間ラベル・図の縮尺）のテスト。

動機＝9/22〜9/24 の3日連続停止: #106・#107・#108 がどれも verify 緑のまま Opus コンプラで🔴になり、
人待ちで公開ゼロが続いた。3つとも「直し方が機械的に決まる」誤りだったので verify で止めて
[直せる] を付け、routine が直して再実行できるようにした。ここではその判定を実例の形で固定する。

実行:  python tests/test_signal_lab_verify_checks.py     （pytest 不要。pytest でも動く）
"""
import os
import sys
import importlib.util

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location("signal_lab_verify", os.path.join(ROOT, "signal_lab_verify.py"))
V = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(V)

REG = {"rsi_oversold_edge": "2026-06-16", "auto_reversal_long-True_trend-上昇": "2026-06-22"}


def _claims(hid, *filters, labels=None):
    labels = labels or [f"c{i}" for i in range(len(filters))]
    return {"hypothesis_id": hid, "claims": [{"label": l, "filter": f, "k": 1, "n": 2} for l, f in zip(labels, filters)]}


# --- ① 期間の区切り（登録日の翌日） ------------------------------------------------------
def test_boundary_same_day_fwd_is_red():
    # #108 の型: 登録日当日（6/22）から FWD に数えていた
    c = _claims("auto_reversal_long-True_trend-上昇",
                {"trend": "上昇", "fired_before": "2026-06-22"}, {"trend": "上昇", "fired_from": "2026-06-22"})
    r = V.period_boundary_check(c, REG)
    assert len(r) == 1 and "2026-06-23" in r[0] and r[0].startswith(V.FIXABLE), r


def test_boundary_next_day_is_green():
    c = _claims("auto_reversal_long-True_trend-上昇",
                {"trend": "上昇", "fired_before": "2026-06-23"}, {"trend": "上昇", "fired_from": "2026-06-23"})
    assert V.period_boundary_check(c, REG) == []


def test_boundary_fwd_subwindow_later_is_green():
    # FWD の部分窓（前半/後半）は境界より後から始まってよい（#071 の型）
    c = _claims("rsi_oversold_edge", {"fired_from": "2026-06-17", "fired_before": "2026-08-01"},
                {"fired_from": "2026-08-01"})
    assert V.period_boundary_check(c, REG) == []


def test_boundary_is_reaching_into_forward_is_red():
    c = _claims("rsi_oversold_edge", {"fired_before": "2026-07-01"})
    r = V.period_boundary_check(c, REG)
    assert len(r) == 1 and "IS に前向きの期間が混ざる" in r[0], r


def test_boundary_needs_hypothesis_id():
    c = _claims(None, {"fired_from": "2026-06-17"})
    r = V.period_boundary_check(c, REG)
    assert len(r) == 1 and "hypothesis_id" in r[0], r


def test_boundary_no_period_keys_is_silent():
    assert V.period_boundary_check(_claims(None, {"trend": "上昇"}), REG) == []


# --- ② 期間ラベル（IS/FWD を名乗るのに期間で絞っていない＝#106 の型） ------------------------
def test_label_is_without_key_is_red():
    c = _claims(None, {"signal": "rsi_oversold_bounce"}, labels=["rsi_oversold_bounce 全体（IS）"])
    r = V.period_label_claims_check(c)
    assert len(r) == 1 and "fired_before" in r[0] and r[0].startswith(V.FIXABLE), r


def test_label_full_period_wording_is_green():
    # 過去記事で実測した正しい書き方（「全期間（IS+FWD合計）」など）は赤にしない
    for lab in ("全期間（IS+FWD合計）", "もみあい×ショート 全件（IS+FWD合算）", "IS全期間: もみあい×ショート"):
        assert V.period_label_claims_check(_claims(None, {"trend": "上昇"}, labels=[lab])) == [], lab


def test_label_with_matching_key_is_green():
    c = _claims("rsi_oversold_edge", {"fired_before": "2026-06-17"}, {"fired_from": "2026-06-17"},
                labels=["IS全体", "FWD全体"])
    assert V.period_label_claims_check(c) == []


# --- ③ 表の「IS」列に全期間の数字（限定①の撤廃） ------------------------------------------
TABLE = ("<table><tr><th>区分</th><th>IS 勝率</th><th>全件（IS+FWD）</th></tr>"
         "<tr><td>上昇</td><td>59.8%</td><td>59.8%</td></tr></table>")


def test_is_column_with_full_period_value_is_red_even_without_keys():
    # 期間キーを1つも使わない記事でも見る（#106 はここを素通りしていた）
    r = V.period_label_check(TABLE, {"IS": set(), "FWD": set(), "none": {59.8}})
    assert len(r) == 1 and "IS 勝率" in r[0], r


def test_full_period_column_is_not_a_period_column():
    t = TABLE.replace("<th>IS 勝率</th>", "<th>勝率</th>")
    assert V.period_label_check(t, {"IS": set(), "FWD": set(), "none": {59.8}}) == []


# --- ④ 図の縮尺（目盛り・基準線・棒） ---------------------------------------------------------
def _chart(line43_y, bar_scale=1.75, tick_scale=1.75):
    """0%=y210 の縦棒グラフ。#107 図2 と同じ作り（目盛り 0/20/40/60/80%・43%の基準線・棒2本）。"""
    ticks = "".join(f'<line x1="78" y1="{210 - tick_scale * v:.0f}" x2="600" y2="{210 - tick_scale * v:.0f}"/>'
                    f'<text x="72" y="{214 - tick_scale * v:.0f}" text-anchor="end">{v}%</text>' for v in (0, 20, 40, 60, 80))
    bars = "".join(f'<rect x="{x}" y="{210 - bar_scale * v:.0f}" width="90" height="{bar_scale * v:.0f}"/>'
                   f'<text x="{x + 45}" y="{205 - bar_scale * v:.0f}" text-anchor="middle">{v}%</text>'
                   for x, v in ((130, 61.9), (440, 42.9)))
    ref = (f'<line x1="80" y1="{line43_y}" x2="590" y2="{line43_y}"/>'
           f'<text x="595" y="{line43_y - 4}" text-anchor="end">43% 損益分岐</text>')
    return f'<svg viewBox="0 0 680 260">{ticks}{ref}{bars}</svg>'


def test_svg_ref_line_at_wrong_height_is_red():
    r = V.svg_scale_check(_chart(122))          # #107: 43% の線が 50% の高さ
    assert len(r) == 1 and "「43%」の線" in r[0] and r[0].startswith(V.FIXABLE), r


def test_svg_correct_chart_is_green():
    assert V.svg_scale_check(_chart(135)) == []  # y = 210 − 1.75×43 = 134.75


def test_svg_bars_on_other_scale_are_red():
    r = V.svg_scale_check(_chart(135, bar_scale=2.2))   # #106: 棒だけ別の縮尺
    assert any("「61.9%」の棒" in m for m in r), r


def test_svg_bar_value_label_is_not_taken_as_tick():
    # #089: 棒の上の「53.0%」が目盛り線の途中にあっても、目盛りの文字として扱わない
    svg = _chart(135).replace("</svg>", '<text x="300" y="118" text-anchor="middle">53.0%</text></svg>')
    assert V.svg_scale_check(svg) == []


def test_svg_two_close_lines_pair_correctly():
    # #029 の実物の座標: 40% の目盛り線（y=130）と 43% の基準線（y=123）が近い。右端の「43%」は
    # 40% の線のほうが近い（3px）が、そこに付けると「40%」が余る。1対1で組を最大にすると正しく結べる。
    lines = "".join(f'<line x1="75" y1="{y}" x2="600" y2="{y}"/>' for y in (30, 80, 130, 180, 230, 123))
    texts = ('<text x="603" y="127">43%</text>' +
             "".join(f'<text x="70" y="{y + 4}" text-anchor="end">{v}%</text>'
                     for v, y in ((80, 30), (60, 80), (40, 130), (20, 180), (0, 230))))
    ls, ts, _ = V._svg_parse(f"<svg>{lines}{texts}</svg>")
    cand = []
    for li, (x1, x2, ly) in enumerate(ls):
        for ti, (tx, ty, body) in enumerate(ts):
            if abs(ty - ly) <= V.SVG_PAIR_DY and (x1 - 60 <= tx <= x1 + V.SVG_END_DX or x2 - V.SVG_END_DX <= tx <= x2 + 60):
                cand.append((li, ti, abs(ty - ly), float(body.rstrip("%")), ly))
    got = {v: ly for _li, _ti, _d, v, ly in V._svg_match(cand)}
    assert got[43.0] == 123 and got[40.0] == 130, got


def test_svg_concept_figure_is_ignored():
    svg = '<svg viewBox="0 0 400 200"><polyline points="0,0 10,10"/><text x="10" y="20">上昇トレンド</text></svg>'
    assert V.svg_scale_check(svg) == []


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
