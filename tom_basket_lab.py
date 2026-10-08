# -*- coding: utf-8 -*-
"""J41 日本の早い月末月初（R3 Q3 の窓）を、売買代金の大きい個別株の籠で、引け成行どうしで取る。
2026-10-08 登録・オーナー「両方登録して進めてください」。PILLAR_PREREG.md「J41」。

籠＝その日の前の日の売買代金10億円以上の全銘柄（J31 と同じ行）。籠の1日の損益率＝その日の籠の銘柄の終値どうしの損益率の平均。
窓＝月の最後から6日目の引けで買い、翌月の2日目の引けで売る（7日分）− 費用 0.02％。比べる相手＝同じ月のふつうの日の平均 × 7。
判定＝月ごとの差の平均の 95％ の幅が3つの時代すべてで0より上なら ✅。**目隠しではない**（指数の窓は R3 で数えた）。

⚠️ 決まりは PILLAR_PREREG.md「J41」と下の定数に固定。行は J31（auction_lab.load・prevday_lab.stock_rows）、500銘柄未満の日の除外は
   prevgap_lab.idio_gap と同じ。窓は R3 Q3（calendar_lab）と同じ決め方。
⚠️ 出力（tom-basket-lab.json / .md）は集計だけ・銘柄名とコードは出さない（SYNC禁忌）。

実行: python tom_basket_lab.py --check   （点検だけ＝時代ごとの月の数と籠の銘柄数。損益は数えない・何も書き出さない）
      python tom_basket_lab.py           （本番。Actions の tom-basket-lab.yml から手動で・1回だけ）
"""
import datetime as dt
import json
import sys

import numpy as np

import auction_lab as AU
import highs_trap_lab as T
import jp_bars
import pillar_lab as P
import prevgap_lab as PG

OUT_JSON, OUT_MD = "tom-basket-lab.json", "tom-basket-lab.md"
C = AU.C
ERAS = AU.ERAS
TV_MIN = 10.0                 # 前の日の売買代金10億円以上
TIERS = ((10.0, 30.0, "10〜30億円"), (30.0, 100.0, "30〜100億円"), (100.0, np.inf, "100億円以上"))
TOP = 10
BACK, AHEAD = 5, 2            # 月の最後の5日＋翌月の最初の2日（月の最後から6日目の引けで買う）
WIN = BACK + AHEAD
COST = AU.LONG_COST           # 0.02％
ALPHA = 0.05
N_BOOT = 10000
OK, NEW_ONLY, OLD_ONLY, NONE = "✅ 3つの時代とも窓が強い", "△ 最近だけ", "△ 昔だけ", "✕ 窓の強さは見えない"


# ════════════════════ 籠と窓 ════════════════════

def daily_returns(A):
    """行ごとの終値どうしの損益率＝（1＋窓）×（1＋寄り→大引け）− 1"""
    return (1 + A[:, C["gap"]]) * (1 + A[:, C["rclose"]]) - 1


def basket(A, r, lo=TV_MIN, hi=np.inf):
    """→ {日: 籠の1日の損益率}（前の日の売買代金が lo 以上 hi 未満の銘柄の平均）"""
    tv = A[:, C["turnover"]]
    m = (tv >= lo) & (tv < hi) & np.isfinite(r)
    days, inv = np.unique(A[m, C["day"]], return_inverse=True)
    sums = np.bincount(inv, weights=r[m])
    cnt = np.bincount(inv)
    return {int(d): float(s / n) for d, s, n in zip(days, sums, cnt)}


def windows(days):
    """取引日（序数・昇順）→ [(買う日, 窓の7日, ふつうの日)]（R3 Q3 と同じ決め方）"""
    by_month = {}
    for d in days:
        x = dt.date.fromordinal(int(d))
        by_month.setdefault((x.year, x.month), []).append(int(d))
    keys = sorted(by_month)
    out = []
    for k, nk in zip(keys, keys[1:]):
        m, n = by_month[k], by_month[nk]
        if len(m) < BACK + 1 + AHEAD or len(n) < AHEAD:
            continue
        out.append((m[-BACK - 1], m[-BACK:] + n[:AHEAD], m[AHEAD:-BACK]))
    return out


def month_rows(b, wins):
    """→ [(買う日, 窓の損益（費用後）, ふつうの日 × 7, 差)]。籠の値が欠ける窓は入れない"""
    out = []
    for buy, w, normal in wins:
        if not all(d in b for d in w):
            continue
        nv = [b[d] for d in normal if d in b]
        if not nv:
            continue
        win = float(np.prod([1 + b[d] for d in w]) - 1 - COST)
        base = float(np.mean(nv) * WIN)
        out.append((buy, win, base, win - base))
    return out


def day_index(A):
    """日ごとの行の範囲（A は日の順に並べてあること）→ {日: (始め, 終わり)}"""
    days, start = np.unique(A[:, C["day"]], return_index=True)
    end = np.r_[start[1:], len(A)]
    return {int(d): (int(s), int(e)) for d, s, e in zip(days, start, end)}


def top_window(A, r, idx, buy, w, k=TOP):
    """買う日の行の売買代金（＝その前の日）の大きい順に k 銘柄を、7日そのまま持った平均（費用後）。7日そろう銘柄だけ"""
    if buy not in idx:
        return None
    s, e = idx[buy]
    tv = A[s:e, C["turnover"]]
    pick = A[s:e, C["code"]][np.argsort(-tv)][:k]
    prod = {c: 1.0 for c in pick}
    seen = {c: 0 for c in pick}
    for d in w:
        if d not in idx:
            return None
        s, e = idx[d]
        codes, rr = A[s:e, C["code"]], r[s:e]
        for c, x in zip(codes[np.isin(codes, pick)], rr[np.isin(codes, pick)]):
            if np.isfinite(x):
                prod[c] *= 1 + x
                seen[c] += 1
    vals = [prod[c] - 1 - COST for c in pick if seen[c] == len(w)]
    return float(np.mean(vals)) if vals else None


def band(x, alpha=ALPHA, n_boot=N_BOOT, seed=P.SEED):
    x = np.asarray(x, float)
    if len(x) < 5:
        return {"n": len(x), "mean": float(x.mean()) if len(x) else None, "lo": None, "hi": None}
    rng = np.random.default_rng(seed)
    sims = np.concatenate([x[rng.integers(0, len(x), (1000, len(x)))].mean(1) for _ in range(n_boot // 1000)])
    lo, hi = np.percentile(sims, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return {"n": len(x), "mean": float(x.mean()), "lo": float(lo), "hi": float(hi)}


def plus(q):
    return q.get("lo") is not None and q["lo"] > 0


def verdict(by_era):
    p = [plus(by_era[k]) for k, _, _ in ERAS]
    if all(p):
        return OK
    if p[2]:
        return NEW_ONLY
    if p[0] and p[1]:
        return OLD_ONLY
    return NONE


def era_of(d):
    for key, _, span in ERAS:
        if dt.date.fromisoformat(span[0]).toordinal() <= d <= dt.date.fromisoformat(span[1]).toordinal():
            return key
    return None


def _mean(x):
    return float(np.mean(x)) if len(x) else None


def analyze(A):
    A, _ = PG.idio_gap(A)                       # 500銘柄未満の日を除く
    A = A[np.argsort(A[:, C["day"]], kind="stable")]
    r = daily_returns(A)
    idx = day_index(A)
    days = np.unique(A[:, C["day"]])
    wins = windows(days)
    main = month_rows(basket(A, r), wins)
    tiers = {name: month_rows(basket(A, r, lo, hi), wins) for lo, hi, name in TIERS}
    res = {"eras": {}, "judge": {}, "read": {}}
    for key, name, span in ERAS:
        rows = [x for x in main if era_of(x[0]) == key]
        res["eras"][key] = {"name": name, "months": len(rows),
                            "first": dt.date.fromordinal(rows[0][0]).isoformat() if rows else None,
                            "last": dt.date.fromordinal(rows[-1][0]).isoformat() if rows else None}
        diffs = [x[3] for x in rows]
        res["judge"][key] = band(diffs)
        half = len(rows) // 2
        tops = [top_window(A, r, idx, buy, w) for buy, w, _ in [x for x in wins if era_of(x[0]) == key]]
        tops = [t for t in tops if t is not None]
        res["read"][key] = {"win_mean": _mean([x[1] for x in rows]), "win_up": _mean([x[1] > 0 for x in rows]),
                            "normal_mean": _mean([x[2] for x in rows]),
                            "early": _mean(diffs[:half]), "late": _mean(diffs[half:]),
                            "tiers": {n: {"win_mean": _mean([x[1] for x in t if era_of(x[0]) == key]),
                                          "diff_mean": _mean([x[3] for x in t if era_of(x[0]) == key])} for n, t in tiers.items()},
                            "top10_win_mean": _mean(tops), "top10_months": len(tops)}
    res["summary"] = verdict(res["judge"])
    return res


def verdicts_of(res, today):
    if res["summary"] != NONE:
        return {}
    q, rd = res["judge"]["e3"], res["read"]["e3"]
    return {"Q1": {"status": "stop", "decided_on": today, "n": q["n"], "mean": q["mean"], "lo": q["lo"], "hi": q["hi"],
                   "reason": "過去のデータで1回だけ数えて窓の強さは見えない（窓 − ふつうの日・2023〜2026年の数字）"}}


def check_summary(A, missing, n_codes, store):
    """点検だけ＝時代ごとの月の数と籠の銘柄数（損益は数えない）"""
    B, _ = PG.idio_gap(A)
    days = np.unique(B[:, C["day"]])
    wins = windows(days)
    tv = B[:, C["turnover"]]
    out = {"n_codes": n_codes, "missing": {k: len(v) for k, v in missing.items()}, "rows": int(len(A)), "store": store, "eras": {}}
    for key, _, _ in ERAS:
        ws = [w for w in wins if era_of(w[0]) == key]
        dd = np.array(sorted({d for _, w, _ in ws for d in w}))
        m = np.isin(B[:, C["day"]], dd) & (tv >= TV_MIN)
        per_day = np.bincount(np.unique(B[m, C["day"]], return_inverse=True)[1]) if m.any() else np.array([0])
        out["eras"][key] = {"months": len(ws), "basket_per_day_min": int(per_day.min()), "basket_per_day_median": float(np.median(per_day))}
    return out


# ════════════════════ 書く ════════════════════

def _p(x, d=2):
    return "—" if x is None else f"{x * 100:+.{d}f}％"


def render_md(res):
    L = ["# J41 日本の早い月末月初（R3 Q3 の窓）を、売買代金の大きい個別株の籠で、引け成行どうしで取る", "",
         f"更新: {res.get('generated_at', '')}（事前登録＝`PILLAR_PREREG.md`「J41」・指紋 `{(res.get('prereg_sha256') or '')[:12]}`）", ""]
    r = res.get("result") or {}
    if "error" in r:
        return "\n".join(L + [f"⚠️ 計算できず：{r['error']}", "", "※ 研究の記録です。投資助言ではありません。"]) + "\n"
    L += ["**目隠しではない**（指数の窓は R3 で数えた）。籠＝その日の前の日の売買代金10億円以上の全銘柄の、終値どうしの損益率の平均。"
          f"窓＝月の最後から6日目の引けで買い、翌月の2日目の引けで売る（7日分・費用 {COST * 100:.2f}％ を引く）。比べる相手＝同じ月のふつうの日の平均 × 7。"
          "幅は 95％（月を引き直す 10,000回）。", "", "## まとめ", "",
          f"**{r['summary']}**", "", "| 時代 | 月の数 | 窓 − ふつうの日 × 7 | 95％の幅 | 前半／後半 | 窓そのもの（費用後） | 窓で上げた月 | ふつうの日 × 7 |",
          "|---|---:|---:|---|---|---:|---:|---:|"]
    for key, e in r["eras"].items():
        q, rd = r["judge"][key], r["read"][key]
        bandtxt = "—" if q["lo"] is None else f"{_p(q['lo'])}〜{_p(q['hi'])}"
        L.append(f"| {e['name']} | {e['months']} | {_p(q['mean'])} | {bandtxt} | {_p(rd['early'])}／{_p(rd['late'])} | {_p(rd['win_mean'])} | "
                 f"{'—' if rd['win_up'] is None else format(rd['win_up'] * 100, '.0f') + '％'} | {_p(rd['normal_mean'])} |")
    L += ["", "## 読むための表（判定しない）", "", "| 時代 | " + " | ".join(f"{n}：窓／差" for _, _, n in TIERS) + " | 上位10銘柄の窓（費用後） |",
          "|---|" + "---|" * (len(TIERS) + 1)]
    for key, e in r["eras"].items():
        rd = r["read"][key]
        cells = [f"{_p(rd['tiers'][n]['win_mean'])}／{_p(rd['tiers'][n]['diff_mean'])}" for _, _, n in TIERS]
        L.append(f"| {e['name']} | " + " | ".join(cells) + f" | {_p(rd['top10_win_mean'])}（{rd['top10_months']}か月） |")
    L += ["", "## 注意", "",
          "- 籠は毎日同じ金額ずつ持つ形の近似（上位10銘柄だけは買った日の銘柄をそのまま7日持った平均）",
          "- 3月・9月などの月末は配当の権利落ちと重なる（終値が下がる分も損益に入る）。いま上場している銘柄だけ",
          "- 月に1回なので回数が少ない", "", "---", "",
          "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def main(argv):
    res = {"generated_at": dt.datetime.now(P.JST).isoformat(timespec="minutes"), "prereg_file": P.PREREG,
           "prereg_sha256": P.prereg_sha256()}
    try:
        stocks, list_date = jp_bars.load_universe()
        codes = sorted(stocks)
        A, missing, drops = AU.load(codes, jp_bars.fetcher())
        store = jp_bars.info()
        res["price_store"] = store
        if "--check" in argv:
            print(json.dumps(check_summary(A, missing, len(codes), store), ensure_ascii=False, indent=1))
            return 0
        if not store or store.get("daily_range") != jp_bars.FULL_DAILY:
            raise RuntimeError("値段の置き場の日足が全期間版ではない（先に jp-bars-cache を回す）")
        if len(set(missing["daily"])) > T.MAX_MISSING * len(codes):
            raise RuntimeError("日足を取れなかった銘柄が5％超。偏った組で数えない（取り直す）")
        res["result"] = dict(analyze(A), n_codes=len(codes), list_date=list_date,
                             n_missing={k: len(v) for k, v in missing.items()}, n_dropped=drops["n"])
        res.update(kind="backtest", titles={"Q1": "日本の早い月末月初を個別株の籠で（前の日の売買代金10億円以上・引け成行どうし・窓 − ふつうの日・2006〜2026-09・1回だけ数えた）"},
                   verdicts=verdicts_of(res["result"], dt.datetime.now(P.JST).date().isoformat()))
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        if "--check" in argv:
            return 1
        res["result"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1, default=str)
    md = render_md(res)
    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
