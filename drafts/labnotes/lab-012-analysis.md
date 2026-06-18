# lab-012: もみあい相場のショート優位性（trend=中立・もみあい × dir=short）

**基準日**: 2026-06-17  
**仮説採択理由**: スイープFDR通過新候補（q=0.005・最上位黒字エッジ）

---

## 1. 仮説

> **もみあい（中立・もみあい）相場のショートシグナルは、損益分岐43%を有意に上回るか**  
> 帰無仮説 H0: 勝率 = 43%  
> 対立仮説 H1: 勝率 > 43%  
> 事前宣言基準: CI下限 > 43% かつ N ≥ 20

---

## 2. 検証スクリプト全文

```python
# lab-012 反実仮想集計スクリプト（2026-06-17実行）
import json, sys
sys.path.insert(0, '.')
from signal_lab_verify import closed, win, match, compute, get_trend, GROUPS, wilson

with open('signals-log.json', encoding='utf-8-sig') as f:
    data = json.load(f)
closed_d = [d for d in data if closed(d)]
# 決済済: 806 / 全: 981

def er(k, n):
    if n == 0: return "N/A"
    p = k/n
    return f"{p*1.33+(1-p)*(-1.0):+.3f}"

# 主要集計
neutral_short = [d for d in closed_d
                 if get_trend(d) == '中立・もみあい'
                 and 'ショート' in (d.get('direction') or '')]
# → k=33 n=49

for g, tickers in GROUPS.items():
    recs = [d for d in neutral_short if d.get('ticker') in tickers]
    ...

for sig in ['macd_dead','low_break','ma_dead']:
    recs = [d for d in neutral_short if d.get('primary_signal') == sig]
    ...

for tf in ['1h','4h']:
    recs = [d for d in neutral_short if d.get('timeframe') == tf]
    ...

# 対照群
neutral_long = [d for d in closed_d if get_trend(d) == '中立・もみあい' and 'ロング' in ...]
# → k=77 n=223

for trend in ['上昇','下降','中立・もみあい']:
    for sig in ['macd_dead']:
        recs = [d for d in closed_d if d.get('primary_signal')==sig and get_trend(d)==trend and 'ショート' in ...]
        ...
```

---

## 3. 生出力（全結果）

```
決済済: 806 / 全: 981

=== #012 仮説: trend=中立・もみあい × dir=short ===
  全体: k=33 n=49 勝率=67.3% CI=[53.4%,78.8%] R=+0.569

--- グループ別 ---
  metal: k=6 n=7 勝率=85.7% CI=[48.7%,97.4%] R=+0.997
  index: k=2 n=3 勝率=66.7% CI=[20.8%,93.9%] R=+0.553
  jpy_fx: k=4 n=9 勝率=44.4% CI=[18.9%,73.3%] R=+0.036
  other_fx: k=13 n=19 勝率=68.4% CI=[46.0%,84.6%] R=+0.594
  btc: k=6 n=7 勝率=85.7% CI=[48.7%,97.4%] R=+0.997
  oil: k=2 n=4 勝率=50.0% CI=[15.0%,85.0%] R=+0.165

--- シグナル別 ---
  macd_dead (N=30): k=19 n=30 勝率=63.3% CI=[45.5%,78.1%] R=+0.476
  low_break (N=13): k=9 n=13 勝率=69.2% CI=[42.4%,87.3%] R=+0.613

--- 時間足別 ---
  tf=1h: k=15 n=20 勝率=75.0% CI=[53.1%,88.8%] R=+0.748
  tf=4h: k=18 n=29 勝率=62.1% CI=[44.0%,77.3%] R=+0.446

--- ticker別（N>=5） ---
  AUDUSD=X (N=10): k=7 n=10 勝率=70.0% CI=[39.7%,89.2%] R=+0.631
  BTC-USD (N=7): k=6 n=7 勝率=85.7% CI=[48.7%,97.4%] R=+0.997
  GBPUSD=X (N=5): k=3 n=5 勝率=60.0% CI=[23.1%,88.2%] R=+0.398

=== 対照群比較 ===
  非中立×short: k=65 n=163 勝率=39.9% CI=[32.7%,47.5%] R=-0.071
  中立×long:    k=77 n=223 勝率=34.5% CI=[28.6%,41.0%] R=-0.195
  全short:      k=98 n=212 勝率=46.2% CI=[39.6%,52.9%] R=+0.077

--- 環境別 macd_dead交叉 ---
  macd_dead×上昇×short: k=30 n=49 61.2% CI=[47.2%,73.6%] R=+0.427
  macd_dead×中立×short: k=19 n=30 63.3% CI=[45.5%,78.1%] R=+0.476
  macd_dead×下降×short: k=11 n=52 21.2% CI=[12.2%,34.0%] R=-0.507

--- low_break 環境別 ---
  low_break×上昇×short:  k=6  n=18 33.3% CI=[16.3%,56.3%] R=-0.223
  low_break×下降×short:  k=7  n=20 35.0% CI=[18.1%,56.7%] R=-0.185
  low_break×中立×short:  k=9  n=13 69.2% CI=[42.4%,87.3%] R=+0.613

--- 環境別 全short集計 ---
  上昇×short: k=43 n=81 53.1% CI=[42.3%,63.6%] R=+0.237
  下降×short: k=21 n=78 26.9% CI=[18.3%,37.7%] R=-0.373

--- 月別（中立×short）---
  2026-05: k=9  n=15 60.0% CI=[35.7%,80.2%] R=+0.398
  2026-06: k=24 n=34 70.6% CI=[53.8%,83.2%] R=+0.645
```

---

## 4. スイープ結果（FDR通過）

```
trend=中立・もみあい×dir=short  k=33/49  勝率67.3%  平均R+0.571  CI[+0.26~+0.88]  q=0.005  ✅FDR黒字
group=index×dir=long             k=82/152 勝率53.9%  平均R+0.259  CI[+0.07~+0.44]  q=0.069  ✅FDR黒字
```

---

## 5. 交絡点検

1. **シグナル偏り**: macd_dead 30件（61.2%）+ low_break 13件（26.5%）= 計88%を2シグナルが占める。  
   → もみあい×short ≒ macd_dead×もみあい×short の側面が強い。

2. **macd_deadの環境依存**: 上昇61.2% / 中立63.3% / **下降21.2%** という大きな差。  
   → もみあい×short の優位は「下降環境ではmacd_dead短絡」が除外されているために生じている可能性。

3. **期間バイアス**: データが2026-05〜06の2ヶ月（N=49）。  
   → 比較的短期間。6月は70.6%と高いが、5月も60%でまずまず安定。

4. **small N**: BTC・metal・指数はN=3〜7（過信禁止）。other_fx（N=19・68.4%）はN少し多め。

5. **low_breakの環境特異性**: 上昇/下降では33-35%なのに中立では69.2%。  
   → もみあい中のレンジブレイクは「フェイクブレイク＝反転」の可能性。ただしN=13。

---

## 6. 判定

**通過A**（事前宣言基準クリア）  
- CI下限53.4% > 43% ✅  
- N=49 ≥ 20 ✅  
- 期待値R=+0.569（全トレード平均の-0.045より大幅上）  
- FDR q=0.005（多重検定補正済みで有意）  

ただし in-sample のみ。前向きトラッカー登録日（2026-06-17）・N=6（100%）は小サンプル過信禁止。

---

## 7. 前向きトラッカー宣言基準

- 前向きN≥80 かつ 平均R（期待値）のCI下限 > 0 でedge確立
- 当面は「もみあい相場×short」として蓄積を続ける
