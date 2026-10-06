# -*- coding: utf-8 -*-
"""J10b 寄り前の気配は、寄り値までにどれだけ動くか（前向き・オーナーの画面の記録）。PILLAR_PREREG.md「J10b」。

オーナーが送ってくれた楽天 MarketSpeed の画面（8:57 ごろの板・3分足・9:30 の値）から、セッションが数字を読んで1件ずつ足す。
⚠️ 記録は**比率だけ**（8:57 の窓・寄りの窓・寄り→9:30・気配から次の注文までの離れ）。銘柄名・コード・値段は残さない
   （日付と値段がそろうと銘柄が分かってしまうため）。
⚠️ 判定は「記録が20営業日たまった日」に1回だけ。それまで平均は計算しない（途中の数字を見て決まりを動かさないため）。
⚠️ 2026-10-06 の1日分は仮説を作るのに使ったので数えない（START より前は足せない）。

使い方:
  python j10b_records.py add --date 2026-10-07 --prev 7777 --mid857 7899.5 --open 7848 --p930 7707 \
      [--best-ask 7900 --next-ask 7901 --best-bid 7899 --next-bid 7861]
  python j10b_records.py status
"""
import argparse
import json
import sys

import numpy as np

RECORDS = "j10b-records.json"
START = "2026-10-07"
GOAL_DAYS = 20
EMPTY = 0.005            # 気配から次の注文まで 0.5％ 以上＝空いている
N_BOOT = 10000
SEED = 20261006


def empty_state():
    return {"registered": "J10b", "start": START, "goal_days": GOAL_DAYS, "records": [], "verdict": None}


def load(path=RECORDS):
    try:
        with open(path, encoding="utf-8") as fh:
            st = json.load(fh)
    except FileNotFoundError:
        return empty_state()
    if st.get("start") != START:
        raise SystemExit(f"🚨 {path} の開始日 {st.get('start')} が {START} と違う＝上書きしない")
    return st


def save(st, path=RECORDS):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(st, fh, ensure_ascii=False, indent=1)
        fh.write("\n")


def make_record(date, prev, mid857, open_, p930, best_ask=None, next_ask=None, best_bid=None, next_bid=None):
    """画面の数字 → 比率だけの記録（値段は残さない）"""
    if min(prev, mid857, open_, p930) <= 0:
        raise ValueError("値段は正の数")
    up = (next_ask / best_ask - 1) if best_ask and next_ask else None
    down = (1 - next_bid / best_bid) if best_bid and next_bid else None
    r = {"date": date, "gap857": mid857 / prev - 1, "gap_open": open_ / prev - 1, "r930": p930 / open_ - 1,
         "away_up": up, "away_down": down}
    return {k: (round(v, 6) if isinstance(v, float) else v) for k, v in r.items()}


def empty_side(rec):
    """気配の外の板が片側だけ空いているか（up／down／None）"""
    up, down = rec.get("away_up"), rec.get("away_down")
    if up is None or down is None:
        return None
    if up >= EMPTY > down:
        return "up"
    if down >= EMPTY > up:
        return "down"
    return None


def add(st, rec):
    if rec["date"] < START:
        raise SystemExit(f"🚨 {rec['date']} は {START} より前＝数えない（10/6 は仮説づくりに使った）")
    if st.get("verdict"):
        print("（判定はもう出ている。記録は足すが判定は変えない）")
    st["records"].append(rec)
    return st


def days_of(st):
    return sorted({r["date"] for r in st["records"]})


def judge(st, n_boot=N_BOOT, seed=SEED):
    """20営業日たまっていれば、20日目までの記録で1回だけ判定して固定する"""
    days = days_of(st)
    if st.get("verdict") or len(days) < GOAL_DAYS:
        return st.get("verdict")
    cut = days[GOAL_DAYS - 1]
    use = [r for r in st["records"] if r["date"] <= cut]
    by_day = {}
    for r in use:
        by_day.setdefault(r["date"], []).append(abs(r["gap857"]) - abs(r["gap_open"]))
    ds = sorted(by_day)
    sums = np.array([sum(by_day[d]) for d in ds])
    cnts = np.array([len(by_day[d]) for d in ds], float)
    mean = float(sums.sum() / cnts.sum())
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(ds), size=(n_boot, len(ds)))
    sims = sums[idx].sum(1) / cnts[idx].sum(1)
    lo, hi = (float(x) for x in np.percentile(sims, [2.5, 97.5]))
    status = "縮みやすい" if lo > 0 else "広がりやすい" if hi < 0 else "見えない"
    st["verdict"] = {"decided_on": cut, "n": len(use), "days": GOAL_DAYS, "mean": mean, "lo": lo, "hi": hi, "status": status}
    return st["verdict"]


def reading_q2(st):
    """問い2（読むだけ）：片側が空いていたとき、寄り→9:30 がその向きに動いた回数"""
    out = {"up": [0, 0], "down": [0, 0]}
    for r in st["records"]:
        side = empty_side(r)
        if side:
            out[side][1] += 1
            moved = r["r930"] > 0 if side == "up" else r["r930"] < 0
            out[side][0] += int(moved)
    return out


def status_text(st):
    days = days_of(st)
    L = [f"J10b：記録 {len(st['records'])}件・{len(days)}営業日（判定は {GOAL_DAYS}営業日で1回だけ）"]
    v = st.get("verdict")
    if v:
        L.append(f"判定（{v['decided_on']}・{v['n']}件）：|8:57の窓| − |寄りの窓| の平均 {v['mean'] * 100:+.2f}％"
                 f"（95％の幅 {v['lo'] * 100:+.2f}〜{v['hi'] * 100:+.2f}％）→ {v['status']}")
        q2 = reading_q2(st)
        L.append(f"読むだけ：上が空いていた {q2['up'][1]}件中 {q2['up'][0]}件が上へ／下が空いていた {q2['down'][1]}件中 {q2['down'][0]}件が下へ")
    else:
        L.append(f"まだ判定しない（あと {max(0, GOAL_DAYS - len(days))}営業日）。途中の平均は出さない")
    return "\n".join(L)


def main(argv):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add")
    for k in ("date",):
        a.add_argument(f"--{k}", required=True)
    for k in ("prev", "mid857", "open", "p930"):
        a.add_argument(f"--{k}", type=float, required=True)
    for k in ("best-ask", "next-ask", "best-bid", "next-bid"):
        a.add_argument(f"--{k}", type=float, default=None)
    sub.add_parser("status")
    args = ap.parse_args(argv)
    st = load()
    if args.cmd == "add":
        rec = make_record(args.date, args.prev, args.mid857, args.open, args.p930,
                          args.best_ask, args.next_ask, args.best_bid, args.next_bid)
        add(st, rec)
        save(st)
        print(f"足した：{rec['date']}（8:57 の窓 {rec['gap857'] * 100:+.2f}％ → 寄りの窓 {rec['gap_open'] * 100:+.2f}％）")
    else:
        if judge(st) and st["verdict"]["decided_on"]:
            save(st)
    print(status_text(st))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
