# -*- coding: utf-8 -*-
"""R9 SQ週（オプションの満期の週）は特別か：日経平均と S&P500 の週の値動き。2026-10-08 登録・オーナー「両方登録して進めてください」。
PILLAR_PREREG.md「R9」。

週＝月曜〜日曜・週の損益率＝その週の最後の取引日の終値 ÷ 前の週の最後の取引日の終値 − 1。満期の週＝日本は第2金曜日、米国は
第3金曜日を含む週。時代＝E1 1992〜2010・E2 2011〜2026-09。問い＝Q1 日本（^N225）・Q2 米国（^GSPC）の「満期の週 − ほかの週」。
判定＝97.5％ の幅（週を引き直す 10,000回）が2つの時代とも同じ側なら ✅。**まだ誰も数えていない**。

⚠️ 決まりは PILLAR_PREREG.md「R9」と下の定数に固定。値段は pillar_lab.fetch（Yahoo の日足・調整後）の終値だけ（始値は使わない＝R8 の教訓）。
⚠️ 出力（sq-week-lab.json / .md）は GitHub 側で生成＝手元から送らない（SYNC禁忌）。

実行: python sq_week_lab.py --check   （点検だけ＝時代ごとの週の数と満期の週の数。損益は数えない・何も書き出さない）
      python sq_week_lab.py           （本番。Actions の sq-week-lab.yml から手動で・1回だけ）
"""
import datetime as dt
import json
import sys

import numpy as np

import pillar_lab as P

OUT_JSON, OUT_MD = "sq-week-lab.json", "sq-week-lab.md"
FETCH_START = "1991-06-01"
QUESTIONS = (("Q1", "日本（日経平均・第2金曜日の SQ週）", "^N225", 2),
             ("Q2", "米国（S&P500・第3金曜日のオプションの満期の週）", "^GSPC", 3))
ERAS = (("e1", "E1 1992〜2010年", ("1992-01-01", "2010-12-31")),
        ("e2", "E2 2011〜2026年", ("2011-01-01", "2026-09-30")))
N_Q = len(QUESTIONS)
ALPHA = 0.05 / N_Q            # 97.5％ の幅
N_BOOT = 10000
COST = 0.0008                 # MT4 の CFD：売り買いの差＋1週間の持ち越しの金利（読むための表だけ）
MAJOR = (3, 6, 9, 12)
OK, NEW_ONLY, OLD_ONLY, NONE = "✅ 2つの時代とも同じ向き", "△ 最近だけ", "△ 昔だけ（いまは消えた）", "✕ 差なし"


# ════════════════════ 週と満期 ════════════════════

def nth_friday(year, month, n):
    d = dt.date(year, month, 1)
    first = d + dt.timedelta((4 - d.weekday()) % 7)
    return first + dt.timedelta(7 * (n - 1))


def monday(d):
    return d - dt.timedelta(d.weekday())


def expiry_mondays(y0, y1, n):
    """→ {満期の週の月曜: 月}"""
    return {monday(nth_friday(y, m, n)): m for y in range(y0, y1 + 1) for m in range(1, 13)}


def weekly(closes):
    """closes＝[(日付, 終値)]（日付順）→ [(週の月曜, 最後の取引日, 週の損益率)]。前の週が無い週は入れない"""
    last = {}
    for d, c in closes:
        if c and c > 0:
            last[monday(d)] = (d, float(c))
    weeks = sorted(last)
    out = []
    for prev, cur in zip(weeks, weeks[1:]):
        out.append((cur, last[cur][0], last[cur][1] / last[prev][1] - 1))
    return out


def label(weeks, n):
    """週ごとに（満期の週か・メジャーか・満期の週の次の週か）"""
    if not weeks:
        return [], [], []
    exp = expiry_mondays(weeks[0][0].year - 1, weeks[-1][0].year + 1, n)
    is_exp = [w in exp for w, _, _ in weeks]
    major = [w in exp and exp[w] in MAJOR for w, _, _ in weeks]
    after = [(w - dt.timedelta(7)) in exp for w, _, _ in weeks]
    return is_exp, major, after


# ════════════════════ 幅と判定 ════════════════════

def diff_band(a, b, alpha=ALPHA, n_boot=N_BOOT, seed=P.SEED):
    """mean(a) − mean(b) の (点, 下, 上)。それぞれの組の中で週を引き直す"""
    a, b = np.asarray(a, float), np.asarray(b, float)
    if len(a) < 5 or len(b) < 5:
        return {"value": None, "lo": None, "hi": None, "n_a": len(a), "n_b": len(b)}
    rng = np.random.default_rng(seed)
    sims = []
    for start in range(0, n_boot, 1000):
        k = min(1000, n_boot - start)
        sims.append(a[rng.integers(0, len(a), (k, len(a)))].mean(1) - b[rng.integers(0, len(b), (k, len(b)))].mean(1))
    s = np.concatenate(sims)
    lo, hi = np.percentile(s, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return {"value": float(a.mean() - b.mean()), "lo": float(lo), "hi": float(hi), "n_a": len(a), "n_b": len(b)}


def side(q):
    if q.get("lo") is None:
        return 0
    return 1 if q["lo"] > 0 else (-1 if q["hi"] < 0 else 0)


def verdict(by_era):
    s1, s2 = side(by_era["e1"]), side(by_era["e2"])
    word = lambda s: "（上向き）" if s > 0 else "（下向き）"  # noqa: E731
    if s1 != 0 and s1 == s2:
        return OK + word(s1)
    if s2 != 0:
        return NEW_ONLY + word(s2)
    if s1 != 0:
        return OLD_ONLY + word(s1)
    return NONE


def _mean(x):
    return float(np.mean(x)) if len(x) else None


def era_rows(weeks, span):
    lo, hi = dt.date.fromisoformat(span[0]), dt.date.fromisoformat(span[1])
    return [i for i, (_, last, _) in enumerate(weeks) if lo <= last <= hi]


def analyze_one(closes, n):
    weeks = weekly(closes)
    is_exp, major, after = label(weeks, n)
    r = np.array([x for _, _, x in weeks])
    out = {"eras": {}, "read": {}}
    for key, name, span in ERAS:
        idx = era_rows(weeks, span)
        e = np.array([is_exp[i] for i in idx], bool)
        mj = np.array([major[i] for i in idx], bool)
        af = np.array([after[i] for i in idx], bool)
        x = r[idx]
        q = diff_band(x[e], x[~e])
        out["eras"][key] = q
        years = {}
        for i in idx:
            years.setdefault(weeks[i][1].year, ([], []))[0 if is_exp[i] else 1].append(r[i])
        ups = [np.mean(a) - np.mean(b) for a, b in years.values() if a and b]
        me = _mean(x[e])
        out["read"][key] = {"weeks": len(idx), "exp_weeks": int(e.sum()), "exp_mean": me, "other_mean": _mean(x[~e]),
                            "major_mean": _mean(x[mj]), "minor_mean": _mean(x[e & ~mj]), "after_mean": _mean(x[af]),
                            "exp_up": float((x[e] > 0).mean()) if e.any() else None,
                            "long_net": None if me is None else me - COST, "short_net": None if me is None else -me - COST,
                            "years": len(ups), "years_up": int(sum(u > 0 for u in ups))}
    out["summary"] = verdict(out["eras"])
    return out


def analyze(data):
    res = {"questions": {}}
    for qk, name, tk, n in QUESTIONS:
        df = data[tk]
        closes = [(t.date(), float(c)) for t, c in zip(df.index, df["Close"])]
        res["questions"][qk] = dict(analyze_one(closes, n), name=name, ticker=tk)
    return res


def verdicts_of(result, today):
    """検証済みリストが読む欄：✕（差なし）だけ stop として載せる（PREREG「R9」の読み方の約束）"""
    out = {}
    for qk, x in result["questions"].items():
        if x["summary"] != NONE:
            continue
        q, rd = x["eras"]["e2"], x["read"]["e2"]
        out[qk] = {"status": "stop", "decided_on": today, "n": rd["exp_weeks"], "mean": q["value"], "lo": q["lo"], "hi": q["hi"],
                   "reason": "過去のデータで1回だけ数えて差なし（満期の週 − ほかの週・2011〜2026年の数字）"}
    return out


def check_summary(data):
    """点検だけ＝時代ごとの週の数と満期の週の数（損益は数えない）"""
    out = {}
    for qk, name, tk, n in QUESTIONS:
        df = data[tk]
        weeks = weekly([(t.date(), float(c)) for t, c in zip(df.index, df["Close"])])
        is_exp, major, _ = label(weeks, n)
        out[qk] = {"ticker": tk, "rows": int(len(df)), "first": str(df.index.min().date()), "last": str(df.index.max().date()),
                   "eras": {key: {"weeks": len(idx := era_rows(weeks, span)), "exp_weeks": int(sum(is_exp[i] for i in idx)),
                                  "major_weeks": int(sum(major[i] for i in idx))} for key, _, span in ERAS}}
    return out


# ════════════════════ 書く ════════════════════

def _p(x, d=2):
    return "—" if x is None else f"{x * 100:+.{d}f}％"


def render_md(res):
    L = ["# R9 SQ週（オプションの満期の週）は特別か：日経平均と S&P500 の週の値動き", "",
         f"更新: {res.get('generated_at', '')}（事前登録＝`PILLAR_PREREG.md`「R9」・指紋 `{(res.get('prereg_sha256') or '')[:12]}`）", ""]
    r = res.get("result") or {}
    if "error" in r:
        return "\n".join(L + [f"⚠️ 計算できず：{r['error']}", "", "※ 研究の記録です。投資助言ではありません。"]) + "\n"
    L += ["週＝月曜〜日曜・週の損益率＝その週の最後の取引日の終値 ÷ 前の週の最後の取引日の終値 − 1（Yahoo の日足の終値）。"
          "満期の週＝日本は第2金曜日（SQ）、米国は第3金曜日を含む週。幅は 97.5％（週を引き直す 10,000回）。**まだ誰も数えていなかった問い**。", "",
          "## まとめ", "", "| 問い | E1 1992〜2010年：満期の週 − ほかの週 | E2 2011〜2026年：満期の週 − ほかの週 | まとめ |", "|---|---|---|---|"]
    for qk, x in r["questions"].items():
        cells = [f"{_p(x['eras'][e]['value'])}（{_p(x['eras'][e]['lo'])}〜{_p(x['eras'][e]['hi'])}）" for e, _, _ in ERAS]
        L.append(f"| {qk} {x['name']} | {cells[0]} | {cells[1]} | **{x['summary']}** |")
    for qk, x in r["questions"].items():
        L += ["", f"## {qk} {x['name']}", "",
              "| 時代 | 週の数（満期の週） | 満期の週の平均 | ほかの週の平均 | メジャーSQ／それ以外の満期の週 | 満期の週の次の週 | 満期の週に上げた割合 | 差がプラスの年 | 費用後：買って持つ／売って持つ |",
              "|---|---:|---:|---:|---|---:|---:|---:|---|"]
        for e, ename, _ in ERAS:
            q = x["read"][e]
            L.append(f"| {ename} | {q['weeks']:,}（{q['exp_weeks']}） | {_p(q['exp_mean'])} | {_p(q['other_mean'])} | {_p(q['major_mean'])}／{_p(q['minor_mean'])} | "
                     f"{_p(q['after_mean'])} | {'—' if q['exp_up'] is None else format(q['exp_up'] * 100, '.0f') + '％'} | {q['years_up']}／{q['years']} | "
                     f"{_p(q['long_net'])}／{_p(q['short_net'])} |")
    L += ["", "## 注意", "",
          f"- 費用（読むための表だけ）＝MT4 の CFD の売り買いの差と1週間の持ち越しの金利で {COST * 100:.2f}％ と決めておいた値",
          "- 指数の終値は CFD の値段そのものではない（CFD は先物に沿う）。週に1回なので回数が少ない",
          "- 判定は2つの問いだけ。表の目立つ数字（メジャーSQ・次の週など）は確かめるまで使わない", "", "---", "",
          "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def load(fetcher=P.fetch):
    out, failed = {}, []
    for _, _, tk, _ in QUESTIONS:
        df = fetcher(tk, "1d", start=FETCH_START)
        if df is None:
            failed.append(tk)
            continue
        out[tk] = df[df["Close"] > 0]
    return out, failed


def main(argv):
    res = {"generated_at": dt.datetime.now(P.JST).isoformat(timespec="minutes"), "prereg_file": P.PREREG,
           "prereg_sha256": P.prereg_sha256()}
    try:
        data, failed = load()
        if failed:
            raise RuntimeError("値段を取れない：" + "・".join(failed))
        if "--check" in argv:
            print(json.dumps(check_summary(data), ensure_ascii=False, indent=1))
            return 0
        res["result"] = analyze(data)
        res.update(kind="backtest", titles={qk: f"{name}の週の値動き（満期の週 − ほかの週・^N225／^GSPC の終値・1992〜2026-09・1回だけ数えた）"
                                            for qk, name, _, _ in QUESTIONS},
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
