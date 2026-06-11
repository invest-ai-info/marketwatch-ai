# signal-lab #003 検証ログ（labnotes）

> **目的**: 記事の数字を人間が照合するための生出力。ここに無い数字は記事に書かない。  
> **基準日**: 2026-06-12 JST（UTC 2026-06-11T21:10）  
> **仮説**: 「メタル（GC=F/SI=F）はレベル反応型＝切り番（50の倍数）近傍で逆張り勝率が上がる」  
>         「指数はトレンド文脈型＝切り番効果は弱い」

---

## スクリプト全文 (section 1〜5 を順に実行)

```python
#!/usr/bin/env python3
"""signal-lab #003 analysis — 銘柄グループ別シグナル相性 + メタル切り番効果"""
import json, math
from collections import defaultdict

with open('/home/user/marketwatch-ai/signals-log.json') as f:
    data = json.load(f)

settled = [d for d in data if d.get('outcome') in ('tp1', 'sl')]

def wilson_ci(k, n, z=1.96):
    if n == 0: return (0.0, 0.0, 0.0)
    p = k/n
    denom = 1 + z**2/n
    center = (p + z**2/(2*n)) / denom
    margin = z * math.sqrt(p*(1-p)/n + z**2/(4*n**2)) / denom
    return (p, max(0.0, center-margin), min(1.0, center+margin))

def expected_r(k, n, r_ratio=1.333):
    if n == 0: return 0.0
    p = k/n
    return round(p * r_ratio - (1-p) * 1.0, 3)

GROUPS = {
    'メタル':  {'GC=F', 'SI=F'},
    '指数':    {'NKD=F', 'ES=F', 'NQ=F', 'YM=F', '^FTSE'},
    '円ペア':  {'USDJPY=X', 'EURJPY=X', 'GBPJPY=X', 'AUDJPY=X'},
    '他FX':   {'EURUSD=X', 'GBPUSD=X', 'AUDUSD=X', 'EURAUD=X', 'GBPAUD=X'},
    'BTC':    {'BTC-USD'},
    '原油':   {'CL=F'},
}

def get_group(ticker):
    for g, ts in GROUPS.items():
        if ticker in ts: return g
    return 'その他'

COUNTER_TREND = {
    'rsi_oversold_bounce', 'rsi_overbought_reversal',
    'bb_lower_touch', 'bb_upper_touch', 'bb_upper_break', 'bb_lower_break'
}

def signal_category(signal_types):
    types = set(signal_types) if signal_types else set()
    has_ct = bool(types & COUNTER_TREND)
    has_tf = bool(types - COUNTER_TREND)
    if has_ct and not has_tf: return '逆張り'
    elif has_tf and not has_ct: return '順張り'
    elif has_ct and has_tf: return '混合'
    return '不明'

def near_round_metal(ticker, entry, threshold_pct=0.005):
    STEPS = {'GC=F': 50.0, 'SI=F': 0.5}
    step = STEPS.get(ticker)
    if step is None or not entry: return None
    dist = min(entry % step, step - entry % step)
    return (dist / entry) < threshold_pct

# セクション1: グループ別全体勝率
# セクション2: グループ×シグナル種別
# セクション3: メタル切り番効果
# セクション4: 指数切り番効果(修正版)
# セクション5: GC=F方向別 / sr_runway分析
# ※各出力は下記「生出力」セクションを参照
```

---

## 生出力（verbatim）

### セクション1: データ概要 + グループ別全体勝率

```
=== 決済済み総数: 628件 ===
  tp1(勝ち): 251件
  sl(負け): 377件

===== 1. グループ別 全体勝率 =====
  メタル   : 105件  勝率23.8%  CI[16.7%〜32.8%]  E[R]=-0.445  ❌
  指数    : 154件  勝率44.2%  CI[36.5%〜52.0%]  E[R]=+0.030  🟡
  円ペア   : 113件  勝率38.9%  CI[30.5%〜48.2%]  E[R]=-0.092  ❌
  他FX   : 178件  勝率46.6%  CI[39.4%〜54.0%]  E[R]=+0.088  🟡
  BTC   :  50件  勝率30.0%  CI[19.1%〜43.8%]  E[R]=-0.300  ❌
  原油    :  28件  勝率57.1%  CI[39.1%〜73.5%]  E[R]=+0.333  🟡
```

### セクション2: グループ×シグナル種別

```
===== 2. グループ × シグナル種別 =====
  メタル×逆張り:  53件  勝率13.2%  CI[6.5%〜24.8%]  E[R]=-0.692  ❌
  メタル×順張り:  38件  勝率36.8%  CI[23.4%〜52.7%]  E[R]=-0.140  ❌
  指数×逆張り:  65件  勝率52.3%  CI[40.4%〜64.0%]  E[R]=+0.220  🟡
  指数×順張り:  72件  勝率38.9%  CI[28.5%〜50.4%]  E[R]=-0.093  ❌
  円ペア×逆張り:  56件  勝率42.9%  CI[30.8%〜55.9%]  E[R]=-0.000  ❌
  円ペア×順張り:  51件  勝率35.3%  CI[23.6%〜49.0%]  E[R]=-0.177  ❌
  他FX×逆張り:  59件  勝率54.2%  CI[41.7%〜66.3%]  E[R]=+0.265  🟡
  他FX×順張り: 107件  勝率43.0%  CI[34.0%〜52.5%]  E[R]=+0.003  ❌
  BTC×逆張り:  30件  勝率20.0%  CI[9.5%〜37.3%]  E[R]=-0.533  ❌
  BTC×順張り:  17件  勝率41.2%  CI[21.6%〜64.0%]  E[R]=-0.039  ❌
  原油×逆張り:  14件  勝率71.4%  CI[45.4%〜88.3%]  E[R]=+0.666  ✅
  原油×順張り:  13件  勝率46.2%  CI[23.2%〜70.9%]  E[R]=+0.077  🟡
```

### セクション3: メタル切り番効果（主仮説・逆張りシグナルに絞る）

```
===== 3. メタル切り番効果 (逆張りシグナルに絞る) =====
  メタル逆張り合計: 53件
  切り番近傍(0.5%以内): 36件, 遠い: 17件, 不明: 0件

  切り番近傍(0.5%以内): 36件  勝率16.7%  CI[7.9%〜31.9%]  E[R]=-0.611  ❌
    └ GC=F: 18件 勝率22.2% CI[9.0%〜45.2%]
    └ SI=F: 18件 勝率11.1% CI[3.1%〜32.8%]
  切り番から遠い: 17件  勝率5.9%  CI[1.0%〜27.0%]  E[R]=-0.863  ❌
    └ GC=F: 17件 勝率5.9% CI[1.0%〜27.0%]

GC=F近傍サンプル（entry価格, outcome）:
  [(4462.01, 'tp1'), (4537.9, 'sl'), (4518.4, 'sl'), (4508.0, 'sl'),
   (4494.5, 'sl'), (4402.2, 'tp1'), (4419.5, 'tp1'), (4365.3, 'sl')]
```

### セクション4: 指数切り番効果（修正版 step=100/1000）

```
===== 4. 指数切り番効果 (逆張りのみ, 修正版) =====
  合計: 64件  近傍: 60件  遠い: 4件
  指数 近傍: 60件 勝率53.3% CI[40.9%〜65.4%]
  指数 遠い: 4件 勝率50.0% CI[15.0%〜85.0%]

  ※ 元のstep=50 (ES=Fの誤設定) では全65件が「近傍」になった。
    step=100に修正したが近傍60/遠い4の偏りは残った。
    指数の切り番効果の検証には「遠い」N増加が必要。
```

### セクション5: GC=F 方向別 + sr_runway分析

```
--- GC=F 方向別 ---
方向分布: ロング（買い）: 47件, ショート（売り）: 18件
  GC=F ロング: 47件 勝率12.8% CI[6.0%〜25.2%]
  GC=F ショート: 18件 勝率61.1% CI[38.6%〜79.7%]

--- sr_runway: blocked vs unblocked (全グループ) ---
  blocked: 37件 勝率51.4% CI[35.9%〜66.6%] E[R]=+0.198
  unblocked: 265件 勝率39.2% CI[33.6%〜45.2%] E[R]=-0.084

--- メタル×逆張り: blocked vs unblocked ---
  メタルCT×unblocked: 30件 勝率10.0% CI[3.5%〜25.6%]
  (blocked=0件)

--- 指数×逆張り: sr_runway ---
  指数CT×unblocked: 58件 勝率51.7% CI[39.2%〜64.1%]
  (blocked=0件)
  
--- メタル週次勝率 ---
  2026-W20: 6件 勝率33.3% CI[9.7%〜70.0%]
  2026-W21: 32件 勝率18.8% CI[8.9%〜35.3%]
  2026-W22: 28件 勝率28.6% CI[15.3%〜47.1%]
  2026-W23: 39件 勝率23.1% CI[12.6%〜38.3%]
```

---

## 人間の照合チェックリスト

- [ ] GC=F ロング12.8% / ショート61.1% の数字確認（Nそれぞれ47/18）
- [ ] メタル×逆張り 切り番近傍16.7% vs 遠い5.9% の数字確認（N 36/17）
- [ ] 指数×逆張り 52.3% CI[40.4%〜64.0%] の数字確認（N=65）
- [ ] 他FX×逆張り 54.2% CI[41.7%〜66.3%] の数字確認（N=59）
- [ ] 原油×逆張り 71.4% CI[45.4%〜88.3%] の数字確認（N=14）
- [ ] SVG図の数字と上記が一致しているか確認
- [ ] compliance-reviewer(Opus) による法務監査
- [ ] 公開判断（人間による最終GO/NOGO）

---

*生成: 2026-06-12 JST | routine signal-lab-daily | 公開前検証のみ*
