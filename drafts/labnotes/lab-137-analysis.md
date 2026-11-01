# lab-137 分析メモ — rl_tf_adx_strong 定点観測（N=110→144）

日付: 2026-11-02 (JST) / 仮説ID: rl_tf_adx_strong（回避）/ 題材の理由: 昇格/反証の変化なし・FDR通過0・読者質問なし → ②前向きで回数が増えた仮説（次のチェックポイント160回の手前）

## スクリプト: drafts/labnotes/lab-137-analysis.py（asof 2026-11-02T06:13 JST）
## 生出力
```
asof issues []
FWD:順張り・トレンド強	49/144	34.0%	[26.8,42.1]	{'family': 'tf', 'adx_band': 'strong', 'fired_from': '2026-09-27'}
FWD:順張り・トレンド弱(対照)	56/131	42.7%	[34.6,51.3]	{'family': 'tf', 'adx_band': 'weak', 'fired_from': '2026-09-27'}
FWD:順張り全体	123/343	35.9%	[31.0,41.1]	{'family': 'tf', 'fired_from': '2026-09-27'}
FWD:全シグナル	225/621	36.2%	[32.5,40.1]	{'fired_from': '2026-09-27'}
IS:順張り・トレンド強	443/1070	41.4%	[38.5,44.4]	{'family': 'tf', 'adx_band': 'strong', 'fired_before': '2026-09-27'}
IS:順張り・トレンド弱	376/851	44.2%	[40.9,47.5]	{'family': 'tf', 'adx_band': 'weak', 'fired_before': '2026-09-27'}
FWD強 4h	41/116	35.3%	[27.2,44.4]	{'family': 'tf', 'adx_band': 'strong', 'tf': '4h', 'fired_from': '2026-09-27'}
FWD強 1h	7/24	29.2%	[14.9,49.2]	{'family': 'tf', 'adx_band': 'strong', 'tf': '1h', 'fired_from': '2026-09-27'}
FWD強 買い	16/60	26.7%	[17.1,39.0]	{'family': 'tf', 'adx_band': 'strong', 'direction': 'long', 'fired_from': '2026-09-27'}
FWD強 売り	33/84	39.3%	[29.5,50.0]	{'family': 'tf', 'adx_band': 'strong', 'direction': 'short', 'fired_from': '2026-09-27'}
FWD強 指数	21/43	48.8%	[34.6,63.2]	{'family': 'tf', 'adx_band': 'strong', 'group': 'index', 'fired_from': '2026-09-27'}
FWD強 円FX	5/28	17.9%	[7.9,35.6]	{'family': 'tf', 'adx_band': 'strong', 'group': 'jpy_fx', 'fired_from': '2026-09-27'}
FWD強 他FX	14/37	37.8%	[24.1,53.9]	{'family': 'tf', 'adx_band': 'strong', 'group': 'other_fx', 'fired_from': '2026-09-27'}
FWD強 金銀	4/14	28.6%	[11.7,54.6]	{'family': 'tf', 'adx_band': 'strong', 'group': 'metal', 'fired_from': '2026-09-27'}
FWD強 btc	3/16	18.8%	[6.6,43.0]	{'family': 'tf', 'adx_band': 'strong', 'group': 'btc', 'fired_from': '2026-09-27'}
FWD強 oil	1/5	20.0%	[3.6,62.4]	{'family': 'tf', 'adx_band': 'strong', 'group': 'oil', 'fired_from': '2026-09-27'}
```

トラッカー: avgR -0.222 [-0.395,-0.049], promote_strikes=1, last_eval_n=87, 次チェックポイント160
