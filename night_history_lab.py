# -*- coding: utf-8 -*-
"""R8 日経平均の夜の上げは、R7 が使っていない昔の時代（1992〜2010年）でも出ていたか。2026-10-08 登録・
オーナー「やり直さなくていいので続けてください」（JP225 の CFD を MT4 で全自動にできる形のうち、R7 でいちばん惜しかったもの）。

⚠️ 物差しと判定は PILLAR_PREREG.md「R8」（事前登録・計算より先にコミット）と下の定数に固定。結果を見てから動かさない。
   出力には事前登録の中身の指紋（sha256）を書き込む。
⚠️ 夜の取引・費用・月で引き直す幅・夜−昼の p は R7（index_open_lab.py）の関数をそのまま使う。変えるのは期間・対象（^N225）・
   配当落ちの夜を除くこと・使える年の決め方・指数の始値の確かめ・判定の関門（問いが1つなので p＜0.05）だけ。
⚠️ 出力 night-history-lab.json / .md は GitHub 側で生成＝手元から送らない（SYNC禁忌）。
⚠️ エンジン・発火条件・固定オラクル（signal_lab_verify.py）には触れない。メールや売買の決まりは変えない。

事前登録に書いていない細かい決め方（計算より先にここで固定）:
  - 年ごとの点検の「前の日の終値」は、年をまたいでも1つ前の行の終値（年の最初の行は前の年の最後の行と比べる）
  - データに無い年（1992〜2010年のうち行が0の年）は使えない年に数える
  - 配当落ちの夜＝売る日（次の取引日）が、データの行で数えて3月・9月の最後の5取引日に入る夜（その月の行が5未満なら全部）
  - 指数の始値の確かめは、2つの夜の「買う日」と「売る日」がどちらも同じ夜だけを並べる（1,000夜に満たなければ確かめられない＝数えない）
  - 95％の幅・前半後半・p は index_open_lab.stats（月を引き直す10,000回・後半＝取引のあった月を古い順に並べた真ん中の月から）

実行: python night_history_lab.py           （Actions の night-history-lab.yml から手動で・1回だけ）
      python night_history_lab.py --check   （データの点検だけ・損益は数えない）
"""
import datetime as dt
import json
import sys

import numpy as np
import pandas as pd

import index_open_lab as I
from pillar_lab import fetch, prereg_sha256

JST = dt.timezone(dt.timedelta(hours=9))
INDEX, ETF = "^N225", "1321.T"
FETCH_START = "1990-01-01"
START, END, CUT = "1992-01-01", "2010-12-31", "2011-01-05"          # 買う日が 1992〜2010年（最後の夜の売る日は 2011-01-04）
FIRST_YEAR, LAST_YEAR = 1992, 2010
OV_START, OV_END, OV_CUT = "2011-01-01", "2026-09-30", "2026-10-01"  # R7 の期間（1321.T の 2026-10-05 の分割の反映もれの前で切る）
COST = I.QS["Q3"]["cost"]                                           # 往復 0.03％（R7 の Q3 と同じ）
MIN_ROWS = 200
MAX_SAME_OPEN = 0.30          # 始値＝前の日の終値の日の割合の上限（始値が埋まっていない）
MAX_OPEN_EQ_CLOSE = 0.05      # 始値＝終値の日の割合の上限
MAX_DAILY = 0.25
MIN_YEARS = 5
DIV_LAST = 5                  # 3月・9月の最後の5取引日に売る夜は配当落ちの夜として数えない
MIN_CORR = 0.90
SD_RATIO = (0.8, 1.25)
MIN_OVERLAP = 1000
ALPHA = 0.05
N_BOOT = I.N_BOOT
SEED = 20261013
VERDICTS = ("◎ 昔の時代でも残っている", "差なし")
NAME = "日経平均の夜の上げ（終値で買い次の取引日の始値で売る・1992〜2010年のうち使える年・配当落ちの夜を除く）"
PERIODS = (("1992〜1997年", 1992, 1997), ("1998〜2003年", 1998, 2003), ("2004〜2010年", 2004, 2010))
OUT_JSON, OUT_MD = "night-history-lab.json", "night-history-lab.md"


# ════════════════════ データの点検 ════════════════════

def year_shape(df):
    """年ごとの形（損益は出さない）→ {年: {rows, same_open, open_eq_close, max_change, stale, ok, why}}"""
    o, c = df["Open"].astype(float), df["Close"].astype(float)
    prev = c.shift(1)
    same = (o == prev) & prev.notna()
    oc = o == c
    ch = (c / prev - 1).abs()
    stale = pd.Series(I._stale(df), index=df.index)
    out = {}
    for y, g in df.groupby(df.index.year):
        ix = g.index
        has_prev = int(prev.loc[ix].notna().sum())
        v = {"rows": int(len(g)), "same_open": float(same.loc[ix].sum() / has_prev) if has_prev else 0.0,
             "open_eq_close": float(oc.loc[ix].mean()), "max_change": float(ch.loc[ix].max()) if has_prev else 0.0,
             "stale": int(stale.loc[ix].sum())}
        why = []
        if v["rows"] < MIN_ROWS:
            why.append(f"行が{v['rows']}")
        if v["same_open"] > MAX_SAME_OPEN:
            why.append(f"始値＝前の日の終値 {v['same_open'] * 100:.0f}%")
        if v["open_eq_close"] > MAX_OPEN_EQ_CLOSE:
            why.append(f"始値＝終値 {v['open_eq_close'] * 100:.0f}%")
        if v["max_change"] > MAX_DAILY:
            why.append(f"終値の変化 {v['max_change'] * 100:.0f}%")
        v["ok"], v["why"] = not why, "・".join(why)
        out[int(y)] = v
    return out


def usable_from(shape):
    """1992〜2010年のうちいちばん新しい使えない年の次の年（使える年が MIN_YEARS 未満なら None）"""
    bad = [y for y in range(FIRST_YEAR, LAST_YEAR + 1) if not shape.get(y, {}).get("ok")]
    y0 = max(bad) + 1 if bad else FIRST_YEAR
    return y0 if LAST_YEAR - y0 + 1 >= MIN_YEARS else None


def div_days(index):
    """3月・9月の最後の DIV_LAST 取引日（データの行で数える）→ 日付の文字列の集合"""
    idx = pd.DatetimeIndex(index)
    out = set()
    for (y, m), g in pd.Series(idx, index=idx).groupby([idx.year, idx.month]):
        if m in (3, 9):
            out.update(str(d.date()) for d in g.iloc[-DIV_LAST:])
    return out


# ════════════════════ 夜の取引 ════════════════════

def nights(df, start, end, cut):
    """R7 の夜の取引（index_open_lab.night_trades）から配当落ちの夜を除く → (行, 除いた数)。行に売る日（sell）を足す"""
    d = df[(df["Open"] > 0) & (df["Close"] > 0) & (df.index < pd.Timestamp(cut))]
    idx = pd.DatetimeIndex(d.index)
    nxt = {str(idx[i].date()): str(idx[i + 1].date()) for i in range(len(idx) - 1)}
    divs = div_days(idx)
    keep, dropped = [], 0
    for r in I.night_trades(d, COST, start=start, end=end, cut=cut):
        r["sell"] = nxt[r["day"]]
        if r["sell"] in divs:
            dropped += 1
            continue
        keep.append(r)
    return keep, dropped


def overlap(index_df, etf_df):
    """R7 の期間で、指数と上場投信の同じ夜の値動き（費用前）を並べる → {n, corr, sd_ratio, ok, ...}"""
    a, _ = nights(index_df, OV_START, OV_END, OV_CUT)
    b, _ = nights(etf_df, OV_START, OV_END, OV_CUT)
    bb = {(r["day"], r["sell"]): r for r in b}
    pairs = [(r, bb[(r["day"], r["sell"])]) for r in a if (r["day"], r["sell"]) in bb]
    out = {"n": len(pairs)}
    if len(pairs) < MIN_OVERLAP:
        out.update(ok=False, why=f"同じ夜が{len(pairs)}（{MIN_OVERLAP}未満）")
        return out
    x = np.array([p[0]["gross"] for p in pairs])
    y = np.array([p[1]["gross"] for p in pairs])
    corr, ratio = float(np.corrcoef(x, y)[0, 1]), float(x.std() / y.std())
    ok = corr >= MIN_CORR and SD_RATIO[0] <= ratio <= SD_RATIO[1]
    out.update(corr=corr, sd_ratio=ratio, ok=ok,
               why="" if ok else f"相関 {corr:.3f}（{MIN_CORR}以上が要る）・ばらつきの比 {ratio:.2f}（{SD_RATIO[0]}〜{SD_RATIO[1]}が要る）",
               _means={"index_gross": float(x.mean()), "etf_gross": float(y.mean()),
                       "index_net": float(np.mean([p[0]["net"] for p in pairs])),
                       "etf_net": float(np.mean([p[1]["net"] for p in pairs]))})
    return out


# ════════════════════ 数える ════════════════════

def judge(st):
    if st.get("n", 0) and st["mean"] > 0 and st["lo"] > 0 and st["first"] > 0 and st["second"] > 0 and st["p"] < ALPHA:
        return VERDICTS[0]
    return VERDICTS[1]


def reading(rows):
    rd = I.reading(rows, "night")
    rd["by_period"] = {lab: {"n": sum(1 for r in rows if a <= int(r["day"][:4]) <= b),
                             "mean": I._mean(r["net"] for r in rows if a <= int(r["day"][:4]) <= b)} for lab, a, b in PERIODS}
    return rd


def gates(data):
    """→ (使える年の最初, 指数の確かめ, 数えない理由のリスト)。損益は出さない"""
    shape = year_shape(data[INDEX])
    y0 = usable_from(shape)
    ov = overlap(data[INDEX], data[ETF])
    why = []
    if y0 is None:
        why.append(f"使える年が{MIN_YEARS}年に満たない")
    if not ov["ok"]:
        why.append("指数の始値が取引できる値段の代わりにならない：" + ov["why"])
    return shape, y0, ov, why


def analyze(data, rng):
    shape, y0, ov, why = gates(data)
    res = {"from_year": y0, "overlap": {k: v for k, v in ov.items() if k != "_means"},
           "bad_years": {y: v["why"] for y, v in shape.items() if FIRST_YEAR <= y <= LAST_YEAR and not v["ok"]}}
    missing = [y for y in range(FIRST_YEAR, LAST_YEAR + 1) if y not in shape]
    if missing:
        res["bad_years"].update({y: "行が0" for y in missing})
    if why:
        res["error"] = "／".join(why)
        return res
    rows, dropped = nights(data[INDEX], f"{y0}-01-01", END, CUT)
    st = I.stats(rows, "night", rng)
    st["verdict"] = judge(st)
    res.update(stats=st, reading=reading(rows), dropped_div=dropped,
               first_day=rows[0]["day"] if rows else None, last_day=rows[-1]["day"] if rows else None)
    # 読むための表：R7 の期間を日経平均で数えた場合（指数の始値のずれの大きさを見る・判定しない）
    r7, _ = nights(data[INDEX], OV_START, OV_END, OV_CUT)
    res["r7_period_index"] = {"n": len(r7), "mean": I._mean(r["net"] for r in r7), "mean_gross": I._mean(r["gross"] for r in r7),
                              "day_gross": I._mean(r["intra"] for r in r7)}
    res["r7_period_pairs"] = ov.get("_means")
    return res


# ════════════════════ 実行 ════════════════════

def load(fetcher=fetch):
    out, failed = {}, []
    for tk, start in ((INDEX, FETCH_START), (ETF, "2007-01-01")):
        df = fetcher(tk, "1d", start=start)
        if df is None:
            failed.append(f"{tk}: 取れない")
            continue
        out[tk] = df[(df["Open"] > 0) & (df["Close"] > 0)]
    return out, failed


def check_summary(data):
    """点検だけ（損益は出さない）→ 表示用の dict"""
    shape, y0, ov, why = gates(data)
    return {"years": {y: {k: v[k] for k in ("rows", "same_open", "open_eq_close", "max_change", "stale", "ok", "why")}
                      for y, v in shape.items()},
            "from_year": y0, "overlap": {k: v for k, v in ov.items() if k != "_means"}, "stop": why}


def check():
    data, failed = load()
    if failed:
        print("⚠️ " + " / ".join(failed))
        return 1
    for tk, df in data.items():
        print(f"{tk}：{len(df)}行・{df.index.min().date()}〜{df.index.max().date()}", flush=True)
    s = check_summary(data)
    print("\n日経平均の年ごとの形（損益は出さない）：")
    for y, v in s["years"].items():
        print(f"  {y}年：{v['rows']}行・始値＝前の日の終値 {v['same_open'] * 100:.1f}%・始値＝終値 {v['open_eq_close'] * 100:.1f}%・"
              f"終値の最大の変化 {v['max_change'] * 100:.1f}%・値の付いていない日 {v['stale']}　{'✅' if v['ok'] else '✕ ' + v['why']}")
    ov = s["overlap"]
    print(f"\n数える最初の年：{s['from_year']}")
    print(f"指数の始値の確かめ（R7 の期間・同じ夜 {ov['n']}）：相関 {ov.get('corr', float('nan')):.3f}・ばらつきの比 "
          f"{ov.get('sd_ratio', float('nan')):.2f}　{'✅' if ov['ok'] else '✕ ' + ov['why']}")
    print("点検だけ（損益は数えていない）。" + ("⚠️ 数えない：" + " / ".join(s["stop"]) if s["stop"] else "本番で数えられる"))
    return 1 if s["stop"] else 0


def _p(x, nd=3):
    return "—" if x is None else f"{x * 100:+.{nd}f}%"


def render_md(out):
    L = ["# R8 日経平均の夜の上げは、昔の時代（1992〜2010年）でも出ていたか", "",
         f"- 生成: {out['generated_jst']}　事前登録の指紋（PILLAR_PREREG.md の sha256）: `{out.get('prereg_sha256')}`",
         f"- 決まり＝PILLAR_PREREG.md「R8」。夜の取引・費用・幅は R7 の Q3 と同じ（往復 0.03%＋持ち越しの金利 年3%・月で引き直す95%の幅）。"
         f"3月・9月の最後の{DIV_LAST}取引日に売る夜（配当落ちの夜）は数えない。p＜{ALPHA}", ""]
    if out.get("failed"):
        return "\n".join(L + ["⚠️ データの取得の失敗＝何も数えていない：" + " / ".join(out["failed"]), ""]) + "\n"
    r = out.get("result") or {}
    ov = r.get("overlap", {})
    L += ["## データの点検（機械で決めた）", "",
          f"- 数える最初の年：{r.get('from_year')}（1992〜2010年の使えない年：" +
          ("、".join(f"{y}年＝{w}" for y, w in sorted(r.get("bad_years", {}).items())) or "なし") + "）",
          f"- 指数の始値の確かめ（R7 の期間・同じ夜 {ov.get('n')}）：相関 {ov.get('corr', float('nan')):.3f}・ばらつきの比 "
          f"{ov.get('sd_ratio', float('nan')):.2f}（{'通った' if ov.get('ok') else '通らない'}）", ""]
    if r.get("error"):
        return "\n".join(L + [f"⚠️ 計算できず：{r['error']}", ""]) + "\n"
    s, rd = r["stats"], r["reading"]
    L += [f"## Q1 {NAME}", "",
          f"- 判定：**{s['verdict']}**",
          f"- 回数 {s['n']}（{r['first_day']}〜{r['last_day']}・{s.get('months', 0)}か月・配当落ちの夜 {r['dropped_div']} を除いた）・"
          f"費用後の平均 {_p(s.get('mean'))}（95%の幅 {_p(s.get('lo'))}〜{_p(s.get('hi'))}）・費用前 {_p(s.get('mean_gross'))}・"
          f"勝ち（費用後プラス）の割合 {s.get('win_rate', 0) * 100:.1f}%",
          f"- 前半 {_p(s.get('first'))}／後半 {_p(s.get('second'))}（後半は {s.get('half_from')} から）・比べる相手＝{s.get('compare')}・"
          f"片側 p {s.get('p', 1):.4f}・夜−昼（費用前）の平均 {_p(s.get('diff_night_minus_day'))}", "",
          "読むための表（判定しない）：", "",
          "- 時期ごと（費用後）：" + "／".join(f"{k} {_p(v['mean'])}（{v['n']}）" for k, v in rd["by_period"].items()),
          "- 曜日（費用後）：" + "／".join(f"{k} {_p(v['mean'])}（{v['n']}）" for k, v in rd["fri"].items()),
          "- 1日の分け方（費用前の平均）：" + "／".join(f"{k} {_p(v)}" for k, v in rd["parts_gross"].items())]
    r7, pr = r.get("r7_period_index") or {}, r.get("r7_period_pairs") or {}
    L += [f"- R7 の期間（2011〜2026-09）を日経平均で数えた場合：費用後 {_p(r7.get('mean'))}・夜（費用前）{_p(r7.get('mean_gross'))}・"
          f"昼 {_p(r7.get('day_gross'))}（{r7.get('n')}夜）",
          f"- 同じ夜どうしの比べ（費用前）：日経平均 {_p(pr.get('index_gross'))}／1321.T {_p(pr.get('etf_gross'))}＝指数の始値のずれの大きさ", "",
          "---", "", "※ 研究の記録です。投資助言ではありません。過去の成績は将来を約束しません。指数の値段は取引できず、"
          "CFD の値段・配当の調整・費用は会社で違います。"]
    return "\n".join(L) + "\n"


def main():
    if "--check" in sys.argv[1:]:
        return check()
    rng = np.random.default_rng(SEED)
    now = dt.datetime.now(dt.timezone.utc)
    today = str(now.astimezone(JST).date())
    out = {"generated_jst": now.astimezone(JST).strftime("%Y-%m-%dT%H:%M+09:00"), "prereg_sha256": prereg_sha256(),
           "kind": "backtest", "section": "R8", "failed": [], "titles": {"Q1": NAME}, "verdicts": {}}
    data, failed = load()
    out["failed"] = failed
    if not failed:
        res = analyze(data, rng)
        out["result"] = res
        s = res.get("stats")
        if s and s["verdict"] == VERDICTS[1]:
            out["verdicts"]["Q1"] = {"status": "stop", "decided_on": today, "n": s["n"], "mean": s.get("mean"), "lo": s.get("lo"),
                                     "hi": s.get("hi"),
                                     "reason": f"昔の時代（{res['from_year']}〜2010年）で1回だけ数えて差なし（夜−昼の p {s.get('p', 1):.3f}）"}
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, default=str)
    md = render_md(out)
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(md)
    print(md)
    return 0 if not out["failed"] and not (out.get("result") or {}).get("error") else 1


if __name__ == "__main__":
    sys.exit(main())
