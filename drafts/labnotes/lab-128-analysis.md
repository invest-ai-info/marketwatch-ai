# 研究日誌 #128 分析ノート

日付: 2026-10-19
仮説ID: rl_tf_adx_strong
仮説: 順張り×ADX強(25以上)(回避)
登録日: 2026-09-26
選定理由: 今日初めて FWD n≥80 かつ rCI 両端マイナス を同時に満たした（前向き n=87、rci_hi=-0.077 < 0）

## 使用フィルター

- family="tf" … 順張りシグナル（高値・安値ブレイク、MACD・移動平均クロス）
- adx_band="strong" … ADX≥25（相場の勢いが強い状態）
- IS期間: fired_before="2026-09-27"
- FWD期間: fired_from="2026-09-27"

## 集計結果

| 条件 | k | n | 勝率 |
|---|---|---|---|
| IS（ADX強）| 443 | 1,070 | 41.4% |
| FWD ADX強 | 28 | 87 | 32.2% |
| FWD ADX弱 | 40 | 106 | 37.7% |
| FWD ベースライン | 160 | 440 | 36.4% |

## 平均R・rCI（tracker から）

- FWD avgR = -0.276（損切り幅の0.276倍の損）
- FWD rCI = [-0.475, -0.077]（両端マイナス → 今回初）
- ベースライン avgR = -0.154（excess = -0.122）

## ウィルソン95%CI（勝率）

| 条件 | ci_lo | ci_hi |
|---|---|---|
| IS ADX強 | 38.5% | 44.4% |
| FWD ADX強 | 23.3% | 42.6% |
| FWD ADX弱 | 29.1% | 47.2% |
| FWD ベースライン | 32.0% | 41.0% |

## 昇格への進捗

- promote_min_n=80: 87回 ✅
- rCI両端マイナス: -0.475〜-0.077 ✅（今回初）
- 2回連続必要: 今回が1回目 → あと1回で ⛔反証 確定

## スクリプト（再現コード）

```python
import json, math
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))
with open('signals-log.json') as f:
    logs = json.load(f)

TF_FAMILY = {
    ('high_break', 'long'), ('low_break', 'short'),
    ('macd_golden', 'long'), ('macd_dead', 'short'),
    ('ma_golden', 'long'), ('ma_dead', 'short'),
}

def family_of(d):
    sig = d.get('primary_signal','')
    direction = d.get('direction','')
    side = 'long' if 'ロング' in direction else ('short' if 'ショート' in direction else None)
    return 'tf' if (side and (sig, side) in TF_FAMILY) else None

def adx_band_of(d):
    ind = d.get('indicators_at_signal')
    adx = ind.get('adx') if isinstance(ind, dict) else None
    if adx is None: return None
    return 'weak' if adx < 20 else ('mid' if adx < 25 else 'strong')

def parse_fired(d):
    fa = d.get('fired_at', '')
    try:
        return datetime.fromisoformat(fa.replace('Z', '+00:00')).astimezone(JST)
    except: return None

fwd_start = datetime(2026,9,27,tzinfo=JST)

def count(flt):
    k=n=0
    for d in logs:
        if d.get('outcome') not in ('tp1','tp2','sl'): continue
        fa = parse_fired(d)
        if fa is None: continue
        if 'fired_from' in flt and fa < flt['fired_from']: continue
        if 'fired_before' in flt and fa >= flt['fired_before']: continue
        if 'family' in flt and family_of(d) != flt['family']: continue
        if 'adx_band' in flt and adx_band_of(d) != flt['adx_band']: continue
        n += 1
        if d.get('outcome') in ('tp1','tp2'): k += 1
    return k, n

# Results:
# IS:  count({'family':'tf','adx_band':'strong','fired_before':fwd_start}) → (443, 1070)
# FWD strong: count({'family':'tf','adx_band':'strong','fired_from':fwd_start}) → (28, 87)
# FWD weak:   count({'family':'tf','adx_band':'weak','fired_from':fwd_start})   → (40, 106)
# baseline:   count({'fired_from':fwd_start}) → (160, 440)
```
