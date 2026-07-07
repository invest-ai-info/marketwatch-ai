# lab-033-analysis.md
## 仮説 #033: blocked=True×ショート 前向き崩落とロングとの方向非対称逆転
## 基準日: 2026-07-08

---

### 1. 仮説の採択理由

前向きトラッカー更新（2026-07-08）で`blocked=True×dir=short`（edge登録 2026-06-25）が
FWD N=22 / 4勝 / 18.2%・E(R)=-0.576 CI[-0.81~-0.34] と記録された。
IS（~2026-06-24）では 31/53=58.5% だったが、前向き22件でCI完全マイナス圏に突入。

同時期に`blocked=True×dir=long`はFWD 26/44=59.1% E(R)=+0.379 CI[+0.04~+0.72]と改善。

「壁あり（blocked=True）シグナルにおけるロング/ショートの方向非対称が前向きで完全逆転」という
優先度②（前向きで大きく動いた仮説）に該当する題材として採択。

---

### 2. 検証スクリプト

```python
import json, math, sys
sys.path.insert(0, '.')
from signal_lab_verify import closed, win, match, wilson, compute

with open('signals-log.json') as f:
    data = json.load(f)

def stats_with_er(data, filt, label, tp_r=1.333, sl_r=-1.0):
    rows = [d for d in data if closed(d) and match(d, filt)]
    n = len(rows)
    k = sum(1 for d in rows if win(d))
    if n == 0:
        print(f"  {label}: N=0")
        return k, n
    p = k/n
    ci = wilson(k, n)
    er = p * tp_r + (1-p) * sl_r
    se_er = (tp_r - sl_r) * math.sqrt(p*(1-p)/n)
    r_lo, r_hi = er - 1.96*se_er, er + 1.96*se_er
    print(f"  {label}: k={k}/N={n} win={p:.1%} CI=[{ci[0]:.1f}%,{ci[1]:.1f}%] E(R)={er:.3f} RCI=[{r_lo:.3f},{r_hi:.3f}]")
    return k, n
```

---

### 3. 生出力

#### 3-1. 全体統計（verify.py で確認可能）
```
blocked=True×Short:         k=35/N=75   win=46.7% CI=[35.8%,57.8%] E(R)=+0.089 RCI=[-0.175,+0.352]
blocked=True×Long:          k=51/N=103  win=49.5% CI=[40.1%,59.0%] E(R)=+0.155 RCI=[-0.070,+0.380]
blocked=True×Short×macd_dead: k=17/N=48 win=35.4% CI=[23.4%,49.6%] E(R)=-0.174 RCI=[-0.489,+0.142]
blocked=True×Short×ma_dead:   k=14/N=20 win=70.0% CI=[48.1%,85.5%] E(R)=+0.633 RCI=[+0.165,+1.102]
blocked=True×Short×metal:     k=9/N=10  win=90.0% CI=[59.6%,98.2%] E(R)=+1.100 RCI=[+0.666,+1.534]
blocked=True×Short×index:     k=4/N=14  win=28.6% CI=[11.7%,54.6%] E(R)=-0.333 RCI=[-0.886,+0.219]
blocked=True×Short×jpy_fx:    k=7/N=17  win=41.2% CI=[21.6%,64.0%] E(R)=-0.039 RCI=[-0.585,+0.506]
blocked=True×Short×other_fx:  k=12/N=24 win=50.0% CI=[31.4%,68.6%] E(R)=+0.166 RCI=[-0.300,+0.633]
```

#### 3-2. IS vs FWD（前向きトラッカー基準日: 2026-06-25）
```
blocked=True×Short IS(<2026-06-25):  k=31/N=53  win=58.5% CI=[45.1%,70.7%] E(R)=+0.365 RCI=[+0.055,+0.674]
blocked=True×Short FWD(>=2026-06-25): k=4/N=22  win=18.2% CI=[7.3%,38.5%]  E(R)=-0.576 RCI=[-0.952,-0.200]
blocked=True×Long IS(<2026-06-25):   k=25/N=59  win=42.4% CI=[30.6%,55.1%] E(R)=-0.011 RCI=[-0.306,+0.283]
blocked=True×Long FWD(>=2026-06-25): k=26/N=44  win=59.1% CI=[44.4%,72.3%] E(R)=+0.379 RCI=[+0.040,+0.718]
```

#### 3-3. FWD内シグナル別
```
FWD sig=macd_dead:           3/17=17.6%
FWD sig=ma_dead:             0/3=0.0%
FWD sig=first_pullback_short: 1/2=50.0%
```

#### 3-4. メタル×blocked=True×Short の消長
```
metal×blocked=True×short IS: N=8 件 → 8/8 が IS期間（すべて）
metal×blocked=True×short FWD: N=2 件のみ
  2026-06-26 GC=F first_pullback_short tp1  (win)
  2026-07-08 SI=F macd_dead tp1             (win)
```

IS=8件中全部が short×metal→主に IS期間に集中していたため、
blocked=True×Short の 9/10=90.0% のほとんどはこのIS件数による

#### 3-5. FWD 22件の詳細
```
2026-06-26 NQ=F      macd_dead             sl
2026-06-26 GC=F      first_pullback_short  tp1  ← win
2026-06-26 ES=F      macd_dead             sl
2026-06-26 NKD=F     macd_dead             sl
2026-06-27 NQ=F      ma_dead               sl
2026-06-27 BTC-USD   macd_dead             sl
2026-06-29 AUDJPY=X  macd_dead             sl
2026-06-30 USDJPY=X  macd_dead             sl
2026-07-01 BTC-USD   macd_dead             sl
2026-07-01 EURUSD=X  macd_dead             sl
2026-07-02 CL=F      macd_dead             sl
2026-07-02 NKD=F     macd_dead             tp1  ← win
2026-07-02 AUDUSD=X  macd_dead             sl
2026-07-02 ES=F      macd_dead             sl
2026-07-02 YM=F      macd_dead             sl
2026-07-02 GBPUSD=X  first_pullback_short  sl
2026-07-02 AUDUSD=X  macd_dead             sl
2026-07-02 NQ=F      ma_dead               sl
2026-07-02 AUDJPY=X  ma_dead               sl
2026-07-02 EURAUD=X  macd_dead             tp1  ← win
2026-07-03 GBPJPY=X  macd_dead             sl
2026-07-08 SI=F      macd_dead             tp1  ← win
```

---

### 4. Wilson CI 計算（主要統計の独立確認）

blocked=True×Short FWD (k=4, n=22):
  p = 4/22 = 0.1818
  z = 1.96
  Wilson CI = [7.3%, 38.5%]  ← 43%損益分岐を完全に下回る

blocked=True×Long FWD (k=26, n=44):
  p = 26/44 = 0.5909
  Wilson CI = [44.4%, 72.3%]  ← 損益分岐43%を大きく上回る

---

### 5. 交絡解析の結論

IS期間(53件)の 31勝=58.5% は metal×blocked=True×short(8件)の高勝率が押し上げた
→ metal IS: 8/10=80%相当（tracker種別を考慮すると IS で metal が全期間の 8割の発火）

FWDでは：
- metal×blocked=True×short: 2件のみ（2/2=100%、ただしN=2はノイズ）
- macd_dead×blocked=True×short: 17件中3勝=17.6%（FWD主体がこれに移行）
- ma_dead×blocked=True×short: 3件中0勝=0.0%

IS時代の "engine" だった metal が消え、
残ったmacd_dead×blocked=True×short（FWD 17.6%）がFWD全体の勝率を決めた。

---

### 6. E(R)の計算方法（注記）

r_multiple フィールドが signals-log では None のため、
機械的 E(R) = 勝率 × (+1.333) + 負率 × (-1.000) で計算。
TP1 = ATR×2.0 / SL = ATR×1.5 の比率より R_win ≈ 1.333。
tracker の -0.576 と一致（4/22 × 1.333 + 18/22 × (-1.0) = 0.242 - 0.818 = -0.576）。

---

### 7. 結論

**仮説「blocked=True×Short には同方向のエッジがある」は前向きで棄却方向**
- IS 58.5%（エッジあり）→ FWD 18.2%（エッジなし・損失圏）
- IS の高勝率は metal×blocked=True×short の偽陽性が主因
- blocked=True はロング専用のエッジ（FWD 59.1% RCI全域プラス）
- ショートでは blocked=True は活用せず、むしろ回避シグナルになりつつある

---

*labnotes 自動生成: 2026-07-08 signal-lab-daily #033*
