# AIシグナル研究日誌 #099 解析ノート
# 基準日: 2026-09-15（JST）
# テーマ: rsi_oversold_bounce FWD N=343 RCI下限+0.012に回復
#         5日間のマイナス期脱出・4H足57%と上昇トレンド63%の二極構造

## 発見スイープ結果
- `python signal_lab_sweep.py --json drafts/labnotes/sweep-2026-09-15.json`
- FDR通過: 0本（なし）

## トラッカー更新
- `python signal_lab_tracker.py update --date 2026-09-15`
- ✅昇格変化: なし（trend=上昇×reversalL が引き続き✅昇格・CI[-0.04~+0.28]）
- ⛔反証変化: なし
- 注目: `売られすぎ逆張り買い(rsi_oversold_bounce・全足)` RCI_lo が -0.004(N=337, 2026-09-14) → +0.012(N=343, 2026-09-15)

## 題材選定
優先度 ②「前向きで大きく動いた仮説」
→ rsi_oversold_bounce: 9/9(N=320)以降5日間マイナスだったRCI_lo が今日N=343で+0.012に回復。

## 事前合否基準
- H1: FWD全体 RCI下限がプラス圏に回復したか（昇格基準: RCI_lo>0）→ 検証
- H2: 4H足 RCI_lo>0 を維持しているか → 検証
- H3: 1H足 RCI_lo は依然マイナスか → 検証
- H4: trend=上昇 RCI_lo>0 を維持しているか → 検証

## 集計スクリプト（全閉済みシグナル対象）

```python
import json, math
from collections import defaultdict

def wilson(k, n, z=1.96):
    if n == 0: return (0.0, 0.0)
    p = k/n
    denom = 1 + z**2/n
    center = (p + z**2/(2*n)) / denom
    spread = z * math.sqrt(p*(1-p)/n + z**2/(4*n**2)) / denom
    return (max(0, center-spread)*100, min(1, center+spread)*100)

def r_of(rec):
    # tp1=+4/3, tp2=+2.0, sl=-1.0（signal_lab_sweep.pyと同一）
    return {'tp2': 2.0, 'tp1': 4.0/3.0, 'sl': -1.0}.get(rec.get('outcome'))

def get_trend(d):
    ta = d.get('trend_alignment')
    if isinstance(ta, dict) and ta.get('higher_tf_trend'):
        return ta['higher_tf_trend']
    return 'unknown'

def analyze(sigs, label):
    rows = [s for s in sigs if r_of(s) is not None]
    n = len(rows)
    k = sum(1 for s in rows if s.get('outcome') in ('tp1','tp2'))
    if n == 0:
        print(f'{label}: N=0'); return
    ci = wilson(k, n)
    groups = defaultdict(list)
    for s in rows:
        date = (s.get('fired_at') or '')[:10]
        groups[date].append(r_of(s))
    Rs = [x for g in groups.values() for x in g]
    nR = len(Rs); G = len(groups)
    meanR = sum(Rs)/nR if nR else 0.0
    if G >= 2:
        seR = (sum((sum(g) - len(g)*meanR)**2 for g in groups.values()) * G / (G-1))**0.5 / nR
    else:
        seR = 0.0
    rci_lo = meanR - 1.96*seR
    rci_hi = meanR + 1.96*seR
    pct = k/n*100
    print(f'{label}: k={k}/n={n}={pct:.1f}% CI[{ci[0]:.1f}%,{ci[1]:.1f}%] avgR={meanR:.3f} RCI=[{rci_lo:.3f},{rci_hi:.3f}]')

with open('signals-log.json') as f:
    all_signals = json.load(f)

reg_date = '2026-06-16'
fwd = [s for s in all_signals
       if 'rsi_oversold_bounce' in s.get('signal_types', [])
       and r_of(s) is not None
       and s.get('fired_at','')[:10] >= reg_date]
is_sigs = [s for s in all_signals
           if 'rsi_oversold_bounce' in s.get('signal_types', [])
           and r_of(s) is not None
           and s.get('fired_at','')[:10] < reg_date]
```

## 生出力

```
=== Basic Stats ===
IS: k=52/n=133=39.1% CI[31.2%,47.6%] avgR=-0.088 RCI=[-0.240,0.065]
FWD全体: k=175/n=343=51.0% CI[45.7%,56.3%] avgR=0.190 RCI=[0.012,0.369]

=== Timeframe ===
FWD 4H: k=60/n=105=57.1% CI[47.6%,66.2%] avgR=0.333 RCI=[0.032,0.634]
FWD 1H: k=104/n=224=46.4% CI[40.0%,53.0%] avgR=0.083 RCI=[-0.130,0.297]
FWD 1D: k=11/n=14=78.6% CI[52.4%,92.4%] avgR=0.833 RCI=[0.351,1.315] ※N=14参考値

=== Trend ===
FWD trend=上昇: k=49/n=78=62.8% CI[51.7%,72.7%] avgR=0.466 RCI=[0.171,0.761]
FWD trend=下降: k=65/n=155=41.9% CI[34.5%,49.8%] avgR=-0.022 RCI=[-0.258,0.215]
FWD trend=中立・もみあい: k=61/n=110=55.5% CI[46.1%,64.4%] avgR=0.294 RCI=[0.062,0.526]

=== 4H x Trend ===
FWD 4H×上昇: k=22/n=32=68.8% CI[51.4%,82.0%] avgR=0.604 RCI=[0.261,0.948]
FWD 4H×下降: k=17/n=43=39.5% CI[26.4%,54.4%] avgR=-0.078 RCI=[-0.502,0.347]
FWD 4H×中立: k=21/n=30=70.0% CI[52.1%,83.3%] avgR=0.633 RCI=[0.205,1.062]

=== 1H x Trend ===
FWD 1H×上昇: k=18/n=36=50.0% CI[34.5%,65.5%] avgR=0.167 RCI=[-0.295,0.628]
FWD 1H×下降: k=46/n=110=41.8% CI[33.0%,51.2%] avgR=-0.024 RCI=[-0.340,0.292]
FWD 1H×中立: k=40/n=78=51.3% CI[40.4%,62.1%] avgR=0.197 RCI=[-0.038,0.432]

=== Recent Months ===
FWD 〜8月: k=140/n=264=53.0% CI[47.0%,59.0%] avgR=0.237 RCI=[0.024,0.451]
FWD 9月: k=35/n=79=44.3% CI[33.9%,55.3%] avgR=0.034 RCI=[-0.308,0.376]
FWD 9/9以降: k=11/n=21=52.4% CI[32.4%,71.7%] avgR=0.222 RCI=[-0.799,1.243]
```

## 仮説採択理由
- FDR通過 0本 → スイープFDR候補なし
- トラッカー優先度②「前向きで大きく動いた仮説」= rsi_oversold_bounce
  - RCI_lo推移: 0.050(9/5) → -0.001(9/9) → -0.014(9/11) → -0.004(9/14) → +0.012(9/15)
  - 5日間マイナス期を経て今日プラス回帰

## 合否結果
- H1: FWD RCI_lo=+0.012 → プラス回帰確認 ✅
- H2: 4H RCI_lo=+0.032 → プラス維持 ✅
- H3: 1H RCI_lo=-0.130 → マイナス継続 ✅（予想通り）
- H4: trend=上昇 RCI_lo=+0.171 → プラス維持 ✅

## 追加観察
- trend=中立・もみあい RCI_lo=+0.062 → プラスエッジ存在
- trend=下降 RCI_lo=-0.258 → ネガティブ（4H×下降 39.5%も弱い）
- 4H×中立 70.0% はサンプル数N=30で参考値扱い
- 9月: 44.3% と 〜8月の53.0%より9pp弱い（ただし9月後半N=21は52.4%と回復傾向）
- promote_strikes=0（2回連続合格が必要・現状1回目到達せず）

## 交絡点検
- 4H足の強さ vs 全体の中間: 4H vs 1H の組成差ではなく実質的な足種効果
- トレンド分布: 上昇78 + 下降155 + 中立110 = 343（unknown=0、全件トレンド有り）
- 4H×上昇 N=32, 4H×中立 N=30 は小サンプルのためCIが広い
