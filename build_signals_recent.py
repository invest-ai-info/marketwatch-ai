# -*- coding: utf-8 -*-
"""4時間足の直近の合図の小さな写し（signals-recent.json）を作る（2026-09-30 AT3・PILLAR_PREREG.md「AT」）。

手元の ea_bridge.py が5分ごとに合図を取りに来る。signals-log.json は約40MB あるので、直近7日の4時間足だけを写して小さくする。
⚠️ エンジン・発火条件には触れない。signals-log.json の一部を写すだけ。
⚠️ 失敗しても technical-alerts を止めない（ワークフロー側で `|| true`）。GitHub 側で生成＝手元から送らない（SYNC禁忌）。

実行: python build_signals_recent.py
"""
import datetime as dt
import json
import sys

SRC, OUT = "signals-log.json", "signals-recent.json"
KEEP_DAYS = 7
TF = "4h"
FIELDS = ("id", "fired_at", "timeframe", "ticker", "primary_signal", "entry", "stop_loss", "take_profit_1",
          "take_profit_2", "atr", "email_sent", "watch_hit", "promoted_hit", "outcome")


def direction(text):
    """「ロング（買い）」→ +1、「ショート（売り）」→ −1、それ以外 → None"""
    t = str(text or "")
    if "ロング" in t or "買い" in t:
        return 1
    if "ショート" in t or "売り" in t:
        return -1
    return None


def build(signals, now):
    since = now - dt.timedelta(days=KEEP_DAYS)
    out = []
    for s in signals:
        if s.get("timeframe") != TF:
            continue
        d = direction(s.get("direction"))
        if d is None:
            continue
        try:
            t = dt.datetime.fromisoformat(str(s.get("fired_at")))
        except ValueError:
            continue
        if t.tzinfo is None or t < since:
            continue
        row = {k: s.get(k) for k in FIELDS}
        row["dir"] = d
        out.append(row)
    return sorted(out, key=lambda x: x["fired_at"])


def main():
    now = dt.datetime.now(dt.timezone.utc)
    with open(SRC, encoding="utf-8") as fh:
        signals = json.load(fh)
    rows = build(signals, now)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump({"generated_utc": now.isoformat(timespec="seconds"), "keep_days": KEEP_DAYS, "timeframe": TF,
                   "signals": rows}, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print(f"signals-recent.json: {len(rows)} 件（直近{KEEP_DAYS}日・{TF}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
