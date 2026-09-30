# -*- coding: utf-8 -*-
"""総当たりのふるい分けの判定（M6 ポンド円・ロンドン時間の総当たり。2026-09-30 登録＝PILLAR_PREREG.md「M6」）。

オーナー「すべての組み合わせを1回ずつ検証…成績の良いものは昇格リスト、悪いものは検証済みリスト…後に改善して再検証したい」。

役目の分け方:
  - 取引を作る（値動きの計算）＝手元の research/mt5/m6_screen.py（MT5 の5分足・M5 の入口と出口を使い回す）
  - 判定する＝このファイル（リポジトリ直下・テストつき・計算より先にコミット）。手元はこれを import して判定を任せる
  - リストにする＝verified_list.py（検証済みリスト）・promotion_list.py（昇格リスト）。GitHub 側で組み立てる

⚠️ 判定の数字（件数200・95%の幅・多重検定・時期・偽薬1,000回・前向きの区切り300／1000）は登録どおりに固定。結果を見てから変えない。
⚠️ 記録（m6-screen.json）には判定と集計だけを書く。値段や取引の行は書かない。
⚠️ 一度出たラウンドの判定は、あとのラウンドで変えない。直して数え直すときは新しいラウンド（版）を登録してから。

手元での使い方（research/mt5/m6_screen.py から）:
    import screen_judge as J
    rows = J.judge_round(combos, "r1")                 # combos = {組み合わせの名前: {"r": [費用後のR…], "date": ["YYYY-MM-DD"…], "pips": […]}}
    for row in J.needs_placebo(rows):
        J.apply_placebo(row, 偽薬の期待値1,000個)       # 種は J.placebo_seed(row["id"])
    rec = J.build_record(rows, "r1", ran_on="2026-10-01", data={...}, labels={...})
    J.write_full_csv(rows, "research/mt5/m6/m6-screen-full.csv")
    J.write_record(rec)                                 # → m6-screen.json（mw sync で送る）
    # 昇格候補が出たら: J.apply_mt5(rec, 名前, EA の R, EA の日付, "2026-10-05")
    # 前向き（月1回）:   J.apply_forward(rec, 名前, 実行日より後の R, 日付, "2026-11-01")
"""
import csv
import datetime as dt
import hashlib
import json
import math
import zlib

import numpy as np

PREREG = "PILLAR_PREREG.md"
SECTION = "## M6 "
OUT_JSON = "m6-screen.json"
NAME = "M6 ポンド円・ロンドン時間の総当たり"

MIN_N = 200                      # 件数の下限
Q = 0.05                         # 多重検定（ベンヤミニ・ホッホベルク）の水準
Z95 = 1.959963984540054          # 95%の幅
START, END = "2022-06-01", "2026-09-24"
HALF = "2024-08-01"              # 前半／後半の境（M5 と同じ）
PERIODS = (("2022-06-01", "2023-05-31"), ("2023-06-01", "2024-07-31"),
           ("2024-08-01", "2025-07-31"), ("2025-08-01", "2026-09-24"))
MIN_PERIODS_PLUS = 3             # 4つの時期のうちプラスがいくつ要るか
N_PLACEBO = 1000
PLACEBO_ALPHA = 0.05
FWD_STOP_MIN, GOAL = 300, 1000   # 前向き：300回以上で幅がまるごとマイナスならストップ／1000回で判定
NEAR_TOP = 20
TFS = ("M5", "M15", "H1")
ROUND_SIZES = {"r1": 3 * 32 * 64}   # ラウンド1＝足3 × 入口32 × 出口64 ＝ 6,144通り（全部渡す＝取引0の組み合わせも）

REASONS = {
    "few": "件数不足",
    "minus": "費用後マイナス",
    "zero": "0と区別できない",
    "luck": "偶然の範囲（多重検定を越えない）",
    "split": "時期で割れた",
    "placebo": "偽薬と差なし",
    "mt5": "MT5 の確かめで消えた",
    "fwd": "前向きで消えた",
}
SCREEN_REASONS = ("few", "minus", "zero", "luck", "split", "placebo")   # この順に調べて、最初に当たった1つ
NEAR_REASONS = ("luck", "split", "placebo")                             # 直す出発点の候補に並べるもの
STAGES = {
    "candidate": "昇格候補（MT5 の確かめ待ち）",
    "mt5_ok": "前向きで数えている（MT5 でも残った）",
    "plus": "前向きでもプラス（使うかどうかはオーナーが決める）",
}


# ───────── 数字 ─────────
def _f(x, nd=4):
    """JSON に書ける数（無限・NaN は None）"""
    if x is None:
        return None
    x = float(x)
    return round(x, nd) if math.isfinite(x) else None


def week_of(date):
    y, w, _ = dt.date.fromisoformat(str(date)[:10]).isocalendar()
    return f"{y}-W{w:02d}"


def cluster_stats(r, dates):
    """週ごとのまとまりで幅を出す（登録の式）。r は入った順に並べた費用後の R"""
    r = np.asarray(r, float)
    n = len(r)
    out = {"n": n, "mean": None, "se": None, "lo": None, "hi": None, "t": None, "p": 1.0,
           "win": None, "pf": None, "mdd": None}
    if n == 0:
        return out
    mean = float(r.mean())
    _, inv = np.unique(np.array([week_of(d) for d in dates]), return_inverse=True)
    s = np.bincount(inv, weights=r)
    c = np.bincount(inv).astype(float)
    g = len(s)
    if g < 2:
        se = math.inf
    else:
        u = s - mean * c
        se = math.sqrt(g / (g - 1) * float(np.sum(u * u))) / n
    if se == 0:
        t = math.inf if mean > 0 else (-math.inf if mean < 0 else 0.0)
    else:
        t = mean / se
    p = 0.5 * math.erfc(t / math.sqrt(2)) if math.isfinite(t) else (0.0 if t > 0 else 1.0)
    gain, loss = float(r[r > 0].sum()), float(-r[r < 0].sum())
    cum = np.cumsum(r)
    peak = np.maximum.accumulate(np.concatenate([[0.0], cum]))[1:]
    out.update(mean=mean, se=se, lo=mean - Z95 * se, hi=mean + Z95 * se, t=t, p=p,
               win=float((r > 0).mean()), pf=(gain / loss if loss > 0 else None), mdd=float((peak - cum).max()))
    return out


def period_means(r, dates):
    """前半・後半と4つの時期の期待値（取引が無ければ None）"""
    r = np.asarray(r, float)
    d = np.array([str(x)[:10] for x in dates])

    def m(mask):
        return float(r[mask].mean()) if mask.any() else None
    half = [m(d < HALF), m(d >= HALF)] if len(r) else [None, None]
    per = [m((d >= a) & (d <= b)) for a, b in PERIODS] if len(r) else [None] * len(PERIODS)
    return half, per


def bh_pass(pvals, m, q=Q):
    """ベンヤミニ・ホッホベルク。m＝これまでに数えた総数（このラウンドの数より小さくはできない）"""
    p = np.asarray(pvals, float)
    k = len(p)
    if m < k:
        raise ValueError(f"多重検定の総数 m={m} が、このラウンドの数 {k} より小さい")
    out = np.zeros(k, bool)
    if k == 0:
        return out
    order = np.argsort(p, kind="stable")
    ok = p[order] <= q * np.arange(1, k + 1) / m
    if ok.any():
        out[order[:np.nonzero(ok)[0].max() + 1]] = True
    return out


def tf_of(cid):
    parts = str(cid).split("-")
    return parts[1] if len(parts) > 1 and parts[1] in TFS else None


# ───────── ふるい分け ─────────
def family_total(prev, rnd, size):
    """多重検定の m＝これまでのラウンドの総数＋このラウンドの数"""
    done = [x for x in (prev or {}).get("rounds", []) if x["round"] != rnd]
    return sum(x["n_combos"] for x in done) + size


def judge_round(combos, rnd, prev=None):
    """1ラウンド分を判定する。combos = {名前: {"r": [...], "date": [...], "pips": [...](任意)}}（取引は入った順）"""
    size = len(combos)
    need = ROUND_SIZES.get(rnd)
    if need is not None and size != need:
        raise ValueError(f"ラウンド {rnd} は {need} 通りすべてを渡す（取引0の組み合わせも）。渡されたのは {size}")
    m_total = family_total(prev, rnd, size)
    rows = []
    for cid, c in combos.items():
        r, dates = list(c.get("r", [])), list(c.get("date", []))
        if len(r) != len(dates):
            raise ValueError(f"{cid}: R と日付の数が合わない")
        st = cluster_stats(r, dates)
        half, per = period_means(r, dates)
        pips = c.get("pips")
        rows.append({"id": cid, "round": rnd, "tf": tf_of(cid), **st, "half": half, "periods": per,
                     "pips": (float(np.mean(pips)) if pips is not None and len(pips) else None),
                     "m_total": m_total, "bh": False, "status": None, "reason": None,
                     "placebo_p": None, "placebo_mean": None})
    passed = bh_pass([x["p"] for x in rows], m_total)
    for x, ok in zip(rows, passed):
        x["bh"] = bool(ok)
        x["reason"] = _screen_reason(x)
        x["status"] = "out" if x["reason"] else "needs_placebo"
    return rows


def _screen_reason(x):
    if x["n"] < MIN_N:
        return "few"
    if x["hi"] < 0:
        return "minus"
    if x["lo"] <= 0:
        return "zero"
    if not x["bh"]:
        return "luck"
    plus_periods = sum(1 for v in x["periods"] if v is not None and v > 0)
    if not (x["half"][0] is not None and x["half"][0] > 0 and x["half"][1] is not None and x["half"][1] > 0
            and plus_periods >= MIN_PERIODS_PLUS):
        return "split"
    return None


def needs_placebo(rows):
    return [x for x in rows if x["status"] == "needs_placebo"]


def placebo_seed(cid):
    """組み合わせごとに決まった種（手元で何度流しても同じ偽薬になる）"""
    return zlib.crc32(str(cid).encode("utf-8"))


def apply_placebo(row, placebo_means):
    """偽薬の期待値（N_PLACEBO 個）と比べる。本物が上で、両側 p＜0.05 なら昇格候補"""
    pm = np.asarray(placebo_means, float)
    if len(pm) != N_PLACEBO:
        raise ValueError(f"偽薬は {N_PLACEBO} 回（渡されたのは {len(pm)}）")
    obs = row["mean"]
    ge = (np.sum(pm >= obs - 1e-12) + 1) / (N_PLACEBO + 1)
    le = (np.sum(pm <= obs + 1e-12) + 1) / (N_PLACEBO + 1)
    p = float(min(1.0, 2 * min(ge, le)))
    row["placebo_p"], row["placebo_mean"] = p, float(pm.mean())
    ok = obs > float(np.median(pm)) and p < PLACEBO_ALPHA
    row["status"], row["reason"] = ("candidate", None) if ok else ("out", "placebo")
    return row


# ───────── 記録 ─────────
def section_sha256(path=PREREG, head=SECTION):
    """登録の節（見出しから次の「## 」の前まで）の指紋"""
    text = open(path, encoding="utf-8").read()
    i = text.find("\n" + head)
    if i < 0:
        raise ValueError(f"{path} に「{head.strip()}」の節が無い")
    j = text.find("\n## ", i + 1)
    return hashlib.sha256(text[i + 1:(j if j >= 0 else len(text))].encode("utf-8")).hexdigest()


def _brief(x, keys=("n", "mean", "lo", "hi", "win", "pf", "t")):
    out = {}
    for k in keys:
        v = x.get(k)
        out[k] = v if k == "n" else _f(v)
    return out


def build_record(rows, rnd, ran_on, data=None, labels=None, prev=None, redo_reason=None, now=None):
    """ラウンドの判定を記録にまとめる（前のラウンドの記録 prev に足す）"""
    if needs_placebo(rows):
        raise ValueError("偽薬がまだの組み合わせがある（apply_placebo を先に）")
    rec = json.loads(json.dumps(prev)) if prev else {
        "kind": "screen", "id": "M6", "name": NAME, "goal": GOAL, "rounds": [], "counts": {}, "reading": {},
        "near_misses": [], "promoted": [], "stopped_after_promotion": [], "labels": {}, "redo": []}
    if any(x["round"] == rnd for x in rec["rounds"]):
        if not redo_reason:
            raise ValueError(f"ラウンド {rnd} は判定済み（変えない）。データや計算の誤りを直したときだけ redo_reason を書いてやり直す")
        rec["redo"].append({"round": rnd, "on": ran_on, "reason": redo_reason})
        rec["rounds"] = [x for x in rec["rounds"] if x["round"] != rnd]
        rec["near_misses"] = [x for x in rec["near_misses"] if x["round"] != rnd]
        rec["promoted"] = [x for x in rec["promoted"] if x["round"] != rnd]
    rec["generated_jst"] = now or dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(timespec="minutes")
    if data:
        rec["data"] = data
    rec["labels"].update(labels or {})
    rec["rounds"].append({"round": rnd, "ran_on": ran_on, "n_combos": len(rows), "m_total": rows[0]["m_total"] if rows else 0,
                          "prereg_sha256": section_sha256()})
    counts = {k: 0 for k in SCREEN_REASONS}
    counts["candidate"] = 0
    for x in rows:
        counts[x["reason"] or "candidate"] += 1
    counts["total"] = len(rows)
    rec["counts"][rnd] = counts
    reading = {}
    for tf in TFS + (None,):
        sub = [x for x in rows if x["tf"] == tf and x["n"] > 0]
        if not sub:
            continue
        means = np.array([x["mean"] for x in sub])
        best = max(sub, key=lambda x: x["mean"])
        reading[tf or "other"] = {"combos": len(sub), "plus": int((means > 0).sum()), "median_mean": _f(np.median(means)),
                                  "median_win": _f(np.median([x["win"] for x in sub])),
                                  "best_id": best["id"], "best_mean": _f(best["mean"]), "best_n": best["n"]}
    rec["reading"][rnd] = reading
    near = [dict(_brief(x), id=x["id"], round=rnd, reason=x["reason"]) for x in rows if x["reason"] in NEAR_REASONS]
    rec["near_misses"] = sorted(rec["near_misses"] + near, key=lambda x: -(x["t"] or 0))[:NEAR_TOP]
    for x in rows:
        if x["status"] == "candidate":
            rec["promoted"].append({"id": x["id"], "round": rnd, "stage": "candidate", "since": ran_on,
                                    "screen": dict(_brief(x), pips=_f(x["pips"], 2), placebo_p=_f(x["placebo_p"])),
                                    "mt5": None, "forward": None})
    return rec


def _find(rec, cid):
    for x in rec["promoted"]:
        if x["id"] == cid:
            return x
    raise KeyError(f"{cid} は昇格リストに無い")


def _stop(rec, item, why, decided_on, st):
    rec["promoted"] = [x for x in rec["promoted"] if x["id"] != item["id"]]
    rec["stopped_after_promotion"].append({"id": item["id"], "round": item["round"], "reason": why,
                                           "decided_on": decided_on, **_brief(st, ("n", "mean", "lo", "hi"))})


def apply_mt5(rec, cid, r, dates, decided_on):
    """MT5 のテスター（実ティック）で1回だけ流した結果。幅がまるごと0より上なら前向きへ、そうでなければ検証済みリストへ"""
    item = _find(rec, cid)
    if item["stage"] != "candidate":
        raise ValueError(f"{cid} は MT5 の確かめ済み（1回だけ）")
    st = cluster_stats(r, dates)
    item["mt5"] = dict(_brief(st, ("n", "mean", "lo", "hi", "win", "pf")), decided_on=decided_on,
                       diff_from_screen=_f(None if st["mean"] is None else st["mean"] - item["screen"]["mean"]))
    if st["n"] and st["lo"] is not None and st["lo"] > 0:
        item["stage"] = "mt5_ok"
    else:
        _stop(rec, item, "mt5", decided_on, st)
    return rec


def forward_verdict(st):
    if st["n"] >= GOAL:
        return "plus" if st["lo"] is not None and st["lo"] > 0 else "stop"
    if st["n"] >= FWD_STOP_MIN and st["hi"] is not None and st["hi"] < 0:
        return "stop"
    return None


def apply_forward(rec, cid, r, dates, today):
    """前向き（ふるい分けの実行日より後に入った取引だけ）。一度数えた取引は減らない。判定が出たら固定"""
    item = _find(rec, cid)
    if item["stage"] == "plus":
        return rec
    if item["stage"] != "mt5_ok":
        raise ValueError(f"{cid} はまだ MT5 の確かめを通っていない")
    since = item["since"]
    if any(str(d)[:10] <= since for d in dates):
        raise ValueError(f"{cid}: 実行日 {since} 以前の取引が混ざっている（前向きは実行日より後だけ）")
    before = (item["forward"] or {}).get("n", 0)
    if len(r) < before:
        raise ValueError(f"{cid}: 前向きの取引が減った（{before}→{len(r)}）。数えた取引は数え直さない")
    if len(r) > GOAL:                       # 1000回に届いた日で判定する（それより後は数えない）
        r, dates = list(r)[:GOAL], list(dates)[:GOAL]
    st = cluster_stats(r, dates)
    item["forward"] = dict(_brief(st, ("n", "mean", "lo", "hi", "win")), updated=today)
    v = forward_verdict(st)
    if v == "plus":
        item["stage"], item["forward"]["decided_on"] = "plus", today
    elif v == "stop":
        _stop(rec, item, "fwd", today, st)
    return rec


def write_record(rec, path=OUT_JSON):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, ensure_ascii=False, indent=1)
        fh.write("\n")


def write_full_csv(rows, path):
    """全部の組み合わせの表（手元専用。research/ の下に置く）"""
    keys = ["id", "round", "tf", "n", "win", "mean", "lo", "hi", "t", "p", "pf", "mdd", "pips", "bh", "status", "reason",
            "placebo_p", "placebo_mean", "half_1", "half_2", "period_1", "period_2", "period_3", "period_4", "m_total"]
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(keys)
        for x in rows:
            y = dict(x, half_1=x["half"][0], half_2=x["half"][1],
                     **{f"period_{i + 1}": v for i, v in enumerate(x["periods"])})
            w.writerow(["" if y.get(k) is None else (_f(y[k], 6) if isinstance(y[k], float) else y[k]) for k in keys])


def describe(rec, cid):
    """名前を読める言葉に（記録の labels にあれば）。例 M6-M15-E07-S2P4 → 15分足・平均足の色・パラボリックSAR × MACD の下抜け"""
    labels = (rec or {}).get("labels") or {}
    parts = str(cid).split("-")
    if len(parts) < 4:
        return ""
    tf = {"M5": "5分足", "M15": "15分足", "H1": "1時間足"}.get(parts[1], parts[1])
    ent, ex = parts[2], parts[3]
    stop, take = ex[:2], ex[2:]
    names = [labels.get(ent), labels.get(stop), labels.get(take)]
    if not any(names):
        return tf
    return f"{tf}・入口 {names[0] or ent}・損切り {names[1] or stop}・利確 {names[2] or take}"
