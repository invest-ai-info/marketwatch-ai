# AIシグナル研究日誌 #076 — labnotes

## 仮説
「MA両線の上（above_both）×ロング」——IS期間（〜2026-07-19）のE(R)全域マイナス（gate条件成立）が、FWD期間（2026-07-20〜）にE(R)プラス・CI下限初プラスへ転換する。主因は金属レジーム転換（#030/#060/#072と同根）仮説。

## 分析スクリプト（Python）
```python
import json, math, sys
sys.path.insert(0, '/home/user/marketwatch-ai')
from signal_lab_verify import closed as is_closed, win, match, compute, wilson, ma_pos_of

with open('/home/user/marketwatch-ai/signals-log.json') as f:
    raw = json.load(f)

# FWD cutoff = tracker "ステート 上昇配置（>MA25&75）×ロング" 登録日
REG = '2026-07-20'

def compute_er(data, f):
    rows = [d for d in data if is_closed(d) and match(d, f)]
    rs = []
    for d in rows:
        o = d.get('outcome')
        sl = abs(d.get('sl_pct') or 0)
        tp1 = abs(d.get('tp1_pct') or 0)
        tp2 = abs(d.get('tp2_pct') or 0)
        if o == 'tp1': rs.append(tp1/sl if sl>0 else 1.33)
        elif o == 'tp2': rs.append(tp2/sl if sl>0 else 2.0)
        elif o == 'sl': rs.append(-1.0)
    if not rs: return 0, 0, 0
    n = len(rs)
    mean = sum(rs)/n
    var = sum((r-mean)**2 for r in rs)/max(1,n-1)
    se = math.sqrt(var/n)
    return mean, se, n
```

## 生出力（全件）

### IS (before 2026-07-20)
- IS above_both×Long: k=175, n=480 (36.5%) CI[32.3%,40.9%]  E(R)=-0.149 RCI[-0.250,-0.049]
- IS above_both×Long×上昇: k=76, n=227 (33.5%) CI[27.7%,39.8%]  E(R)=-0.158 RCI[-0.293,-0.023]
- IS index×above_both×Long: k=61, n=145 (42.1%) CI[34.3%,50.2%]
- IS metal×above_both×Long: k=6, n=27 (22.2%) CI[10.6%,40.8%]  E(R)=-0.481 RCI[-0.854,-0.109]

### FWD (from 2026-07-20)
- FWD above_both×Long: k=250, n=498 (50.2%) CI[45.8%,54.6%]  E(R)=+0.171 RCI[+0.069,+0.274]
  (tracker cluster補正後 CI[+0.03~+0.32])
- FWD above_both×Long×上昇: k=115, n=222 (51.8%) CI[45.3%,58.3%]  E(R)=+0.211 RCI[+0.042,+0.381]
- FWD above_both×Long×中立: k=95, n=192 (49.5%) CI[42.5%,56.5%]
- FWD above_both×Long×下降: k=40, n=84 (47.6%) CI[37.3%,58.2%]
- FWD metal×above_both×Long: k=41, n=72 (56.9%) CI[45.4%,67.7%]  E(R)=+0.329 RCI[+0.060,+0.597]
- FWD index×above_both×Long: k=57, n=107 (53.3%) CI[43.9%,62.4%]  E(R)=+0.243 RCI[+0.021,+0.465]
- FWD jpy_fx×above_both×Long: k=58, n=113 (51.3%) CI[42.2%,60.3%]
- FWD other_fx×above_both×Long: k=55, n=126 (43.7%) CI[35.3%,52.4%]
- FWD above_both×Short: k=47, n=133 (35.3%) CI[27.7%,43.8%]  E(R)=-0.175 RCI[-0.366,+0.015]
- FWD above_both×Long×1h: k=147, n=296 (49.7%) CI[44.0%,55.3%]  E(R)=+0.159 RCI[+0.026,+0.292]
- FWD above_both×Long×4h: k=88, n=170 (51.8%) CI[44.3%,59.2%]  E(R)=+0.208 RCI[+0.032,+0.384]

### FWD 3期間分割（above_both×Long×上昇）
- FWD前期(7/27~8/6): k=28, n=49 (57.1%) E(R)=+0.333 RCI[+0.007,+0.660]
- FWD中期(8/6~8/16): k=23, n=53 (43.4%) E(R)=+0.013 RCI[-0.302,+0.327]
- FWD後期(8/16~): k=44, n=81 (54.3%) E(R)=+0.267 RCI[+0.013,+0.522]

### tracker output (2026-08-23)
- ステート 上昇配置（>MA25&75）×ロング: 245/488 50% E(R)=+0.17 CI[+0.03~+0.32] 🟡蓄積中 🏁N≥30
- ロング×上昇トレンド×MA両線の上: 92/180 51% E(R)=+0.19 CI[-0.06~+0.45] 🟡蓄積中

## 交絡解析
- metal IS→FWD: 22.2%(k=6/n=27) → 56.9%(k=41/n=72) = +34.7pp → 主因（#030/#060/#072と同根）
- 方向非対称: FWD Long50.2% vs Short35.3% = 14.9pp差
- 非metal FWD all-group 改善: index53.3%, jpy_fx51.3%, other_fx43.7%

## 事前宣言条件（検証前に宣言）
- H1（⛔反証接近）: FWD N=498のcluster補正後CI下限>0であること
- H2（方向非対称）: FWD above_both×Long vs Short 差≥10pp
- H3（主因交絡）: metal IS→FWD 変化≥25pp (金属レジーム転換)

## 判定
- H1: cluster補正後CI[+0.03~+0.32]→CI下限+0.03>0 ✅ → 1回目チェックポイント達成
- H2: 14.9pp≥10pp ✅
- H3: +34.7pp≥25pp ✅ → 金属レジーム転換が主因
通過A（3条件全クリア）
