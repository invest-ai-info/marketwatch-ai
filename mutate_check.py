"""わざと壊すテストの共通の道具（検算の関門の部品③・2026-11-27）

設計書: docs/superpowers/specs/2026-11-26-result-audit-design.md（5.4）

道具のファイルを1か所ずつ壊した版で、テストを回す。テストが気づかなかった壊し方を一覧にする。
  壊し方：比べ方（< ↔ <=・> ↔ >=）・足し引き（+ ↔ -）・整数の定数 ±1・and ↔ or・添字の整数 ±1
  元のファイルは読むだけで書き換えない。変えた版は一時フォルダに置き、sitecustomize が import をそこへ向ける
  （__file__ は元の場所のまま＝データの置き場の計算は変わらない）
止める関門ではない（気づかなかった壊し方の中には、意味の変わらないものもある）。新しい道具の登録に
「壊した数・気づかなかった数とその理由」を書く。

  python mutate_check.py TARGET.py [--limit N] [--timeout 300] -- <テストのコマンド>
"""
import argparse
import ast
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass

CMP = {ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt}
CMP_TXT = {ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">="}
ARITH = {ast.Add: ast.Sub, ast.Sub: ast.Add}
ARITH_TXT = {ast.Add: "+", ast.Sub: "-"}
BOOL = {ast.And: ast.Or, ast.Or: ast.And}
BOOL_TXT = {ast.And: "and", ast.Or: "or"}


@dataclass
class Mutant:
    id: int
    line: int
    op: str
    before: str
    after: str


def _is_int(node):
    return isinstance(node, ast.Constant) and type(node.value) is int


def _candidates(tree):
    """(ast.walk の番号, 何番目の演算子, op, before, after, 行)"""
    index_consts = {id(n.slice) for n in ast.walk(tree) if isinstance(n, ast.Subscript) and _is_int(n.slice)}
    out = []
    for i, n in enumerate(ast.walk(tree)):
        if isinstance(n, ast.Compare):
            for j, o in enumerate(n.ops):
                if type(o) in CMP:
                    out.append((i, j, "cmp", CMP_TXT[type(o)], CMP_TXT[CMP[type(o)]], n.lineno))
        elif isinstance(n, ast.BinOp) and type(n.op) in ARITH:
            out.append((i, 0, "arith", ARITH_TXT[type(n.op)], ARITH_TXT[ARITH[type(n.op)]], n.lineno))
        elif isinstance(n, ast.BoolOp) and type(n.op) in BOOL:
            out.append((i, 0, "bool", BOOL_TXT[type(n.op)], BOOL_TXT[BOOL[type(n.op)]], n.lineno))
        elif _is_int(n):
            op = "index" if id(n) in index_consts else "const"
            for d in (1, -1):
                out.append((i, d, op, str(n.value), str(n.value + d), n.lineno))
    return out


def _apply(src, i, j, op):
    tree = ast.parse(src)
    n = list(ast.walk(tree))[i]
    if op == "cmp":
        n.ops[j] = CMP[type(n.ops[j])]()
    elif op == "arith":
        n.op = ARITH[type(n.op)]()
    elif op == "bool":
        n.op = BOOL[type(n.op)]()
    else:
        n.value = n.value + j
    return ast.unparse(tree) + "\n"


def mutants(src: str) -> list:
    tree = ast.parse(src)
    return [(Mutant(k, line, op, before, after), _apply(src, i, j, op))
            for k, (i, j, op, before, after, line) in enumerate(_candidates(tree))]


SITE = '''import importlib.abc, importlib.util, json, os, sys
_C = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "mutate_cfg.json"), encoding="utf-8"))


class _Loader(importlib.abc.Loader):
    def create_module(self, spec):
        return None

    def exec_module(self, m):
        try:
            open(_C["marker"], "w").close()   # 名前で読み込まれた印（無ければ、壊した版はテストに届いていない）
        except OSError:
            pass
        m.__file__ = _C["origin"]
        with open(_C["source"], encoding="utf-8") as f:
            exec(compile(f.read(), _C["origin"], "exec"), m.__dict__)


class _Finder(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if name == _C["name"]:
            return importlib.util.spec_from_loader(name, _Loader(), origin=_C["origin"])
        return None


sys.meta_path.insert(0, _Finder())
'''


def _run_once(tmp, name, origin, src, test_cmd, timeout):
    with open(os.path.join(tmp, "mutant_source.py"), "w", encoding="utf-8", newline="\n") as f:
        f.write(src)
    with open(os.path.join(tmp, "mutate_cfg.json"), "w", encoding="utf-8") as f:
        json.dump({"name": name, "origin": origin, "source": os.path.join(tmp, "mutant_source.py"),
                   "marker": os.path.join(tmp, "imported.marker")}, f)
    env = dict(os.environ)
    env["PYTHONPATH"] = tmp + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    env.setdefault("PYTHONUTF8", "1")
    try:
        p = subprocess.run(test_cmd, env=env, capture_output=True, timeout=timeout)
        return "pass" if p.returncode == 0 else "fail"
    except subprocess.TimeoutExpired:
        return "timeout"


def run(target: str, test_cmd: list, timeout: int = 300, limit=None) -> dict:
    origin = os.path.abspath(target)
    name = os.path.splitext(os.path.basename(origin))[0]
    with open(origin, encoding="utf-8") as f:
        src = f.read()
    out = {"target": target, "total": 0, "killed": 0, "survived": [], "timed_out": [], "baseline_ok": False,
           "reason": ""}
    tmp = tempfile.mkdtemp(prefix="mutate_")
    try:
        with open(os.path.join(tmp, "sitecustomize.py"), "w", encoding="utf-8", newline="\n") as f:
            f.write(SITE)
        if _run_once(tmp, name, origin, src, test_cmd, timeout) != "pass":
            out["reason"] = "baseline_failed"
            return out
        if not os.path.exists(os.path.join(tmp, "imported.marker")):
            out["reason"] = "not_imported"   # テストが道具を名前で import していない（ファイルの場所から読む・別の処理で動かす・-I）
            return out
        out["baseline_ok"] = True
        ms = mutants(src)
        for m, s in ms[:limit] if limit else ms:
            res = _run_once(tmp, name, origin, s, test_cmd, timeout)
            out["total"] += 1
            if res == "fail":
                out["killed"] += 1
            elif res == "timeout":
                out["timed_out"].append(asdict(m))
            else:
                out["survived"].append(asdict(m))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return out


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--" not in argv:
        print("usage: python mutate_check.py TARGET.py [--limit N] [--timeout S] -- <テストのコマンド>")
        return 2
    k = argv.index("--")
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--timeout", type=int, default=300)
    a = ap.parse_args(argv[:k])
    rep = run(a.target, argv[k + 1:], a.timeout, a.limit)
    if not rep["baseline_ok"]:
        if rep.get("reason") == "not_imported":
            print("🚨 テストが道具を名前で import していない＝壊した版がテストに届かない"
                  "（ファイルの場所から読む spec_from_file_location・別の処理で動かす・python -I のどれか）")
        else:
            print("🚨 壊していない版でテストが通らない＝先にテストを直す")
        return 1
    print(f"わざと壊す: {a.target}  壊した {rep['total']}・気づいた {rep['killed']}・"
          f"気づかなかった {len(rep['survived'])}・時間切れ {len(rep['timed_out'])}")
    for s in rep["survived"]:
        print(f"  - {s['line']} 行目 {s['op']}: {s['before']} → {s['after']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
