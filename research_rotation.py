# -*- coding: utf-8 -*-
"""
research_rotation.py — 毎日の「1つ入れて、1つ外す」（2026-11-17 オーナー決定・routine signal-lab-daily が毎朝動かす）

オーナー:「1日1回新しい方法を見つけ出して研究として発表して成績の悪いものは一つ消すという形にしていきましょう」。
事前登録＝PILLAR_PREREG.md「毎日の新しい方法と入れ替え（2026-11-17）」。ここの決まりは結果を見る前にコミットした。

■ daily --date D（1日1回・同じ日に2回動かしても2回目は何もしない）＝第2版（PILLAR_PREREG「毎日の新しい方法と入れ替え・第2版」）
  ① 研究中の新しい方法（method-lab-registry.json）の前向きの成績を method-lab.json から写し、
     signal_lab_tracker と同じ決まりで判定する（80回ごとの区切りでだけ判定・昇格は2回続けて＋偽薬との差がプラス・
     却下は1回で決まる・昇格のあと基準割れが2回続いたら戻す・見込みなし〔futility〕も同じ）。
  ② その日に合格した方法を**全部**登録する（method-lab.json の batches[D].registered。過去の確かめ8つを全部通り、
     すでにある方法と売買が7割以上重ならないもの）。前向きは D の日足から数える。
  ③ **登録した数だけ（少なくとも1つ）**、研究中の中で成績のいちばん悪いものから外す（status=retired・retire_reason=culled・戻さない）。
       対象＝signal-lab-tracker.json の採点中（tracking）の仮説 と、その日より前に登録した研究中の新しい方法。
       物差し＝1回あたりの損益の平均（大きいほど良い）:
         新しい方法＝2018年からいままでの平均（登録前の確かめる期間＋登録後の前向き・費用後）
         シグナルの仮説＝登録後の平均（前向き30回以上だけ・避けるはずの仮説は符号を変える）
       外さないもの＝前向き30回未満の仮説・昇格の途中（1回目の合格のあと）・比べる相手と対の登録（pair）・その日に登録したもの。
       同じ点なら回数の多いほう、それも同じなら登録の古いほう。採点中が合わせて20本以下になったら止める。
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
    """その日に合格した方法を全部登録する。→ (登録した ID の並び, 説明)"""
    b = ((lab or {}).get("batches") or {}).get(today)
    if not b:
        return [], "method-lab.json に今日の候補が無い（method-lab.yml がまだ動いていない）"
    regs = b.get("registered") or []
    if not regs:
        return [], "今日の候補はどれも過去の確かめ8つを全部は通らなかった（いちばん惜しかったものは記事で紹介するが、登録しない）"
    have = {m["id"] for m in reg.get("methods", [])}
    out = []
    for ch in regs:
        if ch["id"] in have:
            continue
        reg.setdefault("methods", []).append({
            "id": ch["id"], "name": ch["name"], "spec": ch["spec"], "exit_ja": ch.get("exit_ja"),
            "universe_ja": ch.get("universe_ja"), "conds_ja": ch.get("conds_ja"), "direction": ch["spec"]["direction"],
            "kind": "edge", "source": ch.get("source"), "why": ch.get("why"), "parent": ch.get("parent"),
            "registered_at": today, "status": "tracking",
            "past": {"explore": ch.get("explore"), "confirm": ch.get("confirm")},
            "forward": {"n": 0, "avgR": None, "rci_lo": None, "rci_hi": None},
        })
        out.append(ch["id"])
    return out, f"{len(out)}件を登録した" if out else "登録済み"


# ─────────────────────────── ③ 入れ替え ───────────────────────────
def method_score(m):
    """新しい方法の物差し＝2018年からいままでの1回あたりの平均（登録前の確かめる期間＋登録後の前向き・回数で重みづけ）。"""
    c = ((m.get("past") or {}).get("confirm") or {})
    f = m.get("forward") or {}
    nc, mc = c.get("n") or 0, c.get("mean")
    nf, mf = f.get("n") or 0, f.get("avgR")
    tot = (nc if mc is not None else 0) + (nf if mf is not None else 0)
    if not tot:
        return None, 0
    val = ((nc * mc) if mc is not None else 0) + ((nf * mf) if mf is not None else 0)
    return val / tot, tot


def cull_pool(tracker, reg, today=None):
    pool, active = [], 0
    for h in tracker.get("hypotheses", []):
        if h.get("status") != "tracking":
            continue
        active += 1
        f = h.get("forward") or {}
        if (f.get("n") or 0) < CULL_MIN_N or h.get("promote_strikes") or h.get("pair") or f.get("avgR") is None:
            continue
        sc = f["avgR"] if h.get("kind") != "gate" else -f["avgR"]
        pool.append({"source": "signal", "id": h["id"], "kind": h.get("kind"), "name": T.plain_name(h.get("filter") or {})
                     or h.get("label"), "label": h.get("label"), "registered_at": h.get("registered_at"),
                     "n": f.get("n"), "avgR": f.get("avgR"), "lo": f.get("rci_lo"), "hi": f.get("rci_hi"),
                     "basis": "登録後", "score": round(sc, 4)})
    for m in reg.get("methods", []):
        if m.get("status") != "tracking":
            continue
        active += 1
        if m.get("promote_strikes") or (today and m.get("registered_at") == today):
            continue
        sc, tot = method_score(m)
        if sc is None:
            continue
        f = m.get("forward") or {}
        pool.append({"source": "method", "id": m["id"], "kind": "edge", "name": m["name"], "label": m["name"],
                     "registered_at": m["registered_at"], "n": tot, "avgR": round(sc, 4),
                     "fwd_n": f.get("n") or 0, "fwd_avgR": f.get("avgR"), "basis": "2018年から", "score": round(sc, 4)})
    pool.sort(key=lambda r: (r["score"], -(r["n"] or 0), r["registered_at"] or ""))
    return pool, active


def cull_some(tracker, reg, today, k):
    """成績の悪いものから k 個外す（採点中が20本以下になったら止める）。→ (外した記録の並び, 説明, 外す前の本数)"""
    pool, active = cull_pool(tracker, reg, today)
    if active <= POOL_FLOOR:
        return [], f"採点中が {active} 本（{POOL_FLOOR} 本以下）なので外さない", active
    if not pool:
        return [], "外せる条件を満たすものが無い", active
    out = []
    left = active
    for w0 in pool:
        if len(out) >= k or left <= POOL_FLOOR:
            break
        w = dict(w0)
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
                    left += 1
        else:
            m = next(x for x in reg["methods"] if x["id"] == w["id"])
            m["status"], m["retired_at"], m["retire_reason"] = "retired", today, "culled"
        reg.setdefault("culls", []).append(w)
        out.append(w)
        left -= 1
    msg = f"{len(out)}件を外した" + ("" if len(out) >= k else f"（{k}件の予定のうち・採点中が{POOL_FLOOR}本に届いたので止めた）")
    return out, msg, active


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
    new_ids, reg_msg = register_today(reg, lab, today)
    k = max(1, len(new_ids))
    culls, cull_msg, active = cull_some(tracker, reg, today, k)
    b = ((lab or {}).get("batches") or {}).get(today) or {}
    day = {"lab_asof": lab.get("asof"), "forward_asof": lab.get("forward_asof"), "rules_version": b.get("rules_version"),
           "chosen_id": (b.get("chosen") or {}).get("id"), "chosen_status": (b.get("chosen") or {}).get("status"),
           "registered": new_ids, "register_note": reg_msg,
           "cull_ids": [c["id"] for c in culls], "cull_target": k, "cull_note": cull_msg,
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
    print(f"今日の主役: {ch['name']}（{ch.get('exit_ja')}・{'合格' if ch.get('status') == 'passed' else '惜しかった方法'}）" if ch
          else "今日の主役: なし")
    print(f"登録: {reg_msg}")
    for c in culls:
        print(f"外した: [{c['source']}] {c['name']}（{c['basis']} {c['n']}回・1回あたり平均 {c['avgR']:+.3f}R）"
              + (f" → 逆向きで登録し直した {c['flip_id']}" if c.get("flip_id") else ""))
    if not culls:
        print(f"外した: なし（{cull_msg}）")
    for e, m in events:
        print(f"判定: {m['name']} → {e}")


def cmd_status(args):
    reg = load(REGISTRY, {"methods": []})
    tracker = load(TRACKER, {"hypotheses": []})
    pool, active = cull_pool(tracker, reg)
    print(f"採点中 {active} 本・外せる候補 {len(pool)} 本（悪い順の5つ）")
    for r in pool[:5]:
        print(f"  {r['score']:+.3f} [{r['source']}] {r['name']}（{r['basis']} {r['n']}回）")
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
            "「でたらめに入った場合」は、同じ銘柄・同じ期間・同じ向き・同じ手じまいで、入る日だけを2,000回でたらめに選んだときの平均。</p>"
            + _chart(years_svg(ch.get("by_year")), "緑の棒はその年がもうけ、赤の棒は損。点線より左は方法を探すのに使った年、"
                     "右は探すのに使っていない年（確かめる期間）です。") + "</div>")


# ─────────────── 図（道具が毎日同じ形で作る＝固定の図の検査を必ず通る形） ───────────────
# 2026-11-17 夜 オーナー「今まで通り画像付きで」。検査＝signal_lab_verify（はみ出し・文字の重なり・後から描いた図形）と
# svg_layout_check（線が文字を横切る・塗った図形と文字が一部重なる）とやさしい日本語（R・×・矢印を書かない）。
# 描く順番＝背景 → 補助線（太さ0.8） → 棒 → 文字（文字はいつも最後・棒や線と重ならない場所に置く）。
_BG = 'fill="var(--c-surface,#fff)"'
_MUTED = 'fill="var(--c-muted,#5a6072)"'
_FONT = 'font-family="sans-serif"'


def _svg_open(w, h, label):
    return (f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{E(label)}" '
            f'style="width:100%;max-width:{w}px;display:block;margin:0 auto">'
            f'<rect width="{w}" height="{h}" {_BG} rx="6"/>')


def funnel_svg(c):
    """200通りが、確かめを前から順に通ってどれだけ残ったか（横棒）。"""
    steps = [("試した数", c.get("tried", 0))] + [(name, c.get(key, 0)) for name, key in (
        ("探す期間（多重検定）", "pass_explore"), ("時代", "pass_eras"), ("銘柄の広がり", "pass_instruments"),
        ("隣の値", "pass_neighbors"), ("別の市場", "pass_markets"), ("確かめる期間", "pass_confirm"),
        ("費用2倍", "pass_cost"), ("回数", "pass_frequency"))]
    tried = max([n for _name, n in steps] + [1])            # 0通りの日や数が食い違う日でも棒が枠からはみ出さない
    W, top, row = 640, 44, 26
    H = top + row * len(steps) + 16
    x0, wmax = 200, 360
    out = [_svg_open(W, H, "試した方法が8つの確かめでどれだけ残ったか")]
    bars, texts = [], [f'<text x="{W / 2:g}" y="24" font-size="13" {_FONT} text-anchor="middle" {_MUTED}>'
                       '試した方法が、確かめを前から順に通って残った数</text>']
    for i, (name, n) in enumerate(steps):
        y = top + i * row
        w = 0 if n <= 0 else min(wmax, max(3.0, wmax * n / tried))
        color = "var(--c-accent,#2563eb)" if i == 0 else ("var(--c-green,#16a34a)" if n > 0 else "var(--c-red,#dc2626)")
        if w:
            bars.append(f'<rect x="{x0}" y="{y}" width="{w:.1f}" height="16" fill="{color}" opacity=".8" rx="2"/>')
        texts.append(f'<text x="{x0 - 10}" y="{y + 13}" font-size="12" {_FONT} text-anchor="end" {_MUTED}>{E(name)}</text>')
        texts.append(f'<text x="{x0 + w + 8:.1f}" y="{y + 13}" font-size="12" {_FONT} font-weight="bold" '
                     f'fill="{color}">{n}通り</text>')
    return "".join(out + bars + texts) + "</svg>"


def years_svg(by_year, title="年ごとの1回あたりの損益の平均（損切り幅を1としたときの倍率・費用を引いたあと）"):
    """主役の方法の年ごとの平均（縦棒）。2017年までが探す期間・2018年からが確かめる期間。"""
    ys = sorted((int(y), v[1]) for y, v in (by_year or {}).items() if v and v[1] is not None)
    if not ys:
        return ""
    W, H = 640, 280
    L, Rr, T, B = 64, 624, 56, 236            # 棒を描く枠（左・右・上・下）
    mx = max(abs(v) for _y, v in ys)
    scale = 0.25 if mx <= 0.25 else 0.5 if mx <= 0.5 else 1.0
    zero = (T + B) / 2
    k = (B - T) / 2 / scale

    def yy(v):
        return zero - max(-scale, min(scale, v)) * k
    n = len(ys)
    step = (Rr - L) / n
    bw = max(3.0, step * 0.62)
    lines, bars, texts = [], [], []
    for v in (scale, scale / 2, 0, -scale / 2, -scale):
        lines.append(f'<line x1="{L}" y1="{yy(v):.1f}" x2="{Rr}" y2="{yy(v):.1f}" stroke="var(--c-muted,#bbb)" '
                     f'stroke-width="{0.8 if v else 0.9}"{"" if v == 0 else " stroke-dasharray=\"3,3\""}/>')
        lab = "0" if v == 0 else f"{v:+.2f}".replace("-", "−")
        texts.append(f'<text x="{L - 6}" y="{yy(v) + 4:.1f}" font-size="10" {_FONT} text-anchor="end" {_MUTED}>{lab}</text>')
    split = next((i for i, (y, _v) in enumerate(ys) if y >= 2018), None)
    if split is not None and split > 0:
        xs = L + step * split
        lines.append(f'<line x1="{xs:.1f}" y1="{T}" x2="{xs:.1f}" y2="{B}" stroke="var(--c-muted,#888)" '
                     f'stroke-width="0.8" stroke-dasharray="5,4"/>')
        from signal_lab_verify import _est_text_width as _tw
        left = "探す期間（2017年まで）" if xs - 8 - _tw("探す期間（2017年まで）", 11) > 6 else "探す期間"
        right = "確かめる期間（2018年から）" if xs + 8 + _tw("確かめる期間（2018年から）", 11) < W - 6 else "確かめる期間"
        if xs - 8 - _tw(left, 11) > 6:
            texts.append(f'<text x="{xs - 8:.1f}" y="{T - 8}" font-size="11" {_FONT} text-anchor="end" {_MUTED}>{left}</text>')
        texts.append(f'<text x="{xs + 8:.1f}" y="{T - 8}" font-size="11" {_FONT} {_MUTED}>{right}</text>')
    for i, (y, v) in enumerate(ys):
        x = L + step * i + (step - bw) / 2
        y1, y2 = sorted((yy(v), zero))
        if y2 - y1 >= 0.5:
            color = "var(--c-green,#16a34a)" if v > 0 else "var(--c-red,#dc2626)"
            bars.append(f'<rect x="{x:.1f}" y="{y1:.1f}" width="{bw:.1f}" height="{y2 - y1:.1f}" fill="{color}" opacity=".8" rx="1"/>')
        if (n <= 12 or y % 5 == 0):
            texts.append(f'<text x="{L + step * i + step / 2:.1f}" y="{B + 18}" font-size="10" {_FONT} '
                         f'text-anchor="middle" {_MUTED}>{y}</text>')
    head = f'<text x="{W / 2:g}" y="22" font-size="12" {_FONT} text-anchor="middle" {_MUTED}>{E(title)}</text>'
    clip = (f'<text x="{W / 2:g}" y="{H - 8}" font-size="10" {_FONT} text-anchor="middle" {_MUTED}>'
            f'目盛りの外に出る年は端で止めて描いています</text>') if mx > scale else ""
    return _svg_open(W, H, "年ごとの1回あたりの損益の平均") + "".join(lines + bars + [head] + texts) + clip + "</svg>"


def _chart(svg, note):
    return f'<div class="s-chart">{svg}<p class="s-chart-note">{note}</p></div>' if svg else ""


CHECK_ROWS = [("explore", "探す期間（2017年まで）", "その日に試したもの全部をまとめて見ても、でたらめに入った場合より良いと言える"),
              ("eras", "時代", "2007年まで・2008〜2012年・2013〜2017年に分けても、でたらめより悪い時代は1つまで"),
              ("instruments", "銘柄の広がり", "銘柄ごとに見ても、半分以上の銘柄ででたらめより良い"),
              ("neighbors", "隣の値", "数を1つずつとなりの値に変えても、3分の2以上ででたらめより良い"),
              ("markets", "別の市場", "監視している18銘柄に入っていない似た市場でも、でたらめより良い"),
              ("confirm", "確かめる期間（2018年から）", "探す期間に使っていない年でも、偶然とは言いにくいほど良く、前半と後半の両方で良い"),
              ("cost", "費用2倍", "売り買いの費用を2倍にしても、確かめる期間の平均がもうけ"),
              ("frequency", "回数", "シグナルが1年に40回以上出る（これからの確かめが2年以内に進む）")]


def checks_table(ch):
    """過去の確かめ8つの結果（通った・落ちた）と、その中身の数字。"""
    g = ch.get("gates") or {}
    eras = ch.get("eras") or []
    inst = ch.get("instruments") or {}
    nb = ch.get("neighbors") or {}
    ot = ch.get("others") or {}
    co = ch.get("confirm") or {}
    hv = co.get("halves") or []
    ex = ch.get("explore") or {}
    detail = {
        "explore": f"{ex.get('n', 0)}回・でたらめとの差 {_r((ex.get('placebo') or {}).get('excess'))}",
        "eras": "・".join(f"{e['from'][:4] if e['from'] > '1901' else ''}{'〜' if e['from'] > '1901' else '〜'}{e['to'][:4]}年 "
                         f"{e['n']}回 {_r(e.get('excess'))}" for e in eras),
        "instruments": f"{inst.get('counted', 0)}銘柄のうち{inst.get('positive', 0)}銘柄",
        "neighbors": f"{nb.get('counted', 0)}通りのうち{nb.get('positive', 0)}通り" if nb.get("counted") else "変えられる数なし",
        "markets": (f"{ot.get('markets', 0)}市場で{ot.get('n', 0)}回・でたらめとの差 {_r(ot.get('excess'))}"
                    if (ot.get("n") or 0) >= 30 else f"{ot.get('n', 0)}回（30回未満なので判定なし）"),
        "confirm": (f"{co.get('n', 0)}回・でたらめとの差 {_r((co.get('placebo') or {}).get('excess'))}・"
                    + "・".join(f"{h['from'][:4]}〜{h['to'][:4]}年 {_r(h.get('excess'))}" for h in hv)) if co else "—",
        "cost": f"平均 {_r(co.get('cost2_mean'))}" if co else "—",
        "frequency": f"1年に{co.get('per_year')}回" if co else "—",
    }
    rows = "".join(f"<tr><td>{E(name)}</td><td>{'通った' if g.get(key) else '落ちた' if key in g else '数えていない'}</td>"
                   f"<td>{E(detail[key])}</td><td>{E(why)}</td></tr>" for key, name, why in CHECK_ROWS)
    return ("<div class=\"s-table-wrap\" data-mw-method-snippet=\"checks\"><table class=\"s-table\"><thead><tr><th>確かめ</th>"
            "<th>結果</th><th>数字</th><th>何を見るか</th></tr></thead><tbody>" + rows + "</tbody></table>"
            "<p class=\"s-chart-note\">数字は、損切りまでの幅を1としたときの1回あたりの損益の、でたらめに入った場合との差。"
            "8つ全部を通ったものだけを登録します。</p></div>")


def batch_box(b, totals=None):
    c = b.get("counts") or {}
    src = c.get("by_source") or {}
    steps = [("探す期間", "pass_explore"), ("時代", "pass_eras"), ("銘柄の広がり", "pass_instruments"), ("隣の値", "pass_neighbors"),
             ("別の市場", "pass_markets"), ("確かめる期間", "pass_confirm"), ("費用2倍", "pass_cost"), ("回数", "pass_frequency")]
    funnel = "、".join(f"{name} {c.get(key, 0)}" for name, key in steps)
    regs = b.get("registered") or []
    reg_html = ("<p><b>今日登録した方法</b>：" + "／".join(E(r["name"]) for r in regs) + "</p>") if regs else \
        "<p><b>今日登録した方法</b>：なし（8つ全部を通ったものが無かった）</p>"
    return ("<div class=\"s-note\" data-mw-method-snippet=\"batch\"><p><b>今日ためした数</b>："
            f"{c.get('tried', 0)}通り（考え方の一覧から{src.get('idea', 0)}・研究中の方法などを1か所変えた形から{src.get('mutation', 0)}・"
            f"部品の組み合わせから{src.get('random', 0)}）</p>"
            + _chart(funnel_svg(c), "上から順に確かめを通ったものだけが下へ進みます。1つでも落ちたら、その先には進みません。") +
            f"<p>確かめを前から順に通って残った数：{funnel}。8つ全部を通ったもの {c.get('pass_all', 0)}"
            f"（そのうち、すでにある方法とほぼ同じもの {c.get('duplicates', 0)}）</p>" + reg_html +
            ((f"<p><b>これまでの歩み</b>：試した形 {totals['tried']}通り・登録 {totals['registered']}本・"
              f"外したもの {totals['culled']}本・研究中の新しい方法 {totals['live']}本</p>") if totals else "") +
            "<p class=\"s-chart-note\">たくさん試すほど、偶然よく見えるものが混じります。だから8つの確かめを全部通っても、"
            "登録した日より後のシグナル（前向き）だけで、もう一度確かめます。</p></div>")


def cull_box(day, reg, today):
    ids = day.get("cull_ids") or ([day["cull_id"]] if day.get("cull_id") else [])
    if not ids:
        return (f"<div class=\"s-note\" data-mw-method-snippet=\"cull\"><p><b>今日外した方法</b>：なし"
                f"（{E(day.get('cull_note') or '')}）</p></div>")
    items = []
    for cid in ids:
        w = next((c for c in reversed(reg.get("culls", [])) if c["id"] == cid and c["date"] == today), None) or {}
        kind = "避けるはずの条件" if w.get("kind") == "gate" else "勝ちやすいはずの条件" if w.get("source") == "signal" else "新しい方法"
        basis = ("2018年からの" if w.get("source") == "method" else "登録した日より後のシグナル")
        flip = "前向きでは逆に平均がプラスだったので、逆向き（勝ちやすいはず）として登録し直しました。" if w.get("flip_id") else ""
        items.append(f"<li>{E(w.get('name') or '')}（{kind}・{E((w.get('registered_at') or '')[:10])} 登録）："
                     f"{basis}{w.get('n')}回で、1回あたり平均 {_rw(w.get('avgR'))}。{flip}</li>")
    return ("<div class=\"s-note\" data-mw-method-snippet=\"cull\"><p><b>今日外した方法</b>"
            f"（今日登録した数だけ・少なくとも1つ。研究中の中で、1回あたりの損益の平均が低い順）</p><ol>" + "".join(items) + "</ol></div>")


def research_list(tracker, reg, limit=10):
    pool, active = cull_pool(tracker, reg)
    rows = []
    for m in reg.get("methods", []):
        if m.get("status") in ("tracking", "promoted"):
            f = m.get("forward") or {}
            sc, tot = method_score(m)
            rows.append(("昇格" if m["status"] == "promoted" else "採点中", m["name"], m["registered_at"], f, sc, tot))
    rows.sort(key=lambda r: -(r[4] if r[4] is not None else -9))
    head = ("<div class=\"s-table-wrap\" data-mw-method-snippet=\"list\"><table class=\"s-table\"><thead><tr><th>状態</th>"
            "<th>研究中の新しい方法</th><th>登録</th><th>2018年からの1回あたりの損益の平均</th><th>登録後の回数</th></tr></thead><tbody>")
    body = "".join(f"<tr><td>{s2}</td><td>{E(n)}</td><td>{E(d)}</td><td>{_r(sc)}（{tot}回）</td><td>{f.get('n') or 0}回</td></tr>"
                   for s2, n, d, f, sc, tot in rows[:limit]) or "<tr><td colspan=\"5\">まだありません</td></tr>"
    more = f"（ほかに {len(rows) - limit} 本）" if len(rows) > limit else ""
    worst = "".join(f"<li>{E(r['name'])}（{r['basis']} {r['n']}回・1回あたり平均 {_rw(r['avgR'])}）</li>" for r in pool[:3])
    return (head + body + "</tbody></table>"
            f"<p class=\"s-chart-note\">{more}シグナルが出た場面の条件（仮説）を含めて合わせて {active} 本を採点中。"
            "損益の数字は損切りまでの幅を1としたときの1回あたりの倍率。次に外れる候補（1回あたりの損益の平均が低い順）：</p><ol>" + worst + "</ol></div>")


MARKERS = {"METHOD_RESULT": "result", "METHOD_CHECKS": "checks", "METHOD_BATCH": "batch", "CULL_BOX": "cull",
           "RESEARCH_LIST": "list"}


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
              "checks": checks_table(ch) if ch else "",
              "batch": batch_box(b, {"tried": len(lab.get("tested_ids") or []),
                                     "registered": sum(1 for m in reg.get("methods", [])),
                                     "culled": len(reg.get("culls") or []),
                                     "live": sum(1 for m in reg.get("methods", []) if m.get("status") in ("tracking", "promoted"))}),
              "cull": cull_box(day, reg, today), "list": research_list(tracker, reg)}
    if not args.into:
        for k, v in blocks.items():
            print(f"<!-- {k} -->\n{v}\n")
        return
    path = args.into
    txt = open(path, encoding="utf-8").read()
    if "<!-- MW:METHOD_CHECKS -->" not in txt and "<!-- MW:METHOD_RESULT -->" in txt:
        # 第2版で足した目印。予約の指示（第1版の4つ）どおりに書かれた下書きでも、過去の成績の表のすぐ後ろに置く
        i = txt.index("<!-- MW:METHOD_RESULT -->")
        j = txt.find("<!-- /MW:METHOD_RESULT -->", i)
        at = (j + len("<!-- /MW:METHOD_RESULT -->")) if j >= 0 else (i + len("<!-- MW:METHOD_RESULT -->"))
        txt = txt[:at] + "\n<!-- MW:METHOD_CHECKS -->" + txt[at:]
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
