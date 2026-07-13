# lab-039-analysis.md
## 基準日: 2026-07-14 / 番号: 039
## 仮説: group=metal×dir=long gate — tracker N=86昇格確認と「前向き改善」の正体解剖

---

## 採択理由（優先度①：tracker 昇格変化）
2026-07-14のtracker update実行結果:
```
🚩 今回ステータス変化:
   - group=metal×dir=long: promoted（前向き 平均R -0.349 / N=86）
```

group=metal×dir=long の前向きトラッカー（登録 2026-06-17）が N=86 に到達し、
平均R の CI[-0.69~-0.01]（上限 -0.01 < 0）を達成 → gate昇格（損失確定）。

---

## Sweepコマンド

```
python signal_lab_sweep.py --json drafts/labnotes/sweep-2026-07-14.json
```

Sweep結果（抜粋）:
- ✅黒字エッジ（FDR通過）: group=index×reversalL(R+0.30), trend=上昇×reversalL(R+0.27)
- ⛔赤字（FDR通過）: group=metal×dir=long(R-0.48), group=metal(R-0.31), tier=neutral(R-0.15)
新規登録 0本（5本全て既登録）

---

## Pythonスクリプト（全文）

```python
import json, math
from collections import Counter

with open('signals-log.json') as f:
    raw = json.load(f)
sigs = raw if isinstance(raw, list) else raw.get('signals', [])
closed = [s for s in sigs if s.get('outcome') in ('tp1','tp2','sl')]
# Total closed: 1631

def is_long(s): return 'ロング' in s.get('direction','') or s.get('direction','')=='long'
def grp(s):
    t = s.get('ticker','')
    if t in ('GC=F','SI=F'): return 'metal'
    ...

def win(s): return 1 if s.get('outcome') in ('tp1','tp2') else 0

def wilson(k, n, z=1.96):
    p = k/n; lo = ...; hi = ...; return max(0,lo), min(1,hi)

def avgR_ci(sg):
    Rs = [2.0 if o=='tp1' else 3.0 if o=='tp2' else -1.5 for o in...]
    mu = sum(Rs)/n; se = std/sqrt(n); return mu, mu-1.96*se, mu+1.96*se

metal_long = [s for s in closed if grp(s)=='metal' and is_long(s)]
```

---

## 生出力（キー統計）

### 全期間 metal×long
```
全体: N=172, k=38, 22.1% CI[16.5%,28.9%] E(R)=-0.727 RCI[-0.944,-0.509]
```

### IS/FWD分割（tracker登録日 2026-06-17）
```
IS (before 2026-06-17): N=86, k=14, 16.3% CI[10.0%,25.5%] E(R)=-0.930 RCI[-1.205,-0.656]
FWD (from 2026-06-17): N=86, k=24, 27.9% CI[19.5%,38.2%] E(R)=-0.523 RCI[-0.857,-0.190]
```
※ tracker表示値（別R計算）: FWD 平均R -0.349 CI[-0.69~-0.01]。方向は一致（全域マイナス）。

### Ticker別（全期間）
```
GC=F×long: N=99, k=25, 25.3% CI[17.7%,34.6%] E(R)=-0.616
SI=F×long: N=73, k=13, 17.8% CI[10.7%,28.1%] E(R)=-0.877
```

### Signal別（全期間）
```
bb_lower_touch:      N=58, k=14, 24.1% CI[15.0%,36.5%] E(R)=-0.655
rsi_oversold_bounce: N=47, k=12, 25.5% CI[15.3%,39.5%] E(R)=-0.606
macd_golden:         N=32, k=5,  15.6% CI[6.9%,31.8%]  E(R)=-0.953
high_break:          N=11, k=1,   9.1% CI[1.6%,37.7%]  E(R)=-1.182
bb_upper_break:      N=9,  k=3,  33.3% CI[12.1%,64.6%] E(R)=-0.333
ma_golden:           N=6,  k=1,  16.7% CI[3.0%,56.4%]  E(R)=-0.917
double_bottom:       N=5,  k=2,  40.0% CI[11.8%,76.9%] E(R)=-0.100
```

### TF別（全期間）
```
tf=1h×metal×long: N=89, k=18, 20.2% CI[13.2%,29.7%] E(R)=-0.792
tf=4h×metal×long: N=73, k=17, 23.3% CI[15.1%,34.2%] E(R)=-0.685
```

### 方向非対称（全期間）
```
metal×long:  N=172, k=38, 22.1% CI[16.5%,28.9%] E(R)=-0.727
metal×short: N=73,  k=34, 46.6% CI[35.6%,57.9%] E(R)=+0.130
方向差: 24.5pp（ロングが大幅不利）
```

### 「前向き改善」の正体（#030との比較）

#030（2026-07-05公開）で「金属IS E(R)=-0.964→FWD+0.672」と記録した。
これは dir=long gate のFWD定義（登録日 2026-06-25以降）内の metal×long を指す。

実際に計算すると:
```
2026-06-25 to 2026-07-04 (10日間): N=35, 51.4% E(R)=+0.300 RCI[-0.288,+0.888]
```
→ RCI が -0.288 から +0.888 と区間幅が広く0を含む（CI非有意）
→ これはN=35の短期サンプルノイズ

その後:
```
2026-07 (July): N=37, 18.9% CI[9.5%,34.2%] E(R)=-0.838 RCI[-1.286,-0.390]
```
→ Julyで急落・RCI全域マイナス確定

### 月別FWD（tracker登録日以降）
```
2026-06: N=49, 34.7% CI[22.9%,48.7%] E(R)=-0.286
2026-07: N=37, 18.9% CI[9.5%,34.2%]  E(R)=-0.838
```

### indicators_at_signal確認
```python
# keys: ['rsi', 'macd', 'macd_sig', 'ma25', 'ma75', 'bb_low', 'bb_up', 'recent_high', 'recent_low']
# trend: None, reversal_long: None
```
→ 金属シグナルには trend/reversal_long フィールドが存在しない（古い構造）
→ tracker/verify.py の trend/reversal_long フィルタは適用不可（除外対象）

### blocked確認（FWD）
```
{False: 86}
```
→ 全86件 blocked=False（金属シグナルには壁あり=blocked=True が発生していない）

---

## 事前宣言基準の評価

| 条件 | 宣言内容 | 結果 | 判定 |
|---|---|---|---|
| H1 | CI上限 < 43% | 28.9% < 43% | ✅ |
| H2 | N ≥ 80（信頼性確保） | N=172 | ✅ |
| H3 | E(R) 全域マイナス（RCI上限<0） | RCI上限=-0.509 < 0 | ✅ |
| H4 | tracker FWD N≥80 かつ gate昇格 | N=86、CI[-0.69~-0.01]上限<0 → ✅昇格 | ✅ |

→ 全4条件クリア → gate確認確定

---

## 比較参照値（対照群・本文引用用）

- index×long: N=294, k=147, 50.0% CI[44.3%,55.7%] E(R)=+0.250（対比）
- metal ALL (L+S): N=245, k=72, 29.4% CI[24.0%,35.4%] E(R)=-0.471
- #030 dir=long gate FWD: N=195, E(R)=+0.231（内訳に金属含む・CI straddles 0）

---

## 次回候補
- blocked=True×long の昇格確認（tracker t: FWD N=44, E(R)=+0.379 RCI[+0.040,+0.718]）
- tier=good FWD N=77→80到達が近い（FWD N=77, 65%）
