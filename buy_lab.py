# -*- coding: utf-8 -*-
"""R2 余剰資金の入れ方：一括で入れるのと、毎月に分けるのと、下がったときに買い増すのでは、10年後にどれだけ違うか。
2026-10-05 登録・オーナー「ニーサは50%程度の下落なら耐えて買い増しする準備がある。そのためのシステムトレードの研究を進めたい」。

⚠️ 物差しと判定の基準は PILLAR_PREREG.md「R2 余剰資金の入れ方」（事前登録・計算より先にコミット）と下の定数に固定。
   結果を見てから動かさない。出力には事前登録の中身の指紋（sha256）を書き込む。
⚠️ データは R1 と同じ（hold_lab.load_prices＝追記の直し方①〜③を当てた円建ての日足・2026-10-02 まで）。
⚠️ 税なし・買うだけ（非課税口座で使える形）。最初の資金＝1（金額は書かない）。現金の利息0・買う費用0。
⚠️ 出力 buy-lab.json / .md は GitHub 側で生成＝手元から送らない（SYNC禁忌）。
⚠️ エンジン・発火条件・固定オラクル（signal_lab_verify.py）には触れない。メールや売買の決まりは変えない。

事前登録に書いていない細かい決め方（計算より先にここで固定）:
  - 「1年の高値」＝その日を含む直近252本の終値の最大
  - 「10年後」＝始めた日の暦の10年後の日付以降で最初の取引日
  - ブートストラップの道は、実際の日付の並びをそのまま使い、日々の対数の変化だけをつなぎ直す（hold_lab.boot_indices）
  - 片側 p は (当てはまった道の数＋1)÷(道の数＋1)
  - 乱数の種は SEED に固定

実行: python buy_lab.py   （Actions の buy-lab.yml から手動で）
"""
import datetime as dt
import json
import math
import sys

import numpy as np
import pandas as pd

from hold_lab import boot_indices, load_prices
from pillar_lab import prereg_sha256

JST = dt.timezone(dt.timedelta(hours=9))
ASSETS = {"SP500": "米国株（S&P500・配当込み・円建て）", "TOPIX": "日本株（TOPIX連動ETF 1306・配当調整済み）",
          "NIFTY": "インド株（Nifty50・配当なし・円建て）"}
UNTIL = "2026-10-02"
HIGH_WIN = 252
HORIZON_Y = 10
READ_Y = 5
WINDOW_M = 24                       # DIP の期限・HYB の積立の月数
DIP_TIERS = (0.10, 0.20, 0.30, 0.40)
HYB_TIERS = (0.10, 0.20, 0.30)
NEAR = (0.75, 1.25)
D_MONTHS = {"D12": 12, "D24": 24}
METHODS = ("D12", "D24", "DIP", "HYB")
METHOD_NAME = {"L": "一括", "D12": "12か月に分ける", "D24": "24か月に分ける", "DIP": "下がったら買う",
               "HYB": "毎月の積立＋下がったら前倒し"}
N_COMPARE = 12
ALPHA = 0.05 / N_COMPARE
N_BOOT = 1000
BLOCK = 250
SEED = 20261006
VERDICTS = ("◎ 一括より良い（確認）", "◯ 一括より良い傾向", "◎ 一括のほうが良い（確認）", "◯ 一括のほうが良い傾向", "差なし")
OUT_JSON, OUT_MD = "buy-lab.json", "buy-lab.md"


# ════════════════════ 下ごしらえ ════════════════════

def month_starts(dates):
    """各月の最初の取引日の添字"""
    ym = np.asarray(dates.year) * 12 + np.asarray(dates.month)
    return np.r_[0, np.flatnonzero(np.diff(ym) != 0) + 1]


def drawdown(p, win=HIGH_WIN):
    """1年（直近 win 本・その日を含む）の高値からの下落（0 以下）"""
    p = np.asarray(p, float)
    return p / pd.Series(p).rolling(win, min_periods=1).max().to_numpy() - 1


def next_hits(dd, tier):
    """各日 i について、i 以降で初めて下落が −tier 以下になる日（無ければ len）"""
    n = len(dd)
    hits = np.flatnonzero(dd <= -tier + 1e-12)
    out = np.full(n, n)
    if len(hits):
        k = np.searchsorted(hits, np.arange(n))
        ok = k < len(hits)
        out[ok] = hits[k[ok]]
    return out


def start_grid(dates, years):
    """始める日（月の最初の取引日・252本より後）と、その years 年後の添字。→ (月初の添字, [(月初の何番目, 始める日, 終わりの日)])"""
    ms = month_starts(dates)
    d = np.asarray(dates.values, dtype="datetime64[D]")
    need = max(WINDOW_M, max(int(math.ceil(k * NEAR[1])) for k in D_MONTHS.values())) + 1
    out = []
    for pos, s in enumerate(ms):
        if s < HIGH_WIN or pos + need >= len(ms):
            continue
        target = np.datetime64((dates[s] + pd.DateOffset(years=years)).date())
        e = int(np.searchsorted(d, target))
        if e >= len(d):
            break
        out.append((pos, int(s), e))
    return ms, out


# ════════════════════ 入れ方（いつ・どれだけ買うか） ════════════════════

def schedule(method, ms, pos, s, hits=None, k=None):
    """→ [(買う日の添字, 最初の資金に対する割合)]。合計は1（HYB は現金が尽きたところで終わる）"""
    if method == "L":
        return [(s, 1.0)]
    if method == "D":
        return [(int(ms[pos + i]), 1.0 / k) for i in range(k)]
    dl = int(ms[pos + WINDOW_M])
    if method == "DIP":
        return [(int(h[s]) if h[s] < dl else dl, 1.0 / len(hits)) for h in hits]
    if method == "HYB":
        ev = sorted([(int(ms[pos + i]), 1.0 / WINDOW_M) for i in range(WINDOW_M)]
                    + [(int(h[s]), 0.25) for h in hits if h[s] < dl], key=lambda x: x[0])
        out, cash = [], 1.0
        for t, a in ev:
            a = min(a, cash)
            if a <= 1e-15:
                break
            out.append((t, a))
            cash -= a
        return out
    raise ValueError(method)


def wealth(p, buys, e):
    """e の日の資産（買った分の値上がり＋残りの現金）"""
    spent = sum(a for _, a in buys)
    return sum(a * p[e] / p[t] for t, a in buys) + (1.0 - spent)


def fund_path(p, buys, s, e):
    """始めた日から e までの資産の道（現金＋持っている分）"""
    seg = p[s:e + 1]
    units = np.zeros(len(seg))
    cash = np.ones(len(seg))
    for t, a in buys:
        units[t - s:] += a / p[t]
        cash[t - s:] -= a
    return cash + units * seg, cash


def configs(tiers_cache):
    """入れ方ごとの (名前, 作り方)。近い設定も含む"""
    def hits_for(tiers):
        return [tiers_cache(t) for t in tiers]
    cfg = {"L": [("L", lambda ms, pos, s: schedule("L", ms, pos, s))]}
    for name, k in D_MONTHS.items():
        cfg[name] = [(f"{kk}か月", (lambda kk: lambda ms, pos, s: schedule("D", ms, pos, s, k=kk))(kk))
                     for kk in (k, int(round(k * NEAR[0])), int(round(k * NEAR[1])))]
    for name, tiers in (("DIP", DIP_TIERS), ("HYB", HYB_TIERS)):
        cfg[name] = [(f"段×{f}" if f != 1.0 else "そのまま",
                      (lambda h, nm: lambda ms, pos, s: schedule(nm, ms, pos, s, hits=h))(hits_for([t * f for t in tiers]), name))
                     for f in (1.0,) + NEAR]
    return cfg


def make_cache(p):
    dd = drawdown(p)
    memo = {}

    def get(t):
        key = round(t, 6)
        if key not in memo:
            memo[key] = next_hits(dd, t)
        return memo[key]
    return get


# ════════════════════ 数える ════════════════════

def mean_logs(p, ms, grid, cfg, methods=METHODS, main_only=True):
    """入れ方ごとの log(資産÷一括) の配列（始める日の並び）"""
    wl = np.array([p[e] / p[s] for _, s, e in grid])
    out = {}
    for m in methods:
        builders = cfg[m][:1] if main_only else cfg[m]
        out[m] = [np.log(np.array([wealth(p, b(ms, pos, s), e) for pos, s, e in grid]) / wl) for _, b in builders]
    return out, wl


def judge(r, p_better, p_worse):
    a_pos = r["mean_log"] > 0 and r["mean_log_first"] > 0 and r["mean_log_second"] > 0
    a_neg = r["mean_log"] < 0 and r["mean_log_first"] < 0 and r["mean_log_second"] < 0
    near = list(r["near_mean_log"].values())
    if a_pos and r["win"] >= 0.5 and all(v > 0 for v in near):
        return VERDICTS[0] if p_better < ALPHA else (VERDICTS[1] if p_better < 0.05 else VERDICTS[4])
    if a_neg and r["win"] <= 0.5 and all(v < 0 for v in near):
        return VERDICTS[2] if p_worse < ALPHA else (VERDICTS[3] if p_worse < 0.05 else VERDICTS[4])
    return VERDICTS[4]


def evaluate(px, seed=SEED, n_boot=N_BOOT):
    p = np.asarray(px.values, float)
    dates = pd.DatetimeIndex(px.index)
    ms, grid = start_grid(dates, HORIZON_Y)
    _, grid5 = start_grid(dates, READ_Y)
    if len(grid) < 24:
        raise ValueError("始める日が少なすぎる")
    cfg = configs(make_cache(p))
    logs, wl = mean_logs(p, ms, grid, cfg, main_only=False)
    logs5, _ = mean_logs(p, ms, grid5, cfg)
    half = len(grid) // 2
    res = {}
    # 一括そのもの（読むため）
    lump_min = []
    for pos, s, e in grid:
        v, _ = fund_path(p, schedule("L", ms, pos, s), s, e)
        lump_min.append(v.min())
    res["L"] = {"median_multiple": float(np.median(wl)), "worst_multiple": float(wl.min()),
                "best_multiple": float(wl.max()), "fund_min_median": float(np.median(lump_min)),
                "fund_min_worst": float(min(lump_min))}
    for m in METHODS:
        x = logs[m][0]
        mins, cash_share = [], []
        _, b = cfg[m][0]
        for pos, s, e in grid:
            v, c = fund_path(p, b(ms, pos, s), s, e)
            mins.append(v.min())
            cash_share.append(float(np.mean(c / v)))
        res[m] = {"mean_log": float(x.mean()), "mean_log_first": float(x[:half].mean()),
                  "mean_log_second": float(x[half:].mean()), "win": float((x > 0).mean()),
                  "median_ratio": float(np.exp(np.median(x))), "worst_ratio": float(np.exp(x.min())),
                  "best_ratio": float(np.exp(x.max())),
                  "near_mean_log": {cfg[m][i][0]: float(logs[m][i].mean()) for i in (1, 2)},
                  "cash_share": float(np.mean(cash_share)), "fund_min_median": float(np.median(mins)),
                  "fund_min_worst": float(min(mins)),
                  "read5": {"mean_log": float(logs5[m][0].mean()), "win": float((logs5[m][0] > 0).mean()),
                            "n": len(grid5)}}
    # ブートストラップ（同じ日付の並びで、日々の対数の変化だけをつなぎ直した道）
    rng = np.random.default_rng(seed)
    r = np.diff(np.log(p))
    le_zero = {m: 0 for m in METHODS}
    ge_zero = {m: 0 for m in METHODS}
    done = 0
    while done < n_boot:
        b = min(100, n_boot - done)
        idx = boot_indices(len(r), b, rng, block=BLOCK)
        for row in idx:
            q = p[0] * np.exp(np.r_[0.0, np.cumsum(r[row])])
            ql, _ = mean_logs(q, ms, grid, configs(make_cache(q)))
            for m in METHODS:
                mu = ql[m][0].mean()
                le_zero[m] += mu <= 0
                ge_zero[m] += mu >= 0
        done += b
    for m in METHODS:
        pb, pw = (le_zero[m] + 1) / (n_boot + 1), (ge_zero[m] + 1) / (n_boot + 1)
        res[m].update({"p_better": pb, "p_worse": pw, "verdict": judge(res[m], pb, pw)})
    info = {"n_starts": len(grid), "first_start": str(dates[grid[0][1]].date()), "last_start": str(dates[grid[-1][1]].date()),
            "mid_start": str(dates[grid[half][1]].date()), "data_from": str(dates[0].date()), "data_to": str(dates[-1].date())}
    return {"info": info, "results": res}


# ════════════════════ 書き出し ════════════════════

def _pct(x, nd=1, sign=True):
    return "—" if x is None else (f"{x * 100:+.{nd}f}%" if sign else f"{x * 100:.{nd}f}%")


def _lr(x):
    """対数の平均 → 一括に対して何%多い／少ないか"""
    return _pct(math.exp(x) - 1)


def render_md(out):
    L = ["# R2 余剰資金の入れ方（一括・分ける・下がったら買う）", "",
         f"- 生成: {out['generated_jst']}　事前登録の指紋（PILLAR_PREREG.md の sha256）: `{out['prereg_sha256']}`",
         "- 物差しと判定＝PILLAR_PREREG.md「R2 余剰資金の入れ方」（計算より先にコミット）。**過去のデータで1回だけ数えた結果**",
         f"- 税なし・買うだけ（非課税口座で使える形）。最初の資金を1として、始めた日から{HORIZON_Y}年後の資産を一括と比べる（金額は書かない）",
         f"- 関門＝ブートストラップ（平均{BLOCK}日のかたまり・{N_BOOT}本）の片側 p＜0.05÷{N_COMPARE}（{ALPHA:.5f}）", ""]
    if out["missing"]:
        return "\n".join(L + [f"## ⚠️ データが取れなかった資産：{'・'.join(out['missing'])}", "",
                              "何も数えていない。データが取れたときだけ、やり直してよい。", ""]) + "\n"
    L += ["## 判定の一覧", "", "| 資産 | " + " | ".join(METHOD_NAME[m] for m in METHODS) + " |",
          "|---|" + "---|" * len(METHODS)]
    for a, r in out["assets"].items():
        L.append(f"| {ASSETS[a]} | " + " | ".join(r["results"][m]["verdict"] for m in METHODS) + " |")
    L.append("")
    for a, r in out["assets"].items():
        i, lr = r["info"], r["results"]["L"]
        L += [f"## {ASSETS[a]}", "",
              f"- 始める日 {i['n_starts']}か月（{i['first_start']}〜{i['last_start']}・前半と後半の境 {i['mid_start']}）"
              f"／データ {i['data_from']}〜{i['data_to']}",
              f"- 一括の{HORIZON_Y}年後の資産：中央値 {lr['median_multiple']:.2f}倍・いちばん悪い {lr['worst_multiple']:.2f}倍・"
              f"いちばん良い {lr['best_multiple']:.2f}倍／途中でいちばん減ったとき 中央値 {_pct(lr['fund_min_median'] - 1)}・"
              f"いちばん悪い {_pct(lr['fund_min_worst'] - 1)}", "",
              f"| 入れ方 | 判定 | 一括に対して（平均） | 前半 | 後半 | 勝った割合 | 中央値 | いちばん悪い | いちばん良い | "
              f"近い設定 | ブートストラップ p（良い／悪い） |", "|---|---|---|---|---|---|---|---|---|---|---|"]
        for m in METHODS:
            x = r["results"][m]
            near = "・".join(f"{k} {_lr(v)}" for k, v in x["near_mean_log"].items())
            L.append(f"| {METHOD_NAME[m]} | {x['verdict']} | {_lr(x['mean_log'])} | {_lr(x['mean_log_first'])} | "
                     f"{_lr(x['mean_log_second'])} | {_pct(x['win'], 0, False)} | {_pct(x['median_ratio'] - 1)} | "
                     f"{_pct(x['worst_ratio'] - 1)} | {_pct(x['best_ratio'] - 1)} | {near} | "
                     f"{x['p_better']:.4f}／{x['p_worse']:.4f} |")
        L += ["", "| 入れ方 | 現金で置いていた平均の割合 | 途中でいちばん減ったとき（中央値） | （いちばん悪い） | "
              f"{READ_Y}年後：一括に対して | {READ_Y}年後：勝った割合 |", "|---|---|---|---|---|---|"]
        for m in METHODS:
            x = r["results"][m]
            L.append(f"| {METHOD_NAME[m]} | {_pct(x['cash_share'], 0, False)} | {_pct(x['fund_min_median'] - 1)} | "
                     f"{_pct(x['fund_min_worst'] - 1)} | {_lr(x['read5']['mean_log'])} | {_pct(x['read5']['win'], 0, False)} |")
        L.append("")
    L += ["## 読み方の約束と限界", "",
          "- 始める日は毎月ずらすので10年の窓は大きく重なる＝独立した例は米国株で約3つ、日本株・インド株は1〜2つ。"
          "前半・後半とブートストラップはそのための確かめ",
          "- どれが勝っても過去の1回の数え上げ。使うかどうかはオーナーが決める。サイトの記事で「この入れ方が良い」とは書かない",
          "- インド株は配当を含まない。米国株の指数は信託報酬を含まない。現金の利息0。日本株は2009年から",
          "- 非課税口座の年間の枠は数えない。過去の成績は将来を約束しない。情報提供であり投資助言ではない", ""]
    return "\n".join(L) + "\n"


def main():
    prices, missing, src, fixes = load_prices(until=UNTIL)
    missing = [a for a in missing if a in ASSETS]
    out = {"generated_jst": dt.datetime.now(JST).strftime("%Y-%m-%dT%H:%M+09:00"), "prereg_sha256": prereg_sha256(),
           "kind": "backtest", "section": "R2", "missing": missing, "until": UNTIL,
           "sources": {a: src.get(a) for a in ASSETS}, "data_fixes": {k: v for k, v in fixes.items()},
           "settings": {"horizon_years": HORIZON_Y, "alpha": ALPHA, "n_boot": N_BOOT, "block": BLOCK, "seed": SEED},
           "assets": {}}
    if not missing:
        for a in ASSETS:
            print(f"{a}: {len(prices[a])} 日 を数える", file=sys.stderr)
            out["assets"][a] = evaluate(prices[a])
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    md = render_md(out)
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(md)
    print(md)
    return 0 if not missing else 1


if __name__ == "__main__":
    sys.exit(main())
