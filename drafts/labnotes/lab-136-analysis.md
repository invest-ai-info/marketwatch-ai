# lab-136 分析メモ（出口の相性ラボ 第5回・日足 ma_golden 買い）
材料: exit-lab.json（asof 2026-10-25 / is_until 2026-09-25）。価格は取得せず、json の cells を読むだけ。
組み立て: drafts/labnotes/lab-136-build.py（claims と下書きを json から機械生成）。
- 基準(atr×atr2): n_entries=719, n=719, avg=-0.0136, win=43.4%
- 目立つ旗(flag)が立ったマス: 0 / 504（全 group・is/fwd 合算）。72マス（all）でも 0。
- 良く見えた(n>=100): atr×none n=716 avg=+0.597 vs_base=+0.616 [-0.101,+1.332] 勝率19.6%（裾の長い分布・ぶれ幅が0をまたぐ）
- 悪く見えた(n>=100): ma×swing n=600 avg=-0.057 vs_base=-0.079 [-0.199,+0.041]
- n<100 の ma×bb_mid(n=10) は幅が極端に広いので並べない
- 資産クラス別 基準: index +0.053(204) / fx -0.144(368) / commodity +0.227(118) / crypto +0.192(29・参考)
- 前向き(fwd): n_entries=1, n=1
