# AIシグナル研究日誌 #078 分析ノート
## 仮説: RSI売られすぎ逆張り買い FWD N=232 WCI下限 46.2%で損益分岐突破——4H足 66.7%・1H足 44.6%の構造差解明

生成日: 2026-08-23  
生成者: signal-lab-daily routine (claude-sonnet-4-6)

---

## 実行スクリプト

```python
import json, math
from collections import Counter

with open('signals-log.json') as f:
    all_sigs = json.load(f)

FWD_CUTOFF = "2026-06-16"

# From signal_lab_verify.py GROUPS
GROUPS = {
    "jpy_fx": {"USDJPY=X","EURJPY=X","GBPJPY=X","AUDJPY=X"},
    "other_fx": {"EURUSD=X","GBPUSD=X","AUDUSD=X","EURAUD=X","GBPAUD=X"},
    "metal": {"GC=F","SI=F"},
    "oil": {"CL=F"},
    "btc": {"BTC-USD"},
    "index": {"NKD=F","ES=F","NQ=F","YM=F","^FTSE"},
}

def closed(s): return s.get('outcome') in ('tp1','tp2','sl')
def win(s): return s.get('outcome') in ('tp1','tp2')
def get_trend(s):
    ta = s.get('trend_alignment', {})
    if isinstance(ta, dict): return ta.get('higher_tf_trend', '中立・もみあい')
    return '中立・もみあい'

def wilson(k, n, z=1.96):
    if n == 0: return (0, 0)
    p = k/n
    den = 1 + z*z/n
    c = (p + z*z/(2*n)) / den
    pm = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / den
    return (max(0, c-pm)*100, min(1, c+pm)*100)

fwd = [s for s in all_sigs 
       if s.get('primary_signal') == 'rsi_oversold_bounce'
       and s.get('fired_at','') >= FWD_CUTOFF
       and closed(s)]

is_all = [s for s in all_sigs 
          if s.get('primary_signal') == 'rsi_oversold_bounce'
          and s.get('fired_at','') < FWD_CUTOFF
          and closed(s)]

def stat(sigs, label=""):
    k = sum(1 for s in sigs if win(s))
    n = len(sigs)
    pct = 100*k/n if n else 0
    wlo, whi = wilson(k, n)
    print(f"{label}: k={k}, n={n}, win={pct:.1f}%, WCI[{wlo:.1f}%,{whi:.1f}%]")
    return k, n

stat(is_all, "IS all")
stat(fwd, "FWD all")
for tf in ('1h','4h','1d'):
    ss = [s for s in fwd if s.get('timeframe','').lower() == tf]
    if ss: stat(ss, f"FWD tf={tf}")
for g in ['jpy_fx','other_fx','metal','oil','btc','index']:
    ss = [s for s in fwd if s.get('ticker','') in GROUPS[g]]
    if ss: stat(ss, f"FWD group={g}")
for tr in ['上昇','下降','中立・もみあい']:
    ss = [s for s in fwd if get_trend(s) == tr]
    if ss: stat(ss, f"FWD trend={tr}")
ss_4hj = [s for s in fwd if s.get('timeframe','').lower() == '4h' and s.get('ticker','') in GROUPS['jpy_fx']]
if ss_4hj: stat(ss_4hj, "FWD 4H×jpy_fx")
fwd_bb = [s for s in all_sigs 
          if s.get('primary_signal') == 'bb_lower_touch'
          and s.get('fired_at','') >= FWD_CUTOFF
          and closed(s)]
stat(fwd_bb, "FWD bb_lower_touch")
```

---

## 生出力

```
IS all: k=52, n=133, win=39.1%, WCI[31.2%,47.6%]
FWD all: k=122, n=232, win=52.6%, WCI[46.2%,58.9%]
FWD tf=1h: k=70, n=157, win=44.6%, WCI[37.0%,52.4%]
FWD tf=4h: k=42, n=63, win=66.7%, WCI[54.4%,77.1%]
FWD tf=1d: k=10, n=12, win=83.3%, WCI[55.2%,95.3%]
FWD group=jpy_fx: k=31, n=47, win=66.0%, WCI[51.7%,77.8%]
FWD group=other_fx: k=28, n=63, win=44.4%, WCI[32.8%,56.7%]
FWD group=metal: k=19, n=34, win=55.9%, WCI[39.5%,71.1%]
FWD group=oil: k=9, n=17, win=52.9%, WCI[31.0%,73.8%]
FWD group=btc: k=7, n=13, win=53.8%, WCI[29.1%,76.8%]
FWD group=index: k=28, n=58, win=48.3%, WCI[35.9%,60.8%]
FWD trend=上昇: k=42, n=63, win=66.7%, WCI[54.4%,77.1%]
FWD trend=下降: k=37, n=89, win=41.6%, WCI[31.9%,52.0%]
FWD trend=中立・もみあい: k=43, n=80, win=53.8%, WCI[42.9%,64.3%]
FWD 4H×jpy_fx: k=15, n=16, win=93.8%, WCI[71.7%,98.9%]
FWD bb_lower_touch: k=239, n=540, win=44.3%, WCI[40.1%,48.5%]
```

---

## 解釈メモ

**H1**: FWD all WCI下限 46.2% > 43% ✅ 損益分岐を初めて上回る  
**H2**: FWD 4H WCI下限 54.4% >> 43% ✅ 鮮明なエッジ確立  
**H3**: FWD 1H WCI下限 37.0% < 43% ✅ 無エッジ（CI 43%を含む）  

主要発見:
- 4H足（66.7%）と1H足（44.6%）に22.1pp差の大きな構造的乖離
- jpy_fx（66.0%）が主要ドライバー。特に4H×jpy_fx=93.8%（N=16・小サンプル注意）
- IS 39.1%からFWD 52.6%へ+13.5ppの改善
- bb_lower_touch比較: 52.6% vs 44.3% = +8.3ppの優位性

**注意点**: 
- 4H×jpy_fx N=16は小サンプル（WCI幅大）
- 1D足 N=12も参考程度
- トレンド別: 上昇66.7%（= 4Hと完全一致、交絡あり）

記事番号: #078  
tracker仮説ID: rsi_oversold_edge（2026-06-16 registered）
