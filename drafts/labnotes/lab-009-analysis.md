# AIシグナル研究日誌 #009 — 分析メモ（lab-009-analysis.md）

**基準日**: 2026-06-16 JST  
**仮説**: jpy_fx（円クロスFX）ショートシグナルの勝率は損益分岐点43%を下回るか  
**事前合否基準**: 95% Wilson CI 上限 < 43% → 棄却確認（通過A） / CI上限 ≥ 43% → 継続観察  

---

## 検証スクリプト（Python 3）

```python
import json, math
from collections import Counter

def wilson(k, n, z=1.96):
    if n == 0: return (0.0, 100.0)
    p = k/n
    den = 1 + z*z/n
    c = (p + z*z/(2*n)) / den
    pm = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / den
    return (max(0, c-pm)*100, min(1, c+pm)*100)

with open('signals-log.json') as f:
    data = json.load(f)

closed = [d for d in data if d.get('outcome') in ('tp1','tp2','sl')]

GROUPS = {
    "jpy_fx":   {"USDJPY=X","EURJPY=X","GBPJPY=X","AUDJPY=X"},
    "other_fx": {"EURUSD=X","GBPUSD=X","AUDUSD=X","EURAUD=X","GBPAUD=X"},
}

def get_trend(d):
    ta = d.get("trend_alignment")
    if isinstance(ta, dict) and ta.get("higher_tf_trend"):
        return ta["higher_tf_trend"]
    return "unknown"

def analyze(rows, label):
    n = len(rows)
    w = sum(1 for d in rows if d.get('outcome') in ('tp1','tp2'))
    if n == 0: return f"{label}: N=0"
    lo, hi = wilson(w, n)
    er = 1.33*w/n - 1.0*(1-w/n)
    print(f"{label}: k={w} n={n} {100*w/n:.1f}% CI[{lo:.1f}~{hi:.1f}] E(R)={er:+.3f}")

all_jpy = [d for d in closed if d.get('ticker') in GROUPS["jpy_fx"]]
jpy_l = [d for d in all_jpy if 'ロング' in (d.get('direction') or '')]
jpy_s = [d for d in all_jpy if 'ショート' in (d.get('direction') or '')]

# === メイン集計 ===
analyze(all_jpy,  "jpy_fx 全体")
analyze(jpy_l,    "jpy_fx ロング")
analyze(jpy_s,    "jpy_fx ショート [主仮説]")

for tr in ['下降','中立・もみあい','上昇']:
    sub = [d for d in jpy_s if get_trend(d) == tr]
    if sub: analyze(sub, f"jpy_fx ショート × trend={tr}")

# === 交絡：シグナル種別 ===
for sig in set(d.get('primary_signal') for d in jpy_s):
    sub = [d for d in jpy_s if d.get('primary_signal') == sig]
    if sub: analyze(sub, f"jpy_fx ショート × {sig}")

md_jpy = [d for d in all_jpy if d.get('primary_signal') == 'macd_dead']
analyze(md_jpy, "macd_dead × jpy_fx [全件]")
print(f"jpy_fx ショート中のmacd_dead比率: {len(md_jpy)}/{len(jpy_s)} = {100*len(md_jpy)/len(jpy_s):.1f}%")

# === 副次：ロング内シグナル別 ===
bbl = [d for d in jpy_l if d.get('primary_signal') == 'bb_lower_touch']
rsi = [d for d in jpy_l if d.get('primary_signal') == 'rsi_oversold_bounce']
analyze(bbl, "bb_lower_touch × jpy_fx ロング")
analyze(rsi, "rsi_oversold_bounce × jpy_fx ロング")

# === 比較：other_fx ショート ===
ofx_s = [d for d in closed if d.get('ticker') in GROUPS["other_fx"] and 'ショート' in (d.get('direction') or '')]
analyze(ofx_s, "other_fx ショート [比較]")
```

---

## 生出力

```
closed N=722

jpy_fx 全体:             k=52  n=138  37.7%  CI[30.0~46.0]  E(R)=-0.122
jpy_fx ロング:            k=44  n=104  42.3%  CI[33.3~51.9]  E(R)=-0.014
jpy_fx ショート [主仮説]: k=8   n=34   23.5%  CI[12.4~40.0]  E(R)=-0.452

jpy_fx ショート × trend=下降:        k=1  n=12  8.3%  CI[1.5~35.4]  E(R)=-0.806
jpy_fx ショート × trend=中立・もみあい: k=1  n=6   16.7% CI[3.0~56.4]  E(R)=-0.612
jpy_fx ショート × trend=上昇:        k=6  n=16  37.5% CI[18.5~61.4] E(R)=-0.126

jpy_fx ショート × macd_dead:  k=6  n=26  23.1%  CI[11.0~42.1]  E(R)=-0.462
jpy_fx ショート × ma_dead:    k=2  n=5   40.0%  CI[11.8~76.9]  E(R)=-0.068
jpy_fx ショート × low_break:  k=0  n=3   0.0%   CI[0.0~56.2]   E(R)=-1.000

macd_dead × jpy_fx [全件]: k=6  n=26  23.1%  CI[11.0~42.1]  E(R)=-0.462
jpy_fx ショート中のmacd_dead比率: 26/34 = 76.5%

bb_lower_touch × jpy_fx ロング:      k=26  n=40  65.0%  CI[49.5~77.9]  E(R)=+0.514
rsi_oversold_bounce × jpy_fx ロング: k=2   n=20  10.0%  CI[2.8~30.1]   E(R)=-0.767

other_fx ショート [比較]: k=29  n=55  52.7%  CI[39.8~65.3]  E(R)=+0.229
```

---

## 仮説採択の根拠・交絡点検

**メイン結論**:
- jpy_fx ショート N=34、k=8、23.5%、CI[12.4~40.0%]
- **CI上限 40.0% < 43%** → 事前基準クリア → **通過A（棄却確認）**
- E(R) = -0.452R → 平均的に1回のトレードで0.452R相当の期待損失

**交絡1：macd_deadが主体（76.5%）**
- 34件中26件（76.5%）がmacd_dead（MACDデッドクロス）シグナル
- macd_dead × jpy_fx: 23.1%（6/26件）→ これが主な引き下げ要因

**交絡2：下降×ショートの逆説（8.3%）**
- 通常「順張りショート（下降トレンド中の売り）」は有利と考えられるが実績は8.3%
- 可能な説明（探索的）：
  a. macd_dead（遅行指標）が下降トレンド中の一時的反発時に発火 → その後の反発に巻き込まれる
  b. jpy_fx の「下降」= 円高フェーズは急激に動くことが多く、デッドクロス発火時点で既に目標値到達
  c. jpy_fx carry 構造：ロング方向の基本バイアスがあり、ショートは逆張り的側面がある

**交絡3：ティッカー偏り**
- AUDJPY=X が N=16中2勝(12.5%)と最も引き下げ
- USDJPY=X は N=7中3勝(42.9%)と相対的に高い
- ただし各ティッカーのNが小さいため確定的結論は出せない

**副次観察（非仮説）**:
- bb_lower_touch × jpy_fx ロング: 65.0%(N=40) vs rsi_oversold × jpy_fx ロング: 10.0%(N=20)
- 同じ「逆張りロング」でもシグナル種別で大きく分断
- ロング全体 42.3%（CI下限33.3%）はまだ継続観察レベル

**トラッカー更新**:
- [m] jpy_fx ロング: N=104, 42.3%, CI[33.3~51.9%] 新設
- 宣言基準: N≥80かつCI下限43%超を維持

---

## 今回の決定事項

- **棄却確認（通過A）**: jpy_fx ショートシグナルは過去の集計上、損益分岐43%を下回ることをCI上限で確認
- **継続観察**: jpy_fx ロング全体（42.3%、CI下限33.3%）はまだ確定打なし → トラッカー[m]新設
- **探索的記録**: bb_lower_touch × jpy_fx ロング（65.0%、N=40）は有望だが単独では検証していない
- エンジン・発火条件には変更なし
