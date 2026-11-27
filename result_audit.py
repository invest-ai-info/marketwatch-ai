"""ありえない数字の点検（検算の関門の部品①・2026-11-27）

設計書: docs/superpowers/specs/2026-11-26-result-audit-design.md（5.1 共通の形・5.2 点検）

研究の道具は、結果を書く前に取引の一覧（または目印の一覧）を共通の形にして gate() に通す。
  - error があれば、点検の要約だけ recheck/audits.json に残して AuditError（結果は書かない）
  - warning は、理由を1行（waivers）書けば進める
  - 出力に損益の合計・平均・勝率は出さない（事前登録の「結果を見る前」を壊さない）

  python result_audit.py ROWS.csv|ROWS.json --study X [--ctx ctx.json] [--waive A6=理由] [--root .] [--local-only] [--dry]
"""
import argparse
import csv
import hashlib
import json
import math
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import recheck_status as S

TRADE_FIELDS = ("study", "market", "symbol", "side", "signal_time", "entry_time", "exit_time",
                "entry_price", "exit_price", "stop_price", "unit", "gross", "cost", "net", "r",
                "exit_reason", "period")
EVENT_FIELDS = ("study", "market", "symbol", "date", "flag", "outcome", "unit", "period")
TRADE_REQUIRED = ("study", "market", "symbol", "side", "entry_time", "exit_time", "unit", "net")
EVENT_REQUIRED = ("study", "market", "symbol", "date", "flag", "unit")
MARKETS = ("fx", "jp", "index", "commodity", "crypto")
UNITS = ("pips", "pct", "bp")
NUMERIC = ("side", "entry_price", "exit_price", "stop_price", "gross", "cost", "net", "r", "outcome")

# 閾値はここ1か所だけ（較正の表＝recheck/CALIBRATION.md）
LIMITS = {
    "missing_max": 0.02,          # A10 データの抜け（平日に対する割合）
    "stop_k": {"fx": 3.0, "jp": 6.0, "index": 4.0, "commodity": 4.0, "crypto": 4.0},   # A2 r < -k
    "gap_mult": 3.0,              # A2 fx で土曜をまたぐか、NY17時の切り替わりの足に触れる取引は k をこの倍に（較正：CP-F の金曜の引けの損切り 6件）
    "move_max": {"fx": 0.12, "jp": 0.5, "index": 0.12, "commodity": 0.2, "crypto": 0.35},  # A3 1平日あたりの動きの上限
    "pips_max_per_day": 600,      # A3 fx で値段が無いとき |gross|
    "price_ratio_max": 5.0,       # A3 同じ銘柄の建値の中央値からのずれ（10倍ずれ・分割）
    "price_ratio_min_rows": 3,
    "split_ks": (2, 3, 4, 5, 10),  # A3 日本株の分割・併合の形（比が 1/k か k に近い）
    "split_tol": 0.03,            # 〃 比の許す差（1/k は ±0.03・k は ±3%）＝明光 1→2 の -47.8% を当てる
    "split_max_days": 5,          # 〃 持った平日がこの日数以下の取引だけ（長く持った2倍は本物がある）
    "cost_tol": {"pips": 0.05, "pct": 0.005, "bp": 0.5},   # A4 |gross - cost - net| の許す差
    "rollover_share_max": 0.25,   # A5・A7 小さい入れ物（取引の割合の上限）
    "profit_share_min": 0.5,      # A5・A7 プラスの net の合計のうち、その入れ物が持つ割合
    "a57_min_n": 10,              # A5・A7 を見る最少の件数
    "year_jump": 3.0,             # A6 ほかの年の中央値の何倍か（1/何倍か）
    "a6_min_years": 3,
    "g1_win": 0.75, "g1_mean_r": 1.0, "g1_min_n": 30,   # G1 良すぎる印
    "event_move_max": {"jp": 0.5, "fx": 0.06, "index": 0.12, "commodity": 0.2, "crypto": 0.35},  # A3 目印の outcome
}

TOKYO = ZoneInfo("Asia/Tokyo")


@dataclass
class Context:
    kind: str = "trade"                     # "trade"／"event"
    one_at_a_time: bool = False             # 1度に1つだけの決まり
    no_friday: bool = False                 # 金曜は取引しない決まり
    friday_tz: str = "Asia/Tokyo"
    missing_ratio: float | None = None      # 道具が数えたデータの抜けの割合
    holidays: dict = field(default_factory=dict)   # 市場 → ["YYYY-MM-DD", ...]
    min_cost: float | None = None           # 費用の下限（unit の単位）
    outcome_days: int = 1                   # 目印の outcome が何営業日の動きか（A3 の上限を日数で広げる・分割の形は split_max_days 以下だけ）


@dataclass
class Finding:
    check: str
    level: str                              # "error"／"warning"／"flag"
    count: int
    examples: list
    note: str = ""


class AuditError(Exception):
    pass


# ---------- 時刻 ----------
def to_utc(s) -> datetime:
    """ISO の時刻 → UTC。時間帯の無い時刻は ValueError（黙って UTC とみなさない）"""
    if isinstance(s, datetime):
        d = s
    else:
        d = datetime.fromisoformat(str(s).strip().replace("Z", "+00:00"))
    if d.tzinfo is None:
        raise ValueError(f"時間帯が無い時刻: {s}")
    return d.astimezone(timezone.utc)


def _minute(s) -> str:
    return to_utc(s).strftime("%Y-%m-%dT%H:%MZ")


def _has(row, k):
    v = row.get(k)
    return v is not None and v != ""


def _num(row, k):
    return float(row[k]) if _has(row, k) else None


# ---------- 形 ----------
def check_rows(rows, kind) -> list:
    msgs = []
    req = TRADE_REQUIRED if kind == "trade" else EVENT_REQUIRED
    for i, r in enumerate(rows):
        for k in req:
            if not _has(r, k):
                msgs.append(f"{i} 行目: {k} がない")
        if _has(r, "market") and r["market"] not in MARKETS:
            msgs.append(f"{i} 行目: market が {MARKETS} のどれでもない")
        if _has(r, "unit") and r["unit"] not in UNITS:
            msgs.append(f"{i} 行目: unit が {UNITS} のどれでもない")
        if kind == "trade":
            if _has(r, "side"):
                try:
                    ok = int(float(r["side"])) in (1, -1) and float(r["side"]) == int(float(r["side"]))
                except (TypeError, ValueError):
                    ok = False
                if not ok:
                    msgs.append(f"{i} 行目: side は 1 か -1")
            for k in ("signal_time", "entry_time", "exit_time"):
                if _has(r, k):
                    try:
                        to_utc(r[k])
                    except ValueError as e:
                        msgs.append(f"{i} 行目: {k} の{'時間帯が無い' if '時間帯' in str(e) else '形が読めない'}")
        else:
            if _has(r, "date"):
                try:
                    datetime.strptime(str(r["date"]), "%Y-%m-%d")
                except ValueError:
                    msgs.append(f"{i} 行目: date は YYYY-MM-DD")
        for k in NUMERIC:
            if _has(r, k):
                try:
                    if not math.isfinite(float(r[k])):
                        msgs.append(f"{i} 行目: {k} が有限の数でない（nan・inf）")
                except (TypeError, ValueError):
                    msgs.append(f"{i} 行目: {k} が数でない")
    return msgs


# ---------- 点検 ----------
def _hit(check, level, idx, note=""):
    idx = sorted(set(idx))
    return Finding(check, level, len(idx), idx[:5], note) if idx else None


def _a1(rows, ctx):
    idx = [i for i, r in enumerate(rows) if to_utc(r["exit_time"]) < to_utc(r["entry_time"])]
    return _hit("A1", "error", idx, "決済が建てより前")


def _a1_signal(rows, ctx):
    idx = [i for i, r in enumerate(rows)
           if _has(r, "signal_time") and to_utc(r["entry_time"]) < to_utc(r["signal_time"])]
    return _hit("A1-signal", "error", idx, "建てが合図の確定より前（先読み）")


def _a8(rows, ctx):
    if ctx.kind == "trade":
        key = lambda r: (r["symbol"], int(float(r["side"])), _minute(r["entry_time"]))
    else:
        key = lambda r: (r["symbol"], str(r["date"]), str(r["flag"]))
    seen, idx = set(), []
    for i, r in enumerate(rows):
        k = key(r)
        if k in seen:
            idx.append(i)
        seen.add(k)
    note = "同じ取引が2回" if ctx.kind == "trade" else "同じ印が2回"
    if ctx.kind == "trade" and ctx.one_at_a_time:
        order = sorted(range(len(rows)), key=lambda i: to_utc(rows[i]["entry_time"]))
        end = None
        for i in order:
            a = to_utc(rows[i]["entry_time"])
            if end is not None and a < end:
                idx.append(i)
                note = "1度に1つの決まりなのに重なる"
            b = to_utc(rows[i]["exit_time"])
            end = b if end is None or b > end else end
    return _hit("A8", "error", idx, note)


def _market_day(r):
    """市場の日付（fx・指数・商品・暗号＝UTC／日本株＝東京）"""
    if "date" in r and _has(r, "date") and not _has(r, "entry_time"):
        return datetime.strptime(str(r["date"]), "%Y-%m-%d").date()
    d = to_utc(r["entry_time"])
    return (d.astimezone(TOKYO) if r["market"] == "jp" else d).date()


def _a9(rows, ctx):
    idx, kinds = [], set()
    tz = ZoneInfo(ctx.friday_tz)
    for i, r in enumerate(rows):
        m = r["market"]
        day = _market_day(r)
        if m != "crypto":
            if day.weekday() == 5 or (day.weekday() == 6 and (m == "jp" or ctx.kind == "event")):
                idx.append(i)
                kinds.add("土日")
        if day.isoformat() in set(ctx.holidays.get(m, [])):
            idx.append(i)
            kinds.add("休場日")
        if ctx.kind == "trade" and ctx.no_friday and to_utc(r["entry_time"]).astimezone(tz).weekday() == 4:
            idx.append(i)
            kinds.add("金曜（金曜は取引しない決まり）")
    return _hit("A9", "error", idx, "・".join(sorted(kinds)))


def _a10(rows, ctx):
    if ctx.missing_ratio is not None and float(ctx.missing_ratio) > LIMITS["missing_max"] + 1e-12:
        return Finding("A10", "error", 1, [], "データの抜けが決まりの上限を超える")
    return None


NY = ZoneInfo("America/New_York")


def _weekdays_between(a, b):
    """建ての日の次の日から決済の日までの平日の数（最少1）"""
    d, n = a.date(), 0
    while d < b.date():
        d += timedelta(days=1)
        if d.weekday() < 5:
            n += 1
    return max(1, n)


def _spans_saturday(a, b):
    d = a.date()
    while d <= b.date():
        if d.weekday() == 5:
            return True
        d += timedelta(days=1)
    return False


def _touches_friday_rollover(r):
    """建てから決済までに、金曜の NY17時（週の引けの切り替わり）がある（決済がちょうどその時刻でも当てる）。
    ふつうの平日の夜をまたぐだけの取引は当てない（全体の読み直しで直した）"""
    a, b = to_utc(r["entry_time"]), to_utc(r["exit_time"])
    d, end = a.astimezone(NY).date(), b.astimezone(NY).date()
    while d <= end:
        if d.weekday() == 4:
            t = datetime(d.year, d.month, d.day, 17, 0, tzinfo=NY).astimezone(timezone.utc)
            if a <= t <= b:
                return True
        d += timedelta(days=1)
    return False


def _split_shape(ratio):
    """値動きの比が、分割・併合のときの形（1/k か k）に近いか"""
    tol = LIMITS["split_tol"]
    return any(abs(ratio - 1 / k) <= tol or abs(ratio - k) <= tol * k for k in LIMITS["split_ks"])


def _a2(rows, ctx):
    idx = []
    for i, r in enumerate(rows):
        if not _has(r, "r"):
            continue
        k = LIMITS["stop_k"][r["market"]]
        if r["market"] == "fx" and (_spans_saturday(to_utc(r["entry_time"]), to_utc(r["exit_time"]))
                                    or _touches_friday_rollover(r)):
            k *= LIMITS["gap_mult"]
        if float(r["r"]) < -k:
            idx.append(i)
    return _hit("A2", "error", idx, "損が損切りの幅を大きく超える（損切りの確かめの誤りの形）")


def _median(xs):
    xs = sorted(xs)
    n = len(xs)
    if not n:
        return None
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def _a3(rows, ctx):
    idx = []
    if ctx.kind == "event":
        for i, r in enumerate(rows):
            if _has(r, "outcome") and r["unit"] == "pct":
                o = float(r["outcome"]) / 100
                days = max(1, int(ctx.outcome_days or 1))
                short_jp = r["market"] == "jp" and days <= LIMITS["split_max_days"]
                if abs(o) > LIMITS["event_move_max"][r["market"]] * days or (short_jp and _split_shape(1 + o)):
                    idx.append(i)
        return _hit("A3", "error", idx, "印のあとの動きがありえない大きさか分割の形（分割の直しもれ・偽の値の形）")
    for i, r in enumerate(rows):
        days = _weekdays_between(to_utc(r["entry_time"]), to_utc(r["exit_time"]))
        lim = LIMITS["move_max"][r["market"]] * days
        short_jp = r["market"] == "jp" and days <= LIMITS["split_max_days"]
        if _has(r, "entry_price") and _has(r, "exit_price"):
            e, x = float(r["entry_price"]), float(r["exit_price"])
            if e <= 0 or x <= 0 or abs(x / e - 1) > lim or (short_jp and _split_shape(x / e)):
                idx.append(i)
            continue
        g = _num(r, "gross") if _has(r, "gross") else _num(r, "net")
        if g is None:
            continue
        if r["unit"] == "pips" and r["market"] == "fx" and abs(g) > LIMITS["pips_max_per_day"] * days:
            idx.append(i)
        elif r["unit"] == "pct" and (abs(g) / 100 > lim or (short_jp and _split_shape(1 + g / 100))):
            idx.append(i)
    by_sym = {}
    for i, r in enumerate(rows):
        if _has(r, "entry_price"):
            by_sym.setdefault(r["symbol"], []).append(i)
    q = LIMITS["price_ratio_max"]
    for _sym, ii in by_sym.items():
        if len(ii) < LIMITS["price_ratio_min_rows"]:
            continue
        med = _median([float(rows[i]["entry_price"]) for i in ii])
        for i in ii:
            v = float(rows[i]["entry_price"])
            if med and med > 0 and (v / med > q or v / med < 1 / q):
                idx.append(i)
    return _hit("A3", "error", idx, "値段か1回の動きがありえない（偽の値・10倍ずれ・分割の形）")


def _a4(rows, ctx):
    idx = []
    for i, r in enumerate(rows):
        c = _num(r, "cost")
        if c is None:
            continue
        if c < 0 or (ctx.min_cost is not None and c < float(ctx.min_cost) - 1e-12):
            idx.append(i)
            continue
        g, n = _num(r, "gross"), _num(r, "net")
        if g is not None and n is not None and abs(g - c - n) > LIMITS["cost_tol"][r["unit"]]:
            idx.append(i)
    return _hit("A4", "error", idx, "費用が負・下限より小さい・費用前と費用後が合わない")


def _crosses_ny17(r, touch=False):
    """建てと決済の間に NY17時（夏冬は zoneinfo）がある。touch=True なら決済がちょうどその時刻でも当てる"""
    a, b = to_utc(r["entry_time"]), to_utc(r["exit_time"])
    la = a.astimezone(NY)
    t = la.replace(hour=17, minute=0, second=0, microsecond=0)
    if t < la:
        t = (la + timedelta(days=1)).replace(hour=17, minute=0, second=0, microsecond=0)
    t = t.astimezone(timezone.utc)
    return t <= b if touch else t < b


def _concentrated(rows, member):
    """小さい入れ物（取引の割合が上限以下）が、プラスの net の合計の半分超を持つか"""
    nets = [float(r["net"]) for r in rows]
    if len(rows) < LIMITS["a57_min_n"] or sum(nets) <= 0:
        return False
    pos = sum(max(v, 0) for v in nets)
    inside = [i for i, r in enumerate(rows) if member(r)]
    if not inside or len(inside) / len(rows) > LIMITS["rollover_share_max"]:
        return False
    return sum(max(nets[i], 0) for i in inside) > LIMITS["profit_share_min"] * pos


def _a5(rows, ctx):
    fx = [r for r in rows if r["market"] == "fx"]
    if fx and _concentrated(fx, _crosses_ny17):
        return Finding("A5", "warning", 1, [], "NY17時の切り替わりをまたぐ取引に利益が寄っている（費用の計算を確かめる）")
    return None


A7_BANDS = ("東京の朝", "東京の午後", "ロンドンの朝", "ロンドンの午後とニューヨークの朝",
            "ニューヨークの午後", "ニューヨークの夕方から夜")   # UTC の 4時間ごと


def _a7(rows, ctx):
    names = []
    buckets = [("建ての時間帯", lambda r: A7_BANDS[to_utc(r["entry_time"]).hour // 4]),
               ("向き", lambda r: "買い" if int(float(r["side"])) > 0 else "売り"),
               ("銘柄", lambda r: r["symbol"])]
    for title, fn in buckets:
        vals = {fn(r) for r in rows}
        if len(vals) < 2:
            continue
        for v in sorted(vals):
            if _concentrated(rows, lambda r, v=v, fn=fn: fn(r) == v):
                names.append(f"{title}＝{v}")
    if names:
        return Finding("A7", "warning", len(names), [], "利益が小さい入れ物に寄っている: " + "・".join(names))
    return None


def _a6(rows, ctx):
    if ctx.kind == "event":
        months = [str(r["date"])[:7] for r in rows]
    else:
        months = [to_utc(r["entry_time"]).strftime("%Y-%m") for r in rows]
    if not months:
        return None
    first, last = min(months), max(months)
    counts = {}
    for ym in months:
        counts[ym[:4]] = counts.get(ym[:4], 0) + 1
    if len(counts) < LIMITS["a6_min_years"]:
        return None
    norm = {}
    for y, n in counts.items():
        m_from = int(first[5:]) if y == first[:4] else 1
        m_to = int(last[5:]) if y == last[:4] else 12
        norm[y] = n * 12 / max(1, m_to - m_from + 1)
    q, hits = LIMITS["year_jump"], []
    for y, v in norm.items():
        med = _median([w for z, w in norm.items() if z != y])
        if med and (v > q * med or v < med / q):
            hits.append(y)
    if hits:
        return Finding("A6", "warning", len(hits), [], "年ごとの回数が跳ねている年がある（データの欠陥の形）")
    return None


def _g1(rows, ctx):
    if len(rows) < LIMITS["g1_min_n"]:
        return None
    win = sum(float(r["net"]) > 0 for r in rows) / len(rows)
    rs = [float(r["r"]) for r in rows if _has(r, "r")]
    mean_r = sum(rs) / len(rs) if rs else None
    if win > LIMITS["g1_win"] or (mean_r is not None and mean_r > LIMITS["g1_mean_r"]):
        return Finding("G1", "flag", 1, [], "良すぎる＝数え直しが必須")
    return None


# 名前・当てる形・要る欄（どの行にも無ければ飛ばす）・要る文脈・関数
CHECKS = [
    ("A1", ("trade",), (), None, _a1),
    ("A1-signal", ("trade",), ("signal_time",), None, _a1_signal),
    ("A2", ("trade",), ("r",), None, _a2),
    ("A3", ("trade", "event"), (), None, _a3),
    ("A4", ("trade",), ("cost",), None, _a4),
    ("A5", ("trade",), (), None, _a5),
    ("A6", ("trade", "event"), (), None, _a6),
    ("A7", ("trade",), (), None, _a7),
    ("A8", ("trade", "event"), (), None, _a8),
    ("A9", ("trade", "event"), (), None, _a9),
    ("A10", ("trade", "event"), (), "missing_ratio", _a10),
    ("G1", ("trade",), (), None, _g1),
]


def _coverage(rows, ctx):
    run, skipped = [], []
    for name, kinds, needs, ctx_need, _fn in CHECKS:
        if ctx.kind not in kinds:
            continue
        ok = all(any(_has(r, k) for r in rows) for k in needs) if needs else True
        if ctx_need and getattr(ctx, ctx_need) is None:
            ok = False
        (run if ok else skipped).append(name)
    return run, skipped


def audit(rows, ctx) -> list:
    rows = list(rows)
    problems = check_rows(rows, ctx.kind)
    if problems:
        bad = sorted({int(m.split(" ", 1)[0]) for m in problems})
        return [Finding("FORMAT", "error", len(bad), bad[:5], problems[0])]
    run, _ = _coverage(rows, ctx)
    out = []
    for name, _kinds, _needs, _ctx_need, fn in CHECKS:
        if name in run and rows:
            f = fn(rows, ctx)
            if f:
                out.append(f)
    return out


# ---------- 要約 ----------
def _sha(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")).hexdigest()


def fingerprint_of(d: dict) -> str:
    return _sha({k: v for k, v in d.items() if k != "fingerprint"})


def summarize(rows, ctx, findings, extra=None) -> dict:
    rows = list(rows)
    run, skipped = _coverage(rows, ctx)
    d = {
        "kind": ctx.kind,
        "n_rows": len(rows),
        "rows_sha256": _sha(rows),
        "checks_run": run,
        "checks_skipped": skipped,
        "errors": sum(f.level == "error" for f in findings),
        "warnings": sum(f.level == "warning" for f in findings),
        "flags": [f.check for f in findings if f.level == "flag"],
        "findings": [asdict(f) for f in findings],
    }
    d.update(extra or {})
    d["fingerprint"] = fingerprint_of(d)
    return d


def gate(rows, ctx, study, root=None, waivers=None, local_only=False, record=True) -> dict:
    """root の既定＝recheck_status.py のあるフォルダ（今いるフォルダではない）。passed＝error 無し・warning は全部理由つき"""
    waivers = dict(waivers or {})
    fs = audit(rows, ctx)
    today = datetime.now(timezone(timedelta(hours=9))).date().isoformat()
    errs = [f.check for f in fs if f.level == "error"]
    open_w = [f.check for f in fs if f.level == "warning" and not str(waivers.get(f.check, "")).strip()]
    s = summarize(rows, ctx, fs, {"study": study, "date": today, "waivers": waivers,
                                  "passed": not errs and not open_w})
    if record:
        S.put("audits", study, s, root, local_only)
    if errs:
        raise AuditError(f"点検で止まりました（error）: {'・'.join(errs)}。結果は書きません")
    if open_w:
        raise AuditError(f"点検の warning に理由がありません: {'・'.join(open_w)}（--waive 名前=理由）")
    return s


# ---------- 読み込み・CLI ----------
def load_rows(path) -> list:
    if path.lower().endswith(".json"):
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        rows = d.get("rows", []) if isinstance(d, dict) else d
    else:
        with open(path, encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        x = {}
        for k, v in r.items():
            if v is None or v == "":
                continue
            if k in NUMERIC:
                try:
                    v = float(v)
                    if k == "side":
                        v = int(v)
                except (TypeError, ValueError):
                    pass
            x[k] = v
        out.append(x)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="ありえない数字の点検（損益の合計・平均・勝率は出さない）")
    ap.add_argument("rows")
    ap.add_argument("--study", required=True)
    ap.add_argument("--ctx", help="Context の JSON（kind・one_at_a_time・no_friday・missing_ratio・holidays・min_cost）")
    ap.add_argument("--waive", action="append", default=[], help="warning の名前=理由")
    ap.add_argument("--root", default=None, help="既定＝recheck_status.py のあるフォルダ")
    ap.add_argument("--local-only", action="store_true")
    ap.add_argument("--dry", action="store_true", help="記録に残さない（試しに見るだけ）")
    a = ap.parse_args(argv)
    ctx = Context()
    if a.ctx:
        with open(a.ctx, encoding="utf-8") as f:
            ctx = Context(**json.load(f))
    waivers = dict(w.split("=", 1) for w in a.waive if "=" in w)
    rows = load_rows(a.rows)
    try:
        s = gate(rows, ctx, a.study, a.root, waivers, a.local_only, record=not a.dry)
        code = 0
    except AuditError as e:
        s = summarize(rows, ctx, audit(rows, ctx))
        print(f"🚨 {e}")
        code = 1
    print(f"点検: {a.study}  行 {s['n_rows']}  error {s['errors']}  warning {s['warnings']}  "
          f"印 {'・'.join(s['flags']) or 'なし'}  点検の指紋 {s['fingerprint'][:12]}")
    for f in s["findings"]:
        print(f"  - {f['check']} [{f['level']}] {f['count']} 件 例 {f['examples']}  {f['note']}")
    if s["checks_skipped"]:
        print(f"  （欄が無くて飛ばした点検: {'・'.join(s['checks_skipped'])}）")
    return code


if __name__ == "__main__":
    sys.exit(main())
