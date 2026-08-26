# lab-081-analysis.md
## AIシグナル研究日誌 #081
### 日付: 2026-08-27 (JST)
### 仮説: 日足ショートは「回避シグナル」へ——前向きFWD22.6%、逆張り買い77.8%との55pp方向非対称

---

## 発見スイープ結果 (sweep-2026-08-27.json)
- FDR通過: 1本 = tf=1d×reversalL (R+0.67, q=0.0431)
- 重複スキップ: 1本（既登録）
- 新規登録: 0本

## トラッカー更新 (signal_lab_tracker.py update --date 2026-08-27)
- ✅昇格: なし
- ⛔反証: なし
- 主要動向:
  - ショート全般(日足・回避): FWD 8/28=29%, CI[-0.70~+0.03] (tracker cluster補正)
  - tf=1d×reversalL: FWD 7/9=78%, CI[+0.04~+1.59] (tracker cluster補正)

## 優先度判定
④ 定点観測（✅昇格/⛔反証なし、FDR新候補なし）
→ 前向きで最も動きがあった仮説を題材: 1D足の方向非対称（ショート vs 逆張り買い）

---

## Pythonスクリプト（signals-log.json 分析）

```python
import json, math

with open('signals-log.json') as f:
    data = json.load(f)

closed = [s for s in data if s.get('outcome') in ['sl','tp1','tp2','be']]

# is_win, r_val, wilson_ci, r_ci, report functions defined

# 1D Short IS/FWD (tracker registration 2026-06-16, boundary 2026-06-17)
IS_BOUNDARY = "2026-06-17"
d1_short = [s for s in closed if s.get('timeframe')=='1d' and 'ショート' in s.get('direction','')]
d1s_is = [s for s in d1_short if s.get('fired_at','')[:10] < IS_BOUNDARY]
d1s_fwd = [s for s in d1_short if s.get('fired_at','')[:10] >= IS_BOUNDARY]

# 1D reversalL (tracker registration 2026-07-15, boundary 2026-07-16)
REVL_BOUNDARY = "2026-07-16"
d1_revl = [s for s in closed if s.get('timeframe')=='1d' and 'ロング' in s.get('direction','') 
           and s.get('primary_signal') in ['bb_lower_touch','rsi_oversold_bounce']]
d1_revl_is = [s for s in d1_revl if s.get('fired_at','')[:10] < REVL_BOUNDARY]
d1_revl_fwd = [s for s in d1_revl if s.get('fired_at','')[:10] >= REVL_BOUNDARY]
```

---

## 生出力

=== IS/FWD 2026-06-17 boundary ===
1D Short IS (fired_before 2026-06-17): N=3, k=3, 100.0% WCI[43.8%,100.0%] avg_R=2.000
1D Short FWD (fired_from 2026-06-17): N=31, k=7, 22.6% WCI[11.4%,39.8%] avg_R=-0.323 RCI[-0.764,0.119]
1D Short 全期間: N=34, k=10, 29.4% WCI[16.8%,46.2%] avg_R=-0.118 RCI[-0.577,0.342]

=== 1D reversalL ===
全期間: N=35, k=25, 71.4% WCI[54.9%,83.7%] avg_R=1.143 RCI[0.694,1.592]
IS (fired_before 2026-07-16): N=26, k=18, 69.2% WCI[50.0%,83.5%] avg_R=1.077 RCI[0.545,1.609]
FWD (fired_from 2026-07-16): N=9, k=7, 77.8% WCI[45.3%,93.7%] avg_R=1.333 RCI[0.518,2.148]

=== 1D Short FWD by signal (fired_from 2026-06-17) ===
FWD×macd_dead: N=17, k=5, 29.4% WCI[13.3%,53.1%] avg_R=-0.118 RCI[-0.767,0.532]
FWD×low_break: N=9, k=1, 11.1% WCI[2.0%,43.5%] avg_R=-0.667 RCI[-1.283,-0.051] ← CI全域マイナス
FWD×ma_dead: N=4, k=1, 25.0% WCI[4.6%,69.9%] avg_R=-0.250 RCI[-1.523,1.023]

=== 1D Long 全期間 ===
1Dロング: N=123, k=60, 48.8% WCI[40.1%,57.5%] avg_R=0.463 RCI[0.198,0.728]

=== Comparison: Short by TF (FWD, fired_from 2026-06-17) ===
1H Short FWD: N=456, k=191, 41.9% WCI[37.4%,46.5%] avg_R=+0.257 RCI[0.121,0.392]
4H Short FWD: N=289, k=113, 39.1% WCI[33.7%,44.8%] avg_R=+0.173 RCI[0.004,0.342]
1D Short FWD: N=31, k=7, 22.6% WCI[11.4%,39.8%] avg_R=-0.323 RCI[-0.764,0.119]

---

## 主要発見

1. **1D Short FWD 22.6% (k=7/n=31)**: IS 100% (N=3, trivial) → FWD 22.6%の急落。
   avg_R=-0.323 RCI[-0.764, +0.119]。CI上限+0.119>0でgate確認未達（N=80まであと49件）。

2. **low_break×1D Short FWD**: N=9, k=1, 11.1%, avg_R=-0.667, **RCI[-1.283, -0.051]**
   → CI全域マイナス（ただしN=9小サンプル・参考値）

3. **1D reversalL FWD**: N=9, k=7, 77.8%, avg_R=+1.333
   → 1D Short FWD 22.6%との方向非対称: 77.8% - 22.6% = 55.2pp

4. **TF別ショートFWD**:
   - 1H: 41.9% avg_R=+0.257（健全・RCI全域プラス）
   - 4H: 39.1% avg_R=+0.173（微弱）
   - 1D: 22.6% avg_R=-0.323（明確な underperform）
   → 1D足のみ際立って低い（TF効果）

5. **事前宣言 H1 進捗**（gate 「日足ショート全般」）:
   - 宣言: FWD N≥80 かつ avg_R CI上限<0
   - 現状: N=31, CI上限+0.119 → gate確認未達（進捗 31/80 = 39%）

---

## 交絡チェック
- 全N=34のうちmacd_dead=17件(50%)、low_break=11件(32%)が主体
- グループ別: jpy_fx/other_fx/btcが全体を占め（FXドミナント）
- 指数×1D短絡の直接発火は少ない（1Dショートシグナルは主にFX系）
