# -*- coding: utf-8 -*-
"""朝のメール用の通貨の強弱（実際の値動き）。2026-10-08 夜 オーナー「FXの強弱…午前中はオージー（豪ドル）の取引をする可能性があるので…
前日のファンダでどの通貨が弱い傾向がある、強い傾向があるなどの情報が欲しい」。

サイトの通貨強弱（generate_technical_alerts.calc_currency_strength）と**同じ計算**＝9ペアの1時間足で、最新の終値と24本前の終値の
変動率（％）を出し、各通貨について「前に来るペアは＋、後ろに来るペアは−」で平均する（USD・EUR・GBP・JPY・AUD）。
あわせて約5日（120本前）も同じ式で出す（傾向を見るため・読むだけ）。強い／弱いの線はサイトと同じ ±0.05（CS-5）。

⚠️ 標準ライブラリだけ（朝のメールのワークフローは追加のライブラリを入れない）。Yahoo に届かなければ None（メールは止めない）。
⚠️ 読むだけ・何も書き出さない。過去の値動きの集計で、この先の向きを約束しない。
"""
import json
import time
import urllib.request

PAIRS = {  # generate_technical_alerts.FX_PAIR_MAP と同じ
    "USDJPY=X": ("USD", "JPY"), "EURJPY=X": ("EUR", "JPY"), "GBPJPY=X": ("GBP", "JPY"), "AUDJPY=X": ("AUD", "JPY"),
    "EURUSD=X": ("EUR", "USD"), "GBPUSD=X": ("GBP", "USD"), "AUDUSD=X": ("AUD", "USD"),
    "EURAUD=X": ("EUR", "AUD"), "GBPAUD=X": ("GBP", "AUD"),
}
CURRENCIES = ("USD", "EUR", "GBP", "JPY", "AUD")
NAMES = {"USD": "米ドル", "EUR": "ユーロ", "GBP": "ポンド", "JPY": "円", "AUD": "豪ドル", "CNY": "人民元"}
PAIR_JA = {"USDJPY=X": "ドル円", "EURJPY=X": "ユーロ円", "GBPJPY=X": "ポンド円", "AUDJPY=X": "豪ドル円", "EURUSD=X": "ユーロドル",
           "GBPUSD=X": "ポンドドル", "AUDUSD=X": "豪ドル米ドル", "EURAUD=X": "ユーロ豪ドル", "GBPAUD=X": "ポンド豪ドル"}
BACK_24H = 24          # サイトと同じ（最新と iloc[-24] の比較）
BACK_5D = 120          # 約5日（1時間足 × 24 × 5）
EDGE = 0.05            # 強い／弱いの線（％・CS-5）
UA = {"User-Agent": "Mozilla/5.0"}


def change(closes, back):
    """1時間足の終値の並び → 最新と back 本前の変動率（％）。足りなければ None。サイトと同じ丸め"""
    if len(closes) < back or not closes[-back]:
        return None
    return round((closes[-1] - closes[-back]) / closes[-back] * 100, 3)


def strength(pair_changes):
    """{ペア: 変動率％} → {通貨: 平均}（calc_currency_strength と同じ式）"""
    scores = {c: [] for c in CURRENCIES}
    for pair, ch in pair_changes.items():
        if ch is None or pair not in PAIRS:
            continue
        base, quote = PAIRS[pair]
        scores[base].append(ch)
        scores[quote].append(-ch)
    return {c: (round(sum(v) / len(v), 3) if v else None) for c, v in scores.items()}


def label(x):
    if x is None:
        return "—"
    return "強い" if x >= EDGE else "弱い" if x <= -EDGE else "中立"


def fetch_closes(ticker, tries=2):
    """Yahoo の1時間足（10日）の終値。取れなければ []"""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=10d&interval=1h"
    for k in range(tries):
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20))["chart"]["result"][0]
            return [float(c) for c in r["indicators"]["quote"][0]["close"] if c is not None]
        except Exception:  # noqa: BLE001
            time.sleep(1 + k)
    return []


def fetch_series(ticker, tries=2):
    """Yahoo の1時間足（10日）の (時刻〔UTC 秒〕, 終値) の並び。取れなければ []（セッション前のメールの「今日の◯◯時から」に使う）"""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=10d&interval=1h"
    for k in range(tries):
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20))["chart"]["result"][0]
            return [(int(t), float(c)) for t, c in zip(r.get("timestamp") or [], r["indicators"]["quote"][0]["close"]) if c is not None]
        except Exception:  # noqa: BLE001
            time.sleep(1 + k)
    return []


def change_since(series, since_ts):
    """(時刻, 終値) の並び → since_ts より前の最後の終値から最新までの変動率（％）。足りなければ None"""
    before = [c for t, c in series if t < since_ts]
    if not before or not series or not before[-1] or series[-1][0] < since_ts:
        return None
    return round((series[-1][1] - before[-1]) / before[-1] * 100, 3)


def compute_full(since_ts=None, fetch=fetch_series):
    """24時間・約5日に加えて、since_ts（UTC 秒）からの強弱も出す（セッション前のメール用）。1つも取れなければ None"""
    pairs = {}
    for t in PAIRS:
        sr = fetch(t)
        cl = [c for _, c in sr]
        pairs[t] = {"h24": change(cl, BACK_24H), "d5": change(cl, BACK_5D),
                    "since": change_since(sr, since_ts) if since_ts else None}
    if all(v["h24"] is None for v in pairs.values()):
        return None
    out = {"h24": strength({p: v["h24"] for p, v in pairs.items()}),
           "d5": strength({p: v["d5"] for p, v in pairs.items()}), "pairs": pairs}
    if since_ts:
        out["since"] = strength({p: v["since"] for p, v in pairs.items()})
    return out


def compute(fetch=fetch_closes):
    """→ {"h24": {通貨: 値}, "d5": {…}, "pairs": {ペア: {"h24", "d5"}}}。1つも取れなければ None"""
    pairs = {}
    for t in PAIRS:
        cl = fetch(t)
        pairs[t] = {"h24": change(cl, BACK_24H), "d5": change(cl, BACK_5D)}
    if all(v["h24"] is None for v in pairs.values()):
        return None
    return {"h24": strength({p: v["h24"] for p, v in pairs.items()}),
            "d5": strength({p: v["d5"] for p, v in pairs.items()}), "pairs": pairs}


def ranking(s):
    """{通貨: 値} → 強い順の文字列"""
    xs = sorted(((c, v) for c, v in (s or {}).items() if v is not None), key=lambda x: -x[1])
    return " ＞ ".join(f"{NAMES[c]} {v:+.2f}%（{label(v)}）" for c, v in xs) or "—"


OUT = ".fx-strength.json"   # 朝のメールのワークフローの中だけの一時ファイル（リポジトリには入れない・.gitignore）
MAX_AGE_MIN = 180


def load(path=OUT, now=None):
    """一時ファイルを読む（無い・古い・壊れた → None）"""
    import datetime as dt
    try:
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
        made = dt.datetime.fromisoformat(d["generated_at"])
        now = now or dt.datetime.now(made.tzinfo)
        return d if (now - made).total_seconds() <= MAX_AGE_MIN * 60 else None
    except Exception:  # noqa: BLE001
        return None


def main(argv=None):
    """--since-jst H＝今日の日本時間 H 時からの強弱も出す（ロンドン前＝9・NY前＝15）"""
    import datetime as dt
    import sys
    argv = sys.argv[1:] if argv is None else argv
    jst = dt.timezone(dt.timedelta(hours=9))
    since_h = int(argv[argv.index("--since-jst") + 1]) if "--since-jst" in argv else None
    if since_h is None:
        d = compute()
    else:
        now = dt.datetime.now(jst)
        start = now.replace(hour=since_h, minute=0, second=0, microsecond=0)
        d = compute_full(int(start.timestamp()))
        if d is not None:
            d["since_jst"] = since_h
    if d is None:
        print("⚠️ 為替の1時間足を1つも取れなかった＝朝のメールの通貨の強弱は「取れなかった」と書く")
        return 0
    d["generated_at"] = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(timespec="minutes")
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(d, fh, ensure_ascii=False)
    print(f"✅ 通貨の強弱（24時間）：{ranking(d['h24'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
