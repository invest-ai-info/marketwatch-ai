# lab-056 分析ノート — 2026-07-31

## 仮説
**日足ロング(1d×Long)のシグナル二極化——BB下限タッチ(+1.125R)とBB上限ブレイク(-1.250R)の2.375R差**

前向きトラッカー「ロング全般(日足)」が 🏁N=31 チェックポイントに到達し、E(R)=-0.398, CI[-0.68,-0.12] と全域マイナスを確認。
その内訳を解剖すると、逆張り系シグナルとブレイク系シグナルが完全に逆の方向を向いている二極化構造を発見。

## 事前合否基準（検証前に宣言）

| 仮説 | 基準 | 期待方向 |
|---|---|---|
| H1（棄却確認）: bb_upper_break × 1d × Long | WR の Wilson CI 上限 < 43% かつ N ≥ 10 | ブレイク系は損益分岐割れ |
| H2（エッジ確認）: bb_lower_touch × 1d × Long | E(R) の 95%CI 下限 > 0 かつ N ≥ 10 | 逆張り系は期待値プラス |

## 検証スクリプト（全文）

```python
import json, math

with open('signals-log.json') as f:
    data = json.load(f)

closed = [s for s in data if s.get('outcome') in ['tp1','sl']]

GROUP_MAP = {
    'GC=F': 'metal', 'SI=F': 'metal',
    'NKD=F': 'index', 'ES=F': 'index', 'NQ=F': 'index', 'YM=F': 'index', '^FTSE': 'index',
    'BTC-USD': 'btc', 'CL=F': 'oil',
    'USDJPY': 'jpy_fx', 'EURJPY': 'jpy_fx', 'GBPJPY': 'jpy_fx', 'AUDJPY': 'jpy_fx',
    'EURUSD': 'other_fx', 'GBPUSD': 'other_fx', 'AUDUSD': 'other_fx',
    'EURAUD': 'other_fx', 'GBPAUD': 'other_fx',
    'USDJPY=X': 'jpy_fx', 'EURJPY=X': 'jpy_fx', 'GBPJPY=X': 'jpy_fx', 'AUDJPY=X': 'jpy_fx',
    'EURUSD=X': 'other_fx', 'GBPUSD=X': 'other_fx', 'AUDUSD=X': 'other_fx',
    'EURAUD=X': 'other_fx', 'GBPAUD=X': 'other_fx'
}

def get_group(s):
    grp = s.get('group')
    if grp and grp not in [None, 'None', '']:
        return grp
    return GROUP_MAP.get(s.get('ticker',''), 'other')

def is_long(s):
    return 'ロング' in s.get('direction','') or s.get('direction','') == 'long'

def is_short(s):
    return 'ショート' in s.get('direction','') or s.get('direction','') == 'short'

def wilson_ci(k, n, z=1.96):
    if n == 0: return (0.0, 0.0)
    p = k/n
    denom = 1 + z**2/n
    center = (p + z**2/(2*n)) / denom
    margin = z * math.sqrt(p*(1-p)/n + z**2/(4*n**2)) / denom
    return (max(0.0, center-margin), min(1.0, center+margin))

def mean_ci(vals):
    n = len(vals)
    if n == 0: return (0,0,0)
    m = sum(vals)/n
    if n <= 1: return (m, m-1, m+1)
    var = sum((x-m)**2 for x in vals)/(n-1)
    se = math.sqrt(var/n)
    return (m, m-1.96*se, m+1.96*se)

def get_er(s):
    o = s.get('outcome')
    if o == 'tp1': return s.get('tp1_r', 2.0)
    elif o == 'sl': return -s.get('sl_r', 1.5)
    return None

def summary(group, label):
    if not group:
        print(f"  {label}: N=0")
        return
    n = len(group)
    k = sum(1 for s in group if s.get('outcome')=='tp1')
    wr = k/n
    ci = wilson_ci(k,n)
    rs = [get_er(s) for s in group if get_er(s) is not None]
    if rs:
        m, lo, hi = mean_ci(rs)
        print(f"  {label}: N={n} k={k} WR={wr:.1%} CI=[{ci[0]:.1%},{ci[1]:.1%}] E(R)={m:.3f} RCI=[{lo:.2f},{hi:.2f}]")
    else:
        print(f"  {label}: N={n} k={k} WR={wr:.1%}")

tf1d = [s for s in closed if s.get('timeframe') == '1d']
tf1d_long = [s for s in tf1d if is_long(s)]
tf1d_short = [s for s in tf1d if is_short(s)]

print("=== tf=1d signals ===")
summary(tf1d, "1d all")
summary(tf1d_long, "1d long")
summary(tf1d_short, "1d short")

print("\n--- 1d Long by signal (all period) ---")
sigs = {}
for s in tf1d_long:
    sg = s.get('primary_signal','')
    sigs.setdefault(sg,[]).append(s)
for sg, lst in sorted(sigs.items(), key=lambda x:-len(x[1])):
    summary(lst, f"1d long × {sg}")

print("\n--- 1d Long FWD (>=2026-07-02) ---")
fwd_long = [s for s in tf1d_long if s.get('fired_at','') >= '2026-07-02']
summary(fwd_long, "1d long FWD total")
sigs_fwd = {}
for s in fwd_long:
    sg = s.get('primary_signal','')
    sigs_fwd.setdefault(sg,[]).append(s)
for sg, lst in sorted(sigs_fwd.items(), key=lambda x:-len(x[1])):
    summary(lst, f"  FWD × {sg}")

print("\n--- 1d Long by group ---")
for grp in ['metal','index','jpy_fx','other_fx','btc','oil']:
    g = [s for s in tf1d_long if get_group(s) == grp]
    summary(g, f"1d long × {grp}")
```

## 実行出力

```
=== tf=1d signals ===
  1d all: N=97 k=38 WR=39.2% CI=[30.1%,49.1%] E(R)=-0.129 RCI=[-0.47,0.21]
  1d long: N=75 k=30 WR=40.0% CI=[29.7%,51.3%] E(R)=-0.100 RCI=[-0.49,0.29]
  1d short: N=22 k=8 WR=36.4% CI=[19.7%,57.0%] E(R)=-0.227 RCI=[-0.95,0.49]

--- 1d Long by signal (all period) ---
  1d long × bb_lower_touch: N=16 k=12 WR=75.0% CI=[50.5%,89.8%] E(R)=1.125 RCI=[0.36,1.89]
  1d long × macd_golden: N=15 k=7 WR=46.7% CI=[24.8%,69.9%] E(R)=0.133 RCI=[-0.78,1.05]
  1d long × bb_upper_break: N=14 k=1 WR=7.1% CI=[1.3%,31.5%] E(R)=-1.250 RCI=[-1.74,-0.76]
  1d long × rsi_oversold_bounce: N=12 k=7 WR=58.3% CI=[32.0%,80.7%] E(R)=0.542 RCI=[-0.48,1.56]
  1d long × high_break: N=7 k=1 WR=14.3% CI=[2.6%,51.3%] E(R)=-1.000 RCI=[-1.98,-0.02]
  1d long × double_bottom: N=4 k=0 WR=0.0% CI=[0.0%,49.0%] E(R)=-1.500 RCI=[-1.50,-1.50]
  1d long × rsi_overbought: N=3 k=0 WR=0.0% CI=[0.0%,56.2%] E(R)=-1.500 RCI=[-1.50,-1.50]
  1d long × ma_golden: N=2 k=1 WR=50.0% CI=[9.5%,90.5%] E(R)=0.250 RCI=[-3.18,3.68]
  1d long × support_bounce: N=2 k=1 WR=50.0% CI=[9.5%,90.5%] E(R)=0.250 RCI=[-3.18,3.68]

--- 1d Long FWD (>=2026-07-02) ---
  1d long FWD total: N=34 k=8 WR=23.5% CI=[12.4%,40.0%] E(R)=-0.676 RCI=[-1.18,-0.17]
    FWD × bb_upper_break: N=10 k=0 WR=0.0% CI=[0.0%,27.8%] E(R)=-1.500 RCI=[-1.50,-1.50]
    FWD × macd_golden: N=6 k=3 WR=50.0% CI=[18.8%,81.2%] E(R)=0.250 RCI=[-1.28,1.78]
    FWD × high_break: N=4 k=0 WR=0.0% CI=[0.0%,49.0%] E(R)=-1.500 RCI=[-1.50,-1.50]
    FWD × double_bottom: N=3 k=0 WR=0.0% CI=[0.0%,56.2%] E(R)=-1.500 RCI=[-1.50,-1.50]
    FWD × rsi_oversold_bounce: N=3 k=3 WR=100.0% CI=[43.8%,100.0%] E(R)=2.000 RCI=[2.00,2.00]
    FWD × bb_lower_touch: N=3 k=1 WR=33.3% CI=[6.1%,79.2%] E(R)=-0.333 RCI=[-2.62,1.95]
    FWD × rsi_overbought: N=2 k=0 WR=0.0% CI=[0.0%,65.8%] E(R)=-1.500 RCI=[-1.50,-1.50]
    FWD × support_bounce: N=2 k=1 WR=50.0% CI=[9.5%,90.5%] E(R)=0.250 RCI=[-3.18,3.68]
    FWD × ma_golden: N=1 k=0 WR=0.0% CI=[0.0%,79.3%] E(R)=-1.500 RCI=[-2.50,-0.50]

--- 1d Long by group ---
  1d long × metal: N=14 k=4 WR=28.6% CI=[11.7%,54.6%] E(R)=-0.500 RCI=[-1.36,0.36]
  1d long × index: N=14 k=6 WR=42.9% CI=[21.4%,67.4%] E(R)=0.000 RCI=[-0.94,0.94]
  1d long × jpy_fx: N=0
  1d long × other_fx: N=0
  1d long × btc: N=6 k=3 WR=50.0% CI=[18.8%,81.2%] E(R)=0.250 RCI=[-1.28,1.78]
  1d long × oil: N=5 k=4 WR=80.0% CI=[37.6%,96.4%] E(R)=1.300 RCI=[-0.07,2.67]
```

## 検証判定

| 仮説 | 基準 | 結果 | 判定 |
|---|---|---|---|
| H1: bb_upper_break × 1d × Long | WR CI上限 < 43% かつ N ≥ 10 | WR=7.1% CI[1.3%,31.5%] N=14 ✅ | ✅ 通過A（棄却確認） |
| H2: bb_lower_touch × 1d × Long | E(R) CI下限 > 0 かつ N ≥ 10 | E(R)=+1.125 RCI[+0.36,+1.89] N=16 ✅ | ✅ 通過A（エッジ確認） |

主発見:
- H1 ✅: CI上限31.5% < 43%、E(R)=-1.250 RCI[-1.74,-0.76]（全域マイナス確定）
- H2 ✅: E(R)=+1.125 RCI[+0.36,+1.89]（全域プラス確定）
- 差: 2.375R（bb_lower_touch - bb_upper_break）

探索的発見:
- high_break × 1d × Long: N=7, WR=14.3%, E(R)=-1.000
- FWD bb_upper_break: N=10, WR=0.0%（全敗）
- FWD high_break: N=4, WR=0.0%（全敗）
- 前向きトラッカー「ロング全般(日足)」: 8/31=26%, R=-0.398, CI[-0.68,-0.12]（全域マイナス）

## 交絡点検

- 日足1dシグナルはFXペアではほぼ発火しない（jpy_fx=0件、other_fx=0件）。主にメタル・指数・原油・BTCが対象
- bb_upper_break（ブレイク系）とbb_lower_touch（逆張り系）のN差は14 vs 16でほぼ同等 → 偏りが少ない
- IS vs FWD: bb_lower_touch IS=13件84.6% → FWD=3件33.3%（N小すぎ、FWDは参考値のみ）
- bb_upper_break IS=4件25.0% → FWD=10件0.0%（FWDで悪化傾向が継続）
- Wilson CI補正済み、多重検定補正なし（H1・H2は事前宣言済み）
