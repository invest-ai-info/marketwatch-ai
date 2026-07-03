# AIシグナル研究日誌 #029 ラボノート

## 基準日
2026-07-04 (JST)

## 仮説
**もみあい×ショートエッジ（#012/019で確認）は前向き追跡（2026-06-17以降 N=54）でも持続するか。**

サブ仮説:
- H1: macd_dead（IS期 #019時点 57.1%）は前向きでも43%を上回るか
- H2: low_break（IS期 #019時点 35.7%）は前向きで有意にマイナスのE(R)を示すか

事前合否基準（宣言）:
- 全体前向き: 勝率 または E(R) CI が43%・0を含む → 「確定打なし」、含まない → 「通過A」
- macd_dead前向き: CI[23.4%~59.3%] が43%をまたいでいる → 確定打なし
- low_break前向き: E(R) CI が完全にマイナス → ⛔反証確認

## 発見スイープ結果
sweep-2026-07-04.json: FDR通過 0本 (新規候補なし)
トラッカー更新: 昇格/反証変化なし

## 題材選択理由
優先度②: 前向きで大きく動いた仮説
- `trend=中立・もみあい×dir=short` (edge): 前向き R=-0.265, N=54
- IS期 50.7% → 前向き 31.5% の大幅崩落
- low_break E(R)CI が全域マイナス（有意な損失）

## Pythonスクリプト

```python
import json, math
from datetime import datetime

def wilson(k, n, z=1.96):
    if n == 0: return (0.0, 100.0)
    p = k / n
    den = 1 + z*z/n
    c = (p + z*z/(2*n)) / den
    pm = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / den
    return (max(0,c-pm)*100, min(1,c+pm)*100)

def get_R(e):
    if e.get('outcome') in ('tp1','tp2'): return 1.333
    return -1.0

d = json.load(open('signals-log.json'))
closed_all = [x for x in d if x.get('outcome') in ('tp1','sl')]

def get_trend(e):
    ta = e.get('trend_alignment')
    if isinstance(ta, dict): return ta.get('higher_tf_trend','unknown')
    return 'unknown'

GROUPS = {
    "metal":    {"GC=F","SI=F"},
    "index":    {"NKD=F","ES=F","NQ=F","YM=F","^FTSE"},
    "jpy_fx":   {"USDJPY=X","EURJPY=X","GBPJPY=X","AUDJPY=X"},
    "other_fx": {"EURUSD=X","GBPUSD=X","AUDUSD=X","EURAUD=X","GBPAUD=X"},
    "btc":      {"BTC-USD"},
    "oil":      {"CL=F"},
}
def get_group(e):
    for g, tickers in GROUPS.items():
        if e.get('ticker','') in tickers: return g
    return 'other'

def is_short(e): return 'ショート' in (e.get('direction') or '')
def win(e): return e.get('outcome') in ('tp1','tp2')

FWD = '2026-06-17'  # tracker registration date

momiai_s_all = [e for e in closed_all if get_trend(e)=='中立・もみあい' and is_short(e)]
momiai_s_is  = [e for e in momiai_s_all if (e.get('fired_at','') or '')[:10] < FWD]
momiai_s_fwd = [e for e in momiai_s_all if (e.get('fired_at','') or '')[:10] >= FWD]

# Stats
for rows, label in [(momiai_s_is,'IS'), (momiai_s_fwd,'FWD'), (momiai_s_all,'TOTAL')]:
    k = sum(1 for e in rows if win(e))
    n = len(rows)
    rs = [get_R(e) for e in rows]
    r = sum(rs)/n if n else 0
    lo, hi = wilson(k, n)
    def r_ci(tp, sl):
        n2 = tp+sl
        rv = [1.333]*tp + [-1.0]*sl
        mu = sum(rv)/n2
        v = sum((x-mu)**2 for x in rv)/(n2-1)
        se = math.sqrt(v/n2)
        return mu, mu-1.96*se, mu+1.96*se
    tp = sum(1 for e in rows if e.get('outcome')=='tp1')
    sl = sum(1 for e in rows if e.get('outcome')=='sl')
    mu, rlo, rhi = r_ci(tp, sl)
    print(f"{label}: {k}/{n}={100*k/n:.1f}% CI[{lo:.1f}%~{hi:.1f}%] R={r:+.3f} RCI[{rlo:+.3f}~{rhi:+.3f}]")
```

## 生出力

### もみあい×ショート 全体・IS/FWD分割
```
IS  (before 2026-06-17): 28/44=63.6% CI[48.9%~76.2%] R=+0.485
FWD (from  2026-06-17) : 17/54=31.5% CI[20.7%~44.7%] R=-0.266 RCI[-0.557~+0.026]
TOTAL                  : 45/98=45.9% CI[36.4%~55.8%] R=+0.071 RCI[-0.160~+0.303]
```

### シグナル種別（全期間 = claims.json検証値）
```
macd_dead  : 24/50=48.0% CI[34.8%~61.5%]
low_break  : 12/33=36.4% CI[22.2%~53.4%]
ma_dead    :  6/12=50.0% CI[25.4%~74.6%]
```

### シグナル種別（前向き: 2026-06-17以降）
```
macd_dead FWD: 10/25=40.0% CI[23.4%~59.3%] R=-0.067 RCI[-0.524~+0.390]
low_break FWD:  3/20=15.0% CI[ 5.2%~36.0%] R=-0.650 RCI[-1.025~-0.275]  ← CI全域マイナス
ma_dead   FWD:  4/ 9=44.4% (N小)
```

### グループ別（前向き）
```
index    :  0/ 4= 0.0% CI[ 0.0%~49.0%]
metal    :  3/16=18.8% CI[ 6.6%~43.0%]
jpy_fx   :  6/13=46.2% CI[23.2%~70.9%]
other_fx :  8/19=42.1% CI[23.1%~63.7%]
btc      :  0/ 2= 0.0%
```

### E(R) CIサマリー
```
low_break FWD: E(R)=-0.650 CI[-1.025~-0.275]  → CI全域マイナス = 有意な損失
全体 FWD      : E(R)=-0.266 CI[-0.557~+0.026]  → CIが0をほぼ含む
macd_dead FWD: E(R)=-0.067 CI[-0.524~+0.390]  → CI内に0あり
```

## 判定

| 仮説 | 結果 |
|---|---|
| もみあい×S 全体エッジ持続 | 反証方向（31.5%<43%、RCI が0をほぼ含む） |
| H1: macd_dead > 43% | 未達（40.0%、CI[23%~59%]が43%をまたぐ）確定打なし |
| H2: low_break E(R) CI全域マイナス | ✅ **確認** (E(R)=-0.650 CI[-1.025~-0.275]) |

## 前向きトラッカー表
- `trend=中立・もみあい×dir=short`: 17/54=32% R=-0.27 CI[-0.70~+0.17] 🟡蓄積中
- 昇格/反証の正式フラグ: なし（RCI が 0 を含む）

## 次の観察候補
- macd_dead×もみあい×S が前向きN=50に達したとき再検証
- low_break×もみあい×S は「ゲート（回避候補）」として蓄積継続
