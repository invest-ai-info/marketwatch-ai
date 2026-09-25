# -*- coding: utf-8 -*-
"""lab_forward.py — 研究ラボの「前向きの確かめ」を週ごとに積み上げる共通部品（2026-09-26 新設）。

オーナー指示「4つとも登録して前向きに検証して」。出口の壁ラボ（exit_wall_lab.py）・損切りラボ（stop_lab.py）が使う。
考え方は研究日誌のトラッカー・出口の相性ラボの前向き（exit_lab.fwd_check）と同じ:
  ・登録日（FWD_FROM）以降に入った取引だけで数える＝定義上、探索に使っていないデータ。
  ・件数が min_n（100）の倍数を新しく越えたときだけ判定する（毎週のぞき見して「たまたま越えた週」で決めない）。
  ・判定＝95%幅が0をまたがず探索と同じ向き、かつ差が min_eff（0.10R）以上 → 「合格」。0をまたがず逆向き → 「逆向き」。
    それ以外 → 「まだ判断できない」。
  ・**合格が2回続けて**はじめて「確かめられた」。逆向きは1回で「前向きでは逆向き」（保守側）。
前回までの判定は、前回の出力 JSON（同じファイル）の history から引き継ぐ＝台帳を別に持たない。
"""
import json
import os

import pandas as pd

FWD_FROM = pd.Timestamp("2026-09-26")   # 登録日（この日以降に入った取引が前向き）
MIN_N = 100
MIN_EFF = 0.10


def fwd_cluster(t):
    """前向きは期間が短い＝時期を年ではなく年月で区切る（exit_rule_backtest.forward_clusters と同じ）。"""
    return (t["ticker"], (t["time"].year, t["time"].month))


def load_prev(path):
    """前回の出力の forward（無ければ {}）。"""
    try:
        with open(path, encoding="utf-8") as f:
            return (json.load(f) or {}).get("forward") or {}
    except (OSError, ValueError):
        return {}


def verdict(d, is_sign, min_eff=MIN_EFF):
    if not d or "lo" not in d or d.get("avg") is None:
        return "undecided"
    same = (d["lo"] > 0) if is_sign > 0 else (d["hi"] < 0)
    opposite = (d["hi"] < 0) if is_sign > 0 else (d["lo"] > 0)
    if same and abs(d["avg"]) >= min_eff:
        return "pass"
    if opposite:
        return "opposite"
    return "undecided"


STATE_LABEL = {"pass": "🟢合格（2回続けば確定）", "opposite": "⛔前向きでは逆向き", "undecided": "⚪まだ判断できない"}


def step(prev_entry, d, is_sign, today, min_n=MIN_N, min_eff=MIN_EFF):
    """1つの仮説の今週の状態。prev_entry＝前回の forward[key]（history を持つ）。戻り値＝新しい forward[key]。"""
    hist = list((prev_entry or {}).get("history") or [])
    n = d.get("n", 0) if d else 0
    last_cp = hist[-1]["cp"] if hist else 0
    cp = n // min_n
    if cp >= 1 and cp > last_cp:
        hist.append({"date": today, "cp": cp, "n": n, "avg": d.get("avg"), "lo": d.get("lo"), "hi": d.get("hi"),
                     "verdict": verdict(d, is_sign, min_eff)})
    if n < min_n and not hist:
        state = "🟡蓄積中"
    elif hist and hist[-1]["verdict"] == "opposite":
        state = STATE_LABEL["opposite"]
    elif len(hist) >= 2 and hist[-1]["verdict"] == "pass" and hist[-2]["verdict"] == "pass":
        state = "✅確かめられた（合格2回連続）"
    elif hist:
        state = STATE_LABEL[hist[-1]["verdict"]]
    else:
        state = "🟡蓄積中"
    return {"n": n, "now": d, "state": state, "history": hist, "min_n": min_n, "is_sign": is_sign}


def split(ts):
    """探索（登録日より前）と前向き（登録日以降）に分ける。"""
    return [t for t in ts if t["time"] < FWD_FROM], [t for t in ts if t["time"] >= FWD_FROM]


def default_path(path):
    return path if path and os.path.exists(path) else None
