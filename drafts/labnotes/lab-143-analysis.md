# lab-143 分析メモ（出口の相性ラボ 第6回・日足MACDデッドの売り）

材料: exit-lab.json (asof 2026-11-01)。生成スクリプト＝lab-143-build.py（claims と下書きをここから組み立てた）。

- 全18銘柄 基準方式 平均R avg -0.07
- 全18銘柄 基準方式 入口件数 n_entries 3616
- 全18銘柄 基準方式 確定件数 n 3616
- 全18銘柄 基準方式 勝率% win 41.0
- 利確なし 平均R avg -0.31
- 利確なし vs_base vs_base -0.23
- 利確なし vs_base下限 vs_base_lo -0.42
- 利確なし vs_base上限 vs_base_hi -0.03
- 利確なし 件数 n 3597
- 利確なし flag flag False
- パラボリックSAR損切り×真ん中の線利確 平均R avg 0.02
- パラボリックSAR損切り×真ん中の線利確 vs_base vs_base 0.09
- パラボリックSAR損切り×真ん中の線利確 vs_base下限 vs_base_lo 0.02
- パラボリックSAR損切り×真ん中の線利確 vs_base上限 vs_base_hi 0.17
- パラボリックSAR損切り×真ん中の線利確 件数 n 1493
- パラボリックSAR損切り×真ん中の線利確 flag flag False
- 利確なし 勝率% win 12.9
- 株価指数 基準方式 平均R avg -0.09
- 株価指数 基準方式 件数 n 1007
- FX 基準方式 平均R avg -0.04
- FX 基準方式 件数 n 1860
- コモディティ 基準方式 平均R avg -0.16
- コモディティ 基準方式 件数 n 611
- ビットコイン 基準方式 平均R avg -0.12
- ビットコイン 基準方式 件数 n 138
- 前向き 入口件数 n_entries 13
- 前向き 確定件数 n 9

全72通り: 目立つ(flag)=0件。vs_base上位/下位は exit-lab.md「日足｜MACDデッドの売り」表を参照。
