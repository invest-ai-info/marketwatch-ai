# lab-004-analysis.md
# AIシグナル研究日誌 #004 — 検証生ログ（人間の数字照合用）
# 基準日: 2026-06-12 (UTC 22:59 → JST 07:59)

---

## 【使用スクリプト全文】

```python
import json, math

def wilson_ci(k, n, z=1.96):
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    denom = 1 + z*z/n
    center = (p + z*z/(2*n)) / denom
    pm = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / denom
    return (max(0, center - pm), min(1, center + pm))

data = json.load(open('signals-log.json'))

# =============================================
# メイン検証 #004: GC=F ロング vs ショートの差
# =============================================
gc = [d for d in data if d.get('ticker') == 'GC=F' and d.get('outcome') in ['tp1','tp2','sl']]

gc_long  = [d for d in gc if d.get('direction') and 'ロング'  in d.get('direction','')]
gc_short = [d for d in gc if d.get('direction') and 'ショート' in d.get('direction','')]

gc_long_wins  = sum(1 for d in gc_long  if d.get('outcome') in ['tp1','tp2'])
gc_short_wins = sum(1 for d in gc_short if d.get('outcome') in ['tp1','tp2'])

# Wilson CI
wilson_ci(gc_long_wins, len(gc_long))    # (0.0598, 0.2520)
wilson_ci(gc_short_wins, len(gc_short))  # (0.3857, 0.7971)

# 平均R:R = 1.333 (両方向とも同一)
# 期待値: ロング = 0.128*1.333 + 0.872*(-1) = -0.702R
#         ショート= 0.611*1.333 + 0.389*(-1) = +0.426R

# GC=F ショート × higher_tf_trend
short_by_trend:
  下降:          8/14 = 57.1%  CI[32.6%~78.6%]
  中立・もみあい: 3/4  = 75.0%  CI[30.1%~95.4%]

# GC=F ロング × higher_tf_trend
long_by_trend:
  下降:          5/42 = 11.9%  CI[5.2%~25.0%]
  中立・もみあい: 0/3  =  0.0%  CI[0.0%~56.2%]
  unknown:       1/2  = 50.0%  CI[9.5%~90.5%]

# GC=F ロング × timeframe
long_by_tf:
  1h:  1/28 = 3.6%  CI[0.6%~17.7%]
  4h:  5/19 = 26.3% CI[11.8%~48.8%]

# GC=F ロング × primary_signal
  bb_lower_touch:    2/20 = 10.0%
  rsi_oversold_bounce: 3/15 = 20.0%
  macd_golden:       1/8  = 12.5%
  fib_pullback_long: 0/3  =  0.0%
  high_break:        0/1  =  0.0%

# SI=F
si_long:  2/26 = 7.7%  CI[2.1%~24.1%]
si_short: 6/15 = 40.0% CI[19.8%~64.3%]
```

---

## 【生出力】（Python 実行結果、そのままコピー）

```
============================================================
【主検証 #004】GC=F の方向別成績
============================================================
GC=F 決済済み総計: N=65

=== 方向別 ===
ロング: 6/47 = 12.8%  CI[6.0, 25.2]
ショート: 11/18 = 61.1%  CI[38.6, 79.7]
direction=None: 0件

平均R:R(tp1/sl) ロング=1.333, ショート=1.333
期待値: ロング=-0.702R, ショート=0.426R

=== GC=F ショート × higher_tf_trend ===
  [下降] 8/14 = 57.1%  CI[32.6%~78.6%]
  [中立・もみあい] 3/4 = 75.0%  CI[30.1%~95.4%]

=== GC=F ロング内訳 ===
  [bb_lower_touch] 2/20 = 10.0%
  [rsi_oversold_bounce] 3/15 = 20.0%
  [macd_golden] 1/8 = 12.5%
  [fib_pullback_long] 0/3 = 0.0%
  [high_break] 0/1 = 0.0%

GC=F ロング × 時間足
  [1h] 1/28 = 3.6%  CI[0.6%~17.7%]
  [4h] 5/19 = 26.3%  CI[11.8%~48.8%]

GC=F ロング × higher_tf_trend
  [unknown] 1/2 = 50.0%  CI[9.5%~90.5%]
  [下降] 5/42 = 11.9%  CI[5.2%~25.0%]
  [中立・もみあい] 0/3 = 0.0%  CI[0.0%~56.2%]

============================================================
【補助検証】SI=F 方向別成績
============================================================
SI=F 決済済み: N=41
  ロング: 2/26 = 7.7%  CI[2.1%~24.1%]
  ショート: 6/15 = 40.0%  CI[19.8%~64.3%]

============================================================
【前向きトラッカー定点観測】
============================================================

[a] 押し目買い4h (2026-06-11以降の新規決済)
  2026-06-11以降の4h決済: 37件
  押し目買い4h: 3/5 (upper_tf_trend=上昇×逆張り条件は別途要確認)

[f] 全逆張りL (rsi_oversold_bounce / bb_lower_touch): 119/284 = 41.9%  CI[36.3%~47.7%]

[g] 指数全シグナル: 72/158 = 45.6%  CI[38.0%~53.3%]
  指数×逆張りL: 34/66 = 51.5%  CI[39.7%~63.2%]

[h] 他FX×逆張りL: 33/60 = 55.0%  CI[42.5%~66.9%]

============================================================
【GC=F ショート詳細一覧】
============================================================
  GC=F_1h_20260522_1324 | TF=1h | sig=macd_dead | trend=下降 | tp1
  GC=F_1h_20260527_1344 | TF=1h | sig=macd_dead | trend=中立・もみあい | sl
  GC=F_4h_20260527_2052 | TF=4h | sig=macd_dead | trend=下降 | tp1
  GC=F_4h_20260528_1348 | TF=4h | sig=macd_dead | trend=下降 | sl
  GC=F_1h_20260530_0439 | TF=1h | sig=macd_dead | trend=中立・もみあい | tp1
  GC=F_4h_20260602_0042 | TF=4h | sig=macd_dead | trend=下降 | sl
  GC=F_1h_20260603_0004 | TF=1h | sig=macd_dead | trend=中立・もみあい | tp1
  GC=F_1h_20260603_0659 | TF=1h | sig=fib_pullback_short | trend=中立・もみあい | tp1
  GC=F_4h_20260604_0501 | TF=4h | sig=fib_pullback_short | trend=下降 | sl
  GC=F_4h_20260605_0659 | TF=4h | sig=ma_dead | trend=下降 | tp1
  GC=F_4h_20260608_1427 | TF=4h | sig=low_break | trend=下降 | tp1
  GC=F_1h_20260608_1504 | TF=1h | sig=low_break | trend=下降 | sl
  GC=F_4h_20260610_0036 | TF=4h | sig=macd_dead | trend=下降 | tp1
  GC=F_4h_20260610_0435 | TF=4h | sig=low_break | trend=下降 | tp1
  GC=F_1h_20260610_0837 | TF=1h | sig=low_break | trend=下降 | tp1
  GC=F_4h_20260610_2051 | TF=4h | sig=low_break | trend=下降 | tp1
  GC=F_1h_20260610_2134 | TF=1h | sig=low_break | trend=下降 | sl
  GC=F_1h_20260611_1035 | TF=1h | sig=first_pullback_short | trend=下降 | sl

============================================================
【GC=F ロングの勝ち6件の内訳】
============================================================
  GC=F_20260520_1330 | TF=4h | sig=rsi_oversold_bounce | trend=N/A | outcome=tp1
  GC=F_1h_20260528_1418 | TF=1h | sig=bb_lower_touch | trend=下降 | outcome=tp1
  GC=F_4h_20260528_1452 | TF=4h | sig=rsi_oversold_bounce | trend=下降 | outcome=tp1
  GC=F_4h_20260529_0137 | TF=4h | sig=macd_golden | trend=下降 | outcome=tp1
  GC=F_4h_20260604_0819 | TF=4h | sig=bb_lower_touch | trend=下降 | outcome=tp1
  GC=F_4h_20260611_1407 | TF=4h | sig=rsi_oversold_bounce | trend=下降 | outcome=tp1
```

---

## 【照合チェックリスト（人間が確認）】

- [ ] GC=F 総件数 65 件（tp1/tp2/sl）を signals-log.json で目視確認
- [ ] ロング47件 / ショート18件 の合計 = 65 ✓
- [ ] ロング6勝の id リストを上記詳細と照合
- [ ] ショート×下降: 詳細一覧の "下降" かつ "tp1" を手数え → 8勝のはず
- [ ] Wilson CI の計算: k=6,n=47 → [6.0%,25.2%]; k=11,n=18 → [38.6%,79.7%]
- [ ] SVG 図の比例確認（棒グラフの幅が勝率に比例しているか）
- [ ] compliance-reviewer(Opus) 監査（断定表現チェック）
- [ ] 公開判断（人間）

---

## 【記事に使う数字の要約（labnotesからの転記リスト）】

| 変数 | 値 | 出典 |
|---|---|---|
| GC=F 決済済み総計 | N=65 | 生出力 |
| GC=F ロング勝率 | 12.8% (6/47) | 生出力 |
| GC=F ロング CI | [6.0%〜25.2%] | 生出力 |
| GC=F ショート勝率 | 61.1% (11/18) | 生出力 |
| GC=F ショート CI | [38.6%〜79.7%] | 生出力 |
| GC=F 期待値 ロング | -0.702R | 生出力 |
| GC=F 期待値 ショート | +0.426R | 生出力 |
| ショート×下降 勝率 | 57.1% (8/14) | 生出力 |
| ショート×下降 CI | [32.6%〜78.6%] | 生出力 |
| ロング×下降 勝率 | 11.9% (5/42) | 生出力 |
| ロング 1h 勝率 | 3.6% (1/28) | 生出力 |
| ロング 4h 勝率 | 26.3% (5/19) | 生出力 |
| SI=F ロング | 7.7% (2/26) | 生出力 |
| SI=F ショート | 40.0% (6/15) | 生出力 |
| 全逆張りL | 41.9% (119/284) | 生出力 |
| 指数×逆張りL | 51.5% (34/66) | 生出力 |
| 他FX×逆張りL | 55.0% (33/60) | 生出力 |
| 損益分岐 | 43% | 既定 |
