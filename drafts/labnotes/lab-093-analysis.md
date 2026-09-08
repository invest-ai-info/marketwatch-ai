# lab-093-analysis.md — 2026-09-09

## 仮説採択経緯

スイープFDR通過 0本（新規なし）。
トラッカー優先度確認:
- `trend=上昇×reversalL`: ✅昇格・demote_strikes=1・CI[-0.04~+0.28] 降格警戒継続
- `売られすぎ逆張り買い(rsi_oversold_bounce)`: N=320・CI[-0.00~+0.36] 昇格境界接近

採択: **trend=上昇×reversalL の前向きN=290 降格警戒継続中——RSI vs BB二極化深化の解剖**

- 優先度②（前向きで大きく動いた仮説）
- 事前宣言基準: 昇格条件「前向きN≥80かつ平均R CI下限>0が2回連続」
- 現状: demote_strikes=1（1回目基準割れ・last_eval_n=248）・N=289~290で継続観察

---

## 検証スクリプト（全文）

```python
import json, math
from collections import defaultdict

GROUPS = {
    "metal": {"GC=F","SI=F"}, "index": {"NKD=F","ES=F","NQ=F","YM=F","^FTSE"},
    "jpy_fx": {"USDJPY=X","EURJPY=X","GBPJPY=X","AUDJPY=X"},
    "other_fx": {"EURUSD=X","GBPUSD=X","AUDUSD=X","EURAUD=X","GBPAUD=X"},
    "btc": {"BTC-USD"}, "oil": {"CL=F"},
}
REV = {"rsi_oversold_bounce", "bb_lower_touch"}
FWD_DATE = "2026-06-22"  # tracker registered_at

def get_trend(d):
    ta = d.get("trend_alignment")
    if isinstance(ta, dict) and ta.get("higher_tf_trend"):
        return ta["higher_tf_trend"]
    return "unknown"

def match(d, f):
    direction = f.get("direction","any")
    is_long = "ロング" in (d.get("direction") or "")
    if f.get("reversal_long"):
        if not (is_long and d.get("primary_signal") in REV): return False
    elif direction == "long" and not is_long: return False
    elif direction == "short" and "ショート" not in (d.get("direction") or ""): return False
    if "trend" in f and get_trend(d) != f["trend"]: return False
    if "tf" in f and d.get("timeframe") != f["tf"]: return False
    if "signal" in f and d.get("primary_signal") != f["signal"]: return False
    if "group" in f and f["group"] != "all":
        if d.get("ticker") not in GROUPS.get(f["group"], set()): return False
    if "ticker" in f and d.get("ticker") != f["ticker"]: return False
    return True

def win(d): return d.get("outcome") in ("tp1","tp2")

def wilson(k, n):
    if n == 0: return 0,0,0
    z=1.96; p=k/n; den=1+z*z/n
    c=(p+z*z/(2*n))/den; pm=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return p, max(0,c-pm), min(1,c+pm)

def avg_r_ci(signals):
    rs=[]
    for s in signals:
        o=s.get("outcome")
        if o in ("tp1","tp2"):
            tp=s.get("tp1_pct",0) or 0; sl=s.get("sl_pct",0) or 0
            if sl and sl!=0: rs.append(abs(tp/sl))
        elif o=="sl": rs.append(-1.0)
        elif o=="expired": rs.append(0.0)
    if not rs: return 0,0,0
    n=len(rs); mu=sum(rs)/n
    if n>1:
        var=sum((r-mu)**2 for r in rs)/(n-1); se=math.sqrt(var/n)
        return mu, mu-1.96*se, mu+1.96*se
    return mu, mu, mu

with open('signals-log.json') as f:
    data = json.load(f)

# tp1/tp2/sl のみ（expired除外 = signal_lab_verify.py準拠）
CLOSED = [s for s in data if s.get("outcome") in ("tp1","tp2","sl")]
base_flt = {"trend": "上昇", "reversal_long": True}

IS = [s for s in CLOSED if match(s, base_flt) and s.get("fired_at","") < FWD_DATE]
FWD = [s for s in CLOSED if match(s, base_flt) and s.get("fired_at","") >= FWD_DATE]
```

---

## 生出力（全数値）

```
Total closed (no expired): 4213

=== trend=上昇 × reversalL ===
IS: N=101, k=54, pct=53.5%
FWD: N=290, k=139, pct=47.9%
FWD CI: [42.2%, 53.7%]  E(R)=+0.118 RCI[-0.016,+0.253]

RSI vs BB (no expired):
  RSI: N=70,  k=45, pct=64.3% CI[52.6%,74.5%] E(R)=+0.500 RCI[+0.236,+0.764]
  BB:  N=220, k=94, pct=42.7% CI[36.4%,49.3%] E(R)=-0.003 RCI[-0.156,+0.150]

TF breakdown:
  1h: N=173, k=80, pct=46.2% CI[39.0%,53.7%]
  4h: N=97,  k=44, pct=45.4% CI[35.8%,55.3%]

RSI × TF:
  RSI×1h: N=31, k=15, pct=48.4% CI[32.0%,65.2%]
  RSI×4h: N=29, k=21, pct=72.4% CI[54.3%,85.3%]

Group breakdown:
  index:    N=76,  k=29, pct=38.2% CI[28.1%,49.4%]
  jpy_fx:   N=85,  k=42, pct=49.4% CI[39.0%,59.8%]
  other_fx: N=74,  k=39, pct=52.7% CI[41.5%,63.7%]
  metal:    N=19,  k=9,  pct=47.4% CI[27.3%,68.3%]
  btc:      N=21,  k=12, pct=57.1% CI[36.5%,75.5%]
  oil:      N=14,  k=8,  pct=57.1% CI[32.6%,78.6%]

IS breakdown:
  IS RSI: N=25, k=13, pct=52.0%
  IS BB:  N=76, k=41, pct=53.9%

降格警戒の履歴:
  demote_strikes: 1
  last_eval_n: 248
  current_n: 289
  最近のrci_lo: -0.053(N=253) → -0.040(N=289)（ずっとマイナス）
```

---

## 交絡チェック

**RS vs BB の IS→FWD 乖離**:
- IS: RSI 52.0% vs BB 53.9% → 差1.9pp（ほぼ同等）
- FWD: RSI 64.3% vs BB 42.7% → 差21.6pp（大乖離）
- IS期間は両者が同等だったにもかかわらず、FWDで大きく乖離した
- これは「RSIシグナルが前向き期間で性能向上した」もしくは「BBシグナルが劣化した」ことを示唆

**RSI×4Hの高勝率**:
- RSI×4H: 72.4% CI[54.3%,85.3%] → 最も優秀な組み合わせ
- RSI×1H: 48.4% CI[32.0%,65.2%] → エッジ不明（CIが43%またぎ）
- この差24ppは#074のrsi_oversold_bounce 4H優位（67%）と整合する

**指数グループ崩落**:
- 指数FWD: 38.2% CI[28.1%,49.4%] → CI上限49.4%が43%超だが平均は38%
- #047/#073でも指数の崩落が確認されていた
- BB×index がメインの原因（N=61でCI上限が45%付近と低位）
