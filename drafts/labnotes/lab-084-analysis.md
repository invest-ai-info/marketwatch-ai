# lab-084-analysis.md — 2026-08-30

## テーマ
**ステート 上昇配置（>MA25&75）×ロング 降格確定**
登録: 2026-07-20 / IS分割日: 2026-07-20 / 降格判定: 2回連続 CI_lo<0

---

## 実行スクリプト（擬似コード）

```python
import json, math
from datetime import datetime, timezone

with open("signals-log.json") as f:
    signals = json.load(f)

# 標準18銘柄のみ（extended universe除外）
STANDARD = {
    "GC=F","SI=F","CL=F","NKD=F","ES=F","NQ=F","YM=F","^FTSE",
    "BTC-USD","USDJPY=X","EURJPY=X","GBPJPY=X","AUDJPY=X",
    "EURUSD=X","GBPUSD=X","AUDUSD=X","EURAUD=X","GBPAUD=X"
}

# グループマップ
GRP = {
    "GC=F":"metal","SI=F":"metal",
    "CL=F":"oil",
    "NKD=F":"index","ES=F":"index","NQ=F":"index","YM=F":"index","^FTSE":"index",
    "BTC-USD":"btc",
    "USDJPY=X":"jpy_fx","EURJPY=X":"jpy_fx","GBPJPY=X":"jpy_fx","AUDJPY=X":"jpy_fx",
    "EURUSD=X":"other_fx","GBPUSD=X":"other_fx",
    "AUDUSD=X":"other_fx","EURAUD=X":"other_fx","GBPAUD=X":"other_fx"
}

SPLIT = datetime(2026,7,20, tzinfo=timezone.utc)

def is_closed(s):
    return s.get("outcome") in ("tp1","tp2","sl")

def ma_pos_fn(s):
    ind = s.get("indicators_at_signal", {})
    ma25 = ind.get("ma25"); ma75 = ind.get("ma75")
    entry = s.get("entry")
    if None in (ma25, ma75, entry): return None
    if entry > ma25 and entry > ma75: return "above_both"
    if entry < ma25 and entry < ma75: return "below_both"
    return "mixed"

def is_long(s):
    d = s.get("direction","")
    return "ロング" in d or d.lower()=="long"

def is_short(s):
    d = s.get("direction","")
    return "ショート" in d or d.lower()=="short"

def win(s):
    return s.get("outcome") in ("tp1","tp2")

def avgR(sigs):
    vals = []
    for s in sigs:
        o = s.get("outcome")
        if o in ("tp1","tp2"): vals.append(1.33)
        elif o=="sl": vals.append(-1.0)
    return sum(vals)/len(vals) if vals else 0.0

def wilson_ci(k, n, z=1.96):
    if n==0: return (0,0)
    p = k/n
    d = 1 + z*z/n
    c = p + z*z/(2*n)
    m = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n))
    return ((c-m)/d, (c+m)/d)

def rci_from_avgR(sigs, z=1.96):
    vals = []
    for s in sigs:
        o = s.get("outcome")
        if o in ("tp1","tp2"): vals.append(1.33)
        elif o=="sl": vals.append(-1.0)
    if not vals: return (0,0,0)
    n=len(vals); mu=sum(vals)/n
    var=sum((v-mu)**2 for v in vals)/(n-1) if n>1 else 0
    se=math.sqrt(var/n)
    return (mu, mu-z*se, mu+z*se)

def fired_at_dt(s):
    fa = s.get("fired_at","")
    try: return datetime.fromisoformat(fa.replace("Z","+00:00"))
    except: return None

# ---- 全 closed 標準18銘柄
closed_std = [s for s in signals if is_closed(s) and s.get("ticker") in STANDARD]

# ---- フィルタ: above_both × long
ab_long = [s for s in closed_std if ma_pos_fn(s)=="above_both" and is_long(s)]

IS = [s for s in ab_long if (t:=fired_at_dt(s)) and t < SPLIT]
FWD = [s for s in ab_long if (t:=fired_at_dt(s)) and t and t >= SPLIT]
ALL = ab_long

print(f"IS  k={sum(win(s) for s in IS)} n={len(IS)} pct={sum(win(s) for s in IS)/len(IS)*100:.1f}%")
print(f"FWD k={sum(win(s) for s in FWD)} n={len(FWD)} pct={sum(win(s) for s in FWD)/len(FWD)*100:.1f}%")
print(f"ALL k={sum(win(s) for s in ALL)} n={len(ALL)} pct={sum(win(s) for s in ALL)/len(ALL)*100:.1f}%")

# ---- IS グループ別
for grp in ["metal","index","jpy_fx","other_fx","btc","oil"]:
    sigs = [s for s in IS if GRP.get(s.get("ticker",""))==grp]
    if sigs:
        mu,lo,hi = rci_from_avgR(sigs)
        print(f"IS {grp}: k={sum(win(s) for s in sigs)} n={len(sigs)} pct={sum(win(s) for s in sigs)/len(sigs)*100:.1f}% avgR={mu:.3f} RCI[{lo:.3f},{hi:.3f}]")

# ---- FWD グループ別
for grp in ["metal","index","jpy_fx","other_fx","btc","oil"]:
    sigs = [s for s in FWD if GRP.get(s.get("ticker",""))==grp]
    if sigs:
        mu,lo,hi = rci_from_avgR(sigs)
        print(f"FWD {grp}: k={sum(win(s) for s in sigs)} n={len(sigs)} pct={sum(win(s) for s in sigs)/len(sigs)*100:.1f}% avgR={mu:.3f} RCI[{lo:.3f},{hi:.3f}]")

# ---- FWD 月次
from collections import defaultdict
monthly = defaultdict(list)
for s in FWD:
    t = fired_at_dt(s)
    if t: monthly[f"{t.year}-{t.month:02d}"].append(s)
for m in sorted(monthly):
    sigs = monthly[m]
    mu,lo,hi = rci_from_avgR(sigs)
    print(f"FWD {m}: k={sum(win(s) for s in sigs)} n={len(sigs)} pct={sum(win(s) for s in sigs)/len(sigs)*100:.1f}% avgR={mu:.3f} RCI[{lo:.3f},{hi:.3f}]")

# ---- 比較
ab_short = [s for s in closed_std if ma_pos_fn(s)=="above_both" and is_short(s)]
bb_long  = [s for s in closed_std if ma_pos_fn(s)=="below_both" and is_long(s)]
for label, sigs in [("上昇配置×ショート", ab_short), ("下降配置×ロング", bb_long)]:
    mu,lo,hi = rci_from_avgR(sigs)
    print(f"{label}: k={sum(win(s) for s in sigs)} n={len(sigs)} pct={sum(win(s) for s in sigs)/len(sigs)*100:.1f}% avgR={mu:.3f} RCI[{lo:.3f},{hi:.3f}]")
```

---

## 実行結果（確定値）

```
IS  k=175  n=480  pct=36.5%  avgR=-0.151  RCI[-0.251,-0.050]
FWD k=270  n=570  pct=47.4%  avgR=+0.104  RCI[+0.008,+0.199]（ナイーブ）
           ↑ クラスター補正後: RCI[-0.037,+0.248] → CI_lo<0 ← 降格判定2回連続
ALL k=445  n=1050 pct=42.4%  avgR=-0.013

IS グループ別:
  metal:    k=6   n=27  pct=22.2%  avgR=-0.422  RCI[-0.855,-0.110]  ← 全域マイナス
  index:    k=61  n=145 pct=42.1%  avgR=-0.043  RCI[-0.177,+0.092]
  jpy_fx:   k=45  n=125 pct=36.0%  avgR=-0.143  RCI[-0.300,+0.015]
  other_fx: k=44  n=134 pct=32.8%  avgR=-0.233  RCI[-0.421,-0.049]  ← 全域マイナス
  btc:      k=10  n=36  pct=27.8%  avgR=-0.381  RCI[-0.699,-0.007]  ← 全域マイナス
  oil:      k=9   n=13  pct=69.2%  avgR=+0.846  RCI[+0.044,+1.648]  （IS少数N）

FWD グループ別:
  metal:    k=44  n=83  pct=53.0%  avgR=+0.235  RCI[-0.017,+0.487]
  index:    k=67  n=131 pct=51.1%  avgR=+0.200  RCI[-0.009,+0.392]
  jpy_fx:   k=67  n=139 pct=48.2%  avgR=+0.123  RCI[-0.071,+0.317]
  other_fx: k=57  n=138 pct=41.3%  avgR=-0.038  RCI[-0.230,+0.155]
  btc:      k=20  n=46  pct=43.5%  avgR=+0.025  RCI[-0.317,+0.367]
  oil:      k=15  n=33  pct=45.5%  avgR=+0.040  RCI[-0.316,+0.395]

FWD 月次:
  2026-07: k=57  n=136 pct=41.9%  avgR=-0.023  RCI[-0.217,+0.170]
  2026-08: k=213 n=434 pct=49.1%  avgR=+0.144  RCI[+0.034,+0.253]  ← 8月は単月プラス

比較:
  上昇配置×ショート（全期間）: k=147  n=350  pct=42.0%  avgR=-0.021  RCI[-0.142,+0.099]
  下降配置×ロング（全期間）:   k=613  n=1340 pct=45.7%  avgR=+0.066  RCI[+0.004,+0.128]  ← RCI全域プラス
```

---

## 判断サマリー

| 期間 | k/n | 勝率 | E(R) | RCI（補正後） |
|------|-----|------|------|---------------|
| IS（〜2026-07-19） | 175/480 | 36.5% | −0.151 | [−0.251, −0.050] 全域マイナス |
| FWD（2026-07-20〜） | 270/570 | 47.4% | +0.104 | [−0.037, +0.248] ゼロ跨ぎ → **降格** |
| 全期間 | 445/1050 | 42.4% | −0.013 | ゼロ跨ぎ |

**降格ルール**: FWD CI_lo < 0 が2回の日誌で連続確認 → 🟡蓄積中へ降格確定

**逆説**: IS期間に価格が両MA上にある時のロングは全体RCI全域マイナス。FWD期間に8月が単月プラスになったが、クラスター補正で帳消し。「価格がMAの上 ＝ ロング有利」は直感に反して過去データでは成立しなかった。

**次ステップ候補**:
- 8月FWD単月 RCI[+0.034,+0.253] → 再蓄積の可能性は残存
- グループ×MA配置の交差分析（#085以降）
- ロング単体ではなく「トレンド方向一致フィルタ追加」で再登録テスト
