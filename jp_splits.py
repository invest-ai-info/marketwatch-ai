# -*- coding: utf-8 -*-
"""日本株の日足・月足（Yahoo chart API）の株式分割の補正。2026-11-19 新設。

起きたこと（2026-11-18 の引け）: キーエンス（6861）は 1→5 の株式分割。Yahoo の日足は**最後の 11/18 の1本だけ
分割後の値**（終値 14,722・出来高 305万株）で、11/17 より前は分割前のまま（終値 72,510・出来高 61万株）だった。
→ jp-rankings.json の値下がり1位に −79.7%（本当は 72,510→73,610 の +1.5%）、人気急上昇に出来高 3.9倍
  （本当は売買代金 449億円 vs 前日 446億円＝急増していない）が出た。

Yahoo は `&events=split` を付けると分割の日付と倍率（chart.result[0].events.splits の numerator/denominator）を返す。
ただし**足の値が分割の分だけ直してあるかは銘柄・時期でまちまち**（全部直してある＝ふつう／一部の足だけ／まだ何も）。
しかも分割の日付と値が変わった足が1営業日ずれる（キーエンスは日付 11/19・値が変わったのは 11/18 の足）。
そこで:
  ① 分割1件ごとに、その日付の SPLIT_BEFORE 暦日前〜SPLIT_AFTER 暦日後にかかる足の切れ目だけを見る
  ② 切れ目の終値の比 q（あと÷まえ）が、「分割で落ちた」（q×倍率 が1に近い）ほうが「分割ではない」（q が1に近い）より近く、
     しかも直したあとの値動き q×倍率 が 1/MAX_MOVE〜MAX_MOVE に収まるときだけ「直していない切れ目」とする（いちばん近い1つ）
  ③ ただし切れ目の前の足（直前の10本）の終値の過半数が呼値（0.1円の倍数）に乗っていなければ、Yahoo がもう倍率で割って
     直してある＝切れ目に見えたのは本物の値動き＝何もしない（already_adjusted・直すのを止めるだけで、直す理由にはしない）
  ④ その切れ目より前の足を分割後の単位に直す＝値段 ÷倍率・出来高 ×倍率（売買代金＝終値×出来高 は変わらない）
  切れ目が見つからない＝もう直してある（ふつうの形）＝何もしない。
  🔍 2026-11-19 の全上場の点検で③を足した：コタ（4923）の 1→1.05 の分割（2026-03）は Yahoo が直し済み（前の足が 1357.14 など
     ＝1425÷1.05）なのに、03-31 の本物の −7% が 1.05 の切れ目に見えた。
  ⑤ 切れ目の前後 REVERT_DAYS 暦日のうちに、逆向きに同じ倍率の切れ目があれば、分割ではなく数日だけの値の誤り＝何もしない
     （2026-11-19 同日夕：日経225連動型上場投信 1321.T に Yahoo の「100:1 の分割」があるが、値は 2026-10-05・06 の2日だけ
      1/100 で 10-07 に戻っていた＝それより前を 1/100 に直すと、かえって全部が狂う。1990年からの日足の点検では
      三菱ケミカル 2005-09-30・ローツェ 2000-08-25 の「1日だけ半分／2倍」が、その次の足で分割の切れ目に見えた）

⚠️ 倍率の小さい分割（1→1.1 など）は、直してある足のふつうの下げと見分けにくい。取り違えても誤差は倍率の分まで
   （大きい分割＝2倍以上は、直したあとの値動きと直す前の値動きの差が大きく取り違えない）。
⚠️ 月足では分割のあった月の足が分割の前と後の値を混ぜている（分割なら高値・併合なら安値が分割前の単位のまま）。
   その値が終値の1.5倍を超えて離れていれば倍率で割る（adjust_hlcv）。同じ月の分割後の値は日足（約2年）が補う。
⚠️ 標準ライブラリだけ。読むところ＝build_jp_rankings.py・build_jp_highs.py・highs_ledger.py（サイト・朝のメール）／
   generate_market_news.py（hot-assets の日本株 主要銘柄）／yori_lab.fetch_chart（研究ラボと前向きの記録の共通の取り方・
   jp_bars の置き場）／tdnet_reaction.py（開示のあとの値動き J51）。
"""
import datetime as dt
import math

JST = dt.timezone(dt.timedelta(hours=9))
SPLIT_BEFORE = 8     # 分割の日付の何暦日前の足から見るか（権利落ちは日付の1〜2営業日前・連休をまたいでも届く幅）
SPLIT_AFTER = 3      # 分割の日付の何暦日後の足まで見るか
MAX_MOVE = 1.5       # 直したあとの1本の値動きの上限（build_jp_highs.MAX_JUMP と同じ＝値幅制限の外には出ない）
TICK_LOOK = 10       # 「もう直してあるか」を見る、切れ目の前の足の本数
REVERT_DAYS = 10     # 切れ目のあと、この暦日のうちに逆向きに戻れば値の誤り（分割ではない）


def on_tick(x):
    """値段が呼値（0.1円の倍数）に乗っているか。Yahoo の生の値段は乗る・倍率で割った値段（1425÷1.05＝1357.14…）は乗らないことが多い。
    Yahoo の値は float32＝大きい値段では誤差を許す。純関数。"""
    return abs(x * 10 - round(x * 10)) <= max(0.02, abs(x) * 10 * 3e-7)


def already_adjusted(closes):
    """切れ目の前の足の終値の過半数が呼値に乗っていない＝Yahoo がもう分割の倍率で割って直してある。純関数。

    乗っている（整数など）ときは決められない（分割前の生の値段か、割り切れた直し済みの値段か）＝False。
    """
    xs = [c for c in closes if c and c > 0]
    return bool(xs) and sum(1 for c in xs if not on_tick(c)) * 2 > len(xs)


def parse_splits(result):
    """Yahoo chart の result → [(分割の日付 JST の ISO, 倍率)]（倍率＝numerator/denominator・1株が何株になるか）。純関数。

    1倍・壊れた値は落とす。株式併合（例: 10株→1株）は倍率が1未満（0.1）。
    """
    ev = ((result or {}).get("events") or {}).get("splits") or {}
    out = []
    for s in ev.values():
        try:
            r = float(s["numerator"]) / float(s["denominator"])
            d = dt.datetime.fromtimestamp(int(s["date"]), JST).date().isoformat()
        except (KeyError, TypeError, ValueError, ZeroDivisionError, OverflowError, OSError):
            continue
        if r > 0 and abs(math.log(r)) > 1e-6:
            out.append((d, r))
    return sorted(out)


def _window(d):
    d0 = dt.date.fromisoformat(d)
    return (d0 - dt.timedelta(days=SPLIT_BEFORE)).isoformat(), (d0 + dt.timedelta(days=SPLIT_AFTER)).isoformat()


def near(date, splits):
    """date（ISO）の足が、どれかの分割の日付の前後（find_breaks が見る幅）にかかるか。純関数。"""
    for d, _ in splits or ():
        lo, hi = _window(d)
        if lo <= date <= hi:
            return True
    return False


def _q(closes, k):
    a, b = closes[k - 1], closes[k]
    if not a or not b or a <= 0 or b <= 0:
        return None
    return b / a


def _reverts(dates, closes, k, r):
    """切れ目 k の前後 REVERT_DAYS 暦日のうちに、逆向きに同じ倍率の切れ目があるか（数日だけの値の誤り）。純関数。

    後ろ＝1321.T（2026-10-05・06 だけ 1/100 → 10-07 に戻る）。前＝三菱ケミカル（4188・2005-09-30 だけ 1/2）・
    ローツェ（6323・2000-08-25 だけ 2倍）＝誤りの足の次の足が「分割で落ちた」切れ目に見える。
    """
    try:
        d0 = dt.date.fromisoformat(dates[k])
        lo = (d0 - dt.timedelta(days=REVERT_DAYS)).isoformat()
        hi = (d0 + dt.timedelta(days=REVERT_DAYS)).isoformat()
    except ValueError:
        return False
    for j in range(1, len(closes)):
        if j == k or dates[j] < lo:
            continue
        if dates[j] > hi:
            break
        q = _q(closes, j)
        if q is None:
            continue
        e_back, e_none = abs(math.log(q / r)), abs(math.log(q))
        if e_back < e_none and e_back <= math.log(MAX_MOVE):
            return True
    return False


def find_break_indices(dates, closes, splits):
    """Yahoo がまだ直していない切れ目 → [(足の番号 k, 倍率)]（k より前の足が分割前の単位のまま）。純関数。

    dates は足の日付（ISO・古い順・日中足なら同じ日付が続く）、closes は同じ長さの終値。
    """
    used, out = set(), []
    for d, r in splits or ():
        try:
            lo, hi = _window(d)
        except ValueError:
            continue
        best = None
        for k in range(1, len(closes)):
            if k in used:
                continue
            # 足 k が覆う期間 [dates[k], dates[k+1]) が分割の日付の前後にかかるか（月足は1本が1か月を覆う）
            if dates[k] > hi or (k + 1 < len(dates) and dates[k + 1] <= lo):
                continue
            q = _q(closes, k)
            if q is None:
                continue
            e_split, e_none = abs(math.log(q * r)), abs(math.log(q))
            if e_split < e_none and e_split <= math.log(MAX_MOVE) and (best is None or e_split < best[0]):
                best = (e_split, k)
        if (best and not already_adjusted(closes[max(0, best[1] - TICK_LOOK):best[1]])
                and not _reverts(dates, closes, best[1], r)):
            used.add(best[1])
            out.append((best[1], r))
    return sorted(out)


def find_breaks(dates, closes, splits):
    """Yahoo がまだ直していない切れ目 → [(切れ目の日付, 倍率)]。純関数。

    切れ目の日付＝分割後の単位になった最初の足の日付（それより前の足は分割前の単位のまま）。日足・月足用（1日1本）。
    """
    return [(dates[k], r) for k, r in find_break_indices(dates, closes, splits)]


def index_factors(dates, closes, splits):
    """足ごとの値段に掛ける数（出来高はこれで割る）と切れ目［(日付, 倍率)］。日中足でも使える（切れ目は足の番号で持つ）。純関数。"""
    br = find_break_indices(dates, closes, splits)
    f = [1.0] * len(closes)
    for k, r in br:
        for i in range(k):
            f[i] /= r
    return f, [(dates[k], r) for k, r in br]


def factor(date, breaks):
    """その日付の足の値段に掛ける数（出来高はこれで割る）。切れ目より前の足だけ 1/倍率。純関数。"""
    f = 1.0
    for bd, r in breaks or ():
        if date < bd:
            f /= r
    return f


def adjust_hlcv(bars, splits):
    """[(日付, 高値, 安値, 終値, 出来高)]（build_jp_highs.parse_bars の形）→ (直した bars, 切れ目[])。純関数。"""
    breaks = find_breaks([b[0] for b in bars], [b[3] for b in bars], splits)
    if not breaks:
        return bars, []
    at = dict(breaks)
    out = []
    for d, h, lo, c, v in bars:
        f = factor(d, breaks)
        h, lo, c, v = h * f, lo * f, c * f, v / f
        r = at.get(d)
        if r:
            # 切れ目の足。月足では分割の前と後の値が混ざる＝分割で値が下がる向き（倍率>1）は高値が、上がる向き（併合）は安値が
            # 分割前の単位のまま残る（キーエンスの 2026年11月の月足＝高値 77,630・終値 14,722）。日足は1本が全部分割後＝ここに来ない
            if r > 1 and h > c * MAX_MOVE:
                h = max(h / r, c)
            if r < 1 and lo < c / MAX_MOVE:
                lo = min(lo / r, c)
        out.append((d, h, lo, c, v))
    return out, breaks


def breaks_of(result):
    """Yahoo chart の result から、まだ直していない切れ目を探す（終値で見る）。純関数。"""
    splits = parse_splits(result)
    if not splits:
        return []
    q = result["indicators"]["quote"][0]
    pairs = [(dt.datetime.fromtimestamp(t, JST).date().isoformat(), float(c))
             for t, c in zip(result.get("timestamp") or [], q.get("close") or []) if c is not None]
    return find_breaks([p[0] for p in pairs], [p[1] for p in pairs], splits)


def adjust_ohlcv(rows, splits):
    """[(JST の時刻, 始, 高, 安, 終, 出来高)]（yori_lab.fetch_chart・tdnet_reaction.parse_chart の形・日足でも日中足でも）
    → (直した rows, 切れ目[])。始値が None の足は None のまま。純関数。"""
    if not splits or not rows:
        return rows, []
    f, breaks = index_factors([r[0].date().isoformat() for r in rows], [r[4] for r in rows], splits)
    if not breaks:
        return rows, []
    return [(t, None if o is None else o * k, h * k, lo * k, c * k, v / k)
            for (t, o, h, lo, c, v), k in zip(rows, f)], breaks


def adjust_close_volume(dates, closes, vols, splits):
    """終値と出来高の列（日足）→ (直した終値, 直した出来高〔None は None のまま〕, 切れ目[])。純関数。"""
    f, breaks = index_factors(dates, closes, splits)
    if not breaks:
        return list(closes), list(vols), []
    return ([c * k for c, k in zip(closes, f)],
            [None if v is None else v / k for v, k in zip(vols, f)], breaks)
