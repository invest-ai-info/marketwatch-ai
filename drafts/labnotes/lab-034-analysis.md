# AIシグナル研究日誌 #034 分析スクリプト・生出力

## 仮説
指数×ロング(全足ライブ) 昇格後フォローアップ——前向きN=155でE(R)CI下限が+0.17→-0.00に低下した。  
後半54件（2026-06-30〜2026-07-08）の勝率・E(R)は前半104件と比べて有意に低下したか？  
シグナル別・時間足別に後半不振の主因を特定する。

## 事前合否基準（仮説採択前宣言）
- H1（軟化確認）: 後半54件の勝率<50%（点推定）かつCI上限<60%
- H2（主因特定）: シグナル別・時間足別で後半低迷の原因コンポーネントを識別

## 検証スクリプト（Python反実仮想集計）

```python
import json, math
from collections import Counter

def wilson(k,n,z=1.96):
    if n==0: return (0,0)
    p=k/n; d=z*math.sqrt(p*(1-p)/n+z**2/(4*n*n))/(1+z**2/n)
    c=p+z**2/(2*n); c/=(1+z**2/n)
    return (max(0,c-d),min(1,c+d))

def atr_r(s):
    sl = abs(float(s.get('sl_pct') or 0))
    tp1 = abs(float(s.get('tp1_pct') or 0))
    if sl == 0: return None
    outcome = s.get('outcome','')
    if outcome == 'tp1': return tp1/sl
    elif outcome == 'sl': return -1.0
    return None

with open('signals-log.json') as f:
    data = json.load(f)
signals = data if isinstance(data, list) else data.get('signals', [])

INDEX_TICKERS = {'NKD=F','ES=F','NQ=F','YM=F','^FTSE'}
def is_index(s): return s.get('ticker','') in INDEX_TICKERS
def is_long(s): return 'ロング' in (s.get('direction') or '') or s.get('direction','') == 'long'
def closed(s): return s.get('outcome') in ('tp1','sl','tp2')
def win(s): return s.get('outcome') in ('tp1','tp2')
def resolve_date(s):
    d = s.get('outcome_resolved_at') or s.get('fired_at','')
    return d[:10] if d else '9999'

REGISTER_DATE = '2026-06-12'

all_il = sorted([s for s in signals if closed(s) and is_index(s) and is_long(s)], key=resolve_date)
is_sample = [s for s in all_il if resolve_date(s) < REGISTER_DATE]
fwd = [s for s in all_il if resolve_date(s) >= REGISTER_DATE]
fwd_early = fwd[:104]
fwd_late  = fwd[104:]

print(f"Total index×long closed: {len(all_il)}")
print(f"IS: {len(is_sample)} / FWD: {len(fwd)}")
```

## 生出力

```
Total signals: 1893
Closed signals (tp1/sl/tp2): 1504

指数×ロング 全体: 143/276=51.8% CI[45.9%,57.6%]  E(R)=+0.209 CI[+0.071,+0.347]
IS (before 2026-06-12): 56/118=47.5% CI[38.7%,56.4%]  E(R)=+0.107
FWD前半(1~104):  62/104=59.6% CI[50.0%,68.5%]  E(R)=+0.391 CI[+0.170,+0.612]
FWD後半(105~158): 25/54=46.3% CI[33.7%,59.4%]  E(R)=+0.080 CI[-0.233,+0.393]
後半期間: 2026-06-30 ～ 2026-07-08

--- シグナル別（全体 IS+FWD） ---
rsi_oversold_bounce: 31/47=66.0% CI[51.7%,77.8%]
bb_lower_touch:      40/77=51.9% CI[41.0%,62.7%]
high_break:          25/49=51.0% CI[37.5%,64.4%]
bb_upper_break:       9/16=56.2% CI[33.2%,76.9%]
macd_golden:         24/53=45.3% CI[32.7%,58.5%]
ma_golden:            6/12=50.0% CI[25.4%,74.6%]

--- シグナル別 前半104件 ---
bb_lower_touch: 20/31=64.5%
high_break:     11/18=61.1%
macd_golden:    10/22=45.5%
bb_upper_break:  9/12=75.0%
rsi_oversold_bounce: 5/6=83.3%

--- シグナル別 後半54件 ---
high_break:     6/15=40.0% CI[20%,64%]
bb_lower_touch: 6/15=40.0% CI[20%,64%]
macd_golden:    5/12=41.7% CI[19%,68%]
rsi_oversold_bounce: 6/6=100.0%
ma_golden:       2/2=100.0%
bb_upper_break:  0/2=0.0%

--- 銘柄別（後半54件） ---
NKD=F: 6/14=42.9%
YM=F:  6/13=46.2%
ES=F:  7/12=58.3%
NQ=F:  5/12=41.7%
^FTSE: 1/3=33.3%

--- 銘柄別（全体） ---
NKD=F: 38/63=60.3% CI[48.0%,71.5%]
ES=F:  37/73=50.7% CI[39.5%,61.8%]
NQ=F:  32/61=52.5% CI[40.2%,64.5%]
YM=F:  26/55=47.3% CI[34.7%,60.2%]
^FTSE: 10/24=41.7% CI[24.5%,61.2%]

--- 時間足別（全体） ---
1h: 84/151=55.6% CI[47.7%,63.3%] E(R)=+0.298
4h: 54/115=47.0% CI[38.1%,56.0%] E(R)=+0.096
1d:  5/10=50.0% CI[23.7%,76.3%] E(R)=+0.167

--- 時間足別（後半54件） ---
1h: 15/25=60.0%
4h:  9/25=36.0%
1d:  1/4=25.0%

--- トラッカー 2026-07-09 update ---
指数×ロング(全足ライブ): ✅昇格 FWD 84/155=54% E(R)=+0.265 CI[-0.00~+0.53]
（注: trackerは独自日付クラスタ補正のためmy計算FWD=158と4件差）
```

## 判定

| 仮説 | 宣言条件 | 結果 | 判定 |
|---|---|---|---|
| H1: 後半軟化確認 | 点推定<50% かつ CI上限<60% | 46.3% / CI上限59.4% | ✅ 通過A |
| H2: 主因特定 | 時間足・シグナル別で識別 | 4H後半36%・bb/high_break後半40% | ✅ 通過A |

## 交絡点検
- 銘柄構成（後半）: NKD=F(14)/YM=F(13)/ES=F(12)/NQ=F(12)/^FTSE(3)。前半と大きな偏りなし
- 4H後半低迷（36%=9/25）は台数が多く（25件）、軽い確率ノイズの範囲を超える可能性
- rsi_oversold_bounce 後半N=6件のみ（100%はN小サンプルの幸運）
- Wilson 95%CI を全件適用。N<20の数値は参考値として扱う

## 現在のトラッカー値（2026-07-09）
- 指数×ロング(全足ライブ): ✅昇格 FWD N=155 54% E(R)=+0.265 CI[-0.00~+0.53]
  （前回#026確認時: N=104 E(R)=+0.391 CI[+0.17~+0.61]）
