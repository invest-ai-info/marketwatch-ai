# -*- coding: utf-8 -*-
"""朝のメール用「強すぎる株＝買わない側」の一覧（過去12か月で一番上げた10銘柄・月1回）。2026-10-08 夜 オーナー
「2を登録して進めてください…注意するべき銘柄、買ってはいけない銘柄、地雷銘柄…平日の朝一メールしてください」。

研究 J42（日本株の数か月単位のモメンタム）の読むための表で、12−1 の上位10銘柄は翌月に全銘柄の平均より弱かった
（2010年〜 −1.45％/月・95％の幅 −2.79〜−0.11・結果を見たあとに気づいた数字）。前向きの記録 J42F（momentum_forward.py）で確かめている。

流れ: build_jp_highs.py（jp-highs.yml・夕方）が取った2年の日足に相乗りして compute() → jp-highs.json の "momentum"
      → 朝の指標メール（send_indicator_digest.py・平日 06:13〜06:20 JST）が section() で節を足す。
      上場からの長さ（37か月）は、上位の候補だけ月足の記録の始まりで確かめる（1晩に多くて100回ほど）。

⚠️ 決まりは J42／J42F と同じ（売買代金1億円以上・決める月の最後の取引日に足・12−1＝m−12 の月末 → m−1 の月末・
   月末の値段＝その月の最後の5取引日のうちの最後の終値・データの誤りの日は値動き0でつなぐ・上位10銘柄）。
   ただし ①始値が無い（誤りの判定は高値・安値・終値）②36か月の月の値の欠けは確かめず、記録の始まりだけ見る
   ③買う日に寄るかは朝にはわからない＝前向きの記録の10銘柄とまれに入れ替わりがありうる。数字を変えるなら研究の登録から。
⚠️ 銘柄名を出すのは**自分用のメールだけ**。サイトには出さない。決まりは「新しく買わない」だけ（空売りの合図ではない）。
⚠️ 標準ライブラリだけ（朝のメールのワークフローは追加のライブラリを入れない）。
"""
import datetime as dt

TV_MIN = 1.0           # 決める月の1日平均の売買代金（億円）
MIN_BARS = 10
LOOK = 12              # 12−1
AGE_MONTHS = 36        # 記録の始まりが決める月の36か月前以前（＝37か月分の月末）
END_WINDOW = 5
MIN_CAL = 50           # 取引日＝50銘柄以上に足がある日
MAX_GAP_DAYS = 7
MAX_JUMP = 1.5         # build_jp_highs.MAX_JUMP と同じ
TOP = 10
MAX_CHECK = 60         # 上場からの長さを確かめる候補の数の上限（1つの一覧あたり）
# 研究の数字（メールに書く根拠・J42 の momentum-lab.md と J42F の事前登録から写した）
EVIDENCE = ("根拠：研究 J42 の表で、この10銘柄は翌月に全銘柄の平均より 2010年〜 −1.45％/月（95％の幅 −2.79〜−0.11）・"
            "2003年〜 −1.04％/月（−2.07〜+0.03）弱かった。結果を見たあとに気づいた数字＝前向きの記録（J42F・2026年10月〜24か月）で確かめ中")


def _ym(d):
    return d[:7]


def _mid(ym):
    y, m = map(int, ym.split("-"))
    return y * 12 + m - 1


def _prev_ym(ym):
    i = _mid(ym) - 1
    return "%04d-%02d" % (i // 12, i % 12 + 1)


def month_table(daily):
    """{コード: bars} → {月: (最初の取引日, 最後の取引日, 最後の5取引日の始まり)}（取引日＝MIN_CAL 銘柄以上に足がある日）"""
    cnt = {}
    for bars in daily.values():
        for b in bars:
            if b[4] and b[4] > 0:                       # 出来高0の足は数えない（momentum_lab.from_rows と同じ）
                cnt[b[0]] = cnt.get(b[0], 0) + 1
    days = sorted(d for d, n in cnt.items() if n >= MIN_CAL)
    by = {}
    for d in days:
        by.setdefault(_ym(d), []).append(d)
    return {ym: (ds[0], ds[-1], ds[max(len(ds) - END_WINDOW, 0)]) for ym, ds in by.items()}


def stock_months(bars, table):
    """1銘柄の bars［(日付, 高値, 安値, 終値, 出来高)］→ {月: (月末の指数 or None, 最後の取引日に足があるか, 売買代金の平均, 足の数)}。
    誤りの日・7暦日を超える間の日は値動き0でつなぐ（momentum_lab.clean_index と同じ物差し・始値の条件だけ無い）"""
    out, P, prev, prev_d = {}, 1.0, None, None
    acc = {}
    for d, h, lo, c, v in bars:
        if not v or v <= 0:                             # 出来高0の足は無いものとして扱う（momentum_lab.from_rows と同じ）
            continue
        if prev is not None:
            gap = (dt.date.fromisoformat(d) - dt.date.fromisoformat(prev_d)).days
            good = (c > 0 and lo > 0 and h >= c * 0.999 and lo <= c * 1.001 and prev > 0
                    and h <= prev * MAX_JUMP and lo >= prev / MAX_JUMP and gap <= MAX_GAP_DAYS)
            if good:
                P *= c / prev
        prev, prev_d = c, d
        a = acc.setdefault(_ym(d), [None, None, 0.0, 0])
        a[0], a[1] = d, P
        a[2] += c * (v or 0) / 1e8
        a[3] += 1
    for ym, (last_d, p, tv, n) in acc.items():
        t = table.get(ym)
        if not t:
            continue
        out[ym] = (p if last_d >= t[2] else None, last_d == t[1], tv / n, n)
    return out


def signal(sm, ym):
    """決める月 ym の 12−1（m−12 の月末 → m−1 の月末）と、m−12〜m の13か月の月末がそろうか。決める月の条件も見る"""
    cur = sm.get(ym)
    if not cur or not cur[1] or cur[3] < MIN_BARS or cur[2] < TV_MIN:
        return None
    i = _mid(ym)
    ends = []
    for k in range(i - LOOK, i + 1):
        x = sm.get("%04d-%02d" % (k // 12, k % 12 + 1))
        if not x or x[0] is None:
            return None
        ends.append(x[0])
    return ends[LOOK - 1] / ends[0] - 1


def first_month(monthly):
    """月足［(日付, …)］→ 記録の始まりの月（無ければ None）"""
    return _ym(monthly[0][0]) if monthly else None


def build_list(sms, stocks, ym, table, age_of):
    """決める月 ym の上位10銘柄（上場から37か月以上を候補の上から確かめる）"""
    if ym not in table:
        return None
    sig = {c: s for c, s in ((c, signal(sm, ym)) for c, sm in sms.items()) if s is not None}
    order = sorted(sig, key=lambda c: (-sig[c], c))
    rows, checked, unknown = [], 0, 0
    for c in order[:MAX_CHECK]:
        checked += 1
        fm = age_of(c)
        if fm is None:
            unknown += 1
            continue
        if _mid(fm) > _mid(ym) - AGE_MONTHS:
            continue
        rows.append({"code": c, "name": (stocks.get(c) or {}).get("name", ""), "ret12": round(sig[c], 4),
                     "tv": round(sms[c][ym][2], 2)})
        if len(rows) == TOP:
            break
    return {"ym": ym, "date": table[ym][1], "universe": len(sig), "checked": checked, "age_unknown": unknown, "rows": rows}


def compute(daily, stocks, asof, fetch_monthly):
    """daily＝{コード: bars}（build_jp_highs の2年の日足）→ jp-highs.json の "momentum"。
    asof の月（asof を最後の取引日とみなす＝月の最後の取引日の夕方なら翌月に使う一覧）と、その前の月の2つを作る"""
    table = month_table(daily)
    sms = {c: stock_months(b, table) for c, b in daily.items()}
    cache = {}

    def age_of(c):
        if c not in cache:
            try:
                cache[c] = first_month(fetch_monthly(c))
            except Exception:  # noqa: BLE001
                cache[c] = None
        return cache[c]

    cur = _ym(asof)
    return {"asof": asof, "rule": "J42F", "lists": {"asof": build_list(sms, stocks, cur, table, age_of),
                                                    "month_end": build_list(sms, stocks, _prev_ym(cur), table, age_of)}}


def pick(mom, today):
    """今朝使う一覧＝決める月が「今日の前の月」のもの（月の最初の取引日の朝は asof の一覧・それ以外は month_end）"""
    if not mom:
        return None
    want = _prev_ym(today.isoformat()[:7])
    for key in ("asof", "month_end"):
        x = (mom.get("lists") or {}).get(key)
        if x and x.get("ym") == want and x.get("rows"):
            return x
    return None


def _tags(code, markers):
    rows = {r["code"]: r for r in (markers or {}).get("rows") or []}
    r = rows.get(code)
    if not r:
        return ""
    t = (" 〔C 売買代金の急増〕" if r.get("c") else "") + (" 〔B候補 前の日 +5%以上〕" if r.get("b") else "")
    return t


def section(mom, markers, today):
    """朝のメールの節（行のリスト）。平日でなければ空。純関数"""
    if today.weekday() >= 5:
        return []
    head = "【🇯🇵 日本株：強すぎる株＝新しく買わない側（過去12か月で一番上げた10銘柄・月1回入れ替え）】"
    x = pick(mom, today)
    if not x:
        why = (f"夕方の jp-highs の最新は {mom.get('asof')} の分" + (f"・⚠️ {mom['error']}" if mom.get("error") else "")) if mom \
            else "夕方の jp-highs が次に回ったときから作る"
        return [head, f"  ⚠️ {today.month}月に使う一覧がまだ無い（{why}）", ""]
    L = [head, f"  {x['date']} の大引けで決めた一覧（{today.month}月のあいだ使う）・売買代金1億円以上・上場から3年以上の{x['universe']}銘柄から、"
               "直近1か月を除く12か月の上げが大きい順"]
    for i, r in enumerate(x["rows"], 1):
        L.append(f"     {i}. {r['code']} {r['name']}  12か月 {r['ret12'] * 100:+.0f}%・売買代金 {r['tv']:.1f}億円/日{_tags(r['code'], markers)}")
    L += ["     → 新しく買わない側に置く（寄りでも、ほかの時間でも）。持っている株を売れという合図ではない・空売りの合図でもない",
          f"  {EVIDENCE}",
          "  ※ 強い株を買い続ける形（上位10%）そのものは、日本では得が見えなかった（J42 ✕・2003〜2026年）", ""]
    return L
