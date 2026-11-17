# -*- coding: utf-8 -*-
"""
research_rotation.py — 毎日の「1つ入れて、1つ外す」（2026-11-17 オーナー決定・routine signal-lab-daily が毎朝動かす）

オーナー:「1日1回新しい方法を見つけ出して研究として発表して成績の悪いものは一つ消すという形にしていきましょう」。
事前登録＝PILLAR_PREREG.md「毎日の新しい方法と入れ替え（2026-11-17）」。ここの決まりは結果を見る前にコミットした。

■ daily --date D（1日1回・同じ日に2回動かしても2回目は何もしない）
  ① 研究中の新しい方法（method-lab-registry.json）の前向きの成績を method-lab.json から写し、
     signal_lab_tracker と同じ決まりで判定する（80回ごとの区切りでだけ判定・昇格は2回続けて＋偽薬との差がプラス・
     却下は1回で決まる・昇格のあと基準割れが2回続いたら戻す・見込みなし〔futility〕も同じ）。
  ② その日の新しい方法を登録する＝method-lab.json の batches[D].chosen が「合格」のときだけ（惜しかった方法は登録しない）。
     前向きは D の日足から数える（記事が出たあとに決まるシグナルだけ）。
  ③ 研究中の中で、いちばん成績の悪いものを1つ外す（status=retired・retire_reason=culled・戻さない）。
       対象＝signal-lab-tracker.json の採点中（tracking）の仮説 と 研究中（tracking）の新しい方法。
       外せる条件＝前向き30回以上・昇格の途中（1回目の合格のあと）でない・比べる相手と対で登録したもの（pair）でない。
       成績の物差し＝「うまくいった場合の見込み」＝前向きの平均Rの95%の幅の良い側の端
         （勝ちやすいはずの仮説・方法＝上の端／避けるはずの仮説＝下の端の符号を変えたもの）。いちばん低いものを外す
         ＝「回数が十分たまっていて、良く見積もっても良くない」ものから順に外れる（回数が少ないものは幅が広いので外れにくい）。
       同じ点なら回数の多いほう、それも同じなら登録の古いほう。
       採点中が合わせて20本以下のときは外さない（研究が空にならないように）。
       避けるはずの仮説（gate）が、前向きでは逆に平均プラスのまま外れたときは、逆向き（勝ちやすいはず）として登録し直す
         ＝9/26 の決まり①（拾い損ね防止）と同じ・外した日の次の日のシグナルから数える。
  ④ 記録＝method-lab-registry.json の days[D]・culls（記事の数字は method_lab_verify.py がここと突き合わせる）。

■ report --date D --into drafts/draft-signal-lab-NNN.html
  下書きの目印（<!-- MW:METHOD_RESULT --> ／ <!-- MW:METHOD_BATCH --> ／ <!-- MW:CULL_BOX --> ／ <!-- MW:RESEARCH_LIST -->）に
  表と箱を差し込む（何度動かしてもよい）。手で書き写さない。

⚠️ routine・エージェントはこのファイルを編集しない（固定の決まり）。直すのは人（オーナーの承認のあと）。
"""
import argparse
import datetime as dt
import html
import json
import os
import re
import sys

import signal_lab_tracker as T

ROOT = os.path.dirname(os.path.abspath(__file__))
REGISTRY = os.path.join(ROOT, "method-lab-registry.json")
LAB = os.path.join(ROOT, "method-lab.json")
TRACKER = os.path.join(ROOT, "signal-lab-tracker.json")

CULL_MIN_N = 30
POOL_FLOOR = 20
MIN_N = T.PROMOTE_MIN_N            # 80


def load(path, default):
    try:
        return json.load(open(path, encoding="utf-8-sig"))
    except Exception:
        return default


def save(path, obj):
    with open(path, "w", encoding="utf-8", newline="") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def as_fwd(st):
    """method-lab の数字（mean/lo/hi）を tracker の形（avgR/rci_lo/rci_hi）にそろえる。"""
    st = st or {}
    return {"n": st.get("n") or 0, "avgR": st.get("mean"), "rci_lo": st.get("lo"), "rci_hi": st.get("hi"),
            "win": st.get("win"), "excess": st.get("excess")}


# ─────────────────────────── ① 判定 ───────────────────────────
def judge_methods(reg, lab, today):
    events = []
    fwd_all = (lab or {}).get("forward") or {}
    for m in reg.get("methods", []):
        if m.get("status") not in ("tracking", "promoted"):
            continue
        st = fwd_all.get(m["id"])
        if st is None:
            continue
        fwd = as_fwd(st)
        m["forward"] = fwd
        m.setdefault("history", []).append({"date": today, "n": fwd["n"], "avgR": fwd["avgR"], "lo": fwd["rci_lo"]})
        m["history"] = m["history"][-120:]
        if not fwd["n"] or fwd["rci_lo"] is None:
            continue
        next_cp = ((m.get("last_eval_n", 0) // MIN_N) + 1) * MIN_N
        if fwd["n"] < next_cp:
            pass
        elif m["status"] == "promoted":
            m["last_eval_n"] = fwd["n"]
            if T.judge("edge", fwd) == "promoted" and (fwd["excess"] or 0) > 0:
                m["demote_strikes"] = 0
            else:
                m["demote_strikes"] = m.get("demote_strikes", 0) + 1
                if m["demote_strikes"] >= 2:
                    m["status"], m["demoted_at"], m["demote_strikes"] = "tracking", today, 0
                    events.append(("demoted", m))
            continue
        else:
            m["last_eval_n"] = fwd["n"]
            v = T.judge("edge", fwd)
            if v == "rejected":
                m["status"], m["rejected_at"] = "rejected", today
                events.append(("rejected", m))
                continue
            if v == "promoted" and (fwd["excess"] or 0) > 0:
                m["promote_strikes"] = m.get("promote_strikes", 0) + 1
                if m["promote_strikes"] >= 2:
                    m["status"], m["promoted_at"], m["promote_strikes"] = "promoted", today, 0
                    events.append(("promoted", m))
                    continue
            else:
                m["promote_strikes"] = 0
        if m["status"] == "tracking":
            why = T.futility({"kind": "edge", "registered_at": m["registered_at"],
                              "promote_strikes": m.get("promote_strikes")}, fwd, today)
            if why:
                m["status"], m["retired_at"], m["retire_reason"] = "retired", today, why
                events.append(("retired", m))
    return events


# ─────────────────────────── ② 登録 ───────────────────────────
def register_today(reg, lab, today):
    b = ((lab or {}).get("batches") or {}).get(today)
    if not b:
        return None, "method-lab.json に今日の候補が無い（method-lab.yml がまだ動いていない）"
    ch = b.get("chosen")
    if not ch:
        return None, "今日の候補が1つも数えられなかった"
    if ch.get("status") != "passed":
        return None, "今日の候補はどれも合格しなかった（いちばん惜しかったものは記事で紹介するが、前向きには進めない）"
    if any(m["id"] == ch["id"] for m in reg.get("methods", [])):
        return ch["id"], "登録済み"
    reg.setdefault("methods", []).append({
        "id": ch["id"], "name": ch["name"], "spec": ch["spec"], "exit_ja": ch.get("exit_ja"),
        "universe_ja": ch.get("universe_ja"), "conds_ja": ch.get("conds_ja"), "direction": ch["spec"]["direction"],
        "kind": "edge", "source": ch.get("source"), "why": ch.get("why"), "parent": ch.get("parent"),
        "registered_at": today, "status": "tracking",
        "past": {"explore": ch.get("explore"), "confirm": ch.get("confirm")},
        "forward": {"n": 0, "avgR": None, "rci_lo": None, "rci_hi": None},
    })
    return ch["id"], "登録した"


# ─────────────────────────── ③ 入れ替え ───────────────────────────
def score_of(kind, fwd):
    """うまくいった場合の見込み（大きいほど良い）。"""
    if kind == "gate":
        return None if fwd.get("rci_lo") is None else -fwd["rci_lo"]
    return fwd.get("rci_hi")


def cull_pool(tracker, reg):
    pool, active = [], 0
    for h in tracker.get("hypotheses", []):
        if h.get("status") != "tracking":
            continue
        active += 1
        f = h.get("forward") or {}
        if (f.get("n") or 0) < CULL_MIN_N or h.get("promote_strikes") or h.get("pair"):
            continue
        s = score_of(h.get("kind"), f)
        if s is None:
            continue
        pool.append({"source": "signal", "id": h["id"], "kind": h.get("kind"), "name": T.plain_name(h.get("filter") or {})
                     or h.get("label"), "label": h.get("label"), "registered_at": h.get("registered_at"),
                     "n": f.get("n"), "avgR": f.get("avgR"), "lo": f.get("rci_lo"), "hi": f.get("rci_hi"), "score": round(s, 4)})
    for m in reg.get("methods", []):
        if m.get("status") != "tracking":
            continue
        active += 1
        f = m.get("forward") or {}
        if (f.get("n") or 0) < CULL_MIN_N or m.get("promote_strikes"):
            continue
        s = score_of("edge", f)
        if s is None:
            continue
        pool.append({"source": "method", "id": m["id"], "kind": "edge", "name": m["name"], "label": m["name"],
                     "registered_at": m["registered_at"], "n": f.get("n"), "avgR": f.get("avgR"),
                     "lo": f.get("rci_lo"), "hi": f.get("rci_hi"), "score": round(s, 4)})
    pool.sort(key=lambda r: (r["score"], -(r["n"] or 0), r["registered_at"] or ""))
    return pool, active


def cull_one(tracker, reg, today):
    pool, active = cull_pool(tracker, reg)
    if active <= POOL_FLOOR:
        return None, f"採点中が {active} 本（{POOL_FLOOR} 本以下）なので外さない", active
    if not pool:
        return None, f"外せる条件（前向き{CULL_MIN_N}回以上など）を満たすものが無い", active
    w = dict(pool[0])
    w.update({"date": today, "pool_size": len(pool), "active_before": active})
    if w["source"] == "signal":
        h = next(x for x in tracker["hypotheses"] if x["id"] == w["id"])
        h["status"], h["retired_at"], h["retire_reason"] = "retired", today, "culled"
        if h.get("kind") == "gate" and (w.get("avgR") or 0) > 0:
            fl = T.make_flip(h, h.get("forward") or {}, today)
            if fl["id"] not in {x["id"] for x in tracker["hypotheses"]}:
                empty = T.stats([], fl["filter"])            # 次の朝の update で数え直される（それまでの表示用）
                fl.update({"status": "tracking", "forward": empty, "alltime": dict(empty), "history": [],
                           "baseline": {"filter": {}, "n": 0, "avgR": 0.0, "excess": None}})
                tracker["hypotheses"].append(fl)
                w["flip_id"] = fl["id"]
    else:
        m = next(x for x in reg["methods"] if x["id"] == w["id"])
        m["status"], m["retired_at"], m["retire_reason"] = "retired", today, "culled"
    reg.setdefault("culls", []).append(w)
    return w, "外した", active


def cmd_daily(args):
    today = args.date
    reg = load(REGISTRY, {"methods": [], "culls": [], "days": {}})
    reg.setdefault("days", {})
    if today in reg["days"] and not args.force:
        print(f"{today} はもう動かした:")
        print(json.dumps(reg["days"][today], ensure_ascii=False, indent=1))
        return
    lab = load(LAB, {})
    tracker = load(TRACKER, None)
    if tracker is None:
        print("❌ signal-lab-tracker.json が読めない")
        sys.exit(1)
    events = judge_methods(reg, lab, today)
    new_id, reg_msg = register_today(reg, lab, today)
    cull, cull_msg, active = cull_one(tracker, reg, today)
    b = ((lab or {}).get("batches") or {}).get(today) or {}
    day = {"lab_asof": lab.get("asof"), "forward_asof": lab.get("forward_asof"),
           "chosen_id": (b.get("chosen") or {}).get("id"), "chosen_status": (b.get("chosen") or {}).get("status"),
           "registered": new_id if reg_msg == "登録した" else None, "register_note": reg_msg,
           "cull_id": cull["id"] if cull else None, "cull_note": cull_msg,
           "events": [{"event": e, "id": m["id"], "name": m["name"]} for e, m in events],
           "active_before": active}
    reg["days"][today] = day
    reg["updated_at"] = today
    if args.dry_run:
        print("（試しに動かしただけ・保存しない）")
    else:
        save(REGISTRY, reg)
        T.save_tracker(tracker)
    print(f"=== {today} の入れ替え ===")
    ch = b.get("chosen")
    if ch:
        print(f"今日の新しい方法: {ch['name']}（{ch.get('exit_ja')}）→ {reg_msg}")
    else:
        print(f"今日の新しい方法: なし → {reg_msg}")
    if cull:
        print(f"外したもの: [{cull['source']}] {cull['name']}（前向き {cull['n']}回・平均 {cull['avgR']:+.3f}R・"
              f"良い側の端 {cull['score']:+.3f}）" + (f" → 逆向きで登録し直した {cull['flip_id']}" if cull.get("flip_id") else ""))
    else:
        print(f"外したもの: なし（{cull_msg}）")
    for e, m in events:
        print(f"判定: {m['name']} → {e}")


def cmd_status(args):
    reg = load(REGISTRY, {"methods": []})
    tracker = load(TRACKER, {"hypotheses": []})
    pool, active = cull_pool(tracker, reg)
    print(f"採点中 {active} 本・外せる候補 {len(pool)} 本（悪い順の5つ）")
    for r in pool[:5]:
        print(f"  {r['score']:+.3f} [{r['source']}] {r['name']}（n={r['n']}・平均 {r['avgR']:+.3f}R）")
    for m in reg.get("methods", []):
        f = m.get("forward") or {}
        print(f"  [{m['status']}] {m['id']} {m['name']} 登録 {m['registered_at']} 前向き n={f.get('n')} 平均 {f.get('avgR')}")


# ─────────────────────────── report（下書きへの差し込み） ───────────────────────────
def E(s):
    """表と箱に出す文字。やさしい日本語の検査（固定）で止まる英字はここで言い換える（routine は直せないため）。"""
    for a, b in (("ADX", "トレンドの強さの指標"),):
        s = str(s).replace(a, b)
    return html.escape(s)


def _r(v, d=2):
    """表の中の損益（損切り幅の何倍か）。やさしい日本語の決まりで「R」は書かない。"""
    return "—" if v is None else f"{v:+.{d}f}".replace("-", "−")


def _rw(v):
    """文の中の損益：「損切り幅の0.17倍の損」「損切り幅の0.20倍のもうけ」。"""
    if v is None:
        return "—"
    if round(v, 2) == 0:
        return "ほぼ0（もうけも損もない）"
    return f"損切り幅の{abs(v):.2f}倍の{'もうけ' if v > 0 else '損'}"


def _p(v):
    return "—" if v is None else f"{100 * v:.1f}%"


def result_table(ch):
    rows = []
    for key, label in (("explore", "探す期間"), ("confirm", "確かめる期間")):
        s = ch.get(key) or {}
        pl = s.get("placebo") or {}
        span = f"{(s.get('from') or '')[:4]}〜2017年" if key == "explore" else f"2018年〜{(s.get('to') or '')[:7].replace('-', '年')}月"
        rows.append(f"<tr><td>{label}<br><small>{E(span)}</small></td><td>{s.get('n', 0)}回</td><td>{_r(s.get('mean'))}</td>"
                    f"<td>{_r(s.get('lo'))}〜{_r(s.get('hi'))}</td><td>{_p(s.get('win'))}</td>"
                    f"<td>{_r(pl.get('mean'))}</td><td>{_r(pl.get('excess'))}</td></tr>")
    return ("<div class=\"s-table-wrap\" data-mw-method-snippet=\"result\"><table class=\"s-table\">"
            "<thead><tr><th>期間</th><th>回数</th><th>1回あたりの損益の平均</th><th>95%の幅</th><th>もうけで終わった割合</th>"
            "<th>でたらめに入った場合の平均</th><th>でたらめとの差</th></tr></thead><tbody>" + "".join(rows) +
            "</tbody></table><p class=\"s-chart-note\">損益の数字は、損切りまでの幅（ATR（ふだんの1日の値動きの幅）の1.5倍）を1としたとき、"
            "1回あたり何倍のもうけ（プラス）か損（マイナス）か。費用（スプレッド）を引いたあと。"
            "「でたらめに入った場合」は、同じ銘柄・同じ期間・同じ向き・同じ手じまいで、入る日だけを2,000回でたらめに選んだときの平均。</p></div>")


def batch_box(b):
    c = b.get("counts") or {}
    src = c.get("by_source") or {}
    return ("<div class=\"s-note\" data-mw-method-snippet=\"batch\"><p><b>今日ためした数</b>："
            f"{c.get('tried', 0)}通り（考え方の一覧から{src.get('idea', 0)}・研究中の方法を1か所変えた形から{src.get('mutation', 0)}・"
            f"部品の組み合わせから{src.get('random', 0)}）</p>"
            f"<p>探す期間の条件を満たした {c.get('pass_explore', 0)} ／ 確かめる期間の条件を満たした {c.get('pass_confirm', 0)} ／ "
            f"回数の条件を満たした {c.get('pass_frequency', 0)} ／ <b>すべて満たした {c.get('pass_all', 0)}</b></p>"
            "<p class=\"s-chart-note\">たくさん試すほど、偶然よく見えるものが混じります。だから合格しても、登録した日より後のシグナル（前向き）"
            "だけで、もう一度確かめます。</p></div>")


def cull_box(day, reg, today):
    cid = day.get("cull_id")
    if not cid:
        return (f"<div class=\"s-note\" data-mw-method-snippet=\"cull\"><p><b>今日外した方法</b>：なし"
                f"（{E(day.get('cull_note') or '')}）</p></div>")
    w = next((c for c in reversed(reg.get("culls", [])) if c["id"] == cid and c["date"] == today), None) or {}
    kind = "避けるはずの条件" if w.get("kind") == "gate" else "勝ちやすいはずの条件" if w.get("source") == "signal" else "新しい方法"
    flip = (f"<p>前向きでは逆に平均がプラスだったので、逆向き（勝ちやすいはず）として登録し直しました。</p>" if w.get("flip_id") else "")
    return ("<div class=\"s-note\" data-mw-method-snippet=\"cull\"><p><b>今日外した方法</b>："
            f"{E(w.get('name') or '')}（{kind}・{E((w.get('registered_at') or '')[:10])} 登録）</p>"
            f"<p>登録した日より後のシグナル {w.get('n')}回で、1回あたり平均 {_rw(w.get('avgR'))}"
            f"（95%の幅は {_r(w.get('lo'))}から{_r(w.get('hi'))}）。外せる {w.get('pool_size')}本の中で、"
            "良く見積もった場合の見込みがいちばん低いものでした。</p>" + flip + "</div>")


def research_list(tracker, reg, limit=10):
    pool, active = cull_pool(tracker, reg)
    rows = []
    for m in reg.get("methods", []):
        if m.get("status") in ("tracking", "promoted"):
            f = m.get("forward") or {}
            rows.append(("✅昇格" if m["status"] == "promoted" else "🟡採点中", m["name"], m["registered_at"], f))
    head = ("<div class=\"s-table-wrap\" data-mw-method-snippet=\"list\"><table class=\"s-table\"><thead><tr><th>状態</th>"
            "<th>研究中の新しい方法</th><th>登録</th><th>前向きの回数</th><th>1回あたりの損益の平均</th></tr></thead><tbody>")
    body = "".join(f"<tr><td>{s}</td><td>{E(n)}</td><td>{E(d)}</td><td>{f.get('n') or 0}回</td><td>{_r(f.get('avgR'))}</td></tr>"
                   for s, n, d, f in rows) or "<tr><td colspan=\"5\">まだありません</td></tr>"
    worst = "".join(f"<li>{E(r['name'])}（前向き {r['n']}回・1回あたり平均 {_rw(r['avgR'])}）</li>" for r in pool[:3])
    return (head + body + "</tbody></table>"
            f"<p class=\"s-chart-note\">ほかに、シグナルが出た場面の条件（仮説）を含めて合わせて {active} 本を採点中。"
            "損益の数字は損切りまでの幅を1としたときの1回あたりの倍率。次に外れる候補（良く見積もった見込みが低い順）：</p><ol>" + worst + "</ol></div>")


MARKERS = {"METHOD_RESULT": "result", "METHOD_BATCH": "batch", "CULL_BOX": "cull", "RESEARCH_LIST": "list"}


def cmd_report(args):
    today = args.date
    reg = load(REGISTRY, {"methods": [], "days": {}})
    lab = load(LAB, {})
    tracker = load(TRACKER, {"hypotheses": []})
    day = (reg.get("days") or {}).get(today)
    b = ((lab.get("batches") or {}).get(today)) or {}
    if day is None:
        print(f"❌ {today} の daily がまだ（先に python research_rotation.py daily --date {today}）")
        sys.exit(1)
    ch = b.get("chosen") or {}
    blocks = {"result": result_table(ch) if ch else "<p>今日は数えられた候補がありませんでした。</p>",
              "batch": batch_box(b), "cull": cull_box(day, reg, today), "list": research_list(tracker, reg)}
    if not args.into:
        for k, v in blocks.items():
            print(f"<!-- {k} -->\n{v}\n")
        return
    path = args.into
    txt = open(path, encoding="utf-8").read()
    for mk, key in MARKERS.items():
        start, end = f"<!-- MW:{mk} -->", f"<!-- /MW:{mk} -->"
        new = f"{start}\n{blocks[key]}\n{end}"
        pat = re.compile(re.escape(start) + r"(?:.*?" + re.escape(end) + r")?", re.S)
        if pat.search(txt):
            txt = pat.sub(lambda _m: new, txt, count=1)
    open(path, "w", encoding="utf-8").write(txt)
    print(f"差し込んだ: {path}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("daily")
    d.add_argument("--date", required=True)
    d.add_argument("--force", action="store_true")
    d.add_argument("--dry-run", action="store_true")
    s = sub.add_parser("status")
    r = sub.add_parser("report")
    r.add_argument("--date", required=True)
    r.add_argument("--into")
    args = ap.parse_args()
    {"daily": cmd_daily, "status": cmd_status, "report": cmd_report}[args.cmd](args)


if __name__ == "__main__":
    main()
