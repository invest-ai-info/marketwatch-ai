# Lab-049 分析メモ — 上昇トレンド×逆張り買い(reversalL) シグナル二極化

**基準日**: 2026-07-24  
**担当**: AIシグナル研究日誌 日次研究会  
**テーマ**: BB下限タッチ vs RSI売られすぎ — 上昇トレンド中の逆張り買いはシグナルで明暗が分かれるか

---

## 採択理由

- tracker state（2026-07-24）で「trend=上昇×reversalL」が ✅昇格済（edge仮説）
- 昇格した仮説の内部構成（BB vs RSI）の格差を解析することで、昇格エッジの「どの部分が強いか」を特定
- 前向きトラッカーに「売られすぎ逆張り買い(rsi_oversold_bounce・全足)」が蓄積中で補完関係にある

---

## 事前宣言基準

- H1: RSI(rsi_oversold_bounce)×上昇×revL: **CI下限 > 43%** かつ N ≥ 20
- H2: BB(bb_lower_touch)×上昇×revL: **CI下限 < 43%**（BBは劣る＝二極化の証拠）

---

## 検証スクリプト

```python
import json, math
from collections import Counter

with open('signals-log.json') as f:
    logs = json.load(f)

GROUPS = {
    "metal": {"GC=F","SI=F"}, "index": {"NKD=F","ES=F","NQ=F","YM=F","^FTSE"},
    "jpy_fx": {"USDJPY=X","EURJPY=X","GBPJPY=X","AUDJPY=X"},
    "other_fx": {"EURUSD=X","GBPUSD=X","AUDUSD=X","EURAUD=X","GBPAUD=X"},
    "btc": {"BTC-USD"}, "oil": {"CL=F"},
}
REV = {"rsi_oversold_bounce", "bb_lower_touch"}

def get_group(d):
    t = d.get("ticker","")
    for g, tickers in GROUPS.items():
        if t in tickers: return g
    return "unknown"

def closed(d): return d.get("outcome") in ("tp1","tp2","sl")
def win(d): return d.get("outcome") in ("tp1","tp2")
def is_long(d): return "ロング" in (d.get("direction") or "")
def is_revL(d): return is_long(d) and d.get("primary_signal") in REV

def get_trend(d):
    ta = d.get("trend_alignment")
    if isinstance(ta, dict): return ta.get("higher_tf_trend","unknown")
    return "unknown"

def wilson(k, n, z=1.95996):
    if n == 0: return (0.0, 0.0)
    p = k/n
    c = (p + z*z/(2*n)) / (1 + z*z/n)
    m = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / (1 + z*z/n)
    return (round((c-m)*100,1), round((c+m)*100,1))

all_closed = [d for d in logs if closed(d)]
rows_revL = [d for d in all_closed if is_revL(d)]
rows_up_revL = [d for d in rows_revL if get_trend(d)=="上昇"]
rows_bb = [d for d in rows_up_revL if d.get("primary_signal")=="bb_lower_touch"]
rows_rsi = [d for d in rows_up_revL if d.get("primary_signal")=="rsi_oversold_bounce"]
```

---

## 生出力（2026-07-24 実行）

```
Total closed records: 2068

All revL (before trend filter): 726

  上昇×revL 全体                       107/209  = 51.2%  CI[44.5~57.9]
  BB(bb_lower_touch)×上昇×revL          77/161  = 47.8%  CI[40.3~55.5]
  RSI(rsi_oversold_bounce)×上昇×revL    30/48   = 62.5%  CI[48.4~74.8]

=== グループ別（上昇×revL）===
  index×上昇×revL                       45/81   = 55.6%  CI[44.7~65.9]
  jpy_fx×上昇×revL                      29/51   = 56.9%  CI[43.3~69.5]
  other_fx×上昇×revL                    21/53   = 39.6%  CI[27.6~53.1]
  metal×上昇×revL                        3/7    = 42.9%  CI[15.8~75.0]
  btc×上昇×revL                          2/8    = 25.0%  CI[ 7.1~59.1]
  oil×上昇×revL                          7/9    = 77.8%  CI[45.3~93.7]

=== BB×グループ（上昇）===
  BB×index×上昇×revL                    31/59   = 52.5%  CI[40.0~64.7]
  BB×jpy_fx×上昇×revL                   25/46   = 54.3%  CI[40.2~67.8]
  BB×other_fx×上昇×revL                 15/44   = 34.1%  CI[21.9~48.9]

=== RSI×グループ（上昇）===
  RSI×index×上昇×revL                   14/22   = 63.6%  CI[43.0~80.3]
  RSI×jpy_fx×上昇×revL                   4/5    = 80.0%  CI[37.6~96.4]
  RSI×other_fx×上昇×revL                 6/9    = 66.7%  CI[35.4~87.9]

=== トレンド別比較 ===
  下降×revL                            121/279  = 43.4%  CI[37.7~49.2]
  中立・もみあい×revL                     91/234  = 38.9%  CI[32.9~45.3]
  全revL（トレンド問わず）               320/726  = 44.1%  CI[40.5~47.7]
```

---

## 判定サマリ

| 仮説 | 基準 | 結果 | 判定 |
|---|---|---|---|
| H1: RSI×上昇×revL | CI下限 > 43% かつ N≥20 | 62.5% CI[48.4~74.8] N=48 | **通過** |
| H2: BB×上昇×revL | CI下限 < 43% | 47.8% CI[40.3~55.5] N=161 | **部分通過（CI下限40.3% < 43%）** |

主要発見:
- RSI売られすぎは上昇トレンド文脈で明確なエッジを示す（CI下限48.4%）
- BB下限タッチは上昇トレンドでもCI下限が43%を下回る（40.3%）
- BB×other_fx（EURなど）が特に弱い（34.1% CI[21.9~48.9]）
- 上昇トレンドでのrevL（51.2%）は下降（43.4%）・中立（38.9%）を上回る
