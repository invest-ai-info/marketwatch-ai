# -*- coding: utf-8 -*-
"""取引の記録（trade_journal.py）の、チャートを見ないと分からない数字を5分足から計算する（決まりの紙 v2・v3＝PILLAR_PREREG.md「OJ」追記⑥⑧）。
2026-11-24 夜 オーナー「作る」（注文の行を送るだけで記録を埋める）。11/25 v3＝「2つ以上が水平線かMAに当たったときに、そのときに一番強い通貨にエントリー」

計算するもの（ドル円・ユーロ円・ポンド円の取引だけ・入る前に見えていた足だけ）:
  割った東京の線・抜けた足／線から30pips 離れるまでの分／いちばん遠い値／50%・割った線・MA のどれに当たっていたか／当たっていたペアの数（v3＝線か MA だけ）／一番強い通貨／3ペアそろいの合図
しないもの: 入る所を知らせる・売買する・勝ち負けを見る（決済の値は使わない）

決まりの読み方（段2 の oj_lab.py と同じ）:
- 線＝8:00 から、そのペアが初めて抜けた足の1本前までの高値の最大（売りは安値の最小）。14:55 に始まる足まで。抜け＝14:00 からの足の終値が線の外
- 30pips＝抜けた足が確定してから、ヒゲが線から30pips に届いた足が確定するまでの分（抜けた足そのものなら 0）
- 50%＝線と、入る前までにいちばん遠くまで行った値の真ん中／MA＝15分足 EMA10（いま動いている15分足の1本前まで）
- 当たり＝入った分までの値動き（1つ前の5分足から）が、線の 3pips 以内に来た。v3 のペアの数は、割った線と MA だけ（50% は入れない）。計算した線は業者のチャートの線と数 pips ずれる（11/24 は 1.3〜3.7pips）ので、線が ±4pips ずれても同じ答えのときだけ ○× を決める
- 一番強い通貨＝ドル円とユーロポンド（ユーロ円÷ポンド円）の、入る前に確定した最後の5分足の終値が 15分足 EMA10 の上か下か（段2 の oj_lab.pick_pair と同じ）。買い＝ドル円が上のときだけ・ユーロポンドが下→ポンド円／上→ユーロ円（売りは逆）。ドル円は選ばない
  業者（MT4）の足と比べて、向きが逆になったのは 1,869本のうち ドル円は ±0.7pips・ユーロポンドは ±0.5pips を「境目」にすると 0本と1本（2026-11-25 に測った・9/30〜11/23 の 15:00〜18:55）。比べるための別の答え＝線からいちばん遠くまで行った割合が大きいペア
- 値は Yahoo の1分足（30日以内）と5分足（60日以内）。業者（BigBoss の MT4・5分足）と比べると、9/30〜11/23 の3,151通りで、線のずれは9割が 1.0pips 以内・いちばん遠い値は 0.7pips 以内、
  「30分以内に30pips」の○×が逆になったのは 0・当たりの○×が逆になったのは 9,447 のうち 44（0.5%）（2026-11-24 に測った）
  → 30pips と 3pips の境目の ±0.5pips は「境目」＝決めずに人に聞く。月曜の8時台は Yahoo に足が無い（冬時間）・線が 4pips ずれると30pips の○×が変わる（104通りのうち25）＝線を人に確かめる。オーナーが言った値（線・いちばん遠い値・分・数・種類）がいつも優先
"""
import datetime as dt
import json
import time
import urllib.request

PAIRS = ("USDJPY", "EURJPY", "GBPJPY")
PAIR_JP = {"USDJPY": "ドル円", "EURJPY": "ユーロ円", "GBPJPY": "ポンド円"}
TYPE_JP = {"half50": "50%", "line": "割った線", "ema15": "15分足MA"}
PIP = 0.01
BAR = 300
LINE_FROM, LINE_TO, BREAK_FROM = 8 * 60, 14 * 60 + 55, 14 * 60     # 日本時間の分
MAX_MISSING, HARD_MISSING = 10, 24                                 # 線を作る足（84本）の欠け：10本まで＝そのまま（oj_lab と同じ）・24本まで＝線を人に確かめる・それより多い＝計算しない
EMA_N = 10
FAR_PIPS, FAR_MIN, NEAR_PIPS, TOL = 30.0, 30, 3.0, 0.5
LINE_SENSE = 4.0                                                   # 線がこれだけ内・外にずれたら30pips の○×が変わるなら、線を人に確かめる（11/24 の赤い線との差 3.7pips から）
LINE_WARN_PIPS = 5.0                                               # オーナーの線と計算した線がこれ以上離れたら知らせる
LM = ("line", "ema15")                                             # v3 で当たりに数える線（割った線・MA）
FLOW_TOL = {"USDJPY": 0.7, "EURGBP": 0.5}                          # 向きの境目（pips・ユーロポンドは 0.0001 が 1pip）
JST = dt.timezone(dt.timedelta(hours=9))
UA = {"User-Agent": "Mozilla/5.0"}


class FillError(Exception):
    """計算できない（足が足りない・対象でないペア・取れない）"""


# ── 値を取る ─────────────────────────────────────

def parse(j):
    """Yahoo の chart の返事 → [(UTC 秒, 始, 高, 安, 終)]。値の無い足は外す。純関数"""
    r = j["chart"]["result"][0]
    q = r["indicators"]["quote"][0]
    out = []
    for i, t in enumerate(r.get("timestamp") or []):
        v = [q[k][i] for k in ("open", "high", "low", "close")]
        if None not in v:
            out.append((int(t), *map(float, v)))
    return out


def fetch(pair, interval, a, b, tries=3):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{pair}=X?interval={interval}&period1={a}&period2={b}"
    err = None
    for k in range(tries):
        try:
            return parse(json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30)))
        except Exception as e:  # noqa: BLE001
            err = e
            time.sleep(1 + k)
    raise FillError(f"Yahoo から {pair} の {interval} 足が取れない（{type(err).__name__}）。5分足は60日・1分足は30日より前は取れない")


def load(t_open):
    """t_open＝日本時間（tz なし）→ ({ペア: 5分足}, {ペア: 1分足})。1分足は取れなければ無しで続ける"""
    t0 = to_ts(t_open)
    b5 = {p: fetch(p, "5m", t0 - 6 * 86400, t0 + BAR) for p in PAIRS}
    b1 = {}
    for p in PAIRS:
        try:
            b1[p] = fetch(p, "1m", t0 - 3600, t0 + 60, tries=2)
        except FillError:
            pass
    return b5, b1


# ── 部品（純関数） ───────────────────────────────

def to_ts(t):
    return int(t.replace(tzinfo=JST).timestamp())


def hhmm(ts):
    return dt.datetime.fromtimestamp(ts, JST).strftime("%H:%M")


def jmin(ts):
    d = dt.datetime.fromtimestamp(ts, JST)
    return d.hour * 60 + d.minute


def ema15(bars):
    """5分足ごとの「いま動いている15分足の1本前までで確定した EMA10」（まだ無ければ None）。15分足の終値＝その中で最後にある5分足の終値"""
    out, ema, bucket, last = [], None, None, None
    a = 2.0 / (EMA_N + 1)
    for b in bars:
        k = b[0] // 900
        if bucket is not None and k != bucket:
            ema = last if ema is None else ema + a * (last - ema)
        bucket, last = k, b[4]
        out.append(ema)
    return out


def find_break(day, s, line=None):
    """その日の確定した足（時刻順）→ (線, 抜けた足の位置)。まだ抜けていなければ (それまでの線 か None, None)。line を渡せばその線で見る"""
    ref = None
    for i, (t, _o, h, l, c) in enumerate(day):
        m = jmin(t)
        if m < LINE_FROM:
            continue
        use = line if line is not None else ref
        if m >= BREAK_FROM and use is not None and s * (c - use) > 0:
            return use, i
        if m <= LINE_TO:
            x = h if s > 0 else l
            ref = x if ref is None else (max(ref, x) if s > 0 else min(ref, x))
    return (line if line is not None else ref), None


def far_of(path):
    """path＝[(抜けてからの分, 線からの pips)]（時刻順・小数1桁）→ (分, True/False/None＝境目)"""
    def first(th):
        return next((m for m, x in path if x >= th), None)

    def ok(m):
        return m is not None and m <= FAR_MIN

    sure, maybe = ok(first(FAR_PIPS + TOL)), ok(first(FAR_PIPS - TOL))
    if sure != maybe:
        return None, None
    return first(FAR_PIPS), sure


def gap(bars, lv):
    """足の値の範囲と線 lv の離れ（pips・またいでいれば 0・足が無ければ None）"""
    if not bars:
        return None
    lo, hi = min(b[3] for b in bars), max(b[2] for b in bars)
    return round(max(0.0, lo - lv, lv - hi) / PIP, 1)


def near_state(win, wide, lv):
    """線 lv の 3pips 以内に来たか → True／False／None＝境目"""
    d, dw = gap(win, lv), gap(wide, lv)
    if d is not None and d <= NEAR_PIPS - TOL:
        return True
    return False if dw is not None and dw > NEAR_PIPS + TOL else None   # 入る所の足が1本も無ければ「境目」＝×とは決めない


def type_of(state, lm_two):
    """入ったペアの当たり → 入口の種類（1つに決まらなければ None）。v3 では 50% は当たりに入れない＝線・MA を先に見る。どれにも当たっていなくて、2ペア以上が線か MA なら series"""
    hit = [k for k in LM if state.get(k) is True]
    if hit:
        return hit[0] if len(hit) == 1 else None
    if any(k in state and state[k] is None for k in LM):
        return None
    if "half50" in state and state["half50"] is not False:
        return "half50" if state["half50"] else None
    return "series" if lm_two else None


def flow_of(bars, pip, tol):
    """最後の5分足の終値 − いま動いている15分足の1本前までの EMA10 → (pips, 1／−1／None＝境目か、まだ無い)"""
    e = ema15(bars)
    if not e or e[-1] is None:
        return None, None
    d = round((bars[-1][4] - e[-1]) / pip, 2)
    return d, (None if abs(d) < tol else (1 if d > 0 else -1))


def pick_of(s, u, g):
    """合図の向き・ドル円の向き・ユーロポンドの向き → (入るペア か None＝決まらない, 確かか)。段2 の oj_lab.pick_pair と同じ"""
    if u is None:
        return None, False
    if u != s:
        return None, True
    if g is None:
        return None, False
    return ("GBPJPY" if g == -s else "EURJPY"), True


def pairs_of(state):
    """{ペア: True/False/None＝境目} → (数, 2ペア以上か)。境目のせいで「2以上か」が変わるときは (None, None)"""
    lo = sum(1 for v in state.values() if v is True)
    hi = lo + sum(1 for v in state.values() if v is None)
    return (lo, lo >= 2) if (lo >= 2) == (hi >= 2) else (None, None)


def any_of(vals):
    vals = list(vals)
    return True if True in vals else (None if None in vals else False)


# ── 1件の計算 ───────────────────────────────────

def pair_state(bars, ones, s, d0, j0, m0, line, extreme, name):
    """1ペアの線・抜け・離れ・当たり。入った足（j0）の中は、1分足で入る1分前まで（当たりだけは入った分まで）"""
    E = ema15(bars)
    day = [b for b in bars if d0 <= b[0] < j0]                          # 入る前に確定した足だけ
    need = len(range(LINE_FROM, min(LINE_TO, jmin(j0) - 5) + 1, 5))
    have = sum(1 for b in day if LINE_FROM <= jmin(b[0]) <= LINE_TO)
    if need - have > HARD_MISSING:
        raise FillError(f"{name}の5分足が足りない（8:00〜14:55 に {have}本）")
    x = {"missing": max(0, need - have), "line": None, "auto": find_break(day, s)[0], "b": None, "path": [], "ext": None}
    ln, i = find_break(day, s, line)
    if i is not None:
        tb = day[i][0]
        rows = [(b[0], b) for b in day[i:]] + [(j0, b) for b in ones if j0 <= b[0] < m0]
        top = [(t, b[2] if s > 0 else b[3]) for t, b in rows]
        x.update(line=ln, b=tb, ext=max(v * s for _, v in top) * s, path=[((t - tb) // 60, round((v - ln) * s / PIP, 1)) for t, v in top])
        if extreme is not None:
            x["ext"] = extreme
    one = [b for b in ones if j0 <= b[0] <= m0]
    win = [b for b in day if b[0] == j0 - BAR] + one
    wide = win + ([] if one else [b for b in bars if b[0] == j0])       # 1分足が無ければ、入った足は「境目」としてだけ使う
    lv = {} if x["b"] is None else {"half50": (x["line"] + x["ext"]) / 2.0, "line": x["line"]}
    e = [E[k] for k, b in enumerate(bars) if b[0] <= j0]
    if e and e[-1] is not None:
        lv["ema15"] = e[-1]
    x["hits"] = {k: gap(win or wide, v) for k, v in lv.items()}
    x["state"] = {k: near_state(win, wide, v) for k, v in lv.items()}
    x["hit"] = any_of(x["state"].values())
    lm = [x["state"][k] for k in LM if k in x["state"]]
    if line is None and x["line"] is not None:                          # 計算した線＝±4pips ずれても同じ答えのときだけ決める
        near = {near_state(win, wide, x["line"] + k * LINE_SENSE * PIP) for k in (-1, 0, 1)}
        lm[0] = near.pop() if len(near) == 1 else None
    x["lm"] = any_of(lm)
    x["coarse"] = not one
    return x


def analyze(b5, b1, pair, side, t_open, entry=None, line=None, extreme=None):
    """5分足・1分足と注文の行 → 記録に要る数字。入ったあとの値動きは使わない。純関数"""
    pair = pair.upper()
    if pair not in PAIRS:
        raise FillError("計算できるのはドル円・ユーロ円・ポンド円の取引だけ")
    s = 1 if side.lower() == "buy" else -1
    t0 = to_ts(t_open)
    j0, m0 = t0 - t0 % BAR, t0 - t0 % 60
    d0 = to_ts(dt.datetime(t_open.year, t_open.month, t_open.day))

    def state(p, ln):
        return pair_state(b5[p], b1.get(p, ()), s, d0, j0, m0, ln, extreme if p == pair else None, f"{PAIR_JP[p]}の {t_open:%Y-%m-%d} ")

    st = {p: state(p, line if p == pair else None) for p in PAIRS}
    me = st[pair]
    leg = depth = far_min = far_state = far_if = None
    if me["b"] is not None:
        leg = round((me["ext"] - me["line"]) * s / PIP, 1)
        if entry is not None and leg > 0:
            depth = round((me["ext"] - entry) * s / PIP / leg * 100, 1)
        far_min, far_state = far_by(me, s, extreme)
        if line is None:                                                 # 線が内・外に少しずれていたら
            far_if = tuple(far_by(state(pair, me["line"] + k * s * LINE_SENSE * PIP), s, extreme)[1] for k in (-1, 1))
    n, two = pairs_of({p: st[p]["hit"] for p in PAIRS})
    lm_state = {p: st[p]["lm"] for p in PAIRS}
    lm_n, lm_two = pairs_of(lm_state)
    flow = flow_pairs(b5, j0)
    pick, sure = pick_of(s, flow["USDJPY"][1], flow["EURGBP"][1])
    share = {p: (st[p]["ext"] - st[p]["line"]) * s / st[p]["line"] for p in PAIRS if st[p]["b"] is not None}
    return {"pair": pair, "side": side.lower(), "time": hhmm(t0), "missing": {p: st[p]["missing"] for p in PAIRS}, "line": me["line"], "line_auto": me["auto"],
            "break_bar": hhmm(me["b"]) if me["b"] is not None else None, "far_min": far_min, "far_state": far_state,
            "far_if": far_if, "far30_pips": max((x for m, x in me["path"] if m <= FAR_MIN), default=None),
            "extreme": me["ext"], "leg_pips": leg, "depth_pct": depth, "coarse": any(st[p]["coarse"] for p in PAIRS),
            "hits": {p: st[p]["hits"] for p in PAIRS}, "hit_state": {p: st[p]["hit"] for p in PAIRS},
            "entry_types": [k for k, v in me["state"].items() if v is True], "maybe_types": [k for k, v in me["state"].items() if v is None],
            "type": type_of(me["state"], lm_two), "pairs_hit": n, "pairs_state": two, "lm_state": lm_state, "pairs_lm": lm_n, "pairs_lm_state": lm_two,
            "flow": flow, "strong_flow": pick, "strong_sure": sure, "strong_state": (pick == pair) if sure else None,
            "strong_far": max(share, key=share.get) if share else None, "share": share, "signal": signal_of(st, b5, s, d0, j0)}


def flow_pairs(b5, j0):
    """ドル円とユーロポンド（ユーロ円÷ポンド円）の向き。入る前に確定した足だけ"""
    g = {b[0]: b[4] for b in b5["GBPJPY"]}
    eg = [(b[0], 0.0, 0.0, 0.0, b[4] / g[b[0]]) for b in b5["EURJPY"] if b[0] < j0 and b[0] in g]
    return {"USDJPY": flow_of([b for b in b5["USDJPY"] if b[0] < j0], PIP, FLOW_TOL["USDJPY"]), "EURGBP": flow_of(eg, 0.0001, FLOW_TOL["EURGBP"])}


def far_by(x, s, extreme):
    """1ペアの状態 → (30pips までの分, 30分以内か)。オーナーのいちばん遠い値で30pips に届いていなければ ×"""
    if x["b"] is None:
        return None, False
    if extreme is not None and round((x["ext"] - x["line"]) * s / PIP, 1) < FAR_PIPS:
        return None, False
    return far_of(x["path"])


def signal_of(st, b5, s, d0, j0):
    """3ペアとも抜け終わり、同じ足の終値で3ペアとも線の外にある最初の足（無ければ None）"""
    if any(st[p]["b"] is None for p in PAIRS):
        return None
    t1 = max(st[p]["b"] for p in PAIRS)
    c = {p: {b[0]: b[4] for b in b5[p] if d0 <= b[0] < j0} for p in PAIRS}
    for t in sorted(set.intersection(*(set(c[p]) for p in PAIRS))):
        if t >= t1 and all(s * (c[p][t] - st[p]["line"]) > 0 for p in PAIRS):
            return hhmm(t)
    return None


# ── 読む文と、人に聞くこと ────────────────────────────

def mark(v):
    return {True: "○", False: "×", None: "境目"}[v]


def report(r):
    L = [f"🔎 {PAIR_JP[r['pair']]} {'買い' if r['side'] == 'buy' else '売り'} {r['time']}（Yahoo の{'5分足' if r['coarse'] else '1分足と5分足'}・入る前の値だけ）"]
    if r["line"] is None:
        return "\n".join(L + ["  東京の線をまだ抜けていない＝線・30pips・50% は埋めない"])
    L.append(f"  割った東京の線 {r['line']:.3f}（{r['break_bar']} の足で抜け）")
    for p in PAIRS:
        if r["missing"][p] > MAX_MISSING:
            L.append(f"  ⚠️ {PAIR_JP[p]}は線を作る足が足りない（{r['missing'][p]}本。月曜の8時台は Yahoo に無い）＝線がずれているかもしれない")
    diff = None if r["line_auto"] is None else round(abs(r["line"] - r["line_auto"]) / PIP, 1)
    if diff is not None and diff >= LINE_WARN_PIPS:
        L.append(f"  ⚠️ 計算した線 {r['line_auto']:.3f} と {diff}pips 違う（渡された線を使った）")
    far = "境目" if r["far_state"] is None else ("届いていない" if r["far_min"] is None else f"{r['far_min']}分")
    L.append(f"  線から30pips まで：{far} → 30分以内 {mark(r['far_state'])}")
    L.append(f"  いちばん遠い値 {r['extreme']:.3f}（線から {r['leg_pips']}pips）" + (f"・入った所は {r['depth_pct']}% 戻した所" if r["depth_pct"] is not None else ""))
    for p in PAIRS:
        d = "・".join(f"{TYPE_JP[k]}まで " + ("入る所の足が無い" if v is None else f"{v}pips") for k, v in r["hits"][p].items())
        L.append(f"  {PAIR_JP[p]}：{mark(r['hit_state'][p])}（{d}）")
    n = "2以上かどうかが境目" if r["pairs_lm"] is None else f"{r['pairs_lm']}ペア"
    who = "・".join(f"{PAIR_JP[p]}＝" + lm_name(r, p) for p in PAIRS if r["lm_state"][p] is not False)
    L.append(f"  線か MA に当たっていたペア：{n}" + (f"（{who}）" if who else "") + f" → 2ペア以上 {mark(r['pairs_lm_state'])}")
    L.append(f"  （50% も入れた v2 の数：{'境目' if r['pairs_hit'] is None else r['pairs_hit']}）")
    best = "" if r["strong_far"] is None else f"／線からいちばん遠いのは {PAIR_JP[r['strong_far']]}（{r['share'][r['strong_far']] * 100:.3f}%）"
    L.append(f"  一番強い通貨：{strong_text(r)} → 入ったペアと同じ {mark(r['strong_state'])}{best}")
    L.append("  3ペアそろいの合図：" + (f"{r['signal']} の足" if r["signal"] else "見つからない（オーナーに確かめる）"))
    return "\n".join(L)


def lm_name(r, p):
    """当たっていた線の名前。計算した線だけの当たりで ±4pips しだいのときは「境目」"""
    if r["lm_state"][p] is None:
        return "境目"
    return "と".join(TYPE_JP[k] for k in LM if r["hits"][p].get(k) is not None and r["hits"][p][k] <= NEAR_PIPS - TOL)


def strong_text(r):
    """一番強い通貨と、その理由（ドル円とユーロポンドの向き）"""
    def way(k):
        d, v = r["flow"][k]
        return "足が無い" if d is None else f"{ {1: '上', -1: '下', None: '境目'}[v] }（MA から {d:+.1f}pips）"
    who = PAIR_JP[r["strong_flow"]] if r["strong_flow"] else ("決まらない（ドル円が逆向き）" if r["strong_sure"] else "境目")
    return f"{who}＝ドル円 {way('USDJPY')}・ユーロポンド {way('EURGBP')}"


def questions(r, given, unknown):
    """決められないもの → 人に聞く文の並び。given＝人が渡した項目・unknown＝分からないままでよいとした項目"""
    if r["line"] is None:
        return []
    q = []
    why = [f"線を作る足が {r['missing'][r['pair']]}本足りない"] if r["missing"][r["pair"]] > MAX_MISSING else []
    if r["far_state"] is not None and "far_min" not in given and r["far_if"] and any(v != r["far_state"] for v in r["far_if"]):
        why.append(f"線が {LINE_SENSE:g}pips ずれると、30分以内に30pips の○×が変わる")
    if why and "break_line" not in given and "line" not in unknown:
        q.append("・".join(why) + f"：チャートの赤い線は {r['line']:.3f} か → --break-line チャートの値（合っていれば同じ値）／分からない＝--unknown line")
    if r["far_state"] is None and "far_min" not in given and "far" not in unknown:
        q.append(f"抜けて30分以内に30pips に届いたかが境目（30分以内の最大 {r['far30_pips']}pips）：チャートの値を聞く → 届いた＝--far-min 分（30分より後でも、その分）／届かない＝--break-line と --extreme にチャートの値／分からない＝--unknown far")
    if r["type"] is None and "entry_type" not in given and "type" not in unknown:
        c = "・".join(TYPE_JP[k] for k in r["entry_types"] + r["maybe_types"]) or "当たった線が無い"
        q.append(f"どの線で入ったか（候補：{c}）→ --entry-type half50／line／ema15／series（入ったペアはまだ線の手前）／other・分からない＝--unknown type")
    if r["pairs_lm"] is None and "pairs_lm" not in given and "pairs" not in unknown:
        q.append("水平線か MA に当たっていたペアが2つ以上かが境目（" + "・".join(f"{PAIR_JP[p]} {mark(r['lm_state'][p])}" for p in PAIRS) + "）→ --pairs-lm 数（0〜3）・分からない＝--unknown pairs")
    if r["strong_state"] is not True and "strongest" not in given and "strong" not in unknown:
        q.append(f"入った{PAIR_JP[r['pair']]}は、そのとき一番強い通貨でしたか（道具の答え：{strong_text(r)}）→ --flags strongest=1 か 0・分からない＝--unknown strong")
    return q
