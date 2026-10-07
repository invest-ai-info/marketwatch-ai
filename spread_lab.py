# -*- coding: utf-8 -*-
"""J28 売り買いの差（費用）の見積もりを、日足と5分足で比べる（損益は数えない）。
2026-10-07 夜 登録・オーナー「登録して続けてください」。PILLAR_PREREG.md「J28」。

J19・J23・J27 の「費用で消える」は日足の高値・安値・終値からの見積もり（Abdi & Ranaldo・J24 の形）に頼っている。
同じ式を5分足（すべての時間／9:00〜9:30）に当てて、日足の見積もりと並べる。前もって決めた使い方＝売買代金10億円以上で
「5分足・9:00〜9:30」の中央値が「日足」の半分以下なら「日足は大きい株で重すぎる」と記録し、大きい株だけの数え直しをオーナーに諮る。

⚠️ 決まりは PILLAR_PREREG.md「J28」と下の定数に固定。日足の見積もりは cost_recount_lab.ar_spread_avg をそのまま使う。
⚠️ 出力（spread-lab.json / .md）は集計だけ・銘柄名とコードは出さない（SYNC禁忌）。

実行: python spread_lab.py --check   （点検だけ＝銘柄数と組の数。見積もりは出さない・何も書き出さない）
      python spread_lab.py           （本番。Actions の spread-lab.yml から手動で・1回だけ）
"""
import datetime as dt
import json
import sys

import numpy as np

import cost_recount_lab as CR
import highs_trap_lab as T
import highs_trap_small as S
import jp_bars
import pillar_lab as P
import yori_lab as Y

OUT_JSON, OUT_MD = "spread-lab.json", "spread-lab.md"
MIN_PAIRS_ALL, MIN_PAIRS_OPEN = 200, 60
OPEN_LAST = (9, 25)                         # 9:00〜9:25 の足（9:30 まで）
TV_DAYS = 20
FLOOR = 0.001                               # 往復 0.1％（J19 の下限）
HALF = 0.5                                  # 「半分以下」
DAILY_RANGE = "1y"
PRICE_BANDS = (("300円未満", 0, 300), ("300〜1,000円", 300, 1000), ("1,000〜3,000円", 1000, 3000), ("3,000円以上", 3000, np.inf))
EST = ("daily", "m5_all", "m5_open")
EST_NAMES = {"daily": "日足（J24 の形）", "m5_all": "5分足・すべての時間", "m5_open": "5分足・9:00〜9:30"}
HEAVY, OK = "日足の見積もりは大きい株で重すぎる（大きい株だけの数え直しをオーナーに諮る）", "日足の見積もりで大きく外れていない（これまでの結論はそのまま）"


# ════════════════════ 見積もり ════════════════════

def _x(b0, b1):
    """続いた2本の足 → 4×(終値−その足の中値)×(終値−次の足の中値)（対数）"""
    c = np.log(b0[4])
    e0 = (np.log(b0[2]) + np.log(b0[3])) / 2
    e1 = (np.log(b1[2]) + np.log(b1[3])) / 2
    return 4 * (c - e0) * (c - e1)


def _ok(b):
    return b[5] and b[5] > 0 and b[2] > 0 and b[3] > 0 and b[4] > 0


def m5_pairs(by_day, open_only=False):
    """{日付: 5分足} → 同じ日の中の続いた足の組の値（日をまたがない・出来高0の足は使わない）。
    open_only＝両方の足が 9:00〜9:25 に始まる組だけ"""
    out = []
    for _day, bars in sorted(by_day.items()):
        b = sorted(bars)
        for b0, b1 in zip(b, b[1:]):
            if (b1[0] - b0[0]) != dt.timedelta(minutes=5) or not (_ok(b0) and _ok(b1)):
                continue
            if open_only and not all((x[0].hour, x[0].minute) >= (9, 0) and (x[0].hour, x[0].minute) <= OPEN_LAST for x in (b0, b1)):
                continue
            out.append(_x(b0, b1))
    return np.array(out, float)


def estimate(x, min_pairs):
    x = x[np.isfinite(x)]
    if len(x) < min_pairs:
        return None
    return float(np.sqrt(max(x.mean(), 0.0)))


def stock_row(daily, by_day):
    """1銘柄 → {日足・5分足すべて・5分足 9:00〜9:30 の見積もり, 直近20営業日の1日平均の売買代金, 最後の終値, 組の数}"""
    sp = CR.ar_spread_avg(daily)
    last = daily[-1][0] if daily else None
    tv = [r[4] * (r[5] or 0) / 1e8 for r in daily[-TV_DAYS:]]
    xa, xo = m5_pairs(by_day), m5_pairs(by_day, open_only=True)
    return {"daily": sp.get(last), "m5_all": estimate(xa, MIN_PAIRS_ALL), "m5_open": estimate(xo, MIN_PAIRS_OPEN),
            "turnover": float(np.mean(tv)) if len(tv) == TV_DAYS else None, "price": daily[-1][4] if daily else None,
            "pairs_all": int(len(xa)), "pairs_open": int(len(xo))}


# ════════════════════ まとめ ════════════════════

def _med(v):
    v = [x for x in v if x is not None]
    return float(np.median(v)) if v else None


def _band_of(x, bands):
    if x is None:
        return None
    for lab, lo, hi in bands:
        if lo <= x < hi:
            return lab
    return None


def summarize(rows):
    def table(sel):
        rs = [r for r in rows if sel(r)]
        return {"n": len(rs), **{k: _med([r[k] for r in rs]) for k in EST},
                "floor_share": {k: (float(np.mean([r[k] < FLOOR for r in rs if r[k] is not None])) if any(r[k] is not None for r in rs) else None)
                                for k in EST}}
    out = {"all": table(lambda r: True), "turnover": {}, "price": {}}
    for lab, lo, hi in S.TURNOVER_BANDS:
        out["turnover"][lab] = table(lambda r, lo=lo, hi=hi: r["turnover"] is not None and lo <= r["turnover"] < hi)
    for lab, lo, hi in PRICE_BANDS:
        out["price"][lab] = table(lambda r, lo=lo, hi=hi: r["price"] is not None and lo <= r["price"] < hi)
    both = [r for r in rows if r["daily"] is not None and r["m5_open"] is not None]
    out["paired"] = {}
    for lab, lo, hi in S.TURNOVER_BANDS:
        rs = [r for r in both if r["turnover"] is not None and lo <= r["turnover"] < hi]
        d, o = _med([r["daily"] for r in rs]), _med([r["m5_open"] for r in rs])
        out["paired"][lab] = {"n": len(rs), "daily": d, "m5_open": o, "ratio": (o / d) if d and o is not None else None,
                              "daily_over_2x": float(np.mean([r["daily"] > 2 * r["m5_open"] for r in rs])) if rs else None}
    big = out["paired"]["10億円以上"]
    out["verdict"] = None if big["ratio"] is None else (HEAVY if big["ratio"] <= HALF else OK)
    return out


# ════════════════════ 読む ════════════════════

def load(codes, fetch):
    rows, missing = [], {"daily": 0, "m5": 0}
    for i, code in enumerate(codes):
        d = fetch(code, "1d", DAILY_RANGE)
        m5 = T._first(fetch, code, "5m", T.M5_RANGES)
        if not d:
            missing["daily"] += 1
            continue
        if not m5:
            missing["m5"] += 1
            continue
        daily = sorted({t.date().isoformat(): (t.date().isoformat(), o, h, lo, c, v) for t, o, h, lo, c, v in d}.values())
        rows.append(stock_row(daily, T._by_day(m5)))
        if (i + 1) % 500 == 0:
            print(f"  ...{i + 1}/{len(codes)}", flush=True)
    return rows, missing


def check_summary(rows, missing, n_codes, store):
    """点検だけ＝銘柄数と組の数（見積もりは出さない）"""
    return {"n_codes": n_codes, "missing": missing, "stocks": len(rows), "store": store,
            "with": {"daily": sum(r["daily"] is not None for r in rows), "m5_all": sum(r["pairs_all"] >= MIN_PAIRS_ALL for r in rows),
                     "m5_open": sum(r["pairs_open"] >= MIN_PAIRS_OPEN for r in rows)},
            "pairs_median": {"all": _med([r["pairs_all"] for r in rows]), "open": _med([r["pairs_open"] for r in rows])},
            "turnover_bands": {lab: sum(r["turnover"] is not None and lo <= r["turnover"] < hi for r in rows) for lab, lo, hi in S.TURNOVER_BANDS}}


# ════════════════════ 書く ════════════════════

def _p(x, d=2):
    return Y._pct(x, d) if x is not None else "—"


def _s(x):
    return "—" if x is None else f"{x * 100:.2f}％"


def render_md(res):
    L = ["# J28 売り買いの差（費用）の見積もりを、日足と5分足で比べる", "",
         f"更新: {res.get('generated_at', '')}（事前登録＝`PILLAR_PREREG.md`「J28」・指紋 `{(res.get('prereg_sha256') or '')[:12]}`）", ""]
    r = res.get("result") or {}
    if "error" in r:
        return "\n".join(L + [f"⚠️ 計算できず：{r['error']}", "", "※ 研究の記録です。投資助言ではありません。"]) + "\n"
    sm = r["summary"]
    L += ["数字は往復の売り買いの差の見積もり（株価に対する割合）の、銘柄ごとの中央値。損益は数えていない。"
          "見積もり＝Abdi & Ranaldo の式を「平均してから平方根」で（J24 と同じ形）。", "",
          f"## まとめ：{sm['verdict'] or '判断できず（大きい株の見積もりがそろわない）'}", "",
          "### 同じ銘柄で日足と 9:00〜9:30 を比べる（両方そろう銘柄だけ）", "",
          "| 売買代金（直近20営業日の1日平均） | 銘柄数 | 日足 | 5分足・9:00〜9:30 | 9:00〜9:30 ÷ 日足 | 日足が2倍を超える割合 |",
          "|---|---:|---:|---:|---:|---:|"]
    for lab, x in sm["paired"].items():
        ratio = "—" if x["ratio"] is None else f"{x['ratio']:.2f}"
        over = "—" if x["daily_over_2x"] is None else f"{x['daily_over_2x'] * 100:.0f}％"
        L.append(f"| {lab} | {x['n']:,} | {_s(x['daily'])} | {_s(x['m5_open'])} | {ratio} | {over} |")
    L += ["", f"前もって決めた線：売買代金10億円以上で「9:00〜9:30 ÷ 日足」が {HALF:.2f} 以下なら「日足は重すぎる」。", "",
          "### 3つの見積もり（そろった銘柄それぞれの中央値）", "",
          "| 区分 | 銘柄数 | " + " | ".join(EST_NAMES[k] for k in EST) + " | 0.1％未満の割合（日足／すべて／9:00〜9:30） |",
          "|---|---:|" + "---:|" * len(EST) + "---|"]

    def line(lab, x):
        fs = "／".join("—" if x["floor_share"][k] is None else f"{x['floor_share'][k] * 100:.0f}％" for k in EST)
        return f"| {lab} | {x['n']:,} | " + " | ".join(_s(x[k]) for k in EST) + f" | {fs} |"
    L.append(line("すべて", sm["all"]))
    for lab, x in sm["turnover"].items():
        L.append(line(f"売買代金 {lab}", x))
    for lab, x in sm["price"].items():
        L.append(line(f"株価 {lab}", x))
    L += ["", "## 注意", "",
          "- 見積もりは実際の板（気配）ではない。5分足の期間は約60日だけ＝昔の時代の費用はわからない。呼値（値段の刻み）の下限は入れていない",
          "- 「重すぎる」でも、すぐに結論を変えない。大きい株だけの数え直しを新しい登録としてオーナーに諮り、プラスが出ても前向きで確かめる",
          "", "---", "", "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def main(argv):
    res = {"generated_at": dt.datetime.now(P.JST).isoformat(timespec="minutes"), "prereg_file": P.PREREG,
           "prereg_sha256": P.prereg_sha256()}
    try:
        stocks, list_date = jp_bars.load_universe()
        codes = sorted(stocks)
        rows, missing = load(codes, jp_bars.fetcher())
        store = jp_bars.info()
        res["price_store"] = store
        if "--check" in argv:
            print(json.dumps(check_summary(rows, missing, len(codes), store), ensure_ascii=False, indent=1))
            return 0
        res["result"] = {"summary": summarize(rows), "n_codes": len(codes), "list_date": list_date, "missing": missing,
                         "stocks": len(rows)}
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
