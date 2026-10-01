# -*- coding: utf-8 -*-
"""EA の記録を数える（手元で動かす・2026-09-30 AT1〜AT3・決まりは PILLAR_PREREG.md「AT」）。

入力（MT4 の共通フォルダ Common\\Files。EA は FILE_COMMON で書く）:
  mw_guard_log.csv   （AT1・本番） 列: utc,rule,ticket,symbol,action,mode,price,lots,profit,detail
      action＝close/partial/set_sl/notify（強制）・flag（見張りだけで「動くはずだった」印。detail の先頭が would_close など）
             ・final（flag を付けた建玉が閉じたときの最終の損益）
  mw_scalp5_log.csv  （AT2・本番） 列: plan,legs,ticket,open_utc,close_utc,symbol,dir,planned,fill,spread,lots,risk,balance,
                                    sl,close_price,profit,commission,swap,reason
  mw_swing4h_log.csv （AT3・デモ） 列: plan,legs,kind,status,ticket,signal_utc,seen_utc,open_utc,close_utc,symbol,dir,
                                    signal_price,fill,spread,lots,risk,balance,sl,tp,close_price,profit,commission,swap,reason
      status＝filled（建てた建玉が閉じた行）／skipped（建てなかった。reason に理由）
  時刻は UTC の 1970年からの秒。plan＝1回の注文（半分ずつの2本＝legs 2）。risk＝その注文全体の損切りまでの損失（口座の通貨）
  1回の R ＝ 注文の全部の建玉の（損益＋手数料＋スワップ）÷ risk（費用込み）

出力:
  AT3 → auto-forward.json（リポジトリ直下。R だけ・デモ口座・金額なし＝送ってよい。検証済みリストが読む）
  AT1・AT2 → --report-dir の md（既定 research/ea/。個人の取引なので送らない）
  🆕 2026-10-01 AT3 の振り返り（PILLAR_PREREG.md「AT」の追記）→ research/ea/at3-review.md と auto-forward.json の review（集計だけ）
      ずれ（遅れ・入った値のずれ・結果が変わった回・サイトの記録との差）／見送りの答え合わせ／負けの理由（AI の敗因分析）／直す候補
      ⚠️ 直す候補は文を出すだけ。いまの1か月の決まりは変えない（次の期間を登録するときに選ぶ）。サイトの記録は signals-log.json（--signals-log）
  🆕 2026-10-01 AT4 約定の試験（デモ・1日約100回・PILLAR_PREREG.md「AT」の追記）→ research/ea/at4-probe.md（手元専用・判定しない）
      mw_probe_log.csv 列: utc,symbol,side,bid,ask,fill_open,lat_open_ms,bid_close,ask_close,fill_close,lat_close_ms,atr_m5,atr_h4,event
      1往復の費用＝送った時のスプレッド＋建ての滑り＋決済の滑り（不利な向きがプラス）。5分足と4時間足の 1R（ATR×1.5）に対する割合も出す

実行: python ea_ledger.py --files "C:\\Users\\...\\MetaQuotes\\Terminal\\Common\\Files"
"""
import argparse
import collections
import csv
import datetime as dt
import io
import json
import os
import re
import sys

import screen_judge as J

JST = dt.timezone(dt.timedelta(hours=9))
FWD_START = "2026-10-01"          # AT3：この日（日本時間）以降に届いた合図だけ数える
# 🆕 2026-10-01 オーナー決定「2年も検証していたら長すぎる」＝AT3 は1か月で1回だけ区切る（PILLAR_PREREG.md「AT」の追記）。
# 300回・1000回の決まりは AT3 には使わない。この日（日本時間）までに届いた合図だけ数え、DECIDE_ON 以降に1回だけ判定する
CUT_END = "2026-10-31"
DECIDE_ON = "2026-11-08"          # 期間の建玉は7日で閉じる＝この日にはすべて閉じている（閉じていない注文があれば閉じるまで待つ）
STEP = 30                         # 読むための区切り（判定ではない）
REAL_MIN = 30                     # 本番へ移す条件の回数（デモ30回以上で幅の下限＞0。変えない）
GOAL = f"{FWD_START}〜{CUT_END} に届いた合図・{DECIDE_ON} 以降に1回だけ判定"
SECTION = "## AT "
OUT_JSON = "auto-forward.json"
TITLE_AT3 = "4時間足のメールの合図を、デモ口座で自動に建てる（前向き・費用込みの R）"
LABELS = {"ok": "機能している", "unknown": "まだ分からない", "stop": "反証（手を止めて設計に戻る）"}
SIG_LOG = "signals-log.json"
PAPER_R = {"tp1": 4 / 3, "tp2": 2.0, "sl": -1.0, "expired": 0.0}   # サイトの成績表と同じ近似（利確1＝ATR×2÷ATR×1.5）
MATCH_SEC = 180                   # 記録の合図とサイトの合図を（銘柄・時刻）で突き合わせるときの許し（秒）
LEG_TOL = 0.15                    # 出た値が利確・損切りの値から「損切りまでの幅×0.15」以内ならそこで出たと読む
# 直す候補を出す条件（PILLAR_PREREG.md「AT」の追記①〜⑥。結果を見て変えない）
PROPOSE = {"delay_min": 60, "entry_gap_r": 0.10, "flips": 3, "skip_n": 5, "skip_gap_r": 0.3, "lot_min_share": 0.30,
           "paper_gap_n": 10, "paper_gap_r": 0.2}


# ───────── 読む ─────────
def read_csv(path):
    """MT4 の CSV（UTF-16 でも ANSI でも）を辞書の並びにする。無ければ空"""
    if not os.path.exists(path):
        return []
    raw = open(path, "rb").read()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        text = raw.decode("utf-16")
    else:
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw.decode("cp932", errors="replace")
    return [{k.strip(): (v or "").strip() for k, v in r.items() if k} for r in csv.DictReader(io.StringIO(text))]


def _f(x, default=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def jst_date(utc_sec):
    return dt.datetime.fromtimestamp(int(_f(utc_sec)), JST).date().isoformat()


def plans(rows, date_key):
    """閉じた建玉の行を注文ごとにまとめる。legs 本すべて閉じた注文だけ返す（入った順）"""
    g = collections.OrderedDict()
    for r in rows:
        if r.get("status", "filled") != "filled" or not r.get("close_utc"):
            continue
        g.setdefault(r["plan"], []).append(r)
    out, still_open = [], 0
    for pid, rs in g.items():
        legs = int(_f(rs[0].get("legs"), 1)) or 1
        if len({r["ticket"] for r in rs}) < legs:
            still_open += 1
            continue
        risk = _f(rs[0].get("risk"))
        if risk <= 0:
            continue
        money = sum(_f(r.get("profit")) + _f(r.get("commission")) + _f(r.get("swap")) for r in rs)
        first = rs[0]
        out.append({"plan": pid, "r": money / risk, "date": jst_date(first[date_key]), "t": int(_f(first[date_key])),
                    "kind": first.get("kind", ""), "symbol": first.get("symbol", ""),
                    "delay_min": (round((_f(first.get("seen_utc")) - _f(first.get("signal_utc"))) / 60, 1)
                                  if first.get("seen_utc") and first.get("signal_utc") else None),
                    "rows": rs})
    return sorted(out, key=lambda p: p["t"]), still_open


# ───────── 数える ─────────
def label(st):
    if st["lo"] is not None and st["lo"] > 0:
        return "ok"
    if st["hi"] is not None and st["hi"] < 0:
        return "stop"
    return "unknown"


def checkpoints(rs, dates):
    out = []
    for k in range(STEP, len(rs) + 1, STEP):
        st = J.cluster_stats(rs[:k], dates[:k])
        out.append({"n": k, "mean": J._f(st["mean"]), "lo": J._f(st["lo"]), "hi": J._f(st["hi"]),
                    "win": J._f(st["win"]), "label": label(st)})
    return out


def at3_verdict(prev, rs, dates, today, still_open):
    """オーナーの決まり（2026-10-01）：期間（FWD_START〜CUT_END に届いた合図）の注文がすべて閉じたあと、DECIDE_ON 以降に1回だけ。
    幅の下限が0より上＝プラス／それ以外（0をまたぐ・まるごと下・0回）＝ストップ。一度出たら変えない"""
    if prev:
        return prev
    if today < DECIDE_ON or still_open:
        return None
    period = f"{FWD_START}〜{CUT_END} に届いた合図"
    n = len(rs)
    if n == 0:
        return {"status": "stop", "decided_on": today, "n": 0, "mean": None, "lo": None, "hi": None,
                "reason": f"{period}で建てた回数が0"}
    st = J.cluster_stats(rs, dates)
    lo, hi = J._f(st["lo"]), J._f(st["hi"])
    if lo is not None and lo > 0:
        status = "plus"
        reason = f"{period}の{n}回で費用込みの平均の幅がまるごと0より上" + (
            f"（{REAL_MIN}回に届かないので本番へは移さない）" if n < REAL_MIN else "")
    elif hi is not None and hi < 0:
        status, reason = "stop", f"{period}の{n}回で費用込みの平均の幅がまるごと0より下"
    elif st["mean"] <= 0:
        status, reason = "stop", f"{period}の{n}回で費用込みの平均がマイナス（幅は0をまたぐ）"
    else:
        status, reason = "stop", f"{period}の{n}回ではプラスと言い切れない（幅が0をまたぐ）"
    return {"status": status, "decided_on": today, "n": n, "mean": J._f(st["mean"]), "lo": lo, "hi": hi, "reason": reason}


def at3_state(v, today, still_open):
    """判定がまだのとき、いまどこにいるか（読むための一言）"""
    if v:
        return "判定済み（変えない）"
    if today <= CUT_END:
        return f"数えている途中（{CUT_END} までに届いた合図）"
    if today < DECIDE_ON:
        return f"区切りのあと＝期間の建玉が閉じるのを待っている（{DECIDE_ON} に判定）"
    return f"期間の注文のうち {still_open} 回がまだ閉じていない＝閉じてから判定"


# ───────── AT3 の振り返り（読むための表・判定に使わない） ─────────
def _base(sym):
    """銘柄名を比べやすく（GBPJPY=X・GBPJPY.m → GBPJPY）"""
    return re.sub(r"[^A-Z]", "", str(sym or "").upper())[:6]


def load_signal_index(path=SIG_LOG):
    """signals-log.json の4時間足を、id と（銘柄・時刻）で引けるようにする。無ければ空"""
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return {}, {}
    by_id, by_sym = {}, collections.defaultdict(list)
    for s in data if isinstance(data, list) else []:
        if s.get("timeframe") != "4h":
            continue
        try:
            ts = int(dt.datetime.fromisoformat(str(s["fired_at"])).timestamp())
        except (KeyError, ValueError):
            continue
        rec = {"id": s.get("id"), "t": ts, "outcome": s.get("outcome"),
               "cause": (((s.get("loss_analysis") or {}).get("ai_result")) or {}).get("primary_category")}
        by_id[rec["id"]] = rec
        by_sym[_base(s.get("ticker"))].append(rec)
    return by_id, by_sym


def find_signal(index, plan, symbol, signal_utc):
    """記録の注文 → サイトの合図（id が同じもの、無ければ同じ銘柄で時刻がいちばん近いもの・180秒以内）"""
    by_id, by_sym = index or ({}, {})
    if plan in by_id:
        return by_id[plan]
    t, best = int(_f(signal_utc)), None
    for rec in by_sym.get(_base(symbol), []):
        d = abs(rec["t"] - t)
        if d <= MATCH_SEC and (best is None or d < best[0]):
            best = (d, rec)
    return best[1] if best else None


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def trade_review(p, index):
    """1回の注文の振り返り：遅れ・入った値のずれ（R）・1本目（利確1）の結果とサイトの記録の結果"""
    rs, first = p["rows"], p["rows"][0]
    sp, sl, fill = _f(first.get("signal_price")), _f(first.get("sl")), _f(first.get("fill"))
    d = 1 if int(_f(first.get("dir"), 1)) > 0 else -1
    dist = abs(sp - sl)
    gap = (fill - sp) * d / dist if dist > 0 and fill else None
    demo = None
    if dist > 0:
        leg1 = min(rs, key=lambda r: abs(_f(r.get("tp")) - sp))          # 合図の値に近いほうの利確＝利確1の建玉
        cp, tp = _f(leg1.get("close_price")), _f(leg1.get("tp"))
        demo = "tp" if tp and abs(cp - tp) <= LEG_TOL * dist else "sl" if abs(cp - sl) <= LEG_TOL * dist else "other"
    sig = find_signal(index, p["plan"], first.get("symbol"), first.get("signal_utc"))
    outcome = sig["outcome"] if sig else None
    paper = {"tp1": "tp", "tp2": "tp", "sl": "sl", "expired": "other"}.get(outcome)
    flip = None
    if demo in ("tp", "sl") and paper in ("tp", "sl") and demo != paper:
        flip = "worse" if demo == "sl" else "better"
    return {"plan": p["plan"], "date": p["date"], "symbol": first.get("symbol", ""), "r": p["r"], "delay_min": p["delay_min"],
            "entry_gap_r": gap, "demo_leg1": demo, "paper": outcome, "paper_r": PAPER_R.get(outcome), "flip": flip,
            "cause": (sig or {}).get("cause") if p["r"] < 0 else None}


def skip_review(rows, index):
    """見送った合図（1つの合図は1回だけ数える）のサイトの記録の成績を、見送りの理由ごとに"""
    seen, by = set(), collections.defaultdict(list)
    for r in rows:
        if r.get("status") != "skipped" or r.get("plan") in seen:
            continue
        seen.add(r.get("plan"))
        sig = find_signal(index, r.get("plan"), r.get("symbol"), r.get("signal_utc"))
        by[r.get("reason") or "（理由なし）"].append(PAPER_R.get(sig["outcome"]) if sig else None)
    return {k: {"n": len(v), "paper_n": sum(1 for x in v if x is not None), "paper_mean": J._f(_mean(v))} for k, v in by.items()}


def propose(gap, skips):
    """直す候補（決まった条件で文を出すだけ。自動では入れない）"""
    out, tail = [], "（次の期間を登録するときに選ぶ・いまの1か月は変えない）"
    c = PROPOSE
    if gap["delay_min"] is not None and gap["delay_min"] > c["delay_min"]:
        out.append({"id": "①", "text": f"合図を受け取るまでの遅れが平均 {gap['delay_min']:.0f}分。橋渡しの間隔や Actions の遅れを減らす{tail}"})
    if gap["entry_gap_r"] is not None and gap["entry_gap_r"] > c["entry_gap_r"]:
        out.append({"id": "②", "text": f"入った値のずれで1回あたり {gap['entry_gap_r']:.2f}R 不利。合図の値の指値で入る形を試す{tail}"})
    if gap["worse_flips"] >= c["flips"] and gap["worse_flips"] > gap["better_flips"]:
        out.append({"id": "③", "text": f"ずれでサイトの記録の利確がデモでは損切りに変わった回が {gap['worse_flips']}回（逆は {gap['better_flips']}回）。遅れ・入り方を見直す{tail}"})
    taken = gap["paper_mean"]
    for reason, s in sorted(skips.items()):
        if s["paper_n"] >= c["skip_n"] and taken is not None and s["paper_mean"] is not None and s["paper_mean"] - taken >= c["skip_gap_r"]:
            out.append({"id": "④", "text": f"見送りの理由「{reason}」の合図はサイトの記録で平均 {s['paper_mean']:+.2f}R（建てた合図は {taken:+.2f}R）。この見送りで良い取引を外している可能性{tail}"})
    total = sum(s["n"] for s in skips.values())
    lot = sum(s["n"] for k, s in skips.items() if "lot_min" in k)
    if total and lot / total > c["lot_min_share"]:
        out.append({"id": "⑤", "text": f"見送りの {lot / total:.0%} が最小ロット（lot_min）。損切りの広い合図が建てられず偏る。残高か口座の最小ロットを見直す{tail}"})
    if gap["paper_n"] >= c["paper_gap_n"] and gap["demo_mean"] is not None and gap["paper_mean"] is not None \
            and gap["demo_mean"] - gap["paper_mean"] <= -c["paper_gap_r"]:
        out.append({"id": "⑥", "text": f"デモの平均 {gap['demo_mean']:+.2f}R がサイトの記録 {gap['paper_mean']:+.2f}R より悪い。メールを見て手で建てても同じだけ悪くなる可能性{tail}"})
    return out


def at3_review(rows, ps, index):
    tr = [trade_review(p, index) for p in ps]
    with_paper = [t for t in tr if t["paper_r"] is not None]
    gap = {"n": len(tr), "delay_min": _mean(t["delay_min"] for t in tr), "entry_gap_r": _mean(t["entry_gap_r"] for t in tr),
           "worse_flips": sum(1 for t in tr if t["flip"] == "worse"), "better_flips": sum(1 for t in tr if t["flip"] == "better"),
           "paper_n": len(with_paper), "demo_mean": _mean(t["r"] for t in with_paper), "paper_mean": _mean(t["paper_r"] for t in with_paper)}
    skips = skip_review(rows, index)
    causes = collections.Counter(t["cause"] for t in tr if t["cause"])
    review = {"gap": {k: (J._f(v) if isinstance(v, float) else v) for k, v in gap.items()}, "skips": skips,
              "loss_causes": dict(causes.most_common()), "proposals": propose(gap, skips)}
    return review, tr


# ───────── AT4 約定の試験（読むための表・判定しない） ─────────
PROBE_LOG = "mw_probe_log.csv"


def _pip(sym):
    return 0.01 if "JPY" in str(sym or "").upper() else 0.0001


def _q(xs, q):
    """分位（q＝0.5 で中央値・0.9 で90%点）。値が無ければ None"""
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    k = (len(xs) - 1) * q
    lo = int(k)
    return xs[lo] + (xs[min(lo + 1, len(xs) - 1)] - xs[lo]) * (k - lo)


def probe_rows(rows):
    """約定の試験の1行 → スプレッド・滑り・費用（pips と R）"""
    out = []
    for r in rows:
        side = 1 if int(_f(r.get("side"), 1)) > 0 else -1
        bid, ask, fo = _f(r.get("bid")), _f(r.get("ask")), _f(r.get("fill_open"))
        bc, ac, fc = _f(r.get("bid_close")), _f(r.get("ask_close")), _f(r.get("fill_close"))
        if not all((bid, ask, fo, bc, ac, fc)):
            continue
        spread = ask - bid
        slip_o = (fo - ask) if side > 0 else (bid - fo)             # 買いは売値（ask）より高く、売りは買値（bid）より安く約定したら不利
        slip_c = (bc - fc) if side > 0 else (fc - ac)
        cost = spread + slip_o + slip_c
        a5, a4, pip = _f(r.get("atr_m5")), _f(r.get("atr_h4")), _pip(r.get("symbol"))
        out.append({"symbol": r.get("symbol", ""), "hour": dt.datetime.fromtimestamp(int(_f(r.get("utc"))), JST).hour,
                    "event": str(r.get("event", "")).strip() in ("1", "true", "True"),
                    "spread_pip": spread / pip, "slip_open_pip": slip_o / pip, "slip_close_pip": slip_c / pip,
                    "lat_open": _f(r.get("lat_open_ms"), None), "lat_close": _f(r.get("lat_close_ms"), None),
                    "cost_r5": cost / (1.5 * a5) if a5 > 0 else None, "cost_r4": cost / (1.5 * a4) if a4 > 0 else None})
    return out


def probe_summary(ps):
    def col(k):
        return [p[k] for p in ps]
    return {"n": len(ps), "spread_med": _q(col("spread_pip"), .5), "spread_p90": _q(col("spread_pip"), .9),
            "slip_open_mean": _mean(col("slip_open_pip")), "slip_open_p90": _q(col("slip_open_pip"), .9),
            "slip_close_mean": _mean(col("slip_close_pip")), "slip_close_p90": _q(col("slip_close_pip"), .9),
            "lat_med": _q(col("lat_open") + col("lat_close"), .5), "lat_p90": _q(col("lat_open") + col("lat_close"), .9),
            "cost_r5_med": _q(col("cost_r5"), .5), "cost_r5_p90": _q(col("cost_r5"), .9),
            "cost_r4_med": _q(col("cost_r4"), .5), "cost_r4_p90": _q(col("cost_r4"), .9)}


def probe_report(rows):
    ps = probe_rows(rows)
    s = probe_summary(ps)

    def n_(x, f="{:.2f}"):
        return "—" if x is None else f.format(x)

    def pct(x):
        return "—" if x is None else f"{x * 100:.1f}%"
    L = ["# AT4 約定の試験（デモ・手元専用・読むための表＝判定しない）", "",
         "⚠️ デモの約定は本番より良いことがある。本番の値は AT2 の実際の取引（予定価格と約定）で確かめる。", "",
         f"- 回数 {s['n']}・スプレッド 中央値 {n_(s['spread_med'])}pips（90%点 {n_(s['spread_p90'])}）",
         f"- 滑り（不利がプラス）：建て 平均 {n_(s['slip_open_mean'])}pips（90%点 {n_(s['slip_open_p90'])}）／決済 平均 {n_(s['slip_close_mean'])}pips（90%点 {n_(s['slip_close_p90'])}）",
         f"- 約定までの時間：中央値 {n_(s['lat_med'], '{:.0f}')}ミリ秒（90%点 {n_(s['lat_p90'], '{:.0f}')}）",
         f"- **1往復の費用が損切り幅に占める割合**：5分足 中央値 {pct(s['cost_r5_med'])}（90%点 {pct(s['cost_r5_p90'])}）／4時間足 中央値 {pct(s['cost_r4_med'])}（90%点 {pct(s['cost_r4_p90'])}）",
         "", "## ペアごと", "", "| ペア | 回数 | スプレッド中央値 | 滑り（建て）平均 | 費用÷5分足の1R | 費用÷4時間足の1R |", "|---|---:|---:|---:|---:|---:|"]
    by = collections.defaultdict(list)
    for p in ps:
        by[p["symbol"]].append(p)
    for sym, xs in sorted(by.items()):
        q = probe_summary(xs)
        L.append(f"| {sym} | {q['n']} | {n_(q['spread_med'])} | {n_(q['slip_open_mean'])} | {pct(q['cost_r5_med'])} | {pct(q['cost_r4_med'])} |")
    L += ["", "## 日本時間の1時間ごと（全部のペア）", "", "| 時 | 回数 | スプレッド中央値 | 費用÷5分足の1R（中央値） |", "|---:|---:|---:|---:|"]
    byh = collections.defaultdict(list)
    for p in ps:
        byh[p["hour"]].append(p)
    for h in sorted(byh, key=lambda h: (h - 15) % 24):                      # 15時から並べる
        q = probe_summary(byh[h])
        L.append(f"| {h} | {q['n']} | {n_(q['spread_med'])} | {pct(q['cost_r5_med'])} |")
    ev = [p for p in ps if p["event"]]
    L += ["", f"- 重要な発表の前後：{len(ev)}回・費用÷5分足の1R 中央値 {pct(probe_summary(ev)['cost_r5_med'])}"
          f"（それ以外 {pct(probe_summary([p for p in ps if not p['event']])['cost_r5_med'])}）"]
    return "\n".join(L) + "\n", s


FLIP_TXT = {"worse": "負けに変わった", "better": "得に変わった"}


def review_md(review, tr):
    g = review["gap"]

    def r_(x):
        return "—" if x is None else f"{x:+.3f}R"
    L = ["# AT3 の振り返り（手元専用・読むための表＝判定には使わない）", "",
         "## ずれ（自動で建てたときに、サイトの記録からどれだけ離れたか）", "",
         f"- 閉じた注文 {g['n']} 回",
         f"- 受け取りの遅れの平均：{'—' if g['delay_min'] is None else str(round(g['delay_min'])) + '分'}",
         f"- 入った値のずれの平均（不利な向きがプラス）：{r_(g['entry_gap_r'])}",
         f"- 1本目（利確1）の結果がサイトの記録と変わった回：負けに変わった {g['worse_flips']}回／得に変わった {g['better_flips']}回",
         f"- サイトの記録と比べられた {g['paper_n']}回：デモ {r_(g['demo_mean'])}／サイトの記録 {r_(g['paper_mean'])}（デモは半分ずつ・金曜決済なので計画の違いも入る）",
         "", "## 見送りの答え合わせ（見送った合図のサイトの記録の成績）", ""]
    if review["skips"]:
        L += ["| 見送りの理由 | 回数 | 記録で比べられた回数 | サイトの記録の平均 |", "|---|---:|---:|---:|"]
        L += [f"| {k} | {s['n']} | {s['paper_n']} | {r_(s['paper_mean'])} |" for k, s in sorted(review["skips"].items(), key=lambda x: -x[1]["n"])]
        L.append(f"| （建てた合図） | {g['n']} | {g['paper_n']} | {r_(g['paper_mean'])} |")
    else:
        L.append("- まだ無い")
    L += ["", "## 負けの理由（デモで負けた回の合図の AI の敗因分析）", ""]
    L += [f"- {k}：{n}回" for k, n in review["loss_causes"].items()] or ["- まだ無い（敗因分析が付くのはサイトの記録で損切りに届いた合図だけ）"]
    L += ["", "## 直す候補（自動では入れない＝11/8 の判定のあと、次の期間を登録するときに選ぶ）", ""]
    L += [f"- {x['id']} {x['text']}" for x in review["proposals"]] or ["- いまは無い"]
    L += ["", "## 注文ごと", "", "| 日付 | 銘柄 | R | 遅れ | 入った値のずれ | 1本目 | サイトの記録 | 変化 |", "|---|---|---:|---:|---:|---|---|---|"]
    L += [f"| {t['date']} | {t['symbol']} | {t['r']:+.2f} | {'—' if t['delay_min'] is None else t['delay_min']} | {r_(t['entry_gap_r'])} | "
          f"{t['demo_leg1'] or '—'} | {t['paper'] or '—'} | {FLIP_TXT.get(t['flip'], '')} |" for t in tr]
    return "\n".join(L) + "\n"


def build_at3(swing_rows, prev=None, today=None, now=None, index=None):
    today = today or dt.datetime.now(JST).date().isoformat()

    def in_period(r):
        return FWD_START <= jst_date(r.get("signal_utc")) <= CUT_END

    rows = [r for r in swing_rows if in_period(r)]                      # 期間の外（登録より前・区切りのあと）は数えない
    after = {r.get("plan") for r in swing_rows if jst_date(r.get("signal_utc")) > CUT_END}
    ps, still_open = plans(rows, "signal_utc")
    rs, dates = [p["r"] for p in ps], [p["date"] for p in ps]
    skipped = collections.Counter(r.get("reason") or "（理由なし）" for r in rows if r.get("status") == "skipped")
    v = at3_verdict(((prev or {}).get("verdicts") or {}).get("AT3"), rs, dates, today, still_open)
    st = J.cluster_stats(rs, dates)
    return {"kind": "forward", "unit": "R", "goal": GOAL, "fwd_start": FWD_START, "cut_end": CUT_END, "decide_on": DECIDE_ON,
            "generated_jst": now or dt.datetime.now(JST).isoformat(timespec="minutes"),
            "prereg_sha256": J.section_sha256(head=SECTION),
            "titles": {"AT3": TITLE_AT3}, "verdicts": {"AT3": v} if v else {},
            "summary": {"n": len(rs), "mean": J._f(st["mean"]), "lo": J._f(st["lo"]), "hi": J._f(st["hi"]),
                        "win": J._f(st["win"]), "open_plans": still_open, "after_cut_signals": len(after),
                        "state": at3_state(v, today, still_open)},
            "checkpoints": checkpoints(rs, dates), "skipped": dict(skipped),
            "review": at3_review(rows, ps, index)[0],
            "trades": [{"c": "AT3", "d": p["date"], "r": round(p["r"], 4), "kind": p["kind"], "delay_min": p["delay_min"]}
                       for p in ps]}


def guard_report(rows):
    """AT1：決まりごとの発動の回数と、見張りだけの期間の「動いていたら」の差（読むための表）"""
    cnt = collections.Counter((r.get("rule"), r.get("mode"), r.get("action")) for r in rows if r.get("action") != "final")
    finals = {r["ticket"]: _f(r.get("profit")) for r in rows if r.get("action") == "final"}
    pairs, seen = [], set()
    for r in rows:
        if r.get("action") == "flag" and r.get("detail", "").startswith("would_close") and (r["ticket"], r["rule"]) not in seen:
            seen.add((r["ticket"], r["rule"]))
            if r["ticket"] in finals:
                pairs.append({"rule": r["rule"], "ticket": r["ticket"], "at_flag": _f(r.get("profit")),
                              "final": finals[r["ticket"]]})
    L = ["# AT1 守りの見張り番の記録（手元専用・送らない）", "",
         "| 決まり | 見張りだけ／強制 | したこと | 回数 |", "|---|---|---|---:|"]
    L += [f"| {k[0]} | {k[1]} | {k[2]} | {n} |" for k, n in sorted(cnt.items(), key=lambda x: (str(x[0]), -x[1]))] or ["| — | — | — | 0 |"]
    L += ["", "## 見張りだけの期間：「決済していたら」と実際の差（口座の通貨・プラス＝見張り番が動いていたら得だった）", ""]
    by = collections.defaultdict(list)
    for p in pairs:
        by[p["rule"]].append(p["at_flag"] - p["final"])
    L += [f"- {k}：{len(v)}件・差の合計 {sum(v):+,.0f}・1件あたり {sum(v) / len(v):+,.0f}" for k, v in sorted(by.items())] or ["- まだ無い"]
    L += ["", "読むための表（判定しない）。決まりの値を変えるときは PILLAR_PREREG.md「AT」に日付つきで追記する。"]
    return "\n".join(L) + "\n", pairs


def scalp_report(rows):
    """AT2：MY_TRADING_RULES.md「デイトレ開始にあたっての事前登録」の区切り（30回ごと）"""
    ps, still_open = plans(rows, "open_utc")
    rs, dates = [p["r"] for p in ps], [p["date"] for p in ps]
    st = J.cluster_stats(rs, dates)
    cps = checkpoints(rs, dates)
    mean_txt = "—" if st["mean"] is None else f"{st['mean']:+.3f}R"
    L = ["# AT2 5分足の執行アシストの記録（手元専用・送らない）", "",
         f"- 閉じた注文 {len(ps)} 回（まだ開いている {still_open}）・費用込みの平均 {mean_txt}", ""]
    L += ["| 区切り | 平均 | 95％の幅 | 勝率 | 判定 |", "|---:|---:|---|---:|---|"]
    L += [f"| {c['n']} | {c['mean']:+.3f}R | {c['lo']:+.3f}〜{c['hi']:+.3f}R | {c['win'] * 100:.0f}％ | {LABELS[c['label']]} |"
          for c in cps] or ["| — | — | — | — | まだ30回に届いていない |"]
    slip = [(_f(r["fill"]) - _f(r["planned"])) * (1 if int(_f(r["dir"])) > 0 else -1)
            for p in ps for r in p["rows"][:1] if r.get("planned") and r.get("fill")]
    by_hour = collections.defaultdict(list)
    for p in ps:
        by_hour[dt.datetime.fromtimestamp(p["t"], JST).hour].append(p["r"])
    L += ["", "## 読むための表（判定しない）", "",
          f"- 滑り（約定−予定・不利な向きがプラス・値の単位）：平均 {sum(slip) / len(slip):+.5f}" if slip else "- 滑り：まだ無い"]
    L += [f"- 日本時間 {h}時台：{len(v)}回・平均 {sum(v) / len(v):+.3f}R" for h, v in sorted(by_hour.items())]
    return "\n".join(L) + "\n", cps


def main(argv=None):
    ap = argparse.ArgumentParser(description="EA の記録を数える（AT1〜AT3）")
    ap.add_argument("--files", required=True, help="MT4 の Common\\Files")
    ap.add_argument("--report-dir", default=os.path.join("research", "ea"))
    ap.add_argument("--json-out", default=OUT_JSON)
    ap.add_argument("--today")
    ap.add_argument("--signals-log", default=SIG_LOG, help="サイトの記録（振り返りで突き合わせる）")
    a = ap.parse_args(argv)
    index = load_signal_index(a.signals_log)
    prev = None
    if os.path.exists(a.json_out):
        with open(a.json_out, encoding="utf-8") as fh:
            prev = json.load(fh)
    swing = read_csv(os.path.join(a.files, "mw_swing4h_log.csv"))
    at3 = build_at3(swing, prev, a.today, index=index)
    with open(a.json_out, "w", encoding="utf-8") as fh:
        json.dump(at3, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    os.makedirs(a.report_dir, exist_ok=True)
    g_md, _ = guard_report(read_csv(os.path.join(a.files, "mw_guard_log.csv")))
    s_md, _ = scalp_report(read_csv(os.path.join(a.files, "mw_scalp5_log.csv")))
    in_period = [r for r in swing if FWD_START <= jst_date(r.get("signal_utc")) <= CUT_END]
    ps, _ = plans(in_period, "signal_utc")
    review, tr = at3_review(in_period, ps, index)
    probe = read_csv(os.path.join(a.files, PROBE_LOG))
    reports = [("at1-guard.md", g_md), ("at2-scalp5.md", s_md), ("at3-review.md", review_md(review, tr))]
    if probe:
        reports.append(("at4-probe.md", probe_report(probe)[0]))
    for name, md in reports:
        with open(os.path.join(a.report_dir, name), "w", encoding="utf-8") as fh:
            fh.write(md)
    s = at3["summary"]
    print(f"AT3：{s['n']}回（開いている {s['open_plans']}）・{s['state']}・判定 {at3['verdicts'].get('AT3', {}).get('status', 'まだ')} → {a.json_out}")
    print(f"AT1・AT2 の報告と AT3 の振り返り{'・AT4 約定の試験' if probe else ''} → {a.report_dir}（送らない）・直す候補 {len(review['proposals'])}件"
          + ("" if index[0] else "（signals-log.json が読めず、サイトの記録との突き合わせは空）"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
