# -*- coding: utf-8 -*-
"""ロンドン時間・NY時間の前の確認メール（平日）。2026-10-08 夜 オーナー「午後の3時までに間に合うようにFXの強弱とロンドン時間の取引に
注意するべきことをメールで…毎日15時に間に合うように。同じ要領で夜20時までにニューヨーク時間のFXの取引をするための注意事項、通貨の強弱の
メールもお願いします」。

- ロンドン前＝平日 13:30〜16:00 JST のあいだの最初の回で1通（15:00 を過ぎたら件名に「⏰遅れ」）。今夜の指標は「いま〜24:00」
- NY前＝平日 18:30〜21:00 JST のあいだの最初の回で1通（20:00 を過ぎたら「⏰遅れ」）。今夜の指標は「いま〜翌 06:00」
- 起動は「まもなく」メール（indicator-alert.yml）と同じく、頻繁に動くワークフローの完了に相乗り＋cron の保険（session-brief.yml）。
  同じ日・同じ時間帯に2通送らないように actions/cache の印を使う（リポジトリには書かない）
- 中身：今夜の指標（発表直後の値動きの倍率つき）・通貨の強弱（24時間・今日の東京時間〔ロンドン前〕／欧州時間〔NY前〕・約5日）・
  AIの見立て（fundamental-context.json・通貨ごとの lean）・ニュースの見出し（英国とユーロ圏／米国）・決まりと研究から分かっていること・休場

⚠️ 標準ライブラリだけ。読むだけ（何も書き換えない）。自分用のメール。投資助言ではない。
⚠️ 研究の要約（NOTES）は各研究の結果から写した＝結果が変わったらここを直す。
"""
import argparse
import datetime as dt
import json
import os
import re
import smtplib
import sys

import asia_news
import fx_strength as FX
import mail_html      # 🆕 2026-10-09 色付きの HTML メール（文字の本文はそのまま）
import morning_brief as MB
import send_indicator_digest as D

HERE = os.path.dirname(os.path.abspath(__file__))
JST = dt.timezone(dt.timedelta(hours=9))
WD = "月火水木金土日"
SESSIONS = {
    "london": {"name": "ロンドン時間", "flag": "🇬🇧", "open": (13, 30), "deadline": (15, 0), "close": (16, 0), "since": 9,
               "since_label": "今日の東京時間（9時〜）", "since_short": "東京時間", "until_next_day": None, "news": "europe", "news_label": "英国・ユーロ圏",
               "pairs": ("GBPJPY=X", "EURJPY=X", "GBPUSD=X", "EURUSD=X")},
    "ny": {"name": "NY時間", "flag": "🇺🇸", "open": (18, 30), "deadline": (20, 0), "close": (21, 0), "since": 15,
           "since_label": "今日の欧州時間（15時〜）", "since_short": "欧州時間", "until_next_day": (6, 0), "news": "us", "news_label": "米国",
           "pairs": ("USDJPY=X", "EURUSD=X", "GBPUSD=X", "AUDUSD=X")},
}
CENTRAL = re.compile(r"政策金利|FOMC|ECB|英中銀|BOE|日銀|RBA|金融政策|議事録|総裁|議長")
RULES = (
    "発表の数時間前〜は新規を建てない。持つならロット半減か手仕舞い（点検表の5つの質問②。9/17 は英中銀の27分前に建てて当日損失の約半分を出した）",
    "1取引の損失は口座の1〜2%以内。同じ出来事に同じ向きを重ねない（ポート全体で何%か・相関ポジは合算）",
    "損切りは入る前に数値で決めて逆指値で置く。+1R で損切りを建値へ（点検表の出口の戦術）",
)
NOTES = {
    "london": (
        "ロンドン時間の日中の癖（L1・L2 ドルの流れ／L4 強い通貨を買い弱い通貨を売る／S1 東京の値幅の抜け／S2 発表のあとに乗る・逆らう／"
        "S3 キリの良い値）は、個人の費用を引くとどれも残らなかった。M6 ポンド円・ロンドン時間の総当たり 6,144通りも昇格候補 0",
        "ECB の値決め（ロンドン 13:15）の前の2時間はユーロドルが下がりやすい向き（XC1・2つの期間で同じ向き）。ただし個人の費用（約1.8pips）では"
        "ほぼ消える＝取引の合図ではない",
        "発表の直後2時間は普段の何倍も動く（上の今夜の指標の 📏）＝いつもの損切り幅では足りなくなりやすい",
    ),
    "ny": (
        "FOMC の日はドルが売られやすい傾向（X5・+3.8bp だが幅が0をまたぐ＝傾向だけ）。ロンドンの値決め（日本時間 0:00／冬は 1:00）の"
        "あとのドル売りは差なし（X2）",
        "発表のあと動いた向きに乗るか逆らうか（S2）は、費用を引くとどちらも残らなかった＝発表の直後に飛び乗らない",
        "金曜の夜は週末の持ち越しに注意（月曜の窓・点検表の守り）。月曜の窓を埋める向き（X1）は件数不足でまだ分からない",
    ),
}


def window(session, now):
    """→ ("send" | "late" | None)。平日だけ。open〜deadline＝send・deadline〜close＝late"""
    s = SESSIONS[session]
    if now.weekday() >= 5:
        return None
    t = (now.hour, now.minute)
    if s["open"] <= t < s["deadline"]:
        return "send"
    if s["deadline"] <= t < s["close"]:
        return "late"
    return None


def session_now(now):
    """いまの時刻 → 送る時間帯の名前（無ければ None）"""
    return next((k for k in SESSIONS if window(k, now)), None)


def events_in(session, now, path=D.EVENTS):
    """今夜の指標と休場（いま〜24:00／翌 06:00）→ ([(時刻, イベント)], [(時刻, 休場)])"""
    s = SESSIONS[session]
    end = (now + dt.timedelta(days=1)).replace(hour=s["until_next_day"][0], minute=s["until_next_day"][1], second=0, microsecond=0) \
        if s["until_next_day"] else now.replace(hour=23, minute=59, second=59, microsecond=0)
    try:
        data = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        return None, None
    ind, hol = [], []
    for e in data.get("events", []):
        try:
            when = dt.datetime.fromisoformat(e["datetime"]).astimezone(JST)
        except Exception:  # noqa: BLE001
            continue
        if e.get("category") == "market_holiday":
            if when.date() in (now.date(), end.date()):
                hol.append((when, e))
        elif now <= when <= end:
            ind.append((when, e))
    return sorted(ind, key=lambda x: x[0]), sorted(hol, key=lambda x: x[0])


def events_section(session, ind, now):
    s = SESSIONS[session]
    span = f"いま〜{'翌 %02d:%02d' % s['until_next_day'] if s['until_next_day'] else '24:00'}"
    L = [f"【📅 今夜の指標（{span}）】"]
    if ind is None:
        return L + ["  ⚠️ 指標の予定を読めない（economic-events.json）", ""]
    if not ind:
        return L + ["  重要指標の予定なし", ""]
    for w, e in ind:
        left = (w - now).total_seconds() / 3600
        mark = "🏦" if CENTRAL.search(e.get("name", "")) else "🚫" if left <= 3 else "🟡"
        L.append(f"  {mark} {w:%H:%M}（あと{left:.1f}h）  {e['name']}　影響: {D.assets_ja(e)}")
        sl = D.shock_line(e)
        if sl:
            L.append("   " + sl.strip())
    L += ["  ⚠️ 発表の数時間前〜は新規を建てない（持つならロット半減か手仕舞い）", ""]
    return L


def fx_section(session, fx):
    s = SESSIONS[session]
    L = ["【💱 通貨の強弱（サイトの通貨強弱と同じ計算・±0.05%で強い／弱い）】"]
    if not fx:
        return L + ["  ⚠️ 値動きの強弱を取れなかった（Yahoo に届かない）＝サイトの通貨強弱で確かめる", ""]
    L.append(f"  24時間：{FX.ranking(fx.get('h24'))}")
    if fx.get("since"):
        L.append(f"  {s['since_label']}：{FX.ranking(fx.get('since'))}")
    L.append(f"  約5日（傾向）：{FX.ranking(fx.get('d5'))}")
    pr = fx.get("pairs") or {}
    rows = []
    for p in s["pairs"]:
        v = pr.get(p) or {}
        if v.get("h24") is None:
            continue
        since = "" if v.get("since") is None else f"・{v['since']:+.2f}%（{s['since_short']}）"
        rows.append(f"{FX.PAIR_JA[p]} {v['h24']:+.2f}%（24時間）{since}")
    if rows:
        L.append("  主なペア：" + "／".join(rows))
    L += ["  ※ 値動きの強弱はここまでの集計（この先の向きではない）", ""]
    return L


def fund_section(fc, now):
    L = ["【🧭 ファンダの見立て（AI・ブリーフィング）】"]
    if not fc or not fc.get("risk_regime"):
        return L + ["  ⚠️ 見立てを読めない（fundamental-context.json）", ""]
    when = str(fc.get("generated_at") or "")
    try:
        age_h = (now - dt.datetime.fromisoformat(when).astimezone(JST)).total_seconds() / 3600
    except ValueError:
        age_h = None
    L.append(f"  {when[:16].replace('T', ' ')} のブリーフィング" + ("（⚠️ 12時間より古い）" if age_h is None or age_h > 12 else ""))
    r = fc["risk_regime"]
    L.append(f"  地合い：{MB.REGIME.get(r.get('regime'), r.get('regime') or '—')}・確度 {MB.CONF.get(r.get('confidence'), r.get('confidence') or '—')}")
    cur = [c for c in fc.get("currencies") or [] if c.get("code")]
    if cur:
        L.append("  通貨ごと：")
        L += [f"   ・{FX.NAMES.get(c['code'], c['code'])} {MB.LEAN.get(c.get('lean'), c.get('lean') or '—')}"
              f"（{MB.CONF.get(c.get('conviction'), c.get('conviction') or '—')}）：{MB._cut(c.get('reason'), 70)}" for c in cur]
    else:
        L.append("  通貨ごと：このブリーフィングには無い")
    for d in [x for x in r.get("key_drivers") or [] if x][:3]:
        L.append(f"   ・材料：{MB._cut(d, 70)}")
    L += ["  ※ AIの見立ての当たり外れはまだ記録していない（参考）", ""]
    return L


def news_section(session, news):
    s = SESSIONS[session]
    L = [f"【📰 {s['news_label']}のニュースの見出し（直近30時間・機械で拾った・重要度の判断なし）】"]
    flags = {"GB": "🇬🇧", "EU": "🇪🇺", "US": "🇺🇸", "AU": "🇦🇺", "CN": "🇨🇳"}
    items = (news or {}).get("items") or []
    if news is None:
        return L + ["  取れなかった", ""]
    if not items:
        return L + ["  直近30時間になし", ""]
    for x in items:
        L.append(f"  {flags.get(x.get('r'), '・')} {str(x.get('dt'))[5:16].replace('T', ' ')} {MB._cut(x.get('t'), 70)}（{x.get('s') or '出典不明'}）")
    return L + [""]


def notes_section(session, now):
    L = ["【⚠️ この時間の注意（点検表の決まりと研究から）】"]
    L += [f"  ・{x}" for x in RULES]
    L += [f"  ・研究：{x}" for x in NOTES[session]]
    if session == "ny" and now.weekday() == 4:
        L.append("  ・🚩 今日は金曜＝週末をまたぐポジションは持たない側に倒す")
    return L + [""]


def holidays_section(hol):
    if not hol:
        return []
    return ["【🏖️ 休場】"] + [f"  {w:%m/%d}({WD[w.weekday()]})  {e['name']}" for w, e in hol] + [""]


def subject_of(session, kind, now, fx, ind):
    s = SESSIONS[session]
    h = [(c, v) for c, v in ((fx or {}).get("h24") or {}).items() if v is not None]
    tops = ""
    if h:
        h.sort(key=lambda x: -x[1])
        tops = f"強い {FX.NAMES[h[0][0]]}／弱い {FX.NAMES[h[-1][0]]}・"
    ev = f"今夜の指標 {len(ind)}件" + (f"（{ind[0][0]:%H:%M} {ind[0][1]['name']}）" if ind else "") if ind is not None else "指標の予定を読めない"
    return f"{'⏰遅れ ' if kind == 'late' else ''}{s['flag']} {s['name']}の前 {now:%m/%d}({WD[now.weekday()]})：{tops}{ev}"


def build(session, now, fx=None, news=None, fc=None, kind="send", events_path=D.EVENTS):
    s = SESSIONS[session]
    ind, hol = events_in(session, now, events_path)
    L = ["━━━━━━━━━━━━━━━━━━━━━", f"{s['flag']} {s['name']}の前の確認（{now:%Y-%m-%d} ({WD[now.weekday()]}) {now:%H:%M}）",
         "━━━━━━━━━━━━━━━━━━━━━", ""]
    if kind == "late":
        L += [f"⏰ 予定（{s['deadline'][0]}:00）より遅れて届いた（相乗り先のワークフローが動かなかった）", ""]
    for name, fn, args in (("今夜の指標", events_section, (session, ind, now)), ("通貨の強弱", fx_section, (session, fx)),
                           ("ファンダの見立て", fund_section, (fc, now)), ("ニュースの見出し", news_section, (session, news)),
                           ("この時間の注意", notes_section, (session, now)), ("休場", holidays_section, (hol,))):
        L += D._safe(name, fn, *args)
    L += ["━━━━━━━━━━━━━━━━━━━━━", "※ 時刻は各機関の定例公表時刻を JST に換算したもの。これは自分用の確認メールであり投資助言ではありません。"]
    return subject_of(session, kind, now, fx, ind), "\n".join(L)


def _load(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def main(argv=None):
    ap = argparse.ArgumentParser(description="ロンドン時間・NY時間の前の確認メール")
    ap.add_argument("--session", choices=list(SESSIONS), help="省略すると、いまの時刻から決める")
    ap.add_argument("--now", help="時刻を指定して確認する（例 2026-10-09T14:00）")
    ap.add_argument("--dry-run", action="store_true", help="送信せず本文を表示するだけ")
    ap.add_argument("--html-out", help="送るメールの HTML（色付き）をこのファイルにも書く（試し表示の確認用）")
    args = ap.parse_args(argv)
    now = dt.datetime.fromisoformat(args.now).replace(tzinfo=JST) if args.now else dt.datetime.now(JST)
    session = args.session or session_now(now)
    kind = window(session, now) if session else None
    if not session or (kind is None and not args.dry_run):
        print(f"  いま {now:%a %H:%M} JST は送る時間帯の外＝送らない")
        return 0
    try:
        fx = FX.load()
    except Exception:  # noqa: BLE001
        fx = None
    try:
        news = asia_news.load(set_name=SESSIONS[session]["news"])
    except Exception:  # noqa: BLE001
        news = None
    subject, body = build(session, now, fx, news, _load(MB.FUND), kind or "send")
    if args.html_out:
        with open(args.html_out, "w", encoding="utf-8") as fh:
            fh.write(mail_html.to_html(body, subject))
    if args.dry_run:
        print(f"Subject: {subject}\n\n{body}")
        return 0
    sender, password = os.environ.get("GMAIL_USER", ""), os.environ.get("GMAIL_APP_PASSWORD", "")
    recipient = os.environ.get("ALERT_RECIPIENT", "") or sender
    if not sender or not password:
        print("  ⚠️ GMAIL_USER / GMAIL_APP_PASSWORD 未設定＝送信スキップ")
        print(f"Subject: {subject}\n{body}")
        return 0
    msg = mail_html.message(subject, body, sender, recipient)      # 文字＋色付きの HTML（2026-10-09〜）
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as smtp:
        smtp.login(sender, password)
        smtp.send_message(msg)
    print(f"✅ 送信しました: {subject}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
