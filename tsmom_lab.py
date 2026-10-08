# -*- coding: utf-8 -*-
"""R11 株価指数・商品（MT4）と為替（MT5）の時系列モメンタム：過去12か月の向きで買いか売りを決め、値動きの大きさで量をそろえて
月1回入れ替える。2026-10-08 夜 登録・オーナー「候補3も登録して進めてください」。PILLAR_PREREG.md「R11」。

向き＝決める月の月末の終値 ÷ 12か月前の月末の終値 − 1 の符号。量＝0.10 ÷（60日の対数の値動きの標準偏差 × √252）・上限3倍。
1か月の値（腕ごと）＝数えられる資産の「向き × 量 × 次の月の値動き − 費用（＋為替はスワップ）」の平均（3つ未満の月は数えない）。
判定＝97.5％（2つの腕）・6か月のかたまり・偽薬（資産ごとに向きの札を入れ替える 2,000回・片側 p＜0.025）。PREREG のとおり。

⚠️ 決まりは PILLAR_PREREG.md「R11」と下の定数に固定。出力（tsmom-lab.json / .md）は集計だけ（SYNC禁忌）。
実行: python tsmom_lab.py --check   （点検だけ＝資産ごとのデータの期間・BIS に届くか・月の数。損益は数えない・何も書き出さない）
      python tsmom_lab.py           （本番。Actions の tsmom-lab.yml から手動で・1回だけ）
"""
import csv
import datetime as dt
import io
import json
import sys
import urllib.request

import numpy as np
import pandas as pd

import momentum_lab as M
import pillar_lab as P

OUT_JSON, OUT_MD = "tsmom-lab.json", "tsmom-lab.md"
Q1_ASSETS = (("^N225", "日経平均"), ("^GSPC", "S&P500"), ("^NDX", "ナスダック100"), ("^DJI", "ダウ"), ("^FTSE", "英FTSE"),
             ("^GDAXI", "独DAX"), ("GC=F", "金"), ("SI=F", "銀"), ("CL=F", "原油"))
FX_PAIRS = ("EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCHF", "USDCAD", "NZDUSD", "EURJPY", "GBPJPY", "AUDJPY", "EURAUD", "GBPAUD")
START = "1985-01-01"
LOOK = 12
VOL_DAYS = 60
ANN = 252
TARGET = 0.10
CAP = 3.0
Q1_COST = 0.0005            # 持つ量の変わった分 × 0.05％
Q1_FIN = 0.03               # 持ち越しの金利 年3％（買いも売りも払う側）
FX_PIPS_JPY, FX_PIPS_OTHER = 1.2, 1.8
FX_MARKUP = 0.01            # スワップの業者の上乗せ 年1％
MAX_DAY = 0.25              # 1日の値動きがこれを超える日はデータの誤り
MIN_ASSETS = 3
FIRST_Q1, LAST = (1990, 1), (2026, 8)
SPLIT = (2010, 1)           # 最近＝この月から
MIN_OLD = 36                # Q2 の昔がこれ未満なら前半と後半に半分ずつ
N_ARMS = 2
ALPHA = 0.05 / N_ARMS
N_PERM = 2000
OK, NEW_ONLY, REV, NONE, SKIP = "✅ 効く", "△ 最近だけ", "✕ 逆向き", "✕ 見えない", "― 判定しない（スワップを数えられない）"
CCY_AREA = {"USD": "US", "EUR": "XM", "GBP": "GB", "JPY": "JP", "AUD": "AU", "CAD": "CA", "CHF": "CH", "NZD": "NZ"}
BIS_URLS = ("https://stats.bis.org/api/v1/data/WS_CBPOL/M.{areas}?format=csv",
            "https://stats.bis.org/api/v2/data/dataflow/BIS/WS_CBPOL/1.0/M.{areas}?format=csv",
            "https://stats.bis.org/api/v1/data/WS_CBPOL_M/M.{areas}?format=csv")


# ════════════════════ データ ════════════════════

def month_key(d):
    return f"{d.year:04d}-{d.month:02d}"


def ym_tuple(k):
    y, m = map(int, k.split("-"))
    return y, m


def monthly_table(daily, spread=None):
    """日ごとの終値（pd.Series・日付の添字）→ 月ごとの表（月末の終値・その日の σ・その月に誤りの日があるか・60日の窓に誤りがあるか・月末の差）"""
    s = daily.dropna().sort_index()
    s = s[~s.index.duplicated(keep="last")]
    bad_day = (s <= 0)
    lr = np.log(s.where(s > 0)).diff()
    bad_day = bad_day | (lr > np.log1p(MAX_DAY)) | (lr < np.log1p(-MAX_DAY))     # 1日 +25％超・−25％超
    lr = lr.where(~bad_day)
    rows = {}
    keys = pd.Series([month_key(d) for d in s.index], index=s.index)
    for k, idx in keys.groupby(keys).groups.items():
        last = idx.max()
        pos = s.index.get_loc(last)
        win = lr.iloc[max(0, pos - VOL_DAYS + 1):pos + 1]
        winbad = bool(bad_day.iloc[max(0, pos - VOL_DAYS + 1):pos + 1].any())
        sig = float(win.std(ddof=1) * np.sqrt(ANN)) if win.notna().sum() >= VOL_DAYS - 5 else np.nan
        rows[k] = {"close": float(s.loc[last]), "sigma": sig, "bad_month": bool(bad_day.loc[idx].any()), "bad_win": winbad,
                   "spread": float(spread.loc[last]) if spread is not None and last in spread.index else np.nan}
    return pd.DataFrame.from_dict(rows, orient="index").sort_index()


def fx_daily(df):
    """fx_bars.load の1時間足（UTC）→ (日ごとの真ん中の終値, 日ごとの最後の足の売り買いの差)"""
    if df is None or df.empty:
        return None, None
    mid = (df["bc"] + df["ac"]) / 2
    spr = df["ac"] - df["bc"]
    day = pd.Index(df.index.tz_convert("UTC").date if df.index.tz is not None else df.index.date)
    c = mid.groupby(day).last()
    sp = spr.groupby(day).last()
    c.index = pd.to_datetime(c.index)
    sp.index = pd.to_datetime(sp.index)
    return c, sp


def parse_bis_csv(text):
    """BIS の CSV → {地域: {YYYY-MM: 年率％}}。列の名前は大文字小文字を問わない"""
    rd = csv.DictReader(io.StringIO(text))
    cols = {c.upper(): c for c in (rd.fieldnames or [])}
    a, t, v = cols.get("REF_AREA"), cols.get("TIME_PERIOD"), cols.get("OBS_VALUE")
    if not (a and t and v):
        return {}
    out = {}
    for r in rd:
        try:
            val = float(r[v])
        except (TypeError, ValueError):
            continue
        k = str(r[t])[:7]
        if len(k) == 7 and k[4] == "-":
            out.setdefault(r[a], {})[k] = val
    return out


def fetch_bis(get=None):
    """→ (地域ごとの政策金利, 使った URL)。届かなければ ({}, None)"""
    areas = "+".join(sorted(set(CCY_AREA.values())))
    for u in BIS_URLS:
        url = u.format(areas=areas)
        try:
            text = get(url) if get else urllib.request.urlopen(
                urllib.request.Request(url, headers={"User-Agent": P.UA, "Accept": "text/csv"}), timeout=60).read().decode("utf-8", "replace")
            rates = parse_bis_csv(text)
            if len(rates) >= 6:
                return rates, url
        except Exception as e:  # noqa: BLE001
            print(f"  ⚠️ BIS に届かない：{url[:70]}… {type(e).__name__}", file=sys.stderr)
    return {}, None


def rate_at(rates, area, k, back=3):
    """その月の政策金利（無ければ3か月前までの直近）"""
    r = rates.get(area) or {}
    y, m = ym_tuple(k)
    for i in range(back + 1):
        mm = (y * 12 + m - 1) - i
        key = f"{mm // 12:04d}-{mm % 12 + 1:02d}"
        if key in r:
            return r[key]
    return None


# ════════════════════ 組み合わせ ════════════════════

def matrices(tables, months, kind, rates=None):
    """資産ごとの月の表 → 行列（資産 × 決める月）：向き S・量 W・次の月の値動き R・数えられる V・売り買いの費用の率 C・持ち越し F・スワップ K"""
    n, T = len(tables), len(months)
    S, W, R, C, F, K = (np.zeros((n, T)) for _ in range(6))
    V = np.zeros((n, T), bool)
    names = list(tables)
    for i, name in enumerate(names):
        tb = tables[name]
        if tb is None or tb.empty:
            continue
        for j, k in enumerate(months):
            y, m = ym_tuple(k)
            prev = f"{(y * 12 + m - 1 - LOOK) // 12:04d}-{(y * 12 + m - 1 - LOOK) % 12 + 1:02d}"
            nxt = f"{(y * 12 + m) // 12:04d}-{(y * 12 + m) % 12 + 1:02d}"
            if k not in tb.index or prev not in tb.index or nxt not in tb.index:
                continue
            a, b, c = tb.loc[prev], tb.loc[k], tb.loc[nxt]
            if a["close"] <= 0 or b["close"] <= 0 or c["close"] <= 0 or not np.isfinite(b["sigma"]) or b["sigma"] <= 0 \
                    or b["bad_win"] or c["bad_month"]:
                continue
            S[i, j] = 1.0 if b["close"] > a["close"] else -1.0 if b["close"] < a["close"] else 0.0
            W[i, j] = min(TARGET / b["sigma"], CAP)
            R[i, j] = c["close"] / b["close"] - 1
            if kind == "q1":
                C[i, j], F[i, j] = Q1_COST, Q1_FIN / 12
            else:
                pip = 0.01 if name.endswith("JPY") else 0.0001
                fixed = (FX_PIPS_JPY if name.endswith("JPY") else FX_PIPS_OTHER) * pip
                C[i, j] = max(fixed, b["spread"] if np.isfinite(b["spread"]) else 0.0) / b["close"]
                if rates is not None:
                    rb, rq = rate_at(rates, CCY_AREA[name[:3]], k), rate_at(rates, CCY_AREA[name[3:]], k)
                    if rb is None or rq is None:
                        continue
                    K[i, j] = (rb - rq) / 100 / 12
                    F[i, j] = FX_MARKUP / 12
            V[i, j] = True
    return {"names": names, "months": months, "S": S, "W": W, "R": R, "V": V, "C": C, "F": F, "K": K}


def net(mx, S=None, long_only=False):
    """→ 資産 × 月の「向き × 量 × 値動き − 費用（＋スワップ）」（数えられないところは NaN）"""
    S = mx["S"] if S is None else S
    if long_only:
        S = np.where(mx["V"], 1.0, 0.0)
    pos = np.where(mx["V"], S * mx["W"], 0.0)
    prev = np.zeros_like(pos)
    prev[:, 1:] = pos[:, :-1]
    val = pos * mx["R"] - np.abs(pos - prev) * mx["C"] - np.abs(pos) * mx["F"] + pos * mx["K"]
    return np.where(mx["V"], val, np.nan)


def arm_series(vals, V):
    """資産の平均（3つ未満の月は NaN）"""
    cnt = V.sum(0)
    with np.errstate(invalid="ignore"):
        m = np.nanmean(np.where(V, vals, np.nan), axis=0)
    return np.where(cnt >= MIN_ASSETS, m, np.nan)


def placebo_p(mx, actual, n_perm=N_PERM, seed=P.SEED):
    """資産ごとに、数えられる月どうしで向きの札を入れ替えた平均が、本物の平均以上になる割合（片側）"""
    rng = np.random.default_rng(seed)
    S0 = mx["S"]
    idx = [np.nonzero(mx["V"][i])[0] for i in range(S0.shape[0])]
    hits = 0
    for _ in range(n_perm):
        S = S0.copy()
        for i, ix in enumerate(idx):
            if len(ix) > 1:
                S[i, ix] = S0[i, rng.permutation(ix)]
        m = arm_series(net(mx, S), mx["V"])
        if np.nanmean(m) >= actual:
            hits += 1
    return (hits + 1) / (n_perm + 1)


def max_drawdown(x):
    x = np.asarray([v for v in x if np.isfinite(v)])
    if not len(x):
        return None
    c = np.cumprod(1 + x)
    return float((c / np.maximum.accumulate(c) - 1).min())


def halves(months, series, kind):
    """昔／最近の月の添字。Q2 で昔が36か月未満なら前半と後半"""
    ok = [j for j, v in enumerate(series) if np.isfinite(v)]
    split = f"{SPLIT[0]:04d}-{SPLIT[1]:02d}"
    old = [j for j in ok if months[j] < split]
    new = [j for j in ok if months[j] >= split]
    label = ("〜2009年", "2010年〜")
    if kind == "q2" and len(old) < MIN_OLD:
        h = len(ok) // 2
        old, new = ok[:h], ok[h:]
        label = ("前半", "後半")
    return old, new, label


def verdict(full, old_mean, new_band, p):
    if M.plus(full) and (old_mean or 0) > 0 and (new_band.get("mean") or 0) > 0 and p is not None and p < ALPHA:
        return OK
    if M.plus(new_band):
        return NEW_ONLY
    if M.minus(full):
        return REV
    return NONE


def analyze_arm(mx, kind, judge=True):
    vals = net(mx)
    ser = arm_series(vals, mx["V"])
    longv = arm_series(net(mx, long_only=True), mx["V"])
    months = mx["months"]
    ok = [j for j, v in enumerate(ser) if np.isfinite(v)]
    old, new, lab = halves(months, ser, kind)
    x = ser[ok]
    full = M.band(x, alpha=ALPHA)
    oldb, newb = M.band(ser[old], alpha=ALPHA), M.band(ser[new], alpha=ALPHA)
    p = placebo_p(mx, float(np.nanmean(x))) if judge and len(ok) else None
    res = {"months": len(ok), "first": months[ok[0]] if ok else None, "last": months[ok[-1]] if ok else None,
           "full": full, "old": oldb, "new": newb, "half_labels": lab, "placebo_p": p,
           "verdict": verdict(full, oldb.get("mean"), newb, p) if judge and ok else SKIP}
    lx = longv[ok]
    res["read"] = {
        "long_mean": float(np.nanmean(lx)) if ok else None,
        "diff_vs_long": M.band((x - lx)[np.isfinite(x - lx)], alpha=ALPHA) if ok else None,
        "sharpe": float(np.nanmean(x) / np.nanstd(x) * np.sqrt(12)) if ok and np.nanstd(x) > 0 else None,
        "long_sharpe": float(np.nanmean(lx) / np.nanstd(lx) * np.sqrt(12)) if ok and np.nanstd(lx) > 0 else None,
        "mdd": max_drawdown(x), "long_mdd": max_drawdown(lx), "worst": float(np.nanmin(x)) if ok else None,
        "y2022": float(np.prod([1 + ser[j] for j in ok if months[j].startswith("2022")]) - 1) if any(months[j].startswith("2022") for j in ok) else None,
        "long_share": float((mx["S"][mx["V"]] > 0).mean()) if mx["V"].any() else None,
        "assets_per_month": float(np.mean(mx["V"].sum(0)[ok])) if ok else None,
        "per_asset": {n: (float(np.nanmean(np.where(mx["V"][i], vals[i], np.nan))) if mx["V"][i].any() else None)
                      for i, n in enumerate(mx["names"])},
    }
    return res


def month_list(first, last=LAST):
    out, (y, m) = [], first
    while (y, m) <= last:
        out.append(f"{y:04d}-{m:02d}")
        y, m = (y + (m == 12), m % 12 + 1)
    return out


# ════════════════════ 読み込み・本番 ════════════════════

def load_q1():
    out = {}
    for tk, _ in Q1_ASSETS:
        df = P.fetch(tk, "1d", start=START)
        out[tk] = monthly_table(df["Close"]) if df is not None and len(df) else None
    return out


def load_q2():
    import fx_bars
    out, info = {}, {}
    for pair in FX_PAIRS:
        df = fx_bars.load(pair, start=fx_bars.EARLY[0])
        c, sp = fx_daily(df)
        out[pair] = monthly_table(c, sp) if c is not None else None
        info[pair] = [str(c.index.min().date()), str(c.index.max().date())] if c is not None and len(c) else None
    return out, info


def coverage(tables):
    return {k: ([str(v.index.min()), str(v.index.max()), int(len(v))] if v is not None and not v.empty else None) for k, v in tables.items()}


def first_month(tables):
    starts = [v.index.min() for v in tables.values() if v is not None and not v.empty]
    if not starts:
        return None
    y, m = ym_tuple(min(starts))
    mm = y * 12 + m - 1 + LOOK + 3
    return mm // 12, mm % 12 + 1


def render_md(res):
    L = ["# R11 株価指数・商品（MT4）と為替（MT5）の時系列モメンタム", "",
         f"更新: {res.get('generated_at', '')}（事前登録＝`PILLAR_PREREG.md`「R11」・指紋 `{(res.get('prereg_sha256') or '')[:12]}`）", ""]
    r = res.get("result") or {}
    if "error" in r:
        return "\n".join(L + [f"⚠️ 計算できず：{r['error']}", "", "※ 研究の記録です。投資助言ではありません。"]) + "\n"
    L += ["向き＝過去12か月の上げ下げで買い（+1）か売り（−1）・量＝年10％の値動きにそろえる（上限3倍）・月末に決めて次の月末まで持つ。"
          "1か月の値＝資産の平均（費用後・Q2 はスワップ込み）。幅は 97.5％（2つの腕・6か月のかたまり）・偽薬は向きの札の入れ替え 2,000回（片側）。",
          f"為替のスワップ＝BIS の政策金利（{r.get('bis_url') or '届かず'}）。", "", "## まとめ（判定）", "",
          "| 腕 | 判定 | 月 | 1か月の平均 | 幅 | 昔／前半 | 最近／後半 | 偽薬 p |", "|---|---|---:|---:|---|---:|---:|---:|"]
    for key, name in (("q1", "Q1 株価指数・商品（MT4）"), ("q2", "Q2 為替（MT5）")):
        a = r.get(key) or {}
        if not a:
            continue
        lab = a.get("half_labels") or ("昔", "最近")
        L.append(f"| {name} | **{a['verdict']}** | {a['months']}（{a['first']}〜{a['last']}） | {M._p(a['full']['mean'])} | {M._band(a['full'])} | "
                 f"{lab[0]} {M._p(a['old']['mean'])} | {lab[1]} {M._p(a['new']['mean'])}（{M._band(a['new'])}） | "
                 f"{'—' if a['placebo_p'] is None else format(a['placebo_p'], '.4f')} |")
    L += ["", "## 読むための表（判定しない）", ""]
    for key, name in (("q1", "Q1 株価指数・商品"), ("q2", "Q2 為替"), ("q2_noswap", "Q2 為替（スワップ抜き・読むだけ）")):
        a = r.get(key)
        if not a:
            continue
        rd = a["read"]
        d = rd.get("diff_vs_long") or {}
        sh = lambda v: "—" if v is None else f"{v:.2f}"
        L += [f"### {name}", "",
              f"- いつも買い（同じ量・同じ費用）の1か月の平均 {M._p(rd['long_mean'])}・差（時系列モメンタム − いつも買い）{M._p(d.get('mean'))}（{M._band(d)}）",
              f"- 成績÷ばらつき（年あたり）{sh(rd['sharpe'])}（いつも買い {sh(rd['long_sharpe'])}）・最大の下落 {M._p(rd['mdd'], 0)}（いつも買い {M._p(rd['long_mdd'], 0)}）"
              f"・最悪の月 {M._p(rd['worst'])}・2022年 {M._p(rd['y2022'], 1)}",
              f"- 買いの割合 {('—' if rd['long_share'] is None else format(rd['long_share'] * 100, '.0f') + '％')}・1か月に数えた資産 {sh(rd['assets_per_month'])}",
              "- 資産ごとの1か月の平均：" + "・".join(f"{n} {M._p(v)}" for n, v in rd["per_asset"].items()), ""]
    L += ["## 注意", "", "- 商品の先物は「つないだ値段」（乗り換えの段差が入る）・指数は配当なし・CFD の持ち越しの金利（年3％）と為替の上乗せ（年1％）は目安",
          "- 量の決め方（年10％・上限3倍）は事前に決めた1つの形だけ。過去の成績は将来を約束しない", "", "---", "",
          "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def verdicts_of(r, today):
    out = {}
    for key, qid in (("q1", "Q1"), ("q2", "Q2")):
        a = r.get(key) or {}
        if a.get("verdict") in (REV, NONE):
            f = a["full"]
            out[qid] = {"status": "stop", "decided_on": today, "n": f["n"], "mean": f["mean"], "lo": f["lo"], "hi": f["hi"],
                        "reason": "過去のデータで1回だけ数えて" + (
                            "逆向き" if a["verdict"] == REV else
                            "、でたらめな向きには勝つが、費用後の平均の幅が0をまたぐ" if (a.get("placebo_p") or 1) < ALPHA else
                            "、でたらめな向きと区別できない") + f"（費用後の1か月の平均・{a['first']}〜{a['last']}）"}
    return out


def main(argv):
    res = {"generated_at": dt.datetime.now(P.JST).isoformat(timespec="minutes"), "prereg_file": P.PREREG,
           "prereg_sha256": P.prereg_sha256()}
    try:
        q1 = load_q1()
        q2, fxinfo = load_q2()
        rates, bis_url = fetch_bis()
        f2 = first_month(q2)
        m1, m2 = month_list(FIRST_Q1), (month_list(f2) if f2 else [])
        if "--check" in argv:
            mx1 = matrices(q1, m1, "q1")
            mx2 = matrices(q2, m2, "q2", rates or None)
            print(json.dumps({"q1_coverage": coverage(q1), "q2_coverage": fxinfo, "bis_url": bis_url,
                              "bis_areas": {a: [min(v), max(v), len(v)] for a, v in rates.items()},
                              "q1_months_counted": int((mx1["V"].sum(0) >= MIN_ASSETS).sum()),
                              "q2_months_counted": int((mx2["V"].sum(0) >= MIN_ASSETS).sum()) if m2 else 0,
                              "q2_first_decision": m2[0] if m2 else None}, ensure_ascii=False, indent=1))
            return 0
        r = {"bis_url": bis_url, "q1_coverage": coverage(q1), "q2_coverage": fxinfo}
        r["q1"] = analyze_arm(matrices(q1, m1, "q1"), "q1")
        if m2:
            r["q2_noswap"] = analyze_arm(matrices(q2, m2, "q2", None), "q2", judge=False)
            r["q2"] = analyze_arm(matrices(q2, m2, "q2", rates), "q2") if rates else dict(r["q2_noswap"], verdict=SKIP)
        res["result"] = r
        res.update(kind="backtest", titles={"Q1": "株価指数・商品の時系列モメンタム（12か月の向き・量をそろえる・月1・CFD の費用と金利・1回だけ数えた）",
                                            "Q2": "為替の時系列モメンタム（12ペア・12か月の向き・量をそろえる・月1・費用とスワップ・1回だけ数えた）"},
                   verdicts=verdicts_of(r, dt.datetime.now(P.JST).date().isoformat()))
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        if "--check" in argv:
            return 1
        res["result"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(M.rounded(res), fh, ensure_ascii=False, indent=1, default=str)
    md = render_md(res)
    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
