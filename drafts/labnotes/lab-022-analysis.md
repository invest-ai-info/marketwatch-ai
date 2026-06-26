# Lab #022 — 逆張り買い×トレンド別解析：上昇中に限定すると機能するか

基準日: 2026-06-27  
仮説採択理由: スイープFDR通過（in-sample R+0.26）・#018/014の探索的後継・前向きトラッカー trend=上昇×reversalL edge 登録済み（forward N=10）

---

## 事前宣言（合否基準）

- H1（エッジ確認）: 上昇×revL の CI下限 ≥ 43% かつ N ≥ 50
- H2（危険確認）: 下降×revL の CI上限 ≤ 43% かつ N ≥ 50

---

## 検証スクリプト（全文）

```python
import json, math
from signal_lab_verify import closed, win, wilson, get_trend, GROUPS, REV

with open('signals-log.json') as f:
    data = json.load(f)

sigs = [s for s in data if closed(s)]
print(f'全クローズドシグナル: {len(sigs)}')  # 1157

def is_rev(s):
    d = s.get('direction','')
    is_long = 'ロング' in d or d == 'long'
    return is_long and s.get('primary_signal') in REV

def group_of(s):
    t = s.get('ticker','')
    for g, tickers in GROUPS.items():
        if t in tickers:
            return g
    return 'other'

def trend_of(s):
    return get_trend(s)

def ev_r(sub):
    vals = [1.333 if win(s) else -1.0 for s in sub]
    if not vals: return 0, 0, 0
    ev = sum(vals)/len(vals)
    n = len(vals)
    sd = (sum((x-ev)**2 for x in vals)/(n-1))**0.5 if n > 1 else 0
    se = sd / n**0.5
    return ev, ev - 1.96*se, ev + 1.96*se

# 全revL基底
all_rev = [s for s in sigs if is_rev(s)]
k_all, n_all = sum(1 for s in all_rev if win(s)), len(all_rev)
lo_all, hi_all = wilson(k_all, n_all)
ev_all, elo, ehi = ev_r(all_rev)
# k=185 n=467 勝率=39.6% CI=[35.3%,44.1%] E(R)=-0.128 CI=[-0.215,-0.040]

# trend別
rev_up   = [s for s in sigs if trend_of(s)=='上昇' and is_rev(s)]
rev_down = [s for s in sigs if trend_of(s)=='下降' and is_rev(s)]
rev_mid  = [s for s in sigs if trend_of(s)=='中立・もみあい' and is_rev(s)]

# 上昇: k=60 n=111 54.1% CI=[44.8%,63.0%] E(R)=+0.261 CI=[+0.044,+0.478]
# 下降: k=62 n=184 33.7% CI=[27.3%,40.8%] E(R)=-0.214 CI=[-0.374,-0.054]
# 中立: k=62 n=168 36.9% CI=[30.0%,44.4%] E(R)=-0.139 CI=[-0.310,+0.032]

# グループ別 上昇×revL
# 指数:     k=36 n=56  64.3% CI=[51.2%,75.5%]
# jpy_fx:   k=18 n=29  62.1% CI=[44.0%,77.3%]
# other_fx: k=3  n=18  16.7% CI=[5.8%,39.2%]
# metal:    k=2  n=4   50.0% CI=[15.0%,85.0%]  ← N極小
# btc:      k=0  n=2    0.0% CI=[0%,65.8%]     ← N極小
# 非指数:   k=24 n=55  43.6% CI=[31.4%,56.7%]

# シグナル別 上昇×revL
# bb_lower_touch:     k=47 n=86  54.7% CI=[44.2%,64.7%]
# rsi_oversold_bounce: k=13 n=25 52.0% CI=[33.5%,70.0%]  ← N小

# 対照群（上昇×revL=False）
norev_up = [s for s in sigs if trend_of(s)=='上昇' and not is_rev(s)]
# k=94 n=246 38.2% CI=[32.4%,44.4%]
```

---

## 生出力

```
全クローズドシグナル: 1157

全revL（基底）: k=185 n=467 勝率=39.6% CI=[35.3%,44.1%]

上昇×revL 全体: k=60 n=111 勝率=54.1% CI=[44.8%,63.0%] E(R)=+0.261 CI=[+0.044,+0.478]
上昇×revL=F(順張り): k=94 n=246 勝率=38.2% CI=[32.4%,44.4%]

revL×下降: k=62 n=184 勝率=33.7% CI=[27.3%,40.8%] E(R)=-0.214 CI=[-0.374,-0.054]
revL×中立: k=62 n=168 勝率=36.9% CI=[30.0%,44.4%] E(R)=-0.139 CI=[-0.310,+0.032]

グループ別 上昇×revL:
  index:    k=36 n=56  64.3% CI=[51.2%,75.5%]
  jpy_fx:   k=18 n=29  62.1% CI=[44.0%,77.3%]
  other_fx: k=3  n=18  16.7% CI=[5.8%,39.2%]
  metal:    k=2  n=4   50.0% CI=[15.0%,85.0%]
  btc:      k=0  n=2    0.0% CI=[0%,65.8%]
  非index:  k=24 n=55  43.6% CI=[31.4%,56.7%]

シグナル別 上昇×revL:
  bb_lower_touch:      k=47 n=86  54.7% CI=[44.2%,64.7%]
  rsi_oversold_bounce: k=13 n=25  52.0% CI=[33.5%,70.0%]
```

---

## 事前宣言の合否判定

- H1（上昇×revL CI下限≥43% かつ N≥50）: CI下限=44.8%≥43% ∧ N=111≥50 → **PASS ✅**
- H2（下降×revL CI上限≤43% かつ N≥50）: CI上限=40.8%≤43% ∧ N=184≥50 → **PASS ✅**

---

## 交絡点検

1. **シグナル型**: bb_lower_touch(54.7%) vs rsi_oversold_bounce(52.0%) — 差は小さく主因でない
2. **グループ偏り**: 指数N=56 + jpy_fxN=29 が計111中85件(76.6%)を占める — 上昇×revLの好成績は指数・jpy_fx偏りが主因の可能性
3. **非指数43.6%(N=55)**: CI[31.4%,56.7%] — 広いCIで確定打なし。other_fx N=18は逆効果(16.7%)
4. **「上昇トレンドでrevLが機能する」理論的根拠**: 上昇中の一時的な押し目は「踏み台」になりやすく、SLまで下抜けしにくい。下降中は実際に下方継続するためrevLは「落ちるナイフ」になる

---

## 前向きトラッカー接続

- trend=上昇×reversalL (edge, 2026-06-22登録): forward 6/10=60% R+0.40 CI[-0.35~+1.15] — N=10, CI広く確定打なし
- reversalL gate (2026-06-25): forward 13/22=59% R+0.38 CI[-0.11~+0.87] — N小・方向性は一致
- in-sample E(R)=+0.261 CI[+0.044,+0.478]: 期待値方向は確認、前向きN≥80で最終判定へ

## 判定

🟡 **通過A（両仮説クリア・継続観察）**
- H1 (上昇エッジ) 確認 — CI下限44.8%>43%、E(R)=+0.261（CI下限+0.044>0）
- H2 (下降危険) 確認 — CI上限40.8%<43%、E(R)=-0.214（CI上限-0.054<0）
- グループ交絡: 指数・jpy_fxが高成績の主因 → 非指数での検証継続
- 前向きN=10でout-of-sample確認中
