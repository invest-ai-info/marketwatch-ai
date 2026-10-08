# -*- coding: utf-8 -*-
"""J31F 空売りの前向き：目印 B・C の付いた株を寄り成行で売り、引け成行で買い戻す（損切りなし／+10％）。
2026-10-08 登録・オーナー「1と2を登録して続けてください」。PILLAR_PREREG.md「J31F」。

**2026-10-09 以降の朝だけ**を、東証の全上場の日足（始値・高値・終値）で数える。記録だけ＝取引に入れるかはオーナーが決める。
- 組：B＝前の日の売買代金10億円以上・前の日 +5％以上・その銘柄だけ +1％以上高く寄った／C＝前の日の売買代金10億円以上・
  前の日の売買代金が20営業日平均の5倍以上
- 腕：B0・C0（損切りなし）／B10・C10（損切り +10％・滑り 0.2％）。費用 0.03％
- 250営業日で1回だけ判定（98.75％の幅・朝と銘柄の広いほう）。60営業日ごとに費用後の平均がマイナスの腕は止める
- 読むだけの欄（判定に使わない）：相場全体を差し引いた平均（10/8 追記）／貸借銘柄だけの割合と平均（10/8 夕方の追記・J36 を受けて）／
  目印B・貸借銘柄・その銘柄だけの窓 +6％以上（10/8 夕方(2)の追記・J38 を受けて）／
  売り禁・規制がかかっていた割合と売り禁でなかった回だけの平均（J40・short-limits.json の毎朝の記録）

⚠️ 決まりは PILLAR_PREREG.md「J31F」と下の定数に固定。途中の数字を見て動かさない。行は J31 と同じ prevday_lab.stock_rows、
   倍率は landmine_lab.prev_more、幅は gap_forward._boot_agg、日の選び方は gap_forward.trading_days をそのまま使う。
⚠️ 1行ずつの取引は持たない。朝ごと・腕ごとの合計と、銘柄ごと（伏せた印）・腕ごとの合計だけ。
⚠️ 出力（auction-forward.json / .md）は GitHub 側で生成＝手元から送らない（SYNC禁忌）。積み上げた判定を持つ＝古い版で上書きしない。

実行: python auction_forward.py          （Actions の auction-forward.yml から平日に）
"""
import datetime as dt
import hashlib
import json
import sys
import time

import numpy as np

import build_jp_highs as H
import gap_forward as GF
import jp_taishaku as JT
import short_limits as SL
import landmine_lab as LM
import pillar_lab as P
import prevday_lab as PD
import yori_lab as Y

STATE, OUT_MD = "auction-forward.json", "auction-forward.md"
FWD_START = "2026-10-09"
GOAL_DAYS = 250
CHECK_EVERY = 60
N_Q = 4
ALPHA = 0.05 / N_Q            # 98.75％ の幅
MIN_N = 30
DAILY_RANGE = "3mo"
MIN_STOCKS = 500
MIN_BIG = 30                  # 🆕 2026-10-08 追記：相場全体（10億円以上の平均）を数えるのに要る銘柄の数（J34 と同じ）
TV_MIN, PREV_BIG, IDIO, TV_HIGH = 10.0, 0.05, 0.01, 5.0     # 点検表 日本株⑤ と同じ数字・10億円以上
COST, STOP, SLIP = 0.0003, 0.10, 0.002                       # J31・J32 と同じ
ARMS = ("B0", "B10", "C0", "C10")
EXTRA = ("BC0", "BW6")       # 読むだけ：B かつ C・損切りなし／B・貸借銘柄・その銘柄だけの窓 +6％以上・損切りなし（J38）
W6 = 0.06                    # 🆕 2026-10-08 夕方(2) 追記：J38 の W の箱（+6％以上）
TITLES = {"B0": "目印B（前の日 +5％以上・その銘柄だけ +1％以上高く寄った・10億円以上）を寄り成行で売り、引け成行で買い戻す（損切りなし・費用後）",
          "B10": "目印B を寄り成行で売り、+10％ の損切りか引け成行で買い戻す（費用後）",
          "C0": "目印C（前の日の売買代金が20営業日平均の5倍以上・10億円以上）を寄り成行で売り、引け成行で買い戻す（損切りなし・費用後）",
          "C10": "目印C を寄り成行で売り、+10％ の損切りか引け成行で買い戻す（費用後）"}
FAR = "2100-12-31"


def empty_state():
    return {"registered": "J31F", "kind": "forward", "fwd_start": FWD_START, "goal_days": GOAL_DAYS, "unit": "pct",
            "titles": TITLES, "verdicts": {}, "days": {}, "stocks": {}, "skipped": {}, "interim": [], "runs": []}


def load_state(path=STATE):
    try:
        with open(path, encoding="utf-8") as fh:
            st = json.load(fh)
    except FileNotFoundError:
        return empty_state()
    if st.get("fwd_start") != FWD_START or st.get("goal_days") != GOAL_DAYS:
        raise SystemExit(f"🚨 {path} の開始日・判定の日数が登録と違う＝上書きしない")
    return st


def tag(code):
    """銘柄コードを伏せた印（同じ銘柄は同じ印・コードには戻せない）"""
    return hashlib.sha1(("j31f:" + str(code)).encode()).hexdigest()[:10]


# ════════════════════ 1銘柄の朝 ════════════════════

def stock_mornings(daily, days, drops=None):
    """daily＝[(日付, 始, 高, 安, 終, 出来高)]（日付順）→ {日付: (窓, 前の日比, 倍率, 前の日の売買代金, 始→終, 始→高)}。
    行と除外は J31 と同じ（prevday_lab.stock_rows）"""
    A = PD.stock_rows(0, daily, {}, {}, first=FWD_START, last=FAR, recent_from=FAR, drops=drops)
    if not len(A):
        return {}
    ratio = LM.prev_more(daily)[0]
    pos = {dt.date.fromisoformat(r[0]).toordinal(): i for i, r in enumerate(daily)}
    out = {}
    for row in A:
        k = pos[int(row[PD.C["day"]])]
        day = daily[k][0]
        if day not in days:
            continue
        o, h = daily[k][1], daily[k][2]
        out[day] = (float(row[PD.C["gap"]]), float(row[PD.C["rprev"]]), float(ratio[k - 1]), float(row[PD.C["turnover"]]),
                    float(row[PD.C["rclose"]]), float(h / o - 1))
    return out


def arms_of(idio, rprev, ratio, tv):
    """→ その朝その銘柄が入る腕（読むだけの組も）"""
    if tv < TV_MIN:
        return []
    b = rprev >= PREV_BIG and idio >= IDIO
    c = np.isfinite(ratio) and ratio >= TV_HIGH
    return (["B0", "B10"] if b else []) + (["C0", "C10"] if c else []) + (["BC0"] if b and c else [])


def arm_net(arm, rclose, rhigh):
    if arm.endswith("10") and rhigh >= STOP:
        return -(STOP + SLIP) - COST
    return -rclose - COST


# ════════════════════ 合計を足す ════════════════════

LIM_ARMS = ("B0T", "BW6")      # J40 の欄：目印B のうち貸借銘柄の回／BW6 の回
LIM_LEN = 8                    # 記録のあった回・売り禁・注意喚起・その他・増担保・日々公表・売り禁でない回・その合計


def add_day(st, day, rows, tai=None, lim=None):
    """rows＝[(印, 窓, 前の日比, 倍率, 売買代金, 始→終, 始→高)]。数えた銘柄が MIN_STOCKS 未満なら足さない（False）。
    tai＝{"tags": 貸借銘柄の印の集合, "asof": 一覧の日付} か None（一覧が取れなかった回＝貸借の欄を空けたまま）"""
    if len(rows) < MIN_STOCKS:
        st.setdefault("skipped", {})[day] = len(rows)
        return False
    med = float(np.median([r[1] for r in rows]))
    big = [r[5] for r in rows if r[4] >= TV_MIN]
    mkt = float(np.mean(big)) if len(big) >= MIN_BIG else None   # 🆕 追記：相場全体の寄り→大引け（読むだけ）
    g = {k: [0, 0.0, 0, 0, 0.0, 0, 0.0] for k in ARMS + EXTRA}
    # 回数・損益の合計・損切りに届いた回数・（読むだけ）相場全体を差し引いた回数・合計・（読むだけ・10/8 夕方の追記）貸借銘柄の回数・合計
    tags = tai["tags"] if tai else None
    use = lim if lim and lim.get("jsf_ok") else None                     # J40：日本証券金融の表が読めた朝だけ
    lt = {k: set((use or {}).get("tags", {}).get(k, [])) for k in SL.CATS}
    lg = {k: [0] * (LIM_LEN - 1) + [0.0] for k in LIM_ARMS}
    for sid, gap, rprev, ratio, tv, rc, rh in rows:
        arms = arms_of(gap - med, rprev, ratio, tv)
        if "B0" in arms and gap - med >= W6 and tags is not None and sid in tags:
            arms.append("BW6")                                 # 読むだけ（一覧が無い朝は入れない）
        if use is not None and tags is not None and sid in tags and "B0" in arms:
            v0 = arm_net("B0", rc, rh)
            for k in [a for a in ("B0T", "BW6") if a == "B0T" or "BW6" in arms]:
                c = lg[k]
                c[0] += 1
                for i, cat in enumerate(("ban", "jsf_alert", "jsf_other", "zoutanpo", "daily"), 1):
                    c[i] += int(sid in lt[cat])
                if sid not in lt["ban"]:
                    c[6] += 1
                    c[7] += v0
        for arm in arms:
            v = arm_net(arm, rc, rh)
            g[arm][0] += 1
            g[arm][1] += v
            g[arm][2] += int(arm.endswith("10") and rh >= STOP)
            if mkt is not None:
                g[arm][3] += 1
                g[arm][4] += v + mkt
            if tags is not None and sid in tags:
                g[arm][5] += 1
                g[arm][6] += v
            if arm in ARMS:
                c = st["stocks"].setdefault(sid, {}).setdefault(arm, [0, 0.0])
                c[0] += 1
                c[1] += v
    st["days"][day] = {"g": g, "median_gap": med, "n": len(rows), "market": mkt, "tai_asof": (tai["asof"] or "日付不明") if tai else None,
                       "lim": lg if use is not None else None}
    st.get("skipped", {}).pop(day, None)
    return True


# ════════════════════ 幅と判定 ════════════════════

def _first(mu):
    return mu[0]


def _point(st, arm, days):
    n = sum(st["days"][d]["g"][arm][0] for d in days)
    return sum(st["days"][d]["g"][arm][1] for d in days) / n if n else None


def measure(st, arm):
    days = sorted(st["days"])
    n = sum(st["days"][d]["g"][arm][0] for d in days)
    out = {"days": len(days), "n": n, "mean": None, "lo": None, "hi": None, "early": None, "late": None}
    if not days or n == 0:
        return out
    Sd = [[st["days"][d]["g"][arm][1] for d in days]]
    Nd = [[st["days"][d]["g"][arm][0] for d in days]]
    ids = sorted(i for i in st["stocks"] if arm in st["stocks"][i])
    Ss = [[st["stocks"][i][arm][1] for i in ids]]
    Ns = [[st["stocks"][i][arm][0] for i in ids]]
    pt, lo_d, hi_d = GF._boot_agg(Sd, Nd, _first, alpha=ALPHA)
    _, lo_s, hi_s = GF._boot_agg(Ss, Ns, _first, alpha=ALPHA)
    half = len(days) // 2
    out.update(mean=pt, by_day=[lo_d, hi_d], by_stock=[lo_s, hi_s],
               early=_point(st, arm, days[:half]) if half else None, late=_point(st, arm, days[half:]))
    if None not in (lo_d, lo_s, hi_d, hi_s):
        out.update(lo=min(lo_d, lo_s), hi=max(hi_d, hi_s))
    return out


def judge(m, day, interim=False):
    if interim:
        return {"status": "stop", "decided_on": day, "n": m["n"], "days": m["days"], "mean": m["mean"], "lo": m["lo"],
                "hi": m["hi"], "early": m["early"], "late": m["late"],
                "reason": f"途中の見張り（{m['days']}営業日）で費用後の平均がマイナス"}
    ok = m["n"] >= MIN_N and m["lo"] is not None and m["lo"] > 0 and (m["early"] or 0) > 0 and (m["late"] or 0) > 0
    reason = "" if ok else ("件数不足" if m["n"] < MIN_N else "98.75％の幅が0をまたぐ／前半か後半がプラスでない")
    return {"status": "plus" if ok else "stop", "decided_on": day, "n": m["n"], "days": m["days"], "mean": m["mean"],
            "lo": m["lo"], "hi": m["hi"], "early": m["early"], "late": m["late"], "reason": reason}


def after_day(st, day):
    """1日足したあと：250営業日なら判定・60営業日ごとにマイナスの腕を止める（判定は書き換えない）"""
    n = len(st["days"])
    for arm in ARMS:
        if arm in st["verdicts"]:
            continue
        if n == GOAL_DAYS:
            st["verdicts"][arm] = judge(measure(st, arm), day)
        elif n % CHECK_EVERY == 0:
            m = measure(st, arm)
            st["interim"].append({"day": day, "days": n, "arm": arm, "mean": m["mean"]})
            if m["mean"] is not None and m["mean"] < 0:
                st["verdicts"][arm] = judge(m, day, interim=True)


def done(st):
    return all(arm in st["verdicts"] for arm in ARMS)


# ════════════════════ 実行 ════════════════════

def run(st, codes, fetch, today, tai_loader=lambda: None, limits=None):
    """1回分：まだ数えていない朝を数えて足す。→ (足した朝, 取れなかった銘柄数)。
    tai_loader＝貸借銘柄の一覧を取る関数（jp_taishaku.load_or_none の形）。足す朝があるときだけ1回呼ぶ"""
    dailies, missing = {}, 0
    for i, code in enumerate(codes):
        d = fetch(code, "1d", DAILY_RANGE)
        if not d:
            missing += 1
            continue
        dailies[code] = sorted({t.date().isoformat(): (t.date().isoformat(), o, h, lo, c, v) for t, o, h, lo, c, v in d}.values())
        if (i + 1) % 500 == 0:
            print(f"  ...{i + 1}/{len(codes)}", flush=True)
        time.sleep(0.02)
    if missing > 0.05 * len(codes):
        print(f"⚠️ 値段を取れなかった銘柄 {missing}/{len(codes)}＝5％超。この回は1日も数えない")
        return [], missing
    new = [d for d in GF.trading_days(dailies, today, start=FWD_START) if d not in st["days"]]
    drops = {"n": 0}
    per = {code: stock_mornings(dailies[code], set(new), drops) for code in dailies}
    lst = tai_loader() if new and not done(st) else None
    tai = {"tags": {tag(c) for c in lst["codes"]}, "asof": lst.get("asof")} if lst else None
    added = []
    for day in new:
        if done(st):
            break
        rows = [(tag(code), *per[code][day]) for code in sorted(per) if day in per[code]]
        if add_day(st, day, rows, tai, ((limits or {}).get("days") or {}).get(day)):
            after_day(st, day)
            added.append(day)
    return added, missing


# ════════════════════ 出力 ════════════════════

_PAD = [0, 0.0, 0, 0, 0.0, 0, 0.0]


def summary(st):
    days = sorted(st["days"])
    def cnt(d, k):                                                         # 追記より前の朝にはその欄が無い
        a = list(st["days"][d]["g"].get(k, []))
        return a + _PAD[len(a):]
    tot = {k: [sum(cnt(d, k)[i] for d in days) for i in range(7)] for k in ARMS + EXTRA}
    listed = [d for d in days if st["days"][d].get("tai_asof")]          # 貸借銘柄の一覧があった朝
    n_listed = {k: sum(cnt(d, k)[0] for d in listed) for k in ARMS + EXTRA}
    daily = {}
    for k in ARMS:
        vals = [st["days"][d]["g"][k][1] / st["days"][d]["g"][k][0] for d in days if st["days"][d]["g"][k][0]]
        daily[k] = {"days": len(vals), "lose": (sum(v < 0 for v in vals) / len(vals)) if vals else None,
                    "worst": min(vals) if vals else None}
    lim_days = [d for d in days if st["days"][d].get("lim")]
    lim = {k: [sum(st["days"][d]["lim"][k][i] for d in lim_days) for i in range(LIM_LEN)] for k in LIM_ARMS}
    limits = {"days": len(lim_days), "arms": {k: {"n": v[0], **{cat: (v[i] / v[0] if v[0] else None) for i, cat in
                                                   enumerate(("ban", "jsf_alert", "jsf_other", "zoutanpo", "daily"), 1)},
                                              "ok_n": v[6], "ok_mean": v[7] / v[6] if v[6] else None} for k, v in lim.items()}}
    return {"days": len(days), "first": days[0] if days else None, "last": days[-1] if days else None, "limits": limits,
            "arms": {k: {"n": v[0], "mean": v[1] / v[0] if v[0] else None, "hit": v[2] / v[0] if v[0] else None,
                         "adj": v[4] / v[3] if v[3] else None, "tai_n": v[5],
                         "tai_share": v[5] / n_listed[k] if n_listed[k] else None,
                         "tai_mean": v[6] / v[5] if v[5] else None} for k, v in tot.items()}, "daily": daily,
            "tai_days": len(listed), "tai_asof": st["days"][listed[-1]]["tai_asof"] if listed else None}


def _tai(a):
    if a.get("tai_share") is None:
        return "—"
    return f"{a['tai_share'] * 100:.0f}％・{GF._p(a['tai_mean'])}"


def render_md(st, now):
    sm = summary(st)
    L = ["# J31F 空売りの前向き：目印 B・C を寄り成行で売り、引け成行で買い戻す", "",
         f"更新: {now}（GitHub Actions）。事前登録＝`{P.PREREG}`「J31F」（指紋 sha256 `{(st.get('prereg_sha256') or '')[:16]}…`）。",
         f"数えるのは **{FWD_START} 以降の朝**だけ（一度数えた朝は数え直さない）。値は日足の始値で売り終値で買い戻したときの損益率"
         f"（プラス＝売りが勝った・費用 {COST * 100:.2f}％ 込み）。銘柄名は出しません。**記録だけ＝売買の決まりではない**。", "",
         f"- 数えた朝：{sm['days']}営業日（{sm['first'] or '—'}〜{sm['last'] or '—'}）／判定は **{GOAL_DAYS}営業日**で1回だけ"
         f"（98.75％の幅・{CHECK_EVERY}営業日ごとに費用後の平均がマイナスの腕は止める）", "",
         "| 腕 | 回数 | 費用後の平均 | 相場全体を差し引いた平均（読むだけ） | 貸借銘柄だけ：割合・平均（読むだけ） | 損切りに届いた割合 | 1日ごとの負けた日 | いちばん悪い日 | 状態 |",
         "|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for k in ARMS:
        a, d, vd = sm["arms"][k], sm["daily"][k], st["verdicts"].get(k)
        state = ("✅ 前向きでもプラス" if vd["status"] == "plus" else "⏹ ストップ") if vd else "観察中"
        hit = "—" if not k.endswith("10") or a["hit"] is None else f"{a['hit'] * 100:.0f}％"
        lose = "—" if d["lose"] is None else f"{d['lose'] * 100:.0f}％"
        L.append(f"| {k} | {a['n']:,} | {GF._p(a['mean'])} | {GF._p(a['adj'])} | {_tai(a)} | {hit} | {lose} | {GF._p(d['worst'])} | {state} |")
    bc, bw = sm["arms"]["BC0"], sm["arms"]["BW6"]
    L += ["", f"- 読むだけ：B かつ C（損切りなし）{bc['n']:,}回・費用後の平均 {GF._p(bc['mean'])}",
          f"- 読むだけ：目印B・貸借銘柄・その銘柄だけの窓 +6％以上（損切りなし・J38 で ✅ の箱・2026-10-08 夕方(2)の追記）{bw['n']:,}回・"
          f"費用後の平均 {GF._p(bw['mean'])}（貸借銘柄の一覧があった朝だけ）",
          "- 相場全体を差し引いた平均＝1回の損益 ＋ その朝の相場全体（前の日の売買代金10億円以上の全銘柄）の寄り→大引け"
          "（同じ金額だけ相場全体を買って打ち消した形・2026-10-08 の追記・判定には使わない）",
          f"- 貸借銘柄だけ＝制度信用で空売りできる銘柄（日本取引所グループの一覧・いちばん新しい朝は {sm['tai_asof'] or '—'}）の回数の割合と費用後の平均"
          f"（2026-10-08 夕方の追記・J36 を受けて・判定には使わない）。一覧があった朝 {sm['tai_days']}／{sm['days']}営業日。"
          "売り禁（貸借取引の申込停止）と証券会社ごとの在庫は入っていない"]
    lm = sm["limits"]
    for k, name in (("B0T", "目印B・貸借銘柄"), ("BW6", "目印B・貸借銘柄・窓 +6％以上")):
        a = lm["arms"][k]
        pc = lambda x: "—" if x is None else f"{x * 100:.0f}％"  # noqa: E731
        L.append(f"- 読むだけ（J40・2026-10-08 夕方の登録）：{name}の回のうち、その朝 売り禁 {pc(a['ban'])}・注意喚起 {pc(a['jsf_alert'])}・"
                 f"その他の措置 {pc(a['jsf_other'])}・増担保 {pc(a['zoutanpo'])}・日々公表 {pc(a['daily'])}（記録のある回 {a['n']:,}・朝 {lm['days']}）／"
                 f"売り禁でなかった回だけの費用後の平均 {GF._p(a['ok_mean'])}（{a['ok_n']:,}回）")
    L += ["", "## 腕ごとの判定", ""]
    for k in ARMS:
        vd = st["verdicts"].get(k)
        if vd:
            res = "✅ 前向きでもプラス" if vd["status"] == "plus" else "⏹ ストップ"
            L.append(f"- **{k} {TITLES[k]}**：{res}（{vd['decided_on']}・{vd['days']}営業日・{vd['n']:,}回）費用後 {GF._p(vd['mean'])}"
                     f"（98.75％の幅 {GF._p(vd['lo'])}〜{GF._p(vd['hi'])}・前半 {GF._p(vd['early'])}／後半 {GF._p(vd['late'])}）{('・' + vd['reason']) if vd['reason'] else ''}")
        else:
            L.append(f"- **{k} {TITLES[k]}**：観察中（{sm['days']}/{GOAL_DAYS}営業日）")
    if st.get("interim"):
        L.append("- 途中の見張り：" + "／".join(f"{x['arm']} {x['days']}営業日 {GF._p(x['mean'])}" for x in st["interim"]))
    if st.get("skipped"):
        L.append(f"- 銘柄が{MIN_STOCKS}未満で数えなかった朝：" + "・".join(f"{d}（{n}）" for d, n in sorted(st["skipped"].items())))
    L += ["", "- 実際の約定ではない（売り禁・在庫切れ・気配と始値のずれ・ストップ高で買い戻せない日・損切りの滑りは入っていない）。",
          "", "---", "", "※ 研究の記録です。投資助言ではありません。空売りは損失が限られない取引です。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def finalize(st):
    """検証済みリスト・研究の地図が読む欄（いまの回数と判定の目安）"""
    sm = summary(st)
    st["progress"] = {k: sm["arms"][k]["n"] for k in ARMS}
    st["goal"] = f"{GOAL_DAYS}営業日で判定・いま {sm['days']}営業日"
    st["summary"] = sm
    return st


def main(argv):
    st = load_state()
    now = dt.datetime.now(P.JST)
    st["prereg_sha256"] = P.prereg_sha256()
    if not done(st):
        stocks, _ = H.load_universe()
        got = {}
        added, missing = run(st, sorted(stocks), Y.fetch_chart, now.date().isoformat(),
                             tai_loader=lambda: got.setdefault("list", JT.load_or_none()), limits=SL.load_json(SL.STATE))
        lst = got.get("list")
        st["runs"] = (st.get("runs") or [])[-30:] + [{"at": now.isoformat(timespec="minutes"), "added": added,
                                                       "n_codes": len(stocks), "missing": missing,
                                                       "taishaku": (lst.get("asof") or "日付不明") if lst else None}]
        print(f"足した朝：{added or 'なし'}（取れなかった銘柄 {missing}/{len(stocks)}）")
    finalize(st)
    with open(STATE, "w", encoding="utf-8") as fh:
        json.dump(st, fh, ensure_ascii=False, indent=0, default=str)
        fh.write("\n")
    md = render_md(st, now.isoformat(timespec="minutes"))
    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
