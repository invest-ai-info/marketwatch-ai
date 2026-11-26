"""mutate_check（わざと壊すテストの共通の道具）のテスト。pytest 不要・pytest でも動く。

  PYTHONUTF8=1 python tests/test_mutate_check.py
"""
import hashlib
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import mutate_check as M  # noqa: E402

TOY = '''import os
HERE = os.path.dirname(os.path.abspath(__file__))


def is_big(x):
    return x >= 10


def add(a, b):
    return a + b


def where():
    return HERE
'''

WEAK = '''import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import toy
assert toy.is_big(20) and not toy.is_big(0)
assert toy.add(2, 2) == 4
assert toy.where() == os.path.dirname(os.path.abspath(__file__))
'''

STRONG = WEAK + '''assert toy.is_big(10) and not toy.is_big(9)
'''


def _toy(strong=False):
    d = tempfile.mkdtemp()
    with open(os.path.join(d, "toy.py"), "w", encoding="utf-8") as f:
        f.write(TOY)
    with open(os.path.join(d, "test_toy.py"), "w", encoding="utf-8") as f:
        f.write(STRONG if strong else WEAK)
    return d


def _sha(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def test_finds_each_operator_kind():
    ops = {m.op for m, _ in M.mutants("def f(a, b):\n    return a[1] + 2 if a[0] < b and b > 0 else 0\n")}
    assert ops == {"cmp", "arith", "const", "bool", "index"}


def test_each_mutant_changes_one_thing():
    src = "def f(a):\n    return a >= 10\n"
    ms = M.mutants(src)
    assert {(m.op, m.before, m.after) for m, _ in ms} == {("cmp", ">=", ">"), ("const", "10", "11"), ("const", "10", "9")}
    assert all(s != src and "def f(a)" in s for _, s in ms)


def test_bools_are_not_constants():
    assert not M.mutants("x = True\n")


def test_weak_test_leaves_survivors_and_original_untouched():
    d = _toy()
    p = os.path.join(d, "toy.py")
    before = _sha(p)
    rep = M.run(p, [sys.executable, os.path.join(d, "test_toy.py")])
    assert rep["baseline_ok"] and rep["survived"] and _sha(p) == before
    assert {"op": "cmp", "before": ">=", "after": ">"} == {k: rep["survived"][0][k] for k in ("op", "before", "after")} \
        or any(s["op"] == "cmp" for s in rep["survived"])
    assert rep["killed"] >= 1                       # add の + → - は気づく


def test_strong_test_kills_boundary_mutant():
    d = _toy(strong=True)
    rep = M.run(os.path.join(d, "toy.py"), [sys.executable, os.path.join(d, "test_toy.py")])
    assert rep["baseline_ok"] and not [s for s in rep["survived"] if s["op"] == "cmp"]


def test_broken_baseline_stops():
    d = _toy()
    with open(os.path.join(d, "test_toy.py"), "a", encoding="utf-8") as f:
        f.write("assert False\n")
    rep = M.run(os.path.join(d, "toy.py"), [sys.executable, os.path.join(d, "test_toy.py")])
    assert rep["baseline_ok"] is False and rep["total"] == 0


def test_target_loaded_by_path_is_reported():     # 名前で import しないテストは、壊しても気づけない＝止めて知らせる
    d = _toy()
    with open(os.path.join(d, "test_toy.py"), "w", encoding="utf-8") as f:
        f.write("import importlib.util, os\n"
                "p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'toy.py')\n"
                "s = importlib.util.spec_from_file_location('toy_by_path', p); m = importlib.util.module_from_spec(s)\n"
                "s.loader.exec_module(m)\nassert m.add(2, 2) == 4\n")
    rep = M.run(os.path.join(d, "toy.py"), [sys.executable, os.path.join(d, "test_toy.py")])
    assert rep["baseline_ok"] is False and rep.get("reason") == "not_imported"


if __name__ == "__main__":
    n = 0
    for k, fn in list(globals().items()):
        if k.startswith("test_") and callable(fn):
            fn()
            n += 1
    print(f"ok {n}")
