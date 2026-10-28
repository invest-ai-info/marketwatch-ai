# -*- coding: utf-8 -*-
"""J49F 上場来高値の罠の目印（急騰の重なり・5本以内の −10%）は、登録より後のケースでも罠を約2倍に見分けるか（前向き）。
2026-10-28 登録・オーナー「登録してください」。PILLAR_PREREG.md「J49F」。

J49（過去20年・1回だけ）で3つの時代とも ✅ だった T1（急騰の重なり3つ以上）と T3（5本以内に終値 −10%以下）を、
J44 の台帳（highs-ledger.csv）の 2026-10-08 以降のケース（登録の時点で60取引日あとが1件も出ていない）だけで確かめる。
ケースの決め方は J48F と同じ（highs_shape_forward の決まり・ただし形の組では分けない）。値段は Yahoo の日足・全体は 1306。
問いごとに、目印ありの結果が100件に届いた最初の週に1回だけ判定（97.5％の幅・ケースの日で引き直す10,000回）。

⚠️ 決まりは PILLAR_PREREG.md「J49F」と下の定数に固定。判定の前は件数だけを出す（途中の割合・差・平均は出さない）。判定は書いたら変えない。
⚠️ 出力（highs-entry-forward.json / .md）は銘柄名とコードを出さない（GitHub 側で生成＝SYNC禁忌）。

実行: python highs_entry_forward.py   （Actions の highs-entry-forward.yml から週1）
"""
import datetime as dt
import json
import sys

import numpy as np

import highs_shape_forward as F

LEDGER = F.LEDGER
OUT_JSON, OUT_MD = "highs-entry-forward.json", "highs-entry-forward.md"
START = "2026-10-08"
TV_MIN, GAP = F.TV_MIN, F.GAP          # 1億円以上・60取引日あける（J48F と同じ）
HOLD = 60                              # 買った日を1本目として60本目の引けで売る（J49 と同じ）
TRAP = -0.10                           # 罠＝損益 − 1306 が −10％以下
M25_HOT, RET_HOT, TVX_HOT, STREAK_HOT, HOT_MIN = 0.20, 0.10, 3.0, 4, 3
T3_DAYS, T3_DROP = 5, 0.10
GOAL = 100                             # 目印ありの結果がこの数に届いた最初の週に判定
LATE, LATE_MIN = "2027-12-31", 50
MIN_B = 50
ALPHA = 0.05 / 2                       # 97.5％ の幅
N_BOOT = 10000
HIGH_PROB = 0.50
TOPIX = "1306"
QUESTIONS = (("T1F", "急騰の重なり3つ以上（25日線 +20%以上・その日 +10%以上・売買代金3倍以上・4日続けて上げ）− 2つ以下：罠の割合", +1),
             ("T3F", "5本以内に終値が記録の日の −10%以下になった − ならなかった：罠の割合", +1))
TITLES = {q: f"上場来高値の罠の目印・{name}（前向き・2026-10-08 以降のケース）" for q, name, _ in QUESTIONS}
OK_WORD = "✅ 前向きでも確認"


def hot_score(dev25, pct, tv_ratio, streak):
    return int((dev25 is not None and dev25 >= M25_HOT) + (pct is not None and pct >= RET_HOT) +
               (tv_ratio is not None and tv_ratio >= TVX_HOT) + (streak is not None and streak >= STREAK_HOT))


def cases(rows, start=START):
    """台帳の行 → ケース（記録上の最高値・1億円以上・60取引日あけ）。J48F の cases と同じ決め方で、形の組では分けない。
    コードはこの道具の中だけで使い、出力には出さない"""
    dates = sorted({r.get("date", "") for r in rows if r.get("date")})
    pos = {d: i for i, d in enumerate(dates)}
    last, out = {}, []
    for r in sorted(rows, key=lambda r: (r.get("date", ""), r.get("code", ""))):
        d = r.get("date", "")
        if d < start or F._f(r.get("record")) != 1:
            continue
        tv, ratio = F._f(r.get("turnover")), F._f(r.get("tv_ratio"))
        if tv is None or not ratio or ratio <= 0 or tv / ratio < TV_MIN:
            continue
        dev, pct = F._f(r.get("dev25")), F._f(r.get("pct"))
        if dev is None or pct is None:
            continue
        code = r.get("code", "")
        if code in last and pos[d] - pos[last[code]] < GAP:
            continue
        last[code] = d
        out.append({"date": d, "code": code, "hot": hot_score(dev, pct, ratio, F._f(r.get("streak")))})
    return out


def to_days(bars):
    """Yahoo の足 [(時刻, 始, 高, 安, 終, 出来高)] → [(YYYY-MM-DD, 始, 終)]（値の無い足は除く）"""
    out = []
    for b in bars or []:
        t, o, c = b[0], b[1], b[4]
        if o and c and o > 0 and c > 0:
            out.append((t.strftime("%Y-%m-%d"), float(o), float(c)))
    return out


def window(days, a, idx):
    """足 a の寄りで買い、60本目の引けで売った損益 − 1306 の同じ区間（足りなければ None）"""
    b = a + HOLD - 1
    if b >= len(days):
        return None
    d_in, d_out = days[a][0], days[b][0]
    if d_in not in idx or d_out not in idx:
        return None
    r = days[b][2] / days[a][1] - 1
    m = idx[d_out][1] / idx[d_in][0] - 1
    return r - m


def outcomes(case, days, idx):
    """1ケース → {"t1": 罠か/None, "t3_flag": True/False/None, "t3": 罠か/None}。days＝その銘柄の日足・idx＝{日: (1306 の始, 終)}"""
    out = {"t1": None, "t3_flag": None, "t3": None}
    j = next((i for i, d in enumerate(days) if d[0] == case["date"]), None)
    if j is None:
        return out
    x1 = window(days, j + 1, idx)
    out["t1"] = None if x1 is None else bool(x1 <= TRAP)
    if j + T3_DAYS >= len(days):
        return out
    c0 = days[j][2]
    ks = [k for k in range(j + 1, j + T3_DAYS + 1) if days[k][2] <= c0 * (1 - T3_DROP)]
    out["t3_flag"] = bool(ks)
    x3 = window(days, (ks[0] + 1) if ks else (j + T3_DAYS + 1), idx)
    out["t3"] = None if x3 is None else bool(x3 <= TRAP)
    return out


def rows_of(q, cs):
    """問い → [(ケースの日, 罠か, "A"/"B")]（結果の出たケースだけ）"""
    out = []
    for c in cs:
        o = c.get("o") or {}
        if q == "T1F" and o.get("t1") is not None:
            out.append((c["date"], o["t1"], "A" if c["hot"] >= HOT_MIN else "B"))
        elif q == "T3F" and o.get("t3") is not None and o.get("t3_flag") is not None:
            out.append((c["date"], o["t3"], "A" if o["t3_flag"] else "B"))
    return out


def band(rows, alpha=ALPHA, n_boot=N_BOOT, seed=F.SEED):
    """罠の割合の差（A − B）と、ケースの日を単位に引き直した両側の幅"""
    a = [x for _, x, g in rows if g == "A"]
    b = [x for _, x, g in rows if g == "B"]
    out = {"n_a": len(a), "n_b": len(b), "a": (float(np.mean(a)) if a else None), "b": (float(np.mean(b)) if b else None),
           "diff": None, "lo": None, "hi": None}
    if not a or not b:
        return out
    out["diff"] = out["a"] - out["b"]
    days = sorted({d for d, _, _ in rows})
    pos = {d: i for i, d in enumerate(days)}
    K = len(days)
    sa, na, sb, nb = (np.zeros(K) for _ in range(4))
    for d, x, g in rows:
        if g == "A":
            sa[pos[d]] += x
            na[pos[d]] += 1
        else:
            sb[pos[d]] += x
            nb[pos[d]] += 1
    if not n_boot:
        return out
    rng = np.random.default_rng(seed)
    W = rng.multinomial(K, np.full(K, 1.0 / K), size=n_boot).astype(float)
    with np.errstate(invalid="ignore", divide="ignore"):
        s = (W @ sa) / (W @ na) - (W @ sb) / (W @ nb)
    s = s[np.isfinite(s)]
    if len(s):
        out["lo"], out["hi"] = (float(v) for v in np.percentile(s, [100 * alpha / 2, 100 * (1 - alpha / 2)]))
    return out


def word(b):
    if b["lo"] is None:
        return "保留"
    if b["lo"] > 0:
        return "確認"
    if b["hi"] < 0:
        return "逆"
    return "見えない"


def due(q, cs, today):
    rows = rows_of(q, cs)
    na = sum(g == "A" for _, _, g in rows)
    nb = sum(g == "B" for _, _, g in rows)
    if na >= GOAL or (today > LATE and na >= LATE_MIN):
        return ("hold", f"目印なしの結果が{nb}件（{MIN_B}件未満）") if nb < MIN_B else ("judge", "")
    if today > LATE:
        return "hold", f"{LATE} を過ぎても目印ありの結果が{na}件（{LATE_MIN}件未満）"
    return "wait", ""


def read_tables(q, cs):
    """判定のあとだけ出す表（判定しない）"""
    rows = rows_of(q, cs)
    out = {"A": {"n": sum(g == "A" for _, _, g in rows)}, "B": {"n": sum(g == "B" for _, _, g in rows)}}
    if q == "T1F":
        for k in range(5):
            xs = [c["o"]["t1"] for c in cs if c["hot"] == k and (c.get("o") or {}).get("t1") is not None]
            out[f"急騰の点数 {k}"] = {"n": len(xs), "trap": (float(np.mean(xs)) if xs else None)}
    return out


def counts(cs):
    out = {"cases": len(cs), "last_case": max((c["date"] for c in cs), default=None)}
    for q, *_ in QUESTIONS:
        rows = rows_of(q, cs)
        out[q] = {"A_filled": sum(g == "A" for _, _, g in rows), "B_filled": sum(g == "B" for _, _, g in rows)}
    out["T1F"]["A_cases"] = sum(c["hot"] >= HOT_MIN for c in cs)
    out["T3F"]["A_cases"] = sum(1 for c in cs if (c.get("o") or {}).get("t3_flag"))
    return out


def build(rows, fetch, prev=None, today=None, n_boot=N_BOOT):
    """fetch(code) → その銘柄の日足 [(日, 始, 終)]。1306 も fetch で取る"""
    today = today or dt.datetime.now(F.JST).date().isoformat()
    prev = prev or {}
    cs = cases(rows)
    idx = {d: (o, c) for d, o, c in fetch(TOPIX)}
    for c in cs:
        c["o"] = outcomes(c, fetch(c["code"]), idx) if idx else {}
    decisions = dict(prev.get("decisions") or {})
    verdicts = dict(prev.get("verdicts") or {})
    for q, name, _ in QUESTIONS:
        if q in decisions:                          # 判定は書いたら変えない
            continue
        state, why = due(q, cs, today)
        if state == "hold":
            decisions[q] = {"status": "保留", "on": today, "reason": why}
        elif state == "judge":
            b = band(rows_of(q, cs), n_boot=n_boot)
            w = word(b)
            ok = w == "確認"
            decisions[q] = {"status": OK_WORD if ok else f"✕ {w}", "on": today, "band": b, "word": w,
                            "high_prob": bool(ok and b["a"] is not None and b["a"] >= HIGH_PROB), "read": read_tables(q, cs)}
            verdicts[q] = {"status": "confirm" if ok else "stop", "decided_on": today, "n": b["n_a"], "mean": b["diff"],
                           "lo": b["lo"], "hi": b["hi"],
                           "reason": ("登録した日より後に結果が出た上場来高値だけで数えて、目印のある株の方が罠（TOPIX より −10%以下）の割合が高かった"
                                      if ok else "登録した日より後に結果が出た上場来高値だけで数えて、目印のある株の罠の割合が高いとは言えなかった")}
    cnt = counts(cs)
    return {"kind": "marker", "fwd_start": START, "goal": GOAL, "titles": TITLES,
            "generated_at": dt.datetime.now(F.JST).isoformat(timespec="minutes"), "prereg_sha256": F.prereg_sha256(),
            "progress": {q: cnt[q]["A_filled"] for q, *_ in QUESTIONS}, "counts": cnt,
            "price_ok": bool(idx), "decisions": decisions, "verdicts": verdicts}


def _p(x, d=0):
    return "—" if x is None else f"{x * 100:+.{d}f}％"


def render_md(res):
    c = res["counts"]
    L = ["# J49F 上場来高値の罠の目印は、登録より後のケースでも罠を見分けるか（前向き）", "",
         f"更新: {res['generated_at']}（事前登録＝`PILLAR_PREREG.md`「J49F」・指紋 `{(res.get('prereg_sha256') or '')[:12]}`）", "",
         "- ケース＝J44 の台帳の上場来高値（2026-10-08 以降・売買代金1億円以上・同じ銘柄は60取引日あける）・値段は Yahoo の日足・全体は 1306",
         "- 罠＝そのあと60本の損益 − 1306 が −10％以下。T1F＝記録の日の急騰の重なり3つ以上／T3F＝5本以内に終値 −10％以下",
         f"- 判定＝目印ありの結果が{GOAL}件に届いた週に問いごとに1回だけ（罠の割合の差・97.5％の幅）",
         "- ⚠️ 判定の前は件数だけ（途中の割合や差は出さない）。銘柄名・コードは出さない。過去の成績は将来を約束しない", ""]
    if not res.get("price_ok"):
        L += ["⚠️ 1306 の日足が取れなかった（この週は結果を数えていない）", ""]
    L += ["## 件数", "", "| 問い | 目印ありのケース | 目印ありの結果が出た | 目印なしの結果が出た |", "|---|---:|---:|---:|"]
    for q, *_ in QUESTIONS:
        x = c[q]
        L.append(f"| {q} | {x['A_cases']} | {x['A_filled']}／{GOAL} | {x['B_filled']} |")
    L += ["", f"ケース {c['cases']}・最後のケース {c['last_case'] or '—'}", ""]
    for q, name, _ in QUESTIONS:
        d = res["decisions"].get(q)
        L += [f"## {q} {name}", ""]
        if not d:
            L += ["判定はまだ（件数がそろうまで待つ）", ""]
            continue
        L += [f"**{d['status']}**（{d['on']}）", ""]
        if d.get("reason"):
            L += [d["reason"], ""]
            continue
        b = d["band"]
        L += ["| 目印あり 罠の割合 | 目印なし 罠の割合 | 差 | 97.5％の幅 | 結果 |", "|---:|---:|---:|---|---|",
              f"| {_p(b['a'])}（{b['n_a']}件） | {_p(b['b'])}（{b['n_b']}件） | {_p(b['diff'], 1)} | {_p(b['lo'], 1)} 〜 {_p(b['hi'], 1)} | {d['word']} |", ""]
        if d.get("high_prob"):
            L += ["高い確率（目印ありの罠の割合 50％以上）", ""]
        rd = d.get("read") or {}
        extra = [(k, v) for k, v in rd.items() if k.startswith("急騰の点数")]
        if extra:
            L += ["読むための表（判定しない）：" + "／".join(f"{k} {_p(v['trap'])}（{v['n']}件）" for k, v in extra), ""]
    return "\n".join(L) + "\n"


def yahoo_fetch():
    import yori_lab as Y          # 値段を取るときだけ読み込む（テストは作り物の fetch で動く）
    cache = {}

    def fetch(code):
        if code not in cache:
            cache[code] = to_days(Y.fetch_chart(code, "1d", "2y") or [])
        return cache[code]
    return fetch


def main(argv):
    try:
        with open(OUT_JSON, encoding="utf-8") as fh:
            prev = json.load(fh)
    except (OSError, ValueError):
        prev = {}
    rows = F.read_ledger(LEDGER)
    if not rows:
        print("⚠️ 台帳が読めない（highs-ledger.csv）＝何も書かない", file=sys.stderr)
        return 1
    res = build(rows, yahoo_fetch(), prev)
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1, default=str)
    md = render_md(res)
    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
