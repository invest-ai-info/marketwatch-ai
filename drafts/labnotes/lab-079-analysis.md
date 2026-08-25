# lab-079 分析ノート — tf=1d×reversal_long 日足逆張り買い正式検証

**基準日**: 2026-08-25  
**仮説**: 日足（1d）逆張り買いシグナル（bb_lower_touch / rsi_oversold_bounce）は損益分岐43%を有意に超過するか

---

## スクリプト全文

```python
import json, math

with open('signals-log.json') as f:
    log = json.load(f)

# verify.py 準拠ロジック（拡張ユニバース除外なし）
REV = {"rsi_oversold_bounce", "bb_lower_touch"}
GROUPS = {
    "metal":    {"GC=F","SI=F"},
    "index":    {"NKD=F","ES=F","NQ=F","YM=F","^FTSE"},
    "jpy_fx":   {"USDJPY=X","EURJPY=X","GBPJPY=X","AUDJPY=X"},
    "other_fx": {"EURUSD=X","GBPUSD=X","AUDUSD=X","EURAUD=X","GBPAUD=X"},
    "btc":      {"BTC-USD"},
    "oil":      {"CL=F"},
}

def is_closed(s): return s.get('outcome') in ('tp1','tp2','sl')
def is_win(s): return s.get('outcome') in ('tp1','tp2')
def get_actual_r(s):
    o = s.get('outcome','')
    if o == 'tp1': return 2.0/1.5
    if o == 'tp2': return 3.0/1.5
    if o == 'sl': return -1.0
    return 0
def match_filter(s, f):
    if not is_closed(s): return False
    d = s.get('direction') or ''
    if f.get('reversal_long')==True:
        # verify.py準拠: is_long = "ロング" in d のみ（d=='long'は不使用）
        is_long = "ロング" in d
        if not (is_long and s.get('primary_signal','') in REV): return False
    if 'tf' in f:
        if s.get('timeframe','') != f['tf']: return False
    if 'signal' in f:
        if s.get('primary_signal','') != f['signal']: return False
    if 'group' in f:
        g = f['group']
        if g!='all' and s.get('ticker','') not in GROUPS.get(g,set()): return False
    fa = (s.get('fired_at') or '')[:10]
    if 'fired_before' in f and fa >= f['fired_before']: return False
    if 'fired_from' in f and fa < f['fired_from']: return False
    return True
```

---

## 生出力（verify.py準拠・拡張ユニバース含む）

### メイン仮説: tf=1d×reversalL 全件

```
tf=1d×reversalL（verify.py準拠）: N=35, k=25, 71.4% CI[54.9%,83.7%] E(R)=0.667 RCI[0.312,1.021]
tf=1d×Long 全件（対照）:          N=122, k=59, 48.4% CI[39.7%,57.1%] E(R)=0.128 RCI[-0.082,+0.338]
```

### シグナル別

```
bb_lower_touch:      N=20, k=15, 75.0% CI[53.1%,88.8%] E(R)=0.750 RCI[+0.296,+1.204]
rsi_oversold_bounce: N=15, k=10, 66.7% CI[41.7%,84.8%] E(R)=0.556 RCI[-0.021,+1.132]
```

### グループ別（ticker推定・verify.py準拠）

```
index:    N=6,  k=5,  83.3% CI[43.6%,97.0%] E(R)=0.944
metal:    N=7,  k=3,  42.9% CI[15.8%,75.0%] E(R)=0.000
jpy_fx:   N=8,  k=6,  75.0% CI[40.9%,92.9%] E(R)=0.750
other_fx: N=6,  k=5,  83.3% CI[43.6%,97.0%] E(R)=0.944
btc:      N=3,  k=2,  66.7% CI[20.8%,93.9%] E(R)=0.556
oil:      N=4,  k=4, 100.0% CI[51.0%,100.0%] E(R)=1.333
^SOX(index_x): N=1, k=0,   0.0% （拡張ユニバース・verify.pyは除外しない）
合計: N=35, k=25 ✓
```

### IS vs FWD（登録日 2026-07-15 基準・fired_from/before）

```
IS (fired_before 2026-07-15): N=25, k=18, 72.0% CI[52.4%,85.7%] E(R)=0.680 RCI[+0.261,+1.099]
FWD (fired_from 2026-07-15):  N=10, k=7,  70.0% CI[39.7%,89.2%] E(R)=0.633 RCI[-0.065,+1.332]
```

### FWD内訳

```
FWD bb_lower_touch:      N=7, k=4, 57.1% E(R)=0.333（^SOX sl追加で N=6→7）
FWD rsi_oversold_bounce: N=3, k=3, 100.0% E(R)=1.333

FWD index:    N=3, k=2, 66.7% E(R)=0.556
FWD jpy_fx:   N=5, k=4, 80.0% E(R)=0.867
FWD other_fx: N=1, k=1, 100.0%
FWD ^SOX(index_x): N=1, k=0, 0.0% E(R)=-1.000
FWD metal:    N=0  ← 金属7件はすべてIS期（〜2026-07-15）。FWD期の発火なし
合計: 3+5+1+1 = 10 ✓（k=2+4+1+0=7 ✓）
```

### 対照群：tf=1d Long 全般

```
tf=1d×Long: N=122, k=59, 48.4% CI[39.7%,57.1%] E(R)=0.128 RCI[-0.082,+0.338]
（1d逆張り買い71.4% vs 1d Long全般48.4%の差 = 23.0pp）
```

---

## 検証メモ

### N=34→35の修正理由
- 当初の分析コードでは拡張ユニバース（EXTENDED）を除外していた
- verify.py は拡張ユニバースを除外しない（match()関数にEXTENDED除外ロジックなし）
- 差分1件: ^SOX, primary_signal=bb_lower_touch, outcome=sl, fired_at=2026-07-28（FWD期間）
- このシグナルはlossなので k は変わらず（k=25のまま）

### 事前宣言（今回）
- H1: 全件 CI下限 > 43% かつ N≥20 → 54.9%>43% ✅ N=35≥20 ✅
- H2: FWD N=10で IS 整合性確認（両期間で72%以上）→ IS=72.0% ✅ / FWD=70.0% ⚠️（2pp未達）
  → 方向性は整合しているが閾値未達のため「方向性整合・閾値条件付き」と評価
- H3: BB(bb_lower_touch) CI下限 > 43% → 53.1%>43% ✅

### 交絡点検
- **金属の引き下げ**: metal N=7, 42.9%が全体を下引き
- **金属除外後**: index+jpy_fx+other_fx+btc+oil = N=27, k=22, 81.5% → 金属が主なアウトライヤー
- **シグナル間差**: BB 75.0% > RSI 66.7%（8.3pp差）。ただしRSI CI幅が広い（N=15）
- **小サンプル**: N=35は全体。1H(#069 の FWD×1H N=115)・4H(#074 の FWD×4H N=59)より大幅に少ない
- **FWD N=10**: 70.0%の解釈は慎重に。RCI下限=-0.065でわずかにマイナス

### トラッカー確認（2026-08-25更新後）
- tf=1d×reversalL: FWD k=7/n=10, 勝率70%, 平均R +0.633 RCI[-0.065,+1.332] 🟡蓄積中
- RCI下限 -0.065 < 0 → 正値未達（蓄積継続）
- 昇格条件: 前向きN≥80（標準）→ 蓄積継続

### 先行研究との比較
| 時間足 | 対象 | FWD勝率 | FWD E(R) | 研究回 |
|---|---|---|---|---|
| 1H | rsi_oversold **1H単体** | 47.0%(N=115) | +0.095R | #069 |
| 4H | rsi_oversold全体 | 67.8%(N=59) | +0.580R | #074 |
| **1D** | **reversal全体** | **70.0%(N=10)** | **+0.633R** | **#079 今回** |

※ FWD Nが異なるため直接比較は慎重に。日足FWD N=10は暫定値。出典回もばらばら（#069/#074/今回）。

---

## 2026-08-25 訂正（Opusコンプラのエスカレ3件に対応）

台帳 `signal-lab-ledger.md` の #069・#074 行と `signals-log.json` から再計算して訂正した。

| # | 誤 | 正 | 根拠 |
|---|---|---|---|
| [A] | 1H足 54.7%（#069・N=179） | 1H足 47.0%（#069・FWD×1H N=115・E(R)=+0.095） | 54.7%/179 は #069 の **FWD全体**（1H+4H+その他の混在）。台帳 #069 行に「FWD×1H 54/115=47.0% CI[38.1%,56.0%] E(R)=+0.095」と明記 |
| [B] | FWD metal N=2, k=0 | FWD metal **N=0**（内訳合計 3+5+1+1=10） | signals-log.json の FWD 10件を明細で確認（NKD=F/EURAUD=X/^SOX/NQ=F/YM=F/GBPJPY=X×2/EURJPY=X/AUDJPY=X）。金属(GC=F,SI=F)は0件＝7件すべてIS期 |
| [C] | #069: N=312 / #074: N=312 | #069: 全期間 N=312（IS133+FWD179）／#074: 全期間 N=353（IS133+FWD220） | 台帳 #069「全期間 150/312」・#074「IS:133 / FWD全体:220」 |

⚠️ [B] により「金属がFWDを引き下げた」という読みは成立しない。金属が引き下げているのは **IS 側だけ**。
本文 §7-2 にこの但し書きを追加済み。
