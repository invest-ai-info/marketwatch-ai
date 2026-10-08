#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""send_indicator_digest.py — 今日の重要指標を朝いちでメールする。

🚨 なぜ必要か（2026-09-17 の実損）:
   オーナーが英中銀の政策金利発表の **27分前**にポンド円を3枚建て、発表の3秒後に
   まとめて手仕舞って -2,370円。当日の損失の約半分がこの1回だった。
   `MY_TRADING_RULES.md` §2「重要指標を持ち越さない」に真正面から反しているが、
   **機械が止める仕組みが無かった**＝環境警戒スコアは*シグナルが出たときのメール*の
   中身でしか届かず、手動の発注は誰も見ていない。

   そこで「シグナルが出たら知らせる」ではなく **「今日これがある」を毎朝先に渡す**。
   判断の直前ではなく、**ポジションを持つ前に**目に入るのが肝。

やること:
   `economic-events.json` を読み、今日〜今後7日の指標を JST で一覧にしてメールする。
   ⚠️ 市場休場（category=market_holiday）は別扱いで末尾にまとめる（本題を埋めないため）。

件名で状態がわかるようにする（開かなくても判断できるのが良いメール）:
   🚨 今日ある / 📅 今日は無いが7日以内にある / ⚪ 7日以内に無い

🕐 いつ届くかの設計（2026-09-17 実測に基づく）:
   GitHub Actions の cron は**当てにならない**。このリポジトリの実績で
     automation-health(00:30UTC) 中央値 +221分・最大 +666分
     health-check(00:00/11:00UTC) 中央値 +160分
     technical-alerts-1d(21:20UTC) 中央値 +59分・90%tile +125分
   ＝「2〜3時間遅れる」というオーナーの体感どおり。朝の便がこれでは意味がない。
   🔑 一方、**予約エージェント(routine)は定刻に近い**（fundamental-context.json の朝コミットは
   実測16件中14件が 06:13〜06:20 JST）。さらに **routine が push したコミットは
   ワークフローを起動できる**（Actions が GITHUB_TOKEN で push したものは起動しない＝
   update-market-news の `jp-rankings.json` パス指定が実は一度も発火していないのが証拠）。
   → だから朝の便は **cron ではなく「routine の push に相乗り」**して飛ばす。cron は保険。

使い方:
   python send_indicator_digest.py                  # 朝の便（JST 04:00-10:00 の窓でのみ送る）
   python send_indicator_digest.py --mode alert     # 発表が近いものだけ「まもなく」通知
   python send_indicator_digest.py --mode alert --sent-file .indicator-alert-sent.json  # 同じ発表は1通だけ
   python send_indicator_digest.py --dry-run        # 本文を表示するだけ（送らない）
   python send_indicator_digest.py --now 2026-09-18T07:00  # 時刻を指定して確認
"""
import argparse
import datetime as dt
import json
import os
import smtplib
import sys
from email.mime.text import MIMEText

import jp_markers
import jp_momentum    # 🆕 2026-10-08 夜 強すぎる株（過去12か月で一番上げた10銘柄・J42／J42F）
import morning_brief  # 🆕 2026-10-08 夜 今日のファンダ・決算・研究から分かっていること

HERE = os.path.dirname(os.path.abspath(__file__))
JST = dt.timezone(dt.timedelta(hours=9))
EVENTS = os.path.join(HERE, "economic-events.json")
JP_HIGHS = os.path.join(HERE, "jp-highs.json")   # 🆕 2026-10-08 朝の目印（jp_markers）
HORIZON_DAYS = 7
# 朝の便を送ってよい時間帯（JST）。routine の相乗りは 06:13 前後、cron の保険は遅れて来るので広めに取る。
MORNING_WINDOW = (4, 10)
# 「まもなく」通知を出す残り時間（分）。⚠️ 幅を実行間隔（毎時）より狭くして二重送信を減らす。
#    それでも cron の揺らぎで稀に2通来ることがあるが、リマインダーなので害は小さい方を選ぶ。
# 🔁 2026-10-04 改定（旧 45〜105分）: 毎時の cron は GitHub に間引かれ、実際は1日4〜5回しか動いていなかった
#    （9/18〜10/4 の87回・間隔の中央値4.7時間）。10/2 のユーロ圏HICP・米雇用統計は「まもなく」が届かなかった。
#    → ワークフローを頻繁な他のワークフローの完了に相乗りさせ（1日約65回・間隔の中央値14分）、
#      範囲を 15〜120分に広げて「範囲に入った最初の回で、その発表について1通だけ」送る（--sent-file で記録）。
#    今週の実績の実行時刻での試算＝取りこぼし 旧81% → 新0.6%。
ALERT_MIN, ALERT_MAX = 15, 120
SENT_KEEP_HOURS = 36   # 送った記録をどれだけ残すか（発表時刻から）。範囲の上限より十分長ければよい

# 監視18銘柄の表示名（affected_assets をそのまま出すと読めないので）
TICKER_JA = {
    "all": "全銘柄", "USDJPY=X": "ドル円", "EURJPY=X": "ユーロ円", "GBPJPY=X": "ポンド円",
    "AUDJPY=X": "豪ドル円", "EURUSD=X": "ユーロドル", "GBPUSD=X": "ポンドドル",
    "AUDUSD=X": "豪ドル", "EURAUD=X": "ユーロ豪ドル", "GBPAUD=X": "ポンド豪ドル",
    "NKD=F": "日経", "ES=F": "S&P500", "NQ=F": "ナスダック", "YM=F": "ダウ",
    "^FTSE": "英FTSE", "GC=F": "金", "SI=F": "銀", "CL=F": "原油", "BTC-USD": "ビットコイン",
}
WD = "月火水木金土日"

# 🆕 2026-09-27 オーナー決定「メールに1行足してください」: 発表直後2時間の値動きが普段の何倍かの実測
#    （新しい柱 B2②・pillar_lab.py が GitHub Actions で計算して pillar-lab.json に書いたもの）を「まもなく」に添える。
#    期待値の話ではなく「ぶれ」の話＝いつもの損切り幅（ATR）では足りなくなりやすいことを、数字で思い出すため。
#    ⚠️ 読めない・測っていない発表では何も足さない（推測の倍率は書かない）。
PILLAR = os.path.join(HERE, "pillar-lab.json")
SHOCK_KIND = [(r"^FOMC.*政策金利", "fomc"), (r"^米\s*CPI", "cpi"), (r"^米雇用統計", "nfp")]
SHOCK_TOP = 3


def load_events(now):
    """(指標, 休場) を (日時, イベント) の昇順タプルで返す。"""
    if not os.path.exists(EVENTS):
        raise SystemExit(f"❌ {EVENTS} が無い")
    data = json.load(open(EVENTS, encoding="utf-8"))
    ind, hol = [], []
    limit = now + dt.timedelta(days=HORIZON_DAYS)
    for e in data.get("events", []):
        try:
            when = dt.datetime.fromisoformat(e["datetime"]).astimezone(JST)
        except Exception:
            continue
        if when < now or when > limit:
            continue
        (hol if e.get("category") == "market_holiday" else ind).append((when, e))
    ind.sort(key=lambda x: x[0])
    hol.sort(key=lambda x: x[0])
    return ind, hol


def assets_ja(e):
    a = e.get("affected_assets", ["all"])
    if "all" in a:
        return "全銘柄"
    return " / ".join(TICKER_JA.get(t, t) for t in a)


def load_markers(path=JP_HIGHS):
    """jp-highs.json の "markers"（build_jp_highs.py が夕方に作る）。無ければ None"""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f).get("markers")
    except (OSError, ValueError):
        return None


def load_fx():
    """通貨の強弱（実際の値動き）の一時ファイル。ワークフローの前の段（fx_strength.py）が作る。無ければ None"""
    try:
        import fx_strength
        return fx_strength.load()
    except Exception:  # noqa: BLE001   壊れても朝のメール（発表の注意）は必ず送る
        return None


def load_news():
    """中国・豪州の見出しの一時ファイル。ワークフローの前の段（asia_news.py）が作る。無ければ None"""
    try:
        import asia_news
        return asia_news.load()
    except Exception:  # noqa: BLE001
        return None


def load_momentum(path=JP_HIGHS):
    """jp-highs.json の "momentum"（build_jp_highs.py → jp_momentum.compute が夕方に作る）。無ければ None"""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f).get("momentum")
    except (OSError, ValueError):
        return None


def _safe(name, fn, *args):
    """節を1つ作る。壊れても朝のメール（発表の注意）は必ず送る＝その節だけ「作れなかった」と書く"""
    try:
        return fn(*args)
    except Exception as e:  # noqa: BLE001
        return [f"【{name}】", f"  ⚠️ この節を作れなかった（{type(e).__name__}）＝今朝は証券会社の画面などで確かめる", ""]


def build(now):
    ind, hol = load_events(now)
    today = now.date()
    today_ev = [(w, e) for w, e in ind if w.date() == today]

    if today_ev:
        head = today_ev[0]
        subject = (f"🚨 今日 重要指標{len(today_ev)}件 — "
                   f"{head[0]:%H:%M} {head[1]['name']}")
    elif ind:
        subject = f"📅 今日は重要指標なし（次は {ind[0][0]:%m/%d %H:%M} {ind[0][1]['name']}）"
    else:
        subject = f"⚪ 今後{HORIZON_DAYS}日に重要指標なし"

    L = ["━━━━━━━━━━━━━━━━━━━━━",
         f"📅 {now:%Y-%m-%d (%a)} の重要指標",
         "━━━━━━━━━━━━━━━━━━━━━", ""]

    if today_ev:
        L.append("【今日】")
        for w, e in today_ev:
            left = (w - now).total_seconds() / 3600
            mark = "🚫" if 0 <= left <= 6 else "🟡"
            L.append(f"  {mark} {w:%H:%M}（あと{left:.1f}h）  {e['name']}")
            L.append(f"       影響: {assets_ja(e)}")
        L.append("")
        # 🔑 ここが本題。ルールを毎朝そのまま渡す（覚えている前提にしない）
        L += ["  ⚠️ MY_TRADING_RULES §2:",
              "     発表の数時間前〜は新規を建てない。持つならロット半減 or 手仕舞い。",
              "     （2026-09-17: 英中銀の27分前に建てて当日損失の約半分を出した）", ""]
    else:
        L += ["【今日】", "  重要指標の予定なし", ""]

    rest = [(w, e) for w, e in ind if w.date() != today]
    if rest:
        L.append(f"【今後{HORIZON_DAYS}日】")
        for w, e in rest:
            L.append(f"  {w:%m/%d}({WD[w.weekday()]}) {w:%H:%M}  {e['name']}")
            L.append(f"       影響: {assets_ja(e)}")
        L.append("")

    # 🆕 2026-10-08 夜 今日のファンダ（AIの朝の見立て）・今日と次の平日の決算（平日だけ）
    # 🆕 2026-10-08 夜（2）通貨の強弱（ワークフローの前の段が fx_strength.py で取った一時ファイル）・中国と豪州のニュース
    L += _safe("今日のファンダ・通貨の強弱・決算", morning_brief.sections, today, morning_brief.FUND, morning_brief.EARN,
               load_fx(), today_ev, load_news())

    # 🆕 2026-10-08 日本株の「寄りで買わない」目印（前の日の引けでわかる C・B候補・💣地雷の印）＝朝の準備（7〜9時）用
    markers = load_markers()
    L += _safe("寄りで買わない目印", jp_markers.section, markers, today)
    # 🆕 2026-10-08 夜 強すぎる株＝新しく買わない側（過去12か月で一番上げた10銘柄・月1回）と、研究から分かっていること（平日だけ）
    L += _safe("強すぎる株", jp_momentum.section, load_momentum(), markers, today)
    L += _safe("研究から分かっていること", morning_brief.research_section, today)

    if hol:
        L.append("【市場休場】")
        for w, e in hol:
            L.append(f"  {w:%m/%d}({WD[w.weekday()]})  {e['name']}")
        L.append("")

    L += ["━━━━━━━━━━━━━━━━━━━━━",
          "※ 日付は各国の公式日程と毎週突合しています（verify-calendar.yml）。",
          "※ 時刻は各機関の定例公表時刻を JST に換算したもので、日付ほどの検証はしていません。",
          "※ これは自分用の確認メールであり投資助言ではありません。"]
    return subject, "\n".join(L)


def shock_line(e, path=PILLAR):
    """この発表の直後2時間は普段の何倍動いたか（過去2年の実測）を1行で。無ければ None"""
    import re
    kind = next((k for pat, k in SHOCK_KIND if re.search(pat, e.get("name", ""))), None)
    if not kind:
        return None
    try:
        with open(path, encoding="utf-8") as f:
            ratio = ((json.load(f).get("b2") or {}).get("ratio") or {}).get(kind) or {}
    except (OSError, ValueError):
        return None
    assets = e.get("affected_assets") or ["all"]
    rows = [(tk, r) for tk, r in ratio.items()
            if ("all" in assets or tk in assets) and r.get("ratio") and r.get("n")]
    if not rows:
        return None
    rows.sort(key=lambda x: -x[1]["ratio"])
    top = rows[:SHOCK_TOP]
    parts = "・".join(f"{TICKER_JA.get(tk, tk)} {r['ratio']:.1f}倍" for tk, r in top)
    ns = [r["n"] for _, r in top]
    times = f"{min(ns)}〜{max(ns)}回" if min(ns) != max(ns) else f"{ns[0]}回"
    return f"  📏 過去2年の実測: 発表直後2時間の値動きは普段の同じ時間帯の {parts}（{times}）"


def event_key(w, e):
    """送った記録のキー＝発表時刻（JST）＋指標名。"""
    return f"{w.astimezone(JST):%Y-%m-%dT%H:%M}|{e.get('name', '')}"


def load_sent(path, now):
    """送った記録 {キー: 送った時刻} を読む。発表から SENT_KEEP_HOURS 過ぎたものは捨てる。"""
    if not path or not os.path.exists(path):
        return {}
    try:
        sent = json.load(open(path, encoding="utf-8")).get("sent", {})
    except Exception:
        return {}           # 壊れていたら空から（同じ発表に2通届くことはあっても、届かないよりよい）
    keep = {}
    for k, v in sent.items():
        try:
            when = dt.datetime.fromisoformat(k.split("|", 1)[0]).replace(tzinfo=JST)
        except ValueError:
            continue
        if now - when <= dt.timedelta(hours=SENT_KEEP_HOURS):
            keep[k] = v
    return keep


def save_sent(path, sent):
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"sent": sent}, f, ensure_ascii=False, indent=1)


def alert_targets(now, sent=None):
    """発表が {ALERT_MIN}〜{ALERT_MAX} 分後に迫っていて、まだ知らせていないもの [(日時, イベント)]。"""
    ind, _ = load_events(now)
    soon = [(w, e) for w, e in ind
            if ALERT_MIN <= (w - now).total_seconds() / 60 <= ALERT_MAX]
    sent = sent or {}
    return [(w, e) for w, e in soon if event_key(w, e) not in sent]


def build_alert(now, sent=None):
    """発表が {ALERT_MIN}〜{ALERT_MAX} 分後に迫っていて、まだ知らせていないものを返す。無ければ (None, None)。"""
    soon = alert_targets(now, sent)
    if not soon:
        return None, None
    w, e = soon[0]
    left = int((w - now).total_seconds() / 60)
    subject = f"⏰ あと{left}分: {e['name']}"
    L = ["━━━━━━━━━━━━━━━━━━━━━",
         f"⏰ まもなく発表  あと {left} 分",
         "━━━━━━━━━━━━━━━━━━━━━", "",
         f"  {w:%H:%M} JST  {e['name']}",
         f"  影響: {assets_ja(e)}", ""]
    sl = shock_line(e)
    if sl:
        L += [sl, "     → いつもの損切り幅（ATR）では足りなくなりやすい", ""]
    if len(soon) > 1:
        L.append("  同じ時間帯にもう1件:")
        L += [f"    {w2:%H:%M}  {e2['name']}" for w2, e2 in soon[1:]]
        L.append("")
    L += ["  ⚠️ いまやること（MY_TRADING_RULES §2）",
          "     ・新規は建てない",
          "     ・持っているならロット半減 or 手仕舞い",
          "     ・「戻ったら入る」で待たない（発表前の値動きは根拠にならない）", "",
          "━━━━━━━━━━━━━━━━━━━━━",
          "※ 2026-09-17: 英中銀の27分前に建てて当日損失の約半分を出した。その再発防止です。",
          "※ これは自分用の確認メールであり投資助言ではありません。"]
    return subject, "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description="重要指標をメールで知らせる")
    ap.add_argument("--mode", choices=["digest", "alert"], default="digest",
                    help="digest=朝の便 / alert=発表が近いものだけ")
    ap.add_argument("--dry-run", action="store_true", help="送信せず本文を表示するだけ")
    ap.add_argument("--now", help="時刻を指定して確認する（例 2026-09-18T07:00）")
    ap.add_argument("--sent-file", help="alert: 送った発表の記録（同じ発表に2通送らないため。"
                                        "ワークフローは actions/cache で次の回へ渡す）")
    args = ap.parse_args()

    now = (dt.datetime.fromisoformat(args.now).replace(tzinfo=JST)
           if args.now else dt.datetime.now(JST))

    sent, new_keys = {}, []
    if args.mode == "alert":
        sent = load_sent(args.sent_file, now)
        new_keys = [event_key(w, e) for w, e in alert_targets(now, sent)]
        subject, body = build_alert(now, sent)
        if subject is None:
            print(f"  発表が {ALERT_MIN}〜{ALERT_MAX} 分後に迫っていて、まだ知らせていない指標なし＝送らない"
                  f"（知らせ済み {len(sent)} 件）")
            return 0
    else:
        lo, hi = MORNING_WINDOW
        if not (lo <= now.hour < hi) and not args.dry_run:
            # ⚠️ routine は朝夕2回 push するので、夕方の push で朝の便が飛ばないようにする
            print(f"  いま {now:%H:%M} JST は朝の窓（{lo}:00-{hi}:00）の外＝送らない")
            return 0
        subject, body = build(now)

    if args.dry_run:
        print(f"Subject: {subject}\n")
        print(body)
        return 0

    sender = os.environ.get("GMAIL_USER", "")
    password = os.environ.get("GMAIL_APP_PASSWORD", "")
    recipient = os.environ.get("ALERT_RECIPIENT", "") or sender
    if not sender or not password:
        # ⚠️ 未設定は「異常」ではなく「この環境では送らない」＝ワークフローを赤くしない
        print("  ⚠️ GMAIL_USER / GMAIL_APP_PASSWORD 未設定＝送信スキップ")
        print(f"Subject: {subject}\n{body}")
        return 0

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as server:
        server.login(sender, password)
        server.send_message(msg)
    print(f"✅ 送信しました: {subject}")
    if args.mode == "alert" and args.sent_file:
        # 送れたときだけ記録する＝送信に失敗した回は、次の回がもう一度送る
        stamp = dt.datetime.now(JST).isoformat(timespec="minutes")
        sent.update({k: stamp for k in new_keys})
        save_sent(args.sent_file, sent)
        out = os.environ.get("GITHUB_OUTPUT")
        if out:
            with open(out, "a", encoding="utf-8") as f:
                f.write("sent=1\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
