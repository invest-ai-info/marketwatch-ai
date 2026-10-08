# -*- coding: utf-8 -*-
"""R10 日本の昼休みの窓：前場の引けから後場の寄りまでの動きのあと、後場は続くか戻るか（株価指数 CFD の自動売買の候補）。
2026-10-08 登録・オーナー「両方登録して進めてください」。PILLAR_PREREG.md「R10」。

値段＝1321.T の1時間足（Yahoo・約730日・日本時間）。前場の足＝12:00 より前に始まる足・後場の足＝12:00 以後に始まる足。
g＝後場の寄り ÷ 前場の引け − 1・a＝大引け ÷ 後場の寄り − 1。Q1＝|g| が上位20％の日に窓と逆向きに建てた損益（−符号(g)×a）の平均・
Q2＝a を g に当てはめた傾き。判定＝97.5％ の幅（日を引き直す 10,000回・両側）。**まだ誰も数えていない**。

⚠️ 決まりは PILLAR_PREREG.md「R10」と下の定数に固定。値段は pillar_lab.fetch（1時間足・UTC）を日本時間に直して使う。
⚠️ 出力（lunch-gap-lab.json / .md）は GitHub 側で生成＝手元から送らない（SYNC禁忌）。

実行: python lunch_gap_lab.py --check   （点検だけ＝日数と足の時刻の分布だけ。損益は数えない・何も書き出さない）
      python lunch_gap_lab.py           （本番。Actions の lunch-gap-lab.yml から手動で・1回だけ）
"""
import datetime as dt
import json
import sys

import numpy as np

import pillar_lab as P

OUT_JSON, OUT_MD = "lunch-gap-lab.json", "lunch-gap-lab.md"
TICKER = "1321.T"
NOON = 12                     # 前場の足＝12:00 より前に始まる足
TOP_SHARE = 0.20              # Q1：|g| が上位20％の日
N_Q = 2
ALPHA = 0.05 / N_Q            # 97.5％ の幅
N_BOOT = 10000
COST = 0.0001                 # MT4 の CFD の売り買いの差（持ち越しなし・読むための表だけ）
EDGE_DAYS = 3                 # 読むための表：月の初めと終わりの3取引日
REVERT, FOLLOW, NONE, SPLIT = "✅ 戻る向き", "✅ 続く向き", "✕ 向きなし", "△ 前半と後半で向きが違う"


# ════════════════════ 日ごとの値 ════════════════════

def sessions(bars):
    """bars＝[(日本時間の datetime, 始, 高, 安, 終)]（時刻の順）→ [(日付, 前場の引け, 後場の寄り, 大引け)]。前場・後場がそろう日だけ"""
    by_day = {}
    for t, o, h, lo, c in bars:
        if not (o and c and o > 0 and c > 0):
            continue
        by_day.setdefault(t.date(), []).append((t, o, c))
    out = []
    for d in sorted(by_day):
        am = [x for x in by_day[d] if x[0].hour < NOON]
        pm = [x for x in by_day[d] if x[0].hour >= NOON]
        if not am or not pm:
            continue
        out.append((d, am[-1][2], pm[0][1], pm[-1][2]))
    return out


def gaps(sess):
    """→ (日付の並び, g, a)"""
    d = [x[0] for x in sess]
    g = np.array([x[2] / x[1] - 1 for x in sess])
    a = np.array([x[3] / x[2] - 1 for x in sess])
    return d, g, a


def fade_values(g, a, share=TOP_SHARE):
    """|g| が上位 share の日の、窓と逆向きに建てた損益（−符号(g)×a）と、その線"""
    if not len(g):
        return np.zeros(0, bool), np.zeros(0), None
    line = float(np.quantile(np.abs(g), 1 - share))
    m = (np.abs(g) >= line) & (g != 0)
    return m, -np.sign(g[m]) * a[m], line


def slope(g, a):
    v = np.var(g)
    return float(np.mean((g - g.mean()) * (a - a.mean())) / v) if v > 0 else None


# ════════════════════ 幅と判定 ════════════════════

def boot(stat, n, alpha=ALPHA, n_boot=N_BOOT, seed=P.SEED):
    """日を引き直した stat(添字) の (下, 上)。5日未満なら None"""
    if n < 5:
        return None, None
    rng = np.random.default_rng(seed)
    sims = [stat(rng.integers(0, n, n)) for _ in range(n_boot)]
    sims = np.array([x for x in sims if x is not None and np.isfinite(x)])
    lo, hi = np.percentile(sims, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(lo), float(hi)


def word(lo, hi, revert_if_positive):
    if lo is None:
        return NONE
    if lo > 0:
        return REVERT if revert_if_positive else FOLLOW
    if hi < 0:
        return FOLLOW if revert_if_positive else REVERT
    return NONE


def analyze_days(d, g, a):
    n = len(d)
    half = n // 2
    m, v, line = fade_values(g, a)
    idx = np.where(m)[0]
    q1_lo, q1_hi = boot(lambda k: float(v[k].mean()), len(v))
    q2 = slope(g, a)
    q2_lo, q2_hi = boot(lambda k: slope(g[k], a[k]), n)
    early = np.array([i < half for i in idx])
    q1 = {"n": int(len(v)), "line": line, "value": float(v.mean()) if len(v) else None, "lo": q1_lo, "hi": q1_hi,
          "early": float(v[early].mean()) if early.any() else None, "late": float(v[~early].mean()) if (~early).any() else None}
    q2d = {"n": n, "value": q2, "lo": q2_lo, "hi": q2_hi, "early": slope(g[:half], a[:half]), "late": slope(g[half:], a[half:])}
    for q, rev in ((q1, True), (q2d, False)):
        w = word(q["lo"], q["hi"], rev)
        if w in (REVERT, FOLLOW) and None not in (q["early"], q["late"]) and np.sign(q["early"]) != np.sign(q["late"]):
            w = SPLIT
        q["summary"] = w
    # 読むための表
    net = None if q1["value"] is None else (q1["value"] - COST if q1["value"] >= 0 else -q1["value"] - COST)
    order = np.argsort(g)
    quint = [{"g_mean": float(g[k].mean()), "a_mean": float(a[k].mean()), "n": int(len(k))} for k in np.array_split(order, 5)]
    wd = {}
    for i in idx:
        wd.setdefault(d[i].weekday(), []).append(-np.sign(g[i]) * a[i])
    pos = {}
    months = {}
    for i, x in enumerate(d):
        months.setdefault((x.year, x.month), []).append(i)
    for ii in months.values():
        for j, i in enumerate(ii):
            key = "first" if j < EDGE_DAYS else "last" if j >= len(ii) - EDGE_DAYS else "mid"
            pos.setdefault(key, []).append(i)
    edge = {k: (float(np.mean([-np.sign(g[i]) * a[i] for i in v_ if m[i]])) if any(m[i] for i in v_) else None,
                int(sum(m[i] for i in v_))) for k, v_ in pos.items()}
    return {"days": n, "first": d[0].isoformat() if n else None, "last": d[-1].isoformat() if n else None,
            "g_sd": float(g.std()) if n else None, "a_sd": float(a.std()) if n else None,
            "Q1": q1, "Q2": q2d, "read": {"net_in_q1_direction": net, "quintiles": quint,
                                         "weekday": {k: (float(np.mean(x)), len(x)) for k, x in sorted(wd.items())}, "month_edge": edge}}


def to_bars(df):
    ix = df.index.tz_convert("Asia/Tokyo")
    return [(t.to_pydatetime(), float(o), float(h), float(lo), float(c))
            for t, o, h, lo, c in zip(ix, df["Open"], df["High"], df["Low"], df["Close"])]


def verdicts_of(res, today):
    out = {}
    for qk in ("Q1", "Q2"):
        q = res[qk]
        if q["summary"] in (REVERT, FOLLOW):
            continue
        out[qk] = {"status": "stop", "decided_on": today, "n": q["n"], "mean": q["value"], "lo": q["lo"], "hi": q["hi"],
                   "reason": f"過去のデータ（約2年）で1回だけ数えて{q['summary'].lstrip('✕△ ')}"}
    return out


def check_summary(df):
    bars = to_bars(df)
    starts = {}
    for t, *_ in bars:
        k = t.strftime("%H:%M")
        starts[k] = starts.get(k, 0) + 1
    sess = sessions(bars)
    return {"ticker": TICKER, "bars": len(bars), "bar_start_times": dict(sorted(starts.items())), "days_with_both_sessions": len(sess),
            "first": sess[0][0].isoformat() if sess else None, "last": sess[-1][0].isoformat() if sess else None}


# ════════════════════ 書く ════════════════════

def _p(x, d=3):
    return "—" if x is None else f"{x * 100:+.{d}f}％"


def render_md(res):
    L = ["# R10 日本の昼休みの窓：前場の引けから後場の寄りまでの動きのあと、後場は続くか戻るか", "",
         f"更新: {res.get('generated_at', '')}（事前登録＝`PILLAR_PREREG.md`「R10」・指紋 `{(res.get('prereg_sha256') or '')[:12]}`）", ""]
    r = res.get("result") or {}
    if "error" in r:
        return "\n".join(L + [f"⚠️ 計算できず：{r['error']}", "", "※ 研究の記録です。投資助言ではありません。"]) + "\n"
    q1, q2, rd = r["Q1"], r["Q2"], r["read"]
    L += [f"値段＝{TICKER} の1時間足（{r['first']}〜{r['last']}・{r['days']}日）。g＝後場の寄り ÷ 前場の引け − 1（ばらつき {_p(r['g_sd'])}）・"
          f"a＝大引け ÷ 後場の寄り − 1（ばらつき {_p(r['a_sd'])}）。幅は 97.5％（日を引き直す 10,000回）。**まだ誰も数えていなかった問い**。", "",
          "## まとめ", "", "| 問い | 値 | 97.5％の幅 | 前半／後半 | まとめ |", "|---|---:|---|---|---|",
          f"| Q1 大きな昼休みの窓（|g| 上位20％・線 {_p(q1['line'])}・{q1['n']}日）のあと、窓と逆向きに建てた後場の損益 | {_p(q1['value'])} | "
          f"{_p(q1['lo'])}〜{_p(q1['hi'])} | {_p(q1['early'])}／{_p(q1['late'])} | **{q1['summary']}** |",
          f"| Q2 すべての日：後場の動きを昼休みの窓に当てはめた傾き（窓1あたり） | {'—' if q2['value'] is None else format(q2['value'], '+.3f')} | "
          f"{'—' if q2['lo'] is None else format(q2['lo'], '+.3f') + '〜' + format(q2['hi'], '+.3f')} | "
          f"{'—' if q2['early'] is None else format(q2['early'], '+.3f')}／{'—' if q2['late'] is None else format(q2['late'], '+.3f')} | **{q2['summary']}** |",
          "", "## 読むための表（判定しない）", "",
          f"- Q1 の向きに建てたときの CFD の費用（{COST * 100:.2f}％）を引いた平均：{_p(rd['net_in_q1_direction'])}", "",
          "| 昼休みの窓の大きさ（5つに分けた順） | 窓の平均 | 後場の動きの平均 | 日数 |", "|---|---:|---:|---:|"]
    for i, q in enumerate(rd["quintiles"], 1):
        L.append(f"| {i} | {_p(q['g_mean'])} | {_p(q['a_mean'])} | {q['n']} |")
    names = "月火水木金土日"
    L += ["", "| 曜日（Q1 の日だけ） | 窓と逆向きの損益 | 日数 |", "|---|---:|---:|"]
    L += [f"| {names[int(k)]} | {_p(v[0])} | {v[1]} |" for k, v in rd["weekday"].items()]
    L += ["", "| 月の中の位置（Q1 の日だけ） | 窓と逆向きの損益 | 日数 |", "|---|---:|---:|"]
    for k, nm in (("first", "月の初め（最初の3取引日）"), ("mid", "それ以外"), ("last", "月の終わり（最後の3取引日）")):
        v = rd["month_edge"].get(k, (None, 0))
        L.append(f"| {nm} | {_p(v[0])} | {v[1]} |")
    L += ["", "## 注意", "",
          "- 1321.T は CFD そのものではない（CFD は昼休みも先物に沿って動くので、12:30 の CFD の値段は 1321.T の後場の寄りに近いと見なした）",
          "- 約2年しかない（昔の時代では確かめられない）。上位20％の線はこの期間の g だけで決めた", "", "---", "",
          "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def main(argv):
    res = {"generated_at": dt.datetime.now(P.JST).isoformat(timespec="minutes"), "prereg_file": P.PREREG,
           "prereg_sha256": P.prereg_sha256()}
    try:
        df = P.fetch(TICKER, "1h")
        if df is None:
            raise RuntimeError(f"{TICKER} の1時間足を取れない")
        if "--check" in argv:
            print(json.dumps(check_summary(df), ensure_ascii=False, indent=1))
            return 0
        d, g, a = gaps(sessions(to_bars(df)))
        res["result"] = analyze_days(d, g, a)
        res.update(kind="backtest", titles={"Q1": "日本の昼休みの大きな窓のあと、後場に窓と逆向き（1321.T の1時間足・約2年・1回だけ数えた）",
                                            "Q2": "日本の昼休みの窓と後場の動きの傾き（1321.T の1時間足・約2年・1回だけ数えた）"},
                   verdicts=verdicts_of(res["result"], dt.datetime.now(P.JST).date().isoformat()))
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
