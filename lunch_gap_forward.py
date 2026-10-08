# -*- coding: utf-8 -*-
"""R10F 昼休みの窓と同じ向きに後場を持つ・前向きの記録（MT4 の株価指数 CFD の自動売買の候補）。
2026-10-08 登録・オーナー「両方登録して進めていってください」。PILLAR_PREREG.md「R10F」。

**2026-10-09 以降の日だけ**を、1321.T の1時間足で数える（g・a の決め方は R10 の lunch_gap_lab と同じ）。記録だけ。
- 腕：F1＝|g| が 0.20％以上の日に窓と同じ向きに後場を持つ／F2＝すべての日に窓と同じ向き。費用 0.01％
- 判定：F2 は 250日・F1 は 100回で1回だけ（97.5％の幅・前半後半）。60・120・180・240日に平均がマイナスの腕は止める

⚠️ 決まりは PILLAR_PREREG.md「R10F」と下の定数に固定。途中の数字を見て動かさない。
⚠️ 出力（lunch-gap-forward.json / .md）は GitHub 側で生成＝手元から送らない（SYNC禁忌）。積み上げた判定を持つ＝古い版で上書きしない。

実行: python lunch_gap_forward.py   （Actions の lunch-gap-forward.yml から平日に）
"""
import datetime as dt
import json
import sys

import numpy as np

import lunch_gap_lab as LG
import pillar_lab as P

STATE, OUT_MD = "lunch-gap-forward.json", "lunch-gap-forward.md"
FWD_START = "2026-10-09"
LINE = 0.0020                 # R10 の上位20％の線 0.199％ を丸めた値（前向きでは動かさない）
COST = LG.COST                # 0.01％
ARMS = ("F1", "F2")
GOAL = {"F1": ("n", 100), "F2": ("days", 250)}   # F1 は 100回・F2 は 250日（数えた日）で判定
CHECKS = (60, 120, 180, 240)
CHECK_MIN_N = 10
N_Q = 2
ALPHA = 0.05 / N_Q            # 97.5％ の幅
N_BOOT = 10000
TITLES = {"F1": "昼休みの窓が 0.20％以上の日に、窓と同じ向きに後場（12:30→大引け）を持つ（1321.T の1時間足・費用 0.01％）",
          "F2": "すべての日に、昼休みの窓と同じ向きに後場を持つ（1321.T の1時間足・費用 0.01％）"}
EDGE_DAYS = 3


def empty_state():
    return {"registered": "R10F", "kind": "forward", "fwd_start": FWD_START, "line": LINE, "unit": "pct",
            "titles": TITLES, "verdicts": {}, "days": {}, "interim": [], "runs": []}


def load_state(path=STATE):
    try:
        with open(path, encoding="utf-8") as fh:
            st = json.load(fh)
    except FileNotFoundError:
        return empty_state()
    if st.get("fwd_start") != FWD_START or st.get("line") != LINE:
        raise SystemExit(f"🚨 {path} の開始日・線が登録と違う＝上書きしない")
    return st


# ════════════════════ 1日の値 ════════════════════

def arm_value(arm, g, a):
    """その日の腕の損益（費用後）。持たない日は None"""
    if g == 0 or (arm == "F1" and abs(g) < LINE):
        return None
    return float(np.sign(g) * a - COST)


def values(st, arm):
    """数えた日の順に（日付, 損益）"""
    out = []
    for d in sorted(st["days"]):
        v = arm_value(arm, st["days"][d]["g"], st["days"][d]["a"])
        if v is not None:
            out.append((d, v))
    return out


def measure(st, arm):
    vals = np.array([v for _, v in values(st, arm)])
    n = len(vals)
    out = {"n": n, "days": len(st["days"]), "mean": float(vals.mean()) if n else None, "lo": None, "hi": None, "early": None, "late": None}
    if n >= 5:
        lo, hi = LG.boot(lambda k: float(vals[k].mean()), n, alpha=ALPHA, n_boot=N_BOOT)
        half = n // 2
        out.update(lo=lo, hi=hi, early=float(vals[:half].mean()) if half else None, late=float(vals[half:].mean()))
    return out


def judge(m, day, interim=False):
    base = {"decided_on": day, "n": m["n"], "days": m["days"], "mean": m["mean"], "lo": m["lo"], "hi": m["hi"],
            "early": m["early"], "late": m["late"]}
    if interim:
        return dict(base, status="stop", reason=f"途中の見張り（{m['days']}日）で費用後の平均がマイナス")
    ok = m["lo"] is not None and m["lo"] > 0 and (m["early"] or 0) > 0 and (m["late"] or 0) > 0
    return dict(base, status="plus" if ok else "stop", reason="" if ok else "97.5％の幅が0をまたぐ／前半か後半がプラスでない")


def after_day(st, day):
    """1日足したあと：判定の時点なら判定・見張りの日なら平均がマイナスの腕を止める（幅を引き直すのはそのときだけ）"""
    n_days = len(st["days"])
    for arm in ARMS:
        if arm in st["verdicts"]:
            continue
        vals = [v for _, v in values(st, arm)]
        kind, goal = GOAL[arm]
        if (kind == "days" and n_days >= goal) or (kind == "n" and len(vals) >= goal):
            st["verdicts"][arm] = judge(measure(st, arm), day)
        elif n_days in CHECKS:
            mean = float(np.mean(vals)) if vals else None
            st["interim"].append({"day": day, "days": n_days, "arm": arm, "n": len(vals), "mean": mean})
            if len(vals) >= CHECK_MIN_N and mean is not None and mean < 0:
                st["verdicts"][arm] = judge(measure(st, arm), day, interim=True)


def done(st):
    return all(arm in st["verdicts"] for arm in ARMS)


def add_days(st, sess, today):
    """sess＝lunch_gap_lab.sessions の形。FWD_START 以降・today より前・まだ数えていない日を足す → 足した日"""
    added = []
    for d, am_close, pm_open, close in sess:
        key = d.isoformat()
        if key < FWD_START or key >= today or key in st["days"] or done(st):
            continue
        st["days"][key] = {"g": pm_open / am_close - 1, "a": close / pm_open - 1}
        after_day(st, key)
        added.append(key)
    return added


# ════════════════════ 出力 ════════════════════

def reading(st):
    """読むための欄（判定しない）"""
    days = sorted(st["days"])
    pos = {}
    for d in days:
        pos.setdefault(d[:7], []).append(d)
    first = {d for v in pos.values() for d in v[:EDGE_DAYS]}
    out = {}
    for name, pick in (("down", lambda d, g: g < 0), ("up", lambda d, g: g > 0),
                       ("monday", lambda d, g: dt.date.fromisoformat(d).weekday() == 0), ("month_first", lambda d, g: d in first)):
        xs = [v for d, v in values(st, "F1") if pick(d, st["days"][d]["g"])]
        out[name] = {"n": len(xs), "mean": float(np.mean(xs)) if xs else None}
    g = np.array([st["days"][d]["g"] for d in days])
    a = np.array([st["days"][d]["a"] for d in days])
    out["slope"] = LG.slope(g, a) if len(days) >= 5 else None
    return out


def _p(x, d=3):
    return "—" if x is None else f"{x * 100:+.{d}f}％"


def render_md(st, now):
    rd = reading(st)
    L = ["# R10F 昼休みの窓と同じ向きに後場を持つ・前向きの記録", "",
         f"更新: {now}（GitHub Actions）。事前登録＝`{P.PREREG}`「R10F」（指紋 sha256 `{(st.get('prereg_sha256') or '')[:16]}…`）。",
         f"数えるのは **{FWD_START} 以降の日**だけ（一度数えた日は数え直さない）。1321.T の1時間足で g＝後場の寄り ÷ 前場の引け − 1・"
         f"a＝大引け ÷ 後場の寄り − 1。損益＝符号(g)×a − {COST * 100:.2f}％。**記録だけ＝売買の決まりではない**。", "",
         f"- 数えた日：{len(st['days'])}日", "",
         "| 腕 | 回数 | 費用後の平均 | 97.5％の幅 | 前半／後半 | 判定まで | 状態 |", "|---|---:|---:|---|---|---|---|"]
    for k in ARMS:
        m, vd = measure(st, k), st["verdicts"].get(k)
        kind, goal = GOAL[k]
        prog = f"{m['n']}/{goal}回" if kind == "n" else f"{m['days']}/{goal}日"
        state = ("✅ 前向きでもプラス" if vd["status"] == "plus" else "⏹ ストップ") if vd else "観察中"
        band = "—" if m["lo"] is None else f"{_p(m['lo'])}〜{_p(m['hi'])}"
        L.append(f"| {k} {TITLES[k]} | {m['n']} | {_p(m['mean'])} | {band} | {_p(m['early'])}／{_p(m['late'])} | {prog} | {state} |")
    L += ["", "## 読むための欄（判定しない・R10 の表で目立ったもの）", ""]
    for key, nm in (("down", "F1 のうち窓が下向きの日"), ("up", "F1 のうち窓が上向きの日"), ("monday", "F1 のうち月曜"), ("month_first", "F1 のうち月の初めの3取引日")):
        L.append(f"- {nm}：{rd[key]['n']}回・費用後の平均 {_p(rd[key]['mean'])}")
    L.append(f"- すべての日の傾き（後場の動き ÷ 昼休みの窓）：{'—' if rd['slope'] is None else format(rd['slope'], '+.3f')}（R10 は +0.436）")
    if st.get("interim"):
        L.append("- 途中の見張り：" + "／".join(f"{x['arm']} {x['days']}日 {x['n']}回 {_p(x['mean'])}" for x in st["interim"]))
    for k in ARMS:
        vd = st["verdicts"].get(k)
        if vd:
            L.append(f"- **{k} の判定**（{vd['decided_on']}）：{'✅ 前向きでもプラス' if vd['status'] == 'plus' else '⏹ ストップ'}・{vd['n']}回・"
                     f"費用後 {_p(vd['mean'])}（{_p(vd['lo'])}〜{_p(vd['hi'])}）{('・' + vd['reason']) if vd['reason'] else ''}")
    L += ["", "- 1321.T は CFD そのものではない（12:30 ちょうどに建てられるとは限らない）", "", "---", "",
          "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def finalize(st):
    st["progress"] = {k: measure(st, k)["n"] for k in ARMS}
    st["goal"] = f"F1 は100回・F2 は250日で判定・いま {len(st['days'])}日"
    return st


def main(argv):
    st = load_state()
    now = dt.datetime.now(P.JST)
    st["prereg_sha256"] = P.prereg_sha256()
    if not done(st):
        df = P.fetch(LG.TICKER, "1h")
        added = add_days(st, LG.sessions(LG.to_bars(df)), now.date().isoformat()) if df is not None else []
        st["runs"] = (st.get("runs") or [])[-30:] + [{"at": now.isoformat(timespec="minutes"), "added": added, "fetched": df is not None}]
        print(f"足した日：{added or 'なし'}{'' if df is not None else '（値段を取れなかった）'}")
    finalize(st)
    with open(STATE, "w", encoding="utf-8") as fh:
        json.dump(st, fh, ensure_ascii=False, indent=0)
        fh.write("\n")
    md = render_md(st, now.isoformat(timespec="minutes"))
    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
