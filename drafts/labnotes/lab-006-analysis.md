# 研究日誌 #006 — labnotes

## 仮説
「blocked=True の優位性はトレンド相場（上昇/下降）に限定され、中立・もみあいでは失われる（逆転する可能性あり）」

事前合否基準:
- ①下降×blocked=True の Wilson CI下限 ≥ 43%（下降でも壁が機能する）
- ②中立×blocked=True の勝率 < 43%（もみあいで効果消失）
→ 両条件満たせば「トレンド依存フィルター」として通過A

---

## 分析スクリプト（全文）

```python
import json, math

data = json.load(open('signals-log.json', encoding='utf-8-sig'))

def closed(d): return d.get('outcome') in ('tp1','tp2','sl')
def win(d): return d.get('outcome') in ('tp1','tp2')
def wilson(k,n,z=1.96):
    if n==0: return (0,100)
    p=k/n; den=1+z*z/n; c=(p+z*z/(2*n))/den; pm=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return (max(0,c-pm)*100, min(1,c+pm)*100)

GROUPS={'metal':{'GC=F','SI=F'},'index':{'NKD=F','ES=F','NQ=F','YM=F','^FTSE'},
        'jpy_fx':{'USDJPY=X','EURJPY=X','GBPJPY=X','AUDJPY=X'},
        'other_fx':{'EURUSD=X','GBPUSD=X','AUDUSD=X','EURAUD=X','GBPAUD=X'},
        'btc':{'BTC-USD'},'oil':{'CL=F'}}

def get_group(d):
    t=d.get('ticker','')
    for g,tks in GROUPS.items():
        if t in tks: return g
    return 'other'

def get_trend(d):
    ta=d.get('trend_alignment')
    if isinstance(ta,dict) and ta.get('higher_tf_trend'): return ta['higher_tf_trend']
    return 'unknown'

def is_long(d): return 'ロング' in (d.get('direction') or '')
def is_short(d): return 'ショート' in (d.get('direction') or '')

closed_data = [d for d in data if closed(d)]
sr_closed = [d for d in closed_data if isinstance(d.get('sr_runway'),dict)]
bt = [d for d in sr_closed if d['sr_runway']['blocked']==True]
bf = [d for d in sr_closed if d['sr_runway']['blocked']==False]

print(f'Total closed: {len(closed_data)}')
print(f'sr_runway有り (closed): {len(sr_closed)}')
print(f'blocked=True: {len(bt)}, blocked=False: {len(bf)}')
print()

# 全体
for label, rows in [('blocked=True all', bt), ('blocked=False all', bf)]:
    k=sum(1 for d in rows if win(d)); n=len(rows)
    lo,hi=wilson(k,n)
    print(f'{label}: {k}/{n} = {k/n*100:.1f}%  CI[{lo:.1f}~{hi:.1f}]')
print()

# blocked × trend
print('=== blocked=True × trend ===')
for tr in ['上昇','下降','中立・もみあい','unknown']:
    rows=[d for d in bt if get_trend(d)==tr]
    if not rows: continue
    k=sum(1 for d in rows if win(d)); n=len(rows)
    lo,hi=wilson(k,n)
    print(f'  {tr}: {k}/{n} = {k/n*100:.1f}%  CI[{lo:.1f}~{hi:.1f}]')

print()
print('=== blocked=False × trend ===')
for tr in ['上昇','下降','中立・もみあい','unknown']:
    rows=[d for d in bf if get_trend(d)==tr]
    if not rows: continue
    k=sum(1 for d in rows if win(d)); n=len(rows)
    lo,hi=wilson(k,n)
    print(f'  {tr}: {k}/{n} = {k/n*100:.1f}%  CI[{lo:.1f}~{hi:.1f}]')

print()
# blocked=True トレンド合算
k_trend, n_trend = 7+13, 11+20
lo,hi = wilson(k_trend, n_trend)
print(f'blocked=T トレンド合算(上昇+下降): {k_trend}/{n_trend} = {k_trend/n_trend*100:.1f}%  CI[{lo:.1f}~{hi:.1f}]')

print()
# 期待値
def er(wr): return wr*1.33 - (1-wr)*1.0
for label,(k,n) in [
    ('blocked=T all', (22,41)), ('blocked=T 上昇', (7,11)),
    ('blocked=T 下降', (13,20)), ('blocked=T 中立', (2,10)),
    ('blocked=F all', (111,285)),
]:
    wr=k/n; print(f'E(R) {label}: {er(wr):+.3f}R  (勝率{wr*100:.1f}%)')

print()
# blocked × group
print('=== blocked=True × group ===')
for g in ['index','jpy_fx','other_fx','metal','btc','oil']:
    rows=[d for d in bt if get_group(d)==g]
    if not rows: continue
    k=sum(1 for d in rows if win(d)); n=len(rows)
    lo,hi=wilson(k,n)
    print(f'  {g:12}: {k}/{n} = {k/n*100:.1f}%  CI[{lo:.1f}~{hi:.1f}]')
print()
print('=== blocked=False × group ===')
for g in ['index','jpy_fx','other_fx','metal','btc','oil']:
    rows=[d for d in bf if get_group(d)==g]
    if not rows: continue
    k=sum(1 for d in rows if win(d)); n=len(rows)
    lo,hi=wilson(k,n)
    print(f'  {g:12}: {k}/{n} = {k/n*100:.1f}%  CI[{lo:.1f}~{hi:.1f}]')

print()
# blocked × direction
print('=== blocked=True × direction ===')
for dr,fn in [('long',is_long),('short',is_short)]:
    rows=[d for d in bt if fn(d)]
    k=sum(1 for d in rows if win(d)); n=len(rows)
    lo,hi=wilson(k,n)
    print(f'  {dr}: {k}/{n} = {(k/n*100 if n else 0):.1f}%  CI[{lo:.1f}~{hi:.1f}]')
```

---

## 生出力

```
Total closed: 652
sr_runway有り (closed): 326
blocked=True: 41, blocked=False: 285

blocked=True all: 22/41 = 53.7%  CI[38.7~67.9]
blocked=False all: 111/285 = 38.9%  CI[33.5~44.7]

=== blocked=True × trend ===
  上昇: 7/11 = 63.6%  CI[35.4~84.8]
  下降: 13/20 = 65.0%  CI[43.3~81.9]
  中立・もみあい: 2/10 = 20.0%  CI[5.7~51.0]

=== blocked=False × trend ===
  上昇: 27/68 = 39.7%  CI[28.9~51.6]
  下降: 48/115 = 41.7%  CI[33.1~50.9]
  中立・もみあい: 36/102 = 35.3%  CI[26.7~44.9]

blocked=T トレンド合算(上昇+下降): 20/31 = 64.5%  CI[46.9~78.9]

E(R) blocked=T all:  +0.250R  (勝率53.7%)
E(R) blocked=T 上昇: +0.483R  (勝率63.6%)
E(R) blocked=T 下降: +0.515R  (勝率65.0%)
E(R) blocked=T 中立: -0.534R  (勝率20.0%)
E(R) blocked=F all:  -0.093R  (勝率38.9%)

=== blocked=True × group ===
  index       : 6/8 = 75.0%  CI[40.9~92.9]
  jpy_fx      : 1/5 = 20.0%  CI[3.6~62.4]
  other_fx    : 10/15 = 66.7%  CI[41.7~84.8]
  metal       : 4/8 = 50.0%  CI[21.5~78.5]
  btc         : 0/3 = 0.0%  CI[0.0~56.2]
  oil         : 1/2 = 50.0%  CI[9.5~90.5]

=== blocked=False × group ===
  index       : 40/89 = 44.9%  CI[35.0~55.2]
  jpy_fx      : 18/58 = 31.0%  CI[20.6~43.8]
  other_fx    : 30/64 = 46.9%  CI[35.2~58.9]
  metal       : 9/50 = 18.0%  CI[9.8~30.3]
  btc         : 5/12 = 41.7%  CI[19.3~68.0]
  oil         : 9/12 = 75.0%  CI[46.8~91.1]

=== blocked=True × direction ===
  long:  10/18 = 55.6%  CI[33.7~75.4]
  short: 12/23 = 52.2%  CI[33.0~70.8]
```

---

## 交絡点検チェックリスト

1. **blocked=True の件数偏り確認**: N=41は#005と同数（同データセット）。トレンド内訳は上昇11/下降20/中立10件。
2. **trend フィールドの欠損**: blocked=True でtrend=unknownは0件。全41件にtrend情報あり（良好）。
3. **方向（long/short）交絡**: blocked=T×long 55.6% vs blocked=T×short 52.2%—差は小さく方向依存ではない。
4. **グループ交絡**: blocked=Tの主要グループはother_fx(15件)+index(8件)+metal(8件)。other_fxとindexは比較的高いが、グループ構成に偏り。
5. **サンプル期間**: 同じ3週間データ（2026-05-20〜06-13）。中立10件は少ないためブレ幅大（CI[5.7~51.0%]）。
6. **「壁あり」がなぜトレンド相場で機能するか**: 解釈として、トレンド相場では動きが一方向に強くS/R壁を突き抜ける力がある。一方もみあいでは壁が本当の障壁として機能しTP1到達を妨げる。

## 前向きトラッカー更新値

| ID | 現在値（2026-06-13） |
|----|---------------------|
| f | 全逆張りL: 41.9% N=284 CI[36.3%~47.7%]（前回と同値） |
| g | 指数×逆張りL: 51.5% N=66 CI[39.7%~63.2%]（前回と同値） |
| h | 他FX×逆張りL: 55.0% N=60 CI[42.5%~66.9%]（前回と同値） |
