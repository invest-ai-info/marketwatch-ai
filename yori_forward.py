# -*- coding: utf-8 -*-
"""J4F 寄り付きの前向き（2026-09-28 夕登録・オーナー「前向きに数える仕組みを作って進めてください。検証結果が1000回を
超えて期待値がプラスにならないようだったら検証はストップして検証済みリストに追加していってください」）。

J4（yori_lab.py）の結果から売買の形にした4つ（F1〜F4）を、登録の翌日（FWD_START）以降の取引だけで数える。
値の決め方・前の日の上位20は yori_lab.py をそのまま使う（寄り＝日足の始値／9:15＝9:10 の足の終値／大引け＝日足の終値）。

⚠️ 決まりは PILLAR_PREREG.md「J4F」と下の定数に固定。結果を見てから動かさない。
⚠️ 1日は一度数えたら固定（Yahoo の値が後から変わっても数え直さない）。判定は1000回に届いた日に1回だけ。
⚠️ 出力（yori-forward.json / .md）は集計だけ・銘柄名なし（銘柄は見分けるための符号だけ）。GitHub 側で生成＝手元から送らない（SYNC禁忌）。
   古い版で上書きすると積み上げた取引と判定が消える。
⚠️ メール・エンジン・売買の決まりには触れない。

実行: python yori_forward.py   （Actions の yori-forward.yml から。そのあと verified_list.py）
"""
import datetime as dt
import hashlib
import json
import sys

import pillar_lab as P
import yori_lab as Y

FWD_START = "2026-09-29"          # この日以降の取引だけ（J4 は 9/28 までを見た）
GOAL = 1000                       # オーナーの決まり：1000回に届いた日に判定
MIN_COVER = 0.95                  # その日に5分足が取れた銘柄がユニバースのこの割合未満なら、その日は数えない（次の実行でやり直す）
MAX_MISSING = 0.02                # 値段を取れなかった銘柄がこの割合を超えた実行は、何も書き換えずに失敗させる
PREV_BIG = 0.05                   # F4 前の日に+5％以上（yori_lab.prev_band の「+5％以上」と同じ）
OUT_JSON, OUT_MD = "yori-forward.json", "yori-forward.md"

J4G_START = "2026-10-06"          # 🆕 J4G（9:30 で手仕舞う版・F5〜F7）はこの日以降の取引だけ（PILLAR_PREREG.md「J4G」）
CANDS = {
    "F1": {"title": "前の日の上位20を寄りで買い、9:15 で手仕舞う", "entry": "open", "exit": "09:15"},
    "F2": {"title": "窓+3％以上で寄った上位を寄りで買い、9:15 で手仕舞う", "entry": "open", "exit": "09:15"},
    "F3": {"title": "9:15 に急騰（寄りから+2％以上）している上位を 9:15 で買い、大引けで手仕舞う", "entry": "09:15", "exit": "15:30"},
    "F4": {"title": "前の日に+5％以上上げ、9:15 に急騰している上位を 9:15 で買い、大引けで手仕舞う", "entry": "09:15", "exit": "15:30"},
    # 🆕 2026-10-05 J4G＝オーナーの取引時間（9:00〜9:30）に収まる版。F1〜F4 の数え方と判定は変えない
    "F5": {"title": "前の日の上位20を寄りで買い、9:30 で手仕舞う", "entry": "open", "exit": "09:30", "from": J4G_START},
    "F6": {"title": "窓+3％以上で寄った上位を寄りで買い、9:30 で手仕舞う", "entry": "open", "exit": "09:30", "from": J4G_START},
    "F7": {"title": "9:15 に急騰（寄りから+2％以上）している上位を 9:15 で買い、9:30 で手仕舞う", "entry": "09:15", "exit": "09:30",
           "from": J4G_START},
}


def cand_from(cid):
    """その候補を数え始める日（F1〜F4＝FWD_START／F5〜F7＝J4G_START）"""
    return CANDS[cid].get("from", FWD_START)


def qualifies(cid, r):
    if not r.get("hot"):
        return False
    if cid in ("F1", "F5"):
        return True
    if cid in ("F2", "F6"):
        return r["gap"] >= Y.GAP_BIG
    if cid in ("F3", "F7"):
        return r["cls"] == "up"
    if cid == "F4":
        return r["cls"] == "up" and r.get("prev_ret") is not None and r["prev_ret"] >= PREV_BIG
    raise KeyError(cid)


def trade_return(cid, r):
    """費用後の損益率（手仕舞いの値 ÷ 入った値 − 1 − 往復の費用）。値が無ければ None"""
    c = CANDS[cid]
    g = Y.ret(r, c["entry"], c["exit"])
    return None if g is None else g - Y.COST


def stock_key(code):
    return hashlib.sha256(str(code).encode()).hexdigest()[:8]


def empty_state():
    return {"fwd_start": FWD_START, "goal": GOAL, "titles": {k: v["title"] for k, v in CANDS.items()},
            "trades": [], "days": {}, "verdicts": {}}


def update(state, recs, cover, today):
    """recs＝yori_lab.load_all の記録、cover＝{日付: その日に5分足が取れた銘柄の割合}。
    まだ数えていない日（FWD_START 以降・today より前・取れた割合が MIN_COVER 以上）だけを足す。足した日数を返す"""
    stopped = {c for c, v in state["verdicts"].items() if v["status"] == "stop"}
    by_day = {}
    for r in recs:
        if FWD_START <= r["date"] < today and r["date"] not in state["days"]:
            by_day.setdefault(r["date"], []).append(r)
    added = 0
    for day in sorted(by_day):
        if cover.get(day, 0) < MIN_COVER:
            continue
        rows = by_day[day]
        state["days"][day] = {"hot": sum(1 for r in rows if r["hot"]), "cover": round(cover[day], 3)}
        for r in sorted(rows, key=lambda x: x["code"]):
            for cid in CANDS:
                if cid in stopped or day < cand_from(cid) or not qualifies(cid, r):
                    continue
                v = trade_return(cid, r)
                if v is not None:
                    state["trades"].append({"c": cid, "d": day, "k": stock_key(r["code"]), "r": round(v, 6)})
        added += 1
    return added


def stats(trades):
    if not trades:
        return {"n": 0}
    return P.mean_ci([t["r"] for t in trades], [(t["k"], t["d"]) for t in trades])


def judge(state):
    """1000回に届いた候補を1回だけ判定して固定する。ストップはその日より後の取引を外す"""
    for cid in CANDS:
        if cid in state["verdicts"]:
            continue
        ts = [t for t in state["trades"] if t["c"] == cid]
        if len(ts) < GOAL:
            continue
        per_day = {}
        for t in ts:
            per_day[t["d"]] = per_day.get(t["d"], 0) + 1
        cum, cut = 0, None
        for d in sorted(per_day):
            cum += per_day[d]
            if cum >= GOAL:
                cut = d
                break
        use = [t for t in ts if t["d"] <= cut]
        st = stats(use)
        plus = st.get("lo") is not None and st["lo"] > 0
        if plus:
            reason = "費用後の平均の95％の幅がまるごと0より上"
        elif (st.get("mean") or 0) <= 0:
            reason = "費用後の平均がマイナス"
        else:
            reason = "費用後の平均はプラスだが、95％の幅が0をまたぐ（プラスと言い切れない）"
        state["verdicts"][cid] = {"status": "plus" if plus else "stop", "decided_on": cut, "n": st["n"],
                                  "mean": st.get("mean"), "lo": st.get("lo"), "hi": st.get("hi"), "reason": reason}
        if not plus:
            state["trades"] = [t for t in state["trades"] if not (t["c"] == cid and t["d"] > cut)]


def summary(state):
    days = sorted(state["days"])
    out = {}
    for cid in CANDS:
        ts = [t for t in state["trades"] if t["c"] == cid]
        st = stats(ts)
        my_days = [d for d in days if d >= cand_from(cid)]
        pace = len(ts) / len(my_days) if my_days else None
        left = None if not pace or cid in state["verdicts"] else max(0, GOAL - len(ts)) / pace
        out[cid] = dict(st, per_day=pace, days_left=left)
    return out


def _pct(x, d=2):
    return "—" if x is None else f"{x * 100:+.{d}f}％"


def render_md(state):
    days = sorted(state["days"])
    sm = summary(state)
    L = ["# J4F 寄り付きの前向き（前の日に出来高が急増した銘柄）", "",
         f"更新: {state.get('generated_at', '')}（GitHub Actions）。事前登録＝`{P.PREREG}`「J4F」（指紋 sha256 `{(state.get('prereg_sha256') or '')[:16]}…`）。",
         f"数えるのは **{FWD_START} 以降**の取引だけ（9:30 で手仕舞う F5〜F7＝J4G は **{J4G_START} 以降**）。1回の損益は費用（往復{Y.COST * 100:.1f}％）を引いた値。銘柄名は出しません。**売買の決まりではない**。", "",
         f"- 数えた日：{len(days)}日" + (f"（{days[0]}〜{days[-1]}）" if days else "（まだ無い）"),
         f"- 判定：取引が **{GOAL}回** に届いた日に1回だけ。費用後の平均の95％の幅がまるごと0より上なら「✅ プラスを確認」、"
         "それ以外は「⏹ ストップ」＝数えるのをやめて `verified-list.md`（検証済みリスト）に載せる", "",
         "| | 決まり | 回数 | 平均（費用後） | 95％の幅 | 状態 |", "|---|---|---:|---:|---|---|"]
    for cid, c in CANDS.items():
        s, v = sm[cid], state["verdicts"].get(cid)
        if v:
            st = (f"✅ プラスを確認（{v['decided_on']}・{v['n']}回で判定）" if v["status"] == "plus"
                  else f"⏹ ストップ（{v['decided_on']}・{v['n']}回で判定）：{v['reason']}")
        else:
            left = s.get("days_left")
            st = f"観察中（{s.get('n', 0)}/{GOAL}" + (f"・あと約{left:.0f}営業日）" if left is not None else "）")
        L.append(f"| {cid} | {c['title']} | {s.get('n', 0)} | {_pct(s.get('mean'))} | "
                 f"{_pct(s.get('lo'))}〜{_pct(s.get('hi'))} | {st} |")
    thin = [d for d in days if state["days"][d]["hot"] < 15]
    L += ["", f"- 上位の記録が15件未満だった日：{len(thin)}日" + (f"（{'・'.join(thin[-5:])}）" if thin else ""),
          "- 途中の数字は進み具合として出すだけ（1000回より前には判定しない）。実際の約定（寄りの成行・9:15 の値）とはずれる。空売りは数えない。",
          "", "---", "", "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def load_state(path=OUT_JSON):
    """記録が無ければ空から始める。壊れている・登録日が違うときは止める（空で上書きすると積み上げた取引が消えるため）"""
    try:
        with open(path, encoding="utf-8") as fh:
            st = json.load(fh)
    except FileNotFoundError:
        return empty_state()
    if st.get("fwd_start") != FWD_START:
        raise SystemExit(f"🚨 {path} の登録日 {st.get('fwd_start')} が {FWD_START} と違う＝上書きしない")
    return st


def main():
    state = load_state()
    state["titles"] = {k: v["title"] for k, v in CANDS.items()}      # 🆕 候補を足したとき（J4G）に検証済みリストへ載るように
    info = json.load(open(Y.UNIVERSE, encoding="utf-8"))["stocks"]
    today = dt.datetime.now(P.JST).date().isoformat()
    diag = {}
    recs, missing = Y.load_all(list(info), info, today, diag=diag)
    if len(missing) > MAX_MISSING * len(info):
        print(f"🚨 値段を取れなかった銘柄が {len(missing)}/{len(info)}＝上位20の顔ぶれが変わるので何も書き換えない", file=sys.stderr)
        return 1
    n_ok = len(info) - len(missing)
    cover = {d: k / n_ok for d, k in diag.get("stocks_with_5m_by_date", {}).items()} if n_ok else {}
    added = update(state, recs, cover, today)
    judge(state)
    state["generated_at"] = dt.datetime.now(P.JST).isoformat(timespec="minutes")
    state["prereg_sha256"] = P.prereg_sha256()
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=0)
    md = render_md(state)
    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write(md)
    print(f"足した日: {added}")
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
