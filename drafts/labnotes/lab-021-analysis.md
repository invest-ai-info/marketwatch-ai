# Lab-021 分析ノート — 指数×ロング 前向きトラッカー初昇格

**基準日**: 2026-06-26  
**仮説**: 指数グループ（NKD=F / ES=F / NQ=F / YM=F / ^FTSE）×ロング方向のシグナルは、  
　　　　損益分岐43%を上回る正期待値エッジを持つか

---

## 採択経緯

- **発端**: スイープ(#013以降)で group=index×dir=long が FDR通過、2026-06-12 にトラッカー登録
- **今日のトリガー**: `python signal_lab_tracker.py update --date 2026-06-26` が  
  前向き N=90, 平均R=+0.400 CI[+0.16~+0.64] → CI下限+0.16 > 0 で **✅昇格** を検出
- 昇格基準: 前向きN≥80 AND 平均RのCI下限>0（edgeクラス）
- **シリーズ初の「前向き昇格」**（#001〜#020で初）

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

def er_ci(r_vals):
    if not r_vals: return 0, 0, 0
    n = len(r_vals)
    m = sum(r_vals)/n
    if n < 2: return m, m, m
    s = math.sqrt(sum((v-m)**2 for v in r_vals)/(n-1))
    se = s/math.sqrt(n)
    return m, m - 1.96*se, m + 1.96*se

GROUPS = {
    "metal":    {"GC=F", "SI=F"},
    "index":    {"NKD=F", "ES=F", "NQ=F", "YM=F", "^FTSE"},
    "jpy_fx":   {"USDJPY=X", "EURJPY=X", "GBPJPY=X", "AUDJPY=X"},
    "other_fx": {"EURUSD=X", "GBPUSD=X", "AUDUSD=X", "EURAUD=X", "GBPAUD=X"},
    "btc":      {"BTC-USD"},
    "oil":      {"CL=F"},
}

with open('signals-log.json') as f:
    records = json.load(f)

def closed(r): return r.get('outcome') in ('tp1','tp2','sl')
def win(r): return r.get('outcome') in ('tp1','tp2')
def is_long(r): return 'ロング' in (r.get('direction') or '')
def is_short(r): return 'ショート' in (r.get('direction') or '')
def get_trend(r):
    ta = r.get('trend_alignment')
    if isinstance(ta, dict) and ta.get('higher_tf_trend'):
        return ta['higher_tf_trend']
    return 'unknown'
def get_tf(r):
    tf = r.get('timeframe') or r.get('tf') or ''
    for v in ['1h','1H']:
        if v in tf: return '1h'
    for v in ['4h','4H']:
        if v in tf: return '4h'
    return 'unknown'
def get_r(r):
    rv = r.get('r_multiple') or r.get('r_result')
    if rv is not None: return float(rv)
    if win(r): return 1.33
    return -1.0

all_closed = [r for r in records if closed(r)]
idx_long = [r for r in all_closed if r.get('ticker') in GROUPS['index'] and is_long(r)]
```

---

## 生出力

```
=== 全体ベースライン ===
N=1117, k=441, 勝率=39.5% CI[36.7%~42.4%]
E(R)=-0.080 CI[-0.147~-0.013]

=== 指数×ロング IN-SAMPLE ===
N=211, k=113, 勝率=53.6% CI[46.8%~60.2%]
E(R)=0.248 CI[0.091~0.405]

=== 指数×ショート IN-SAMPLE ===
N=56, k=17, 勝率=30.4% CI[19.9%~43.3%]

=== グループ×ロング比較 ===
  metal:    19/114 = 16.7% CI[10.9%~24.6%] E(R)=-0.612 CI[-0.772~-0.452]
  index:   113/211 = 53.6% CI[46.8%~60.2%] E(R)=+0.248 CI[+0.091~+0.405]
  jpy_fx:  61/156 = 39.1% CI[31.8%~46.9%] E(R)=-0.089 CI[-0.268~+0.090]
  other_fx: 80/237 = 33.8% CI[28.0%~40.0%] E(R)=-0.214 CI[-0.354~-0.073]
  btc:     19/64  = 29.7% CI[19.9%~41.8%] E(R)=-0.308 CI[-0.571~-0.045]
  oil:     16/32  = 50.0% CI[33.6%~66.4%] E(R)=+0.165 CI[-0.245~+0.575]

=== 銘柄別（指数×ロング）===
  NKD=F: 31/48 = 64.6% CI[50.4%~76.6%]
  ES=F:  28/56 = 50.0% CI[37.3%~62.7%]
  NQ=F:  25/46 = 54.3% CI[40.2%~67.8%]
  YM=F:  20/41 = 48.8% CI[34.3%~63.5%]
  ^FTSE:  9/20 = 45.0% CI[25.8%~65.8%]

=== トレンド別（指数×ロング）===
  上昇:      68/130 = 52.3% CI[43.8%~60.7%]
  下降:       13/18 = 72.2% CI[49.1%~87.5%]
  中立・もみあい: 28/59 = 47.5% CI[35.3%~60.0%]

=== 時間足別（指数×ロング）===
  1h: 67/122 = 54.9% CI[46.1%~63.5%]
  4h: 42/83  = 50.6% CI[40.1%~61.1%]

=== シグナル種別（指数×ロング）===
  bb_lower_touch:      32/57 = 56.1% CI[43.3%~68.2%]
  rsi_oversold_bounce: 24/40 = 60.0% CI[44.6%~73.7%]
  macd_golden:         17/38 = 44.7% CI[30.1%~60.3%]
  high_break:          19/33 = 57.6% CI[40.8%~72.8%]
```

---

## 前向きトラッカー出力（signal_lab_tracker.py update 2026-06-26）

```
指数×ロング(全足ライブ)  edge  2026-06-12  54/90  60%  +0.400  [+0.16~+0.64]  ✅昇格
```

昇格条件:
- 前向き N=90 ≥ 80 ✅
- 平均R CI下限 +0.16 > 0 ✅

---

## 解釈メモ

1. **in-sample 53.6% → 前向き 60.0%**: out-of-sample で過去よりむしろ強化された希有なケース
2. **方向非対称**: ロング53.6% vs ショート30.4%（23pp差）。指数は「買い方有利」
3. **銘柄間のバラつき**: NKD=F 64.6% > NQ=F 54.3% > ES=F 50.0% > YM=F 48.8% > ^FTSE 45.0%
   NKD=F の優位は既存 #013「指数ロング頑健性」と整合する
4. **トレンド別**: 下降72.2%(N=18小)は過信禁止。上昇52.3%・中立47.5%はいずれも43%超
5. **shignal: rsi_oversold_bounce 60.0%(N=40)**: 逆張りが指数では有効
6. **交絡チェック**: 各トレンドでも43%を下回るものがない（中立は CI下限35.3%は割れるが勝率47.5%は維持）

---

## 制限と注意事項

- N=211は各銘柄40〜56件と中程度。^FTSEは20件で信頼区間が広い
- 前向きN=90は2週間強（2026-06-12〜）のデータ。短期偏りの可能性あり
- トレンド別は trend_alignment.higher_tf_trend を使用（不記録分はunknown=4件のみ）
- 昇格は「ライブ配信フィルタへの反映候補」であり、自動で発火エンジンには触れない
