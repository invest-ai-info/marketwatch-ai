# -*- coding: utf-8 -*-
"""オーナーの裁量の取引の記録（段3）。PILLAR_PREREG.md「OJ」・MY_TRADING_RULES.md「デイトレ開始にあたっての事前登録」（2026-07-26）。

2026-11-24 オーナー「最終的にはシステムトレードで高勝率のトレードを目指したい」→「1段と3段を並行してください」。
オーナーが MT4 の注文の行（とチャート）を送ってくれたら、セッションが1件ずつ足す。
- 物差し＝**費用を引いた後の R**（MT4 の約定値は買いが買値・決済が売値＝スプレッドは結果にもう入っている）。
  R＝損益（pips）÷ 損切りまでの幅（pips）。損切りの逆指値が無い取引は R を出せない＝数えずに別に数える
- 決まりの紙 v1（PILLAR_PREREG.md「OJ」）の項目を ○×（True/False・わからなければ None）で残す
- ⚠️ 残すのは値段・pips・R・○× だけ。**ロット・円の損益・口座の番号・名前は残さない**（公開リポジトリのため）
- ⚠️ 判定は 7/26 の事前登録どおり **30件ごと（30・60・90…）に1回だけ**。それまで平均は出さない（途中の数字を見て続け方を変えないため）。
  判定＝その時点の全件の R の平均の95%の幅（日ごとのまとまりで引き直す・10,000回）。下限>0＝機能している／上限<0＝反証／ほか＝まだ分からない。
  同じ日に、項目ごとの ○ と × の平均を「読むための表」として出す（決まりにはしない＝決まりにするなら段2の過去のデータか別の前向きで確かめる）

使い方:
  python trade_journal.py add --id 30211960 --pair GBPJPY --side buy \
      --open "2026.11.24 09:04:08" --entry 207.605 --sl 207.469 --tp 207.778 \
      --close "2026.11.24 09:27:03" --exit 207.734 --spread 1.8 --server-time \
      --entry-type ema15 --push 2 --sl-line 207.51 \
      --flags tokyo_break=1,strongest=1,htf_aligned=0,tp_before_high=0,event_clear=1,sl_at_line=1 \
      --note "ユーロドルの直近安値のラインと比べ、上に強いほうのポンド円"
  python trade_journal.py status
  （--server-time＝MT4 の画面の時刻（BigBoss のサーバー時刻）を日本時間に直す。冬＝+7時間・夏＝+6時間）
"""
import argparse
import datetime as dt
import json
import random
import sys

JOURNAL = "trade-journal.json"
START = "2026-11-24"          # 記録を始めた日（PILLAR_PREREG.md「OJ」の登録の日）
CHECK_EVERY = 30              # 7/26 の事前登録の刻み（signal_lab_tracker の PROMOTE_MIN_N_HOLDOUT と同じ）
N_BOOT = 10000
SEED = 20261124
WINDOW = ("15:00", "16:55")   # 決まりの紙 v1 の入る時間（TB と同じ・日本時間）
SPREAD_MAX = 2.5              # 決まりの紙 v1：スプレッドがこれより広ければ入らない（pips）
COST_MULT = 7.0               # 決まりの紙 v1：損切りの幅はスプレッドの7倍以上（費用 0.15R 以下）
# 手で付ける項目（決まりの紙 v1 の部品）。自動で付く3つ（in_window・sl_order・spread_ok）は数字から決める
MANUAL_FLAGS = ("tokyo_break", "strongest", "htf_aligned", "tp_before_high", "event_clear", "sl_at_line")
AUTO_FLAGS = ("in_window", "sl_order", "spread_ok")
ENTRY_TYPES = ("ema15", "line", "other")
# 何押しで入ったか（2026-11-24 夜 オーナー「1押し、2押しで入った場合は1押しの方の直近安値のラインで損切り」）
PUSHES = ("break", "1", "2", "3+")
# 入口が決まりの紙 v1 に全部当てはまるか（出口の tp_before_high と、段2で腕にする htf_aligned は入れない）
V1_ENTRY = ("tokyo_break", "in_window", "strongest", "sl_order", "event_clear", "spread_ok")


def empty_state():
    return {"registered": "OJ", "start": START, "check_every": CHECK_EVERY, "trades": [], "checkpoints": []}


def load(path=JOURNAL):
    try:
        with open(path, encoding="utf-8") as fh:
            st = json.load(fh)
    except FileNotFoundError:
        return empty_state()
    if st.get("start") != START:
        raise SystemExit(f"🚨 {path} の開始日 {st.get('start')} が {START} と違う＝上書きしない")
    return st


def save(st, path=JOURNAL):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(st, fh, ensure_ascii=False, indent=1)
        fh.write("\n")


def us_dst(day):
    """米国の夏時間か（3月の第2日曜〜11月の第1日曜）。BigBoss のサーバー時刻はこれに合わせて GMT+3／+2 を切り替える"""
    y = day.year
    mar = dt.date(y, 3, 8) + dt.timedelta(days=(6 - dt.date(y, 3, 8).weekday()) % 7)
    nov = dt.date(y, 11, 1) + dt.timedelta(days=(6 - dt.date(y, 11, 1).weekday()) % 7)
    return mar <= day < nov


def server_to_jst(t):
    """MT4（BigBoss）のサーバー時刻 → 日本時間。冬（GMT+2）＝+7時間・夏（GMT+3）＝+6時間"""
    return t + dt.timedelta(hours=6 if us_dst(t.date()) else 7)


def parse_time(s):
    s = s.strip().replace("/", ".").replace("-", ".")
    for fmt in ("%Y.%m.%d %H:%M:%S", "%Y.%m.%d %H:%M"):
        try:
            return dt.datetime.strptime(s, fmt)
        except ValueError:
            pass
    raise SystemExit(f"🚨 時刻が読めない：{s}")


def pip_size(pair):
    return 0.01 if pair.upper().endswith("JPY") else 0.0001


def parse_flags(text):
    out = {k: None for k in MANUAL_FLAGS}
    for part in (text or "").split(","):
        if not part.strip():
            continue
        k, _, v = part.partition("=")
        k = k.strip()
        if k not in MANUAL_FLAGS:
            raise SystemExit(f"🚨 知らない項目：{k}（使えるのは {', '.join(MANUAL_FLAGS)}）")
        v = v.strip().lower()
        out[k] = None if v in ("", "?", "none") else v in ("1", "true", "yes", "y", "o", "○")
    return out


def make_trade(tid, pair, side, t_open, entry, sl, tp, t_close, exit_, spread=None, pip=None,
               entry_type="other", flags=None, note="", used_for_rule=False, push=None, sl_line=None):
    """MT4 の行の数字 → 記録（値段・pips・R・○×だけ）。t_open・t_close は日本時間。純関数

    used_for_rule＝決まりの紙を作るのに使った取引（11/24 のポンド円）。7/26 の判定には数えるが、読むための表からは外す
    push＝何押しで入ったか（break＝ブレイクラインまでの戻り・1・2・3+）。sl_line＝決まりの損切りの線（ブレイクラインか1押しの安値）の値段
    → 逆指値がその線からどれだけ離れていたか（sl_buffer_pips・余白）を残す＝段2の前に余白を決めるため（成績は見ない）
    """
    side = side.lower()
    if side not in ("buy", "sell"):
        raise ValueError("side は buy か sell")
    if entry_type not in ENTRY_TYPES:
        raise ValueError(f"entry_type は {ENTRY_TYPES}")
    if push is not None and push not in PUSHES:
        raise ValueError(f"push は {PUSHES}")
    pip = pip or pip_size(pair)
    sgn = 1 if side == "buy" else -1
    sl = sl if sl else None             # MT4 の 0.00000＝逆指値なし
    tp = tp if tp else None
    pnl = round((exit_ - entry) * sgn / pip, 1)
    risk = round(abs(entry - sl) / pip, 1) if sl is not None else None
    if risk is not None and (sl - entry) * sgn >= 0:
        raise ValueError("損切りが入った値の利益側にある（入力の取り違え？）")
    r_net = round(pnl / risk, 3) if risk else None
    buf = round((sl_line - sl) * sgn / pip, 1) if (sl is not None and sl_line) else None
    cost_r = round(spread / risk, 3) if (risk and spread is not None) else None
    r_gross = round((pnl + spread) / risk, 3) if (risk and spread is not None) else None
    kind = "manual"
    if sl is not None and abs(exit_ - sl) <= pip * 0.5:
        kind = "sl"
    elif tp is not None and abs(exit_ - tp) <= pip * 0.5:
        kind = "tp"
    f = dict(flags or {k: None for k in MANUAL_FLAGS})
    hm = t_open.strftime("%H:%M")
    f["in_window"] = WINDOW[0] <= hm <= WINDOW[1]
    f["sl_order"] = sl is not None
    f["spread_ok"] = (spread <= SPREAD_MAX and risk >= COST_MULT * spread) if (risk and spread is not None) else (
        False if (spread is not None and spread > SPREAD_MAX) else None)
    vals = [f.get(k) for k in V1_ENTRY]
    fits = (False if (False in vals or entry_type != "ema15") else (None if None in vals else True))
    return {"id": str(tid), "date": t_open.strftime("%Y-%m-%d"), "entry_time": t_open.strftime("%H:%M:%S"),
            "exit_time": t_close.strftime("%H:%M:%S"), "hold_min": round((t_close - t_open).total_seconds() / 60, 1),
            "pair": pair.upper(), "side": side, "entry": entry, "sl": sl, "tp": tp, "exit": exit_,
            "spread_pips": spread, "risk_pips": risk, "pnl_pips": pnl, "r_net": r_net, "r_gross": r_gross,
            "cost_r": cost_r, "exit_kind": kind, "entry_type": entry_type, "push": push, "sl_line": sl_line,
            "sl_buffer_pips": buf, "flags": f, "fits_v1_entry": fits,
            "used_for_rule": bool(used_for_rule), "note": note}


def add(st, trade):
    if trade["date"] < START:
        raise SystemExit(f"🚨 {trade['date']} は {START} より前＝この記録には入れない（過去の取引は別に扱う）")
    if any(t["id"] == trade["id"] for t in st["trades"]):
        raise SystemExit(f"🚨 注文番号 {trade['id']} はもう記録してある（二重に足さない）")
    st["trades"].append(trade)
    st["trades"].sort(key=lambda t: (t["date"], t["entry_time"]))
    return st


def counted(st):
    """R を出せる取引（損切りの逆指値があったもの）を時刻順に"""
    return [t for t in st["trades"] if t.get("r_net") is not None]


def boot_ci(trades, n_boot=N_BOOT, seed=SEED):
    """日ごとのまとまりで引き直した平均の95%の幅。純関数"""
    days = {}
    for t in trades:
        days.setdefault(t["date"], []).append(t["r_net"])
    blocks = list(days.values())
    rng = random.Random(seed)
    means = []
    for _ in range(n_boot):
        pick = [x for _ in blocks for x in rng.choice(blocks)]
        means.append(sum(pick) / len(pick))
    means.sort()
    return means[int(0.025 * n_boot)], means[int(0.975 * n_boot) - 1]


def verdict_of(lo, hi):
    if lo > 0:
        return "機能している（サイズは据え置き。上げるのは次の判定でも下限>0のとき）"
    if hi < 0:
        return "反証（手を止めて設計に戻る＝土俵・時間帯・費用のどれが効いているかを潰す）"
    return "まだ分からない（サイズを上げない・続けてよい）"


def reading_table(trades):
    """項目ごとの ○ と × の R の平均と件数（読むだけ・決まりの紙を作るのに使った取引は外す）"""
    trades = [t for t in trades if not t.get("used_for_rule")]
    rows = {}
    for k in V1_ENTRY + ("htf_aligned", "tp_before_high", "sl_at_line"):
        for v in (True, False):
            xs = [t["r_net"] for t in trades if t["flags"].get(k) is v]
            rows[f"{k}={'o' if v else 'x'}"] = {"n": len(xs), "mean": round(sum(xs) / len(xs), 3) if xs else None}
    for v in (True, False):
        xs = [t["r_net"] for t in trades if t.get("fits_v1_entry") is v]
        rows[f"fits_v1_entry={'o' if v else 'x'}"] = {"n": len(xs), "mean": round(sum(xs) / len(xs), 3) if xs else None}
    return rows


def run_checkpoints(st, n_boot=N_BOOT, seed=SEED):
    """30件の倍数に届いた判定を、まだ出していない分だけ1回ずつ出して固定する"""
    rs = counted(st)
    done = {c["n"] for c in st["checkpoints"]}
    for n in range(CHECK_EVERY, len(rs) + 1, CHECK_EVERY):
        if n in done:
            continue
        part = rs[:n]
        lo, hi = boot_ci(part, n_boot, seed)
        mean = sum(t["r_net"] for t in part) / n
        wins = sum(1 for t in part if t["r_net"] > 0)
        st["checkpoints"].append({
            "n": n, "through": part[-1]["date"], "days": len({t["date"] for t in part}),
            "mean_r": round(mean, 3), "lo": round(lo, 3), "hi": round(hi, 3), "win_rate": round(wins / n, 3),
            "verdict": verdict_of(lo, hi), "reading": reading_table(part)})
    return st


def status_text(st):
    rs = counted(st)
    no_sl = [t for t in st["trades"] if t.get("r_net") is None]
    nxt = (len(rs) // CHECK_EVERY + 1) * CHECK_EVERY
    L = [f"OJ 裁量の取引の記録（{START} から）：R を出せる取引 {len(rs)}件・{len({t['date'] for t in rs})}日"
         f"（次の判定は {nxt}件目・あと {nxt - len(rs)}件。途中の平均は出さない）"]
    if no_sl:
        L.append(f"⚠️ 損切りの逆指値が無く R を出せない取引 {len(no_sl)}件（数えない）：" +
                 "・".join(f"{t['date']} {t['pair']}" for t in no_sl))
    fit = sum(1 for t in rs if t.get("fits_v1_entry") is True)
    L.append(f"決まりの紙 v1 の入口に全部当てはまった取引 {fit}件（成績は判定の日にだけ出す）")
    for c in st["checkpoints"]:
        L.append(f"判定（{c['n']}件・{c['through']} まで・{c['days']}日）：平均 {c['mean_r']:+.3f}R"
                 f"（95%の幅 {c['lo']:+.3f}〜{c['hi']:+.3f}）・勝率 {c['win_rate'] * 100:.0f}% → {c['verdict']}")
    return "\n".join(L)


def main(argv):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add")
    a.add_argument("--id", required=True)
    a.add_argument("--pair", required=True)
    a.add_argument("--side", required=True)
    a.add_argument("--open", required=True)
    a.add_argument("--close", required=True)
    for k in ("entry", "exit"):
        a.add_argument(f"--{k}", type=float, required=True)
    for k in ("sl", "tp", "spread", "pip"):
        a.add_argument(f"--{k}", type=float, default=None)
    a.add_argument("--server-time", action="store_true", help="時刻は MT4 の画面の時刻（サーバー時刻）")
    a.add_argument("--entry-type", default="other", choices=ENTRY_TYPES)
    a.add_argument("--push", default=None, choices=PUSHES, help="何押しで入ったか")
    a.add_argument("--sl-line", type=float, default=None, help="決まりの損切りの線（ブレイクラインか1押しの安値）")
    a.add_argument("--flags", default="")
    a.add_argument("--note", default="")
    a.add_argument("--used-for-rule", action="store_true", help="決まりの紙を作るのに使った取引（読むための表から外す）")
    sub.add_parser("status")
    args = ap.parse_args(argv)
    st = load()
    if args.cmd == "add":
        t_open, t_close = parse_time(args.open), parse_time(args.close)
        if args.server_time:
            t_open, t_close = server_to_jst(t_open), server_to_jst(t_close)
        tr = make_trade(args.id, args.pair, args.side, t_open, args.entry, args.sl, args.tp, t_close, args.exit,
                        args.spread, args.pip, args.entry_type, parse_flags(args.flags), args.note,
                        args.used_for_rule, args.push, args.sl_line)
        add(st, tr)
        r = f"{tr['r_net']:+.2f}R" if tr["r_net"] is not None else "R なし（逆指値なし）"
        print(f"足した：{tr['date']} {tr['entry_time']} {tr['pair']} {tr['side']}・{tr['pnl_pips']:+.1f}pips・{r}")
    had = len(st["checkpoints"])
    run_checkpoints(st)
    if args.cmd == "add" or len(st["checkpoints"]) != had:
        save(st)
    print(status_text(st))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
