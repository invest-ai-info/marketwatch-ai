import numpy as np
import pandas as pd
import exit_ind_lab as E


def _x(o, h, l, c, atr=1.0):
    n = len(c)
    nan = np.full(n, np.nan)
    ctx = {"o": np.array(o, float), "h": np.array(h, float), "l": np.array(l, float), "c": np.array(c, float),
           "atr": np.full(n, atr), "n": n, "lines": {k: (nan, nan) for k in ("S1", "S3", "S4", "S5", "S6", "S7")}, "nxt": {}}
    return ctx


def _flat(n=80, px=100.0):
    return [px] * n


def test_fixed_stop_and_target():
    n = 80
    o = _flat(n); h = [100.2] * n; l = [99.8] * n; c = _flat(n)
    x = _x(o, h, l, c)
    e = 10
    # 買い：3本目に安値が損切り(100-1.5=98.5)へ
    l[12] = 98.0
    x["l"] = np.array(l, float)
    se = E.stop_event(x, e, 1.0, 1.0, "S0")
    assert se == (12, 98.5)
    assert abs(E.outcome(x, e, 1.0, 1.0, "S0", "P0") - (-1.0)) < 1e-9


def test_target_first_and_same_bar_stop_first():
    n = 80
    o = _flat(n); h = [100.2] * n; l = [99.8] * n; c = _flat(n)
    h[11] = 102.5                         # 利確(102)に届く
    x = _x(o, h, l, c)
    assert abs(E.outcome(x, 10, 1.0, 1.0, "S0", "P0") - (2.0 / 1.5)) < 1e-9
    l[11] = 98.0                          # 同じ足で損切りにも届く → 損切りが先
    x = _x(o, h, l, c)
    assert abs(E.outcome(x, 10, 1.0, 1.0, "S0", "P0") - (-1.0)) < 1e-9


def test_short_mirror_and_cap():
    n = 80
    o = _flat(n); h = [100.2] * n; l = [99.8] * n; c = [100.0] * n
    c[10 + E.CAP - 1] = 99.0             # 何も起きなければ60本目の終値
    x = _x(o, h, l, c)
    assert abs(E.outcome(x, 10, -1.0, 1.0, "S0", "P7") - (1.0 / 1.5)) < 1e-9
    assert abs(E.outcome(x, 10, 1.0, 1.0, "S0", "P7") - (-1.0 / 1.5)) < 1e-9


def test_indicator_tp_exits_next_open_and_stop_ordering():
    n = 80
    o = _flat(n); h = [100.2] * n; l = [99.8] * n; c = _flat(n)
    o[16] = 101.0
    x = _x(o, h, l, c)
    nx = np.full(n + 1, 10 ** 9, dtype=np.int64); nx[:16] = 15; nx[15:] = 15   # 15本目の終値で合図
    x["nxt"] = {"P1": (nx, nx)}
    x["nxt"]["P1"] = (np.where(np.arange(n + 1) <= 15, 15, 10 ** 9), np.where(np.arange(n + 1) <= 15, 15, 10 ** 9))
    assert E.tp_event(x, 10, 1.0, 1.0, "P1") == (15, 101.0)
    assert abs(E.outcome(x, 10, 1.0, 1.0, "S0", "P1") - (1.0 / 1.5)) < 1e-9
    l[15] = 98.0                          # 合図の足の中で損切り → 損切りが先
    x["l"] = np.array(l, float)
    assert abs(E.outcome(x, 10, 1.0, 1.0, "S0", "P1") - (-1.0)) < 1e-9


def test_line_stop_is_clipped_and_ratchets():
    n = 80
    o = _flat(n); h = [100.2] * n; l = [99.8] * n; c = _flat(n)
    x = _x(o, h, l, c)
    line = np.full(n, 90.0)               # 遠すぎる線 → 4ATR(96)へ収める
    x["lines"]["S1"] = (line, line)
    l[13] = 95.5
    x["l"] = np.array(l, float)
    assert E.stop_event(x, 10, 1.0, 1.0, "S1") == (13, 96.0)
