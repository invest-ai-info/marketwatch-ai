# -*- coding: utf-8 -*-
"""トレンドの見方の比べ比べ（T1〜T9・2026-09-27 オーナー決定「その形で進めてください」）。

一覧＝TREND_INDICATORS.md。機械で数えられるトレンドの見方を、同じ物差しで「でたらめな向き（偽薬）」と比べる。
⚠️ 見方の決め方・物差し・判定は PILLAR_PREREG.md「トレンドの見方の比べ比べ」と下の定数に固定。結果を見てから動かさない。
⚠️ 出力 trend-lab.json / trend-lab.md は GitHub 側で生成＝手元から送らない（SYNC禁忌）。
⚠️ エンジン・発火条件・固定オラクルには触れない（読むだけ・別に計算する）。

実行: python trend_lab.py   （Actions の trend-lab.yml から手動で）
"""
import datetime as dt
import json
import math
import sys

import numpy as np
import pandas as pd

import pillar_lab as P

OUT_JSON, OUT_MD = "trend-lab.json", "trend-lab.md"
START = "2006-01-01"
WARMUP = 260
SPLIT = "2016-01-01"            # 探索＝2015年まで／確かめ＝2016年から（入る日で分ける）
MIN_N = 300
N_DEFS = 9
P_LIMIT = 0.05 / N_DEFS         # 9つ試すので厳しくする
VOL_DAYS = 20

TICKERS = {  # 監視18銘柄と資産の種類（regime_lab.CLASS_OF と同じ）
    "GC=F": "commodity", "SI=F": "commodity", "CL=F": "commodity",
    "NKD=F": "index", "ES=F": "index", "NQ=F": "index", "YM=F": "index", "^FTSE": "index",
    "BTC-USD": "crypto",
    "USDJPY=X": "fx", "EURJPY=X": "fx", "GBPJPY=X": "fx", "AUDJPY=X": "fx",
    "EURUSD=X": "fx", "GBPUSD=X": "fx", "AUDUSD=X": "fx", "EURAUD=X": "fx", "GBPAUD=X": "fx",
}
CLASS_JA = {"fx": "為替", "index": "株価指数", "commodity": "商品", "crypto": "ビットコイン"}
NAMES = {"T1": "移動平均（25・75本・いまのエンジン）", "T2": "200日線", "T3": "ダウ理論（山と谷）",
         "T4": "一目均衡表（三役好転・逆転）", "T5": "ドンチャン55日（タートル）", "T6": "スーパートレンド",
         "T7": "GMMA（指数平滑線の束）", "T8": "平均足（3本）", "T9": "ADX／DMI"}


# ════════════════════ 見方（その日の終値までで決まる ＋1／−1／0）════════════════════

def _keep(raw):
    """0 のところは前の状態を続ける（最初は0）"""
    out, cur = np.zeros(len(raw)), 0.0
    for i, v in enumerate(raw):
        if v != 0:
            cur = v
        out[i] = cur
    return out


def rma(x, n):
    """ワイルダーの平滑（ADX・値動きの大きさで使う）"""
    return pd.Series(x).ewm(alpha=1 / n, adjust=False).mean().values


def true_range(h, l, c):
    pc = np.concatenate([[c[0]], c[:-1]])
    return np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))


def t1_ma(c):
    s = pd.Series(c)
    m25, m75 = s.rolling(25).mean(), s.rolling(75).mean()
    up = (m25 > m75) & (m25 > m25.shift(5))
    dn = (m25 < m75) & (m25 < m25.shift(5))
    return np.where(up, 1.0, np.where(dn, -1.0, 0.0))


def t2_ma200(c):
    m = pd.Series(c).rolling(200).mean().values
    return np.where(np.isnan(m), 0.0, np.where(c > m, 1.0, np.where(c < m, -1.0, 0.0)))


def t3_dow(h, l, n=5):
    """山＝前後 n 本の中で一番高い高値、谷＝一番安い安値。n 本後に確定（先を見ない）。
    直近の山と谷がどちらも1つ前より高い＝＋1、どちらも低い＝−1、それ以外は前の状態を続ける"""
    L = len(h)
    raw = np.zeros(L)
    peaks, troughs = [], []
    state = 0.0
    for i in range(L):
        j = i - n                                     # いま確定する候補
        if j - n >= 0:
            win_h, win_l = h[j - n:j + n + 1], l[j - n:j + n + 1]
            if h[j] == win_h.max() and np.argmax(win_h) == n:
                peaks.append(h[j])
            if l[j] == win_l.min() and np.argmin(win_l) == n:
                troughs.append(l[j])
        if len(peaks) >= 2 and len(troughs) >= 2:
            if peaks[-1] > peaks[-2] and troughs[-1] > troughs[-2]:
                state = 1.0
            elif peaks[-1] < peaks[-2] and troughs[-1] < troughs[-2]:
                state = -1.0
        raw[i] = state
    return raw


def t4_ichimoku(h, l, c):
    H, Lw, C = pd.Series(h), pd.Series(l), pd.Series(c)
    tenkan = (H.rolling(9).max() + Lw.rolling(9).min()) / 2
    kijun = (H.rolling(26).max() + Lw.rolling(26).min()) / 2
    span_a = ((tenkan + kijun) / 2).shift(26)            # 26本前に計算した先行スパン＝いまの雲
    span_b = ((H.rolling(52).max() + Lw.rolling(52).min()) / 2).shift(26)
    top, bot = np.maximum(span_a, span_b), np.minimum(span_a, span_b)
    chikou_up, chikou_dn = C > C.shift(26), C < C.shift(26)
    up = (tenkan > kijun) & (C > top) & chikou_up
    dn = (tenkan < kijun) & (C < bot) & chikou_dn
    return np.where(up, 1.0, np.where(dn, -1.0, 0.0))


def t5_donchian(h, l, c, n=55):
    hi = pd.Series(h).shift(1).rolling(n).max().values
    lo = pd.Series(l).shift(1).rolling(n).min().values
    raw = np.where(c > hi, 1.0, np.where(c < lo, -1.0, 0.0))
    return _keep(np.nan_to_num(raw))


def t6_supertrend(h, l, c, n=10, m=3.0):
    atr = rma(true_range(h, l, c), n)
    hl2 = (h + l) / 2
    bu, bl = hl2 + m * atr, hl2 - m * atr
    fu, fl = bu.copy(), bl.copy()
    st = np.zeros(len(c))
    for i in range(1, len(c)):
        fu[i] = bu[i] if (bu[i] < fu[i - 1] or c[i - 1] > fu[i - 1]) else fu[i - 1]
        fl[i] = bl[i] if (bl[i] > fl[i - 1] or c[i - 1] < fl[i - 1]) else fl[i - 1]
        prev = st[i - 1] if st[i - 1] != 0 else 1.0
        if prev < 0 and c[i] > fu[i]:
            st[i] = 1.0
        elif prev > 0 and c[i] < fl[i]:
            st[i] = -1.0
        else:
            st[i] = prev
    st[:n] = 0.0
    return st


def t7_gmma(c):
    s = pd.Series(c)
    short = np.vstack([s.ewm(span=k, adjust=False).mean().values for k in (3, 5, 8, 10, 12, 15)])
    long_ = np.vstack([s.ewm(span=k, adjust=False).mean().values for k in (30, 35, 40, 45, 50, 60)])
    up = short.min(axis=0) > long_.max(axis=0)
    dn = short.max(axis=0) < long_.min(axis=0)
    return np.where(up, 1.0, np.where(dn, -1.0, 0.0))


def t8_heikin(o, h, l, c, k=3):
    hc = (o + h + l + c) / 4
    ho = np.zeros(len(c))
    ho[0] = (o[0] + c[0]) / 2
    for i in range(1, len(c)):
        ho[i] = (ho[i - 1] + hc[i - 1]) / 2
    bull = pd.Series((hc > ho).astype(float))
    bear = pd.Series((hc < ho).astype(float))
    up = bull.rolling(k).sum().values == k
    dn = bear.rolling(k).sum().values == k
    return np.where(up, 1.0, np.where(dn, -1.0, 0.0))


def t9_adx(h, l, c, n=14, th=25.0):
    up_move = np.concatenate([[0.0], h[1:] - h[:-1]])
    dn_move = np.concatenate([[0.0], l[:-1] - l[1:]])
    pdm = np.where((up_move > dn_move) & (up_move > 0), up_move, 0.0)
    ndm = np.where((dn_move > up_move) & (dn_move > 0), dn_move, 0.0)
    atr = rma(true_range(h, l, c), n)
    with np.errstate(divide="ignore", invalid="ignore"):
        pdi = 100 * rma(pdm, n) / atr
        ndi = 100 * rma(ndm, n) / atr
        dx = 100 * np.abs(pdi - ndi) / (pdi + ndi)
    adx = rma(np.nan_to_num(dx), n)
    up = (adx > th) & (pdi > ndi)
    dn = (adx > th) & (ndi > pdi)
    return np.where(up, 1.0, np.where(dn, -1.0, 0.0))


def all_states(df):
    o, h, l, c = (np.asarray(df[k].values, float) for k in ("Open", "High", "Low", "Close"))
    return {"T1": t1_ma(c), "T2": t2_ma200(c), "T3": t3_dow(h, l), "T4": t4_ichimoku(h, l, c),
            "T5": t5_donchian(h, l, c), "T6": t6_supertrend(h, l, c), "T7": t7_gmma(c),
            "T8": t8_heikin(o, h, l, c), "T9": t9_adx(h, l, c)}


# ════════════════════ 物差し（月ごと）════════════════════

def month_ends(index):
    """各月の最終取引日の位置"""
    days = [x.date() for x in index]
    last = {}
    for i, d in enumerate(days):
        last[(d.year, d.month)] = i
    return [last[k] for k in sorted(last)]


def monthly_rows(ticker, df, states):
    """月末の向きで次の月末まで持つ。1件＝{ticker, date, def, sign, raw, z}"""
    c = np.asarray(df["Close"].values, float)
    lr = np.diff(np.log(c))
    ends = month_ends(df.index)
    rows = []
    for a, b in zip(ends[:-1], ends[1:]):
        if a < WARMUP or b <= a:
            continue
        v = float(np.std(lr[a - VOL_DAYS:a], ddof=1))
        if not v > 0:
            continue
        n_days = b - a
        raw = math.log(c[b] / c[a]) / (v * math.sqrt(n_days))
        date = df.index[a].date().isoformat()
        for k, st in states.items():
            s = st[a]
            if s != 0 and not np.isnan(s):
                rows.append({"ticker": ticker, "date": date, "def": k, "sign": float(s), "raw": raw, "z": s * raw,
                             "conv": ""})
        rows.append({"ticker": ticker, "date": date, "def": "LONG", "sign": 1.0, "raw": raw, "z": raw, "conv": ""})
    return rows


def judge(r):
    if r.get("n", 0) < MIN_N:
        return "件数不足"
    lo, hi, e, l, p = (r.get(k) for k in ("lo", "hi", "early", "late", "p_perm"))
    if None in (lo, hi, e, l, p):
        return "偽薬と差なし"
    if lo > 0 and e > 0 and l > 0 and p < P_LIMIT:
        return "偽薬より当てになる"
    if hi < 0 and e < 0 and l < 0 and p < P_LIMIT:
        return "逆に効く"
    return "偽薬と差なし"


def stats_for(rows, n_perm=P.N_PERM, seed=P.SEED):
    if not rows:
        return {"n": 0, "verdict": "件数不足"}
    res = P.mean_ci([r["z"] for r in rows], [(r["ticker"], r["date"][:7]) for r in rows])
    early = [r["z"] for r in rows if r["date"] < SPLIT]
    late = [r["z"] for r in rows if r["date"] >= SPLIT]
    res.update({"early": P._mean(early), "late": P._mean(late), "n_early": len(early), "n_late": len(late),
                "p_perm": P.perm_p(rows, n_perm, seed), "share_long": sum(r["sign"] > 0 for r in rows) / len(rows)})
    res["by_class"] = {CLASS_JA[k]: {"n": len(v), "mean": P._mean(v)}
                       for k in ("fx", "index", "commodity", "crypto")
                       for v in [[r["z"] for r in rows if TICKERS.get(r["ticker"]) == k]] if v}
    res["verdict"] = judge(res)
    return res


def agreement(rows):
    """見方どうしで向きが同じだった割合（同じ銘柄・同じ月で両方が0でないとき）"""
    by = {}
    for r in rows:
        if r["def"] != "LONG":
            by.setdefault((r["ticker"], r["date"]), {})[r["def"]] = r["sign"]
    keys = sorted(NAMES)
    out = {}
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            both = [(m[a], m[b]) for m in by.values() if a in m and b in m]
            if both:
                out[f"{a}-{b}"] = sum(x == y for x, y in both) / len(both)
    return out


def run(n_perm=P.N_PERM):
    all_rows, got, missing = [], {}, []
    for tk in TICKERS:
        df = P.fetch(tk, "1d", start=START)
        if df is None or len(df) < WARMUP + 40:
            missing.append(tk)
            continue
        df = df.dropna(subset=["Open", "High", "Low", "Close"])
        got[tk] = {"first": df.index[0].date().isoformat(), "last": df.index[-1].date().isoformat(), "bars": len(df)}
        all_rows += monthly_rows(tk, df, all_states(df))
    out = {"tickers": got, "missing": missing, "defs": {}}
    for k in list(NAMES) + ["LONG"]:
        rows = [r for r in all_rows if r["def"] == k]
        st = stats_for(rows, n_perm=n_perm)
        if k == "LONG":
            st.pop("p_perm", None)
            st["verdict"] = "参考（いつも買い）"
        out["defs"][k] = st
    out["agreement"] = agreement(all_rows)
    return out


def render_md(res):
    f = P._f
    L = ["# トレンドの見方の比べ比べ（T1〜T9）", "",
         f"作成: {res['generated_at']}（GitHub Actions で計算）。事前登録＝`{P.PREREG}`「トレンドの見方の比べ比べ」（指紋 sha256 `{(res.get('prereg_sha256') or '')[:16]}…`）。",
         "物差し＝月末の向きで次の月末まで持ったときの値動き÷普段のばらつき（プラスなら向きが当たった）。**売買の決まりではない**。", ""]
    r = res.get("result") or {}
    if r.get("error"):
        L += [f"- ⚠️ 計算できず: {r['error']}", ""]
    else:
        L += [f"判定＝平均の95%の幅がまるごと0より上・前半（2015年まで）と後半（2016年から）ともプラス・偽薬との比較 p＜{P_LIMIT:.4f}（9つ試すので厳しく）", "",
              "| 見方 | 件数 | 上昇の割合 | 平均 | 95%の幅 | 前半 | 後半 | 偽薬との比較 p | 判定 |",
              "|---|---:|---:|---:|---|---:|---:|---:|---|"]
        for k, name in list(NAMES.items()) + [("LONG", "（参考）いつも買い")]:
            x = (r.get("defs") or {}).get(k) or {}
            L.append(f"| {k} {name} | {x.get('n', 0)} | {f((x.get('share_long') or 0) * 100, 0, False)}% | {f(x.get('mean'))} | "
                     f"{f(x.get('lo'))}〜{f(x.get('hi'))} | {f(x.get('early'))} | {f(x.get('late'))} | "
                     f"{f(x.get('p_perm'), 4, False)} | {x.get('verdict', '—')} |")
        L += ["", "読むための表（資産の種類別の平均）", "", "| 見方 | 為替 | 株価指数 | 商品 | ビットコイン |", "|---|---:|---:|---:|---:|"]
        for k, name in list(NAMES.items()) + [("LONG", "いつも買い")]:
            bc = ((r.get("defs") or {}).get(k) or {}).get("by_class") or {}
            L.append(f"| {k} | " + " | ".join(f"{f((bc.get(c) or {}).get('mean'))}（{(bc.get(c) or {}).get('n', 0)}）"
                                            for c in ("為替", "株価指数", "商品", "ビットコイン")) + " |")
        ag = r.get("agreement") or {}
        if ag:
            L += ["", "見方どうしの向きの一致率（高い＝ほぼ同じことを見ている）：" +
                  "、".join(f"{k} {v * 100:.0f}%" for k, v in sorted(ag.items(), key=lambda x: -x[1])[:10]), ""]
        if r.get("missing"):
            L += [f"- 値段を取れなかった銘柄: {', '.join(r['missing'])}", ""]
    L += ["---", "", "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def main():
    res = {"generated_at": dt.datetime.now(P.JST).isoformat(timespec="minutes"),
           "prereg_file": P.PREREG, "prereg_sha256": P.prereg_sha256()}
    try:
        res["result"] = run()
    except Exception as e:  # noqa: BLE001
        res["result"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1, default=str)
    md = render_md(res)
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
