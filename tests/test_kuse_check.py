# -*- coding: utf-8 -*-
"""投資のクセ診断（guide-kuse-check.html）のテスト。2026-09-27 新設。

確かめること＝①17問がそろっていて、計算の順番（KEYS）と一致する ②広告を置かない（本文で約束している）
③免責の三層 ④全国調査の数字と引用の書き方（J-FLEC の転載の決まり＝出典・データ名の明記）
⑤答えを外へ出さない（送信・保存の仕組みが計算の部分に無い）⑥判定の決まり（node があれば実際に計算して確かめる）。

実行:  python tests/test_kuse_check.py     （pytest 不要。pytest でも動く）
"""
import json
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
PAGE = "guide-kuse-check.html"


def _html():
    return open(PAGE, encoding="utf-8").read()


def _logic():
    return _html().split("/* KUSE-LOGIC-START */")[1].split("/* KUSE-LOGIC-END */")[0]


def test_17_questions_in_the_order_of_the_logic():
    names = re.findall(r'<fieldset class="kq-q" data-q="(\w+)"', _html())
    keys = json.loads(re.search(r"var KEYS = (\[[^\]]*\])", _logic()).group(1).replace("'", '"'))
    assert len(names) == 17 and names == keys


def test_no_ads_and_three_disclaimers():
    h = _html()
    assert 'class="mw-ad"' not in h and "mw-ads.js" not in h and "adsbygoogle" not in h
    assert h.count('data-disclaimer="kinsho-v1"') >= 3
    import inject_ads
    assert PAGE in inject_ads.DENY_EXACT                 # 毎回の update-market-news で広告が差し込まれない


def test_national_numbers_and_citation():
    h, lg = _html(), _logic()
    assert "金融経済教育推進機構「金融リテラシー調査」（2025年）" in h
    for n in ("72.8", "62.9", "82.4", "45.5", "17.0", "13.4", "6.8", "8.4", "10.8"):
        assert n in h, n
    for k in ("q1", "q2", "q3", "q4"):
        pct = json.loads(re.search(k + r": \{labels: \[[^\]]*\], pct: (\[[^\]]*\])", lg).group(1))
        assert abs(sum(pct) - 100) < 0.15, (k, sum(pct))
    assert "nat: 55.2" in lg and "nat: 47.8" in lg


def test_answers_never_leave_the_page():
    lg = _logic()
    for bad in ("fetch(", "XMLHttpRequest", "sendBeacon", "localStorage", "sessionStorage", "document.cookie"):
        assert bad not in lg, bad
    assert "どこにも送りません" in _html()


def test_no_promise_of_fit_or_accuracy():
    h = _html()
    for bad in ("向いている投資がわかる", "あなたに合う投資", "正確にわかる", "タイプ診断"):
        assert bad not in h, bad
    assert "向いている、という意味ではありません" in h


def _node(script):
    node = shutil.which("node")
    if not node:
        return None
    code = _logic() + "\n" + script
    return subprocess.run([node, "-e", code], capture_output=True, text=True, timeout=30)


BASE = dict(q1=1, q2=4, q3=4, q4=2, k1=2, k2=3, g10=1, g15=1, g30=0, bta=1, s1=1, s2=1, s3=0, s4=0, c1=2, c2=2, c3=0)


def test_rules_by_running_the_logic():
    cases = {
        "strong": dict(BASE),                                        # 2万は受けない・3万は受ける
        "very": dict(BASE, g30=1),                                   # 3万でも受けない
        "mild": dict(BASE, q1=0, g15=1),                             # 2万から受ける
        "normal": dict(BASE, q1=0, g15=0),                           # 1.5万から受ける
        "weak": dict(BASE, q1=0, g15=0, g10=0),                      # 1万でも受ける
        "shaky": dict(BASE, g10=0),                                  # 1万は受けて2万は受けない
        "flags": dict(BASE, q2=1, q3=0, q4=0, k1=0, k2=0, s1=4, s2=4, s3=2, s4=2, c1=0, c2=1, c3=3),
    }
    r = _node("var C=" + json.dumps(cases) + ";var o={};for(var k in C){o[k]=KUSE.diagnose(C[k]);}"
              "o.miss=KUSE.missing({q1:0});console.log(JSON.stringify(o));")
    if r is None:
        print("  （node が無いので計算の確かめは飛ばす）")
        return
    assert r.returncode == 0, r.stderr
    o = json.loads(r.stdout)
    assert o["strong"]["loss"] == {"threshold": 3, "level": "強い", "shaky": False}
    assert o["very"]["loss"]["level"] == "とても強い" and o["very"]["flags"]["L_strong"]
    assert o["mild"]["loss"]["level"] == "やや強い" and not o["mild"]["flags"]["L_strong"]
    assert o["normal"]["loss"]["level"] == "ふつう"
    assert o["weak"]["loss"]["level"] == "弱い" and o["weak"]["flags"]["L_weak"]
    assert o["shaky"]["loss"]["shaky"] and o["shaky"]["loss"]["threshold"] == 3
    f = o["flags"]["flags"]
    assert f["M"] and f["H"] and f["O"] and f["S"] and f["R"] and f["C_day"] and f["C_night"]
    assert o["flags"]["score"] == 0 and o["flags"]["sMean"] == 4.0
    assert len(o["flags"]["styles"]["shortS"]) >= 4 and o["flags"]["styles"]["longS"]
    none = o["normal"]
    assert not any(none["flags"][k] for k in ("L_strong", "L_weak", "M", "H", "O", "S", "R", "BIG", "C_day", "C_night"))
    assert none["styles"] == {"shortS": [], "swing": [], "longS": []}   # 何も出ない人には「つまずきは見つからず」
    assert o["miss"] == list(range(2, 18))


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
