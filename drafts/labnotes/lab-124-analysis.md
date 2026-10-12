# 研究日誌 #124 分析メモ — 上昇トレンド×RSI売られすぎ（仮説ID: auto_rsi_band-os_trend-上昇）

作成日: 2026-10-13
仮説登録日: 2026-08-11
IS/FWD 分割日（カットオフ）: 2026-08-12

## 計算方法

```python
import json, sys
sys.path.insert(0, '/home/user/marketwatch-ai')
import signal_lab_verify as v

with open('/home/user/marketwatch-ai/signals-log.json') as f:
    log = json.load(f)

signals = log if isinstance(log, list) else log.get('signals', log.get('data', []))

# closed() と win() は signal_lab_verify から
def match_filter(sig, flt):
    return v.match(sig, {k: val for k, val in flt.items()
                          if k not in ('fired_before', 'fired_from', 'tf')})

def date_filter(sig, flt):
    fa = sig.get('fired_at', '')[:10]
    if 'fired_before' in flt and fa >= flt['fired_before']:
        return False
    if 'fired_from' in flt and fa < flt['fired_from']:
        return False
    return True

def tf_filter(sig, flt):
    if 'tf' not in flt:
        return True
    return sig.get('timeframe', '') == flt['tf']

def compute(flt):
    subset = [s for s in signals
              if v.closed(s) and match_filter(s, flt)
              and date_filter(s, flt) and tf_filter(s, flt)]
    k = sum(1 for s in subset if v.win(s))
    n = len(subset)
    return k, n
```

## 全シグナル（ベースライン）

- closed signals: n=5,174
- win: k=2,199
- 勝率: 42.5%
- avgR: -0.009

## IS（検証に使った期間 / fired_before=2026-08-12）

### ロング
- filter: {rsi_band=os, trend=上昇, direction=long, fired_before=2026-08-12}
- k=40, n=52, 勝率=76.9%, avgR=+0.792
- Wilson 95%CI: [63.9%~86.3%]

### 全方向
- filter: {rsi_band=os, trend=上昇, fired_before=2026-08-12}
- k=45, n=74, 勝率=60.8%, avgR=+0.417
- Wilson 95%CI: [49.4%~71.1%]

## FWD（その後の期間 / fired_from=2026-08-12）

### ロング・全足
- filter: {rsi_band=os, trend=上昇, direction=long, fired_from=2026-08-12}
- k=21, n=46, 勝率=45.7%, avgR=+0.064
- Wilson 95%CI: [32.2%~59.8%]

### ロング・4時間足
- filter: {rsi_band=os, trend=上昇, direction=long, tf=4h, fired_from=2026-08-12}
- k=13, n=22, 勝率=59.1%, avgR=+0.377
- Wilson 95%CI: [38.7%~76.7%]

### ロング・1時間足
- filter: {rsi_band=os, trend=上昇, direction=long, tf=1h, fired_from=2026-08-12}
- k=8, n=23, 勝率=34.8%, avgR=-0.190
- Wilson 95%CI: [18.8%~55.1%]

### 全方向・全足
- filter: {rsi_band=os, trend=上昇, fired_from=2026-08-12}
- k=34, n=72, 勝率=47.2%, avgR=+0.100
- Wilson 95%CI: [36.1%~58.6%]

## 参考: 上昇なし（RSI売られすぎ×ロング・全トレンド）
- k_all=241, n_all=488, 勝率=49.4%, avgR=+0.151

## トラッカー現在値（蓄積中）
- alltime: k=79, n=146, 勝率=54.1%
- FWD: k=35, n=73, 勝率=47.9%, CI=[36.9%~59.2%], avgR=+0.119

## IS vs FWD の差（ロング）
- IS 76.9% → FWD 45.7% （差: -31.2pp）
- IS avgR +0.79 → FWD avgR +0.06 （差: -0.73R）

## 解釈
- IS期間の高すぎる勝率（76.9%）が「後から見つけた」パターンであることを示す典型例。
- 事前登録によりFWDで前向きに確かめたところ、45.7%（とんとん43%に近い）となった。
- 4時間足FWD（59.1%）が1時間足FWD（34.8%）を大きく上回る点は引き続き注目に値する。
- ただし4時間足のCI（38.7%〜76.7%）は広く、まだ結論を出せる段階ではない。
