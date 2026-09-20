# AIシグナル研究日誌 #105 — 分析スクリプト・生出力

**基準日**: 2026-09-21  
**仮説**: RSI売られすぎ（≤30）での逆張りロングは、RSI売られすぎ以外の逆張りロングより有意に高い勝率・期待値を示すか

---

## 実行スクリプト

```python
import json, math
from signal_lab_verify import closed, win, match, wilson, rsi_band_of

with open('signals-log.json') as f:
    logs = json.load(f)

def ev_r(data):
    rs = []
    for d in data:
        o = d.get('outcome')
        if o == 'tp2': rs.append(3.0)
        elif o == 'tp1': rs.append(2.0)
        elif o == 'sl': rs.append(-1.5)
    return sum(rs)/len(rs) if rs else 0.0

closed_all = [d for d in logs if closed(d)]
N_all = len(closed_all)
k_all = sum(1 for d in closed_all if win(d))
# ベース
# N=4583, wr=43.1%, EV=+0.010R

# rsi_os×reversalL
f = {"rsi_band": "os", "reversal_long": True}
m = [d for d in closed_all if match(d, f)]
# N=407, k=205, wr=50.4%, EV=+0.263, CI=[45.5%,55.2%]

# trend別
# trend=下降: N=160, k=73, wr=45.6%, EV=+0.097, CI=[38.1%,53.4%]
# trend=中立: N=159, k=74, wr=46.5%, EV=+0.129, CI=[39.0%,54.3%]
# trend=上昇: N=87,  k=57, wr=65.5%, EV=+0.793, CI=[55.1%,74.7%]

# tf別
# 1h: N=254, k=119, wr=46.9%, EV=+0.140, CI=[40.8%,53.0%]
# 4h: N=140, k=75,  wr=53.6%, EV=+0.375, CI=[45.3%,61.6%]

# group別
# jpy_fx: N=104, k=39, wr=37.5%, EV=-0.188, CI=[28.8%,47.1%]  ← 損益分岐を下回る
# other_fx: N=103, k=59, wr=57.3%, EV=+0.505, CI=[47.6%,66.4%]
# metal:    N=51,  k=28, wr=54.9%, EV=+0.422, CI=[41.4%,67.7%]
# index:    N=108, k=60, wr=55.6%, EV=+0.444, CI=[46.2%,64.6%]
# btc:      N=25,  k=9,  wr=36.0%, EV=-0.240, CI=[20.2%,55.5%]
# oil:      N=16,  k=10, wr=62.5%, EV=+0.688, CI=[38.6%,81.5%]

# 対照群（reversalL×rsi_not_os）
# N=988, k=427, wr=43.2%, EV=+0.013, CI=[40.2%,46.3%]

# 全reversalL
# N=1395, k=632, wr=45.3%, EV=+0.086, CI=[42.7%,47.9%]
```

---

## 生出力

```
ベース: N=4583, wr=43.1%, EV=0.010

=== RSI売られすぎ逆張り買い (rsi_os×reversalL) ===
N=407, k=205, wr=50.4%, EV=0.263, CI=[45.5%,55.2%]
PASS条件: CI下限45.5%>43%? True / N≥30? True
  trend=下降: N=160, k=73, wr=45.6%, EV=0.097, CI=[38.1%,53.4%]
  trend=中立・もみあい: N=159, k=74, wr=46.5%, EV=0.129, CI=[39.0%,54.3%]
  trend=上昇: N=87, k=57, wr=65.5%, EV=0.793, CI=[55.1%,74.7%]
  tf=1h: N=254, k=119, wr=46.9%, EV=0.140, CI=[40.8%,53.0%]
  tf=4h: N=140, k=75, wr=53.6%, EV=0.375, CI=[45.3%,61.6%]
  grp=jpy_fx: N=104, k=39, wr=37.5%, EV=-0.188, CI=[28.8%,47.1%]
  grp=other_fx: N=103, k=59, wr=57.3%, EV=0.505, CI=[47.6%,66.4%]
  grp=metal: N=51, k=28, wr=54.9%, EV=0.422, CI=[41.4%,67.7%]
  grp=index: N=108, k=60, wr=55.6%, EV=0.444, CI=[46.2%,64.6%]
  grp=btc: N=25, k=9, wr=36.0%, EV=-0.240, CI=[20.2%,55.5%]
  grp=oil: N=16, k=10, wr=62.5%, EV=0.688, CI=[38.6%,81.5%]

対照群 reversalL×rsi_not_os: N=988, k=427, wr=43.2%, EV=0.013, CI=[40.2%,46.3%]
全reversalL: N=1395, k=632, wr=45.3%, EV=0.086, CI=[42.7%,47.9%]

上昇×rsi_os×reversalL グループ別:
  grp=jpy_fx: N=20, k=12, wr=60.0%, CI=[38.7%,78.1%]
  grp=other_fx: N=17, k=12, wr=70.6%, CI=[46.9%,86.7%]
  grp=metal: N=7, k=5, wr=71.4%, CI=[35.9%,91.8%]
  grp=index: N=35, k=21, wr=60.0%, CI=[43.6%,74.4%]
```

---

## スイープ結果（2026-09-21）

- FDR通過: 0本（薄い日）
- 前向きトラッカー更新: 昇格・反証変化なし
- trend=上昇×reversalL（tracker）: ✅昇格継続（150/315, 48%, EV=+0.11, CI[-0.04~+0.26]）

## 判定

**✅ 通過A**（主仮説）
- CI下限 45.5% > 43%（損益分岐）✅  
- N=407 ≥ 30 ✅  
- EV=+0.263R（全体平均+0.010Rを大きく上回る）

**交絡発見（探索的）**:
- 上昇トレンド×rsi_os×reversalL: 65.5%（CI全区間>43%）― 特に有力
- JPYクロス×rsi_os×reversalL: 37.5%（損益分岐43%を下回る）― 逆効果
- BTC×rsi_os×reversalL: 36.0%（小N・信頼区間広い）

**前向きトラッカー観察**（既存仮説 `売られすぎ逆張り買い(rsi_oversold_bounce・全足)`）:
- FWD 187/359, 52%, EV=+0.215, CI[+0.04~+0.39] → CI全区間プラス（🟡蓄積中）
