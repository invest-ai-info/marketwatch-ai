# Signal Lab #063 — 分析ノート
## テーマ: rsi_oversold_bounce 全足統合 IS vs FWD 解析
## 基準日: 2026-08-07（トラッカー登録日 2026-06-16）

---

## スクリプト

```python
#!/usr/bin/env python3
"""
signal-lab #063: rsi_oversold_bounce 全足統合 前向き解析
基準日: 2026-08-07
仮説: IS 39.1%（損益分岐割れ）→ FWD で改善するか。グループ・トレンド・TF格差解析。
"""
import json, math
from collections import defaultdict

with open('signals-log.json') as f:
    signals = json.load(f)

TICKERS = {
    'GC=F':'metal','SI=F':'metal','CL=F':'oil',
    'NKD=F':'index','ES=F':'index','NQ=F':'index','YM=F':'index','^FTSE':'index',
    'BTC-USD':'btc',
    'USDJPY':'jpy_fx','USDJPY=X':'jpy_fx','EURJPY':'jpy_fx','EURJPY=X':'jpy_fx',
    'GBPJPY':'jpy_fx','GBPJPY=X':'jpy_fx','AUDJPY':'jpy_fx','AUDJPY=X':'jpy_fx',
    'EURUSD':'other_fx','EURUSD=X':'other_fx','GBPUSD':'other_fx','GBPUSD=X':'other_fx',
    'AUDUSD':'other_fx','AUDUSD=X':'other_fx','EURAUD':'other_fx','EURAUD=X':'other_fx',
    'GBPAUD':'other_fx','GBPAUD=X':'other_fx',
}

def get_group(s): return TICKERS.get(s.get('ticker',''), 'unknown')
def get_trend(s):
    ta = s.get('trend_alignment')
    if isinstance(ta, dict) and ta.get('higher_tf_trend'):
        return ta['higher_tf_trend']
    return 'unknown'
def is_closed(s): return s.get('outcome') in ['tp1','sl']
def win(s): return s.get('outcome') == 'tp1'

def wilson_ci(k, n, z=1.96):
    if n == 0: return (0.0, 0.0)
    p = k/n
    denom = 1 + z**2/n
    center = (p + z**2/(2*n)) / denom
    spread = z * math.sqrt(p*(1-p)/n + z**2/(4*n**2)) / denom
    return (max(0.0, center-spread), min(1.0, center+spread))

def r_of(s):
    o = s.get('outcome')
    if o == 'tp1': return 1.333
    if o == 'sl': return -1.0
    return None

def cluster_mean_r(sigs):
    """Cluster-corrected E(R) CI — same as signal_lab_tracker.py"""
    groups = defaultdict(list)
    for s in sigs:
        r = r_of(s)
        if r is not None:
            groups[s.get('fired_at','')[:10]].append(r)
    Rs = [x for g in groups.values() for x in g]
    nR, G = len(Rs), len(groups)
    if nR == 0: return None, None, None
    meanR = sum(Rs)/nR
    if G >= 2:
        seR = (sum((sum(g) - len(g)*meanR)**2 for g in groups.values()) * G/(G-1))**0.5 / nR
    else:
        seR = 0.0
    return meanR, meanR-1.96*seR, meanR+1.96*seR

REG_DATE = '2026-06-16'

closed = [s for s in signals if is_closed(s)]
rsi_fwd = [s for s in closed if s.get('primary_signal')=='rsi_oversold_bounce'
           and s.get('fired_at','')[:10] >= REG_DATE]
rsi_is  = [s for s in closed if s.get('primary_signal')=='rsi_oversold_bounce'
           and s.get('fired_at','')[:10] < REG_DATE]
bb_fwd  = [s for s in closed if s.get('primary_signal')=='bb_lower_touch'
           and s.get('fired_at','')[:10] >= REG_DATE]
bb_is   = [s for s in closed if s.get('primary_signal')=='bb_lower_touch'
           and s.get('fired_at','')[:10] < REG_DATE]

def fmt(sigs, label):
    n = len(sigs); k = sum(1 for s in sigs if win(s))
    lo, hi = wilson_ci(k, n)
    mr, mlo, mhi = cluster_mean_r(sigs)
    wr = k/n*100 if n else 0
    return (label, k, n, wr, lo*100, hi*100, mr or 0, mlo or 0, mhi or 0)

print("=== RSI FWD vs IS vs BB ===")
for row in [
    fmt(rsi_is, 'RSI IS'),
    fmt(rsi_fwd, 'RSI FWD'),
    fmt(bb_is,  'BB IS'),
    fmt(bb_fwd, 'BB FWD'),
]:
    l,k,n,wr,lo,hi,mr,mlo,mhi = row
    print(f"  {l:8s}: {k}/{n}={wr:.1f}% CI[{lo:.1f}%,{hi:.1f}%]  E(R)={mr:+.3f} CI[{mlo:+.3f},{mhi:+.3f}]")

print("\n=== FWD グループ別 ===")
for g in ['index','jpy_fx','other_fx','metal','btc','oil']:
    fwd = [s for s in rsi_fwd if get_group(s)==g]
    isg = [s for s in rsi_is  if get_group(s)==g]
    n,k = len(fwd), sum(1 for s in fwd if win(s))
    ni,ki = len(isg), sum(1 for s in isg if win(s))
    lo,hi = wilson_ci(k,n)
    mr,mlo,mhi = cluster_mean_r(fwd)
    if n > 0:
        is_str = f"IS {ki}/{ni}={ki/ni*100:.1f}%" if ni > 0 else "IS N=0"
        print(f"  {g:10s}: FWD {k}/{n}={k/n*100:.1f}% CI[{lo*100:.1f}%,{hi*100:.1f}%]  E(R)={mr:+.3f}  |  {is_str}")

print("\n=== FWD トレンド別 ===")
for t in ['上昇','下降','中立・もみあい','unknown']:
    fwd = [s for s in rsi_fwd if get_trend(s)==t]
    n,k = len(fwd), sum(1 for s in fwd if win(s))
    lo,hi = wilson_ci(k,n)
    mr,mlo,mhi = cluster_mean_r(fwd)
    if n > 0:
        print(f"  {t:12s}: {k}/{n}={k/n*100:.1f}% CI[{lo*100:.1f}%,{hi*100:.1f}%]  E(R)={mr:+.3f}")

print("\n=== FWD 時間足別 ===")
for tf in ['1h','4h','1d']:
    fwd = [s for s in rsi_fwd if s.get('timeframe')==tf]
    n,k = len(fwd), sum(1 for s in fwd if win(s))
    lo,hi = wilson_ci(k,n)
    mr,mlo,mhi = cluster_mean_r(fwd)
    if n > 0:
        print(f"  {tf:5s}: {k}/{n}={k/n*100:.1f}% CI[{lo*100:.1f}%,{hi*100:.1f}%]  E(R)={mr:+.3f}")

# H1: FWD Wilson CI lower > 43%?
print("\n=== H1: FWD win rate CI lower > 43%? ===")
n = len(rsi_fwd); k = sum(1 for s in rsi_fwd if win(s))
lo,hi = wilson_ci(k,n)
print(f"  FWD: {k}/{n}={k/n*100:.1f}% CI[{lo*100:.2f}%,{hi*100:.2f}%]")
print(f"  H1 {'✅ PASS' if lo*100 > 43 else '❌ FAIL'}: CI lower {lo*100:.2f}% {'>' if lo*100>43 else '<'} 43%")

# H2: 上昇×RSI CI lower > 50%?
print("\n=== H2: 上昇×RSI FWD CI lower > 50%? ===")
up = [s for s in rsi_fwd if get_trend(s)=='上昇']
n2,k2 = len(up), sum(1 for s in up if win(s))
lo2,hi2 = wilson_ci(k2,n2)
print(f"  上昇×RSI FWD: {k2}/{n2}={k2/n2*100:.1f}% CI[{lo2*100:.1f}%,{hi2*100:.1f}%]")
print(f"  H2 {'✅ PASS' if lo2*100 > 50 else '❌ FAIL'}: CI lower {lo2*100:.1f}% {'>' if lo2*100>50 else '<'} 50%")

# H3: IS low performers (jpy_fx + metal) recovered in FWD?
print("\n=== H3: IS低勝率(jpy_fx+metal)のFWD改善 ===")
for g in ['jpy_fx','metal']:
    i = [s for s in rsi_is  if get_group(s)==g]
    f = [s for s in rsi_fwd if get_group(s)==g]
    ni,ki = len(i), sum(1 for s in i if win(s))
    nf,kf = len(f), sum(1 for s in f if win(s))
    wr_i = ki/ni*100 if ni else 0
    wr_f = kf/nf*100 if nf else 0
    diff = wr_f - wr_i
    lo,hi = wilson_ci(kf,nf)
    print(f"  {g}: IS {ki}/{ni}={wr_i:.1f}% → FWD {kf}/{nf}={wr_f:.1f}% (+{diff:.1f}pp) CI[{lo*100:.1f}%,{hi*100:.1f}%]")

# FWD halves
print("\n=== 前半・後半比較 ===")
rsi_s = sorted(rsi_fwd, key=lambda s: s.get('fired_at',''))
h = len(rsi_s)//2
for label, grp in [('前半', rsi_s[:h]), ('後半', rsi_s[h:])]:
    n,k = len(grp), sum(1 for s in grp if win(s))
    lo,hi = wilson_ci(k,n)
    mr,mlo,mhi = cluster_mean_r(grp)
    print(f"  {label}: {k}/{n}={k/n*100:.1f}% CI[{lo*100:.1f}%,{hi*100:.1f}%]  E(R)={mr:+.3f} CI[{mlo:+.3f},{mhi:+.3f}]")

# E(R) cluster correction
mr, mlo, mhi = cluster_mean_r(rsi_fwd)
print(f"\n=== E(R) クラスタ補正CI ===")
print(f"  E(R)={mr:+.3f} CI[{mlo:+.3f},{mhi:+.3f}]")
print(f"  CI lower > 0: {'✅' if mlo > 0 else '❌（⛔反証未確定）'}")

# Index×RSI vs Index×BB comparison
print("\n=== 指数×RSI vs 指数×BB ===")
idx_rsi = [s for s in rsi_fwd if get_group(s)=='index']
idx_bb  = [s for s in bb_fwd  if get_group(s)=='index']
for label, grp in [('index×RSI FWD', idx_rsi), ('index×BB FWD', idx_bb)]:
    n,k = len(grp), sum(1 for s in grp if win(s))
    lo,hi = wilson_ci(k,n)
    mr,mlo,mhi = cluster_mean_r(grp)
    if n > 0:
        print(f"  {label}: {k}/{n}={k/n*100:.1f}% CI[{lo*100:.1f}%,{hi*100:.1f}%]  E(R)={mr:+.3f}")

# jpy_fx×RSI vs jpy_fx×BB (reference to #024)
print("\n=== jpy_fx×RSI vs jpy_fx×BB (FWD) ===")
jpyrsi = [s for s in rsi_fwd if get_group(s)=='jpy_fx']
jpybb  = [s for s in bb_fwd  if get_group(s)=='jpy_fx']
for label, grp in [('jpy_fx×RSI FWD', jpyrsi), ('jpy_fx×BB FWD', jpybb)]:
    n,k = len(grp), sum(1 for s in grp if win(s))
    lo,hi = wilson_ci(k,n)
    if n > 0:
        print(f"  {label}: {k}/{n}={k/n*100:.1f}% CI[{lo*100:.1f}%,{hi*100:.1f}%]")

print("\n=== 総クローズシグナル数 ===")
print(f"  {len(closed)}")
```

---

## 実行結果（2026-08-07）

```
=== RSI FWD vs IS vs BB ===
  RSI IS  : 52/133=39.1% CI[31.2%,47.6%]  E(R)=-0.088 CI[-0.240,+0.065]
  RSI FWD : 87/168=51.8% CI[44.3%,59.2%]  E(R)=+0.208 CI[-0.058,+0.474]
  BB IS   : 75/175=42.9% CI[35.8%,50.3%]  E(R)=-0.000 CI[-0.237,+0.236]
  BB FWD  : 175/391=44.8% CI[39.9%,49.7%]  E(R)=+0.044 CI[-0.106,+0.194]

=== FWD グループ別 ===
  index     : FWD 19/28=67.9% CI[49.3%,82.1%]  E(R)=+0.583  |  IS 20/35=57.1%
  jpy_fx    : FWD 17/29=58.6% CI[40.7%,74.5%]  E(R)=+0.368  |  IS 2/20=10.0%
  other_fx  : FWD 23/55=41.8% CI[29.7%,55.0%]  E(R)=-0.024  |  IS 14/23=60.9%
  metal     : FWD 15/29=51.7% CI[34.4%,68.6%]  E(R)=+0.207  |  IS 4/31=12.9%
  btc       : FWD 5/11=45.5% CI[21.3%,72.0%]  E(R)=+0.060  |  IS 4/14=28.6%
  oil       : FWD 8/16=50.0% CI[28.0%,72.0%]  E(R)=+0.167  |  IS 8/10=80.0%

=== FWD トレンド別 ===
  上昇          : 27/38=71.1% CI[55.2%,83.0%]  E(R)=+0.658
  下降          : 33/82=40.2% CI[30.3%,51.1%]  E(R)=-0.061
  中立・もみあい     : 27/48=56.2% CI[42.3%,69.3%]  E(R)=+0.312

=== FWD 時間足別 ===
  1h   : 50/111=45.0% CI[36.1%,54.3%]  E(R)=+0.051
  4h   : 30/48=62.5% CI[48.4%,74.8%]  E(R)=+0.458
  1d   : 7/9=77.8% CI[45.3%,93.7%]  E(R)=+0.815

=== H1: FWD win rate CI lower > 43%? ===
  FWD: 87/168=51.8% CI[44.27%,59.22%]
  H1 ✅ PASS: CI lower 44.27% > 43%

=== H2: 上昇×RSI FWD CI lower > 50%? ===
  上昇×RSI FWD: 27/38=71.1% CI[55.2%,83.0%]
  H2 ✅ PASS: CI lower 55.2% > 50%

=== H3: IS低勝率(jpy_fx+metal)のFWD改善 ===
  jpy_fx: IS 2/20=10.0% → FWD 17/29=58.6% (+48.6pp) CI[40.7%,74.5%]
  metal: IS 4/31=12.9% → FWD 15/29=51.7% (+38.8pp) CI[34.4%,68.6%]

=== 前半・後半比較 ===
  前半: 38/84=45.2% CI[35.0%,55.9%]  E(R)=+0.055 CI[-0.315,+0.426]
  後半: 49/84=58.3% CI[47.7%,68.3%]  E(R)=+0.361 CI[+0.045,+0.677]

=== E(R) クラスタ補正CI ===
  E(R)=+0.208 CI[-0.058,+0.474]
  CI lower > 0: ❌（⛔反証未確定）

=== 指数×RSI vs 指数×BB ===
  index×RSI FWD: 19/28=67.9% CI[49.3%,82.1%]  E(R)=+0.583
  index×BB FWD: 43/102=42.2% CI[33.0%,51.9%]  E(R)=-0.016

=== jpy_fx×RSI vs jpy_fx×BB (FWD) ===
  jpy_fx×RSI FWD: 17/29=58.6% CI[40.7%,74.5%]
  jpy_fx×BB FWD: 35/82=42.7% CI[32.5%,53.5%]

=== 総クローズシグナル数 ===
  2660
```

---

## 判定まとめ

| 仮説 | 結果 |
|---|---|
| H1: FWD 勝率 CI下限 > 43% | ✅ PASS (44.3% > 43%) |
| H2: 上昇×RSI FWD CI下限 > 50% | ✅ PASS (55.2% > 50%) |
| H3: IS低勝率グループ(jpy_fx+metal)のFWD改善 | ✅ PASS (+48.6pp / +38.8pp) |
| E(R) クラスタ補正CI全域プラス | ❌ FAIL (CI下限 -0.058 < 0) |

**E(R)はまだ0をまたぐため🟡蓄積中継続。N=168でCI下限がゼロに近づいており次回チェック時が注目。**
