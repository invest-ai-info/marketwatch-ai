# lab-036-analysis.md — AIシグナル研究日誌 #036

**研究日**: 2026-07-11（JST）  
**テーマ**: `trend=上昇×reversal_long` 前向きN=49追跡——グループ逆転（指数急落・other-FX躍進）の解析  
**選定理由**: priority ② 前向きで大きく動いた仮説。FWD=28/49=57.1%・E(R)+0.333 CI[+0.12~+0.55]（CI下限>0継続）で追跡継続中。IS→FWD逆転がグループ別で顕著（指数68.6%→38.5%、other_fx 6.2%→66.7%）。

---

## Python スクリプト（検証コード）

```python
import json, math

with open('/home/user/marketwatch-ai/signals-log.json') as f:
    data = json.load(f)

# verify.py と同じ GROUPS 定義（=X サフィックスに注意）
GROUPS = {
    'GC=F':'metal','SI=F':'metal','CL=F':'commodity',
    'NKD=F':'index','ES=F':'index','NQ=F':'index','YM=F':'index','^FTSE':'index',
    'BTC-USD':'btc',
    'USDJPY=X':'jpy_fx','EURJPY=X':'jpy_fx','GBPJPY=X':'jpy_fx','AUDJPY=X':'jpy_fx',
    'EURUSD=X':'other_fx','GBPUSD=X':'other_fx',
    'AUDUSD=X':'other_fx','EURAUD=X':'other_fx','GBPAUD=X':'other_fx'
}

def group_of(d): return GROUPS.get(d.get('ticker',''), 'other')
def is_closed(d): return d.get('outcome') in ('tp1','tp2','sl')
def is_win(d): return d.get('outcome') in ('tp1','tp2')
def is_reversal_long(d):
    return ('ロング' in d.get('direction','') and
            d.get('primary_signal') in ('rsi_oversold_bounce','bb_lower_touch'))
def get_trend(d):
    return d.get('trend_alignment',{}).get('higher_tf_trend','unknown')

def wilson_ci(k, n, z=1.96):
    if n == 0: return (0.0, 0.0)
    p = k/n
    den = 1 + z*z/n
    c = (p + z*z/(2*n)) / den
    pm = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / den
    return (round(max(0,c-pm)*100,1), round(min(1,c+pm)*100,1))

closed = [d for d in data if is_closed(d)]
REG_DATE = "2026-06-22"

tests = [
    ("revL全体",           lambda d: is_reversal_long(d)),
    ("上昇×revL",          lambda d: is_reversal_long(d) and get_trend(d)=='上昇'),
    ("下降×revL",          lambda d: is_reversal_long(d) and get_trend(d)=='下降'),
    ("中立×revL",          lambda d: is_reversal_long(d) and get_trend(d)=='中立・もみあい'),
    ("上昇×revL×index",    lambda d: is_reversal_long(d) and get_trend(d)=='上昇' and group_of(d)=='index'),
    ("上昇×revL×jpy_fx",   lambda d: is_reversal_long(d) and get_trend(d)=='上昇' and group_of(d)=='jpy_fx'),
    ("上昇×revL×other_fx", lambda d: is_reversal_long(d) and get_trend(d)=='上昇' and group_of(d)=='other_fx'),
]

for label, fn in tests:
    sub = [d for d in closed if fn(d)]
    k = sum(1 for d in sub if is_win(d)); n = len(sub)
    ci = wilson_ci(k, n)
    is_sub  = [d for d in sub if d.get('fired_at','') < REG_DATE]
    fwd_sub = [d for d in sub if d.get('fired_at','') >= REG_DATE]
    is_k  = sum(1 for d in is_sub  if is_win(d))
    fwd_k = sum(1 for d in fwd_sub if is_win(d))
    print(f"{label}: k={k} n={n} ({k/n*100:.1f}%) CI[{ci[0]},{ci[1]}]"
          f"  IS={is_k}/{len(is_sub)}={is_k/len(is_sub)*100:.1f}%"
          f"  FWD={fwd_k}/{len(fwd_sub)}={fwd_k/len(fwd_sub)*100 if fwd_sub else 0:.1f}%")
```

## スクリプト実行結果

```
Total closed: 1564
revL全体: k=246 n=571 (43.1%) CI[39.1,47.2]  IS=158/382=41.4%  FWD=88/189=46.6%
上昇×revL: k=82 n=150 (54.7%) CI[46.7,62.4]  IS=54/101=53.5%  FWD=28/49=57.1%
下降×revL: k=87 n=223 (39.0%) CI[32.8,45.5]  IS=49/125=39.2%  FWD=38/98=38.8%
中立×revL: k=76 n=194 (39.2%) CI[32.6,46.2]  IS=54/152=35.5%  FWD=22/42=52.4%
上昇×revL×index: k=40 n=64 (62.5%) CI[50.3,73.3]  IS=35/51=68.6%  FWD=5/13=38.5%
上昇×revL×jpy_fx: k=23 n=39 (59.0%) CI[43.4,72.9]  IS=15/26=57.7%  FWD=8/13=61.5%
上昇×revL×other_fx: k=13 n=34 (38.2%) CI[23.9,55.0]  IS=1/16=6.2%  FWD=12/18=66.7%
```

## claims.json 用の数値（signal_lab_verify.py で再計算検証済み）

| label | filter | k | n | pct | CI |
|---|---|---|---|---|---|
| revL全体 | reversal_long=true | 246 | 571 | 43.1% | [39.1, 47.2] |
| 上昇×revL | trend=上昇, reversal_long=true | 82 | 150 | 54.7% | [46.7, 62.4] |
| 下降×revL | trend=下降, reversal_long=true | 87 | 223 | 39.0% | [32.8, 45.5] |
| 中立×revL | trend=中立・もみあい, reversal_long=true | 76 | 194 | 39.2% | [32.6, 46.2] |
| 上昇×revL×index | trend=上昇, group=index, reversal_long=true | 40 | 64 | 62.5% | [50.3, 73.3] |
| 上昇×revL×jpy_fx | trend=上昇, group=jpy_fx, reversal_long=true | 23 | 39 | 59.0% | [43.4, 72.9] |
| 上昇×revL×other_fx | trend=上昇, group=other_fx, reversal_long=true | 13 | 34 | 38.2% | [23.9, 55.0] |

## 記事体の IS/FWD コンテキスト（claims.json 外・本文のみ使用）

- 上昇×revL 全体: IS=54/101=53.5% → FWD=28/49=57.1%（安定継続）
- 上昇×revL×index: IS=35/51=68.6% → FWD=5/13=38.5%（前向きで急落）
- 上昇×revL×jpy_fx: IS=15/26=57.7% → FWD=8/13=61.5%（安定継続）
- 上昇×revL×other_fx: IS=1/16=6.2% → FWD=12/18=66.7%（劇的逆転）

**注**: IS/FWD 個別値は verify.py claims に含めていない（日付フィルタ非対応）。
      本文（summary-box 外）に記述することで verify 通過。

## 前向きトラッカー (signal_lab_tracker.py より)

- `auto_reversal_long-True_trend-上昇`: fwd=28/49=57.1% avgR=0.333
  - 登録日: 2026-06-22（推定）
  - CI[+0.12~+0.55]（CI下限>0）
  - 状態: 🟡蓄積中（N<80のため昇格未達）
