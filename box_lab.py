# -*- coding: utf-8 -*-
"""S1 時間帯の箱の抜け（東京の値幅を、ロンドン・NY の始まりで抜ける）。2026-09-27 夜登録・オーナー「登録して先に数えてください」。

出どころ＝FX スキャルピング本の整理（手元の非公開メモ）。問いは1つ・窓は2つ・1回だけ数える。
⚠️ 物差しと判定の基準は PILLAR_PREREG.md「S1 時間帯の箱の抜け」（事前登録・計算より先にコミット済み）と下の定数に固定。
   結果を見てから動かさない。出力には事前登録の中身の指紋（sha256）を書き込む。
⚠️ 出力 box-lab.json / box-lab.md は GitHub 側で生成＝手元から送らない（SYNC禁忌）。
⚠️ エンジン・発火条件・固定オラクル（signal_lab_verify.py）には触れない。メールや売買の決まりは変えない。

実行: python box_lab.py   （Actions の box-lab.yml から手動で）
"""
import datetime as dt
import json
import sys
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from pillar_lab import fetch, prereg_sha256

UTC = ZoneInfo("UTC")
LON = ZoneInfo("Europe/London")
NY = ZoneInfo("America/New_York")
JST = ZoneInfo("Asia/Tokyo")
OUT_JSON, OUT_MD = "box-lab.json", "box-lab.md"
SEED = 20260927
N_PERM = 2000          # 偽薬の回数
N_BOOT = 2000          # 幅（日ごとのまとまり）の回数
MIN_N = 300            # 窓ごと・これ未満は「件数不足」
ALPHA = 0.05 / 2       # 窓が2つなので厳しくする

PAIRS = ["USDJPY=X", "EURJPY=X", "GBPJPY=X", "AUDJPY=X", "EURUSD=X", "GBPUSD=X", "AUDUSD=X", "EURAUD=X", "GBPAUD=X"]
PAIR_NAME = {"USDJPY=X": "ドル円", "EURJPY=X": "ユーロ円", "GBPJPY=X": "ポンド円", "AUDJPY=X": "豪ドル円",
             "EURUSD=X": "ユーロドル", "GBPUSD=X": "ポンドドル", "AUDUSD=X": "豪ドル米ドル",
             "EURAUD=X": "ユーロ豪ドル", "GBPAUD=X": "ポンド豪ドル"}

BOX_HOURS = range(0, 7)          # ロンドン時間 00:00〜06:00 に始まる7本（東京時間）
BOX_MIN_BARS = 6                 # 箱の足が6本未満の日は数えない
WINDOWS = {
    "L": {"name": "ロンドンの始まり", "tz": LON, "hours": range(7, 12), "exit_hour": 16},   # 07:00〜11:00 に始まる足
    "N": {"name": "NY の始まり", "tz": NY, "hours": range(8, 11), "exit_hour": 16},        # 08:00〜10:00 に始まる足
}

# 費用＝15分足の時間帯の実測と同じ約束（research/_fx_session_15m_scan.py の COST と同じ）：円のペア 0.8pips・ほか 1.2pips × 滑りの係数 1.5（往復）
COST_PIPS = {"JPY": 0.8, "other": 1.2}
COST_MULT = 1.5
# 読むための表＝公式の原則固定スプレッド（外為どっとコム「スプレッドと取引手数料」2026-09-27 閲覧・午前9時〜翌3時）。無いペアは出さない
OFFICIAL_SPREAD_PIPS = {"USDJPY=X": 0.2, "EURJPY=X": 0.4, "EURUSD=X": 0.3, "AUDJPY=X": 0.5,
                        "GBPJPY=X": 0.9, "GBPUSD=X": 1.0, "AUDUSD=X": 0.4}
EVENTS = "economic-events.json"


def pip_size(ticker):
    return 0.01 if ticker.endswith("JPY=X") else 0.0001


def cost_price(ticker):
    return COST_PIPS["JPY" if ticker.endswith("JPY=X") else "other"] * COST_MULT * pip_size(ticker)


def local_ts(day, hour, tz):
    """現地の日付・時刻（毎正時）→ UTC の足の始まり。夏時間は zoneinfo に任せる"""
    return pd.Timestamp(dt.datetime(day.year, day.month, day.day, hour, tzinfo=tz)).tz_convert("UTC")


def simulate(o, h, lo, c, start, stop, entry, direction, risk, width, exit_px):
    """start の足の始値で入り、stop の足の手前まで見て、決まらなければ exit_px で時間切れ。
    損切り＝risk・利確＝width（入った値から）。同じ足で両方に触れたら損切りが先。
    足の始値がすでに先にあるときは始値で手じまう。戻り値＝(R, 出口の種類)"""
    sl = entry - direction * risk
    tp = entry + direction * width
    for i in range(start, stop):
        if i > start:   # 入った足の始値＝entry。次の足からは始値で飛び越えを先に見る
            if direction * (o[i] - sl) <= 0:
                return direction * (o[i] - entry) / risk, "損切り"
            if direction * (o[i] - tp) >= 0:
                return direction * (o[i] - entry) / risk, "利確"
        hit_sl = (lo[i] <= sl) if direction > 0 else (h[i] >= sl)
        hit_tp = (h[i] >= tp) if direction > 0 else (lo[i] <= tp)
        if hit_sl:
            return -1.0, "損切り"
        if hit_tp:
            return width / risk, "利確"
    return direction * (exit_px - entry) / risk, "時間切れ"


def day_trades(bars, ticker, day, pos, arrs=None):
    """その日（ロンドンの日付）の窓L・窓N の取引。pos＝UTC の足の始まり→行番号。arrs＝(始値, 高値, 安値, 終値)の配列"""
    o, h, lo, c = arrs or tuple(bars[k].to_numpy(float) for k in ("Open", "High", "Low", "Close"))
    box_idx = [pos[t] for t in (local_ts(day, hr, LON) for hr in BOX_HOURS) if t in pos]
    if len(box_idx) < BOX_MIN_BARS:
        return [], "箱の足が足りない"
    out = []
    for key, w in WINDOWS.items():
        wd = day   # 窓の現地の日付＝ロンドンの日付と同じ（NY 08:00 はロンドン 13:00。夏時間の切り替えの週は 12:00）
        if key == "L":
            hi, lw = float(h[box_idx].max()), float(lo[box_idx].min())
        else:   # 箱＝ロンドン 00:00 から NY 08:00 の直前の足まで（東京とロンドンの値幅）
            a, b = local_ts(day, 0, LON), local_ts(wd, 8, NY)
            i0, i1 = int(bars.index.searchsorted(a)), int(bars.index.searchsorted(b))
            if i1 <= i0:
                continue
            hi, lw = float(h[i0:i1].max()), float(lo[i0:i1].min())
        width = hi - lw
        if width <= 0:
            continue
        sig, direction = None, 0
        for hr in w["hours"]:
            t = local_ts(wd, hr, w["tz"])
            if t not in pos:
                continue
            i = pos[t]
            if c[i] > hi:
                sig, direction = i, 1
                break
            if c[i] < lw:
                sig, direction = i, -1
                break
        if sig is None:
            continue
        t_entry = bars.index[sig] + pd.Timedelta(hours=1)
        if t_entry not in pos:
            continue
        e = pos[t_entry]
        entry = float(o[e])
        t_exit = local_ts(wd, w["exit_hour"], w["tz"])
        stop = int(bars.index.searchsorted(t_exit))
        if stop <= e:
            continue
        # 時間切れ＝現地16時の足の始値。その足が無い（欠け・週末）ときは、その手前の最後の足の終値
        if stop < len(o) and bars.index[stop] - t_exit < pd.Timedelta(hours=1):
            exit_px = float(o[stop])
        else:
            exit_px = float(c[stop - 1])
        risk = direction * (entry - (lw if direction > 0 else hi))
        if risk <= 0:
            continue
        r, kind = simulate(o, h, lo, c, e, stop, entry, direction, risk, width, exit_px)
        r_mirror, _ = simulate(o, h, lo, c, e, stop, entry, -direction, risk, width, exit_px)
        cost_r = cost_price(ticker) / risk
        off = OFFICIAL_SPREAD_PIPS.get(ticker)
        out.append({"window": key, "ticker": ticker, "date": day.isoformat(), "weekday": day.weekday(),
                    "dir": direction, "gross": r, "net": r - cost_r, "mirror_net": r_mirror - cost_r,
                    "cost_r": cost_r, "net_official": (r - off * pip_size(ticker) / risk) if off is not None else None,
                    "exit": kind, "width_pips": width / pip_size(ticker),
                    "entry_utc": bars.index[e].isoformat()})
    return out, None


def trades_for(bars, ticker):
    pos = {t: i for i, t in enumerate(bars.index)}
    arrs = tuple(bars[k].to_numpy(float) for k in ("Open", "High", "Low", "Close"))
    days = sorted({t.tz_convert(LON).date() for t in bars.index})
    rows, skipped = [], {}
    for d in days:
        if d.weekday() >= 5:
            continue
        got, why = day_trades(bars, ticker, d, pos, arrs)
        if why:
            skipped[why] = skipped.get(why, 0) + 1
        rows += got
    return rows, skipped


def boot_ci(vals, days, n_boot=N_BOOT, seed=SEED):
    """日ごとのまとまりで日を引き直す（2,000回）→ 平均の2.5%・97.5%点"""
    vals = np.asarray(vals, float)
    uniq, inv = np.unique(np.asarray(days), return_inverse=True)
    s = np.bincount(inv, weights=vals, minlength=len(uniq))
    n = np.bincount(inv, minlength=len(uniq)).astype(float)
    rng = np.random.default_rng(seed)
    pick = rng.integers(0, len(uniq), size=(n_boot, len(uniq)))
    means = s[pick].sum(1) / n[pick].sum(1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def placebo_p(real, mirror, n_perm=N_PERM, seed=SEED):
    """偽薬＝同じ取引で向きだけコインで決める（2,000回・両側）。戻り値＝(p, 偽薬の平均の平均)"""
    real, mirror = np.asarray(real, float), np.asarray(mirror, float)
    rng = np.random.default_rng(seed + 1)
    flip = rng.integers(0, 2, size=(n_perm, len(real))).astype(bool)
    means = np.where(flip, mirror, real).mean(1)
    obs = real.mean()
    ge = (np.sum(means >= obs - 1e-12) + 1) / (n_perm + 1)
    le = (np.sum(means <= obs + 1e-12) + 1) / (n_perm + 1)
    return float(min(1.0, 2 * min(ge, le))), float(means.mean())


def judge(r):
    if r["n"] < MIN_N:
        return "件数不足"
    lo, hi, e, l, p = r["lo"], r["hi"], r["early"], r["late"], r["p"]
    if lo > 0 and e > 0 and l > 0 and p < ALPHA:
        return "過去2年では残る"
    if hi < 0 and e < 0 and l < 0 and p < ALPHA:
        return "逆に効く（だましが多い）"
    return "差なし"


def _m(xs):
    xs = [x for x in xs if x is not None]
    return float(np.mean(xs)) if xs else None


def event_days(path=EVENTS):
    """重要な指標のある日（休場を除く・impact が high/critical）。ファイルは2026年から＝それより前は数えない"""
    try:
        ev = json.load(open(path, encoding="utf-8"))["events"]
    except (OSError, ValueError, KeyError):
        return set(), None
    days = set()
    for e in ev:
        if e.get("category") == "market_holiday" or e.get("impact") not in ("high", "critical"):
            continue
        try:
            days.add(pd.Timestamp(e["datetime"]).tz_convert(LON).date().isoformat())
        except (KeyError, ValueError):
            continue
    return days, (min(days) if days else None)


def window_stats(rows, ev_days, ev_from):
    res = {"n": len(rows)}
    if not rows:
        res["verdict"] = "件数不足"
        return res
    net = [r["net"] for r in rows]
    dates = [r["date"] for r in rows]
    res["mean"] = float(np.mean(net))
    res["lo"], res["hi"] = boot_ci(net, dates)
    ud = sorted(set(dates))
    mid = ud[len(ud) // 2]
    early = [r["net"] for r in rows if r["date"] < mid]
    late = [r["net"] for r in rows if r["date"] >= mid]
    res.update({"split": mid, "early": _m(early), "late": _m(late), "n_early": len(early), "n_late": len(late),
                "first": ud[0], "last": ud[-1]})
    res["p"], res["placebo_mean"] = placebo_p(net, [r["mirror_net"] for r in rows])
    res["verdict"] = judge(res)
    # ── 読むための表（判定には使わない）──
    res["gross"] = _m(r["gross"] for r in rows)
    res["cost_median"] = float(np.median([r["cost_r"] for r in rows]))
    off = [r for r in rows if r["net_official"] is not None]
    res["net_official"] = {"n": len(off), "mean": _m(r["net_official"] for r in off)}
    res["by_pair"] = {tk: {"n": len(v), "mean": _m(v), "gross": _m(g)} for tk in PAIRS
                      for v, g in [([r["net"] for r in rows if r["ticker"] == tk],
                                    [r["gross"] for r in rows if r["ticker"] == tk])] if v}
    terc = {}
    for tk in PAIRS:
        sub = [r for r in rows if r["ticker"] == tk]
        if len(sub) < 3:
            continue
        q1, q2 = np.quantile([r["width_pips"] for r in sub], [1 / 3, 2 / 3])
        for r in sub:
            k = "狭い" if r["width_pips"] <= q1 else ("中くらい" if r["width_pips"] <= q2 else "広い")
            terc.setdefault(k, []).append(r["net"])
    res["by_width"] = {k: {"n": len(terc[k]), "mean": _m(terc[k])} for k in ("狭い", "中くらい", "広い") if k in terc}
    wd = "月火水木金"
    res["by_weekday"] = {wd[i]: {"n": len(v), "mean": _m(v)} for i in range(5)
                         for v in [[r["net"] for r in rows if r["weekday"] == i]] if v}
    if ev_from:
        cov = [r for r in rows if r["date"] >= ev_from]
        yes = [r["net"] for r in cov if r["date"] in ev_days]
        no = [r["net"] for r in cov if r["date"] not in ev_days]
        res["by_event"] = {"from": ev_from, "ある日": {"n": len(yes), "mean": _m(yes)},
                           "ない日": {"n": len(no), "mean": _m(no)}}
    res["exits"] = {k: sum(1 for r in rows if r["exit"] == k) / len(rows) for k in ("利確", "損切り", "時間切れ")}
    res["long_share"] = sum(1 for r in rows if r["dir"] > 0) / len(rows)
    return res


def _f(x, nd=3, sign=True):
    if x is None:
        return "—"
    return f"{x:+.{nd}f}" if sign else f"{x:.{nd}f}"


def render_md(out):
    L = ["# S1 時間帯の箱の抜けの結果", "",
         f"作成: {out['generated_jst']}（GitHub Actions で計算）。事前登録＝`PILLAR_PREREG.md`「S1 時間帯の箱の抜け」"
         f"（指紋 sha256 `{(out['prereg_sha256'] or '')[:16]}…`）。",
         "値＝1回の取引の損益（R・費用後。1R＝入った値から損切り＝箱の反対側の端まで）。**売買の決まりではない**。", "",
         f"判定＝費用後の平均Rの95%の幅がまるごと0より上・前半と後半ともプラス・偽薬（向きだけコイン）との比較 p＜{ALPHA:g}（窓が2つ）。件数{MIN_N}未満は件数不足", ""]
    if out["missing"]:
        L += [f"⚠️ 取得できなかったペア：{'・'.join(PAIR_NAME[t] for t in out['missing'])}", ""]
    L += ["| 窓 | 件数 | 平均R | 95%の幅 | 前半 | 後半 | 偽薬の平均 | 偽薬との比較 p | 判定 |",
          "|---|---:|---:|---|---:|---:|---:|---:|---|"]
    for k, w in WINDOWS.items():
        r = out["windows"][k]
        if r["n"] == 0:
            L.append(f"| {w['name']} | 0 | — | — | — | — | — | — | {r['verdict']} |")
            continue
        L.append(f"| {w['name']} | {r['n']} | {_f(r['mean'])} | {_f(r['lo'])}〜{_f(r['hi'])} | {_f(r['early'])} | "
                 f"{_f(r['late'])} | {_f(r['placebo_mean'])} | {r['p']:.4f} | {r['verdict']} |")
    L += ["", "## 読むための表（判定には使わない）", ""]
    for k, w in WINDOWS.items():
        r = out["windows"][k]
        if not r.get("n"):
            continue
        L += [f"### {w['name']}（{r['first']}〜{r['last']}・前半と後半の境 {r['split']}）", "",
              f"- 費用前の平均 {_f(r['gross'])}R／費用の中央値 {_f(r['cost_median'], sign=False)}R／"
              f"公式スプレッドで引いた平均 {_f(r['net_official']['mean'])}R（{r['net_official']['n']}件・ユーロ豪ドルとポンド豪ドルは除く）",
              f"- 出口の割合：利確 {r['exits']['利確']:.0%}・損切り {r['exits']['損切り']:.0%}・時間切れ {r['exits']['時間切れ']:.0%}／買いの割合 {r['long_share']:.0%}", "",
              "| ペア | 件数 | 平均R | 費用前 |", "|---|---:|---:|---:|"]
        L += [f"| {PAIR_NAME[t]} | {v['n']} | {_f(v['mean'])} | {_f(v['gross'])} |" for t, v in r["by_pair"].items()]
        L += ["", "| 箱の幅（ペアごとの3つの区分） | 件数 | 平均R |", "|---|---:|---:|"]
        L += [f"| {k2} | {v['n']} | {_f(v['mean'])} |" for k2, v in r["by_width"].items()]
        L += ["", "| 曜日 | 件数 | 平均R |", "|---|---:|---:|"]
        L += [f"| {k2} | {v['n']} | {_f(v['mean'])} |" for k2, v in r["by_weekday"].items()]
        if r.get("by_event"):
            be = r["by_event"]
            L += ["", f"- 重要な指標のある日 {be['ある日']['n']}件 平均 {_f(be['ある日']['mean'])}／ない日 "
                      f"{be['ない日']['n']}件 平均 {_f(be['ない日']['mean'])}（`economic-events.json` が {be['from']} からなので、それ以降だけ）"]
        L.append("")
    L += ["---", "", "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def main():
    rows, missing, skipped = [], [], {}
    for tk in PAIRS:
        bars = fetch(tk, "1h")
        if bars is None:
            missing.append(tk)
            continue
        got, sk = trades_for(bars, tk)
        rows += got
        for k, v in sk.items():
            skipped[f"{PAIR_NAME[tk]}:{k}"] = v
        print(f"{tk}: 取引 {len(got)}", file=sys.stderr)
    ev_days, ev_from = event_days()
    out = {"generated_jst": dt.datetime.now(JST).strftime("%Y-%m-%dT%H:%M+09:00"),
           "prereg_sha256": prereg_sha256(), "missing": missing, "skipped": skipped,
           "windows": {k: window_stats([r for r in rows if r["window"] == k], ev_days, ev_from) for k in WINDOWS}}
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(render_md(out))
    print(f"wrote {OUT_JSON} / {OUT_MD}", file=sys.stderr)
    return 0 if len(missing) < len(PAIRS) else 1


if __name__ == "__main__":
    sys.exit(main())
