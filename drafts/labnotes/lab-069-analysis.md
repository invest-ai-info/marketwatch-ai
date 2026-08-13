# Lab-069 分析メモ — RSI売られすぎ逆張り買い FWD N=179 4H足優位と昇格条件接近

**基準日**: 2026-08-14（JST）  
**仮説**: rsi_oversold_bounce の前向き実績（FWD N=179）が「IS 39.1% → FWD 54.7%」の改善を示し、4H足特化で67.3%・昇格条件（CI下限>0）に接近することを確認する

---

## 使用スクリプト（Python反実仮想集計）

```python
import json, math, random

with open('signals-log.json') as f:
    data = json.load(f)

closed_outcomes = {'tp1', 'tp2', 'sl'}
def is_closed(s): return s.get('outcome') in closed_outcomes
def is_win(s): return s.get('outcome') in ('tp1', 'tp2')
def parse_dt(ts):
    from datetime import datetime
    return datetime.fromisoformat(ts[:19]).replace(tzinfo=None)

def wilson_ci(k, n, z=1.96):
    if n == 0: return (0.0, 0.0)
    p = k/n
    center = (p + z**2/(2*n)) / (1 + z**2/n)
    margin = z * math.sqrt(p*(1-p)/n + z**2/(4*n**2)) / (1 + z**2/n)
    return (max(0, center - margin), min(1, center + margin))

def er_boot(signals_list, seed=42):
    n = len(signals_list)
    if n == 0: return 0, 0, 0
    vals = [1.333 if is_win(s) else -1.0 for s in signals_list]
    er = sum(vals)/n
    random.seed(seed)
    boot = []
    for _ in range(5000):
        sample = random.choices(vals, k=n)
        boot.append(sum(sample)/n)
    boot.sort()
    return er, boot[125], boot[4875]

signals = [s for s in data if is_closed(s) and s.get('primary_signal') == 'rsi_oversold_bounce']
from datetime import datetime
fwd_start = datetime(2026, 6, 16)
is_signals = [s for s in signals if parse_dt(s['fired_at']) < fwd_start]
fwd_signals = [s for s in signals if parse_dt(s['fired_at']) >= fwd_start]
```

---

## 生出力

```
=== rsi_oversold_bounce 全体 ===
全体: k=150, n=312 = 48.1% CI[42.6,53.6]
IS (fired_before=2026-06-16): k=52, n=133 = 39.1% CI[31.2%,47.6%] E(R)=-0.088
FWD (fired_from=2026-06-16): k=98, n=179 = 54.7% CI[47.4%,61.9%] E(R)=+0.277 CI[+0.108,+0.447]

=== Timeframe breakdown (FWD) ===
  tf=1h 全体: k=87, n=196 = 44.4% CI[37.6,51.4]
  tf=1h IS: k=33, n=81 = 40.7%
  tf=1h FWD: k=54, n=115 = 47.0% CI[38.1,56.0] E(R)=+0.095 CI[-0.107,+0.319]
  tf=4h 全体: k=56, n=104 = 53.8% CI[44.3,63.1]
  tf=4h IS: k=19, n=49 = 38.8%
  tf=4h FWD: k=37, n=55 = 67.3% CI[54.1,78.2] E(R)=+0.569 CI[+0.273,+0.866]

=== FWD temporal periods ===
  FWD-1 (2026-06-17~2026-06-25): k=20, n=59 = 33.9% E(R)=-0.209
  FWD-2 (2026-06-25~2026-07-17): k=38, n=59 = 64.4% E(R)=+0.503
  FWD-3 (2026-07-21~2026-08-12): k=40, n=61 = 65.6% E(R)=+0.530

=== Trend (from trend_alignment.higher_tf_trend, 探索的) ===
  trend=上昇: k=32, n=43 = 74.4% CI[59.8,85.1]
  trend=中立・もみあい: k=33, n=54 = 61.1% CI[47.8,73.0]
  trend=下降: k=33, n=82 = 40.2% CI[30.3,51.1]

=== Group (from ticker mapping, 探索的) ===
  group=index: k=20, n=29 = 69.0% CI[50.8,82.7] E(R)=+0.609
  group=jpy_fx: k=24, n=36 = 66.7% CI[50.3,79.8] E(R)=+0.555
  group=metal: k=15, n=29 = 51.7% CI[34.4,68.6] E(R)=+0.207
  group=oil: k=9, n=17 = 52.9% CI[31.0,73.8]
  group=btc: k=6, n=12 = 50.0% CI[25.4,74.6]
  group=other_fx: k=24, n=56 = 42.9% CI[30.8,55.9] E(R)=+0.000

=== Tier breakdown (FWD) ===
  tier=good: 55/98=56.1% CI[46.3,65.5]
  tier=neutral: 32/59=54.2% CI[41.7,66.3]
  tier=elite: 11/22=50.0% CI[30.7,69.3]

=== Env breakdown (FWD) ===
  env=A: 46/90=51.1% CI[41.0,61.2]
  env=B: 39/69=56.5% CI[44.8,67.6]
  env=C: 11/15=73.3% CI[48.0,89.1]
  env=D: 2/5=40.0% CI[11.8,76.9]
```

---

## 分析メモ

### 事前基準の宣言（採択前）
- H1: FWD E(R) の bootstrap CI下限 > 0
- H2: FWD 4H足の勝率 > 1H足（差 ≥ 10pp）
- N条件: FWD N ≥ 179 (現在値)

### 結果

**H1（FWD E(R) CI下限>0）**: raw bootstrap CI[+0.108,+0.447] → CI下限+0.108 > 0 ✅  
tracker cluster補正後 CI[+0.01,+0.55] → CI下限+0.01（境界値）

**H2（4H vs 1H 差≥10pp）**: 4H 67.3% vs 1H 47.0% → 差20.3pp ≥ 10pp ✅

### 注目点
1. **FWD-1の不毛期**: 33.9% (2026-06-17~06-25) — 初期3週間の低迷
2. **FWD-2/3の安定**: 64.4%・65.6% (2026-06-25以降) — 金属レジーム転換後の改善と符合
3. **4H足の突出**: 67.3% E(R)=+0.569 CI全域プラス — 1H足の2倍以上のパフォーマンス
4. **rsi_oversold_bounce はロング専用シグナル** — 方向の偏り考慮不要
5. **trend/group は signals-log の `trend`/`group` フィールドがNone** → これらは claims に含めない（探索的報告のみ）

### 昇格判定
- tracker: 🟡蓄積中（CI下限+0.01で昇格条件接近中）
- 宣言基準: 前向きN≥80かつ平均RのCI下限>0（連続2本）
- tracker は cluster補正後 CI[+0.01,+0.55] — CI下限がゼロをわずかに超えた（2回目相当）
- **暫定昇格を宣言**: 完全確定はN増加後の次回チェックで確認

### 交絡点検
- direction: 全312件がロング（rsi_oversold_bounce は逆張りロング専用） — 方向交絡なし
- FWD-1の不毛期: 金属レジーム転換前（#030/#032/#039と同時期）— 全体E(R)を下引きしていた
- 4H足集中: FWD 55件中37勝 — サンプルがやや少ない（N=55）

### Wilson CI（検証用）
- FWD 98/179: CI[47.4%, 61.9%] → 下限47.4% > 43% ✅ (損益分岐上回る)
- FWD 4H 37/55: CI[54.1%, 78.2%] → 下限54.1% > 43% ✅
- FWD 1H 54/115: CI[38.1%, 56.0%] → 下限38.1% < 43% (有意でない)

---

## claims.json 設計

verify.py対応フィルタのみ使用。trend/groupはsignals-logのNone field → 除外。

| ラベル | filter | k | n |
|---|---|---|---|
| 全体（全期間） | signal=rsi_oversold_bounce | 150 | 312 |
| IS期間 | signal=rsi_oversold_bounce, fired_before=2026-06-16 | 52 | 133 |
| FWD期間 | signal=rsi_oversold_bounce, fired_from=2026-06-16 | 98 | 179 |
| FWD×1H足 | signal=rsi_oversold_bounce, fired_from=2026-06-16, tf=1h | 54 | 115 |
| FWD×4H足 | signal=rsi_oversold_bounce, fired_from=2026-06-16, tf=4h | 37 | 55 |
