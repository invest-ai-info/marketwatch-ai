# lab-126 分析ノート — 通貨の強弱と同じ向きのシグナル（cs_aligned）

基準日: 2026-10-15  
仮説ID: cs_aligned  
登録日: 2026-09-28（FWD境界: 2026-09-29）

---

## 分析スクリプト（Python・信号は signals-log.json から直接集計）

```python
import json, math

def r_of(rec):
    return {'tp2': 2.0, 'tp1': 4.0/3.0, 'sl': -1.0}.get(rec.get('outcome'))

def cs_align_of(d):
    fa = d.get('fx_alignment') or {}
    aligned = fa.get('aligned')
    if aligned is True: return 'aligned'
    if aligned is False: return 'against'
    return None

def wilson_ci(k, n, z=1.96):
    if n == 0: return (0, 0)
    p = k/n
    z2 = z*z
    lo = (p + z2/(2*n) - z*math.sqrt((p*(1-p)+z2/(4*n))/n)) / (1 + z2/n)
    hi = (p + z2/(2*n) + z*math.sqrt((p*(1-p)+z2/(4*n))/n)) / (1 + z2/n)
    return (lo, hi)

def r_ci(rs, z=1.96):
    n = len(rs)
    if n == 0: return (0,0)
    avg = sum(rs)/n
    var = sum((r-avg)**2 for r in rs)/(n-1) if n>1 else 0
    se = math.sqrt(var/n)
    return (avg - z*se, avg + z*se)

with open('signals-log.json') as f:
    signals = json.load(f)

BOUND = '2026-09-29'  # registered_at翌日

groups = {
    'cs_aligned_is': [], 'cs_against_is': [], 'baseline_is': [],
    'cs_aligned_fwd': [], 'cs_against_fwd': [], 'baseline_fwd': [], 'cs_neutral_fwd': []
}

for s in signals:
    r = r_of(s)
    if r is None: continue  # expired/no_plan/openは除外
    fired = s.get('fired_at','')[:10]
    csa = cs_align_of(s)
    
    if fired < BOUND:  # IS
        groups['baseline_is'].append(r)
        if csa == 'aligned': groups['cs_aligned_is'].append(r)
        elif csa == 'against': groups['cs_against_is'].append(r)
    else:  # FWD
        groups['baseline_fwd'].append(r)
        if csa == 'aligned': groups['cs_aligned_fwd'].append(r)
        elif csa == 'against': groups['cs_against_fwd'].append(r)
        elif csa is None: groups['cs_neutral_fwd'].append(r)
```

---

## 生出力

```
=== 全数統計 (boundary: 2026-09-29) ===
cs_aligned_is:   n=788,  k=318, win=40.4%, CI_win=[37.0%~43.8%], avgR=-0.058, R_CI=[-0.138~+0.022]
cs_against_is:   n=798,  k=354, win=44.4%, CI_win=[40.9%~47.8%], avgR=+0.035, R_CI=[-0.045~+0.116]
baseline_is:     n=4867, k=2085, win=42.8%, CI_win=[41.5%~44.2%], avgR=-0.000, R_CI=[-0.033~+0.032]

cs_aligned_fwd:  n=65,   k=15,  win=23.1%, CI_win=[14.5%~34.6%], avgR=-0.462, R_CI=[-0.702~-0.221]
cs_against_fwd:  n=68,   k=26,  win=38.2%, CI_win=[27.6%~50.1%], avgR=-0.108, R_CI=[-0.379~+0.164]
baseline_fwd:    n=365,  k=132, win=36.2%, CI_win=[31.4%~41.2%], avgR=-0.156, R_CI=[-0.271~-0.041]
cs_neutral_fwd:  n=232,  k=91,  win=39.2%, CI_win=[33.2%~45.6%], avgR=-0.085, R_CI=[-0.232~+0.062]

=== FWD cs_aligned 内訳（銘柄グループ別）===
JPY系FX: n=30, win=20%, avgR=-0.53
非JPY系FX: n=35, win=26%, avgR=-0.40
```

---

## 解釈

### IS（事前登録前・n=788）
- 勝率40.4%（全体42.8%より約2ポイント低め）
- R_CI=[-0.138~+0.022]：0を跨いでいる → 有意差なし
- 「少し悪め」程度で、確信できる差ではなかった

### FWD（前向き2026-09-28登録・n=65）
- 勝率23.1%（全体36.2%より13ポイント低い）
- avgR=-0.462 vs 全体-0.156 → 差=-0.306R/1回
- R_CI=[-0.702~-0.221]：**両端が負** → 統計的に有意な損の傾向

### 対照群（cs_against・n=68）
- 勝率38.2%（全体36.2%とほぼ同じ）
- R_CI=[-0.379~+0.164]：0を跨いでいる → 全体と有意差なし

### 結論
通貨の強弱と「同じ向き」に入ると、同期間の全体平均より顕著に悪い。
「逆向き」は全体と差がない（避けるべきとは言えない）。
FX取引の「通貨強弱に乗る」という直感と逆の結果。

### 交絡点
- cs_aligned は FX のみ（JPY系30・非JPY系35）。他のアセットはcs_align=None。
- 期間（2026-09-28〜）全体の成績も悪い（avgR=-0.156）。難しい相場環境の中での結果。
- n=65（トラッカーのN≥80未満）→ まだ蓄積中。官式ステータス：🟡蓄積中。

### 比較
- トラッカー値（日付クラスタ補正SE使用）：k=15/n=70, avgR=-0.500, rci_lo=-0.864, rci_hi=-0.136
  ※ 境界が registered_at当日（2026-09-28）のため本集計より5件多い
- 本集計値（verify.py準拠・fired_from=2026-09-29）：k=15/n=65, avgR=-0.462, R_CI=[-0.702~-0.221]
- どちらでも R_CI の両端が負 → 解釈は変わらない
