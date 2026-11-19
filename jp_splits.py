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

  ⑥ 倍率の小さい分割（SMALL_RATIO 未満・1→1.1 など）は、切れ目を **Yahoo の分割の日付の 2取引日前〜その日** に限る
     （2026-11-19 の点検：Yahoo が直し済みの21件で、値が変わった最初の足は日付の −1取引日が13件・0が6件・−2が2件。
      キーエンス・しまむら・メイコーも −1。倍率が小さいと近くの本物の値動き〔コタの −7%〕を切れ目と取り違えやすいため）
  ⑦ **単位のずれ**（分割の情報が無くても）：となりの足との動きが **東証の値幅制限を4倍に広げてもありえない** 大きさで
     （impossible）、比が 10・100・1000 倍（またはその逆数）の ±15% に入る切れ目は、データの誤り。いちばん新しい足の単位に
     そろえる（それより前の足を同じ倍率で直す）。Yahoo の分割の倍率のほうが比に近ければ、その倍率を使う
     （1990年からの点検：ブルドックソース 2005 は 5,950↔661.11＝ちょうど9倍で何度も行き来していた＝10 で直すと11%ずれる。
      値幅制限で絞るのは、¥100 未満の制限が ¥30 の定額＝¥3→¥33 のストップ高は本物でありうるため）。
     数日で戻る誤りは、ずれた時と戻った時の2つの切れ目で打ち消し合って、その間の足だけが直る
     （1306.T〔TOPIX 連動の上場投信〕の 2026-03-30・31 だけ 1/10・1321.T の 2026-10-05・06 だけ 1/100＝出来高は 10倍・100倍。
      PILLAR_PREREG.md の 2026-10-05「データの取得の失敗と、その直し方」①と同じ考え方）。
     いちばん新しい足から REVERT_DAYS 暦日のうちのずれがまだ戻っていない＝単位がどちらか決められない＝unit_pending が True
     （サイトの一覧はその銘柄を出さない）

⚠️ 倍率の小さい分割は、⑥で絞っても日付の前後2取引日の本物の値動きと取り違えることがある。取り違えても誤差は倍率の分まで
   （大きい分割＝2倍以上は、直したあとの値動きと直す前の値動きの差が大きく取り違えない）。
⚠️ 月足では分割のあった月の足が分割の前と後の値を混ぜている（分割なら高値・併合なら安値が分割前の単位のまま）。
   その値が終値の1.5倍を超えて離れていれば倍率で割る（adjust_hlcv）。同じ月の分割後の値は日足（約2年）が補う。
⚠️ 標準ライブラリだけ。読むところ＝build_jp_rankings.py・build_jp_highs.py・highs_ledger.py（サイト・朝のメール）／
   generate_market_news.py（hot-assets の日本株 主要銘柄）／yori_lab.fetch_chart（研究ラボと前向きの記録の共通の取り方・
   jp_bars の置き場）／tdnet_reaction.py（開示のあとの値動き J51）。
"""
import bisect
import datetime as dt
import math

JST = dt.timezone(dt.timedelta(hours=9))
SPLIT_BEFORE = 8     # 分割の日付の何暦日前の足から見るか（権利落ちは日付の1〜2営業日前・連休をまたいでも届く幅）
SPLIT_AFTER = 3      # 分割の日付の何暦日後の足まで見るか
MAX_MOVE = 1.5       # 直したあとの1本の値動きの上限（build_jp_highs.MAX_JUMP と同じ＝値幅制限の外には出ない）
TICK_LOOK = 10       # 「もう直してあるか」を見る、切れ目の前の足の本数
REVERT_DAYS = 10     # 切れ目のあと、この暦日のうちに逆向きに戻れば値の誤り（分割ではない）
SMALL_RATIO = 1.5    # これより倍率の小さい分割（併合なら 1/これ より大きい）は、切れ目を Yahoo の日付の前の取引日に限る
SMALL_DAYS_BEFORE = 2   # 何取引日前まで（0＝分割の日付の足）
UNITS = (10.0, 100.0, 1000.0)   # 単位のずれ
UNIT_TOL = 1.15      # ±15%（PILLAR_PREREG の 2026-10-05 の決まりは 8.7〜11.5倍）
# 東証の値幅制限（基準値段がこの値未満 → 制限値幅〔円〕）。単位のずれを「4倍に広げてもありえない動き」に限るための表
LIMITS = ((100, 30), (200, 50), (500, 80), (700, 100), (1000, 150), (1500, 300), (2000, 400), (3000, 500),
          (5000, 700), (7000, 1000), (10000, 1500), (15000, 3000), (20000, 4000), (30000, 5000), (50000, 7000),
          (70000, 10000), (100000, 15000), (150000, 30000), (200000, 40000), (300000, 50000), (500000, 70000),
          (700000, 100000), (1000000, 150000), (1500000, 300000), (2000000, 400000), (3000000, 500000),
          (5000000, 700000), (7000000, 1000000), (10000000, 1500000))
LIMIT_WIDEN = 4      # 制限値幅の拡大（ストップ高・安が続いたとき）を見込んで4倍まで広げる


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


def _small_days(dates, d):
    """倍率の小さい分割で見る取引日（分割の日付 d の SMALL_DAYS_BEFORE 取引日前〜d の取引日）の集合。純関数。"""
    days = sorted(set(dates))
    i = bisect.bisect_left(days, d)                   # d 以降で最初の取引日（無ければ len）
    return set(days[max(0, i - SMALL_DAYS_BEFORE):i + 1])


def find_break_indices(dates, closes, splits):
    """Yahoo がまだ直していない分割の切れ目 → [(足の番号 k, 倍率)]（k より前の足が分割前の単位のまま）。純関数。

    dates は足の日付（ISO・古い順・日中足なら同じ日付が続く）、closes は同じ長さの終値。
    切れ目はその日の最初の足だけ（分割は取引日の始まりから効く＝日中足でも日の境目）。
    """
    used, out = set(), []
    for d, r in splits or ():
        try:
            lo, hi = _window(d)
        except ValueError:
            continue
        small = abs(math.log(r)) < math.log(SMALL_RATIO)
        only = _small_days(dates, d) if small else None
        best = None
        for k in range(1, len(closes)):
            if k in used or dates[k] == dates[k - 1]:
                continue
            if small:
                if dates[k] not in only:
                    continue
            # 足 k が覆う期間 [dates[k], dates[k+1]) が分割の日付の前後にかかるか（月足は1本が1か月を覆う）
            elif dates[k] > hi or (k + 1 < len(dates) and dates[k + 1] <= lo):
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


def price_limit(p):
    """基準値段 p の制限値幅（円）。表より上は 30%。純関数。"""
    for top, w in LIMITS:
        if p < top:
            return w
    return p * 0.3


def impossible(prev, cur):
    """前の足 prev → cur の動きが、値幅制限を LIMIT_WIDEN 倍に広げても届かない（＝データの誤り）か。純関数。"""
    if not prev or not cur or prev <= 0 or cur <= 0:
        return False
    w = price_limit(prev) * LIMIT_WIDEN
    return cur > prev + w or cur < prev - w


def _unit(prev, cur, ratios=()):
    """ありえない切れ目（impossible）の比が、単位（10・100・1000 倍）か Yahoo の分割の倍率（またはその逆数）に近ければ、
    その前の足に掛ければそろう数（cur が prev の 1/10 なら 1/10）。違えば None。純関数。"""
    if not impossible(prev, cur):
        return None
    q = cur / prev
    best = None
    for G, tol in [(F, UNIT_TOL) for F in UNITS] + [(r if r > 1 else 1 / r, MAX_MOVE) for r in ratios if r and r > 0]:
        if abs(math.log(G)) < 1e-9:
            continue
        for u in (G, 1 / G):
            e = abs(math.log(q / u))
            if e <= math.log(tol) and (best is None or e < best[0]):
                best = (e, u)
    return best[1] if best else None


def all_break_indices(dates, closes, splits):
    """分割の切れ目と単位のずれをまとめて → [(足の番号 k, 割る数)]（k より前の足の値段をその数で割る＝出来高は掛ける）。純関数。

    分割の切れ目を先に直し、そのあとの終値で単位のずれを探す（分割で直したところは、もうずれていない）。
    """
    br = find_break_indices(dates, closes, splits)
    f = [1.0] * len(closes)
    for k, r in br:
        for i in range(k):
            f[i] /= r
    adj = [None if not c else c * x for c, x in zip(closes, f)]
    ratios = [r for _, r in splits or ()]
    out = list(br)
    for k in range(1, len(adj)):
        u = _unit(adj[k - 1], adj[k], ratios)
        if u:
            out.append((k, 1 / u))
    return sorted(out)


def unit_pending(dates, closes, splits=()):
    """いちばん新しい足から REVERT_DAYS 暦日のうちに単位のずれがあり、まだ戻っていない（掛け合わせて1にならない）か。純関数。

    True＝いまの値段の単位がどちらか決められない＝サイトの一覧には出さない。
    """
    if not dates:
        return False
    try:
        since = (dt.date.fromisoformat(dates[-1]) - dt.timedelta(days=REVERT_DAYS)).isoformat()
    except ValueError:
        return False
    br = set(find_break_indices(dates, closes, splits))
    net = 1.0
    for k, d in all_break_indices(dates, closes, splits):
        if (k, d) not in br and dates[k] >= since:
            net *= d
    return abs(math.log(net)) > 1e-6


def find_breaks(dates, closes, splits):
    """Yahoo がまだ直していない分割の切れ目 → [(切れ目の日付, 倍率)]。純関数。

    切れ目の日付＝分割後の単位になった最初の足の日付（それより前の足は分割前の単位のまま）。日足・月足用（1日1本）。
    単位のずれは含まない（all_break_indices）。
    """
    return [(dates[k], r) for k, r in find_break_indices(dates, closes, splits)]


def index_factors(dates, closes, splits):
    """足ごとの値段に掛ける数（出来高はこれで割る）と直したところ［(日付, 割る数)］（分割の切れ目と単位のずれ）。
    日中足でも使える（切れ目は足の番号で持つ）。純関数。"""
    br = all_break_indices(dates, closes, splits)
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
    """[(日付, 高値, 安値, 終値, 出来高)]（build_jp_highs.parse_bars の形）→ (直した bars, 直したところ[])。純関数。"""
    dates = [b[0] for b in bars]
    f, fixes = index_factors(dates, [b[3] for b in bars], splits)
    if not fixes:
        return bars, []
    at = dict(find_breaks(dates, [b[3] for b in bars], splits))     # 分割の切れ目だけ（月足の混ざった足の直しに使う）
    out = []
    for (d, h, lo, c, v), k in zip(bars, f):
        h, lo, c, v = h * k, lo * k, c * k, v / k
        r = at.get(d)
        if r:
            # 切れ目の足。月足では分割の前と後の値が混ざる＝分割で値が下がる向き（倍率>1）は高値が、上がる向き（併合）は安値が
            # 分割前の単位のまま残る（キーエンスの 2026年11月の月足＝高値 77,630・終値 14,722）。日足は1本が全部分割後＝ここに来ない
            if r > 1 and h > c * MAX_MOVE:
                h = max(h / r, c)
            if r < 1 and lo < c / MAX_MOVE:
                lo = min(lo / r, c)
        out.append((d, h, lo, c, v))
    return out, fixes


def _result_closes(result):
    q = result["indicators"]["quote"][0]
    pairs = [(dt.datetime.fromtimestamp(t, JST).date().isoformat(), float(c))
             for t, c in zip(result.get("timestamp") or [], q.get("close") or []) if c is not None]
    return [p[0] for p in pairs], [p[1] for p in pairs]


def breaks_of(result):
    """Yahoo chart の result から、直すところ［(日付, 割る数)］（分割の切れ目と単位のずれ）を探す（終値で見る）。純関数。"""
    dates, closes = _result_closes(result)
    return [(dates[k], r) for k, r in all_break_indices(dates, closes, parse_splits(result))]


def adjust_ohlcv(rows, splits):
    """[(JST の時刻, 始, 高, 安, 終, 出来高)]（yori_lab.fetch_chart・tdnet_reaction.parse_chart の形・日足でも日中足でも）
    → (直した rows, 直したところ[])。始値が None の足は None のまま。純関数。"""
    if not rows:
        return rows, []
    f, fixes = index_factors([r[0].date().isoformat() for r in rows], [r[4] for r in rows], splits)
    if not fixes:
        return rows, []
    return [(t, None if o is None else o * k, h * k, lo * k, c * k, v / k)
            for (t, o, h, lo, c, v), k in zip(rows, f)], fixes


def adjust_close_volume(dates, closes, vols, splits):
    """終値と出来高の列（日足）→ (直した終値, 直した出来高〔None は None のまま〕, 直したところ[])。純関数。"""
    f, fixes = index_factors(dates, closes, splits)
    if not fixes:
        return list(closes), list(vols), []
    return ([c * k for c, k in zip(closes, f)],
            [None if v is None else v / k for v, k in zip(vols, f)], fixes)
