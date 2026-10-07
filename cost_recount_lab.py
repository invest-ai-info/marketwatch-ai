# -*- coding: utf-8 -*-
"""J24 J19・J23 の費用の数え直し（偏りの小さい見積もり）。2026-10-07 登録・オーナー「一二を登録して続けてください」。
PILLAR_PREREG.md「J24」。

J19・J23 の費用＝Abdi & Ranaldo (2017) の「2日ごとの値を0で切ってから平均」（bounce_cost_lab.ar_spread）は、値動きの大きい株ほど上に偏る。
新しい見積もり＝その朝より前の60営業日の 4(c_t−η_t)(c_t−η_{t+1}) を**まず平均し**、0より小さければ0にしてから平方根（下限 往復0.1％は同じ）。
それ以外はすべて J19・J23 と同じ＝bounce_cost_lab.analyze／dip_lab.analyze をそのまま使い、費用の列だけを入れ替える。

⚠️ 目隠しではない（費用前の数字を見たあとの登録）。元の判定は書き換えない＝「数え直し」として並べるだけ。
⚠️ 出力（cost-recount-lab.json / .md）は集計だけ・銘柄名とコードは出さない（SYNC禁忌）。

実行: python cost_recount_lab.py --check   （点検だけ＝行数と2つの見積もりの費用の中央値。損益は数えない・何も書き出さない）
      python cost_recount_lab.py           （本番。Actions の cost-recount-lab.yml から手動で・1回だけ）
"""
import datetime as dt
import json
import sys

import numpy as np

import bounce_cost_lab as BC
import dip_lab as D
import highs_trap_lab as T
import highs_trap_small as S
import jp_bars
import pillar_lab as P
import prevday_lab as PD

OUT_JSON, OUT_MD = "cost-recount-lab.json", "cost-recount-lab.md"
ORIG_J19, ORIG_J23 = "bounce-cost-lab.json", "dip-lab.json"
WINDOW, MIN_OBS = BC.WINDOW, BC.MIN_OBS       # 60営業日・20組（J19 と同じ）


# ════════════════════ 新しい見積もり ════════════════════

def ar_spread_avg(daily, window=WINDOW, min_obs=MIN_OBS):
    """Abdi & Ranaldo (2017) の窓で平均してから平方根を取る形。daily＝[(日付, 始, 高, 安, 終, 出来高)]（日付の順）
    → {日付: その朝より前の window 営業日の見積もり}。使う組・出来高0の扱い・朝より前の値だけ、は bounce_cost_lab.ar_spread と同じ"""
    n = len(daily)
    out = {}
    if n < 3:
        return out
    with np.errstate(invalid="ignore", divide="ignore"):
        c = np.log(np.array([r[4] for r in daily], float))
        eta = (np.log(np.array([r[2] for r in daily], float)) + np.log(np.array([r[3] for r in daily], float))) / 2
    vol = np.array([r[5] or 0 for r in daily], float)
    x = 4 * (c[:-1] - eta[:-1]) * (c[:-1] - eta[1:])
    ok = (vol[:-1] > 0) & (vol[1:] > 0) & np.isfinite(x)
    xv = np.where(ok, x, 0.0)
    cs = np.concatenate([[0.0], np.cumsum(xv)])
    cn = np.concatenate([[0], np.cumsum(ok.astype(int))])
    for j in range(2, n):
        hi = j - 1
        lo = max(0, hi - window)
        k = cn[hi] - cn[lo]
        if k >= min_obs:
            out[daily[j][0]] = float(np.sqrt(max((cs[hi] - cs[lo]) / k, 0.0)))
    return out


def _spread_for(A, day_col, sp):
    m = {dt.date.fromisoformat(d).toordinal(): v for d, v in sp.items()}
    return np.array([m.get(int(o), np.nan) for o in A[:, day_col]], float)


# ════════════════════ 行 ════════════════════

def rows_j19(ci, daily, m5, h1, sp, drops=None):
    """J19 と同じ行（bounce_cost_lab.stock_rows）で、費用の列だけ新しい見積もり"""
    A = PD.stock_rows(ci, daily, m5, h1, first=BC.SELECT[0], last=PD.NEW[1], recent_from=PD.NEW[0], drops=drops)
    if not len(A):
        return np.zeros((0, len(BC.COLS)))
    return np.hstack([A, _spread_for(A, PD.C["day"], sp).reshape(-1, 1)])


def rows_j23(ci, daily, m5, h1, sp, drops=None):
    """J23 と同じ行（dip_lab.stock_rows）で、費用の列だけ新しい見積もり → (行, 元の見積もり)"""
    A = D.stock_rows(ci, daily, m5, h1, drops=drops)
    if not len(A):
        return A, np.zeros(0)
    old = A[:, D.C["spread"]].copy()
    A[:, D.C["spread"]] = _spread_for(A, D.C["day"], sp)
    return A, old


# ════════════════════ 費用の比べ ════════════════════

def _med(x):
    x = x[np.isfinite(x)]
    return float(np.median(BC.cost(x))) if len(x) else None


def cost_table(A, old):
    """J23 の3つの窓ごとに、2つの見積もりの往復の費用の中央値（売買代金ごと・前日比 −3％以下まで下げた朝）"""
    S_, _ = D.samples(A)
    new = A[:, D.C["spread"]]
    tv = A[:, D.C["turnover"]]
    out = {}
    for key, _, lo_col, _ in D.WINDOWS:
        m = S_[key] & np.isfinite(old)
        dip = m & (A[:, D.C[lo_col]] - 1 <= D.REV_DEPTH)
        out[key] = {"all": {"old": _med(old[m]), "new": _med(new[m]), "n": int(m.sum())},
                    "dip": {"old": _med(old[dip]), "new": _med(new[dip]), "n": int(dip.sum())},
                    "turnover": {lab: {"old": _med(old[m & (tv >= a) & (tv < b)]), "new": _med(new[m & (tv >= a) & (tv < b)])}
                                 for lab, a, b in S.TURNOVER_BANDS}}
    return out


def _load_json(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def originals():
    """元の判定（書き換えない・並べるだけ）"""
    o19, o23 = _load_json(ORIG_J19), _load_json(ORIG_J23)
    r19 = (o19 or {}).get("result") or {}
    r23 = (o23 or {}).get("result") or {}
    return {"j19": {"chosen": r19.get("chosen"), "overall": r19.get("overall")},
            "j23": {"summary": r23.get("summary") or {}}}


# ════════════════════ 読む ════════════════════

def load(codes, fetch):
    p19, p23, olds = [], [], []
    missing, d19, d23 = {"daily": [], "h1": [], "m5": []}, {"n": 0}, {"n": 0}
    for i, code in enumerate(codes):
        d = fetch(code, "1d", jp_bars.FULL_DAILY)
        h1 = T._first(fetch, code, "60m", T.H1_RANGES)
        m5 = T._first(fetch, code, "5m", T.M5_RANGES)
        if not d:
            missing["daily"].append(code)
            continue
        if not h1:
            missing["h1"].append(code)
        if not m5:
            missing["m5"].append(code)
        daily = sorted({t.date().isoformat(): (t.date().isoformat(), o, h, lo, c, v) for t, o, h, lo, c, v in d}.values())
        sp = ar_spread_avg(daily)
        bm5, bh1 = T._by_day(m5), T._by_day(h1)
        p19.append(rows_j19(i, daily, bm5, bh1, sp, drops=d19))
        a23, old = rows_j23(i, daily, bm5, bh1, sp, drops=d23)
        p23.append(a23)
        olds.append(old)
        if (i + 1) % 500 == 0:
            print(f"  ...{i + 1}/{len(codes)}", flush=True)
    A19 = np.vstack(p19) if p19 else np.zeros((0, len(BC.COLS)))
    A23 = np.vstack(p23) if p23 else np.zeros((0, len(D.COLS)))
    old = np.concatenate(olds) if olds else np.zeros(0)
    return A19, A23, old, missing, {"j19": d19["n"], "j23": d23["n"]}


def check_summary(A19, A23, old, missing, n_codes, store):
    ct = cost_table(A23, old)
    return {"n_codes": n_codes, "missing": {k: len(v) for k, v in missing.items()}, "store": store,
            "rows": {"j19": int(len(A19)), "j23": int(len(A23))},
            "j19_with_cost": int(np.isfinite(A19[:, BC.C["spread"]]).sum()) if len(A19) else 0,
            "cost_median": {k: {"all": v["all"], "dip": v["dip"]} for k, v in ct.items()}}


def _p(x, d=2):
    return D._p(x, d)


def _demote(md):
    """元のラボの md を節として埋め込む（見出しを2段下げる・最後の免責は1回だけにする）"""
    out = []
    for line in md.splitlines():
        if line.startswith("※ 研究の記録です") or line == "---":
            continue
        out.append("##" + line if line.startswith("#") else line)
    return "\n".join(out).rstrip()


def render_md(res):
    L = ["# J24 J19・J23 の費用の数え直し（偏りの小さい見積もり）", "",
         f"作成: {res['generated_at']}（GitHub Actions で計算）。事前登録＝`{P.PREREG}`「J24」（指紋 sha256 `{(res.get('prereg_sha256') or '')[:16]}…`）。",
         "**費用の見積もりだけを直した数え直し**（窓の中で平均してから平方根・下限 往復 0.1％）。それ以外は J19・J23 と同じ。"
         "**目隠しではない**（費用前の数字を見たあとの登録）＝元の判定は書き換えず、並べるだけ。銘柄名は出しません。**売買の決まりではない**。", ""]
    r = res.get("result") or {}
    if r.get("error"):
        return "\n".join(L + [f"- ⚠️ 計算できず: {r['error']}", ""]) + "\n"
    o = r["originals"]
    j19, j23 = r["j19"], r["j23"]
    L += [f"- 対象：置き場の一覧 {r.get('n_codes')}銘柄（いま上場している銘柄だけ）。取れなかった銘柄 {r.get('n_missing')}", "",
          "## まとめ（元の判定 → 数え直し）", "",
          f"- **J19 安く寄った株の戻り**：元＝{o['j19'].get('overall') or '—'}（選んだ形 {o['j19'].get('chosen') or 'なし'}）"
          f" → 数え直し＝**{j19.get('overall')}**（選んだ形 {j19.get('chosen') or 'なし'}）", "",
          "| J23 の指値 | 元の判定 | 数え直しの判定 | 9:30 の費用後（数え直し） | 10:00 の費用後（数え直し） |", "|---|---|---|---|---|"]
    for x in D.LEVELS:
        k = f"{x:.2f}"
        jm, jc = j23["judge"][k]["main"], j23["judge"][k]["conf"]
        L.append(f"| 前日比 −{x * 100:.0f}％ | {o['j23']['summary'].get(k, '—')} | **{j23['summary'][k]}** | "
                 f"{_p(jm.get('value'))}（{_p(jm.get('lo'))}〜{_p(jm.get('hi'))}） | {_p(jc.get('value'))}（{_p(jc.get('lo'))}〜{_p(jc.get('hi'))}） |")
    L += ["", "## 2つの見積もりの往復の費用（中央値）", "",
          "| 窓 | 朝の数 | 元（0で切ってから平均） | 新（平均してから平方根） | −3％以下まで下げた朝：元 | 新 |", "|---|---:|---:|---:|---:|---:|"]
    names = {k: n for k, n, *_ in D.WINDOWS}
    for key, v in r["costs"].items():
        L.append(f"| {names[key]} | {v['all']['n']:,} | {_p(v['all']['old'])} | {_p(v['all']['new'])} | {_p(v['dip']['old'])} | {_p(v['dip']['new'])} |")
    L += ["", "| 売買代金（9:00〜10:00 の窓の朝） | 元 | 新 |", "|---|---:|---:|"]
    for lab, v in r["costs"]["conf"]["turnover"].items():
        L.append(f"| {lab} | {_p(v['old'])} | {_p(v['new'])} |")
    L += ["", "- ⚠️ どちらの見積もりも日足からの推定で、寄りの板の厚さ（大きく買うと値が動く分）は入らない。プラスが出ても前向きの登録で確かめるまで柱にしない。",
          "", "---", "", "## 付録1：J19 の数え直しの全表", "", _demote(BC.render_md(r["j19_res"])),
          "", "## 付録2：J23 の数え直しの全表", "", _demote(D.render_md(r["j23_res"])),
          "", "---", "", "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def analyze(A19, A23, old, meta):
    j19 = BC.analyze(A19)
    j23 = D.analyze(A23)
    return {"j19": {"chosen": j19["chosen"], "overall": j19["overall"], "confirm": j19["confirm"]},
            "j23": {"summary": j23["summary"], "judge": j23["judge"]},
            "costs": cost_table(A23, old), "originals": originals(),
            "j19_res": {"generated_at": meta["generated_at"], "prereg_sha256": meta.get("prereg_sha256"), "price_store": meta.get("price_store"),
                        "result": dict(j19, n_codes=meta["n_codes"], n_missing=meta["n_missing"], n_dropped=meta["n_dropped"]["j19"])},
            "j23_res": {"generated_at": meta["generated_at"], "prereg_sha256": meta.get("prereg_sha256"),
                        "result": dict(j23, n_codes=meta["n_codes"], n_missing=meta["n_missing"], n_dropped=meta["n_dropped"]["j23"])}}


def main(argv):
    res = {"generated_at": dt.datetime.now(P.JST).isoformat(timespec="minutes"), "prereg_file": P.PREREG,
           "prereg_sha256": P.prereg_sha256()}
    try:
        stocks, list_date = jp_bars.load_universe()
        codes = sorted(stocks)
        A19, A23, old, missing, drops = load(codes, jp_bars.fetcher())
        store = jp_bars.info()
        res["price_store"] = store
        if "--check" in argv:
            print(json.dumps(check_summary(A19, A23, old, missing, len(codes), store), ensure_ascii=False, indent=1))
            return 0
        if not store or store.get("daily_range") != jp_bars.FULL_DAILY:
            raise RuntimeError("値段の置き場の日足が全期間版ではない（先に jp-bars-cache を回す）")
        bad = set(missing["daily"]) | set(missing["h1"]) | set(missing["m5"])
        if len(bad) > T.MAX_MISSING * len(codes):
            raise RuntimeError(f"日足・1時間足・5分足のどれかを取れなかった銘柄が {len(bad)}/{len(codes)}＝5％超。偏った組で判定しない（取り直す）")
        meta = {"generated_at": res["generated_at"], "prereg_sha256": res["prereg_sha256"], "price_store": store,
                "n_codes": len(codes), "n_missing": {k: len(v) for k, v in missing.items()}, "n_dropped": drops}
        res["result"] = dict(analyze(A19, A23, old, meta), n_codes=len(codes), list_date=list_date, n_missing=meta["n_missing"])
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
