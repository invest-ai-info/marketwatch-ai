# lab-017-analysis.md — AIシグナル研究日誌 #17
## テーマ: blocked=True の方向性分解
## 基準日: 2026-06-22

---

## スクリプト

```python
import json, math

data = json.load(open('signals-log.json', encoding='utf-8-sig'))

def closed(d): return d.get('outcome') in ('tp1','tp2','sl')
def win(d): return d.get('outcome') in ('tp1','tp2')
def wilson(k,n,z=1.96):
    if n==0: return (0,100)
    p=k/n; den=1+z*z/n; c=(p+z*z/(2*n))/den; pm=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return (max(0,c-pm)*100, min(1,c+pm)*100)
def er_val(d):
    o=d.get('outcome')
    if o=='tp1': return 1.33
    if o=='tp2': return 2.0
    if o=='sl': return -1.0
    return None

closed_data = [d for d in data if closed(d)]

def is_long(d): return 'ロング' in (d.get('direction') or '')
def is_short(d): return 'ショート' in (d.get('direction') or '')
def has_blocked(d,v):
    sr = d.get('sr_runway')
    return isinstance(sr,dict) and sr.get('blocked')==v

def calc(filt_fn):
    rows = [d for d in closed_data if filt_fn(d)]
    n = len(rows)
    k = sum(1 for d in rows if win(d))
    ers = [er_val(d) for d in rows if er_val(d) is not None]
    avg_r = sum(ers)/len(ers) if ers else 0
    lo,hi = wilson(k,n)
    return k,n,lo,hi,avg_r
```

---

## 生出力

### blocked×direction クロス表 (N=883決済済)

| ラベル | k/n | 勝率 | 95%CI | E(R) |
|---|---|---|---|---|
| blocked=True ALL       | 37/78  | 47.4% | [36.7~58.4] | +0.105 |
| blocked=True × Long    | 18/44  | 40.9% | [27.7~55.6] | -0.047 |
| blocked=True × Short   | 19/34  | 55.9% | [39.5~71.1] | +0.302 |
| blocked=False ALL      | 189/479| 39.5% | [35.2~43.9] | -0.081 |
| blocked=False × Long   | 145/365| 39.7% | [34.8~44.8] | -0.074 |
| blocked=False × Short  | 44/114 | 38.6% | [30.2~47.8] | -0.101 |
| SR無し ALL              | 128/326| 39.3% | [34.1~44.7] | -0.085 |
| 全体 ALL               | 354/883| 40.1% | [36.9~43.4] | -0.066 |

### 探索的: blocked=True×Short × signal種別

| signal | k/n | 勝率 | CI |
|---|---|---|---|
| ma_dead × short × blocked=True  | 10/11 | 90.9% | [62.3~98.4] |
| ma_golden × long × blocked=True | 9/13  | 69.2% | [42.4~87.3] |
| macd_dead × short × blocked=True | 7/19 | 36.8% | [19.1~59.0] |
| macd_golden × long × blocked=True| 9/25 | 36.0% | [20.2~55.5] |

### 参照: #5時点(2026-06-13) blocked=True ALL

- #5時点: 22/41 = 53.7% CI[38.7~67.9]（N=41）
- 現在:   37/78 = 47.4% CI[36.7~58.4]（N=78）
- 変化: N=41→78（ほぼ倍増）で勝率は 53.7% → 47.4% に希薄化

### FDR多重検定結果（スイープ参照）
- blocked=True ALL: q≒0.576（FDR未通過）
- blocked=True×Short: q≒0.331（FDR未通過）

---

## 交絡点検

- blocked=True の組成: Long 44/78 = 56.4%, Short 34/78 = 43.6%
- blocked=True は全シグナルの 78/883 = 8.8%
- blocked=False は全シグナルの 479/883 = 54.2%
- SR無し（sr_runway=null）は 326/883 = 36.9%

- blocked=True×Short の signal 内訳: ma_dead×S=11, macd_dead×S=19, first_pullback_short×S=2, fib_pullback_short×S=1, double_top×S=1 → 計34
- ma_dead×short×blocked=True の 10/11=90.9%は N小さすぎ・探索的のみ

---

## トラッカー更新 (2026-06-22)

スイープ: FDR通過 9本 → すべて既登録（重複スキップ）
昇格/反証: なし

---

## 判定

主仮説:
- blocked=True × Short: 55.9%(19/34) CI下限39.5% < 43% → 確定打なし
- ただし blocked=False × Short (38.6%) より 17.3pp高く、方向性非対称は明確
- 🟡 通過A方向（CI不足・継続観察）

探索的:
- ma_dead×short×blocked=True: 90.9%(10/11) → N=11小サンプル・探索的記録のみ

事前宣言基準（新設）:
- blocked=True × Short: 前向きN≥30 かつ 平均R の CI下限>0
