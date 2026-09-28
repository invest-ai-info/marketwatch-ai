# -*- coding: utf-8 -*-
"""C2 チャートパターン（三尊・逆三尊）を、論文の定義どおりに数える（2026-09-28 オーナー「2と3を進めてください」）。

定義＝Osler & Chang (1995)「Head and Shoulders: Not Just a Flaky Pattern」ニューヨーク連銀 Staff Report 4。
教科書7冊から数字まで決めた、為替のための定義。2026-09-28 に PDF 本文で確認した。
⚠️ 形の決め方・物差し・判定は PILLAR_PREREG.md「C2 チャートパターン」と下の定数に固定。結果を見てから動かさない。
⚠️ 出力 pattern-lab.json / pattern-lab.md は GitHub 側で生成＝手元から送らない（SYNC禁忌）。
⚠️ エンジン・発火条件・固定オラクルには触れない（読むだけ・別に計算する）。

実行: python pattern_lab.py   （Actions の pattern-lab.yml から手動で）
"""
import datetime as dt
import json
import sys

import numpy as np

import pillar_lab as P
import trend_lab as TL
from combo_lab import simulate
from signal_lab_sweep import cost_r_of

OUT_JSON, OUT_MD = "pattern-lab.json", "pattern-lab.md"
START, WARMUP, SPLIT = TL.START, TL.WARMUP, TL.SPLIT   # 2006年から・先頭260本は数えない・前半＝2015年まで
MIN_N = 300
P_LIMIT = 0.05                  # 三尊と逆三尊を合わせて1問
MULTS = (1.00, 1.25, 1.50, 1.75, 2.00, 2.50, 3.00, 3.50, 4.00, 4.50)   # χ＝σ×これ（論文の10段）
ASYM = 2.5                      # 横のゆがみ（肩から頭・頭から肩の日数の比）
DEDUPE = 2                      # 同じ銘柄で、採った合図の日から2日以内は捨てる（論文の脚注8）
RISK_ATR = 1.5                  # 1R＝ATR14×1.5
EXIT = "X1"                     # 損切り1.5ATR・利確2ATR・最長20本（combo_lab と同じ）
HORIZONS = (10, 20)             # 読むための表：入る足を1本目として10本目・20本目の終値
N_PERM = P.N_PERM
SIDE_JA = {1: "三尊（売り）", -1: "逆三尊（買い）"}


# ════════════════════ 山と谷（ジグザグ）════════════════════

def zigzag(c, chi):
    """終値の山と谷。[(種類, 位置, 値, 確定した位置)]。種類＝+1 山／−1 谷（交互に並ぶ）。
    山＝直前の谷から χ 以上（比率）高い高値で、終値がそこから χ 下がった日に確定する。谷は逆。"""
    piv = []
    n = len(c)
    if n < 2:
        return piv
    mode, hi_i, lo_i = 0, 0, 0          # 0＝まだ決まらない／+1＝山を探している／−1＝谷を探している
    for i in range(1, n):
        x = c[i]
        if mode == 0:
            if x > c[hi_i]:
                hi_i = i
            if x < c[lo_i]:
                lo_i = i
            if x >= c[lo_i] * (1 + chi):
                piv.append((-1, lo_i, float(c[lo_i]), i))
                mode, hi_i = 1, i
            elif x <= c[hi_i] * (1 - chi):
                piv.append((1, hi_i, float(c[hi_i]), i))
                mode, lo_i = -1, i
        elif mode == 1:
            if x > c[hi_i]:
                hi_i = i
            elif x <= c[hi_i] * (1 - chi):
                piv.append((1, hi_i, float(c[hi_i]), i))
                mode, lo_i = -1, i
        else:
            if x < c[lo_i]:
                lo_i = i
            elif x >= c[lo_i] * (1 + chi):
                piv.append((-1, lo_i, float(c[lo_i]), i))
                mode, hi_i = 1, i
    return piv


# ════════════════════ 三尊・逆三尊（論文の5つの条件）════════════════════

def find_hs(c, piv, sign):
    """sign=+1 三尊（山4つ）／−1 逆三尊（谷4つ）。[(合図の日の位置, 中身)]"""
    def gt(x, y):
        return x > y if sign > 0 else x < y

    def le(x, y):
        return x <= y if sign > 0 else x >= y

    n = len(c)
    ks = [j for j, p in enumerate(piv) if p[0] == sign]
    out = []
    for a in range(3, len(ks)):
        jp, jls, jh, jrs = ks[a - 3], ks[a - 2], ks[a - 1], ks[a]
        pv, ls, hd, rs = (piv[j][2] for j in (jp, jls, jh, jrs))
        t_ls, t_h, t_rs = piv[jls][1], piv[jh][1], piv[jrs][1]
        (_, _, v_ll, _), (_, t_l, v_l, _), (_, t_r, v_r, _) = piv[jp + 1], piv[jls + 1], piv[jh + 1]
        if not (gt(hd, ls) and gt(hd, rs)):                          # 1 頭が両肩より高い
            continue
        if not (gt(ls, pv) and gt(v_l, v_ll)):                       # 2 上昇のあとに出る
            continue
        m1, m2 = (ls + v_l) / 2, (rs + v_r) / 2                      # 3 縦にゆがみすぎない
        if not (gt(rs, m1) and le(v_r, m1) and gt(ls, m2) and le(v_l, m2)):
            continue
        d1, d2 = t_h - t_ls, t_rs - t_h                              # 4 横にゆがみすぎない
        if d1 > ASYM * d2 or d2 > ASYM * d1:
            continue
        slope = (v_r - v_l) / (t_r - t_l)
        limit = t_rs + (t_rs - t_ls)                                 # 5 抜けるまでの期限
        conf = piv[jrs][3]                                           # 右肩が確定した日
        nxt = piv[jrs + 2][3] if jrs + 2 < len(piv) else None        # 右肩の次の山が確定した日
        for d in range(conf, min(limit, n - 1) + 1):
            if nxt is not None and d >= nxt:
                break
            neck = v_l + slope * (d - t_l)
            if (c[d] < neck) if sign > 0 else (c[d] > neck):
                out.append((d, {"t_ls": t_ls, "t_h": t_h, "t_rs": t_rs, "neck": float(neck)}))
                break
    return out


def detect(c, chis):
    """10段の χ を小さい順に探し、2日以内の重なりを捨てる。[{d, sign, step}]（step＝何段目か 0〜9）"""
    kept = []
    for step, chi in enumerate(chis):
        piv = zigzag(c, chi)
        found = [(d, s) for s in (1, -1) for d, _ in find_hs(c, piv, s)]
        for d, s in sorted(found):
            if any(abs(d - k["d"]) <= DEDUPE for k in kept):
                continue
            kept.append({"d": d, "sign": s, "step": step})
    return sorted(kept, key=lambda k: k["d"])


def sigma_of(c):
    """日々の終値の変化率の標準偏差（データ全体で1つ・論文と同じ）"""
    r = np.diff(c) / c[:-1]
    r = r[np.isfinite(r)]
    return float(np.std(r, ddof=1)) if len(r) > 2 else float("nan")


# ════════════════════ 取引の数え方 ════════════════════

def _arrays(df):
    o, h, l, c = (np.asarray(df[k].values, float) for k in ("Open", "High", "Low", "Close"))
    atr = TL.rma(TL.true_range(h, l, c), 14)
    return o, h, l, c, atr


def trade(ticker, o, h, l, c, atr, i, s):
    """合図の日 i → 次の足の始値で入る。s＝売買の向き（+1 買い／−1 売り）。{R, reason, H10, H20}（費用後）。数えられなければ None"""
    if not atr[i] > 0:
        return None
    side = "long" if s > 0 else "short"
    r = simulate(o, h, l, c, None, atr[i], i, side, EXIT)
    if r is None:
        return None
    e, unit = i + 1, RISK_ATR * atr[i]
    cost = cost_r_of({"entry": o[e], "stop_loss": o[e] - unit, "ticker": ticker})
    reason = "損切り" if r <= -1 + 1e-9 else ("利確" if r >= 2.0 / RISK_ATR - 1e-9 else "時間切れ")
    out = {"R": r - cost, "reason": reason}
    for hz in HORIZONS:
        out[f"H{hz}"] = (s * (c[e + hz - 1] - o[e]) / unit - cost) if e + hz - 1 < len(c) else None
    return out


def half_of(date_iso):
    return "前半" if date_iso < SPLIT else "後半"


def ticker_rows(ticker, df):
    """本物の合図の取引と、偽薬の候補（同じ銘柄・同じ売買の向き・同じ時期の全部の日）。偽薬の鍵の向き＝売買の向き"""
    o, h, l, c, atr = _arrays(df)
    sig = sigma_of(c)
    dates = [x.date().isoformat() for x in df.index]
    found = detect(c, [m * sig for m in MULTS])
    real = []
    for k in found:
        i = k["d"]
        if i < WARMUP:
            continue
        way = -k["sign"]                                           # 三尊（+1）＝売り／逆三尊（−1）＝買い
        t = trade(ticker, o, h, l, c, atr, i, way)
        if t is None:
            continue
        real.append({"ticker": ticker, "cls": TL.TICKERS[ticker], "date": dates[i + 1], "half": half_of(dates[i + 1]),
                     "sign": k["sign"], "dir": way, "step": k["step"], **t})
    pool = {}
    for s in (1, -1):
        for i in range(WARMUP, len(c) - 1):
            t = trade(ticker, o, h, l, c, atr, i, s)
            if t is None:
                continue
            key = (ticker, s, half_of(dates[i + 1]))
            for m in ("R",) + tuple(f"H{hz}" for hz in HORIZONS):
                if t[m] is not None:
                    pool.setdefault(key, {}).setdefault(m, []).append(t[m])
    pool = {k: {m: np.asarray(v, float) for m, v in d.items()} for k, d in pool.items()}
    return real, pool, {"sigma": sig, "n_found": len(found)}


# ════════════════════ 比べる・判定する ════════════════════

def _key(r):
    return (r["ticker"], r["dir"], r["half"])


def expected(rows, pool, m="R"):
    """偽薬の平均の見込み（本物と同じ 銘柄・向き・時期 の数で重み付け）"""
    tot, w = 0.0, 0
    for r in rows:
        if r.get(m) is None:
            continue
        arr = pool.get(_key(r), {}).get(m)
        if arr is None or not len(arr):
            continue
        tot += float(arr.mean())
        w += 1
    return tot / w if w else None


def placebo_p(rows, pool, n_perm=N_PERM, seed=P.SEED):
    """偽薬＝同じ 銘柄・向き・時期 からでたらめに同じ数だけ入る（両側の p）"""
    counts = {}
    for r in rows:
        k = _key(r)
        if len(pool.get(k, {}).get("R", [])):
            counts[k] = counts.get(k, 0) + 1
    total = sum(counts.values())
    if not total:
        return None
    rng = np.random.default_rng(seed)
    sims = np.empty(n_perm)
    for j in range(n_perm):
        s = 0.0
        for k, cnt in counts.items():
            arr = pool[k]["R"]
            s += float(arr[rng.integers(0, len(arr), cnt)].sum())
        sims[j] = s / total
    real = float(np.mean([r["R"] for r in rows if len(pool.get(_key(r), {}).get("R", []))]))
    cen = float(np.mean(sims))
    return float((np.sum(np.abs(sims - cen) >= abs(real - cen)) + 1) / (n_perm + 1))


def summary(rows, pool, m="R"):
    vals = [r[m] for r in rows if r.get(m) is not None]
    groups = [(r["ticker"], r["date"][:7]) for r in rows if r.get(m) is not None]
    st = P.mean_ci(vals, groups) if vals else {"n": 0, "mean": None, "lo": None, "hi": None}
    ex = expected(rows, pool, m)
    st["placebo"] = ex
    st["diff"] = (st["mean"] - ex) if (st.get("mean") is not None and ex is not None) else None
    return st


def verdict(allst, p, halves):
    if allst["n"] < MIN_N or allst.get("diff") is None or p is None:
        return "件数不足"
    ok_h = all(h.get("mean") is not None and h.get("diff") is not None for h in halves.values())
    if (allst["mean"] > 0 and allst["diff"] > 0 and p < P_LIMIT and ok_h
            and all(h["mean"] > 0 and h["diff"] > 0 for h in halves.values())):
        return "論文の三尊は残る"
    if allst["diff"] < 0 and p < P_LIMIT and ok_h and all(h["diff"] < 0 for h in halves.values()):
        return "逆に効く"
    return "差なし"


def analyse(real, pool, n_perm=N_PERM):
    res = {"all": summary(real, pool)}
    res["p"] = placebo_p(real, pool, n_perm=n_perm)
    res["halves"] = {hv: summary([r for r in real if r["half"] == hv], pool) for hv in ("前半", "後半")}
    res["verdict"] = verdict(res["all"], res["p"], res["halves"])
    rd = {}
    rd["side"] = {SIDE_JA[s]: summary([r for r in real if r["sign"] == s], pool) for s in (1, -1)}
    rd["class"] = {TL.CLASS_JA[k]: summary([r for r in real if r["cls"] == k], pool) for k in TL.CLASS_JA}
    rd["step"] = {f"σ×{MULTS[i]:.2f}": sum(1 for r in real if r["step"] == i) for i in range(len(MULTS))}
    n = len(real) or 1
    rd["reason"] = {k: sum(1 for r in real if r["reason"] == k) / n for k in ("利確", "損切り", "時間切れ")}
    rd["horizon"] = {f"{hz}本目の終値": summary(real, pool, f"H{hz}") for hz in HORIZONS}
    res["read"] = rd
    return res


def run(n_perm=N_PERM):
    real, pool, got, missing = [], {}, {}, []
    for tk in TL.TICKERS:
        df = P.fetch(tk, "1d", start=START)
        if df is None or len(df) < WARMUP + 60:
            missing.append(tk)
            continue
        df = df.dropna(subset=["Open", "High", "Low", "Close"])
        df = df[df["Close"] > 0]                                   # 終値が0以下の日を除く（原油の2020年4月）
        rows, pl, info = ticker_rows(tk, df)
        real += rows
        pool.update(pl)
        got[tk] = {"first": df.index[0].date().isoformat(), "last": df.index[-1].date().isoformat(),
                   "bars": len(df), "sigma": info["sigma"], "n_found": info["n_found"], "n_trades": len(rows)}
    res = analyse(real, pool, n_perm=n_perm) if real else {"verdict": "件数不足", "all": {"n": 0}}
    res.update({"tickers": got, "missing": missing})
    return res


# ════════════════════ 書き出し ════════════════════

def _pt(x):
    return "—" if x is None else f"{x:+.3f}"


def _row(name, st):
    ci = f"{_pt(st.get('lo'))}〜{_pt(st.get('hi'))}" if st.get("lo") is not None else "—"
    return f"| {name} | {st.get('n', 0)} | {_pt(st.get('mean'))} | {ci} | {_pt(st.get('placebo'))} | {_pt(st.get('diff'))} |"


HEAD = ["| 区分 | 件数 | 平均R（費用後） | 95%の幅 | 偽薬の平均R | 偽薬との差 |", "|---|---:|---:|---|---:|---:|"]


def render(res):
    L = ["# C2 チャートパターン（三尊・逆三尊）", "",
         f"作成: {res.get('generated_at')}（GitHub Actions で計算）。事前登録＝`{P.PREREG}`「C2 チャートパターン」"
         f"（指紋 sha256 `{(res.get('prereg_sha256') or '')[:16]}…`）。",
         "定義＝Osler & Chang (1995) ニューヨーク連銀 Staff Report 4（教科書7冊から数字まで決めた三尊の定義）。"
         "監視18銘柄の日足・2006年から。出口＝損切り1.5ATR・利確2ATR・最長20本。**売買の決まりではない**。", ""]
    if res.get("missing"):
        L += [f"- ⚠️ 取れなかった銘柄: {', '.join(res['missing'])}", ""]
    a = res.get("all") or {}
    p_txt = "—" if res.get("p") is None else f"{res['p']:.3f}"
    L += [f"## 判定：**{res.get('verdict')}**", "",
          f"基準＝費用後の平均がプラス・偽薬との差がプラスで p＜{P_LIMIT}・前半（2015年まで）と後半（2016年から）とも両方プラス。件数{MIN_N}未満は件数不足。", "",
          f"偽薬との比較 p＝{p_txt}（同じ銘柄・同じ向き・同じ時期のでたらめな日・{N_PERM}回）", ""]
    L += HEAD + [_row("全部", a)] + [_row(k, v) for k, v in (res.get("halves") or {}).items()]
    rd = res.get("read") or {}
    if rd:
        L += ["", "## 読むための表（判定しない）", "", "### 三尊・逆三尊の別", ""] + HEAD
        L += [_row(k, v) for k, v in rd["side"].items()]
        L += ["", "### 資産の種類別", ""] + HEAD + [_row(k, v) for k, v in rd["class"].items()]
        L += ["", "### 論文に近い物差し（決めた本数だけ持った場合）", ""] + HEAD
        L += [_row(k, v) for k, v in rd["horizon"].items()]
        L += ["", "### 手じまいの内訳", "", " ・".join(f"{k} {v:.0%}" for k, v in rd["reason"].items()),
              "", "### χ の段ごとの件数（小さい段から順に採り、2日以内の重なりは捨てた）", "",
              " ・".join(f"{k} {v}件" for k, v in rd["step"].items())]
    L += ["", "### 銘柄ごとの件数", "", "| 銘柄 | 期間 | σ（日々） | 見つかった形 | 数えた取引 |", "|---|---|---:|---:|---:|"]
    for tk, g in (res.get("tickers") or {}).items():
        L.append(f"| {tk} | {g['first']}〜{g['last']} | {g['sigma']:.4f} | {g['n_found']} | {g['n_trades']} |")
    L += ["", "---", "", "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
    return "\n".join(L)


def main():
    res = run()
    res["generated_at"] = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).strftime("%Y-%m-%dT%H:%M+09:00")
    res["prereg_file"] = P.PREREG
    res["prereg_sha256"] = P.prereg_sha256()
    res["constants"] = {"MULTS": MULTS, "ASYM": ASYM, "DEDUPE": DEDUPE, "RISK_ATR": RISK_ATR, "EXIT": EXIT,
                        "MIN_N": MIN_N, "P_LIMIT": P_LIMIT, "START": START, "WARMUP": WARMUP, "SPLIT": SPLIT}
    json.dump(res, open(OUT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    open(OUT_MD, "w", encoding="utf-8").write(render(res))
    print(f"C2: {res.get('all', {}).get('n', 0)} 件・判定 {res.get('verdict')}", file=sys.stderr)


if __name__ == "__main__":
    main()
