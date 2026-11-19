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

⚠️ 倍率の小さい分割（1→1.1 など）は、直してある足のふつうの下げと見分けにくい。取り違えても誤差は倍率の分まで
   （大きい分割＝2倍以上は、直したあとの値動きと直す前の値動きの差が大きく取り違えない）。
⚠️ 月足では分割のあった月の足が分割の前と後の値を混ぜている（分割なら高値・併合なら安値が分割前の単位のまま）。
   その値が終値の1.5倍を超えて離れていれば倍率で割る（adjust_hlcv）。同じ月の分割後の値は日足（約2年）が補う。
⚠️ 標準ライブラリだけ（build_jp_rankings.py・build_jp_highs.py・highs_ledger.py が読む）。
"""
import datetime as dt
import math

JST = dt.timezone(dt.timedelta(hours=9))
SPLIT_BEFORE = 8     # 分割の日付の何暦日前の足から見るか（権利落ちは日付の1〜2営業日前・連休をまたいでも届く幅）
SPLIT_AFTER = 3      # 分割の日付の何暦日後の足まで見るか
MAX_MOVE = 1.5       # 直したあとの1本の値動きの上限（build_jp_highs.MAX_JUMP と同じ＝値幅制限の外には出ない）
TICK_LOOK = 10       # 「もう直してあるか」を見る、切れ目の前の足の本数


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


def find_breaks(dates, closes, splits):
    """Yahoo がまだ直していない切れ目 → [(切れ目の日付, 倍率)]。純関数。

    切れ目の日付＝分割後の単位になった最初の足の日付（それより前の足は分割前の単位のまま）。
    dates は足の日付（ISO・古い順）、closes は同じ長さの終値。
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
            a, b = closes[k - 1], closes[k]
            if not a or not b or a <= 0 or b <= 0:
                continue
            q = b / a
            e_split, e_none = abs(math.log(q * r)), abs(math.log(q))
            if e_split < e_none and e_split <= math.log(MAX_MOVE) and (best is None or e_split < best[0]):
                best = (e_split, k)
        if best and not already_adjusted(closes[max(0, best[1] - TICK_LOOK):best[1]]):
            used.add(best[1])
            out.append((dates[best[1]], r))
    return out


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
