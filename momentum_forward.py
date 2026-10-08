# -*- coding: utf-8 -*-
"""J42F 「過去12か月で一番上げた10銘柄」は翌月弱いか・前向きの記録。2026-10-08 夜 登録・オーナー「2を登録して進めてください」。
PILLAR_PREREG.md「J42F」。

J42 の読むための表で、12−1 の上位10銘柄は翌月に全銘柄の平均より弱かった（最近 −1.45％/月・結果を見たあとに気づいた数字）。
**登録してからのデータだけ**で確かめる＝決める月 2026-10〜2028-09 の24か月。計算は momentum_lab の関数をそのまま使う
（1か月の値＝momentum_lab.diff(kind=10)＝10銘柄の平均 − 同じ組の全銘柄の平均 − 入れ替えた割合 × 往復0.1％）。

- 毎月、Yahoo から東証の全上場の5年の日足（始値つき）を取り直す（置き場 jp-bars は手動で古くなるため使わない）
- 一度記録した月は書き換えない。持つ月のあいだに上場廃止で消えた株を数えるため、買う日が過ぎた月の上位10銘柄を
  **符号（コードのハッシュ）だけ**残し、売る日のあとの回で「組に残っているか」を数える（コードは出さない）
- 24か月そろったら1回だけ判定（95％の幅・6か月のかたまり）。それまで md には数えた月の数だけを出す

実行: python momentum_forward.py --check   （点検だけ＝取れた銘柄の数・数えられる月の数。損益は数えない・何も書き出さない）
      python momentum_forward.py           （本番。Actions の momentum-forward.yml から・毎月3日ごろ）
"""
import datetime as dt
import hashlib
import json
import sys

import numpy as np

import jp_bars
import momentum_lab as M
import pillar_lab as P
import yori_lab as Y

OUT_JSON, OUT_MD = "momentum-forward.json", "momentum-forward.md"
FWD_FIRST, FWD_LAST = (2026, 10), (2028, 9)
PREV = (2026, 9)              # 入れ替えた割合を数えるためだけに使う前の月（記録しない）
GOAL = 24
TOP = 10
RANGE = "5y"
PAUSE = 0.05
ALPHA = 0.05
OK, REV, NONE = "✅ 前向きでも弱い", "✕ 逆向き", "― 見えない"
FID = "F1"
TITLE = "過去12か月で一番上げた10銘柄（12−1・売買代金1億円以上）を翌月持つ − 全銘柄の平均（前向き・決める月 2026-10〜2028-09）"


def ym_of(i):
    return "%04d-%02d" % M.id_ym(i)


def in_window(ym):
    y, m = map(int, ym.split("-"))
    return M.ym_id(*FWD_FIRST) <= M.ym_id(y, m) <= M.ym_id(*FWD_LAST)


def tag(code):
    """コードの代わりに残す符号（出力にコードを出さない）"""
    return hashlib.sha256(f"j42f:{code}".encode()).hexdigest()[:12]


def month_values(recs):
    """momentum_lab.records の結果 → {決める月: 値}（記録する24か月の窓の中だけ）"""
    out = {}
    for r in recs:
        if not in_window(r["ym"]):
            continue
        a = r["arms"]["Q1"]
        out[r["ym"]] = {"d10": M.diff(r, "Q1", kind=10), "d20": M.diff(r, "Q1", kind=20), "top10": a["top10"],
                        "uni": r["uni"], "rep10": a["rep10"], "n_u": r["n_u"]}
    return out


def merge(old, new):
    """一度記録した月は書き換えない → (合わせたもの, 新しく足した月)"""
    out = dict(old or {})
    added = [ym for ym in sorted(new) if ym not in out]
    for ym in added:
        out[ym] = new[ym]
    return out, added


def _mkt(R):
    fin = np.isfinite(R)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(fin.any(0), np.nansum(R, 0) / np.maximum(fin.sum(0), 1), np.nan)


def pending_tops(T, codes, k=TOP):
    """買う日（翌月の最初の取引日）が置き場にあり、売る日がまだの決める月 → {決める月: [符号]}（records と同じ組と並べ方）"""
    M_ = T["M"]
    R = M.month_returns(T)
    mkt = _mkt(R)
    IND = M.industry_loo(R, T["sector"])
    out = {}
    with np.errstate(invalid="ignore", divide="ignore"):
        for j in range(M.HIST, len(M_) - 1):
            ym = ym_of(M_[j])
            if not in_window(ym) or M_[j] - M_[j - M.HIST] != M.HIST or M_[j + 1] - M_[j] != 1:
                continue
            win = R[:, j - M.HIST + 1:j + 1]
            m = (T["has_last"][:, j] & (T["nb"][:, j] >= M.MIN_BARS) & (T["tv"][:, j] >= M.TV_MIN) & np.isfinite(win).all(1)
                 & np.isfinite(T["hi"][:, j]) & np.isfinite(T["q_entry"][:, j + 1]))
            sig = M.signals(T, R, mkt, IND, j, m)
            m = m & np.isfinite(sig["res"])
            idx = np.nonzero(m)[0]
            if len(idx) < M.MIN_UNIVERSE:
                continue
            out[ym] = [tag(codes[i]) for i in M.rank_top(sig["mom"], idx, k)]
    return out


def gone_counts(T, codes, pending, months):
    """記録した月ごとに、買う日の上位10銘柄のうち売る日のあとの組に残っていない（消えた）数"""
    M_ = T["M"]
    R = M.month_returns(T)
    pos = {ym_of(i): j for j, i in enumerate(M_)}
    out = {}
    with np.errstate(invalid="ignore", divide="ignore"):
        for ym in months:
            if ym not in pending or ym not in pos:
                continue
            m, _ = M.universe(T, R, pos[ym])
            alive = {tag(codes[i]) for i in np.nonzero(m)[0]}
            out[ym] = sum(1 for t in pending[ym] if t not in alive)
    return out


def judge(months):
    """24か月そろったら1回だけ → dict（そろわなければ None）"""
    keys = sorted(months)[:GOAL]
    if len(keys) < GOAL:
        return None
    b = M.band([months[k]["d10"] for k in keys], alpha=ALPHA)
    v = OK if b["hi"] is not None and b["hi"] < 0 else REV if b["lo"] is not None and b["lo"] > 0 else NONE
    return dict(b, verdict=v, months=keys)


def verdicts_of(j, today):
    if not j:
        return {}
    st = "confirm" if j["verdict"] == OK else "stop"
    return {FID: {"status": st, "decided_on": today, "n": j["n"], "mean": j["mean"], "lo": j["lo"], "hi": j["hi"],
                  "reason": f"登録後の24か月で{j['verdict'].split(' ', 1)[1]}（10銘柄 − 全銘柄の平均・費用後・95％の幅）"}}


def render_md(res):
    L = ["# J42F 「過去12か月で一番上げた10銘柄」は翌月弱いか（前向きの記録）", "",
         f"更新: {res.get('generated_at', '')}（事前登録＝`PILLAR_PREREG.md`「J42F」・指紋 `{(res.get('prereg_sha256') or '')[:12]}`）", ""]
    if res.get("error"):
        return "\n".join(L + [f"⚠️ 計算できず：{res['error']}", "", "※ 研究の記録です。投資助言ではありません。"]) + "\n"
    months = res.get("months") or {}
    L += ["決める月 2026-10〜2028-09 の24か月（月末の大引けで上位10銘柄を選び、翌月の最初の取引日の寄りで買い、その次の月の最初の取引日の寄りで売る）。",
          f"**数えた月：{len(months)}/{GOAL}**（{', '.join(sorted(months)) or 'まだなし'}）。"
          f"買う日の一覧を残した月：{len(res.get('pending') or {})}。", ""]
    j = res.get("judge")
    if not j:
        L += ["24か月そろうまで、途中の数字は出さない（事前登録のとおり）。", ""]
    else:
        L += ["## 判定", "", f"**{j['verdict']}**：10銘柄 − 全銘柄の平均（費用後・月あたり）{M._p(j['mean'])}・95％の幅 {M._band(j)}", "",
              "## 読むための表", ""]
        keys = j["months"]
        d20 = [months[k]["d20"] for k in keys]
        L += [f"- 上位20銘柄の差 {M._p(float(np.mean(d20)))}・10銘柄そのもの {M._p(float(np.mean([months[k]['top10'] for k in keys])))}"
              f"・全銘柄の平均 {M._p(float(np.mean([months[k]['uni'] for k in keys])))}",
              f"- 最悪の月 {M._p(min(months[k]['d10'] for k in keys))}・差がプラスの月 {sum(months[k]['d10'] > 0 for k in keys)}/{len(keys)}",
              f"- 消えた銘柄（売る日のあとの組に残っていない）：{sum((res.get('gone') or {}).get(k, 0) for k in keys)}", ""]
    L += ["## 注意", "",
          "- 判定の力は弱い（24か月の平均の誤差は約 ±2.1％）＝「見えない」で終わる見込みが高い（事前登録に書いたとおり）",
          "- いま上場している銘柄だけ・配当なし・空売りの合図ではない（「買わない」側の目印の記録）", "", "---", "",
          "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def read_prev(path=OUT_JSON):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def main(argv):
    now = dt.datetime.now(P.JST)
    prev = read_prev()
    res = {"generated_at": now.isoformat(timespec="minutes"), "prereg_file": P.PREREG, "prereg_sha256": P.prereg_sha256(),
           "kind": "forward", "fwd_start": "2026-10", "goal": GOAL, "titles": {FID: TITLE},
           "months": prev.get("months") or {}, "pending": prev.get("pending") or {}, "gone": prev.get("gone") or {}}
    try:
        stocks, list_date = jp_bars.load_universe()
        codes = sorted(stocks)
        series, missing, cal = M.load(codes, Y.fetch_chart, rng=RANGE, pause=PAUSE)
        Mi, first, last, tail = M.month_table(cal)
        T = M.panel(series, {c: (stocks[c] or {}).get("sector") or "" for c in series}, Mi, first, last, tail)
        have = sorted(series)
        if "--check" in argv:
            recs, _ = M.records(T, first=PREV, last=FWD_LAST)
            print(json.dumps({"n_codes": len(codes), "missing_daily": missing, "list_date": list_date,
                              "calendar": [ym_of(Mi[0]), ym_of(Mi[-1])] if len(Mi) else None,
                              "settled_months_in_window": sorted(r["ym"] for r in recs if in_window(r["ym"])),
                              "pending_months": sorted(pending_tops(T, have)), "bad_days_zeroed": int(T["bad_days"])},
                             ensure_ascii=False, indent=1))
            return 0
        if missing > 0.05 * len(codes):
            raise RuntimeError("日足を取れなかった銘柄が5％超。偏った組で数えない（次の回で取り直す）")
        for ym, tags in pending_tops(T, have).items():
            res["pending"].setdefault(ym, tags)                       # 買う日の一覧も一度残したら書き換えない
        recs, _ = M.records(T, first=PREV, last=FWD_LAST)
        res["months"], added = merge(res["months"], month_values(recs))
        res["gone"].update({k: v for k, v in gone_counts(T, have, res["pending"], added).items() if k not in res["gone"]})
        res["added"] = added
        res["n_codes"], res["n_missing"], res["list_date"] = len(codes), missing, list_date
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        if "--check" in argv:
            return 1
        res["error"] = f"{type(e).__name__}: {str(e)[:200]}"
    res["progress"] = {FID: len(res["months"])}
    res["judge"] = judge(res["months"])
    res["verdicts"] = verdicts_of(res["judge"], now.date().isoformat()) if res["judge"] else (prev.get("verdicts") or {})
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(M.rounded(res), fh, ensure_ascii=False, indent=1, default=str)
    md = render_md(res)
    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
