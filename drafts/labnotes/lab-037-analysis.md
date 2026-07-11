# Lab-037 分析メモ

## 基準日
2026-07-12 JST（次番号037）

## 仮説採択プロセス

### スイープ・トラッカー更新結果（2026-07-12）
- `python signal_lab_tracker.py update --date 2026-07-12` 実行
- `python signal_lab_sweep.py --json drafts/labnotes/sweep-2026-07-12.json` 実行
- FDR通過5本（全既登録・新規なし）
- ✅昇格/⛔反証 新発生なし

### 本日の優先度判定
- 優先度②：前向きで大きく動いた仮説
- 選定: `trend=中立・もみあい × reversal_long` gate（tracker ID: trend_neutral_revl）
  - 登録日: 2026-06-19
  - 前向き現在値: 28/48=58.3% E(R)=+0.361 CI[-0.04~+0.76]
  - IS当初観察: 48/146=32.9%（損益分岐明確割れでgate登録）
  - **急改善要因の解析が本日の題材**

---

## 検証スクリプト（Python反実仮想集計）

```python
import json, math
from signal_lab_verify import closed, win, match, compute, get_trend, wilson

with open('signals-log.json') as f:
    data = json.load(f)

FWD_DATE = "2026-06-19"

def R_stats_fwd(data, filt, fwd_date=None):
    def date_ok(d):
        if fwd_date is None: return True
        return d.get("fired_at", "") >= fwd_date
    rows = [d for d in data if closed(d) and match(d, filt) and date_ok(d)]
    n = len(rows)
    if n == 0: return 0, 0, 0.0, (0.0, 0.0), 0.0, (0.0, 0.0)
    k = sum(1 for d in rows if win(d))
    pct = k/n*100
    ci = wilson(k, n)
    R = []
    for d in rows:
        o = d.get('outcome')
        if o == 'tp1': R.append(2.0)
        elif o == 'tp2': R.append(4.0)
        elif o == 'sl': R.append(-1.5)
    avgR = sum(R)/len(R) if R else 0.0
    if len(R) > 1:
        std = math.sqrt(sum((r-avgR)**2 for r in R)/(len(R)-1))
        se = std/math.sqrt(len(R))
        rci = (avgR - 1.96*se, avgR + 1.96*se)
    else:
        rci = (avgR, avgR)
    return k, n, pct, ci, avgR, rci
```

---

## 生出力

### トレンド3分類×revL 全期間比較
```
trend=上昇 × revL:       82/151=54.3%  CI[46.4%~62.0%] E(R)=+0.401
trend=下降 × revL:       87/224=38.8%  CI[32.7%~45.4%] E(R)=-0.141
trend=中立・もみあい × revL: 76/194=39.2%  CI[32.6%~46.2%] E(R)=-0.129
```

### IS vs FWD 比較（中立×revL）
```
IS(~2026-06-18前): 48/146=32.9%
FWD(2026-06-19~): 28/48=58.3% CI[44.3%~71.2%] E(R)=+0.542 CI[+0.048~+1.035]
全期間: 76/194=39.2% CI[32.6%~46.2%]
```
※ trackerのE(R)は+0.361 CI[-0.04~+0.76]（tracker算定方式の違いによる差異あり）

### グループ別（中立×revL）全期間
```
index:    20/45=44.4%  CI[30.9%~58.8%]  E(R)=+0.056
jpy_fx:   18/49=36.7%  CI[24.7%~50.7%]  E(R)=-0.214
other_fx: 30/69=43.5%  CI[32.4%~55.2%]  E(R)=+0.022
metal:     4/9=44.4%   CI[18.9%~73.3%]  E(R)=+0.056
btc:       2/17=11.8%  CI[3.3%~34.3%]   E(R)=-1.088
```

### グループ別 IS→FWD 比較（中立×revL）
```
index:    IS 11/29=37.9% → FWD  9/16=56.2% E(R)=+0.469 (+18.3pp)
jpy_fx:   IS 14/39=35.9% → FWD  4/10=40.0% E(R)=-0.100 (+4.1pp、最小)
other_fx: IS 18/52=34.6% → FWD 12/17=70.6% E(R)=+0.971 (+36.0pp、最大・主ドライバー)
metal:    IS  2/5=40.0%  → FWD  2/4=50.0%  E(R)=+0.250 (+10.0pp)
btc:      IS  1/16=6.2%  → FWD  1/1=100.0% E(R)=+2.000 (N=1、無意味)
```

### シグナル種別（全期間、中立×revL系）
```
rsi_oversold_bounce (dir=long): 29/76=38.2%  CI[28.1%~49.4%]  E(R)=-0.164
bb_lower_touch (dir=long):      47/118=39.8%  CI[31.5%~48.8%]  E(R)=-0.106
```

### シグナル種別 FWD（中立×revL）
```
rsi_oversold_bounce: 9/11=81.8%  CI[52.3%~94.9%]  E(R)=+1.364
bb_lower_touch:      19/37=51.4%  CI[35.9%~66.6%]  E(R)=+0.297
```

### 指数×中立 signal別（全期間）
```
index×中立×rsi_oversold_bounce: 14/21=66.7%  CI[45.4%~82.8%]
index×中立×bb_lower_touch:       6/24=25.0%  CI[12.0%~44.9%]
→ 41.7pp差（同グループ・同トレンドでシグナルにより真逆）
```

### 時間足別（全期間、中立×revL）
```
tf=1h: 47/111=42.3%  CI[33.6%~51.6%]  E(R)=-0.018
tf=4h: 26/79=32.9%   CI[23.6%~43.9%]  E(R)=-0.348
```

### 対照群
```
中立×dir=long (全シグナル):  151/372=40.6%  CI[35.7%~45.7%]
中立×dir=short (全シグナル): 52/113=46.0%   CI[37.1%~55.2%]
revL全体(全期間):            246/573=42.9%   CI[38.9%~47.0%]
中立×revL全体(全期間):       76/194=39.2%
```

### other_fx × 中立 signal別（全期間）
```
other_fx×中立×rsi: 7/19=36.8%
other_fx×中立×bb:  23/50=46.0%
```

---

## 検証まとめ・交絡点検

### 主な発見
1. IS(~2026-06-18) 48/146=32.9% → FWD(2026-06-19~) 28/48=58.3%の急改善（+25.4pp）
2. **主ドライバー**: other_fx IS34.6%→FWD70.6%（+36pp・FWD N=17・17件中12件勝利）
3. **指数も改善**: IS37.9%→FWD56.2%（+18.3pp）
4. **jpy_fxは最小改善**: IS35.9%→FWD40.0%（+4.1pp・jpy_fxのrevLはもともと弱い）
5. **シグナル非対称**: FWD rsi=81.8%(N=11小) vs bb=51.4%(N=37)
6. **指数内シグナル逆転**: index×rsi=66.7% vs index×bb=25.0%（IS、41.7pp差）
7. **4h足が弱い**: 中立×revL×4h=32.9% vs 1h=42.3%（#015の4H弱さ継続）
8. **btcの壊滅**: IS 1/16=6.2%（ただしFWDはN=1で無視）

### 交絡点検（主因の特定）
- other_fxがFWD改善の主ドライバーは確実（17件中12件=70.6%）
- 金属（metal）は IS40.0%→FWD50.0%（改善中だが N小でブレ大）
- 全体のFWD改善はother_fx主導＋指数改善の合算

### 前向きトラッカー状態
- 現在値: 28/48=58.3% E(R)=+0.361 CI[-0.04~+0.76]
- CI下限が-0.04でわずかにマイナス → ⛔反証確定には至らず
- 🏁ホールドアウト該当なし（N≥80基準、現在N=48）
- N=80到達でCI判定・昇格/反証の最終判断

### 事前宣言（今回は記録のみ・正式検証ではない）
- IS期間での損益分岐割れ確認：48/146=32.9% ✅（gate登録の根拠）
- FWD改善の解析：58.3%で+25.4pp改善を確認
- 主因確認：other_fx主導・jpy_fxは最小改善・btc壊滅の継続観察
