# -*- coding: utf-8 -*-
"""R1 持ち方の研究：ビットコインと株価指数を「ただ持つ」のと、「200日線で離れる」「値動きに合わせて量を変える」のでは、
費用と税を引いたあとどちらが良いか。2026-10-05 登録・オーナー「システムトレードで勝つ方法、資産を増やす方法を考えてください」
→「余剰資金で徹底的な研究を進めていきたい」。

⚠️ 物差しと判定の基準は PILLAR_PREREG.md「R1 持ち方の研究」（事前登録・計算より先にコミット）と下の定数に固定。
   結果を見てから動かさない。出力には事前登録の中身の指紋（sha256）を書き込む。
⚠️ 1回だけ数える。データの取得に失敗した資産があれば何も数えずに終わる（その資産だけやり直してよい＝出力に書く）。
⚠️ 出力 hold-lab.json / .md は GitHub 側で生成＝手元から送らない（SYNC禁忌）。研究資金の金額はどこにも書かない
   （計算は「最初の資金＝1」で行う）。
⚠️ エンジン・発火条件・固定オラクル（signal_lab_verify.py）には触れない。メールや売買の決まりは変えない。

事前登録に書いていない細かい決め方（計算より先にここで固定）:
  - 年率にする日数＝ビットコイン 365（土日も動く）・株価指数 252
  - 最大の下落は日々の資産の曲線（現金＋持っている量×終値。年末に払った税は引く・最後の売り切りは入れない）で測る。
    年率の成績は「最後の日にすべて売って税を払ったあとの資産」÷最初の資金で測る（全期間）。前半・後半は曲線の両端で測る
  - 費用は取得価格に足し、売った代金から引く（日本の税の計算と同じ扱い）
  - 片側 p は (当てはまった回数＋1)÷(回数＋1)＝box_lab.placebo_p と同じ数え方（0にしない・少し厳しめ）
  - 乱数の種は SEED に固定（同じデータなら同じ答え）

実行: python hold_lab.py   （Actions の hold-lab.yml から手動で）
"""
import datetime as dt
import json
import math
import sys

import numpy as np
import pandas as pd

from pillar_lab import fetch, prereg_sha256

JST = dt.timezone(dt.timedelta(hours=9))
FETCH_START = "1985-01-01"
WARMUP = 260            # 最初の260日は線を作るためだけに使う
SMA_BASE = 200
SMA_NEAR = (150, 250)
VOL_WIN = 60            # 値動きの大きさを測る日数
VT_NEAR = (0.75, 1.25)  # 目標の0.75倍・1.25倍
CARRY_YEARS = 3         # 株価指数の損の繰り越し
N_COMPARE = 12          # 3つの持ち方×4資産
ALPHA = 0.05 / N_COMPARE
DD_RATIO = 0.75
N_BOOT = 2000
BLOCK = 60              # ブロック・ブートストラップの平均のかたまりの長さ（日）
N_PLACEBO = 1000
SEED = 20261005
BOOT_CHUNK = 250
BTC_READING_RATES = (0.20, 0.55)
METHODS = ("M200", "VT", "M200VT")
METHOD_NAME = {"H": "ただ持ち続ける", "M200": "200日線で離れる", "VT": "値動きに合わせて量を変える",
               "M200VT": "200日線×値動きで量"}
ASSETS = {
    "BTC": {"name": "ビットコイン", "kind": "btc", "cost": 0.0015, "tax": 0.30, "vt_target": 0.40, "ann": 365},
    "SP500": {"name": "米国株（S&P500・配当込み・円建て）", "kind": "index", "cost": 0.0005, "tax": 0.20315,
              "vt_target": 0.12, "ann": 252},
    "TOPIX": {"name": "日本株（TOPIX連動ETF 1306・配当調整済み）", "kind": "index", "cost": 0.0005, "tax": 0.20315,
              "vt_target": 0.12, "ann": 252},
    "NIFTY": {"name": "インド株（Nifty50・配当なし・円建て）", "kind": "index", "cost": 0.0005, "tax": 0.20315,
              "vt_target": 0.12, "ann": 252},
}
VERDICTS = ("◎ 確認", "◯ 傾向", "△ 守りだけ", "✕")
OUT_JSON, OUT_MD = "hold-lab.json", "hold-lab.md"
# 🆕 2026-10-05 追記：データの取得の失敗の直し方（PILLAR_PREREG.md「R1」の追記・数え直しより先にコミット）
UNIT_LO, UNIT_HI = 8.7, 11.5   # 前の日との比がこの範囲（またはその逆数）＝10倍の単位のずれ
UNIT_BACK_DAYS = 10            # この日数のうちに逆向きの同じずれで戻れば「その間だけのずれ」
FX_SPIKE, FX_BACK = 0.04, 0.025   # 為替：4%以上動いて、次の日に戻り、2日の変化が2.5%以内＝1日だけの跳ね
FX_TICKERS = ("USDJPY=X", "INRJPY=X", "INR=X")
CROSS_GAP = 0.10               # 🆕 追記2：1306.T と 1348.T の1日の変化がこれ以上食い違う日＝1306.T の段差


# ════════════════════ データ ════════════════════

def to_jpy(px, fx):
    """外貨建ての値段 px に、その日の円の為替 fx を掛ける。為替が無い日（土日・祝日のずれ）は直前の値"""
    fx = fx.sort_index()
    f = fx.reindex(fx.index.union(px.index)).ffill().reindex(px.index)
    return (px * f).dropna()


def _unit(r):
    if UNIT_LO <= r <= UNIT_HI:
        return 10.0
    if 1 / UNIT_HI <= r <= 1 / UNIT_LO:
        return 0.1
    return None


def clean(s, fx=False):
    """取得の失敗だけを直す（2026-10-05 追記）。→ (直した Series, 直した記録のリスト)
    ① 単位のずれ（どの元データも）：前の日との比が10倍か1/10に近い日。10日以内に逆向きの同じずれで戻るなら、
       その間の値を戻す。戻らなければ、それより前の値をすべて同じ比で直す（分割の調整漏れ）
    ② 1日だけの跳ね（為替だけ）：前の日から4%以上動き、次の日に逆向きへ戻って2日の変化が2.5%以内なら、前の日の値に置き換える"""
    v = s.to_numpy(float).copy()
    ix = s.index
    fixes = []
    t = 1
    while t < len(v):
        f = _unit(v[t] / v[t - 1])
        if f is None:
            t += 1
            continue
        back = next((k for k in range(t + 1, min(len(v), t + UNIT_BACK_DAYS + 1))
                     if _unit(v[k] / v[k - 1]) == 1 / f), None)
        if back is not None:
            fixes.append({"kind": "単位のずれ（その間だけ）", "from": str(ix[t].date()), "to": str(ix[back - 1].date()),
                          "factor": 1 / f})
            v[t:back] /= f
            t = back + 1
        else:
            fixes.append({"kind": "単位のずれ（それより前をすべて）", "from": str(ix[0].date()),
                          "to": str(ix[t - 1].date()), "factor": f})
            v[:t] *= f
            t += 1
    if fx:
        for t in range(1, len(v) - 1):
            r1, r2 = v[t] / v[t - 1] - 1, v[t + 1] / v[t] - 1
            if abs(r1) >= FX_SPIKE and r1 * r2 < 0 and abs(v[t + 1] / v[t - 1] - 1) <= FX_BACK:
                fixes.append({"kind": "1日だけの跳ね", "from": str(ix[t].date()), "to": str(ix[t].date()),
                              "was": float(v[t]), "now": float(v[t - 1])})
                v[t] = v[t - 1]
    return pd.Series(v, index=ix, name=s.name), fixes


def cross_fix(s, ref, ref_name, gap=CROSS_GAP):
    """③（追記2）同じ指数に連動するもう1本の ETF と、両方の値がある日の1日の変化が gap 以上食い違う日は、
    s のその日の変化を ref の変化に置き換える（その日より前の s をすべて同じ比で直す）。→ (直した Series, 記録)"""
    j = pd.concat([s, ref], axis=1, keys=["s", "r"]).dropna()
    rs, rr = j["s"].pct_change(), j["r"].pct_change()
    bad = j.index[((rs - rr).abs() > gap).to_numpy()]
    v = s.copy()
    fixes = []
    for d in bad:
        k = (1 + rs[d]) / (1 + rr[d])
        before = v.index < d
        fixes.append({"kind": f"{ref_name} との食い違い（それより前をすべて）", "from": str(v.index[0].date()),
                      "to": str(v.index[before][-1].date()), "factor": float(k),
                      "day": str(d.date()), "own": float(rs[d]), "ref": float(rr[d])})
        v[before] = v[before] * k
    return v, fixes


def load_prices(fetcher=fetch, until=None):
    """→ ({資産: 円建ての終値の Series}, 取れなかった資産, {資産: 使った表記}, {元データ: 直した記録})
    until＝この日までに切る（数え直しで期間を1回目とそろえるため）"""
    fixes = {}

    def get(tk):
        df = fetcher(tk, "1d", start=FETCH_START)
        if df is None:
            return None
        s = df["Close"].astype(float)
        s = s[s > 0]
        if until is not None:
            s = s[s.index <= pd.Timestamp(until)]
        s, fx = clean(s, fx=tk in FX_TICKERS)
        if fx:
            fixes[tk] = fx
        return s

    out, missing, src = {}, [], {}
    usd = get("USDJPY=X")
    b = get("BTC-JPY")
    if b is not None:
        out["BTC"], src["BTC"] = b, "BTC-JPY"
    else:
        bu = get("BTC-USD")
        if bu is not None and usd is not None:
            out["BTC"], src["BTC"] = to_jpy(bu, usd), "BTC-USD×USDJPY=X（BTC-JPY が取れず）"
        else:
            missing.append("BTC")
    sp = get("^SP500TR")
    if sp is not None and usd is not None:
        out["SP500"], src["SP500"] = to_jpy(sp, usd), "^SP500TR×USDJPY=X"
    else:
        missing.append("SP500")
    tp = get("1306.T")
    ref = get("1348.T") if tp is not None else None
    if tp is not None and ref is not None:
        tp, f3 = cross_fix(tp, ref, "1348.T")
        if f3:
            fixes.setdefault("1306.T", []).extend(f3)
        out["TOPIX"], src["TOPIX"] = tp, "1306.T（1348.T と突き合わせ）"
    else:
        missing.append("TOPIX")
    nf, inr = get("^NSEI"), get("INRJPY=X")
    usd_inr = get("INR=X") if nf is not None and inr is None and usd is not None else None
    if nf is not None and inr is not None:
        out["NIFTY"], src["NIFTY"] = to_jpy(nf, inr), "^NSEI×INRJPY=X"
    elif usd_inr is not None:
        cross = (usd / usd_inr.reindex(usd.index).ffill()).dropna()   # 円/ルピー＝円/ドル÷ルピー/ドル
        out["NIFTY"], src["NIFTY"] = to_jpy(nf, cross), "^NSEI×(USDJPY=X÷INR=X)（INRJPY=X が取れず同じ値を作った）"
    else:
        missing.append("NIFTY")
    return out, missing, src, fixes


ASSET_TICKERS = {"BTC": ("BTC-JPY", "BTC-USD", "USDJPY=X"), "SP500": ("^SP500TR", "USDJPY=X"), "TOPIX": ("1306.T", "1348.T"),
                 "NIFTY": ("^NSEI", "INRJPY=X", "INR=X", "USDJPY=X")}


def fixes_for(asset, src, fixes):
    """その資産に使った元データのうち、直しが入ったもの"""
    used = [tk for tk in ASSET_TICKERS[asset] if tk in src.get(asset, "")]
    return {tk: fixes[tk] for tk in used if tk in fixes}


# ════════════════════ 持つ割合 ════════════════════

def m200_weights(p, n):
    """w[t]＝前の日（t−1）の終値が n 日の単純平均より上なら1、下なら0。その日（t）の終値で売買する。決められない日は NaN"""
    p = np.asarray(p, float)
    sma = pd.Series(p).rolling(n, min_periods=n).mean().to_numpy()
    sig = np.where(np.isnan(sma), np.nan, (p > sma).astype(float))
    w = np.full(len(p), np.nan)
    w[1:] = sig[:-1]
    return w


def month_end_mask(dates):
    """月の最後の行（次の行の月が違う）。最後の行は月の途中かもしれないので月末にしない"""
    ym = np.asarray(dates.year) * 12 + np.asarray(dates.month)
    me = np.zeros(len(ym), bool)
    me[:-1] = ym[1:] != ym[:-1]
    return me


def vt_weights(p, dates, target, ann):
    """月の最後の日 m の終値で過去60日の値動きの大きさ（日々の対数の変化の標準偏差×√ann）を測り、割合＝min(1, 目標÷大きさ)。
    次の日（m+1）の終値で合わせ、次に合わせる日まで同じ割合。→ (w, 合わせる日の印)。決められない日は NaN"""
    p = np.asarray(p, float)
    n = len(p)
    lr = np.diff(np.log(p))            # lr[k]＝p[k]→p[k+1]
    me = month_end_mask(dates)
    w = np.full(n, np.nan)
    ex = np.zeros(n, bool)
    cur = np.nan
    for t in range(1, n):
        m = t - 1
        if me[m] and m >= VOL_WIN:
            vol = float(np.std(lr[m - VOL_WIN:m], ddof=1)) * math.sqrt(ann)
            cur = min(1.0, target / vol) if vol > 0 else 1.0
            ex[t] = True
        w[t] = cur
    return w, ex


def changes(x):
    out = np.zeros(len(x), bool)
    out[1:] = x[1:] != x[:-1]
    return out


# ════════════════════ 費用と税を入れた売買 ════════════════════

def year_tax(G, carry, year, kind, rate):
    """その年の売って出た利益 G（損ならマイナス）の税。→ (税, 新しい繰り越し [(年, 損の額)])
    ビットコイン＝同じ年の中だけで相殺・繰り越さない／株価指数＝損を3年繰り越す（古いものから使う）"""
    if kind == "btc":
        return max(G, 0.0) * rate, []
    carry = [(y, a) for y, a in carry if year - y <= CARRY_YEARS]
    if G <= 0:
        return 0.0, carry + ([(year, -G)] if G < 0 else [])
    rem, new = G, []
    for y, a in carry:
        use = min(a, rem)
        rem -= use
        if a - use > 1e-15:
            new.append((y, a - use))
    return rem * rate, new


def pay_tax(C, U, A, G, carry, P, cost, year, kind, rate):
    """年末に税を現金から払う。足りなければ年末の値段で売って払い、その売りで出た利益も同じ年に入れる。
    → (現金, 量, 新しい繰り越し, 払った税)"""
    net = P * (1 - cost)
    x = 0.0
    for _ in range(200):
        tax, _c = year_tax(G + x * (net - A), carry, year, kind, rate)
        need = tax - (C + x * net)
        if need <= 1e-12 or x >= U:
            break
        x = min(U, x + need / net)
    tax, new_carry = year_tax(G + x * (net - A), carry, year, kind, rate)
    return C + x * net - tax, U - x, new_carry, tax


def simulate(p, dates, w, rebal, cost, rate, kind):
    """最初の資金1で、rebal の日の終値で持つ割合を w に合わせる（0日目は必ず合わせる）。年末に税、最後の日に売り切って税。
    → {curve: 日々の資産（最後の売り切りの前）, final: 売り切って税を払ったあと, taxes, trades, expo}"""
    p = np.asarray(p, float)
    n = len(p)
    yr = np.asarray(dates.year)
    ye = np.zeros(n, bool)
    ye[:-1] = yr[1:] != yr[:-1]
    reb = np.asarray(rebal, bool).copy()
    reb[0] = True
    ev = np.flatnonzero(reb | ye | (np.arange(n) == n - 1))
    C, U, A, G = 1.0, 0.0, 0.0, 0.0
    carry, taxes, trades, final = [], 0.0, 0, None
    Cs, Us = np.empty(len(ev)), np.empty(len(ev))
    for k, t in enumerate(ev):
        P = p[t]
        if reb[t]:
            V = C + U * P
            tgt = float(w[t])
            nu = tgt * (V + cost * U * P) / (P * (1 + tgt * cost))        # 買うとき
            if nu < U:
                nu = tgt * (V - cost * U * P) / (P * (1 - tgt * cost))    # 売るとき
            d = nu - U
            if abs(d) * P > 1e-12:
                if d > 0:
                    spend = d * P * (1 + cost)
                    A = (U * A + spend) / nu
                    C -= spend
                else:
                    proceeds = -d * P * (1 - cost)
                    G += proceeds - (-d) * A
                    C += proceeds
                U = nu if nu > 1e-15 else 0.0
                if t > 0:
                    trades += 1
        if t == n - 1:
            Cs[k], Us[k] = C, U
            if U > 0:
                proceeds = U * P * (1 - cost)
                G += proceeds - U * A
                C += proceeds
            tax, carry = year_tax(G, carry, int(yr[t]), kind, rate)
            taxes += tax
            final = C - tax
        else:
            if ye[t]:
                C, U, carry, tax = pay_tax(C, U, A, G, carry, P, cost, int(yr[t]), kind, rate)
                taxes += tax
                G = 0.0
            Cs[k], Us[k] = C, U
    seg = np.searchsorted(ev, np.arange(n), side="right") - 1
    curve = Cs[seg] + Us[seg] * p
    expo = np.where(curve > 0, Us[seg] * p / np.where(curve > 0, curve, 1), 0.0)
    return {"curve": curve, "final": float(final), "taxes": float(taxes), "trades": trades, "expo": expo}


# ════════════════════ 物差し ════════════════════

def max_dd(curve):
    c = np.asarray(curve, float)
    return float((c / np.maximum.accumulate(c) - 1).min())


def cagr(v0, v1, years):
    return float((v1 / v0) ** (1 / years) - 1) if v1 > 0 and years > 0 else -1.0


def calmar(g, dd):
    return float(g / max(-dd, 1e-9))


def years_between(d0, d1):
    return (d1 - d0).days / 365.25


def longest_underwater(curve, dates):
    """元の高値を下回っていた、いちばん長い日数（暦日）"""
    peak, pi, best, below = curve[0], 0, 0, False
    for i in range(1, len(curve)):
        if curve[i] >= peak:
            if below:
                best = max(best, (dates[i] - dates[pi]).days)
            peak, pi, below = curve[i], i, False
        else:
            below = True
    if below:
        best = max(best, (dates[-1] - dates[pi]).days)
    return int(best)


def worst_12m(curve, dates):
    d = np.asarray(dates.values, dtype="datetime64[D]")
    k = np.searchsorted(d, d - np.timedelta64(365, "D"), side="right") - 1
    ok = k >= 0
    if not ok.any():
        return None
    return float((curve[ok] / curve[k[ok]] - 1).min())


def seg_stats(curve, dates, i0, i1):
    c = curve[i0:i1 + 1]
    g = cagr(c[0], c[-1], years_between(dates[i0], dates[i1]))
    dd = max_dd(c)
    return {"cagr": g, "maxdd": dd, "calmar": calmar(g, dd)}


def metrics(sim, dates):
    c = sim["curve"]
    n = len(c)
    yrs = years_between(dates[0], dates[-1])
    g = cagr(1.0, sim["final"], yrs)
    dd = max_dd(c)
    mid = n // 2
    return {"cagr": g, "maxdd": dd, "calmar": calmar(g, dd),
            "first": seg_stats(c, dates, 0, mid), "second": seg_stats(c, dates, mid, n - 1),
            "underwater_days": longest_underwater(c, dates), "worst_12m": worst_12m(c, dates),
            "trades_per_year": sim["trades"] / yrs, "avg_exposure": float(sim["expo"].mean()),
            "days_in_share": float((sim["expo"] > 1e-9).mean()), "taxes_per_start": sim["taxes"]}


# ════════════════════ ブートストラップと偽薬 ════════════════════

def boot_indices(n, b, rng, block=BLOCK):
    """平均 block 日のかたまり（長さは幾何分布）でつないだ添字（止まらないブートストラップ）"""
    idx = np.empty((b, n), np.int64)
    idx[:, 0] = rng.integers(0, n, b)
    jump = rng.random((b, n)) < 1.0 / block
    starts = rng.integers(0, n, (b, n))
    for t in range(1, n):
        idx[:, t] = np.where(jump[:, t], starts[:, t], (idx[:, t - 1] + 1) % n)
    return idx


def _boot_calmar(r, idx, c0, liq, years):
    cs = c0 * np.cumprod(1 + r[idx], axis=1)
    full = np.hstack([np.full((cs.shape[0], 1), c0), cs])
    dd = (full / np.maximum.accumulate(full, axis=1) - 1).min(axis=1)
    g = np.where(cs[:, -1] * liq > 0, np.abs(cs[:, -1] * liq) ** (1 / years) - 1, -1.0)
    return g / np.maximum(-dd, 1e-9)


def boot_p(sim_s, sim_h, dates, rng, n_boot=N_BOOT):
    """日々の成績を H と組にしたまま引き直し、「Calmar の差≦0」の割合（片側 p）。最後の売り切りの税は元の比のまま掛ける"""
    cs, ch = sim_s["curve"], sim_h["curve"]
    rs, rh = cs[1:] / cs[:-1] - 1, ch[1:] / ch[:-1] - 1
    ls, lh = sim_s["final"] / cs[-1], sim_h["final"] / ch[-1]
    yrs = years_between(dates[0], dates[-1])
    hit, done = 0, 0
    while done < n_boot:
        b = min(BOOT_CHUNK, n_boot - done)
        idx = boot_indices(len(rs), b, rng)
        d = _boot_calmar(rs, idx, cs[0], ls, yrs) - _boot_calmar(rh, idx, ch[0], lh, yrs)
        hit += int((d <= 0).sum())
        done += b
    return (hit + 1) / (n_boot + 1)


def shuffle_runs(x, rng):
    """0/1 の並びの、持つ区間・持たない区間の長さをそれぞれ入れ替える（区間の数＝売買回数と、持つ日の数は同じ）"""
    x = np.asarray(x, float)
    cut = np.r_[0, np.flatnonzero(np.diff(x) != 0) + 1, len(x)]
    vals, lens = x[cut[:-1]], np.diff(cut)
    ins, outs = list(rng.permutation(lens[vals == 1])), list(rng.permutation(lens[vals == 0]))
    out = np.empty(len(x))
    pos = 0
    for v in vals:
        L = ins.pop() if v == 1 else outs.pop()
        out[pos:pos + L] = v
        pos += L
    return out


def shuffle_months(w, ex, rng):
    """合わせる日で区切った区間（ひと月）ごとの割合の並びを入れ替える。区間の日付はそのまま"""
    w = np.asarray(w, float)
    starts = np.unique(np.r_[0, np.flatnonzero(ex)])
    ends = np.r_[starts[1:], len(w)]
    return np.repeat(rng.permutation(w[starts]), ends - starts)


def verdict(chk, p_placebo):
    """(a)〜(e) と偽薬の p から ◎／◯／△／✕"""
    if all(chk[k] for k in "abcde"):
        return VERDICTS[0]
    if chk["a"] and chk["b"] and chk["c"] and p_placebo < 0.05:
        return VERDICTS[1]
    if chk["b"] and p_placebo >= 0.05:
        return VERDICTS[2]
    return VERDICTS[3]


# ════════════════════ 1つの資産を数える ════════════════════

def evaluate(px, cfg, seed=SEED, n_boot=N_BOOT, n_placebo=N_PLACEBO):
    p_all = np.asarray(px.values, float)
    d_all = pd.DatetimeIndex(px.index)
    m = {n: m200_weights(p_all, n) for n in (SMA_BASE,) + SMA_NEAR}
    vt = {f: vt_weights(p_all, d_all, cfg["vt_target"] * f, cfg["ann"]) for f in (1.0,) + VT_NEAR}
    s = WARMUP
    while s < len(p_all) and (any(np.isnan(v[s]) for v in m.values()) or any(np.isnan(v[0][s]) for v in vt.values())):
        s += 1
    p, d = p_all[s:], d_all[s:]
    if len(p) < 500:
        raise ValueError("評価できる日が少なすぎる")

    def plan(meth, sma=SMA_BASE, f=1.0):
        if meth == "H":
            return np.ones(len(p)), np.zeros(len(p), bool)
        mw = m[sma][s:]
        vw, vex = vt[f][0][s:], vt[f][1][s:]
        if meth == "M200":
            return mw, changes(mw)
        if meth == "VT":
            return vw, vex
        return mw * vw, changes(mw) | vex

    def run(w, reb, rate=cfg["tax"]):
        return simulate(p, d, w, reb, cfg["cost"], rate, cfg["kind"])

    def near_plans(meth):
        if meth == "M200":
            return {f"{n}日": plan(meth, sma=n) for n in SMA_NEAR}
        if meth == "VT":
            return {f"目標×{f}": plan(meth, f=f) for f in VT_NEAR}
        return {f"{n}日": plan(meth, sma=n) for n in SMA_NEAR}

    rng = np.random.default_rng(seed)
    sim_h = run(*plan("H"))
    res = {"H": metrics(sim_h, d)}
    hm = res["H"]
    for meth in METHODS:
        w, reb = plan(meth)
        sim = run(w, reb)
        r = metrics(sim, d)
        near = {k: calmar_of(run(*v), d) for k, v in near_plans(meth).items()}
        pb = boot_p(sim, sim_h, d, rng, n_boot)
        pl = placebo_p(meth, plan, run, d, r["calmar"], rng, n_placebo)
        chk = {
            "a": all(r[k]["calmar"] > hm[k]["calmar"] for k in ("first", "second")) and r["calmar"] > hm["calmar"],
            "b": all(abs(r[k]["maxdd"]) <= DD_RATIO * abs(hm[k]["maxdd"]) for k in ("first", "second"))
                 and abs(r["maxdd"]) <= DD_RATIO * abs(hm["maxdd"]),
            "c": all(v > hm["calmar"] for v in near.values()),
            "d": pb < ALPHA,
            "e": pl < ALPHA,
        }
        r.update({"near_calmar": near, "p_boot": pb, "p_placebo": pl, "checks": chk, "verdict": verdict(chk, pl)})
        res[meth] = r
    # 読むための数字（判定には使わない）
    reading = {"no_tax": {}}
    for meth in ("H",) + METHODS:
        sim0 = run(*plan(meth), rate=0.0)
        reading["no_tax"][meth] = {"cagr": cagr(1.0, sim0["final"], years_between(d[0], d[-1])),
                                   "maxdd": max_dd(sim0["curve"]), "calmar": calmar_of(sim0, d)}
    if cfg["kind"] == "btc":
        for rt in BTC_READING_RATES:
            reading[f"tax_{int(rt * 100)}"] = {meth: {"calmar": calmar_of(run(*plan(meth), rate=rt), d)}
                                               for meth in ("H",) + METHODS}
    info = {"first_date": str(d_all[0].date()), "eval_start": str(d[0].date()), "eval_end": str(d[-1].date()),
            "mid_date": str(d[len(d) // 2].date()), "n_days": int(len(p)), "years": years_between(d[0], d[-1]),
            "max_abs_daily_change": float(np.max(np.abs(np.diff(p) / p[:-1])))}
    return {"info": info, "results": res, "reading": reading}


def calmar_of(sim, dates):
    return calmar(cagr(1.0, sim["final"], years_between(dates[0], dates[-1])), max_dd(sim["curve"]))


def placebo_p(meth, plan, run, dates, real_calmar, rng, n_placebo=N_PLACEBO):
    """偽薬の Calmar が本物以上だった割合（片側 p）。M200＝区間の長さの並び／VT＝月ごとの割合の並び／M200VT＝両方を入れ替える"""
    mw, _ = plan("M200")
    vw, vex = plan("VT")
    hit = 0
    for _ in range(n_placebo):
        if meth == "M200":
            w = shuffle_runs(mw, rng)
            reb = changes(w)
        elif meth == "VT":
            w, reb = shuffle_months(vw, vex, rng), vex
        else:
            sm = shuffle_runs(mw, rng)
            w, reb = sm * shuffle_months(vw, vex, rng), changes(sm) | vex
        if calmar_of(run(w, reb), dates) >= real_calmar - 1e-12:
            hit += 1
    return (hit + 1) / (n_placebo + 1)


# ════════════════════ 書き出し ════════════════════

def _pct(x, nd=1, sign=False):
    if x is None:
        return "—"
    return f"{x * 100:+.{nd}f}%" if sign else f"{x * 100:.{nd}f}%"


def _f(x, nd=2):
    return "—" if x is None else f"{x:.{nd}f}"


def render_md(out):
    L = ["# R1 持ち方の研究（ビットコインと株価指数）", "",
         f"- 生成: {out['generated_jst']}　事前登録の指紋（PILLAR_PREREG.md の sha256）: `{out['prereg_sha256']}`",
         "- 物差しと判定＝PILLAR_PREREG.md「R1 持ち方の研究」（計算より先にコミット）。**過去のデータで1回だけ数えた結果**",
         "- 課税口座で持つとして、費用と税を引いたあと。最初の資金を1として計算（金額は書かない）",
         f"- 関門＝ブートストラップと偽薬の片側 p＜0.05÷{N_COMPARE}（{ALPHA:.5f}）"]
    for rr in out.get("reruns", []):
        L.append(f"- やり直し: {rr['jst']} に {'・'.join(rr['assets'])} だけ数え直した（{rr['reason']}・"
                 f"データは {rr['until'] or '最後'} まで）。ほかの資産は1回目の結果のまま")
    L.append("")
    if out["missing"]:
        L += [f"## ⚠️ データが取れなかった資産：{'・'.join(out['missing'])}", "",
              "何も数えていない（1回だけ数えるため）。この資産のデータが取れたときだけ、やり直してよい。", ""]
        return "\n".join(L) + "\n"
    L += ["## 判定の一覧", "", "| 資産 | 200日線で離れる | 値動きに合わせて量を変える | 200日線×値動きで量 |", "|---|---|---|---|"]
    for a, r in out["assets"].items():
        L.append(f"| {ASSETS[a]['name']} | " + " | ".join(r["results"][m]["verdict"] for m in METHODS) + " |")
    L += ["", "◎ 確認＝(a)〜(e) すべて／◯ 傾向＝(a)(b)(c) と偽薬 p＜0.05／△ 守りだけ＝最大の下落は浅いが、"
          "持つ日をでたらめに減らしても同じくらい（偽薬 p≧0.05）／✕＝それ以外", ""]
    for a, r in out["assets"].items():
        i = r["info"]
        L += [f"## {ASSETS[a]['name']}", "",
              f"- データ: {out['sources'].get(a, '')}／評価 {i['eval_start']}〜{i['eval_end']}（{i['years']:.1f}年・"
              f"前半と後半の境 {i['mid_date']}）／1日の最大の変化 {_pct(i['max_abs_daily_change'])}",
              f"- 数えた日: {r.get('counted_jst', out['generated_jst'])}／事前登録の指紋 "
              f"`{(r.get('prereg_sha256') or out['prereg_sha256'] or '')[:12]}…`",
              "- データの直し: " + ("なし" if not r.get("data_fixes") else "／".join(
                  f"{tk} {x['kind']} {x['from']}" + (f"〜{x['to']}" if x['to'] != x['from'] else "")
                  for tk, xs in r["data_fixes"].items() for x in xs)),
              f"- 費用 片道 {ASSETS[a]['cost'] * 100:.2f}%／税 {ASSETS[a]['tax'] * 100:.3g}%"
              + ("（損は繰り越さない）" if ASSETS[a]["kind"] == "btc" else "（損は3年繰り越す）"), "",
              "| 持ち方 | 判定 | Calmar 全期間 | 前半 | 後半 | 最大の下落 全期間 | 前半 | 後半 | 年率（税のあと） | "
              "ブートストラップ p | 偽薬 p | 近い設定の Calmar |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for m in ("H",) + METHODS:
            x = r["results"][m]
            near = "・".join(f"{k} {_f(v)}" for k, v in x.get("near_calmar", {}).items()) or "—"
            L.append(f"| {METHOD_NAME[m]} | {x.get('verdict', '（比べる相手）')} | {_f(x['calmar'])} | "
                     f"{_f(x['first']['calmar'])} | {_f(x['second']['calmar'])} | {_pct(x['maxdd'])} | "
                     f"{_pct(x['first']['maxdd'])} | {_pct(x['second']['maxdd'])} | {_pct(x['cagr'], sign=True)} | "
                     f"{_f(x.get('p_boot'), 4) if 'p_boot' in x else '—'} | "
                     f"{_f(x.get('p_placebo'), 4) if 'p_placebo' in x else '—'} | {near} |")
        L += ["", "| 持ち方 | (a) | (b) | (c) | (d) | (e) | 元の高値を下回った最長 | 最悪の12か月 | 売買/年 | "
              "平均の持つ割合 | 持っていた日 | 払った税（最初の資金=1） |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for m in ("H",) + METHODS:
            x = r["results"][m]
            ck = x.get("checks")
            marks = " | ".join(("◯" if ck[k] else "✕") if ck else "—" for k in "abcde")
            L.append(f"| {METHOD_NAME[m]} | {marks} | {x['underwater_days']}日 | {_pct(x['worst_12m'], sign=True)} | "
                     f"{_f(x['trades_per_year'], 1)} | {_pct(x['avg_exposure'], 0)} | {_pct(x['days_in_share'], 0)} | "
                     f"{_f(x['taxes_per_start'], 3)} |")
        rd = r["reading"]
        L += ["", "読むための数字（判定には使わない）:",
              "- 税なし（非課税口座）の Calmar: " + "・".join(f"{METHOD_NAME[m]} {_f(rd['no_tax'][m]['calmar'])}"
                                                    for m in ("H",) + METHODS)
              + "　⚠️ 非課税口座の中で売り買いすると枠が戻るのは翌年"]
        for k in sorted(x for x in rd if x.startswith("tax_")):
            L.append(f"- 税 {k[4:]}% の Calmar: " + "・".join(f"{METHOD_NAME[m]} {_f(rd[k][m]['calmar'])}"
                                                           for m in ("H",) + METHODS))
        L.append("")
    L += ["## 読み方の約束と限界", "",
          "- ◎ でも過去の1回の数え上げ。前向きの確かめは売買が年に数回なので何年もかかる。使うかどうかはオーナーが決める。"
          "サイトの記事で「この持ち方が良い」とは書かない",
          "- ✕・△ は「ただ持ち続ける」を変える理由が見つからなかった、という結果。これも研究の答え",
          "- インド株は配当を含まない（年1%前後の差）。TOPIX は ETF の配当調整の値で、信託報酬を含む",
          "- 現金の利息0・借りて増やさない・約定の滑りは入れていない",
          "- 税は単純化（平均の取得価格・年末にまとめて払う・住民税込みの一律の率）。実際の税率は所得で変わる（ビットコインは20〜55%）",
          "- ビットコインは歴史が短く、大きな下落の回数が少ない＝前半・後半の比べが粗い",
          "- 過去の成績は将来を約束しない。情報提供であり投資助言ではない", ""]
    return "\n".join(L) + "\n"


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="数え直す資産（カンマ区切り）。ほかは今の hold-lab.json の結果をそのまま使う")
    ap.add_argument("--until", default="", help="この日までのデータで数える（YYYY-MM-DD）")
    a = ap.parse_args(argv)
    only = [x for x in a.only.split(",") if x]
    if any(x not in ASSETS for x in only):
        print(f"知らない資産: {only}", file=sys.stderr)
        return 2
    now = dt.datetime.now(JST).strftime("%Y-%m-%dT%H:%M+09:00")
    prices, missing, src, fixes = load_prices(until=a.until or None)
    targets = only or list(ASSETS)
    missing = [x for x in missing if x in targets]
    if only:
        with open(OUT_JSON, encoding="utf-8") as f:
            out = json.load(f)
        for k, r in out["assets"].items():            # 1回目の結果に、いつ・どの登録で数えたかを書き足す
            r.setdefault("counted_jst", out["generated_jst"])
            r.setdefault("prereg_sha256", out["prereg_sha256"])
        if missing:
            print(f"数え直す資産のデータが取れない: {missing}（何も書き換えない）", file=sys.stderr)
            return 1
        out.setdefault("reruns", []).append({"jst": now, "assets": only, "until": a.until or None,
                                            "prereg_sha256": prereg_sha256(),
                                            "reason": "データの取得の失敗（PILLAR_PREREG.md「R1」の追記）"})
    else:
        out = {"generated_jst": now, "prereg_sha256": prereg_sha256(),
               "kind": "backtest", "section": "R1", "missing": missing, "sources": {},
               "settings": {"warmup": WARMUP, "alpha": ALPHA, "n_boot": N_BOOT, "block": BLOCK,
                            "n_placebo": N_PLACEBO, "seed": SEED, "dd_ratio": DD_RATIO},
               "assets": {}}
    if not missing:
        for x in targets:
            print(f"{x}: {len(prices[x])} 日 を数える", file=sys.stderr)
            r = evaluate(prices[x], ASSETS[x])
            r.update({"counted_jst": now, "prereg_sha256": prereg_sha256(), "data_fixes": fixes_for(x, src, fixes)})
            out["assets"][x] = r
            out["sources"][x] = src[x]
    out["assets"] = {x: out["assets"][x] for x in ASSETS if x in out["assets"]}
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    md = render_md(out)
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(md)
    print(md)
    return 0 if not missing else 1


if __name__ == "__main__":
    sys.exit(main())
