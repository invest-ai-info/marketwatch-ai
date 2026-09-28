# -*- coding: utf-8 -*-
"""J4 前の日に出来高が急増した銘柄の、次の日の寄り付き（2026-09-28 オーナー「寄り付きから何分ぐらいで手仕舞ったら
いいのか。どんな条件だと急騰しやすいのか。どんな条件だと入らない方がいいのか」）。

⚠️ 決まりは PILLAR_PREREG.md「J4」と下の定数に固定。結果を見てから動かさない。
⚠️ 出力（yori-lab.json / yori-lab.md）は集計だけ。銘柄名・銘柄コードは出さない。GitHub 側で生成＝手元から送らない（SYNC禁忌）。
⚠️ 前の日の上位20の決め方は build_jp_rankings.py と同じ（相対出来高＝その日の出来高÷直前20営業日の平均・売買代金10億円以上）。

実行: python yori_lab.py   （Actions の yori-lab.yml から手動で）
"""
import datetime as dt
import json
import sys
import time
import urllib.request

import numpy as np

import pillar_lab as P

UNIVERSE = "jp-stock-info.json"
OUT_JSON, OUT_MD = "yori-lab.json", "yori-lab.md"
TOP_N, HOT_MIN_TURNOVER, HOT_BASE_DAYS, HOT_MIN_BASE = 20, 10.0, 20, 15   # build_jp_rankings.py と同じ
UP, DOWN = 0.02, -0.02            # 最初の15分：急騰＝+2％以上／急落＝−2％以下
GAP_BIG = 0.03                    # P3 窓が+3％以上
WICK = 0.5                        # P4 最初の15分の上げ幅の半分以上を戻した
COST = 0.001                      # 往復0.1％
TIMES = ["09:15", "09:30", "09:45", "10:00", "10:30", "11:30", "13:00", "14:00", "15:30"]
MIN_CELL = 30
N_BOOT = 2000


# ════════════════════ データ ════════════════════

def fetch_chart(code, interval, rng, tries=3):
    """Yahoo chart API → [(JSTの時刻, 始, 高, 安, 終, 出来高)]（値の欠けた足は除く）"""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{code}.T?range={rng}&interval={interval}"
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            d = json.load(urllib.request.urlopen(req, timeout=30))["chart"]["result"][0]
            q = d["indicators"]["quote"][0]
            out = []
            for t, o, h, l, c, v in zip(d.get("timestamp") or [], q["open"], q["high"], q["low"], q["close"], q["volume"]):
                if None in (o, h, l, c):
                    continue
                out.append((dt.datetime.fromtimestamp(t, P.JST), float(o), float(h), float(l), float(c), float(v or 0)))
            return out
        except Exception as e:  # noqa: BLE001
            print(f"  ⚠️ {code} {interval} 取得失敗 {k + 1}/{tries}: {type(e).__name__}", file=sys.stderr)
            time.sleep(2 * (k + 1))
    return None


def hot_lists(daily):
    """daily＝{code: [(日付, 終値, 出来高)]} → {日付: set(その日の上位20のコード)}（build_jp_rankings.py と同じ決め方）"""
    by_day = {}
    for code, rows in daily.items():
        vols = [v for _, _, v in rows]
        for i, (d, c, v) in enumerate(rows):
            base = [x for x in vols[max(0, i - HOT_BASE_DAYS):i] if x]
            if len(base) < HOT_MIN_BASE or v <= 0:
                continue
            relvol = v / (sum(base) / len(base))
            if c * v / 1e8 < HOT_MIN_TURNOVER:
                continue
            by_day.setdefault(d, []).append((relvol, code))
    return {d: {c for _, c in sorted(xs, reverse=True)[:TOP_N]} for d, xs in by_day.items()}


def price_at(bars, hhmm):
    """その日の5分足から、hh:mm より前の最後の足の終値（30分以内に足が無ければ None）"""
    h, m = map(int, hhmm.split(":"))
    last = None
    for t, o, hi, lo, c, v in bars:
        end = t + dt.timedelta(minutes=5)
        if (end.hour, end.minute) <= (h, m):
            last = (t, c)
    if last is None:
        return None
    t_end = last[0] + dt.timedelta(minutes=5)
    gap_min = (h * 60 + m) - (t_end.hour * 60 + t_end.minute)
    return last[1] if gap_min <= 30 else None


def day_record(bars, prev_close, prev_prev_close, prev_vol, close):
    """その日の5分足（9:00 から並ぶ）→ 1件の記録。9:00 の足が無ければ None"""
    if not bars or (bars[0][0].hour, bars[0][0].minute) != (9, 0) or not prev_close or not close:
        return None
    op = bars[0][1]
    first = [b for b in bars if (b[0].hour, b[0].minute) < (9, 15)]
    p915 = price_at(bars, "09:15")
    if not op or p915 is None or not first:
        return None
    hi15 = max(b[2] for b in first)
    vol15 = sum(b[5] for b in first)
    path = {t: (close if t == "15:30" else price_at(bars, t)) for t in TIMES}
    r15 = p915 / op - 1
    wick = (hi15 - p915) / (hi15 - op) if hi15 > op else 0.0
    return {"gap": op / prev_close - 1, "r15": r15, "cls": "up" if r15 >= UP else "down" if r15 <= DOWN else "flat",
            "wick": wick, "vol_share": vol15 / prev_vol if prev_vol else None,
            "prev_ret": prev_close / prev_prev_close - 1 if prev_prev_close else None,
            "open": op, "p915": p915, "path": path, "price": prev_close}


# ════════════════════ 数える ════════════════════

def ret(r, frm, to):
    a = r["open"] if frm == "open" else r["path"].get(frm)
    b = r["path"].get(to)
    return b / a - 1 if a and b else None


def stats(rows, fn):
    xs = [(fn(r), (r["code"], r["date"])) for r in rows]
    xs = [(v, g) for v, g in xs if v is not None]
    if not xs:
        return {"n": 0}
    return P.mean_ci([v for v, _ in xs], [g for _, g in xs])


def boot_diff(rows, fn, is_a, n=N_BOOT, seed=P.SEED):
    """「a の平均 − b の平均」と、日ごとに引き直した95％の幅"""
    by_day = {}
    for r in rows:
        v = fn(r)
        if v is not None:
            by_day.setdefault(r["date"], []).append((is_a(r), v))
    days = sorted(by_day)

    def diff(ds):
        a = [v for d in ds for k, v in by_day[d] if k]
        b = [v for d in ds for k, v in by_day[d] if not k]
        return (np.mean(a) - np.mean(b)) if a and b else None

    d0 = diff(days)
    if d0 is None or len(days) < 5:
        return {"diff": d0, "lo": None, "hi": None, "n_a": 0, "n_b": 0}
    rng = np.random.default_rng(seed)
    sims = [x for x in (diff([days[i] for i in rng.integers(0, len(days), len(days))]) for _ in range(n)) if x is not None]
    lo, hi = np.percentile(sims, [2.5, 97.5])
    na = sum(1 for d in days for k, _ in by_day[d] if k)
    return {"diff": float(d0), "lo": float(lo), "hi": float(hi), "n_a": na, "n_b": sum(len(by_day[d]) for d in days) - na}


def split_days(rows):
    days = sorted({r["date"] for r in rows})
    cut = days[len(days) // 2] if days else ""
    return [r for r in rows if r["date"] < cut], [r for r in rows if r["date"] >= cut], cut


def judge_p1(st, e, c):
    ok = st.get("hi") is not None and st["hi"] < 0 and (e.get("mean") or 0) < 0 and (c.get("mean") or 0) < 0
    return "寄りの急騰は、その日のうちに失速しやすい兆し" if ok else "見えない"


def judge_p2(st):
    return "兆し" if st.get("lo") is not None and st["lo"] > 0 else "見えない"


def judge_diff(d, e, c, sign):
    """sign=+1：差がまるごと0より上 かつ 前半・後半とも上／sign=−1：その逆"""
    if d.get("lo") is None or e.get("diff") is None or c.get("diff") is None:
        return False
    if sign > 0:
        return d["lo"] > 0 and e["diff"] > 0 and c["diff"] > 0
    return d["hi"] < 0 and e["diff"] < 0 and c["diff"] < 0


def bins_table(rows, keyf, labels, valf):
    out = []
    for lab in labels:
        xs = [r for r in rows if keyf(r) == lab]
        st = stats(xs, valf) if len(xs) >= MIN_CELL else {"n": len(xs)}
        out.append(dict(st, label=lab))
    return out


def price_band(p):
    return "500円未満" if p < 500 else "500〜3,000円" if p < 3000 else "3,000円以上"


def gap_band(g):
    return "−1％未満" if g < -0.01 else "−1〜+1％" if g < 0.01 else "+1〜+3％" if g < 0.03 else "+3％以上"


def prev_band(x):
    return None if x is None else ("−5％以下" if x <= -0.05 else "−5〜+5％" if x < 0.05 else "+5％以上")


def relvol_band(x):
    return "3倍未満" if x < 3 else "3〜5倍" if x < 5 else "5倍以上"


def share_band(x):
    return None if x is None else ("10％未満" if x < 0.1 else "10〜30％" if x < 0.3 else "30％以上")


WEEK = "月火水木金土日"


def analyze(recs):
    hot = [r for r in recs if r["hot"]]
    ctl = [r for r in recs if not r["hot"]]
    e_hot, c_hot, cut = split_days(hot)
    res = {"n_hot": len(hot), "n_ctl": len(ctl), "days": len({r["date"] for r in hot}), "cut": cut,
           "first": min((r["date"] for r in hot), default=None), "last": max((r["date"] for r in hot), default=None)}
    up = [r for r in hot if r["cls"] == "up"]
    # P1
    f1 = lambda r: ret(r, "09:15", "15:30")  # noqa: E731
    st1, e1, c1 = stats(up, f1), stats([r for r in up if r["date"] < cut], f1), stats([r for r in up if r["date"] >= cut], f1)
    st1_ctl = stats([r for r in ctl if r["cls"] == "up"], f1)
    res["p1"] = {"all": st1, "early": e1, "late": c1, "ctl": st1_ctl, "verdict": judge_p1(st1, e1, c1)}
    # P2
    means = {t: stats(e_hot, lambda r, t=t: (ret(r, "open", t) or 0) - COST if ret(r, "open", t) is not None else None).get("mean")
             for t in TIMES}
    t_best = max((t for t in TIMES if means[t] is not None), key=lambda t: means[t], default=None)
    st2 = stats(c_hot, lambda r: (ret(r, "open", t_best) - COST) if t_best and ret(r, "open", t_best) is not None else None)
    res["p2"] = {"explore_means": means, "t_best": t_best, "confirm": st2, "verdict": judge_p2(st2)}
    # P3
    f3 = lambda r: 1.0 if r["cls"] == "up" else 0.0  # noqa: E731
    a3 = lambda r: r["gap"] >= GAP_BIG  # noqa: E731
    d3, e3, c3 = boot_diff(hot, f3, a3), boot_diff(e_hot, f3, a3), boot_diff(c_hot, f3, a3)
    res["p3"] = {"all": d3, "early": e3, "late": c3,
                 "verdict": "窓が大きいと、寄りのあとも上がりやすい兆し" if judge_diff(d3, e3, c3, +1) else "見えない"}
    # P4
    a4 = lambda r: r["wick"] >= WICK  # noqa: E731
    e_up, c_up, _ = [r for r in up if r["date"] < cut], [r for r in up if r["date"] >= cut], None
    d4, e4, c4 = boot_diff(up, f1, a4), boot_diff(e_up, f1, a4), boot_diff(c_up, f1, a4)
    res["p4"] = {"all": d4, "early": e4, "late": c4,
                 "verdict": "上ヒゲの長い寄りの急騰は、その後さらに下げやすい兆し" if judge_diff(d4, e4, c4, -1) else "見えない"}
    # 読むための表
    paths = {}
    for name, rows in (("急騰", up), ("急落", [r for r in hot if r["cls"] == "down"]), ("変わらず", [r for r in hot if r["cls"] == "flat"])):
        paths[name] = {t: stats(rows, lambda r, t=t: ret(r, "09:15", t)).get("mean") for t in TIMES[1:]} | {"n": len(rows)}
    for name, cl in (("対照の急騰", "up"), ("対照の急落", "down"), ("対照の変わらず", "flat")):
        rows = [r for r in ctl if r["cls"] == cl]
        paths[name] = {t: stats(rows, lambda r, t=t: ret(r, "09:15", t)).get("mean") for t in TIMES[1:]} | {"n": len(rows)}
    res["paths_from_915"] = paths
    res["paths_from_open"] = {
        "上位20すべて": {t: stats(hot, lambda r, t=t: ret(r, "open", t)).get("mean") for t in TIMES} | {"n": len(hot)},
        "対照すべて": {t: stats(ctl, lambda r, t=t: ret(r, "open", t)).get("mean") for t in TIMES} | {"n": len(ctl)}}
    share = {}
    conds = [("窓", lambda r: gap_band(r["gap"]), ["−1％未満", "−1〜+1％", "+1〜+3％", "+3％以上"]),
             ("前の日の上げ下げ", lambda r: prev_band(r["prev_ret"]), ["−5％以下", "−5〜+5％", "+5％以上"]),
             ("前の日の出来高の倍率", lambda r: relvol_band(r["relvol"]), ["3倍未満", "3〜5倍", "5倍以上"]),
             ("株価の水準", lambda r: price_band(r["price"]), ["500円未満", "500〜3,000円", "3,000円以上"]),
             ("赤字か", lambda r: "赤字" if r.get("akaji") else "黒字", ["赤字", "黒字"]),
             ("曜日", lambda r: WEEK[dt.date.fromisoformat(r["date"]).weekday()], list("月火水木金"))]
    for name, kf, labs in conds:
        share[name] = {"急騰になる割合": bins_table(hot, kf, labs, lambda r: 1.0 if r["cls"] == "up" else 0.0),
                       "急落になる割合": bins_table(hot, kf, labs, lambda r: 1.0 if r["cls"] == "down" else 0.0),
                       "急騰のあと（9:15→大引け）": bins_table(up, kf, labs, f1)}
    share["最初の15分の出来高÷前の日の出来高"] = {
        "急騰のあと（9:15→大引け）": bins_table(up, lambda r: share_band(r["vol_share"]), ["10％未満", "10〜30％", "30％以上"], f1)}
    share["上ヒゲ"] = {"急騰のあと（9:15→大引け）": bins_table(up, lambda r: "長い（半分以上戻した）" if r["wick"] >= WICK else "短い",
                                                        ["長い（半分以上戻した）", "短い"], f1)}
    res["tables"] = share
    res["cls_counts"] = {k: sum(1 for r in hot if r["cls"] == k) for k in ("up", "flat", "down")}
    return res


# ════════════════════ 実行 ════════════════════

def load_all(codes, meta, today, fetch=fetch_chart, diag=None):
    """diag に dict を渡すと、データがどこで抜けたかを数えて入れる（集計だけ・銘柄名なし。--diag 用）"""
    daily, intraday, missing = {}, {}, []
    for i, code in enumerate(codes):
        d = fetch(code, "1d", "6mo")
        m60 = fetch(code, "5m", "60d")
        m = m60 or fetch(code, "5m", "1mo")   # 60日が断られたら1か月
        if diag is not None:
            diag.setdefault("5m_range", {}).setdefault("60d" if m60 else "1mo" if m else "none", 0)
            diag["5m_range"]["60d" if m60 else "1mo" if m else "none"] += 1
            for t, *_ in d or []:
                k = t.strftime("%H:%M")
                diag.setdefault("daily_time", {}).setdefault(k, 0)
                diag["daily_time"][k] += 1
            n_days = len({b[0].date() for b in m or []})
            diag.setdefault("5m_days_per_stock", []).append(n_days)
        if not d or not m:
            missing.append(code)
            continue
        daily[code] = [(t.date().isoformat(), c, v) for t, o, h, l, c, v in d]
        by = {}
        for b in m:
            by.setdefault(b[0].date().isoformat(), []).append(b)
        intraday[code] = by
        if (i + 1) % 100 == 0:
            print(f"  ...{i + 1}/{len(codes)}", flush=True)
        time.sleep(0.05)
    hot = hot_lists(daily)
    recs = []
    for code, rows in daily.items():
        idx = {d: k for k, (d, _, _) in enumerate(rows)}
        for day, bars in intraday.get(code, {}).items():
            k = idx.get(day)
            if k is None or k < 2 or day >= today:
                continue
            prev_d, prev_c, prev_v = rows[k - 1]
            rec = day_record(sorted(bars), prev_c, rows[k - 2][1], prev_v, rows[k][1])
            if rec is None:
                continue
            base = [x for _, _, x in rows[max(0, k - 1 - HOT_BASE_DAYS):k - 1] if x]
            rec.update(code=code, date=day, hot=code in hot.get(prev_d, set()), akaji=meta.get(code, {}).get("akaji"),
                       relvol=prev_v / (sum(base) / len(base)) if base else 0.0)
            recs.append(rec)
    if diag is not None:
        _diagnose(daily, intraday, hot, today, diag)
    return recs, missing


def _diagnose(daily, intraday, hot, today, diag):
    """前の日の上位20に入った銘柄が、次の日の記録になるまでにどこで落ちたかを、次の日の曜日ごとに数える"""
    why, first_bar = {}, {}
    for code, rows in daily.items():
        by = intraday.get(code, {})
        for day, bars in by.items():
            t0 = min(bars)[0].strftime("%H:%M")
            first_bar[t0] = first_bar.get(t0, 0) + 1
        for k in range(len(rows) - 1):
            d0, d1 = rows[k][0], rows[k + 1][0]
            if code not in hot.get(d0, ()) or d1 >= today:
                continue
            bars = sorted(by.get(d1, []))
            if not bars:
                r = "次の日の5分足なし"
            elif (bars[0][0].hour, bars[0][0].minute) != (9, 0):
                r = "最初の足が9:00でない"
            elif day_record(bars, rows[k][1], rows[k - 1][1] if k else None, rows[k][2], rows[k + 1][1]) is None:
                r = "そのほか記録にならない"
            else:
                r = "記録になった"
            wd = WEEK[dt.date.fromisoformat(d1).weekday()]
            why.setdefault(wd, {}).setdefault(r, 0)
            why[wd][r] += 1
    days5 = sorted({d for by in intraday.values() for d in by})
    diag["hot_next_day_by_weekday"] = why
    diag["first_bar_time"] = dict(sorted(first_bar.items(), key=lambda kv: -kv[1])[:10])
    diag["5m_dates"] = {"n": len(days5), "first": days5[0] if days5 else None, "last": days5[-1] if days5 else None}
    diag["stocks_with_5m_by_date"] = {d: sum(1 for by in intraday.values() if d in by) for d in days5}
    diag["hot_size_by_date"] = {d: len(v) for d, v in sorted(hot.items()) if days5 and d >= days5[0]}
    xs = sorted(diag.pop("5m_days_per_stock", []))
    diag["5m_days_per_stock"] = {"min": xs[0], "median": xs[len(xs) // 2], "max": xs[-1]} if xs else {}


def today_cutoff(now=None):
    """その日の場が終わっていなければ、その日は使わない（15:45 JST まで）"""
    now = now or dt.datetime.now(P.JST)
    return (now.date() + dt.timedelta(days=1)).isoformat() if (now.hour, now.minute) >= (15, 45) else now.date().isoformat()


def _pct(x, d=2):
    return "—" if x is None else f"{x * 100:+.{d}f}％"


def render_md(res):
    L = ["# J4 前の日に出来高が急増した銘柄の、次の日の寄り付き", "",
         f"作成: {res['generated_at']}（GitHub Actions で計算）。事前登録＝`{P.PREREG}`「J4」（指紋 sha256 `{(res.get('prereg_sha256') or '')[:16]}…`）。",
         "銘柄名は出しません。値は株価の変化率（％）。**売買の決まりではない**。", ""]
    r = res.get("result") or {}
    if r.get("error"):
        return "\n".join(L + [f"- ⚠️ 計算できず: {r['error']}", ""]) + "\n"
    cc = r.get("cls_counts", {})
    L += [f"- 期間 {r.get('first')}〜{r.get('last')}（{r.get('days')}営業日・前半と後半の境 {r.get('cut')}）",
          f"- 前の日の上位20：{r.get('n_hot')}件（急騰 {cc.get('up', 0)}・変わらず {cc.get('flat', 0)}・急落 {cc.get('down', 0)}）／対照 {r.get('n_ctl')}件",
          f"- 値段を取れなかった銘柄 {len(r.get('missing') or [])}", "", "## 判定（事前登録の4つ）", ""]
    p1, p2, p3, p4 = r["p1"], r["p2"], r["p3"], r["p4"]
    a = p1["all"]
    L += [f"- **P1 寄り天**：急騰を 9:15 に買って大引けまで＝平均 {_pct(a.get('mean'))}（幅 {_pct(a.get('lo'))}〜{_pct(a.get('hi'))}・{a.get('n', 0)}件）"
          f"・前半 {_pct(p1['early'].get('mean'))}／後半 {_pct(p1['late'].get('mean'))} → **{p1['verdict']}**（対照の急騰 {_pct(p1['ctl'].get('mean'))}）"]
    c = p2["confirm"]
    L += [f"- **P2 手仕舞いの時刻**：前半で一番よかった時刻＝{p2['t_best']} → 後半の平均（費用後）{_pct(c.get('mean'))}（幅 {_pct(c.get('lo'))}〜{_pct(c.get('hi'))}・{c.get('n', 0)}件） → **{p2['verdict']}**"]
    for key, name in (("p3", "P3 急騰しやすい条件（窓+3％以上）"), ("p4", "P4 入らない方がいい条件（上ヒゲが長い急騰）")):
        d = r[key]["all"]
        L += [f"- **{name}**：差 {_pct(d.get('diff'))}（幅 {_pct(d.get('lo'))}〜{_pct(d.get('hi'))}・{d.get('n_a', 0)}件 対 {d.get('n_b', 0)}件）"
              f"・前半 {_pct(r[key]['early'].get('diff'))}／後半 {_pct(r[key]['late'].get('diff'))} → **{r[key]['verdict']}**"]
    L += ["", "## 読むための表（判定しない）", "", "### 寄りで買った場合の平均（寄り→各時刻・費用なし）", "",
          "| | " + " | ".join(TIMES) + " | 件数 |", "|---|" + "---:|" * (len(TIMES) + 1)]
    for k, v in r["paths_from_open"].items():
        L.append(f"| {k} | " + " | ".join(_pct(v.get(t)) for t in TIMES) + f" | {v.get('n')} |")
    L += ["", f"- 前半で選んだときの各時刻の平均（費用後）：" + "・".join(f"{t} {_pct(m)}" for t, m in p2["explore_means"].items()),
          "", "### 9:15 から持った場合の平均（9:15→各時刻・費用なし）", "",
          "| | " + " | ".join(TIMES[1:]) + " | 件数 |", "|---|" + "---:|" * len(TIMES)]
    for k, v in r["paths_from_915"].items():
        L.append(f"| {k} | " + " | ".join(_pct(v.get(t)) for t in TIMES[1:]) + f" | {v.get('n')} |")
    for name, tabs in r["tables"].items():
        L += ["", f"### {name}", ""]
        for tname, rows in tabs.items():
            cells = [f"{x['label']} {(_pct(x.get('mean'), 1) if x.get('n', 0) >= MIN_CELL else '—')}（{x.get('n', 0)}）" for x in rows]
            L.append(f"- {tname}：" + "／".join(cells))
    L += ["", f"- 30件未満の区分は「—」。費用＝往復{COST * 100:.1f}％（P2 だけ差し引く）。空売りができない銘柄・日もある。",
          "", "---", "", "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def main_diag():
    """データの抜けを調べる（集計だけ・銘柄名なし・何も書き出さない）"""
    info = json.load(open(UNIVERSE, encoding="utf-8"))["stocks"]
    diag = {}
    recs, missing = load_all(list(info), info, today_cutoff(), diag=diag)
    diag["n_recs"], diag["n_hot"], diag["n_missing"] = len(recs), sum(r["hot"] for r in recs), len(missing)
    print(json.dumps(diag, ensure_ascii=False, indent=1))
    return 0


def main():
    res = {"generated_at": dt.datetime.now(P.JST).isoformat(timespec="minutes"), "prereg_file": P.PREREG,
           "prereg_sha256": P.prereg_sha256()}
    try:
        info = json.load(open(UNIVERSE, encoding="utf-8"))["stocks"]
        recs, missing = load_all(list(info), info, today_cutoff())
        res["result"] = dict(analyze(recs), missing=missing)
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        res["result"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1, default=str)
    md = render_md(res)
    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main_diag() if "--diag" in sys.argv else main())
