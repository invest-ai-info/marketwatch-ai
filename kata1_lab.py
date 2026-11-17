# -*- coding: utf-8 -*-
"""KT1 オーナーの型1：クロス円3つ（ドル円・ポンド円・ユーロ円）がそろって東京時間の最安値（最高値）を割ったら、
戻りの 50% と線で分けて入る（5分足・ロンドン時間の前後3時間・2つの期間で1回だけ）。2026-11-17 登録・PILLAR_PREREG.md「KT1」。

決まりの要点（全文は PILLAR_PREREG.md「KT1」・ここの定数に固定）:
- 線＝日本時間 8:00〜15:00 に始まる5分足の安値の最小（買いは高値の最大）
- 窓＝ロンドン時間の始まりの1時間前〜2時間後（冬 16:00〜18:55・夏 15:05〜17:55 に始まる足）
- 合図＝窓の中で、3つとも終値が線の外にある最初の足（その1本前は3つそろっていない＝最後の1つが割れた足）
- 1発目（3分の1）＝線と新安値の真ん中（50%）・線から新安値まで 20 pips 以上（60 pips 以上は判定の外）・新安値の足から30分以内
- 2発目（3分の2）＝線。損切り＝5分足の終値が線の内側 → 次の足の始値。利確＝直近安値。早めの利確＝3つそろって陰線のあと、
  どれかが陽線で確定 → 次の足の始値。時間切れ＝ロンドンの2時間後の足の始値。発表の60分前〜30分後は合図・指値なし・5分前に手じまい
- 腕 KT1-A＝16時より前は3等分・16時以降はユーロポンド（ユーロ円÷ポンド円の終値）の向きで1ペア／KT1-B＝いつも3等分
- 荒れすぎの日＝前の日までの20営業日の日足の値幅の平均が、その前の250営業日の上位5% に入るペアが1つでもある日は入らない

⚠️ データは手元にだけある＝**手元で1回だけ**回す。値動きはクラウドでは見ていない（この道具は 2026-11-17 にクラウドで作った）。
実行（手元）:
  python kata1_lab.py check --dir C:\\mt5run --duka C:\\mt5run\\duka_fx   （足・線・合図・入れた数だけ。損益は数えない・何も書き出さない）
  python kata1_lab.py run   --dir C:\\mt5run --duka C:\\mt5run\\duka_fx   （本番・1回だけ → kata1-lab.json（送る）・research/oikawa/kata1-result.md と取引の CSV（手元））
"""
import argparse
import datetime as dt
import json
import lzma
import os
import re
import sys
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

import oikawa_lab as OK

# ════════════════════ 事前登録の値（PILLAR_PREREG.md「KT1」） ════════════════════
PAIRS = ("USDJPY", "GBPJPY", "EURJPY")
SEEN_START = "2022-06-01"                # 見た期間＝MT5（BigBoss）の5分足 2022-06-01〜
OLD = ("2017-01-01", "2022-05-31")       # 昔の期間＝Dukascopy の1分足 → 5分足
SPLIT = "2024-08-01"                     # 前半＝〜2024-07-31／後半＝2024-08-01〜
JST = ZoneInfo("Asia/Tokyo")
LON = ZoneInfo("Europe/London")
NY = ZoneInfo("America/New_York")
LINE = (8 * 60, 15 * 60)                 # 線＝8:00〜15:00 に始まる足（両端を含む＝85本）
LINE_BARS = 85
LINE_MAX_MISSING = 10                    # 欠けが10本を超える日はそのペアを使わない
EARLIEST = 15 * 60 + 5                   # 合図・入るのは 15:05 に始まる足から（15:00 の足は線に使う）
BEFORE_LON = 60                          # ロンドンの始まりの60分前から
LAST_BAR = 115                           # 合図・入る足はロンドンの始まりの115分後に始まる足まで
STOP_AFTER = 120                         # 時間切れ＝ロンドンの始まりの120分後に始まる足の始値
SPLIT_3 = 16 * 60                        # 16:00 より前の合図は3等分
MIN_PIPS = 20.0                          # 線から新安値まで 20 pips 以上
MAX_PIPS = 60.0                          # 60 pips 以上は判定の外（読むための表で別に出す）
WAIT_MIN = 30                            # いちばん新しい安値の足から30分以内に 50% に届かなければ入らない
FIRST, SECOND = 1.0 / 3.0, 2.0 / 3.0
EV_BEFORE, EV_AFTER, EV_EXIT = 60, 30, 5  # 発表の60分前〜30分後は合図・指値なし／5分前に手じまい
VOL_DAYS, VOL_HIST, VOL_Q = 20, 250, 0.95
COMMISSION = 0.8                         # 判定の6：手数料 1回 0.8 pips（入れた大きさに比例）
N_MIN = 200
ALPHA = 0.05 / 2                         # 2つの腕
N_PERM = 1000
SEED = 20261117
EVENTS = os.path.join("research", "oikawa", "flow-jpy-events.csv")
EV_EXPECT = {"USDJPY": 1631, "EURJPY": 1971, "GBPJPY": 2094}    # FLH の一覧の件数（4ペアとも 1,631・ユーロ円だけ 340・ポンド円だけ 463）
PREREG = "PILLAR_PREREG.md"
SECTION = "## KT1 オーナーの型1"
OUT_JSON = "kata1-lab.json"
OUT_MD = os.path.join("research", "oikawa", "kata1-result.md")
OUT_CSV = os.path.join("research", "oikawa", "kata1-{}.csv")
TITLES = {"KT1-A": "オーナーの型1（決めたとおり）：クロス円3つがそろって東京時間の最安値（最高値）を割ったら、線と新安値の50%で1/3・線で2/3。"
                   "16時以降はユーロポンドの向きで1ペア（5分足・ロンドン時間の前後3時間・過去のデータ・1回だけ・手元の MT5 と Dukascopy）",
          "KT1-B": "オーナーの型1（いつも3等分）：同じ合図で、ドル円・ポンド円・ユーロ円に3等分して入る"
                   "（5分足・ロンドン時間の前後3時間・過去のデータ・1回だけ・手元の MT5 と Dukascopy）"}
SURVIVED = OK.SURVIVED
MIN = 60 * 10 ** 9                       # 1分（ns）


def pip(p):
    return OK.pip(p)


# ════════════════════ 読み込み ════════════════════

def parse_duka_day(data, day, p):
    """Dukascopy の1分足（伸張後のバイト列）→ (UTC の秒の配列, 始, 終, 安, 高, 取引量)。値は円のペアなら 1/1000"""
    if not data:
        return None
    a = np.frombuffer(data, dtype=np.dtype([("t", ">u4"), ("o", ">u4"), ("c", ">u4"), ("l", ">u4"), ("h", ">u4"), ("v", ">f4")]))
    t0 = int(pd.Timestamp(day).tz_localize("UTC").value // 10 ** 9)
    pt = OK.point(p)
    return (a["t"].astype(np.int64) + t0, a["o"] * pt, a["c"] * pt, a["l"] * pt, a["h"] * pt, a["v"].astype(float))


def _read_bi5(path):
    try:
        with open(path, "rb") as f:
            body = f.read()
    except OSError:
        return None
    return lzma.decompress(body) if body else b""


def duka_day_5m(bid, ask):
    """1日の売値・買値の1分足 → 5分足（売値の始高安終・スプレッド＝その5分の最初の1分の買値の始値−売値の始値）。
    使う1分＝売値と買値の両方がそろい、どちらかの取引量が0より大きい分だけ（FLC と同じ）"""
    if bid is None or ask is None:
        return None
    tb, ta = bid[0], ask[0]
    common, ib, ia = np.intersect1d(tb, ta, return_indices=True)
    if not len(common):
        return None
    keep = (bid[5][ib] > 0) | (ask[5][ia] > 0)
    common, ib, ia = common[keep], ib[keep], ia[keep]
    if not len(common):
        return None
    order = np.argsort(common, kind="stable")
    common, ib, ia = common[order], ib[order], ia[order]
    bucket = common // 300
    ub, first = np.unique(bucket, return_index=True)
    last = np.r_[first[1:], len(common)] - 1
    o = bid[1][ib][first]
    c = bid[2][ib][last]
    lo = np.minimum.reduceat(bid[3][ib], first)
    hi = np.maximum.reduceat(bid[4][ib], first)
    so = ask[1][ia][first] - bid[1][ib][first]
    idx = pd.to_datetime(ub * 300, unit="s", utc=True)
    return pd.DataFrame({"open": o, "high": hi, "low": lo, "close": c, "so": so}, index=idx)


def read_duka(root, p, first=OLD[0], last=OLD[1]):
    """<root>/<ペア>/BID|ASK/YYYY-MM-DD.bi5（gold_bars.py の置き方）→ 5分足（UTC）"""
    d0, d1 = dt.date.fromisoformat(first), dt.date.fromisoformat(last)
    parts = []
    d = d0
    while d <= d1:
        if d.weekday() != 5:
            raw = {}
            for side in ("BID", "ASK"):
                b = _read_bi5(os.path.join(root, p, side, f"{d.isoformat()}.bi5"))
                raw[side] = parse_duka_day(b, d, p) if b else None
            df = duka_day_5m(raw["BID"], raw["ASK"])
            if df is not None:
                parts.append(df)
        d += dt.timedelta(days=1)
    if not parts:
        return pd.DataFrame(columns=["open", "high", "low", "close", "so"])
    out = pd.concat(parts)
    return out[~out.index.duplicated(keep="first")].sort_index()


def read_mt5(folder, p):
    b = OK.read_bars(os.path.join(folder, f"m5tick_{p}.csv"), p)
    return b[b.index >= pd.Timestamp(SEEN_START, tz="UTC")][["open", "high", "low", "close", "so"]]


def read_events(path):
    """発表の一覧（FLH の flow-jpy-events.csv・時刻は UTC）→ {ペア: UTC の ns の並び}。
    ペアの当てはめ＝行の中のペアの名前（USDJPY など）／「4ペア」「ALL」「全」＝円の4ペアとも／通貨の列（USD・JPY＝4ペアとも・EUR・GBP）"""
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
    # 11/17 手元で直した：FLH の一覧の通貨の列は「scope」（ALL・EUR・GBP・AUD）。候補に無く、ユーロ・ポンドだけの発表が落ちていた
    ccol = next((low[k] for k in ("scope", "currency", "ccy", "cur", "country") if k in low), None)
    allp = {"USDJPY", "EURJPY", "GBPJPY", "AUDJPY"}
    cmap = {"USD": allp, "US": allp, "JPY": allp, "JP": allp, "EUR": {"EURJPY"}, "EU": {"EURJPY"},
            "GBP": {"GBPJPY"}, "GB": {"GBPJPY"}, "UK": {"GBPJPY"}, "AUD": {"AUDJPY"}, "AU": {"AUDJPY"}, "CNY": {"AUDJPY"}, "CN": {"AUDJPY"}}
    out = {p: [] for p in PAIRS}
    for i in range(len(df)):
        if pd.isna(t.iloc[i]):
            continue
        text = " ".join(str(v) for c, v in df.iloc[i].items() if c != tcol).upper().replace("/", "")
        hit = set(re.findall(r"(USDJPY|EURJPY|GBPJPY|AUDJPY)", text))
        if not hit and re.search(r"(4ペア|ALL|全)", text):
            hit = allp
        if not hit and ccol:
            for tok in re.findall(r"[A-Z]{2,3}", str(df.iloc[i][ccol]).upper()):
                hit |= cmap.get(tok, set())
        for p in hit & set(PAIRS):
            out[p].append(t.iloc[i].value)
    return {p: np.array(sorted(set(v)), dtype=np.int64) for p, v in out.items()}


# ════════════════════ 足をそろえる ════════════════════

def london_open_minute(day):
    """その日の英国の朝8時を日本時間の分で（冬 1020＝17:00・夏 960＝16:00）"""
    t = pd.Timestamp(dt.datetime(day.year, day.month, day.day, 8, 0), tz=LON).tz_convert(JST)
    return t.hour * 60 + t.minute


def panel(bars, start, end):
    """ペアごとの5分足 → 共通の時刻（和）にそろえた配列。期間は [start, end]（UTC の日付）"""
    idx = None
    for b in bars.values():
        idx = b.index if idx is None else idx.union(b.index)
    idx = idx[(idx >= pd.Timestamp(start, tz="UTC")) & (idx < pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1))]
    P = {}
    for p, b in bars.items():
        r = b.reindex(idx)
        P[p] = {k: r[col].to_numpy(float) for k, col in (("o", "open"), ("h", "high"), ("l", "low"), ("c", "close"), ("so", "so"))}
    idx = idx.as_unit("ns")              # 時刻の単位をナノ秒にそろえる（足の作り方でマイクロ秒になることがある）
    jst = idx.tz_convert(JST)
    T = idx.asi8.copy()
    minute = (jst.hour * 60 + jst.minute).to_numpy()
    date = np.array(jst.date)
    eg = P["EURJPY"]["c"] / P["GBPJPY"]["c"]
    return {"P": P, "T": T, "minute": minute, "date": date, "eg": eg, "idx": idx}


def server_day(idx):
    """FX の1日（ニューヨークの夕方5時で区切る＝BigBoss のサーバーの日付）"""
    return np.array((idx.tz_convert(NY) + pd.Timedelta(hours=7)).date)


def daily_ranges(b):
    """5分足 → サーバーの日ごとの値幅（高値−安値・pips ではなく値段）。足が200本未満の日は捨てる"""
    if b is None or not len(b):
        return pd.Series(dtype=float)
    d = server_day(b.index)
    g = pd.DataFrame({"h": b["high"].to_numpy(float), "l": b["low"].to_numpy(float), "d": d}).groupby("d")
    agg = g.agg(h=("h", "max"), l=("l", "min"), n=("h", "count"))
    agg = agg[agg["n"] >= 200]
    return (agg["h"] - agg["l"]).sort_index()


def abnormal_days(ranges, days=VOL_DAYS, hist=VOL_HIST, q=VOL_Q):
    """日 → True（荒れすぎ）／False／None（前の日までの記録が足りない）。前の日までの数字だけで決める"""
    r = ranges.to_numpy(float)
    keys = list(ranges.index)
    csum = np.r_[0.0, np.cumsum(r)]
    # mean20[i] ＝ i の前の20日（i-20〜i-1）の平均
    mean20 = np.full(len(r), np.nan)
    for i in range(days, len(r)):
        mean20[i] = (csum[i] - csum[i - days]) / days
    out = {}
    for i, k in enumerate(keys):
        if i < days + hist or np.isnan(mean20[i]):
            out[k] = None
            continue
        h = np.sort(mean20[i - hist:i])
        if np.isnan(h).any():
            out[k] = None
            continue
        out[k] = bool(mean20[i] > h[int(q * len(h))])
    return out


def event_blocked(E, t):
    """足の始まり t が発表の60分前〜30分後（両端を含む）か"""
    if E is None or not len(E):
        return False
    j = np.searchsorted(E, t - EV_AFTER * MIN, "left")
    return bool(j < len(E) and E[j] <= t + EV_BEFORE * MIN)


def next_event_exit(E, t_entry):
    """入った時刻より後の発表の「5分前」（ns）。無ければ None"""
    if E is None or not len(E):
        return None
    j = np.searchsorted(E, t_entry + EV_EXIT * MIN, "right")
    return int(E[j] - EV_EXIT * MIN) if j < len(E) else None


# ════════════════════ 日ごとの線と合図 ════════════════════

def day_slices(D):
    """日本時間の日付 → その日の足の位置（連続の範囲）"""
    out = {}
    date = D["date"]
    if not len(date):
        return out
    cut = np.flatnonzero(date[1:] != date[:-1]) + 1
    starts = np.r_[0, cut]
    ends = np.r_[cut, len(date)]
    for a, b in zip(starts, ends):
        out[date[a]] = (int(a), int(b))
    return out


def lines_of(D, a, b):
    """その日の線（ペアごと）とユーロポンドのレンジ。使えなければ None"""
    mn = D["minute"][a:b]
    sel = np.flatnonzero((mn >= LINE[0]) & (mn <= LINE[1])) + a
    out = {}
    for p in PAIRS:
        c = D["P"][p]["c"][sel]
        ok = np.isfinite(c)
        if ok.sum() < LINE_BARS - LINE_MAX_MISSING:
            return None
        out[p] = (float(np.nanmin(D["P"][p]["l"][sel])), float(np.nanmax(D["P"][p]["h"][sel])))
    eg = D["eg"][sel]
    eg = eg[np.isfinite(eg)]
    out["EG"] = (float(eg.min()), float(eg.max())) if len(eg) else (np.nan, np.nan)
    return out


def window_of(day):
    lo = london_open_minute(day)
    return lo, max(lo - BEFORE_LON, EARLIEST), lo + LAST_BAR, lo + STOP_AFTER


def find_signal(D, a, b, lines, w0, w1, E):
    """窓の中で、3つとも終値が線の外にある最初の足（1本前は3つそろっていない）。→ (位置, 向き s) か None。s＝-1 売り／+1 買い"""
    P, mn, T = D["P"], D["minute"], D["T"]

    def side(k):
        cs = [P[p]["c"][k] for p in PAIRS]
        if not all(np.isfinite(cs)):
            return 0
        if all(c < lines[p][0] for c, p in zip(cs, PAIRS)):
            return -1
        if all(c > lines[p][1] for c, p in zip(cs, PAIRS)):
            return 1
        return 0

    for k in range(a, b):
        if mn[k] < w0 or mn[k] > w1:
            continue
        s = side(k)
        if s == 0:
            continue
        prev_same = k > a and T[k] - T[k - 1] == 5 * MIN and side(k - 1) == s
        if prev_same or k == a:
            continue
        if any(event_blocked(E.get(p), T[k]) for p in PAIRS):
            continue
        return k, s
    return None


# ════════════════════ 入り方と出方 ════════════════════

def eg_state(D, k, rng):
    """そのペアが 50% に届いた足の1本前の足の終値で、ユーロポンドがレンジの上（+1）・下（-1）・中（0）"""
    if k < 1:
        return 0
    v = D["eg"][k - 1]
    if not np.isfinite(v) or not np.isfinite(rng[0]):
        return 0
    return 1 if v > rng[1] else (-1 if v < rng[0] else 0)


def gate_pair(p, s, state):
    """16時以降：売り＝上→ポンド円・下→ユーロ円／買い＝上→ユーロ円・下→ポンド円"""
    if state == 0:
        return False
    want = ("GBPJPY" if state > 0 else "EURJPY") if s < 0 else ("EURJPY" if state > 0 else "GBPJPY")
    return p == want


def scan_entry(D, p, s, k_sig, line, w1, b, E, gate=None):
    """1発目を探す。→ dict（位置・値段・目標＝直近安値・幅 pips・待った分・ユーロポンドの状態）か None"""
    P, T, mn = D["P"][p], D["T"], D["minute"]
    pp = pip(p)
    if not np.isfinite(P["l"][k_sig]):
        return None
    ext = P["l"][k_sig] if s < 0 else P["h"][k_sig]
    t_ext = T[k_sig]
    for k in range(k_sig + 1, b):
        if mn[k] > w1:
            return None
        if not np.isfinite(P["o"][k]):
            continue
        if T[k] - t_ext > WAIT_MIN * MIN:
            return None
        l50 = (line + ext) / 2.0
        dist = (line - ext) / pp if s < 0 else (ext - line) / pp
        ok_gate = gate is None or gate(k)
        if dist >= MIN_PIPS and ok_gate and not event_blocked(E, T[k]):
            if s < 0 and P["h"][k] >= l50:
                return {"k": k, "price": max(l50, P["o"][k]), "target": ext, "dist": dist, "wait": (T[k] - t_ext) / MIN}
            if s > 0:
                ask_o = P["o"][k] + P["so"][k]
                if P["l"][k] + P["so"][k] <= l50:
                    return {"k": k, "price": min(l50, ask_o), "target": ext, "dist": dist, "wait": (T[k] - t_ext) / MIN}
        lo, hi = P["l"][k], P["h"][k]
        if s < 0 and lo < ext:
            ext, t_ext = lo, T[k]
        elif s > 0 and hi > ext:
            ext, t_ext = hi, T[k]
    return None


def manage(D, p, s, k1, price1, line, target, w1, stop_min, E, b_limit):
    """1発目のあとの持ち方。→ dict（損益 pips＝満玉1つ分に直す前の、そのペアの1/3＋2/3 の合計・費用・出口・2発目の有無）"""
    P, T, mn = D["P"], D["T"], D["minute"]
    Q = P[p]
    pp = pip(p)
    fills = [(FIRST, price1, k1)]
    second = False
    armed = False
    pending = None
    ev_exit = next_event_exit(E, T[k1])
    day0 = D["date"][k1]
    exit_k, exit_px, reason = None, None, None

    def close_out(k, px, why):
        return k, px, why

    last_k = k1
    for k in range(k1, b_limit):
        if not np.isfinite(Q["o"][k]):
            continue
        last_k = k
        ask_o = Q["o"][k] + Q["so"][k]
        if k > k1:
            if pending:
                exit_k, exit_px, reason = close_out(k, ask_o if s < 0 else Q["o"][k], pending)
                break
            if (D["date"][k] != day0) or mn[k] >= stop_min:
                exit_k, exit_px, reason = close_out(k, ask_o if s < 0 else Q["o"][k], "time")
                break
            if ev_exit is not None and T[k] >= ev_exit:
                exit_k, exit_px, reason = close_out(k, ask_o if s < 0 else Q["o"][k], "event")
                break
        # 足の中：2発目と利確
        tp_hit = False
        if k > k1:
            tp_hit = (Q["l"][k] + Q["so"][k] <= target) if s < 0 else (Q["h"][k] >= target)
        if not second and mn[k] <= w1 and not event_blocked(E, T[k]) and not (tp_hit and k > k1):
            if s < 0 and Q["h"][k] >= line:
                fills.append((SECOND, max(line, Q["o"][k]) if k > k1 else line, k))
                second = True
            elif s > 0 and Q["l"][k] + Q["so"][k] <= line:
                fills.append((SECOND, min(line, ask_o) if k > k1 else line, k))
                second = True
        # 足の終わり：損切り・利確・早めの利確
        sl = (Q["c"][k] > line) if s < 0 else (Q["c"][k] < line)
        if sl:
            pending = "sl"
            continue
        if tp_hit:
            exit_k, exit_px, reason = close_out(k, target, "tp")
            break
        if k > k1:
            cols = []
            for q in PAIRS:
                o, c = P[q]["o"][k], P[q]["c"][k]
                cols.append(0 if not (np.isfinite(o) and np.isfinite(c)) else (1 if c > o else (-1 if c < o else 0)))
            fav = -1 if s < 0 else 1          # 売りは陰線がそろう向き
            if all(x == fav for x in cols):
                armed = True
            elif armed and any(x == -fav for x in cols):
                pending = "early"
    if exit_k is None:
        k = last_k
        exit_k, exit_px, reason = k, (Q["c"][k] + Q["so"][k]) if s < 0 else Q["c"][k], "end"
    so_exit = Q["so"][exit_k] if np.isfinite(Q["so"][exit_k]) else 0.0
    after = before = cost = 0.0
    size = 0.0
    for frac, px, kf in fills:
        if s < 0:
            a = (px - exit_px) / pp
            c_ = so_exit / pp
        else:
            a = (exit_px - px) / pp
            c_ = (Q["so"][kf] if np.isfinite(Q["so"][kf]) else 0.0) / pp
        after += frac * a
        cost += frac * c_
        size += frac
    before = after + cost
    return {"after": after, "before": before, "cost": cost, "size": size, "second": second, "exit": reason,
            "exit_k": int(exit_k), "hold_min": (T[exit_k] - T[k1]) / MIN}


# ════════════════════ 1日ずつ数える ════════════════════

def adx_series(b):
    """5分足 → 1時間足の ADX(14)（Wilder）。値は1時間足の終わり（次の時間の始まり）から使える"""
    if b is None or not len(b):
        return pd.Series(dtype=float)
    h = b[["high", "low", "close"]].resample("1h").agg({"high": "max", "low": "min", "close": "last"}).dropna()
    hi, lo, cl = h["high"].to_numpy(), h["low"].to_numpy(), h["close"].to_numpy()
    n = len(h)
    if n < 30:
        return pd.Series(np.nan, index=h.index + pd.Timedelta(hours=1))
    up = np.r_[0, hi[1:] - hi[:-1]]
    dn = np.r_[0, lo[:-1] - lo[1:]]
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    ndm = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr = np.r_[hi[0] - lo[0], np.maximum.reduce([hi[1:] - lo[1:], np.abs(hi[1:] - cl[:-1]), np.abs(lo[1:] - cl[:-1])])]

    def wilder(x):
        out = np.full(n, np.nan)
        out[14] = x[1:15].sum()
        for i in range(15, n):
            out[i] = out[i - 1] - out[i - 1] / 14 + x[i]
        return out
    atr, pdi_s, ndi_s = wilder(tr), wilder(pdm), wilder(ndm)
    with np.errstate(divide="ignore", invalid="ignore"):
        pdi = 100 * pdi_s / atr
        ndi = 100 * ndi_s / atr
        dx = 100 * np.abs(pdi - ndi) / (pdi + ndi)
    adx = np.full(n, np.nan)
    if n > 28:
        adx[27] = np.nanmean(dx[14:28])
        for i in range(28, n):
            adx[i] = (adx[i - 1] * 13 + dx[i]) / 14
    return pd.Series(adx, index=h.index + pd.Timedelta(hours=1))


def adx_band(series, t_ns):
    if series is None or not len(series):
        return None
    j = series.index.searchsorted(pd.Timestamp(t_ns, tz="UTC"), "right") - 1
    if j < 0:
        return None
    v = series.iloc[j]
    if not np.isfinite(v):
        return None
    return "20未満" if v < 20 else ("20〜25" if v < 25 else "25以上")


def dist_bucket(d):
    return "20〜30" if d < 30 else ("30〜40" if d < 40 else ("40〜60" if d < 60 else "60以上"))


def simulate(D, E, abn, adx=None, collect_pool=False, pnl=True):
    """1つの期間を数える → 合図の記録・腕ごとの取引・偽薬の入れ物"""
    days = day_slices(D)
    stats = {"days": 0, "line_missing": 0, "abnormal": 0, "no_history": 0, "usable": 0}
    signals, trades = [], {"A": [], "B": []}
    pool = {p: [] for p in PAIRS}
    for day, (a, b) in sorted(days.items()):
        if day.weekday() >= 5:
            continue
        stats["days"] += 1
        lines = lines_of(D, a, b)
        if lines is None:
            stats["line_missing"] += 1
            continue
        flags = [abn.get(p, {}).get(day) for p in PAIRS]
        if any(f is None for f in flags):
            stats["no_history"] += 1
            continue
        if any(flags):
            stats["abnormal"] += 1
            continue
        stats["usable"] += 1
        lo_min, w0, w1, stop_min = window_of(day)
        if collect_pool:
            for p in PAIRS:
                for k in range(a, b):
                    if w0 <= D["minute"][k] <= w1 and np.isfinite(D["P"][p]["o"][k]) and not event_blocked(E.get(p), D["T"][k]):
                        pool[p].append((k, w1, stop_min, b))
        sig = find_signal(D, a, b, lines, w0, w1, E)
        if sig is None:
            continue
        k_sig, s = sig
        season = "夏" if lo_min == 16 * 60 else "冬"
        g = {"day": day.isoformat(), "k": k_sig, "s": s, "minute": int(D["minute"][k_sig]), "season": season}
        signals.append(g)
        for arm in ("A", "B"):
            three = arm == "B" or g["minute"] < SPLIT_3
            pairs = PAIRS if three else ("EURJPY", "GBPJPY")
            weight = 1.0 / 3.0 if three else 1.0
            cands = []
            for p in pairs:
                line = lines[p][0] if s < 0 else lines[p][1]
                gate = None if three else (lambda k, p=p: gate_pair(p, s, eg_state(D, k, lines["EG"])))
                e = scan_entry(D, p, s, k_sig, line, w1, b, E.get(p), gate)
                if e is not None:
                    cands.append((p, line, e))
            if not three and cands:
                cands = [min(cands, key=lambda x: x[2]["k"])]      # 16時以降は1ペアだけ（先に入れたほう）
            pos = []
            for p, line, e in cands:
                if not pnl:                     # check：入れた数だけ（損益は数えない）
                    pos.append({"pair": p, "dist": e["dist"]})
                    continue
                m = manage(D, p, s, e["k"], e["price"], line, e["target"], w1, stop_min, E.get(p), b)
                pos.append(dict(m, pair=p, weight=weight, dist=e["dist"], wait=e["wait"], line_dist=abs(line - e["price"]) / pip(p),
                                tp_dist=abs(e["price"] - e["target"]) / pip(p), eg=eg_state(D, e["k"], lines["EG"]),
                                adx=adx_band((adx or {}).get(p), int(D["T"][e["k"]])), k=e["k"], price=e["price"]))
            if pos:
                trades[arm].append(dict(g, positions=pos))
    return {"stats": stats, "signals": signals, "trades": trades, "pool": pool}


def signal_value(tr, judged=True):
    """合図1つの値（満玉1つ分に直した pips）。judged＝60 pips 未満の建玉だけ"""
    ps = [q for q in tr["positions"] if (q["dist"] < MAX_PIPS) == judged]
    if not ps:
        return None
    after = sum(q["weight"] * q["after"] for q in ps)
    before = sum(q["weight"] * q["before"] for q in ps)
    size = sum(q["weight"] * q["size"] for q in ps)
    return {"after": after, "before": before, "size": size, "commission": after - COMMISSION * size}


# ════════════════════ 偽薬 ════════════════════

def placebo(D, E, trades, pool, n_perm=N_PERM, seed=SEED):
    """本物の建玉ごとに、同じペア・同じ向きで、窓の中の足をでたらめに選び、始値で入る（損切り・利確までの幅・大きさ・出方・費用は本物と同じ）"""
    rng = np.random.default_rng(seed)
    real = [signal_value(t) for t in trades]
    rows = [(t, v) for t, v in zip(trades, real) if v is not None]
    if not rows:
        return None, None
    actual = float(np.mean([v["after"] for _, v in rows]))
    sims = np.zeros(n_perm)
    P = D["P"]
    for t, _ in rows:
        for q in t["positions"]:
            if q["dist"] >= MAX_PIPS:
                continue
            pl = pool.get(q["pair"]) or []
            if not pl:
                continue
            picks = rng.integers(0, len(pl), n_perm)
            for j, ix in enumerate(picks):
                k, w1, stop_min, b = pl[ix]
                Q = P[q["pair"]]
                entry = Q["o"][k] if t["s"] < 0 else Q["o"][k] + Q["so"][k]
                line = entry + q["line_dist"] * pip(q["pair"]) if t["s"] < 0 else entry - q["line_dist"] * pip(q["pair"])
                target = entry - q["tp_dist"] * pip(q["pair"]) if t["s"] < 0 else entry + q["tp_dist"] * pip(q["pair"])
                m = manage(D, q["pair"], t["s"], k, entry, line, target, w1, stop_min, E.get(q["pair"]), b)
                sims[j] += q["weight"] * m["after"]
    sims /= len(rows)
    return float((np.sum(sims >= actual) + 1) / (n_perm + 1)), float(sims.mean())


# ════════════════════ まとめと判定 ════════════════════

def _group(rows, key):
    out = {}
    for r in rows:
        k = key(r)
        if k is None:
            continue
        out.setdefault(k, []).append(r["v"])
    return {str(k): {"n": len(v), "mean": float(np.mean(v)), "win": float(np.mean(np.asarray(v) > 0))} for k, v in sorted(out.items(), key=lambda x: str(x[0]))}


def summarize(trades):
    rows = []
    for t in trades:
        v = signal_value(t)
        if v is not None:
            rows.append(dict(t, v=v["after"], vb=v["before"], vc=v["commission"], size=v["size"]))
    if not rows:
        return {"n": 0}
    after = [r["v"] for r in rows]
    days_ = [r["day"] for r in rows]
    st = OK.cluster(after, days_)
    old = [r["v"] for r in rows if r["day"] < SPLIT]
    new = [r["v"] for r in rows if r["day"] >= SPLIT]
    pos = [dict(q, v=q["after"], s=r["s"], minute=r["minute"], season=r["season"]) for r in rows for q in r["positions"] if q["dist"] < MAX_PIPS]
    out = dict(st, win=float(np.mean(np.asarray(after) > 0)), before_mean=float(np.mean([r["vb"] for r in rows])),
               commission_mean=float(np.mean([r["vc"] for r in rows])), size_mean=float(np.mean([r["size"] for r in rows])),
               old_mean=float(np.mean(old)) if old else None, new_mean=float(np.mean(new)) if new else None, old_n=len(old), new_n=len(new),
               exits={k: sum(1 for q in pos if q["exit"] == k) for k in ("tp", "sl", "early", "time", "event", "end")},
               full=sum(1 for q in pos if q["second"]), first_only=sum(1 for q in pos if not q["second"]),
               by_side=_group(rows, lambda r: "売り" if r["s"] < 0 else "買い"),
               by_season=_group(rows, lambda r: r["season"]),
               by_time=_group(rows, lambda r: f"{r['minute'] // 60:02d}:{(r['minute'] % 60) // 30 * 30:02d}"),
               by_pair=_group(pos, lambda q: q["pair"]),
               by_pair_hour=_group(pos, lambda q: f"{q['pair']} {q['minute'] // 60:02d}時台"),
               by_exit=_group(pos, lambda q: q["exit"]),
               by_dist=_group(pos, lambda q: dist_bucket(q["dist"])),
               by_wait=_group(pos, lambda q: "0〜10分" if q["wait"] <= 10 else ("10〜20分" if q["wait"] <= 20 else "20〜30分")),
               by_eg=_group(pos, lambda q: {1: "上（ユーロが強い）", -1: "下（ポンドが強い）", 0: "レンジの中"}[q["eg"]]),
               by_adx=_group(pos, lambda q: q["adx"]),
               by_fill=_group(pos, lambda q: "満玉（2発目まで）" if q["second"] else "1発目だけ"))
    over = []
    for t in trades:
        v = signal_value(t, judged=False)
        if v is not None:
            over.append(v["after"])
    out["over60"] = {"n": len(over), "mean": float(np.mean(over)) if over else None}
    return out


def judge(seen, p, old_period):
    if seen.get("n", 0) < N_MIN:
        return "検定不能"
    if seen["lo"] is None or seen["lo"] <= 0:
        return "費用後マイナス" if (seen["hi"] is not None and seen["hi"] < 0) else "0と区別できない"
    if p is None or p >= ALPHA:
        return "でたらめな足と差なし"
    if not ((seen.get("old_mean") or 0) > 0 and (seen.get("new_mean") or 0) > 0):
        return "前半と後半で割れた"
    if not ((old_period.get("mean") or 0) > 0):
        return "昔の期間で消えた"
    if not ((seen.get("commission_mean") or 0) > 0 and (old_period.get("commission_mean") or 0) > 0):
        return "手数料で消える"
    return SURVIVED


def verdicts_of(arms, today):
    out = {}
    for arm, key in (("A", "KT1-A"), ("B", "KT1-B")):
        a = arms.get(arm) or {}
        v = a.get("verdict")
        s = a.get("seen") or {}
        if v and v != SURVIVED:
            out[key] = {"status": "stop", "decided_on": today, "n": s.get("n"), "mean": s.get("mean"), "lo": s.get("lo"), "hi": s.get("hi"),
                        "reason": f"{v}（過去のデータ・1回だけ数えた・手元の MT5 と Dukascopy の5分足・勝率 {(s.get('win') or 0) * 100:.1f}%・"
                                  f"機械の決まりは裁量の一部だけ）"}
    return out


# ════════════════════ 読み込みから判定まで ════════════════════

def load_all(folder, duka_root):
    seen = {p: read_mt5(folder, p) for p in PAIRS}
    old = {p: read_duka(duka_root, p) for p in PAIRS}
    # 昔の期間のスプレッドの下限＝見た期間の BigBoss の、そのペア・その時間（日本時間）の入る足の始まりのスプレッドの中央値
    floor = {}
    for p in PAIRS:
        b = seen[p]
        hours = b.index.tz_convert(JST).hour
        floor[p] = pd.Series(b["so"].to_numpy(float)).groupby(np.asarray(hours)).median().to_dict()
        if len(old[p]):
            oh = np.asarray(old[p].index.tz_convert(JST).hour)
            fl = np.array([floor[p].get(h, np.nan) for h in oh])
            old[p] = old[p].assign(so=np.fmax(old[p]["so"].to_numpy(float), np.nan_to_num(fl, nan=0.0)))
    abn = {}
    adx = {}
    for p in PAIRS:
        both = pd.concat([old[p], seen[p]]).sort_index()
        both = both[~both.index.duplicated(keep="last")]
        abn[p] = abnormal_days(daily_ranges(both))
        adx[p] = adx_series(both)
    return seen, old, abn, adx, floor


def run_all(folder, duka_root, events_path, n_perm=N_PERM):
    seen, old, abn, adx, floor = load_all(folder, duka_root)
    E = read_events(events_path)
    D_seen = panel(seen, SEEN_START, str(max(b.index.max() for b in seen.values()).date()))
    D_old = panel(old, OLD[0], OLD[1])
    r_seen = simulate(D_seen, E, abn, adx, collect_pool=True)
    r_old = simulate(D_old, E, abn, adx)
    arms = {}
    for arm in ("A", "B"):
        s_sum = summarize(r_seen["trades"][arm])
        o_sum = summarize(r_old["trades"][arm])
        p, pm = placebo(D_seen, E, r_seen["trades"][arm], r_seen["pool"], n_perm) if s_sum.get("n") else (None, None)
        s_sum["placebo_p"], s_sum["placebo_mean"] = p, pm
        arms[arm] = {"seen": s_sum, "old": o_sum, "verdict": judge(s_sum, p, o_sum),
                     "signals_seen": len(r_seen["signals"]), "signals_old": len(r_old["signals"]),
                     "not_entered_seen": len(r_seen["signals"]) - len(r_seen["trades"][arm]),
                     "not_entered_old": len(r_old["signals"]) - len(r_old["trades"][arm])}
    return {"arms": arms, "stats": {"seen": r_seen["stats"], "old": r_old["stats"]},
            "events": {p: int(len(E[p])) for p in PAIRS},
            "data": {"seen": f"{str(D_seen['idx'].min())[:10]}〜{str(D_seen['idx'].max())[:10]}",
                     "old": f"{str(D_old['idx'].min())[:10]}〜{str(D_old['idx'].max())[:10]}" if len(D_old["idx"]) else "なし"},
            "trades": {"seen": r_seen["trades"], "old": r_old["trades"]}}


def check(folder, duka_root, events_path):
    """足・線・合図・入れた数だけ（損益は数えない・何も書き出さない）"""
    seen, old, abn, adx, floor = load_all(folder, duka_root)
    rep = {"prereg_sha256": OK.section_sha256(PREREG, SECTION), "bars": {}}
    for name, bars in (("seen", seen), ("old", old)):
        for p in PAIRS:
            b = bars[p]
            so = b["so"].to_numpy(float) / pip(p) if len(b) else np.array([])
            rep["bars"][f"{name}:{p}"] = {"rows": int(len(b)), "first_utc": str(b.index.min()) if len(b) else None,
                                         "last_utc": str(b.index.max()) if len(b) else None,
                                         "spread_median_pips": float(np.nanmedian(so)) if len(so) else None}
    try:
        E = read_events(events_path)
        rep["events"] = {p: {"n": int(len(E[p])), "expected": EV_EXPECT[p], "ok": int(len(E[p])) == EV_EXPECT[p]} for p in PAIRS}
    except (OSError, SystemExit) as e:
        rep["events"] = {"error": str(e)}
        E = {p: np.array([], dtype=np.int64) for p in PAIRS}
    for name, bars, start, end in (("seen", seen, SEEN_START, None), ("old", old, OLD[0], OLD[1])):
        if not all(len(b) for b in bars.values()):
            rep[name] = {"error": "足が無い"}
            continue
        end = end or str(max(b.index.max() for b in bars.values()).date())
        D = panel(bars, start, end)
        r = simulate(D, E, abn, None, pnl=False)
        sig = r["signals"]
        rep[name] = {"days": r["stats"], "signals": len(sig),
                     "by_side_season": {f"{'売り' if s < 0 else '買い'}・{se}": sum(1 for g in sig if g["s"] == s and g["season"] == se)
                                        for s in (-1, 1) for se in ("冬", "夏")},
                     "entered": {arm: {"signals_with_entry": len(r["trades"][arm]),
                                       "judged": sum(1 for t in r["trades"][arm] if any(q["dist"] < MAX_PIPS for q in t["positions"])),
                                       "over60_only": sum(1 for t in r["trades"][arm] if all(q["dist"] >= MAX_PIPS for q in t["positions"]))}
                                 for arm in ("A", "B")}}
    rep["abnormal_share"] = {p: (sum(1 for v in abn[p].values() if v) / max(1, sum(1 for v in abn[p].values() if v is not None))) for p in PAIRS}
    return rep


def render_md(rec):
    f = lambda v: "—" if v is None else f"{v:+.2f}"
    L = ["# KT1 オーナーの型1：クロス円3つがそろって東京時間の最安値（最高値）を割ったら、戻りの 50% と線で分けて入る", "",
         f"更新: {rec.get('generated_jst')}（事前登録＝`PILLAR_PREREG.md`「KT1」・節の指紋 `{(rec.get('prereg_sha256') or '')[:12]}`）・"
         f"見た期間 {rec['data']['seen']}・昔の期間 {rec['data']['old']}・数字は pips（満玉1つ分・費用後）", "",
         "| 腕 | 判定 | 回数 | 平均 | 97.5%の幅 | 偽薬 p | 前半／後半 | 昔の期間 | 手数料後（見た／昔） | 勝率 | 入れなかった合図 |",
         "|---|---|---:|---:|---|---:|---|---|---|---:|---:|"]
    for arm, key in (("A", "KT1-A"), ("B", "KT1-B")):
        a = rec["arms"].get(arm) or {}
        s, o = a.get("seen") or {}, a.get("old") or {}
        if not s.get("n"):
            L.append(f"| {key} | {a.get('verdict')} | 0 | | | | | | | | {a.get('not_entered_seen')} |")
            continue
        pv = s.get("placebo_p")
        L.append(f"| {key} | **{a['verdict']}** | {s['n']} | {f(s['mean'])} | {f(s['lo'])}〜{f(s['hi'])} | {'—' if pv is None else format(pv, '.4f')} | "
                 f"{f(s['old_mean'])}／{f(s['new_mean'])} | {o.get('n', 0)}回・{f(o.get('mean'))} | {f(s.get('commission_mean'))}／{f(o.get('commission_mean'))} | "
                 f"{s['win'] * 100:.1f}% | {a.get('not_entered_seen')} |")
    L += ["", "## 読むための表（判定しない・回数・平均 pips・勝率）", ""]
    names = (("買い売り", "by_side"), ("冬夏", "by_season"), ("合図の時刻（30分ごと）", "by_time"), ("ペア（1ペア満玉あたり）", "by_pair"),
             ("ペア × 時間（通貨×時間帯）", "by_pair_hour"), ("出口", "by_exit"), ("線から新安値までの幅", "by_dist"), ("50%に届くまで", "by_wait"),
             ("ユーロポンド", "by_eg"), ("ADX(14)・1時間足", "by_adx"), ("1発目だけ／満玉", "by_fill"))
    for arm, key in (("A", "KT1-A"), ("B", "KT1-B")):
        for per in ("seen", "old"):
            s = (rec["arms"].get(arm) or {}).get(per) or {}
            if not s.get("n"):
                continue
            L += [f"### {key}・{'見た期間' if per == 'seen' else '昔の期間'}", "",
                  f"- 費用前の平均 {f(s.get('before_mean'))}・入れた大きさの平均 {s.get('size_mean', 0):.2f}（満玉＝1）・60 pips 以上（判定の外）{s['over60']['n']}回・{f(s['over60']['mean'])}"]
            for name, k in names:
                L.append(f"- {name}：" + "／".join(f"{g} {v['n']}・{f(v['mean'])}・{v['win'] * 100:.0f}%" for g, v in (s.get(k) or {}).items()))
            L.append("")
    L += ["---", "", "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。機械の決まりは裁量の一部だけを数えています。"]
    return "\n".join(L) + "\n"


def trades_csv(trades, path):
    rows = []
    for arm, ts in trades.items():
        for t in ts:
            for q in t["positions"]:
                rows.append({"arm": arm, "day": t["day"], "minute": t["minute"], "s": t["s"], "season": t["season"], "pair": q["pair"],
                             "weight": q["weight"], "dist": q["dist"], "wait": q["wait"], "after": q["after"], "before": q["before"],
                             "size": q["size"], "second": q["second"], "exit": q["exit"], "hold_min": q["hold_min"], "eg": q["eg"], "adx": q["adx"]})
    os.makedirs(os.path.dirname(path), exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")


def run(folder, duka_root, events_path, n_perm=N_PERM):
    res = run_all(folder, duka_root, events_path, n_perm)
    now = dt.datetime.now(JST)
    rec = {"kind": "backtest", "unit": "pips", "source": "手元の MT5（BigBoss）の実ティックの5分足（見た期間）・Dukascopy の1分足 → 5分足（昔の期間）",
           "generated_jst": now.isoformat(timespec="minutes"), "prereg_sha256": OK.section_sha256(PREREG, SECTION),
           "data": res["data"], "titles": TITLES, "verdicts": verdicts_of(res["arms"], now.date().isoformat()),
           "arms": res["arms"], "stats": res["stats"], "events": res["events"]}
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
    rec, trades = run(a.dir, a.duka, a.events)
    rec = OK._clean(rec)
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, ensure_ascii=False, indent=1)
    md = render_md(rec)
    os.makedirs(os.path.dirname(OUT_MD), exist_ok=True)
    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write(md)
    trades_csv(trades["seen"], OUT_CSV.format("seen"))
    trades_csv(trades["old"], OUT_CSV.format("old"))
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
