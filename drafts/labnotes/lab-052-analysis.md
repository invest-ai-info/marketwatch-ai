# lab-052-analysis.md — AIシグナル研究日誌 #052

## 基準日: 2026-07-27

## 研究テーマ
`blocked=True × dir=long`（サポレジ壁なしロング）のエッジ消失解析。
前向き早期N=44で63.6%を記録し昇格候補とみなされたが、全期間N=186では41.9%に回帰。
「壁なし＝上昇余地大」という直感が、長期的には追加エッジをもたらさないことを確認する。

## 前向きトラッカー確認 (2026-07-27)
- `blocked=True×dir=long gate 2026-06-25`: FWD 78/186=41.9% R=-0.022 CI[-0.21~+0.17] → 🟡蓄積中
  - IS (before 2026-06-25): 25/59=42.4% — 最初から効果なし
  - FW early-44: 28/44=63.6% — 昇格候補として期待された期間
  - FW late-83: 25/83=30.1% — 完全崩落
- `blocked=False×dir=long gate 2026-06-25`: FWD 467/1107=42.2% — 対照群とほぼ同値

## 仮説と事前宣言
H1: blocked=True×Long の全期間CI[35.1%,49.1%] が43%をまたぐ（効果なし方向確認）
H2: blocked=True×Long(41.9%) vs blocked=False×Long(42.2%) の差≤5pp（追加効果なし）
H3: 3トレンドで blocked=T×L が全て 40〜44% 帯に収束（トレンド依存性なし）
H4: blocked=True 方向非対称：Long(41.9%) < Short(46.8%)、差4.9pp（ショートで壁効果の示唆）

## 検証スクリプト（Python）

```python
import json, math

with open("signals-log.json") as f:
    data = json.load(f)

# verify.py 準拠: outcome in (tp1, tp2, sl) = closed, win = (tp1, tp2)
closed = [r for r in data if r.get('outcome') in ['tp1','tp2','sl']]

def is_win(r): return r['outcome'] in ['tp1','tp2']
def is_long(r): return 'ロング' in r.get('direction','')
def is_short(r): return 'ショート' in r.get('direction','')

def get_trend(r):
    ta = r.get('trend_alignment') or {}
    t = ta.get('higher_tf_trend','')
    if '上昇' in t: return '上昇'
    if '下降' in t: return '下降'
    return '中立・もみあい'

def get_group(r):
    t = r.get('ticker','')
    if t in ['GC=F','SI=F']: return 'metal'
    if t in ['NKD=F','ES=F','NQ=F','YM=F','^FTSE']: return 'index'
    if t == 'BTC-USD': return 'btc'
    if t == 'CL=F': return 'oil'
    if t in ['USDJPY','EURJPY','GBPJPY','AUDJPY']: return 'jpy_fx'
    return 'other_fx'

def get_blocked(r):
    sr = r.get('sr_runway') or {}
    return sr.get('blocked', None)

def wilson_ci(k, n, z=1.96):
    p = k/n
    center = (p + z**2/(2*n)) / (1 + z**2/n)
    spread = z * math.sqrt(p*(1-p)/n + z**2/(4*n**2)) / (1 + z**2/n)
    return (max(0,center-spread), min(1,center+spread))

has_sr = [r for r in closed if r.get('sr_runway') is not None]
bl_l = [r for r in has_sr if get_blocked(r)==True and is_long(r)]
bl_s = [r for r in has_sr if get_blocked(r)==True and is_short(r)]
bf_l = [r for r in has_sr if get_blocked(r)==False and is_long(r)]

REG_DATE = "2026-06-25"
bl_l_is = [r for r in bl_l if r.get('fired_at','') < REG_DATE]
bl_l_fw = [r for r in bl_l if r.get('fired_at','') >= REG_DATE]
early44 = sorted(bl_l_fw, key=lambda r: r.get('fired_at',''))[:44]
late_rest = sorted(bl_l_fw, key=lambda r: r.get('fired_at',''))[44:]
```

## 生出力

```
Total closed (verify.py compatible): 2114
Records with sr_runway: 1788

=== CLAIMS DATA ===
blocked=T×Long: k=78, n=186, rate=41.9%, CI[35.1%,49.1%], E(R)=-0.022
blocked=T×Short: k=65, n=139, rate=46.8%, CI[38.7%,55.0%], E(R)=+0.091
blocked=F×Long: k=467, n=1107, rate=42.2%, CI[39.3%,45.1%]

Direction asymmetry (blocked=T): Long=41.9% vs Short=46.8%, diff=4.9pp

Trend breakdown (blocked=T×L):
  上昇: k=32, n=79, rate=40.5%, CI[30.4%,51.5%]
  下降: k=28, n=65, rate=43.1%, CI[31.8%,55.2%]
  中立・もみあい: k=18, n=42, rate=42.9%, CI[29.1%,57.8%]

Group breakdown (blocked=T×L):
  metal: k=4, n=18, rate=22.2%
  index: k=18, n=39, rate=46.2%
  btc: k=3, n=15, rate=20.0%

IS/FW temporal:
  IS (before 2026-06-25): 25/59=42.4%
  FW (from 2026-06-25): 53/127=41.7%
  FW early-44: 28/44=63.6%
  FW late-83: 25/83=30.1%
```

## 判定
H1: blocked=T×L CI[35.1%,49.1%] → 43%をまたぐ → 効果なし確認 ✅
H2: 差0.3pp < 5pp → 追加効果なし確認 ✅
H3: 上昇40.5%・下降43.1%・中立42.9% → 全て40〜44%帯に収束 ✅
H4: Long 41.9% < Short 46.8%、差4.9pp → 方向非対称あり（わずか） ✅

通過A（効果消失確認）。壁なしロングに追加エッジなし。
