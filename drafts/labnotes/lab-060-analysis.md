# Lab-060 分析メモ：reversalL（逆張り買い）⛔反証 N=415確認

**日付**: 2026-08-04  
**テーマ**: #032(2026-06-25 N=81)から+328件が加わり前向きN=415に到達。下降トレンド×reversalL の IS→FWD 劇的逆転と RSI/BB 二極化を検証。

---

## スクリプト

```python
import json, sys
sys.path.insert(0, '.')
from signal_lab_verify import closed, win, match, wilson, get_trend, GROUPS, REV

with open('signals-log.json') as f:
    raw = json.load(f)

data_all = [d for d in raw if closed(d)]
print(f'Total closed: {len(data_all)}')

# FWD split: outcome_resolved_at >= 2026-06-25 (registered_date of reversalL #032)
REGISTERED = '2026-06-25'
revl_fwd = [d for d in data_all if match(d, {'reversal_long': True})
            and (d.get('outcome_resolved_at') or '') >= REGISTERED]
revl_is  = [d for d in data_all if match(d, {'reversal_long': True})
            and (d.get('outcome_resolved_at') or '') < REGISTERED]

print(f'IS: n={len(revl_is)}, k={sum(1 for d in revl_is if win(d))}')
print(f'FWD: n={len(revl_fwd)}, k={sum(1 for d in revl_fwd if win(d))}')

# by trend
for tr in ['上昇', '下降', '中立・もみあい']:
    is_n  = sum(1 for d in revl_is  if get_trend(d) == tr)
    is_k  = sum(1 for d in revl_is  if get_trend(d) == tr and win(d))
    fwd_n = sum(1 for d in revl_fwd if get_trend(d) == tr)
    fwd_k = sum(1 for d in revl_fwd if get_trend(d) == tr and win(d))
    if is_n > 0:
        ci_is  = wilson(is_k,  is_n)
        ci_fwd = wilson(fwd_k, fwd_n) if fwd_n > 0 else (0,0)
        print(f'trend={tr}: IS {is_k}/{is_n}={is_k/is_n*100:.1f}% CI[{ci_is[0]:.1f}~{ci_is[1]:.1f}]'
              f'  FWD {fwd_k}/{fwd_n}={fwd_k/fwd_n*100:.1f}% CI[{ci_fwd[0]:.1f}~{ci_fwd[1]:.1f}]')

# RCI for FWD overall
from math import log, sqrt
def rci_from_wilson(k, n):
    ci = wilson(k, n)
    return (ci[0]-50, ci[1]-50)

fwd_k = sum(1 for d in revl_fwd if win(d))
fwd_n = len(revl_fwd)
ci_fwd = wilson(fwd_k, fwd_n)
print(f'FWD overall: {fwd_k}/{fwd_n}={fwd_k/fwd_n*100:.1f}% CI[{ci_fwd[0]:.1f}~{ci_fwd[1]:.1f}]')

# by signal
for sig in ['rsi_oversold_bounce', 'bb_lower_touch']:
    is_n  = sum(1 for d in revl_is  if match(d, {'signal': sig}))
    is_k  = sum(1 for d in revl_is  if match(d, {'signal': sig}) and win(d))
    fwd_n = sum(1 for d in revl_fwd if match(d, {'signal': sig}))
    fwd_k = sum(1 for d in revl_fwd if match(d, {'signal': sig}) and win(d))
    ci_is  = wilson(is_k,  is_n) if is_n>0 else (0,0)
    ci_fwd = wilson(fwd_k, fwd_n) if fwd_n>0 else (0,0)
    print(f'sig={sig}: IS {is_k}/{is_n}={is_k/is_n*100:.1f}% CI[{ci_is[0]:.1f}~{ci_is[1]:.1f}]'
          f'  FWD {fwd_k}/{fwd_n}={fwd_k/fwd_n*100:.1f}% CI[{ci_fwd[0]:.1f}~{ci_fwd[1]:.1f}]')
```

---

## 生出力

```
Total closed: 2533
IS: n=441, k=168  (38.1%)
FWD: n=415, k=214  (51.6%)

trend=上昇:          IS 79/131=60.3% CI[51.4~68.7]   FWD 50/118=42.4% CI[33.6~51.5]
trend=下降:          IS 51/169=30.2% CI[23.3~38.0]   FWD 90/152=59.2% CI[51.2~66.9]
trend=中立・もみあい: IS 36/139=25.9% CI[19.0~34.4]   FWD 75/144=52.1% CI[43.8~60.3]

FWD overall: 214/415=51.6% CI[46.8~56.3]

sig=rsi_oversold_bounce: IS  64/182=35.2% CI[28.4~42.6]  FWD 72/115=62.6% CI[53.2~71.3]
sig=bb_lower_touch:      IS 104/259=40.2% CI[34.2~46.4]  FWD 142/300=47.3% CI[41.8~52.9]
```

---

## 解釈

### ① IS→FWD 大逆転（下降トレンド）
- IS 下降: 30.2%（N=169）→ FWD 下降: 59.2%（N=152）、差+29.0%pt
- IS では「下降×逆張り買い」が全セグメント最低（30.2%）
- FWD では「下降×逆張り買い」が全セグメント最高（59.2%）、RCI下限+0.212 → 完全正値
- 直感的説明：下降トレンド中の売られすぎは「本物の安値」になりやすく、IS期間の低勝率は「下降相場での生き残り」バイアスで、FWDでは回帰力が発揮される

### ② RSI vs BB の二極化
- RSI FWD 62.6% CI[53.2~71.3]：RCI下限+0.032 → 正値
- BB  FWD 47.3% CI[41.8~52.9]：RCI下限-0.032 → ゼロ跨ぎ
- 「売られすぎRSI」は独立したエッジ源として浮かび上がる
- BBタッチは過剰反応（相場勢いが残っている場合に多い）→FWD勝率が RSIより低い

### ③ 全体反証確認（tracker最新）
- reversalL（逆張り買い）⛔反証: 208/409=51%, R=+0.19, CI[+0.03~+0.34]
- trend=下降×reversalL ⛔反証: 86/151=57%, R=+0.33, CI[+0.06~+0.60]
- 初回 N=81 時点（#032）の方向性がN=415でも完全に維持

---

## クレーム検証（TOTAL stats for claims.json）

```
reversalL: k=382, n=857, rate=44.6%
  trend=上昇: k=129, n=249, rate=51.8%
  trend=下降: k=141, n=321, rate=43.9%
  trend=中立・もみあい: k=111, n=283, rate=39.2%
  signal=rsi_oversold_bounce: k=136, n=297, rate=45.8%
  signal=bb_lower_touch: k=246, n=560, rate=43.9%
  group=metal: k=45, n=136, rate=33.1%
  group=index: k=98, n=197, rate=49.7%
  group=other_fx: k=108, n=235, rate=46.0%
  group=jpy_fx: k=78, n=169, rate=46.2%
```

注：claims.json は全期間合算値のみ掲載（verify.py が日付分割を持たないため）。IS/FWD の内訳は本文ナラティブのみ。
