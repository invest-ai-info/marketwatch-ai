# -*- coding: utf-8 -*-
"""いま検証中のこと（研究の地図）— 動いている検証を1か所にまとめる。2026-09-26 新設。

オーナーの言葉:「検証する内容が増えてきて把握できなくなってきたので、今動いている検証内容をまとめてほしい。
シグナル成績のところに置いてもらえますか。読者も何をしているのか分かりやすいと思うので」。

⚠️ 手で書く一覧は必ず古くなる＝**データから毎回組み立てる**（新しい検証を登録すれば自動で加わり、終われば
   「終わった検証」へ移る）。読むだけでデータは書き換えない。
読むもの（無ければその節を飛ばす＝ページ全体は落とさない）:
  signal-lab-tracker.json            … 前向きに追っている仮説（エッジ番付と同じもの）
  signal_lab_tracker.py の REGISTER_* … 登録したがまだトラッカーの集計に入っていない仮説（翌朝の集計から入る）
  exit-lab.json / exit-lab-hypotheses.json … 出口の相性ラボの前向きの確認
  exit-wall-lab.json / stop-lab.json  … 出口の壁ラボ・損切りラボの前向きの確認
  signal-env-profile-history.json     … 相場の環境の統計（毎月）
  🆕 2026-10-01 オーナー「今進めている研究はすべて…研究中一覧、検証中一覧に簡潔に短くまとめて」＝先頭の「📋 研究中・検証中の一覧」:
  yori-forward.json / combo-forward.json / auto-forward.json / calendar-forward.json / highs-trap-forward.json / gap-forward.json / prevgap-forward.json / market-dip-forward.json … 前向きの検証（判定が出たら一覧から外れる）
  ⚠️ 自動で建てる検証（auto-forward）は ea_ledger.py の PAUSED_SINCE が入っているあいだは出さない（2026-10-05〜・止めている検証を「検証中」と見せない）
  yutai-edinet/                       … 株主優待のデータ集め（研究中）
  ⚠️ 個人の取引の記録（守りの見張り番・5分足の執行・取引の記録）と research/ だけの研究は載せない（件数も出さない）

使い方:
  python research_map.py            # 一覧を文字で表示（セッションでの確認用）
  generate_track_record_page.py が build_pane() を呼んで track-record.html の「🗺️ いま検証中のこと」タブにする
  （track-record.html#map で直接そのタブが開く）
"""
import datetime
import html
import json
import os
import sys

import signal_lab_tracker as T

TRACKER_FILE = "signal-lab-tracker.json"
EXIT_LAB = "exit-lab.json"
EXIT_HYPS = "exit-lab-hypotheses.json"
WALL_LAB = "exit-wall-lab.json"
STOP_LAB = "stop-lab.json"
ENV_HISTORY = "signal-env-profile-history.json"
YORI_FWD = "yori-forward.json"
COMBO_FWD = "combo-forward.json"
AUTO_FWD = "auto-forward.json"
CAL_FWD = "calendar-forward.json"
HIGHS_FWD = "highs-trap-forward.json"     # 🆕 2026-10-06 J10F 高値更新の翌朝の罠の目印・前向き
GAP_FWD = "gap-forward.json"              # 🆕 2026-10-06 夜 J13F 窓の戻し・前向き
PREVGAP_FWD = "prevgap-forward.json"      # 🆕 2026-10-07 J17F 「寄りで買わない」目印の前向き
MARKET_DIP_FWD = "market-dip-forward.json"   # 🆕 2026-10-07 J25F 相場全体が安く寄った朝の深い下げ・前向き
YUTAI_DIR = "yutai-edinet"

# 仮説のまとまり（条件のキーで自動で振り分ける。上から順に最初に当たったもの）
THEMES = [
    ("env", "🌦️ 相場の環境で、効き方が変わるか",
     "同じシグナルでも、相場が落ち着いているとき・荒れているとき・ニュースが多いとき・"
     "ファンダ（経済や政治の材料）の見立てと向きが合っているかどうかで、成績が変わるかを確かめています。",
     {"env", "regime", "regime4", "vix_band", "adx_band", "news", "fbias", "cs_align"}),
    ("state", "🧩 指標の状態・組み合わせ",
     "RSI（買われすぎ・売られすぎの目安）や移動平均線などの指標がどんな状態のときに出たシグナルか、"
     "2つのシグナルが同時に出たときはどうか、を確かめています。",
     {"signals_all", "rsi_band", "ma_pos", "macd_side"}),
    ("wall", "🧱 利確までの壁・シグナルの選別ランク",
     "利確の目標までの間に、値動きを止めそうな節目（壁）があるかどうか、"
     "シグナルに付けている選別ランクで成績が変わるかを確かめています。",
     {"blocked", "tier"}),
    ("basic", "🎯 銘柄・向き・トレンド・シグナルの種類",
     "どの銘柄で、買いか売りか、トレンドの向き、シグナルの種類によって、勝ちやすさが違うかを確かめています。",
     None),
]

# 仮説の名前に出てくる用語の説明（表より前に1回だけ出す＝初めて出たところで説明する）。使われた用語だけ出す
TERMS = [
    ("ADX", "ADX（トレンドの強さを表す指標。数字が大きいほどトレンドが強い）"),
    ("VIX", "VIX（米国株の先行きへの不安の大きさを表す指数。恐怖指数とも呼ばれる）"),
    ("RSI", "RSI（相対力指数：買われすぎ・売られすぎの目安。70以上は買われすぎ、30以下は売られすぎ）"),
    ("MACD", "MACD（2本の移動平均線の差から、値動きの勢いを見る指標）"),
    ("ボリンジャーバンド", "ボリンジャーバンド（値動きのふだんの幅を表す線。−2σは下の線、+2σは上の線）"),
]

# 定期的に回している研究（しくみ）。頻度と場所は各ワークフロー／routine の設定に合わせる
ROUTINES = [
    ("🧪 AIシグナル研究日誌", "毎朝",
     "過去のシグナルを使って「こういう場面だけに絞ったら成績は変わるか」を1日に1つ確かめ、記事にしています。",
     "guides.html#cat-lab", "記事の一覧へ"),
    ("🏆 仮説の前向きの採点（番付）", "毎日",
     "登録した仮説を、登録した日より後に出たシグナルだけで採点しています。下の「仮説の前向きの採点」がその一覧です。",
     "#banzuke", "🏆 エッジ番付のタブへ"),
    ("🚪 出口の研究（利確と損切りの置き方）", "毎週日曜",
     "過去の長い値動きで、利確・損切りの置き方を変えると成績がどう変わるかを比べ、"
     "よさそうに見えたものは登録して、その後のデータで確かめています。", None, None),
    ("🌡️ 相場の環境の統計", "毎月2日",
     "シグナルが効いたとき・効かなかったときに、相場がどんな環境だったかを、毎月同じ物差しで数え直しています。",
     None, None),
]

SL_PLAIN = {"atr": "いまの方式", "swing": "直近の安値の少し下", "ma": "25本の移動平均線を割ったら",
            "chandelier": "高値から一定の幅で追いかける方式", "psar": "パラボリック（値動きに合わせて動く線）",
            "turtle": "タートル型", "atr_time": "いまの損切り＋一定の本数で時間切れ", "be": "いまの損切り＋利益が出たら建値へ"}
TP_PLAIN = {"atr2": "いまの方式", "swing": "直近の高値", "rr2": "損切り幅の2倍", "rr3": "損切り幅の3倍",
            "bb_mid": "ボリンジャーバンドの真ん中の線", "bb_up": "ボリンジャーバンドの上の線", "rsi70": "RSIが70を超えたら",
            "none": "利確を置かない", "half": "半分を先に利確・残りは建値で"}
SCOPE_PLAIN = dict(T.PLAIN_GROUP, fx="為替（FX）", index="株価指数", commodity="金・銀・原油", crypto="ビットコイン")
# 出口の壁ラボ・損切りラボの前向きの確認（キー → やさしい説明）。無いキーはラボの説明文をそのまま出す
FORWARD_PLAIN = {
    "tf_open_trail_1d": "日足の順張りで、利確の目標の先にしばらく壁（値動きを止めそうな節目）がないときは、"
                        "利確を置かずに利益を伸ばすと、いまの方式と比べて成績は変わるか",
    "1d|mr|A30": "日足の逆張り買いで、損切りの幅をいまの2倍に広げると、成績は変わるか",
    "4h|mr|A30": "4時間足の逆張り買いで、損切りの幅をいまの2倍に広げると、成績は変わるか",
}
# 結果を見たあとに登録した仮説の注記（id → 注記）。偶然よく見えただけの可能性を、その行で必ず伝える
_SEEN = "結果を見たあとの登録（偶然よく見えただけの可能性も十分あります）"
_BELOW = "事前に決めた基準には届かなかった候補の登録（偶然よく見えただけの可能性も十分あります）"
POST_HOC_NOTES = {
    "ep_fbias_mismatch": "結果を見たあとの登録（約50の区分を調べて見つかった1つ。偶然よく見えただけの可能性も十分あります）",
    "ep_fbias_aligned": "結果を見たあとの登録（約50の区分を調べて見つかった1つ。偶然よく見えただけの可能性も十分あります）",
    "rl_fx_mr_1d": _SEEN, "rl_tf_blocked": _SEEN,
    "rl_tf_adx_weak": _BELOW, "rl_tf_adx_strong": _BELOW, "rl_mr_vix_high": _BELOW, "rl_mr_vix_low": _BELOW,
    "4h|mr|A30": _SEEN,             # 損切りラボ（2026-09-26 の診断で4時間足の差 +0.052R を見てから登録）
    "tf_open_trail_1d": _SEEN,      # 出口の壁ラボ（exit_wall_lab.py の冒頭「探索の結果を見た後の登録」）
}
# 相場の環境の統計の判定（データ側の文字列）→ 表示の言い方（断定に読めないように）
VERDICT_PLAIN = [("確かめられた・効きやすい", "厳しい基準を満たした・平均より成績がよかった区分（過去の記録）"),
                 ("確かめられた・効きにくい", "厳しい基準を満たした・平均より成績が悪かった区分（過去の記録）"),
                 ("効きやすい側", "平均より成績がよかった側（過去の記録）"),
                 ("効きにくい側", "平均より成績が悪かった側（過去の記録）")]


def verdict_plain(v):
    for a, b in VERDICT_PLAIN:
        v = v.replace(a, b)
    return v


# 出口の相性ラボの前向きの仮説（id → 題名／比べ方の説明 → やさしい言い方）。無いものはラボの文をそのまま出す
EXIT_TITLE_PLAIN = {
    "bb_lower_deep_wait": "「ボリンジャーバンド−2σタッチ」の買いで、すぐに入らず、見込める利益が損失の3倍になる値段まで"
                          "下がるのを待って入ると、成績は変わるか",
}
EXIT_DESC_PLAIN = {
    "3で全部 − いまの方式（損切り1.5ATR・利確2.0ATR）": "日足で、待って入るやり方は、いまの方式と比べて成績が変わるか",
    "3で全部 − すぐ全部（節目・1.3以上）＝待つ効果そのもの": "日足で、待って入るやり方は、すぐに入る場合と比べて成績が変わるか（待つことそのものの効果）",
    "分けて入る（30%＠1.3・70%＠3）− いまの方式": "日足で、2回に分けて入るやり方は、いまの方式と比べて成績が変わるか",
    "4時間足で再現するか（過去2年では再現しなかった）": "4時間足でも同じ結果になるか（過去2年のデータでは同じにならなかった）",
}


def _load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def theme_of(f):
    keys = set(f or {})
    for key, _title, _desc, ks in THEMES:
        if ks is None or keys & ks:
            return key
    return "basic"


def next_checkpoint(h):
    """トラッカーが次に判定する件数（signal_lab_tracker.cmd_update と同じ式）。"""
    mn = T.min_n_of(h)
    return ((h.get("last_eval_n", 0) // mn) + 1) * mn


def registered_not_yet_tracked(tracker):
    """signal_lab_tracker.py に登録したが、まだ tracker.json に入っていない仮説（翌朝の集計で入る）。
    重複の見分け方はトラッカーの登録処理と同じ（id か条件のどちらかが既にあれば登録済み）。"""
    hyps = (tracker or {}).get("hypotheses") or []
    ids = {h.get("id") for h in hyps}
    keys = {T._filter_key(h.get("filter") or {}) for h in hyps}
    out = []
    for name in sorted(dir(T)):
        v = getattr(T, name)
        if not (name.isupper() and isinstance(v, dict) and isinstance(v.get("register"), list)):
            continue
        for s in v["register"]:
            if s.get("id") in ids or T._filter_key(s.get("filter") or {}) in keys:
                continue
            ids.add(s.get("id"))
            keys.add(T._filter_key(s.get("filter") or {}))
            out.append(dict(s, status="pending", forward={"n": 0}))
    return out


def _stage(h):
    st = h.get("status")
    if st == "pending":
        return "new", "🆕 登録したばかり（次の朝から数える）"
    if st == "promoted":
        return "done", "✅ 判定の基準を満たした（昇格中・今後外れることもある）"
    if h.get("holdout_pass"):
        return "cand", "🌟 過去のデータの確認は通過（登録後のデータを集めている）"
    return "track", "🌱 データを集めている"


def _question(h):
    label = h.get("label") or ""
    if "対照" in label:
        return "比べる相手（対照）"
    return ("負けやすいか（記録上の損益の平均がマイナスか）" if h.get("kind") == "gate"
            else "勝ちやすいか（記録上の損益の平均がプラスか）")


def collect(root="."):
    """表示に使う中身を集める（純粋にデータだけ。HTML も文字も作らない）。"""
    p = lambda name: os.path.join(root, name)
    tracker = _load(p(TRACKER_FILE)) or {}
    hyps = tracker.get("hypotheses") or []
    by_id = {h.get("id"): h for h in hyps}
    pending = registered_not_yet_tracked(tracker)
    for s in pending:
        by_id.setdefault(s.get("id"), s)

    active, ended = [], []
    for h in hyps + pending:
        if h.get("status") in ("tracking", "promoted", "pending"):
            active.append(h)
        else:
            ended.append(h)

    def item(h):
        stage_key, stage = _stage(h)
        n = (h.get("forward") or {}).get("n") or 0
        cp = T.min_n_of(h) if h.get("status") == "pending" else next_checkpoint(h)
        pair = by_id.get(h.get("pair")) if h.get("pair") else None
        return {"id": h.get("id"), "name": T.plain_name(h.get("filter") or {}), "question": _question(h),
                "stage": stage, "stage_key": stage_key, "registered": (h.get("registered_at") or "")[:10],
                "n": n, "checkpoint": cp,
                "pair_name": T.plain_name(pair.get("filter") or {}) if pair else None,
                "note": POST_HOC_NOTES.get(h.get("id"))}

    themes = []
    for key, title, desc, _ks in THEMES:
        rows = [item(h) for h in active if theme_of(h.get("filter")) == key]
        rows.sort(key=lambda r: (r["registered"], r["id"] or ""), reverse=True)
        if rows:
            themes.append({"key": key, "title": title, "desc": desc, "rows": rows})
    ended_rows = sorted(({"name": T.plain_name(h.get("filter") or {}), "question": _question(h),
                          "registered": (h.get("registered_at") or "")[:10],
                          "ended": h.get("demoted_at") or ""} for h in ended),
                        key=lambda r: r["registered"], reverse=True)

    return {"asof": tracker.get("updated_at") or "", "themes": themes, "ended": ended_rows,
            "n_active": len(active), "n_pending": len(pending),
            "exits": collect_exits(root), "env": collect_env(root)}


def _state(s):
    """ラボの状態の表示（「🟡蓄積中」など）をやさしい言い方にする。知らない表示はそのまま。"""
    return (s or "").replace("蓄積中", " データを集めている")


def _signal_side(tf, entry, side, scope):
    tfs = T.PLAIN_TF.get(tf, tf)
    sig = T.PLAIN_SIGNAL.get(entry, entry)
    sd = {"long": "買い", "short": "売り"}.get(side, side)
    sc = SCOPE_PLAIN.get(scope, scope)
    return f"{tfs}・「{sig}」の{sd}" + (f"（{sc}）" if scope and scope != "all" else "")


def collect_exits(root="."):
    """出口の研究の前向きの確認。1件＝{title, registered, note, rows[{desc, n, goal, state}]}。"""
    p = lambda name: os.path.join(root, name)
    out = []
    lab = _load(p(EXIT_LAB)) or {}
    hyps = {h.get("id"): h for h in ((_load(p(EXIT_HYPS)) or {}).get("hypotheses") or [])}
    groups = {}
    for fh in lab.get("forward_hypotheses") or []:
        groups.setdefault(fh.get("id"), []).append(fh)
    for hid, rows in groups.items():
        reg = (hyps.get(hid) or {}).get("registered_at") or ""
        out.append({"title": EXIT_TITLE_PLAIN.get(hid) or rows[0].get("label") or hid, "registered": reg,
                    "note": "入り方と出口をまとめて変えたルールを、登録した日の翌日より後に出たシグナルで、いまの方式と比べています。",
                    "rows": [{"desc": f"{'主な比較' if r.get('role') == '主' else '補足の比較'}："
                                      f"{EXIT_DESC_PLAIN.get(r.get('desc', ''), r.get('desc', ''))}",
                              "n": r.get("n") or 0, "goal": r.get("min_n"), "state": _state(r.get("status"))}
                             for r in rows]})
    flagged = lab.get("flagged_forward") or []
    if flagged:
        out.append({"title": "過去のデータで「いまの方式より悪い」と出た出口の組み合わせを見張る",
                    "registered": lab.get("is_until") or lab.get("asof") or "",
                    "note": f"過去のデータ（{lab.get('is_until') or '登録日'}まで）で、いまの方式よりはっきり悪かった"
                            f"{len(flagged)}通りの組み合わせです。その後のデータでも悪いままかを見ています。",
                    "rows": [{"desc": _signal_side(c.get("tf"), c.get("entry"), c.get("side"), c.get("group"))
                              + f"：損切り＝{SL_PLAIN.get(c.get('sl'), c.get('sl'))}／利確＝{TP_PLAIN.get(c.get('tp'), c.get('tp'))}",
                              "n": (c.get("vs_base") or {}).get("n") or 0, "goal": None, "state": _state(c.get("state"))}
                             for c in flagged]})
    for fname, lab_name in ((WALL_LAB, "出口の壁ラボ"), (STOP_LAB, "損切りラボ")):
        d = _load(p(fname)) or {}
        for key, v in (d.get("forward") or {}).items():
            if not isinstance(v, dict) or "min_n" not in v:    # 探索で差なし＝参考表示は載せない
                continue
            reg = v.get("registered") or d.get("fwd_from") or ""
            out.append({"title": FORWARD_PLAIN.get(key) or v.get("desc") or key,
                        "registered": reg[:10],
                        "note": f"{lab_name}で見つかった候補を、登録した日より後のデータで確かめています。"
                                + (f"{_SEEN}。" if "結果を見た" in reg or key in POST_HOC_NOTES else ""),
                        "rows": [{"desc": "いまの方式との差", "n": v.get("n") or 0, "goal": v.get("min_n"),
                                  "state": _state(v.get("state"))}]})
    return out


def collect_env(root="."):
    hist = _load(os.path.join(root, ENV_HISTORY))
    if not isinstance(hist, list) or not hist:
        return None
    last = hist[-1]
    cells = last.get("cells") or {}
    notable = [f"{c.get('title')}＝{c.get('bucket')}：{verdict_plain(c.get('verdict'))}" for c in cells.values()
               if str(c.get("verdict", "")).startswith(("確かめられた", "傾向あり"))]
    try:
        y, m = map(int, str(last.get("month", "")).split("-"))
        nxt = datetime.date(y + (m == 12), m % 12 + 1, 2).isoformat()
    except ValueError:
        nxt = ""
    return {"month": last.get("month"), "asof": last.get("asof"), "n": last.get("n"),
            "first": last.get("first"), "last": last.get("last"), "cells": len(cells),
            "notable": notable, "next": nxt}


# ---------------------------------------------------------------- 表示（HTML）
# ---------------------------------------------------------------- 研究中・検証中の一覧（短く）
def _md(iso):
    """2026-10-31 → 10月31日"""
    try:
        d = datetime.date.fromisoformat(str(iso)[:10])
    except ValueError:
        return str(iso)
    return f"{d.month}月{d.day}日"


def _const(root, filename, name):
    """部品を読み込まずに、ファイルの中の `NAME = "YYYY-MM-DD"`（または数字）を文字から取る。読めなければ None"""
    import re
    try:
        src = open(os.path.join(root, filename), encoding="utf-8").read()
    except OSError:
        return None
    g = re.search(rf'^{name}\s*=\s*"?(\d{{4}}-\d{{2}}-\d{{2}}|\d+)"?\s*(#.*)?$', src, re.M)
    return g.group(1) if g else None


def _ea_paused(root="."):
    """自動で建てる検証を止めている日（ea_ledger.py の PAUSED_SINCE）。動いていれば None"""
    here = os.path.dirname(os.path.abspath(__file__))
    for r in (root, here):
        if os.path.exists(os.path.join(r, "ea_ledger.py")):
            return _const(r, "ea_ledger.py", "PAUSED_SINCE")
    return None


def _ea_dates(root="."):
    """自動で建てる検証の区切りの日（ea_ledger.py の決まり）。読み込まずに文字から取る（重い部品を読まない）。読めなければ None"""
    import re
    try:
        src = open(os.path.join(root, "ea_ledger.py"), encoding="utf-8").read()
    except OSError:
        src = ""
    got = [re.search(rf'^{k}\s*=\s*"(\d{{4}}-\d{{2}}-\d{{2}})"', src, re.M) for k in ("FWD_START", "CUT_END", "DECIDE_ON")]
    return tuple(g.group(1) for g in got) if all(got) else None


def collect_studies(root, m):
    """いま進めている研究を短く並べる。前向きの検証は記録から進み具合を読み、判定が出たら一覧から外す。
    m は collect() の結果（仮説の採点・出口・環境の件数をそこから取る）"""
    p = lambda name: os.path.join(root, name)
    verify, research = [], []

    y = _load(p(YORI_FWD))
    if y:
        codes = list((y.get("titles") or {}).keys())
        done = set((y.get("verdicts") or {}).keys())
        live = [c for c in codes if c not in done]
        if live:
            cnt = {}
            for t in y.get("trades") or []:
                cnt[t.get("c")] = cnt.get(t.get("c"), 0) + 1
            prog = "・".join(f"形{i + 1} {cnt.get(c, 0)}回" for i, c in enumerate(codes) if c in live)
            extra = f"・判定が出た形 {len(done)}つ" if done else ""
            verify.append({"name": "前の日に出来高が急に増えた日本株の、次の日の寄り付き",
                           "what": "出来高（売買された株の数）が前の日に急に増えた銘柄について、次の日の朝いちばんの取引から"
                                   "決まった形で数え、手数料などを引いても平均がプラスになるかを確かめています"
                                   "（形1〜4は朝から持つ形、形5〜7は9時30分までに手じまう形で、10月6日から数えています）",
                           "since": y.get("fwd_start") or "",
                           "progress": f"{prog}（それぞれ{y.get('goal') or 1000}回で1回だけ判定）{extra}"})

    h = _load(p(HIGHS_FWD))
    if h:
        done = set((h.get("verdicts") or {}).keys())
        live = [c for c in ("A", "B") if c not in done]
        if live:
            cnt = {c: sum(1 for t in h.get("trades") or [] if t.get("c") == c and t.get("f")) for c in live}
            names = {"A": "よく売買される約400銘柄", "B": "サイトの高値更新の一覧"}
            prog = "・".join(f"{names[c]} {cnt[c]}回" for c in live)
            verify.append({"name": "高値を更新した日本株の、次の日の寄り付き",
                           "what": "年初来高値を更新した銘柄のうち、次の日の朝いちばんの値段（寄り付き）が前の日の終わりの値段より"
                                   "1パーセント以上高かったものは、9時30分までに値下がりしやすいか（入らない方がいい目印になるか）を、"
                                   "登録した日より後の取引だけで確かめています",
                           "since": h.get("fwd_start") or "",
                           "progress": f"目印にあてはまった取引 {prog}（それぞれ{h.get('goal') or 1000}回で1回だけ判定）"})

    g = _load(p(GAP_FWD))
    if g and not ((g.get("verdicts") or {}).get("B") and (g.get("marker_verdicts") or {}).get("A")):
        sm = g.get("summary") or {}
        days = sm.get("days", 0)
        verify.append({"name": "前の日の終わりの値段から離れて始まった日本株の、9時30分までの値動き",
                       "what": "朝いちばんの値段（寄り付き）が前の日の終わりの値段より1パーセント以上高く始まった銘柄は9時30分までに値下がりしやすいか、"
                               "3パーセント以上安く始まった銘柄をその値段で買うと手数料などを引いてもプラスになるかを、"
                               "東証のすべての銘柄の毎朝について、登録した日より後の朝だけで確かめています",
                       "since": g.get("fwd_start") or "",
                       "progress": f"数えた朝 {days}営業日（{g.get('goal_days') or 250}営業日で1回だけ判定）"})

    pg = _load(p(PREVGAP_FWD))
    if pg and not all(k in (pg.get("marker_verdicts") or {}) for k in ("A", "B")):
        days = (pg.get("summary") or {}).get("days", 0)
        verify.append({"name": "「寄りで買わない」目印（日本株の寄り付き）",
                       "what": "その銘柄だけが相場全体より1パーセント以上高く始まった銘柄と、前の日に5パーセント以上上がったうえに今朝も"
                               "そうして始まった銘柄は、9時30分までに値下がりしやすいかを、東証のすべての銘柄の毎朝について、"
                               "登録した日より後の朝だけで確かめています（オーナーの発注前の点検表に入れた目印）",
                       "since": pg.get("fwd_start") or "",
                       "progress": f"数えた朝 {days}営業日（{pg.get('goal_days') or 250}営業日で1回だけ判定）"})

    md = _load(p(MARKET_DIP_FWD))
    if md and not all(k in (md.get("verdicts") or {}) for k in (md.get("titles") or {})):
        sm = md.get("summary") or {}
        verify.append({"name": "相場全体が安く始まった朝に、大きく下げた日本株を拾う",
                       "what": "東証のすべての銘柄の朝いちばんの値段（寄り付き）が、まん中で前の日の終わりの値段より0.5パーセント以上安く始まった朝に、"
                               "前の日の終わりの値段より5・8・10パーセント下に買いの注文を置いておき、9時30分に売ると手数料などを引いてもプラスになるかを、"
                               "登録した日より後の朝だけで確かめています",
                       "since": md.get("fwd_start") or "",
                       "progress": f"相場全体が安く始まった朝 {sm.get('down_days', 0)}朝（{md.get('goal_down_days') or 30}朝で1回だけ判定・数えた朝 {sm.get('days', 0)}営業日）"})

    a = _load(p(AUTO_FWD))
    if not _ea_paused(root) and not (a and (a.get("verdicts") or {}).get("AT3")):
        dates = ((a.get("fwd_start"), a.get("cut_end"), a.get("decide_on")) if a and a.get("cut_end")
                 else (_ea_dates(root) or _ea_dates(os.path.dirname(os.path.abspath(__file__)))))
        n = ((a or {}).get("summary") or {}).get("n", 0)
        when = (f"{_md(dates[1])}までに届いた合図を数え、{_md(dates[2])}以降に1回だけ判定" if dates
                else "1か月のあいだに届いた合図を数え、そのあと1回だけ判定")
        verify.append({"name": "4時間足の合図を、練習用の口座で自動に建てる",
                       "what": "メールで届く4時間足の合図どおりに、練習用の口座（デモ口座）で自動に注文を出し、"
                               "実際の約定の値・費用・届くまでの遅れで、記録上の成績とどれだけずれるかを確かめています",
                       "since": dates[0] if dates else "",
                       "progress": f"{n}回（{when}）"})

    cf = _load(p(CAL_FWD))
    cal_start = (cf or {}).get("fwd_start") or _const(root, "calendar_forward.py", "FWD_START") \
        or _const(os.path.dirname(os.path.abspath(__file__)), "calendar_forward.py", "FWD_START")
    if cal_start:
        every = (cf or {}).get("goal") or 36
        names = {"Q1": "米国", "Q3": "日本"}
        stopped = set(((cf or {}).get("verdicts") or {}).keys())
        live = [q for q in ("Q1", "Q3") if q not in stopped]
        if live:
            cnt = {q: sum(1 for t in (cf or {}).get("trades") or [] if t.get("c") == q) for q in live}
            prog = "・".join(f"{names[q]} {cnt[q]}回" for q in live)
            try:
                nxt = datetime.date.fromisoformat(cal_start).month % 12 + 1
                first = "" if any(cnt.values()) else f"。最初の記録は{nxt}月上旬"
            except ValueError:
                first = ""
            verify.append({"name": "株価指数の月末月初（" + "・".join(names[q] for q in live) + "）",
                           "what": "月の変わり目の数日は株価指数が上がりやすい、という論文の癖（過去のデータでは傾向あり）が、"
                                   "登録した日より後の新しい月でも、売り買いの費用と持ち越しの金利を引いて崩れていないかを見張っています",
                           "since": cal_start,
                           "progress": f"{prog}。{every}回ごとに、費用を引いた平均がマイナスなら止めます（月に1回なので時間がかかります{first}）"})

    c = _load(p(COMBO_FWD))
    if c:
        r = c.get("result") or {}
        cps = r.get("checkpoints") or {}
        nxt = next((k for k in (50, 100, 150) if str(k) not in cps and k not in cps), None)
        if nxt is not None:
            n = (r.get("now") or {}).get("n", 0)
            verify.append({"name": "過去の確かめで向きだけ残った組み合わせ",
                           "what": "一目均衡表（いちもくきんこうひょう：トレンドの向きを見る指標）と、ボリンジャーバンド"
                                   "（値動きのふだんの幅を表す線）の下の線、値動きを追いかける損切りの組み合わせが、"
                                   "新しいデータでも同じ向きに残るかを見ています",
                           "since": "2026-09-28",
                           "progress": f"{n}件（次の区切りは{nxt}件。1年に30件ほどなので時間がかかります）"})

    verify.append({"name": "シグナルが出た場面の条件（仮説）の採点",
                   "what": "どんな場面で出たシグナルなら勝ちやすいか（負けやすいか）を仮説として登録し、登録した日より後のシグナルだけで採点しています",
                   "since": "", "progress": f"{m['n_active']}本を採点中（くわしくは下の②）"})
    if m["exits"]:
        verify.append({"name": "利確と損切りの置き方", "what": "利確と損切りの置き方を変えると成績がどう変わるかを、登録した日より後のデータで確かめています",
                       "since": "", "progress": f"{len(m['exits'])}件（くわしくは下の③）"})
    if m["env"]:
        verify.append({"name": "相場の環境の統計", "what": "シグナルが効いたとき・効かなかったときの相場の環境を、毎月同じ物差しで数え直しています",
                       "since": "", "progress": "毎月2日に数え直し（くわしくは下の④）"})

    if os.path.isdir(p(YUTAI_DIR)):
        research.append({"name": "株主優待のある銘柄の値動き",
                         "what": "株主優待のある銘柄は、権利の日の3か月ほど前から値動きに偏りがあるか、"
                                 "空売りしにくい銘柄ほどその偏りが大きいかを確かめる準備をしています",
                         "since": "2026-09-30",
                         "progress": "有価証券報告書（会社が毎年出す報告書）から優待の中身を集めている途中。集め終わったら1回だけ数えます"})
    return {"verify": verify, "research": research}


def _study_list(rows):
    out = ['<ul class="rm-list">']
    for r in rows:
        since = f"{_e(r['since'])} から・" if r.get("since") else ""
        out.append(f'<li><strong>{_e(r["name"])}</strong>：{_e(r["what"])}'
                   f'<br><span class="rm-sub">{since}{_e(r["progress"])}</span></li>')
    out.append("</ul>")
    return "".join(out)


def _e(s):
    return html.escape(str(s), quote=True)


def _progress(n, goal):
    if not goal:
        return f"{n}回"
    pct = max(0, min(100, round(100 * n / goal))) if goal else 0
    return (f'<div class="rm-prog"><span>{n}回／次の判定 {goal}回</span>'
            f'<div class="rm-bar"><i style="width:{pct}%"></i></div></div>')


RECENT_DAYS = 30   # 「最近始めた検証」に出す範囲（仮説の基準日から数えて）


def recent_rows(m):
    """直近 RECENT_DAYS 日に登録した仮説（テーマをまたいで新しい順）。基準日が読めなければ出さない。"""
    try:
        base = datetime.date.fromisoformat(str(m.get("asof"))[:10])
    except ValueError:
        return []
    since = (base - datetime.timedelta(days=RECENT_DAYS)).isoformat()
    rows = [r for th in m["themes"] for r in th["rows"] if r["registered"] >= since]
    return sorted(rows, key=lambda r: (r["registered"], r["id"] or ""), reverse=True)


def _studies_html(root, m):
    st = m.get("studies") or collect_studies(root, m)
    priv = ('<p class="rm-sub" style="margin:6px 0 0">このほかに、手元だけで進めている研究があります'
            '（個人の取引の記録や、外に出せないデータを使うため、ここには載せていません）。</p>')
    # ⚠️ f-string の {} の中にバックスラッシュを書かない＝Actions の Python 3.11 では構文エラーになり、
    #    成績ページの地図とトップの研究の帯が黙って消える（2026-10-01 実際に発生）。先に変数へ出す。
    research = _study_list(st["research"]) if st["research"] else '<p class="rm-desc">いまはありません。</p>'
    return ('<h3>📋 研究中・検証中の一覧</h3>'
            '<p class="rm-desc">いま進めている研究を短く並べました。判定が出たものは一覧から外れます。くわしい中身はこの下の①〜④にあります。</p>'
            f'<div class="rm-card"><strong>🧪 検証中</strong>（登録した日より後のデータで数えていて、判定はまだ）{_study_list(st["verify"])}</div>'
            f'<div class="rm-card"><strong>🔬 研究中</strong>（数える前の準備・データを集めている途中）'
            f'{research}{priv}</div>')


def build_pane(root=".", model=None):
    m = model if model is not None else collect(root)
    parts = [f"""
<div class="tab-pane" id="pane-map">
  <style>
    .rm-lead{{background:#ddf4ff;border:1px solid #54aeff66;border-radius:8px;padding:14px 16px;font-size:.92rem;line-height:1.75;margin-bottom:18px}}
    .rm-sum{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:0 0 22px}}
    .rm-sum div{{border:1px solid #d0d7de;border-radius:8px;padding:10px 12px;background:#fff}}
    .rm-sum b{{display:block;font-size:1.35rem;color:#0969da}}
    .rm-sum span{{font-size:.82rem;color:#57606a}}
    .rm-theme{{margin:22px 0 6px}}
    .rm-desc{{font-size:.86rem;color:#57606a;margin:0 0 8px;line-height:1.7}}
    .rm-prog span{{font-size:.8rem;white-space:nowrap}}
    .rm-bar{{height:6px;background:#eaeef2;border-radius:3px;margin-top:4px;min-width:90px}}
    .rm-bar i{{display:block;height:6px;background:#0969da;border-radius:3px}}
    .rm-new{{color:#8250df;font-weight:700}} .rm-cand{{color:#9a6700;font-weight:700}} .rm-done{{color:#1a7f37;font-weight:700}}
    .rm-sub{{font-size:.78rem;color:#8b949e}}
    .rm-det{{border:1px solid #d0d7de;border-radius:8px;padding:10px 14px;margin:0 0 10px;background:#fff}}
    .rm-det summary{{cursor:pointer;font-size:.93rem;line-height:1.6}}
    body.dark .rm-det{{background:#161b22;border-color:#30363d}}
    @media (max-width:640px){{
      .rm-t,.rm-t tbody,.rm-t tr,.rm-t td{{display:block;width:auto}}
      .rm-t tr:first-child{{display:none}}
      .rm-t tr{{border-top:1px solid #d0d7de;padding:8px 2px}}
      .rm-t td{{border:0;padding:3px 4px;white-space:normal!important}}
      .rm-t td[data-l]::before{{content:attr(data-l) "："; color:#8b949e;font-size:.78rem}}
      .rm-t td[data-l] .rm-prog{{display:inline-block;vertical-align:top;min-width:60%}}
      .rm-det{{padding:8px 10px}}
    }}
    .rm-card{{border:1px solid #d0d7de;border-radius:8px;padding:12px 14px;margin:0 0 12px;background:#fff}}
    .rm-list{{margin:8px 0 4px;padding-left:20px;font-size:.9rem;line-height:1.7}} .rm-list li{{margin:0 0 8px}}
    body.dark .rm-lead{{background:#0d1a2b;border-color:#388bfd66}}
    body.dark .rm-sum div,body.dark .rm-card{{background:#161b22;border-color:#30363d}}
    body.dark .rm-sum b{{color:#58a6ff}} body.dark .rm-desc,body.dark .rm-sum span{{color:#8b949e}}
    body.dark .rm-bar{{background:#30363d}} body.dark .rm-bar i{{background:#58a6ff}}
  </style>
  <h2>🗺️ いま検証中のこと</h2>
  <div class="rm-lead">
    当サイトが<strong>いま何を確かめているか</strong>を1か所にまとめた一覧です。新しい検証を始めると自動でここに加わり、
    終わると下の「終わった検証」へ移ります（仮説の一覧の基準日：{_e(m['asof'] or '—')}）。<br>
    どの検証も、<strong>登録した日より後に出たシグナルだけ</strong>で採点します。登録した条件と日付は記録に残し、あとから都合のよい条件に選び直さないきまりにしています。
    ここに並ぶ仮説は過去のデータを見て見つけた条件なので、偶然よく見えただけのものも多く含まれ、大半は判定で外れます。
    条件がめったに起きない仮説は、判定までに何か月〜何年もかかります。判定の前に途中の数字だけで結論を出さないのが、この研究のきまりです。
    確かめ方のきまりと数字の読み方は、<a href="guide-how-we-research.html">🧭 はじめての方へ</a>で説明しています。
  </div>
  <div class="rm-sum">
    <div><b>{m['n_active']}本</b><span>前向きに追っている仮説</span></div>
    <div><b>{len(m['exits'])}件</b><span>出口（利確・損切り）の研究</span></div>
    <div><b>{(m['env'] or {}).get('cells', 0)}区分</b><span>毎月数え直す相場の環境</span></div>
    <div><b>{len(m['ended'])}本</b><span>終わった検証（記録は残す）</span></div>
  </div>
  {_studies_html(root, m)}
  <h3>① 定期的に回している研究</h3>
  <div class="scroll-x"><table class="rm-t"><tr><th>研究</th><th>いつ</th><th>何をしているか</th></tr>"""]
    for name, when, what, href, link in ROUTINES:
        a = f' <a href="{_e(href)}">{_e(link)} →</a>' if href else ""
        parts.append(f'<tr><td><strong>{_e(name)}</strong></td><td data-l="いつ" style="white-space:nowrap">{_e(when)}</td><td>{_e(what)}{a}</td></tr>')
    parts.append("</table></div>")

    parts.append('<h3 style="margin-top:28px">② 仮説の前向きの採点</h3>'
                 '<p class="rm-desc">「どんな場面で出たシグナルか」を仮説として登録し、その場面のシグナルが'
                 '「勝ちやすいか（記録上の損益の平均がプラスか）」「負けやすいか（マイナスか）」を確かめています。'
                 '売買のタイミングや銘柄を示すものではありません。'
                 '決まった件数がたまるごとに判定し、基準を2回続けて満たすと昇格、反対の結果が出ると終わりになります。'
                 '成績の数字は <a href="#banzuke">🏆 エッジ番付</a> のタブで見られます。</p>')
    names = " ".join(r["name"] for th in m["themes"] for r in th["rows"])
    used = [text for term, text in TERMS if term in names]
    if used:
        parts.append(f'<p class="rm-desc">表に出てくる言葉：{_e("／".join(used))}</p>')
    head = "<tr><th>仮説（どんな場面のシグナルか）</th><th>確かめていること</th><th>段階</th><th>登録した日より後の件数</th></tr>"

    def table(rows):
        out = [f'<div class="scroll-x"><table class="rm-t">{head}']
        for r in rows:
            pair = (f'<br><span class="rm-sub">対になる仮説「{_e(r["pair_name"])}」と並べて、差を見ます</span>'
                    if r["pair_name"] else "")
            if r.get("note"):
                pair += f'<br><span class="rm-sub">⚠️ {_e(r["note"])}</span>'
            out.append(
                f'<tr><td><strong>{_e(r["name"])}</strong>{pair}'
                f'<br><span class="rm-sub">登録 {_e(r["registered"])}</span> <span class="meta-line rm-sub">{_e(r["id"])}</span></td>'
                f'<td data-l="確かめていること">{_e(r["question"])}</td>'
                f'<td data-l="段階"><span class="rm-{r["stage_key"]}">{_e(r["stage"])}</span></td>'
                f'<td data-l="件数">{_progress(r["n"], r["checkpoint"])}</td></tr>')
        out.append("</table></div>")
        return "".join(out)

    recent = recent_rows(m)
    if recent:
        parts.append(f'<h4 class="rm-theme">🆕 最近始めた検証（直近{RECENT_DAYS}日に登録・{len(recent)}本）</h4>'
                     + table(recent))
    parts.append('<h4 class="rm-theme">📂 テーマ別の一覧（すべての仮説・クリックで開く）</h4>')
    for th in m["themes"]:
        cnt = {k: sum(1 for r in th["rows"] if r["stage_key"] == k) for k in ("done", "cand", "new")}
        extra = "・".join(f"{lab}{cnt[k]}本" for k, lab in (("done", "基準を満たした"), ("cand", "過去のデータの確認を通過"),
                                                              ("new", "集計待ち")) if cnt[k])
        parts.append(f'<details class="rm-det"><summary><strong>{_e(th["title"])}</strong>（{len(th["rows"])}本'
                     f'{"：" + extra if extra else ""}）</summary>'
                     f'<p class="rm-desc" style="margin-top:8px">{_e(th["desc"])}</p>{table(th["rows"])}</details>')

    parts.append('<h3 style="margin-top:28px">③ 出口（利確・損切り）の研究</h3>'
                 '<p class="rm-desc">入るところは同じでも、利確と損切りの置き方で成績は変わります。'
                 '過去のデータでよさそう（または悪そう）に見えた置き方を登録し、その後のデータでも同じかを確かめています。'
                 '組み合わせをたくさん試したぶん、偶然よく見えただけの可能性があるので、判定は100件たまってからです。'
                 '「いまの方式」とは、このサイトがシグナルの記録を採点するときに使っている決まった置き方で、'
                 '損切りをATR（値動きの平均的な幅）の1.5倍、利確を2.0倍の位置に置きます。</p>')
    if not m["exits"]:
        parts.append('<p class="rm-desc">いま前向きに確かめている出口の研究はありません。</p>')
    for x in m["exits"]:
        rows = "".join(f'<tr><td>{_e(r["desc"])}</td><td data-l="件数">{_progress(r["n"], r["goal"])}</td>'
                       f'<td data-l="状態">{_e(r["state"])}</td></tr>'
                       for r in x["rows"])
        table = (f'<div class="scroll-x"><table class="rm-t"><tr><th>比べていること</th><th>登録した日より後の件数</th><th>状態</th></tr>'
                 f'{rows}</table></div>')
        if len(x["rows"]) > 4:
            table = (f'<details><summary style="cursor:pointer;font-size:.88rem;color:#0969da">'
                     f'{len(x["rows"])}通りの中身を開く</summary>{table}</details>')
        parts.append(f'<div class="rm-card"><strong>{_e(x["title"])}</strong>'
                     f'<br><span class="rm-sub">登録 {_e(x["registered"] or "—")}</span>'
                     f'<p class="rm-desc" style="margin-top:6px">{_e(x["note"])}</p>{table}</div>')

    env = m["env"]
    parts.append('<h3 style="margin-top:28px">④ 相場の環境の統計（毎月）</h3>')
    if env:
        notable = ("".join(f"<li>{_e(s)}</li>" for s in env["notable"]) if env["notable"]
                   else "<li>目立った差のある区分はありませんでした。</li>")
        parts.append(
            f'<div class="rm-card"><p class="rm-desc" style="margin:0">シグナルが出たときの相場の環境'
            f'（警戒の度合い・市場の不安の大きさ・トレンドの強さ・ニュースの多さ・ファンダの見立てなど）を'
            f'{env["cells"]}の区分に分け、区分ごとに勝ちやすさが平均と違うかを数えています。'
            f'前回は {_e(env["asof"])} に、{_e(env["first"])}〜{_e(env["last"])} のシグナル {env["n"]:,}件で数えました。'
            f'次回は {_e(env["next"] or "来月2日")} の予定です。</p>'
            f'<p class="rm-desc" style="margin:8px 0 2px">前回、差がありそうだった区分：</p><ul class="rm-desc">{notable}</ul>'
            f'<p class="rm-desc" style="margin:0">差がありそうな区分は、偶然の可能性があるので②の仮説として登録し、'
            f'その後のデータで確かめています。</p></div>')
    else:
        parts.append('<p class="rm-desc">まだ集計がありません（毎月2日に数えます）。</p>')

    if m["ended"]:
        rows = "".join(f'<tr><td>{_e(r["name"])}</td><td data-l="確かめていたこと">{_e(r["question"])}</td>'
                       f'<td data-l="登録">{_e(r["registered"])}</td></tr>'
                       for r in m["ended"])
        parts.append(
            f'<h3 style="margin-top:28px">⑤ 終わった検証（{len(m["ended"])}本）</h3>'
            f'<details><summary style="cursor:pointer;font-size:.9rem;color:#57606a">'
            f'思ったとおりにならなかった検証も、消さずに残しています（開く）</summary>'
            f'<div class="scroll-x" style="margin-top:10px"><table class="rm-t"><tr><th>仮説</th><th>確かめていたこと</th><th>登録</th></tr>'
            f'{rows}</table></div></details>')

    parts.append('<p style="font-size:.82rem;color:#8b949e;margin-top:22px">'
                 '※ この一覧は研究の進み具合の記録です。「基準を満たした」仮説も、特定の取引や銘柄の売買をすすめるものではありません。'
                 '採点は、シグナルを決まったルールで機械的に記録した仮想の結果で、実際の取引ではありません'
                 '（手数料や価格の滑りなど、実際の取引で生じる差は十分には反映されていません）。'
                 '過去や途中の成績は、これからの成績を約束するものではありません。投資の判断はご自身の責任でお願いします。</p>\n</div>')
    return "\n".join(parts)


# ---------------------------------------------------------------- 表示（文字）
def render_text(m):
    st = m.get("studies") or collect_studies(".", m)
    L = ["研究中・検証中の一覧"] + [f"  検証中: {r['name']}（{r['progress']}）" for r in st["verify"]] \
        + [f"  研究中: {r['name']}（{r['progress']}）" for r in st["research"]] + [""]
    L += [f"いま検証中のこと（仮説の基準日 {m['asof'] or '—'}）",
         f"前向きに追っている仮説 {m['n_active']}本（うち集計待ち {m['n_pending']}本）／出口の研究 {len(m['exits'])}件／"
         f"終わった検証 {len(m['ended'])}本", ""]
    for th in m["themes"]:
        L.append(f"■ {th['title']}（{len(th['rows'])}本）")
        for r in th["rows"]:
            L.append(f"  {r['registered']} {r['stage']:<20} {r['n']:>5}/{r['checkpoint']:<5} {r['name']}（{r['question']}）")
        L.append("")
    L.append("■ 出口の研究")
    for x in m["exits"]:
        L.append(f"  {x['registered'] or '—'} {x['title']}")
        for r in x["rows"]:
            L.append(f"      {r['n']:>4}/{r['goal'] or '—'} {r['state']} {r['desc']}")
    env = m["env"]
    if env:
        L += ["", f"■ 相場の環境の統計: 前回 {env['asof']}（{env['n']:,}件・{env['cells']}区分）次回 {env['next']}"]
        L += [f"  差がありそう: {s}" for s in env["notable"]] or ["  差がありそうな区分なし"]
    return "\n".join(L)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(render_text(collect()))
