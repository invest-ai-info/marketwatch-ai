# -*- coding: utf-8 -*-
"""J10b 寄り前の気配は、寄り値までにどれだけ動くか（前向き・オーナーの画面の記録）。PILLAR_PREREG.md「J10b」。

オーナーが送ってくれた楽天 MarketSpeed の画面（8:57 ごろの板・3分足・9:30 の値）から、セッションが数字を読んで1件ずつ足す。
⚠️ 記録は**比率だけ**（8:57 の窓・寄りの窓・寄り→9:30・気配から次の注文までの離れ）。銘柄名・コード・値段は残さない
   （日付と値段がそろうと銘柄が分かってしまうため）。
⚠️ 判定は「記録が20営業日たまった日」に1回だけ。それまで平均は計算しない（途中の数字を見て決まりを動かさないため）。
⚠️ 2026-10-06 の1日分は仮説を作るのに使ったので数えない（START より前は足せない）。

🆕 2026-10-22 J46（PILLAR_PREREG.md「J46」・オーナー「寄り付き前の売買代金の多さで罠になるかそうでないかも検証してください」）：
   同じ記録に「寄り前の売買代金の比率」pre_tv を足す＝（成行＋最良気配の数量の売り買いの平均）×100株×中値 ÷ ふだんの1日の売買代金
   （前の日より前の20営業日の平均＝目印Cの分母）。判定は 2026-10-23 からの pre_tv のある記録が1000件に届いた日に1回だけ。

使い方:
  python j10b_records.py add --date 2026-10-07 --prev 7777 --mid857 7899.5 --open 7848 --p930 7707 \
      [--best-ask 7900 --next-ask 7901 --best-bid 7899 --next-bid 7861] \
      [--ask-qty 456 --bid-qty 447 --mkt-sell 129 --mkt-buy 382 --base-tv 1.2e10]   # J46（数量は画面の百株のまま・base-tv は円）
  python j10b_records.py basetv --date 2026-10-22 5076 6407 ...   # J46 のふだんの売買代金（円）を Yahoo の日足から（コードは残さない）
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

# J46 寄り前の売買代金の多さ（PILLAR_PREREG.md「J46」）。ここで数字を変えない（変えるなら登録から）
J46_START = "2026-10-23"  # 10/22 は寄り→9:30 を見たあとに問いが出た＝読むためだけ
J46_GOAL = 1000           # pre_tv のある記録がこの件数に届いた日に1回だけ判定
J46_MIN_DAY = 6           # その日の銘柄が6未満の日は比べない（件数には入る）
LOT = 100                 # 画面の数量の単位＝百株
TV_DAYS = 20              # ふだんの売買代金＝前の日より前の20営業日の平均（jp_markers.TV_DAYS と同じ）
COST = 0.001              # 往復 0.1％（J4・J10 と同じ）
J46_SEED = 20261022


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


def make_record(date, prev, mid857, open_, p930, best_ask=None, next_ask=None, best_bid=None, next_bid=None, pre_tv=None):
    """画面の数字 → 比率だけの記録（値段は残さない）。pre_tv（J46）は渡したときだけ欄を足す"""
    if min(prev, mid857, open_, p930) <= 0:
        raise ValueError("値段は正の数")
    up = (next_ask / best_ask - 1) if best_ask and next_ask else None
    down = (1 - next_bid / best_bid) if best_bid and next_bid else None
    r = {"date": date, "gap857": mid857 / prev - 1, "gap_open": open_ / prev - 1, "r930": p930 / open_ - 1,
         "away_up": up, "away_down": down}
    if pre_tv is not None:
        r["pre_tv"] = pre_tv
    return {k: (round(v, 6) if isinstance(v, float) else v) for k, v in r.items()}


def pre_tv_ratio(mid, ask_qty, bid_qty, mkt_sell, mkt_buy, base_tv, lot=LOT):
    """J46：寄り前の注文の量の目安（売り側と買い側の平均）× 中値 ÷ ふだんの1日の売買代金（円）。

    売り側＝成行の売り＋最良の売り気配の数量、買い側＝成行の買い＋最良の買い気配の数量（画面の百株のまま渡す）。
    片側の気配の数量が無い（特別気配など）か、ふだんの売買代金が無ければ None＝数えない。純関数。
    """
    if not ask_qty or not bid_qty or not base_tv or base_tv <= 0 or mid <= 0:
        return None
    sell = (mkt_sell or 0) + ask_qty
    buy = (mkt_buy or 0) + bid_qty
    return (sell + buy) / 2 * lot * mid / base_tv


def base_turnover(bars, date):
    """bars＝[(YYYY-MM-DD, 終値, 出来高)]（古い順）→ date の前の日より前の20営業日の売買代金の平均（円）。

    目印Cの分母と同じ（jp_markers.stock_values の base）。date 当日以降の足は使わない。足りなければ None。純関数。
    """
    past = [b for b in bars if b[0] < date]
    if len(past) < TV_DAYS + 1:
        return None
    base = past[-TV_DAYS - 1:-1]
    v = sum(c * (vol or 0) for _, c, vol in base) / TV_DAYS
    return v if v > 0 else None


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


def j46_records(st):
    return [r for r in st["records"] if r["date"] >= J46_START and r.get("pre_tv") is not None]


def judge_j46(st, n_boot=N_BOOT, seed=J46_SEED):
    """J46：pre_tv のある記録が1000件に届いていれば、その日までの記録で1回だけ判定して固定する。

    日ごとに pre_tv の大きい順の上位3分の1（多い組）と下位3分の1（少ない組）の寄り→9:30 の平均の差を出し、
    日ごとの差の平均と95％の幅（日で引き直す）で判定する。
    """
    if st.get("verdict_j46"):
        return st["verdict_j46"]
    recs = j46_records(st)
    if len(recs) < J46_GOAL:
        return None
    by_day = {}
    for r in recs:
        by_day.setdefault(r["date"], []).append(r)
    cnt, cut = 0, None
    for d in sorted(by_day):
        cnt += len(by_day[d])
        if cnt >= J46_GOAL:
            cut = d
            break
    diffs, top = [], []
    for d in sorted(x for x in by_day if x <= cut):
        rs = sorted(by_day[d], key=lambda r: r["pre_tv"])
        if len(rs) < J46_MIN_DAY:
            continue
        k = len(rs) // 3
        hi_g, lo_g = rs[-k:], rs[:k]
        diffs.append(np.mean([r["r930"] for r in hi_g]) - np.mean([r["r930"] for r in lo_g]))
        top += [r["r930"] for r in hi_g]
    if not diffs:
        st["verdict_j46"] = {"decided_on": cut, "n": cnt, "days_compared": 0, "mean_diff": 0.0, "lo": 0.0, "hi": 0.0,
                             "top_net": 0.0, "status": "見えない（比べられる日が無い）"}
        return st["verdict_j46"]
    diffs = np.array(diffs)
    mean = float(diffs.mean())
    rng = np.random.default_rng(seed)
    sims = diffs[rng.integers(0, len(diffs), size=(n_boot, len(diffs)))].mean(1)
    lo, hi = (float(x) for x in np.percentile(sims, [2.5, 97.5]))
    top_net = float(np.mean(top)) - COST
    status = ("罠の目印（兆し）" if hi < 0 and top_net < 0 else
              "強さの目印（兆し）" if lo > 0 and top_net > 0 else "見えない")
    st["verdict_j46"] = {"decided_on": cut, "n": cnt, "days_compared": len(diffs), "mean_diff": mean,
                         "lo": lo, "hi": hi, "top_net": top_net, "status": status}
    return st["verdict_j46"]


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
    v46 = st.get("verdict_j46")
    if v46:
        L.append(f"J46 判定（{v46['decided_on']}・{v46['n']}件・比べた日 {v46['days_compared']}）：寄り前の売買代金 多い組 − 少ない組 の"
                 f"寄り→9:30 {v46['mean_diff'] * 100:+.2f}％（95％の幅 {v46['lo'] * 100:+.2f}〜{v46['hi'] * 100:+.2f}％）・"
                 f"多い組の費用後 {v46['top_net'] * 100:+.2f}％ → {v46['status']}")
    else:
        recs = j46_records(st)
        L.append(f"J46（寄り前の売買代金の多さ）：{J46_START} からの記録 {len(recs)}件・{len({r['date'] for r in recs})}営業日"
                 f"（{J46_GOAL}件で1回だけ判定・あと {max(0, J46_GOAL - len(recs))}件）。途中の平均は出さない")
    return "\n".join(L)


def fetch_base_tv(date, codes):
    """Yahoo の日足から {コード: ふだんの売買代金（円）}。コードは記録に残さない（画面の数字を足すときだけ使う）"""
    import yori_lab as Y          # 記録と判定だけのときに Yahoo の道具を読み込まない
    out = {}
    for code in codes:
        bars = Y.fetch_chart(code, "1d", "3mo") or []
        out[code] = base_turnover([(t.strftime("%Y-%m-%d"), c, v) for t, _, _, _, c, v in bars], date)
    return out


def main(argv):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add")
    for k in ("date",):
        a.add_argument(f"--{k}", required=True)
    for k in ("prev", "mid857", "open", "p930"):
        a.add_argument(f"--{k}", type=float, required=True)
    for k in ("best-ask", "next-ask", "best-bid", "next-bid", "ask-qty", "bid-qty", "mkt-sell", "mkt-buy", "base-tv"):
        a.add_argument(f"--{k}", type=float, default=None)
    sub.add_parser("status")
    b = sub.add_parser("basetv")
    b.add_argument("--date", required=True)
    b.add_argument("codes", nargs="+")
    args = ap.parse_args(argv)
    if args.cmd == "basetv":
        for code, v in fetch_base_tv(args.date, args.codes).items():
            print(f"{code}\t{v:.0f}" if v else f"{code}\t（取れない）")
        return 0
    st = load()
    if args.cmd == "add":
        pre = None
        if args.ask_qty is not None or args.bid_qty is not None:
            if not args.base_tv:
                raise SystemExit("🚨 J46 の数量を渡すときは --base-tv（ふだんの売買代金・円）も渡す")
            pre = pre_tv_ratio(args.mid857, args.ask_qty, args.bid_qty, args.mkt_sell, args.mkt_buy, args.base_tv)
        rec = make_record(args.date, args.prev, args.mid857, args.open, args.p930,
                          args.best_ask, args.next_ask, args.best_bid, args.next_bid, pre)
        add(st, rec)
        save(st)
        print(f"足した：{rec['date']}（8:57 の窓 {rec['gap857'] * 100:+.2f}％ → 寄りの窓 {rec['gap_open'] * 100:+.2f}％）")
    else:
        had = (bool(st.get("verdict")), bool(st.get("verdict_j46")))
        judge(st)
        judge_j46(st)
        if (bool(st.get("verdict")), bool(st.get("verdict_j46"))) != had:
            save(st)
    print(status_text(st))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
