"""別の書き方での数え直しの突き合わせ（検算の関門の部品②・2026-11-27）

設計書: docs/superpowers/specs/2026-11-26-result-audit-design.md（5.3）・手順: recheck/RECOUNT_GUIDE.md

元の道具の一覧と、数え直しの担当（登録の文だけから別に書いた道具）の一覧を、1件ずつ突き合わせる。
  鍵：取引＝銘柄・向き・建ての時刻（UTC の分）／目印＝銘柄・日付・印
  比べる：取引＝決済の時刻・決済の値・出た理由・費用後／目印＝そのあとの動き
  許す差：値段 1e-6（相対）・損益 0.1pips／0.01%／1bp
食い違いは全部、理由を書く（recheck/<研究>/explanations.json に追記）。
  original_error・recount_error・ambiguous_rule＝直して数え直してから（説明だけでは通らない）
  data_version＝入力の値段そのものが違うと示せた行だけ、一致から外せる
説明できない食い違いが残らず、一致が100%なら、記録を recheck/records.json に足す（値段は入れない）。

  python recount_compare.py ORIG RECOUNT --study X [--kind trade|event] [--explain FILE] [--opened FILE]
                            [--forbid PATH ...] [--write] [--local-only] [--root .]
"""
import argparse
import hashlib
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import recheck_status as S
from result_audit import load_rows, to_utc

TOL = {"price": 1e-6, "pips": 0.1, "pct": 0.01, "bp": 1.0}
CATEGORIES = ("original_error", "recount_error", "ambiguous_rule", "data_version")


@dataclass
class Mismatch:
    key: tuple
    what: str                     # only_original／only_recount／differs／duplicate
    fields: list = field(default_factory=list)


@dataclass
class Compared:
    n_orig: int
    n_recount: int
    matched: int
    mismatches: list


class RecountError(Exception):
    pass


def _minute(s):
    return to_utc(s).strftime("%Y-%m-%dT%H:%MZ")


def key_of(row, kind="trade") -> tuple:
    if kind == "trade":
        return (str(row["symbol"]), int(float(row["side"])), _minute(row["entry_time"]))
    return (str(row["symbol"]), str(row["date"])[:10], str(row["flag"]))


def _has(r, k):
    return r.get(k) is not None and r.get(k) != ""


def _diff_fields(a, b, kind):
    out = []
    unit = a.get("unit") or b.get("unit") or "pips"
    tol = TOL.get(unit, TOL["pips"])
    if kind == "trade":
        if _minute(a["exit_time"]) != _minute(b["exit_time"]):
            out.append("exit_time")
        if _has(a, "exit_price") and _has(b, "exit_price"):
            x, y = float(a["exit_price"]), float(b["exit_price"])
            if abs(x - y) > TOL["price"] * max(1.0, abs(x)):
                out.append("exit_price")
        if _has(a, "exit_reason") and _has(b, "exit_reason") and str(a["exit_reason"]) != str(b["exit_reason"]):
            out.append("exit_reason")
        if abs(float(a["net"]) - float(b["net"])) > tol + 1e-12:
            out.append("net")
    else:
        if _has(a, "outcome") or _has(b, "outcome"):
            if not (_has(a, "outcome") and _has(b, "outcome")) or \
                    abs(float(a["outcome"]) - float(b["outcome"])) > tol + 1e-12:
                out.append("outcome")
    return out


def _index(rows, kind):
    m, dup = {}, []
    for r in rows:
        k = key_of(r, kind)
        if k in m:
            dup.append(k)
        else:
            m[k] = r
    return m, dup


def compare(orig, recount, kind="trade") -> Compared:
    a, da = _index(orig, kind)
    b, db = _index(recount, kind)
    mm = [Mismatch(k, "duplicate") for k in da + db]
    matched = 0
    for k in sorted(set(a) | set(b)):
        if k not in b:
            mm.append(Mismatch(k, "only_original"))
        elif k not in a:
            mm.append(Mismatch(k, "only_recount"))
        else:
            f = _diff_fields(a[k], b[k], kind)
            if f:
                mm.append(Mismatch(k, "differs", f))
            else:
                matched += 1
    return Compared(len(orig), len(recount), matched, mm)


def _sha(rows):
    return hashlib.sha256(json.dumps(list(rows), sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")).hexdigest()


def _norm(p):
    return str(p).replace("\\", "/").strip().lower()


def finalize(study, orig, recount, kind, explanations, opened, forbidden, root=None, today=None, local_only=False) -> dict:
    bad_open = [p for p in opened for f in forbidden if _norm(p).endswith(_norm(f)) or _norm(f).endswith(_norm(p))]
    if bad_open:
        raise RecountError(f"数え直しの担当が元の道具を開いた＝独立でない: {bad_open}")
    if not orig:
        raise RecountError("元の一覧が0件＝検算済みにできない")
    ex = list(explanations or [])
    for e in ex:
        if e.get("category") not in CATEGORIES:
            raise RecountError(f"食い違いの理由の種類が違う: {e.get('category')}（{CATEGORIES}）")
    dv = set()
    for e in ex:
        if e["category"] != "data_version":
            continue
        ev = e.get("evidence") or {}
        if "orig_input" not in ev or "recount_input" not in ev or ev["orig_input"] == ev["recount_input"]:
            raise RecountError(f"データの版の違いには、違う入力の値の証拠が要る: {e.get('key')}")
        dv.add(tuple(e["key"]) if kind == "event" else (str(e["key"][0]), int(e["key"][1]), str(e["key"][2])))
    c = compare(orig, recount, kind)
    left = [m for m in c.mismatches if m.key not in dv]
    if left:
        raise RecountError(f"説明できていない（直していない）食い違いが {len(left)} 件: 例 {[(m.key, m.what, m.fields) for m in left[:3]]}")
    excluded = len({k for k in dv})
    if excluded > S.DATA_VERSION_MAX * c.n_orig:
        raise RecountError(f"データの版の違いで外す行が多すぎる（{excluded}／{c.n_orig}・上限は元の件数の"
                           f"{S.DATA_VERSION_MAX:.0%}）＝同じ入力のデータで数え直す")
    base = c.n_orig - excluded
    agreement = c.matched / base if base > 0 else 0.0
    if base <= 0 or agreement != 1.0 or c.n_recount - excluded != c.matched:
        raise RecountError(f"一致が100%でない（一致 {c.matched}・元 {c.n_orig}・数え直し {c.n_recount}・外した {excluded}）")
    breakdown = {}
    for e in ex:
        breakdown[e["category"]] = breakdown.get(e["category"], 0) + 1
    rec = {"study": study, "kind": kind,
           "date": today or datetime.now(timezone(timedelta(hours=9))).date().isoformat(),
           "orig_sha256": _sha(orig), "recount_sha256": _sha(recount), "n_orig": c.n_orig, "n_recount": c.n_recount,
           "matched": c.matched, "excluded_data_version": excluded, "breakdown": breakdown,
           "agreement": agreement, "opened": [str(p) for p in opened]}
    S.put("records", study, rec, root, local_only)
    return rec


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="別の書き方での数え直しの突き合わせ")
    ap.add_argument("orig")
    ap.add_argument("recount")
    ap.add_argument("--study", required=True)
    ap.add_argument("--kind", default="trade", choices=("trade", "event"))
    ap.add_argument("--explain", help="食い違いの説明の JSON（一覧）")
    ap.add_argument("--opened", help="数え直しの担当が開いたファイルの一覧（1行に1つ）")
    ap.add_argument("--forbid", action="append", default=[], help="開いてはいけない元の道具のファイル")
    ap.add_argument("--write", action="store_true", help="一致100%なら記録に足す")
    ap.add_argument("--local-only", action="store_true")
    ap.add_argument("--root", default=None, help="既定＝recheck_status.py のあるフォルダ")
    a = ap.parse_args(argv)
    orig, rec = load_rows(a.orig), load_rows(a.recount)
    c = compare(orig, rec, a.kind)
    print(f"突き合わせ: {a.study}  元 {c.n_orig}・数え直し {c.n_recount}・一致 {c.matched}・食い違い {len(c.mismatches)}")
    for m in c.mismatches[:20]:
        print(f"  - {m.what} {list(m.key)} {m.fields}")
    if not a.write:
        return 0 if not c.mismatches else 1
    ex = json.load(open(a.explain, encoding="utf-8")) if a.explain else []
    opened = [x.strip() for x in open(a.opened, encoding="utf-8")] if a.opened else []
    try:
        r = finalize(a.study, orig, rec, a.kind, ex, [x for x in opened if x], a.forbid, a.root, local_only=a.local_only)
    except RecountError as e:
        print(f"🚨 {e}")
        return 1
    print(f"✅ 検算済みの記録を足しました（一致 {r['matched']}・外した {r['excluded_data_version']}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
