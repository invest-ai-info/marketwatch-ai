> ⚠️ 2026-09-24 追記（エスカレ復旧）: このメモの「IS全体」は全期間の集計、IS/FWD の数字は旧い区切り（2026-08-11）のもの。
> 公開した記事と `lab-106-claims.json` が正（全期間は「全期間」と表記・IS/FWD は登録日 2026-08-11 の翌日 2026-08-12 で区切り直し）。

# lab-106-analysis.md — #106 RSI売られすぎ×トレンド依存性

## 仮説
rsi_oversold_bounce（RSI売られすぎ逆張り買い）の勝率はトレンド環境によって系統的に異なるか。
上昇中 vs 下降中 vs 中立という3区分で比較し、IS/FWD分離で過剰フィッティングを確認する。

## 採択理由
- トラッカー優先度②: `rsi=os×trend=上昇`（前向きN=60 52%/R=+0.21）が蓄積中
- `売られすぜ逆張り買い(全足)`（前向きN=359 52%/R=+0.215/CI[+0.04~+0.39]）のCI下限がプラス圏入り
- #105（rsi_oversold_bounce×long方向）の翌日として、トレンド次元の交絡解析に自然発展

## 事前合否基準
H1（主）: 上昇中のCI下限≥43%、かつN≥20 → IS全体で達成 [50.1%, 68.8%]
H2（副）: 下降中の勝率 < 上昇中の勝率（10pp以上の差） → 59.8%-43.9%=15.9pp差で達成

## Python スクリプト

```python
import json, math
from datetime import datetime
from collections import Counter

def wilson_ci(k, n, z=1.96):
    if n == 0: return (0,0)
    p = k/n
    denom = 1 + z**2/n
    c = (p + z**2/(2*n))/denom
    h = z*math.sqrt(p*(1-p)/n + z**2/(4*n**2))/denom
    return (max(0,c-h), min(1,c+h))

with open('signals-log.json') as f:
    data = json.load(f)

closed = [d for d in data if d.get('outcome') in ('tp1','tp2','sl','tp1_closed','tp2_closed')]
# Total closed: 4613

def get_trend(d):
    ta = d.get("trend_alignment")
    if isinstance(ta, dict) and ta.get("higher_tf_trend"):
        return ta["higher_tf_trend"]
    return "unknown"

def is_win(d): return d.get('outcome') in ('tp1','tp2')
def get_r(d):
    out = d.get('outcome','')
    if 'tp2' in out: return 2.0
    if 'tp1' in out: return 1.33
    return -1.0
```

## 生出力

```
=== RSI oversold bounce by trend ===
  全体: 239/492=48.6% CI=[44.2%,53.0%] E(R)=+0.132 CI[+0.029,+0.235]
  上昇: 61/102=59.8% CI=[50.1%,68.8%] E(R)=+0.393 CI[+0.170,+0.617]
  下降: 93/212=43.9% CI=[37.4%,50.6%] E(R)=+0.022 CI[-0.134,+0.179]
  中立・もみあい: 84/176=47.7% CI=[40.5%,55.1%] E(R)=+0.112 CI[-0.061,+0.285]

=== 上昇中 by timeframe ===
  1h: 22/46=47.8% CI=[34.1%,61.9%] E(R)=+0.114 CI[-0.229,+0.458]
  4h: 29/43=67.4% CI=[52.5%,79.5%] E(R)=+0.571 CI[+0.237,+0.906]

=== IS vs FWD (上昇中, 登録日=2026-08-11) ===
  IS: 43/65=66.2% CI=[54.0%,76.5%] E(R)=+0.541 CI[+0.269,+0.814]
  FWD: 18/37=48.6% CI=[33.4%,64.1%] E(R)=+0.134 CI[-0.252,+0.519]

=== IS/FWD × timeframe (上昇中) ===
  1h IS: 15/29=51.7% CI=[34.4%,68.6%] E(R)=+0.205
  1h FWD: 7/17=41.2% CI=[21.6%,64.0%] E(R)=-0.041
  4h IS: 19/25=76.0% CI=[56.6%,88.5%] E(R)=+0.771
  4h FWD: 10/18=55.6% CI=[33.7%,75.4%] E(R)=+0.294

=== rsi_oversold×下降 by group ===
  metal×下降: 14/47=29.8% CI=[18.7%,44.0%] E(R)=-0.306
  index×下降: 15/28=53.6% CI=[35.8%,70.5%] E(R)=+0.248

=== Ticker distribution in uptrend ===
{'YM=F': 14, 'ES=F': 9, 'NQ=F': 8, 'USDJPY=X': 7, 'GBPAUD=X': 7, 'AUDJPY=X': 7, 'CL=F': 6, 'GC=F': 6, 'AUDUSD=X': 6, 'GBPJPY=X': 5}
```

## 解釈

1. **トレンド非対称性（15.9pp差）**: 上昇59.8% vs 下降43.9%は事前宣言H2クリア。
   上昇中はCI下限50.1%≥43%でH1もクリア（IS全体）。

2. **4H足の突出**: 上昇×4H=67.4%（E(R)+0.571R）は上昇×1H=47.8%より+19.6pp。
   IS段階では4H×IS=76.0%が特に高い。FWD=55.6%（N=18小）へ減衰。

3. **IS/FWD乖離（重要）**: 上昇IS=66.2% → FWD=48.6%（-17.6pp）。
   FWD N=37小でCIが[33.4%,64.1%]と広く、統計的には継続観察が必要。
   ただし4H×FWD=55.6%はまだプラス域。

4. **下降×メタル（危険域）**: 14/47=29.8%（CI[18.7%,44.0%]）は損益分岐を大幅割れ。
   メタルの下降中RSI逆張りは明確に避けるべき組み合わせ。

5. **指数偏り**: 上昇中102件中YM=F:14+ES=F:9+NQ=F:8=31件(30%)が指数。
   指数上昇中のバイアスが上昇全体の優位性を押し上げている可能性あり。
   ただし指数×下降=53.6%（N=28）は別の研究課題。

## 判定

通過A（IS×全体でCI下限50.1%≥43%・N=102≥20・E(R)CI下限+0.170>0）
IS/FWD乖離に注意：FWD N=37で継続観察中。4H足は両サンプルで比較的頑健。
下降×メタルは探索的回避フラグ（N=47・要前向き確認）。
