# lab-104-analysis.md — 逆張り買い×トレンド3区分の前向き比較

## 実行日時
2026-09-20 JST（JST 06:10）

## 仮説
「トレンド3環境（上昇・下降・中立）で逆張り買い（reversalL: rsi_oversold_bounce または bb_lower_touch のロング）の成績は異なるか」
- 今日の優先ケース: ①✅昇格確認（trend=上昇×reversalL が promoted 維持）
- 追加発見: 下降×reversalL の gate 仮説が ⛔反証（FWD rci_lo=+0.039 > 0）

## スクリプト実行（/tmp/lab104_script.py）

```python
import json, sys
sys.path.insert(0, '/home/user/marketwatch-ai')
from signal_lab_verify import closed, win, match, wilson, REV, GROUPS

with open('signals-log.json') as f:
    logs = json.load(f)
cl = [x for x in logs if closed(x)]

def r_of(x):
    if x.get('outcome')=='tp1': return 2.0/1.5
    if x.get('outcome')=='tp2': return 3.0/1.5
    if x.get('outcome')=='sl': return -1.0
    return 0.0
```

## 実行結果

### スイープ結果（2026-09-20）
FDR通過 0本（新候補なし）

### トラッカー更新（2026-09-20）
- ✅昇格維持: trend=上昇×reversalL（edge）前向き N=315, 47.6%, avgR=+0.111, RCI=[-0.04,+0.262], demote_strikes=1

### IS/FWD 分割集計

#### 登録日（tracker registered_at）
- trend=上昇×reversalL: 2026-06-22 → IS: fired_before=2026-06-23 / FWD: fired_from=2026-06-23
- trend=下降×reversalL: 2026-06-25 → IS: fired_before=2026-06-26 / FWD: fired_from=2026-06-26
- trend=中立×reversalL: 2026-06-19 → IS: fired_before=2026-06-20 / FWD: fired_from=2026-06-20

#### IS（in-sample）
- 上昇×reversalL: N=103, k=56, 54.4%, CI=[44.8%,63.7%], ER=+0.269R
- 下降×reversalL: N=186, k=63, 33.9%, CI=[27.5%,40.9%], ER=-0.210R
- 中立×reversalL: N=152, k=54, 35.5%, CI=[28.4%,43.4%], ER=-0.171R

#### FWD（前向き、signals-log）
- 上昇×reversalL: N=316, k=148, 46.8%, CI=[41.4%,52.3%], ER=+0.093R
- 下降×reversalL: N=312, k=160, 51.3%, CI=[45.8%,56.8%], ER=+0.197R
- 中立×reversalL: N=322, k=150, 46.6%, CI=[41.2%,52.0%], ER=+0.087R

#### 全期間合算
- 上昇×reversalL: N=419, k=204, 48.7%, CI=[43.9%,53.5%], ER=+0.136R
- 下降×reversalL: N=498, k=223, 44.8%, CI=[40.5%,49.2%], ER=+0.045R
- 中立×reversalL: N=474, k=204, 43.0%, CI=[38.7%,47.5%], ER=+0.004R
- reversalL全体: N=1395, k=632, 45.3%, CI=[42.7%,47.9%], ER=+0.057R
- 全体 closed: N=4580, k=1977, 43.2%

### トラッカー FWD（signal-lab-tracker.json）
- 上昇×reversalL: status=promoted, N=315, 47.6%, RCI=[-0.04,+0.262], demote_strikes=1
- 下降×reversalL: status=rejected(gate), N=327, 51.4%, RCI=[+0.039,+0.358]
- 中立×reversalL: status=tracking, N=326, 47.5%, RCI=[-0.023,+0.241]
- reversalL全体: status=rejected(gate), N=942, 48.5%, RCI=[+0.035,+0.229]

### 主要発見
1. IS時の上昇優位（54.4% vs 下降33.9% vs 中立35.5%）は前向きで大幅縮小（上昇46.8% vs 下降51.3% vs 中立46.6%）
2. IS時に赤字（ER-0.210）だった下降×reversalL が、前向きでは最高値（ER+0.197）に
3. 「下降逆張りは避けよ」gate 仮説が ⛔反証確定（FWD rci_lo=+0.039 > 0）
4. 上昇×reversalL のみが独立のエッジとして昇格維持（ただし demote_strikes=1 で降格圏内）

### 交絡点検
- IS期間のサンプル数が異なる（上昇103件, 下降186件, 中立152件）: 特に上昇ISはN=103と小さい
- IS の優位性差は小サンプル（N=103）に由来する過剰フィッティングの可能性が高い
- FWD では3環境が47-51%に収束（差= 4.5pp）→ トレンド環境フィルターの信頼性は限定的

### Wilson CI計算確認
- 56/103: p=0.544, wilson=[44.8%,63.7%] ✓
- 63/186: p=0.339, wilson=[27.5%,40.9%] ✓
- 54/152: p=0.355, wilson=[28.4%,43.4%] ✓
- 148/316: p=0.468, wilson=[41.4%,52.3%] ✓
- 160/312: p=0.513, wilson=[45.8%,56.8%] ✓
- 150/322: p=0.466, wilson=[41.2%,52.0%] ✓
