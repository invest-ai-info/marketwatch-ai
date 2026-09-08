# Signal Lab #092 分析ノート
## テーマ: rsi_oversold_bounce ps=1 到達 × trend=上昇×reversalL ds=1 降格警戒

**分析日**: 2026-09-08 (JST)
**担当仮説**: rsi_oversold_bounce (tracking, promote_strikes=1) / trend=上昇×reversalL (promoted, demote_strikes=1)

---

## 1. 使用スクリプト（再現可能）

```python
import json

with open('signals-log.json') as f:
    logs = json.load(f)

closed = [x for x in logs if x.get('outcome') in ('tp1','tp2','sl','expired')]

REVERSAL_LONG_SIGNALS = {'rsi_oversold_bounce','bb_lower_touch'}

def get_trend(d):
    ta = d.get('trend_alignment')
    if isinstance(ta, dict) and ta.get('higher_tf_trend'):
        return ta['higher_tf_trend']
    return None

def is_long(d):
    return 'ロング' in (d.get('direction') or '')

# [A] rsi_oversold_bounce FWD (direction=long, fired_from=2026-06-16)
fwd_os = [x for x in closed
          if x.get('primary_signal') == 'rsi_oversold_bounce'
          and is_long(x)
          and x.get('fired_at','') >= '2026-06-16']
k_os = sum(1 for x in fwd_os if x.get('outcome') in ('tp1','tp2'))
print(f'rsi_os FWD all: N={len(fwd_os)}, k={k_os}')

for tf in ['1h','4h','1d']:
    sub = [x for x in fwd_os if x.get('timeframe') == tf]
    k = sum(1 for x in sub if x.get('outcome') in ('tp1','tp2'))
    print(f'  tf={tf}: N={len(sub)}, k={k}')

# [B] trend=上昇 × reversal_long FWD
fwd_rl_up = [x for x in closed
             if x.get('fired_at','') >= '2026-06-16'
             and is_long(x)
             and x.get('primary_signal') in REVERSAL_LONG_SIGNALS
             and get_trend(x) == '上昇']
k_rl = sum(1 for x in fwd_rl_up if x.get('outcome') in ('tp1','tp2'))
print(f'trend=上昇 x reversalL FWD: N={len(fwd_rl_up)}, k={k_rl}')
```

---

## 2. 実行結果（2026-09-08）

```
rsi_os FWD all: N=308, k=158
  tf=1h: N=198, k=92
  tf=4h: N=94, k=56
  tf=1d: N=16, k=10
trend=上昇 x reversalL FWD: N=319, k=155
```

---

## 3. 導出統計（Wilson 95% CI）

### rsi_oversold_bounce FWD 全足
- 勝率: 51.3% (158/308)
- CI: [45.7%, 56.8%]

### rsi_oversold_bounce FWD 4H
- 勝率: 59.6% (56/94)
- CI: [49.5%, 68.9%]

### rsi_oversold_bounce FWD 1H
- 勝率: 46.5% (92/198)
- CI: [39.7%, 53.4%]

### trend=上昇×reversal_long FWD
- 勝率: 48.6% (155/319)
- CI: [43.2%, 54.1%]

---

## 4. トラッカー状態（cluster補正後）

### rsi_oversold_bounce (tracking)
- Forward: k=158, n=302, 52.3%, RCI[+0.033, +0.409]
- promote_strikes = 1 (本日RCI下限がプラス→1回目)
- alltime: k=210, n=435, 48.3%, RCI[-0.017, +0.270]

### trend=上昇×reversalL (promoted)
- Forward: k=139, n=287, 48.4%, RCI[-0.030, +0.290]
- demote_strikes = 1 (本日RCI下限がマイナス→降格警戒1回目)

---

## 5. 本日のストーリー

rsi_oversold_bounce の昇格ストライクカウンタが1に達した（ps=1）。
同時に、promoted 済みの trend=上昇×reversalL の降格警戒カウンタも1に達した（ds=1）。
これは対称的なシグナル: 一方が昇格に近づき、もう一方が降格警戒に入った。

4H足では59.6%と良好だが、1H足では46.5%と損益分岐点(43%)に近い。
逆張りは足の長さで大きく結果が変わることを示唆。
