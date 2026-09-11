# lab-096-analysis.md — 上昇トレンド×RSI売られすぎ（rsi_band=os × trend=上昇）IS/FWD検証

## 実行日時
- 基準日: 2026-09-12（JST）
- スクリプト実行: 上記本文参照

## 仮説
- **テーマ**: 上昇トレンド中にRSIが売られすぎ域（rsi_band=os）に入ったシグナルは、IS期間に高い勝率を示した。前向きN=56でその汎化を検証する。
- **フィルタ**: `{rsi_band: "os", trend: "上昇"}`
- **登録日**: 2026-08-11（tracker）
- **IS期間**: fired_at < 2026-08-11
- **FWD期間**: fired_at ≥ 2026-08-11

## スクリプト全文

```python
import json, sys
sys.path.insert(0, '.')
from signal_lab_verify import closed, win, match, wilson

with open('signals-log.json') as f:
    data = json.load(f)
logs = [x for x in data if closed(x)]

base_filter = {'rsi_band': 'os', 'trend': '上昇'}
REG_DATE = '2026-08-11'
TP1_R = 2.0/1.5
SL_R = -1.0

def calc_E(subset):
    tp1 = sum(1 for x in subset if x.get('outcome') == 'tp1')
    sl  = sum(1 for x in subset if x.get('outcome') == 'sl')
    n = len(subset)
    return (tp1 * TP1_R + sl * SL_R) / n if n else 0

IS  = [x for x in logs if match(x, {**base_filter, 'fired_before': REG_DATE})]
FWD = [x for x in logs if match(x, {**base_filter, 'fired_from': REG_DATE})]

# IS全体
k, n = sum(1 for x in IS if win(x)), len(IS)
lo, hi = wilson(k, n)
print(f'IS全体: N={n}, k={k}, {k/n*100:.1f}%, E(R)={calc_E(IS):.3f}, CI[{lo:.1f}%~{hi:.1f}%]')

# IS by direction
for d in ['long','short']:
    s = [x for x in IS if match(x, {'direction': d})]
    kd, nd = sum(1 for x in s if win(x)), len(s)
    lo2, hi2 = wilson(kd, nd)
    print(f'IS {d}: N={nd}, k={kd}, {kd/nd*100:.1f}%, E(R)={calc_E(s):.3f}, CI[{lo2:.1f}%~{hi2:.1f}%]')

# IS by tf
for tf in ['1h','4h']:
    s = [x for x in IS if match(x, {'tf': tf})]
    kt, nt = sum(1 for x in s if win(x)), len(s)
    lo3, hi3 = wilson(kt, nt)
    print(f'IS {tf}: N={nt}, k={kt}, {kt/nt*100:.1f}%, E(R)={calc_E(s):.3f}, CI[{lo3:.1f}%~{hi3:.1f}%]')

# IS 4H×Long
s4l = [x for x in IS if match(x, {'tf': '4h', 'direction': 'long'})]
k4l, n4l = sum(1 for x in s4l if win(x)), len(s4l)
lo4l, hi4l = wilson(k4l, n4l)
print(f'IS 4H×Long: N={n4l}, k={k4l}, {k4l/n4l*100:.1f}%, E(R)={calc_E(s4l):.3f}, CI[{lo4l:.1f}%~{hi4l:.1f}%]')

# FWD全体
kf, nf = sum(1 for x in FWD if win(x)), len(FWD)
lof, hif = wilson(kf, nf)
print(f'FWD全体: N={nf}, k={kf}, {kf/nf*100:.1f}%, E(R)={calc_E(FWD):.3f}, CI[{lof:.1f}%~{hif:.1f}%]')

# FWD by direction
for d in ['long','short']:
    s = [x for x in FWD if match(x, {'direction': d})]
    kd, nd = sum(1 for x in s if win(x)), len(s)
    if nd:
        lo5, hi5 = wilson(kd, nd)
        print(f'FWD {d}: N={nd}, k={kd}, {kd/nd*100:.1f}%, E(R)={calc_E(s):.3f}, CI[{lo5:.1f}%~{hi5:.1f}%]')

# All-time confirm
all_s = [x for x in logs if match(x, base_filter)]
ka, na = sum(1 for x in all_s if win(x)), len(all_s)
print(f'All-time: N={na}, k={ka}, {ka/na*100:.1f}%')
print(f'Base rate: {sum(1 for x in logs if win(x))}/{len(logs)} = {sum(1 for x in logs if win(x))/len(logs)*100:.1f}%')
```

## 生出力

```
IS全体: N=73, k=44, 60.3%, E(R)=0.406, CI[48.8%~70.7%]
IS long: N=51, k=39, 76.5%, E(R)=0.784, CI[63.2%~86.0%]
IS short: N=22, k=5, 22.7%, E(R)=-0.470, CI[10.1%~43.4%]
IS 1h: N=28, k=12, 42.9%, E(R)=0.048, CI[26.5%~60.9%]
IS 4h: N=35, k=25, 71.4%, E(R)=0.667, CI[54.9%~83.7%]
IS 4H×Long: N=26, k=23, 88.5%, E(R)=1.064, CI[71.0%~96.0%]
FWD全体: N=56, k=29, 51.8%, E(R)=0.208, CI[39.0%~64.3%]
FWD long: N=39, k=20, 51.3%, E(R)=0.197, CI[36.2%~66.1%]
FWD short: N=17, k=9, 52.9%, E(R)=0.216, CI[31.0%~73.8%]
All-time: N=129, k=73, 56.6%
Base rate: 1877/4369 = 43.0%
```

## 解釈メモ

- IS期間(N=73)はLong 76.5%という強い数値だが、N=51の小サンプル。
- IS 4H×Long 88.5% (N=26) はさらに小サンプルで過大推定リスク大。
- FWDではLong 51.3%、Short 52.9%と方向差がほぼ消えた（CI幅広し）。
- IS→FWDのLong勝率: 76.5% → 51.3%（-25.2pp収縮）は大きな縮小。
- FWD全体CI[39.0%~64.3%]は損益分岐43%を含む幅広いCIのため、優位性は未確定。
- N=80到達はFWD+24件（2026-09-12時点N=56）。現状は「有望だが判断保留」。

## ベースライン比較
- 全体ベース: 43.0%（N=4369）
- IS全体の60.3%はベースより+17.3pp
- FWD全体の51.8%はベースより+8.8pp（ただしCI内）

## 事前合否基準
- H1: IS Long CI下限 > 43% → 63.2% > 43% → ✅
- H2: IS全体 CI下限 > 43% → 48.8% > 43% → ✅
- H3: FWD CI下限が43%未満（昇格未達を確認） → 39.0% < 43% → ✅
