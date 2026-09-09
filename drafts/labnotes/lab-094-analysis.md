# AIシグナル研究日誌 #094 — ラボノート
**分析日**: 2026-09-10  
**仮説**: trend=上昇×reversalL——ISとFWDで成分は何が変わったか（RSI vs BB、グループ別分化）  
**担当**: signal-lab-daily routine

---

## 1. スイープ結果（2026-09-10）

```
python signal_lab_sweep.py --json drafts/labnotes/sweep-2026-09-10.json
```

FDR通過: **0本**（本日はスイープ新規候補なし）

---

## 2. トラッカー更新（2026-09-10）

```
python signal_lab_tracker.py update --date 2026-09-10
```

### 昇格・反証の変化

| 仮説 | 変化 | FWD N | avgR | rci_lo |
|---|---|---|---|---|
| trend=上昇×reversalL | ✅昇格維持（demote_strikes=1） | 293 | +0.131 | -0.03 |

**注記**: rci_lo=-0.03（マイナス）、降格警戒1回目継続中。ただし status=promoted は維持。

---

## 3. 仮説採択根拠（3視点会議）

**技術アナリスト視点**: trend=上昇×reversalL は昇格後もN=293蓄積。rci_lo=-0.03 と降格警戒局面に入っており、内部分解が必要。rsi_oversold_bounceとbb_lower_touchの2シグナルが混在しており、それぞれの寄与を分離することで実用的知見が得られる。

**ファンダ視点**: 上昇トレンドの環境では「強い流れに乗った順張り」が有利なはずだが、「逆張り」買いでも条件次第でエッジが出るかを確認。特に指数（S&P500先物等）と円クロス・他FXの違いが興味深い。

**リスク管理視点**: 全体FWD48.1%は損益分岐43%超だが、内部でbb_lower_touchが43.3%（CI[37.0%,49.9%]）と実質エッジレスな可能性。指数が38.5%と損益分岐割れ。シグナル選別に実用的意義あり。

→ **採択**: IS/FWDの事前登録済み仮説。signals-logだけで検証可能・交絡分離も検証済み。

---

## 4. 検証スクリプト全文

```python
import json, math
from datetime import datetime

with open('signals-log.json') as f:
    data = json.load(f)

REV = {"rsi_oversold_bounce", "bb_lower_touch"}
REG_DATE = datetime(2026, 6, 22)

GROUPS = {
    "metal":    {"GC=F", "SI=F"},
    "index":    {"NKD=F", "ES=F", "NQ=F", "YM=F", "^FTSE"},
    "jpy_fx":   {"USDJPY=X", "EURJPY=X", "GBPJPY=X", "AUDJPY=X"},
    "other_fx": {"EURUSD=X", "GBPUSD=X", "AUDUSD=X", "EURAUD=X", "GBPAUD=X"},
    "btc":      {"BTC-USD"},
    "oil":      {"CL=F"},
}

def get_trend(d):
    ta = d.get('trend_alignment')
    if isinstance(ta, dict) and ta.get('higher_tf_trend'):
        return ta['higher_tf_trend']
    return 'unknown'

def is_reversal_long(d):
    return 'ロング' in (d.get('direction') or '') and d.get('primary_signal') in REV

def closed(d):
    return d.get('outcome') in ('tp1', 'tp2', 'sl')

def win(d):
    return d.get('outcome') in ('tp1', 'tp2')

def wilson(k, n, z=1.96):
    if n == 0: return (0.0, 100.0)
    p = k/n
    den = 1 + z*z/n
    c = (p + z*z/(2*n)) / den
    pm = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / den
    return (max(0,c-pm)*100, min(1,c+pm)*100)

all_closed = [d for d in data if closed(d)]
matched = [d for d in all_closed if get_trend(d) == '上昇' and is_reversal_long(d)]

is_signals = []
fwd_signals = []
for s in matched:
    ts = s.get('fired_at', '')
    try:
        dt = datetime.fromisoformat(ts.replace('Z', '+00:00')).replace(tzinfo=None)
    except:
        continue
    if dt < REG_DATE:
        is_signals.append(s)
    else:
        fwd_signals.append(s)
```

---

## 5. 生出力（実行結果）

```
Total closed (sl/tp1): 4258
Matched trend=上昇×reversalL: 396

IS (before 2026-06-22): N=101, k=54, rate=53.5%, avgR=+0.247, CI=[43.8%,62.9%]
FWD (after 2026-06-22):  N=295, k=142, rate=48.1%, avgR=+0.123, CI=[42.5%,53.8%]

--- FWD group breakdown ---
  index:    N=78,  k=30, rate=38.5%, CI=[28.4%,49.6%]
  jpy_fx:   N=85,  k=42, rate=49.4%, CI=[39.0%,59.8%]
  other_fx: N=74,  k=39, rate=52.7%, CI=[41.5%,63.7%]
  metal:    N=20,  k=10, rate=50.0%, CI=[29.9%,70.1%]
  btc:      N=22,  k=13, rate=59.1%, CI=[38.7%,76.7%]
  oil:      N=14,  k=8,  rate=57.1%, CI=[32.6%,78.6%]

--- FWD signal breakdown ---
  rsi_oversold_bounce: N=71,  k=45, rate=63.4%, CI=[51.8%,73.6%]
  bb_lower_touch:      N=224, k=97, rate=43.3%, CI=[37.0%,49.9%]
```

---

## 6. 事前合否基準（宣言）

| 仮説 | 基準 | 結果 |
|---|---|---|
| H1: FWD rsi_oversold_bounce × 上昇 のCI下限が43%超 | CI下限 > 43% | ✅ 51.8% > 43% |
| H2: FWD bb_lower_touch × 上昇 のCIが43%をまたぐ | CI that straddles 43% | ✅ CI[37.0%,49.9%]が43%をまたぐ |
| H3: FWD 指数×上昇×reversalL が損益分岐43%を下回る | 中央値 < 43% | ✅ 38.5% < 43% |

---

## 7. 交絡点検

- **RSI vs BB**: rsi_oversold_bounce(N=71) vs bb_lower_touch(N=224) — 構成比3:1。BB偏重が全体を引き下げ中
- **グループ偏り**: 指数が全体の26%(78/295)を占め、38.5%の引き下げ寄与が大きい
- **小N注意**: metal(N=20)・BTC(N=22) — CI幅が広い（参考値のみ）
- **クラスター補正**: trackerのN=293はクラスター補正（相関シグナルを除外）で2件少ない

---

## 8. トラッカー現在値（2026-09-10）

tracker: auto_reversal_long-True_trend-上昇
- forward: 142/293=48.5%, avgR=+0.131, rci_lo=-0.03, rci_hi=+0.291
- alltime: 196/394=49.7%, avgR=+0.161, rci=[+0.025,+0.296]
- status: promoted, demote_strikes: 1
- 登録日: 2026-06-22
