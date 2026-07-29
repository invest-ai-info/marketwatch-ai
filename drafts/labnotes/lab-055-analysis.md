# Lab-055 分析ノート — other_fx×逆張り買い gate 前向きN=87 ⛔反証接近
## 基準日: 2026-07-30 (JST)

---

## 検証スクリプト (反実仮想集計)

```python
import json, math
from collections import Counter

with open("signals-log.json") as f:
    data = json.load(f)

GROUPS = {
    "metal":    {"GC=F", "SI=F"},
    "index":    {"NKD=F", "ES=F", "NQ=F", "YM=F", "^FTSE"},
    "jpy_fx":   {"USDJPY=X", "EURJPY=X", "GBPJPY=X", "AUDJPY=X"},
    "other_fx": {"EURUSD=X", "GBPUSD=X", "AUDUSD=X", "EURAUD=X", "GBPAUD=X"},
    "btc":      {"BTC-USD"},
    "oil":      {"CL=F"},
}
REV_SIGNALS = {"rsi_oversold_bounce", "bb_lower_touch"}
REGISTER_DATE = "2026-07-02"

def group_of(s):
    ticker = s.get("ticker","")
    for g, tickers in GROUPS.items():
        if ticker in tickers:
            return g
    return None

def is_1d_ext(s):
    EXT_1D = {"HG=F","PL=F","NG=F","ZN=F","ETH-USD","^GDAXI","^HSI","^SOX"}
    return s.get("ticker","") in EXT_1D

def direction_of(s):
    d = s.get("direction","")
    if "ロング" in d: return "long"
    if "ショート" in d: return "short"
    return None

def is_reversal_long(s):
    return direction_of(s) == "long" and s.get("primary_signal","") in REV_SIGNALS

def get_date(s):
    dt = s.get("fired_at","")
    return dt[:10] if dt else ""

def trend_of(s):
    ta = s.get("trend_alignment",{}) or {}
    htf = ta.get("higher_tf_trend","")
    if htf == "上昇": return "上昇"
    if htf == "下降": return "下降"
    if htf in ("横ばい","中立","もみあい","中立・もみあい"): return "中立・もみあい"
    return None

def get_R(s):
    if s.get("outcome") == "tp1":
        tp1 = s.get("tp1_pct",0)
        sl = abs(s.get("sl_pct",-1.0))
        return tp1/sl if sl > 0 else 2.0
    return -1.0

closed = [s for s in data if s.get("outcome") in ("tp1","sl") and not is_1d_ext(s)]
```

---

## 生出力 (Python実行結果)

```
総closed: 2358

=== CLAIMS (全期間) ===
other_fx×reversalL 全期間: 106/230=46.1% CI[39.8%,52.5%] E(R)=+0.075 RCI[-0.075,+0.226]
other_fx×reversalL×下降 全期間: 45/85=52.9% CI[42.4%,63.2%] E(R)=+0.235 RCI[-0.014,+0.484]
other_fx×reversalL×上昇 全期間: 25/59=42.4% CI[30.6%,55.1%] E(R)=-0.011 RCI[-0.308,+0.285]
other_fx×reversalL×中立 全期間: 36/86=41.9% CI[32.0%,52.4%] E(R)=-0.023 RCI[-0.268,+0.221]
other_fx×reversalL×4h 全期間: 48/96=50.0% CI[40.2%,59.8%] E(R)=+0.167 RCI[-0.068,+0.401]
other_fx×reversalL×1h 全期間: 53/128=41.4% CI[33.2%,50.1%] E(R)=-0.034 RCI[-0.234,+0.166]
other_fx×reversalL×bb 全期間: 69/152=45.4% CI[37.7%,53.3%] E(R)=+0.059 RCI[-0.126,+0.245]
other_fx×reversalL×rsi 全期間: 37/78=47.4% CI[36.7%,58.4%] E(R)=+0.107 RCI[-0.153,+0.367]
other_fx×ロング(非revL) 全期間: 104/272=38.2% CI[32.7%,44.1%] E(R)=-0.108 RCI[-0.243,+0.027]
jpy_fx×reversalL 全期間: 72/144=50.0% CI[41.9%,58.1%] E(R)=+0.167 RCI[-0.025,+0.358]
index×reversalL 全期間: 90/188=47.9% CI[40.8%,55.0%] E(R)=+0.117 RCI[-0.050,+0.284]
全体reversalL 全期間: 361/808=44.7% CI[41.3%,48.1%] E(R)=+0.042 RCI[-0.038,+0.123]

=== IS/FWD ===
IS(〜2026-07-02前): 60/143=42.0% CI[34.2%,50.2%] E(R)=-0.021 RCI[-0.210,+0.168]
FWD(2026-07-02〜): 46/87=52.9% CI[42.5%,63.0%] E(R)=+0.234 RCI[-0.012,+0.480]

-- FWD トレンド別 --
FWD×下降: 22/32=68.8% CI[51.4%,82.0%] E(R)=+0.604 RCI[+0.223,+0.985]
FWD×上昇: 17/34=50.0% CI[34.1%,65.9%] E(R)=+0.167 RCI[-0.231,+0.565]
FWD×中立: 7/21=33.3% CI[17.2%,54.6%] E(R)=-0.222 RCI[-0.704,+0.260]

-- FWD TF別 --
FWD×1h: 24/52=46.2% CI[33.3%,59.5%] E(R)=+0.077 RCI[-0.242,+0.396]
FWD×4h: 21/34=61.8% CI[45.0%,76.1%] E(R)=+0.441 RCI[+0.054,+0.828]  ← CI全域プラス！

-- FWD シグナル別 --
FWD×bb_lower_touch: 32/64=50.0% CI[38.1%,61.9%] E(R)=+0.167 RCI[-0.121,+0.455]
FWD×rsi_oversold_bounce: 14/23=60.9% CI[40.8%,77.8%] E(R)=+0.420 RCI[-0.056,+0.896]

-- FWD 銘柄別 --
FWD×AUDUSD=X: 9/11=81.8% CI[52.3%,94.9%] E(R)=+0.909 RCI[+0.351,+1.467]  ← 突出（N=11小サンプル）
FWD×GBPAUD=X: 14/25=56.0% CI[37.1%,73.3%] E(R)=+0.307 RCI[-0.157,+0.770]
FWD×EURUSD=X: 7/12=58.3% CI[32.0%,80.7%] E(R)=+0.361 RCI[-0.319,+1.041]
FWD×EURAUD=X: 11/24=45.8% CI[27.9%,64.9%] E(R)=+0.069 RCI[-0.406,+0.545]
FWD×GBPUSD=X: 5/15=33.3% CI[15.2%,58.3%] E(R)=-0.222 RCI[-0.798,+0.354]

-- IS トレンド別 --
IS×上昇: 8/25=32.0% CI[17.2%,51.6%] E(R)=-0.253
IS×下降: 23/53=43.4% CI[31.0%,56.7%] E(R)=+0.013
IS×中立: 29/65=44.6% CI[33.2%,56.7%] E(R)=+0.041

-- IS TF別 --
IS×1h: 29/76=38.2% CI[28.1%,49.4%] E(R)=-0.110
IS×4h: 27/62=43.5% CI[31.9%,55.9%] E(R)=+0.016

=== 全体 reversalL ===
全reversalL IS: 214/513=41.7% CI[37.5%,46.0%] E(R)=-0.027 RCI[-0.126,+0.073]
全reversalL FWD: 147/295=49.8% CI[44.2%,55.5%] E(R)=+0.163 RCI[+0.029,+0.296]
```

---

## 解釈・交絡点検

### IS→FWD変化サマリ
| 区分 | IS | FWD | 差 |
|---|---|---|---|
| 全体 | 42.0% | 52.9% | +10.9pp |
| 下降×other_fx×revL | 43.4% | 68.8% | +25.4pp ← 主ドライバー |
| 上昇×other_fx×revL | 32.0% | 50.0% | +18.0pp |
| 中立×other_fx×revL | 44.6% | 33.3% | -11.3pp ← 悪化 |
| 1h | 38.2% | 46.2% | +8.0pp |
| 4h | 43.5% | 61.8% | +18.3pp ← CI全域プラス |

### 仮説の状態
- **gate条件（回避確認）**: FWD RCI上限<0 → 現状 RCI[-0.012,+0.480]：**未達** (CI上限+0.480)
- **⛔反証条件**: FWD RCI下限>0 → 現状 -0.012：**未達（あと+0.012で到達）**
- **tracker宣言**: 🏁N≥30（ホールドアウト合格・既達 N=87≥30）

### 全体reversalL⛔反証（#032確認済）との関係
- 全reversalL FWD: 147/295=49.8% RCI[+0.029,+0.296]（CI全域プラス・⛔反証確定）
- other_fx×reversalL FWD: 46/87=52.9% RCI[-0.012,+0.480]（ほぼゼロまたぎ）
- 差: other_fxはCI下限がわずかに負（全体より個別で揺れ大きい）

### 金属レジーム転換との関連
#030/#032/#039/#040で確認された「IS不毛期→FWD改善」のパターンは、gold/silver等の金属が主因だった。
other_fx×reversalLの改善も「全体逆張り改善の波及」と整合するが、金属を含まない（other_fx はドルクロスFX）ため直接の金属影響はない。
→ 金属レジーム転換とは別の力学（FX市場の方向性変化・ボラ低下後の逆張り有効期間延長）の可能性。

### 注目: FWD×4h CI全域プラス（RCI[+0.054,+0.828]）
N=34と小サンプルだが、CI全域プラスは注目に値する。全体のFWD×4h=61.8%はIS×4h=43.5%から+18.3pp改善。
他の分析（#015: 4h×L全般は回避、#034: 指数4h後半36%）との比較: other_fx×reversal_long×4hは例外的に改善している。

### AUDUSD突出の扱い
AUDUSD=X FWD: 9/11=81.8% N=11は小サンプルノイズの可能性大。継続観察。
GBPUSD=X FWD: 5/15=33.3%が最低で、銘柄間格差が大きい（CI幅も広い）。

---

## Wilson CI計算確認（主要値）
- other_fx×reversalL 全期間: 106/230, z=1.96 → CI[39.8%,52.5%] ✓
- 下降 全期間: 45/85 → CI[42.4%,63.2%] ✓
- FWD全体: 46/87 → CI[42.5%,63.0%] ✓

## 43%比較
- 全期間 46.1%: 43%超（損益分岐は超えているが旧IS42%のgate根拠と整合）
- IS 42.0%: 43%をわずかに割る（gate設立の根拠）
- FWD 52.9%: 43%を9.9pp超（改善中）

---

## tracker宣言基準確認
```
[tracker] other_fx×逆張り買い(回避) gate
  宣言基準: 前向きN≥30かつ平均RのCI上限<0🏁
  現在値 (2026-07-30): 平均R +0.23 CI[-0.08~+0.55]（46/87・勝率53%）
  状態: 🟡蓄積中
```

gate条件 (CI上限<0) 未達（+0.55）
⛔反証 (CI下限>0) 未達（-0.08/私の計算では-0.012）
→ 引き続き蓄積中。次チェックポイントでの確認待ち。
