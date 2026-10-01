# -*- coding: utf-8 -*-
"""EA の記録を数える（手元で動かす・2026-09-30 AT1〜AT3・決まりは PILLAR_PREREG.md「AT」）。

入力（MT4 の共通フォルダ Common\\Files。EA は FILE_COMMON で書く）:
  mw_guard_log.csv   （AT1・本番） 列: utc,rule,ticket,symbol,action,mode,price,lots,profit,detail
      action＝close/partial/set_sl/notify（強制）・flag（見張りだけで「動くはずだった」印。detail の先頭が would_close など）
             ・final（flag を付けた建玉が閉じたときの最終の損益）
  mw_scalp5_log.csv  （AT2・本番） 列: plan,legs,ticket,open_utc,close_utc,symbol,dir,planned,fill,spread,lots,risk,balance,
                                    sl,close_price,profit,commission,swap,reason
  mw_swing4h_log.csv （AT3・デモ） 列: plan,legs,kind,status,ticket,signal_utc,seen_utc,open_utc,close_utc,symbol,dir,
                                    signal_price,fill,spread,lots,risk,balance,sl,tp,close_price,profit,commission,swap,reason
      status＝filled（建てた建玉が閉じた行）／skipped（建てなかった。reason に理由）
  時刻は UTC の 1970年からの秒。plan＝1回の注文（半分ずつの2本＝legs 2）。risk＝その注文全体の損切りまでの損失（口座の通貨）
  1回の R ＝ 注文の全部の建玉の（損益＋手数料＋スワップ）÷ risk（費用込み）

出力:
  AT3 → auto-forward.json（リポジトリ直下。R だけ・デモ口座・金額なし＝送ってよい。検証済みリストが読む）
  AT1・AT2 → --report-dir の md（既定 research/ea/。個人の取引なので送らない）

実行: python ea_ledger.py --files "C:\\Users\\...\\MetaQuotes\\Terminal\\Common\\Files"
"""
import argparse
import collections
import csv
import datetime as dt
import io
import json
import os
import sys

import screen_judge as J

JST = dt.timezone(dt.timedelta(hours=9))
FWD_START = "2026-10-01"          # AT3：この日（日本時間）以降に届いた合図だけ数える
# 🆕 2026-10-01 オーナー決定「2年も検証していたら長すぎる」＝AT3 は1か月で1回だけ区切る（PILLAR_PREREG.md「AT」の追記）。
# 300回・1000回の決まりは AT3 には使わない。この日（日本時間）までに届いた合図だけ数え、DECIDE_ON 以降に1回だけ判定する
CUT_END = "2026-10-31"
DECIDE_ON = "2026-11-08"          # 期間の建玉は7日で閉じる＝この日にはすべて閉じている（閉じていない注文があれば閉じるまで待つ）
STEP = 30                         # 読むための区切り（判定ではない）
REAL_MIN = 30                     # 本番へ移す条件の回数（デモ30回以上で幅の下限＞0。変えない）
GOAL = f"{FWD_START}〜{CUT_END} に届いた合図・{DECIDE_ON} 以降に1回だけ判定"
SECTION = "## AT "
OUT_JSON = "auto-forward.json"
TITLE_AT3 = "4時間足のメールの合図を、デモ口座で自動に建てる（前向き・費用込みの R）"
LABELS = {"ok": "機能している", "unknown": "まだ分からない", "stop": "反証（手を止めて設計に戻る）"}


# ───────── 読む ─────────
def read_csv(path):
    """MT4 の CSV（UTF-16 でも ANSI でも）を辞書の並びにする。無ければ空"""
    if not os.path.exists(path):
        return []
    raw = open(path, "rb").read()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        text = raw.decode("utf-16")
    else:
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw.decode("cp932", errors="replace")
    return [{k.strip(): (v or "").strip() for k, v in r.items() if k} for r in csv.DictReader(io.StringIO(text))]


def _f(x, default=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def jst_date(utc_sec):
    return dt.datetime.fromtimestamp(int(_f(utc_sec)), JST).date().isoformat()


def plans(rows, date_key):
    """閉じた建玉の行を注文ごとにまとめる。legs 本すべて閉じた注文だけ返す（入った順）"""
    g = collections.OrderedDict()
    for r in rows:
        if r.get("status", "filled") != "filled" or not r.get("close_utc"):
            continue
        g.setdefault(r["plan"], []).append(r)
    out, still_open = [], 0
    for pid, rs in g.items():
        legs = int(_f(rs[0].get("legs"), 1)) or 1
        if len({r["ticket"] for r in rs}) < legs:
            still_open += 1
            continue
        risk = _f(rs[0].get("risk"))
        if risk <= 0:
            continue
        money = sum(_f(r.get("profit")) + _f(r.get("commission")) + _f(r.get("swap")) for r in rs)
        first = rs[0]
        out.append({"plan": pid, "r": money / risk, "date": jst_date(first[date_key]), "t": int(_f(first[date_key])),
                    "kind": first.get("kind", ""), "symbol": first.get("symbol", ""),
                    "delay_min": (round((_f(first.get("seen_utc")) - _f(first.get("signal_utc"))) / 60, 1)
                                  if first.get("seen_utc") and first.get("signal_utc") else None),
                    "rows": rs})
    return sorted(out, key=lambda p: p["t"]), still_open


# ───────── 数える ─────────
def label(st):
    if st["lo"] is not None and st["lo"] > 0:
        return "ok"
    if st["hi"] is not None and st["hi"] < 0:
        return "stop"
    return "unknown"


def checkpoints(rs, dates):
    out = []
    for k in range(STEP, len(rs) + 1, STEP):
        st = J.cluster_stats(rs[:k], dates[:k])
        out.append({"n": k, "mean": J._f(st["mean"]), "lo": J._f(st["lo"]), "hi": J._f(st["hi"]),
                    "win": J._f(st["win"]), "label": label(st)})
    return out


def at3_verdict(prev, rs, dates, today, still_open):
    """オーナーの決まり（2026-10-01）：期間（FWD_START〜CUT_END に届いた合図）の注文がすべて閉じたあと、DECIDE_ON 以降に1回だけ。
    幅の下限が0より上＝プラス／それ以外（0をまたぐ・まるごと下・0回）＝ストップ。一度出たら変えない"""
    if prev:
        return prev
    if today < DECIDE_ON or still_open:
        return None
    period = f"{FWD_START}〜{CUT_END} に届いた合図"
    n = len(rs)
    if n == 0:
        return {"status": "stop", "decided_on": today, "n": 0, "mean": None, "lo": None, "hi": None,
                "reason": f"{period}で建てた回数が0"}
    st = J.cluster_stats(rs, dates)
    lo, hi = J._f(st["lo"]), J._f(st["hi"])
    if lo is not None and lo > 0:
        status = "plus"
        reason = f"{period}の{n}回で費用込みの平均の幅がまるごと0より上" + (
            f"（{REAL_MIN}回に届かないので本番へは移さない）" if n < REAL_MIN else "")
    elif hi is not None and hi < 0:
        status, reason = "stop", f"{period}の{n}回で費用込みの平均の幅がまるごと0より下"
    elif st["mean"] <= 0:
        status, reason = "stop", f"{period}の{n}回で費用込みの平均がマイナス（幅は0をまたぐ）"
    else:
        status, reason = "stop", f"{period}の{n}回ではプラスと言い切れない（幅が0をまたぐ）"
    return {"status": status, "decided_on": today, "n": n, "mean": J._f(st["mean"]), "lo": lo, "hi": hi, "reason": reason}


def at3_state(v, today, still_open):
    """判定がまだのとき、いまどこにいるか（読むための一言）"""
    if v:
        return "判定済み（変えない）"
    if today <= CUT_END:
        return f"数えている途中（{CUT_END} までに届いた合図）"
    if today < DECIDE_ON:
        return f"区切りのあと＝期間の建玉が閉じるのを待っている（{DECIDE_ON} に判定）"
    return f"期間の注文のうち {still_open} 回がまだ閉じていない＝閉じてから判定"


def build_at3(swing_rows, prev=None, today=None, now=None):
    today = today or dt.datetime.now(JST).date().isoformat()

    def in_period(r):
        return FWD_START <= jst_date(r.get("signal_utc")) <= CUT_END

    rows = [r for r in swing_rows if in_period(r)]                      # 期間の外（登録より前・区切りのあと）は数えない
    after = {r.get("plan") for r in swing_rows if jst_date(r.get("signal_utc")) > CUT_END}
    ps, still_open = plans(rows, "signal_utc")
    rs, dates = [p["r"] for p in ps], [p["date"] for p in ps]
    skipped = collections.Counter(r.get("reason") or "（理由なし）" for r in rows if r.get("status") == "skipped")
    v = at3_verdict(((prev or {}).get("verdicts") or {}).get("AT3"), rs, dates, today, still_open)
    st = J.cluster_stats(rs, dates)
    return {"kind": "forward", "unit": "R", "goal": GOAL, "fwd_start": FWD_START, "cut_end": CUT_END, "decide_on": DECIDE_ON,
            "generated_jst": now or dt.datetime.now(JST).isoformat(timespec="minutes"),
            "prereg_sha256": J.section_sha256(head=SECTION),
            "titles": {"AT3": TITLE_AT3}, "verdicts": {"AT3": v} if v else {},
            "summary": {"n": len(rs), "mean": J._f(st["mean"]), "lo": J._f(st["lo"]), "hi": J._f(st["hi"]),
                        "win": J._f(st["win"]), "open_plans": still_open, "after_cut_signals": len(after),
                        "state": at3_state(v, today, still_open)},
            "checkpoints": checkpoints(rs, dates), "skipped": dict(skipped),
            "trades": [{"c": "AT3", "d": p["date"], "r": round(p["r"], 4), "kind": p["kind"], "delay_min": p["delay_min"]}
                       for p in ps]}


def guard_report(rows):
    """AT1：決まりごとの発動の回数と、見張りだけの期間の「動いていたら」の差（読むための表）"""
    cnt = collections.Counter((r.get("rule"), r.get("mode"), r.get("action")) for r in rows if r.get("action") != "final")
    finals = {r["ticket"]: _f(r.get("profit")) for r in rows if r.get("action") == "final"}
    pairs, seen = [], set()
    for r in rows:
        if r.get("action") == "flag" and r.get("detail", "").startswith("would_close") and (r["ticket"], r["rule"]) not in seen:
            seen.add((r["ticket"], r["rule"]))
            if r["ticket"] in finals:
                pairs.append({"rule": r["rule"], "ticket": r["ticket"], "at_flag": _f(r.get("profit")),
                              "final": finals[r["ticket"]]})
    L = ["# AT1 守りの見張り番の記録（手元専用・送らない）", "",
         "| 決まり | 見張りだけ／強制 | したこと | 回数 |", "|---|---|---|---:|"]
    L += [f"| {k[0]} | {k[1]} | {k[2]} | {n} |" for k, n in sorted(cnt.items(), key=lambda x: (str(x[0]), -x[1]))] or ["| — | — | — | 0 |"]
    L += ["", "## 見張りだけの期間：「決済していたら」と実際の差（口座の通貨・プラス＝見張り番が動いていたら得だった）", ""]
    by = collections.defaultdict(list)
    for p in pairs:
        by[p["rule"]].append(p["at_flag"] - p["final"])
    L += [f"- {k}：{len(v)}件・差の合計 {sum(v):+,.0f}・1件あたり {sum(v) / len(v):+,.0f}" for k, v in sorted(by.items())] or ["- まだ無い"]
    L += ["", "読むための表（判定しない）。決まりの値を変えるときは PILLAR_PREREG.md「AT」に日付つきで追記する。"]
    return "\n".join(L) + "\n", pairs


def scalp_report(rows):
    """AT2：MY_TRADING_RULES.md「デイトレ開始にあたっての事前登録」の区切り（30回ごと）"""
    ps, still_open = plans(rows, "open_utc")
    rs, dates = [p["r"] for p in ps], [p["date"] for p in ps]
    st = J.cluster_stats(rs, dates)
    cps = checkpoints(rs, dates)
    mean_txt = "—" if st["mean"] is None else f"{st['mean']:+.3f}R"
    L = ["# AT2 5分足の執行アシストの記録（手元専用・送らない）", "",
         f"- 閉じた注文 {len(ps)} 回（まだ開いている {still_open}）・費用込みの平均 {mean_txt}", ""]
    L += ["| 区切り | 平均 | 95％の幅 | 勝率 | 判定 |", "|---:|---:|---|---:|---|"]
    L += [f"| {c['n']} | {c['mean']:+.3f}R | {c['lo']:+.3f}〜{c['hi']:+.3f}R | {c['win'] * 100:.0f}％ | {LABELS[c['label']]} |"
          for c in cps] or ["| — | — | — | — | まだ30回に届いていない |"]
    slip = [(_f(r["fill"]) - _f(r["planned"])) * (1 if int(_f(r["dir"])) > 0 else -1)
            for p in ps for r in p["rows"][:1] if r.get("planned") and r.get("fill")]
    by_hour = collections.defaultdict(list)
    for p in ps:
        by_hour[dt.datetime.fromtimestamp(p["t"], JST).hour].append(p["r"])
    L += ["", "## 読むための表（判定しない）", "",
          f"- 滑り（約定−予定・不利な向きがプラス・値の単位）：平均 {sum(slip) / len(slip):+.5f}" if slip else "- 滑り：まだ無い"]
    L += [f"- 日本時間 {h}時台：{len(v)}回・平均 {sum(v) / len(v):+.3f}R" for h, v in sorted(by_hour.items())]
    return "\n".join(L) + "\n", cps


def main(argv=None):
    ap = argparse.ArgumentParser(description="EA の記録を数える（AT1〜AT3）")
    ap.add_argument("--files", required=True, help="MT4 の Common\\Files")
    ap.add_argument("--report-dir", default=os.path.join("research", "ea"))
    ap.add_argument("--json-out", default=OUT_JSON)
    ap.add_argument("--today")
    a = ap.parse_args(argv)
    prev = None
    if os.path.exists(a.json_out):
        with open(a.json_out, encoding="utf-8") as fh:
            prev = json.load(fh)
    at3 = build_at3(read_csv(os.path.join(a.files, "mw_swing4h_log.csv")), prev, a.today)
    with open(a.json_out, "w", encoding="utf-8") as fh:
        json.dump(at3, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    os.makedirs(a.report_dir, exist_ok=True)
    g_md, _ = guard_report(read_csv(os.path.join(a.files, "mw_guard_log.csv")))
    s_md, _ = scalp_report(read_csv(os.path.join(a.files, "mw_scalp5_log.csv")))
    for name, md in (("at1-guard.md", g_md), ("at2-scalp5.md", s_md)):
        with open(os.path.join(a.report_dir, name), "w", encoding="utf-8") as fh:
            fh.write(md)
    s = at3["summary"]
    print(f"AT3：{s['n']}回（開いている {s['open_plans']}）・{s['state']}・判定 {at3['verdicts'].get('AT3', {}).get('status', 'まだ')} → {a.json_out}")
    print(f"AT1・AT2 の報告 → {a.report_dir}（送らない）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
