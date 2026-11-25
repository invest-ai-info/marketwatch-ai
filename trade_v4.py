# -*- coding: utf-8 -*-
"""取引の記録（trade_journal.py）の、決まりの紙 v4 の項目を5分足から計算する（PILLAR_PREREG.md「OJ」追記⑨⑩・「OJ3」）。
2026-11-25 オーナー「主役はあくまでユーロとポンド。で、ドル円は上か下かの判断でしかありません。ユーロポンドでどっちに動くかが一番重要です。」→ 記録に v4 の項目を「足す」

計算するもの（ドル円・ユーロ円・ポンド円。ユーロドル・ポンドドルは向きだけ）:
  ドル円とユーロポンドの向き（15分足 EMA10 の1時間の動き）／ユーロポンドで強いほう／見るペア（入らなかったほう）の割った線・直近の端／入口の項目7つ／型の見当（①押し目か④ドル円レンジか＝入ったペアが抜けている＋ドル円の向き）
  入ったあと＝v4 の出口（見るペアが直近の端＝利確／割った線の 4pips 外＝損切り）が先に来ていたか・そのときの pips・そこから伸ばした分・持っている間のいちばんの伸び
しないもの: 入る所を知らせる・売買する。**入ったあとの数字は書くだけ**（足すときに見せない・平均は判定の日に読む表だけ）

決まり＝「OJ3」の入口と同じ（research/oikawa/oj3_lab.py と別に書き、過去の足で突き合わせた）。変えた所は1つだけ：
- 50% の押し・当たりは、機械の「次の足の始値」ではなく、**入った分までの値動き**で見る（いちばん遠くより後に、どこまで戻ったか）
境目（None）＝次のどれかで答えが変わるとき：線が ±1pip ずれる・当たりの 3pips が ±0.5pips ずれる（Yahoo と業者の足のずれ）／ドル円 2pips の ±0.2・ユーロポンド 0.5pips の ±0.1
  （2026-11-25 に測った・10/2〜11/24 の月〜木 15:00〜終わりの 1,293本：業者〔BigBoss の MT4〕の足と違う答えは、境目の外では 0本・上と下が逆になったのは境目の中でも 0本）
線を作る足が10本より多く欠ける日（月曜の冬の8時台）は、線の項目を決めない（向きは決める）。オーナーが言った値がいつも優先
"""
import datetime as dt
import math

import trade_fill as F

CROSS, DOLLAR = ("EURJPY", "GBPJPY"), ("EURUSD", "GBPUSD")
OTHER = {"EURJPY": "GBPJPY", "GBPJPY": "EURJPY"}
PAIR_JP = dict(F.PAIR_JP, EURUSD="ユーロドル", GBPUSD="ポンドドル")
LINE_FROM, LINE_TO, S1_FROM, S2_FROM, OLD = 480, 900, 720, 905, 6      # 線＝8:00〜15:00 に始まる足。S1＝12:00 から・30分以上前まで／S2＝15:05 から
USD_MIN, USD_TOL, EG_MIN, EG_TOL = 2.0, 0.2, 0.5, 0.1
SLOPE_BARS = 12
FAR, MOM, AGE, AGO, DEP, TOUCH_N, NEAR = 20.0, 6, 24, 6, 50.0, 3, 3.0
NEAR_TOL, SHIFT, OUT = 0.5, 1.0, 4.0
PIP = F.PIP
KATA = ("push", "fade", "range", "other")
KATA_JP = {"push": "①押し目", "fade": "②抜けの失敗の逆張り", "range": "④ドル円レンジの押し目", "other": "ほか"}
FLAGS = ("both_broken", "usd_dir", "pick_eg", "far20", "fresh", "pull50", "touch1")
LINE_FLAGS = ("both_broken", "far20", "fresh", "pull50", "touch1")
FLAG_JP = {"both_broken": "両方の抜け", "usd_dir": "ドル円の向き", "pick_eg": "強いほう", "far20": "30分で20pips", "fresh": "新しさ", "pull50": "50%の押し", "touch1": "線か MA に当たり"}


# ── 向き ──────────────────────────────────────

def slope(bars, pip):
    """15分足 EMA10（確定した15分足だけ）の、最後の足と12本前の差（pips）。まだ無ければ None"""
    e = F.ema15(bars)
    if len(e) <= SLOPE_BARS or e[-1] is None or e[-1 - SLOPE_BARS] is None:
        return None
    return round((e[-1] - e[-1 - SLOPE_BARS]) / pip, 2)


def state_of(x, lo, tol):
    """動き x → 1（上）・−1（下）・0（その間）・None（境目か、まだ無い）"""
    if x is None:
        return None
    a = round(abs(x), 6)
    if a >= round(lo + tol, 6):
        return 1 if x > 0 else -1
    return 0 if a <= round(lo - tol, 6) else None


def strong_of(s, g):
    """買い（1）か売り（−1）か・ユーロポンドの向き → (強いほうの通貨 か None, 確かか)"""
    if g is None:
        return None, False
    return ("EUR" if g == s else "GBP" if g == -s else None), True


# ── 線と抜け（上向きの形にそろえて数える） ────────────────────

def up(bars, s):
    """足 → 上向きの形 [(時刻, 高, 安, 終)]（売りは符号を逆に）"""
    return [(b[0], b[2], b[3], b[4]) if s > 0 else (b[0], -b[3], -b[2], -b[4]) for b in bars]


def walk(U, shift=0.0):
    """その日の確定した足（上向きの形）→ 足ごとの {S2・S1 の (線, 抜けた足) か None} と、線を作る足の反対側の端。shift＝線を外へずらす pips"""
    top, bot, a, b = [], [], None, None
    for t, h, l, _c in U:
        if LINE_FROM <= F.jmin(t) <= LINE_TO:
            a, b = h if a is None else max(a, h), l if b is None else min(b, l)
        top.append(a)
        bot.append(b)
    logs = []
    for first, lag in ((S2_FROM, 0), (S1_FROM, OLD)):
        cur, log = None, []
        for i, (t, _h, _l, c) in enumerate(U):
            if F.jmin(t) >= first:
                if cur and c <= cur[0]:
                    cur = None
                if cur is None and i >= max(1, lag) and top[i - lag] is not None:
                    ln = top[i - lag] + shift * PIP
                    if c > ln >= U[i - 1][3]:
                        cur = (ln, i)
            log.append(cur)
        logs.append(log)
    return logs, bot


def leg_of(U, logs, ones=(), m0=None):
    """最後の足で続いている抜け（S2 を先に）。ones＝入った足の中の1分足（m0 より前の分で、いちばん遠くを伸ばす）。値は上向きの形"""
    if not U:
        return None
    n = len(U) - 1
    for log in logs:
        if not log[n]:
            continue
        L, b = log[n]
        k = max(range(b, n + 1), key=lambda z: (U[z][1], -z))
        ext, at, age, ago = U[k][1], U[k][0], n - b, n - k
        t20 = next((z - b for z in range(b, n + 1) if (U[z][1] - L) / PIP >= FAR - 1e-6), None)
        for t, h, _l, _c in ones:
            if m0 is not None and t >= m0:
                break
            if h > ext:
                ext, at, ago = h, t, 0
            if t20 is None and (h - L) / PIP >= FAR - 1e-6:
                t20 = n + 1 - b
        return {"L": L, "ext": ext, "ex": (ext - L) / PIP, "at": at, "age": age, "t20": t20, "ago": ago}
    return None


def leg_now(day, s, shift=0.0):
    """その日の確定した足 → 最後の足で続いている抜け（値段は元の符号）"""
    U = up(day, s)
    x = leg_of(U, walk(U, shift)[0])
    return None if x is None else dict(x, L=x["L"] * s, ext=x["ext"] * s)


def pull_of(U, ones, leg):
    """いちばん遠くより後に戻った深さ（%・線まで戻ると100）。1分足は入った分まで"""
    lows = [c for t, _h, _l, c in U if t == leg["at"]] + [l for t, _h, l, _c in U if t > leg["at"]]
    one = [(t, l, c) for t, _h, l, c in ones]
    lows += [c for t, _l, c in one if t == leg["at"]] + [l for t, l, _c in one if t > leg["at"]]
    return (leg["ext"] - min(lows)) / (leg["ext"] - leg["L"]) * 100 if lows else 0.0


def touches(U, logs, bot, E, ones, j0, near):
    """直近3本か、入った足の中（入った分まで）で、線・MA・反対側の東京の線・きりのよい値の near pips 以内に来たか"""
    n = len(U)

    def hit(i, low, e):
        m = F.jmin(U[i][0]) if i < n else F.jmin(j0)
        if i < 1 or m < S1_FROM:
            return False
        prev = U[i - 1][3]
        lv = [e] + [log[i - 1][0] for log in logs if log[i - 1]] + [math.floor(prev)]
        if m >= F.LINE_TO + 5 and i >= OLD:
            lv.append(bot[i - OLD])
        return any(v is not None and prev > v and (low - v) / PIP <= near + 1e-7 for v in lv)

    if any(hit(i, U[i][2], E[i]) for i in range(max(0, n - TOUCH_N), n)):
        return True
    return bool(ones) and hit(n, min(o[2] for o in ones), E[n])


# ── 1件の計算 ───────────────────────────────────

def one_set(D, pair, shift, near):
    """線を shift pips ずらし、当たりを near pips としたときの、線の項目の○×"""
    logs = {p: walk(x["U"], shift) for p, x in D.items()}
    legs = {p: leg_of(x["U"], logs[p][0], x["ones"], x["m0"]) for p, x in D.items()}
    mine = [legs[p] for p in CROSS if legs[p]]
    pulls = {p: pull_of(D[p]["U"], D[p]["ones"], legs[p]) for p in CROSS if legs[p]}
    own = legs.get(pair)
    f = {"both_broken": len(mine) == 2, "far20": any(x["t20"] is not None and x["t20"] <= MOM for x in mine),
         "fresh": None if pair not in CROSS else bool(own and own["age"] <= AGE and own["ago"] <= AGO),
         "pull50": any(legs[p]["ex"] >= FAR - 1e-6 and pulls[p] >= DEP - 1e-9 for p in pulls),
         "touch1": any(touches(x["U"], logs[p][0], logs[p][1], x["E"], x["ones"], x["j0"], near) for p, x in D.items())}
    return f, legs, pulls


def analyze(b5, b1, pair, side, t_open):
    """5分足・1分足と注文の行 → v4 の項目。入ったあとの値動きは使わない（当たりと押しだけは入った分まで）。純関数"""
    pair = pair.upper()
    if pair not in F.PAIRS + DOLLAR:
        raise F.FillError("v4 の項目を計算できるのは、ドル円・ユーロ円・ポンド円・ユーロドル・ポンドドルの取引だけ")
    s = 1 if side.lower() == "buy" else -1
    t0 = F.to_ts(t_open)
    j0, m0 = t0 - t0 % F.BAR, t0 - t0 % 60
    d0 = F.to_ts(dt.datetime(t_open.year, t_open.month, t_open.day))
    g = {b[0]: b[4] for b in b5["GBPJPY"]}
    eg = [(b[0], 0.0, 0.0, 0.0, b[4] / g[b[0]]) for b in b5["EURJPY"] if b[0] < j0 and b[0] in g]
    usd, eur = slope([b for b in b5["USDJPY"] if b[0] < j0], PIP), slope(eg, 0.0001)
    us, gs = state_of(usd, USD_MIN, USD_TOL), state_of(eur, EG_MIN, EG_TOL)
    cur, sure = strong_of(s, gs)
    pick = cur == pair[:3] if sure else None                            # ドル円は選ばない（いつも ×）
    need = len(range(LINE_FROM, min(F.LINE_TO, F.jmin(j0) - 5) + 1, 5))
    D, missing, coarse = {}, {}, False
    for p in F.PAIRS:
        past = [b for b in b5[p] if b[0] < j0]
        day = [b for b in past if b[0] >= d0]
        ones = up([b for b in b1.get(p, ()) if j0 <= b[0] <= m0], s)
        missing[p] = max(0, need - sum(1 for b in day if LINE_FROM <= F.jmin(b[0]) <= F.LINE_TO))
        E = F.ema15(past + [(j0, 0.0, 0.0, 0.0, 0.0)])[len(past) - len(day):]
        D[p] = {"U": up(day, s), "ones": ones, "E": [None if e is None else e * s for e in E], "j0": j0, "m0": m0}
        coarse = coarse or not ones
    flags = {k: None for k in FLAGS}
    flags["usd_dir"], flags["pick_eg"] = None if us is None else us == s, pick
    legs, pulls = {}, {}
    if pair not in DOLLAR:
        sets = [one_set(D, pair, k * SHIFT, NEAR + j * NEAR_TOL) for k in (0, -1, 1) for j in (0, -1, 1)]
        _f, legs, pulls = sets[0]
        short = any(v > F.MAX_MISSING for v in missing.values())
        for k in LINE_FLAGS:
            vals = {x[0][k] for x in sets}
            v = vals.pop() if len(vals) == 1 and not short else None
            flags[k] = None if v is False and coarse and k in ("pull50", "touch1") else v      # 1分足が無い＝入った足の中が見えない
    kata = None                                                        # 型＝名前だけ（入ったペアが抜けている＋ドル円の向き）。②と境目は人に聞く
    if pair in CROSS and legs[pair]:
        kata = {s: "push", 0: "range"}.get(us)
    elif pair in DOLLAR and us == 0:
        kata = "range"
    watch = OTHER.get(pair)
    w = legs.get(watch) if flags["both_broken"] else None
    price = {p: None if x is None else dict(x, L=x["L"] * s, ext=x["ext"] * s) for p, x in legs.items()}
    return {"pair": pair, "side": side.lower(), "time": F.hhmm(t0), "missing": missing, "coarse": coarse, "usd": (usd, us), "eg": (eur, gs),
            "strong": None if cur is None else cur + "JPY", "pick": pick, "kata": kata, "watch": watch, "watch_line": None if w is None else round(w["L"] * s, 5),
            "watch_ext": None if w is None else round(w["ext"] * s, 5), "legs": price, "pulls": pulls, "flags": flags, "named": pair in DOLLAR or legs.get(pair) is not None}


def record(r):
    """analyze の答え → 記録（trade_journal.make_trade の v4）"""
    rd = lambda x: None if x is None else round(x, 3)
    return {"usd_1h": r["usd"][0], "eg_1h": r["eg"][0], "strong_eg": r["strong"], "watch": r["watch"], "watch_line": rd(r["watch_line"]), "watch_extreme": rd(r["watch_ext"]),
            "flags": dict(r["flags"])}


# ── 読む文と、人に聞くこと ────────────────────────────

def way(x):
    d, v = x
    return "足が無い" if d is None else f"{ {1: '上', -1: '下', 0: 'レンジ', None: '境目'}[v] }（1時間に {d:+.1f}pips）"


def strong_text(r):
    who = PAIR_JP[r["strong"]] if r["strong"] else ("決まらない（ユーロポンドがレンジ）" if r["eg"][1] == 0 else "境目")
    return f"{who}＝ユーロポンド {way(r['eg'])}"


def report(r):
    L = [f"  v4：ドル円 {way(r['usd'])}・ユーロポンド {way(r['eg'])} → 強いほう {PAIR_JP[r['strong']] if r['strong'] else '決まらない'}（入ったペアと同じ {F.mark(r['pick'])}）",
         f"  v4 の型：{KATA_JP[r['kata']] if r['kata'] else '決まらない'}" if r["kata"] else "  v4 の型：決まらない"]
    if r["watch"]:
        L.append(f"  v4 の見るペア {PAIR_JP[r['watch']]}（" + (f"割った線 {r['watch_line']:.3f}・直近の端 {r['watch_ext']:.3f}" if r["watch_line"] is not None else "まだ抜けていない・境目・足が足りないのどれか") + "）")
    if r["pair"] not in DOLLAR:
        L.append("  v4 の項目：" + "・".join(f"{FLAG_JP[k]} {F.mark(r['flags'][k])}" for k in FLAGS))
    return "\n".join(L)


def questions(r, given, unknown):
    """決められないもの → 人に聞く文"""
    q = []
    if r["kata"] is None and "kata" not in given and "kata" not in unknown:
        q.append("どの型で入ったか → --kata push（①押し目）／fade（②抜けの失敗の逆張り）／range（④ドル円レンジの押し目・クロス円とドルストを1つずつ）／other・分からない＝--unknown kata")
    if r["named"] and r["pick"] is not True and "strongest" not in given and "strong" not in unknown:
        q.append(f"入った{PAIR_JP[r['pair']]}は、ユーロポンドで強いほうでしたか（道具の答え：{strong_text(r)}）→ --flags strongest=1 か 0・分からない＝--unknown strong")
    return q


# ── 入ったあと（書くだけ） ──────────────────────────

def load_after(pair, watch, t_open, t_close):
    """入ってから出るまでの足 → (入ったペア, 見るペア, 足の秒数)。1分足が取れなければ2つとも5分足。取れなければ空"""
    a, b = F.to_ts(t_open), F.to_ts(t_close) + 60
    for step, name in ((60, "1m"), (300, "5m")):
        try:
            p = F.fetch(pair, name, a - a % step, b, tries=2)
            return p, (F.fetch(watch, name, a - a % step, b, tries=2) if watch else []), step
        except F.FillError:
            pass
    return [], [], 60


def after(p, q, side, entry, spread, line, ext, t_open, t_close, pip, pnl, step=60):
    """入ってから出るまでの、まるごと入っている足だけを見る → v4 の出口・伸ばした分。純関数
    v4 の出口＝見るペア（q）が直近の端 ext に着いた（tp）／割った線 line の 4pips 外（sl）。同じ足に両方なら sl。pips はその足の、入ったペア（p）の終値で数える（売りは＋スプレッド）"""
    s = 1 if side.lower() == "buy" else -1
    t0, t1 = F.to_ts(t_open), F.to_ts(t_close)
    first, m0 = t0 - t0 % step + step, t0 - t0 % 60
    P, Q = ([b for b in x if b[0] >= first and b[0] + step <= t1] for x in (p, q))
    pay = 0.0 if s > 0 else spread
    out = {"v4_exit": None, "v4_exit_min": None, "v4_exit_pips": None, "run_pips": None, "mfe_pips": None}

    def gain(v):
        return None if pay is None else round((v - entry) * s / pip - pay, 1)

    if P:
        out["mfe_pips"] = gain(max(b[2] for b in P) if s > 0 else min(b[3] for b in P))
    if line is None or ext is None or not Q:
        return out
    out["v4_exit"] = "none"
    for (t, h, l, _c), b in zip(up(Q, s), Q):
        kind = "sl" if l <= line * s - OUT * PIP + 1e-7 else "tp" if h >= ext * s - 1e-7 else None
        if kind:
            px = [x[4] for x in P if x[0] <= t]
            out.update(v4_exit=kind, v4_exit_min=(t - m0) // 60, v4_exit_pips=gain(px[-1]) if px else None)
            if kind == "tp" and out["v4_exit_pips"] is not None:
                out["run_pips"] = round(pnl - out["v4_exit_pips"], 1)
            break
    return out
