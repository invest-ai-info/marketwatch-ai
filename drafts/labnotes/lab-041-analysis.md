# signal-lab #041 — 分析ノート

**基準日**: 2026-07-16 (JST)  
**仮説**: trend=下降×reversalL（下降トレンド中の逆張り買い）gate の前向き急上昇解析  
**優先度**: ②前向きで大きく動いた仮説（tracker FWD 49/75=65% R+0.524 CI[+0.15~+0.90]）

---

## 採択理由

signal_lab_tracker.py update (2026-07-16) 出力:
```
trend=下降×reversalL  gate  2026-06-25  49/75  65%  +0.524  [+0.15~+0.90]  🟡蓄積中  (全期間R -0.01)
```

gate は IS 期間（2026-06-25 より前）の勝率 34.1% を根拠に「下降トレンド中の逆張り買いは回避」として
設立された。ところが前向きデータでは 65%（R+0.524 CI[+0.15~+0.90]）まで急上昇し、
N=75 で次チェックポイント N=80 まであと 5 件。今日の題材として最適。

---

## Pythonスクリプト全文

```python
"""
#041: trend=下降×reversalL 前向き急上昇の解析
verify.py の定義に完全準拠
"""
import json, math
from datetime import datetime, timezone

GROUPS = {
    "metal":    {"GC=F", "SI=F"},
    "index":    {"NKD=F", "ES=F", "NQ=F", "YM=F", "^FTSE"},
    "jpy_fx":   {"USDJPY=X", "EURJPY=X", "GBPJPY=X", "AUDJPY=X"},
    "other_fx": {"EURUSD=X", "GBPUSD=X", "AUDUSD=X", "EURAUD=X", "GBPAUD=X"},
    "btc":      {"BTC-USD"},
    "oil":      {"CL=F"},
}
REV = {"rsi_oversold_bounce", "bb_lower_touch"}

def closed(d): return d.get("outcome") in ("tp1","tp2","sl")
def win(d): return d.get("outcome") in ("tp1","tp2")

def get_trend(d):
    ta = d.get("trend_alignment")
    if isinstance(ta, dict) and ta.get("higher_tf_trend"):
        return ta["higher_tf_trend"]
    return "unknown"

def get_group(d):
    t = d.get("ticker","")
    for g, ts in GROUPS.items():
        if t in ts: return g
    return "other"

def is_revL(d):
    return "ロング" in (d.get("direction") or "") and d.get("primary_signal") in REV

def wilson(k, n, z=1.96):
    if n == 0: return (0.0, 0.0)
    p = k/n
    den = 1 + z*z/n
    c = (p + z*z/(2*n))/den
    pm = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))/den
    return (max(0,c-pm)*100, min(1,c+pm)*100)

def mean_r(sigs):
    rs = []
    for s in sigs:
        o = s.get("outcome","")
        if o=="tp1": rs.append(4/3)
        elif o=="tp2": rs.append(2.0)
        elif o=="sl": rs.append(-1.0)
    if not rs: return 0.0, (0.0, 0.0)
    r = sum(rs)/len(rs)
    if len(rs) < 2: return r, (r, r)
    se = math.sqrt(sum((x-r)**2 for x in rs)/(len(rs)-1))/math.sqrt(len(rs))
    return r, (r-1.96*se, r+1.96*se)

def get_ts(s, use_resolved=False):
    ts = (s.get("outcome_resolved_at") if use_resolved else None) or s.get("fired_at") or ""
    try: return datetime.fromisoformat(ts.replace("Z","+00:00"))
    except: return None

with open("/home/user/marketwatch-ai/signals-log.json") as f:
    data = json.load(f)
signals = data if isinstance(data, list) else data.get("signals", [])
cls = [s for s in signals if closed(s)]

reg_date = datetime(2026, 6, 25, tzinfo=timezone.utc)
down_revL_all = [s for s in cls if is_revL(s) and get_trend(s)=="下降"]
down_revL_IS  = [s for s in down_revL_all if (get_ts(s) or reg_date) < reg_date]
down_revL_FWD = [s for s in down_revL_all if (get_ts(s) or reg_date) >= reg_date]
```

---

## 生出力

```
Closed signals (tp1/tp2/sl): 1744

=== IS (全期間): trend=下降×reversalL ===
  k=104 n=245 勝率=42.4% CI=[36.4%,48.7%]
  E(R)=-0.010 RCI=[-0.154,0.135]
  IS (before 2026-06-25): k=62 n=182 勝率=34.1% CI=[27.6%,41.2%] E(R)=-0.205
  FWD (since 2026-06-25): k=42 n=63 勝率=66.7% CI=[54.4%,77.1%] E(R)=0.556 RCI=[0.282,0.829]

=== 3トレンド×reversalL 比較 (全期間) ===
  上昇×revL: k=94  n=171 勝率=55.0% CI=[47.5%,62.2%] E(R)=+0.283
  下降×revL: k=104 n=245 勝率=42.4% CI=[36.4%,48.7%] E(R)=-0.010
  中立×revL: k=84  n=211 勝率=39.8% CI=[33.4%,46.5%] E(R)=-0.071

=== 3トレンド×reversalL 比較 (FWD since 2026-06-25) ===
  上昇×revL FWD: k=35 n=62 勝率=56.5% CI=[44.1%,68.1%] E(R)=+0.317 RCI=[+0.027,+0.608]
  下降×revL FWD: k=42 n=63 勝率=66.7% CI=[54.4%,77.1%] E(R)=+0.556 RCI=[+0.282,+0.829]
  中立×revL FWD: k=18 n=40 勝率=45.0% CI=[30.7%,60.2%] E(R)=+0.050 RCI=[-0.314,+0.414]

=== グループ別: trend=下降×reversalL (全期間) ===
  index: k=12 n=17 勝率=70.6% CI=[46.9%,86.7%] E(R)=+0.647
  metal: k=22 n=87 勝率=25.3% CI=[17.3%,35.3%] E(R)=-0.410
  btc:   k=14 n=33 勝率=42.4% CI=[27.2%,59.2%] E(R)=-0.010
  jpy_fx: k=10 n=19 勝率=52.6% CI=[31.7%,72.7%] E(R)=+0.228
  other_fx: k=33 n=67 勝率=49.3% CI=[37.7%,60.9%] E(R)=+0.149
  oil: k=13 n=22 勝率=59.1% CI=[38.7%,76.7%] E(R)=+0.379

=== グループ別: trend=下降×reversalL (FWD since 2026-06-25) ===
  index FWD:    k=7  n=10 勝率=70.0% CI=[39.7%,89.2%]
  metal FWD:    k=9  n=13 勝率=69.2% CI=[42.4%,87.3%] E(R)=+0.615 RCI=[+0.006,+1.225]
  btc FWD:      k=5  n=11 勝率=45.5% CI=[21.3%,72.0%]
  jpy_fx FWD:   k=5  n=5  勝率=100%  CI=[56.6%,100%]
  other_fx FWD: k=12 n=18 勝率=66.7% CI=[43.7%,83.7%] E(R)=+0.556 RCI=[+0.033,+1.078]
  oil FWD:      k=4  n=6  勝率=66.7% CI=[30.0%,90.3%]

=== シグナル別: trend=下降×reversalL (全期間) ===
  bb_lower_touch:     k=59 n=136 勝率=43.4% CI=[35.3%,51.8%] E(R)=+0.012
  rsi_oversold_bounce: k=45 n=109 勝率=41.3% CI=[32.5%,50.7%] E(R)=-0.037

=== シグナル別: trend=下降×reversalL (FWD) ===
  bb_lower_touch FWD:     k=30 n=47 勝率=63.8% CI=[49.5%,76.0%] E(R)=+0.489 RCI=[+0.165,+0.813]
  rsi_oversold_bounce FWD: k=12 n=16 勝率=75.0% CI=[50.5%,89.8%] E(R)=+0.750 RCI=[+0.239,+1.261]

=== TF別: trend=下降×reversalL (全期間) ===
  tf=1h: k=54 n=142 勝率=38.0% CI=[30.5%,46.2%] E(R)=-0.113
  tf=4h: k=48 n=100 勝率=48.0% CI=[38.5%,57.7%] E(R)=+0.120

=== TF別: trend=下降×reversalL (FWD) ===
  tf=1h FWD: k=16 n=30 勝率=53.3% CI=[36.1%,69.8%] E(R)=+0.244 RCI=[-0.179,+0.668]
  tf=4h FWD: k=25 n=32 勝率=78.1% CI=[61.2%,89.0%] E(R)=+0.823 RCI=[+0.483,+1.162]

=== 全reversalL (全期間) ===
  全revL: k=283 n=631 勝率=44.8% CI=[41.0%,48.7%] E(R)=+0.046

=== 全reversalL (FWD since 2026-06-25) ===
  全revL FWD: k=95 n=165 勝率=57.6% CI=[49.9%,64.9%] E(R)=+0.343 RCI=[+0.167,+0.520]

=== blocked別: trend=下降×reversalL (全期間) ===
  blocked=True:  k=3  n=9   勝率=33.3%
  blocked=False: k=85 n=198 勝率=42.9% CI=[36.2%,49.9%]
  sr_runway無し: N=38
```

---

## 主要発見まとめ

| 観点 | IS（2026-06-25前） | FWD（tracker, 2026-06-25〜） |
|---|---|---|
| 下降×revL 全体 | 62/182=**34.1%** E(R)=-0.205 | 49/75=**65%** E(R)=+0.524 RCI[+0.15,+0.90] |
| metal×下降×revL | 25.3% (IS全期間22/87) | 9/13=69.2% E(R)=+0.615 |
| tf=4h×下降×revL | 48.0% (全期間48/100) | 25/32=**78.1%** E(R)=+0.823 RCI[+0.483,+1.162] |
| rsi_oversold×下降×revL | 41.3% (全期間45/109) | 12/16=**75.0%** E(R)=+0.750 |

- **主因**: metal の劇的レジーム転換（IS 25.3% → FWD 69.2%）= #030/#032/#040 と同根
- **次チェックポイント**: tracker N=75 → N=80 まであと 5 件（今日の時点で昇格/反証は判定前）
- **全 revL FWD**: 95/165=57.6% E(R)=+0.343 → 全 reversalL ⛔反証（#032）の流れと整合

---

*作成: 2026-07-16 JST*
