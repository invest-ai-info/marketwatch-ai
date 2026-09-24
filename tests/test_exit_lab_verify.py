# -*- coding: utf-8 -*-
"""exit_lab_verify.py（研究日誌「出口の相性」回の数字の照合）のテスト。2026-09-24 新設。

正しい下書きは緑、数字の取り違え・出どころの無い数字・良い組だけを並べる・「この出口が合う／おすすめ」・
断り書きの欠け・exit-lab.json の版違い、はどれも赤（[直せる]）になることを固定する。

実行:  python tests/test_exit_lab_verify.py     （pytest 不要。pytest でも動く）
"""
import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_spec = importlib.util.spec_from_file_location("exit_lab_verify", os.path.join(ROOT, "exit_lab_verify.py"))
V = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(V)


def _cell(sl, tp, avg, vs=None, n=1000, win=0.4, flag=False):
    c = {"tf": "1d", "entry": "bb_lower_touch", "side": "long", "sl": sl, "tp": tp, "period": "is",
         "n_entries": 4105, "n": n, "avg": avg, "lo": avg - 0.1, "hi": avg + 0.1, "win": win, "flag": flag,
         "risk_atr_median": 1.5}
    if vs is not None:
        c["vs_base"] = {"n": n, "avg": vs, "lo": vs - 0.08, "hi": vs + 0.08}
    return c


LAB = {"asof": "2026-09-27", "cells": [
    _cell("atr", "atr2", -0.06),
    _cell("atr", "none", 0.21, vs=0.27),
    _cell("chandelier", "atr2", -0.45, vs=-0.25, flag=True),
    _cell("swing", "swing", 0.0, vs=0.06),
]}

GOOD_CLAIMS = {"article_id": "110", "exit_lab_asof": "2026-09-27", "claims": [
    {"label": "いまの方式", "tf": "1d", "entry": "bb_lower_touch", "side": "long", "sl": "atr", "tp": "atr2",
     "period": "is", "field": "avg", "value": -0.06},
    {"label": "利確なし", "tf": "1d", "entry": "bb_lower_touch", "side": "long", "sl": "atr", "tp": "none",
     "period": "is", "field": "vs_base", "value": 0.27},
    {"label": "シャンデリア", "tf": "1d", "entry": "bb_lower_touch", "side": "long", "sl": "chandelier", "tp": "atr2",
     "period": "is", "field": "vs_base", "value": -0.25},
    {"label": "シャンデリアは目立つ", "tf": "1d", "entry": "bb_lower_touch", "side": "long", "sl": "chandelier",
     "tp": "atr2", "period": "is", "field": "flag", "value": True},
    {"label": "入口の数", "tf": "1d", "entry": "bb_lower_touch", "side": "long", "sl": "atr", "tp": "atr2",
     "period": "is", "field": "n_entries", "value": 4105},
]}

GOOD_HTML = """<html><head><title>t</title></head><body>
<div class="info-box">30秒でわかる: −2σタッチの買い 4,105件で、いまの方式は平均 -0.06R。
利確を置かない組は、いまの方式より +0.27R 上、シャンデリア型の損切りは -0.25R 下で、目立つ組でした。</div>
<p>1R は損切り幅。差が 0.15R 以上で目立つと呼びます。組み合わせが多いので、偶然で良く見える組も出ます。
2026-09-25 以降の前向きのシグナルで確かめます。安値−0.3ATR に損切り。</p>
<svg viewBox="0 0 100 50"><text x="1" y="10">+0.2</text><text x="1" y="40">-0.2</text><text x="50" y="20">+0.27</text></svg>
<div class="meta-line" data-mw-tracker-legend>表の見方</div><table><tr><td>平均R +0.04 CI[-0.02~+0.09]（1581/3564・勝率44%）</td></tr></table>
<p class="disclaimer" data-disclaimer="kinsho-v1">売買推奨ではありません。将来の成果を保証するものではありません。</p>
</body></html>"""


def run(html, claims, lab=LAB, extra=None):
    with tempfile.TemporaryDirectory() as d:
        hp, cp, lp = (os.path.join(d, n) for n in ("draft.html", "claims.json", "exit-lab.json"))
        open(hp, "w", encoding="utf-8").write(html)
        json.dump(claims, open(cp, "w", encoding="utf-8"), ensure_ascii=False)
        json.dump(lab, open(lp, "w", encoding="utf-8"), ensure_ascii=False)
        old, V.LAB_PATH = V.LAB_PATH, lp
        argv, sys.argv = sys.argv, ["exit_lab_verify.py", hp, cp] + (extra or [])
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                V.main()
            code = 0
        except SystemExit as e:
            code = e.code
        finally:
            V.LAB_PATH, sys.argv = old, argv
        return code, buf.getvalue()


def test_good_draft_is_green():
    code, out = run(GOOD_HTML, GOOD_CLAIMS)
    assert code == 0, out


def test_wrong_value_is_red():
    c = json.loads(json.dumps(GOOD_CLAIMS))
    c["claims"][1]["value"] = 0.37
    code, out = run(GOOD_HTML.replace("+0.27R", "+0.37R").replace(">+0.27<", ">+0.37<"), c)
    assert code == 1 and "0.37" in out and V.FIXABLE in out, out


def test_unbacked_number_in_text_is_red():
    code, out = run(GOOD_HTML.replace("目立つ組でした。", "目立つ組でした。半分利確は +0.44R でした。"), GOOD_CLAIMS)
    assert code == 1 and "出どころの無い数字" in out and "0.44" in out, out


def test_unbacked_count_is_red():
    code, out = run(GOOD_HTML.replace("4,105件", "5,000件"), GOOD_CLAIMS)
    assert code == 1 and "5000" in out, out


def test_only_good_combos_is_red():
    c = json.loads(json.dumps(GOOD_CLAIMS))
    c["claims"] = [x for x in c["claims"] if x["sl"] != "chandelier"]
    html = GOOD_HTML.replace("シャンデリア型の損切りは -0.25R 下で、目立つ組でした。", "").replace(
        '<text x="50" y="20">+0.27</text>', '<text x="50" y="20">+0.27</text>')
    code, out = run(html.replace("目立つ", "大きい"), c)
    assert code == 1 and "片側だけ" in out, out


def test_banned_wording_is_red():
    for w in ("この入口には利確なしが合う", "利確なしがおすすめです", "相性が良い組み合わせです", "この出口を使うべきです"):
        code, out = run(GOOD_HTML.replace("目立つ組でした。", "目立つ組でした。" + w + "。"), GOOD_CLAIMS)
        assert code == 1 and "言い方" in out, (w, out)


def test_disclaimer_negation_is_not_banned():
    code, out = run(GOOD_HTML, GOOD_CLAIMS)
    assert code == 0 and "言い方「" not in out, out


def test_missing_caveat_is_red():
    code, out = run(GOOD_HTML.replace("偶然で良く見える組も出ます。", ""), GOOD_CLAIMS)
    assert code == 1 and "偶然" in out, out


def test_medatsu_needs_flag_claim():
    c = json.loads(json.dumps(GOOD_CLAIMS))
    c["claims"] = [x for x in c["claims"] if x["field"] != "flag"]
    code, out = run(GOOD_HTML, c)
    assert code == 1 and "flag" in out, out


def test_wrong_asof_is_fixable_red():
    c = dict(GOOD_CLAIMS, exit_lab_asof="2026-09-20")
    code, out = run(GOOD_HTML, c)
    assert code == 1 and V.FIXABLE in out and "2026-09-27" in out, out


def test_svg_ticks_allowed_but_svg_values_checked():
    code, out = run(GOOD_HTML.replace(">+0.27<", ">+0.31<"), GOOD_CLAIMS)
    assert code == 1 and "0.31" in out, out


def test_signal_claims_numbers_are_allowed():
    html = GOOD_HTML.replace("目立つ組でした。", "目立つ組でした。エンジンの記録では 150/324 勝ち（46.3%・幅 40.9%〜51.7%）、324件。")
    with tempfile.TemporaryDirectory() as d:
        sp = os.path.join(d, "sig.json")
        json.dump({"claims": [{"label": "x", "filter": {}, "k": 150, "n": 324}]}, open(sp, "w", encoding="utf-8"))
        code, out = run(html, GOOD_CLAIMS, extra=["--signal-claims", sp])
    assert code == 0, out
    code, out = run(html, GOOD_CLAIMS)
    assert code == 1 and "46.3" in out, out


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"✅ {name}")
            except AssertionError as e:
                fails += 1
                print(f"❌ {name}\n{e}")
    print("すべて期待どおり" if not fails else f"{fails}件 失敗")
    sys.exit(1 if fails else 0)
