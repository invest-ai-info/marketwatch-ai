# 🧪 signal-lab 運用SOP — 「多数仮説スイープ → 前向きトラッカー自動昇格 → 朝1記事」

（2026-06-16 新設。`signal-lab-daily` routine はこの手順に従う。人間が編集する手順書＝SYNC_FILES入り）

## 設計思想（なぜこの形か）
- 検証は signals-log への決定論計算。**同じデータを何度回しても新情報は増えない／回しすぎると偶然の“勝てそう”を掴む(p-hacking)**。
- だから二段構え：
  1. **発見スイープ（in-sample・LLM不使用）**＝仮説グリッドを全数検証し、**最小N＋BH-FDR多重検定補正**を通った“候補”だけ拾う。
  2. **前向きトラッカー（out-of-sample）**＝登録日以降に発火した分だけで勝率を測り、**事前宣言ルールで自動昇格**。登録後データ＝定義上アウトオブサンプルなので、たくさん試しても自滅しない。
- **記事は朝1本**だけ（鮮度はそれで足りる）。検証の“幅”はエンジンで好きなだけ広げる。
- 🚨 **昇格＝ライブ配信フィルタ/信頼度へ反映する“候補”の旗立てのみ。発火エンジン・配信条件には絶対に自動で触れない**（人間が最終反映）。

## 部品
| ファイル | 役割 | SYNC |
|---|---|---|
| `signal_lab_verify.py` | 固定オラクル（match/compute/wilson/GROUPS）。**編集禁止**・他が import | ✅ |
| `signal_lab_sweep.py` | 発見スイープ（全数検証＋最小N＋FDR）。`--json` で候補出力 | ✅ |
| `signal_lab_tracker.py` | 前向きトラッカー（update/register/table）。SEEDは本体内 | ✅ |
| `signal-lab-tracker.json` | トラッカー状態（routineがGitHub側でupdate・commit） | 🚫**禁忌**（ローカルpush厳禁） |
| `finalize_signal_lab.py` | 下書き→公開HTML仕上げ | ✅ |

## 毎日の routine 手順（06:10 JST）
```bash
# 0) 最新データ（GitHub側ではリポジトリ直下の signals-log.json が最新）
# 1) 前向きトラッカー更新＋自動昇格判定（毎日・安価）
python signal_lab_tracker.py update --date <YYYY-MM-DD>
#    → 🚩昇格/反証の変化があればログに出る

# 2) 発見スイープ（候補出し）→ FDR通過を登録（重複は自動スキップ）
python signal_lab_sweep.py --json drafts/labnotes/sweep-<YYYY-MM-DD>.json
python signal_lab_tracker.py register --from drafts/labnotes/sweep-<YYYY-MM-DD>.json --date <YYYY-MM-DD>

# 3) 記事用トラッカー表（HTML）を生成して下書きに差し込む
python signal_lab_tracker.py table --html --date <YYYY-MM-DD>
```

## 朝1記事の選び方（その日いちばんのニュースを1本）
優先度: **①新たに🟢昇格 or ⛔反証が出た** ＞ ②前向きで大きく動いた仮説 ＞ ③スイープでFDR通過した新候補 ＞ ④動きが薄い日は「定点観測のみ（30秒まとめ＋トラッカー表）」で軽く。
- 記事には必ず**前向きトラッカー表**（`table --html`）と「30秒まとめ」を載せる。
- 主張する数値は claims.json に入れ、**既存の自動公開ゲート**を通す：
  `signal_lab_verify.py draft.html claims.json`（exit0＝緑）→ Opusコンプラ → 公開（`finalize_signal_lab.py`）。
- ⚠️ claims の filter は `signal_lab_verify.py` の `ALLOWED_FILTER_KEYS` の範囲のみ。新次元が要る仮説は**verify.pyを人間が拡張するまでエスカレ**（勝手に増やさない）。

## 昇格基準（コード化済み・`signal_lab_tracker.py`）
- 共通: 前向き **N≥80**（PROMOTE_MIN_N）。損益分岐 **43%**（R:R 1:1.33）。
- **edge（順＝勝ち筋）**: 前向き **CI下限 > 43%** → ✅昇格／CI上限<43% → ⛔反証。
- **gate（逆＝回避筋）**: 前向き **CI上限 < 43%** → ✅昇格（回避確定）／CI下限>43% → ⛔反証。
- promoted/rejected は確定後ロック（戻さない）。

## 2026-06-16 ブートストラップ時点の登録仮説（20年バックテスト基準・足一致）
- edge(tf=1d)：指数×ロング(44.7%)・メタル×ロング(52.9%)・BTC×ロング(52.1%)・指数×逆張り買い(47.6%)
- gate(tf=1d)：other_fxクロス(38%)・ショート全般(39%)・下降トレンド発火(40.5%)
- edge(全足ライブ)：指数×ロング（1か月でも20年でも一貫）
- いずれも前向きNが貯まり次第、自動で🟢昇格/⛔反証が立つ（登録直後は🟡蓄積中）。
- ⚠️旧SEEDの「メタル＝回避ゲート」「全逆張り買い」はライブ1か月(時間足・極小N)由来で20年日足と矛盾＝不採用。**1か月の所見を20年が上書きした好例**。

## 拡張の仕方（ルールが増えても破綻させない）
- 新しいフィルタ次元 → `signal_lab_verify.py` の `match()` と `ALLOWED_FILTER_KEYS` に**人間が**追加（オラクルは単一ソース）。
- スイープの仮説グリッド → `signal_lab_sweep.py` の `build_grid()` に追記。組合せ爆発に注意（FDRが効くよう本数は数十〜百程度に抑える）。

## 🕰️ 検証データ拡張：日足リプレイ・バックテスト（2026-06-16 追加）
ライブ signals-log は約1か月＝“今の相場”に過学習しがち。`signal_lab_backtest.py` がライブ発火エンジン（`generate_technical_alerts.py` の `detect_signals` 等を **import**）を**過去20年の日足にリプレイ**して検証データを桁違いに増やす（2026-06-16初回＝**19,103発火/16,222決済・2006〜**＝ライブの約18倍・全レジーム）。
- 実行：`python signal_lab_backtest.py --years 20`（→ `signals-log-backtest.json`／週次・月次に再生成すれば良い・毎日は不要）。
- 発見スイープ：`python signal_lab_sweep.py --log signals-log-backtest.json --min-n 50`。
- **限界（必読）**：シミュレーション＝実約定でない／同バーTP・SL両達は保守的にSL（負け）／スプレッド無視／first_pullback無効／**source=backtest_1dでライブと混ぜない**。
- **使い分け（最重要）**：バックテストは **in-sample の“発見＋レジーム頑健性チェック”** に使う。**昇格判定はあくまでライブの前向きトラッカー（真のout-of-sample）が主役**。流れ＝バックテストで頑健な候補を見つける → `tracker register` で前向きに登録 → ライブで N が貯まって基準を満たせば昇格。
- 時間足(1h/4h)はYahooで約2年が上限。2年超の intraday が要るなら Dukascopy(無料FX/CFD・2007頃〜) 等を別途。
- データ運用：`signals-log-backtest.json` は派生・大容量＝**SYNC禁忌**（ローカル/週次再生成。リンターの SYNC_FORBIDDEN 済）。

### 2026-06-16 初回バックテスト（日足20年・参考所見）
- ✅順エッジ：メタル×ロング52.9%(N1557)・BTC×ロング52.1%・指数×逆張り47.6%・指数×ロング44.7%(N3699)・RSI過熱→ショート47.5%。
- ⛔逆エッジ：other_fxクロス38%・jpy_fxクロス40%・ショート全般39%・下降局面40.5%・double_top34%・**「逆張り買い」全般39.8%（指数限定でのみ有効）**。
- 教訓：ライブ1か月の「逆張り買い有望」は **20年では平均負け**＝レジーム/時間足で激変。バックテストが過度な楽観を冷ます。
