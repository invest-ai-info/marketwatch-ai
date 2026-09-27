# -*- coding: utf-8 -*-
"""S2 重要な発表のあと、動いた向きに乗るか逆らうか。2026-09-27 夜登録・オーナー「登録してください」。

B2（発表直後の値動きの大きさ）の続きの1問。FOMC・米CPI・米雇用統計の発表を含む1時間足が動いた向きに、
次の足から乗る取引と逆らう取引を、同じ入り方・同じ幅で数える。1回だけ数える。
⚠️ 物差しと判定の基準は PILLAR_PREREG.md「S2 重要な発表のあと」（事前登録・計算より先にコミット済み）と下の定数に固定。
   結果を見てから動かさない。出力には事前登録の中身の指紋（sha256）を書き込む。
⚠️ 出力 event-dir-lab.json / event-dir-lab.md は GitHub 側で生成＝手元から送らない（SYNC禁忌）。
⚠️ エンジン・発火条件・固定オラクル（signal_lab_verify.py）には触れない。メールや売買の決まりは変えない。

実行: python event_dir_lab.py   （Actions の event-dir-lab.yml から手動で。bls.gov は Actions からなら届く）
"""
import datetime as dt
import json
import sys

import numpy as np
import pandas as pd

from box_lab import (COST_MULT, COST_PIPS, OFFICIAL_SPREAD_PIPS, PAIR_NAME, PAIRS, _f, _m, boot_ci, cost_price,
                     pip_size, placebo_p, simulate)
from pillar_lab import (BLS_PREFIX, BLS_URLS, ET, EVENT_NAME, FOMC_URL, JST, event_time, fetch, http_get, parse_bls,
                        parse_fomc, prereg_sha256)

OUT_JSON, OUT_MD = "event-dir-lab.json", "event-dir-lab.md"
SEED = 20260927
MIN_N = 300            # 取引の数・これ未満は「件数不足」
ALPHA = 0.05 / 2       # 問いは乗る・逆らうの2つ
ATR_N = 14             # 発表の足の直前の14本
SL_ATR, TP_ATR = 1.5, 2.0
HOLD_BARS = 4          # 入る足を1本目として4本目の終値で時間切れ
KINDS = ("fomc", "cpi", "nfp")


def load_events():
    """一次情報から発表日を取る（B2 と同じ）。取れなかった種類は数えない"""
    events, sources = {}, {}
    try:
        events["fomc"] = parse_fomc(http_get(FOMC_URL))
        sources["fomc"] = "ok" if events["fomc"] else "解析0件"
    except Exception as e:  # noqa: BLE001
        sources["fomc"] = f"取得できず: {type(e).__name__}"
    for k, url in BLS_URLS.items():
        try:
            events[k] = parse_bls(http_get(url), BLS_PREFIX[k])
            sources[k] = "ok" if events[k] else "解析0件"
        except Exception as e:  # noqa: BLE001
            sources[k] = f"取得できず: {type(e).__name__}"
    return {k: v for k, v in events.items() if v}, sources


def event_list(events, lo_d, hi_d, today):
    """[(発表時刻 UTC, 種類のタプル)]。足の最初の日と最後の日の間・今日より前だけ。同じ時刻は1回"""
    by_ts = {}
    for kind, dates in events.items():
        for d in dates:
            if not (lo_d < d < hi_d) or d >= today:
                continue
            ts = pd.Timestamp(event_time(d, kind)).tz_convert("UTC")
            by_ts.setdefault(ts, set()).add(kind)
    return [(ts, tuple(k for k in KINDS if k in ks)) for ts, ks in sorted(by_ts.items())]


def atr_before(h, lo, c, i0, n=ATR_N):
    """発表の足の直前 n 本の真の値幅の単純平均。前の足の終値が要るので n+1 本そろわなければ None"""
    if i0 < n + 1:
        return None
    tr = [max(h[k], c[k - 1]) - min(lo[k], c[k - 1]) for k in range(i0 - n, i0)]
    return float(np.mean(tr))


def event_trade(bars, ticker, ts, kinds, pos, arrs):
    """1つの発表・1つのペアの取引（乗る・逆らうの両方）。戻り値＝(行, 数えなかった理由)"""
    o, h, lo, c = arrs
    h0 = ts.floor("h")
    if h0 not in pos:
        return None, "発表の足が無い"
    i0 = pos[h0]
    move = float(c[i0] - o[i0])
    if move == 0:
        return None, "発表の足が動いていない"
    direction = 1 if move > 0 else -1
    t1 = h0 + pd.Timedelta(hours=1)
    if t1 not in pos:
        return None, "次の足が無い"
    e = pos[t1]
    atr = atr_before(h, lo, c, i0)
    if atr is None or atr <= 0:
        return None, "直前の足が足りない"
    risk, width = SL_ATR * atr, TP_ATR * atr
    stop = int(bars.index.searchsorted(h0 + pd.Timedelta(hours=HOLD_BARS + 1)))
    if stop <= e:
        return None, "次の足が無い"
    entry, exit_px = float(o[e]), float(c[stop - 1])
    r_f, x_f = simulate(o, h, lo, c, e, stop, entry, direction, risk, width, exit_px)
    r_x, x_x = simulate(o, h, lo, c, e, stop, entry, -direction, risk, width, exit_px)
    cost_r = cost_price(ticker) / risk
    off = OFFICIAL_SPREAD_PIPS.get(ticker)
    off_r = off * pip_size(ticker) / risk if off is not None else None
    return {"ticker": ticker, "date": ts.tz_convert(ET).date().isoformat(), "event_utc": ts.isoformat(),
            "kinds": list(kinds), "dir": direction, "move_atr": abs(move) / atr,
            "follow_gross": r_f, "follow_net": r_f - cost_r, "fade_gross": r_x, "fade_net": r_x - cost_r,
            "cost_r": cost_r,
            "follow_official": (r_f - off_r) if off_r is not None else None,
            "fade_official": (r_x - off_r) if off_r is not None else None,
            "exit_follow": x_f, "exit_fade": x_x}, None


def trades_for(bars, ticker, events, today):
    pos = {t: i for i, t in enumerate(bars.index)}
    arrs = tuple(bars[k].to_numpy(float) for k in ("Open", "High", "Low", "Close"))
    lo_d, hi_d = bars.index[0].tz_convert(ET).date(), bars.index[-1].tz_convert(ET).date()
    rows, skipped = [], {}
    for ts, kinds in event_list(events, lo_d, hi_d, today):
        row, why = event_trade(bars, ticker, ts, kinds, pos, arrs)
        if why:
            skipped[why] = skipped.get(why, 0) + 1
        else:
            rows.append(row)
    return rows, skipped


def _pos(v):
    return v is not None and v > 0


def judge(r):
    if r["n"] < MIN_N:
        return "件数不足"
    f, x, p = r["follow"], r["fade"], r["p"]
    if _pos(f["mean"]) and p < ALPHA and _pos(f["early"]) and _pos(f["late"]):
        return "発表のあと、動いた向きに乗る形が残る"
    if f["gross"] is not None and f["gross"] < 0 and p < ALPHA and _pos(x["mean"]) and _pos(x["early"]) and _pos(x["late"]):
        return "発表のあと、逆らう形が残る"
    return "差なし"


def _side(rows, key, dates, mid):
    net = [r[f"{key}_net"] for r in rows]
    lo_, hi_ = boot_ci(net, dates)
    return {"mean": _m(net), "gross": _m(r[f"{key}_gross"] for r in rows), "lo": lo_, "hi": hi_,
            "early": _m(r[f"{key}_net"] for r in rows if r["date"] < mid),
            "late": _m(r[f"{key}_net"] for r in rows if r["date"] >= mid),
            "official": _m(r[f"{key}_official"] for r in rows)}


def stats(rows):
    res = {"n": len(rows)}
    if not rows:
        res["verdict"] = "件数不足"
        return res
    dates = [r["date"] for r in rows]
    ud = sorted(set(dates))
    mid = ud[len(ud) // 2]
    res.update({"n_days": len(ud), "first": ud[0], "last": ud[-1], "split": mid,
                "n_early": sum(1 for d in dates if d < mid), "n_late": sum(1 for d in dates if d >= mid)})
    res["follow"] = _side(rows, "follow", dates, mid)
    res["fade"] = _side(rows, "fade", dates, mid)
    res["p"], res["placebo_mean"] = placebo_p([r["follow_net"] for r in rows], [r["fade_net"] for r in rows])
    res["verdict"] = judge(res)
    # ── 読むための表（判定には使わない）──
    res["cost_median"] = float(np.median([r["cost_r"] for r in rows]))
    res["n_official"] = sum(1 for r in rows if r["follow_official"] is not None)
    by_kind = {}
    for r in rows:
        k = r["kinds"][0] if len(r["kinds"]) == 1 else "重なり"
        by_kind.setdefault(k, []).append(r)
    res["by_kind"] = {k: {"n": len(v), "days": len({r["date"] for r in v}), "follow": _m(r["follow_net"] for r in v),
                          "fade": _m(r["fade_net"] for r in v)} for k, v in by_kind.items()}
    res["by_pair"] = {tk: {"n": len(v), "follow": _m(r["follow_net"] for r in v), "fade": _m(r["fade_net"] for r in v),
                           "gross": _m(r["follow_gross"] for r in v)}
                      for tk in PAIRS for v in [[r for r in rows if r["ticker"] == tk]] if v}
    q1, q2 = np.quantile([r["move_atr"] for r in rows], [1 / 3, 2 / 3])
    terc = {}
    for r in rows:
        k = "小さい" if r["move_atr"] <= q1 else ("中くらい" if r["move_atr"] <= q2 else "大きい")
        terc.setdefault(k, []).append(r)
    res["by_move"] = {k: {"n": len(terc[k]), "follow": _m(r["follow_net"] for r in terc[k]),
                          "fade": _m(r["fade_net"] for r in terc[k])} for k in ("小さい", "中くらい", "大きい") if k in terc}
    res["move_cut"] = [float(q1), float(q2)]
    res["exits_follow"] = {k: sum(1 for r in rows if r["exit_follow"] == k) / len(rows) for k in ("利確", "損切り", "時間切れ")}
    res["long_share"] = sum(1 for r in rows if r["dir"] > 0) / len(rows)
    return res


def render_md(out):
    L = ["# S2 重要な発表のあと、動いた向きに乗るか逆らうかの結果", "",
         f"作成: {out['generated_jst']}（GitHub Actions で計算）。事前登録＝`PILLAR_PREREG.md`「S2 重要な発表のあと」"
         f"（指紋 sha256 `{(out['prereg_sha256'] or '')[:16]}…`）。",
         "値＝1回の取引の損益（R・費用後。1R＝発表前の平均的な値幅×1.5）。**売買の決まりではない**。", "",
         f"判定＝乗る取引（または逆らう取引）の費用後の平均がプラス・前半と後半ともプラス・偽薬（向きだけコイン）との比較 "
         f"p＜{ALPHA:g}（問いが2つ）。取引{MIN_N}件未満は件数不足", ""]
    src = "・".join(f"{EVENT_NAME[k]}＝{v}" for k, v in out["sources"].items())
    L += [f"発表日の取得：{src}", ""]
    if out["missing"]:
        L += [f"⚠️ 取得できなかったペア：{'・'.join(PAIR_NAME[t] for t in out['missing'])}", ""]
    r = out["result"]
    if not r.get("n"):
        L += [f"判定：**{r['verdict']}**（取引0件）", ""]
    else:
        L += [f"判定：**{r['verdict']}**", "",
              f"取引 {r['n']}件・発表日 {r['n_days']}日（{r['first']}〜{r['last']}・前半と後半の境 {r['split']}）", "",
              "| 取引 | 平均R（費用後） | 95%の幅 | 前半 | 後半 | 費用前 |", "|---|---:|---|---:|---:|---:|"]
        for key, name in (("follow", "乗る"), ("fade", "逆らう")):
            s = r[key]
            L.append(f"| {name} | {_f(s['mean'])} | {_f(s['lo'])}〜{_f(s['hi'])} | {_f(s['early'])} | {_f(s['late'])} | {_f(s['gross'])} |")
        L += ["", f"偽薬（向きだけコイン）の平均 {_f(r['placebo_mean'])}・乗る取引との比較 p={r['p']:.4f}", "",
              "## 読むための表（判定には使わない）", "",
              f"- 費用の中央値 {_f(r['cost_median'], sign=False)}R／公式スプレッドで引いた平均＝乗る {_f(r['follow']['official'])}R・"
              f"逆らう {_f(r['fade']['official'])}R（{r['n_official']}件・ユーロ豪ドルとポンド豪ドルは除く）",
              f"- 乗る取引の出口：利確 {r['exits_follow']['利確']:.0%}・損切り {r['exits_follow']['損切り']:.0%}・"
              f"時間切れ {r['exits_follow']['時間切れ']:.0%}／発表の足が上向きだった割合 {r['long_share']:.0%}", "",
              "| 発表の種類 | 取引 | 発表日 | 乗る | 逆らう |", "|---|---:|---:|---:|---:|"]
        L += [f"| {EVENT_NAME.get(k, k)} | {v['n']} | {v['days']} | {_f(v['follow'])} | {_f(v['fade'])} |"
              for k, v in r["by_kind"].items()]
        L += ["", "| ペア | 取引 | 乗る | 逆らう | 乗る（費用前） |", "|---|---:|---:|---:|---:|"]
        L += [f"| {PAIR_NAME[t]} | {v['n']} | {_f(v['follow'])} | {_f(v['fade'])} | {_f(v['gross'])} |"
              for t, v in r["by_pair"].items()]
        L += ["", f"| 発表の足の動き（平均的な値幅の何倍か・境 {r['move_cut'][0]:.2f}／{r['move_cut'][1]:.2f}） | 取引 | 乗る | 逆らう |",
              "|---|---:|---:|---:|"]
        L += [f"| {k} | {v['n']} | {_f(v['follow'])} | {_f(v['fade'])} |" for k, v in r["by_move"].items()]
        L.append("")
    if out["skipped"]:
        L += ["数えなかった発表（ペアごと）：" + "・".join(f"{k} {v}" for k, v in sorted(out["skipped"].items())), ""]
    L += ["---", "", "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def main():
    today = dt.datetime.now(JST).date()
    events, sources = load_events()
    rows, missing, skipped = [], [], {}
    for tk in PAIRS:
        bars = fetch(tk, "1h")
        if bars is None:
            missing.append(tk)
            continue
        got, sk = trades_for(bars, tk, events, today)
        rows += got
        for k, v in sk.items():
            skipped[f"{PAIR_NAME[tk]}:{k}"] = v
        print(f"{tk}: 取引 {len(got)}", file=sys.stderr)
    out = {"generated_jst": dt.datetime.now(JST).strftime("%Y-%m-%dT%H:%M+09:00"),
           "prereg_sha256": prereg_sha256(), "sources": sources,
           "event_counts": {k: len(v) for k, v in events.items()},
           "missing": missing, "skipped": skipped, "cost_pips": COST_PIPS, "cost_mult": COST_MULT,
           "result": stats(rows)}
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(render_md(out))
    print(f"wrote {OUT_JSON} / {OUT_MD}", file=sys.stderr)
    return 0 if events and len(missing) < len(PAIRS) else 1


if __name__ == "__main__":
    sys.exit(main())
