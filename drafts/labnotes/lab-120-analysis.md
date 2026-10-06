# lab-120-analysis.md
# 下降トレンドで逆張り買いをすると負けやすい？ 前向き370回の答え

基準日: 2026-10-07  
仮説: trend=下降×reversal_long (gate、登録 2026-06-25、FWD from 2026-06-26)

---

## スクリプト

```python
import json, math
from signal_lab_verify import match, win, get_trend
from signal_lab_sweep import r_of

with open('signals-log.json') as f:
    all_sig = json.load(f)

def closed(s): return s.get('outcome') in ('tp1','tp2','sl')
def get_date(s): return (s.get('fired_at') or '')[:10]

closed_sigs = [s for s in all_sig if closed(s)]
# 全closed: 5083

def stats_full(sigs):
    n = len(sigs)
    k = sum(1 for s in sigs if win(s))
    pct = k/n*100 if n > 0 else 0
    r_vals = [r_of(s) for s in sigs if r_of(s) is not None]
    nR = len(r_vals)
    meanR = sum(r_vals)/nR if nR > 0 else 0
    # Date-clustered SE for R
    groups = {}
    for s in sigs:
        r = r_of(s)
        if r is not None:
            d = get_date(s)
            groups.setdefault(d, []).append(r)
    Rs = [x for g in groups.values() for x in g]
    G = len(groups)
    nR2 = len(Rs)
    mean2 = sum(Rs)/nR2 if nR2 else 0
    if G >= 2:
        seR = (sum((sum(g) - len(g)*mean2)**2 for g in groups.values()) * G/(G-1))**0.5 / nR2
    else:
        seR = 0
    rci = (mean2 - 1.96*seR, mean2 + 1.96*seR)
    # Wilson CI
    if n > 0:
        z = 1.96
        p_hat = k/n
        denom = 1 + z**2/n
        ctr = (p_hat + z**2/(2*n))/denom
        pm = z*math.sqrt(p_hat*(1-p_hat)/n + z**2/(4*n**2))/denom
        wci = (ctr-pm, ctr+pm)
    else:
        wci = (0,0)
    return n,k,pct,mean2,wci,rci
```

---

## 生出力

```
Closed signals: 5083

=== trend=下降×reversal_long ===
IS (〜2026-06-25): n=186, k=63, 33.9%, avgR=-0.210, R-CI=[-0.442~+0.023], W-CI=[27.5%~40.9%]
FWD (2026-06-26〜): n=370, k=188, 50.8%, avgR=+0.186, R-CI=[+0.030~+0.341], W-CI=[45.7%~55.9%]
  FWD 1h: n=252, k=122, 48.4%, avgR=+0.130, R-CI=[-0.051~+0.310], W-CI=[42.3%~54.6%]
  FWD 4h: n=104, k=63, 60.6%, avgR=+0.413, R-CI=[+0.120~+0.707], W-CI=[51.0%~69.4%]
  FWD 1d: n=14, k=3, 21.4%, avgR=-0.500, R-CI=[-0.996~-0.004], W-CI=[7.6%~47.6%]

FWD reversal_long (全トレンド): n=1059, k=494, 46.6%, avgR=+0.088, R-CI=[-0.006~+0.183]
FWD trend=下降×long (全シグナル): n=912, k=433, 47.5%, avgR=+0.108, R-CI=[+0.009~+0.207]

FWD baseline (全体long): n=2955, k=1304, 44.1%, avgR=+0.030, R-CI=[-0.042~+0.102]
  FWD rsi_oversold_bounce: n=135, k=66, 48.9%, avgR=+0.141, R-CI=[-0.093~+0.375]
  FWD bb_lower_touch: n=235, k=122, 51.9%, avgR=+0.211, R-CI=[+0.025~+0.398]

FWD 全シグナル: n=3925, k=1711, 43.6%, avgR=+0.017, R-CI=[-0.032~+0.066]
```

---

## 解釈メモ

- IS (n=186): 33.9% — ベースライン43%を大きく下回り、「避けるべき条件」として機能するかに見えた
- FWD (n=370): 50.8%, avgR=+0.186, R-CI=[+0.030~+0.341] — CIがまるごとプラス → ⛔反証確定
- 特に4時間足 (n=104): 60.6%, R=+0.413, CI=[+0.120~+0.707] — CI全体がプラス
- 1時間足 (n=252): 48.4%, R=+0.130, CI=[-0.051~+0.310] — CIが0をまたぐ（不確実）
- 日足 (n=14): n小さすぎ
- BB下限タッチ×下降トレンド: 51.9%, R=+0.211, CI=[+0.025~+0.398] — CI全体プラス
- RSI売られすぎ×下降トレンド: 48.9%, R=+0.141, CI=[-0.093~+0.375] — CI不確実

仮説の逆向き再登録 (edge): 17/31=55%, CI=[-0.43~+0.98] — まだ蓄積中 (n小)

注意: ⛔反証 = 「避ける条件」としては機能しないとわかった、ということ。
「積極的に買う理由」にはならない（逆向きedgeの前向きはまだ不確実）。
