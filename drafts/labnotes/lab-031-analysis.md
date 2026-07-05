# lab-031-analysis: selection.tier 4段階の損益序列検証
# 基準日: 2026-07-05 / signals-log.json closed N=1356 (with_tier=1028)

## 実行スクリプト

```python
import json, math, statistics

with open('signals-log.json') as f:
    data = json.load(f)
signals = data if isinstance(data, list) else data.get('signals', [])
closed = [s for s in signals if s.get('outcome') in ('tp1','sl','expired')]
with_tier = [s for s in closed if s.get('selection') and s['selection'].get('tier')]

def win(s): return 1 if s.get('outcome')=='tp1' else 0
def r_val(s):
    o = s.get('outcome')
    if o == 'tp1':
        tp1 = abs(s.get('tp1_pct', 2.0))
        sl  = abs(s.get('sl_pct', 1.5))
        return (tp1/sl) if sl else 1.33
    return -1.0 if o == 'sl' else 0.0

def group_of(s):
    t = s.get('ticker','')
    if t in ['GC=F','SI=F']: return 'metal'
    if t in ['NKD=F','ES=F','NQ=F','YM=F','^FTSE']: return 'index'
    if t in ['BTC-USD']: return 'btc'
    if t == 'CL=F': return 'oil'
    if t in ['USDJPY=X','EURJPY=X','GBPJPY=X','AUDJPY=X']: return 'jpy_fx'
    if t in ['EURUSD=X','GBPUSD=X','AUDUSD=X','EURAUD=X','GBPAUD=X']: return 'other_fx'
    return 'unknown'

def full_stats(ss):
    k = sum(win(s) for s in ss); n = len(ss)
    if n == 0: return None
    p = k/n; z = 1.96
    denom = 1 + z**2/n
    center = (p + z**2/(2*n))/denom
    delta = (z/denom)*math.sqrt(p*(1-p)/n + z**2/(4*n**2))
    rs = [r_val(s) for s in ss]; avg_r = sum(rs)/len(rs)
    se_r = statistics.stdev(rs)/math.sqrt(len(rs)) if len(rs)>=2 else 0
    return dict(k=k,n=n,p=p,ci_lo=center-delta,ci_hi=center+delta,
                avg_r=avg_r,r_lo=avg_r-1.96*se_r,r_hi=avg_r+1.96*se_r)
```

## 生出力

### 全体 (1028 signals with tier)

Total closed: 1356
With tier:   1028
Without:      328 (旧シグナル・selection フィールド未記録)

### Tier 比較 (メイン結果)

| tier    | k   | n   | WR     | 95%CI                   | E(R)   | R 95%CI             |
|---------|-----|-----|--------|-------------------------|--------|---------------------|
| elite   |  60 | 126 | 47.6%  | [39.1% ~ 56.3%]         | +0.111 | [-0.093 ~ +0.315]   |
| good    |  94 | 232 | 40.5%  | [34.4% ~ 46.9%]         | -0.055 | [-0.202 ~ +0.093]   |
| neutral | 125 | 350 | 35.7%  | [30.9% ~ 40.9%]         | -0.161 | [-0.278 ~ -0.044]   |
| avoid   | 147 | 320 | 45.9%  | [40.6% ~ 51.4%]         | +0.072 | [-0.056 ~ +0.199]   |

★ 設計意図: elite > good > neutral > avoid
★ 実際の序列: elite(47.6%) > avoid(45.9%) > good(40.5%) > neutral(35.7%) ← avoid と good が逆転！

### H1 検証: tier=neutral CI上限 < 43%

tier=neutral: k=125/350, WR=35.7%, CI[30.9%~40.9%]
→ CI上限 40.9% < 43% ✅ H1通過
→ E(R) RCI[-0.278~-0.044]: CI上限=-0.044 < 0 → E(R)も全域マイナス確認

### H2 検証: tier=avoid > tier=good (探索的)

avoid=45.9% vs good=40.5%: 5.4pp差
CI: avoid[40.6%~51.4%] vs good[34.4%~46.9%] → 重複あり → 統計的確定打なし
→ 探索的発見 (要継続観察)

### Direction breakdown

| tier×dir  | k   | n   | WR    | 95%CI              | E(R)   |
|-----------|-----|-----|-------|--------------------|--------|
| elite×L   |  39 |  78 | 50.0% | [39.2%~60.8%]     | +0.167 |
| elite×S   |  21 |  48 | 43.8% | [30.7%~57.7%]     | +0.021 |
| good×L    |  87 | 222 | 39.2% | [33.0%~45.7%]     | -0.086 |
| good×S    |   7 |  10 | 70.0% | [39.7%~89.2%]     | +0.633 |
| neutral×L |  70 | 190 | 36.8% | [30.3%~43.9%]     | -0.135 |
| neutral×S |  55 | 160 | 34.4% | [27.5%~42.0%]     | -0.192 |
| avoid×L   | 114 | 249 | 45.8% | [39.7%~52.0%]     | +0.068 |
| avoid×S   |  33 |  71 | 46.5% | [35.4%~58.0%]     | +0.085 |

注: good の N=232のうち 222件がロング(95.7%)。good は事実上ロング専用ティアの様相。

### Group breakdown (主要)

| tier×group   | k  | n  | WR    | E(R)   |
|--------------|----|----|-------|--------|
| elite×index  | 13 | 22 | 59.1% | +0.379 |
| elite×other_fx| 29|  53 | 54.7% | +0.277 |
| elite×jpy_fx | 16 | 33 | 48.5% | +0.131 |
| elite×metal  |  1 | 13 |  7.7% | -0.821 |
| good×index   | 32 | 69 | 46.4% | +0.082 |
| good×jpy_fx  | 16 | 39 | 41.0% | -0.043 |
| good×other_fx| 27 | 66 | 40.9% | -0.045 |
| good×metal   |  9 | 34 | 26.5% | -0.382 |
| good×btc     |  7 | 11 | 63.6% | +0.485 |
| good×oil     |  3 | 13 | 23.1% | -0.462 |
| neutral×index| 31 | 73 | 42.5% | -0.009 |
| neutral×jpy_fx|14 | 59 | 23.7% | -0.446 |
| neutral×other| 26 | 77 | 33.8% | -0.212 |
| neutral×metal| 27 | 82 | 32.9% | -0.232 |
| avoid×index  | 49 | 91 | 53.8% | +0.256 |
| avoid×jpy_fx | 29 | 76 | 38.2% | -0.110 |
| avoid×other_fx|40 | 90 | 44.4% | +0.037 |
| avoid×metal  | 16 | 31 | 51.6% | +0.204 |

★ good が低い主因: good×metal=26.5%(N=34), good×oil=23.1%(N=13) が足を引く
★ avoid が高い主因: avoid×index=53.8%(N=91), avoid×index×L=45/77=58.4% が押し上げる
★ neutral の最悪: neutral×jpy_fx=23.7%(N=59) が底を作る

### avoid veto breakdown (探索的・verify.py非対応次元)

| veto条件           | k  | n   | WR    | E(R)   |
|-------------------|-----|-----|-------|--------|
| veto_chasing only | 66 | 151 | 43.7% | +0.020 |
| veto_runway only  | 46 |  98 | 46.9% | +0.095 |
| both vetoあり     | 19 |  41 | 46.3% | +0.081 |

veto_runway (blocked=True) シグナル = sr_runway.blocked=True で全161件該当
→ #005/#006で確認した「blocked=True は意外と強い」と整合

### 前向きトラッカー関連 (signal-lab-tracker.json 参照)

tier=good (gate):  26/36=72%, E(R)=+0.685, CI[+0.30~+1.07] N=36蓄積中
tier=neutral (gate): 51/130=39%, E(R)=-0.085, CI[-0.32~+0.15] N=130蓄積中

## 仮説まとめ

H1: tier=neutral CI上限 < 43% → ✅ 通過A (35.7%, CI上限40.9%<43%, N=350≥100)
    さらに E(R) RCI上限=-0.044<0 → E(R)も全域マイナス確認

H2 (探索的): tier=avoid(45.9%) > tier=good(40.5%) の逆転
    → 探索的確認 (差5.4pp、CI重複のため確定打なし)

## 交絡点検

- tiered sample (N=1028) vs no-tier (N=328): tieredは比較的新しいシグナルのみ
  → 旧シグナルに偏りがある可能性あり (バイアス方向: tieredの方が最近の相場)
- avoid のグループ偏り: avoid×index=28% vs good×index=30% → ほぼ同等
  → グループ構成差では説明できない (5.4pp差の主因ではない)
- good のロング偏在: good×L = 222/232 = 95.7% → ほぼ全件ロング
  → good は「aligned=True 全条件クリア・vetoes なし」の純粋トレンドフォロー ロング集中
  → ロング全般の苦手期間 (IS E(R)=-0.161→FWD+0.231) と時期重複の可能性
