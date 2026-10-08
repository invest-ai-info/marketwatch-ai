# -*- coding: utf-8 -*-
"""朝の準備用「寄りで買わない」目印の銘柄一覧（前の日の引けでわかるもの）。2026-10-08 オーナー「一、二。に進めてください」。

点検表（MY_TRADING_RULES.md 日本株⑤）の目印のうち、**前の日の引けでわかる2つ**を東証の全上場から毎日拾う:
  C     ＝前の日の売買代金が、その前の20営業日の平均の5倍以上 → 寄りでは買わない
  B候補 ＝前の日に +5% 以上 → 今朝その銘柄だけ +1% 以上高く寄ったら B（寄りでは買わない・いちばん強い目印）
  （A＝その銘柄だけ +1% 以上高く寄る、は寄りの気配でしかわからない＝メールでは決まりを1行添えるだけ）

流れ: build_jp_highs.py（jp-highs.yml・夕方）が取った日足に相乗りして compute() → jp-highs.json の "markers"
      → 朝の指標メール（send_indicator_digest.py・平日 06:13〜06:20 JST）が section() で節を足す。
      Yahoo に余分に取りに行かない。

⚠️ 目印の数字は研究と同じ（売買代金＝終値×出来高・倍率の分母＝その前の20本の日足の平均＝landmine_lab.prev_more と同じ式・
   前の日の上げ＝前の日の終値÷その前の終値−1）。ここで数字を変えない（変えるなら研究の登録から）。
⚠️ 銘柄名を出すのは**自分用のメールだけ**。サイトには出さない（「この銘柄を寄りで買わない」は個別銘柄の売買の推奨に近づくため）。
⚠️ 決まりは「寄りで買わない」だけ（空売りの合図ではない）。
🆕 2026-10-08 夕方（オーナー「両方登録して進めてください」・研究 J36 を受けて）：各銘柄に〔貸借〕の印＝制度信用で空売りできる銘柄
   （日本取引所グループの一覧を jp_taishaku.py で読む・build_jp_highs が夕方に取りに行く）。印だけ＝空売りの決まりではない。
"""
import datetime as dt

TV_DAYS = 20
TV_HIGH = 5.0           # 目印C（MY_TRADING_RULES 日本株⑤・研究 J26・J26F と同じ）
TV_STRONG = 10.0        # 10倍以上はもっと強い（J26 の読むための表）
UP = 0.05               # B候補＝前の日 +5% 以上（J16・J17・J17F と同じ）
KEEP_MIN_TV = 1.0       # 一覧に残すのは前の日の売買代金1億円以上（件数は全部を数える）
SHOW_TOP = 25
STALE_DAYS = 4          # 一覧の日付が今朝からこれより古ければ使わない（連休明けでも金曜の引けなら4日以内）
# 🆕 2026-10-08 夜 オーナー「地雷銘柄…平日の朝一メール」＝研究 J21（landmine_lab）で 2006〜2016年に「地雷」と決まった形を、
#    J21 と同じ「主戦場」（前の日 +5% 以上・前の日の売買代金10億円以上）の株にだけ印として付ける（数字は main_field_lab と同じ）
MAIN_TV = 10.0          # 主戦場の売買代金（億円）
OVERHEAT = 0.15         # L2 過熱＝前の日の終値が25日線より +15% 超（main_field_lab.OVERHEAT）
STREAK = 4              # L3 連騰＝前の日まで4日以上続けて上がった（main_field_lab.STREAK）
SURGE = 0.15            # L4 急騰＝前の日 +15% 以上


def stock_values(bars):
    """bars＝[(日付, 高値, 安値, 終値, 出来高)]（build_jp_highs.parse_bars の形）→ (売買代金[億円], 倍率, 前の日比)。

    倍率は日足が21本に満たないか分母が0なら None。前の日比は2本に満たなければ None。純関数。
    """
    if len(bars) < 2:
        return None
    c = [b[3] for b in bars]
    tv = [b[3] * (b[4] or 0) / 1e8 for b in bars]
    ret = c[-1] / c[-2] - 1 if c[-2] > 0 else None
    ratio = None
    if len(bars) >= TV_DAYS + 1:
        base = sum(tv[-TV_DAYS - 1:-1]) / TV_DAYS
        if base > 0:
            ratio = tv[-1] / base
    return tv[-1], ratio, ret


def landmine_values(bars):
    """bars → (25日線からの離れ, それまで続けて上がった日数)。main_field_lab.prev_features の最後の日と同じ数字。純関数"""
    c = [b[3] for b in bars]
    dev = c[-1] / (sum(c[-25:]) / 25) - 1 if len(c) >= 25 and sum(c[-25:]) > 0 else None
    streak = 0
    for k in range(len(c) - 1, 0, -1):
        if c[k] > c[k - 1]:
            streak += 1
        else:
            break
    return dev, streak


def mines(r):
    """一覧の行 → 当てはまる地雷の名前（主戦場の株だけ・J21 の L2〜L5）"""
    if not r.get("b") or (r.get("tv") or 0) < MAIN_TV:
        return []
    out = []
    if r.get("dev25") is not None and r["dev25"] > OVERHEAT:
        out.append(f"過熱（25日線 +{r['dev25'] * 100:.0f}%）")
    if (r.get("streak") or 0) >= STREAK:
        out.append(f"連騰（{r['streak']}日）")
    if (r.get("ret") or 0) >= SURGE:
        out.append("急騰（+15%以上）")
    if r.get("c"):
        out.append("売買代金の急増")
    return out


def compute(daily, stocks, asof, tai=None):
    """daily＝{コード: bars}（最後のバーが asof の銘柄だけ・データの誤りの日は除いてから渡す）→ jp-highs.json の "markers"。
    tai＝jp_taishaku.load_or_none() の形（{"codes", "asof", "n"}）か None（一覧が取れなかった＝印を付けない）。"""
    rows, n_c, n_b, n_ratio = [], 0, 0, 0
    for code, bars in daily.items():
        v = stock_values(bars)
        if v is None:
            continue
        tv, ratio, ret = v
        if ratio is not None:
            n_ratio += 1
        c = ratio is not None and ratio >= TV_HIGH
        b = ret is not None and ret >= UP
        n_c += c
        n_b += b
        if (c or b) and tv >= KEEP_MIN_TV:
            dev, streak = landmine_values(bars)
            rows.append({"code": code, "name": (stocks.get(code) or {}).get("name", ""), "tv": round(tv, 2),
                         "ratio": None if ratio is None else round(ratio, 1), "ret": None if ret is None else round(ret, 4),
                         "c": bool(c), "b": bool(b), "tai": (code in tai["codes"]) if tai else None,
                         "dev25": None if dev is None else round(dev, 4), "streak": int(streak)})
    rows.sort(key=lambda r: r["tv"], reverse=True)
    return {"asof": asof, "universe": len(daily), "with_ratio": n_ratio, "n_c": int(n_c), "n_b": int(n_b),
            "keep_min_tv": KEEP_MIN_TV, "rows": rows,
            "taishaku": {"asof": tai.get("asof") or "", "n": len(tai["codes"])} if tai else None}


def _fmt(r):
    ratio = "—" if r.get("ratio") is None else f"{r['ratio']:.1f}倍"
    ret = "—" if r.get("ret") is None else f"{r['ret'] * 100:+.1f}%"
    both = " ★C・B候補の両方" if r.get("c") and r.get("b") else " 〔C〕" if r.get("c") else " 〔B候補〕" if r.get("b") else ""
    tai = " 〔貸借〕" if r.get("tai") is True else ""
    m = mines(r)
    mine = f" 💣地雷：{'・'.join(m)}" if m else ""
    return f"{r['code']} {r['name']}  売買代金 {r['tv']:.1f}億円（{ratio}）・前の日 {ret}{both}{tai}{mine}"


def fresh(markers, today):
    """今朝使ってよい一覧か（前の取引日の引けの分＝今日より前・STALE_DAYS 日以内）"""
    if not markers or not markers.get("asof"):
        return False
    age = (today - dt.date.fromisoformat(markers["asof"])).days
    return 0 < age <= STALE_DAYS


def merged(rows, top=SHOW_TOP):
    """C の大きい順 top と B候補の大きい順 top を1つの一覧に（売買代金の大きい順・同じ銘柄は1回）。
    2026-10-09 オーナー「1と2を進めて」＝前は C と B候補の2つの一覧で、両方に当てはまる銘柄が2回出ていた（10/9 は25のうち16）"""
    keep = {r["code"] for r in [r for r in rows if r.get("c")][:top]} | {r["code"] for r in [r for r in rows if r.get("b")][:top]}
    return [r for r in rows if r["code"] in keep]


def section(markers, today):
    """朝のメールの節（行のリスト）。today＝date。平日でなければ空。一覧が無い・古いときはそう書く。純関数。"""
    if today.weekday() >= 5:
        return []
    head = "【🇯🇵 日本株：寄りで買わない目印（点検表 日本株⑤・前の日の引けでわかるもの）】"
    if not markers or not markers.get("asof"):
        return [head, "  ⚠️ 一覧を作れていない（jp-highs.json に目印の欄が無い）＝今朝は証券会社の画面で確かめる", ""]
    asof = dt.date.fromisoformat(markers["asof"])
    if not fresh(markers, today):
        return [head, f"  ⚠️ 一覧の日付が {asof}（今朝の前の取引日ではない）＝今朝は使わない", ""]
    rows = markers.get("rows") or []
    keep = markers.get("keep_min_tv", KEEP_MIN_TV)
    cs = [r for r in rows if r.get("c")]
    bs = [r for r in rows if r.get("b")]
    show = merged(rows)
    n_both = sum(1 for r in rows if r.get("c") and r.get("b"))
    L = [head, f"  {asof} の引けで判定・東証の全上場 {markers.get('universe', 0)}銘柄から（売買代金{keep:g}億円以上・"
               f"C と B候補それぞれ大きい順に{SHOW_TOP}までを1つの一覧に）", "",
         f"  🚫 C 前の日の売買代金が20営業日平均の5倍以上：{markers.get('n_c', 0)}銘柄（うち{keep:g}億円以上 {len(cs)}）",
         f"     → 寄りでは買わない（{TV_STRONG:g}倍以上はもっと強い・気配がふつうでも買わない）",
         f"  🚫🚫 B候補 前の日に +5% 以上：{markers.get('n_b', 0)}銘柄（うち{keep:g}億円以上 {len(bs)}）",
         "     → 今朝その銘柄だけ全体より +1% 以上高く寄ったら B＝寄りでは買わない（いちばん強い目印・大きい株でも強い）", "",
         f"  一覧（C と B候補をまとめて売買代金の大きい順・印＝〔C〕〔B候補〕★C・B候補の両方 {n_both}銘柄）："]
    L += [f"     {i}. {_fmt(r)}" for i, r in enumerate(show, 1)] or ["     （なし）"]
    if len(rows) > len(show):
        L.append(f"     …ほか {len(rows) - len(show)}銘柄（売買代金の小さいもの）")
    n_mine = sum(1 for r in rows if mines(r))
    L += ["", f"  💣 地雷（研究 J21）＝前の日 +5%以上・売買代金10億円以上の株のうち、過熱（25日線 +15%超）・連騰（4日以上）・"
              f"急騰（+15%以上）・売買代金の急増（5倍以上）のどれかに当てはまるもの：{n_mine}銘柄（上の一覧に印）",
          "     → 2006〜2016年に寄りのあと特に弱かった形（−0.6〜−1.5%）。2023年〜は弱まっている。地雷を外しても、残りを寄りで買う手にはならない（J21）"]
    if "taishaku" in markers:          # 2026-10-08 夕方より前に作った一覧にはこの欄が無い＝何も書かない
        t = markers["taishaku"]
        L += ["", f"  〔貸借〕＝制度信用で空売りできる銘柄（日本取引所グループの一覧 {t.get('asof') or '日付不明'}・{t.get('n', 0):,}銘柄）。"
                  "売り禁・証券会社の在庫は入っていない。印だけ＝空売りの決まりではない（空売りの前向き J31F で記録中）"] if t else \
             ["", "  〔貸借〕の印は今回なし（日本取引所グループの一覧を取れなかった）"]
    L += ["", "  🚫 A はどの銘柄でも：その銘柄だけ全体より +1% 以上高く寄ったら寄りでは買わない（気配で見る・ぎりぎりは買わない側に倒す）",
          "  ※ 決まりは「寄りで買わない」だけ（空売りの合図ではない）。前向きの確かめ（J13F・J17F・J26F）が約1年で判定する", ""]
    return L
