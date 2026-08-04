# lab-061-analysis.md — もみあい×ショート 前向きCI全域マイナス確定

## 実行日
2026-08-05 JST

## 仮説
trend=中立・もみあい × dir=short の前向き期待値（E(R)）は損益分岐（ゼロ）を下回るか。
IS（2026-06-17以前）での高勝率63.6%は前向きで維持されなかったことを#059で確認済み。
今回N=149でRCI上限が初めてゼロを切った（-0.008）→ CI全域マイナス確定の解剖分析。

## 検証スクリプト（Python 反実仮想集計）

```python
import json, math
from collections import Counter

with open('signals-log.json') as f:
    logs = json.load(f)

def get_trend(d):
    ta = d.get("trend_alignment")
    if isinstance(ta, dict) and ta.get("higher_tf_trend"):
        return ta["higher_tf_trend"]
    return None

def get_direction(d):
    dir_str = d.get("direction", "")
    if "ロング" in str(dir_str) or dir_str == "long": return "long"
    if "ショート" in str(dir_str) or dir_str == "short": return "short"
    return None

def get_outcome(d):
    oc = d.get("outcome")
    if oc in ("tp1", "tp2"): return "win"
    if oc == "sl": return "loss"
    return None

def get_r(d):
    oc = d.get("outcome")
    if oc == "tp1": return 2.0
    if oc == "tp2": return 3.0
    if oc == "sl": return -1.5
    return None

def wilson(k, n, z=1.96):
    if n == 0: return (0, 1)
    p = k/n
    z2 = z*z
    d = 1 + z2/n
    c = (p + z2/(2*n)) / d
    s = (z * math.sqrt(p*(1-p)/n + z2/(4*n*n))) / d
    return (max(0, c-s), min(1, c+s))

closed = [s for s in logs if get_outcome(s) is not None]
reg_date = "2026-06-17"  # tracker登録日

base = [s for s in closed if get_trend(s)=="中立・もみあい" and get_direction(s)=="short"]
fwd = [s for s in base if s.get('fired_at','')[:10] >= reg_date]
is_d = [s for s in base if s.get('fired_at','')[:10] < reg_date]
```

## 生出力

### 全データ（IS+FWD）
```
全件: 78/193 = 40.4% CI[33.7%,47.5%] E(R)=-0.085
```

### IS（2026-06-17以前）
```
IS: 28/44 = 63.6% CI[48.9%,76.2%] E(R)=+0.727
```

### FWD（2026-06-17以降・前向きデータ）
```
FWD N=149: 50/149 = 33.6% Wilson CI[26.5%,41.5%]
Outcome: {'tp1': 50, 'sl': 99}
E(R) = -0.326（単純SE、cluster-corrected trackerでは -0.217）
```

### tracker値（cluster補正SE）
```
avgR = -0.217
rci_lo = -0.426, rci_hi = -0.008
→ 2026-08-05時点でRCI上限が初めて0を切った（前日:+0.003→今日:-0.008）
```

### シグナル別 FWD
```
macd_dead: 30/79 = 38.0% CI[28.1%,49.0%] E(R)=-0.171
ma_dead: 9/24 = 37.5% CI[21.2%,57.3%] E(R)=-0.188
low_break: 11/41 = 26.8% CI[15.7%,41.9%] E(R)=-0.561
first_pullback_short: 0/5 = 0.0% CI[0.0%,43.4%] E(R)=-1.500
```

### シグナル別 IS（参照）
```
low_break IS: 9/13 = 69.2% E(R)=+0.923
macd_dead IS: 14/25 = 56.0% E(R)=+0.460
ma_dead IS: 2/3 = 66.7% E(R)=+0.833
```

### low_break IS→FWD
```
IS: 9/13 = 69.2% E(R)=+0.923
FWD: 11/41 = 26.8% E(R)=-0.561
乖離: -42.4pp（最大の逆転）
```

### グループ別 FWD
```
metal: 9/27 = 33.3% CI[18.6%,52.2%] E(R)=-0.333
index: 14/36 = 38.9% CI[24.8%,55.1%] E(R)=-0.139（相対ベスト）
jpy_fx: 8/30 = 26.7% CI[14.2%,44.4%] E(R)=-0.567（最悪）
other_fx: 13/38 = 34.2% CI[21.2%,50.1%] E(R)=-0.303
btc: 2/11 = 18.2% CI[5.1%,47.7%] E(R)=-0.864（小サンプル注意）
oil: 4/7 = 57.1% E(R)=+0.500（N=7・探索的）
```

### グループ別 全件（IS+FWD）
```
group=metal: 15/34 = 44.1% E(R)=+0.044
group=index: 16/39 = 41.0% E(R)=-0.064
group=jpy_fx: 10/37 = 27.0% CI[15.4%,43.0%] E(R)=-0.554
group=other_fx: 23/54 = 42.6% E(R)=-0.009
group=btc: 8/18 = 44.4% E(R)=+0.056
group=oil: 6/11 = 54.5% E(R)=+0.409
```

### シグナル別 全件
```
signal=macd_dead: 44/104 = 42.3% CI[33.3%,51.9%] E(R)=-0.019
signal=low_break: 20/54 = 37.0% CI[25.4%,50.4%] E(R)=-0.204
signal=ma_dead: 11/27 = 40.7% CI[24.5%,59.3%] E(R)=-0.074
signal=first_pullback_short: 1/6 = 16.7%
```

### 対照群
```
もみあい×ロング FWD: 189/412 = 45.9% CI[41.1%,50.7%] E(R)=+0.106
もみあい×ロング 全件: 264/629 = 42.0% CI[38.2%,45.9%] E(R)=-0.031
```

## 交絡点検
1. **低サンプル偏り**: IS N=44 vs FWD N=149。IS期間はAIシグナルシステム導入直後で発火銘柄・相場環境が異なる可能性がある。
2. **low_breakのfront-running bias**: IS期間に最適化されたパターン（安値ブレイク後の戻り売り）が、前向きで機能しなくなった。具体的にはIS 69.2%→FWD 26.8%の42.4pp逆転。
3. **グループ構成**: FWD N=149の内訳はmacd_dead79件(53%)、low_break41件(28%)、ma_dead24件(16%)。
4. **トラッカー判定**: これは"edge"種別（正の期待値期待）として登録されたためtracker auto-promoteは起きないが、CI全域マイナスは実質的な反証（損益分岐を下回るエッジの確認）。

## 前向きトラッカー更新
- trend=中立・もみあい×dir=short: N=149 avgR=-0.217 RCI[-0.43~-0.01] 🟡蓄積中
  → RCI上限が初めて0未満（-0.008）に到達。実質的な損失有意化確認。
  → 次チェックポイント: N=160（チェックポイント検定の次の倍数）

## 結論
IS期間（N=44）63.6%・E(R)=+0.727の「高勝率シグナル」が、前向きN=149で33.6%・E(R)=-0.217に完全逆転。
cluster-corrected RCI上限が今日初めて0を切った(-0.008)ことで、**もみあい×ショートの期待値がマイナスであることが統計的に確定**した。
主犯はlow_break（IS69.2%→FWD26.8%・42.4ppの崩落）。macd_deadは38%で損益分岐を下回るが確定打なし（CI[28.1%,49.0%]）。
