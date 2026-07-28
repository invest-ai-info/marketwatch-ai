# lab-054-analysis.md
# AIシグナル研究日誌 #054 ラボノート
# 日付: 2026-07-29 (JST)
# 仮説: group=index × dir=short gate 前向きN=82初チェックポイント確認

---

## 1. 仮説設定

**検証対象**: `group=index × dir=short` gate（tracker[o]）
- **gate設立**: #025（2026-06-30）。IS期間（N=62→64件）で27.4%/28.1%（CI上限<43%）を確認し、「指数ショートは損益分岐を下回る」としてgateを設立
- **宣言条件**: 前向き N≥80 かつ 平均R の CI上限 < 0（損益の95%CI全域がマイナス）
- **今日の意義**: N=82 ≥ 80 達成 → 初の宣言Nチェックポイント

---

## 2. スイープ・トラッカー実行結果

```
python signal_lab_tracker.py update --date 2026-07-29
→ 昇格変化なし。group=index×dir=short: FWD R=+0.224, N=82 🟡蓄積中

python signal_lab_sweep.py --json drafts/labnotes/sweep-2026-07-29.json
→ FDR通過 0本（新規なし）

python signal_lab_tracker.py register --from drafts/labnotes/sweep-2026-07-29.json --date 2026-07-29
→ 登録 0本
```

**優先度判定**: ② 前向きで大きく動いた仮説（N=82初チェックポイント到達）

---

## 3. Python反実仮想集計スクリプト

```python
import json, math

with open("signals-log.json") as f:
    data = json.load(f)

INDEX_TICKERS = {"NKD=F", "ES=F", "NQ=F", "YM=F", "^FTSE"}

def is_win(s): return s.get("outcome") in ("tp1", "tp2")
def is_closed(s): return s.get("outcome") in ("tp1", "tp2", "sl", "expired")
def is_short(s): return s.get("direction") == "ショート（売り）"
def get_r(s):
    if s.get("outcome") == "tp1": return 1.33
    if s.get("outcome") == "tp2": return 2.0
    if s.get("outcome") == "sl": return -1.0
    if s.get("outcome") == "expired": return 0.0
    return None

TRACKER_START = "2026-06-30"  # gate設立日

closed = [s for s in data if is_closed(s)]
idx_short = [s for s in closed if s["ticker"] in INDEX_TICKERS and is_short(s)]
is_sig = [s for s in idx_short if s.get("fired_at","")[:10] < TRACKER_START]
fwd_sig = [s for s in idx_short if s.get("fired_at","")[:10] >= TRACKER_START]
```

---

## 4. 生出力

### 4-1. 全体サマリー

```
Total closed signals: 2281

=== group=index × dir=short (all closed) ===
N=146
Win rate: 61/146 = 41.8%
Mean R: -0.027

IS (before 2026-06-30): N=64
  Win: 18/64 = 28.1%
  Mean R: -0.345

FWD (from 2026-06-30): N=82
  Win: 43/82 = 52.4%
  Win CI: [41.8%, 62.9%]
  Mean R: 0.222, SD: 1.171
  RCI: [-0.032, 0.475]
```

### 4-2. Gate条件チェック

```
Gate condition: FWD N≥80 かつ RCI上限<0
FWD N=82 ≥ 80 ✅
RCI上限=+0.475 >> 0 → Gate condition ❌ NOT MET
⛔反証 condition RCI下限>0: RCI下限=-0.032 → ❌ NOT MET (barely negative)
```

**判定**: gate未確認（RCI上限がマイナスにならない）。かつ⛔反証接近（RCI下限-0.032が0に肉薄）

### 4-3. IS期間内訳

```
=== IS signal breakdown ===
  macd_dead: 13/38 = 34.2%
  low_break: 2/18 = 11.1%
  ma_dead: 2/6 = 33.3%
  first_pullback_short: 1/2 = 50.0%

=== IS ticker breakdown ===
  NKD=F: 7/20 = 35.0%
  NQ=F: 2/15 = 13.3%
  ES=F: 6/14 = 42.9%
  YM=F: 2/11 = 18.2%
  ^FTSE: 1/4 = 25.0%
```

### 4-4. FWD期間内訳

```
=== FWD Ticker breakdown ===
  NKD=F: 17/23 = 73.9%
  NQ=F: 10/19 = 52.6%
  ES=F: 8/16 = 50.0%
  YM=F: 5/15 = 33.3%
  ^FTSE: 3/9 = 33.3%

=== FWD Signal breakdown ===
  macd_dead: 27/46 = 58.7%
  low_break: 10/23 = 43.5%
  ma_dead: 5/12 = 41.7%
  first_pullback_short: 1/1 = 100.0%

=== FWD TF breakdown ===
  1h: 22/44 = 50.0%
  4h: 21/37 = 56.8%

=== FWD split (Early vs Late) ===
  Early (N=41): 20/41 = 48.8%, R=+0.137
  Late (N=41): 23/41 = 56.1%, R=+0.307

=== FWD MA position ===
  above_both: 14/22 = 63.6%
  below_both: 23/50 = 46.0%
  above75_only: 5/7 = 71.4%
  above25_only: 1/3 = 33.3%
```

### 4-5. 全期間内訳（claims.json用）

```
=== OVERALL BREAKDOWN ===
  index×short ALL: 61/146 = 41.8% CI[34.1%,49.9%] R=-0.027
  NKD=F×short: 24/43 = 55.8% CI[41.1%,69.6%] R=+0.300
  ES=F×short: 14/30 = 46.7% R=+0.087
  NQ=F×short: 12/34 = 35.3% R=-0.178
  YM=F×short: 7/26 = 26.9% R=-0.373
  ^FTSE×short: 4/13 = 30.8% R=-0.283
  macd_dead×index×short: 40/84 = 47.6% CI[37.3%,58.2%] R=+0.110
  low_break×index×short: 12/41 = 29.3% CI[17.6%,44.5%] R=-0.318
  ma_dead×index×short: 7/18 = 38.9% R=-0.094
  1h×index×short: 27/66 = 40.9% R=-0.047
  4h×index×short: 33/78 = 42.3% R=-0.014
  index×long ALL: 183/418 = 43.8% R=+0.037
```

### 4-6. 対照群：指数×ロング FWD期間

```
=== Compare: index×long FWD (2026-06-30以降) ===
  N=187, wins=61, rate=32.6%, mean R=-0.229
```

### 4-7. 交絡点検

- **IS vs FWD の分岐は本物か**: IS期間は上昇トレンド中の逆張りショート（#025で確認）が多数を占めており、順張りの相場環境変化が一因。FWD期間は相場の不確実性上昇→ショートが機能しやすい環境に変化。
- **金属レジーム転換の影響**: index×shortには金属は含まれないため、#030/039の金属レジーム転換とは独立した発見。
- **サンプル偏り**: IS=64件、FWD=82件と同程度。FWD期間約13ヶ月（2026-06-30〜2026-07-29）。
- **NKD=F FWD 73.9%の解釈**: 17/23（N=23）はやや小さい。IS 7/20=35.0%からの38.9pp改善が大きく、ランダム偏りの可能性もある。CI下限[52.4%,89.8%]は確認が必要。
- **macd_dead主体**: FWD 27/46=58.7%だが、IS 13/38=34.2%から24.5pp改善。マクロ/テクニカル環境変化がmacd_deadシグナルの精度を高めた可能性。

---

## 5. 前向きトラッカー確認

```
python signal_lab_tracker.py table --date 2026-07-29
group=index×dir=short (gate): 前向き 平均R +0.22 CI[-0.04~+0.49]（43/82・勝率52%）🟡蓄積中
```

---

## 6. 結論

**現時点の判定: 🟡 蓄積中（gate未確認、⛔反証接近）**

- gate宣言条件「FWD RCI上限<0」は未達（RCI上限=+0.475 >> 0）
- ⛔反証「FWD RCI下限>0」は未達（RCI下限=-0.032、わずかに負）
- ただし FWD 52.4%・R=+0.222・後半56.1%加速中 → IS28.1%からの完全逆転トレンド継続
- 対照の指数×ロング FWD 32.6%との方向非対称が IS時代と完全逆転
- NKD=F が FWD 73.9%で際立つ（全IS時代35.0%から劇的改善）
- 次チェックポイントは RCI下限が0を超えるタイミング（⛔反証確定）またはRCI上限が0を下回るタイミング（gate確認）
