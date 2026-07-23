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
  🆕 2026-07-19 昇格入口の対称化（オーナー承認・以後の新規昇格に適用＝既存昇格へは不遡及）:
    (1) 昇格は基準合格がチェックポイント2回連続（promote_strikes）ではじめて確定
        ＝降格の2ストライクと対称。1回のラッキーCPによる winner's curse 昇格を防ぐ
        （実例: 指数×ロングは N43-60 の初期好調1回で昇格→N212 で R+0.05 まで平均回帰）。
    (2) holdout_pass=False（時間分割ホールドアウトで不合格が確定）の仮説はライブCIのみで昇格しない
        （holdout 未評価=None はブロックしない＝ライブ専用仮説を永久昇格不能にしないため）。
    反証(rejected)は従来どおり1CPで確定（エッジに不利方向＝保守側なので非対称のまま）。
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
from signal_lab_sweep import BREAKEVEN, load_log, r_of, _mean_std

ROOT = os.path.dirname(os.path.abspath(__file__))
TRACKER = os.path.join(ROOT, "signal-lab-tracker.json")
PROMOTE_MIN_N = 80          # 昇格に必要な前向きN（既存基準 N≥80）

# 🆕 2026-07-21 ユニバース凍結（1d拡張と同時導入・オーナー承認）:
#   generate_technical_alerts.py の SYMBOLS_1D_EXTRA（銅/プラチナ/天然ガス/米10年債/ETH/DAX/HSI/SOX）は
#   記録専用レーン。既存仮説は「18銘柄ユニバース」を前提に事前登録されているため、拡張銘柄が
#   direction/state 等の group 無しフィルタ経由で前向きNに混入すると母集団が途中で変わる＝前向き検証の汚染。
#   → トラッカーの全集計はこの凍結ユニバースに限定する（生ログ signals-log は全銘柄を記録し続ける）。
#   拡張銘柄を含む仮説を検証したくなったら、人間が GROUPS 正式拡張＋新Q事前登録をしてから。
LEGACY_UNIVERSE = frozenset({
    "GC=F", "SI=F", "CL=F", "NKD=F", "ES=F", "NQ=F", "YM=F", "^FTSE", "BTC-USD",
    "USDJPY=X", "EURJPY=X", "GBPJPY=X", "AUDJPY=X",
    "EURUSD=X", "GBPUSD=X", "AUDUSD=X", "EURAUD=X", "GBPAUD=X",
})


def freeze_universe(data):
    """トラッカー集計用に凍結ユニバース（18銘柄）へ絞る。除外件数を表示（沈黙の欠落防止）。"""
    kept = [d for d in data if d.get("ticker") in LEGACY_UNIVERSE]
    dropped = len(data) - len(kept)
    if dropped:
        print(f"🧊 ユニバース凍結: 1d拡張銘柄の {dropped} 件を集計から除外（記録は signals-log に残存）")
    return kept


# 🆕 2026-07-23 Q23 拡張ユニバース正式組入れ（人間による正式拡張・事前登録済み）:
#   signal_lab_verify.GROUPS に新設した拡張 group（既存 group と非重複）を filter に持つ仮説だけ、
#   凍結を迂回して全量データで集計する。既存仮説（group 無し含む）は従来どおり18銘柄凍結＝汚染なし。
EXTENDED_GROUPS = frozenset({"metal_x", "energy_x", "rates", "crypto_x", "index_x"})


def pick_data(h, frozen, full):
    """仮説ごとの集計データ選択: 拡張group仮説=全量 / それ以外=凍結ユニバース。"""
    return full if (h.get("filter") or {}).get("group") in EXTENDED_GROUPS else frozen
# 🕰️ 事前登録ルール（2026-07-02 宣言・以後変更しない）:
#   時間分割ホールドアウト（sweep --split。発見に一切使っていない直近数年で同方向に有意）を
#   合格した仮説は、擬似out-of-sampleを既に数百〜数千件通過しているため、ライブ前向きNの
#   要求を 80→30 に緩和する。ホールドアウト情報が無い仮説は従来どおり N≥80。
PROMOTE_MIN_N_HOLDOUT = 30
BE_PCT = BREAKEVEN * 100    # 43.0


def min_n_of(h):
    """仮説ごとの昇格に必要な前向きN（ホールドアウト合格なら緩和）。"""
    return PROMOTE_MIN_N_HOLDOUT if h.get("holdout_pass") else PROMOTE_MIN_N

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


# 🕰️ 2026-07-02 時間分割ホールドアウト検証の確定結果（コードが単一ソース・以後変更しない）。
#   実行: python signal_lab_sweep.py --log signals-log-backtest.json --min-n 50 --split 2021-01-01
#   発見=2006〜2020（決済済11,754件）／ホールドアウト=2021〜2026-06（決済済4,468件・探索に未使用）。
#   in-sample FDR通過26本 → ホールドアウト合格11本（15本は直近5年で有意性消失＝過学習を検出）。
#   tracker.json は GitHub 側で routine が更新するため、結果をここに固定し cmd_update が冪等に適用する。
#   annotate: 既存仮説への注記（pass=True なら昇格N基準 80→30）。register: 新規に前向き登録する合格仮説。
#   ※ index_long_live と dir=long 系は日足バックテスト由来の証拠（時間足は未検証）である点に留意。
HOLDOUT_2026_07_02 = {
    "annotate": {
        "metal_long_1d":   {"pass": True,  "holdout": {"k": 228, "n": 416,  "pct": 54.8, "avgR": 0.345,  "rci_lo": 0.226,  "rci_hi": 0.463}},
        "btc_long_1d":     {"pass": True,  "holdout": {"k": 128, "n": 272,  "pct": 47.1, "avgR": 0.164,  "rci_lo": 0.016,  "rci_hi": 0.313}},
        # index_revL_1d: 2026-07-03 クラスタ補正SEで再検定→FDR段階で脱落＝pass取消（旧CIは独立扱いの過小SE）
        "index_revL_1d":   {"pass": False, "holdout": {"k": 151, "n": 312,  "pct": 48.4, "avgR": 0.142,  "rci_lo": 0.011,  "rci_hi": 0.274}},
        "other_fx_1d":     {"pass": True,  "holdout": {"k": 390, "n": 1041, "pct": 37.5, "avgR": -0.113, "rci_lo": -0.183, "rci_hi": -0.043}},
        "index_long_1d":   {"pass": False, "holdout": {"k": 457, "n": 1028, "pct": 44.5, "avgR": 0.05,   "rci_lo": -0.022, "rci_hi": 0.122}},
        "index_long_live": {"pass": False, "holdout": {"k": 457, "n": 1028, "pct": 44.5, "avgR": 0.05,   "rci_lo": -0.022, "rci_hi": 0.122}},
        # short_1d / dntrend_1d / rsi_oversold_edge は 2020年以前だけの発見スイープでは FDR を通らず＝注記なし（N≥80のまま）
    },
    "register": [
        {"id": "btc_all_1d", "label": "BTC全方向(日足)", "filter": {"group": "btc"}, "kind": "edge", "registered_at": "2026-07-02",
         "holdout_pass": True, "holdout": {"k": 166, "n": 363, "pct": 45.7, "avgR": 0.137, "rci_lo": 0.008, "rci_hi": 0.266}},
        {"id": "metal_all_1d", "label": "メタル全方向(日足)", "filter": {"group": "metal"}, "kind": "edge", "registered_at": "2026-07-02",
         "holdout_pass": True, "holdout": {"k": 290, "n": 591, "pct": 49.1, "avgR": 0.201, "rci_lo": 0.102, "rci_hi": 0.301}},
        {"id": "other_fx_revL", "label": "other_fx×逆張り買い(回避)", "filter": {"group": "other_fx", "reversal_long": True}, "kind": "gate", "registered_at": "2026-07-02",
         "holdout_pass": True, "holdout": {"k": 148, "n": 427, "pct": 34.7, "avgR": -0.183, "rci_lo": -0.29, "rci_hi": -0.077}},
        {"id": "other_fx_long", "label": "other_fx×ロング(回避)", "filter": {"group": "other_fx", "direction": "long"}, "kind": "gate", "registered_at": "2026-07-02",
         "holdout_pass": True, "holdout": {"k": 293, "n": 796, "pct": 36.8, "avgR": -0.126, "rci_lo": -0.206, "rci_hi": -0.046}},
        # ↓3本: 2026-07-03 クラスタ補正SEで holdout 不合格に転落＝holdout_pass=False（登録は維持・N=80の通常仮説として前向き蓄積）
        {"id": "unblocked_long", "label": "runway非阻害×ロング", "filter": {"blocked": False, "direction": "long"}, "kind": "edge", "registered_at": "2026-07-02",
         "holdout_pass": False, "holdout": {"k": 1150, "n": 2611, "pct": 44.0, "avgR": 0.053, "rci_lo": 0.007, "rci_hi": 0.099}},
        {"id": "long_all", "label": "ロング全般(全足)", "filter": {"direction": "long"}, "kind": "edge", "registered_at": "2026-07-02",
         "holdout_pass": False, "holdout": {"k": 1467, "n": 3324, "pct": 44.1, "avgR": 0.056, "rci_lo": 0.015, "rci_hi": 0.096}},
        {"id": "long_1d", "label": "ロング全般(日足)", "filter": {"tf": "1d", "direction": "long"}, "kind": "edge", "registered_at": "2026-07-02",
         "holdout_pass": False, "holdout": {"k": 1467, "n": 3324, "pct": 44.1, "avgR": 0.056, "rci_lo": 0.015, "rci_hi": 0.096}},
    ],
}

# 2026-07-03 方法論監査（クラスタ補正SE）による再スイープ＝FDR通過26→20・holdout合格11→7。
# 不合格に転じた4仮説の「N=30緩和」を剥奪し N=80 に戻す（オーナー決定 2026-07-03・冪等）。
# 旧合格は独立扱いの過小SEによる見せかけ＝剥奪はエッジに不利方向の保守化なので事前登録の精神に反しない。
HOLDOUT_REVOKE_2026_07_03 = ("index_revL_1d", "unblocked_long", "long_all", "long_1d")

# 🆕 2026-07-19 コンフルエンス（2指標同時発火）発見スイープの確定結果（オーナー依頼・確定後は変更しない）。
#   実行: python signal_lab_sweep.py --log signals-log-backtest.json --min-n 50 --split 2021-01-01
#   ペア次元 signals_all（train内共起 support≥40）。tracker.json はGitHub側でroutine更新のため冪等適用。
#   ⚠️ 1dバックテスト由来の証拠で全足ライブを前向き追跡する点は index_long_live 等と同じ留意。
#   結果: ペア14本中 train-FDR通過3本（ITT/ITT+netでも上位2本は頑健）→ 3本とも holdout(2021+)で
#   有意性消失＝holdout_pass=False で登録（2026-07-19昇格ルールにより live CI のみでの昇格は不可＝
#   前向き蓄積と定点観測のみ。ライブ現在値も high_break+rsi_overbought は R-0.26/n44 と逆向き）。
#   なお直感に反し「ダブル売られすぎ」bb_lower_touch+rsi_oversold_bounce は train R-0.153（q=0.15・FDR落ち）。
COMBO_2026_07_19 = {"register": [
    {"id": "combo_hb_rsiob", "label": "コンボ 高値ブレイク×RSI買われすぎ", "kind": "edge",
     "filter": {"signals_all": ["high_break", "rsi_overbought"]}, "registered_at": "2026-07-19",
     "holdout_pass": False,
     "holdout": {"k": 107, "n": 233, "pct": 45.9, "avgR": 0.112, "rci_lo": -0.05, "rci_hi": 0.27}},
    {"id": "combo_bbub_rsiob", "label": "コンボ +2σ突破×RSI買われすぎ", "kind": "edge",
     "filter": {"signals_all": ["bb_upper_break", "rsi_overbought"]}, "registered_at": "2026-07-19",
     "holdout_pass": False,
     "holdout": {"k": 66, "n": 141, "pct": 46.8, "avgR": 0.139, "rci_lo": -0.07, "rci_hi": 0.35}},
    {"id": "combo_db_hb", "label": "コンボ ダブルボトム×高値ブレイク", "kind": "edge",
     "filter": {"signals_all": ["double_bottom", "high_break"]}, "registered_at": "2026-07-19",
     "holdout_pass": False,
     "holdout": {"k": 14, "n": 31, "pct": 45.2, "avgR": 0.097, "rci_lo": -0.34, "rci_hi": 0.53}},
]}

# 🆕 2026-07-20 指標ステート組み合わせ発見スイープの確定結果（オーナー依頼「指標の組み合わせ研究」・確定後は変更しない）。
#   実行: python signal_lab_sweep.py --log signals-log-backtest.json --split 2021-01-01
#   新filterキー rsi_band/ma_pos（verify.py 2026-07-20拡張・数式ロック）。1dバックテスト由来の留意は COMBO と同じ。
#   結果: 新ステート族から holdout(2021+)合格4本（ma=above_both単体は above_both×long の上位集合のため登録は3本に絞る）＋
#   「RSI中立での逆張り」2本は train-FDR有意赤字→holdout方向維持だがCI 0跨ぎ＝holdout_pass=False の gate 定点観測。
#   ⚠️ ライブ直近窓(5/20-7/20)では過熱系合格2本（rsi=ob×上昇・above_both×long）が逆向き＝metal_longと同じ
#   「20年は本物・今は機能不全」パターンの可能性＝前向きトラッカーが最終法廷（昇格は2CP連続ルール）。
STATE_2026_07_20 = {"register": [
    {"id": "state_macdg_below", "label": "ステート MACDゴールデン×両MA下（底値圏転換）", "kind": "edge",
     "filter": {"signal": "macd_golden", "ma_pos": "below_both"}, "registered_at": "2026-07-20",
     "holdout_pass": True,
     "holdout": {"k": 125, "n": 254, "pct": 49.2, "avgR": 0.167, "rci_lo": 0.01, "rci_hi": 0.323}},
    {"id": "state_rsiob_uptrend", "label": "ステート RSI≥70×上昇トレンド（強さは続く）", "kind": "edge",
     "filter": {"rsi_band": "ob", "trend": "上昇"}, "registered_at": "2026-07-20",
     "holdout_pass": True,
     "holdout": {"k": 189, "n": 405, "pct": 46.7, "avgR": 0.151, "rci_lo": 0.017, "rci_hi": 0.286}},
    {"id": "state_maup_long", "label": "ステート 上昇配置（>MA25&75）×ロング", "kind": "edge",
     "filter": {"ma_pos": "above_both", "direction": "long"}, "registered_at": "2026-07-20",
     "holdout_pass": True,
     "holdout": {"k": 791, "n": 1747, "pct": 45.3, "avgR": 0.092, "rci_lo": 0.028, "rci_hi": 0.157}},
    {"id": "state_bblt_rsimid", "label": "ステート BB下限タッチ×RSI中立（弱い逆張り＝回避）", "kind": "gate",
     "filter": {"signal": "bb_lower_touch", "rsi_band": "mid"}, "registered_at": "2026-07-20",
     "holdout_pass": False,
     "holdout": {"k": 66, "n": 181, "pct": 36.5, "avgR": -0.134, "rci_lo": -0.308, "rci_hi": 0.039}},
    {"id": "state_sb_rsimid", "label": "ステート サポート反発×RSI中立（弱い逆張り＝回避）", "kind": "gate",
     "filter": {"signal": "support_bounce", "rsi_band": "mid"}, "registered_at": "2026-07-20",
     "holdout_pass": False,
     "holdout": {"k": 81, "n": 215, "pct": 37.7, "avgR": -0.096, "rci_lo": -0.265, "rci_hi": 0.072}},
]}


def _filter_key(f):
    """filter dict の同一性キー。🆕 2026-07-19: signals_all のリスト値でも壊れないよう JSON 化。"""
    return json.dumps(f, sort_keys=True, ensure_ascii=False)


def apply_holdout_bootstrap(t):
    """HOLDOUT_2026_07_02 / COMBO_2026_07_19 / STATE_2026_07_20 を tracker に冪等適用（注記は未設定の仮説のみ・登録は filter 非重複のみ）。"""
    changed = 0
    for h in t["hypotheses"]:
        ann = HOLDOUT_2026_07_02["annotate"].get(h.get("id"))
        if ann and "holdout_pass" not in h:
            h["holdout_pass"], h["holdout"] = ann["pass"], ann["holdout"]
            changed += 1
    existing = {_filter_key(h["filter"]) for h in t["hypotheses"]}
    for s in HOLDOUT_2026_07_02["register"] + COMBO_2026_07_19["register"] + STATE_2026_07_20["register"]:
        if _filter_key(s["filter"]) in existing:
            continue
        t["hypotheses"].append(json.loads(json.dumps(s)))  # deep copy
        existing.add(_filter_key(s["filter"]))
        changed += 1
    # 2026-07-03 剥奪の冪等適用（GitHub側 tracker.json には旧 pass=True が既に書かれているため）
    for h in t["hypotheses"]:
        if h.get("id") in HOLDOUT_REVOKE_2026_07_03 and h.get("holdout_pass"):
            h["holdout_pass"] = False
            h["holdout_note"] = "2026-07-03 クラスタ補正SEで再検定→不合格＝N30緩和を剥奪（N80に復帰）"
            changed += 1
    return changed


def fired_date(d):
    return (d.get("fired_at") or "")[:10]


def stats(data, f, since=None):
    rows = [d for d in data if closed(d) and match(d, f) and (since is None or fired_date(d) >= since)]
    n = len(rows)
    k = sum(1 for d in rows if win(d))
    lo, hi = wilson(k, n)
    pct = (100 * k / n) if n else 0.0
    # 2026-07-03: R の SE を日付クラスタ補正に変更（同日発火の相関＝実効N過大を是正。
    # CR0×G/(G-1)・決定論。各日1件なら従来の sd/√n に一致）
    groups = {}
    for d in rows:
        r = r_of(d)
        if r is not None:
            groups.setdefault(fired_date(d), []).append(r)
    Rs = [x for g in groups.values() for x in g]
    nR, G = len(Rs), len(groups)
    meanR = sum(Rs) / nR if nR else 0.0
    if G >= 2:
        seR = (sum((sum(g) - len(g) * meanR) ** 2 for g in groups.values()) * G / (G - 1)) ** 0.5 / nR
    else:
        seR = 0.0
    return {"k": k, "n": n, "pct": round(pct, 1), "ci_lo": round(lo, 1), "ci_hi": round(hi, 1),
            "avgR": round(meanR, 3), "rci_lo": round(meanR - 1.96 * seR, 3), "rci_hi": round(meanR + 1.96 * seR, 3)}


def judge(kind, fwd, min_n=PROMOTE_MIN_N):
    """方向対応の昇格判定（期待値ベース：前向き平均R の95%CIが0を跨がないか）。"""
    if fwd["n"] < min_n:
        return "tracking"
    if kind == "edge":
        if fwd["rci_lo"] > 0:   # 期待値プラスが有意＝本物のエッジ確認
            return "promoted"
        if fwd["rci_hi"] < 0:
            return "rejected"
    else:  # gate（回避）
        if fwd["rci_hi"] < 0:   # 期待値マイナスが有意＝回避確定
            return "promoted"
        if fwd["rci_lo"] > 0:
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


def cmd_update(args, data, today, data_full=None):
    t = load_tracker()
    boot = apply_holdout_bootstrap(t)
    if boot:
        print(f"🕰️ ホールドアウト検証(2026-07-02)を適用: 注記/新規登録 {boot}件")
    newly = []
    for h in t["hypotheses"]:
        dat = pick_data(h, data, data_full if data_full is not None else data)  # Q23: 拡張group仮説のみ全量
        fwd = stats(dat, h["filter"], since=h["registered_at"])
        allt = stats(dat, h["filter"])
        prev = h.get("status", "tracking")
        # 🆕 2026-07-03 チェックポイント検定: 毎日CIを覗く逐次検定は「たまたま越えた日」に
        #    昇格が確定してしまい実質αが膨張する。判定は前向きNが min_n の倍数
        #    （例 30/60/90…）を新たに越えたときだけ実施（look回数を日次→数回に削減）。
        mn = min_n_of(h)
        next_cp = ((h.get("last_eval_n", 0) // mn) + 1) * mn
        if prev == "rejected":
            st = prev                       # 反証はラチェット維持（終了扱い）
        elif prev == "promoted":
            # 🆕 2026-07-18 降格ルール（事前登録・オーナー承認＝案A）: 昇格後もチェック
            #    ポイントごとに再判定し、昇格基準を満たさない判定が【2回連続】したら
            #    tracking へ降格（＝昇格限定メールも自動停止。基準を再び満たせば再昇格可）。
            #    1回のCI揺れでは往復しないヒステリシス。従来の永久ラチェットは
            #    「期待値が減衰しても昇格が残る」非対称（7/18に3本とも基準割れで発覚）のため廃止。
            st = prev
            if fwd["n"] >= next_cp:
                h["last_eval_n"] = fwd["n"]
                if judge(h["kind"], fwd, mn) == "promoted":
                    h["demote_strikes"] = 0
                else:
                    h["demote_strikes"] = h.get("demote_strikes", 0) + 1
                    if h["demote_strikes"] >= 2:
                        st = "tracking"
                        h["demote_strikes"] = 0
                        h["demoted_at"] = today
                        newly.append((h, "demoted（降格＝基準割れ2回連続）"))
        elif fwd["n"] >= next_cp:
            h["last_eval_n"] = fwd["n"]
            verdict = judge(h["kind"], fwd, mn)
            st = "tracking"
            if verdict == "rejected":
                st = "rejected"              # 反証は従来どおり1CPで確定（保守側）
                newly.append((h, st))
            elif verdict == "promoted":
                # 🆕 2026-07-19 昇格入口の対称化（詳細は冒頭docstring）
                if h.get("holdout_pass") is False:
                    h["promote_block"] = "holdout_fail"   # ライブCIのみでの昇格を禁止
                else:
                    h.pop("promote_block", None)
                    h["promote_strikes"] = h.get("promote_strikes", 0) + 1
                    if h["promote_strikes"] >= 2:
                        st = "promoted"
                        h["promote_strikes"] = 0
                        h["promoted_at"] = today
                        newly.append((h, st))
            else:
                h["promote_strikes"] = 0     # 連続要件＝不合格CPでリセット
                h.pop("promote_block", None)
        else:
            st = "tracking"                 # チェックポイント未到達＝判定しない（蓄積のみ）
        h["forward"], h["alltime"], h["status"] = fwd, allt, st
        h.setdefault("history", [])
        h["history"].append({"date": today, "fwd_n": fwd["n"], "fwd_avgR": fwd["avgR"], "fwd_rci_lo": fwd["rci_lo"]})
        h["history"] = h["history"][-30:]  # 直近30点キープ
    t["updated_at"] = today
    save_tracker(t)

    print(f"=== 前向きトラッカー update（基準日 {today} / signals決済済 {sum(1 for d in data if closed(d))}件） ===")
    print(f"昇格基準（期待値ベース）: forward N≥{PROMOTE_MIN_N}（🏁ホールドアウト合格はN≥{PROMOTE_MIN_N_HOLDOUT}） "
          f"／ edge=平均RのCI下限>0 ／ gate=平均RのCI上限<0"
          f"\n判定方式（2026-07-03〜）: 日付クラスタ補正SE＋チェックポイント検定（Nがmin_nの倍数を越えた時のみ判定＝覗き見バイアス抑制）"
          f"\n降格（2026-07-18〜）: 昇格後もチェックポイントごとに再判定し、基準割れ2回連続で tracking へ降格（再昇格可・反証⛔のみラチェット）"
          f"\n昇格（2026-07-19〜）: 基準合格2回連続(promote_strikes)ではじめて昇格＝降格と対称。holdout不合格(False)確定の仮説はライブCIのみで昇格しない")
    print(f"{'仮説':<26}{'種別':>5}{'登録日':>12}{'前向きk/n':>11}{'勝率':>6}{'平均R':>8}{'  R 95%CI':>17}  状態")
    print("-" * 108)
    order = {"promoted": 0, "tracking": 1, "rejected": 2}
    for h in sorted(t["hypotheses"], key=lambda x: (order.get(x["status"], 9), -x["forward"]["n"])):
        fwd = h["forward"]
        rci = f"[{fwd['rci_lo']:+.2f}~{fwd['rci_hi']:+.2f}]"
        icon = {"promoted": "✅昇格", "tracking": "🟡蓄積中", "rejected": "⛔反証"}[h["status"]]
        ho = f" 🏁N≥{PROMOTE_MIN_N_HOLDOUT}" if h.get("holdout_pass") else ""
        print(f"{h['label']:<26}{h['kind']:>5}{h['registered_at']:>12}"
              f"{str(fwd['k'])+'/'+str(fwd['n']):>11}{fwd['pct']:>5.0f}%{fwd['avgR']:>+8.3f}{rci:>17}  {icon}"
              f"  (全期間R {h['alltime']['avgR']:+.2f}){ho}")
    if newly:
        print("-" * 108)
        print("🚩 今回ステータス変化（人間レビュー＝ライブ配信/信頼度への反映を検討）:")
        for h, st in newly:
            print(f"   - {h['label']}: {st}（前向き 平均R {h['forward']['avgR']:+.3f} / N={h['forward']['n']}）")
    print("\n※ 昇格＝ライブ配信フィルタ/信頼度へ反映する“候補”の旗立てのみ。発火エンジンには自動で触れない（人間が最終反映）。")
    # 2026-07-04: 7/3・7/4 に routine が tracker.json のコミットを2日連続で漏らした（8-1 の add 例に
    # 本ファイルが無く、注記が見落とされた）。実行主体への明示リマインドをコード側から出す。
    print("⚠️ 必須（routine向け）: signal-lab-tracker.json を更新した。8-1 のコミットに必ず含めること："
          "`git add drafts/ signal-lab-ledger.md signal-lab-tracker.json` → `git show --stat HEAD` で本ファイルが"
          "入ったことを確認。未コミットのままだと finalize_signal_lab.py が公開を拒否する。")


def cmd_register(args, data, today):
    t = load_tracker()
    by_key = {_filter_key(h["filter"]): h for h in t["hypotheses"]}
    src = json.load(open(args.src, encoding="utf-8-sig"))
    uniform_tf = src.get("uniform_tf")  # 例: 日足バックテスト由来なら "1d"
    added = annotated = 0
    for c in src.get("candidates", []):
        # 単一時間足ログ由来の候補は tf 付き登録済み仮説（例 SEED の tf=1d）とも同一視する
        keys = [_filter_key(c["filter"])]
        if uniform_tf and "tf" not in c["filter"]:
            keys.append(_filter_key(dict(c["filter"], tf=uniform_tf)))
        hit = next((by_key[k] for k in keys if k in by_key), None)
        if hit is not None:
            # 既存仮説＝登録はスキップ。ただしホールドアウト結果があれば注記（昇格基準の緩和に使う）
            if "holdout" in c:
                hit["holdout"], hit["holdout_pass"] = c["holdout"], bool(c.get("holdout_pass"))
                annotated += 1
                mark = "🏁合格" if hit["holdout_pass"] else "❌不合格"
                print(f"  ~ ホールドアウト注記: {hit['label']} {mark}"
                      f"（holdout R{c['holdout']['avgR']:+.2f} N={c['holdout']['n']}・前向きN基準 {min_n_of(hit)}）")
            continue
        # 期待値ベース：avgR>0 なら edge、<0 なら gate（avgR無しは勝率で代替）
        metric = c["avgR"] if c.get("avgR") is not None else (c.get("pct", 0) - BE_PCT)
        kind = "edge" if metric > 0 else "gate"
        hid = "auto_" + "_".join(
            f"{k}-{'+'.join(map(str, v)) if isinstance(v, list) else v}" for k, v in sorted(c["filter"].items()))
        h = {
            "id": hid[:60], "label": c["label"], "filter": c["filter"], "kind": kind,
            "registered_at": today,
        }
        if "holdout" in c:
            h["holdout"], h["holdout_pass"] = c["holdout"], bool(c.get("holdout_pass"))
        t["hypotheses"].append(h)
        by_key[keys[0]] = h
        added += 1
        ho = "・🏁ホールドアウト合格" if h.get("holdout_pass") else ""
        print(f"  + 登録: {c['label']}（{kind}・registered_at={today}{ho}）")
    save_tracker(t)
    print(f"登録 {added}本／ホールドアウト注記 {annotated}本"
          f"（重複スキップ {len(src.get('candidates', [])) - added - annotated}本）。次に update で前向き計測。")


def cmd_table(args, data, today):
    t = load_tracker()
    rows = sorted(t["hypotheses"], key=lambda x: ({"promoted": 0, "tracking": 1, "rejected": 2}.get(x.get("status", "tracking"), 9), -x.get("forward", {}).get("n", 0)))
    if args.html:
        out = ['<h2 id="tracker">📡 前向きトラッカー定点観測（期待値ベース）</h2>',
               f'<p class="meta-line">基準日 {t.get("updated_at", today)}／昇格＝前向きN≥{PROMOTE_MIN_N}'
               f'（🏁ホールドアウト合格はN≥{PROMOTE_MIN_N_HOLDOUT}）・平均R(期待値)の95%CIが0を跨がない'
               f'・基準合格2回連続で確定（2026-07-19〜）'
               f'／降格＝昇格後の再判定で基準割れ2回連続→🟡へ（2026-07-18〜・再昇格可）</p>',
               '<table><tr><th>仮説</th><th>種別</th><th>宣言基準</th><th>前向き現在値(平均R)</th><th>状態</th></tr>']
        icon = {"promoted": "✅昇格", "tracking": "🟡蓄積中", "rejected": "⛔反証"}
        for h in rows:
            fwd = h.get("forward", {"k": 0, "n": 0, "pct": 0, "avgR": 0, "rci_lo": 0, "rci_hi": 0})
            mn = min_n_of(h)
            ho = "🏁" if h.get("holdout_pass") else ""
            crit = (f"前向きN≥{mn}かつ平均RのCI下限>0" if h["kind"] == "edge"
                    else f"前向きN≥{mn}かつ平均RのCI上限<0") + ho
            val = f"平均R {fwd.get('avgR',0):+.2f} CI[{fwd.get('rci_lo',0):+.2f}~{fwd.get('rci_hi',0):+.2f}]（{fwd['k']}/{fwd['n']}・勝率{fwd['pct']:.0f}%）"
            out.append(f'<tr><td>{h["label"]}</td><td>{h["kind"]}</td><td>{crit}</td>'
                       f'<td>{val}</td><td>{icon[h.get("status","tracking")]}</td></tr>')
        out.append("</table>")
        print("\n".join(out))
    else:
        print(f"# 前向きトラッカー（基準日 {t.get('updated_at', today)}）")
        for h in rows:
            fwd = h.get("forward", {"k": 0, "n": 0, "avgR": 0})
            print(f"- [{h.get('status','tracking')}] {h['label']}（{h['kind']}）: 前向き 平均R {fwd.get('avgR',0):+.3f} / N={fwd['n']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["update", "register", "table"])
    ap.add_argument("--from", dest="src", help="register: スイープのJSON")
    ap.add_argument("--date", help="基準日 YYYY-MM-DD（既定=今日）")
    ap.add_argument("--html", action="store_true", help="table: HTMLで出力")
    args = ap.parse_args()
    today = args.date or datetime.date.today().isoformat()
    data_full = load_log()
    data = freeze_universe(data_full)
    if args.cmd == "update":
        cmd_update(args, data, today, data_full)
    elif args.cmd == "register":
        if not args.src:
            print("register には --from sweep.json が必要"); sys.exit(2)
        cmd_register(args, data, today)
    elif args.cmd == "table":
        cmd_table(args, data, today)


if __name__ == "__main__":
    main()
