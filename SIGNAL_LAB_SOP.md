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

## 2026-06-16 ブートストラップ時点の登録仮説
- edge: 指数×ロング(全期間55%)、指数×逆張り買い(54%)、全逆張り買い(42%)、runway阻害blocked=True(57%)
- gate: メタル全体(27%)、メタル×ロング(18%)、下降×ショート(27%)
- いずれも前向きNが貯まり次第、自動で🟢/⛔が立つ（現状は🟡蓄積中）。

## 拡張の仕方（ルールが増えても破綻させない）
- 新しいフィルタ次元 → `signal_lab_verify.py` の `match()` と `ALLOWED_FILTER_KEYS` に**人間が**追加（オラクルは単一ソース）。
- スイープの仮説グリッド → `signal_lab_sweep.py` の `build_grid()` に追記。組合せ爆発に注意（FDRが効くよう本数は数十〜百程度に抑える）。
