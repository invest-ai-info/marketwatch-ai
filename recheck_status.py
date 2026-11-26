"""検算の記録の読み書き（検算の関門・2026-11-27）

設計書: docs/superpowers/specs/2026-11-26-result-audit-design.md

記録は値段を含まない2つのファイルにまとめる（送るファイルは1つずつ名前を書く決まりのため）:
  recheck/audits.json   … 点検（result_audit.py）の出力。研究の名前 → 点検の要約
  recheck/records.json  … 数え直し（recount_compare.py）の記録。研究の名前 → 突き合わせの要約
J-Quants を使う研究などは local_only=True で research/recheck/ に置く（送らない）。読むときは両方を重ねる。

使い始めの日（GO_LIVE）より前の合格・登録はさかのぼらない（設計書 5.5・5.7）。
"""
import json
import os
import re

GO_LIVE = "2026-11-27"   # 使い始めの日（JST）。ここ1か所だけ
DATA_VERSION_MAX = 0.1   # 「データの版の違い」で一致から外してよい行の上限（元の件数に対する割合）
REPO = os.path.dirname(os.path.abspath(__file__))   # 記録の置き場の既定＝このファイルのあるフォルダ（今いるフォルダではない）

KINDS = ("audits", "records")


def safe(study: str) -> str:
    """記録の鍵にする研究の名前（文字・数字・_ . - 以外は _ に。日本語は残す＝「上昇」「下降」がぶつからない）"""
    return re.sub(r"[^\w.-]", "_", str(study))


def store_path(kind: str, root=None, local_only: bool = False) -> str:
    root = root or REPO
    if kind not in KINDS:
        raise ValueError(f"記録の種類は {KINDS} のどれか: {kind}")
    base = os.path.join(root, "research", "recheck") if local_only else os.path.join(root, "recheck")
    return os.path.join(base, f"{kind}.json")


def _read(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def load_store(kind: str, root=None) -> dict:
    """{研究の名前: 記録}。無い・壊れている → {}。research/ 側を上に重ねる"""
    out = dict(_read(store_path(kind, root)))
    out.update(_read(store_path(kind, root, local_only=True)))
    return out


def put(kind: str, study: str, entry: dict, root=None, local_only: bool = False) -> str:
    """記録を足す。同じ研究の前の記録は entry["previous"] に積む（訂正はいつも追記）"""
    path = store_path(kind, root, local_only)
    d = _read(path)
    key = safe(study)
    new = dict(entry)
    old = d.get(key)
    if old:
        prev = list(old.pop("previous", []))
        new["previous"] = prev + [old]
    d[key] = new
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(d, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")
    return path


def entry_ok(entry) -> bool:
    """一致の決まり（ここ1か所）: 件数が1以上・一致が100%・データの版の違いで外した行が上限以下"""
    if not isinstance(entry, dict):
        return False
    try:
        n = int(entry.get("n_orig", 0))
        return (n > 0 and float(entry.get("agreement", 0)) == 1.0
                and int(entry.get("excluded_data_version", 0)) <= DATA_VERSION_MAX * n)
    except (TypeError, ValueError):
        return False


def recheck_ok(study: str, root=None) -> bool:
    return entry_ok(load_store("records", root).get(safe(study)))


def is_waiting(study: str, passed_on, root=None, go_live: str | None = None) -> bool:
    """合格の日が使い始めの日以降で、数え直しの記録がまだ無い → 待ち"""
    if not passed_on:
        return False
    if str(passed_on)[:10] < (go_live or GO_LIVE):
        return False
    return not recheck_ok(study, root)


def audit_by_fingerprint(hex12: str, root=None):
    """点検の指紋で記録を引く。前の記録（previous）も探す＝同じ研究を点検し直しても、登録に書いた指紋は見つかる"""
    h = str(hex12).lower()
    if not h:
        return None
    for e in load_store("audits", root).values():
        for x in ([e] + list(e.get("previous", [])) if isinstance(e, dict) else []):
            if isinstance(x, dict) and str(x.get("fingerprint", "")).startswith(h):
                return x
    return None


WAIT_MARK = "🔍 数え直し待ち"


def promoted_waiting(h, root=None, go_live: str | None = None) -> bool:
    """シグナル研究の tracker の仮説が、昇格したのに数え直しの記録がまだ無いか（表示と使う所で同じ判定）"""
    return isinstance(h, dict) and h.get("status") == "promoted" and \
        is_waiting(h.get("id", ""), h.get("promoted_at"), root, go_live)
