# -*- coding: utf-8 -*-
"""J10F 高値更新の翌朝の罠の目印・前向き（2026-10-06 登録・オーナー「進めてください」）。

J10（highs_trap_lab.py）で「窓 +1％ 以上で寄る」が罠の目印（兆し）だったので、使う前に結果のあとのデータだけで確かめる。
2つの組を同じ決まりで別々に数える：
  A＝約400銘柄（jp-stock-info.json）。J10 と同じ決め方（highs_trap_lab.ytd_flags）で高値更新を日足から決め直す＝取りこぼしても数え直せる
  B＝サイトの高値更新の一覧そのもの（jp-highs.json の highs・東証の全上場）。出たら写して取っておき、翌朝を数える＝写せなかった日は数えない

⚠️ 決まりは PILLAR_PREREG.md「J10F」と下の定数に固定。結果を見てから動かさない。
⚠️ 1日は一度数えたら固定。判定は組ごとに「目印ありが1000回に届いた日」に1回だけ。
⚠️ 出力（highs-trap-forward.json / .md）は集計だけ・銘柄名なし（銘柄は見分けるための符号だけ）。B の一覧は数え終わったら消す。
   GitHub 側で生成＝手元から送らない（SYNC禁忌）。古い版で上書きすると積み上げた取引と判定が消える。
⚠️ メール・エンジン・売買の決まりには触れない。

実行: python highs_trap_forward.py                 （平日：一覧を写す＋数える＋判定。そのあと verified_list.py）
      python highs_trap_forward.py --capture-only  （「JP Highs Lows」の完了で：一覧を写すだけ・値段は取りに行かない）
"""
import datetime as dt
import hashlib
import json
import sys
import time

import highs_trap_lab as T
import pillar_lab as P
import yori_lab as Y

FWD_START = "2026-10-07"      # 翌朝がこの日以降の取引だけ（J10 は 10/5 まで・10/6 は仮説づくり）
LIST_START = "2026-10-06"     # B はこの日の大引けのあとの一覧から（翌朝＝10/7）
GOAL = 1000                   # 目印ありの取引がこの回数に届いた日に1回だけ判定（オーナーの1000回の決まり）
ALPHA = 0.05                  # 95％の幅
GAP_UP = T.GAP_UP             # 目印＝窓 +1％ 以上（J10 の Q1）
MIN_COVER_A = 0.95            # A：その日に5分足が取れた銘柄がユニバースのこの割合未満なら数えない（J4F と同じ）
MIN_COVER_B = 0.90            # B：一覧の銘柄のこの割合以上で値が取れたら数える
B_WAIT_DAYS = 10              # B：翌朝から10営業日を過ぎたら取れた分だけで数える
B_TOO_OLD = 55                # B：翌朝から55日を超えると5分足が取れない＝数えられなかったとして残す
MAX_MISSING = 0.02            # A：値段を取れなかった銘柄がこの割合を超えた実行は数えない
DAILY_RANGE = "2y"            # A：年初来の期間（1〜3月は前の年の1月から）を覆う
MIN_WINDOW_START = "2025-01-01"
OUT_JSON, OUT_MD = "highs-trap-forward.json", "highs-trap-forward.md"
HIGHS = "jp-highs.json"
TITLES = {
    "A": "窓+1％以上で寄った高値更新は、寄り→9:30 が目印なしより弱い（約400銘柄・J10 と同じ決め方）",
    "B": "窓+1％以上で寄った高値更新は、寄り→9:30 が目印なしより弱い（サイトの高値更新の一覧そのもの）",
}


def stock_key(code):
    return hashlib.sha256(str(code).encode()).hexdigest()[:8]


def empty_state():
    return {"kind": "marker", "fwd_start": FWD_START, "goal": GOAL, "titles": dict(TITLES),
            "trades": [], "days": {"A": {}, "B": {}}, "lists": {}, "verdicts": {}}


def load_state(path=OUT_JSON):
    """記録が無ければ空から始める。登録日が違うときは止める（空で上書きすると積み上げた取引が消えるため）"""
    try:
        with open(path, encoding="utf-8") as fh:
            st = json.load(fh)
    except FileNotFoundError:
        return empty_state()
    if st.get("fwd_start") != FWD_START or st.get("kind") != "marker":
        raise SystemExit(f"🚨 {path} の登録日・種類が違う（{st.get('fwd_start')}／{st.get('kind')}）＝上書きしない")
    return st


# ════════════════════ B：サイトの一覧を写す ════════════════════

def capture(state, highs, now_iso):
    """jp-highs.json の中身（dict）→ まだ写していない一覧なら写す。写した asof を返す（写さなければ None）"""
    asof = (highs or {}).get("asof")
    if not asof or asof < LIST_START or asof in state["lists"]:
        return None
    items = [[it["code"], float(it["price"])] for it in highs.get("highs") or [] if it.get("code") and it.get("price")]
    state["lists"][asof] = {"captured_at": now_iso, "universe": highs.get("universe"), "items": items, "status": "pending"}
    return asof


def _close_list(L, status, **kw):
    """数え終わった（または数えられなかった）一覧は、銘柄コードを消して件数だけ残す"""
    L.update(kw, status=status, n_items=len(L.get("items") or []))
    L["items"] = []


def next_trading_day(tdays, asof):
    i = next((k for k, d in enumerate(tdays) if d > asof), None)
    return None if i is None else tdays[i]


def process_b(state, tdays, cut, today, fetch=Y.fetch_chart):
    """写した一覧の翌朝を数える。tdays＝取引のあった日（日付順）、cut＝この日より前だけ使う（場が終わった日）。数えた一覧の数を返す"""
    done = 0
    stopped = state["verdicts"].get("B", {}).get("status") == "stop"
    for asof in sorted(state["lists"]):
        L = state["lists"][asof]
        if L["status"] != "pending":
            continue
        target = next_trading_day(tdays, asof)
        if target is None or target >= cut:
            continue
        if stopped:
            _close_list(L, "skipped_after_stop", target=target)
            continue
        if (dt.date.fromisoformat(today) - dt.date.fromisoformat(target)).days > B_TOO_OLD:
            _close_list(L, "lost", target=target)
            continue
        rows = []
        for code, close in L["items"]:
            d = fetch(code, "1d", "3mo")
            m = fetch(code, "5m", "60d") or fetch(code, "5m", "1mo")
            op = next((o for t, o, h, lo, c, v in d or [] if t.date().isoformat() == target), None)
            bars = sorted(b for b in m or [] if b[0].date().isoformat() == target)
            p930 = Y.price_at(bars, "09:30") if bars else None
            if op and p930 and close:
                r = p930 / op - 1
                if abs(r) <= T.MAX_MOVE:
                    rows.append({"k": stock_key(code), "g": op / close - 1, "r": r})
            time.sleep(0.05)
        n = len(L["items"])
        waited = sum(1 for x in tdays if target < x < cut)
        if n and len(rows) < MIN_COVER_B * n and waited < B_WAIT_DAYS:
            continue                      # 足りない＝次の実行でやり直す
        for x in sorted(rows, key=lambda z: z["k"]):
            state["trades"].append({"c": "B", "d": target, "k": x["k"], "g": round(x["g"], 6), "r": round(x["r"], 6),
                                    "f": int(x["g"] >= GAP_UP)})
        state["days"]["B"][target] = {"asof": asof, "n": n, "got": len(rows)}
        _close_list(L, "done", target=target, got=len(rows))
        done += 1
    return done


# ════════════════════ A：約400銘柄を日足から決め直す ════════════════════

def load_a(codes, meta, end_day, fetch=Y.fetch_chart):
    """→ (高値更新の翌朝の記録, 取れなかった銘柄, {日付: その日に5分足が取れた銘柄の数}, 取引のあった日)"""
    recs, missing, cover, seen = [], [], {}, {}
    for i, code in enumerate(codes):
        d = fetch(code, "1d", DAILY_RANGE)
        m = fetch(code, "5m", "60d") or fetch(code, "5m", "1mo")
        if not d or not m:
            missing.append(code)
            continue
        daily = sorted({t.date().isoformat(): (t.date().isoformat(), o, h, lo, c, v) for t, o, h, lo, c, v in d}.values())
        for day, *_ in daily:
            seen[day] = seen.get(day, 0) + 1
        by5 = T._by_day(m)
        for day in by5:
            cover[day] = cover.get(day, 0) + 1
        ev, _ = T.stock_records(code, daily, by5, {}, akaji=meta.get(code, {}).get("akaji"), end_day=end_day,
                                min_window_start=MIN_WINDOW_START)
        recs += [r for r in ev if r["r930"] is not None]
        if (i + 1) % 100 == 0:
            print(f"  ...{i + 1}/{len(codes)}", flush=True)
        time.sleep(0.05)
    n_ok = len(codes) - len(missing)
    tdays = sorted(d for d, k in seen.items() if n_ok and k >= 0.5 * n_ok)    # 半分以上の銘柄に足がある日＝取引のあった日
    return recs, missing, cover, tdays


def update_a(state, recs, cover, n_ok, cut):
    """まだ数えていない日（FWD_START 以降・cut より前・5分足が取れた割合が MIN_COVER_A 以上）だけを足す。足した日数を返す"""
    if state["verdicts"].get("A", {}).get("status") == "stop" or not n_ok:
        return 0
    by_day = {}
    for r in recs:
        by_day.setdefault(r["date"], []).append(r)
    added = 0
    for day in sorted(d for d in cover if FWD_START <= d < cut and d not in state["days"]["A"]):
        if cover[day] / n_ok < MIN_COVER_A:
            continue
        rows = by_day.get(day, [])
        state["days"]["A"][day] = {"n": len(rows), "cover": round(cover[day] / n_ok, 3)}
        for r in sorted(rows, key=lambda x: x["code"]):
            state["trades"].append({"c": "A", "d": day, "k": stock_key(r["code"]), "g": round(r["gap"], 6),
                                    "r": round(r["r930"], 6), "f": int(r["gap"] >= GAP_UP)})
        added += 1
    return added


# ════════════════════ 判定・まとめ ════════════════════

def _rows(trades):
    return [{"date": t["d"], "code": t["k"], "r": t["r"], "f": t["f"]} for t in trades]


def diff_stats(trades, alpha=ALPHA):
    return T.safe(_rows(trades), lambda r: r["r"], lambda r: bool(r["f"]), alpha=alpha)


def judge(state, goal=GOAL):
    """目印ありが goal 回に届いた組を1回だけ判定して固定する。ストップはその日より後の取引を外す"""
    for arm in ("A", "B"):
        if arm in state["verdicts"]:
            continue
        ts = [t for t in state["trades"] if t["c"] == arm]
        per_day = {}
        for t in ts:
            per_day[t["d"]] = per_day.get(t["d"], 0) + t["f"]
        cum, cut = 0, None
        for d in sorted(per_day):
            cum += per_day[d]
            if cum >= goal:
                cut = d
                break
        if cut is None:
            continue
        st = diff_stats([t for t in ts if t["d"] <= cut])
        ok = st.get("hi") is not None and st["hi"] < 0
        if ok:
            reason = "目印あり−なしの差の95％の幅がまるごと0より下"
        elif (st.get("diff") or 0) >= 0:
            reason = "目印ありのほうが弱くなかった（差が0以上）"
        else:
            reason = "差はマイナスだが、95％の幅が0をまたぐ（罠の目印と言い切れない）"
        state["verdicts"][arm] = {"status": "confirm" if ok else "stop", "decided_on": cut, "n": st.get("n_a"),
                                  "n_all": st.get("n"), "mean": st.get("diff"), "lo": st.get("lo"), "hi": st.get("hi"),
                                  "reason": reason}
        if not ok:
            state["trades"] = [t for t in state["trades"] if not (t["c"] == arm and t["d"] > cut)]


def _mean(xs):
    return sum(xs) / len(xs) if xs else None


def summary(state):
    out = {}
    for arm in ("A", "B"):
        ts = [t for t in state["trades"] if t["c"] == arm]
        a = [t["r"] for t in ts if t["f"]]
        b = [t["r"] for t in ts if not t["f"]]
        days = len(state["days"][arm])
        pace = len(a) / days if days else None
        left = None if not pace or arm in state["verdicts"] else max(0, GOAL - len(a)) / pace
        out[arm] = {"n_a": len(a), "n_b": len(b), "mean_a": _mean(a), "mean_b": _mean(b),
                    "trap_a": _mean([1.0 if x <= T.TRAP else 0.0 for x in a]),
                    "trap_b": _mean([1.0 if x <= T.TRAP else 0.0 for x in b]),
                    "days": days, "per_day": pace, "days_left": left}
    return out


def _pct(x, d=2):
    return "—" if x is None else f"{x * 100:+.{d}f}％"


def _share(x):
    return "—" if x is None else f"{x * 100:.1f}％"


def render_md(state):
    sm = summary(state)
    lists = state["lists"]
    L = ["# J10F 高値更新の翌朝の罠の目印・前向き", "",
         f"更新: {state.get('generated_at', '')}（GitHub Actions）。事前登録＝`{P.PREREG}`「J10F」（指紋 sha256 `{(state.get('prereg_sha256') or '')[:16]}…`）。",
         f"数えるのは **翌朝が {FWD_START} 以降**の取引だけ。値は寄り→9:30 の株価の変化率（費用前・費用後は往復{T.COST * 100:.1f}％を引いた値）。"
         "銘柄名は出しません。**売買の決まりではない**。", "",
         f"- 目印＝窓（寄り ÷ 前日終値 − 1）が **+{GAP_UP * 100:.0f}％ 以上**（J10 の Q1）",
         f"- 判定：組ごとに、**目印ありが {GOAL}回** に届いた日に1回だけ。目印あり−なしの差の95％の幅がまるごと0より下なら「✅ 罠の目印を前向きで確認」、"
         "それ以外は「⏹ ストップ」＝数えるのをやめて `verified-list.md`（検証済みリスト）に載せる", "",
         "| 組 | 数えた日 | 目印あり | 目印なし | 目印ありの平均（費用前→費用後） | 目印なしの平均（費用前→費用後） | 差 | 罠の割合（−1％以下）あり／なし | 状態 |",
         "|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for arm in ("A", "B"):
        s, v = sm[arm], state["verdicts"].get(arm)
        if v:
            st = (f"✅ 罠の目印を前向きで確認（{v['decided_on']}・目印あり{v['n']}回で判定・差 {_pct(v['mean'])}・幅 {_pct(v['lo'])}〜{_pct(v['hi'])}）"
                  if v["status"] == "confirm" else
                  f"⏹ ストップ（{v['decided_on']}・目印あり{v['n']}回で判定）：{v['reason']}")
        else:
            left = s.get("days_left")
            st = f"観察中（目印あり {s['n_a']}/{GOAL}" + (f"・あと約{left:.0f}営業日）" if left is not None else "）")
        cost = lambda x: None if x is None else x - T.COST  # noqa: E731
        d = None if s["mean_a"] is None or s["mean_b"] is None else s["mean_a"] - s["mean_b"]
        L.append(f"| {arm} {'約400銘柄' if arm == 'A' else 'サイトの一覧'} | {s['days']} | {s['n_a']} | {s['n_b']} | "
                 f"{_pct(s['mean_a'])}→{_pct(cost(s['mean_a']))} | {_pct(s['mean_b'])}→{_pct(cost(s['mean_b']))} | {_pct(d)} | "
                 f"{_share(s['trap_a'])}／{_share(s['trap_b'])} | {st} |")
    by_status = {}
    for x in lists.values():
        by_status[x["status"]] = by_status.get(x["status"], 0) + 1
    L += ["", f"- B で写した一覧：{len(lists)}日分（" + "・".join(f"{k} {v}" for k, v in sorted(by_status.items())) + "）"
          if lists else "- B で写した一覧：まだ無い（「JP Highs Lows」の完了で写す）",
          "- 途中の数字は進み具合として出すだけ（判定は目印ありが1000回に届いた日に1回だけ）。実際の約定（寄りの成行・9:30 の値）とはずれる。空売りは数えない。",
          "", "---", "", "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def save(state, md=True):
    state["generated_at"] = dt.datetime.now(P.JST).isoformat(timespec="minutes")
    state["prereg_sha256"] = P.prereg_sha256()
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=0)
    if md:
        with open(OUT_MD, "w", encoding="utf-8") as fh:
            fh.write(render_md(state))


def _read_highs(path=HIGHS):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def main(argv):
    state = load_state()
    state["titles"] = dict(TITLES)
    now = dt.datetime.now(P.JST)
    got = capture(state, _read_highs(), now.isoformat(timespec="minutes"))
    print(f"写した一覧: {got or 'なし（同じ日の一覧はもう写した・または古い）'}")
    if "--capture-only" in argv:
        if got:
            save(state)
        return 0
    info = json.load(open(Y.UNIVERSE, encoding="utf-8"))["stocks"]
    cut = Y.today_cutoff(now)
    end_day = (dt.date.fromisoformat(cut) - dt.timedelta(days=1)).isoformat()
    recs, missing, cover, tdays = load_a(list(info), info, end_day)
    if len(missing) > MAX_MISSING * len(info):
        save(state)                       # 写した一覧だけは残す（数えるのは次の実行で）
        print(f"🚨 値段を取れなかった銘柄が {len(missing)}/{len(info)}＝今回は数えない", file=sys.stderr)
        return 1
    added = update_a(state, recs, cover, len(info) - len(missing), cut)
    done = process_b(state, tdays, cut, now.date().isoformat())
    judge(state)
    save(state)
    print(f"A で足した日: {added}／B で数えた一覧: {done}")
    print(render_md(state))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
