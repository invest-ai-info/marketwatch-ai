# -*- coding: utf-8 -*-
"""J48F 上場来高値の「急騰型」は、罠と途中の下げが大きいか（前向き）。
2026-10-27 登録・オーナー「登録して進めてください」。PILLAR_PREREG.md「J48F」。

J48 の読むための表（判定外）で3つの時代とも同じ向きに見えた傾向を、J44 の台帳（highs-ledger.csv）の
2026-10-08 以降のケース（登録の時点で60取引日あとが1件も出ていない）だけで確かめる。
組＝A 急騰型（25日線 +20%以上 または その日 +10%以上）／B ふつう（25日線 +10%未満 かつ その日 +3%未満）。
F1 罠（ex60 ≦ −10%）の割合の差・F2 いちばん深い下げ（min60）の中央値の差（A − B）。
A の埋まったケースが100件に届いた最初の週の実行で1回だけ判定（97.5％の幅・ケースの日で引き直す10,000回）。

⚠️ 決まりは PILLAR_PREREG.md「J48F」と下の定数に固定。台帳を読むだけ（値段は取りに行かない）。
⚠️ 判定の前は件数だけを出す（途中の割合・差・平均は出さない）。判定は書いたら変えない。
⚠️ 出力（highs-shape-forward.json / .md）は銘柄名とコードを出さない（GitHub 側で生成＝SYNC禁忌）。

実行: python highs_shape_forward.py   （Actions の highs-shape-forward.yml から週1）
"""
import csv
import datetime as dt
import hashlib
import json
import sys
from zoneinfo import ZoneInfo

import numpy as np

# pillar_lab と同じ値（pillar_lab は yfinance まで読み込むので、台帳を読むだけのこの道具では使わない＝numpy だけで動く）
JST = ZoneInfo("Asia/Tokyo")
PREREG = "PILLAR_PREREG.md"
SEED = 20260927


def prereg_sha256(path=PREREG):
    try:
        with open(path, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()
    except OSError:
        return None

LEDGER = "highs-ledger.csv"
OUT_JSON, OUT_MD = "highs-shape-forward.json", "highs-shape-forward.md"
START = "2026-10-08"
TV_MIN = 1.0                  # その日より前の20営業日の平均売買代金（億円）＝turnover ÷ tv_ratio
GAP = 60                      # 同じ銘柄は前のケースから60取引日（台帳の日付の数）あける
A_DEV, A_PCT = 0.20, 0.10     # 急騰型：25日線 +20%以上 または その日 +10%以上
B_DEV, B_PCT = 0.10, 0.03     # ふつう：25日線 +10%未満 かつ その日 +3%未満
TRAP = -0.10                  # 罠＝60取引日あとの TOPIX と比べた差が −10%以下
GOAL = 100                    # A の埋まったケースがこの数に届いた最初の週に判定
LATE = "2027-12-31"           # これを過ぎても届かなければ、A が LATE_MIN 件以上なら数える
LATE_MIN = 50
MIN_B = 50
ALPHA = 0.05 / 2              # 97.5％ の幅
N_BOOT = 10000
QUESTIONS = (("F1", "罠（60取引日あとの TOPIX と比べた差が −10%以下）の割合", +1),
             ("F2", "60取引日の間のいちばん深い下げの中央値", -1))
TITLES = {q: f"上場来高値の急騰型（25日線 +20%以上かその日 +10%以上）− ふつうの形：{name}" for q, name, _ in QUESTIONS}
OK_WORD = "✅ 急騰型は罠と途中の下げが大きい（前向きで確認）"


def _f(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if np.isfinite(v) else None


def read_ledger(path=LEDGER):
    try:
        with open(path, encoding="utf-8-sig") as fh:
            return list(csv.DictReader(fh))
    except OSError:
        return []


def group_of(dev25, pct):
    if dev25 is None or pct is None:
        return None
    if dev25 >= A_DEV or pct >= A_PCT:
        return "A"
    if dev25 < B_DEV and pct < B_PCT:
        return "B"
    return None


def cases(rows, start=START):
    """台帳の行 → ケース（記録上の最高値・1億円以上・60取引日あけ・組つき）。取引日＝台帳に出てくる日付"""
    dates = sorted({r.get("date", "") for r in rows if r.get("date")})
    pos = {d: i for i, d in enumerate(dates)}
    last, out = {}, []
    for r in sorted(rows, key=lambda r: (r.get("date", ""), r.get("code", ""))):
        d = r.get("date", "")
        if d < start or _f(r.get("record")) != 1:
            continue
        tv, ratio = _f(r.get("turnover")), _f(r.get("tv_ratio"))
        if tv is None or not ratio or ratio <= 0 or tv / ratio < TV_MIN:
            continue
        dev, pct = _f(r.get("dev25")), _f(r.get("pct"))
        if dev is None or pct is None:
            continue
        code = r.get("code", "")
        if code in last and pos[d] - pos[last[code]] < GAP:
            continue
        last[code] = d                            # 真ん中の組の日もケース（60取引日あけに数える＝J48 と同じ）
        g = group_of(dev, pct)
        if g is None:
            continue
        out.append({"date": d, "g": g, "ex60": _f(r.get("ex60")), "min60": _f(r.get("min60")),
                    "ex20": _f(r.get("ex20")), "ex120": _f(r.get("ex120")),
                    "dev_hit": (_f(r.get("dev25")) or 0) >= A_DEV, "pct_hit": (_f(r.get("pct")) or 0) >= A_PCT})
    return out


def filled(cs):
    return [c for c in cs if c["ex60"] is not None and c["min60"] is not None]


def stat(q, xs):
    if not xs:
        return None
    if q == "F1":
        return float(np.mean([x["ex60"] <= TRAP for x in xs]))
    return float(np.median([x["min60"] for x in xs]))


def band(q, cs, alpha=ALPHA, n_boot=N_BOOT, seed=SEED):
    """A − B と、ケースの日を単位に引き直した両側の幅"""
    a = [c for c in cs if c["g"] == "A"]
    b = [c for c in cs if c["g"] == "B"]
    out = {"n_a": len(a), "n_b": len(b), "a": stat(q, a), "b": stat(q, b), "diff": None, "lo": None, "hi": None}
    if not a or not b:
        return out
    out["diff"] = out["a"] - out["b"]
    days = sorted({c["date"] for c in cs})
    by = {d: ([c for c in a if c["date"] == d], [c for c in b if c["date"] == d]) for d in days}
    rng = np.random.default_rng(seed)
    sims = []
    for _ in range(n_boot):
        pick = rng.integers(0, len(days), len(days))
        sa = [c for i in pick for c in by[days[i]][0]]
        sb = [c for i in pick for c in by[days[i]][1]]
        if sa and sb:
            sims.append(stat(q, sa) - stat(q, sb))
    if sims:
        out["lo"], out["hi"] = (float(v) for v in np.percentile(sims, [100 * alpha / 2, 100 * (1 - alpha / 2)]))
    return out


def word(b, sign):
    if b["lo"] is None:
        return "保留"
    if (sign > 0 and b["lo"] > 0) or (sign < 0 and b["hi"] < 0):
        return "確認"
    if (sign > 0 and b["hi"] < 0) or (sign < 0 and b["lo"] > 0):
        return "逆"
    return "見えない"


def due(cs, today):
    """判定する日か → (する/しない/保留, 理由)"""
    f = filled(cs)
    na, nb = sum(c["g"] == "A" for c in f), sum(c["g"] == "B" for c in f)
    if na >= GOAL or (today > LATE and na >= LATE_MIN):
        return ("hold", f"ふつうの形の埋まったケースが{nb}件（{MIN_B}件未満）") if nb < MIN_B else ("judge", "")
    if today > LATE:
        return "hold", f"{LATE} を過ぎても急騰型の埋まったケースが{na}件（{LATE_MIN}件未満）"
    return "wait", ""


def read_tables(cs):
    """判定のあとだけ出す表"""
    f = filled(cs)

    def summ(xs):
        ex = [x["ex60"] for x in xs]
        return {"n": len(xs), "trap": stat("F1", xs), "dd_median": stat("F2", xs),
                "ex60_mean": float(np.mean(ex)) if ex else None, "ex60_median": float(np.median(ex)) if ex else None,
                "up": float(np.mean([v >= 0.10 for v in ex])) if ex else None}
    a = [c for c in f if c["g"] == "A"]
    return {"A": summ(a), "B": summ([c for c in f if c["g"] == "B"]),
            "A_dev_only": summ([c for c in a if c["dev_hit"] and not c["pct_hit"]]),
            "A_pct_only": summ([c for c in a if c["pct_hit"] and not c["dev_hit"]]),
            "A_both": summ([c for c in a if c["dev_hit"] and c["pct_hit"]])}


def build(rows, prev=None, today=None, n_boot=N_BOOT):
    today = today or dt.datetime.now(JST).date().isoformat()
    prev = prev or {}
    cs = cases(rows)
    f = filled(cs)
    res = {"kind": "marker", "fwd_start": START, "goal": GOAL, "titles": TITLES,
           "generated_at": dt.datetime.now(JST).isoformat(timespec="minutes"), "prereg_sha256": prereg_sha256(),
           "progress": {"F1": sum(c["g"] == "A" for c in f), "F2": sum(c["g"] == "A" for c in f)},
           "counts": {"A_cases": sum(c["g"] == "A" for c in cs), "B_cases": sum(c["g"] == "B" for c in cs),
                      "A_filled": sum(c["g"] == "A" for c in f), "B_filled": sum(c["g"] == "B" for c in f),
                      "ledger_days": len({r.get("date") for r in rows if r.get("date", "") >= START}),
                      "last_case": max((c["date"] for c in cs), default=None)},
           "verdicts": prev.get("verdicts") or {}}
    if prev.get("decision"):                       # 判定は書いたら変えない
        res["decision"] = prev["decision"]
        return res
    state, why = due(cs, today)
    if state == "hold":
        res["decision"] = {"status": "保留", "on": today, "reason": why}
    elif state == "judge":
        bands = {q: band(q, f, n_boot=n_boot) for q, *_ in QUESTIONS}
        words = {q: word(bands[q], s) for q, _, s in QUESTIONS}
        ok = all(w == "確認" for w in words.values())
        res["decision"] = {"status": OK_WORD if ok else "✕", "on": today, "bands": bands, "words": words,
                           "read": read_tables(cs)}
        res["verdicts"] = {q: {"status": "confirm" if ok else "stop", "decided_on": today, "n": bands[q]["n_a"],
                               "mean": bands[q]["diff"], "lo": bands[q]["lo"], "hi": bands[q]["hi"],
                               "reason": ("登録した日より後に結果が出た上場来高値だけで数えて、急騰型の方が罠の割合と途中の下げが大きかった"
                                          if ok else "登録した日より後に結果が出た上場来高値だけで数えて、急騰型とふつうの形の差が予想の向きにそろわなかった")}
                           for q, *_ in QUESTIONS}
    return res


def _p(x, d=1):
    return "—" if x is None else f"{x * 100:+.{d}f}％"


def render_md(res):
    c = res["counts"]
    L = ["# J48F 上場来高値の「急騰型」は、罠と途中の下げが大きいか（前向き）", "",
         f"更新: {res['generated_at']}（事前登録＝`PILLAR_PREREG.md`「J48F」・指紋 `{(res.get('prereg_sha256') or '')[:12]}`）", "",
         "- ケース＝J44 の台帳の上場来高値（2026-10-08 以降・売買代金1億円以上・同じ銘柄は60取引日あける）",
         "- A 急騰型＝25日線から +20%以上 または その日 +10%以上／B ふつう＝25日線 +10%未満 かつ その日 +3%未満",
         f"- 判定＝A の60取引日あとが埋まったケースが{GOAL}件に届いた週に1回だけ（F1 罠の割合・F2 いちばん深い下げの中央値・97.5％の幅）",
         "- ⚠️ 判定の前は件数だけ（途中の割合や差は出さない）。銘柄名・コードは出さない。過去の成績は将来を約束しない", "",
         "## 件数", "", "| 組 | ケース | 60取引日あとが埋まった |", "|---|---:|---:|",
         f"| A 急騰型 | {c['A_cases']} | {c['A_filled']}／{GOAL} |", f"| B ふつう | {c['B_cases']} | {c['B_filled']} |", "",
         f"台帳の日数 {c['ledger_days']}・最後のケース {c['last_case'] or '—'}", ""]
    d = res.get("decision")
    if not d:
        return "\n".join(L + ["判定はまだ（件数がそろうまで待つ）", ""])
    L += ["## 判定", "", f"**{d['status']}**（{d['on']}）", ""]
    if d.get("reason"):
        return "\n".join(L + [d["reason"], ""])
    L += ["| 問い | A 急騰型 | B ふつう | 差（A − B） | 97.5％の幅 | 結果 |", "|---|---:|---:|---:|---|---|"]
    for q, name, _ in QUESTIONS:
        b = d["bands"][q]
        L.append(f"| {q} {name} | {_p(b['a'])}（{b['n_a']}件） | {_p(b['b'])}（{b['n_b']}件） | {_p(b['diff'])} | "
                 f"{_p(b['lo'])} 〜 {_p(b['hi'])} | {d['words'][q]} |")
    L += ["", "## 読むための表（判定しない）", "", "| 組 | 件数 | 罠の割合 | 下げの中央値 | TOPIX比の平均 | 中央値 | 伸びた（+10%以上） |",
          "|---|---:|---:|---:|---:|---:|---:|"]
    for k, label in (("A", "A 急騰型"), ("B", "B ふつう"), ("A_dev_only", "A のうち25日線だけ"),
                     ("A_pct_only", "A のうちその日だけ"), ("A_both", "A のうち両方")):
        s = d["read"][k]
        L.append(f"| {label} | {s['n']} | {_p(s['trap'], 0)} | {_p(s['dd_median'])} | {_p(s['ex60_mean'])} | "
                 f"{_p(s['ex60_median'])} | {_p(s['up'], 0)} |")
    return "\n".join(L) + "\n"


def main(argv):
    try:
        with open(OUT_JSON, encoding="utf-8") as fh:
            prev = json.load(fh)
    except (OSError, ValueError):
        prev = {}
    rows = read_ledger()
    if not rows:
        print("⚠️ 台帳が読めない（highs-ledger.csv）＝何も書かない", file=sys.stderr)
        return 1
    res = build(rows, prev)
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1, default=str)
    md = render_md(res)
    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
