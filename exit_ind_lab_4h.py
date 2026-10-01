# -*- coding: utf-8 -*-
"""M7 腕A：4時間足で E1 と同じ総当たり（入口60 × 出口64 ＝ 3,840通り・監視18銘柄・時間帯の縛りなし）。

2026-10-01 登録＝PILLAR_PREREG.md「M7」（オーナー「同じ条件で4時間足と日足で検証することはできますか…時間帯の縛りはなしで」）。
日足は E1（exit-ind-lab）で数え済み＝ここでは数えない。

E1（exit_ind_lab.py）の関数を読むだけ。違うのは次の3つだけ:
  ① 足＝Yahoo の1時間足（過去730日）を UTC で4時間ごとに束ねる（始値＝最初・高値＝最大・安値＝最小・終値＝最後）
  ② 前半・後半の区切り＝2025-10-01（取れた730日のほぼ真ん中）
  ③ 幅のまとまり＝銘柄×月（E1 は銘柄×年。確かめが1年しか無いため）
⚠️ 入口・出口・1R・費用・選び方・確かめ方・偽薬は E1 と同じ。結果を見てから動かさない。出力は GitHub 側生成＝手元から送らない。

実行: python exit_ind_lab_4h.py   （exit-ind-lab-4h.yml・手動・1回だけ）
"""
import datetime as dt
import json
import sys

import pandas as pd

import combo_lab as CL
import exit_ind_lab as E
import pillar_lab as P
import screen_judge as J
import trend_lab as TL

OUT_JSON, OUT_MD = "exit-ind-lab-4h.json", "exit-ind-lab-4h.md"
SPLIT_4H = "2025-10-01"
SECTION = "## M7 "
TITLE = "4時間足で同じ総当たり M7・腕A（損切り8 × 利確8 × 入口60・時間帯の縛りなし）"
AGG = {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}


def to_4h(df):
    """1時間足（添字は UTC）→ 4時間足。0・4・8・12・16・20時 UTC で区切る（generate_technical_alerts と同じ）"""
    if df is None or len(df) == 0:
        return None
    cols = {k: v for k, v in AGG.items() if k in df.columns}
    out = df.resample("4h").agg(cols).dropna(subset=["Open", "High", "Low", "Close"])
    return out if len(out) else None


def load_4h(tk):
    return to_4h(P.fetch(tk, "1h"))


def confirm_stats_month(xs, vals):
    """幅のまとまり＝銘柄×月（E1 は銘柄×年）"""
    groups = [(e["ticker"], e["date"][:7]) for e in xs]
    return P.mean_ci(vals, groups)


def run(n_perm=E.N_PERM, loader=load_4h):
    """E1 の run を、区切り・まとまり・足だけ差し替えて1回呼ぶ（呼んだあと元に戻す）"""
    keep_split, keep_cs = E.SPLIT, CL.confirm_stats
    E.SPLIT, CL.confirm_stats = SPLIT_4H, confirm_stats_month
    try:
        return E.run(n_perm=n_perm, loader=loader)
    finally:
        E.SPLIT, CL.confirm_stats = keep_split, keep_cs


def main():
    res = {"generated_at": dt.datetime.now(P.JST).isoformat(timespec="minutes"), "prereg_file": P.PREREG,
           "prereg_sha256": P.prereg_sha256(), "section_sha256": J.section_sha256(head=SECTION),
           "timeframe": "4h", "split": SPLIT_4H, "cluster": "ticker×month", "warmup_bars": TL.WARMUP}
    try:
        res["result"] = run()
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        res["result"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1, default=str)
    md = E.render_md(res, title=TITLE, section="M7", front=f"{SPLIT_4H} より前", back=f"{SPLIT_4H} から")
    md = md.replace("※ 研究の記録です。", "- 足＝Yahoo の1時間足（過去730日）を4時間ごとに束ねたもの・費用はサイトの仮の値（実スプレッドではない）・幅のまとまりは銘柄×月\n\n※ 研究の記録です。")
    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
