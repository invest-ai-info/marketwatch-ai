# -*- coding: utf-8 -*-
"""
monthly_calendar_reminder.py
───────────────────────────────────────
毎月 25 日朝に「来月の主要経済指標」を Gemini で取得し、
economic-events.json に追加すべき項目をメールで通知する。

設計思想:
- 市場休場は generate_market_holidays.py で自動補充されるので対象外
- ここでは重要指標（FOMC, 雇用統計, CPI, PCE, 日銀, ECB, BOE 等）にフォーカス
- Gemini に「来月の主要指標スケジュール」を JSON 形式で生成させる
- メール本文にコピペ可能な JSON 形式で提示
- ユーザーが内容確認のうえ economic-events.json に追加

使い方:
    python monthly_calendar_reminder.py            # 通常実行
    python monthly_calendar_reminder.py --no-email # メール送信なし（テスト用）

GitHub Actions: 毎月 25 日 00:13 UTC = 09:13 JST 25 日
"""
import json
import os
import sys
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

JST = timezone(timedelta(hours=9))


def ask_gemini_for_calendar(year, month, api_key):
    """Gemini に来月の主要経済指標スケジュールを尋ねる"""
    if not api_key:
        return None
    try:
        import google.generativeai as genai
    except ImportError:
        return None
    genai.configure(api_key=api_key)

    prompt = f"""日本人個人投資家向けに、{year}年{month}月の主要経済指標スケジュールを教えてください。

【対象国・指標】
- 米国: FOMC、雇用統計（NFP）、CPI、PCE デフレーター、GDP、PPI、小売売上高
- 日本: 日銀金融政策決定会合、植田総裁会見
- EU: ECB 政策金利、ラガルド総裁会見
- 英国: BOE 政策金利、ベイリー総裁会見
- 中国: CPI、PMI、貿易収支
- 豪州: RBA 政策金利、雇用統計、CPI
- OPEC: 月次会合

【出力フォーマット】
以下のように1行1イベントで出力してください（時刻は JST、ISO8601 形式）:

YYYY-MM-DDTHH:MM:00+09:00 | impact | 国 | イベント名 | note

例:
2026-07-30T03:00:00+09:00 | critical | US | FOMC 政策金利発表（7月） | 7/29 18:00 EDT
2026-07-04T21:30:00+09:00 | critical | US | 米雇用統計 6 月 NFP | 第 1 金曜 8:30 EDT

【ルール】
- 確実に発表される指標のみ（不確実な日付は除外）
- 重要度: critical = FOMC/雇用統計/CPI/日銀、high = それ以外
- 日付は WebSearch で確認できる確定情報のみ
- 出力は表データのみ、前置きや解説は不要"""

    text = ""
    for model_name in ("gemini-2.5-flash", "gemini-2.5-flash-lite"):
        try:
            model = genai.GenerativeModel(model_name)
            resp = model.generate_content(prompt)
            text = (resp.text or "").strip()
            if text:
                return text
        except Exception:
            continue
    return None


def build_json_template(events_text):
    """Gemini 出力をパースして JSON テンプレを生成"""
    json_lines = []
    for line in events_text.splitlines():
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 4:
            continue
        try:
            dt_str = parts[0]
            impact = parts[1]
            country = parts[2]
            name = parts[3]
            note = parts[4] if len(parts) > 4 else ""
            # 影響銘柄を国別に推定
            affected_map = {
                "US": '["all"]',
                "EU": '["EURUSD=X", "EURJPY=X", "EURAUD=X"]',
                "UK": '["GBPUSD=X", "GBPJPY=X", "GBPAUD=X"]',
                "JP": '["NKD=F", "USDJPY=X"]',
                "CN": '["NKD=F", "CL=F", "AUDJPY=X"]',
                "AU": '["AUDJPY=X", "AUDUSD=X", "EURAUD=X", "GBPAUD=X"]',
                "OPEC": '["CL=F"]',
            }
            affected = affected_map.get(country, '["all"]')

            json_lines.append(
                f'    {{\n'
                f'      "name": "{name}",\n'
                f'      "datetime": "{dt_str}",\n'
                f'      "impact": "{impact}",\n'
                f'      "affected_assets": {affected},\n'
                f'      "country": "{country}",\n'
                f'      "note": "{note}"\n'
                f'    }},'
            )
        except Exception:
            continue
    return "\n".join(json_lines)


# ── 種類ごとの先詰まり（2026-11-14）─────────────────────────────────────
# なぜ要るか：下の assess_state は、指標が「全体であと何日ぶんあるか」しか見ていなかった。
#   2027年は米・英・ユーロ圏が12月まで入っているので、**中国や日本の統計が1件も無くても「✅ 対応不要」**と出る。
#   足し忘れると、その種類だけ発表前のメール（indicator-alert・indicator-digest）と環境警戒が黙る。
# 物差し：「まだ登録の無い次の発表」（＝最後の登録日＋その種類の間隔）が KIND_LEAD_DAYS 日より近づいたら知らせる。
#   月に1回の種類 → 最後の登録日まで45日以内／年8回の会合 → 29日以内／
#   四半期に1回（GDP・日銀短観）→ 登録が残っているうちは鳴らさない（次まで約3か月ある＝過ぎてから知らせても間に合う）。
#   間隔は sync_economic_events.py の RULES の every_days（書いていなければ月に1回）。
#   ⚠️ 物差しをゆるめない：やらなくていい作業を毎月催促するメールは読まれなくなる（assess_state の説明と同じ）。
KIND_LEAD_DAYS = 75
_COUNTRY_ORDER = ["US", "JP", "CN", "EU", "UK", "AU"]          # 「やること」の中の並び（国ごとにまとめる）


def kind_runway(events, now_jst, rules=None, lead_days=KIND_LEAD_DAYS):
    """種類（RULES の label）ごとに、台帳の最後の登録日を見る（純関数＝読まない・書かない・通信しない）。

    events : economic-events.json の events（市場休場は読み飛ばす）。名前と種類の照合は json_pattern
             （先に一致した決まりを採る＝sync_economic_events.plan_additions と同じ）。
    戻り値 : RULES と同じ順の list。1件＝dict(label, country, every_days, last, future, days_left, state)
             state  "none"＝今より先の登録が1件も無い ／ "soon"＝もうすぐ登録が尽きる ／ "ok"
             last   最後の登録日（日本時間の日付。台帳に1件も無ければ None）
    """
    import re
    import sync_economic_events as S          # 種類の決まりの単一の真実。ここで読む＝読めなくても月次メール自体は出せる
    rules = S.RULES if rules is None else rules
    seen = {}
    for e in events:
        if e.get("category") == "market_holiday":
            continue
        name = e.get("name") or ""
        rule = next((r for r in rules if re.search(r["json_pattern"], name)), None)
        if rule is None:
            continue
        try:
            when = datetime.fromisoformat(e.get("datetime") or "")
        except (TypeError, ValueError):       # 読めない日付の行は数えない（＝その種類は「無い」側に倒れる）
            continue
        if when.tzinfo is None:
            when = when.replace(tzinfo=JST)
        seen.setdefault(rule["label"], []).append(when.astimezone(JST))

    today = now_jst.astimezone(JST).date()
    rows = []
    for rule in rules:
        whens = seen.get(rule["label"], [])
        every = S.every_days_of(rule)
        future = sum(1 for w in whens if w >= now_jst)
        last = max(whens).date() if whens else None
        days_left = (last - today).days if future else None
        if not future:
            state = "none"
        elif days_left <= lead_days - every:
            state = "soon"
        else:
            state = "ok"
        rows.append(dict(label=rule["label"], country=rule.get("country", ""), every_days=every,
                         last=last, future=future, days_left=days_left, state=state))
    return rows


def _how_often(every_days):
    return "四半期に1回" if every_days >= 80 else "年8回" if every_days >= 40 else "月1回"


def kind_runway_todo(rows):
    """kind_runway の結果から「あなたがやること」の文を **1件** 作る（知らせる種類が無ければ None）。"""
    order = lambda r: _COUNTRY_ORDER.index(r["country"]) if r["country"] in _COUNTRY_ORDER else len(_COUNTRY_ORDER)  # noqa: E731
    none = sorted((r for r in rows if r["state"] == "none"), key=order)       # sorted は元の順（RULES の順）を保つ
    soon = sorted((r for r in rows if r["state"] == "soon"), key=order)
    if not none and not soon:
        return None
    pad = "     "
    L = [f"⚠️ 指標を種類ごとに見ると、**先の登録が無い・残りが少ない種類が {len(none) + len(soon)}種類**あります。"
         f"このままだと、その種類だけ発表前のメールと環境警戒が鳴りません。",
         f"{pad}各国の公式の日程で確かめて、generate_market_news.py の ECONOMIC_EVENTS_<年> に足してください"
         f"（公式がまだ日程を出していない種類は、出てから足す）。",
         f"{pad}足したあと、このワークフローをもう一度動かすと台帳に入ります（動かさなくても次の25日に入ります）。"]
    if none:
        L.append(f"{pad}▼ 先の登録が1件も無い（{len(none)}種類）")
        for r in none:
            tail = f"最後の登録 {r['last'].isoformat()}" if r["last"] else "台帳に1件も無い"
            L.append(f"{pad}   ・{r['label']}（{_how_often(r['every_days'])}・{tail}）")
    if soon:
        L.append(f"{pad}▼ もうすぐ登録が尽きる（{len(soon)}種類）")
        for r in soon:
            L.append(f"{pad}   ・{r['label']}（{_how_often(r['every_days'])}・"
                     f"最後の登録 {r['last'].isoformat()}＝あと{r['days_left']}日）")
    return "\n".join(L)


def assess_state(now_jst, here=None):
    """自動更新の結果を読み、**人がやるべきことだけ**を todos に返す。

    2026-08-30 まで、このメールは「economic-events.json に翌月の指標を手で追加して
    ください」という依頼だった。しかし転記は sync_economic_events.py と
    build_earnings_calendar.py が自動でやるようになったので、依頼は成立しなくなった。
    ⚠️ **やらなくていい作業を毎月催促するメールは読まれなくなる。**実際、今回の事故
    （指標が2か月ゼロ）は、このメールが届き続けたのに誰も動かなかった結果でもある。
    ⇒ 依頼をやめ、状態の報告に変える。todos が空なら「対応不要」と明示する。

    here : 台帳のある場所（省けばこのファイルと同じ場所。テストが作り物の台帳を渡すためのもの）
    """
    here = here or os.path.dirname(os.path.abspath(__file__))
    todos, stats = [], {}
    now_iso = now_jst.isoformat(timespec="minutes")
    ev = fut = None

    # ── 経済指標（sync_economic_events.py が年ごとの表 ECONOMIC_EVENTS_<年> から生成）──
    try:
        ev = json.load(open(os.path.join(here, "economic-events.json"), encoding="utf-8"))["events"]
        ind = sorted((e for e in ev if e.get("category") != "market_holiday"),
                     key=lambda x: x.get("datetime", ""))
        fut = [e for e in ind if e.get("datetime", "") >= now_iso]
        stats["ind_future"] = len(fut)
        stats["ind_last"] = fut[-1]["datetime"][:10] if fut else None
        stats["ind_next3"] = [(e["datetime"][:16], e["name"]) for e in fut[:3]]
        if not fut:
            todos.append(
                "🚨 経済指標の未来分が **0件**。generate_market_news.py の年ごとの表 "
                "ECONOMIC_EVENTS_<年> に翌月以降を追記してから、このワークフローを再実行してください。"
                "（economic-events.json を直接編集しても生成対象にはなりません）")
        else:
            runway = (datetime.fromisoformat(fut[-1]["datetime"]) - now_jst).days
            stats["ind_runway"] = runway
            if runway < 75:
                todos.append(
                    f"⚠️ 経済指標が **あと{runway}日ぶん**（最終 {fut[-1]['datetime'][:10]}）。"
                    f"元の表は年ごと（ECONOMIC_EVENTS_<年>）で、公式がまだ出していない先の分は入っていません。"
                    f"**各国の公式の日程で確かめて書き足さないと、その先が空になります**"
                    f"（翌年の表が無ければ ECONOMIC_EVENTS_<翌年> = [...] を作るだけで読まれます）。下の候補リストは材料です"
                    f"（そのまま写さず公式で確かめる）")
    except Exception as e:
        todos.append(f"🚨 economic-events.json を読めませんでした: {e}")

    # ── 種類ごとの先詰まり（全体では先まで入っていても、中国や日本だけ空ということがある）──
    if ev is not None:
        try:
            rows = kind_runway(ev, now_jst)
            stats["kind_total"] = len(rows)
            stats["kind_none"] = sum(1 for r in rows if r["state"] == "none")
            stats["kind_soon"] = sum(1 for r in rows if r["state"] == "soon")
            todo = kind_runway_todo(rows)
            if todo and fut != []:            # 指標が全部0件のときは、上の「未来分が0件」の1件で足りる
                todos.append(todo)
        except Exception as e:                # 見張りが動かないのを黙って通さない
            todos.append(f"🚨 種類ごとの先詰まりを調べられませんでした（monthly_calendar_reminder.py の kind_runway）: {e}")

    # ── 決算予定（build_earnings_calendar.py が Nasdaq API + yfinance で取得）──
    try:
        ec = json.load(open(os.path.join(here, "earnings-calendar.json"), encoding="utf-8"))
        today = now_jst.date().isoformat()
        fus = [x for x in ec.get("us", []) if x.get("date", "") >= today]
        fjp = [x for x in ec.get("jp", []) if x.get("date", "") >= today]
        stats["ern_us"], stats["ern_jp"] = len(fus), len(fjp)
        stats["ern_updated"] = ec.get("updated")
        if not fus or not fjp:
            todos.append(
                f"🚨 決算予定の未来分が足りません（米 {len(fus)} 件 / 日 {len(fjp)} 件）。"
                f"両方0なら上流（Nasdaq API・yfinance）の障害、片方だけなら該当国のソースを疑ってください")
    except Exception as e:
        todos.append(f"🚨 earnings-calendar.json を読めませんでした: {e}")

    return todos, stats


def build_report(year, month, todos, stats, raw_text):
    """メールの件名と本文を作る（送らない＝テストと --no-email の見本で同じ文面を見られる）。"""
    if todos:
        subject = f"⚠️ [要対応 {len(todos)}件] {year}年{month}月 カレンダー自動更新"
    else:
        subject = f"✅ [対応不要] {year}年{month}月 カレンダー自動更新"

    L = ["━━━━━━━━━━━━━━━━━━━━━",
         "📅 カレンダー自動更新レポート",
         "━━━━━━━━━━━━━━━━━━━━━", ""]
    L += ["【いまの状態】",
          f"  経済指標   未来 {stats.get('ind_future', '?')} 件"
          + (f"（最終 {stats['ind_last']} ／あと{stats.get('ind_runway','?')}日ぶん）" if stats.get("ind_last") else "")]
    if "kind_total" in stats:
        L += [f"  種類ごと   {stats['kind_total']} 種類のうち 先の登録なし {stats['kind_none']}"
              f" ／ もうすぐ尽きる {stats['kind_soon']}"]
    L += [f"  決算予定   米 {stats.get('ern_us', '?')} 件 / 日 {stats.get('ern_jp', '?')} 件"
          f"（更新 {stats.get('ern_updated', '?')}）", ""]
    if stats.get("ind_next3"):
        L.append("  直近の指標:")
        L += [f"    {d}  {n}" for d, n in stats["ind_next3"]]
        L.append("")

    if todos:
        L += ["━━━━━━━━━━━━━━━━━━━━━", "【あなたがやること】", ""]
        for i, t in enumerate(todos, 1):
            L += [f"  {i}. {t}", ""]
        if raw_text:
            L += ["━━━━━━━━━━━━━━━━━━━━━",
                  f"【材料】Gemini が挙げた {year}年{month}月の主要指標候補",
                  "  ※ そのまま貼らず、ECONOMIC_EVENTS_<年> の書式",
                  "     (月, 日, \"us\", \"high\", \"名称\", \"説明\") に直して追記してください", "",
                  raw_text, ""]
    else:
        L += ["━━━━━━━━━━━━━━━━━━━━━",
              "✅ 対応は要りません。指標も決算も自動で更新済みです。", ""]

    L += ["━━━━━━━━━━━━━━━━━━━━━",
          "指標  = sync_economic_events.py（年ごとの表 ECONOMIC_EVENTS_<年> から生成）",
          "決算  = build_earnings_calendar.py（Nasdaq API + yfinance）",
          "休場  = generate_market_holidays.py（米英は2027年・東証は2028年まで自動）",
          "見張り = automation-health §⑬（先詰まりを毎朝チェック）",
          "時短投資ラボ Calendar"]
    return subject, chr(10).join(L)


def send_report_email(year, month, todos, stats, raw_text):
    sender = os.environ.get("GMAIL_USER", "")
    password = os.environ.get("GMAIL_APP_PASSWORD", "")
    recipient = os.environ.get("ALERT_RECIPIENT", "") or sender
    if not sender or not password:
        print("  ⚠️ GMAIL_USER / GMAIL_APP_PASSWORD 未設定＝送信スキップ")
        return False

    subject, body = build_report(year, month, todos, stats, raw_text)

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg.attach(MIMEText(body, "plain", "utf-8"))
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as server:
            server.login(sender, password)
            server.sendmail(sender, [recipient], msg.as_string())
        print(f"  📧 送信完了: {recipient}（{subject}）")
        return True
    except Exception as e:
        print(f"  ❌ 送信失敗: {e}")
        return False


def main():
    now_jst = datetime.now(JST)
    today = now_jst.date()
    no_email = "--no-email" in sys.argv

    if today.month == 12:
        target_year, target_month = today.year + 1, 1
    else:
        target_year, target_month = today.year, today.month + 1

    print(f"📅 カレンダー自動更新レポート ({today} → 翌月 {target_year}-{target_month:02d})")

    todos, stats = assess_state(now_jst)
    print(f"  状態: 指標 未来{stats.get('ind_future','?')}件 / "
          f"決算 米{stats.get('ern_us','?')}・日{stats.get('ern_jp','?')}件")
    print(f"  要対応: {len(todos)} 件")
    for t in todos:
        print(f"    - {t[:110]}")

    # 対応事項があるときだけ Gemini を叩く（不要な API 呼び出しと待ち時間を作らない）
    raw_text = ""
    if todos:
        api_key = os.environ.get("GEMINI_API_KEY", "")
        print(f"  🤖 Gemini に {target_year}-{target_month:02d} の主要指標を問合せ中...")
        raw_text = ask_gemini_for_calendar(target_year, target_month, api_key) or ""
        if not raw_text:
            raw_text = (f"(Gemini 取得失敗。WebSearch で「{target_year}年{target_month}月 "
                        f"FOMC 雇用統計 CPI 日銀」を調べてください)")
        else:
            print(f"  ✅ Gemini から {len(raw_text)} 文字取得")

    if no_email:
        print("  🔇 メール送信スキップ (--no-email)。送るはずだった文面は下のとおり:")
        subject, body = build_report(target_year, target_month, todos, stats, raw_text)
        print(f"\n件名: {subject}\n\n{body}")
        return

    send_report_email(target_year, target_month, todos, stats, raw_text)


if __name__ == "__main__":
    main()
