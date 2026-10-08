# -*- coding: utf-8 -*-
"""XC X の読むための表から出た候補を、X が使っていない昔の期間（2004〜2011年）で確かめる。2026-10-08 登録。

物差しと判定は PILLAR_PREREG.md「XC」に固定（計算より先にコミット）。決まりは X（fx_clock_lab.py）と同じ関数を使う。
- XC1 ECB の値決めの前、ユーロドルだけ売る（ロンドン 11:00→13:00）
- XC2 大きな月曜の窓（直近20日の1日の値幅の0.5以上）を埋める向き（12ペア）
- XC3 FOMC の日のドル売り（ドルのペア7つ・ロンドン 08:00→ニューヨーク 16:00）
費用は2段＝個人（円 1.2・ほか 1.8pips）と低い費用（円 0.6・ほか 0.8pips）。どちらもその時間の実際の差と大きいほう。

使い方:  python fx_confirm_lab.py --check   （点検だけ・損益は出さない）
         python fx_confirm_lab.py           （1回だけ数えて fx-confirm-lab.json / .md を書く）
"""
import argparse
import datetime as dt
import json
import os
import re
import sys

import numpy as np

import fx_bars as FB
import fx_clock_lab as X

START, END = "2004-01-05", "2011-12-30"
HALF = "2008-01-01"
PERIOD = ((2004, 1), (2011, 12))
LOW_PIPS = {"JPY": 0.6, "other": 0.8}
GAP_MIN = 0.5
N_BOOT, ALPHA, SEED = 10000, 0.05 / 3, 20261013
MIN_N = {"XC1": 500, "XC2": 60, "XC3": 50}
MISSING_MAX = 0.05
VERDICTS = ("◎ 昔の期間でも個人の費用のあとプラス", "◯ 低い費用ならプラス", "△ 癖は本物だが費用で消える", "差なし", "件数不足")
TITLE = {"XC1": "ECB の値決めの前、ユーロドルだけ売る（ロンドン 11:00→13:00・2004〜2011年）",
         "XC2": "大きな月曜の窓（直近20日の1日の値幅の0.5以上）を埋める向き（12ペア・2004〜2011年）",
         "XC3": "FOMC の日のドル売り（ロンドン 08:00→ニューヨーク 16:00・ドルのペア7つ・2004〜2011年）"}
OUT_JSON, OUT_MD = "fx-confirm-lab.json", "fx-confirm-lab.md"


def low_cost(pair):
    return LOW_PIPS["JPY" if pair.endswith("JPY") else "other"] * X.pip(pair)


# ════════════════════ FOMC の日（昔のページの形も読む） ════════════════════

STMT = re.compile(r'monetary/?(?:\d{4}/)?(\d{8})(?:[a-z]?\.htm|/)')


def parse_fomc_any(html):
    """年ごとの過去のページ（2004年＝/boarddocs/press/monetary/<年>/<日付>/・2005〜2011年＝press/monetary/<日付>a.htm・
    2012年から＝monetary<日付>a.htm）：見出し「… Meeting - 年」の欄の声明の日。臨時・取りやめ・持ち回り・電話会議は除く"""
    out = set()
    for block in re.split(r'<h5', html)[1:]:
        head = re.search(r'>([^<]*)</h5>', block)
        if not head:
            continue
        h = head.group(1).lower()
        if "meeting" not in h or any(w in h for w in ("unscheduled", "cancel", "notation", "conference call")):
            continue
        s = STMT.search(block)
        if s:
            out.add(dt.datetime.strptime(s.group(1), "%Y%m%d").date())
    return sorted(out)


def fomc_dates(opener=None):
    dates, status = set(), {}
    for y in range(int(START[:4]), int(END[:4]) + 1):
        try:
            got = parse_fomc_any(X.http_get(X.FOMC_HIST.format(y=y), opener))
        except Exception as e:  # noqa: BLE001
            status[str(y)] = f"取得できず: {type(e).__name__}"
            continue
        if not got:
            status[str(y)] = "解析0件"
            continue
        status[str(y)] = f"{len(got)}件"
        dates |= set(got)
    return sorted(dates), status


# ════════════════════ 取引 ════════════════════

def window_rows(kind, bars, days, pairs):
    """XC1・XC3：日ごとの（費用前・個人の費用後・低い費用後）。pairs＝{ペア: 損益の向き}。
    ペアが1つ（XC1）ならそのペアがある日、複数（XC3）なら X と同じく5つ以上そろった日だけ"""
    t_in, t_out = X.fix_windows(kind, days)
    G, NR, NL, per = [], [], [], {}
    for p, sign in pairs.items():
        d = bars.get(p)
        if d is None or d.empty:
            continue
        e, x = d.reindex(t_in), d.reindex(t_out)
        mo, mc = e["mo"].to_numpy(), x["mc"].to_numpy()
        actual = (e["so"].to_numpy() + x["sc"].to_numpy()) / 2
        g = sign * (mc / mo - 1) * 1e4
        nr = g - np.maximum(X.fixed_cost(p), actual) / mo * 1e4
        nl = g - np.maximum(low_cost(p), actual) / mo * 1e4
        G.append(g), NR.append(nr), NL.append(nl)
        per[p] = (g, nr)
    rows = []
    if not G:
        return rows, {}
    G, NR, NL = np.array(G), np.array(NR), np.array(NL)
    need = 1 if len(pairs) == 1 else X.MIN_PAIRS
    ok = (~np.isnan(NR)).sum(0)
    for i, d in enumerate(days):
        if ok[i] < need:
            continue
        rows.append({"date": d.isoformat(), "gross": float(np.nanmean(G[:, i])), "net": float(np.nanmean(NR[:, i])),
                     "net_low": float(np.nanmean(NL[:, i])), "n_pairs": int(ok[i])})
    return rows, {p: {"n": int((~np.isnan(n)).sum()), "gross": X._nm(g), "net": X._nm(n)} for p, (g, n) in per.items()}


def gap_trades_low(bars):
    """XC2：X1 と同じ取引（窓 0.5 以上・入る前に埋まった週は入らない）に、低い費用の損益を足す"""
    out = []
    for p, d in bars.items():
        for t in X.gap_trades(d, p, gap_min=GAP_MIN):
            if not t["traded"]:
                continue
            t["net_low"] = t["gross"] - max(low_cost(p) / t["entry"] * 1e4, t["actual"])
            out.append(t)
    return out


def week_rows(trades):
    by = {}
    for t in trades:
        by.setdefault(t["week"], []).append(t)
    return [{"date": w, "gross": float(np.mean([x["gross"] for x in v])), "net": float(np.mean([x["net"] for x in v])),
             "net_low": float(np.mean([x["net_low"] for x in v])), "n_pairs": len(v)} for w, v in sorted(by.items())]


# ════════════════════ 物差しと判定 ════════════════════

def stats(rows, kind):
    n = len(rows)
    if n < MIN_N[kind]:
        return {"n": n, "verdict": VERDICTS[4]}
    dates = np.array([r["date"] for r in rows])
    st = {"n": n, "n_first": int((dates < HALF).sum()), "n_second": int((dates >= HALF).sum())}
    for key, col, seed in (("gross", "gross", SEED), ("net", "net", SEED + 1), ("low", "net_low", SEED + 2)):
        v = np.array([r[col] for r in rows])
        lo, hi = X.boot_ci(v, n_boot=N_BOOT, alpha=ALPHA, seed=seed)
        st[key] = {"mean": float(v.mean()), "lo": lo, "hi": hi,
                   "first": float(v[dates < HALF].mean()) if (dates < HALF).any() else None,
                   "second": float(v[dates >= HALF].mean()) if (dates >= HALF).any() else None}
    st["verdict"] = judge(st)
    return st


def _ok(s):
    return s["lo"] > 0 and (s["first"] or 0) > 0 and (s["second"] or 0) > 0


def judge(st):
    if "gross" not in st:
        return VERDICTS[4]
    if _ok(st["net"]):
        return VERDICTS[0]
    if _ok(st["low"]):
        return VERDICTS[1]
    if _ok(st["gross"]):
        return VERDICTS[2]
    return VERDICTS[3]


# ════════════════════ 点検・本番 ════════════════════

def load_all(root=None):
    bars, dropped = {}, {}
    for p in FB.PAIRS:
        d, n_bad = X.prep(FB.load(p, root=root, start=PERIOD[0], end=PERIOD[1]), p, START, END)
        bars[p], dropped[p] = d, n_bad
    return bars, dropped


def coverage(root=None):
    cov = FB.coverage(root, start=PERIOD[0], end=PERIOD[1])
    want = sum(v["want"] for v in cov.values())
    have = sum(v["have"] for v in cov.values())
    return (1 - have / want) if want else 1.0, cov


def check(root=None):
    """点検だけ（損益は出さない）"""
    miss, cov = coverage(root)
    print(f"置き場：{FB.info(root)}", flush=True)
    print(f"昔の期間（{PERIOD[0][0]}〜{PERIOD[1][0]}）で欠けている月の割合 {miss:.1%}（上限 {MISSING_MAX:.0%}）", flush=True)
    bars, dropped = load_all(root)
    print("| ペア | 足の数 | 最初 | 最後 | 差がおかしく落とした足 | 終値の中値の範囲 | 差の中央値（pips） |\n|---|---|---|---|---|---|---|")
    for p, d in bars.items():
        if d.empty:
            print(f"| {p} | 0 | — | — | {dropped[p]} | — | — |")
            continue
        print(f"| {p} | {len(d)} | {d.index[0]:%Y-%m-%d} | {d.index[-1]:%Y-%m-%d} | {dropped[p]} | "
              f"{d['mc'].min():.5g}〜{d['mc'].max():.5g} | {(d['so'] / X.pip(p)).median():.2f} |")
    fomc, status = fomc_dates()
    print(f"FOMC の定例会合の声明の日：{len(fomc)}件・{status}", flush=True)
    ok = miss <= MISSING_MAX and not bars["EURUSD"].empty
    print("数えられる" if ok else "数えない（置き場を取り直す）", flush=True)
    return 0 if ok else 1


def run(root=None, today=None):
    miss, _ = coverage(root)
    if miss > MISSING_MAX:
        print(f"欠けている月の割合 {miss:.1%} が上限を超えた＝数えない", flush=True)
        return None
    bars, dropped = load_all(root)
    fomc, fomc_status = fomc_dates()
    res, rows = {}, {}
    rows["XC1"], pairs1 = window_rows("X3", bars, X.days_for("X3", None, START, END), {"EURUSD": -1})
    trades = gap_trades_low(bars)
    rows["XC2"] = week_rows(trades)
    usd_sell = {p: -s for p, s in X.USD_BUY.items()}
    rows["XC3"], pairs3 = window_rows("X5", bars, X.days_for("X5", fomc, START, END), usd_sell)
    for k in ("XC1", "XC2", "XC3"):
        res[k] = stats(rows[k], k)
        res[k]["title"] = TITLE[k]
        res[k]["by_year"] = X.by_year(rows[k])
    res["XC1"]["pairs"] = pairs1
    res["XC3"]["pairs"] = pairs3
    res["XC2"]["pairs"] = {p: X._x1_sub([t for t in trades if t["pair"] == p]) for p in FB.PAIRS}
    res["XC2"]["filled_share"] = float(np.mean([t["filled"] for t in trades])) if trades else None
    res["XC2"]["n_trades"] = len(trades)
    basket, _ = window_rows("X3", bars, X.days_for("X3", None, START, END), dict(X.USD_BUY))
    res["XC1"]["basket_gross"] = X._nm([r["gross"] for r in basket])
    res["XC1"]["basket_n"] = len(basket)
    now = today or dt.datetime.now(X.JST)
    return {"generated": now.isoformat(timespec="minutes"), "prereg_sha256": X.prereg_sha(), "kind": "backtest", "section": "XC",
            "store": FB.info(root), "period": [START, END], "dropped_bars": dropped, "fomc_status": fomc_status, "n_fomc": len(fomc),
            "titles": dict(TITLE), "verdicts": list_verdicts(res, now.date().isoformat()), "results": res}


def list_verdicts(res, day):
    """検証済みリストに載せる形（△・差なし＝ストップ）。値は個人の費用後の損益率（bp÷10000）"""
    out = {}
    for k, r in res.items():
        if r.get("verdict") not in (VERDICTS[2], VERDICTS[3]):
            continue
        n = r["net"]
        why = "癖は本物だが個人の費用でも低い費用でも消える" if r["verdict"] == VERDICTS[2] else "差なし"
        out[k] = {"status": "stop", "decided_on": day, "n": r["n"], "mean": n["mean"] / 1e4, "lo": n["lo"] / 1e4, "hi": n["hi"] / 1e4,
                  "reason": f"X が使っていない昔の期間（2004〜2011年・Dukascopy の1時間足）で1回だけ数えて{why}（98.33%の幅・前半後半）"}
    return out


def _f(x, nd=2):
    return "—" if x is None else f"{x:+.{nd}f}"


def render_md(out):
    R = out["results"]
    L = ["# XC X の候補を昔の期間（2004〜2011年）で確かめる", "",
         f"- 生成: {out['generated']}　事前登録の指紋（PILLAR_PREREG.md の sha256）: `{out['prereg_sha256']}`",
         f"- 物差しと判定＝PILLAR_PREREG.md「XC」（計算より先にコミット）。期間 {out['period'][0]}〜{out['period'][1]}・**1回だけ数えた結果**",
         f"- 値段＝為替の値段の置き場（Dukascopy の1時間足・売値と買値）：{out['store']}",
         "- 単位＝ベーシスポイント（0.01%）。費用は2段＝個人（円 1.2・ほか 1.8pips）／低い費用（円 0.6・ほか 0.8pips）、どちらもその時間の実際の差と大きいほう。**売買の決まりではない**",
         "- 判定＝98.33%の幅（問いが3つ＝0.05÷3）がまるごと0より上・前半（2004〜2007）と後半（2008〜2011）ともプラス。◎ 個人の費用後／◯ 低い費用後／△ 費用の前だけ", "",
         "## 判定の一覧", "",
         "| 問い | 判定 | 回数 | 費用前（幅） | 個人の費用後（幅） | 低い費用後（幅） | 前半／後半（個人の費用後） |",
         "|---|---|---|---|---|---|---|"]
    for k in ("XC1", "XC2", "XC3"):
        r = R[k]
        if r["verdict"] == VERDICTS[4]:
            L.append(f"| {k} {r['title']} | {r['verdict']} | {r['n']} | — | — | — | — |")
            continue
        c = {key: f"{_f(r[key]['mean'])}（{_f(r[key]['lo'])}〜{_f(r[key]['hi'])}）" for key in ("gross", "net", "low")}
        L.append(f"| {k} {r['title']} | {r['verdict']} | {r['n']} | {c['gross']} | {c['net']} | {c['low']} | "
                 f"{_f(r['net']['first'])}／{_f(r['net']['second'])} |")
    L += ["", "## 読むための表（判定には使わない）", ""]
    for k in ("XC1", "XC2", "XC3"):
        r = R[k]
        L += [f"### {k} {r['title']}", ""]
        if r.get("by_year"):
            L.append("- 年ごとの個人の費用後の平均：" + "・".join(f"{y} {_f(v['net'])}（{v['n']}）" for y, v in r["by_year"].items()))
        if k == "XC1" and r.get("basket_gross") is not None:
            L.append(f"- X3 と同じドルのペア7つのかご（費用前）：{_f(r['basket_gross'])}（{r['basket_n']}日）")
        if k == "XC2":
            fs = r.get("filled_share")
            L.append(f"- 取引 {r.get('n_trades')}回・金曜の終値まで戻った割合 {'—' if fs is None else f'{fs:.0%}'}")
        if r.get("pairs"):
            L.append("- ペアごと（費用前／個人の費用後・回数）：" + "・".join(f"{p} {_f(v.get('gross'))}／{_f(v.get('net'))}（{v['n']}）"
                                                               for p, v in r["pairs"].items() if v.get("n")))
        L.append("")
    L += [f"- FOMC の日：{out['n_fomc']}件・{out['fomc_status']}", "",
          "## 読み方の約束と限界", "",
          "- ◎ なら MT5 のデモで前向きを別に登録してから始める。◯ なら手元の MT5 で実際の往復の費用を測る（低い費用以下の口座なら前向きを登録）。△・差なしは検証済みリストへ",
          "- 2004〜2007年の Dukascopy の売り買いの差は今より広い（実際の差を使うので費用は重めに出る）・XC1 と XC2 は X の表を見てから選んだ・スワップは入れない",
          "- 過去の成績は将来を約束しない。情報提供であり投資助言ではない"]
    return "\n".join(L) + "\n"


def write(out):
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, default=str)
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(render_md(out))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--root", default=None)
    a = ap.parse_args(argv)
    if a.check:
        return check(a.root)
    if os.path.exists(OUT_JSON):
        print(f"{OUT_JSON} がすでにある＝1回だけ数える決まりなので数えない", flush=True)
        return 1
    out = run(a.root)
    if out is None:
        return 1
    write(out)
    print(render_md(out), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
