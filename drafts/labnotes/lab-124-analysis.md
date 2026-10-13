# lab-124 分析ノート — rl_tf_adx_strong（順張り×ADX強）

**日付**: 2026-10-14  
**仮説ID**: rl_tf_adx_strong  
**ラベル**: 順張り×ADX強(25以上)(回避)  
**登録日**: 2026-09-26  
**種類**: gate（回避仮説）  

---

## 仮説の意味

ADX（Average Directional Index：方向性指数）は0〜100でトレンドの強さを表す指標。
25以上で「強いトレンドあり」と一般に言われる。

**仮説**: 「トレンドが強い場面（ADX≥25）での順張りシグナル（高値・安値ブレイク、MACD/MA クロス）は、勝率が低く、回避すべき」

逆説的に思えるが、強いトレンド相場では「すでに動き切った」後に乗ることになりやすい。また強いトレンドはVIX上昇・急落局面とも重なりやすい。

---

## フィルタ定義

```
family = 'tf'（順張り族: high_break/low_break/macd_golden/macd_dead/ma_golden/ma_dead）
adx_band = 'strong'（ADX≥25）
```

ADX帯の分類:
- 'strong': ADX≥25（強いトレンド）
- 'mid': ADX 20〜25
- 'weak': ADX<20（弱いトレンド）

---

## 集計スクリプト

```python
import json, math
from signal_lab_verify import closed, win, wilson, family_of, adx_band_of

with open('signals-log.json') as f:
    raw = json.load(f)

closed_list = [d for d in raw if closed(d)]

def fired_date(d):
    return d.get('fired_at', '')[:10]

def count(filters):
    result = []
    for d in closed_list:
        ok = True
        for k, v in filters.items():
            if k == 'fired_before':
                if fired_date(d) >= v: ok = False; break
            elif k == 'fired_from':
                if fired_date(d) < v: ok = False; break
            elif k == 'family':
                if family_of(d) != v: ok = False; break
            elif k == 'adx_band':
                if adx_band_of(d) != v: ok = False; break
            else:
                ok = False; break
        if ok:
            result.append(d)
    k = sum(1 for d in result if win(d))
    n = len(result)
    return k, n

cases = [
    ('全体IS', {'fired_before':'2026-09-26'}),
    ('順張りIS', {'family':'tf','fired_before':'2026-09-26'}),
    ('順張り×ADX強IS', {'family':'tf','adx_band':'strong','fired_before':'2026-09-26'}),
    ('順張り×ADX弱IS', {'family':'tf','adx_band':'weak','fired_before':'2026-09-26'}),
    ('全体FWD', {'fired_from':'2026-09-26'}),
    ('順張りFWD', {'family':'tf','fired_from':'2026-09-26'}),
    ('順張り×ADX強FWD', {'family':'tf','adx_band':'strong','fired_from':'2026-09-26'}),
    ('順張り×ADX弱FWD', {'family':'tf','adx_band':'weak','fired_from':'2026-09-26'}),
]
for label, filt in cases:
    k, n = count(filt)
    if n > 0:
        lo, hi = wilson(k, n)
        print(f'{label}: k={k}, n={n}, pct={k/n*100:.1f}%, CI=[{lo:.1f}%~{hi:.1f}%]')
```

---

## 実行結果

```
全体IS: k=2071, n=4825, pct=42.9%, CI=[41.5%~44.3%]
順張りIS: k=1056, n=2478, pct=42.6%, CI=[40.7%~44.6%]
順張り×ADX強IS: k=443, n=1069, pct=41.4%, CI=[38.5%~44.4%]
順張り×ADX弱IS: k=376, n=847, pct=44.4%, CI=[41.1%~47.8%]
全体FWD: k=136, n=372, pct=36.6%, CI=[31.8%~41.6%]
順張りFWD: k=62, n=203, pct=30.5%, CI=[24.6%~37.2%]
順張り×ADX強FWD: k=20, n=71, pct=28.2%, CI=[19.0%~39.5%]
順張り×ADX弱FWD: k=33, n=92, pct=35.9%, CI=[26.8%~46.1%]
```

---

## トラッカーデータ（signal-lab-tracker.json）

```
rl_tf_adx_strong:
  forward.k = 19, n = 70 (※直接計算では k=20, n=71 → 1件差。asof差と思われる)
  pct = 27.1%
  avgR = -0.367（1回あたり平均で、損切り幅の0.37倍の損）
  R-CI = [-0.585, -0.148]（上端も0を下回る）
  status = tracking
  promote_strikes = 0
  promote_min_n = 80（昇格に必要な前向き件数）
```

※記事では直接計算値（k=20, n=71）を使用。signal_lab_verify.py が同じ計算をするため。

---

## 解釈メモ

1. **IS期（登録前）**: 全体42.9%に対し、順張り×ADX強は41.4%。差は1.5ptで大きくない。
2. **FWD期（前向き、2026-09-26〜）**: 全体36.6%に対し、順張り×ADX強は28.2%。差8.4pt。
   - さらに順張り×ADX弱（35.9%）と比べても7.7pt下。
3. **avgR = -0.367, R-CI = [-0.585, -0.148]**: R-CIの上端（-0.148）も0未満 → 損する方向が偶然とは言いにくい。
4. **n=71 < 80（昇格閾値）**: まだ前向き期間18日。昇格判断にはあと9件（最低）必要。
5. **FWD全体が不調**: この期間は全銘柄が勝率36.6%と低調（IS比-6.3pt）。ADX強の弱さはこの環境悪化の上乗せか？→ 判断保留、継続観察が必要。

---

## 損益分岐との比較

損益分岐勝率 = 43%（breakeven_pct in tracker）

| 区分 | 勝率 | 損益分岐比 |
|---|---|---|
| 全体IS | 42.9% | わずかに下回る |
| 順張り×ADX強IS | 41.4% | 下回る |
| 全体FWD | 36.6% | 大きく下回る |
| 順張り×ADX強FWD | 28.2% | 大きく下回る |
| 順張り×ADX弱FWD | 35.9% | 下回る |

前向き結果はいずれも損益分岐を下回っているが、ADX強は特に低い。

---

## 記事で使う数値（確認済み）

- 全体IS: 42.9%（k=2071/n=4825）
- 順張りIS: 42.6%（k=1056/n=2478）
- 順張り×ADX強IS: 41.4%（k=443/n=1069）
- 順張り×ADX弱IS: 44.4%（k=376/n=847）
- 全体FWD: 36.6%, CI=[31.8%~41.6%]（k=136/n=372）
- 順張りFWD: 30.5%, CI=[24.6%~37.2%]（k=62/n=203）
- 順張り×ADX強FWD: **28.2%, CI=[19.0%~39.5%]**（k=20/n=71）← 主役
- 順張り×ADX弱FWD: 35.9%, CI=[26.8%~46.1%]（k=33/n=92）
- avgR=-0.367, R-CI=[-0.585~-0.148]
