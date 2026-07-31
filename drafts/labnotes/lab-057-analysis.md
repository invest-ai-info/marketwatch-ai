# lab-057-analysis.md
## AIシグナル研究日誌 #057
**テーマ**: 「静寂な市場」vs「ニュース渦中」——news件数が勝率に与えるグループ依存効果
**解析日**: 2026-08-01
**信号定義**: verify.py互換（tp1/tp2/sl のみ、expired 除外）

---

## Python スクリプト

```python
"""lab-057-analysis.py
#057 ニュース注目度と勝率——news件数がシグナル成績に与える影響
使用日: 2026-08-01  信号定義: verify.py互換 (tp1/tp2/sl のみ, expired 除外)
"""
import json, math

def wilson_ci(k, n, z=1.96):
    if n == 0: return 0.0, 100.0
    p = k/n
    denom = 1 + z**2/n
    center = (p + z**2/(2*n)) / denom
    margin = (z * math.sqrt(p*(1-p)/n + z**2/(4*n**2))) / denom
    return max(0, center - margin)*100, min(1, center + margin)*100

def exp_return(sigs, TP=2.0, SL=1.5):
    k = sum(1 for s in sigs if s.get('outcome') in ['tp1','tp2'])
    l = sum(1 for s in sigs if s.get('outcome') == 'sl')
    n = len(sigs)
    return (k/n)*TP - (l/n)*SL if n > 0 else 0

with open('signals-log.json') as f:
    signals = json.load(f)
closed = [s for s in signals if s.get('outcome') in ['tp1','tp2','sl']]

def nc_band(s):
    nc = s.get('news_count', 0) or 0
    if nc <= 0: return '0'
    elif nc <= 2: return '1-2'
    else: return '3+'

def get_group(s):
    t = s.get('ticker','')
    if t in ['GC=F','SI=F']: return 'metal'
    if t in ['NKD=F','ES=F','NQ=F','YM=F','^FTSE']: return 'index'
    if t == 'BTC-USD': return 'btc'
    if t == 'CL=F': return 'oil'
    if t in ['USDJPY=X','EURJPY=X','GBPJPY=X','AUDJPY=X']: return 'jpy_fx'
    if t in ['EURUSD=X','GBPUSD=X','AUDUSD=X','EURAUD=X','GBPAUD=X']: return 'other_fx'
    return 'unknown'

print("=== 全体集計 ===")
print(f"Total closed (tp1/tp2/sl): {len(closed)}")
for band in ['0', '1-2', '3+']:
    subset = [s for s in closed if nc_band(s) == band]
    k = sum(1 for s in subset if s.get('outcome') in ['tp1','tp2'])
    n = len(subset)
    lo, hi = wilson_ci(k, n)
    er = exp_return(subset)
    print(f"  news={band}: k={k} n={n} rate={k/n*100:.1f}% CI[{lo:.1f}%,{hi:.1f}%] E(R)={er:.3f}")

print()
print("=== グループ別 (news=3+) ===")
for grp in ['metal','index','other_fx','jpy_fx','btc','oil']:
    subset = [s for s in closed if nc_band(s)=='3+' and get_group(s)==grp]
    k = sum(1 for s in subset if s.get('outcome') in ['tp1','tp2'])
    n = len(subset)
    if n < 5: print(f"  news=3+×{grp}: N={n} (小)"); continue
    lo, hi = wilson_ci(k, n)
    er = exp_return(subset)
    print(f"  news=3+×{grp}: k={k} n={n} rate={k/n*100:.1f}% CI[{lo:.1f}%,{hi:.1f}%] E(R)={er:.3f}")

print()
print("=== グループ別 (news=0) ===")
for grp in ['metal','index','other_fx','jpy_fx','btc','oil']:
    subset = [s for s in closed if nc_band(s)=='0' and get_group(s)==grp]
    k = sum(1 for s in subset if s.get('outcome') in ['tp1','tp2'])
    n = len(subset)
    if n < 5: print(f"  news=0×{grp}: N={n} (小)"); continue
    lo, hi = wilson_ci(k, n)
    er = exp_return(subset)
    print(f"  news=0×{grp}: k={k} n={n} rate={k/n*100:.1f}% CI[{lo:.1f}%,{hi:.1f}%] E(R)={er:.3f}")

print()
print("=== news=0 グループ組成 ===")
news0 = [s for s in closed if nc_band(s) == '0']
total_n0 = len(news0)
for grp in ['metal','index','other_fx','jpy_fx','btc','oil']:
    n = sum(1 for s in news0 if get_group(s)==grp)
    print(f"  {grp}: N={n} ({n/total_n0*100:.1f}%)")

print()
print("=== 方向別 × news ===")
for nb in ['0','3+']:
    for dir_ in ['long','short']:
        subset = [s for s in closed if nc_band(s)==nb and (
            'ロング' in (s.get('direction','') or '') if dir_=='long'
            else 'ショート' in (s.get('direction','') or '')
        )]
        k = sum(1 for s in subset if s.get('outcome') in ['tp1','tp2'])
        n = len(subset)
        if n < 10: continue
        lo, hi = wilson_ci(k, n)
        er = exp_return(subset)
        print(f"  news={nb}×{dir_}: k={k} n={n} rate={k/n*100:.1f}% CI[{lo:.1f}%,{hi:.1f}%] E(R)={er:.3f}")

print()
print("=== H1/H2 判定 ===")
idx0 = [s for s in closed if nc_band(s)=='0' and get_group(s)=='index']
idx3 = [s for s in closed if nc_band(s)=='3+' and get_group(s)=='index']
k0 = sum(1 for s in idx0 if s.get('outcome') in ['tp1','tp2'])
k3 = sum(1 for s in idx3 if s.get('outcome') in ['tp1','tp2'])
r0 = k0/len(idx0)*100
r3 = k3/len(idx3)*100
diff_idx = r0 - r3
print(f"H1 - index: news=0 {k0}/{len(idx0)}={r0:.1f}% vs news=3+ {k3}/{len(idx3)}={r3:.1f}% -> 差{diff_idx:.1f}pp")
print(f"H1達成: {'✅' if diff_idx >= 10 else '❌'} (>=10pp)")

ofx0 = [s for s in closed if nc_band(s)=='0' and get_group(s)=='other_fx']
ofx3 = [s for s in closed if nc_band(s)=='3+' and get_group(s)=='other_fx']
ko0 = sum(1 for s in ofx0 if s.get('outcome') in ['tp1','tp2'])
ko3 = sum(1 for s in ofx3 if s.get('outcome') in ['tp1','tp2'])
ro0 = ko0/len(ofx0)*100
ro3 = ko3/len(ofx3)*100
diff_ofx = abs(ro0 - ro3)
print(f"H2 - other_fx: news=0 {ko0}/{len(ofx0)}={ro0:.1f}% vs news=3+ {ko3}/{len(ofx3)}={ro3:.1f}% -> 差{diff_ofx:.1f}pp")
print(f"H2達成: {'✅' if diff_ofx < 5 else '❌'} (<5pp)")
```

---

## 実行出力（最終版・signals-log N=3117・2026-08-01 確定）

```
=== 全体集計 ===
Total closed (tp1/tp2/sl): 2485
  news=0: k=209 n=442 rate=47.3% CI[42.7%,51.9%] E(R)=0.155
  news=1-2: k=122 n=317 rate=38.5% CI[33.3%,43.9%] E(R)=-0.153
  news=3+: k=708 n=1726 rate=41.0% CI[38.7%,43.4%] E(R)=-0.064

=== グループ別 (news=3+) ===
  news=3+×metal: k=115 n=333 rate=34.5% CI[29.6%,39.8%] E(R)=-0.291
  news=3+×index: k=194 n=467 rate=41.5% CI[37.2%,46.1%] E(R)=-0.046
  news=3+×other_fx: k=180 n=418 rate=43.1% CI[38.4%,47.9%] E(R)=0.007
  news=3+×jpy_fx: k=88 n=190 rate=46.3% CI[39.4%,53.4%] E(R)=0.121
  news=3+×btc: k=70 n=187 rate=37.4% CI[30.8%,44.6%] E(R)=-0.190
  news=3+×oil: k=61 n=127 rate=48.0% CI[39.5%,56.7%] E(R)=0.181

=== グループ別 (news=0) ===
  news=0×metal: N=1 (小)
  news=0×index: k=79 n=146 rate=54.1% CI[46.0%,62.0%] E(R)=0.394
  news=0×other_fx: k=129 n=295 rate=43.7% CI[38.2%,49.4%] E(R)=0.031
  news=0×jpy_fx: N=0 (小)
  news=0×btc: N=0 (小)
  news=0×oil: N=0 (小)

=== news=0 グループ組成 ===
  metal: N=1 (0.2%)
  index: N=146 (33.0%)
  other_fx: N=295 (66.7%)
  jpy_fx: N=0 (0.0%)
  btc: N=0 (0.0%)
  oil: N=0 (0.0%)

=== 方向別 × news ===
  news=0×long: k=152 n=335 rate=45.4% CI[40.1%,50.7%] E(R)=0.088
  news=0×short: k=57 n=107 rate=53.3% CI[43.9%,62.4%] E(R)=0.364
  news=3+×long: k=515 n=1267 rate=40.6% CI[38.0%,43.4%] E(R)=-0.077
  news=3+×short: k=193 n=459 rate=42.0% CI[37.6%,46.6%] E(R)=-0.028

=== H1/H2 判定 ===
H1 - index: news=0 79/146=54.1% vs news=3+ 194/467=41.5% -> 差12.6pp
H1達成: ✅ (>=10pp)
H2 - other_fx: news=0 129/295=43.7% vs news=3+ 180/418=43.1% -> 差0.7pp
H2達成: ✅ (<5pp)
```

---

## 解釈メモ

- **news=0 の組成が偏っている**: 442件中 index=146(33.0%)・other_fx=295(66.7%)。jpy_fx/btc/oil/metalはほぼゼロ。つまりnews=0シグナルは実質「指数 or ドルクロスFX」の2択構成。
- **指数群の非対称が鮮明**: index×news=0 は 54.1%（E(R)=+0.394）、index×news=3+ は 41.5%（E(R)=-0.046）。差12.6pp、E(R)差+0.44 R。
- **other_fx群はほぼ影響なし**: 43.7% vs 43.1%（差0.7pp）——news有無が勝率に与える影響は統計的にノイズ水準。
- **news=1-2 の交絡**: 317件はすべてjpy_fx（円クロスFX）。バンド間の単純比較には強いグループ交絡あり。
- **H1・H2ともにクリア**: 事前宣言した2仮説（index差≥10pp・other_fx差<5pp）は両方成立。
- **解釈の注意**: news=0 × index の高勝率（54.1%）は「news=0かつ指数シグナル」全般の傾向。个別シグナルや銘柄の交絡は本解析で未制御。
