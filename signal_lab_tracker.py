# -*- coding: utf-8 -*-
"""
signal_lab_tracker.py — 前向きトラッカー（登録→out-of-sample で蓄積→自動昇格判定）。

考え方:
- 発見スイープ(signal_lab_sweep.py)は in-sample の「候補出し」。ここに登録したら、以後は
  「登録日(registered_at)以降に発火したシグナルだけ」で勝率を測る＝定義上アウトオブサンプル。
  これにより「たくさん試しても p-hacking で自滅しない」を構造的に担保する。
- 昇格はコード化した事前宣言ルールで自動判定（方向対応）:
    edge（順＝損益分岐超を期待）: forward N≥min_n かつ forward CI下限 > breakeven → ✅昇格（本物のエッジ確認）
    gate（逆＝回避を期待）      : forward N≥min_n かつ forward CI上限 < breakeven → ✅昇格（回避ゲート確認）
    反証（期待と逆に確定）した場合は rejected。どちらも未達なら tracking（蓄積中）。
- ⚠️ 昇格はあくまで「ライブ配信フィルタ/信頼度へ反映する“候補”」を旗立てするだけ。
  発火エンジンや配信条件には絶対に自動で触れない（CLAUDE.md の鉄則）。人間が最終反映。

使い方:
    python signal_lab_tracker.py update                 # 最新signals-logで全件再計算＋昇格判定＋表示
    python signal_lab_tracker.py register --from sweep.json   # FDR通過候補を登録（重複は無視）
    python signal_lab_tracker.py table [--html]         # 記事用トラッカー表を出力
    共通オプション: --date YYYY-MM-DD（基準日。既定は今日／routineでは固定日を渡す）

データ: signal-lab-tracker.json（GitHub側でroutineが更新・commit＝SYNC禁忌にする）
"""
import argparse
import datetime
import json
import os
import sys

from signal_lab_verify import wilson, closed, win, match
from signal_lab_sweep import BREAKEVEN, load_log

ROOT = os.path.dirname(os.path.abspath(__file__))
TRACKER = os.path.join(ROOT, "signal-lab-tracker.json")
PROMOTE_MIN_N = 80          # 昇格に必要な前向きN（既存基準 N≥80）
BE_PCT = BREAKEVEN * 100    # 43.0

# 初期登録（トラッカー未作成時のシード）。
# registered_at: 既に過去記事で宣言済みの仮説はその宣言日、新規発見は今日。
SEED = [
    # ── 20年バックテスト(日足)で FDR 通過した頑健な順エッジ＝tf=1d で前向き登録 ──
    #    （ライブの日足ストリームで out-of-sample に検証。()内は20年backtest勝率）
    {"id": "index_long_1d", "label": "指数×ロング(日足)", "filter": {"group": "index", "direction": "long", "tf": "1d"},
     "kind": "edge", "registered_at": "2026-06-16"},          # 44.7% N3699
    {"id": "metal_long_1d", "label": "メタル×ロング(日足)", "filter": {"group": "metal", "direction": "long", "tf": "1d"},
     "kind": "edge", "registered_at": "2026-06-16"},          # 52.9% N1557
    {"id": "btc_long_1d", "label": "BTC×ロング(日足)", "filter": {"group": "btc", "direction": "long", "tf": "1d"},
     "kind": "edge", "registered_at": "2026-06-16"},          # 52.1% N589
    {"id": "index_revL_1d", "label": "指数×逆張り買い(日足)", "filter": {"group": "index", "reversal_long": True, "tf": "1d"},
     "kind": "edge", "registered_at": "2026-06-16"},          # 47.6% N1127
    # ── 20年で頑健な回避ゲート（tf=1d） ──
    {"id": "other_fx_1d", "label": "other_fxクロス(日足・回避)", "filter": {"group": "other_fx", "tf": "1d"},
     "kind": "gate", "registered_at": "2026-06-16"},          # 38.0% N4032
    {"id": "short_1d", "label": "ショート全般(日足・回避)", "filter": {"direction": "short", "tf": "1d"},
     "kind": "gate", "registered_at": "2026-06-16"},          # 39.3% N4085
    {"id": "dntrend_1d", "label": "下降トレンド発火(日足・回避)", "filter": {"trend": "下降", "tf": "1d"},
     "kind": "gate", "registered_at": "2026-06-16"},          # 40.5% N4088
    # ── ライブ1か月でも20年でも一貫して強い（足を絞らない＝全足ライブ） ──
    {"id": "index_long_live", "label": "指数×ロング(全足ライブ)", "filter": {"group": "index", "direction": "long"},
     "kind": "edge", "registered_at": "2026-06-12"},
    # ── FX2年intradayで唯一FDRを生き残ったエッジ＝コア仮説「売られすぎの逆張り買い」を前向き検証 ──
    {"id": "rsi_oversold_edge", "label": "売られすぎ逆張り買い(rsi_oversold_bounce・全足)", "filter": {"signal": "rsi_oversold_bounce"},
     "kind": "edge", "registered_at": "2026-06-16"},   # FX intraday 47.4%（q=0.06）
    # 注: 旧SEEDの「メタル＝回避ゲート」「全逆張り買い」はライブ1か月(主に時間足・極小N)由来で
    #     20年日足エビデンス(メタル×ロング勝ち/逆張りは指数限定)と矛盾するため不採用。
]


def fired_date(d):
    return (d.get("fired_at") or "")[:10]


def stats(data, f, since=None):
    rows = [d for d in data if closed(d) and match(d, f) and (since is None or fired_date(d) >= since)]
    n = len(rows)
    k = sum(1 for d in rows if win(d))
    lo, hi = wilson(k, n)
    pct = (100 * k / n) if n else 0.0
    return {"k": k, "n": n, "pct": round(pct, 1), "ci_lo": round(lo, 1), "ci_hi": round(hi, 1)}


def judge(kind, fwd):
    """方向対応の昇格判定。"""
    if fwd["n"] < PROMOTE_MIN_N:
        return "tracking"
    if kind == "edge":
        if fwd["ci_lo"] > BE_PCT:
            return "promoted"
        if fwd["ci_hi"] < BE_PCT:
            return "rejected"
    else:  # gate（回避）
        if fwd["ci_hi"] < BE_PCT:
            return "promoted"
        if fwd["ci_lo"] > BE_PCT:
            return "rejected"
    return "tracking"


def load_tracker():
    if os.path.exists(TRACKER):
        return json.load(open(TRACKER, encoding="utf-8-sig"))
    return {"updated_at": None, "breakeven_pct": BE_PCT, "promote_min_n": PROMOTE_MIN_N,
            "hypotheses": [dict(s) for s in SEED]}


def save_tracker(t):
    with open(TRACKER, "w", encoding="utf-8", newline="") as f:
        json.dump(t, f, ensure_ascii=False, indent=2)


def cmd_update(args, data, today):
    t = load_tracker()
    newly = []
    for h in t["hypotheses"]:
        fwd = stats(data, h["filter"], since=h["registered_at"])
        allt = stats(data, h["filter"])
        prev = h.get("status", "tracking")
        st = judge(h["kind"], fwd)
        # rejected は維持（戻さない）。promoted も維持。
        if prev in ("promoted", "rejected"):
            st = prev
        elif st in ("promoted", "rejected"):
            newly.append((h, st))
        h["forward"], h["alltime"], h["status"] = fwd, allt, st
        h.setdefault("history", [])
        h["history"].append({"date": today, "fwd_n": fwd["n"], "fwd_pct": fwd["pct"], "fwd_ci_lo": fwd["ci_lo"]})
        h["history"] = h["history"][-30:]  # 直近30点キープ
    t["updated_at"] = today
    save_tracker(t)

    print(f"=== 前向きトラッカー update（基準日 {today} / signals決済済 {sum(1 for d in data if closed(d))}件） ===")
    print(f"昇格基準: forward N≥{PROMOTE_MIN_N} ／ edge=CI下限>{BE_PCT:.0f}% ／ gate=CI上限<{BE_PCT:.0f}%")
    print(f"{'仮説':<26}{'種別':>5}{'登録日':>12}{'前向きk/n':>11}{'前向き勝率':>9}{'  前向き95%CI':>17}  状態")
    print("-" * 100)
    order = {"promoted": 0, "tracking": 1, "rejected": 2}
    for h in sorted(t["hypotheses"], key=lambda x: (order.get(x["status"], 9), -x["forward"]["n"])):
        fwd = h["forward"]
        ci = f"[{fwd['ci_lo']:.1f}~{fwd['ci_hi']:.1f}]"
        icon = {"promoted": "✅昇格", "tracking": "🟡蓄積中", "rejected": "⛔反証"}[h["status"]]
        print(f"{h['label']:<26}{h['kind']:>5}{h['registered_at']:>12}"
              f"{str(fwd['k'])+'/'+str(fwd['n']):>11}{fwd['pct']:>8.1f}%{ci:>17}  {icon}"
              f"  (全期間 {h['alltime']['k']}/{h['alltime']['n']}={h['alltime']['pct']:.0f}%)")
    if newly:
        print("-" * 100)
        print("🚩 今回ステータス変化（人間レビュー＝ライブ配信/信頼度への反映を検討）:")
        for h, st in newly:
            print(f"   - {h['label']}: {st}（前向き {h['forward']['k']}/{h['forward']['n']} = {h['forward']['pct']:.1f}%）")
    print("\n※ 昇格＝ライブ配信フィルタ/信頼度へ反映する“候補”の旗立てのみ。発火エンジンには自動で触れない（人間が最終反映）。")


def cmd_register(args, data, today):
    t = load_tracker()
    existing = {tuple(sorted(h["filter"].items())) for h in t["hypotheses"]}
    src = json.load(open(args.src, encoding="utf-8-sig"))
    added = 0
    for c in src.get("candidates", []):
        key = tuple(sorted(c["filter"].items()))
        if key in existing:
            continue
        kind = "edge" if c.get("pct", 0) >= BE_PCT else "gate"
        hid = "auto_" + "_".join(f"{k}-{v}" for k, v in sorted(c["filter"].items()))
        t["hypotheses"].append({
            "id": hid[:60], "label": c["label"], "filter": c["filter"], "kind": kind,
            "registered_at": today,
        })
        existing.add(key)
        added += 1
        print(f"  + 登録: {c['label']}（{kind}・registered_at={today}）")
    save_tracker(t)
    print(f"登録 {added}本（重複スキップ {len(src.get('candidates', [])) - added}本）。次に update で前向き計測。")


def cmd_table(args, data, today):
    t = load_tracker()
    rows = sorted(t["hypotheses"], key=lambda x: ({"promoted": 0, "tracking": 1, "rejected": 2}.get(x.get("status", "tracking"), 9), -x.get("forward", {}).get("n", 0)))
    if args.html:
        out = ['<h2 id="tracker">📡 前向きトラッカー定点観測</h2>',
               f'<p class="meta-line">基準日 {t.get("updated_at", today)}／昇格＝前向きN≥{PROMOTE_MIN_N}・損益分岐{BE_PCT:.0f}%をCIで突破</p>',
               '<table><tr><th>仮説</th><th>種別</th><th>宣言基準</th><th>前向き現在値</th><th>状態</th></tr>']
        crit = {"edge": f"前向きN≥{PROMOTE_MIN_N}かつCI下限>{BE_PCT:.0f}%", "gate": f"前向きN≥{PROMOTE_MIN_N}かつCI上限<{BE_PCT:.0f}%"}
        icon = {"promoted": "✅昇格", "tracking": "🟡蓄積中", "rejected": "⛔反証"}
        for h in rows:
            fwd = h.get("forward", {"k": 0, "n": 0, "pct": 0, "ci_lo": 0, "ci_hi": 0})
            val = f"{fwd['k']}/{fwd['n']} = {fwd['pct']:.1f}% CI[{fwd['ci_lo']:.1f}~{fwd['ci_hi']:.1f}]"
            out.append(f'<tr><td>{h["label"]}</td><td>{h["kind"]}</td><td>{crit[h["kind"]]}</td>'
                       f'<td>{val}</td><td>{icon[h.get("status","tracking")]}</td></tr>')
        out.append("</table>")
        print("\n".join(out))
    else:
        print(f"# 前向きトラッカー（基準日 {t.get('updated_at', today)}）")
        for h in rows:
            fwd = h.get("forward", {"k": 0, "n": 0, "pct": 0})
            print(f"- [{h.get('status','tracking')}] {h['label']}（{h['kind']}）: 前向き {fwd['k']}/{fwd['n']} = {fwd['pct']:.1f}%")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["update", "register", "table"])
    ap.add_argument("--from", dest="src", help="register: スイープのJSON")
    ap.add_argument("--date", help="基準日 YYYY-MM-DD（既定=今日）")
    ap.add_argument("--html", action="store_true", help="table: HTMLで出力")
    args = ap.parse_args()
    today = args.date or datetime.date.today().isoformat()
    data = load_log()
    if args.cmd == "update":
        cmd_update(args, data, today)
    elif args.cmd == "register":
        if not args.src:
            print("register には --from sweep.json が必要"); sys.exit(2)
        cmd_register(args, data, today)
    elif args.cmd == "table":
        cmd_table(args, data, today)


if __name__ == "__main__":
    main()
