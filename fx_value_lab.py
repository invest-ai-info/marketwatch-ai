# -*- coding: utf-8 -*-
"""F2 為替の割安と経済の勢い：8つの通貨を、物価で直した割安さ（V）と、物価・雇用の数字の勢い（E）で並べ、月1回入れ替える。
2026-10-10 登録・オーナー「おすすめ通りにお願いします」（テクニカルの区切りのあとの、ファンダメンタルの柱の1本目）。PILLAR_PREREG.md「F2」。

V＝log（使える最新の月の 54〜66か月前の13か月の平均）− log（使える最新の月の値）＝BIS の実質実効為替レート。大きい＝割安＝買い。
E＝物価の勢い（前年比 − 12か月前の前年比）と雇用の勢い（−〔失業率 − 12か月前の失業率〕）の、通貨どうしの順位の平均。
使える値＝月ごとは参照の月が t−2 以前・四半期ごとは最後の月が t−3 以前。重み＝「順位 − 順位の平均」に比例・買い1・売り1。

⚠️ 決まりは PILLAR_PREREG.md「F2」と下の定数に固定。出力（fx-value-lab.json / .md）は集計だけ（SYNC禁忌）。
実行: python fx_value_lab.py --check   （点検だけ＝BIS・OECD・FRED に届くか・通貨ごとの期間・合図がそろう月の数。損益は数えない・何も書き出さない）
      本番（run）は check の結果で系列の名前を PREREG に追記してから足す（このファイルにはまだ無い）
"""
import csv
import io
import json
import re
import sys
import urllib.error
import urllib.request

import numpy as np

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

# ════════════════════ 取り口（check で確かめる・決まりではない） ════════════════════
_BIS_AREAS = "+".join(BIS_AREA[c] for c in CCYS)
BIS_REER_URLS = (f"https://stats.bis.org/api/v1/data/WS_EER/M.R.B.{_BIS_AREAS}?format=csv",
                 f"https://stats.bis.org/api/v2/data/dataflow/BIS/WS_EER/1.0/M.R.B.{_BIS_AREAS}?format=csv")
BIS_CPI_URLS = (f"https://stats.bis.org/api/v1/data/WS_LONG_CPI/M+Q.{_BIS_AREAS}.628+771?format=csv",
                f"https://stats.bis.org/api/v2/data/dataflow/BIS/WS_LONG_CPI/1.0/M+Q.{_BIS_AREAS}.628+771?format=csv")
OECD_FLOWS_URL = "https://sdmx.oecd.org/public/rest/dataflow/all?detail=allstubs"
OECD_UNE_URLS = ("https://sdmx.oecd.org/public/rest/data/OECD.SDD.TPS,DSD_LFS@DF_IALFS_UNE_M,1.0/all?startPeriod=1995-01&format=csvfile",)
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
    """BIS の消費者物価 → ({通貨: {(年, 月): 指数}}, {通貨: 'M'|'Q'})。指数（628）の月ごとを優先、無ければ四半期"""
    out, freq = {}, {}
    for c in CCYS:
        a = BIS_AREA[c]
        m = parsed.get(("M", a, "628")) or {}
        q = parsed.get(("Q", a, "628")) or {}
        if len(m) >= 24:
            out[c], freq[c] = m, "M"
        elif q:
            out[c], freq[c] = q, "Q"      # 四半期の値は最後の月に置いたまま（前年比も12か月前の同じ四半期と比べる）
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
        cols = [c for c in (rd.fieldnames or [])]
        rep["oecd_une_columns"] = cols
        p = parse_sdmx_csv(text, tuple(c for c in cols if c.upper() not in ("TIME_PERIOD", "OBS_VALUE", "OBS_STATUS",
                                                                          "UNIT_MULT", "DECIMALS", "BASE_PER", "DATAFLOW",
                                                                          "STRUCTURE", "STRUCTURE_ID", "ACTION", "OBS_STATUS_2")))
        want = set(OECD_AREA.values()) | {"EA19", "EA", "EA20"}
        kept = {"|".join(k): span(s) for k, s in sorted(p.items()) if any(x in want for x in k)}
        rep["oecd_une"] = {"url": u, "n_series": len(p), "target_series": dict(list(kept.items())[:120])}
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


def _must(get, url):
    text, err = get(url)
    if text is None:
        raise RuntimeError(err)
    return text


def main(argv):
    if "--check" in argv:
        print(json.dumps(check(), ensure_ascii=False, indent=1, default=str))
        return 0
    print("run はまだ無い：check の結果で系列の名前を PILLAR_PREREG.md「F2」に追記してから足す", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
