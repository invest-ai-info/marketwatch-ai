# -*- coding: utf-8 -*-
"""SB シリーズの抜けにすぐ乗る：東京時間の線（8:00〜15:00 に始まる5分足の高値の最大・安値の最小）を、1つのシリーズの中で
2ペア以上が同じ5分足の終値で抜けたら、抜けたペアのうち一番動いたペアに次の足の始値で入る。2026-11-25 夜 登録・PILLAR_PREREG.md「SB」。

オーナー「そしたら条件はすべて同じで、入り口だけシリーズでブレイクしたらすぐに入る。クロス円かドルストレートかユーロシリーズか
ポンドシリーズか豪ドルシリーズか。そのうち2つ以上が同時にブレイクしたらエントリーするという条件で。ブレイクラインを戻したら損切り。
利確はエントリーしてから20ピップスのところで利食い。で検証をしてください。」
→ 聞いて決めたこと（4つとも選んでもらった答え）：2つ以上＝1つのシリーズの中で2ペア以上／入るペア＝抜けたペアで一番動いたもの／
  損切り＝線の4pips外（v2〜v5 と同じ）／損切りの幅がスプレッドの7倍に届かなければ入らない（決まりどおり）

決まりの要点（全文は PILLAR_PREREG.md「SB」・ここの定数に固定）:
- 入る時間＝決まりの紙 v5（追記⑫⑭）：ロンドンの始まり L（冬 17:00・夏 16:00）の60分前〜5分前の前（冬 16:00〜16:54）と、
  30分後〜120分後の前（冬 17:30〜18:59）。月〜木だけ。15:00 の足は線に使うので、合図の足は 15:05 から（夏の前の窓）
- 合図＝窓の中の足で、そのシリーズの「同じ向きに線の外で終わったペアの数」が 2 以上になった最初の足（1本前は 2 未満）。
  シリーズ・向き・窓（前／後）ごとに1回だけ
- 入るペア＝その足で線の外にあるペアのうち、窓の基準（前の窓＝窓の最初の足の始値・後の窓＝始まりの足の始値）からの動き（%・抜けた向き）が
  いちばん大きいペア。入る＝次の足の始値（買いは買値・売りは売値）
- 損切り＝割った線の 4pips 外（逆指値・足の中で届いたらその値・始値で飛び越えたら始値）／利確＝入った値から 20pips（指値）。
  同じ足で両方に届いたら損切りが先。時間切れ＝前の窓は始まりの5分前（冬 16:55）・後の窓は始まりの120分後（冬 19:00）の足の始値。
  発表の60分前〜30分後は入らない・5分前に手じまい（KT1・FLH と同じ）
- 見送り：スプレッドが 2.5pips より広い／損切りまでの幅がスプレッドの7倍に届かない／入る値がもう線の内側／そのペアを持っている

⚠️ データは手元にだけある＝**手元で1回だけ**回す。値動きはクラウドでは見ていない（この道具は 2026-11-25 にクラウドで作った）。
実行（手元）:
  python series_break_lab.py check --dir C:\\mt5run --duka C:\\mt5run\\duka_fx   （足・線・合図・入れた数・見送りの理由だけ。損益は数えない・何も書き出さない）
  python series_break_lab.py run   --dir C:\\mt5run --duka C:\\mt5run\\duka_fx   （本番・1回だけ → series-break-lab.json（送る）・research/oikawa/series-break-result.md と取引の CSV（手元））
"""
import argparse
import datetime as dt
import hashlib
import json
import math
import os
import re
import sys

import numpy as np
import pandas as pd

import kata1_lab as K
import oikawa_lab as OK

# ════════════════════ 事前登録の値（PILLAR_PREREG.md「SB」） ════════════════════
PAIRS = OK.PAIRS                         # ドル円・ユーロドル・ポンドドル・ユーロ円・ポンド円・豪ドル円・豪ドル米ドル（手元の MT5 の書き出しにある7つ）
SEEN_START = K.SEEN_START                # A＝MT5（BigBoss）の5分足 2022-06-01〜
OLD = K.OLD                              # B＝Dukascopy の1分足 → 5分足 2017-01-01〜2022-05-31
SPLIT_A = "2024-08-01"                   # A の前半＝〜2024-07-31／後半＝2024-08-01〜
SPLIT_B = "2019-10-01"                   # B の前半＝〜2019-09-30／後半＝2019-10-01〜
JST = K.JST
LINE = K.LINE                            # 線＝8:00〜15:00 に始まる足（両端を含む＝85本）
LINE_BARS = K.LINE_BARS
LINE_MAX_MISSING = K.LINE_MAX_MISSING    # 欠けが10本を超える日はそのペアを使わない（ほかのペアは使う）
EARLIEST = K.EARLIEST                    # 合図の足は 15:05 に始まる足から（15:00 の足は線に使う）
BEFORE_FROM, FLAT_BEFORE, WAIT_AFTER, END_AFTER = 60, 5, 30, 120   # 始まり L からの分：前の窓 [L−60, L−5)・後の窓 [L+30, L+120)
# シリーズ（オーナーの言葉の5つ・7ペアの中で）。どのシリーズも、中のペアは同じ通貨を同じ側に持つ＝「同じ向き」＝線を抜けた向きが同じ
SERIES = {
    "クロス円": ("USDJPY", "EURJPY", "GBPJPY", "AUDJPY"),
    "ドルストレート": ("EURUSD", "GBPUSD", "AUDUSD"),
    "ユーロ": ("EURJPY", "EURUSD"),
    "ポンド": ("GBPJPY", "GBPUSD"),
    "豪ドル": ("AUDJPY", "AUDUSD"),
}
MIN_PAIRS = 2                            # 1つのシリーズの中で2ペア以上
SL_OUT = 4.0                             # 損切り＝割った線の 4pips 外
TP_PIPS = 20.0                           # 利確＝入った値から 20pips
SPREAD_MAX = 2.5                         # スプレッドがこれより広ければ入らない（pips）
COST_MULT = 7.0                          # 損切りの幅はスプレッドの7倍以上
EV_BEFORE, EV_AFTER, EV_EXIT = K.EV_BEFORE, K.EV_AFTER, K.EV_EXIT   # 発表の60分前〜30分後は入らない・5分前に手じまい
EVENTS = K.EVENTS                        # FLH の発表の一覧（手元・UTC）
COMMISSION = 0.8                         # 読むだけ：手数料 1回 0.8pips を引いた平均
N_MIN_A, N_MIN_B = 200, 100
Z = 1.959963984540054                    # 95% の幅（腕は1つ）
ALPHA = 0.05
N_PERM = 1000
SEED = 20261125
PREREG = "PILLAR_PREREG.md"
SECTION = "## SB シリーズの抜けにすぐ乗る"
OUT_JSON = "series-break-lab.json"
OUT_MD = os.path.join("research", "oikawa", "series-break-result.md")
OUT_CSV = os.path.join("research", "oikawa", "series-break-{}.csv")
TAG = "SB"
HEADING = "SB シリーズの抜けにすぐ乗る：1つのシリーズの中で2ペア以上が同時に東京の線を抜けたら、一番動いたペアに次の足で入る"
TITLES = {"SB": "シリーズの抜けにすぐ乗る（オーナーの案）：クロス円・ドルストレート・ユーロ・ポンド・豪ドルのどれかで、2ペア以上が同じ5分足で東京時間の線を抜けたら、"
                "抜けたペアで一番動いたものに次の足で入る・損切り＝線の4pips外・利確＝20pips（決まりの紙 v5 の時間・5分足・過去のデータ・1回だけ・手元の MT5 と Dukascopy）"}
SURVIVED = OK.SURVIVED
MIN = K.MIN                              # 1分（ns）
SKIPS = ("event", "spread", "cost7", "inside", "busy", "no_next")


def pip(p):
    return OK.pip(p)


# ════════════════════ 発表の一覧（7ペアに当てはめる） ════════════════════

CUR_PAIRS = {c: {p for p in PAIRS if c in (p[:3], p[3:])} for c in ("USD", "JPY", "EUR", "GBP", "AUD")}
YEN4 = {"USDJPY", "EURJPY", "GBPJPY", "AUDJPY"}


def read_events(path):
    """発表の一覧（FLH の flow-jpy-events.csv・時刻は UTC）→ {ペア: UTC の ns の並び}。
    FLH の一覧は円の4ペア向け：「ALL・4ペア・全」＝米国か日本の発表 → 7ペアとも（日本の発表もドルストレートに当てる＝見送りが少し多めになる側）／
    通貨の列（scope など）の EUR・GBP・AUD（CNY は AUD）→ その通貨を含むペア／行の中のペアの名前（EURJPY など）→ その円でない側の通貨を含むペア"""
    df = pd.read_csv(path, dtype=str, encoding="utf-8-sig").fillna("")
    low = {c.lower().strip(): c for c in df.columns}
    tcol = next((low[k] for k in ("utc", "time_utc", "datetime_utc", "utc_time", "time", "datetime", "when", "date_time", "t") if k in low), None)
    if tcol is None:
        for c in df.columns:
            if pd.to_datetime(df[c], errors="coerce", utc=True).notna().mean() > 0.9:
                tcol = c
                break
    if tcol is None:
        raise SystemExit(f"🚨 {path}：時刻の列が見つからない（列＝{list(df.columns)}）")
    t = pd.to_datetime(df[tcol], errors="coerce", utc=True)
    ccol = next((low[k] for k in ("scope", "currency", "ccy", "cur", "country") if k in low), None)
    alias = {"US": "USD", "JP": "JPY", "EU": "EUR", "GB": "GBP", "UK": "GBP", "AU": "AUD", "CNY": "AUD", "CN": "AUD"}
    out = {p: [] for p in PAIRS}
    for i in range(len(df)):
        if pd.isna(t.iloc[i]):
            continue
        text = " ".join(str(v) for c, v in df.iloc[i].items() if c != tcol).upper().replace("/", "")
        hit = set()
        named = set(re.findall(r"(USDJPY|EURJPY|GBPJPY|AUDJPY)", text))
        if named == YEN4 or (not named and re.search(r"(4ペア|ALL|全)", text)):
            hit = set(PAIRS)
        elif named:
            for p in named:
                hit |= CUR_PAIRS[p[:3]] if p != "USDJPY" else set(PAIRS)
        elif ccol:
            for tok in re.findall(r"[A-Z]{2,3}", str(df.iloc[i][ccol]).upper()):
                c = alias.get(tok, tok)
                hit |= set(PAIRS) if c in ("USD", "JPY") else CUR_PAIRS.get(c, set())
        for p in hit:
            out[p].append(t.iloc[i].value)
    return {p: np.array(sorted(set(v)), dtype=np.int64) for p, v in out.items()}


# ════════════════════ 日ごとの線・窓・合図 ════════════════════

def windows(day):
    """その日の窓 → {"前": (合図の足の最初, 入る足の終わり〔含まない〕, 動きの基準の足, 時間切れ), "後": (…)}（日本時間の分）"""
    L = K.london_open_minute(day)
    a0 = max(L - BEFORE_FROM, EARLIEST)
    return {"前": (a0, L - FLAT_BEFORE, a0, L - FLAT_BEFORE),
            "後": (L + WAIT_AFTER, L + END_AFTER, L, L + END_AFTER)}


def lines_of(D, a, b):
    """その日の線 → {ペア: (安値の最小, 高値の最大)}。足が足りないペアは入れない（そのペアはその日は抜けず・入らない）"""
    mn = D["minute"][a:b]
    sel = np.flatnonzero((mn >= LINE[0]) & (mn <= LINE[1])) + a
    out = {}
    for p in PAIRS:
        c = D["P"][p]["c"][sel]
        if np.isfinite(c).sum() < LINE_BARS - LINE_MAX_MISSING:
            continue
        out[p] = (float(np.nanmin(D["P"][p]["l"][sel])), float(np.nanmax(D["P"][p]["h"][sel])))
    return out


def beyond(D, lines, pairs, k, d):
    """足 k の終値で、向き d（+1＝高値の上・−1＝安値の下）に線の外にあるペア"""
    out = []
    for p in pairs:
        if p not in lines:
            continue
        c = D["P"][p]["c"][k]
        if not np.isfinite(c):
            continue
        if (d > 0 and c > lines[p][1]) or (d < 0 and c < lines[p][0]):
            out.append(p)
    return out


def find_signals(D, a, b, lines, win):
    """その日の合図 → [{"k", "series", "d", "seg", "cands"}]（時刻の順・同じ足ならシリーズの順）。シリーズ・向き・窓ごとに最初の1回だけ"""
    mn, T = D["minute"], D["T"]
    out = []
    for seg, (s0, e0, _ref, _x) in win.items():
        for name, pairs in SERIES.items():
            for d in (1, -1):
                for k in range(a, b):
                    if mn[k] < s0 or mn[k] + 5 >= e0:      # 合図の足は窓の中・次の足（入る足）も窓の中
                        continue
                    now = beyond(D, lines, pairs, k, d)
                    if len(now) < MIN_PAIRS:
                        continue
                    contiguous = k > a and T[k] - T[k - 1] == 5 * MIN
                    if contiguous and len(beyond(D, lines, pairs, k - 1, d)) >= MIN_PAIRS:
                        continue                            # 1本前にもう2つ以上＝この足で「そろった」のではない
                    out.append({"k": int(k), "series": name, "d": d, "seg": seg, "cands": now})
                    break
    order = {n: i for i, n in enumerate(SERIES)}
    return sorted(out, key=lambda g: (g["k"], order[g["series"]], -g["d"]))


def pick_pair(D, a, b, g, win):
    """抜けたペアのうち、窓の基準の足の始値からの動き（%・抜けた向き）がいちばん大きいペア。基準の足が無いペアは選ばない"""
    ref_min = win[g["seg"]][2]
    idx = np.flatnonzero(D["minute"][a:b] == ref_min)
    if not len(idx):
        return None, None
    r = int(idx[0]) + a
    best, val = None, None
    for p in g["cands"]:
        o, c = D["P"][p]["o"][r], D["P"][p]["c"][g["k"]]
        if not (np.isfinite(o) and np.isfinite(c)) or o <= 0:
            continue
        m = (c / o - 1.0) * g["d"]
        if val is None or m > val:
            best, val = p, m
    return best, val


# ════════════════════ 入って、出る ════════════════════

def entry_of(D, p, d, k1, line):
    """入る足 k1 の始値で入る → (入った値, 損切り, 利確, 損切りまでの幅 pips, スプレッド pips) か None（理由）"""
    Q = D["P"][p]
    pp = pip(p)
    so = Q["so"][k1] / pp
    entry = Q["o"][k1] + Q["so"][k1] if d > 0 else Q["o"][k1]
    sl = line - SL_OUT * pp if d > 0 else line + SL_OUT * pp
    tp = entry + TP_PIPS * pp if d > 0 else entry - TP_PIPS * pp
    dist = round((entry - sl) / pp if d > 0 else (sl - entry) / pp, 6)       # 小数の誤差で 7倍の境目がずれないように
    return entry, sl, tp, dist, so


def manage(D, p, d, k1, entry, sl, tp, exit_min, E, b):
    """入った足 k1 から出るまで。→ dict（費用後の pips・費用・出口・出た位置・持った分）"""
    Q, T, mn = D["P"][p], D["T"], D["minute"]
    pp = pip(p)
    ev_exit = K.next_event_exit(E, T[k1])
    day0 = D["date"][k1]
    exit_k, exit_px, why = None, None, None
    last = k1
    for k in range(k1, b):
        o = Q["o"][k]
        if not np.isfinite(o):
            continue
        so = Q["so"][k] if np.isfinite(Q["so"][k]) else 0.0
        last = k
        if k > k1:
            px_o = o if d > 0 else o + so                   # 出る値＝買いは売値・売りは買値
            if D["date"][k] != day0 or mn[k] >= exit_min:
                exit_k, exit_px, why = k, px_o, "time"
                break
            if ev_exit is not None and T[k] >= ev_exit:
                exit_k, exit_px, why = k, px_o, "event"
                break
            if (d > 0 and px_o <= sl) or (d < 0 and px_o >= sl):
                exit_k, exit_px, why = k, px_o, "sl"          # 始値で飛び越えた
                break
            if (d > 0 and px_o >= tp) or (d < 0 and px_o <= tp):
                exit_k, exit_px, why = k, px_o, "tp"
                break
        hi, lo = (Q["h"][k], Q["l"][k]) if d > 0 else (Q["h"][k] + so, Q["l"][k] + so)
        if (d > 0 and lo <= sl) or (d < 0 and hi >= sl):
            exit_k, exit_px, why = k, sl, "sl"                # 同じ足で両方に届いたら損切りが先
            break
        if (d > 0 and hi >= tp) or (d < 0 and lo <= tp):
            exit_k, exit_px, why = k, tp, "tp"
            break
    if exit_k is None:
        so = Q["so"][last] if np.isfinite(Q["so"][last]) else 0.0
        exit_k, exit_px, why = last, (Q["c"][last] if d > 0 else Q["c"][last] + so), "end"
    after = ((exit_px - entry) if d > 0 else (entry - exit_px)) / pp
    so_in = Q["so"][k1] if np.isfinite(Q["so"][k1]) else 0.0
    so_out = Q["so"][exit_k] if np.isfinite(Q["so"][exit_k]) else 0.0
    cost = (so_in if d > 0 else so_out) / pp
    return {"after": float(after), "before": float(after + cost), "cost": float(cost), "exit": why, "exit_k": int(exit_k),
            "exit_t": int(T[exit_k]), "hold_min": float((T[exit_k] - T[k1]) / MIN)}


def simulate(D, E, collect_pool=False, pnl=True):
    """1つの期間を数える → 合図・取引・見送り・偽薬の入れ物"""
    days = K.day_slices(D)
    stats = {"days": 0, "weekday_days": 0, "line_missing_pairs": 0}
    signals, trades = [], []
    skips = {k: 0 for k in SKIPS}
    pool = {p: [] for p in PAIRS}
    for day, (a, b) in sorted(days.items()):
        stats["days"] += 1
        if day.weekday() >= 4:                             # 月〜木だけ（金・土・日は入らない）
            continue
        stats["weekday_days"] += 1
        lines = lines_of(D, a, b)
        stats["line_missing_pairs"] += len(PAIRS) - len(lines)
        win = windows(day)
        if collect_pool:
            for seg, (s0, e0, _r, x) in win.items():
                for p in lines:
                    for k in range(a, b):
                        if s0 + 5 <= D["minute"][k] < e0 and np.isfinite(D["P"][p]["o"][k]) and not K.event_blocked(E.get(p), D["T"][k]):
                            pool[p].append((k, x, b))
        busy = {}
        for g in find_signals(D, a, b, lines, win):
            p, move = pick_pair(D, a, b, g, win)
            rec = {"day": day.isoformat(), "minute": int(D["minute"][g["k"]]), "series": g["series"], "d": g["d"], "seg": g["seg"],
                   "n_broken": len(g["cands"]), "pair": p, "season": "夏" if K.london_open_minute(day) == 16 * 60 else "冬"}
            signals.append(rec)
            if p is None:
                continue
            k1 = g["k"] + 1
            if k1 >= b or D["T"][k1] - D["T"][g["k"]] != 5 * MIN or not np.isfinite(D["P"][p]["o"][k1]):
                skips["no_next"] += 1
                continue
            if busy.get(p, -1) >= D["T"][k1]:
                skips["busy"] += 1
                continue
            if K.event_blocked(E.get(p), D["T"][k1]):
                skips["event"] += 1
                continue
            line = lines[p][1] if g["d"] > 0 else lines[p][0]
            entry, sl, tp, dist, so = entry_of(D, p, g["d"], k1, line)
            if not np.isfinite(so) or so > SPREAD_MAX:
                skips["spread"] += 1
                continue
            if dist <= 0:
                skips["inside"] += 1
                continue
            if dist < COST_MULT * so:
                skips["cost7"] += 1
                continue
            t = dict(rec, k=int(k1), entry=float(entry), sl_dist=float(dist), spread=float(so), move=float(move))
            if pnl:
                m = manage(D, p, g["d"], k1, entry, sl, tp, win[g["seg"]][3], E.get(p), b)
                t.update(m, r=m["after"] / dist)
                busy[p] = m["exit_t"]
            else:
                busy[p] = D["T"][k1]                           # check：持っている間は分からない＝入った足だけ重ならないようにする
            trades.append(t)
    return {"stats": stats, "signals": signals, "trades": trades, "skips": skips, "pool": pool}


# ════════════════════ 偽薬・まとめ・判定 ════════════════════

def placebo(D, E, trades, pool, n_perm=N_PERM, seed=SEED):
    """本物の取引ごとに、同じペア・同じ向きで、窓の中の足をでたらめに選んで始値で入る（損切りまでの幅・利確 20pips・出方・費用は本物と同じ）"""
    if not trades:
        return None, None
    rng = np.random.default_rng(seed)
    actual = float(np.mean([t["after"] for t in trades]))
    sims = np.zeros(n_perm)
    for t in trades:
        pl = pool.get(t["pair"]) or []
        if not pl:
            continue
        pp = pip(t["pair"])
        Q = D["P"][t["pair"]]
        for j, ix in enumerate(rng.integers(0, len(pl), n_perm)):
            k, x, b = pl[ix]
            entry = Q["o"][k] + Q["so"][k] if t["d"] > 0 else Q["o"][k]
            sl = entry - t["sl_dist"] * pp if t["d"] > 0 else entry + t["sl_dist"] * pp
            tp = entry + TP_PIPS * pp if t["d"] > 0 else entry - TP_PIPS * pp
            sims[j] += manage(D, t["pair"], t["d"], k, entry, sl, tp, x, E.get(t["pair"]), b)["after"]
    sims /= len(trades)
    return float((np.sum(sims >= actual) + 1) / (n_perm + 1)), float(sims.mean())


def cluster(vals, days):
    """平均と 95% の幅（日本時間の日ごとのまとまり）"""
    r = np.asarray(vals, float)
    n = len(r)
    if n == 0:
        return {"n": 0, "mean": None, "lo": None, "hi": None}
    m = float(r.mean())
    _, inv = np.unique(np.asarray(days), return_inverse=True)
    s = np.bincount(inv, weights=r)
    cnt = np.bincount(inv).astype(float)
    g = len(s)
    if g < 2:
        return {"n": n, "mean": m, "lo": None, "hi": None}
    u = s - m * cnt
    se = math.sqrt(g / (g - 1) * float(np.sum(u * u))) / n
    return {"n": n, "mean": m, "lo": m - Z * se, "hi": m + Z * se}


def _group(rows, key):
    out = {}
    for r in rows:
        out.setdefault(key(r), []).append(r["after"])
    return {str(k): {"n": len(v), "mean": float(np.mean(v)), "win": float(np.mean(np.asarray(v) > 0))} for k, v in sorted(out.items(), key=lambda x: str(x[0]))}


def summarize(trades, split):
    if not trades:
        return {"n": 0}
    after = [t["after"] for t in trades]
    st = cluster(after, [t["day"] for t in trades])
    old = [t["after"] for t in trades if t["day"] < split]
    new = [t["after"] for t in trades if t["day"] >= split]
    wins = [v for v in after if v > 0]
    loss = [v for v in after if v <= 0]
    return dict(st, win=float(np.mean(np.asarray(after) > 0)), before_mean=float(np.mean([t["before"] for t in trades])),
                cost_mean=float(np.mean([t["cost"] for t in trades])), commission_mean=float(np.mean(after) - COMMISSION),
                r_mean=float(np.mean([t["r"] for t in trades])), avg_win=float(np.mean(wins)) if wins else None,
                avg_loss=float(np.mean(loss)) if loss else None, sl_dist_median=float(np.median([t["sl_dist"] for t in trades])),
                old_mean=float(np.mean(old)) if old else None, new_mean=float(np.mean(new)) if new else None, old_n=len(old), new_n=len(new),
                exits={k: sum(1 for t in trades if t["exit"] == k) for k in ("tp", "sl", "time", "event", "end")},
                by_series=_group(trades, lambda t: t["series"]),
                by_pair=_group(trades, lambda t: t["pair"]),
                by_side=_group(trades, lambda t: "買い" if t["d"] > 0 else "売り"),
                by_seg=_group(trades, lambda t: "始まりの前" if t["seg"] == "前" else "始まりの30分後から"),
                by_season=_group(trades, lambda t: t["season"]),
                by_broken=_group(trades, lambda t: f"{t['n_broken']}ペア"),
                by_time=_group(trades, lambda t: f"{t['minute'] // 60:02d}:{(t['minute'] % 60) // 30 * 30:02d}"),
                by_exit=_group(trades, lambda t: t["exit"]),
                by_year=_group(trades, lambda t: t["day"][:4]))


def judge(a, p, b):
    """A で4つの関門 → B で確かめる"""
    if a.get("n", 0) < N_MIN_A:
        return "検定不能"
    if a["lo"] is None or a["lo"] <= 0:
        return "費用後マイナス" if (a["hi"] is not None and a["hi"] < 0) else "0と区別できない"
    if p is None or p >= ALPHA:
        return "でたらめな足と差なし"
    if not ((a.get("old_mean") or 0) > 0 and (a.get("new_mean") or 0) > 0):
        return "前半と後半で割れた"
    if b.get("n", 0) < N_MIN_B:
        return "昔の期間は検定不能"
    if b["lo"] is None or b["lo"] <= 0 or not ((b.get("old_mean") or 0) > 0 and (b.get("new_mean") or 0) > 0):
        return "昔の期間で消えた"
    return SURVIVED


def verdicts_of(v, a, today):
    if not v or v == SURVIVED:
        return {}
    return {TAG: {"status": "stop", "decided_on": today, "n": a.get("n"), "mean": a.get("mean"), "lo": a.get("lo"), "hi": a.get("hi"),
                  "reason": f"{v}（過去のデータ・1回だけ数えた・手元の MT5 と Dukascopy の5分足・勝率 {(a.get('win') or 0) * 100:.1f}%・"
                            f"機械の決まりは裁量の一部だけ）"}}


# ════════════════════ 読み込みから判定まで ════════════════════

def load_all(folder, duka_root):
    seen = {p: K.read_mt5(folder, p) for p in PAIRS}
    old = {p: K.read_duka(duka_root, p) for p in PAIRS}
    # B のスプレッドの下限＝A の BigBoss の、そのペア・その時間（日本時間）の足の始まりのスプレッドの中央値（KT1 と同じ）
    for p in PAIRS:
        b = seen[p]
        if not len(b) or not len(old[p]):
            continue
        floor = pd.Series(b["so"].to_numpy(float)).groupby(np.asarray(b.index.tz_convert(JST).hour)).median().to_dict()
        oh = np.asarray(old[p].index.tz_convert(JST).hour)
        fl = np.array([floor.get(h, np.nan) for h in oh])
        old[p] = old[p].assign(so=np.fmax(old[p]["so"].to_numpy(float), np.nan_to_num(fl, nan=0.0)))
    return seen, old


def panel_of(bars, start, end=None):
    """ペアごとの5分足 → KT1 と同じ並べ方。足の無いペアは空（値はすべて欠け＝線が無い＝そのペアは抜けず・入らない）。1つも無ければ None"""
    full = {p: b for p, b in bars.items() if len(b)}
    if not full:
        return None
    end = end or str(max(b.index.max() for b in full.values()).date())
    empty = pd.DataFrame({c: pd.Series(dtype=float) for c in ("open", "high", "low", "close", "so")}, index=pd.DatetimeIndex([], tz="UTC"))
    return K.panel({p: (b if len(b) else empty) for p, b in bars.items()}, start, end)


def panels(seen, old):
    return panel_of(seen, SEEN_START), panel_of(old, OLD[0], OLD[1])


def tool_sha256():
    with open(os.path.abspath(__file__), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def check(folder, duka_root, events_path):
    """足・線・合図・入れた数・見送りの理由だけ（損益は数えない・何も書き出さない）"""
    seen, old = load_all(folder, duka_root)
    rep = {"prereg_sha256": OK.section_sha256(PREREG, SECTION), "tool_sha256": tool_sha256(), "bars": {}}
    for name, bars in (("A", seen), ("B", old)):
        for p in PAIRS:
            b = bars[p]
            so = b["so"].to_numpy(float) / pip(p) if len(b) else np.array([])
            rep["bars"][f"{name}:{p}"] = {"rows": int(len(b)), "first_utc": str(b.index.min()) if len(b) else None,
                                         "last_utc": str(b.index.max()) if len(b) else None,
                                         "spread_median_pips": float(np.nanmedian(so)) if len(so) else None}
    try:
        E = read_events(events_path)
        n = {p: int(len(E[p])) for p in PAIRS}
        # FLH の一覧の件数（KT1）：4ペアとも 1,631・ユーロ円だけ 340・ポンド円だけ 463。ここでは米国・日本の発表を7ペアとも・ユーロ・ポンド・豪ドルの発表を
        # その通貨の2ペアに当てる＝同じ通貨の2ペアは同じ数・ドル円の数は 1,631 のまま（KT1 の数え方との差は same_as_kt1 で読む）
        ok = n["USDJPY"] == 1631 and n["EURJPY"] == n["EURUSD"] and n["GBPJPY"] == n["GBPUSD"] and n["AUDJPY"] == n["AUDUSD"]
        rep["events"] = {"n": n, "ok": ok, "same_as_kt1": n["EURJPY"] == 1971 and n["GBPJPY"] == 2094}
    except (OSError, SystemExit) as e:
        rep["events"] = {"error": str(e)}
        E = {p: np.array([], dtype=np.int64) for p in PAIRS}
    D_a, D_b = panels(seen, old)
    for name, D in (("A", D_a), ("B", D_b)):
        if D is None or not len(D["idx"]):
            rep[name] = {"error": "足が無い"}
            continue
        r = simulate(D, E, pnl=False)
        sig, tr = r["signals"], r["trades"]
        rep[name] = {"days": r["stats"], "signals": len(sig), "entered": len(tr), "skips": r["skips"],
                     "no_pair": sum(1 for g in sig if g["pair"] is None),
                     "signals_by_series": {s: sum(1 for g in sig if g["series"] == s) for s in SERIES},
                     "entered_by_series": {s: sum(1 for t in tr if t["series"] == s) for s in SERIES},
                     "entered_by_seg_season": {f"{sg}・{se}": sum(1 for t in tr if t["seg"] == sg and t["season"] == se) for sg in ("前", "後") for se in ("冬", "夏")},
                     "entered_by_side": {"買い": sum(1 for t in tr if t["d"] > 0), "売り": sum(1 for t in tr if t["d"] < 0)},
                     "entered_by_year": {y: sum(1 for t in tr if t["day"][:4] == y) for y in sorted({t["day"][:4] for t in tr})},
                     "sl_dist_median": float(np.median([t["sl_dist"] for t in tr])) if tr else None,
                     "spread_median": float(np.median([t["spread"] for t in tr])) if tr else None}
    return rep


def run_all(folder, duka_root, events_path, n_perm=N_PERM):
    seen, old = load_all(folder, duka_root)
    E = read_events(events_path)
    D_a, D_b = panels(seen, old)
    if D_a is None:
        raise SystemExit("🚨 A（MT5 の5分足）が読めない＝数えない")
    r_a = simulate(D_a, E, collect_pool=True)
    r_b = simulate(D_b, E) if D_b is not None else {"trades": [], "signals": [], "skips": {k: 0 for k in SKIPS}, "stats": {}}
    a = summarize(r_a["trades"], SPLIT_A)
    b = summarize(r_b["trades"], SPLIT_B)
    p, pm = placebo(D_a, E, r_a["trades"], r_a["pool"], n_perm) if a.get("n") else (None, None)
    a["placebo_p"], a["placebo_mean"] = p, pm
    v = judge(a, p, b)
    return {"verdict": v, "A": a, "B": b, "skips": {"A": r_a["skips"], "B": r_b["skips"]},
            "signals": {"A": len(r_a["signals"]), "B": len(r_b["signals"])}, "stats": {"A": r_a["stats"], "B": r_b["stats"]},
            "events": {p_: int(len(E[p_])) for p_ in PAIRS},
            "data": {"A": f"{str(D_a['idx'].min())[:10]}〜{str(D_a['idx'].max())[:10]}",
                     "B": f"{str(D_b['idx'].min())[:10]}〜{str(D_b['idx'].max())[:10]}" if D_b is not None and len(D_b["idx"]) else "なし"},
            "pairs_with_bars": {"A": [p_ for p_ in PAIRS if len(seen[p_])], "B": [p_ for p_ in PAIRS if len(old[p_])]},
            "trades": {"A": r_a["trades"], "B": r_b["trades"]}}


def render_md(rec):
    f = lambda v: "—" if v is None else f"{v:+.2f}"
    a, b = rec["A"], rec["B"]
    L = [f"# {HEADING}", "",
         f"更新: {rec.get('generated_jst')}（事前登録＝`PILLAR_PREREG.md`「{TAG}」・節の指紋 `{(rec.get('prereg_sha256') or '')[:12]}`・"
         f"道具の指紋 `{(rec.get('tool_sha256') or '')[:12]}`）・A {rec['data']['A']}・B {rec['data']['B']}・数字は費用後の pips（1回あたり）", "",
         f"**判定：{rec['verdict']}**", "",
         "| データ | 回数 | 平均（95%の幅） | 勝率 | 平均の勝ち／負け | 偽薬 p（偽薬の平均） | 前半／後半 | R（読むだけ） | 手数料0.8pips後 |",
         "|---|---:|---|---:|---|---|---|---:|---:|"]
    for name, s in (("A 判定（MT5 2022-06〜）", a), ("B 確かめ（Dukascopy 2017〜2022-05）", b)):
        if not s.get("n"):
            L.append(f"| {name} | 0 | | | | | | | |")
            continue
        pv = s.get("placebo_p")
        L.append(f"| {name} | {s['n']} | {f(s['mean'])}〔{f(s['lo'])}〜{f(s['hi'])}〕 | {s['win'] * 100:.1f}% | {f(s['avg_win'])}／{f(s['avg_loss'])} | "
                 f"{'—' if pv is None else format(pv, '.4f')}{'' if s.get('placebo_mean') is None else '（' + f(s['placebo_mean']) + '）'} | "
                 f"{f(s['old_mean'])}／{f(s['new_mean'])} | {s['r_mean']:+.3f} | {f(s['commission_mean'])} |")
    L += ["", f"- 合図 A {rec['signals']['A']}・B {rec['signals']['B']}／見送り A {rec['skips']['A']}・B {rec['skips']['B']}", "",
          "## 読むための表（判定しない・回数・平均 pips・勝率）", ""]
    names = (("シリーズ", "by_series"), ("ペア", "by_pair"), ("買い売り", "by_side"), ("窓", "by_seg"), ("冬夏", "by_season"),
             ("抜けたペアの数", "by_broken"), ("合図の時刻（30分ごと）", "by_time"), ("出口", "by_exit"), ("年", "by_year"))
    for name, s in (("A", a), ("B", b)):
        if not s.get("n"):
            continue
        L += [f"### {name}", "", f"- 費用前の平均 {f(s.get('before_mean'))}・費用の平均 {s['cost_mean']:.2f}pips・損切りまでの幅の中央値 {s['sl_dist_median']:.1f}pips・出口 {s['exits']}"]
        for label, k in names:
            L.append(f"- {label}：" + "／".join(f"{g} {v['n']}・{f(v['mean'])}・{v['win'] * 100:.0f}%" for g, v in (s.get(k) or {}).items()))
        L.append("")
    L += ["---", "", "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。機械の決まりは裁量の一部だけを数えています。"]
    return "\n".join(L) + "\n"


def trades_csv(trades, path):
    cols = ("day", "minute", "series", "d", "seg", "season", "n_broken", "pair", "entry", "sl_dist", "spread", "move", "after", "before",
            "cost", "r", "exit", "hold_min")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    pd.DataFrame([{c: t.get(c) for c in cols} for t in trades]).to_csv(path, index=False, encoding="utf-8-sig")


def run(folder, duka_root, events_path, n_perm=N_PERM):
    res = run_all(folder, duka_root, events_path, n_perm)
    now = dt.datetime.now(JST)
    a = res["A"]
    rec = {"kind": "backtest", "unit": "pips", "source": "手元の MT5（BigBoss）の実ティックの5分足（A）・Dukascopy の1分足 → 5分足（B）",
           "generated_jst": now.isoformat(timespec="minutes"), "prereg_sha256": OK.section_sha256(PREREG, SECTION), "tool_sha256": tool_sha256(),
           "data": res["data"], "titles": TITLES, "verdict": res["verdict"], "verdicts": verdicts_of(res["verdict"], a, now.date().isoformat()),
           "progress": {TAG: a.get("n", 0)}, "A": a, "B": res["B"], "skips": res["skips"], "signals": res["signals"], "stats": res["stats"],
           "events": res["events"], "pairs_with_bars": res["pairs_with_bars"]}
    return rec, res["trades"]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["check", "run"])
    ap.add_argument("--dir", default=r"C:\mt5run", help="m5tick_*.csv のあるフォルダ")
    ap.add_argument("--duka", default=r"C:\mt5run\duka_fx", help="Dukascopy の1分足の置き場（<ペア>/BID|ASK/YYYY-MM-DD.bi5）")
    ap.add_argument("--events", default=EVENTS, help="発表の一覧（FLH と同じ）")
    a = ap.parse_args(argv)
    if a.mode == "check":
        print(json.dumps(OK._clean(check(a.dir, a.duka, a.events)), ensure_ascii=False, indent=1))
        return 0
    if os.path.exists(OUT_JSON):
        raise SystemExit(f"🚨 {OUT_JSON} がもうある＝1回だけの約束（データの読み込みの失敗でやり直すときだけ、消してから）")
    rec, trades = run(a.dir, a.duka, a.events)
    rec = OK._clean(rec)
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, ensure_ascii=False, indent=1)
    md = render_md(rec)
    os.makedirs(os.path.dirname(OUT_MD), exist_ok=True)
    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write(md)
    trades_csv(trades["A"], OUT_CSV.format("A"))
    trades_csv(trades["B"], OUT_CSV.format("B"))
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
