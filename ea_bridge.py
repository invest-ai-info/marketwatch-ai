# -*- coding: utf-8 -*-
"""EA へ渡すデータを作る（手元で5分ごとに動かす・2026-09-30 AT1〜AT3・決まりは PILLAR_PREREG.md「AT」）。

EA（MT4 のプログラム）は手元の research/ea/ に置き、リポジトリには入れない。ここは EA が読むファイルを作るだけ。

入力（既定は GitHub から取る。--local ならリポジトリの手元の写しを使う）:
  signals-recent.json  …… 直近7日の4時間足の合図（build_signals_recent.py が technical-alerts のあとに書く）
  economic-events.json …… 重要な発表の日程
出力（--out-dir＝MT4 の MQL4\\Files。書きかけを読ませないよう、別名に書いてから置き換える）:
  mw_events.csv        …… 重要な発表（AT1 の G4・AT2）。列: utc,name,country,currencies,symbols
                          utc＝発表の時刻（UTC の 1970年からの秒）。symbols＝業者の銘柄名を ; でつなぐ。「*」＝全部
  mw_orders.csv        …… メールで届いた4時間足の合図（AT3）。列: id,fired_utc,symbol,dir,entry,sl,tp1,tp2,atr,kind
                          dir＝1（買い）／-1（売り）。kind＝promoted（昇格エッジ）／watch（観察中の候補）
  mw_bridge_status.csv …… 最後に書いた時刻（列: written_utc,events,orders,unmapped）。EA がデータの古さを確かめる
文字は UTF-16（BOM つき）。EA は FileOpen(name, FILE_READ|FILE_CSV, ',')（Unicode の既定のまま）で読む。

銘柄名：サイトのティッカー → 業者の銘柄名。為替は「=X」を外して --suffix を足す（例 GBPJPY=X → GBPJPY）。
為替以外（GC=F・NKD=F など）は --symbols の JSON（{"GC=F": "GOLD", ...}・手元の research/ea/ に置く）で決める。無いものは書かない。

実行例（Windows のタスクで5分ごと）:
  python ea_bridge.py --out-dir "C:\\...\\MQL4\\Files" --symbols research\\ea\\symbols.json
"""
import argparse
import datetime as dt
import json
import os
import sys
import urllib.request

RAW = "https://raw.githubusercontent.com/invest-ai-info/marketwatch-ai/main/"
UTC = dt.timezone.utc
IMPACTS = ("high", "critical")
COUNTRY_CCY = {"US": "USD", "UK": "GBP", "GB": "GBP", "EU": "EUR", "JP": "JPY", "CN": "CNH", "AU": "AUD",
               "NZ": "NZD", "CA": "CAD", "CH": "CHF"}
EVENT_PAST_H, EVENT_AHEAD_D = 2, 8        # 発表の2時間前のものから8日先まで
ORDER_MAX_AGE_H = 24                     # EA が「90分より後なので建てない」と記録できるよう、少し長めに渡す
EV_HEAD = ["utc", "name", "country", "currencies", "symbols"]
OR_HEAD = ["id", "fired_utc", "symbol", "dir", "entry", "sl", "tp1", "tp2", "atr", "kind"]
ST_HEAD = ["written_utc", "events", "orders", "unmapped"]


def fetch_json(name, local=False, timeout=30):
    if local:
        with open(name, encoding="utf-8") as fh:
            return json.load(fh)
    req = urllib.request.Request(RAW + name, headers={"User-Agent": "mw-ea-bridge"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def map_symbol(ticker, suffix="", extra=None):
    """サイトのティッカー → 業者の銘柄名（決まらなければ None）"""
    extra = extra or {}
    if ticker in extra:
        return extra[ticker]
    t = str(ticker)
    if t.endswith("=X") and len(t) == 8:
        return t[:-2] + suffix
    return None


def _utc(text):
    t = dt.datetime.fromisoformat(str(text))
    if t.tzinfo is None:
        raise ValueError(f"時刻に時差が無い: {text}")
    return t.astimezone(UTC)


def _clean(text):
    return str(text).replace(",", "・").replace("\n", " ").replace("\r", " ").strip()


def events_rows(events, now, suffix="", extra=None):
    rows, unmapped = [], set()
    lo, hi = now - dt.timedelta(hours=EVENT_PAST_H), now + dt.timedelta(days=EVENT_AHEAD_D)
    for e in events:
        if e.get("impact") not in IMPACTS or e.get("category") == "market_holiday":
            continue
        try:
            t = _utc(e["datetime"])
        except (KeyError, ValueError):
            continue
        if not lo <= t <= hi:
            continue
        assets = e.get("affected_assets") or []
        if "all" in assets:
            syms = "*"
        else:
            got = []
            for a in assets:
                s = map_symbol(a, suffix, extra)
                (got.append(s) if s else unmapped.add(a))
            syms = ";".join(sorted(set(got)))
        rows.append([int(t.timestamp()), _clean(e.get("name", "")), e.get("country", ""),
                     COUNTRY_CCY.get(e.get("country", ""), ""), syms])
    return sorted(rows, key=lambda r: r[0]), unmapped


def orders_rows(recent, now, suffix="", extra=None):
    rows, unmapped = [], set()
    since = now - dt.timedelta(hours=ORDER_MAX_AGE_H)
    for s in (recent or {}).get("signals", []):
        if s.get("timeframe") != "4h" or not s.get("email_sent") or s.get("dir") not in (1, -1):
            continue
        kind = "promoted" if s.get("promoted_hit") else "watch" if s.get("watch_hit") else None
        if not kind or s.get("stop_loss") is None or s.get("entry") is None:
            continue
        try:
            t = _utc(s["fired_at"])
        except (KeyError, ValueError):
            continue
        if t < since or t > now + dt.timedelta(minutes=5):
            continue
        sym = map_symbol(s.get("ticker"), suffix, extra)
        if not sym:
            unmapped.add(s.get("ticker"))
            continue
        rows.append([_clean(s["id"]), int(t.timestamp()), sym, int(s["dir"]),
                     *(repr(float(s[k])) if s.get(k) is not None else "" for k in
                       ("entry", "stop_loss", "take_profit_1", "take_profit_2", "atr")), kind])
    return sorted(rows, key=lambda r: r[1]), unmapped


def write_csv_utf16(path, head, rows):
    """UTF-16（BOM つき）・カンマ区切り。別名に書いてから置き換える（EA に書きかけを読ませない）"""
    tmp = path + ".tmp"
    text = "\r\n".join(",".join(str(c) for c in r) for r in [head] + list(rows)) + "\r\n"
    with open(tmp, "wb") as fh:
        fh.write(text.encode("utf-16"))          # Python の utf-16 は BOM（リトルエンディアン）つき
    os.replace(tmp, path)


def run(out_dir, events, recent, now, suffix="", extra=None):
    ev, un1 = events_rows(events, now, suffix, extra)
    orders, un2 = orders_rows(recent, now, suffix, extra)
    unmapped = sorted(x for x in (un1 | un2) if x)
    write_csv_utf16(os.path.join(out_dir, "mw_events.csv"), EV_HEAD, ev)
    write_csv_utf16(os.path.join(out_dir, "mw_orders.csv"), OR_HEAD, orders)
    write_csv_utf16(os.path.join(out_dir, "mw_bridge_status.csv"), ST_HEAD,
                    [[int(now.timestamp()), len(ev), len(orders), ";".join(unmapped)]])
    return ev, orders, unmapped


def main(argv=None):
    ap = argparse.ArgumentParser(description="EA へ渡すデータを作る（AT1〜AT3）")
    ap.add_argument("--out-dir", required=True, help="MT4 の MQL4\\Files")
    ap.add_argument("--suffix", default="", help="業者の銘柄名の後ろの文字（例 .m）")
    ap.add_argument("--symbols", help="為替以外の銘柄名の対応（JSON）")
    ap.add_argument("--local", action="store_true", help="GitHub から取らず、手元の写しを使う")
    a = ap.parse_args(argv)
    extra = {}
    if a.symbols:
        with open(a.symbols, encoding="utf-8") as fh:
            extra = json.load(fh)
    events = fetch_json("economic-events.json", a.local)["events"]
    recent = fetch_json("signals-recent.json", a.local)
    ev, orders, unmapped = run(a.out_dir, events, recent, dt.datetime.now(UTC), a.suffix, extra)
    print(f"発表 {len(ev)} 件・合図 {len(orders)} 件を書いた（{a.out_dir}）。銘柄名が決まらないもの: {unmapped or 'なし'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
