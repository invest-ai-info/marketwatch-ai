# lab-129 分析メモ（出口の相性ラボ 第4回・日足 ma_dead 売り）
材料: exit-lab.json（asof 2026-10-18 / is_until 2026-09-25）。価格は取得せず、json の cells を読むだけ。
集計: tf=1d, entry=ma_dead, side=short, period=is, group=all/index/fx/commodity/crypto。
- 基準(atr×atr2): n_entries=724, n=724, avg=-0.1098, win=0.3895(→39.0), lo=-0.2281, hi=0.0085
- 目立つ旗(flag)が立ったマス: 0 / 72（all）。資産クラス別も 0。
- 良く見えた: atr_time×rsi70 n=634 avg=-0.0165 vs_base=+0.1201 [+0.0430,+0.1972]
- 悪く見えた: atr×none n=721 avg=-0.2466 vs_base=-0.1308 [-0.4673,+0.2056]
- 資産クラス別 基準: index -0.1454(205) / fx -0.1060(372) / commodity -0.0760(118) / crypto -0.0447(29)
- 前向き(fwd): n_entries=7, n=3
- 注: 72マスのうち多くで vs_base は正（基準が悪いため）。旗の基準（差0.15R以上・前後半同向き・Bonferroni 10%）に届かず。
