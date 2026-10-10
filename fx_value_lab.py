# -*- coding: utf-8 -*-
"""F2 為替の割安と経済の勢い：8つの通貨を、物価で直した割安さ（V）と、物価・雇用の数字の勢い（E）で並べ、月1回入れ替える。
2026-10-10 登録・オーナー「おすすめ通りにお願いします」（テクニカルの区切りのあとの、ファンダメンタルの柱の1本目）。PILLAR_PREREG.md「F2」。

V＝log（使える最新の月の 54〜66か月前の13か月の平均）− log（使える最新の月の値）＝BIS の実質実効為替レート。大きい＝割安＝買い。
E＝物価の勢い（前年比 − 12か月前の前年比）と雇用の勢い（−〔失業率 − 12か月前の失業率〕）の、通貨どうしの順位の平均。
使える値＝月ごとは参照の月が t−2 以前・四半期ごとは最後の月が t−3 以前。重み＝「順位 − 順位の平均」に比例・買い1・売り1。

⚠️ 決まりは PILLAR_PREREG.md「F2」と下の定数に固定。出力（fx-value-lab.json / .md）は集計だけ（SYNC禁忌）。
実行: python fx_value_lab.py --check   （点検だけ＝BIS・OECD・FRED に届くか・通貨ごとの期間・合図がそろう月の数。損益は数えない・何も書き出さない）
      python fx_value_lab.py           （本番。Actions の fx-value-lab.yml から手動で・1回だけ。データの取り口は PREREG「F2」の追記）
"""
import csv
import io
import json
import re
import sys
import urllib.error
import urllib.request

import datetime as dt

import numpy as np

import momentum_lab as M
import pillar_lab as P
import tsmom_lab as T

# ════════════════════ 事前登録の値（PILLAR_PREREG.md「F2」） ════════════════════
CCYS = ("USD", "EUR", "GBP", "JPY", "AUD", "CHF", "CAD", "NZD")
PAIRS = ("EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCHF", "USDCAD", "NZDUSD")
BIS_AREA = {"USD": "US", "EUR": "XM", "GBP": "GB", "JPY": "JP", "AUD": "AU", "CHF": "CH", "CAD": "CA", "NZD": "NZ"}
OECD_AREA = {"USD": "USA", "EUR": "EA20", "GBP": "GBR", "JPY": "JPN", "AUD": "AUS", "CHF": "CHE", "CAD": "CAN", "NZD": "NZL"}
LAG_M = 2                   # 月ごとの値＝参照の月が t−2 以前
LAG_Q = 3                   # 四半期ごとの値＝最後の月が t−3 以前
STALE = 14                  # 使える最新の値が t−14 より古ければ、その月の合図に入れない
V_FROM, V_TO = 54, 66       # V＝最新の月の 54〜66か月前の13か月の平均
MOM = 12                    # E＝12か月前との差
MIN_CCY = 6                 # 合図がそろう通貨がこれ未満の月は数えない
LAST = (2026, 8)
SPLIT = (2015, 1)           # 最近＝この月から
N_ARMS = 3
ALPHA = 0.05 / N_ARMS
N_BOOT, N_PERM, BLOCK = 10000, 2000, 6
FX_PIPS_JPY, FX_PIPS_OTHER, FX_MARKUP = 1.2, 1.8, 0.01
FIRST = (2004, 1)           # 決める月の最初（置き場の最初の月）
# 追記（2026-10-10・check のあと、数える前）＝データの取り口
CPI_QUARTERLY = ("AUD", "NZD")                         # 公式の消費者物価が四半期ごと＝3・6・9・12月の行だけ・四半期の遅れ
UNE_PICK = {"USD": ("USA", "M"), "EUR": ("EA", "M"), "GBP": ("GBR", "M"), "JPY": ("JPN", "M"), "AUD": ("AUS", "M"),
            "CAD": ("CAN", "M"), "CHF": ("CHE", "Q"), "NZD": ("NZL", "Q")}
UNE_KEY = ("UNE_LF_M", "PT_LF_SUB", "Y", "_T", "Y_GE15")   # 総数・季節調整済み・全体・15歳以上
OUT_JSON, OUT_MD = "fx-value-lab.json", "fx-value-lab.md"
OK, NEW_ONLY, REV, NONE, SKIP = "✅ 効く", "△ 最近だけ", "✕ 逆向き", "✕ 見えない", "― 判定しない（スワップを数えられない）"
ARMS = (("V", "V 割安（実質実効為替レートの5年の変化）"), ("E", "E 経済の勢い（物価の前年比・失業率の12か月の変化）"),
        ("VE", "VE 割安と経済の勢いを半分ずつ"))

# ════════════════════ 取り口（check で確かめる・決まりではない） ════════════════════
_BIS_AREAS = "+".join(BIS_AREA[c] for c in CCYS)
BIS_REER_URLS = (f"https://stats.bis.org/api/v1/data/WS_EER/M.R.B.{_BIS_AREAS}?format=csv",
                 f"https://stats.bis.org/api/v2/data/dataflow/BIS/WS_EER/1.0/M.R.B.{_BIS_AREAS}?format=csv")
BIS_CPI_URLS = (f"https://stats.bis.org/api/v1/data/WS_LONG_CPI/M+Q.{_BIS_AREAS}.628+771?format=csv",
                f"https://stats.bis.org/api/v2/data/dataflow/BIS/WS_LONG_CPI/1.0/M+Q.{_BIS_AREAS}.628+771?format=csv")
OECD_FLOWS_URL = "https://sdmx.oecd.org/public/rest/dataflow/all?detail=allstubs"
OECD_UNE_URLS = ("https://sdmx.oecd.org/public/rest/data/OECD.SDD.TPS,DSD_LFS@DF_IALFS_UNE_M,1.0/all?startPeriod=1995-01&format=csvfile",)
UNE_DIMS = ("REF_AREA", "MEASURE", "UNIT_MEASURE", "ADJUSTMENT", "SEX", "AGE", "FREQ")   # 失業率の総数＝UNE_LF_M・PT_LF_SUB・_T・Y_GE15
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
FRED_UNE = {"USD": ("LRHUTTTTUSM156S",), "EUR": ("LRHUTTTTEZM156S",), "GBP": ("LRHUTTTTGBM156S",), "JPY": ("LRHUTTTTJPM156S",),
            "AUD": ("LRHUTTTTAUM156S",), "CHF": ("LRHUTTTTCHM156S", "LRHUTTTTCHQ156S"), "CAD": ("LRHUTTTTCAM156S",),
            "NZD": ("LRHUTTTTNZM156S", "LRHUTTTTNZQ156S")}


def get_text(url, timeout=300):
    """→ (本文, None) か (None, 失敗の理由)"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": P.UA, "Accept": "text/csv, application/xml, */*"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", "replace"), None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}"
    except Exception as e:  # noqa: BLE001  通信の失敗はまとめて書く
        return None, f"{type(e).__name__}: {str(e)[:80]}"


# ════════════════════ 読み方 ════════════════════

def period_key(s):
    """'2020-01'・'2020-Q1'・'2020-01-31' → ('M'|'Q', 年, 最後の月)。読めなければ None"""
    s = str(s).strip()
    m = re.fullmatch(r"(\d{4})-Q([1-4])", s)
    if m:
        return "Q", int(m.group(1)), int(m.group(2)) * 3
    m = re.fullmatch(r"(\d{4})-(\d{2})(?:-\d{2})?", s)
    if m and 1 <= int(m.group(2)) <= 12:
        return "M", int(m.group(1)), int(m.group(2))
    return None


def parse_sdmx_csv(text, dims=("REF_AREA", "FREQ")):
    """SDMX の CSV（BIS・OECD）→ {(dims の値…): {(年, 月): 値}}。dims は大文字小文字を問わない・無い列は '' として扱う"""
    rd = csv.DictReader(io.StringIO(text))
    cols = {c.upper(): c for c in (rd.fieldnames or [])}
    t, v = cols.get("TIME_PERIOD"), cols.get("OBS_VALUE")
    if not (t and v):
        return {}
    out = {}
    for r in rd:
        try:
            val = float(r[v])
        except (TypeError, ValueError):
            continue
        pk = period_key(r[t])
        if not pk or not np.isfinite(val):
            continue
        key = tuple(r.get(cols.get(d.upper(), ""), "") or "" for d in dims)
        out.setdefault(key, {})[(pk[1], pk[2])] = val
    return out


def parse_fred_csv(text):
    """FRED の fredgraph.csv → {(年, 月): 値}（'.' は飛ばす）"""
    rows = list(csv.reader(io.StringIO(text)))
    out = {}
    for r in rows[1:]:
        if len(r) < 2:
            continue
        pk = period_key(r[0])
        try:
            val = float(r[1])
        except ValueError:
            continue
        if pk:
            out[(pk[1], pk[2])] = val
    return out


def flows_matching(xml, word="UNE"):
    """OECD の dataflow の一覧（XML）から、id に word を含むもの"""
    ids = re.findall(r'<structure:Dataflow[^>]*\bid="([^"]+)"[^>]*\bagencyID="([^"]+)"', xml)
    ids += [(i, a) for a, i in re.findall(r'<structure:Dataflow[^>]*\bagencyID="([^"]+)"[^>]*\bid="([^"]+)"', xml)]
    return sorted({f"{a},{i}" for i, a in ids if word in i})


def span(series):
    """{(年, 月): 値} → ['YYYY-MM', 'YYYY-MM', 件数]"""
    if not series:
        return None
    ks = sorted(series)
    return [f"{ks[0][0]:04d}-{ks[0][1]:02d}", f"{ks[-1][0]:04d}-{ks[-1][1]:02d}", len(ks)]


def freq_of(series):
    """月の並びから 'M' か 'Q' を推す（月の間隔の中央値が3なら Q）"""
    ks = sorted(series)
    if len(ks) < 3:
        return "?"
    gaps = [(b[0] * 12 + b[1]) - (a[0] * 12 + a[1]) for a, b in zip(ks, ks[1:])]
    return "Q" if float(np.median(gaps)) >= 3 else "M"


# ════════════════════ 決まり（使える値・合図・重み） ════════════════════

def mi(y, m):
    return y * 12 + m - 1


def latest_usable(series, t, freq):
    """決める月 t（(年, 月)）に使える最新の値 → ((年, 月), 値)。無い・古すぎれば None"""
    if not series:
        return None
    lim = mi(*t) - (LAG_Q if freq == "Q" else LAG_M)
    ok = [k for k in series if mi(*k) <= lim]
    if not ok:
        return None
    k = max(ok, key=lambda x: mi(*x))
    if mi(*k) < mi(*t) - STALE:
        return None
    return k, series[k]


def v_signal(reer, t):
    """V＝log（最新の月の 54〜66か月前の13か月の平均）− log（最新の月の値）。足りなければ None"""
    got = latest_usable(reer, t, "M")
    if not got:
        return None
    (y, m), now = got
    base = mi(y, m)
    past = [reer.get(((base - k) // 12, (base - k) % 12 + 1)) for k in range(V_FROM, V_TO + 1)]
    if any(p is None or p <= 0 for p in past) or now <= 0:
        return None
    return float(np.log(np.mean(past)) - np.log(now))


def yoy(series, k):
    """前年比（％）＝ k の値 ÷ 12か月前の値 − 1"""
    b = mi(*k) - 12
    prev = series.get((b // 12, b % 12 + 1))
    cur = series.get(k)
    if prev is None or cur is None or prev <= 0:
        return None
    return (cur / prev - 1) * 100


def momentum(level_fn, series, t, freq):
    """勢い＝（使える最新の値）−（その12か月前の値）。level_fn(series, k) で値を作る"""
    got = latest_usable(series, t, freq)
    if not got:
        return None
    k = got[0]
    b = mi(*k) - MOM
    k0 = (b // 12, b % 12 + 1)
    a, z = level_fn(series, k), level_fn(series, k0)
    if a is None or z is None:
        return None
    return a - z


def ranks(sig):
    """{通貨: 値} → {通貨: 順位（1＝最小・同じ値は平均）}"""
    items = sorted(sig.items(), key=lambda x: x[1])
    out, i = {}, 0
    while i < len(items):
        j = i
        while j + 1 < len(items) and items[j + 1][1] == items[i][1]:
            j += 1
        for k in range(i, j + 1):
            out[items[k][0]] = (i + j) / 2 + 1
        i = j + 1
    return out


def rank_weights(sig):
    """{通貨: 合図} → {通貨: 重み}（「順位 − 順位の平均」に比例・買いの合計1・売りの合計1）。MIN_CCY 未満・全部同じなら None"""
    sig = {c: v for c, v in sig.items() if v is not None and np.isfinite(v)}
    if len(sig) < MIN_CCY:
        return None
    r = ranks(sig)
    mean = np.mean(list(r.values()))
    d = {c: r[c] - mean for c in r}
    tot = sum(abs(x) for x in d.values()) / 2
    if tot <= 0:
        return None
    return {c: x / tot for c, x in d.items()}


def e_signal(cpi, une, t, cpi_freq, une_freq):
    """E＝物価の勢いと雇用の勢いの、通貨どうしの順位の平均。cpi・une は {通貨: {(年, 月): 値}}。une が空なら物価だけ"""
    pm = {c: momentum(yoy, cpi.get(c) or {}, t, cpi_freq.get(c, "M")) for c in CCYS}
    pm = {c: v for c, v in pm.items() if v is not None}
    if not une:
        return pm
    um = {c: momentum(lambda s, k: s.get(k), une.get(c) or {}, t, une_freq.get(c, "M")) for c in CCYS}
    um = {c: -v for c, v in um.items() if v is not None}
    both = [c for c in CCYS if c in pm and c in um]
    rp, ru = ranks({c: pm[c] for c in both}), ranks({c: um[c] for c in both})
    return {c: (rp[c] + ru[c]) / 2 for c in both}


def month_list(first, last=LAST):
    out, (y, m) = [], first
    while (y, m) <= last:
        out.append((y, m))
        y, m = (y + (m == 12), m % 12 + 1)
    return out


# ════════════════════ 点検（check） ════════════════════

def pick_cpi(parsed):
    """BIS の消費者物価（指数 628）→ ({通貨: {(年, 月): 指数}}, {通貨: 'M'|'Q'})。
    豪ドル・NZドルは 3・6・9・12月の行だけを四半期の値として使う（PREREG「F2」の追記）。月ごとが無ければ四半期の行"""
    out, freq = {}, {}
    for c in CCYS:
        a = BIS_AREA[c]
        m = parsed.get(("M", a, "628")) or {}
        q = parsed.get(("Q", a, "628")) or {}
        if c in CPI_QUARTERLY:
            s = {k: v for k, v in (m or q).items() if k[1] in (3, 6, 9, 12)}
            if s:
                out[c], freq[c] = s, "Q"
        elif len(m) >= 24:
            out[c], freq[c] = m, "M"
        elif q:
            out[c], freq[c] = q, "Q"
    return out, freq


def pick_une(parsed):
    """OECD の失業率（UNE_DIMS で読んだもの）→ ({通貨: {(年, 月): ％}}, {通貨: 'M'|'Q'})（PREREG「F2」の追記の系列）"""
    out, freq = {}, {}
    for c, (area, f) in UNE_PICK.items():
        s = parsed.get((area,) + UNE_KEY + (f,)) or {}
        if s:
            out[c], freq[c] = s, f
    return out, freq


def check(get=get_text, fx_root=None):
    rep = {"prereg_sha256": P.prereg_sha256()}
    # 政策金利（スワップ）＝R11 と同じ取り口
    rates, bis_url = T.fetch_bis(get=(lambda u: _must(get, u)) if get is not get_text else None)
    rep["bis_cbpol"] = {"url": bis_url, "areas": {a: [min(v), max(v), len(v)] for a, v in rates.items()}}
    # 実質実効為替レート
    reer = {}
    for u in BIS_REER_URLS:
        text, err = get(u)
        if text:
            p = parse_sdmx_csv(text, ("REF_AREA",))
            reer = {c: p.get((BIS_AREA[c],), {}) for c in CCYS}
            rep["bis_reer"] = {"url": u, "areas": {c: span(s) for c, s in reer.items()}}
            if sum(1 for s in reer.values() if s) >= MIN_CCY:
                break
        else:
            rep.setdefault("bis_reer_errors", []).append(f"{u[:60]}… {err}")
    # 消費者物価
    cpi, cpi_freq = {}, {}
    for u in BIS_CPI_URLS:
        text, err = get(u)
        if text:
            p = parse_sdmx_csv(text, ("FREQ", "REF_AREA", "UNIT_MEASURE"))
            rep["bis_cpi"] = {"url": u, "series": {"|".join(k): span(s) for k, s in sorted(p.items())}}
            cpi, cpi_freq = pick_cpi(p)
            if len(cpi) >= MIN_CCY:
                break
        else:
            rep.setdefault("bis_cpi_errors", []).append(f"{u[:60]}… {err}")
    rep["cpi_used"] = {c: [cpi_freq.get(c)] + (span(cpi[c]) or []) for c in cpi}
    # 失業率：OECD（dataflow の一覧と、月ごとの失業率）
    xml, err = get(OECD_FLOWS_URL)
    rep["oecd_flows_une"] = flows_matching(xml) if xml else f"届かない：{err}"
    for u in OECD_UNE_URLS:
        text, err = get(u)
        if not text:
            rep.setdefault("oecd_une_errors", []).append(f"{u[:70]}… {err}")
            continue
        rd = csv.DictReader(io.StringIO(text))
        rep["oecd_une_columns"] = list(rd.fieldnames or [])
        p = parse_sdmx_csv(text, UNE_DIMS)
        want = set(OECD_AREA.values()) | {"EA19", "EA", "EA20"}
        rep["oecd_une"] = {"url": u, "n_series": len(p),
                           "total_rate": {"|".join(k): span(s) for k, s in sorted(p.items())
                                          if k[0] in want and k[1:3] == ("UNE_LF_M", "PT_LF_SUB") and k[4:6] == ("_T", "Y_GE15")}}
    # 失業率：FRED（OECD の系列）
    fred = {}
    for c, sids in FRED_UNE.items():
        for sid in sids:
            text, err = get(FRED_URL.format(sid=sid))
            s = parse_fred_csv(text) if text else {}
            fred[sid] = ([freq_of(s)] + span(s)) if s else f"届かない・空：{err}"
    rep["fred_une"] = fred
    # 為替の置き場（7ペアの月の有無だけ）
    try:
        import fx_bars
        cov = fx_bars.coverage(fx_root, pairs=PAIRS, start=fx_bars.EARLY[0])
        rep["fx_bars"] = {k: [v["have"], v["want"]] for k, v in cov.items()}
    except Exception as e:  # noqa: BLE001
        rep["fx_bars"] = f"読めない：{type(e).__name__}"
    # 合図がそろう月の数（損益は数えない）
    months = month_list((2004, 1))
    rep["months_with_signal"] = {
        "V": sum(1 for t in months if rank_weights({c: v_signal(reer.get(c) or {}, t) for c in CCYS})),
        "E_cpi_only": sum(1 for t in months if rank_weights(e_signal(cpi, {}, t, cpi_freq, {}))),
        "months_total": len(months)}
    return rep


# ════════════════════ 本番（run）：1か月の値・偽薬・判定 ════════════════════

def pair_of(c):
    """通貨 c（USD 以外）→ (ペア, 向き)。XXXUSD なら +1、USDXXX なら −1（ドルに対する c の値動き＝向き × ペアの値動き）"""
    for pr in PAIRS:
        if pr.startswith(c):
            return pr, 1.0
        if pr.endswith(c):
            return pr, -1.0
    raise KeyError(c)


def ymk(t):
    return f"{t[0]:04d}-{t[1]:02d}"


def month_inputs(prices, months):
    """月ごとの表（ペア → 月 'YYYY-MM' の close・spread）→ 決める月ごとに {通貨: (値動き, 1単位を入れ替える費用の率)}（そろわない通貨は入れない）"""
    out = []
    for t in months:
        b = mi(*t) + 1
        nxt = ymk((b // 12, b % 12 + 1))
        row = {}
        for c in CCYS[1:]:
            pr, sgn = pair_of(c)
            tb = prices.get(pr)
            if tb is None or ymk(t) not in tb.index or nxt not in tb.index:
                continue
            p0, p1, sp = float(tb.loc[ymk(t), "close"]), float(tb.loc[nxt, "close"]), tb.loc[ymk(t), "spread"]
            if not (p0 > 0 and p1 > 0):
                continue
            pip = 0.01 if pr.endswith("JPY") else 0.0001
            fixed = (FX_PIPS_JPY if pr.endswith("JPY") else FX_PIPS_OTHER) * pip
            cost = max(fixed, float(sp) if sp is not None and np.isfinite(sp) else 0.0) / p0
            row[c] = (sgn * float(np.log(p1 / p0)), cost)
        out.append(row)
    return out


def rate_table(rates, months):
    """決める月ごとの {通貨: 政策金利（％）}（R11 と同じ＝その月か3か月前までの直近）"""
    return [{c: T.rate_at(rates, BIS_AREA[c], ymk(t)) for c in CCYS} for t in months] if rates else None


def eligible(sig, row):
    """合図のうち、値段がそろう通貨だけ（ドルはいつも入る）"""
    return {c: v for c, v in sig.items() if v is not None and np.isfinite(v) and (c == "USD" or c in row)}


def arm_values(weights, inp, rtab=None):
    """月ごとの重み（dict か None）→ (1か月の値, 入れ替えの量, スワップの分)。rtab が None ならスワップと上乗せを入れない"""
    n = len(weights)
    vals, turn, swp = np.full(n, np.nan), np.full(n, np.nan), np.full(n, np.nan)
    prev = {}
    for j, w in enumerate(weights):
        row = inp[j]
        if w is None:
            prev = {}
            continue
        xs = [c for c in CCYS[1:] if w.get(c, 0.0) != 0.0 or prev.get(c, 0.0) != 0.0]
        if any(c not in row for c in xs if w.get(c, 0.0) != 0.0):
            prev = {}
            continue
        ret = sum(w.get(c, 0.0) * row[c][0] for c in xs if c in row)
        to = sum(abs(w.get(c, 0.0) - prev.get(c, 0.0)) for c in xs)
        cost = sum(abs(w.get(c, 0.0) - prev.get(c, 0.0)) * (row[c][1] if c in row else 0.0) for c in xs)
        sw = 0.0
        if rtab is not None:
            ru = rtab[j].get("USD")
            need = [c for c in CCYS[1:] if w.get(c, 0.0) != 0.0]
            if ru is None or any(rtab[j].get(c) is None for c in need):
                prev = {}
                continue
            sw = sum(w[c] * (rtab[j][c] - ru) / 100 / 12 - abs(w[c]) * FX_MARKUP / 12 for c in need)
        vals[j], turn[j], swp[j] = ret - cost + sw, to, sw
        prev = w
    return vals, turn, swp


def signals_by_month(reer, cpi, cfreq, une, ufreq, inp, months):
    """月ごとの合図（値段がそろう通貨だけ）：V・E・（読むだけ）E の物価だけ・E の失業率だけ"""
    S = {"V": [], "E": [], "E_cpi": [], "E_une": []}
    for j, t in enumerate(months):
        row = inp[j]
        S["V"].append(eligible({c: v_signal(reer.get(c) or {}, t) for c in CCYS}, row))
        S["E"].append(eligible(e_signal(cpi, une, t, cfreq, ufreq), row))
        S["E_cpi"].append(eligible(e_signal(cpi, {}, t, cfreq, {}), row))
        um = {c: momentum(lambda s, k: s.get(k), une.get(c) or {}, t, ufreq.get(c, "M")) for c in CCYS}
        S["E_une"].append(eligible({c: -v for c, v in um.items() if v is not None}, row))
    return S


def combine(a, b):
    """VE＝V と E の1か月の値の平均（どちらかが無い月は数えない）"""
    return np.where(np.isfinite(a) & np.isfinite(b), (a + b) / 2, np.nan)


def shuffled(sigs, rng):
    """月ごとに、合図の値を通貨どうしで入れ替える（偽薬）"""
    out = []
    for s in sigs:
        ks = list(s)
        vs = [s[k] for k in ks]
        out.append(dict(zip(ks, [vs[i] for i in rng.permutation(len(vs))])) if len(vs) > 1 else dict(s))
    return out


def arm_series(arm, S, inp, rtab):
    if arm == "VE":
        return combine(arm_series("V", S, inp, rtab), arm_series("E", S, inp, rtab))
    return arm_values([rank_weights(s) for s in S[arm]], inp, rtab)[0]


def placebo_p(arm, S, inp, rtab, actual, n_perm=N_PERM, seed=P.SEED):
    """偽薬（月ごとに合図を通貨どうしで入れ替える）の平均が本物の平均以上になる割合（片側）"""
    rng = np.random.default_rng(seed)
    hits = 0
    for _ in range(n_perm):
        S2 = {k: shuffled(S[k], rng) for k in (("V", "E") if arm == "VE" else (arm,))}
        x = arm_series(arm, S2, inp, rtab)
        if np.nanmean(x) >= actual:
            hits += 1
    return (hits + 1) / (n_perm + 1)


def verdict(full, old_mean, new_band, p):
    if M.plus(full) and (old_mean or 0) > 0 and (new_band.get("mean") or 0) > 0 and p is not None and p < ALPHA:
        return OK
    if M.plus(new_band):
        return NEW_ONLY
    if M.minus(full):
        return REV
    return NONE


def describe(x, months, judge_p=None, skip=False):
    ok = [j for j, v in enumerate(x) if np.isfinite(v)]
    split = mi(*SPLIT)
    old = [j for j in ok if mi(*months[j]) < split]
    new = [j for j in ok if mi(*months[j]) >= split]
    full = M.band(x[ok], alpha=ALPHA)
    oldb, newb = M.band(x[old], alpha=ALPHA), M.band(x[new], alpha=ALPHA)
    v = SKIP if skip else verdict(full, oldb.get("mean"), newb, judge_p)
    xs = x[ok]
    years = sorted({months[j][0] for j in ok})
    return {"months": len(ok), "first": ymk(months[ok[0]]) if ok else None, "last": ymk(months[ok[-1]]) if ok else None,
            "full": full, "old": oldb, "new": newb, "placebo_p": judge_p, "verdict": v if ok else SKIP,
            "sharpe": float(np.mean(xs) / np.std(xs) * np.sqrt(12)) if ok and np.std(xs) > 0 else None,
            "mdd": T.max_drawdown(xs), "worst": float(np.min(xs)) if ok else None,
            "by_year": {str(y): float(np.mean([x[j] for j in ok if months[j][0] == y])) for y in years}}


def corr(a, b):
    m = np.isfinite(a) & np.isfinite(b)
    return float(np.corrcoef(a[m], b[m])[0, 1]) if m.sum() > 2 and np.std(a[m]) > 0 and np.std(b[m]) > 0 else None


def analyze(prices, reer, cpi, cfreq, une, ufreq, rates, months, n_perm=N_PERM):
    inp = month_inputs(prices, months)
    rtab = rate_table(rates, months)
    S = signals_by_month(reer, cpi, cfreq, une, ufreq, inp, months)
    skip = rtab is None
    carry = arm_values([rank_weights(eligible(r, inp[j])) for j, r in enumerate(rtab)], inp, rtab)[0] if rtab else None
    res = {"une_used": sorted(une), "cpi_freq": cfreq, "une_freq": ufreq}
    for arm, _ in ARMS:
        if arm == "VE":
            x = combine(arm_values([rank_weights(s) for s in S["V"]], inp, rtab)[0], arm_values([rank_weights(s) for s in S["E"]], inp, rtab)[0])
            x0 = combine(arm_values([rank_weights(s) for s in S["V"]], inp)[0], arm_values([rank_weights(s) for s in S["E"]], inp)[0])
            to = np.nan
            wavg = {}
        else:
            W = [rank_weights(s) for s in S[arm]]
            x, tn, sw = arm_values(W, inp, rtab)
            x0 = arm_values(W, inp)[0]
            to = float(np.nanmean(tn)) if np.isfinite(tn).any() else None
            wavg = {c: float(np.mean([w.get(c, 0.0) for w in W if w])) for c in CCYS}
        p = placebo_p(arm, S, inp, rtab, float(np.nanmean(x)), n_perm=n_perm) if not skip and np.isfinite(x).any() else None
        d = describe(x if not skip else x0, months, p, skip=skip)
        d["read"] = {"noswap_mean": float(np.nanmean(x0)) if np.isfinite(x0).any() else None,
                     "swap_part": (float(np.nanmean(x)) - float(np.nanmean(x0))) if not skip and np.isfinite(x).any() else None,
                     "turnover": to, "avg_weight": wavg, "corr_carry": corr(x, carry) if carry is not None else None}
        res[arm] = d
    for k in ("E_cpi", "E_une"):
        xx = arm_values([rank_weights(s) for s in S[k]], inp, rtab)[0]
        res[k + "_read"] = {"months": int(np.isfinite(xx).sum()), "mean": float(np.nanmean(xx)) if np.isfinite(xx).any() else None}
    if carry is not None:
        res["carry_read"] = {"months": int(np.isfinite(carry).sum()), "mean": float(np.nanmean(carry)) if np.isfinite(carry).any() else None}
    return res


def verdicts_of(r, today):
    out = {}
    for arm, _ in ARMS:
        a = r.get(arm) or {}
        if a.get("verdict") in (REV, NONE):
            f = a["full"]
            out[arm] = {"status": "stop", "decided_on": today, "n": f["n"], "mean": f["mean"], "lo": f["lo"], "hi": f["hi"],
                        "reason": "過去のデータで1回だけ数えて" + ("逆向き" if a["verdict"] == REV else
                                                          "、でたらめな並べ方には勝つが、費用とスワップのあとの平均の幅が0をまたぐ"
                                                          if (a.get("placebo_p") or 1) < ALPHA else "、でたらめな並べ方と区別できない")
                                  + f"（費用とスワップのあとの1か月の平均・{a['first']}〜{a['last']}）"}
    return out


def render_md(res):
    L = ["# F2 為替の割安と経済の勢い（8通貨・月1回の入れ替え）", "",
         f"更新: {res.get('generated_at', '')}（事前登録＝`PILLAR_PREREG.md`「F2」・指紋 `{(res.get('prereg_sha256') or '')[:12]}`）", ""]
    r = res.get("result") or {}
    if "error" in r:
        return "\n".join(L + [f"⚠️ 計算できず：{r['error']}", "", "※ 研究の記録です。投資助言ではありません。"]) + "\n"
    L += ["8通貨（USD・EUR・GBP・JPY・AUD・CHF・CAD・NZD）を合図の順に並べ、順位に比例した重み（買いの合計1・売りの合計1）で月末に入れ替える。"
          "1か月の値＝ドルに対する値動き（月末どうしの対数）＋スワップ（政策金利の差 − 年1％の上乗せ）− 入れ替えの費用。"
          "幅は 98.33％（3つの腕・6か月のかたまり）・偽薬は月ごとに合図を通貨どうしで入れ替える 2,000回（片側）。", "",
          "## まとめ（判定）", "", "| 腕 | 判定 | 月 | 1か月の平均 | 幅 | 昔（〜2014年） | 最近（2015年〜） | 偽薬 p |", "|---|---|---:|---:|---|---:|---:|---:|"]
    for arm, name in ARMS:
        a = r.get(arm) or {}
        if not a:
            continue
        L.append(f"| {name} | **{a['verdict']}** | {a['months']}（{a['first']}〜{a['last']}） | {M._p(a['full']['mean'])} | {M._band(a['full'])} | "
                 f"{M._p(a['old']['mean'])} | {M._p(a['new']['mean'])}（{M._band(a['new'])}） | "
                 f"{'—' if a['placebo_p'] is None else format(a['placebo_p'], '.4f')} |")
    sh = lambda v: "—" if v is None else f"{v:.2f}"
    L += ["", "## 読むための表（判定しない）", ""]
    for arm, name in ARMS:
        a = r.get(arm) or {}
        if not a:
            continue
        rd = a["read"]
        L += [f"### {name}", "",
              f"- 年あたりの成績÷ばらつき {sh(a['sharpe'])}・最大の下落 {M._p(a['mdd'], 0)}・最悪の月 {M._p(a['worst'])}",
              f"- スワップ抜きの1か月の平均 {M._p(rd['noswap_mean'])}・スワップの分 {M._p(rd['swap_part'])}・入れ替えの量（1か月）{sh(rd['turnover'])}"
              f"・キャリー（政策金利の順）との相関 {sh(rd['corr_carry'])}",
              ("- 通貨ごとの平均の重み：" + "・".join(f"{c} {w:+.2f}" for c, w in rd["avg_weight"].items())) if rd["avg_weight"] else "- 通貨ごとの重み：V と E の半分ずつ",
              "- 年ごと：" + "・".join(f"{y} {M._p(v, 1)}" for y, v in a["by_year"].items()), ""]
    L += [f"- E の2つの数字それぞれ（読むだけ）：物価の勢いだけ {M._p((r.get('E_cpi_read') or {}).get('mean'))}"
          f"・失業率の勢いだけ {M._p((r.get('E_une_read') or {}).get('mean'))}・キャリー（政策金利の順・同じ重み）{M._p((r.get('carry_read') or {}).get('mean'))}",
          f"- 失業率を数えた通貨：{'・'.join(r.get('une_used') or []) or 'なし（E は物価だけ）'}", "",
          "## 注意", "", "- 通貨は8つだけ・経済の数字は今の値（後で直された値）で、発表の遅れを2〜3か月とって見込んだ・スワップは政策金利で近づけた目安",
          "- 実質実効為替レートは広い通貨のかごに対する強さ（ドルとの値段ではない）。過去の成績は将来を約束しない", "", "---", "",
          "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def load_all(get=get_text, fx_root=None):
    """本番のデータ（ネット・置き場）→ (prices, reer, cpi, cfreq, une, ufreq, rates, info)"""
    import fx_bars
    info = {}
    text = _must(get, BIS_REER_URLS[0])
    p = parse_sdmx_csv(text, ("REF_AREA",))
    reer = {c: p.get((BIS_AREA[c],), {}) for c in CCYS}
    cpi, cfreq = pick_cpi(parse_sdmx_csv(_must(get, BIS_CPI_URLS[0]), ("FREQ", "REF_AREA", "UNIT_MEASURE")))
    text, err = get(OECD_UNE_URLS[0])
    une, ufreq = pick_une(parse_sdmx_csv(text, UNE_DIMS)) if text else ({}, {})
    if len(une) < MIN_CCY:
        info["une_note"] = f"失業率が{len(une)}通貨しか取れない＝E は物価の勢いだけ（PREREG のとおり）：{err or ''}"
        une, ufreq = {}, {}
    rates, info["bis_url"] = T.fetch_bis()
    prices = {}
    for pr in PAIRS:
        c, sp = T.fx_daily(fx_bars.load(pr, root=fx_root, start=fx_bars.EARLY[0]))
        prices[pr] = T.monthly_table(c, sp) if c is not None else None
    info["prices"] = {pr: ([str(tb.index.min()), str(tb.index.max()), int(len(tb))] if tb is not None and len(tb) else None) for pr, tb in prices.items()}
    return prices, reer, cpi, cfreq, une, ufreq, rates, info


def _must(get, url):
    text, err = get(url)
    if text is None:
        raise RuntimeError(err)
    return text


def main(argv):
    if "--check" in argv:
        print(json.dumps(check(), ensure_ascii=False, indent=1, default=str))
        return 0
    res = {"generated_at": dt.datetime.now(P.JST).isoformat(timespec="minutes"), "prereg_file": P.PREREG,
           "prereg_sha256": P.prereg_sha256(), "kind": "backtest", "titles": {
               "V": "為替の割安（8通貨・実質実効為替レートの5年の変化・月1・費用とスワップ・2004〜2026-08・1回だけ数えた）",
               "E": "為替の経済の勢い（8通貨・物価の前年比と失業率の12か月の変化・月1・費用とスワップ・1回だけ数えた）",
               "VE": "為替の割安と経済の勢いを半分ずつ（8通貨・月1・費用とスワップ・1回だけ数えた）"}}
    try:
        prices, reer, cpi, cfreq, une, ufreq, rates, info = load_all()
        r = analyze(prices, reer, cpi, cfreq, une, ufreq, rates, month_list(FIRST))
        r.update(info)
        res["result"] = r
        res["verdicts"] = verdicts_of(r, dt.datetime.now(P.JST).date().isoformat())
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
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
