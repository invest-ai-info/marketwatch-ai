# -*- coding: utf-8 -*-
"""朝の指標メールに足す節：今日のファンダ（AIの朝の見立て）・今日と明日の決算・研究から分かっていること。
2026-10-08 夜 オーナー「これらの結果、注意するべき銘柄、買ってはいけない銘柄、地雷銘柄。あとその日の注意するべきファンダメンタルなどを
平日の朝一、メールしてください」。

- 今日のファンダ＝fundamental-context.json（routine fundamental-briefing が毎朝 06:13〜06:20 JST に押す＝朝の指標メールはこの push で起動する）
- 決算＝earnings-calendar.json（build_earnings_calendar.py・毎月25日に更新・主な銘柄だけ）
- 研究から分かっていること＝下の RESEARCH（研究の結果が変わったらここを直す・数字は各研究の md と PILLAR_PREREG から写す）

⚠️ 読むだけ（何も書き換えない）。標準ライブラリだけ（朝のメールのワークフローは追加のライブラリを入れない）。
⚠️ 自分用のメール。サイトには出さない。投資助言ではない。
"""
import datetime as dt
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
FUND = os.path.join(HERE, "fundamental-context.json")
EARN = os.path.join(HERE, "earnings-calendar.json")
RESULTS = os.path.join(HERE, "indicator-result.json")   # 🆕 2026-10-08 夜 発表の結果と市場の反応（別の予約が書く）
COUNTRY_CCY = {"us": "USD", "jp": "JPY", "eu": "EUR", "ez": "EUR", "de": "EUR", "uk": "GBP", "gb": "GBP", "au": "AUD", "cn": "CNY"}
COUNTRY_FLAG = {"USD": "🇺🇸", "JPY": "🇯🇵", "EUR": "🇪🇺", "GBP": "🇬🇧", "AUD": "🇦🇺", "CNY": "🇨🇳"}
BIAS = {"BULLISH": "上向き", "BEARISH": "下向き", "NEUTRAL": "中立"}
REGIME = {"RISK_ON": "リスクオン（買われやすい）", "RISK_OFF": "リスクオフ（売られやすい）", "NEUTRAL": "中立", "MIXED": "まちまち"}
CONF = {"HIGH": "高", "MID": "中", "LOW": "低"}
WD = "月火水木金土日"
RATIONALE_CHARS = 160
DRIVERS = 3
# 研究から分かっていること（日本株・朝の売買）。研究の結果が変わったらここを直す
RESEARCH = (
    "寄りで買わない目印（A その銘柄だけ +1%以上高く寄る・B 前の日 +5%以上でさらに高く寄る・C 売買代金の急増）＝"
    "過去の時代で寄りのあとほかの株より弱かった（J13〜J17・J26）。前向きで確かめ中（J13F・J17F・J26F）",
    "地雷（過熱・連騰・急騰・売買代金の急増）を外しても、前の日に大きく上げた株を寄りで買う手にはならない（J21）",
    "強い株を数か月買い続ける形（モメンタム）は、日本では得が見えない（J42 ✕・2003〜2026年）。"
    "一番上げた10銘柄はむしろ弱かった（結果を見たあとの数字＝J42F で確かめ中）",
)


def _load(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def _cut(s, n):
    s = " ".join(str(s or "").split())
    return s if len(s) <= n else s[:n] + "…"


def fundamentals_section(fc, today):
    """今日のファンダ（AIの朝の見立て）。平日だけ。純関数"""
    if today.weekday() >= 5:
        return []
    head = "【🧭 今日のファンダ（AIの朝の見立て・ニュースの要約から）】"
    if not fc or not fc.get("risk_regime"):
        return [head, "  ⚠️ 今朝の見立てを読めない（fundamental-context.json が無い）", ""]
    when = str(fc.get("generated_at") or "")
    L = [head]
    if when[:10] != today.isoformat():
        L.append(f"  ⚠️ 今朝の見立てではない（{when[:16] or '日付不明'} のもの）")
    r = fc["risk_regime"]
    L.append(f"  地合い：{REGIME.get(r.get('regime'), r.get('regime') or '—')}・確度 {CONF.get(r.get('confidence'), r.get('confidence') or '—')}"
             + (f"（{when[11:16]} 作成）" if when[:10] == today.isoformat() else ""))
    if r.get("rationale"):
        L.append(f"  理由：{_cut(r['rationale'], RATIONALE_CHARS)}")
    drivers = [d for d in (r.get("key_drivers") or []) if d][:DRIVERS]
    if drivers:
        L.append("  主な材料：")
        L += [f"   ・{_cut(d, 70)}" for d in drivers]
    assets = [a for a in fc.get("assets") or [] if a.get("name")]
    if assets:
        L.append("  向き：" + "・".join(f"{a['name']} {BIAS.get(a.get('bias'), a.get('bias') or '—')}"
                                     f"（{CONF.get(a.get('conviction'), a.get('conviction') or '—')}）" for a in assets))
        nk = next((a for a in assets if a.get("ticker") == "NKD=F"), None)
        if nk and nk.get("rationale"):
            L.append(f"  日経：{_cut(nk['rationale'], 120)}")
    L += ["  ※ AIの見立ての当たり外れは記録中（研究 A1・まだ偶然の範囲）＝向きは参考。発表の前後は上の【今日】の決まりが優先", ""]
    return L


def _next_weekday(d):
    d += dt.timedelta(days=1)
    while d.weekday() >= 5:
        d += dt.timedelta(days=1)
    return d


LEAN = {"STRONG": "強い", "WEAK": "弱い", "NEUTRAL": "中立"}
ASIA_TOP = 5


def _is_au_cn(e):
    """今日の指標のうち、豪州・中国のもの（国の欄か名前で見る）"""
    return e.get("country") in ("AU", "CN") or any(k in str(e.get("name") or "") for k in ("豪", "中国", "RBA", "オーストラリア"))


def recent_results(res, today):
    """indicator-result.json → 前の平日〜今日の発表の結果（新しい順）"""
    lo = _prev_weekday(today).isoformat()
    xs = [r for r in (res or {}).get("results") or [] if lo <= str(r.get("event_date") or "") <= today.isoformat()]
    return sorted(xs, key=lambda r: str(r.get("event_date")), reverse=True)


def fx_section(fx, fc, today_events, today, results=None):
    """通貨の強弱（前の日の値動き＝fx_strength の一時ファイル／ファンダの見立て＝fundamental-context の currencies）と、
    今日の豪州・中国の指標。平日だけ。純関数（fx_strength は計算の部品だけ使う）"""
    import fx_strength as FX
    if today.weekday() >= 5:
        return []
    L = ["【💱 通貨の強弱（前の日の値動き＋ファンダの見立て）】"]
    if fx:
        L.append(f"  値動き 24時間（サイトの通貨強弱と同じ計算・±{FX.EDGE:g}%で強い／弱い）：{FX.ranking(fx.get('h24'))}")
        L.append(f"  値動き 約5日（傾向）：{FX.ranking(fx.get('d5'))}")
        pr = fx.get("pairs") or {}
        aud = [f"{FX.PAIR_JA[p]} {pr[p]['h24']:+.2f}%（24時間）・{'—' if pr[p].get('d5') is None else format(pr[p]['d5'], '+.2f') + '%'}（約5日）"
               for p in ("AUDJPY=X", "AUDUSD=X") if (pr.get(p) or {}).get("h24") is not None]
        if aud:
            L.append("  豪ドル：" + "／".join(aud))
    else:
        L.append("  ⚠️ 値動きの強弱を取れなかった（Yahoo に届かない・朝のワークフローの前の段が失敗）＝サイトの通貨強弱で確かめる")
    cur = (fc or {}).get("currencies")
    if cur:
        when = str((fc or {}).get("generated_at") or "")[:16]
        L.append(f"  ファンダの見立て（AI・{when} のブリーフィング・前の日〜今朝の材料から）：")
        for c in cur:
            if not c.get("code"):
                continue
            L.append(f"   ・{FX.NAMES.get(c['code'], c['code'])} {LEAN.get(c.get('lean'), c.get('lean') or '—')}"
                     f"（{CONF.get(c.get('conviction'), c.get('conviction') or '—')}）：{_cut(c.get('reason'), 70)}")
    else:
        L.append("  ファンダの見立て（AI・通貨ごと）：まだ無い（予約 fundamental-briefing の指示に通貨の欄を足すと、ここに出る）")
    rr = recent_results(results, today)
    if rr:
        L.append("  前の日〜今朝の指標の結果（予想との差と市場の反応）：")
        for r in rr[:4]:
            ccy = COUNTRY_CCY.get(str(r.get("country") or "").lower(), "")
            L.append(f"   {COUNTRY_FLAG.get(ccy, '・')} {r.get('name', '')}（{str(r.get('event_date'))[5:]}）：{_cut(r.get('headline'), 70)}")
            if r.get("market_reaction"):
                L.append(f"      → {_cut(r['market_reaction'], 90)}")
    au = [(w, e) for w, e in today_events or [] if _is_au_cn(e)]
    if au:
        L.append("  今日の豪州・中国の指標：" + "・".join(f"{w:%H:%M} {e['name']}" for w, e in au))
    else:
        L.append("  今日の豪州・中国の指標：なし")
    L += ["  ※ 値動きの強弱は前の日までの集計（この先の向きではない）。AIの通貨の見立ては当たり外れをまだ記録していない＝参考", ""]
    return L


def asia_section(fc, today, news=None):
    """中国・オーストラリアのニュース。AI が選んだもの（fundamental-context の asia_watch・予約の指示に欄を足したら出る）と、
    機械で拾った見出し（asia_news.py・重要度の判断なし）。平日だけ。純関数"""
    if today.weekday() >= 5:
        return []
    head = "【🇨🇳🇦🇺 中国・オーストラリアのニュース（豪ドルと日経に効くもの）】"
    L = [head] + _asia_ai(fc)
    picked = (news or {}).get("items") or []
    if picked:
        L.append("  機械で拾った見出し（直近30時間・新しい順・重要度の判断はしていない）：")
        for x in picked:
            flag = {"CN": "🇨🇳", "AU": "🇦🇺"}.get(x.get("r"), "・")
            L.append(f"   {flag} {str(x.get('dt'))[5:16].replace('T', ' ')} {_cut(x.get('t'), 70)}（{x.get('s') or '出典不明'}）")
    elif news is None:
        L.append("  機械で拾った見出し：取れなかった（朝のワークフローの前の段が失敗）")
    else:
        L.append("  機械で拾った見出し：直近30時間になし")
    L.append("")
    return L


def _asia_ai(fc):
    if not fc or "asia_watch" not in fc:
        return ["  AI が選んだもの：まだ無い（予約 fundamental-briefing の指示に欄を足すと、ここに出る）"]
    items = [x for x in fc.get("asia_watch") or [] if x.get("headline")]
    rank = {"high": 0, "mid": 1, "low": 2}
    def newest(x):
        try:
            return -dt.date.fromisoformat(str(x.get("published"))[:10]).toordinal()
        except ValueError:
            return 0
    items.sort(key=lambda x: (rank.get(x.get("materiality"), 3), newest(x)))
    if not items:
        return ["  AI が選んだもの：今朝は特になし"]
    L = ["  AI が選んだもの（直近2日・重要度の高い順）："]
    imp = {"high": "高", "mid": "中", "low": "低"}
    for x in items[:ASIA_TOP]:
        flag = {"CN": "🇨🇳", "AU": "🇦🇺"}.get(x.get("region"), "・")
        L.append(f"  {flag} [重要度 {imp.get(x.get('materiality'), '—')}] {_cut(x['headline'], 70)}（{x.get('published') or '日付不明'}・{x.get('source') or '出典不明'}）")
        if x.get("why"):
            L.append(f"     → {_cut(x['why'], 70)}")
    return L


def _prev_weekday(d):
    d -= dt.timedelta(days=1)
    while d.weekday() >= 5:
        d -= dt.timedelta(days=1)
    return d


def earnings_section(ec, today):
    """前の平日の引け後（今日の寄りに効く）・今日・次の平日の決算発表（主な銘柄）。平日だけ。純関数"""
    if today.weekday() >= 5:
        return []
    head = "【📊 決算発表（前の平日の引け後・今日・次の平日／主な銘柄だけ・予定は変わることがある）】"
    if not ec:
        return [head, "  ⚠️ 決算の予定を読めない（earnings-calendar.json が無い）", ""]
    prev = _prev_weekday(today)
    days = (prev, today, _next_weekday(today))
    L, n = [head], 0
    for d in days:
        iso = d.isoformat()
        after = (lambda e: "引け後" in str(e.get("time") or "")) if d == prev else (lambda e: True)
        jp = [e for e in ec.get("jp") or [] if e.get("date") == iso and after(e)]
        us = [e for e in ec.get("us") or [] if e.get("date") == iso and after(e)]
        if not jp and not us:
            continue
        label = "今日" if d == today else f"{d:%m/%d}({WD[d.weekday()]})" + ("＝今日の寄りに効く" if d == prev else "")
        for e in jp:
            n += 1
            L.append(f"  🇯🇵 {label} {e.get('time') or ''} {e.get('code', '')} {e.get('name', '')}{'（予定）' if e.get('tentative') else ''}")
        for e in us:
            n += 1
            L.append(f"  🇺🇸 {label}（米国の日付） {e.get('time') or ''} {e.get('ticker', '')} {e.get('name', '')}{'（予定）' if e.get('tentative') else ''}")
    if not n:
        L.append("  主な銘柄の決算の予定なし")
    else:
        L.append("  → 決算の前後は値動きが大きくなりやすい。その銘柄（と関連の銘柄）を新しく持つときは、発表をまたぐかを先に確かめる")
    L.append(f"  （一覧の更新 {ec.get('updated') or '不明'}・日本は約{len(ec.get('jp') or [])}銘柄だけ）")
    L.append("")
    return L


def research_section(today):
    """研究から分かっていること（日本株・朝の売買）。平日だけ。純関数"""
    if today.weekday() >= 5:
        return []
    return ["【📚 研究から分かっていること（日本株・朝の売買）】"] + [f"  ・{x}" for x in RESEARCH] + \
           ["  ・くわしくはサイトの検証済みリスト（verified-list.md）と研究の地図", ""]


def sections(today, fund_path=FUND, earn_path=EARN, fx=None, today_events=None, news=None, results_path=RESULTS):
    """朝のメールに足す節（ファンダ・通貨の強弱・中国と豪州のニュース・決算）。研究の要約は日本株の節のあとに置くので別"""
    fc = _load(fund_path)
    return (fundamentals_section(fc, today) + fx_section(fx, fc, today_events, today, _load(results_path))
            + asia_section(fc, today, news) + earnings_section(_load(earn_path), today))
