# -*- coding: utf-8 -*-
"""J52F：業績予想の修正のあと、どのタイミングで入ると勝ちやすいか（前向き・PILLAR_PREREG.md「J52」）。

2026-11-17 オーナー「おそらく発表されるのは東京時間が終わってからのことなので、次の日にもう値動きは決まってしまっているので、
エントリーしても勝つのは難しいのは理解しています。そこでどのタイミングでエントリーすれば勝つ可能性が高いのかを調査してください」。

- 出来事：J51 の台帳（`tdnet-reaction.csv`）のうち **2026-11-18 以降の開示**で、上方修正（U）・下方修正（D）の付いたもの
  （表題の言葉と PDF の表の向き）。反応の日 R の前の取引日の売買代金 1億円以上
- 記録（値段は置かない＝R の寄りを 1 とした比だけ）：R の寄り・R+1 の寄り・R の 10:00・R の後場寄り（12:30）と、
  R〜R+30 の引け（31本）。TOPIX（1306）も同じ形。5分足は約60日で消えるので、R の引けが確定したら早めに取る
- 判定：入る E1〜E8 × 出る X0・X5・X20 の 34升（U・D それぞれ17）。**升ごとに 300件・開示の日40日に届いた日に1回だけ**
  （平均が費用を超え・前半と後半が同じ向き・z が基準を超える）。一度決めたら変えない。途中の平均は出さない（件数だけ）

⚠️ 出力（disclosure-timing-forward.csv／.json）は GitHub 側で生成＝ローカルから push しない（SYNC禁忌）。
⚠️ ✅ でも取引の決まりではない（売り禁・在庫切れ・約定の滑りは入っていない）。

実行: python disclosure_timing_forward.py      （tdnet-reaction.yml の中・J51 のあと）
"""
import csv
import datetime as dt
import json
import statistics
import sys
import time

import tdnet_reaction as TR

JST = TR.JST
START = "2026-11-18"
OUT_CSV, OUT_JSON = "disclosure-timing-forward.csv", "disclosure-timing-forward.json"
J52_HISTORY_CHECKED = {}   # 🔁 2026-11-20 J52 で ✅ だった升（＝基準を 1.96 に下げる升）。J52 は 26升すべて ✕ だったので空
N_CLOSE = 31                    # R〜R+30 の引け
MIN_TV = 1e8                    # R の前の取引日の売買代金（円）
COST_LONG, COST_SHORT = 0.001, 0.002
GOAL_N, GOAL_DAYS = 300, 40
INTRA_DAYS = 25                 # R からこの暦日以内に5分足を取る（Yahoo の 1mo の範囲）
PAUSE = 0.15
COLS = ("date", "code", "kind", "time", "react_on", "tv_prev", "o", "c", "to", "tc", "intra", "ok")
ENTRIES = {"E1": "R の寄り", "E2": "R の引け", "E3": "R+1 の寄り", "E4": "R+2 の引け", "E5": "R+4 の引け",
           "E6": "押し目・戻り待ち（R+1〜R+10）", "E7": "R の 10:00", "E8": "R の後場寄り"}
CELLS = (("E1", "X0"), ("E1", "X5"), ("E1", "X20"), ("E2", "X5"), ("E2", "X20"), ("E3", "X5"), ("E3", "X20"),
         ("E4", "X5"), ("E4", "X20"), ("E5", "X5"), ("E5", "X20"), ("E6", "X5"), ("E6", "X20"),
         ("E7", "X0"), ("E7", "X5"), ("E8", "X0"), ("E8", "X5"))
KINDS = {"U": "上方修正", "D": "下方修正"}
# 🆕 2026-11-21 オーナー決定（記録はどの升も1件以下＝結果を見る前）：登録の文「0.05/34（両側・約3.4）」は
#    式どおりなら z 3.18・括弧の「約3.4」なら 3.38 で食い違っていた → **きびしい方の「約3.4」をとる**
#    ＝升34で両側 0.05/68 → z 3.376（J52 の過去で文の「約3.3」をとったのと同じ考え方）。`PILLAR_PREREG.md`「J52」の補足
Z_NEED = statistics.NormalDist().inv_cdf(1 - 0.05 / (4 * len(CELLS) * len(KINDS)))


# ════════════════════ 出来事・値段の道（純関数） ════════════════════

def kind_of(row):
    ks = TR.row_kinds(row)
    u, d = "上方修正" in ks, "下方修正" in ks
    return "U" if u and not d else ("D" if d and not u else None)


def events_from_ledger(rows, start=START):
    out = []
    for r in rows:
        if r.get("date", "") < start or str(r.get("ok")) != "1" or not r.get("react_on"):
            continue
        k = kind_of(r)
        if k:
            out.append({"date": r["date"], "code": r["code"], "kind": k, "time": r["time"], "react_on": r["react_on"]})
    return out


def bar_map(bars):
    """[(時刻, 始, 高, 安, 終, 出来高)] → {日付: (始, 終, 出来高)}"""
    return {t.date().isoformat(): (o, c, v) for t, o, h, l, c, v in bars or []}


def intraday(bars5, day):
    """その日の5分足 → (最初の足の始値, 10:00 の始値, 後場寄りの始値)。無ければ None"""
    xs = sorted((t, o) for t, o, h, l, c, v in bars5 or [] if t.date().isoformat() == day)
    first = xs[0][1] if xs else None
    at10 = next((o for t, o in xs if (10, 0) <= (t.hour, t.minute) < (11, 30)), None)
    at1230 = next((o for t, o in xs if (t.hour, t.minute) >= (12, 30)), None)
    return first, at10, at1230


def closes_path(m, days, react_on, now):
    """R〜R+30 の引けの値段（取引の無い日は前の値・いちばん新しい日が無ければそこで止める・確定前の日は入れない）"""
    if react_on not in days:
        return []
    i0 = days.index(react_on)
    out, last = [], None
    for k in range(N_CLOSE):
        if i0 + k >= len(days):
            break
        d = days[i0 + k]
        if not TR.matured(d, now):
            break
        if d in m and m[d][1]:
            last = m[d][1]
        elif d == days[-1]:
            break                                   # 夜中にいちばん新しい日が空＝次の回を待つ
        if last is None:
            break
        out.append(last)
    return out


def ratios(xs, base):
    return ";".join("" if x is None else f"{x / base:.5f}" for x in xs)


def parse_ratios(s):
    return [None if x == "" else float(x) for x in (s or "").split(";")] if s else []


# ════════════════════ 升の値（純関数） ════════════════════

def entry_point(row, e):
    """→ (入った値段の比, 1306 の比, 日の番号 k, 寄りか引けか)。入れなければ None"""
    o, c, to, tc = (parse_ratios(row.get(k)) for k in ("o", "c", "to", "tc"))
    if not o or not c or not to or not tc:
        return None

    def at(xs, i):
        return xs[i] if i < len(xs) else None
    if e == "E1":
        return (o[0], to[0], 0, "open")
    if e == "E2":
        return (at(c, 0), at(tc, 0), 0, "close")
    if e == "E3":
        return (at(o, 1), at(to, 1), 1, "open")
    if e == "E4":
        return (at(c, 2), at(tc, 2), 2, "close")
    if e == "E5":
        return (at(c, 4), at(tc, 4), 4, "close")
    if e == "E6":
        for k in range(1, 11):
            x = at(c, k)
            if x is None:
                return None
            if (row["kind"] == "U" and x <= o[0]) or (row["kind"] == "D" and x >= o[0]):
                return (x, at(tc, k), k, "close")
        return ("none",)                            # 10日のうちに来なかった＝入らない（数えない）
    if e == "E7":
        return (at(o, 2), at(to, 2), 0, "open")
    if e == "E8":
        return (at(o, 3), at(to, 3), 0, "open")
    return None


def cell_return(row, e, x):
    """その升の値（入ってから出るまで − 同じ時間の 1306）。まだ出られない・入れないなら None"""
    p = entry_point(row, e)
    if not p or p == ("none",) or p[0] is None or p[1] is None:
        return None
    pe, te, k, typ = p
    c, tc = parse_ratios(row["c"]), parse_ratios(row["tc"])
    if x == "X0":
        j = 0
    else:
        h = 5 if x == "X5" else 20
        j = k + (h - 1 if typ == "open" else h)
    if j >= len(c) or j >= len(tc) or c[j] is None or tc[j] is None:
        return None
    return (c[j] / pe) - (tc[j] / te)


def judge(rows, today, hist=None):
    """→ {"U|E1|X0": {"n", "days", (判定)}}。升ごとに 300件・開示の日40日で1回だけ（前の判定は変えない）"""
    hist = hist or {}
    zc = Z_NEED
    out = {}
    for kind in KINDS:
        rs = [r for r in rows if r.get("kind") == kind and str(r.get("ok")) == "1"]
        for e, x in CELLS:
            vals = [(r["date"], v) for r in rs for v in [cell_return(r, e, x)] if v is not None]
            key = f"{kind}|{e}|{x}"
            days = len({d for d, _ in vals})
            res = {"n": len(vals), "days": days}
            if len(vals) >= GOAL_N and days >= GOAL_DAYS:
                mean, z, _ = TR.cluster_z(vals)
                vs = sorted(vals)
                h = len(vs) // 2
                m1 = sum(v for _, v in vs[:h]) / h
                m2 = sum(v for _, v in vs[h:]) / (len(vs) - h)
                side = "買い" if mean > COST_LONG else ("売り" if mean < -COST_SHORT else None)
                need = 1.96 if side and hist.get(key) == f"✅ {side}" else zc
                ok = bool(side and z is not None and abs(z) >= need and m1 * mean > 0 and m2 * mean > 0)
                res.update(decided_on=today, mean=round(mean, 6), z=round(z, 3) if z is not None else None,
                           first_half=round(m1, 6), second_half=round(m2, 6), z_need=round(need, 3),
                           status=f"✅ {side}" if ok else "✕ 見えない")
            out[key] = res
    return out


# ════════════════════ 取る・ためる ════════════════════

def needs_update(row, now):
    if str(row.get("ok")) == "0" and row.get("c"):
        return False
    full = len(parse_ratios(row.get("c"))) >= N_CLOSE
    intra_open = row.get("intra") not in ("1", "na")
    return not full or intra_open


def update_row(row, days, daily, tx_daily, b5, tx5, now):
    """1件の行を値段で埋める（daily＝bar_map・b5＝5分足）。→ 行（ok を付ける）"""
    R = row["react_on"]
    if R not in days or not TR.matured(R, now):
        return row
    i = days.index(R)
    prev = days[i - 1] if i > 0 else None
    if prev and prev in daily and daily[prev][1]:
        row["tv_prev"] = f"{daily[prev][1] * daily[prev][2] / 1e8:.2f}"
    first, at10, at1230 = intraday(b5, R) if b5 else (None, None, None)           # 空の5分足＝取れなかった（次の回にもう一度）
    tfirst, t10, t1230 = intraday(tx5, R) if tx5 else (None, None, None)
    o0 = (daily.get(R) or (None,))[0] or first
    t0 = (tx_daily.get(R) or (None,))[0] or tfirst
    if not o0 or not t0:
        return row
    nxt = days[i + 1] if i + 1 < len(days) else None
    o1 = daily[nxt][0] if nxt and nxt in daily and TR.matured(nxt, now) else None
    to1 = tx_daily[nxt][0] if nxt and nxt in tx_daily and TR.matured(nxt, now) else None
    old_o, old_to = parse_ratios(row.get("o")), parse_ratios(row.get("to"))
    if b5 and tx5:
        row["intra"] = "1" if (at10 or at1230) and (t10 or t1230) else "na"
    else:
        at10 = old_o[2] * o0 if len(old_o) > 2 and old_o[2] else None
        at1230 = old_o[3] * o0 if len(old_o) > 3 and old_o[3] else None
        t10 = old_to[2] * t0 if len(old_to) > 2 and old_to[2] else None
        t1230 = old_to[3] * t0 if len(old_to) > 3 and old_to[3] else None
    row["o"] = ratios([o0, o1, at10, at1230], o0)
    row["to"] = ratios([t0, to1, t10, t1230], t0)
    row["c"] = ratios(closes_path(daily, days, R, now), o0)
    row["tc"] = ratios(closes_path(tx_daily, days, R, now), t0)
    tv = TR.num(row.get("tv_prev"))
    row["ok"] = "1" if tv is not None and tv * 1e8 >= MIN_TV else "0"
    return row


def run(ledger_rows, old_rows, now, getter=None, pause=PAUSE, log=print):
    getter = getter or TR.fetch_chart
    tx = getter(TR.TOPIX, "1d", "6mo") or []
    days = sorted(bar_map(tx))
    if not days:
        log("  ⚠️ 1306 の日足が取れない＝今回は更新しない")
        return old_rows
    tx_daily = bar_map(tx)
    tx5 = None
    rows = {(r["date"], r["code"], r["react_on"]): r for r in old_rows}
    for ev in events_from_ledger(ledger_rows):
        rows.setdefault((ev["date"], ev["code"], ev["react_on"]), dict({k: "" for k in COLS}, **ev))
    cache, n = {}, 0
    for key, r in sorted(rows.items()):
        if not needs_update(r, now) or r["react_on"] not in days or not TR.matured(r["react_on"], now):
            continue
        c = r["code"]
        if c not in cache:
            time.sleep(pause)
            cache[c] = bar_map(getter(c, "1d", "6mo") or [])
        want5 = r.get("intra") not in ("1", "na") and (now.date() - dt.date.fromisoformat(r["react_on"])).days <= INTRA_DAYS
        b5 = None
        if want5:
            time.sleep(pause)
            b5 = getter(c, "5m", "1mo") or []
            if tx5 is None:
                tx5 = getter(TR.TOPIX, "5m", "1mo") or []
        elif r.get("intra") not in ("1", "na"):
            r["intra"] = "na"                              # 5分足の窓を過ぎた＝場中の升には入れない
        update_row(r, days, cache[c], tx_daily, b5, tx5 if want5 else None, now)
        n += 1
    log(f"  J52F：出来事 {len(rows)}件・更新 {n}件（{len(cache)}社）")
    return list(rows.values())


def read_csv(path=OUT_CSV):
    try:
        with open(path, encoding="utf-8-sig") as fh:
            return list(csv.DictReader(fh))
    except OSError:
        return []


def save_csv(rows, path=OUT_CSV):
    rows = sorted(rows, key=lambda r: (r["date"], r["time"], r["code"]))
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in COLS})


def status_lines(js):
    """メールに載せる行（件数だけ・途中の平均は出さない）"""
    cells = js.get("cells") or {}
    by = js.get("by_kind") or {}
    L = []
    for kind, name in KINDS.items():
        b = by.get(kind) or {}
        done = [k for k, v in cells.items() if k.startswith(kind + "|") and v.get("status")]
        L.append(f"・{name}：記録 {b.get('n', 0)}件・開示の日 {b.get('days', 0)}日（升ごとに {GOAL_N}件・{GOAL_DAYS}日で1回だけ判定）"
                 + (f"・判定済み {len(done)}升" if done else ""))
    for k, v in sorted(cells.items()):
        if v.get("status"):
            L.append(f"  {k}：{v['status']}（{v['n']}件・平均 {v['mean'] * 100:+.2f}%）")
    return L


def main(argv=None):
    now = dt.datetime.now(JST)
    ledger = TR.read_ledger()
    old = read_csv()
    rows = run(ledger, old, now)
    save_csv(rows)
    prev = TR.read_json(OUT_JSON, {})
    # 🔁 2026-11-20 j52-history.json（J52 を J-Quants で数えた升ごとの ✅／✕）は読まない＝公開のリポジトリに置かない（相談メモ⑪ の C）。
    #    J52 の判定は 26升すべて ✕ だった（2026-11-17）＝基準を下げる升は1つも無い＝空にしても判定は同じ（どの升も厳しい基準 zc）
    hist = J52_HISTORY_CHECKED
    cells = judge(rows, now.date().isoformat(), hist)
    for k, v in (prev.get("cells") or {}).items():          # 一度決めた判定は変えない
        if v.get("status"):
            cells[k] = v
    usable = [r for r in rows if str(r.get("ok")) == "1"]
    by_kind = {k: {"n": sum(1 for r in usable if r["kind"] == k), "days": len({r["date"] for r in usable if r["kind"] == k})}
               for k in KINDS}
    js = {"registered": "J52F（2026-11-17）", "start": START, "updated": now.isoformat(timespec="minutes"),
          "goal_n": GOAL_N, "goal_days": GOAL_DAYS, "events": len(rows), "usable": len(usable), "by_kind": by_kind,
          "cells": cells}
    TR.save_json(js, OUT_JSON)
    print("\n".join(status_lines(js)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
