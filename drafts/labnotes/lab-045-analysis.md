# AIシグナル研究日誌 #045 — 分析ノート

**基準日**: 2026-07-20 (JST)  
**総クローズ件数**: 1,845件  
**テーマ**: 指数グループ×ショートgate 前向き52.8%への逆転——IS 28.1%からの完全方向非対称逆転

---

## 1. 研究背景

### 経緯
- **#025 (2026-06-30)**: 指数×ショートの损益分岐割れ正式検証。in-sample 27.4%(17/62) CI上限39.6%<43%で通過A。前向きトラッカー[o] `group=index×dir=short（gate）` を2026-06-30に新設。
- **#044 (2026-07-19)**: 指数×ロング 前向き後半N=57で19.3% E(R)=-0.825崩落。降格ルール（2026-07-18新設）初日チェック。

### 今日の問い
トラッカー[o]登録から約20日経過。前向き期間の指数×ショート勝率はどう推移したか？  
そして#044の指数×ロング崩落と同時に、方向非対称は完全逆転したか？

---

## 2. データ収集スクリプト

```python
import json, math

def wilson_ci(k, n, z=1.96):
    z2 = z*z
    center = (k + z2/2) / (n + z2)
    margin = z * math.sqrt(k*(n-k)/n + z2/4) / (n + z2)
    return max(0, center - margin), min(1, center + margin)

def er(k, n):
    wr = k/n
    return wr * 1.333 - (1-wr) * 1.0

with open('signals-log.json') as f:
    data = json.load(f)

GROUPS = {
    'GC=F': 'metal', 'SI=F': 'metal',
    'CL=F': 'oil',
    'NKD=F': 'index', 'ES=F': 'index', 'NQ=F': 'index', 'YM=F': 'index', '^FTSE': 'index',
    'BTC-USD': 'btc',
    'USDJPY': 'jpy_fx', 'EURJPY': 'jpy_fx', 'GBPJPY': 'jpy_fx', 'AUDJPY': 'jpy_fx',
    'EURUSD': 'other_fx', 'GBPUSD': 'other_fx', 'AUDUSD': 'other_fx',
    'EURAUD': 'other_fx', 'GBPAUD': 'other_fx',
}

closed = [r for r in data if r.get('outcome') in ('tp1','tp2','sl')]
# Total: 1845

def get_group(r): return GROUPS.get(r.get('ticker',''), '')
def is_win(r): return r.get('outcome') in ('tp1','tp2')
def is_short(r): return 'ショート' in r.get('direction','')
def is_long(r): return 'ロング' in r.get('direction','')
def is_index(r): return get_group(r) == 'index'
def get_trend(r): return (r.get('trend_alignment') or {}).get('higher_tf_trend','')
```

---

## 3. 主要検証結果

### 全期間統計（IS+FWD合計）

| フィルター | k | n | 勝率 | 95%CI | E(R) |
|---|---|---|---|---|---|
| 指数×ショート 全期間 | 46 | 117 | 39.3% | [30.9%, 48.4%] | -0.08R |
| 指数×ロング 全期間（対照） | 154 | 333 | 46.2% | [41.0%, 51.6%] | +0.12R |
| 指数×S trend=上昇 | 28 | 77 | 36.4% | [26.5%, 47.5%] | -0.16R |
| 指数×S trend=下降 | 10 | 19 | 52.6% | [31.7%, 72.7%] | +0.36R |
| 指数×S trend=中立・もみあい | 8 | 20 | 40.0% | [21.9%, 61.3%] | -0.07R |
| 指数×S signal=macd_dead | 31 | 69 | 44.9% | [33.8%, 56.6%] | +0.05R |
| 指数×S signal=low_break | 8 | 32 | 25.0% | [13.3%, 42.1%] | -0.42R |
| 指数×S signal=ma_dead | 6 | 14 | 42.9% | [21.4%, 67.4%] | -0.04R |
| NKD=F ショート | 19 | 37 | 51.4% | [35.9%, 66.5%] | +0.20R |
| NQ=F ショート | 8 | 27 | 29.6% | [15.9%, 48.5%] | -0.31R |
| ES=F ショート | 10 | 23 | 43.5% | [25.6%, 63.2%] | +0.02R |
| YM=F ショート | 6 | 20 | 30.0% | [14.5%, 51.9%] | -0.30R |
| 指数×S tf=1h | 19 | 51 | 37.3% | [25.3%, 51.0%] | -0.13R |
| 指数×S tf=4h | 26 | 65 | 40.0% | [29.0%, 52.1%] | -0.07R |

### IS vs FWD 分断解析（tracker[o] 登録日 2026-06-30 基準）

| 期間 | 指数×ショート | 指数×ロング |
|---|---|---|
| IS期間（~2026-06-29） | 18/64 = 28.1% | IS = 54.0%（tracker-derived） |
| FWD期間（2026-06-30~） | 28/53 = 52.8%（tracker[o]） | FWD = 29.9%（tracker-derived） |
| 全期間 | 46/117 = 39.3% | 154/333 = 46.2% |

**KEY FINDING**: IS期間ではロング54%>ショート28%という強い方向優位があったが、  
前向き期間（2026-06-30以降）ではショート52.8%>ロング29.9%に**完全逆転**している。

### トラッカー[o] 現在値（2026-07-20確認）

- 宣言条件: 前向きN≥80かつE(R) CI上限<0
- FWD N=53, k=28 → 52.8% E(R)=+0.233 CI[-0.10~+0.56]
- 状態: 🟡蓄積中（N=53<80、しかもCI方向は完全逆転）

---

## 4. 記事テーマ・構成

**テーマ**: IS 28.1%→前向き52.8%の方向非対称完全逆転  
**主軸**: #044の指数×ロング崩落と対称的な「ショートの浮上」  
**SVG**: IS vs FWD の4本棒グラフ（逆転を視覚化）  
**判定**: 🟡蓄積中（N=53<80でゲート判定保留、ただし方向は宣言と逆）

---

## 5. Wilson CI計算メモ

- 46/117: center=0.3966, margin=0.0872 → [30.9%, 48.4%]
- 154/333: center=0.4629, margin=0.0532 → [41.0%, 51.6%]
- 31/69: center=0.4519, margin=0.1142 → [33.8%, 56.6%]
- 8/32: center=0.2768, margin=0.1442 → [13.3%, 42.1%]
- 19/37: center=0.5122, margin=0.1533 → [35.9%, 66.5%]
- 28/77: center=0.3701, margin=0.1051 → [26.5%, 47.5%]
- 10/19: center=0.5220, margin=0.2049 → [31.7%, 72.7%]
- 8/20: center=0.4161, margin=0.1973 → [21.9%, 61.3%]
- 19/51: center=0.3814, margin=0.1283 → [25.3%, 51.0%]
- 26/65: center=0.4056, margin=0.1159 → [29.0%, 52.1%]
- 19/37: center=0.5122, margin=0.1533 → [35.9%, 66.5%]
- 8/27: center=0.3217, margin=0.1632 → [15.9%, 48.5%]
- 10/23: center=0.4441, margin=0.1878 → [25.6%, 63.2%]
- 6/20: center=0.3322, margin=0.1868 → [14.5%, 51.9%]
- 6/14: center=0.4440, margin=0.2302 → [21.4%, 67.4%]
