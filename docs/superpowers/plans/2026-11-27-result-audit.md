# 検算の関門 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 研究の取引の一覧を「ありえない数字の点検」に通し、合格は「別の書き方での数え直し」で1件ずつ一致した記録がないと使わない仕組みを作る。

**Architecture:** 根に小さな道具を4つ置く（`recheck_status.py`＝記録の読み書き・`result_audit.py`＝点検・`recount_compare.py`＝突き合わせ・`mutate_check.py`＝わざと壊す）。記録は値段を含まない2つのファイル（`recheck/audits.json`・`recheck/records.json`）にまとめて GitHub に送る。リスト・地図・メールの絞り・総当たりの段・`mw check`・`_doctrine_check.py`・見張り番が `recheck_status` を読んで止める。

**Tech Stack:** Python 3.12（標準ライブラリ＋`zoneinfo`）。テストは `tests/test_*.py`（pytest 不要・`__main__` の実行部つき）

**Spec:** `docs/superpowers/specs/2026-11-26-result-audit-design.md`（実装する人は必ず読む）

## Global Constraints

- 手元は git ではない。git コマンドを使わない。送るのは `PYTHONUTF8=1 python sync_to_github.py --batch --dry-run` → `--batch`（`--force` は使わない）。送る前に `python mw.py check`
- `research/` の下は送らない（SYNC禁忌）。取引の一覧（値段を含む）は手元だけ＝`research/recheck/<研究>/`
- 送るファイルは `sync_to_github.py` の `SYNC_FILES` に1つずつ名前を書く（ディレクトリや * は使えない）
- 点検の出力に損益の合計・平均・勝率を出さない。A5・A7 は名前だけ（数字なし）
- 許す差＝値段 1e-6（相対）・損益 0.1pips／0.01%（pct）／1bp
- データの抜け＝2%超で error。年ごとの回数の跳ね＝ほかの年の中央値の3倍超か1/3未満
- `GO_LIVE = "2026-11-27"`（使い始めの日・`recheck_status.py` の1か所だけ）。この日より前の登録・昇格はさかのぼらない（`rl_tf_adx_strong` 2026-11-07 昇格・OJ5 2026-11-26 登録は例外のまま）
- 固定の検査（`signal_lab_verify.py`・`check_guide_draft.py`・`check_plain_japanese.py`・`exit_lab_verify.py`）は編集しない。`_doctrine_check.py` には検査を「足すだけ」（設計書の承認＝オーナーの承認）
- 訂正はいつも追記。記録を上書きするときは前の記録を `previous` に残す
- メッセージ・文書はやさしい日本語（記号・略語を減らす・数字は変えない）
- 閾値は `result_audit.LIMITS` の1か所だけ

## Review Focus

1. **時間帯の無い時刻**（oj の CSV は日本時間の `YYYY-MM-DD HH:MM`）→ 黙って UTC とみなさず、形の検査で止める（Task 2 にテスト）
2. **任意の欄が無い一覧**（値段・損切りが無い）→ その欄が要る点検は飛ばし、飛ばした名前を `checks_skipped` に出す。落ちない（Task 2・3 にテスト）
3. **0件の一覧** → 点検は何も出さず、`recheck_ok` は偽（Task 1・2 にテスト）
4. **`recheck/records.json` が無い・壊れている**（Actions 側）→ 新しい合格は待ち、使い始めの日より前のものは今のまま。メールの仕組みは落ちない（Task 1・8 にテスト）
5. **研究の名前に `/` や空白・登録の ID の重複（B4・M6・ST）** → 記録の鍵は `safe(study)`、登録の関門は ID ではなく点検の指紋で引く（Task 1・9 にテスト）

---

### Task 0: 設計書と計画を送る

**Files:**
- Modify: `sync_to_github.py`（`SYNC_FILES` に `docs/superpowers/specs/2026-11-26-result-audit-design.md` と `docs/superpowers/plans/2026-11-27-result-audit.md`）

- [ ] **Step 1:** 2行を `SYNC_FILES` に足す（`_config.yml` が `*.md` を除くのでサイトには出ない）
- [ ] **Step 2:** `python mw.py check` → error 0
- [ ] **Step 3:** `PYTHONUTF8=1 python sync_to_github.py --batch --dry-run` で2件だけ増えるのを見てから `--batch`

### Task 1: 記録の読み書き `recheck_status.py`

**Files:**
- Create: `recheck_status.py`・`tests/test_recheck_status.py`
- Modify: `sync_to_github.py`（2ファイルを足す）

**Interfaces:**
- Produces:
  - `GO_LIVE: str = "2026-11-27"`
  - `safe(study: str) -> str`（`[A-Za-z0-9_.-]` 以外を `_` に）
  - `store_path(kind: str, root: str = ".", local_only: bool = False) -> str`（kind＝`"audits"`／`"records"`。`recheck/<kind>.json`、local_only なら `research/recheck/<kind>.json`）
  - `load_store(kind, root=".") -> dict`（両方の置き場を読み、`research/` 側を上に重ねる。無い・壊れている→ `{}`）
  - `put(kind, study, entry: dict, root=".", local_only=False) -> str`（既にあれば前のものを `entry["previous"]` に積む・LF で書く）
  - `entry_ok(entry: dict | None) -> bool`（`n_orig > 0` かつ `agreement == 1.0`＝一致の決まりはここ1か所。見張り番も使う）
  - `recheck_ok(study, root=".") -> bool`（`entry_ok(load_store("records", root).get(safe(study)))`）
  - `is_waiting(study, passed_on: str | None, root=".", go_live: str | None = None) -> bool`（`passed_on` が None か go_live より前→ False。それ以外は `not recheck_ok`）
  - `audit_by_fingerprint(hex12: str, root=".") -> dict | None`（`audits` の中で `fingerprint` がその12文字で始まるもの）

- [ ] **Step 1: 失敗するテストを書く**

```python
def test_waiting_only_after_go_live():
    r = _root({})                                   # 空の recheck/
    assert not S.is_waiting("x", "2026-11-07", r, go_live="2026-11-27")
    assert not S.is_waiting("x", None, r, go_live="2026-11-27")
    assert S.is_waiting("x", "2026-11-27", r, go_live="2026-11-27")

def test_record_with_full_agreement_releases():
    r = _root({"records": {"x": {"n_orig": 10, "matched": 10, "agreement": 1.0}}})
    assert S.recheck_ok("x", r) and not S.is_waiting("x", "2026-12-01", r, go_live="2026-11-27")

def test_zero_rows_or_partial_agreement_is_not_ok():
    r = _root({"records": {"a": {"n_orig": 0, "agreement": 1.0}, "b": {"n_orig": 5, "agreement": 0.8}}})
    assert not S.recheck_ok("a", r) and not S.recheck_ok("b", r)

def test_broken_store_reads_as_empty():           # Review Focus 4
    r = _root_raw("recheck/records.json", "{壊れた")
    assert S.load_store("records", r) == {} and not S.recheck_ok("x", r)

def test_put_keeps_previous_and_safe_names():     # Review Focus 5
    r = _root({}); S.put("records", "J4F/F 1", {"agreement": 0.5}, r); S.put("records", "J4F/F 1", {"agreement": 1.0}, r)
    e = S.load_store("records", r)["J4F_F_1"]
    assert e["agreement"] == 1.0 and e["previous"][0]["agreement"] == 0.5
```

- [ ] **Step 2:** `PYTHONUTF8=1 python tests/test_recheck_status.py` → ImportError で落ちる
- [ ] **Step 3:** 上の Interfaces どおりに書く（`put` は `safe()` を通した鍵で保存。`load_store` の戻りは `{study: entry}`）
- [ ] **Step 4:** 同じコマンド → 全部通る
- [ ] **Step 5:** `SYNC_FILES` に `recheck_status.py`・`tests/test_recheck_status.py` を足す

### Task 2: 点検の土台 `result_audit.py`（形・A1・A8・A9・A10・漏らさない・関門）

**Files:**
- Create: `result_audit.py`・`tests/test_result_audit.py`
- Modify: `sync_to_github.py`

**Interfaces:**
- Consumes: `recheck_status.put("audits", ...)`
- Produces:
  - `TRADE_FIELDS`（設計書 5.1 の17欄の順）・`EVENT_FIELDS = ("study","market","symbol","date","flag","outcome","unit","period")`・`MARKETS = ("fx","jp","index","commodity","crypto")`・`UNITS = ("pips","pct","bp")`
  - `LIMITS: dict`（この Task では `"missing_max": 0.02` だけ。Task 3 で足す）
  - `@dataclass Context(kind="trade", one_at_a_time=False, no_friday=False, friday_tz="Asia/Tokyo", missing_ratio=None, holidays: dict[str, list[str]] = {}, min_cost=None)`
  - `@dataclass Finding(check: str, level: str, count: int, examples: list[int], note: str = "")`（level＝`error`／`warning`／`flag`・examples は行の番号を最大5）
  - `to_utc(s: str) -> datetime`（時間帯の無い時刻は ValueError）
  - `check_rows(rows: list[dict], kind: str) -> list[str]`（形の問題を日本語1行ずつ）
  - `audit(rows, ctx) -> list[Finding]`
  - `summarize(rows, ctx, findings) -> dict`＝`{"kind","n_rows","rows_sha256","checks_run","checks_skipped","errors","warnings","flags","findings","fingerprint"}`（fingerprint＝ほかの欄を `sort_keys` で JSON にした sha256）
  - `class AuditError(Exception)`
  - `gate(rows, ctx, study, root=".", waivers: dict[str, str] | None = None, local_only=False) -> dict`（形の問題か error があれば、記録してから AuditError。warning は waivers に理由が無ければ AuditError。通れば summary を返す）
  - CLI：`python result_audit.py ROWS.csv|json --study X [--ctx ctx.json] [--waive A6=理由]`（error で exit 1）

- [ ] **Step 1: 失敗するテストを書く**（行は `_trade(**kw)` で作る。既定＝fx・USDJPY・買い・UTC の時刻・net/gross/cost あり）

```python
def test_naive_time_is_rejected():                 # Review Focus 1
    assert any("時間帯" in m for m in A.check_rows([_trade(entry_time="2026-11-26 09:00")], "trade"))

def test_bad_market_side_unit_are_rejected():
    msgs = A.check_rows([_trade(market="forex", side=2, unit="yen")], "trade")
    assert len(msgs) == 3

def test_a1_exit_before_entry():
    f = _find(A.audit([_trade(entry_time="2026-01-05T10:00Z", exit_time="2026-01-05T09:00Z")], A.Context()), "A1")
    assert f.level == "error" and f.examples == [0]

def test_a1_entry_before_signal():
    assert _find(A.audit([_trade(signal_time="2026-01-05T10:05Z", entry_time="2026-01-05T10:00Z")], A.Context()), "A1")

def test_a8_duplicate_and_overlap():
    t = _trade(); assert _find(A.audit([t, dict(t)], A.Context()), "A8").level == "error"
    a, b = _trade(entry_time="2026-01-05T10:00Z", exit_time="2026-01-05T12:00Z"), _trade(entry_time="2026-01-05T11:00Z", exit_time="2026-01-05T13:00Z", symbol="EURJPY")
    assert _find(A.audit([a, b], A.Context(one_at_a_time=True)), "A8") and not _find(A.audit([a, b], A.Context()), "A8")

def test_a9_saturday_holiday_friday():
    assert _find(A.audit([_trade(entry_time="2026-01-10T03:00Z", exit_time="2026-01-10T04:00Z")], A.Context()), "A9")   # 土曜
    fri = _trade(entry_time="2026-01-09T01:00Z", exit_time="2026-01-09T02:00Z")                                       # 金曜（東京）
    assert _find(A.audit([fri], A.Context(no_friday=True)), "A9") and not _find(A.audit([fri], A.Context()), "A9")

def test_oj5_c_missing_seven_percent_is_error():   # 過去の型：2026-11-26 OJ5 の C
    assert _find(A.audit([_trade()], A.Context(missing_ratio=0.07)), "A10").level == "error"
    assert not _find(A.audit([_trade()], A.Context(missing_ratio=0.02)), "A10")

def test_empty_list_is_clean():                    # Review Focus 3
    s = A.summarize([], A.Context(), A.audit([], A.Context()))
    assert s["n_rows"] == 0 and s["errors"] == 0

def test_missing_optional_fields_are_skipped():   # Review Focus 2
    t = _trade(); t.pop("signal_time"); t.pop("stop_price")
    s = A.summarize([t], A.Context(), A.audit([t], A.Context()))
    assert "A1-signal" in s["checks_skipped"]

def test_summary_never_shows_pnl():
    rows = [_trade(net=v, gross=v + 0.5, cost=0.5) for v in (3.0, -1.0, 7.25)]
    s = A.summarize(rows, A.Context(), A.audit(rows, A.Context()))
    assert not _has_key(s, {"sum", "mean", "avg", "win", "win_rate", "pf", "total", "pnl"})
    assert not _has_value(s, {9.25, 9.25 / 3, 2 / 3})

def test_gate_records_then_refuses_errors_and_unwaived_warnings():
    r = _root()
    try: A.gate([_trade(entry_time="2026-01-05T10:00Z", exit_time="2026-01-05T09:00Z")], A.Context(), "T", r); assert False
    except A.AuditError: pass
    assert S.load_store("audits", r)["T"]["errors"] == 1
```

- [ ] **Step 2:** `PYTHONUTF8=1 python tests/test_result_audit.py` → 落ちる
- [ ] **Step 3:** Interfaces どおりに書く。点検の中身：
  - A1＝`exit < entry` は error。`signal_time` があり `entry < signal` も error（無ければ `A1-signal` を skipped に入れる）
  - A8＝同じ `(symbol, side, entry_time)` が2回、または `one_at_a_time` で研究の中の期間が重なる
  - A9＝建ての UTC の土曜。`holidays[market]` の日（市場の日付＝fx は UTC・jp は東京）。`no_friday` なら `friday_tz` で金曜
  - A10＝`missing_ratio > LIMITS["missing_max"]`
  - 鍵の時刻は分まで UTC にそろえる
- [ ] **Step 4:** 同じコマンド → 全部通る
- [ ] **Step 5:** `SYNC_FILES` に2ファイルを足す

### Task 3: 点検の残り（A2〜A7・G1）と過去の型の見本

**Files:**
- Modify: `result_audit.py`・`tests/test_result_audit.py`

**Interfaces:**
- Produces: `LIMITS` に次を足す（初めの値。Task 4 で較正して変えてよい）
  - `"stop_k": {"fx": 3.0, "jp": 6.0, "index": 4.0, "commodity": 4.0, "crypto": 4.0}`（`r < -k` で error。fx で土曜をまたぐ取引は k を2倍）
  - `"move_max": {"fx": 0.06, "jp": 0.5, "index": 0.12, "commodity": 0.2, "crypto": 0.35}`（値段があるとき `|exit/entry-1| > move_max × max(1, 平日の日数)` で error）
  - `"pips_max_per_day": 600`（fx で値段が無いとき `|gross|` を見る）
  - `"price_ratio_max": 5.0`（同じ銘柄の建値が、その銘柄の中央値の5倍超か1/5未満で error＝10倍ずれ・分割）
  - `"cost_tol": {"pips": 0.05, "pct": 0.005, "bp": 0.5}`（`|gross - cost - net|` の許す差）
  - `"rollover_share_max": 0.25`・`"profit_share_min": 0.5`（A5・A7）
  - `"year_jump": 3.0`（A6・3年以上あるときだけ）
  - `"g1_win": 0.75`・`"g1_mean_r": 1.0`・`"g1_min_n": 30`
  - `"event_move_max": {"jp": 0.5, "fx": 0.06, "index": 0.12, "commodity": 0.2, "crypto": 0.35}`（目印の形の outcome・1日あたり）
- 重さ：A2・A3・A4＝error／A5・A6・A7＝warning／G1＝flag。目印の形には A3・A6・A8・A9・A10 だけ

- [ ] **Step 1: 失敗するテストを書く**（名前は過去の例）

```python
def test_rv_one_sided_stop_check():                # RV：1回で -694R
    assert _find(A.audit([_trade(r=-694.0, stop_price=150.0)], A.Context()), "A2").level == "error"

def test_weekend_gap_allows_double():
    t = _trade(entry_time="2026-01-09T20:00Z", exit_time="2026-01-12T01:00Z", r=-5.0)
    assert not _find(A.audit([t], A.Context()), "A2")

def test_r1_fake_yahoo_jump():                     # R1：+947.9%
    t = _trade(market="jp", symbol="9999.T", unit="pct", entry_price=100.0, exit_price=1047.9,
               entry_time="2026-01-05T00:00Z", exit_time="2026-01-05T06:00Z")
    assert _find(A.audit([t], A.Context()), "A3").level == "error"

def test_ten_times_price_is_caught():              # R1：1306.T の10倍ずれ
    rows = [_jp("1306.T", 2000.0 + i) for i in range(9)] + [_jp("1306.T", 20000.0)]
    assert _find(A.audit(rows, A.Context()), "A3").examples == [9]

def test_st_cost_negative_and_not_adding_up():    # ST ラウンド1
    assert _find(A.audit([_trade(cost=-0.3, gross=1.0, net=1.3)], A.Context()), "A4")
    assert _find(A.audit([_trade(cost=0.3, gross=1.0, net=2.0)], A.Context()), "A4")

def test_st_rollover_concentration_warns_by_name_only():
    rows = _rollover_fixture()                     # 40件：8件が NY17時をまたぎ +50、残りは -1
    f = _find(A.audit(rows, A.Context()), "A5")
    assert f.level == "warning" and "NY17時" in f.note and not any(c.isdigit() for c in f.note)

def test_m1_year_jump_warns():                     # M1：MT5 の欠陥データで回数が3〜4倍
    assert _find(A.audit(_per_year({2020: 100, 2021: 100, 2022: 380}), A.Context()), "A6").level == "warning"

def test_partial_years_are_scaled():
    assert not _find(A.audit(_per_year({2020: 25, 2021: 100, 2022: 100}, first_months=3), A.Context()), "A6")

def test_a7_names_bucket_and_skips_single_symbol():
    f = _find(A.audit(_bucket_fixture(), A.Context()), "A7")
    assert f and not any(c.isdigit() for c in f.note)   # 入れ物の名前だけ（帯は「東京の朝」などの言葉）
    assert not _find(A.audit(_single_symbol_fixture(), A.Context()), "A7")

def test_g1_too_good_is_flag_not_error():
    rows = [_trade(net=2.0, r=2.0, entry_time=_t(i), exit_time=_t(i, 1)) for i in range(40)]
    f = _find(A.audit(rows, A.Context()), "G1")
    assert f.level == "flag"

def test_split_in_events_is_caught_and_events_skip_trade_checks():   # Yahoo の分割の直しもれ
    ev = [_event("7203.T", "2026-01-05", outcome=-80.0)]
    fs = A.audit(ev, A.Context(kind="event"))
    assert _find(fs, "A3") and not _find(fs, "A2") and not _find(fs, "A5")
```

- [ ] **Step 2:** `PYTHONUTF8=1 python tests/test_result_audit.py` → 新しいテストが落ちる
- [ ] **Step 3:** 点検を書く。決めてあること：
  - A5＝fx だけ。NY17時は `America/New_York` の 17:00（夏冬は zoneinfo に任せる）を建てと決済の間にまたぐ取引。「またぐ取引が `rollover_share_max` 以下の割合なのに、プラスの net の合計の `profit_share_min` 超をそこが持つ」で warning。net の合計が0以下なら見ない
  - A6＝年ごとの件数を「その年に入っている月の数」で割って12倍し、ほかの年の中央値と比べる
  - A7＝入れ物は3種類（建ての UTC の時刻を4時間ごとの6つの帯・向き・銘柄）。銘柄が1つ・向きが1つならその入れ物は見ない。「取引の割合が 0.25 未満の入れ物が、プラスの net の合計の半分超」で warning。note には入れ物の名前だけ（帯は「東京の朝」などの言葉）
  - G1＝`n >= g1_min_n` で、勝ち（net>0）の割合か平均の r が目安を超えたら flag「数え直しが必須」。数字は出さない
- [ ] **Step 4:** 同じコマンド → 全部通る（Task 2 のテストも）

### Task 4: 較正（今ある一覧で誤報を測る）

**Files:**
- Create: `research/recheck/convert_existing.py`（手元だけ・送らない）・`recheck/CALIBRATION.md`（送る）
- Modify: `result_audit.py`（`LIMITS` を直すときだけ）・`sync_to_github.py`

**Interfaces:**
- Produces: `convert_existing.py` の `from_oj(path, study, period) -> list[dict]`（oj・oj2・oj3・oj5 の CSV。`jst`・`jst_out` は東京の時刻として UTC にする。費用前か後かは各 `write_trades` を読んで決め、コメントに書く）と、一覧ごとの変換 `LISTS: list[tuple[name, loader, Context]]`
- 対象：oj A/B・oj2 A/B・oj3 A/B（腕ごと）・series-break A/B・chart-pattern seen/old・quiet-range seen/old・`yori-forward.json` の trades・`highs-trap-forward.json` の trades・`r4-window-lab.json` の trades_end・`research/mt5/m1-data/m1_*.csv`（M1 の欠陥データを含むはず＝A6 が鳴れば当たり）

- [ ] **Step 1:** `python research/recheck/convert_existing.py` が一覧ごとに `check_rows` を通し、`audit` をかけ、点検ごとの件数の表を出す（損益は出さない）
- [ ] **Step 2:** 鳴ったものを1件ずつ見る：誤報なら閾値を直す（Task 3 のテストが通るままか確かめる）／本物の疑いならオーナーへ報告する一覧に入れる（閾値で隠さない）
- [ ] **Step 3:** `recheck/CALIBRATION.md` に表（一覧 × 点検 → 件数・誤報／本物の疑い・直した閾値と理由）を書く。値段・損益は書かない
- [ ] **Step 4:** `PYTHONUTF8=1 python tests/test_result_audit.py` → 全部通る（過去の型を全部見つけるまま）
- [ ] **Step 5:** `SYNC_FILES` に `recheck/CALIBRATION.md` を足す

### Task 5: 突き合わせ `recount_compare.py` と数え直しの手順書

**Files:**
- Create: `recount_compare.py`・`tests/test_recount_compare.py`・`recheck/RECOUNT_GUIDE.md`
- Modify: `sync_to_github.py`

**Interfaces:**
- Consumes: `result_audit.to_utc`・`recheck_status.put("records", ...)`
- Produces:
  - `TOL = {"price": 1e-6, "pips": 0.1, "pct": 0.01, "bp": 1.0}`（値段は相対）
  - `CATEGORIES = ("original_error", "recount_error", "ambiguous_rule", "data_version")`
  - `@dataclass Mismatch(key: tuple, what: str, fields: list[str])`（what＝`only_original`／`only_recount`／`differs`）
  - `@dataclass Compared(n_orig: int, n_recount: int, matched: int, mismatches: list[Mismatch])`
  - `key_of(row, kind) -> tuple`（trade＝`(symbol, side, entry_time を UTC の分)`／event＝`(symbol, date, str(flag))`）
  - `compare(orig, recount, kind="trade") -> Compared`（trade は exit_time・exit_price・exit_reason・net、event は outcome を比べる）
  - `class RecountError(Exception)`
  - `finalize(study, orig, recount, kind, explanations: list[dict], opened: list[str], forbidden: list[str], root=".", today=None, local_only=False) -> dict`
    - explanations の1件＝`{"key": [...], "category": CATEGORIES のどれか, "note": str, "evidence": {...}}`。`data_version` は `evidence={"orig_input": x, "recount_input": y}` で x≠y のときだけ有効
    - 残った食い違いが全部「証拠つきの data_version」でなければ RecountError
    - `opened` に `forbidden` のどれかがあれば RecountError（元の道具を開いた＝独立でない）
    - 記録＝`{"study","kind","date","orig_sha256","recount_sha256","n_orig","n_recount","matched","excluded_data_version","breakdown","agreement","opened"}` を `put("records", ...)`。値段は入れない
- `RECOUNT_GUIDE.md` の中身（手順は設計書 5.3 のとおり）：数え直しの担当（Sonnet の新しいサブエージェント）への指示文のひな形。渡すもの＝登録の節の文（`**結果（` より前だけ）・データの置き場・共通の形の説明・使ってよい読み込み部品。渡さないもの＝元の道具のファイル名を名指しして「開かない」・結果の数字。出すもの＝`research/recheck/<研究>/recount.py` と `recount-rows.csv`・開いたファイルの一覧。食い違いの説明は `research/recheck/<研究>/explanations.json` に追記していく

- [ ] **Step 1: 失敗するテストを書く**

```python
def test_same_lists_agree():
    c = R.compare(_rows(5), _rows(5)); assert c.matched == 5 and not c.mismatches

def test_cp_off_by_one_is_caught():                # CP：突き合わせの番号の誤り
    o = _rows(5); r = [dict(x, exit_price=o[(i + 1) % 5]["exit_price"]) for i, x in enumerate(o)]
    assert sum(m.what == "differs" for m in R.compare(o, r).mismatches) == 5

def test_tolerances():
    o = _rows(1); r = [dict(o[0], net=o[0]["net"] + 0.09, exit_price=o[0]["exit_price"] * (1 + 5e-7))]
    assert R.compare(o, r).matched == 1
    r = [dict(o[0], net=o[0]["net"] + 0.2)]; assert R.compare(o, r).matched == 0

def test_missing_and_extra_rows():
    whats = sorted(m.what for m in R.compare(_rows(3), _rows(3)[1:] + [_extra()]).mismatches)
    assert whats == ["only_original", "only_recount"]

def test_data_version_needs_different_inputs():
    o, r = _rows(2), _rows(2); r[1] = dict(r[1], net=r[1]["net"] + 5)
    ex = [{"key": list(R.key_of(o[1], "trade")), "category": "data_version", "note": "", "evidence": {"orig_input": 1.0, "recount_input": 1.0}}]
    _raises(R.RecountError, R.finalize, "S", o, r, "trade", ex, [], [], _root())

def test_refuses_unexplained_and_opened_original():
    o, r = _rows(2), _rows(2); r[0] = dict(r[0], net=99.0)
    _raises(R.RecountError, R.finalize, "S", o, r, "trade", [], [], [], _root())
    _raises(R.RecountError, R.finalize, "S", o, o, "trade", [], ["research/oikawa/oj5_lab.py"], ["research/oikawa/oj5_lab.py"], _root())

def test_record_has_no_prices_and_is_append_only():
    root = _root(); o = _rows(3)
    R.finalize("S", o, o, "trade", [], [], [], root); R.finalize("S", o, o, "trade", [], [], [], root)
    rec = S.load_store("records", root)["S"]
    assert rec["agreement"] == 1.0 and "previous" in rec
    assert not _has_value(rec, {x["entry_price"] for x in o} | {x["exit_price"] for x in o})

def test_events_matched_by_symbol_date_flag():
    e = [_event("7203.T", "2026-01-05", "C", 1.2)]
    assert R.compare(e, e, kind="event").matched == 1
```

- [ ] **Step 2:** `PYTHONUTF8=1 python tests/test_recount_compare.py` → 落ちる
- [ ] **Step 3:** Interfaces どおりに書く。CLI＝`python recount_compare.py ORIG RECOUNT --study X --kind trade [--explain FILE] [--opened FILE] [--forbid PATH ...] [--write] [--local-only]`（`--write` なしは突き合わせの表だけ出す）。`RECOUNT_GUIDE.md` を書く
- [ ] **Step 4:** 同じコマンド → 全部通る
- [ ] **Step 5:** `SYNC_FILES` に3ファイルを足す

### Task 6: わざと壊す道具 `mutate_check.py`

**Files:**
- Create: `mutate_check.py`・`tests/test_mutate_check.py`（中に小さな見本の道具とテストを一時フォルダへ書いて使う）
- Modify: `sync_to_github.py`

**Interfaces:**
- Produces:
  - `@dataclass Mutant(id: int, line: int, op: str, before: str, after: str)`（op＝`cmp`／`arith`／`const`／`bool`／`index`）
  - `mutants(src: str) -> list[tuple[Mutant, str]]`（1つずつ変えた版の全文）
  - `run(target: str, test_cmd: list[str], timeout: int = 300, limit: int | None = None) -> dict`＝`{"target","total","killed","survived","timed_out","baseline_ok"}`（survived は Mutant の dict の一覧）
  - CLI：`python mutate_check.py TARGET.py -- <テストのコマンド>`
- 壊し方：`<`↔`<=`・`>`↔`>=`・`+`↔`-`・整数の定数 ±1・`and`↔`or`・添字の整数 ±1
- 仕組み（決めてあること）：元のファイルは開いて読むだけ。一時フォルダに変えた版と `sitecustomize.py` を置き、`sitecustomize` が `importlib.abc.MetaPathFinder` を `sys.meta_path` の先頭に入れて、対象のモジュール名だけ変えた版から読ませる。テストのコマンドは環境変数 `PYTHONPATH` の先頭に一時フォルダを足して走らせる（テスト側の `sys.path` の差し込みに負けない）。最初に壊していない版で走らせ、落ちたら `baseline_ok=False` で止める

- [ ] **Step 1: 失敗するテストを書く**

```python
def test_finds_each_operator_kind():
    ops = {m.op for m, _ in M.mutants("def f(a, b):\n    return a[1] + 2 if a[0] < b and b > 0 else 0\n")}
    assert ops == {"cmp", "arith", "const", "bool", "index"}

def test_weak_test_leaves_survivors_and_original_untouched():
    d = _toy()                                   # toy.py と、境目を見ない test_toy.py
    before = _sha(d / "toy.py")
    rep = M.run(str(d / "toy.py"), [sys.executable, str(d / "test_toy.py")])
    assert rep["baseline_ok"] and rep["survived"] and _sha(d / "toy.py") == before

def test_strong_test_kills_boundary_mutant():
    d = _toy(strong=True)
    rep = M.run(str(d / "toy.py"), [sys.executable, str(d / "test_toy.py")])
    assert not [s for s in rep["survived"] if s["op"] == "cmp"]
```

- [ ] **Step 2:** `PYTHONUTF8=1 python tests/test_mutate_check.py` → 落ちる
- [ ] **Step 3:** Interfaces どおりに書く（`ast` で数えて、`ast.unparse` で全文を作る）
- [ ] **Step 4:** 同じコマンド → 全部通る
- [ ] **Step 5:** `SYNC_FILES` に2ファイルを足す

### Task 7: 表示に「🔍 数え直し待ち」を出す

**Files:**
- Modify: `verified_list.py`（`render`・`render_markers`・`main`）・`promotion_list.py`（`render`・`main`）・`research_map.py`（`_stage` と CSS）・`generate_track_record_page.py`（`build_banzuke_section`）・`auto_weekly_review.py`（`summarize_banzuke`）・`signal_lab_tracker.py`（`table_rows`）
- Test: `tests/test_recheck_display.py`（新しく）

**Interfaces:**
- Consumes: `recheck_status.is_waiting(study, passed_on, root, go_live)`
- Produces:
  - `verified_list.split_waiting(rows: list[dict], root=".", go_live=None) -> tuple[list, list]`（rows は `collect()` の plus。研究の名前＝`_label(r)`、合格の日＝`r["v"].get("decided_on")`）
  - `verified_list.render(..., waiting=None)`：✅ の節と 👀 の節の間に `## 🔍 数え直し待ち（数え直すまで合格として使わない）` を置く。`collect()` の戻りの形は変えない
  - 目印：`marker_verdicts` の `confirm` で `is_waiting(f"{sec}-{cid}", decided_on)` のものは「🔍 数え直し待ち」と出す
  - `promotion_list.main`：🥇 は `split_waiting` を通した残り。🔬 の候補は `is_waiting(item["id"], item["since"])` なら「（数え直し待ち）」を足す
  - 研究の地図・成績ページ・週の振り返り・tracker の表：`status == "promoted"` で `is_waiting(h["id"], h.get("promoted_at"))` のものは段を `("wait", "🔍 数え直し待ち（基準は満たした・数え直すまで使わない）")` にする。`rm-wait` の色は `rm-done` に並べて足す

- [ ] **Step 1: 失敗するテストを書く**

```python
def test_verified_list_moves_new_pass_to_waiting():
    plus = [_row("J9F", "F1", decided_on="2026-12-01"), _row("J4F", "F1", decided_on="2026-11-20")]
    ok, wait = V.split_waiting(plus, _root({}), go_live="2026-11-27")
    assert [r["sec"] for r in ok] == ["J4F"] and [r["sec"] for r in wait] == ["J9F"]
    md = V.render([], ok, [], "2026-12-02", waiting=wait)
    assert md.index("✅ プラスを確認") < md.index("🔍 数え直し待ち") < md.index("👀")

def test_record_releases_to_pass():
    root = _root({"records": {"J9F-F1": {"n_orig": 5, "matched": 5, "agreement": 1.0}}})
    ok, wait = V.split_waiting([_row("J9F", "F1", decided_on="2026-12-01")], root, go_live="2026-11-27")
    assert ok and not wait

def test_map_stage_shows_waiting_but_keeps_adx():
    assert RM._stage({"id": "new", "status": "promoted", "promoted_at": "2026-12-01"}, root=_root({}), go_live="2026-11-27")[0] == "wait"
    assert RM._stage({"id": "rl_tf_adx_strong", "status": "promoted", "promoted_at": "2026-11-07"}, root=_root({}), go_live="2026-11-27")[0] == "done"
```

- [ ] **Step 2:** `PYTHONUTF8=1 python tests/test_recheck_display.py` → 落ちる
- [ ] **Step 3:** 書く（`_stage` には `root=None, go_live=None` を足し、既定は今のまま動く）
- [ ] **Step 4:** 新しいテストと、触ったファイルの既存のテスト（`tests/test_retire.py`・`tests/test_screen_judge.py`・`tests/test_research_map.py`・`tests/test_verified_list_observe.py`）→ 全部通る
- [ ] **Step 5:** `SYNC_FILES` に新しいテストを足す

### Task 8: 使う所で止める（メールの絞り・総当たりの MT5 段）

**Files:**
- Modify: `generate_technical_alerts.py`（`load_promoted_hypotheses` :2774 付近）・`screen_judge.py`（`apply_mt5` :305 付近）
- Test: `tests/test_recheck_gate_live.py`（新しく）

**Interfaces:**
- Consumes: `recheck_status.is_waiting`
- Produces:
  - `load_promoted_hypotheses(kind="edge", path=None, root=None, go_live=None)`：今の戻りから `is_waiting(h["id"], h.get("promoted_at"))` のものを外し、外した id を `🔍 数え直し待ちのため使わない:` で1行出す。読み込みの失敗で `None` を返す今の動きは変えない
  - `screen_judge.apply_mt5(...)`：`candidate` を `mt5_ok` に進める前に `is_waiting(item["id"], item["since"])` なら SystemExit（「数え直しが済むまで MT5 の段に進めません」）
- `ea_bridge.py` は変えない：`promoted_hit` を書く所がどこにも無い（死んだ道）。将来つなぐときは `load_promoted_hypotheses` を通るので、ここで止まる。この事実を `ea_bridge.py` の該当行（:122）にコメント1行で残す

- [ ] **Step 1: 失敗するテストを書く**

```python
def test_new_promoted_edge_waits_old_one_stays():
    p = _tracker([_h("new_edge", "edge", "2026-12-01"), _h("old_edge", "edge", "2026-11-07"), _h("rl_tf_adx_strong", "gate", "2026-11-07")])
    ids = [h["id"] for h in G.load_promoted_hypotheses("edge", path=p, root=_root({}), go_live="2026-11-27")]
    assert ids == ["old_edge"]

def test_recorded_edge_is_used():
    p = _tracker([_h("new_edge", "edge", "2026-12-01")])
    root = _root({"records": {"new_edge": {"n_orig": 9, "matched": 9, "agreement": 1.0}}})
    assert [h["id"] for h in G.load_promoted_hypotheses("edge", path=p, root=root, go_live="2026-11-27")] == ["new_edge"]

def test_broken_records_do_not_crash_alerts():    # Review Focus 4
    p = _tracker([_h("new_edge", "edge", "2026-12-01")])
    assert G.load_promoted_hypotheses("edge", path=p, root=_root_raw("recheck/records.json", "{"), go_live="2026-11-27") == []

def test_screen_candidate_cannot_enter_mt5_before_recount():
    rec = _screen_record(since="2026-12-01")
    _raises(SystemExit, _apply_mt5, rec, "c1", _root({}), "2026-11-27")   # _apply_mt5＝今の apply_mt5 の引数に合わせて呼び、後ろに root と go_live を渡す小さな助け
```

- [ ] **Step 2:** `PYTHONUTF8=1 python tests/test_recheck_gate_live.py` → 落ちる
- [ ] **Step 3:** 書く（`apply_mt5` の今の引数はそのまま、`root=None, go_live=None` を後ろに足す）
- [ ] **Step 4:** 新しいテスト・`tests/test_watch_email.py`・`tests/test_screen_judge.py`・`tests/test_ea_tools.py` → 全部通る
- [ ] **Step 5:** `SYNC_FILES` に新しいテストを足す

### Task 9: 登録の関門（`mw check`）と DOCTRINE の関門

**Files:**
- Modify: `check_site_consistency.py`（`check_prereg_audit()` を足し `main()` から呼ぶ）・`_doctrine_check.py`（`check_doctrine_recheck()` を足し `main()` の `check_regime_state()` の後で呼ぶ・冒頭の検査の一覧に9番として書く）
- Create: `tests/test_prereg_audit.py`・`_test_doctrine_recheck.py`（`_` 始まり＝手元だけ・`_test_doctrine_registry.py` と同じ読み込み方）

**Interfaces:**
- Consumes: `recheck_status.GO_LIVE`・`audit_by_fingerprint`・`recheck_ok`
- Produces:
  - `check_prereg_audit(text: str | None = None, root: str | None = None, go_live: str | None = None)`：`PILLAR_PREREG.md` を `\n## ` で節に分け、見出しの日付（正規表現 `(\d{4}-\d{2}-\d{2})[^）・]{0,6}登録`）が go_live 以降で、本文に `\n**結果（` がある節だけを見る。`**結果（` から節の終わりまでに `` 点検の指紋 `([0-9a-f]{12})` `` が無い → error「🚨 <見出しの頭>: 結果があるのに点検の指紋が無い」。指紋が `audit_by_fingerprint` で見つからない、または見つかった記録の `errors > 0` → error。見出しに日付の無い節は見ない
  - `check_doctrine_recheck()`：`research/DOCTRINE.md` の `### ✅`・`### 🏅` で始まる見出しを、`research/_doctrine_recheck_baseline.json`（無ければ今ある見出しで作る＝さかのぼらない）と比べる。新しい見出しの節に `[recheck:<研究>]` が無いか、`recheck_ok(研究)` が偽なら `errors` に足す
- 結果の書き方（新しい登録から）：`**結果（…・節の指紋 `…`・道具の指紋 `…`・点検の指紋 `<12文字>`）**`

- [ ] **Step 1: 失敗するテストを書く**

```python
def test_new_registration_with_result_needs_audit():
    t = _prereg("## X1 試し（2026-12-01 登録）\n本文\n**結果（2026-12-02・登録どおり1回）**：ストップ\n")
    _run(t, _root({}), "2026-11-27"); assert any("点検の指紋" in e for e in csc.errors)

def test_audit_fingerprint_passes_and_errors_fail():
    fp = "ab12cd34ef56"
    ok = _root({"audits": {"X1": {"fingerprint": fp + "0" * 52, "errors": 0}}})
    t = _prereg(f"## X1 試し（2026-12-01 登録）\n**結果（2026-12-02・点検の指紋 `{fp}`）**：ストップ\n")
    _run(t, ok, "2026-11-27"); assert not csc.errors
    bad = _root({"audits": {"X1": {"fingerprint": fp + "0" * 52, "errors": 2}}})
    _run(t, bad, "2026-11-27"); assert csc.errors

def test_old_and_undated_and_duplicate_ids_are_fine():   # Review Focus 5
    t = _prereg("## OJ5 v5（2026-11-26 登録）\n**結果（2026-11-28）**：x\n## B4 追記（2026-09-27 午後）\n**結果（…）**\n## 共通の決まり\n**結果（…）**\n")
    _run(t, _root({}), "2026-11-27"); assert not csc.errors

def test_registration_without_result_is_fine():
    _run(_prereg("## X2 まだ（2026-12-01 登録）\n本文\n"), _root({}), "2026-11-27"); assert not csc.errors
```

`_test_doctrine_recheck.py`：新しい `### ✅` に `[recheck:Q99]` が無ければ error／記録があれば通る／基準のファイルに入っている見出しは通る、の3つ。

- [ ] **Step 2:** `PYTHONUTF8=1 python tests/test_prereg_audit.py` と `PYTHONUTF8=1 python _test_doctrine_recheck.py` → 落ちる
- [ ] **Step 3:** 書く
- [ ] **Step 4:** 同じ2つ → 通る。`python mw.py check` → 今の PILLAR_PREREG で error 0（今日より前の登録だけなので）。`PYTHONUTF8=1 python _doctrine_check.py` → 今と同じ結果（基準のファイルができるだけ）
- [ ] **Step 5:** `SYNC_FILES` に `tests/test_prereg_audit.py` を足す（`_doctrine_check.py`・`_test_*` は `_` 始まり＝送らない）

### Task 10: 見張り番に「数え直し待ち」の節を足す

**Files:**
- Modify: `check_automation_health.py`（純粋な関数 `eval_recheck_waiting` と、節⑥の後に新しい節）
- Test: `tests/test_health_recheck.py`

**Interfaces:**
- Consumes: `recheck_status.GO_LIVE`・`entry_ok`・`safe`
- Produces: `eval_recheck_waiting(tracker: dict, records: dict, screens: list[dict], today: str, go_live: str) -> tuple[str, str, list[str]]`
  - 戻り＝`("new" | "waiting" | "none", 日本語1行, 研究の名前の一覧)`
  - 待ち＝tracker の `promoted` で `promoted_at >= go_live` かつ `recheck_status.entry_ok(records.get(safe(id)))` が偽のもの＋screens の `promoted[]` で `stage == "candidate"`・`since >= go_live`・記録無し
  - 「new」＝待ちのうち、合格の日が今日から2日以内のものがある
- 節：`new` → `bad.append(("数え直し待ち", "warn"))`（Issue に出る）／`waiting` → ⚪ の行だけ（毎日の Issue の書き込みを増やさない＝知らせ疲れを避ける）／`none` → ✅。読みは今の `api_raw` で `signal-lab-tracker.json`・`recheck/records.json`・`m6-screen.json`・`m7-screen.json`。読めないときは ⚪

- [ ] **Step 1: 失敗するテストを書く**

```python
def test_new_waiting_warns_once_then_quiet():
    tr = {"hypotheses": [{"id": "e1", "status": "promoted", "promoted_at": "2026-12-01"}]}
    assert H.eval_recheck_waiting(tr, {}, [], "2026-12-02", "2026-11-27")[0] == "new"
    assert H.eval_recheck_waiting(tr, {}, [], "2026-12-06", "2026-11-27")[0] == "waiting"

def test_old_promotion_and_recorded_are_not_waiting():
    tr = {"hypotheses": [{"id": "rl_tf_adx_strong", "status": "promoted", "promoted_at": "2026-11-07"},
                         {"id": "e2", "status": "promoted", "promoted_at": "2026-12-01"}]}
    rec = {"e2": {"n_orig": 3, "matched": 3, "agreement": 1.0}}
    assert H.eval_recheck_waiting(tr, rec, [], "2026-12-02", "2026-11-27")[0] == "none"

def test_screen_candidate_counts():
    sc = [{"promoted": [{"id": "c1", "stage": "candidate", "since": "2026-12-01"}]}]
    assert H.eval_recheck_waiting({"hypotheses": []}, {}, sc, "2026-12-01", "2026-11-27")[2] == ["c1"]
```

- [ ] **Step 2:** `PYTHONUTF8=1 python tests/test_health_recheck.py` → 落ちる
- [ ] **Step 3:** 書く（節は ⑥ の書き方をまねる。例外は ⚪ で受ける）
- [ ] **Step 4:** 新しいテストと `tests/test_health_*.py` → 全部通る
- [ ] **Step 5:** `SYNC_FILES` に新しいテストを足す

### Task 11: 送る準備・文書・送る

**Files:**
- Modify: `_config.yml`（`exclude` に `recheck/`）・`.github/workflows/research-lists.yml`（`on.push.paths` に `recheck/records.json`＝`verified_list.py` が読むので）・`sync_to_github.py`（`recheck/records.json`・`recheck/audits.json` を `SYNC_NOT_YET` に「最初の記録ができる日まで」として入れる＝無くても失敗にしない）・`RESEARCH_LABS.md`（共通の決まりに1行）・`OPERATIONS.md`（「検算の関門」の節）・`SESSION_HANDOFF.md`（`_doctrine_check.py` を強めた理由・先に古い節を SESSION_ARCHIVE へ）
- 研究ラボの共通の決まりの1行：「2026-11-27 から：run は結果を書く前に `result_audit.gate(rows, ctx, study)` を通す（取引の一覧は `to_common()` で共通の形に）。結果の行に `点検の指紋` を書く。合格側の判定は `recheck/RECOUNT_GUIDE.md` で数え直し、`recheck/records.json` に一致100%の記録が無いうちは使わない。新しい道具は `mutate_check.py` で壊した数・気づかなかった数とその理由を登録に書く」
- CLAUDE.md は 32KB の上限の近く（32,670 バイト）＝書き足さない

- [ ] **Step 1:** 上の変更を入れる
- [ ] **Step 2:** 全部のテスト：`for f in tests/test_*.py; do PYTHONUTF8=1 python "$f" >/dev/null 2>&1 || echo "FAIL $f"; done` → 落ちるのは前からの7つ（auto_pull ×2・fx_clock_lab・gemini_retired_models・holiday_lab・pillar_lab_jp・research_map のナビの名前）だけ。増えていれば直す
- [ ] **Step 3:** `python mw.py check` → error 0
- [ ] **Step 4:** `PYTHONUTF8=1 python sync_to_github.py --batch --dry-run` → 送るのが Task 0〜10 のファイルだけで `research/` が入っていないのを見てから `--batch`
- [ ] **Step 5:** 次の Actions の実行（technical-alerts・research-lists）で、メールの絞りと検証済みリストが今までと同じ中身なのを確かめる（いま待ちになるものは無いはず）

### Task 12: 洗い直し① ADX の見送り（`rl_tf_adx_strong`）

**Files:**
- Create: `research/recheck/rl_tf_adx_strong/export.py`（元の結果を共通の形で出す・手元だけ）

- [ ] **Step 1:** `export.py`：`signals-log.json` のうち `rl_tf_adx_strong` に当てはまる行（決まった日＝この Task を始めた日の前日までの記録）を共通の形で出す。結果（損切り・利確に当たったか・費用・r）は記録の値をそのまま写す＝これが「元の一覧」
- [ ] **Step 2:** `python result_audit.py research/recheck/rl_tf_adx_strong/orig.csv --study rl_tf_adx_strong` → error があればオーナーへ
- [ ] **Step 3:** 数え直しの担当を `recheck/RECOUNT_GUIDE.md` のひな形で呼ぶ。渡すもの＝仮説の定義（tracker の `label` と `filter` の意味の文）・登録の日・使う値段の足の置き場。開かないもの＝`signal_lab_tracker.py`・`signal_lab_verify.py`・`generate_technical_alerts.py`。合図の入力（その時の ADX など）は記録の値を使い、結果の判定は値段の足から作り直す（設計書 5.6）
- [ ] **Step 4:** `python recount_compare.py orig.csv recount-rows.csv --study rl_tf_adx_strong --kind trade` → 食い違いを全部説明（explanations.json に追記）→ 一致100%で `--write`
- [ ] **Step 5:** オーナーへ報告：一致したか・食い違いの内訳・直したもの（「研究の記録で、投資の助言ではありません」を添える）。外すかはオーナーが決める

### Task 13: 洗い直し②〜⑤

設計書 5.6 の表の順（②目印C・B候補＝J26・J16／J17 → ③危険スコア＝DOCTRINE Q12・Q14・Q22・Q26-A → ④決算のゲート J6 → ⑤そのほかの目印 J21・J36・J42・J49・前向きの記録）に、Task 12 と同じ5つの手順を1件ずつ。目印は event の形。J-Quants を使うものは `--local-only`（記録は `research/recheck/` に）。1件ごとにオーナーへ報告してから次へ

### Task 14: OJ5 にあとから点検をかける（OJ5 の run の後）

- [ ] **Step 1:** OJ5 を登録どおり1回 run（道具は変えない＝設計書 5.7）
- [ ] **Step 2:** `convert_existing.from_oj` で `oj5-trades-{C,B,A}.csv` を共通の形にし、`result_audit.py` をかける（C の抜けの割合は `check` の出力の数を `missing_ratio` に渡す）
- [ ] **Step 3:** 誤りが見つかれば「計算の誤りの直し」として登録に追記。見つからなければ PILLAR の OJ5 の結果に「あとからの点検：error 0（点検の指紋 `…`）」を追記
