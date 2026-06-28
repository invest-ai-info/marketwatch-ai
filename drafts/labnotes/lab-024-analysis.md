# lab-024 分析ノート
## 仮説
円クロス（jpy_fx: USDJPY/EURJPY/GBPJPY/AUDJPY）での
RSI売られすぎ逆張り買い（rsi_oversold_bounce）は
損益分岐43%を有意に下回るか。

## 事前宣言基準
- H1: CI上限 < 43%（損益分岐割れ確認）
- H2: N ≥ 20
→ 両条件クリアで「通過A（棄却確認）」と判定

## Pythonスクリプト全文

```python
import json, sys, math
sys.path.insert(0, '/home/user/marketwatch-ai')
from signal_lab_verify import closed, win, match, compute, wilson, GROUPS, REV, ALLOWED_FILTER_KEYS

log = json.load(open('/home/user/marketwatch-ai/signals-log.json', encoding='utf-8-sig'))
cl = [s for s in log if closed(s)]

def pct(w, n): return f"{w/n*100:.1f}%" if n else "N/A"
def ci_str(w, n):
    lo, hi = wilson(w, n)  # already in %
    return f"CI[{lo:.1f}%~{hi:.1f}%]"
def ev_r(w, n):
    if n == 0: return "N/A"
    p = w/n
    return f"{p * 1.33 - (1-p):.3f}R"

# ---- 核心仮説 ----
flt_main = {'group': 'jpy_fx', 'signal': 'rsi_oversold_bounce'}
m = [s for s in cl if match(s, flt_main)]
w = sum(1 for s in m if win(s))
print(f"jpy_fx × rsi_oversold_bounce: {w}/{len(m)} = {pct(w,len(m))} {ci_str(w,len(m))} E(R)={ev_r(w,len(m))}")

# direction
for d in ['long', 'short']:
    flt2 = {'group': 'jpy_fx', 'signal': 'rsi_oversold_bounce', 'direction': d}
    m2 = [s for s in cl if match(s, flt2)]
    w2 = sum(1 for s in m2 if win(s))
    print(f"  {d}: {w2}/{len(m2)} = {pct(w2,len(m2))} {ci_str(w2,len(m2))}")

# trend
for tr in ['上昇', '下降', '中立・もみあい']:
    flt3 = {'group': 'jpy_fx', 'signal': 'rsi_oversold_bounce', 'trend': tr}
    m3 = [s for s in cl if match(s, flt3)]
    w3 = sum(1 for s in m3 if win(s))
    print(f"  trend={tr}: {w3}/{len(m3)} = {pct(w3,len(m3))} {ci_str(w3,len(m3))}")

# tf
for tf in ['1h', '4h']:
    flt4 = {'group': 'jpy_fx', 'signal': 'rsi_oversold_bounce', 'tf': tf}
    m4 = [s for s in cl if match(s, flt4)]
    w4 = sum(1 for s in m4 if win(s))
    print(f"  tf={tf}: {w4}/{len(m4)} = {pct(w4,len(m4))} {ci_str(w4,len(m4))}")

# 比較対照群
flt_bb = {'group': 'jpy_fx', 'signal': 'bb_lower_touch'}
m_bb = [s for s in cl if match(s, flt_bb)]
w_bb = sum(1 for s in m_bb if win(s))
print(f"\njpy_fx × bb_lower_touch: {w_bb}/{len(m_bb)} = {pct(w_bb,len(m_bb))} {ci_str(w_bb,len(m_bb))} E(R)={ev_r(w_bb,len(m_bb))}")
for tf in ['1h', '4h']:
    flt4 = {'group': 'jpy_fx', 'signal': 'bb_lower_touch', 'tf': tf}
    m4 = [s for s in cl if match(s, flt4)]
    w4 = sum(1 for s in m4 if win(s))
    print(f"  tf={tf}: {w4}/{len(m4)} = {pct(w4,len(m4))} {ci_str(w4,len(m4))}")

# RSI グループ別
print("\n--- rsi_oversold_bounce グループ別 ---")
for g in ['metal', 'index', 'jpy_fx', 'other_fx', 'btc', 'oil']:
    flt_g = {'group': g, 'signal': 'rsi_oversold_bounce'}
    m_g = [s for s in cl if match(s, flt_g)]
    w_g = sum(1 for s in m_g if win(s))
    print(f"  {g}: {w_g}/{len(m_g)} = {pct(w_g,len(m_g))} {ci_str(w_g,len(m_g))} E(R)={ev_r(w_g,len(m_g))}")
```

## 生出力

```
closed件数: 1163

jpy_fx × rsi_oversold_bounce: 6/31 = 19.4% CI[9.2%~36.3%] E(R)=-0.549R
  long: 6/31 = 19.4% CI[9.2%~36.3%]
  short: 0/0 = N/A CI[0.0%~100.0%]
  trend=上昇: 2/2 = 100.0% CI[34.2%~100.0%]
  trend=下降: 1/7 = 14.3% CI[2.6%~51.3%]
  trend=中立・もみあい: 3/22 = 13.6% CI[4.7%~33.3%]
  tf=1h: 3/24 = 12.5% CI[4.3%~31.0%]
  tf=4h: 3/7 = 42.9% CI[15.8%~75.0%]

jpy_fx × bb_lower_touch: 32/55 = 58.2% CI[45.0%~70.3%] E(R)=+0.356R
  tf=1h: 25/34 = 73.5% CI[56.9%~85.4%]
  tf=4h: 7/20 = 35.0% CI[18.1%~56.7%]

--- rsi_oversold_bounce グループ別 ---
  metal: 6/38 = 15.8% CI[7.4%~30.4%]
  index: 24/40 = 60.0% CI[44.6%~73.7%] E(R)=+0.398R
  jpy_fx: 6/31 = 19.4% CI[9.2%~36.3%] E(R)=-0.549R
  other_fx: 19/50 = 38.0% CI[25.9%~51.8%]
  btc: 5/17 = 29.4% CI[13.3%~53.1%]
  oil: 10/16 = 62.5% CI[38.6%~81.5%]
```

## 事前宣言の照合

| 基準 | 結果 | 判定 |
|---|---|---|
| H1: CI上限 < 43% | 36.3% < 43% | ✅ クリア |
| H2: N ≥ 20 | 31 ≥ 20 | ✅ クリア |

→ **通過A（棄却確認）**

## 交絡確認

- **方向偏り**: 全31件がロング（ショート0件）— rsi_oversold_bounceシグナルの定義上（逆張り買い）
- **トレンド偏り**: 中立・もみあいが22/31=71%を占める。中立×RSI=13.6%（3/22）が主体的な失敗パターン
- **時間足偏り**: 1hが24/31=77%を占める。1h×RSI=12.5%（3/24）が中心
- **BB比較**: 同じjpy_fx・同じ「逆張り買い」でもBB下限タッチは58.2%（32/55）。差は38.8pp
- **グループ比較**: 同じRSI逆張りでも指数=60.0%（24/40）。差は40.6pp

## 含意

RSI「売られすぎ」は「本当に売られすぎ（強制ロスカット水準）」か「トレンドの初動」かを
区別できない。円クロスFXは流動性高く、一方向トレンドが長続きしやすい市場構造のため、
RSI=30付近は「底値」ではなく「下落継続の途中」であることが多い。
一方BBは「相場の価格帯幅に対する相対位置」を見るため、
同じ「逆張り」でも意味が異なる可能性がある。

## tracker update 要点（2026-06-29）

- 指数×ロング: ✅昇格 N=96（+6件）、E(R)=+0.313 CI[+0.08~+0.55] — 前回#021からの継続昇格状態
- rsi_oversold_bounce(全足): 前向き 18/59=30% E(R)=-0.288 CI[-0.56~-0.01] — 蓄積中
- sweep: FDR通過19本（新候補なし）
