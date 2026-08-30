"""指数を動かす主要銘柄の決算発表予定を economic-events.json に取り込む。

── なぜ「指数を動かす銘柄」だけなのか ──
このリポジトリのシグナル対象は指数・為替・商品・暗号資産だけで、個別株は1つも無い
（NKD=F / ES=F / NQ=F / YM=F / USDJPY=X / GC=F / CL=F / BTC-USD ...）。
そのため決算は「その銘柄を売買するため」ではなく、**指数のボラティリティ要因**として
入れる。affected_assets も個別株ではなく指数先物に向ける。

── データ源の経緯（2026-08-30 実測）──
- J-Quants の決算系（announcement / fins/statements）は **HTTP 403**＝契約プランに
  含まれていない。JQUANTS_API_KEY は有効で equities/master・equities/bars/daily は通るので、
  鍵ではなくプランの問題。決算日をここから取ることはできない。
- Yahoo の quoteSummary は crumb 認証が要り生の curl では 401。yfinance が内部で
  処理するので **yfinance 経由なら取れる**（このリポジトリは既に yfinance に依存）。
- ⚠️ ローカルPCからは curl_cffi が CA 証明書を見つけられず検証できない。
  **GitHub Actions 上で確かめること。**

── 設計上の約束（sync_economic_events.py と揃える）──
1. 既定はドライラン。`--write` を付けたときだけ economic-events.json に書く。
2. **未来の自分の登録ぶんだけ入れ替える。**決算日は後から変更されるので、追加のみだと
   古い日付が残って二重に警告が出る。同じ銘柄の「未来の earnings エントリ」を一度落として
   から入れ直す＝冪等かつ日程変更に追随する。過去の登録と、他のスクリプトが作った
   エントリ（経済指標・市場休場）には**一切触らない**。
3. **推測日を入れない。** yfinance が「日付だけで時刻が無い」や範囲（レンジ）で返すことが
   あるので、確定日時が取れないものは落として一覧に出す。
4. 取れなかった銘柄は黙って消さず、必ず件数と理由を標準出力に出す。
"""
import datetime as dt
import json
import os
import sys
import zoneinfo

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET_JSON = os.path.join(HERE, "economic-events.json")
JST = zoneinfo.ZoneInfo("Asia/Tokyo")
NY = zoneinfo.ZoneInfo("America/New_York")

FORWARD_DAYS = 100   # 先を見る期間。四半期決算なので1四半期ぶんを見込む

# 指数への効き方で選ぶ。impact は economic-events.json の既存値に合わせ high/critical のみ。
#   critical = 単独で指数を動かしうる（NVDA は NQ 全体を動かした実績が繰り返しある）
WATCH = [
    dict(ticker="NVDA",  label="NVIDIA",      impact="critical",
         assets=["ES=F", "NQ=F", "YM=F"], country="US"),
    dict(ticker="AAPL",  label="Apple",       impact="high",
         assets=["ES=F", "NQ=F", "YM=F"], country="US"),
    dict(ticker="MSFT",  label="Microsoft",   impact="high",
         assets=["ES=F", "NQ=F", "YM=F"], country="US"),
    dict(ticker="GOOGL", label="Alphabet",    impact="high",
         assets=["ES=F", "NQ=F"], country="US"),
    dict(ticker="AMZN",  label="Amazon",      impact="high",
         assets=["ES=F", "NQ=F"], country="US"),
    dict(ticker="META",  label="Meta",        impact="high",
         assets=["ES=F", "NQ=F"], country="US"),
    dict(ticker="TSLA",  label="Tesla",       impact="high",
         assets=["ES=F", "NQ=F"], country="US"),
    # 日本株は個別では NKD=F をあまり動かさないが、トヨタだけは規模が別格なので入れる
    dict(ticker="7203.T", label="トヨタ自動車", impact="high",
         assets=["NKD=F"], country="JP"),
]


def fetch_earnings_dates(ticker):
    """(確定日時のリスト, メモ) を返す。取れなければ ([], 理由)。"""
    import yfinance as yf
    try:
        t = yf.Ticker(ticker)
    except Exception as e:
        return [], f"Ticker生成失敗 {type(e).__name__}"

    out, notes = [], []
    # ① get_earnings_dates が最も情報量が多い（時刻つきのことが多い）
    try:
        df = t.get_earnings_dates(limit=12)
        if df is not None and len(df):
            for idx in df.index:
                try:
                    ts = idx.to_pydatetime()
                except Exception:
                    continue
                if ts.tzinfo is None:      # tz が無い＝時刻の裏が取れない → 使わない
                    notes.append("tz無しの行を除外")
                    continue
                out.append(ts)
        else:
            notes.append("get_earnings_dates が空")
    except Exception as e:
        notes.append(f"get_earnings_dates 失敗 {type(e).__name__}")

    # ② 予備: calendar（次回のみ。範囲で返ることがあるので1件に確定できるときだけ）
    if not out:
        try:
            cal = t.calendar
            ed = (cal or {}).get("Earnings Date") if isinstance(cal, dict) else None
            if isinstance(ed, list) and len(ed) == 1:
                d = ed[0]
                # date しか無い＝時刻不明。引け後発表が通例だが**推測しない**ので落とす
                notes.append("calendar は日付のみ（時刻不明）＝採用しない")
            elif isinstance(ed, list) and len(ed) > 1:
                notes.append(f"calendar は範囲（{len(ed)}件）＝日付未確定なので採用しない")
            else:
                notes.append("calendar に Earnings Date 無し")
        except Exception as e:
            notes.append(f"calendar 失敗 {type(e).__name__}")

    return out, " / ".join(notes) if notes else ""


def main():
    apply_changes = "--write" in sys.argv
    now = dt.datetime.now(JST)
    horizon = now + dt.timedelta(days=FORWARD_DAYS)

    data = json.load(open(TARGET_JSON, encoding="utf-8"))
    existing = data["events"]
    watched_names = {f"決算発表 {w['label']}（{w['ticker']}）" for w in WATCH}
    now_iso = now.isoformat(timespec="minutes")

    # 自分が入れた「未来の決算」だけ落とす。過去の記録・他カテゴリは残す。
    def is_own_future(e):
        return (e.get("category") == "earnings"
                and e.get("name") in watched_names
                and e.get("datetime", "") >= now_iso)

    dropped = [e for e in existing if is_own_future(e)]
    existing = [e for e in existing if not is_own_future(e)]
    have = {(e["datetime"][:10], e.get("name", "")) for e in existing}

    added, report = [], []
    for w in WATCH:
        dates, note = fetch_earnings_dates(w["ticker"])
        future = [d.astimezone(JST) for d in dates if now <= d.astimezone(JST) <= horizon]
        report.append((w["ticker"], len(dates), len(future), note))
        for d in sorted(future):
            name = f"決算発表 {w['label']}（{w['ticker']}）"
            if (d.isoformat()[:10], name) in have:
                continue
            added.append({
                "name": name,
                "datetime": d.isoformat(timespec="minutes"),
                "impact": w["impact"],
                "affected_assets": list(w["assets"]),
                "country": w["country"],
                "category": "earnings",
                "note": "sync_earnings_events.py が yfinance から取得（指数のボラ要因として登録）",
            })

    print(f"監視銘柄 {len(WATCH)} 件 / 今後 {FORWARD_DAYS} 日を対象\n")
    print(f"{'ticker':8s} {'取得':>4s} {'今後':>4s}  メモ")
    for tk, n_all, n_fut, note in report:
        print(f"{tk:8s} {n_all:4d} {n_fut:4d}  {note}")

    print(f"\n登録する: {len(added)} 件（入れ替えで落とした未来分 {len(dropped)} 件）")
    for e in sorted(added, key=lambda x: x["datetime"]):
        print(f"   + {e['datetime'][:16]} [{e['impact']:8s}] {e['name']}  → {e['affected_assets']}")

    if not apply_changes:
        print("\n（--write を付けると書き込みます。いまは何も変更していません）")
        return
    if not added and dropped:
        # yfinance が一時的に何も返さなかった回で、既存の予定を消してしまわない
        print("\n⚠️ 取得0件。既存の登録を消さずに現状維持する（yfinance の一時障害を疑う）")
        return
    if not added:
        print("\n変更なし。")
        return
    data["events"] = sorted(existing + added, key=lambda x: x["datetime"])
    with open(TARGET_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"\n✅ economic-events.json に {len(added)} 件を追加（合計 {len(data['events'])} 件）")


if __name__ == "__main__":
    main()
