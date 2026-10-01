# -*- coding: utf-8 -*-
"""ドル円5分足の「取引→検証→改善」の繰り返し（LP）の判定と台帳（2026-10-01 登録＝PILLAR_PREREG.md「LP」）。

オーナー「10万円のデモ口座で1日平均3%以上…取引の検証をして、改善をして、また取引をする。この繰り返しで目標を達成するまで繰り返す設計」。

役目の分け方:
  - 過去で数える（値動きの計算）＝手元の research/loop/loop_lab.py（MT5 の5分足・M5 の入口と出口を使い回す）
  - デモで建てる＝手元の research/ea/MW_Loop5.mq5（記録 mw_loop_log.csv＝mw_scalp5_log.csv と同じ列＋ round）
  - 判定・段階・台帳＝このファイル（リポジトリ直下・テストつき・計算より先にコミット）。手元はこれを import し、判定を書き換えない

物差し＝1日の損益率（日本時間 07:00 区切り）。過去＝Σ(R×1%)・デモ＝損益÷その日の初めの残高（％だけ・金額は台帳に書かない）。
1日の損失の上限 −3%（AT1 の G5）は過去の計算にも入れる。段は**デモ（前向き）の数字だけ**で上がる。
⚠️ 値（1%・−3%・段の目標・窓・20ラウンド〔登録は12→追記①で20〕・3回）は登録どおりに固定。結果を見て変えない。

手元での使い方:
    import loop_judge as LJ
    led = LJ.load(path) or LJ.new_ledger()
    LJ.register_round(led, "LP-01", mechanism="…", change="…", reason="…", parent=None, variants=1, on="2026-10-02")
    sel = LJ.daily_from_r(選ぶ期間の取引); con = LJ.daily_from_r(確かめ期間の取引)
    LJ.record_backtest(led, "LP-01", sel, con, placebo_p=…)          # 関門A（段0）
    LJ.record_forward(led, "LP-01", LJ.daily_from_money(デモの記録の行), today="…")   # 段1〜4
    LJ.save(led, path); open(md, "w").write(LJ.render_md(led))
"""
import collections
import datetime as dt
import json
import math
import sys

import screen_judge as J

SECTION = "## LP "
RISK_PCT = 0.01                   # 1回のリスク＝残高の1%
DAILY_STOP = -0.03                # 1日の損失の上限（AT1 の G5）
DAY_CUT_HOUR = 7                  # 日本時間 07:00 区切り
JST = dt.timezone(dt.timedelta(hours=9))
SELECT = ("2022-06-01", "2024-07-31")
CONFIRM = ("2024-08-01", "2026-09-24")
STAGES = [("S0", "費用後の期待値が0より上（過去の確かめ期間）", None),
          ("S1", "デモの前向きでも0より上", 0.0),
          ("S2", "1日平均 +0.3%", 0.003),
          ("S3", "1日平均 +1%", 0.01),
          ("S4", "1日平均 +3%（オーナーの目標）", 0.03)]
ALPHA = 0.05
CONFIRM_BASE = 6                  # 確かめた回数の累計は M5-3 の6回から始める
MAX_VARIANTS = 3                  # 同じ仕組みの値違いは1ラウンドに3つまで
MAX_ROUNDS = 20                   # 20ラウンドで段1に届かなければ止める（登録は12だった→2026-10-01 夕・オーナー指示で20に。PREREG「LP」追記①）
MAX_FWD_FAILS = 3                 # 段0の決まりが3回続けてデモで消えたら止める
FWD_MIN_TRADES, FWD_MIN_DAYS = 100, 10
EARLY_TRADES, EARLY_DAYS = 30, 5
Z95 = J.Z95
OUT_REASONS = {"select": "選ぶ期間で費用後プラスでない", "confirm": "確かめ期間で費用後プラスでない",
               "placebo": "偽薬と差なし", "faded": "前向きで消えた", "stage1": "前向きで段1に届かなかった"}


# ───────── 日ごとに ─────────
def trading_day(utc_sec):
    """UTC の秒 → 日本時間 07:00 区切りの日付"""
    t = dt.datetime.fromtimestamp(int(float(utc_sec)), JST)
    if t.hour < DAY_CUT_HOUR:
        t -= dt.timedelta(days=1)
    return t.date().isoformat()


def _f(x, default=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def daily_from_r(trades, risk=RISK_PCT, stop=DAILY_STOP):
    """過去の取引（入った順・{"t": UTC秒 または "d": 日付, "r": 費用後のR, "cost_r": 費用のR(任意)}）→ 日ごとの損益率。
    1日の累計が stop に届いたら、その日の残りは入らない（stopped）"""
    days = collections.OrderedDict()
    for x in trades:
        d = x["d"] if x.get("d") else trading_day(x["t"])
        day = days.setdefault(d, {"d": d, "pct": 0.0, "n": 0, "cost_pct": 0.0, "stopped": False, "skipped": 0})
        if day["stopped"]:
            day["skipped"] += 1
            continue
        day["pct"] += float(x["r"]) * risk
        day["cost_pct"] += _f(x.get("cost_r")) * risk
        day["n"] += 1
        if day["pct"] <= stop:
            day["stopped"] = True
    return list(days.values())


def daily_from_money(rows):
    """デモの記録（mw_loop_log.csv の行＝open_utc・balance・profit・commission・swap）→ 日ごとの損益率（％だけ）"""
    days = collections.OrderedDict()
    for r in rows:
        if not r.get("close_utc") or r.get("status", "filled") != "filled":
            continue
        d = trading_day(r["open_utc"])
        day = days.setdefault(d, {"d": d, "pct": 0.0, "n": 0, "cost_pct": None, "stopped": False, "skipped": 0, "_b0": _f(r.get("balance"))})
        b0 = day["_b0"]
        if b0 > 0:
            day["pct"] += (_f(r.get("profit")) + _f(r.get("commission")) + _f(r.get("swap"))) / b0
        day["n"] += 1
        if day["pct"] <= DAILY_STOP:
            day["stopped"] = True
    out = []
    for day in days.values():
        day.pop("_b0")
        out.append(day)
    return out


def day_stats(days):
    """日ごとの損益率の平均と95%の幅（日のまとまり）・回数／日・止めた日・勝った日・最大の落ち込み・費用"""
    p = [d["pct"] for d in days]
    n = len(p)
    out = {"days": n, "trades": sum(d["n"] for d in days), "mean": None, "se": None, "lo": None, "hi": None,
           "win_days": None, "stop_days": sum(1 for d in days if d["stopped"]), "max_dd": None, "cost_per_day": None,
           "trades_per_day": None}
    if n == 0:
        return out
    mean = sum(p) / n
    sd = math.sqrt(sum((x - mean) ** 2 for x in p) / (n - 1)) if n > 1 else math.inf
    se = sd / math.sqrt(n)
    cum = peak = dd = 0.0
    for x in p:
        cum += x
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    costs = [d["cost_pct"] for d in days if d.get("cost_pct") is not None]
    out.update(mean=mean, se=se, lo=mean - Z95 * se, hi=mean + Z95 * se, win_days=sum(1 for x in p if x > 0) / n,
               max_dd=dd, cost_per_day=(sum(costs) / n if costs else None), trades_per_day=out["trades"] / n)
    return out


# ───────── 段階と関門 ─────────
def stage_from_forward(st):
    """デモの日次平均の幅の下限で、段1〜4のどこまで届いたか（0＝届いていない）"""
    lo = st.get("lo")
    if lo is None or lo == -math.inf:
        return 0
    reached = 0
    for i, (_, _, target) in enumerate(STAGES):
        if target is not None and lo > target:
            reached = i
    return reached


def gate_a(confirm_st, placebo_p, confirm_count):
    """関門A（段0）：確かめ期間の日次平均の幅の下限 > 0 かつ 偽薬 p < 0.05 ÷ 確かめた回数の累計"""
    lo = confirm_st.get("lo")
    if lo is None or not lo > 0:
        return False, "confirm"
    if placebo_p is None or not placebo_p < ALPHA / confirm_count:
        return False, "placebo"
    return True, None


def fwd_status(st):
    """デモの窓：100回以上かつ10営業日以上で判定。5営業日かつ30回以上で幅の上限 < 0 なら途中で消える"""
    if st["days"] >= EARLY_DAYS and st["trades"] >= EARLY_TRADES and st["hi"] is not None and st["hi"] < 0:
        return "faded"
    if st["days"] >= FWD_MIN_DAYS and st["trades"] >= FWD_MIN_TRADES:
        return "window_done"
    return "continue"


# ───────── 台帳 ─────────
def _brief(st):
    keys = ("days", "trades", "mean", "lo", "hi", "win_days", "stop_days", "max_dd", "cost_per_day", "trades_per_day")
    return {k: (st[k] if k in ("days", "trades", "stop_days") else J._f(st.get(k), 5)) for k in keys}


def new_ledger():
    return {"kind": "loop", "id": "LP", "prereg_sha256": J.section_sha256(head=SECTION), "status": "open", "closed_reason": None,
            "confirm_tests": CONFIRM_BASE, "fwd_fails": 0, "rounds": []}


def load(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def save(led, path):
    txt = json.dumps(led, ensure_ascii=False, indent=1)
    for bad in ("balance", "profit"):
        if f'"{bad}"' in txt:
            raise ValueError(f"台帳に金額の項目（{bad}）が入っている")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(txt + "\n")


def _round(led, rid):
    for r in led["rounds"]:
        if r["round"] == rid:
            return r
    raise KeyError(f"ラウンド {rid} が台帳に無い")


def register_round(led, rid, mechanism, change, reason, parent=None, variants=1, on=None):
    """①登録：直す中身・なぜ効くはずか・親。同じ仕組みの値違いは3つまで（確かめの回数に足す）"""
    if led["status"] != "open":
        raise ValueError(f"このループは止まっている（{led['closed_reason']}）。続けるなら新しい節を登録してから")
    if any(r["round"] == rid for r in led["rounds"]):
        raise ValueError(f"ラウンド {rid} は登録済み")
    if not (1 <= int(variants) <= MAX_VARIANTS):
        raise ValueError(f"値違いは1ラウンドに{MAX_VARIANTS}つまで")
    if not (mechanism and reason):
        raise ValueError("仕組みと、なぜ効くはずかを書く")
    led["confirm_tests"] += int(variants)
    led["rounds"].append({"round": rid, "parent": parent, "mechanism": mechanism, "change": change, "reason": reason,
                          "variants": int(variants), "registered_on": on or dt.date.today().isoformat(),
                          "confirm_count_at_gate": led["confirm_tests"], "status": "registered", "out_reason": None,
                          "backtest": None, "forward": None, "stage": 0})
    return led


def record_backtest(led, rid, select_days, confirm_days, placebo_p):
    """②③ 過去で数えた結果（日ごとの損益率）→ 関門A。越えればデモへ、越えなければ検証済みへ"""
    r = _round(led, rid)
    if r["status"] != "registered":
        raise ValueError(f"ラウンド {rid} は過去の計算を記録済み（1回だけ）")
    sel, con = day_stats(select_days), day_stats(confirm_days)
    ok, why = gate_a(con, placebo_p, r["confirm_count_at_gate"])
    r["backtest"] = {"select": _brief(sel), "confirm": _brief(con), "placebo_p": J._f(placebo_p, 6),
                     "p_needed": J._f(ALPHA / r["confirm_count_at_gate"], 6), "gate_a": ok}
    if ok:
        r["status"], r["stage"] = "s0", 0
    else:
        r["status"], r["out_reason"] = "out", OUT_REASONS[why]
    _close_check(led)
    return led


def record_forward(led, rid, days, today=None):
    """④⑤ デモの前向き（同じ決まりの累計）→ 窓の判定と段。段は窓を満たしたときだけ上がり、下がらない"""
    r = _round(led, rid)
    if r["status"] not in ("s0", "forward", "judged"):          # judged＝窓は満たした。同じ決まりで数え続けて段を上げてよい
        raise ValueError(f"ラウンド {rid} はデモに進めない（{r['status']}）")
    st = day_stats(days)
    status = fwd_status(st)
    # 段は窓（100回以上かつ10営業日以上）を満たしてから上げる。途中の少ない日数の幅で上げない。上がった段は下がらない
    stage = max(r["stage"], stage_from_forward(st)) if status == "window_done" else r["stage"]
    r["forward"] = dict(_brief(st), updated=today or dt.date.today().isoformat(), window=status)
    if status == "faded" or (status == "window_done" and stage < 1):
        r["status"], r["out_reason"] = "out", OUT_REASONS["faded" if status == "faded" else "stage1"]
        led["fwd_fails"] += 1
    else:
        r["status"], r["stage"] = ("judged" if status == "window_done" else "forward"), stage
        if stage >= 1:
            led["fwd_fails"] = 0
    _close_check(led)
    return led


def _close_check(led):
    if led["status"] != "open":
        return
    done = [r for r in led["rounds"] if r["status"] in ("out", "judged")]
    best = max((r["stage"] for r in led["rounds"]), default=0)
    if led["fwd_fails"] >= MAX_FWD_FAILS:
        led["status"], led["closed_reason"] = "closed", f"段0の決まりが{MAX_FWD_FAILS}回続けてデモで消えた（当てはめすぎの印）"
    elif len(done) >= MAX_ROUNDS and best < 1:
        led["status"], led["closed_reason"] = "closed", f"{MAX_ROUNDS}ラウンドで段1に届かなかった（ドル円の5分足・この業者の費用では、前向きで残る決まりは見つからなかった）"


# ───────── 振り返り（読むための表・判定しない） ─────────
def review_tables(trades):
    """取引（{"t": UTC秒, "r": R, "cost_r": 費用のR}）→ 時間帯・曜日・費用の大きさ・連敗のあと の平均R（判定しない）"""
    by_hour, by_wd, by_cost, after = (collections.defaultdict(list) for _ in range(4))
    streak = 0
    for x in trades:
        t = dt.datetime.fromtimestamp(int(float(x["t"])), JST)
        r, c = float(x["r"]), _f(x.get("cost_r"))
        by_hour[t.hour].append(r)
        by_wd[t.weekday()].append(r)
        by_cost["費用 <0.10R" if c < 0.10 else "0.10〜0.20R" if c < 0.20 else "≥0.20R"].append(r)
        after["2連敗のあと" if streak >= 2 else "それ以外"].append(r)
        streak = streak + 1 if r < 0 else 0

    def tab(d):
        return {str(k): {"n": len(v), "mean_r": J._f(sum(v) / len(v))} for k, v in sorted(d.items())}
    return {"by_hour_jst": tab(by_hour), "by_weekday": tab(by_wd), "by_cost": tab(by_cost), "after_losses": tab(after)}


def render_md(led):
    def pct(x):
        return "—" if x is None else f"{x * 100:+.2f}%"

    def rng(st):
        return "—" if not st or st.get("lo") is None else f"{pct(st['lo'])}〜{pct(st['hi'])}"
    L = ["# LP ドル円5分足の「取引→検証→改善」の台帳（手元専用・送らない）", "",
         f"状態：{'回している' if led['status'] == 'open' else '止めた＝' + str(led['closed_reason'])}・ラウンド {len(led['rounds'])}／{MAX_ROUNDS}・"
         f"確かめた回数の累計 {led['confirm_tests']}（関門A の p＜{ALPHA / max(led['confirm_tests'], 1):.4f}）・デモで続けて消えた数 {led['fwd_fails']}／{MAX_FWD_FAILS}", "",
         "目標の段階（デモの日次平均の幅の下限で上がる）：" + "／".join(f"{s[0]} {s[1]}" for s in STAGES), "",
         "| ラウンド | 親 | 仕組み | 直した中身 | 状態 | 段 | 過去：確かめ期間の日次平均（幅） | 偽薬 p（要る p） | デモ：日次平均（幅）・日数・回数 | 理由 |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for r in led["rounds"]:
        bt, fw = r.get("backtest") or {}, r.get("forward") or {}
        con = bt.get("confirm") or {}
        L.append(f"| {r['round']} | {r['parent'] or '—'} | {r['mechanism']} | {r['change']} | {r['status']} | {STAGES[r['stage']][0]} | "
                 f"{pct(con.get('mean'))}（{rng(con)}） | {bt.get('placebo_p', '—')}（{bt.get('p_needed', '—')}） | "
                 f"{pct(fw.get('mean'))}（{rng(fw)}）・{fw.get('days', 0)}日・{fw.get('trades', 0)}回 | {r.get('out_reason') or ''} |")
    L += ["", "決まりは `PILLAR_PREREG.md`「LP」。段は前向き（デモ）の数字だけで上がる。直す候補は仕組みの理由が言えるものだけ登録する。", "",
          "※ 個人の取引の記録です。投資助言ではありません。"]
    return "\n".join(L) + "\n"


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="LP の台帳を読む版にする（手元）")
    ap.add_argument("--ledger", default="research/loop/loop-ledger.json")
    ap.add_argument("--md", default="research/loop/LOOP_LEDGER.md")
    a = ap.parse_args(argv)
    led = load(a.ledger) or new_ledger()
    with open(a.md, "w", encoding="utf-8") as fh:
        fh.write(render_md(led))
    print(f"{a.md}：ラウンド {len(led['rounds'])}・状態 {led['status']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
