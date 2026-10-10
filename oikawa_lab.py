# -*- coding: utf-8 -*-
"""OK 及川式の通貨の強弱（5分足・ロンドン時間・次の足で手じまう）。2026-10-10 登録・PILLAR_PREREG.md「OK」。

オーナー「ドル円とユーロポンドは通貨の強弱を確認する指標として取引をせず、ポンド円、ポンドドル、ユーロ円、ユーロドルを強い方に
エントリーする方法で検証をしてください。ちなみに OG（オージー＝豪ドル）シリーズは同時に同じ方向に動いたときにエントリーする形とします」。

腕A：ユーロポンド（ユーロドル÷ポンドドル）とドル円の、その5分足の向きで「強い欧州通貨 × 弱い方」を買い／「弱い欧州通貨 × 強い方」を売る
     （そのペアが同じ足で同じ向きに動いていたとき）。
腕B：豪ドル円と豪ドル米ドルが同じ足で同じ向き → ドル円の向きで相手（円かドル）を選んで、豪ドルを買う／売る。
入る＝次の足の始値・出る＝その足の終値（5分だけ持つ）。費用＝実際のスプレッド（出る側は出る時のスプレッド）。

⚠️ 決まりは PILLAR_PREREG.md「OK」と下の定数に固定。データは手元の MT5 の5分足だけ＝**手元で1回だけ**回す。
実行（手元）: python oikawa_lab.py check --dir C:\\mt5run   （足の数・時刻・スプレッドの単位だけ。損益は数えない・何も書き出さない）
             python oikawa_lab.py run   --dir C:\\mt5run   （本番・1回だけ → oikawa-lab.json（送る）・research/oikawa/oikawa-result.md（手元））
"""
import argparse
import datetime as dt
import hashlib
import json
import math
import os
import sys
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

import r4_window_lab as R4

# ════════════════════ 事前登録の値（PILLAR_PREREG.md「OK」） ════════════════════
PAIRS = ("USDJPY", "EURUSD", "GBPUSD", "EURJPY", "GBPJPY", "AUDJPY", "AUDUSD")
TRADED = ("EURUSD", "GBPUSD", "EURJPY", "GBPJPY", "AUDJPY", "AUDUSD")   # ドル円（とユーロポンド）は見るだけ
START = "2022-06-01"                 # これより前は業者のデータの欠陥で使わない
SPLIT = "2024-08-01"                 # 前半＝〜2024-07-31／後半＝2024-08-01〜（入った日）
LON = ZoneInfo("Europe/London")
SIG_FROM, SIG_TO = (8, 0), (15, 50)  # 合図の足の始まり（ロンドンの現地時刻）
BAR = pd.Timedelta(minutes=5)
N_MIN = 300
ALPHA = 0.05 / 2                     # 2つの腕
Z = 2.241402727604947                # 97.5% の幅（両側）の z
N_PERM = 2000
SEED = 20261010
HOLD = 1                             # 次の足だけ持つ
HOLD_READ = 3                        # 読むための表：15分持つ
SPREAD_PIPS_OK = (0.1, 8.0)          # ロンドン時間のスプレッドの中央値（pips）がこの外なら単位の取り違え
PREREG, SECTION = "PILLAR_PREREG.md", "## OK 及川式の通貨の強弱"
OUT_JSON = "oikawa-lab.json"
OUT_MD = os.path.join("research", "oikawa", "oikawa-result.md")
TITLES = {"OK-A": "及川式・ドル円とユーロポンドで強弱を見てポンド円・ポンドドル・ユーロ円・ユーロドルの強い方に入る（5分足・ロンドン時間・次の足で手じまう・手元の MT5）",
          "OK-B": "及川式・豪ドル円と豪ドル米ドルが同じ足で同じ向きに動いたら、ドル円で相手を選んで豪ドルに入る（5分足・ロンドン時間・次の足で手じまう・手元の MT5）"}
SURVIVED = "期間内では残った"


def point(pair):
    return 0.001 if pair.endswith("JPY") else 0.00001


def pip(pair):
    return 0.01 if pair.endswith("JPY") else 0.0001


# ════════════════════ 読み込み ════════════════════

def read_bars(path, pair):
    """ExportBarsEA の5分足 → UTC の DataFrame（open high low close＝売値・so＝始まりのスプレッド・sm＝足の中の最大スプレッド・値段の単位）。
    文字コード・区切り・見出しの有無・日付と時刻が別の列かは r4_window_lab.read_mt5_csv と同じ見分け方"""
    with open(path, "rb") as f:
        head = f.read(4)
    enc = "utf-16" if head[:2] in (b"\xff\xfe", b"\xfe\xff") else ("utf-8-sig" if head[:3] == b"\xef\xbb\xbf" else "utf-8")
    with open(path, encoding=enc, errors="replace") as f:
        first = f.readline()
    sep = max([",", "\t", ";"], key=first.count)
    has_header = not first.split(sep)[0].strip()[:1].isdigit()
    raw = pd.read_csv(path, sep=sep, encoding=enc, header=None, skiprows=1 if has_header else 0, dtype=str)
    c0 = raw.iloc[:, 0].str.strip()
    rest = raw.iloc[:, 1:]
    if rest.iloc[:, 0].str.strip().str.match(r"^\d{1,2}:\d{2}").all():
        c0 = c0 + " " + rest.iloc[:, 0].str.strip()
        rest = rest.iloc[:, 1:]
    t = R4.parse_server_time(c0)
    nums = rest.apply(lambda s: pd.to_numeric(s.str.strip(), errors="coerce"))
    idx = R4.server_to_utc(t)
    pt = point(pair)
    df = pd.DataFrame({"open": nums.iloc[:, 0].to_numpy(float), "high": nums.iloc[:, 1].to_numpy(float),
                       "low": nums.iloc[:, 2].to_numpy(float), "close": nums.iloc[:, 3].to_numpy(float),
                       "so": nums.iloc[:, 5].to_numpy(float) * pt, "sm": nums.iloc[:, 6].to_numpy(float) * pt}, index=idx)
    df = df[df.index.notna()]
    df = df[~df.index.duplicated(keep="first")].sort_index()
    return df[df.index >= pd.Timestamp(START, tz="UTC") - pd.Timedelta(days=1)]


def panel(bars):
    """ペアごとの足 → 共通の時刻（全部の和）にそろえた配列 {pair: {o, c, so, sm}}・時刻・ロンドンの時刻"""
    idx = None
    for b in bars.values():
        idx = b.index if idx is None else idx.union(b.index)
    idx = idx[idx >= pd.Timestamp(START, tz="UTC")]
    P = {}
    for p, b in bars.items():
        r = b.reindex(idx)
        P[p] = {k: r[col].to_numpy(float) for k, col in (("o", "open"), ("c", "close"), ("so", "so"), ("sm", "sm"))}
    lon = idx.tz_convert(LON)
    return P, idx, lon


def direction(o, c):
    with np.errstate(invalid="ignore"):
        d = np.sign(c - o)
    return np.where(np.isfinite(d), d, np.nan)


def in_window(lon):
    mins = lon.hour * 60 + lon.minute
    lo, hi = SIG_FROM[0] * 60 + SIG_FROM[1], SIG_TO[0] * 60 + SIG_TO[1]
    return (lon.weekday < 5) & (mins >= lo) & (mins <= hi)


# ════════════════════ 合図 ════════════════════

def signals(P, lon):
    """→ {腕: [(i, pair, s)]}（i＝合図の足の位置・s＝＋1 買い／−1 売り）と、読むための腕B の「両方に入る」"""
    d = {p: direction(P[p]["o"], P[p]["c"]) for p in P}
    with np.errstate(invalid="ignore", divide="ignore"):
        eg_c = P["EURUSD"]["c"] / P["GBPUSD"]["c"]
        eg_o = P["EURUSD"]["o"] / P["GBPUSD"]["o"]
    dE = direction(eg_o, eg_c)
    dU = d["USDJPY"]
    win = in_window(lon)
    out = {"A": [], "B": [], "B_both": []}
    for i in np.flatnonzero(win):
        u, e = dU[i], dE[i]
        if not (np.isfinite(u) and u != 0):
            continue
        if np.isfinite(e) and e != 0:
            strong, weak = ("EUR", "GBP") if e > 0 else ("GBP", "EUR")
            low, high = ("JPY", "USD") if u > 0 else ("USD", "JPY")      # 弱い方・強い方（ドル円が上げ＝円が弱い）
            lp, sp = strong + low, weak + high
            if d[lp][i] > 0:
                out["A"].append((i, lp, 1.0))
            if d[sp][i] < 0:
                out["A"].append((i, sp, -1.0))
        aj, au = d["AUDJPY"][i], d["AUDUSD"][i]
        if np.isfinite(aj) and np.isfinite(au) and aj == au and aj != 0:
            s = float(aj)
            if s > 0:
                pr = "AUDJPY" if u > 0 else "AUDUSD"
            else:
                pr = "AUDUSD" if u > 0 else "AUDJPY"
            out["B"].append((i, pr, s))
            out["B_both"] += [(i, "AUDJPY", s), (i, "AUDUSD", s)]
    return out


# ════════════════════ 1回の損益 ════════════════════

def trade(P, idx, i, pair, s, hold=HOLD):
    """合図の足 i → 次の足 e の始値で入り、e＋hold−1 の足の終値で出る。足が5分ずつ続いていなければ None。
    → (費用後の損益率, 費用前の損益率, 入った足の位置)"""
    e, x = i + 1, i + hold
    n = len(idx)
    if x >= n:
        return None
    for k in range(i, x):
        if idx[k + 1] - idx[k] != BAR:
            return None
    A = P[pair]
    o, c, so, sm = A["o"], A["c"], A["so"], A["sm"]
    if not all(np.isfinite(v) for v in (o[e], c[x], so[e])) or o[e] <= 0:
        return None
    if s > 0:
        entry, exit_ = o[e] + so[e], c[x]
    else:
        nxt = so[x + 1] if (x + 1 < n and idx[x + 1] - idx[x] == BAR and np.isfinite(so[x + 1])) else sm[x]
        if not np.isfinite(nxt):
            return None
        entry, exit_ = o[e], c[x] + nxt
    after = s * (exit_ - entry) / entry
    before = s * (c[x] - o[e]) / o[e]
    return after, before, e


def trades_of(P, idx, sig, hold=HOLD):
    rows = []
    for i, pair, s in sig:
        r = trade(P, idx, i, pair, s, hold)
        if r is not None:
            rows.append({"pair": pair, "s": s, "i": i, "after": r[0], "before": r[1], "e": r[2]})
    return rows


# ════════════════════ 物差し ════════════════════

def day_of(idx, e):
    return idx[e].tz_convert(LON).date().isoformat()


def cluster(vals, days):
    """平均と 97.5% の幅（ロンドンの日ごとのまとまり）"""
    r = np.asarray(vals, float)
    n = len(r)
    if n == 0:
        return {"n": 0, "mean": None, "lo": None, "hi": None}
    m = float(r.mean())
    _, inv = np.unique(np.asarray(days), return_inverse=True)
    s = np.bincount(inv, weights=r)
    cnt = np.bincount(inv).astype(float)
    g = len(s)
    if g < 2:
        return {"n": n, "mean": m, "lo": None, "hi": None}
    u = s - m * cnt
    se = math.sqrt(g / (g - 1) * float(np.sum(u * u))) / n
    return {"n": n, "mean": m, "lo": m - Z * se, "hi": m + Z * se}


def pools(P, idx, lon, hold=HOLD):
    """偽薬の入れ物：ロンドン時間の入れる足ぜんぶ（ペア×向き）の費用後の損益率"""
    win = np.flatnonzero(in_window(lon))
    out = {}
    for p in TRADED:
        for s in (1.0, -1.0):
            v = []
            for i in win:
                r = trade(P, idx, i, p, s, hold)
                if r is not None:
                    v.append(r[0])
            out[(p, s)] = np.asarray(v, float)
    return out


def placebo_p(rows, pool, actual, n_perm=N_PERM, seed=SEED):
    counts = {}
    for r in rows:
        counts[(r["pair"], r["s"])] = counts.get((r["pair"], r["s"]), 0) + 1
    keys = [k for k in counts if len(pool.get(k, [])) > 0]
    total = sum(counts[k] for k in keys)
    if not total:
        return None, None
    rng = np.random.default_rng(seed)
    sims = np.empty(n_perm)
    for j in range(n_perm):
        acc = 0.0
        for k in keys:
            pl = pool[k]
            acc += float(pl[rng.integers(0, len(pl), counts[k])].sum())
        sims[j] = acc / total
    return float((np.sum(sims >= actual) + 1) / (n_perm + 1)), float(sims.mean())


def judge(st, p, old, new):
    if st["n"] < N_MIN:
        return "検定不能"
    if st["lo"] is None or st["lo"] <= 0:
        return "費用後マイナス" if (st["hi"] is not None and st["hi"] < 0) else "0と区別できない"
    if p is None or p >= ALPHA:
        return "でたらめな足と差なし"
    if not ((old or 0) > 0 and (new or 0) > 0):
        return "前半と後半で割れた"
    return SURVIVED


def summarize(rows, idx, pool=None, n_perm=N_PERM):
    if not rows:
        return {"n": 0, "verdict": "検定不能"}
    after = [r["after"] for r in rows]
    days = [day_of(idx, r["e"]) for r in rows]
    st = cluster(after, days)
    old = [a for a, d in zip(after, days) if d < SPLIT]
    new = [a for a, d in zip(after, days) if d >= SPLIT]
    p, pm = placebo_p(rows, pool, st["mean"], n_perm) if pool is not None else (None, None)
    before = np.array([r["before"] for r in rows])
    pairs = sorted({r["pair"] for r in rows})
    out = dict(st, placebo_p=p, placebo_mean=pm, old_mean=float(np.mean(old)) if old else None, new_mean=float(np.mean(new)) if new else None,
               old_n=len(old), new_n=len(new), before_mean=float(before.mean()), cost_mean=float(before.mean() - np.mean(after)),
               win=float(np.mean(np.asarray(after) > 0)),
               by_pair={p_: {"n": sum(1 for r in rows if r["pair"] == p_),
                             "after": float(np.mean([r["after"] for r in rows if r["pair"] == p_])),
                             "before": float(np.mean([r["before"] for r in rows if r["pair"] == p_]))} for p_ in pairs},
               by_side={("買い" if s > 0 else "売り"): {"n": sum(1 for r in rows if r["s"] == s),
                                                    "after": float(np.mean([r["after"] for r in rows if r["s"] == s])),
                                                    "before": float(np.mean([r["before"] for r in rows if r["s"] == s]))}
                        for s in (1.0, -1.0) if any(r["s"] == s for r in rows)})
    if pool is not None:
        out["verdict"] = judge(st, p, out["old_mean"], out["new_mean"])
    return out


def section_sha256(path=PREREG, head=SECTION):
    text = open(path, encoding="utf-8").read()
    i = text.find("\n" + head)
    if i < 0:
        return None
    j = text.find("\n## ", i + 1)
    return hashlib.sha256(text[i + 1:(j if j >= 0 else len(text))].encode("utf-8")).hexdigest()


def analyze(P, idx, lon, n_perm=N_PERM):
    sig = signals(P, lon)
    pool = pools(P, idx, lon)
    res = {}
    for arm in ("A", "B"):
        rows = trades_of(P, idx, sig[arm])
        res[arm] = summarize(rows, idx, pool, n_perm)
        rows3 = trades_of(P, idx, sig[arm], hold=HOLD_READ)
        res[arm]["read_hold3"] = {k: v for k, v in summarize(rows3, idx).items() if k in ("n", "mean", "lo", "hi", "before_mean", "cost_mean", "win")}
    both = trades_of(P, idx, sig["B_both"])
    res["B"]["read_both_pairs"] = {k: v for k, v in summarize(both, idx).items() if k in ("n", "mean", "lo", "hi", "before_mean", "cost_mean", "win")}
    return res


def verdicts_of(res, today):
    out = {}
    for arm, key in (("A", "OK-A"), ("B", "OK-B")):
        a = res.get(arm) or {}
        v = a.get("verdict")
        if v and v != SURVIVED:
            out[key] = {"status": "stop", "decided_on": today, "n": a.get("n"), "mean": a.get("mean"), "lo": a.get("lo"), "hi": a.get("hi"),
                        "reason": f"{v}（過去のデータ・1回だけ数えた・手元の MT5 の5分足・費用前 {a.get('before_mean', 0) * 1e4:+.2f}bp・勝率 {a.get('win', 0) * 100:.1f}%）"}
    return out


def render_md(rec):
    bp = lambda v: "—" if v is None else f"{v * 1e4:+.2f}bp"
    L = ["# OK 及川式の通貨の強弱（5分足・ロンドン時間・次の足で手じまう）", "",
         f"更新: {rec.get('generated_jst')}（事前登録＝`PILLAR_PREREG.md`「OK」・節の指紋 `{(rec.get('prereg_sha256') or '')[:12]}`）・データ {rec.get('data')}", "",
         "| 腕 | 判定 | 回数 | 費用後の平均 | 97.5%の幅 | 偽薬 p | 前半／後半 | 費用前 | 1回の費用 | 勝率 |", "|---|---|---:|---:|---|---:|---|---:|---:|---:|"]
    for arm, key in (("A", "OK-A"), ("B", "OK-B")):
        a = rec["arms"].get(arm) or {}
        if not a.get("n"):
            L.append(f"| {key} | {a.get('verdict')} | 0 | | | | | | | |")
            continue
        L.append(f"| {key} | **{a['verdict']}** | {a['n']} | {bp(a['mean'])} | {bp(a['lo'])}〜{bp(a['hi'])} | "
                 f"{'—' if a['placebo_p'] is None else format(a['placebo_p'], '.4f')} | {bp(a['old_mean'])}／{bp(a['new_mean'])} | "
                 f"{bp(a['before_mean'])} | {bp(a['cost_mean'])} | {a['win'] * 100:.1f}% |")
    L += ["", "## 読むための表（判定しない）", ""]
    for arm, key in (("A", "OK-A"), ("B", "OK-B")):
        a = rec["arms"].get(arm) or {}
        if not a.get("n"):
            continue
        L += [f"### {key}", "", "- ペアごと（回数・費用後・費用前）：" + "／".join(f"{p} {v['n']}・{bp(v['after'])}・{bp(v['before'])}" for p, v in a["by_pair"].items()),
              "- 買い売りごと：" + "／".join(f"{k} {v['n']}・{bp(v['after'])}・{bp(v['before'])}" for k, v in a["by_side"].items()),
              f"- 15分持った場合：{a['read_hold3'].get('n')}回・費用後 {bp(a['read_hold3'].get('mean'))}・費用前 {bp(a['read_hold3'].get('before_mean'))}"]
        if "read_both_pairs" in a:
            b = a["read_both_pairs"]
            L.append(f"- 豪ドル円と豪ドル米ドルの両方に入った場合：{b.get('n')}回・費用後 {bp(b.get('mean'))}・費用前 {bp(b.get('before_mean'))}")
        L.append("")
    L += ["---", "", "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def load(folder):
    bars = {p: read_bars(os.path.join(folder, f"m5tick_{p}.csv"), p) for p in PAIRS}
    return bars


def check(folder):
    bars = load(folder)
    P, idx, lon = panel(bars)
    win = in_window(lon)
    rep = {"prereg_sha256": section_sha256(), "bars": {}, "london_bars": int(win.sum())}
    for p, b in bars.items():
        bl = b[b.index >= pd.Timestamp(START, tz="UTC")]
        lw = in_window(bl.index.tz_convert(LON))
        med = float(np.median(bl["so"].to_numpy()[lw])) / pip(p) if lw.any() else None
        rep["bars"][p] = {"rows": int(len(bl)), "first_utc": str(bl.index.min()), "last_utc": str(bl.index.max()),
                          "london_bars": int(lw.sum()), "spread_median_pips": med,
                          "spread_ok": bool(med is not None and SPREAD_PIPS_OK[0] <= med <= SPREAD_PIPS_OK[1])}
    sig = signals(P, lon)
    rep["signals"] = {k: len(v) for k, v in sig.items()}            # 合図の数だけ（損益は数えない）
    return rep


def run(folder, n_perm=N_PERM):
    bars = load(folder)
    P, idx, lon = panel(bars)
    res = analyze(P, idx, lon, n_perm)
    today = dt.datetime.now(ZoneInfo("Asia/Tokyo")).date().isoformat()
    rec = {"kind": "backtest", "unit": "pct", "source": "手元の MT5（BigBoss）の実ティックの5分足",
           "generated_jst": dt.datetime.now(ZoneInfo("Asia/Tokyo")).isoformat(timespec="minutes"),
           "prereg_sha256": section_sha256(), "data": f"{str(idx.min())[:10]}〜{str(idx.max())[:10]}",
           "titles": TITLES, "verdicts": verdicts_of(res, today), "arms": res}
    return rec


def _clean(x):
    if isinstance(x, float):
        return None if not math.isfinite(x) else round(x, 8)
    if isinstance(x, dict):
        return {str(k): _clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_clean(v) for v in x]
    return x


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["check", "run"])
    ap.add_argument("--dir", default=r"C:\mt5run", help="m5tick_*.csv のあるフォルダ")
    a = ap.parse_args(argv)
    if a.mode == "check":
        print(json.dumps(_clean(check(a.dir)), ensure_ascii=False, indent=1))
        return 0
    rec = _clean(run(a.dir))
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=1)
    os.makedirs(os.path.dirname(OUT_MD), exist_ok=True)
    md = render_md(rec)
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
