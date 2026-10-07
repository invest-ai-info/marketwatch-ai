# -*- coding: utf-8 -*-
"""J27 最初の5分で大きく動いた株は、足を1本空けても 9:30 までに戻るか（J22 の W1・W2 が売り買いの差の見かけかを切り分ける）。
2026-10-07 夜 登録・オーナー「続けてください」。PILLAR_PREREG.md「J27」。

J22 の W2（最初の5分で −1％以下 → 9:05→9:30 で戻る）は、オーナーの取引時間の中で初めての買い側の候補。ただし 9:05 の値は
急に下げた株では売りの値で付きやすく、売り買いの差の跳ね返りでも「戻った」ように見える。足を1本空けて 9:10→9:30 で数え直し、
銘柄ごとの往復の費用（J24 の見積もり）を引いても残るかを見る。J22 と同じ朝＝独立した確かめではなく、見かけかどうかの切り分け。

⚠️ 決まりは PILLAR_PREREG.md「J27」と下の定数に固定。値は yori_lab.price_at、幅と向きは open30_lab の measure・direction、
   費用は cost_recount_lab.ar_spread_avg をそのまま使う。
⚠️ 出力（open5-skip-lab.json / .md）は集計だけ・銘柄名とコードは出さない（SYNC禁忌）。

実行: python open5_skip_lab.py --check   （点検だけ＝朝の数と組ごとの件数。損益は数えない・何も書き出さない）
      python open5_skip_lab.py           （本番。Actions の open5-skip-lab.yml から手動で・1回だけ）
      python open5_skip_lab.py --relist  （数え直さずに、書き出した結果へ検証済みリストの欄を足す）
"""
import datetime as dt
import json
import sys

import numpy as np

import bounce_cost_lab as BC
import cost_recount_lab as CR
import gap_lab as GL
import highs_trap_lab as T
import highs_trap_small as S
import jp_bars
import main_field_lab as MF
import open30_lab as O
import pillar_lab as P
import yori_lab as Y

OUT_JSON, OUT_MD = "open5-skip-lab.json", "open5-skip-lab.md"
COLS = ("day", "code", "f5", "r905", "r910", "r915", "r905_910", "turnover", "cost")
C = {k: i for i, k in enumerate(COLS)}
MIN_STOCKS = 500
BIG, FLAT = 0.01, 0.003                    # 最初の5分 ±1％・ふつう ±0.3％未満（J22 と同じ）
N_Q = 3
ALPHA = 0.05 / N_Q                         # 98.33％ の幅
DAILY_RANGE = "1y"                         # 費用の見積もり（その朝より前の60営業日）に足りる長さ
UP, DOWN = O.UP, O.DOWN
DEPTHS = (("−1〜−2％", -0.02, -0.01), ("−2〜−4％", -0.04, -0.02), ("−4％以下", -1.0, -0.04))


# ════════════════════ 行 ════════════════════

def stock_rows(ci, daily, m5):
    """1銘柄の朝ごとの行。9:00 の足がある朝だけ。値は寄り＝日足の始値／各時刻＝その時刻より前の最後の5分足の終値"""
    sp = CR.ar_spread_avg(daily)
    pos = {r[0]: i for i, r in enumerate(daily)}
    out = []
    for day, bars in sorted(m5.items()):
        k = pos.get(day)
        if k is None or k == 0:
            continue
        b = sorted(bars)
        if (b[0][0].hour, b[0][0].minute) != (9, 0):
            continue
        op = daily[k][1]
        p = {t: Y.price_at(b, t) for t in ("09:05", "09:10", "09:15", "09:30")}
        if not op or op <= 0 or any(v is None or v <= 0 for v in p.values()):
            continue
        if any(abs(v / op - 1) > T.MAX_MOVE for v in p.values()):
            continue
        prev = daily[k - 1]
        tv = prev[4] * (prev[5] or 0) / 1e8
        cost = max(sp[day], BC.COST_FLOOR) if day in sp else np.nan
        out.append((dt.date.fromisoformat(day).toordinal(), ci, p["09:05"] / op - 1, p["09:30"] / p["09:05"] - 1,
                    p["09:30"] / p["09:10"] - 1, p["09:30"] / p["09:15"] - 1, p["09:10"] / p["09:05"] - 1, tv, cost))
    return np.array(out, float).reshape(-1, len(COLS))


def mornings(A):
    """9:10→9:30 が数えられる銘柄が MIN_STOCKS 以上の朝の行だけ"""
    if not len(A):
        return A
    u, inv, n = np.unique(A[:, C["day"]], return_inverse=True, return_counts=True)
    return A[(n >= MIN_STOCKS)[inv]]


def groups(A):
    f5 = A[:, C["f5"]]
    return {"down": f5 <= -BIG, "up": f5 >= BIG, "flat": np.abs(f5) < FLAT}


# ════════════════════ 判定 ════════════════════

def _first(mu):
    return mu[0]


def net_mean(A, m, alpha=ALPHA):
    """下げた組を 9:10 に買って 9:30 に売る＝9:10→9:30 − 銘柄ごとの往復の費用。平均と、日と銘柄で引き直した広いほうの幅・前半後半"""
    v = A[:, C["r910"]] - A[:, C["cost"]]
    ok = m & np.isfinite(v)
    g = np.where(ok, 0, -1)
    out = {"n": int(ok.sum()), "value": None, "lo": None, "hi": None, "early": None, "late": None}
    if out["n"] < T.MIN_N:
        return out
    pt, lo_d, hi_d = GL.boot(v, g, 1, A[:, C["day"]], _first, alpha)
    _, lo_c, hi_c = GL.boot(v, g, 1, A[:, C["code"]], _first, alpha)
    days = np.unique(A[ok, C["day"]])
    cut = days[len(days) // 2]
    d = A[:, C["day"]]
    out.update(value=pt, early=float(v[ok & (d < cut)].mean()) if (ok & (d < cut)).any() else None,
               late=float(v[ok & (d >= cut)].mean()) if (ok & (d >= cut)).any() else None,
               by_day=[lo_d, hi_d], by_stock=[lo_c, hi_c])
    if None not in (lo_d, lo_c, hi_d, hi_c):
        out.update(lo=min(lo_d, lo_c), hi=max(hi_d, hi_c))
    return out


def net_ok(q):
    if q.get("lo") is None or q["n"] < T.MIN_N:
        return False
    return q["lo"] > 0 and (q.get("early") or 0) > 0 and (q.get("late") or 0) > 0


def summary(d1, ok3):
    if d1 == UP and ok3:
        return "兆し：足を空けても戻り、費用のあとも残る（前向き J27F を登録してオーナーに諮る）"
    if d1 == UP:
        return "戻りは残るが、費用で消える"
    if d1 == DOWN:
        return "⚠️ 逆向き（足を空けると下げ続ける）"
    return "見えない＝J22 の W2 は売り買いの差の見かけ"


def _share(v, m):
    x = v[m & np.isfinite(v)]
    if len(x) < T.MIN_N:
        return {"n": int(len(x)), "mean": None, "up": None}
    return {"n": int(len(x)), "mean": float(x.mean()), "up": float((x > 0).mean())}


def analyze(A):
    A = mornings(A)
    g = groups(A)
    rb = A[:, C["r910"]]
    days = np.unique(A[:, C["day"]])
    res = {"sample": {"days": int(len(days)), "rows": int(len(A)), "stocks": int(len(np.unique(A[:, C["code"]]))),
                      "first": dt.date.fromordinal(int(days[0])).isoformat() if len(days) else None,
                      "last": dt.date.fromordinal(int(days[-1])).isoformat() if len(days) else None},
           "judges": {}}
    q1 = O.measure(A, rb, GL.pair_grp(g["down"], g["flat"]), ALPHA)
    q2 = O.measure(A, rb, GL.pair_grp(g["up"], g["flat"]), ALPHA)
    q3 = net_mean(A, g["down"])
    d1, d2 = O.direction(q1), O.direction(q2)
    res["judges"] = {"Q1": dict(q1, direction=d1, expected=UP), "Q2": dict(q2, direction=d2, expected=DOWN),
                     "Q3": dict(q3, ok=net_ok(q3))}
    res["summary"] = {"W2": summary(d1, net_ok(q3)),
                      "W1": "足を空けても戻される" if d2 == DOWN else "⚠️ 逆向き（足を空けると上げ続ける）" if d2 == UP
                      else "見えない＝J22 の W1 は売り買いの差の見かけ"}
    # ── 読むための表（判定しない）──
    rd = {"by_group": {}, "by_turnover": {}, "depth": {}}
    for name in ("down", "flat", "up"):
        m = g[name]
        c = A[m, C["cost"]]
        c = c[np.isfinite(c)]
        rd["by_group"][name] = {"r905_910": _share(A[:, C["r905_910"]], m), "r905": _share(A[:, C["r905"]], m),
                                "r910": _share(rb, m), "r915": _share(A[:, C["r915"]], m),
                                "cost_median": float(np.median(c)) if len(c) else None}
    tv = A[:, C["turnover"]]
    for lab, lo, hi in S.TURNOVER_BANDS:
        band = (tv >= lo) & (tv < hi)
        rd["by_turnover"][lab] = {"q1": MF._plain(rb, GL.pair_grp(g["down"] & band, g["flat"] & band), "diff")[0],
                                  "n_down": int((g["down"] & band).sum()),
                                  "q3": _share(rb - A[:, C["cost"]], g["down"] & band)}
    f5 = A[:, C["f5"]]
    for lab, lo, hi in DEPTHS:
        rd["depth"][lab] = {"r910": _share(rb, (f5 > lo) & (f5 <= hi)), "net": _share(rb - A[:, C["cost"]], (f5 > lo) & (f5 <= hi))}
    res["reading"] = rd
    return res


def listing(res, today):
    """検証済みリスト（verified_list.SOURCES）が読む欄。Q3（下げた組を 9:10 に買い 9:30 に売る・費用後）がプラスでなければストップ"""
    j = ((res.get("result") or {}).get("judges") or {})
    q3, q1 = j.get("Q3") or {}, j.get("Q1") or {}
    out = {"kind": "backtest", "section": "J27",
           "titles": {"J27": "最初の5分で −1％以下まで下げた株を 9:10 に買い 9:30 に売る（足を1本空ける・銘柄ごとの売り買いの差を引く・約40朝）"},
           "verdicts": {}}
    if q3 and not q3.get("ok"):
        out["verdicts"]["J27"] = {"status": "stop", "decided_on": today, "n": q3.get("n"), "mean": q3.get("value"),
                                  "lo": q3.get("lo"), "hi": q3.get("hi"),
                                  "reason": f"過去のデータで1回だけ数えて費用後プラスにならない（9:05→9:30 の戻りの大半は最初の1本の跳ね返り・"
                                            f"足を空けた戻りは ふつうとの差 {_p(q1.get('value'))}・幅は 98.33％・費用は推定）"}
    return out


def relist(path=OUT_JSON):
    """数え直さずに、書き出した結果へ検証済みリストの欄を足す（2026-10-07：1回目の本番のあとに欄を足したため）"""
    with open(path, encoding="utf-8") as fh:
        res = json.load(fh)
    res.update(listing(res, dt.datetime.now(P.JST).date().isoformat()))
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1, default=str)
    return res


# ════════════════════ 読む ════════════════════

def load(codes, fetch):
    parts, missing = [], {"daily": [], "m5": []}
    for i, code in enumerate(codes):
        d = fetch(code, "1d", DAILY_RANGE)
        m5 = T._first(fetch, code, "5m", T.M5_RANGES)
        if not d:
            missing["daily"].append(code)
            continue
        if not m5:
            missing["m5"].append(code)
            continue
        daily = sorted({t.date().isoformat(): (t.date().isoformat(), o, h, lo, c, v) for t, o, h, lo, c, v in d}.values())
        parts.append(stock_rows(i, daily, T._by_day(m5)))
        if (i + 1) % 500 == 0:
            print(f"  ...{i + 1}/{len(codes)}", flush=True)
    A = np.vstack(parts) if parts else np.zeros((0, len(COLS)))
    return A, missing


def check_summary(A, missing, n_codes, store):
    """点検だけ＝朝の数と組ごとの件数（損益は数えない）"""
    B = mornings(A)
    g = groups(B)
    return {"n_codes": n_codes, "missing": {k: len(v) for k, v in missing.items()}, "rows_all": int(len(A)), "store": store,
            "days": int(len(np.unique(B[:, C["day"]]))), "rows": int(len(B)),
            "first": dt.date.fromordinal(int(B[:, C["day"]].min())).isoformat() if len(B) else None,
            "last": dt.date.fromordinal(int(B[:, C["day"]].max())).isoformat() if len(B) else None,
            "groups": {k: int(m.sum()) for k, m in g.items()}, "with_cost_down": int((g["down"] & np.isfinite(B[:, C["cost"]])).sum())}


# ════════════════════ 書く ════════════════════

def _p(x, d=2):
    return Y._pct(x, d)


def _band(q):
    return "—" if q.get("lo") is None else f"{_p(q['lo'])}〜{_p(q['hi'])}"


def _cell(s):
    return "—" if s["mean"] is None else f"{_p(s['mean'])}（上がった {s['up'] * 100:.0f}％・{s['n']:,}）"


def render_md(res):
    L = ["# J27 最初の5分で大きく動いた株は、足を1本空けても 9:30 までに戻るか", "",
         f"更新: {res.get('generated_at', '')}（事前登録＝`PILLAR_PREREG.md`「J27」・指紋 `{(res.get('prereg_sha256') or '')[:12]}`）", ""]
    r = res.get("result") or {}
    if "error" in r:
        return "\n".join(L + [f"⚠️ 計算できず：{r['error']}", "", "※ 研究の記録です。投資助言ではありません。"]) + "\n"
    s = r["sample"]
    L += [f"朝：{s['first']}〜{s['last']}・{s['days']}朝・{s['rows']:,}行・{s['stocks']:,}銘柄（J22 と同じ朝＝独立した確かめではなく、見かけかどうかの切り分け）。"
          "最初の5分＝寄り→9:05。下げた＝−1％以下／上げた＝+1％以上／ふつう＝±0.3％未満。幅は 98.33％（日と銘柄で引き直した広いほう）。", "",
          "## まとめ", "",
          f"- **下げた株（J22 の W2）**：{r['summary']['W2']}",
          f"- **上げた株（J22 の W1）**：{r['summary']['W1']}", "",
          "| 判定 | 中身 | 件数 | 値 | 98.33％の幅 | 前半／後半 | 結果 |", "|---|---|---|---:|---|---|---|"]
    j = r["judges"]
    L.append(f"| Q1 | 下げた − ふつう（9:10→9:30） | {j['Q1']['ns'][0]:,}／{j['Q1']['ns'][1]:,} | {_p(j['Q1']['value'])} | {_band(j['Q1'])} | "
             f"{_p(j['Q1']['early'])}／{_p(j['Q1']['late'])} | {j['Q1']['direction'] or '見えない'}（期待＝上） |")
    L.append(f"| Q2 | 上げた − ふつう（9:10→9:30） | {j['Q2']['ns'][0]:,}／{j['Q2']['ns'][1]:,} | {_p(j['Q2']['value'])} | {_band(j['Q2'])} | "
             f"{_p(j['Q2']['early'])}／{_p(j['Q2']['late'])} | {j['Q2']['direction'] or '見えない'}（期待＝下） |")
    L.append(f"| Q3 | 下げた組を 9:10 に買い 9:30 に売る（費用後） | {j['Q3']['n']:,} | {_p(j['Q3']['value'])} | {_band(j['Q3'])} | "
             f"{_p(j['Q3']['early'])}／{_p(j['Q3']['late'])} | {'上' if j['Q3']['ok'] else '見えない'} |")
    rd = r["reading"]
    L += ["", "## 読むための表（判定しない）", "", "### 組ごとの値動き（費用前）", "",
          "| 組 | 9:05→9:10（跳ね返り） | 9:05→9:30（J22 と同じ） | 9:10→9:30（1本空け） | 9:15→9:30（2本空け） | 往復の費用の中央値 |",
          "|---|---|---|---|---|---:|"]
    names = {"down": "下げた（−1％以下）", "flat": "ふつう（±0.3％未満）", "up": "上げた（+1％以上）"}
    for k, g in rd["by_group"].items():
        L.append(f"| {names[k]} | {_cell(g['r905_910'])} | {_cell(g['r905'])} | {_cell(g['r910'])} | {_cell(g['r915'])} | {_p(g['cost_median'])} |")
    L += ["", "### 前の日の売買代金ごと", "", "| 売買代金 | 下げた件数 | Q1 下げた − ふつう | Q3 下げた組の費用後 |", "|---|---:|---:|---|"]
    for lab, x in rd["by_turnover"].items():
        L.append(f"| {lab} | {x['n_down']:,} | {_p(x['q1'])} | {_cell(x['q3'])} |")
    L += ["", "### 最初の5分の下げの深さごと（9:10→9:30）", "", "| 深さ | 費用前 | 費用後 |", "|---|---|---|"]
    for lab, x in rd["depth"].items():
        L.append(f"| {lab} | {_cell(x['r910'])} | {_cell(x['net'])} |")
    L += ["", "## 注意", "",
          "- J22 と同じ朝（約40朝）＝独立した確かめではない。残っても売買の決まりにはせず、前向き（登録したあとの朝だけ）で確かめる",
          "- 費用は日足からのふだんの見積もり（Abdi & Ranaldo・J24 の形）。寄りの直後の荒れた時間の差はもっと広いかもしれない（甘めの側）",
          "- 空売りは数えない", "", "---", "", "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def main(argv):
    if "--relist" in argv:
        res = relist()
        print(json.dumps(res.get("verdicts"), ensure_ascii=False, indent=1))
        return 0
    res = {"generated_at": dt.datetime.now(P.JST).isoformat(timespec="minutes"), "prereg_file": P.PREREG,
           "prereg_sha256": P.prereg_sha256()}
    try:
        stocks, list_date = jp_bars.load_universe()
        codes = sorted(stocks)
        A, missing = load(codes, jp_bars.fetcher())
        store = jp_bars.info()
        res["price_store"] = store
        if "--check" in argv:
            print(json.dumps(check_summary(A, missing, len(codes), store), ensure_ascii=False, indent=1))
            return 0
        if len(missing["daily"]) > T.MAX_MISSING * len(codes):
            raise RuntimeError(f"日足を取れなかった銘柄が {len(missing['daily'])}/{len(codes)}＝5％超。偏った組で判定しない（取り直す）")
        res["result"] = dict(analyze(A), n_codes=len(codes), list_date=list_date, n_missing={k: len(v) for k, v in missing.items()})
        res.update(listing(res, dt.datetime.now(P.JST).date().isoformat()))
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
