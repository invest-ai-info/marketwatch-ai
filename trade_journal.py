# -*- coding: utf-8 -*-
"""オーナーの裁量の取引の記録（段3）。PILLAR_PREREG.md「OJ」・MY_TRADING_RULES.md「デイトレ開始にあたっての事前登録」（2026-07-26）。

2026-11-24 オーナー「最終的にはシステムトレードで高勝率のトレードを目指したい」→「1段と3段を並行してください」。
オーナーが MT4 の注文の行（とチャート）を送ってくれたら、セッションが1件ずつ足す。
- 物差し＝**費用を引いた後の R**（MT4 の約定値は買いが買値・決済が売値＝スプレッドは結果にもう入っている）。
  R＝損益（pips）÷ 損切りまでの幅（pips）。損切りの逆指値が無い取引は R を出せない＝数えずに別に数える
- 決まりの紙 v1（PILLAR_PREREG.md「OJ」）の項目を ○×（True/False・わからなければ None）で残す
- ⚠️ 残すのは値段・pips・R・○× だけ。**ロット・円の損益・口座の番号・名前は残さない**（公開リポジトリのため）
- ⚠️ 判定は 7/26 の事前登録どおり **30件ごと（30・60・90…）に1回だけ**。それまで平均は出さない（途中の数字を見て続け方を変えないため）。
  判定＝その時点の全件の R の平均の95%の幅（日ごとのまとまりで引き直す・10,000回）。下限>0＝機能している／上限<0＝反証／ほか＝まだ分からない。
  同じ日に、項目ごとの ○ と × の平均を「読むための表」として出す（決まりにはしない＝決まりにするなら段2の過去のデータか別の前向きで確かめる）

使い方:
  python trade_journal.py add --id 30211960 --pair GBPJPY --side buy \
      --open "2026.11.24 09:04:08" --entry 207.605 --sl 207.469 --tp 207.778 \
      --close "2026.11.24 09:27:03" --exit 207.734 --spread 1.8 --server-time \
      --entry-type ema15 --push 2 --sl-line 207.51 \
      --flags tokyo_break=1,strongest=1,htf_aligned=0,tp_before_high=0,event_clear=1,sl_at_line=1 \
      --note "ユーロドルの直近安値のラインと比べ、上に強いほうのポンド円"
  50%押し目（型1＝memory/07_fx_setups.md）は --entry-type half50 と、割った線・そこからいちばん遠くまで行った値を付ける：
      … --entry-type half50 --break-line 209.963 --extreme 209.570
      （線で入る2発目も half50＝depth_pct が 100 前後になる。型1 は足の確定で手じまうが、逆指値が無いと R を出せず判定に数えない）
  決まりの紙 v2（「OJ」追記⑥＝抜けて30分以内に30pips → 50%・水平線・MA の押し・損切りは割った線の 4pips 外）は、当たった線を
  --entry-type half50（50%）・line（割った線）・ema15（MA）で選び、割った線・いちばん遠い値に加えて
      … --far-min 20 --pairs-hit 2 --sl-line 割った線
      --far-min＝抜けた5分足が確定してから、ヒゲが線から30pips に届いた足が確定するまでの分（抜けた足そのものなら 0・届いていなければ付けない）
      --pairs-hit＝入ったとき、ドル円・ユーロ円・ポンド円のうち、それぞれの 50%・割った線・MA のどれかまで 3pips 以内に来ていた数（入ったペアも入れる）
  決まりの紙 v3（「OJ」追記⑧・2026-11-25＝3つのうち2つ以上が割った線か MA に当たったときに、一番強い通貨に入る。50% は当たりに入れない・強い通貨そのものは当たっていなくてよい）は
      … --far-min 20 --pairs-lm 2 --flags strongest=1 --sl-line 割った線（--pairs-lm＝割った線か MA まで 3pips 以内に来ていた数。入ったペアがまだ線の手前なら --entry-type series）
  🆕 **いつもの足し方**（ドル円・ユーロ円・ポンド円）＝ add に --auto を付ける：入口の種類・割った線・いちばん遠い値・30pips までの分・当たったペアの数・
     一番強い通貨か・3ペアそろいを、Yahoo の足から埋める（trade_fill.py・入る前の値だけ）。人が渡した値がいつも優先。v1〜v3 だけで使う項目（線・30pips・種類・当たりの数・3ペアそろい）が決まらないときは**聞かずに空**（⬜・11/25 オーナー「聞かずに空にする」）
     聞くのは v4 の2つだけ（型・ユーロポンドで強いほう）＝決まらないと**書かずに止まる** → 値を付けてもう一度／分からないままなら --unknown strong,kata。書かずに見るだけ＝ python trade_journal.py fill --pair … --side … --open … --entry …
  決まりの紙 v4（「OJ」追記⑨⑩・2026-11-25＝ユーロポンドで「ユーロかポンドか」・ドル円で「上か下か」）は、--auto が trade_v4.py で埋める（ユーロドル・ポンドドルの取引も向きと型だけ埋める）：
     型（--kata push＝①押し目／fade＝②抜けの失敗の逆張り／range＝④ドル円レンジの押し目／other）・ドル円とユーロポンドの1時間の動き・強いほう・見るペアの線と端・項目7つ・v4 の出口まで・伸ばした分
     ①と④は道具が決める。②・どれでもない・境目は聞く（②は、抜けと逆の向きに入るので道具は決めない）
  python trade_journal.py status
  （--server-time＝MT4 の画面の時刻（BigBoss のサーバー時刻）を日本時間に直す。冬＝+7時間・夏＝+6時間）
"""
import argparse
import datetime as dt
import json
import random
import sys

JOURNAL = "trade-journal.json"
START = "2026-11-24"          # 記録を始めた日（PILLAR_PREREG.md「OJ」の登録の日）
CHECK_EVERY = 30              # 7/26 の事前登録の刻み（signal_lab_tracker の PROMOTE_MIN_N_HOLDOUT と同じ）
N_BOOT = 10000
SEED = 20261124
WINDOW = ("15:00", "16:55")   # 決まりの紙 v1 の入る時間（TB と同じ・日本時間）
SPREAD_MAX = 2.5              # 決まりの紙 v1：スプレッドがこれより広ければ入らない（pips）
COST_MULT = 7.0               # 決まりの紙 v1：損切りの幅はスプレッドの7倍以上（費用 0.15R 以下）
# 手で付ける項目（決まりの紙 v1 の部品）。自動で付く3つ（in_window・sl_order・spread_ok）は数字から決める
MANUAL_FLAGS = ("tokyo_break", "strongest", "htf_aligned", "tp_before_high", "event_clear", "sl_at_line")
AUTO_FLAGS = ("in_window", "sl_order", "spread_ok", "weekday_ok", "in_window2", "far30", "pairs2", "pairs_lm2", "pick_flow", "pick_far",
              "both_broken", "usd_dir", "pick_eg", "far20", "fresh", "pull50", "touch1", "in_window5", "ldn_flat", "usd_dir5", "pick_eg5")
# half50＝50%押し目（型1：クロス円がそろって東京時間の線を割る → 線と新安値の 50% の戻りで入る。2026-11-24 夜 オーナー「はい、足す」）。判定は種類で分けない＝読むための表だけ
# series＝ほかの2ペアが線か MA に当たったとき、まだ線の手前にいる一番強いペアに入った（v3・11/25）
ENTRY_TYPES = ("ema15", "line", "half50", "series", "other")
TYPE_JP = {"ema15": "15分足EMAの押し", "line": "ライン", "half50": "50%押し目", "series": "シリーズの当たり（入ったペアは線の手前）", "other": "ほか"}
# 何押しで入ったか（2026-11-24 夜 オーナー「1押し、2押しで入った場合は1押しの方の直近安値のラインで損切り」）
PUSHES = ("break", "1", "2", "3+")
# 入口が決まりの紙 v1 に全部当てはまるか（出口の tp_before_high と、段2で腕にする htf_aligned は入れない）
V1_ENTRY = ("tokyo_break", "in_window", "strongest", "sl_order", "event_clear", "spread_ok", "weekday_ok")
# 決まりの紙 v2（「OJ」追記⑥・2026-11-24 夜 オーナー「ブレイクしてから30分以内に30ピップス以上離れたものだけ押し目待ち…50%か、水平線か、MA」→「これからの取引を記録する」）
# 2ペア以上（pairs2）は「できれば」＝入口の条件に入れず、読むための表で分ける
FAR_PIPS = 30.0
FAR_MIN = 30
FILL_TOL = 0.5                # trade_fill.py で埋めた値の幅（pips・trade_fill.TOL と同じ）
WINDOW2_HOURS = 2             # 終わり＝ロンドンの始まり（英国の朝8時）から2時間まで（段2の登録と同じ＝冬 19:00・夏 18:00 の前）
V2_ENTRY = ("tokyo_break", "in_window2", "strongest", "sl_order", "event_clear", "spread_ok", "weekday_ok", "far30")
V2_TYPES = ("ema15", "line", "half50")
# 決まりの紙 v3（「OJ」追記⑧・2026-11-25 オーナー「入る条件はドル円、ユーロ円、ポンド円の2つ以上が水平線かMAに当たったときに、そのときに一番強い通貨にエントリーする」）
# 2ペア以上は条件・50% は当たりに入れない・入ったペアがどの線に当たっていたかは問わない
V3_ENTRY = ("tokyo_break", "in_window2", "strongest", "sl_order", "event_clear", "spread_ok", "weekday_ok", "far30", "pairs_lm2")
# 決まりの紙 v4（「OJ」追記⑨⑩・2026-11-25 オーナー「主役はあくまでユーロとポンド。で、ドル円は上か下かの判断でしかありません」→ 記録に「足す」）。trade_v4.py の FLAGS・KATA と同じ（テストで見張る）
KATA = ("push", "fade", "range", "other")
KATA_JP = {"push": "①押し目", "fade": "②抜けの失敗の逆張り", "range": "④ドル円レンジの押し目", "other": "ほか"}
V4_FLAGS = ("both_broken", "usd_dir", "pick_eg", "far20", "fresh", "pull50", "touch1")
V4_ENTRY = ("in_window2", "sl_order", "event_clear", "spread_ok", "weekday_ok") + V4_FLAGS      # ①押し目の入口。strongest・tokyo_break（3ペアそろい）は条件に入れない（pick_eg・both_broken が代わり）
V4_KEYS = ("usd_1h", "eg_1h", "strong_eg", "watch", "watch_line", "watch_extreme")
AFTER_KEYS = ("v4_exit", "v4_exit_min", "v4_exit_pips", "run_pips", "mfe_pips")                 # 入ったあと。書くだけ＝足すときに見せない・判定の日に読む表だけ
# 決まりの紙 v5（「OJ」追記⑫・2026-11-25 オーナー「ロンドン時間が始まる5分前には手締まりして、ロンドン時間が始まったらまたそこから新しく考え始める。方向性を考え始める」）
# 聞いて決めたこと（3つとも選んでもらった答え）：新しく入るのは始まりの30分後から・向きは始まりからの動きだけで測る・線は東京の線のまま。ほかは v4 と同じ
LDN_FLAT_MIN = 5              # ロンドンの始まりの5分前（冬 16:55・夏 15:55）に手じまう。その1分のうちの決済は ○
LDN_WAIT_MIN = 30             # 始まりから30分（冬 17:00〜17:29・夏 16:00〜16:29）は入らない＝そこから新しく考える
V5_FLAGS = ("both_broken", "usd_dir5", "pick_eg5", "far20", "fresh", "pull50", "touch1")
V5_ENTRY = ("in_window5", "sl_order", "event_clear", "spread_ok", "weekday_ok") + V5_FLAGS      # ①押し目の入口（v4 の時間と向きだけを替えた）
V5_KEYS = ("usd_ldn", "eg_ldn", "strong_ldn", "kata5")                                            # trade_v4.record の答え（始まりからの動き・強いほう・型）
PAPERS = ("v1", "v2", "v3", "v4", "v5")


def empty_state():
    return {"registered": "OJ", "start": START, "check_every": CHECK_EVERY, "trades": [], "checkpoints": []}


def load(path=JOURNAL):
    try:
        with open(path, encoding="utf-8") as fh:
            st = json.load(fh)
    except FileNotFoundError:
        return empty_state()
    if st.get("start") != START:
        raise SystemExit(f"🚨 {path} の開始日 {st.get('start')} が {START} と違う＝上書きしない")
    return st


def save(st, path=JOURNAL):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(st, fh, ensure_ascii=False, indent=1)
        fh.write("\n")


def us_dst(day):
    """米国の夏時間か（3月の第2日曜〜11月の第1日曜）。BigBoss のサーバー時刻はこれに合わせて GMT+3／+2 を切り替える"""
    y = day.year
    mar = dt.date(y, 3, 8) + dt.timedelta(days=(6 - dt.date(y, 3, 8).weekday()) % 7)
    nov = dt.date(y, 11, 1) + dt.timedelta(days=(6 - dt.date(y, 11, 1).weekday()) % 7)
    return mar <= day < nov


def last_sunday(year, month):
    d = dt.date(year, month, 31)          # 3月・10月だけで使う（どちらも31日まで）
    return d - dt.timedelta(days=(d.weekday() + 1) % 7)


def london_open(day):
    """ロンドンの始まり（英国の朝8時）の日本時間の時。冬＝17・夏＝16。英国の夏時間（3月〜10月の最後の日曜）で決まる（米国とは切り替えの日が違う）"""
    return 16 if last_sunday(day.year, 3) <= day < last_sunday(day.year, 10) else 17


def london_phase(t):
    """日本時間 t → "before"（始まりの5分前より前）・"flat"（5分前〜30分後＝持たない・入らない）・"after"（30分後から＝新しく考える）。v5（追記⑫）"""
    l0 = dt.datetime(t.year, t.month, t.day, london_open(t.date()))
    if t < l0 - dt.timedelta(minutes=LDN_FLAT_MIN):
        return "before"
    return "flat" if t < l0 + dt.timedelta(minutes=LDN_WAIT_MIN) else "after"


def in_window5(t_open):
    """v5 の入る時間：15:00〜始まりの5分前の前（冬 16:55・夏 15:55）と、始まりの30分後〜2時間後の前（冬 17:30〜19:00・夏 16:30〜18:00）"""
    if t_open.time() < dt.time(15, 0):
        return False
    ph = london_phase(t_open)
    return ph == "before" or (ph == "after" and t_open.hour < london_open(t_open.date()) + WINDOW2_HOURS)


def ldn_flat_ok(t_open, t_close):
    """始まりの5分前をまたいで持っていないか（v5）。5分前の1分（冬 16:55:00〜16:55:59）のうちに決済すれば ○"""
    l0 = dt.datetime(t_open.year, t_open.month, t_open.day, london_open(t_open.date()))
    cut = l0 - dt.timedelta(minutes=LDN_FLAT_MIN)
    return not (t_open < cut and t_close >= cut + dt.timedelta(minutes=1))


def server_to_jst(t):
    """MT4（BigBoss）のサーバー時刻 → 日本時間。冬（GMT+2）＝+7時間・夏（GMT+3）＝+6時間"""
    return t + dt.timedelta(hours=6 if us_dst(t.date()) else 7)


def parse_time(s):
    s = s.strip().replace("/", ".").replace("-", ".")
    for fmt in ("%Y.%m.%d %H:%M:%S", "%Y.%m.%d %H:%M"):
        try:
            return dt.datetime.strptime(s, fmt)
        except ValueError:
            pass
    raise SystemExit(f"🚨 時刻が読めない：{s}")


def pip_size(pair):
    return 0.01 if pair.upper().endswith("JPY") else 0.0001


def parse_flags(text):
    out = {k: None for k in MANUAL_FLAGS}
    for part in (text or "").split(","):
        if not part.strip():
            continue
        k, _, v = part.partition("=")
        k = k.strip()
        if k not in MANUAL_FLAGS:
            raise SystemExit(f"🚨 知らない項目：{k}（使えるのは {', '.join(MANUAL_FLAGS)}）")
        v = v.strip().lower()
        out[k] = None if v in ("", "?", "none") else v in ("1", "true", "yes", "y", "o", "○")
    return out


def leg_of(side, entry, break_line, extreme, pip):
    """割った線からいちばん遠くまで行った値（売り＝新安値・買い＝最高値）までの pips と、入った値がその何％戻したところか。純関数
    50＝ちょうど真ん中・100＝線まで戻った。線と新安値の値は、50% を測った時点のもの（入る前まで）"""
    if break_line is None and extreme is None:
        return None, None
    if break_line is None or extreme is None:
        raise ValueError("--break-line と --extreme は両方いる（片方だけでは測れない）")
    sgn = 1 if side == "buy" else -1
    leg = (extreme - break_line) * sgn
    if leg <= 0:
        raise ValueError("新安値（買いは最高値）が線の内側にある（入力の取り違え？）")
    return round(leg / pip, 1), round((extreme - entry) * sgn / leg * 100, 1)


def far30_of(leg_pips, far_min, tol=0.0):
    """抜けて30分以内に線から30pips 離れたか。True／False／分からない（None）。純関数
    tol＝線やいちばん遠い値を Yahoo の足から埋めたときの、業者の値とのずれの幅（この中なら、人が言った分を信じる）"""
    if far_min is not None and far_min < 0:
        raise ValueError("--far-min は 0 以上")
    if leg_pips is not None and leg_pips < FAR_PIPS:
        if far_min is None:
            return False
        if leg_pips < FAR_PIPS - tol:
            raise ValueError("線から30pips 離れていないのに --far-min がある（入力の取り違え？）")
    return None if far_min is None else far_min <= FAR_MIN


def fits(flags, keys, type_ok):
    """項目が全部 ○＝True・1つでも × か入口の種類が違う＝False・ほか（種類が決まらない None も）＝None"""
    vals = [flags.get(k) for k in keys] + [type_ok]
    if False in vals:
        return False
    return None if None in vals else True


def fits_v4(flags, kata, keys=V4_ENTRY):
    """決まりの紙 v4 の①押し目の入口に全部当てはまるか。②④は紙に入口の決まりが無い（記録だけ）＝None・型が分からない＝None・ほか＝False"""
    if kata in ("fade", "range"):
        return None
    f = fits(flags, keys, kata != "other")
    return None if f and kata is None else f


def fits_v5(flags, kata5):
    """決まりの紙 v5 の①押し目の入口（v4 の時間を in_window5 に・向きと強いほうを始まりからの動きに替えたもの）。型は v5 の型（kata5）"""
    return fits_v4(flags, kata5, V5_ENTRY)


def pnl_of(pair, side, entry, exit_, pip=None):
    return round((exit_ - entry) * (1 if side.lower() == "buy" else -1) / (pip or pip_size(pair)), 1)


def make_trade(tid, pair, side, t_open, entry, sl, tp, t_close, exit_, spread=None, pip=None,
               entry_type="other", flags=None, note="", used_for_rule=False, push=None, sl_line=None,
               break_line=None, extreme=None, far_min=None, pairs_hit=None, filled=(), far_unknown=False,
               pairs_lm=None, strong_flow=None, strong_far=None, kata=None, v4=None, after=None):
    """MT4 の行の数字 → 記録（値段・pips・R・○×だけ）。t_open・t_close は日本時間。純関数

    used_for_rule＝決まりの紙を作るのに使った取引（11/24 のポンド円）。7/26 の判定には数えるが、読むための表からは外す
    push＝何押しで入ったか（break＝ブレイクラインまでの戻り・1・2・3+）。sl_line＝決まりの損切りの線（ブレイクラインか1押しの安値）の値段
    → 逆指値がその線からどれだけ離れていたか（sl_buffer_pips・余白）を残す＝段2の前に余白を決めるため（成績は見ない）
    break_line・extreme＝割った線と、そこからいちばん遠くまで行った値（型1）→ leg_pips・depth_pct を残す
    far_min＝抜けてから30pips 離れるまでの分・pairs_hit＝線の近くにいたペアの数（決まりの紙 v2）→ far30・pairs2 を残す
    filled＝trade_fill.py が埋めた項目（人が言った値と分けて残す）・far_unknown＝30pips に届いたかが決まらない（聞かずに空）
    pairs_lm＝割った線か MA に当たっていたペアの数（v3）→ pairs_lm2。strong_flow・strong_far＝道具が出した「一番強い通貨」の2つの答え（ドル円×ユーロポンドの向き／線からいちばん遠い割合）
    → 入ったペアと同じか（pick_flow・pick_far）を読むための表に残す。決まりの○×は strongest（オーナーの見立てが優先）
    kata＝型（v4）・v4＝trade_v4.record の答え（向き・強いほう・見るペアの線と端・項目7つ）・after＝trade_v4.after の答え（v4 の出口・伸ばした分）。無ければ None のまま
    """
    side = side.lower()
    if side not in ("buy", "sell"):
        raise ValueError("side は buy か sell")
    if entry_type is not None and entry_type not in ENTRY_TYPES:      # None＝--auto で決まらなかった
        raise ValueError(f"entry_type は {ENTRY_TYPES}")
    if push is not None and push not in PUSHES:
        raise ValueError(f"push は {PUSHES}")
    if kata is not None and kata not in KATA:
        raise ValueError(f"kata は {KATA}")
    for k, v in (("pairs_hit", pairs_hit), ("pairs_lm", pairs_lm)):
        if v is not None and not 0 <= v <= 3:
            raise ValueError(f"{k} は 0〜3（ドル円・ユーロ円・ポンド円）")
    pip = pip or pip_size(pair)
    sgn = 1 if side == "buy" else -1
    sl = sl if sl else None             # MT4 の 0.00000＝逆指値なし
    tp = tp if tp else None
    pnl = pnl_of(pair, side, entry, exit_, pip)
    risk = round(abs(entry - sl) / pip, 1) if sl is not None else None
    if risk is not None and (sl - entry) * sgn >= 0:
        raise ValueError("損切りが入った値の利益側にある（入力の取り違え？）")
    r_net = round(pnl / risk, 3) if risk else None
    buf = round((sl_line - sl) * sgn / pip, 1) if (sl is not None and sl_line) else None
    leg_pips, depth_pct = leg_of(side, entry, break_line, extreme, pip)
    cost_r = round(spread / risk, 3) if (risk and spread is not None) else None
    r_gross = round((pnl + spread) / risk, 3) if (risk and spread is not None) else None
    kind = "manual"
    if sl is not None and abs(exit_ - sl) <= pip * 0.5:
        kind = "sl"
    elif tp is not None and abs(exit_ - tp) <= pip * 0.5:
        kind = "tp"
    f = dict(flags or {k: None for k in MANUAL_FLAGS})
    hm = t_open.strftime("%H:%M")
    f["in_window"] = WINDOW[0] <= hm <= WINDOW[1]
    f["sl_order"] = sl is not None
    f["weekday_ok"] = t_open.weekday() <= 3   # 月〜木（オーナー「もちろん金曜日は取引しません」・日本時間）
    f["spread_ok"] = (spread <= SPREAD_MAX and risk >= COST_MULT * spread) if (risk and spread is not None) else (
        False if (spread is not None and spread > SPREAD_MAX) else None)
    f["in_window2"] = dt.time(15, 0) <= t_open.time() < dt.time(london_open(t_open.date()) + WINDOW2_HOURS, 0)
    f["far30"] = None if far_unknown else far30_of(leg_pips, far_min, FILL_TOL if {"break_line", "extreme"} & set(filled) else 0.0)
    f["pairs2"] = None if pairs_hit is None else pairs_hit >= 2
    f["pairs_lm2"] = None if pairs_lm is None else pairs_lm >= 2
    f["pick_flow"], f["pick_far"] = (None if x is None else x == pair.upper() for x in (strong_flow, strong_far))
    v4, after = v4 or {}, after or {}
    f.update({k: (v4.get("flags") or {}).get(k) for k in V4_FLAGS})
    f["in_window5"] = in_window5(t_open)
    f["ldn_flat"] = ldn_flat_ok(t_open, t_close)
    f.update({k: (v4.get("flags5") or {}).get(k) for k in ("usd_dir5", "pick_eg5")})
    kata5 = v4.get("kata5", kata) if v4 else kata                       # v5 の型（--auto で埋めていなければ v4 の型と同じ）
    return {"id": str(tid), "date": t_open.strftime("%Y-%m-%d"), "entry_time": t_open.strftime("%H:%M:%S"),
            "exit_time": t_close.strftime("%H:%M:%S"), "hold_min": round((t_close - t_open).total_seconds() / 60, 1),
            "pair": pair.upper(), "side": side, "entry": entry, "sl": sl, "tp": tp, "exit": exit_,
            "spread_pips": spread, "risk_pips": risk, "pnl_pips": pnl, "r_net": r_net, "r_gross": r_gross,
            "cost_r": cost_r, "exit_kind": kind, "entry_type": entry_type, "push": push, "sl_line": sl_line,
            "sl_buffer_pips": buf, "break_line": break_line, "extreme": extreme, "leg_pips": leg_pips,
            "depth_pct": depth_pct, "far_min": far_min, "pairs_hit": pairs_hit, "pairs_lm": pairs_lm, "strong_flow": strong_flow, "strong_far": strong_far, "flags": f,
            "fits_v1_entry": fits(f, V1_ENTRY, entry_type and entry_type == "ema15"), "fits_v2_entry": fits(f, V2_ENTRY, entry_type and entry_type in V2_TYPES), "fits_v3_entry": fits(f, V3_ENTRY, True),
            "kata": kata, **{k: v4.get(k) for k in V4_KEYS}, **{k: after.get(k) for k in AFTER_KEYS}, "fits_v4_entry": fits_v4(f, kata),
            **{k: (kata5 if k == "kata5" else v4.get(k)) for k in V5_KEYS}, "fits_v5_entry": fits_v5(f, kata5),
            "filled": list(filled), "used_for_rule": bool(used_for_rule), "note": note}


def auto_fill(args, t_open, flags):
    """注文の行（args）の空いている項目を trade_fill.py と trade_v4.py で埋める → (埋めた項目の並び, 決まらず空にする項目, 読む文, 人に聞くこと＝v4 の2つだけ)"""
    import trade_fill as F
    import trade_v4 as V
    pair = args.pair.upper()
    if pair not in F.PAIRS + V.DOLLAR:
        return [], set(), "（自動で埋めるのはドル円・ユーロ円・ポンド円〔とユーロドル・ポンドドルの向き〕の取引だけ＝埋めずに足す）", []
    unknown = parse_unknown(args.unknown)
    given = {k for k in ("entry_type", "break_line", "extreme", "far_min", "pairs_hit", "pairs_lm", "kata") if getattr(args, k) is not None}
    given |= {k for k in ("strongest", "tokyo_break") if flags.get(k) is not None}
    b5, b1 = F.load(t_open)
    val, text, blank, done = {}, [], set(), []
    if pair in F.PAIRS:
        r = F.analyze(b5, b1, pair, args.side, t_open, args.entry, args.break_line, args.extreme)
        rows = F.blanks(r, given)
        blank = {k for ks, _ in rows for k in ks}
        text += [F.report(r)] + F.blank_text(rows)
        if r["line"] is not None:
            val = {"entry_type": r["type"], "break_line": round(r["line"], 3), "extreme": round(r["extreme"], 3), "far_min": r["far_min"],
                   "pairs_hit": r["pairs_hit"], "pairs_lm": r["pairs_lm"]}
            args.strong_flow, args.strong_far = r["strong_flow"], None if "strong_far" in blank else r["strong_far"]
    v = V.analyze(b5, b1, pair, args.side, t_open)
    args.v4 = V.record(v)
    if "kata" in given:                       # オーナーが言った型は v5 の型にも使う
        args.v4["kata5"] = args.kata
    ask = V.questions(v, given, unknown)      # 「一番強い」は v4 の答え（ユーロポンドの1時間の動き）で聞く。始まりの30分後からは v5 の答え（始まりからの動き）
    text.append(V.report(v))
    val["kata"] = v["kata"]
    for k, x in val.items():
        if k not in given | blank and x is not None:
            setattr(args, k, x)
            done.append(k)
    if v["named"] and V.pick_now(v) and flags.get("strongest") is None:      # 道具の答えと違うときは × と決めない（オーナーはチャートの形で見る）
        flags["strongest"] = True
        done.append("strongest")
    if pair in F.PAIRS and flags.get("tokyo_break") is None and r["signal"] and "tokyo_break" not in blank:      # 見つからないときは × と決めない（線の見方が違うだけかもしれない）
        flags["tokyo_break"] = True
        done.append("tokyo_break")
    return done, blank, "\n".join(text), ask


def after_entry(args, t_open, t_close):
    """--auto で足すとき、入ってから出るまでの足から v4 の出口・伸ばした分を数える（書くだけ）。取れなければ空"""
    import trade_fill as F
    import trade_v4 as V
    pair = args.pair.upper()
    if pair not in F.PAIRS + V.DOLLAR:
        return None
    v = args.v4 or {}
    use = args.kata == "push" and v.get("watch_line") is not None
    p, q, step = V.load_after(pair, v["watch"] if use else None, t_open, t_close)
    return V.after(p, q, args.side, args.entry, args.spread, v["watch_line"] if use else None, v["watch_extreme"] if use else None, t_open, t_close,
                   args.pip or pip_size(pair), pnl_of(pair, args.side, args.entry, args.exit, args.pip), step)


def parse_unknown(text):
    out = {x.strip() for x in (text or "").split(",") if x.strip()}
    bad = out - {"strong", "kata"}
    if bad:
        raise SystemExit(f"🚨 --unknown に使えるのは strong・kata（{', '.join(sorted(bad))} は要らない＝線・30pips・種類・数は、決まらなければ聞かずに空）")
    return out


def add(st, trade):
    if trade["date"] < START:
        raise SystemExit(f"🚨 {trade['date']} は {START} より前＝この記録には入れない（過去の取引は別に扱う）")
    if any(t["id"] == trade["id"] for t in st["trades"]):
        raise SystemExit(f"🚨 注文番号 {trade['id']} はもう記録してある（二重に足さない）")
    st["trades"].append(trade)
    st["trades"].sort(key=lambda t: (t["date"], t["entry_time"]))
    return st


def counted(st):
    """R を出せる取引（損切りの逆指値があったもの）を時刻順に"""
    return [t for t in st["trades"] if t.get("r_net") is not None]


def boot_ci(trades, n_boot=N_BOOT, seed=SEED):
    """日ごとのまとまりで引き直した平均の95%の幅。純関数"""
    days = {}
    for t in trades:
        days.setdefault(t["date"], []).append(t["r_net"])
    blocks = list(days.values())
    rng = random.Random(seed)
    means = []
    for _ in range(n_boot):
        pick = [x for _ in blocks for x in rng.choice(blocks)]
        means.append(sum(pick) / len(pick))
    means.sort()
    return means[int(0.025 * n_boot)], means[int(0.975 * n_boot) - 1]


def verdict_of(lo, hi):
    if lo > 0:
        return "機能している（サイズは据え置き。上げるのは次の判定でも下限>0のとき）"
    if hi < 0:
        return "反証（手を止めて設計に戻る＝土俵・時間帯・費用のどれが効いているかを潰す）"
    return "まだ分からない（サイズを上げない・続けてよい）"


def reading_table(trades):
    """項目ごとの ○ と × ・入口の種類ごとの R の平均と件数（読むだけ・決まりの紙を作るのに使った取引は外す）"""
    trades = [t for t in trades if not t.get("used_for_rule")]
    rows = {}
    for k in V1_ENTRY + ("htf_aligned", "tp_before_high", "sl_at_line", "in_window2", "far30", "pairs2", "pairs_lm2", "pick_flow", "pick_far") + V4_FLAGS + (
            "in_window5", "ldn_flat", "usd_dir5", "pick_eg5"):
        for v in (True, False):
            xs = [t["r_net"] for t in trades if t["flags"].get(k) is v]
            rows[f"{k}={'o' if v else 'x'}"] = {"n": len(xs), "mean": round(sum(xs) / len(xs), 3) if xs else None}
    for k in (f"fits_{v}_entry" for v in PAPERS):
        for v in (True, False):
            xs = [t["r_net"] for t in trades if t.get(k) is v]
            rows[f"{k}={'o' if v else 'x'}"] = {"n": len(xs), "mean": round(sum(xs) / len(xs), 3) if xs else None}
    for k in ENTRY_TYPES:
        xs = [t["r_net"] for t in trades if t.get("entry_type") == k]
        rows[f"entry_type={k}"] = {"n": len(xs), "mean": round(sum(xs) / len(xs), 3) if xs else None}
    for key, words in (("kata", KATA), ("v4_exit", ("tp", "sl", "none"))):      # v4：型ごと・v4 の出口が先に来ていたか
        for k in words:
            xs = [t["r_net"] for t in trades if t.get(key) == k]
            rows[f"{key}={k}"] = {"n": len(xs), "mean": round(sum(xs) / len(xs), 3) if xs else None}
    xs = [t["run_pips"] for t in trades if t.get("run_pips") is not None]       # v4 の利確のあと、そこから伸ばした分（pips）
    rows["run_pips"] = {"n": len(xs), "mean": round(sum(xs) / len(xs), 1) if xs else None}
    return rows


def run_checkpoints(st, n_boot=N_BOOT, seed=SEED):
    """30件の倍数に届いた判定を、まだ出していない分だけ1回ずつ出して固定する"""
    rs = counted(st)
    done = {c["n"] for c in st["checkpoints"]}
    for n in range(CHECK_EVERY, len(rs) + 1, CHECK_EVERY):
        if n in done:
            continue
        part = rs[:n]
        lo, hi = boot_ci(part, n_boot, seed)
        mean = sum(t["r_net"] for t in part) / n
        wins = sum(1 for t in part if t["r_net"] > 0)
        st["checkpoints"].append({
            "n": n, "through": part[-1]["date"], "days": len({t["date"] for t in part}),
            "mean_r": round(mean, 3), "lo": round(lo, 3), "hi": round(hi, 3), "win_rate": round(wins / n, 3),
            "verdict": verdict_of(lo, hi), "reading": reading_table(part)})
    return st


def status_text(st):
    rs = counted(st)
    no_sl = [t for t in st["trades"] if t.get("r_net") is None]
    nxt = (len(rs) // CHECK_EVERY + 1) * CHECK_EVERY
    L = [f"OJ 裁量の取引の記録（{START} から）：R を出せる取引 {len(rs)}件・{len({t['date'] for t in rs})}日"
         f"（次の判定は {nxt}件目・あと {nxt - len(rs)}件。途中の平均は出さない）"]
    if no_sl:
        L.append(f"⚠️ 損切りの逆指値が無く R を出せない取引 {len(no_sl)}件（数えない）：" +
                 "・".join(f"{t['date']} {t['pair']}" for t in no_sl))
    for v in PAPERS:
        fit = sum(1 for t in rs if t.get(f"fits_{v}_entry") is True)
        L.append(f"決まりの紙 {v} の入口に全部当てはまった取引 {fit}件（成績は判定の日にだけ出す）")
    held = [t for t in st["trades"] if (t.get("flags") or {}).get("ldn_flat") is False]
    if held:
        L.append(f"⚠️ ロンドンの始まりの5分前をまたいで持っていた取引 {len(held)}件（v5 の決まりに反する）：" +
                 "・".join(f"{t['date']} {t['pair']}" for t in held))
    kinds = [(k, sum(1 for t in rs if t.get("entry_type") == k)) for k in ENTRY_TYPES]
    kinds4 = [(k, sum(1 for t in rs if t.get("kata") == k)) for k in KATA]
    if any(n for _, n in kinds4):
        L.append("v4 の型：" + "・".join(f"{KATA_JP[k]} {n}件" for k, n in kinds4 if n))
    none = sum(1 for t in rs if t.get("entry_type") is None)
    L.append("入口の種類：" + "・".join([f"{TYPE_JP[k]} {n}件" for k, n in kinds if n] + ([f"決まらない {none}件"] if none else [])) if rs else "入口の種類：まだ無い")
    for c in st["checkpoints"]:
        L.append(f"判定（{c['n']}件・{c['through']} まで・{c['days']}日）：平均 {c['mean_r']:+.3f}R"
                 f"（95%の幅 {c['lo']:+.3f}〜{c['hi']:+.3f}）・勝率 {c['win_rate'] * 100:.0f}% → {c['verdict']}")
    return "\n".join(L)


def fill_text(args, t_open, flags):
    """埋めて読む文を出す → (終わりの番号＝0：決まった・2：人に聞くことがある／取れない, 埋めた項目, 空にする項目)"""
    import trade_fill as F
    try:
        done, blank, text, ask = auto_fill(args, t_open, flags)
    except F.FillError as e:
        print(f"🛑 {e}")
        return 2, [], set()
    print(text)
    for q in ask:
        print(f"❓ {q}")
    return (2 if ask else 0), done, blank


def main(argv):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add")
    a.add_argument("--id", required=True)
    a.add_argument("--pair", required=True)
    a.add_argument("--side", required=True)
    a.add_argument("--open", required=True)
    a.add_argument("--close", required=True)
    for k in ("entry", "exit"):
        a.add_argument(f"--{k}", type=float, required=True)
    for k in ("sl", "tp", "spread", "pip"):
        a.add_argument(f"--{k}", type=float, default=None)
    a.add_argument("--server-time", action="store_true", help="時刻は MT4 の画面の時刻（サーバー時刻）")
    a.add_argument("--entry-type", default=None, choices=ENTRY_TYPES, help="付けなければ other（--auto なら、当たっていた線が1つのときだけ埋める・決まらなければ空）")
    a.add_argument("--push", default=None, choices=PUSHES, help="何押しで入ったか")
    a.add_argument("--sl-line", type=float, default=None, help="決まりの損切りの線（ブレイクラインか1押しの安値）")
    a.add_argument("--break-line", type=float, default=None, help="型1：割った線（売り＝東京時間の最安値・買い＝最高値）")
    a.add_argument("--extreme", type=float, default=None, help="型1：線からいちばん遠くまで行った値（売り＝新安値・買い＝最高値）")
    a.add_argument("--far-min", type=float, default=None, help="決まりの紙 v2：抜けてから線の30pips 先に届くまでの分（抜けた足なら 0・届いていなければ付けない）")
    a.add_argument("--pairs-hit", type=int, default=None, help="決まりの紙 v2：線まで 3pips 以内に来ていたペアの数（0〜3・入ったペアも入れる）")
    a.add_argument("--pairs-lm", type=int, default=None, help="決まりの紙 v3：割った線か MA まで 3pips 以内に来ていたペアの数（0〜3・50%% は入れない・入ったペアも入れる）")
    a.add_argument("--kata", default=None, choices=KATA, help="決まりの紙 v4 の型：push＝①押し目・fade＝②抜けの失敗の逆張り・range＝④ドル円レンジの押し目・other＝ほか")
    a.add_argument("--auto", action="store_true", help="空いている項目を Yahoo の足から埋める（v1〜v3 の項目が決まらなければ空・v4 の型と強いほうは聞く）")
    a.add_argument("--unknown", default="", help="--auto で決められず、聞いても分からなかったもの（strong,kata）")
    a.add_argument("--flags", default="")
    a.add_argument("--note", default="")
    a.add_argument("--used-for-rule", action="store_true", help="決まりの紙を作るのに使った取引（読むための表から外す）")
    b = sub.add_parser("fill", help="記録に要る数字を Yahoo の足から計算して見るだけ（書かない）")
    for k in ("pair", "side", "open"):
        b.add_argument(f"--{k}", required=True)
    for k in ("entry", "break-line", "extreme"):
        b.add_argument(f"--{k}", type=float, default=None)
    b.add_argument("--server-time", action="store_true")
    sub.add_parser("status")
    args = ap.parse_args(argv)
    args.strong_flow = args.strong_far = args.v4 = None
    if args.cmd == "fill":
        t_open = parse_time(args.open)
        t_open = server_to_jst(t_open) if args.server_time else t_open
        args.entry_type = args.far_min = args.pairs_hit = args.pairs_lm = args.kata = None
        args.unknown = ""
        return fill_text(args, t_open, {})[0]
    st = load()
    if args.cmd == "add":
        if any(t["id"] == str(args.id) for t in st["trades"]):
            raise SystemExit(f"🚨 注文番号 {args.id} はもう記録してある（二重に足さない）")
        t_open, t_close = parse_time(args.open), parse_time(args.close)
        if args.server_time:
            t_open, t_close = server_to_jst(t_open), server_to_jst(t_close)
        flags, done, blank, aft = parse_flags(args.flags), [], set(), None
        if args.auto:
            code, done, blank = fill_text(args, t_open, flags)
            if code:
                print("🛑 まだ記録していない＝上のことを決めてから、もう一度 add する")
                return code
            aft = after_entry(args, t_open, t_close)
        tr = make_trade(args.id, args.pair, args.side, t_open, args.entry, args.sl, args.tp, t_close, args.exit,
                        args.spread, args.pip, args.entry_type or (None if "entry_type" in blank else "other"), flags, args.note,
                        args.used_for_rule, args.push, args.sl_line, args.break_line, args.extreme, args.far_min, args.pairs_hit,
                        done, "far_min" in blank, args.pairs_lm, args.strong_flow, args.strong_far, args.kata, args.v4, aft)
        add(st, tr)
        r = f"{tr['r_net']:+.2f}R" if tr["r_net"] is not None else "R なし（逆指値なし）"
        print(f"足した：{tr['date']} {tr['entry_time']} {tr['pair']} {tr['side']}・{tr['pnl_pips']:+.1f}pips・{r}")
    had = len(st["checkpoints"])
    run_checkpoints(st)
    if args.cmd == "add" or len(st["checkpoints"]) != had:
        save(st)
    print(status_text(st))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
