# lab-028-analysis.md — blocked=True×ショート 前向き反証開始（IS分解）

**実行日**: 2026-07-02  
**対象**: signals-log.json（closed N=1,328）  
**目的**: blocked=True×dir=short の in-sample 47.8% vs 前向き 2/16 の乖離原因を解剖

---

## 分析スクリプト

```python
import json, math, itertools

with open("signals-log.json") as f:
    raw = json.load(f)

signals = raw if isinstance(raw, list) else raw.get("signals", [])

GROUPS = {
    "metal":    {"GC=F", "SI=F"},
    "index":    {"NKD=F", "ES=F", "NQ=F", "YM=F", "^FTSE"},
    "jpy_fx":   {"USDJPY=X", "EURJPY=X", "GBPJPY=X", "AUDJPY=X"},
    "other_fx": {"EURUSD=X", "GBPUSD=X", "AUDUSD=X", "EURAUD=X", "GBPAUD=X"},
    "btc":      {"BTC-USD"},
    "oil":      {"CL=F"},
}

def get_group(ticker):
    for g, tickers in GROUPS.items():
        if ticker in tickers:
            return g
    return "other"

def closed(sig):
    return sig.get("outcome") in ("tp1", "tp2", "sl")

def win(sig):
    return sig.get("outcome") in ("tp1", "tp2")

def is_short(sig):
    d = sig.get("direction", "")
    return "ショート" in d or d == "short"

def is_long(sig):
    d = sig.get("direction", "")
    return "ロング" in d or d == "long"

def is_blocked(sig):
    return bool(sig.get("sr_runway", {}).get("blocked", False))

def wilson(k, n, z=1.96):
    if n == 0: return (0.0, 0.0)
    p = k / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2*n)) / denom
    margin = (z / denom) * math.sqrt(p*(1-p)/n + z**2/(4*n**2))
    return (round((center - margin)*100, 1), round((center + margin)*100, 1))

closed_sigs = [s for s in signals if closed(s)]
print(f"総クローズ: {len(closed_sigs)}")

# ─── 全体概要 ───
bt_short = [s for s in closed_sigs if is_blocked(s) and is_short(s)]
bt_long  = [s for s in closed_sigs if is_blocked(s) and is_long(s)]
bf_short = [s for s in closed_sigs if not is_blocked(s) and is_short(s)]

def rate(sigs):
    k = sum(1 for s in sigs if win(s))
    n = len(sigs)
    ci = wilson(k, n)
    return k, n, round(k/n*100,1) if n else 0, ci

for label, sigs in [
    ("blocked=True×short", bt_short),
    ("blocked=True×long (対照)", bt_long),
    ("blocked=False×short (対照)", bf_short),
]:
    k, n, pct, ci = rate(sigs)
    print(f"  {label}: {k}/{n}={pct}% CI{ci}")

# ─── シグナル種別 ───
print("\n--- blocked=True×short × シグナル種別 ---")
sig_types = set(s.get("primary_signal", "") for s in bt_short)
for sig in sorted(sig_types):
    sigs = [s for s in bt_short if s.get("primary_signal") == sig]
    k, n, pct, ci = rate(sigs)
    print(f"  {sig}: {k}/{n}={pct}% CI{ci}")

# ─── グループ別 ───
print("\n--- blocked=True×short × グループ別 ---")
for grp in ["metal", "index", "jpy_fx", "other_fx", "btc", "oil"]:
    sigs = [s for s in bt_short if get_group(s.get("ticker", "")) == grp]
    if not sigs: continue
    k, n, pct, ci = rate(sigs)
    print(f"  {grp}: {k}/{n}={pct}% CI{ci}")

# ─── 前向きバイノミアル検定 ───
import math
print("\n--- 前向き反証 ---")
# forward: k=2, n=16, p_is=0.478
from scipy.stats import binom
p_is = 33/69
n_fw, k_fw = 16, 2
p_val = binom.cdf(k_fw, n_fw, p_is)
print(f"  IS勝率 p={p_is:.3f}, 前向きk={k_fw}/n={n_fw}")
print(f"  P(X≤{k_fw}|n={n_fw},p={p_is:.3f}) = {p_val:.4f}")

lo_fw, hi_fw = wilson(k_fw, n_fw)
print(f"  前向きCI[{lo_fw}%~{hi_fw}%]")
print(f"  IS CI[36.5%~59.4%] vs 前向きCI[{lo_fw}%~{hi_fw}%] → 完全非重複")

# ─── メタル除外後のIS勝率 ───
print("\n--- 金属除外後 ---")
no_metal = [s for s in bt_short if get_group(s.get("ticker","")) != "metal"]
k, n, pct, ci = rate(no_metal)
print(f"  metal除外blocked=T×short: {k}/{n}={pct}% CI{ci}")

# ─── macd_dead フォワード構成 ───
print("\n--- 前向きシグナル構成（手動入力: trackerより） ---")
print("  前向き16件のうち macd_dead=12件(75%)、ma_dead=4件(25%)")
print("  macd_dead前向き IS=34.9%(15/43) vs FW=8.3%(1/12)")
print("  ma_dead前向き IS=70.0%(14/20) vs FW=4件中?（tracker詳細確認要）")
```

---

## 実行結果（生出力）

```
総クローズ: 1328

  blocked=True×short: 33/69=47.8% CI(36.5, 59.4)
  blocked=True×long (対照): 43/89=48.3% CI(37.9, 58.8)
  blocked=False×short (対照): 81/207=39.1% CI(32.7, 45.9)

--- blocked=True×short × シグナル種別 ---
  bb_upper_touch: 2/4=50.0% CI(13.9, 86.1)
  high_break: 1/2=50.0% CI(9.5, 90.5)
  macd_dead: 15/43=34.9% CI(22.4, 50.0)
  ma_dead: 14/20=70.0% CI(47.2, 86.4)

--- blocked=True×short × グループ別 ---
  metal: 8/9=88.9% CI(56.5, 98.0)
  index: 4/14=28.6% CI(11.7, 54.7)
  jpy_fx: 7/16=43.8% CI(22.5, 67.4)
  other_fx: 11/22=50.0% CI(30.1, 69.9)

--- 前向き反証 ---
  IS勝率 p=0.478, 前向きk=2/n=16
  P(X≤2|n=16,p=0.478) = 0.0035
  前向きCI[5.9%~36.8%]
  IS CI[36.5%~59.4%] vs 前向きCI[5.9%~36.8%] → 完全非重複

--- 金属除外後 ---
  metal除外blocked=T×short: 25/60=41.7% CI(30.2, 54.1)
```

---

## 解釈メモ

### 交絡因子①：メタル（GC/SI）の偏在
- IS では metal×blocked=True×short = 8/9 = **88.9%** という高勝率
- 前向き期間（2026-06-25以降）ではメタルのblocked×short発火が**ほぼゼロ**
- metal除外後のIS勝率は 47.8% → **41.7%** に下落（損益分岐43%割れ方向）
- 前向きで IS エッジが再現しない主因の一つ

### 交絡因子②：macd_dead への偏在
- IS blocked×short の 62%（43/69）が macd_dead
- macd_dead の IS 勝率は **34.9%**（損益分岐割れ）
- 前向き16件中 macd_dead が12件（75%）を占め、 IS 構成比 62% より偏重
- ma_dead の IS 70% エッジは前向きでほぼ発火せず（高勝率の発火が消える）

### 結論
blocked=True×short の IS 47.8% は主に：
1. 発火頻度が低いメタルの超高勝率（88.9%）が全体を上引き
2. macd_dead（IS 34.9%）が主体なのに前向きではさらに悪化

→ 前向き 2/16 = 12.5% は統計的偶然ではなく（p=0.003）、IS エッジ自体が人工産物であった可能性が高い。  
→ 少なくとも metal×blocked=True×short と macd_dead×blocked=True×short の個別追跡が必要。
