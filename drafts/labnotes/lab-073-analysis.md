# Lab Note #073 — trend=上昇×reversalL 前向きN=205の解剖

**基準日**: 2026-08-19 (JST)  
**仮説**: 上昇トレンドで逆張り買い（reversal_long=True）は前向きN=205まで蓄積したが、  
RSI(67%)とBB(42%)、指数(33%)とJPY(57%)の二極化が拡大している。

---

## 検証スクリプト (Python)

```python
import json, math

with open('signals-log.json', 'r') as f:
    data = json.load(f)

signals = data if isinstance(data, list) else data.get('signals', [])

REV = {"rsi_oversold_bounce", "bb_lower_touch"}
GROUPS = {
    "metal": {"GC=F", "SI=F"}, 
    "index": {"NKD=F", "ES=F", "NQ=F", "YM=F", "^FTSE"},
    "jpy_fx": {"USDJPY=X", "EURJPY=X", "GBPJPY=X", "AUDJPY=X"},
    "other_fx": {"EURUSD=X", "GBPUSD=X", "AUDUSD=X", "EURAUD=X", "GBPAUD=X"},
    "btc": {"BTC-USD"}, "oil": {"CL=F"},
}

def get_trend(d):
    ta = d.get("trend_alignment")
    return ta["higher_tf_trend"] if isinstance(ta, dict) and ta.get("higher_tf_trend") else "unknown"

def grp(d):
    for g, tickers in GROUPS.items():
        if d.get('ticker') in tickers: return g
    return 'other'

def closed(d): return d.get("outcome") in ("tp1", "tp2", "sl")
def win(d): return d.get("outcome") in ("tp1", "tp2")
def is_revL(d): return "ロング" in (d.get("direction") or "") and d.get('primary_signal') in REV

def get_fire(d): return str(d.get('fired_at', ''))

def wilson_ci(k, n, z=1.96):
    if n == 0: return 0, 0
    p = k/n
    denom = 1 + z*z/n
    nl = p + z*z/(2*n) - z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))
    nh = p + z*z/(2*n) + z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))
    return max(0, nl/denom), min(1, nh/denom)

FWD_START = '2026-06-22'
P3_START = '2026-08-03'

is_target = lambda d: get_trend(d) == '上昇' and is_revL(d) and closed(d)
all_t = [d for d in signals if is_target(d)]
fwd = [d for d in all_t if get_fire(d) >= FWD_START]
is_only = [d for d in all_t if get_fire(d) < FWD_START]
p3 = [d for d in fwd if get_fire(d) >= P3_START]
```

---

## 生出力（全期間・IS・FWD）

```
=== trend=上昇×reversalL (IS/FWD by fired_at) ===
全期間: N=306, k=152, 49.7%, CI[44.1%,55.2%], E(R)=+0.239
IS (fired<2026-06-22): N=101, k=54, 53.5%, E(R)=+0.371
FWD (fired>=2026-06-22): N=205, k=98, 47.8%, CI[41.1%,54.6%], E(R)=+0.173

[tracker 補正後] N=204, 48%, E(R)=+0.12, CI[-0.05~+0.30] (cluster補正SEでCI下限が-0.05に転落)

#047 boundary (N=102): 2026-07-21
#062 boundary (N=148): 2026-07-31

Sub-period breakdown (sorted by fired_at):
  P1(N≤102, Jun22-Jul21): N=102, k=51, 50.0%, E(R)=+0.250
  P2(N=103-148, Jul21-Jul31): N=46, k=24, 52.2%, E(R)=+0.326
  P3(N=149+, Aug03-Aug19): N=57, k=23, 40.4%, E(R)=-0.088  ← 失速!

=== By signal (FWD) ===
  RSI: N=46, k=31, 67.4%, CI[53.0%,79.1%], E(R)=+0.859
  BB: N=159, k=67, 42.1%, CI[34.7%,49.9%], E(R)=-0.025

=== By group (FWD) ===
  index: N=60, k=20, 33.3%, CI[22.7%,45.9%], E(R)=-0.333
  jpy_fx: N=58, k=33, 56.9%, CI[44.1%,68.8%], E(R)=+0.491
  other_fx: N=53, k=28, 52.8%, CI[39.7%,65.6%], E(R)=+0.349
  metal: N=11, k=5, 45.5%, E(R)=+0.091
  btc: N=12, k=6, 50.0%, E(R)=+0.250
  oil: N=10, k=6, 60.0%, E(R)=+0.600

=== P3 (N=57, fired>=2026-08-03) breakdown ===
  P3全体: N=57, k=23, 40.4%, CI[28.6%,53.3%]
  P3 RSI: N=13, k=8, 61.5%, E(R)=+0.654
  P3 BB: N=44, k=15, 34.1%, E(R)=-0.307
  P3 index: N=27, k=7, 25.9%, E(R)=-0.593  ← 急落!
  P3 jpy_fx: N=12, k=10, 83.3%, E(R)=+1.417  ← 急上昇!
  P3 other_fx: N=8, k=3, 37.5%, E(R)=-0.188
  P3 1h: N=40, k=16, 40.0%, E(R)=-0.100
  P3 4h: N=14, k=4, 28.6%, E(R)=-0.500

=== IS by signal ===
  IS RSI: N=25, k=13, 52.0%, E(R)=+0.320
  IS BB: N=76, k=41, 53.9%, E(R)=+0.388
```

---

## 解釈まとめ

- FWD全体 47.8% (N=205): tracker cluster補正後 CI[-0.05~+0.30]。CI下限が初めてゼロをわずかに割った（降格ルール1回目の警戒ライン）
- RSI(67.4%)とBB(42.1%)の差は25.3pp。IS期は差2%だったのが FWD で大きく開いた
- BB主体 (N=159/205 = 77.6%) が全体を引き下げている（BB alone E(R)≈-0.025）
- 指数グループ FWD 33.3%（CI下限22.7%）: 全FWD中で最も低い、損益分岐を大きく割る
- JPY FWD 56.9%（CI下限44.1%）: 43%を超えており健全
- P3 (N=57, 2026-08-03以降) での指数 25.9%が最重要警告シグナル
- 仮説の棄却とは言えないが「何も考えずに上昇×逆張り買い」は危険  
  → 指数を避けてJPY/other_fxに絞り、BBよりRSIを選ぶことでエッジを維持できる

## 交絡点検
- 指数比率: FWD 60/205 = 29.3%（IS 42/101=41.6%より低い = 指数が減っているのに指数の勝率が下がっている）
- BB比率: FWD 159/205 = 77.6%（IS 76/101=75.2%とほぼ同じ = 構成変化は少ない）
- → 指数の勝率低下は比率変化ではなく実勝率の劣化
- → BB の 42.1% (FWD) vs RSI 67.4% (FWD) の差は IS (53.9% vs 52.0%) の 2pp 差から 25pp 差に拡大 = 純粋な性能乖離

## FDR/Wilson CI
- H1: RSI FWD CI下限53.0%≥43% かつ N=46≥20 ✅ (棄却:RSIは有効)
- H2: BB FWD CI[34.7%,49.9%] が43%をまたぐ かつ N=159≥20 ✅ (BBは無エッジ確認)
- H3: 指数 FWD CI上限45.9%<43%? → 45.9%>43% ✗ (CI上限が超えているため棄却確認未達)
  ただし CI下限22.7%<43% と E(R)=-0.333 から「有望な棄却方向」
- H4: jpy_fx FWD CI下限44.1%>43% ✅ (JPYは有効を示唆)

---

*作成: 2026-08-19 JST*
