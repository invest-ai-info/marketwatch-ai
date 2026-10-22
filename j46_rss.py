# -*- coding: utf-8 -*-
"""J46R 寄り前の売買代金の多さ（マーケットスピード II RSS で自動に記録する版）。PILLAR_PREREG.md「J46」の追記（J46R）。

手元の PC（楽天 マーケットスピード II RSS＋Excel）が 8:59:30 と 9:30:05 ごろに取った生の値（手元の research/rss/ だけに置く）を、
比率だけの記録にして j46-rss.json に足す（手元から送る）。判定は記録が1000件以上かつ20営業日以上になった日に1回だけ
（比べ方は J46 と同じ＝j10b_records.compare_within_day）。2026-10-22 オーナー「指示文作ってください」。

⚠️ j46-rss.json には比率だけ（銘柄コード・値段は残さない）。生の CSV は送らない（research/ は SYNC禁忌）。
⚠️ diag は件数と形と pre_tv の大きさの目安だけ。寄り→9:30 は出さない（試運転で値動きを見ないため）。
⚠️ 1日は一度だけ足す（同じ日をもう一度 convert しても足さない）。start より前の日は足さない（試運転の日は数えない）。

生の CSV の形（手元の取り込みの道具がこの見出しで書く・1行1銘柄・UTF-8）:
  8:59  date,time,code,prev_close,ask,ask_qty,bid,bid_qty,mkt_sell_qty,mkt_buy_qty,ask_flag,bid_flag
  9:30  date,time,code,open,last,last_time
  数量の単位は RSS のまま渡し、--qty-unit で株に直す（株なら 1・百株なら 100）。値の無い欄は空か「-」

使い方（手元）:
  python j46_rss.py diag --date 2026-10-26 --snap859 research/rss/raw/2026-10-26_0859.csv [--snap930 ...] [--qty-unit 1]
  python j46_rss.py start --date 2026-10-27      # 試運転が済んだら、数え始める日を1回だけ決める
  python j46_rss.py convert --date 2026-10-27 --snap859 ... --snap930 ... [--qty-unit 1] [--special-flags 特]
  python j46_rss.py status
"""
import argparse
import csv
import json
import sys

import j10b_records as B

RECORDS = "j46-rss.json"
GOAL_N = 1000            # 記録が1000件以上
GOAL_DAYS = 20           # かつ20営業日以上（1日約400件で数日で1000件に届くため）
MIN_930 = "09:20"        # 9:30 の値の時刻がこれより前なら数えない
MAX_MOVE = 0.25          # 寄り→9:30 が ±25％ を超えたらデータの誤り（J10 と同じ）
COLS_859 = ("date", "time", "code", "prev_close", "ask", "ask_qty", "bid", "bid_qty", "mkt_sell_qty", "mkt_buy_qty",
            "ask_flag", "bid_flag")
COLS_930 = ("date", "time", "code", "open", "last", "last_time")


def empty_state():
    return {"registered": "J46R", "start": None, "goal_n": GOAL_N, "goal_days": GOAL_DAYS, "records": [], "days": {},
            "verdict": None}


def load(path=RECORDS):
    try:
        with open(path, encoding="utf-8") as fh:
            st = json.load(fh)
    except FileNotFoundError:
        return empty_state()
    if st.get("registered") != "J46R":
        raise SystemExit(f"🚨 {path} は J46R の記録ではない＝上書きしない")
    return st


def save(st, path=RECORDS):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(st, fh, ensure_ascii=False, indent=1)
        fh.write("\n")


def num(x):
    """'1,234.5'・''・'-' → float か None"""
    if x is None:
        return None
    s = str(x).strip().replace(",", "")
    if s in ("", "-", "--"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def norm_code(c):
    return str(c or "").strip().upper().replace(".T", "").replace(".JP", "")


def read_csv(path, cols):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    miss = [c for c in cols if rows and c not in rows[0]]
    if miss:
        raise SystemExit(f"🚨 {path} に見出し {miss} が無い（見出し＝{','.join(cols)}）")
    return rows


def hhmm(t):
    """'09:30:01'・'9:30'・'2026-10-27 09:30:01' → '09:30'（読めなければ ''）"""
    s = str(t or "").strip()
    if " " in s:
        s = s.split()[-1]
    parts = s.split(":")
    if len(parts) < 2 or not parts[0].isdigit() or not parts[1][:2].isdigit():
        return ""
    return f"{int(parts[0]):02d}:{int(parts[1][:2]):02d}"


def pre_values(r859, qty_unit=1, special=()):
    """8:59 の1行 → (中値, 前日終値, pre_tv の分子＝寄り前の売買代金の目安[円]) か、数えない理由の文字列"""
    flags = " ".join(str(r859.get(k) or "") for k in ("ask_flag", "bid_flag"))
    if any(m in flags for m in special):
        return "特別気配"
    ask, bid, aq, bq = (num(r859.get(k)) for k in ("ask", "bid", "ask_qty", "bid_qty"))
    prev = num(r859.get("prev_close"))
    if not ask or not bid or not aq or not bq or ask <= 0 or bid <= 0 or aq <= 0 or bq <= 0:
        return "片側の気配が無い"
    if not prev or prev <= 0:
        return "前日終値が無い"
    mid = (ask + bid) / 2
    sell = (num(r859.get("mkt_sell_qty")) or 0) + aq
    buy = (num(r859.get("mkt_buy_qty")) or 0) + bq
    return mid, prev, (sell + buy) / 2 * qty_unit * mid


def make_records(date, rows859, rows930, base, qty_unit=1, special=()):
    """生の行 → (比率だけの記録の一覧, 数えなかった理由ごとの件数)。base＝{コード: ふだんの売買代金（円）}。純関数"""
    at930 = {norm_code(r.get("code")): r for r in rows930 if str(r.get("date") or date)[:10] == date}
    recs, skipped = [], {}

    def skip(why):
        skipped[why] = skipped.get(why, 0) + 1

    for r in rows859:
        if str(r.get("date") or date)[:10] != date:
            skip("日付が違う")
            continue
        code = norm_code(r.get("code"))
        pv = pre_values(r, qty_unit, special)
        if isinstance(pv, str):
            skip(pv)
            continue
        mid, prev, value = pv
        bt = base.get(code)
        if not bt or bt <= 0:
            skip("ふだんの売買代金が無い")
            continue
        r9 = at930.get(code)
        op, last = (num(r9.get("open")), num(r9.get("last"))) if r9 else (None, None)
        if not op or not last or op <= 0 or last <= 0:
            skip("寄っていない・9:30 の値が無い")
            continue
        if hhmm(r9.get("last_time")) < MIN_930:
            skip("9:30 の値が古い")
            continue
        r930 = last / op - 1
        if abs(r930) > MAX_MOVE:
            skip("データの誤り（±25％超）")
            continue
        rec = {"date": date, "gap859": mid / prev - 1, "gap_open": op / prev - 1, "r930": r930, "pre_tv": value / bt}
        recs.append({k: (round(v, 6) if isinstance(v, float) else v) for k, v in rec.items()})
    return recs, skipped


def add_day(st, date, recs, skipped):
    """1日分を足す。start が無い・start より前・もう足した日なら足さない（理由を返す）"""
    if not st.get("start"):
        return "まだ start を決めていない（試運転の日は数えない）"
    if date < st["start"]:
        return f"{date} は start {st['start']} より前＝数えない"
    if date in st["days"]:
        return f"{date} はもう足した（1日は一度だけ）"
    st["records"] += recs
    st["days"][date] = {"n": len(recs), "skipped": skipped}
    return None


def judge(st, n_boot=B.N_BOOT, seed=B.J46_SEED):
    """記録が1000件以上かつ20営業日以上になった日までの記録で1回だけ判定して固定する"""
    if st.get("verdict"):
        return st["verdict"]
    days = sorted(st["days"])
    cnt, cut = 0, None
    for k, d in enumerate(days, 1):
        cnt += st["days"][d]["n"]
        if cnt >= GOAL_N and k >= GOAL_DAYS:
            cut = d
            break
    if cut is None:
        return None
    v = B.compare_within_day([r for r in st["records"] if r["date"] <= cut], n_boot, seed)
    st["verdict"] = {"decided_on": cut, "n": cnt, "days": len([d for d in days if d <= cut]), **v}
    return st["verdict"]


def status_text(st):
    n, days = len(st["records"]), len(st["days"])
    L = [f"J46R（RSS・寄り前の売買代金の多さ）：start {st.get('start') or '未定（試運転中）'}・記録 {n}件・{days}営業日"
         f"（{GOAL_N}件以上かつ{GOAL_DAYS}営業日以上で1回だけ判定）"]
    v = st.get("verdict")
    if v:
        L.append(f"判定（{v['decided_on']}・{v['n']}件・{v['days']}営業日・比べた日 {v['days_compared']}）：多い組 − 少ない組 の"
                 f"寄り→9:30 {v['mean_diff'] * 100:+.2f}％（95％の幅 {v['lo'] * 100:+.2f}〜{v['hi'] * 100:+.2f}％）・"
                 f"多い組の費用後 {v['top_net'] * 100:+.2f}％ → {v['status']}")
    else:
        L.append(f"まだ判定しない（あと {max(0, GOAL_N - n)}件・{max(0, GOAL_DAYS - days)}営業日）。途中の平均は出さない")
    if st["days"]:
        last = sorted(st["days"])[-1]
        L.append(f"最後の日 {last}：{st['days'][last]['n']}件・数えなかった {st['days'][last]['skipped'] or 'なし'}")
    return "\n".join(L)


def diag_text(date, rows859, rows930, base=None, qty_unit=1, special=()):
    """試運転用：件数と形と pre_tv の大きさの目安だけ（寄り→9:30 は出さない）"""
    L = [f"diag {date}：8:59 の行 {len(rows859)}・9:30 の行 {len(rows930)}"]
    why, pres = {}, []
    for r in rows859:
        pv = pre_values(r, qty_unit, special)
        if isinstance(pv, str):
            why[pv] = why.get(pv, 0) + 1
        elif base is not None and base.get(norm_code(r.get("code"))):
            pres.append(pv[2] / base[norm_code(r.get("code"))])
    L.append(f"  8:59 で数えられない行：{why or 'なし'}")
    flags = {}
    for r in rows859:
        for k in ("ask_flag", "bid_flag"):
            f = str(r.get(k) or "").strip()
            flags[f or "（空）"] = flags.get(f or "（空）", 0) + 1
    L.append(f"  気配の印の種類と数（売り・買いの合計）：{flags}")
    times = sorted(hhmm(r.get("time")) for r in rows859 if hhmm(r.get("time")))
    if times:
        L.append(f"  8:59 の取った時刻：{times[0]}〜{times[-1]}")
    if pres:
        pres.sort()
        q = [pres[int(len(pres) * x)] for x in (0.1, 0.5, 0.9)]
        L.append(f"  pre_tv（寄り前の売買代金 ÷ ふだんの1日）の 10%・50%・90% 点：{q[0] * 100:.1f}%・{q[1] * 100:.1f}%・"
                 f"{q[2] * 100:.1f}%（{len(pres)}銘柄。50% 点が 0.1% 未満や 1000% 超なら数量の単位を疑う）")
    if rows930:
        opened = sum(1 for r in rows930 if num(r.get("open")))
        lt = sorted(hhmm(r.get("last_time")) for r in rows930 if hhmm(r.get("last_time")))
        L.append(f"  9:30 の行：始値あり {opened}/{len(rows930)}"
                 + (f"・現在値の時刻 {lt[0]}〜{lt[-1]}（{MIN_930} より前は {sum(1 for t in lt if t < MIN_930)}件）" if lt else ""))
    L.append("  （寄り→9:30 は出さない＝試運転で値動きを見ない）")
    return "\n".join(L)


def main(argv):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("diag", "convert"):
        a = sub.add_parser(name)
        a.add_argument("--date", required=True)
        a.add_argument("--snap859", required=True)
        a.add_argument("--snap930", required=(name == "convert"))
        a.add_argument("--qty-unit", type=float, default=1.0)
        a.add_argument("--special-flags", default="", help="特別気配を表す印（カンマ区切り・その文字を含めば数えない）")
        a.add_argument("--no-base", action="store_true", help="diag で Yahoo の日足を取らない")
    s = sub.add_parser("start")
    s.add_argument("--date", required=True)
    sub.add_parser("status")
    args = ap.parse_args(argv)
    st = load()
    if args.cmd == "status":
        if judge(st) and st["verdict"]:
            save(st)
        print(status_text(st))
        return 0
    if args.cmd == "start":
        if st.get("start"):
            raise SystemExit(f"🚨 start はもう {st['start']} に決まっている（変えない）")
        st["start"] = args.date
        save(st)
        print(f"start＝{args.date}（この日から数える・試運転の日は数えない）")
        return 0
    special = tuple(x for x in args.special_flags.split(",") if x)
    rows859 = read_csv(args.snap859, COLS_859)
    rows930 = read_csv(args.snap930, COLS_930) if args.snap930 else []
    codes = sorted({norm_code(r.get("code")) for r in rows859 if norm_code(r.get("code"))})
    if args.cmd == "diag":
        base = None if args.no_base else B.fetch_base_tv(args.date, codes)
        print(diag_text(args.date, rows859, rows930, base, args.qty_unit, special))
        return 0
    if args.date in st["days"]:
        print(f"{args.date} はもう足した（1日は一度だけ）")
        return 0
    base = B.fetch_base_tv(args.date, codes)
    recs, skipped = make_records(args.date, rows859, rows930, base, args.qty_unit, special)
    why = add_day(st, args.date, recs, skipped)
    if why:
        print(f"足さなかった：{why}")
        return 0
    judge(st)
    save(st)
    print(f"足した：{args.date} {len(recs)}件（数えなかった {skipped or 'なし'}）")
    print(status_text(st))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
