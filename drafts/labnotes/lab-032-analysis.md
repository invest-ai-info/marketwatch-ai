# AIシグナル研究日誌 #032 — 分析ノート
## 仮説: reversalL（逆張り買い）gate が前向きで⛔反証
### 基準日: 2026-07-07 / 担当: signal-lab-daily

---

## 優先度判定

トラッカーupdate（2026-07-07）で以下のステータス変化を検出：
- **reversalL（逆張り買い）**: 🟡蓄積中 → ⛔反証（前向き N=81、E(R)+0.383、RCI[+0.08~+0.69]）

優先度①（⛔反証検出）により本仮説を採択。

---

## スイープ結果（sweep-2026-07-07.json）

FDR通過: 1本（group=index×reversalL, R+0.37）→ 既登録のため新規なし

---

## 検証スクリプト（Python）

```python
import json, math

def wilson(k, n, z=1.96):
    if n == 0: return (0.0, 100.0)
    p = k / n
    den = 1 + z*z/n
    c = (p + z*z/(2*n)) / den
    pm = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / den
    return (max(0, c-pm)*100, min(1, c+pm)*100)

def r_ci_mean(rs, z=1.96):
    n = len(rs)
    if n == 0: return 0, 0, 0
    m = sum(rs)/n
    s2 = sum((r-m)**2 for r in rs)/(n-1) if n > 1 else 0
    se = math.sqrt(s2/n)
    return m, m - z*se, m + z*se

def get_group(d):
    GROUPS = {
        "metal":    {"GC=F","SI=F"},
        "index":    {"NKD=F","ES=F","NQ=F","YM=F","^FTSE"},
        "jpy_fx":   {"USDJPY=X","EURJPY=X","GBPJPY=X","AUDJPY=X"},
        "other_fx": {"EURUSD=X","GBPUSD=X","AUDUSD=X","EURAUD=X","GBPAUD=X"},
        "btc":      {"BTC-USD"},
        "oil":      {"CL=F"},
    }
    t = d.get("ticker","")
    for g, tickers in GROUPS.items():
        if t in tickers:
            return g
    return "unknown"

def get_trend(d):
    ta = d.get("trend_alignment")
    if isinstance(ta, dict) and ta.get("higher_tf_trend"):
        return ta["higher_tf_trend"]
    return "unknown"

def is_long(d):
    return "ロング" in (d.get("direction") or "")

REV = {"rsi_oversold_bounce","bb_lower_touch"}
def is_reversal_long(d):
    return is_long(d) and d.get("primary_signal") in REV

def closed(d):
    return d.get("outcome") in ("tp1","tp2","sl")

def win(d):
    return d.get("outcome") in ("tp1","tp2")

TP1_R = 1.33
TP2_R = 2.00
SL_R  = -1.00

def calc_r(d):
    o = d.get("outcome")
    if o == "tp1": return TP1_R
    if o == "tp2": return TP2_R
    if o == "sl":  return SL_R
    return None

with open("signals-log.json") as f:
    data = json.load(f)

closed_data = [d for d in data if closed(d)]
reg_date = "2026-06-25"  # tracker登録日
def is_forward(d):
    fa = d.get("fired_at","")
    return fa[:10] >= reg_date

rev_all = [d for d in closed_data if is_reversal_long(d)]
rev_fwd = [d for d in rev_all if is_forward(d)]
rev_is  = [d for d in rev_all if not is_forward(d)]
```

---

## 生出力（実行結果）

```
Total closed: 1394

=== reversalL（逆張り買い）⛔反証分析 ===
in-sample (〜2026-06-24): k=174, N=447, WR=38.9%, CI=[34.5%~43.5%], E(R)=-0.093 RCI=[-0.198~+0.012]
forward (2026-06-25〜):  k=48,  N=81,  WR=59.3%, CI=[48.4%~69.3%], E(R)=+0.381 RCI=[+0.130~+0.632]
全期間（IS+FWD合計）:      k=222, N=528, WR=42.0%, CI=[37.9%~46.3%], E(R)=-0.020

--- グループ別 ---
  IS  metal:    k=13, N=79,  WR=16.5%, CI=[9.9%~26.1%],  E(R)=-0.617 RCI=[-0.808~-0.425]
  FWD metal:    k=11, N=15,  WR=73.3%, CI=[48.0%~89.1%], E(R)=+0.709 RCI=[+0.169~+1.248]
  IS  index:    k=54, N=96,  WR=56.2%, CI=[46.3%~65.7%], E(R)=+0.311 RCI=[+0.078~+0.543]
  FWD index:    k=10, N=13,  WR=76.9%, CI=[49.7%~91.8%], E(R)=+0.792 RCI=[+0.237~+1.348]
  IS  jpy_fx:   k=38, N=86,  WR=44.2%, CI=[34.2%~54.7%], E(R)=+0.030 RCI=[-0.216~+0.276]
  FWD jpy_fx:   k=8,  N=15,  WR=53.3%, CI=[30.1%~75.2%], E(R)=+0.243 RCI=[-0.366~+0.852]
  IS  other_fx: k=48, N=126, WR=38.1%, CI=[30.1%~46.8%], E(R)=-0.112 RCI=[-0.311~+0.086]
  FWD other_fx: k=11, N=19,  WR=57.9%, CI=[36.3%~76.9%], E(R)=+0.349 RCI=[-0.183~+0.880]
  IS  btc:      k=9,  N=38,  WR=23.7%, CI=[13.0%~39.2%], E(R)=-0.448 RCI=[-0.767~-0.129]
  FWD btc:      k=5,  N=12,  WR=41.7%, CI=[19.3%~68.0%], E(R)=-0.029 RCI=[-0.708~+0.650]
  IS  oil:      k=12, N=22,  WR=54.5%, CI=[34.7%~73.1%], E(R)=+0.271 RCI=[-0.225~+0.767]
  FWD oil:      k=3,  N=7,   WR=42.9%, CI=[15.8%~75.0%], E(R)=-0.001 RCI=[-0.924~+0.921]

--- FWD トレンド別 ---
  FWD trend=上昇:     k=13, N=22, WR=59.1%, CI=[38.7%~76.7%], E(R)=+0.377 RCI=[-0.113~+0.867]
  FWD trend=下降:     k=22, N=39, WR=56.4%, CI=[41.0%~70.7%], E(R)=+0.314 RCI=[-0.053~+0.682]
  FWD trend=中立・もみあい: k=13, N=20, WR=65.0%, CI=[43.3%~81.9%], E(R)=+0.515 RCI=[+0.015~+1.014]

--- FWD シグナル別 ---
  FWD rsi_oversold_bounce: k=18, N=25, WR=72.0%, CI=[52.4%~85.7%], E(R)=+0.678 RCI=[+0.259~+1.096]
  FWD bb_lower_touch:      k=30, N=56, WR=53.6%, CI=[40.7%~66.0%], E(R)=+0.248 RCI=[-0.059~+0.555]

--- FWD 時間足別 ---
  FWD tf=1h: k=28, N=51, WR=54.9%, CI=[41.4%~67.7%], E(R)=+0.279 RCI=[-0.042~+0.601]
  FWD tf=4h: k=17, N=27, WR=63.0%, CI=[44.2%~78.5%], E(R)=+0.467 RCI=[+0.035~+0.900]

--- 非金属比較（レジーム転換が唯一の原因かの交絡点検） ---
  IS  非metal: k=161, N=368, WR=43.8%
  FWD 非metal: k=37,  N=66,  WR=56.1%

--- 月別集計（FWD）---
  2026-06: k=33, N=52, WR=63.5%, E(R)=+0.479
  2026-07: k=15, N=29, WR=51.7%, E(R)=+0.205

--- 比較: 非reversalL FWD ---
  FWD 非reversalL: k=96, N=224, WR=42.9%, E(R)=-0.001
```

---

## 解釈メモ

### ⛔反証成立の条件
- gate設定時の宣言: 「前向きN≥80かつ平均RのCI上限<0」（全域マイナス確認）
- 実際の前向き: N=81 ✅、E(R)=+0.381 RCI=[+0.130~+0.632]（CI下限+0.130>>0）
- → CI上限<0 の条件を全く満たさず、逆に全域プラス。⛔反証確定。

### 主因: 金属群のレジーム転換（#030と同根）
- IS metal 16.5%（N=79）が全体を大きく引き下げていた
- FWD metal 73.3%（N=15）への劇的な転換 = +56.8pp
- これは #030「ロング全般gate前向き⛔反証」の主因と同一（金属IS E(R)-0.964→FWD+0.672）

### 交絡点検: 非金属群でも改善
- IS non-metal: 43.8%、FWD non-metal: 56.1%（+12.3pp改善）
- 金属レジーム転換だけが原因ではない。非金属群でも逆張り買いのエッジが改善している

### トレンド非依存性（#022と比較）
- #022: 上昇54.1%>> 下降33.7%（大きな非対称）
- FWD: 上昇59.1%、下降56.4%、中立65.0% → トレンド依存性がほぼ消えた
- 特に下降×逆張り買いの改善が注目点（IS下降=33.7%→FWD下降=56.4%）

### RSI vs BB（FWD）
- rsi_oversold_bounce: FWD 72.0%（N=25）— 非常に強い
- bb_lower_touch: FWD 53.6%（N=56）— 堅実

### 留意点
- FWD N=81は昇格基準（N≥80）ちょうど到達。2026-07月分（N=29）は51.7%とやや軟化
- グループ別はN=7〜19と小サンプル。個別CIは広い
- 「反証=今後もプラスが続く」ではなく「gateの仮定が現時点では否定された」の意味
