# -*- coding: utf-8 -*-
"""J22 9:00〜9:30 に上がった銘柄と下がった銘柄、それぞれの法則（寄りの前に分かる特徴・30分の値動きの形・朝の地合い）。
2026-10-07 登録・オーナー「9時から9時半までの間に上がった銘柄と下がった銘柄で分けて、それぞれの法則性を見つけてください」。
PILLAR_PREREG.md「J22」。

主＝5分足のある朝（直近約60日・寄り→9:30）／確かめ＝それより前の1時間足の朝（2023-10〜・寄り→10:00）。
特徴14（F1〜F14）は「特徴あり − 比べる相手」の平均の差を両方で数え、同じ向きのときだけ「法則」と呼ぶ。
W1・W2＝最初の5分の動きのあと 9:05→9:30 は続くか戻るか（主の朝だけ）。値動きの形と朝の地合いは読むための表。

⚠️ 決まりは PILLAR_PREREG.md「J22」と下の定数に固定。朝の行は prevday_lab（J16）と同じ作り方。
⚠️ 出力（open30-lab.json / .md）は集計だけ・銘柄名とコードは出さない（SYNC禁忌）。

実行: python open30_lab.py --check   （点検だけ＝行数と組ごとの回数。損益は数えない・何も書き出さない）
      python open30_lab.py           （本番。Actions の open30-lab.yml から手動で・1回だけ）
"""
import datetime as dt
import json
import sys

import numpy as np

import gap_lab as GL
import highs_trap_lab as T
import jp_bars
import landmine_lab as LM
import main_field_lab as MF
import pillar_lab as P
import prevday_lab as PD
import prevgap_lab as PG
import yori_lab as Y

OUT_JSON, OUT_MD = "open30-lab.json", "open30-lab.md"
FIRST, LAST = PD.NEW                       # 2023-10-10〜2026-10-05
COLS = PD.COLS + ("dev25", "tv_ratio", "wick", "hi_close", "new_high", "new_low", "price", "range",
                  "r905", "hi_slot", "lo_slot", "yoriten", "yorizoko")
C = {k: i for i, k in enumerate(COLS)}
HIGH_DAYS = LM.HIGH_DAYS                   # 250営業日
SLOTS = 6                                  # 9:00〜9:30 の5分足
MIN_STOCKS = PG.MIN_STOCKS                 # 500
IDIO = 0.01
N_Q = 16
ALPHA = 0.05 / N_Q                         # 99.69％ の幅
UP, DOWN = "上がりやすい", "下がりやすい"
LAW, MAIN_ONLY, CONF_ONLY, NONE = "✅ 法則（9:30 と 10:00 の両方で同じ向き）", "△ 9:30（60日）だけ", "△ 10:00（約3年）だけ", "見えない"
SIGN_W = "兆し（60日だけ・前向きで確かめる）"

# (名前, 説明, 特徴あり, 比べる相手)。それぞれ (A, idio) → bool の配列
FEATURES = (
    ("F1", "その銘柄だけ +1％以上高く寄る（比べる相手＝±1％未満）", lambda A, i: i >= IDIO, lambda A, i: np.abs(i) < IDIO),
    ("F2", "その銘柄だけ −1％以下安く寄る（比べる相手＝±1％未満）", lambda A, i: i <= -IDIO, lambda A, i: np.abs(i) < IDIO),
    ("F3", "前の日 +5％以上（比べる相手＝前の日 ±2％未満）", lambda A, i: A[:, C["rprev"]] >= 0.05, lambda A, i: np.abs(A[:, C["rprev"]]) < 0.02),
    ("F4", "前の日 −5％以下（比べる相手＝前の日 ±2％未満）", lambda A, i: A[:, C["rprev"]] <= -0.05, lambda A, i: np.abs(A[:, C["rprev"]]) < 0.02),
    ("F5", "25日線より +15％超（比べる相手＝±5％以内）", lambda A, i: A[:, C["dev25"]] > 0.15, lambda A, i: np.abs(A[:, C["dev25"]]) <= 0.05),
    ("F6", "25日線より −15％以下（比べる相手＝±5％以内）", lambda A, i: A[:, C["dev25"]] <= -0.15, lambda A, i: np.abs(A[:, C["dev25"]]) <= 0.05),
    ("F7", "前の日の売買代金が20営業日平均の5倍以上（比べる相手＝2倍未満）", lambda A, i: A[:, C["tv_ratio"]] >= 5, lambda A, i: A[:, C["tv_ratio"]] < 2),
    ("F8", "前の日の値幅が8％以上（比べる相手＝3％未満）", lambda A, i: A[:, C["range"]] >= 0.08, lambda A, i: A[:, C["range"]] < 0.03),
    ("F9", "前の日が高値引け（比べる相手＝そうでない）", lambda A, i: A[:, C["hi_close"]] >= 0.5, lambda A, i: A[:, C["hi_close"]] < 0.5),
    ("F10", "前の日の上ヒゲが長い（比べる相手＝そうでない）", lambda A, i: A[:, C["wick"]] >= 0.5, lambda A, i: A[:, C["wick"]] < 0.5),
    ("F11", "前の日に52週高値を更新（比べる相手＝そうでない）", lambda A, i: A[:, C["new_high"]] >= 0.5, lambda A, i: A[:, C["new_high"]] < 0.5),
    ("F12", "前の日に52週安値を更新（比べる相手＝そうでない）", lambda A, i: A[:, C["new_low"]] >= 0.5, lambda A, i: A[:, C["new_low"]] < 0.5),
    ("F13", "低位株＝前の日の終値300円未満（比べる相手＝1,000円以上）", lambda A, i: A[:, C["price"]] < 300, lambda A, i: A[:, C["price"]] >= 1000),
    ("F14", "前の日の売買代金10億円以上（比べる相手＝1億円未満）", lambda A, i: A[:, C["turnover"]] >= 10, lambda A, i: A[:, C["turnover"]] < 1),
)
W_FLAT = 0.003
WINDOWS = (("W1", "最初の5分で +1％以上（比べる相手＝±0.3％未満）", lambda r: r >= 0.01),
           ("W2", "最初の5分で −1％以下（比べる相手＝±0.3％未満）", lambda r: r <= -0.01))
MKT_BANDS = (("≦ −0.5％", lambda g: g <= -0.005), ("±0.5％未満", lambda g: np.abs(g) < 0.005), ("≧ +0.5％", lambda g: g >= 0.005))
PRICE_BANDS = (("300円未満", 0, 300), ("300〜1,000円", 300, 1000), ("1,000〜3,000円", 1000, 3000), ("3,000円以上", 3000, np.inf))
WEEKDAYS = "月火水木金"


# ════════════════════ 行 ════════════════════

def prev_low(daily):
    """日足の各日 k について、その前の250営業日の安値をすべて下回ったか（そろわなければ NaN）"""
    lo = np.array([r[3] for r in daily], float)
    n = len(lo)
    out = np.full(n, np.nan)
    if n > HIGH_DAYS:
        past = np.lib.stride_tricks.sliding_window_view(lo, HIGH_DAYS)[:-1].min(axis=1)
        out[HIGH_DAYS:] = (lo[HIGH_DAYS:] < past).astype(float)
    return out


def shape(bars5, op):
    """5分足（9:00 の足がある朝だけ）→ (寄り→9:05, 高値の足, 安値の足, 寄り天, 寄り底)。足の番号は 0＝9:00〜5＝9:25"""
    nan = (np.nan,) * 5
    if not bars5:
        return nan
    b = sorted(bars5)
    if (b[0][0].hour, b[0][0].minute) != (9, 0):
        return nan
    win = [x for x in b if (x[0].hour, x[0].minute) < (9, 30)]
    p905 = Y.price_at(b, "09:05")
    r905 = p905 / op - 1 if p905 else np.nan
    if not np.isfinite(r905) or abs(r905) > T.MAX_MOVE:
        r905 = np.nan
    hs = [x[2] for x in win]
    ls = [x[3] for x in win]
    slot = lambda x: (x[0].minute // 5) if x[0].hour == 9 else 0  # noqa: E731
    hi_slot = slot(win[int(np.argmax(hs))])
    lo_slot = slot(win[int(np.argmin(ls))])
    return (r905, float(hi_slot), float(lo_slot), float(op >= max(hs) * (1 - 1e-9)), float(op <= min(ls) * (1 + 1e-9)))


def stock_rows(ci, daily, m5, h1, drops=None):
    """J16 の行（2023-10-10〜2026-10-05）＋前の日までの特徴＋5分足の値動きの形"""
    A = PD.stock_rows(ci, daily, m5, h1, first=FIRST, last=LAST, recent_from=FIRST, drops=drops)
    if not len(A):
        return np.zeros((0, len(COLS)))
    dev, _ = MF.prev_features(daily)
    ratio, wick, hi_close, new_high = LM.prev_more(daily)
    new_low = prev_low(daily)
    c = np.array([r[4] for r in daily], float)
    h = np.array([r[2] for r in daily], float)
    lo = np.array([r[3] for r in daily], float)
    with np.errstate(invalid="ignore", divide="ignore"):
        rng = np.where(c > 0, (h - lo) / c, np.nan)
    pos = {dt.date.fromisoformat(r[0]).toordinal(): i for i, r in enumerate(daily)}
    kk = np.array([pos[int(o)] for o in A[:, C["day"]]])
    k = kk - 1
    shp = np.array([shape(m5.get(daily[j][0]), daily[j][1]) if np.isfinite(r930) else (np.nan,) * 5
                    for j, r930 in zip(kk, A[:, C["r930"]])], float).reshape(-1, 5)
    extra = [dev[k], ratio[k], wick[k], hi_close[k], new_high[k], new_low[k], c[k], rng[k]]
    return np.hstack([A] + [x.reshape(-1, 1) for x in extra] + [shp])


# ════════════════════ 組と判定 ════════════════════

def samples(A):
    """→ (主＝寄り→9:30 が数えられる朝, 確かめ＝5分足の期間が始まる朝より前で寄り→10:00 が数えられる朝, 5分足の期間の始まり)"""
    day = A[:, C["day"]]
    has = np.isfinite(A[:, C["r930"]])
    u, n = np.unique(day[has], return_counts=True)
    ok = u[n >= MIN_STOCKS]
    if not len(ok):
        return has, np.zeros(len(A), bool), None
    start = ok.min()
    return has & (day >= start), np.isfinite(A[:, C["r1000"]]) & (day < start), int(start)


def measure(A, v, g, alpha=ALPHA):
    """組0 − 組1 の平均の差（費用前）。日と銘柄で引き直した広いほう・主の朝の前半と後半"""
    gg = np.where(np.isfinite(v), g, -1)
    ns = [int((gg == k).sum()) for k in range(2)]
    out = {"ns": ns, "value": None, "lo": None, "hi": None, "early": None, "late": None}
    if min(ns) == 0:
        return out
    pt, lo_d, hi_d = GL.boot(v, gg, 2, A[:, C["day"]], GL._diff2, alpha)
    _, lo_c, hi_c = GL.boot(v, gg, 2, A[:, C["code"]], GL._diff2, alpha)
    days = np.unique(A[gg >= 0, C["day"]])
    cut = days[len(days) // 2]
    early, late = A[:, C["day"]] < cut, A[:, C["day"]] >= cut
    out.update(value=pt, early=MF._plain(v[early], gg[early], "diff")[0], late=MF._plain(v[late], gg[late], "diff")[0],
               by_day=[lo_d, hi_d], by_stock=[lo_c, hi_c])
    if None not in (lo_d, lo_c, hi_d, hi_c):
        out.update(lo=min(lo_d, lo_c), hi=max(hi_d, hi_c))
    return out


def direction(q, halves=True):
    """幅がまるごと0の片側・30件以上（・前半と後半が同じ向き）なら UP／DOWN、それ以外は None"""
    if q.get("lo") is None or min(q["ns"]) < T.MIN_N:
        return None
    if q["lo"] > 0:
        d = UP
    elif q["hi"] < 0:
        d = DOWN
    else:
        return None
    if halves:
        s = 1 if d == UP else -1
        if q.get("early") is None or q.get("late") is None or q["early"] * s <= 0 or q["late"] * s <= 0:
            return None
    return d


def summarize(dm, dc):
    if dm and dc:
        return f"{LAW}：{dm}" if dm == dc else NONE
    if dm:
        return f"{MAIN_ONLY}：{dm}"
    if dc:
        return f"{CONF_ONLY}：{dc}"
    return NONE


def r_after905(A):
    with np.errstate(invalid="ignore"):
        return (1 + A[:, C["r930"]]) / (1 + A[:, C["r905"]]) - 1


def _share(v, m):
    x = v[m & np.isfinite(v)]
    if not len(x):
        return {"n": 0, "up": None, "down": None, "flat": None, "mean": None, "net": None}
    return {"n": int(len(x)), "up": float((x > 0).mean()), "down": float((x < 0).mean()), "flat": float((x == 0).mean()),
            "mean": float(x.mean()), "net": float(x.mean() - T.COST)}


def _dist(x, m):
    x = x[m & np.isfinite(x)]
    return [int((x == s).sum()) for s in range(SLOTS)]


def reading(A, idio, main, conf):
    v9, v10 = A[:, C["r930"]], A[:, C["r1000"]]
    up9, dn9 = main & (v9 > 0), main & (v9 < 0)
    out = {"overall": {"930": _share(v9, main), "1000": _share(v10, conf)},
           "price_flat": {name: _share(v9, main & (A[:, C["price"]] >= a) & (A[:, C["price"]] < b)) for name, a, b in PRICE_BANDS},
           "features": {}, "shape": {}, "morning": {}}
    n_up, n_dn = max(int(up9.sum()), 1), max(int(dn9.sum()), 1)
    for key, _, yes, ref in FEATURES:
        y, r = yes(A, idio), ref(A, idio)
        out["features"][key] = {"yes": _share(v9, main & y), "ref": _share(v9, main & r),
                                "in_up": float((up9 & y).sum() / n_up), "in_down": float((dn9 & y).sum() / n_dn),
                                "yes_1000": _share(v10, conf & y), "ref_1000": _share(v10, conf & r)}
    has = main & np.isfinite(A[:, C["hi_slot"]])
    r905 = A[:, C["r905"]]
    for name, m in (("up", has & (v9 > 0)), ("down", has & (v9 < 0))):
        n = max(int(m.sum()), 1)
        same = (np.sign(r905) == np.sign(v9)) & np.isfinite(r905)
        out["shape"][name] = {"n": int(m.sum()), "yoriten": float(A[m, C["yoriten"]].sum() / n), "yorizoko": float(A[m, C["yorizoko"]].sum() / n),
                              "hi_slot": _dist(A[:, C["hi_slot"]], m), "lo_slot": _dist(A[:, C["lo_slot"]], m),
                              "first5_same": float((m & same).sum() / n)}
    ra = r_after905(A)
    out["shape"]["after905"] = {"up1": _share(ra, has & (r905 >= 0.01)), "flat": _share(ra, has & (np.abs(r905) < W_FLAT)),
                                "down1": _share(ra, has & (r905 <= -0.01))}
    mg = A[:, C["gap"]] - idio
    wd = np.array([dt.date.fromordinal(int(o)).weekday() for o in A[:, C["day"]]])
    for tag, v, m in (("930", v9, main), ("1000", v10, conf)):
        out["morning"][tag] = {"mkt_gap": {name: _morning(A, v, m & f(mg)) for name, f in MKT_BANDS},
                               "weekday": {WEEKDAYS[w]: _morning(A, v, m & (wd == w)) for w in range(5)}}
    return out


def _morning(A, v, m):
    """朝ごとの「上がった株の割合」の平均と、行の平均・朝の数"""
    d = A[m, C["day"]]
    x = v[m]
    if not len(x):
        return {"days": 0, "up_share": None, "mean": None}
    u, inv = np.unique(d, return_inverse=True)
    up = np.bincount(inv, weights=(x > 0).astype(float)) / np.bincount(inv)
    return {"days": int(len(u)), "up_share": float(up.mean()), "mean": float(x.mean())}


def analyze(A):
    A, idio = PG.idio_gap(A)
    main, conf, start = samples(A)
    res = {"sample": {"start_5m": dt.date.fromordinal(start).isoformat() if start else None,
                      "main_days": int(len(np.unique(A[main, C["day"]]))), "main_rows": int(main.sum()),
                      "conf_days": int(len(np.unique(A[conf, C["day"]]))), "conf_rows": int(conf.sum())},
           "features": {}, "windows": {}, "summary": {}}
    v9, v10 = A[:, C["r930"]], A[:, C["r1000"]]
    for key, _, yes, ref in FEATURES:
        y, r = yes(A, idio), ref(A, idio)
        qm = measure(A, v9, GL.pair_grp(main & y, main & r & ~y))
        qc = measure(A, v10, GL.pair_grp(conf & y, conf & r & ~y))
        dm, dc = direction(qm), direction(qc, halves=False)
        res["features"][key] = {"main": qm, "conf": qc, "dir_main": dm, "dir_conf": dc}
        res["summary"][key] = summarize(dm, dc)
    ra, r905 = r_after905(A), A[:, C["r905"]]
    flat = main & (np.abs(r905) < W_FLAT)
    for key, _, f in WINDOWS:
        q = measure(A, ra, GL.pair_grp(main & f(r905), flat))
        d = direction(q)
        res["windows"][key] = q
        res["summary"][key] = f"{SIGN_W}：{'続く' if (d == UP) == (key == 'W1') else '戻る'}" if d else NONE
    res["reading"] = reading(A, idio, main, conf)
    return res


# ════════════════════ 読む ════════════════════

def load(codes, fetch):
    parts, missing, drops = [], {"daily": [], "h1": [], "m5": []}, {"n": 0}
    for i, code in enumerate(codes):
        d = fetch(code, "1d", "10y")
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
        parts.append(stock_rows(i, daily, T._by_day(m5), T._by_day(h1), drops=drops))
        if (i + 1) % 500 == 0:
            print(f"  ...{i + 1}/{len(codes)}", flush=True)
    A = np.vstack(parts) if parts else np.zeros((0, len(COLS)))
    return A, missing, drops


def check_summary(A, missing, n_codes, store):
    B, idio = PG.idio_gap(A)
    main, conf, start = samples(B)
    out = {"n_codes": n_codes, "missing": {k: len(v) for k, v in missing.items()}, "rows": int(len(A)), "store": store,
           "start_5m": dt.date.fromordinal(start).isoformat() if start else None,
           "main": {"days": int(len(np.unique(B[main, C["day"]]))), "rows": int(main.sum()),
                    "with_shape": int((main & np.isfinite(B[:, C["hi_slot"]])).sum())},
           "conf": {"days": int(len(np.unique(B[conf, C["day"]]))), "rows": int(conf.sum())}, "sizes": {}}
    for key, _, yes, ref in FEATURES:
        y, r = yes(B, idio), ref(B, idio)
        out["sizes"][key] = {"main": [int((main & y).sum()), int((main & r & ~y).sum())], "conf": [int((conf & y).sum()), int((conf & r & ~y).sum())]}
    r905 = B[:, C["r905"]]
    for key, _, f in WINDOWS:
        out["sizes"][key] = [int((main & f(r905)).sum()), int((main & (np.abs(r905) < W_FLAT)).sum())]
    return out


def _p(x, d=2):
    return Y._pct(x, d)


def _w(x):
    return "—" if x is None else f"{x * 100:.1f}％"


def render_md(res):
    L = ["# J22 9:00〜9:30 に上がった銘柄と下がった銘柄、それぞれの法則", "",
         f"作成: {res['generated_at']}（GitHub Actions で計算）。事前登録＝`{P.PREREG}`「J22」（指紋 sha256 `{(res.get('prereg_sha256') or '')[:16]}…`）。",
         "銘柄名は出しません。**上がった＝寄り値より 9:30 の値が上**（費用前）。特徴はすべて寄りの時点で分かるもの。**売買の決まりではない**。", ""]
    r = res.get("result") or {}
    if r.get("error"):
        return "\n".join(L + [f"- ⚠️ 計算できず: {r['error']}", ""]) + "\n"
    s, rd = r["sample"], r["reading"]
    o9, o10 = rd["overall"]["930"], rd["overall"]["1000"]
    L += [f"- 対象：置き場の一覧 {r.get('n_codes')}銘柄（いま上場している銘柄だけ）。取れなかった銘柄 {r.get('n_missing')}",
          f"- 主（寄り→9:30）＝{s['start_5m']}〜 の {s['main_days']}朝・{s['main_rows']:,}行／確かめ（寄り→10:00）＝それより前の {s['conf_days']}朝・{s['conf_rows']:,}行",
          f"- 全体：9:30 までに **上がった {_w(o9['up'])}・下がった {_w(o9['down'])}・変わらず {_w(o9['flat'])}**（平均 {_p(o9['mean'])}・費用後 {_p(o9['net'])}）／"
          f"10:00 は上がった {_w(o10['up'])}・下がった {_w(o10['down'])}・変わらず {_w(o10['flat'])}（平均 {_p(o10['mean'])}）", ""]
    names = {k: n for k, n, *_ in FEATURES} | {k: n for k, n, _ in WINDOWS}
    summ = r["summary"]
    ups = [k for k, v in summ.items() if v.startswith(LAW) and v.endswith(UP)]
    dns = [k for k, v in summ.items() if v.startswith(LAW) and v.endswith(DOWN)]
    tri = [k for k, v in summ.items() if v.startswith("△") or v.startswith(SIGN_W)]
    L += ["## まとめ", "",
          "- **上がりやすい特徴（9:30 と 10:00 の両方で同じ向き）**：" + ("／".join(f"{k} {names[k]}" for k in ups) or "なし"),
          "- **下がりやすい特徴（同）**：" + ("／".join(f"{k} {names[k]}" for k in dns) or "なし"),
          "- 片方だけ・兆し：" + ("／".join(f"{k} {names[k]}＝{summ[k]}" for k in tri) or "なし"), "",
          "## 特徴ごとの判定（特徴あり − 比べる相手・1回あたりの平均の差・費用前・幅 99.69％）", "",
          "| 特徴 | 9:30（60日）の差（幅） | 回数（あり／相手） | 10:00（約3年）の差（幅） | 回数（あり／相手） | まとめ |", "|---|---|---|---|---|---|"]
    for key, name, *_ in FEATURES:
        f = r["features"][key]
        qm, qc = f["main"], f["conf"]
        L.append(f"| {key} {name} | {_p(qm.get('value'))}（{_p(qm.get('lo'))}〜{_p(qm.get('hi'))}） | {qm['ns'][0]:,}／{qm['ns'][1]:,} | "
                 f"{_p(qc.get('value'))}（{_p(qc.get('lo'))}〜{_p(qc.get('hi'))}） | {qc['ns'][0]:,}／{qc['ns'][1]:,} | {summ[key]} |")
    L += ["", "## 上がった株に多い特徴・下がった株に多い特徴（9:30・読むだけ）", "",
          "| 特徴 | 上がった株のうち | 下がった株のうち | その特徴の株が上がった割合／下がった割合 | 比べる相手の上がった割合／下がった割合 | 平均（費用後）あり／相手 |",
          "|---|---:|---:|---|---|---|"]
    for key, name, *_ in FEATURES:
        f = rd["features"][key]
        y, rf = f["yes"], f["ref"]
        L.append(f"| {key} {name} | {_w(f['in_up'])} | {_w(f['in_down'])} | {_w(y['up'])}／{_w(y['down'])}（{y['n']:,}回） | "
                 f"{_w(rf['up'])}／{_w(rf['down'])} | {_p(y['net'])}／{_p(rf['net'])} |")
    sh = rd["shape"]
    slot_names = ["9:00", "9:05", "9:10", "9:15", "9:20", "9:25"]

    def dist(x):
        n = max(sum(x), 1)
        return "・".join(f"{slot_names[i]} {x[i] / n * 100:.0f}％" for i in range(SLOTS))
    L += ["", "## 30分の値動きの形（5分足の 9:00 の足がある朝・読むだけ）", "",
          "| | 上がった株 | 下がった株 |", "|---|---|---|",
          f"| 回数 | {sh['up']['n']:,} | {sh['down']['n']:,} |",
          f"| 寄り天（寄り値が 9:00〜9:30 の高値） | {_w(sh['up']['yoriten'])} | {_w(sh['down']['yoriten'])} |",
          f"| 寄り底（寄り値が安値） | {_w(sh['up']['yorizoko'])} | {_w(sh['down']['yorizoko'])} |",
          f"| 最初の5分の向きが 9:30 と同じ | {_w(sh['up']['first5_same'])} | {_w(sh['down']['first5_same'])} |",
          f"| 30分の高値をつけた5分足 | {dist(sh['up']['hi_slot'])} | {dist(sh['down']['hi_slot'])} |",
          f"| 30分の安値をつけた5分足 | {dist(sh['up']['lo_slot'])} | {dist(sh['down']['lo_slot'])} |"]
    a9 = sh["after905"]
    L += ["", "### 最初の5分のあと、9:05 → 9:30 は続くか戻るか", "",
          "| 最初の5分 | 9:05→9:30 で上がった割合／下がった割合 | 平均（費用前） | 回数 |", "|---|---|---|---:|"]
    for k, lab in (("up1", "+1％以上"), ("flat", "±0.3％未満"), ("down1", "−1％以下")):
        x = a9[k]
        L.append(f"| {lab} | {_w(x['up'])}／{_w(x['down'])} | {_p(x['mean'])} | {x['n']:,} |")
    for key, name, _ in WINDOWS:
        q = r["windows"][key]
        L.append(f"- **{key} {name}**：差 {_p(q.get('value'))}（幅 {_p(q.get('lo'))}〜{_p(q.get('hi'))}・{q['ns'][0]:,}／{q['ns'][1]:,}回）→ **{summ[key]}**")
    L += ["", "## 朝の地合い（その朝の全銘柄の窓の中央値・曜日ごと・読むだけ）", "",
          "| 区分 | 9:30：朝の数・上がった株の割合（朝の平均）・平均 | 10:00：同じ |", "|---|---|---|"]
    mo = rd["morning"]
    for grp, lab in (("mkt_gap", "相場全体の窓 "), ("weekday", "曜日 ")):
        for k in mo["930"][grp]:
            a, b = mo["930"][grp][k], mo["1000"][grp][k]
            L.append(f"| {lab}{k} | {a['days']}朝・{_w(a['up_share'])}・{_p(a['mean'])} | {b['days']}朝・{_w(b['up_share'])}・{_p(b['mean'])} |")
    L += ["", "- 価格帯ごとの「変わらず」の割合（9:30・呼値の影響）：" + "／".join(
        f"{k} {_w(v['flat'])}（上がった {_w(v['up'])}・下がった {_w(v['down'])}）" for k, v in rd["price_flat"].items()),
          "", "- ⚠️ 9:30 は約60日だけ（日で引き直した幅が広い）。確かめは 10:00 で 9:30 そのものではない。F1〜F4 は J13・J15・J16 で同じ1時間足の朝の向きを見ている＝確かめは完全な目隠しではない。"
          "いま上場している銘柄だけ。上がった・下がったは費用前。**使うなら前向きの登録で確かめてから**。",
          "", "---", "", "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def main(argv):
    res = {"generated_at": dt.datetime.now(P.JST).isoformat(timespec="minutes"), "prereg_file": P.PREREG,
           "prereg_sha256": P.prereg_sha256()}
    try:
        stocks, list_date = jp_bars.load_universe()
        codes = sorted(stocks)
        A, missing, drops = load(codes, jp_bars.fetcher())
        store = jp_bars.info()
        res["price_store"] = store
        if "--check" in argv:
            print(json.dumps(check_summary(A, missing, len(codes), store), ensure_ascii=False, indent=1))
            return 0
        bad = set(missing["daily"]) | set(missing["h1"]) | set(missing["m5"])
        if len(bad) > T.MAX_MISSING * len(codes):
            raise RuntimeError(f"日足・1時間足・5分足のどれかを取れなかった銘柄が {len(bad)}/{len(codes)}＝5％超。偏った組で判定しない（取り直す）")
        res["result"] = dict(analyze(A), n_codes=len(codes), list_date=list_date,
                             n_missing={k: len(v) for k, v in missing.items()}, n_dropped=drops["n"])
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
