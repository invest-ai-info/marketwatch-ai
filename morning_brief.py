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


def sections(today, fund_path=FUND, earn_path=EARN):
    """朝のメールに足す節（ファンダ・決算）。研究の要約は日本株の節のあとに置くので別"""
    return fundamentals_section(_load(fund_path), today) + earnings_section(_load(earn_path), today)
