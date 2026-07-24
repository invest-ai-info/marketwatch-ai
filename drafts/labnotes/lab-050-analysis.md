# lab-050-analysis.md — AIシグナル研究日誌 #050

**基準日**: 2026-07-25（JST）  
**題材**: 上昇×逆張り買い（reversalL）前向き後半失速——RSI 73% vs BB 44% 二極化、FWD N=113 CI下限ゼロ割れ  
**優先度**: ②（前向きトラッカー大変動：trend=上昇×reversalL FWD N=113 E(R)=+0.177 CI[-0.01~+0.36]、CI下限がゼロ割れ）  
**先行**: #047（昇格確認 N=102）、#049（RSI vs BB 全期間二極化）

---

## 【仮説・事前宣言】

trend=上昇×reversalL（上昇トレンド中の逆張り買い）の前向きトラッカーでCI下限が-0.01にゼロ割れした。  
#049で確認した「RSI62.5% vs BB47.8%の全期間格差」が前向き期間でも拡大しており、  
特にBB×指数の前向き勝率が低迷している構造が、全体のCI下限を押し下げている可能性を検証する。

**仮説H1**: RSIの前向き勝率 > 43%（CI下限 > 43%を含む）  
**仮説H2**: BBの前向きE(R) ≈ 0（CI下限 < 0、つまり断定的優位なし）  
**仮説H3**: FWD前半 > FWD後半（時系列で後半に失速がある）

---

## 【スクリプト】

```python
import json, math

with open('signals-log.json') as f:
    data = json.load(f)

GROUPS = {
    "metal": {"GC=F", "SI=F"},
    "index": {"NKD=F", "ES=F", "NQ=F", "YM=F", "^FTSE"},
    "jpy_fx": {"USDJPY=X", "EURJPY=X", "GBPJPY=X", "AUDJPY=X"},
    "other_fx": {"EURUSD=X", "GBPUSD=X", "AUDUSD=X", "EURAUD=X", "GBPAUD=X"},
    "btc": {"BTC-USD"},
    "oil": {"CL=F"},
}
REV = {"rsi_oversold_bounce", "bb_lower_touch"}

def get_trend(d):
    ta = d.get("trend_alignment")
    if isinstance(ta, dict) and ta.get("higher_tf_trend"):
        return ta["higher_tf_trend"]
    return "unknown"

def get_group(d):
    t = d.get("ticker", "")
    for g, s in GROUPS.items():
        if t in s: return g
    return "other"

def is_win(d): return d.get("outcome") in ("tp1", "tp2")
def is_rev(d): return "ロング" in (d.get("direction") or "") and d.get("primary_signal") in REV

def get_r(d):
    o = d.get("outcome")
    sl = abs(d.get("sl_pct", 1)) or 1
    tp1 = d.get("tp1_pct", 1.33*sl)
    tp2 = d.get("tp2_pct", 2.0*sl)
    if o == "tp1": return tp1/sl
    elif o == "tp2": return tp2/sl
    elif o == "sl": return -1.0
    elif o == "expired": return 0.0
    return None
```

---

## 【生出力】

総クローズ件数: 2130  
Trends: {'unknown': 13, '下降': 728, '中立・もみあい': 628, '上昇': 761}

### trend=上昇×reversalL 全体

| 区分 | k/n | 勝率 | Wilson CI | E(R) | RCI |
|---|---|---|---|---|---|
| 全期間 | 111/214 | 51.9% | [45.2%~58.5%] | +0.210 | [+0.054~+0.367] |
| IS期間（登録前） | 54/101 | 53.5% | [43.8%~62.9%] | +0.248 | [+0.019~+0.476] |
| FWD全体 | 57/113 | 50.4% | [41.4%~59.5%] | +0.177 | [-0.039~+0.393] |
| FWD前半 | 34/56 | 60.7% | [47.6%~72.4%] | +0.417 | [+0.115~+0.718] |
| FWD後半 | 23/57 | 40.4% | [28.6%~53.3%] | -0.058 | [-0.358~+0.241] |

**tracker（クラスタ補正SE）**: FWD E(R)=+0.177 CI[-0.01~+0.36]（昇格基準 CI下限>0 を辛うじて下回る）

### シグナル別

| シグナル | 全期間 k/n | 勝率 | CI | FWD k/n | FWD勝率 | FWD E(R) | FWD RCI |
|---|---|---|---|---|---|---|---|
| RSI (rsi_oversold_bounce) | 32/51 | 62.7% | [49.0~74.7%] | 19/26 | 73.1% | +0.705 | [+0.299~+1.111] |
| BB (bb_lower_touch) | 79/163 | 48.5% | [40.9~56.1%] | 38/87 | 43.7% | +0.019 | [-0.225~+0.264] |

### グループ別

| グループ | 全期間 k/n | 勝率 | CI | FWD k/n | FWD勝率 | FWD E(R) |
|---|---|---|---|---|---|---|
| index | 45/81 | 55.6% | [44.7~65.9%] | 10/30 | 33.3% | -0.222 |
| jpy_fx | 30/52 | 57.7% | [44.2~70.1%] | 15/26 | 57.7% | +0.346 |
| other_fx | 21/54 | 38.9% | [27.0~52.2%] | 20/38 | 52.6% | +0.228 |
| metal | 4/8 | 50.0% | [21.5~78.5%] | 2/4 | 50.0% | N小 |
| oil | 7/9 | 77.8% | [45.3~93.7%] | 6/7 | 85.7% | +1.000 |

### グループ×シグナル（FWD 主要）

| 組合せ | FWD k/n | 勝率 | RCI |
|---|---|---|---|
| index×RSI FWD | 3/3 | 100.0% | N=3 小サンプル |
| index×BB FWD | 7/27 | 25.9% | [-0.788~-0.002] CI全域マイナス |
| jpy_fx×RSI FWD | 2/3 | 66.7% | N=3 小サンプル |
| jpy_fx×BB FWD | 13/23 | 56.5% | [-0.165~+0.802] |

### 時間足別（全期間）

| TF | 全期間 k/n | 勝率 | FWD k/n | FWD勝率 |
|---|---|---|---|---|
| 1h | 65/131 | 49.6% | 33/66 | 50.0% |
| 4h | 33/66 | 50.0% | 16/38 | 42.1% |

### 比較群（全期間）

| 区分 | k/n | 勝率 | CI |
|---|---|---|---|
| 下降×reversalL | 124/286 | 43.4% | [37.7~49.2%] |
| 中立×reversalL | 92/240 | 38.3% | [32.4~44.6%] |
| 下降×reversalL FWD | 75/159 | 47.2% | [39.6~54.9%] |

---

## 【結論】

- **H1 検証**: RSI FWD 73.1% (19/26) CI下限53.9% > 43% ✅通過
- **H2 検証**: BB FWD 43.7% (38/87) E(R)=+0.019 RCI[-0.225~+0.264]→CI下限マイナス ✅通過
- **H3 検証**: FWD前半60.7% > FWD後半40.4%（差20.3pp）✅通過（E(R): 前半+0.417 vs 後半-0.058）
- **最重要発見**: index×BB FWD=7/27=25.9% RCI[-0.788~-0.002]→CI全域マイナス（index×RSI FWD=3/3=100%・N=3）
- **トラッカー**: FWD N=113 CI[-0.01~+0.36]（クラスタ補正SE使用。昇格基準CI下限>0を辛うじて割る。降格ルール1回目チェックポイント候補）
- **構造**: BB主体の比率が高い（163/214=76%）ため、BBの軟化が全体を引き下げている
