# -*- coding: utf-8 -*-
"""
signal_lab_sweep.py — 仮説グリッドを「エンジンで全数検証」する発見スイープ。

設計（CLAUDE.md / SESSION_HANDOFF.md の方針）:
- LLM を使わず、signals-log.json を決定論で全数検証する（好きなだけ・ほぼ無料で回せる）。
- 検証ロジックは固定オラクル signal_lab_verify.py の部品をそのまま import（単一ソース＝捏造不能）。
- 多重検定（同じデータに多数の仮説を当てると偶然の“勝てそう”が必ず出る＝p-hacking）対策として
  Benjamini-Hochberg の FDR 補正を入れる。最小N で小サンプルの罠も除外。
- ここで「FDR を生き残った候補」を前向きトラッカー(signal_lab_tracker.py)に登録する流れ。
  ＝ 発見(in-sample)は仮説の“候補出し”、採否は前向き(out-of-sample)で判定する二段構え。

使い方:
    python signal_lab_sweep.py                 # 実データでスイープ→ランキング表示
    python signal_lab_sweep.py --json out.json # 候補を JSON 出力（トラッカー登録用）
    python signal_lab_sweep.py --min-n 15      # 最小N変更（既定20）
    python signal_lab_sweep.py --alpha 0.10    # FDR の α（既定0.10）
    python signal_lab_sweep.py --log signals-log-backtest.json --min-n 50 --split 2021-01-01
        # 🕰️ 時間分割ホールドアウト（2026-07-02 導入）:
        #   発見(グリッド全数＋FDR)を split より前のデータだけで行い、split 以降は一度も探索に
        #   触れない検証専用データとして FDR 通過候補を再評価する。ホールドアウトでも
        #   同方向に有意（edge=R CI下限>0 / gate=R CI上限<0、N≥holdout-min-n）なら holdout_pass。
        #   合格候補はトラッカー側の事前登録ルールで前向きN基準が 80→30 に緩和される
        #   （擬似out-of-sampleを数千件通過済みのため。基準は signal_lab_tracker.py にコード化）。

終了コード: 0 正常 / 2 引数エラー。
"""
import argparse
import itertools
import json
import os
import sys
from math import comb, erf, sqrt

# 固定オラクルの部品を再利用（編集しない・import のみ）
from signal_lab_verify import (
    GROUPS, REV, ALLOWED_FILTER_KEYS, wilson, closed, win, match, compute, get_trend,
)

ROOT = os.path.dirname(os.path.abspath(__file__))
BREAKEVEN = 0.43  # R:R 1:1.33（TP1=2.0ATR / SL=1.5ATR）の損益分岐勝率
TFS = ("1h", "4h", "1d")
DIRECTIONS = ("long", "short")
TRENDS = ("上昇", "下降", "中立・もみあい")


def load_log(path=None):
    if path:
        p = path if os.path.isabs(path) else os.path.join(ROOT, path)
    else:
        p = os.path.join(ROOT, "signals-log.json")
        if not os.path.exists(p):
            alt = os.path.join(ROOT, "_signals_live.json")
            if os.path.exists(alt):
                p = alt
    return json.load(open(p, encoding="utf-8-sig"))


def binom_p_ge(k, n, p):
    """P(X>=k) ／ X~Binomial(n,p)。n は最大でも数百なので厳密計算で十分。"""
    return sum(comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1))


def binom_p_le(k, n, p):
    """P(X<=k)。"""
    return sum(comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(0, k + 1))


def _norm_cdf(x):
    return 0.5 * (1 + erf(x / sqrt(2)))


def two_sided_p(k, n, p0=BREAKEVEN):
    """損益分岐 p0 と有意に異なるかの両側 p 値（方向は別途 pct で判定）。
    n≤1000 は厳密二項、それ超は正規近似（厳密だと comb が桁あふれ＋近似で十分）。"""
    if n <= 1000:
        up = binom_p_ge(k, n, p0)
        down = binom_p_le(k, n, p0)
        return min(1.0, 2.0 * min(up, down))
    se = sqrt(p0 * (1 - p0) / n)
    if se == 0:
        return 1.0
    z = (k / n - p0) / se
    return max(0.0, min(1.0, 2.0 * (1 - _norm_cdf(abs(z)))))


def signal_types(data):
    s = set()
    for d in data:
        ps = d.get("primary_signal")
        if ps:
            s.add(ps)
    return sorted(s)


def build_grid(data):
    """検証する仮説（filter dict）を列挙。組合せ爆発を避けるため厳選した1次元＋意味のある2次元。"""
    sigs = signal_types(data)
    grid = []

    def add(label, f):
        grid.append((label, f))

    # --- 1次元 ---
    for g in list(GROUPS.keys()) + ["all"]:
        add(f"group={g}", {"group": g})
    for tf in TFS:
        add(f"tf={tf}", {"tf": tf})
    for di in DIRECTIONS:
        add(f"dir={di}", {"direction": di})
    for tr in TRENDS:
        add(f"trend={tr}", {"trend": tr})
    add("reversalL（逆張り買い）", {"reversal_long": True})
    add("blocked=True（runway阻害）", {"blocked": True})
    add("blocked=False", {"blocked": False})
    for s in sigs:
        add(f"signal={s}", {"signal": s})
    # 選別タグ（エンジン既存・elite/good/neutral/avoid が期待値で分かれるか）
    for tier in ("elite", "good", "neutral", "avoid"):
        add(f"tier={tier}", {"tier": tier})
    for tier in ("elite", "good"):
        add(f"tier={tier}×dir=long", {"tier": tier, "direction": "long"})

    # --- 2次元（意味のある組合せのみ） ---
    for g in GROUPS.keys():
        add(f"group={g}×reversalL", {"group": g, "reversal_long": True})
    for di in DIRECTIONS:
        for g in GROUPS.keys():
            add(f"group={g}×dir={di}", {"group": g, "direction": di})
    for tr in TRENDS:  # 押し目買い vs 落ちるナイフ（本命）
        add(f"trend={tr}×reversalL", {"trend": tr, "reversal_long": True})
    for tf in TFS:
        add(f"tf={tf}×reversalL", {"tf": tf, "reversal_long": True})
    for tr in TRENDS:
        for di in DIRECTIONS:
            add(f"trend={tr}×dir={di}", {"trend": tr, "direction": di})
    for di in DIRECTIONS:
        add(f"blocked=True×dir={di}", {"blocked": True, "direction": di})
        add(f"blocked=False×dir={di}", {"blocked": False, "direction": di})
    for tf in TFS:
        for di in DIRECTIONS:
            add(f"tf={tf}×dir={di}", {"tf": tf, "direction": di})

    # --- 🆕 2026-07-19 ファンダ次元（オーナー依頼・既に全件記録済みの environment/risk_regime を解禁） ---
    #   ⚠️ 過去の教訓: ファンダの「方向一致ゲート」は逆転して棄却済（Layer1 11.8% vs 不一致56.6%）。
    #   ここで検証するのは方向でなく「地合い条件付け」（RISK_ON 72.7%/n11 の監視項目を大Nで正式検定）。
    #   バックテストログには無い次元＝ライブログ実行時のみセルが立つ（N不足はmin_nで自然に落ちる）。
    for e in ("A", "B", "C", "D"):
        add(f"env={e}", {"env": e})
        add(f"env={e}×dir=long", {"env": e, "direction": "long"})
    for rg in ("RISK_ON", "RISK_OFF", "NEUTRAL"):
        add(f"regime={rg}", {"regime": rg})
        add(f"regime={rg}×dir=long", {"regime": rg, "direction": "long"})

    # --- 🆕 2026-07-19 コンフルエンス（2指標の同時発火・オーナー依頼「最低2つの組み合わせ」） ---
    #   事前宣言: ペアは渡されたデータ（--split時はtrainのみ＝holdout非接触）内の共起 support≥40 だけを
    #   列挙（希薄セルの検定濫発を防ぐ）。3指標以上は列挙しない。多重性はFDRが補正。
    pair_cnt = {}
    for d in data:
        ts = sorted(set(d.get("signal_types") or []))
        for i in range(len(ts)):
            for j in range(i + 1, len(ts)):
                pair_cnt[(ts[i], ts[j])] = pair_cnt.get((ts[i], ts[j]), 0) + 1
    for (a, b), c in sorted(pair_cnt.items()):
        if c >= 40:
            add(f"combo={a}+{b}", {"signals_all": [a, b]})

    # --- 🆕 2026-07-20 指標ステート次元（オーナー依頼「指標の組み合わせ研究」・人間による正式拡張） ---
    #   事前宣言: バンド境界は verify.py の rsi_band_of/ma_pos_of/macd_side_of（数式ロック）。
    #   クロスは {direction, trend, reversal_long, signal} × {rsi_band, ma_pos, macd_side} に限定し、
    #   signal×ステートは渡されたデータ（--split時はtrainのみ＝holdout非接触）内の support≥40 だけ列挙
    #   （コンフルエンスのペア列挙と同じルール）。3重クロスは列挙しない。多重性はFDRが補正。
    #   macd/bb はバックテストログに記録なし＝ライブ実行時のみセルが立つ（N不足はmin_nで自然に落ちる）。
    from signal_lab_verify import rsi_band_of, ma_pos_of, macd_side_of
    RSI_BANDS = ("os", "low", "mid", "high", "ob")
    MA_POSES = ("above_both", "below_both", "above25_only", "above75_only")
    MACD_SIDES = ("pos", "neg")
    for b in RSI_BANDS:
        add(f"rsi={b}", {"rsi_band": b})
        for di in DIRECTIONS:
            add(f"rsi={b}×dir={di}", {"rsi_band": b, "direction": di})
        for tr in TRENDS:
            add(f"rsi={b}×trend={tr}", {"rsi_band": b, "trend": tr})
    for mp in MA_POSES:
        add(f"ma={mp}", {"ma_pos": mp})
        for di in DIRECTIONS:
            add(f"ma={mp}×dir={di}", {"ma_pos": mp, "direction": di})
        add(f"ma={mp}×reversalL", {"ma_pos": mp, "reversal_long": True})
    for ms in MACD_SIDES:
        add(f"macd={ms}", {"macd_side": ms})
        for di in DIRECTIONS:
            add(f"macd={ms}×dir={di}", {"macd_side": ms, "direction": di})
    state_cnt = {}
    for d in data:
        s = d.get("primary_signal")
        if not s:
            continue
        for dim, val in (("rsi_band", rsi_band_of(d)), ("ma_pos", ma_pos_of(d)), ("macd_side", macd_side_of(d))):
            if val is not None:
                state_cnt[(s, dim, val)] = state_cnt.get((s, dim, val), 0) + 1
    for (s, dim, val), c in sorted(state_cnt.items()):
        if c >= 40:
            short = {"rsi_band": "rsi", "ma_pos": "ma", "macd_side": "macd"}[dim]
            add(f"signal={s}×{short}={val}", {"signal": s, dim: val})

    # filter の重複（同一 dict）を除去（signals_all のリスト値も扱えるよう JSON キー化）
    seen, uniq = set(), []
    for label, f in grid:
        key = json.dumps(f, sort_keys=True, ensure_ascii=False)
        if key in seen:
            continue
        seen.add(key)
        uniq.append((label, f))
    return uniq


def r_of(rec):
    """outcome → 実現Rマルチプル（SL=1.5ATR=-1R / TP1=2.0ATR=+1.33R / TP2=3.0ATR=+2R）。"""
    return {"tp2": 2.0, "tp1": 4.0 / 3.0, "sl": -1.0}.get(rec.get("outcome"))


# ─────────────────────────────────────────
# 取引コスト（2026-07-03 方法論監査で導入）
# 往復スプレッドの概算。⚠️ブローカー実約定で要更新（規律ループの実スリッページ実測と接続予定）。
# R換算 = spread × mult ÷ |entry−SL|（mult=1.5 はスプレッド＋滑り分の保守係数）。
# ⚠️設計注意: 20年で価格が数十倍動く資産（BTC/金/指数）に現在基準の絶対額スプレッドを適用すると
#   過去年代のコストが数R相当に化ける（例: 2015年BTC$300に$35は約10%）→ FX以外は【価格比%】で持つ。
#   FXはpip絶対額が市場慣行として安定（レンジ相場・桁ドリフトなし）なので絶対額のまま。
# 表に無い ticker はコスト0（グロス扱い）＝過大控除より過小控除を選ぶ（不明分は正直にグロス）。
# ─────────────────────────────────────────
SPREAD_PCT = {                       # entry価格に対する往復スプレッド比率
    "GC=F": 0.00015, "SI=F": 0.0008, "CL=F": 0.0005,
    "NKD=F": 0.0002, "ES=F": 0.0001, "NQ=F": 0.00008, "YM=F": 0.00008, "^FTSE": 0.0002,
    "BTC-USD": 0.0004,
}


def cost_r_of(d, mult=1.5):
    """1取引の往復コストをR単位で返す（SL幅=1.5ATRを1Rとして換算）。不明は0＝グロス扱い。"""
    entry, sl = d.get("entry"), d.get("stop_loss")
    if not entry or not sl or entry == sl:
        return 0.0
    t = (d.get("ticker") or "")
    if t in SPREAD_PCT:
        sp = entry * SPREAD_PCT[t]            # 価格比＝年代をまたいでもコスト規模が自然
    elif t.endswith("=X"):                    # FX: JPYクロス=0.8pip / その他=1.2pip 相当（絶対額）
        sp = 0.008 if "JPY" in t.upper() else 0.00012
    else:
        return 0.0
    return sp * mult / abs(entry - sl)


def r_used(d, net=False, cost_mult=1.5, itt=False):
    """検定に使うR。itt=True なら expired を 0R（満了フラット決済の近似）で算入＝
    「解決した取引だけの条件付き期待値」バイアス（expired≈15%除外）を是正する intent-to-treat。
    net=True なら往復コストを控除（expired もスプレッドは払っている＝控除対象）。"""
    r = r_of(d)
    if r is None:
        if itt and d.get("outcome") == "expired":
            r = 0.0
        else:
            return None
    return r - cost_r_of(d, cost_mult) if net else r


def _mean_std(xs):
    n = len(xs)
    if n == 0:
        return 0.0, 0.0
    m = sum(xs) / n
    if n < 2:
        return m, 0.0
    return m, (sum((x - m) ** 2 for x in xs) / (n - 1)) ** 0.5


def fired_date(d):
    return (d.get("fired_at") or "")[:10]


def cluster_stats(matched, **mode):
    """期待値Rの平均と【日付クラスタ・ロバストSE】を返す（2026-07-03 方法論監査で導入）。

    従来の SE=sd/√n は全シグナルを独立扱いだが、実際は18銘柄が同じ日に束で発火する
    （同日複数発火≈25%）＝実効Nが見かけより小さく、p値が過小＝FDRを通りすぎていた。
    同じ発火日を1クラスタとして誤差を測る（CR0×G/(G-1)小標本補正・決定論＝乱数不使用）。
    各日1件なら従来の sd/√n に一致する（後方互換）。"""
    groups = {}
    for d in matched:
        r = r_used(d, **mode)
        if r is None:
            continue
        groups.setdefault(fired_date(d), []).append(r)
    xs = [x for g in groups.values() for x in g]
    n, G = len(xs), len(groups)
    if n == 0:
        return 0.0, 0.0, 0
    m = sum(xs) / n
    if G < 2:
        return m, 0.0, G
    var = sum((sum(g) - len(g) * m) ** 2 for g in groups.values()) * G / (G - 1) / (n * n)
    return m, var ** 0.5, G


def eval_stats(data, f, **mode):
    """1仮説を与えられたデータで評価（勝率＋期待値R＋95%CI）。ホールドアウト再評価用。
    R の SE は日付クラスタ補正（cluster_stats）。勝率の Wilson CI は表示用の参考値
    （独立仮定のまま＝判定には期待値R側を使う）。mode: net/cost_mult/itt（r_used参照）。"""
    m_res = [d for d in data if closed(d) and match(d, f)]
    m_exp = [d for d in data if d.get("outcome") == "expired" and match(d, f)]
    matched = m_res + m_exp if mode.get("itt") else m_res
    n = len(matched)
    k = sum(1 for d in m_res if win(d))
    lo, hi = wilson(k, n)
    meanR, seR, n_days = cluster_stats(matched, **mode)
    exp_pct = round(100 * len(m_exp) / (len(m_res) + len(m_exp)), 1) if (m_res or m_exp) else 0.0
    return {"k": k, "n": n, "pct": round(100 * k / n, 1) if n else 0.0,
            "ci_lo": round(lo, 1), "ci_hi": round(hi, 1), "avgR": round(meanR, 3),
            "rci_lo": round(meanR - 1.96 * seR, 3), "rci_hi": round(meanR + 1.96 * seR, 3),
            "n_days": n_days, "exp_pct": exp_pct}


def sweep(data, min_n, alpha, **mode):
    """各仮説の勝率＋【期待値(平均R)】を集計し、「期待値≠0」でBH-FDR判定（＝本当に黒字か）。
    mode: net=コスト控除 / itt=expiredを0R算入（r_used参照）。exp%はどのモードでも常時表示。"""
    rows = []
    for label, f in build_grid(data):
        m_res = [d for d in data if closed(d) and match(d, f)]
        m_exp = [d for d in data if d.get("outcome") == "expired" and match(d, f)]
        matched = m_res + m_exp if mode.get("itt") else m_res
        n = len(matched)
        if n < min_n:
            continue
        k = sum(1 for d in m_res if win(d))
        pct = 100 * k / n
        lo, hi = wilson(k, n)
        # 2026-07-03: SE を日付クラスタ補正に変更（同日相関の独立扱い＝実効N過大を是正）
        meanR, seR, n_days = cluster_stats(matched, **mode)
        if seR > 0:
            pR = max(0.0, min(1.0, 2 * (1 - _norm_cdf(abs(meanR / seR)))))  # 期待値≠0 の両側p
        else:
            pR = 1.0
        exp_pct = round(100 * len(m_exp) / (len(m_res) + len(m_exp)), 1) if (m_res or m_exp) else 0.0
        rows.append({
            "label": label, "filter": f, "k": k, "n": n, "n_days": n_days, "pct": round(pct, 1),
            "ci_lo": round(lo, 1), "ci_hi": round(hi, 1),
            "avgR": round(meanR, 3), "rci_lo": round(meanR - 1.96 * seR, 3),
            "rci_hi": round(meanR + 1.96 * seR, 3), "p": pR, "profitable": meanR > 0,
            "exp_pct": exp_pct,
        })

    # Benjamini-Hochberg FDR（期待値検定の p に対して）
    m = len(rows)
    ordered = sorted(range(m), key=lambda i: rows[i]["p"])
    qvals = [0.0] * m
    prev = 1.0
    for rank in range(m, 0, -1):
        i = ordered[rank - 1]
        prev = min(prev, rows[i]["p"] * m / rank)
        qvals[i] = min(1.0, prev)
    thresh_rank = 0
    for rank in range(1, m + 1):
        if rows[ordered[rank - 1]]["p"] <= (rank / m) * alpha:
            thresh_rank = rank
    reject = set(ordered[:thresh_rank])
    for i, r in enumerate(rows):
        r["q"] = round(qvals[i], 4)
        r["fdr_pass"] = i in reject
    return rows, m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-n", type=int, default=20, help="最小サンプル数（既定20）")
    ap.add_argument("--alpha", type=float, default=0.10, help="FDRのα（既定0.10）")
    ap.add_argument("--json", help="候補をJSON出力するパス（トラッカー登録用）")
    ap.add_argument("--log", help="検証する signals-log のパス（既定=signals-log.json。バックテストは signals-log-backtest.json）")
    ap.add_argument("--split", help="時間分割ホールドアウト: この日付より前だけで発見(FDR)し、以降は未接触の検証専用（例 2021-01-01）")
    ap.add_argument("--holdout-min-n", type=int, default=30, help="ホールドアウト合格に必要な最小N（既定30）")
    ap.add_argument("--net", action="store_true", help="往復スプレッドをR換算で控除（SPREADS表・概算）")
    ap.add_argument("--cost-mult", type=float, default=1.5, help="コスト係数（スプレッド×この値。滑り込みの保守既定1.5）")
    ap.add_argument("--itt", action="store_true", help="expired を 0R で算入（intent-to-treat＝解決分だけの条件付き期待値バイアスを是正）")
    args = ap.parse_args()
    mode = {"net": args.net, "cost_mult": args.cost_mult, "itt": args.itt}

    data = load_log(args.log)
    resolved = [d for d in data if closed(d)]
    n_expired = sum(1 for d in data if d.get("outcome") == "expired")

    if args.split:
        train = [d for d in data if fired_date(d) < args.split]
        hold = [d for d in data if fired_date(d) >= args.split]
        rows, m = sweep(train, args.min_n, args.alpha, **mode)
        n_hold = sum(1 for d in hold if closed(d))
        # FDR通過候補だけをホールドアウトで再評価（探索に使っていないデータ＝擬似out-of-sample）
        for r in rows:
            if not r["fdr_pass"]:
                continue
            ho = eval_stats(hold, r["filter"], **mode)
            # 合格条件（事前登録）: ホールドアウトN≥最小N かつ train と同方向に有意
            if r["profitable"]:
                ok = ho["n"] >= args.holdout_min_n and ho["rci_lo"] > 0
            else:
                ok = ho["n"] >= args.holdout_min_n and ho["rci_hi"] < 0
            r["holdout"], r["holdout_pass"] = ho, ok
    else:
        train, hold, n_hold = data, [], 0
        rows, m = sweep(data, args.min_n, args.alpha, **mode)

    print("=== signal-lab スイープ（期待値R）===")
    if args.split:
        print(f"🕰️ 時間分割: 発見={args.split}より前（決済済 {sum(1 for d in train if closed(d))}件）／"
              f"ホールドアウト={args.split}以降（決済済 {n_hold}件・探索未接触）")
    print(f"signals-log {len(data)}件（決済済 {len(resolved)}件・expired {n_expired}件"
          f"={100 * n_expired / max(len(resolved) + n_expired, 1):.0f}%） / 検証仮説 {m}本（N≥{args.min_n}） / "
          f"R: SL=-1.0 / TP1=+1.33 / TP2=+2.0 / FDR α={args.alpha}（期待値≠0を検定・SE=日付クラスタ補正）")
    print(f"モード: R={'ネット（スプレッド×' + str(args.cost_mult) + ' 控除）' if args.net else 'グロス（コスト未控除）'} / "
          f"expired={'0Rで算入（ITT）' if args.itt else '除外（解決分のみ＝条件付き期待値・exp%列で規模を明示）'}")
    print(f"{'仮説':<34}{'k/n':>9}{'勝率':>7}{'  平均R':>9}{'  R 95%CI':>18}{'  q':>8}{'exp%':>7}  判定")
    print("-" * 117)
    rows.sort(key=lambda r: (not r["fdr_pass"], r["q"], -r["avgR"]))
    for r in rows:
        flag = ("✅FDR" if r["fdr_pass"] else "  ") + ("黒字" if r["profitable"] else "赤字")
        if r["exp_pct"] > 20 and not args.itt:
            flag += "⚠exp"        # expired比率が高い＝除外バイアス大の警告（--itt で確認推奨）
        rci = f"[{r['rci_lo']:+.2f}~{r['rci_hi']:+.2f}]"
        print(f"{r['label']:<34}{str(r['k'])+'/'+str(r['n']):>9}{r['pct']:>6.1f}%{r['avgR']:>+9.3f}{rci:>18}{r['q']:>8.3f}{r['exp_pct']:>6.1f}%  {flag}")

    winners = [r for r in rows if r["fdr_pass"] and r["profitable"]]
    losers = [r for r in rows if r["fdr_pass"] and not r["profitable"]]
    print("-" * 110)
    print(f"✅黒字エッジ（期待値プラスが有意・FDR通過）: {len(winners)}本"
          + ("＝" + "、".join(f"{r['label']}(R{r['avgR']:+.2f})" for r in winners) if winners else "（なし）"))
    print(f"⛔赤字（期待値マイナスが有意・回避）: {len(losers)}本"
          + ("＝" + "、".join(f"{r['label']}(R{r['avgR']:+.2f})" for r in losers) if losers else "（なし）"))
    print("※ in-sample の候補出し。採否はライブ前向きトラッカーで out-of-sample 確認。")

    if args.split:
        passed = [r for r in rows if r.get("holdout_pass")]
        failed = [r for r in rows if r["fdr_pass"] and not r.get("holdout_pass")]
        print("-" * 110)
        print(f"🕰️ ホールドアウト検証（{args.split}以降・探索未接触・合格=同方向に有意かつN≥{args.holdout_min_n}）:")
        for r in sorted(rows, key=lambda x: not x.get("holdout_pass", False)):
            if not r["fdr_pass"]:
                continue
            ho = r["holdout"]
            mark = "🏁合格" if r["holdout_pass"] else "❌不合格"
            print(f"   {mark} {r['label']:<30} train R{r['avgR']:+.3f} → holdout R{ho['avgR']:+.3f} "
                  f"CI[{ho['rci_lo']:+.2f}~{ho['rci_hi']:+.2f}] ({ho['k']}/{ho['n']})")
        print(f"   → 合格 {len(passed)}本 / 不合格 {len(failed)}本。"
              f"合格は tracker register で前向きN基準 80→30 に緩和（事前登録ルール）。")

    if args.json:
        out = {"min_n": args.min_n, "alpha": args.alpha, "breakeven_pct": BREAKEVEN * 100,
               "mode": mode,
               "candidates": [r for r in rows if r["fdr_pass"]]}  # winners/losers両方＝tracker登録用
        if args.split:
            out["split"] = args.split
            out["holdout_min_n"] = args.holdout_min_n
        # データが単一時間足（例: 日足バックテスト）なら明記＝tracker側で tf=1d 登録済み仮説と突合できる
        tfs = {d.get("timeframe") for d in data if closed(d)}
        if len(tfs) == 1:
            out["uniform_tf"] = next(iter(tfs))
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(f"→ FDR通過 {len(out['candidates'])}本を {args.json} に出力（トラッカー登録用）。")
        print(f"⚠️ 必須（routine向け）: {args.json} を 8-1 のコミットに必ず含めること（git show --stat HEAD で確認）。")


if __name__ == "__main__":
    main()
