# lab-102-analysis.md
# 検証日: 2026-09-18 (JST)
# 仮説: trend=中立・もみあい × dir=short の前向き反証分析

## スクリプト

```python
import signal_lab_sweep as sl
import json, math, collections, datetime

with open('signals-log.json') as f:
    data = json.load(f)

cl = [e for e in data if sl.closed(e)]
REG_DATE = '2026-06-17'

neutral_short = [e for e in cl if sl.match(e, {'trend': '中立・もみあい', 'direction': 'short'})]
oos = [e for e in neutral_short if e.get('fired_at','')[:10] >= REG_DATE]
iis = neutral_short

def wilson_ci(k, n, z=1.96):
    if n == 0: return (0.0, 0.0)
    p = k/n
    denom = 1 + z**2/n
    center = (p + z**2/(2*n)) / denom
    margin = z * math.sqrt(p*(1-p)/n + z**2/(4*n**2)) / denom
    return (max(0, center - margin), min(1, center + margin))

def er_stats(entries):
    rs = []
    for e in entries:
        result = e.get('outcome','')
        if result == 'tp1':
            rs.append(e.get('tp1_pct', 0) / e.get('sl_pct', -1) * -1 if e.get('sl_pct') else 2.0)
        elif result == 'sl':
            rs.append(-1.0)
    if not rs: return None, None, None
    n = len(rs)
    mean = sum(rs)/n
    se = math.sqrt(sum((r-mean)**2 for r in rs)/max(n-1,1)) / math.sqrt(n)
    return mean, mean - 1.96*se, mean + 1.96*se
```

## 生出力

```
total closed: 4527
neutral×short IS: 339
IS wins: 140

=== IS (全期間) ===
IS: 140/339 = 41.3%  Wilson95%CI [36.2~46.6%]

=== OOS (from 2026-06-17) ===
OOS: 112/295 = 38.0%  Wilson95%CI [32.6~43.6%]
OOS 期待値R: -0.114  CI[-0.24~+0.02]

=== Pre-reg (IS before 2026-06-17) ===
Pre-reg: 28/44 = 63.6%

=== OOS by primary_signal ===
  macd_dead: 62/162 = 38.3%
  low_break: 35/86 = 40.7%
  ma_dead: 13/38 = 34.2%
  first_pullback_short: 2/9 = 22.2%

=== OOS by timeframe ===
  1h: 58/155 = 37.4%
  4h: 51/130 = 39.2%
  1d: 3/10 = 30.0%

=== OOS quarterly ===
  2026Q2: 15/43 = 34.9%  CI[22.4~49.8%]
  2026Q3: 97/252 = 38.5%  CI[32.7~44.6%]

=== OOS by group/ticker ===
  SI=F: 10/33 = 30.3%
  NQ=F: 11/26 = 42.3%
  EURAUD=X: 6/23 = 26.1%
  NKD=F: 12/22 = 54.5%
  AUDJPY=X: 9/21 = 42.9%
  BTC-USD: 5/20 = 25.0%
  GBPAUD=X: 10/19 = 52.6%
  AUDUSD=X: 5/17 = 29.4%

=== OOS by env_score ===
  env=A: 73/203 = 36.0%
  env=B: 24/61 = 39.3%
  env=C: 11/24 = 45.8%
  env=D: 4/7 = 57.1%
```

## 考察

- Pre-reg N=44の63.6%は、登録前の小サンプルノイズだった可能性が高い
- IS全体(N=339)では41.3%で、既に損益分岐43%未満
- OOS(N=295)は38.0%にさらに悪化し、期待値Rは-0.114
- トラッカーの宣言基準「CI下限>0」に対し、CI[-0.24~+0.02]と大幅未達 → ⛔反証確定
- OOS全シグナル種で損益分岐未達（macd_dead 38.3%、low_break 40.7%、ma_dead 34.2%）
- 時間足別でも差はなく（1h 37.4%、4h 39.2%）、もみあい×ショートの弱さは普遍的
- Q2→Q3で横ばい（34.9%→38.5%）：時系列の改善兆候も見られない
- 環境スコア別では env=D のみ57.1%だが N=7 と小さく参考値
- 教訓：小サンプル(N<50)の高勝率発見は信用しない・前向きN=295での収束を待って判断
