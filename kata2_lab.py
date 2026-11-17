# -*- coding: utf-8 -*-
"""KT2 オーナーの型1（一気版）：KT1 に「ブレイクから最安値（最高値）まで、途中で押し目をつけずに一気に」を足す。
2026-11-17 夜 登録・PILLAR_PREREG.md「KT2」。KT1 から変えるのは入り方（scan_entry）の1か所だけ。

決まりの要点（全文は PILLAR_PREREG.md「KT2」）:
- 一気の間＝合図の足の次の足から。入るペアの5分足に陽線が2本続いたら「押し目をつけた」（買いは陰線2本）。陽線＝終値＞始値
- 押し目をつける前に安値を更新したら、最安値・50%・30分をずらす（KT1 と同じ）
- 押し目をつけたあと、50% に届く前に最安値を下に更新したら、そのペアはその日入らない
- それ以外（線・窓・合図・20 pips・60 pips・30分・1/3 と 2/3・出方・荒れすぎの日・発表・腕・判定・偽薬・データ）は KT1 と同じ

KT1 の道具 kata1_lab.py を「別の写し」として読み込み、その写しの入り方の関数と名前だけを差し替える
（import kata1_lab の本体には触れない＝KT1 の道具と結果は変わらない・同じ回に両方のテストを動かしても混ざらない）。

使い方（手元・KT1 と同じデータ）:
  python kata2_lab.py check --dir C:\\mt5run --duka C:\\mt5run\\duka_fx   （足・線・合図・入れた数だけ。損益は数えない・何も書き出さない）
  python kata2_lab.py run   --dir C:\\mt5run --duka C:\\mt5run\\duka_fx   （本番・1回だけ → kata2-lab.json（送る）・research/oikawa/kata2-result.md と取引の CSV（手元））
⚠️ 研究の記録。投資助言ではない。過去のデータの集計で、これからの成績を約束しない。
"""
import importlib.util
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

_spec = importlib.util.spec_from_file_location("_kata1_for_kt2", os.path.join(HERE, "kata1_lab.py"))
K = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(K)

PUSH_BARS = 2                              # 陽線（買いは陰線）が2本続いたら押し目


def scan_entry(D, p, s, k_sig, line, w1, b, E, gate=None):
    """1発目を探す（KT2）。→ dict（位置・値段・目標＝最安値・幅 pips・待った分）か None。
    KT1 の scan_entry に「押し目（陽線2本）のあとに最安値を更新したら見送り」を足しただけ"""
    P, T, mn = D["P"][p], D["T"], D["minute"]
    pp = K.pip(p)
    if not np.isfinite(P["l"][k_sig]):
        return None
    ext = P["l"][k_sig] if s < 0 else P["h"][k_sig]
    t_ext = T[k_sig]
    run = 0                                # 押し目の向きの足（売りは陽線）が続いた本数
    pushed = False                         # 押し目をつけたか
    for k in range(k_sig + 1, b):
        if mn[k] > w1:
            return None
        if not np.isfinite(P["o"][k]):
            continue
        if T[k] - t_ext > K.WAIT_MIN * K.MIN:
            return None
        l50 = (line + ext) / 2.0
        dist = (line - ext) / pp if s < 0 else (ext - line) / pp
        ok_gate = gate is None or gate(k)
        if dist >= K.MIN_PIPS and ok_gate and not K.event_blocked(E, T[k]):
            if s < 0 and P["h"][k] >= l50:
                return {"k": k, "price": max(l50, P["o"][k]), "target": ext, "dist": dist, "wait": (T[k] - t_ext) / K.MIN}
            if s > 0:
                ask_o = P["o"][k] + P["so"][k]
                if P["l"][k] + P["so"][k] <= l50:
                    return {"k": k, "price": min(l50, ask_o), "target": ext, "dist": dist, "wait": (T[k] - t_ext) / K.MIN}
        lo, hi = P["l"][k], P["h"][k]
        newer = (s < 0 and lo < ext) or (s > 0 and hi > ext)
        if newer:
            if pushed:
                return None                # 押し目のあとに最安値（最高値）を更新＝一気ではない → 見送り
            ext, t_ext = (lo, T[k]) if s < 0 else (hi, T[k])
        o_, c_ = P["o"][k], P["c"][k]
        against = (c_ > o_) if s < 0 else (c_ < o_)
        run = run + 1 if against else 0
        if run >= PUSH_BARS:
            pushed = True
    return None


# ── 写しの中の名前と入り方を差し替える（PILLAR_PREREG.md「KT2」） ──
K.scan_entry = scan_entry
K.TAG = "KT2"
K.HEADING = "KT2 オーナーの型1（一気版）：ブレイクから最安値（最高値）まで押し目をつけずに一気に動いた日だけ、戻りの 50% と線で分けて入る"
K.SECTION = "## KT2 オーナーの型1（一気版）"
K.OUT_JSON = "kata2-lab.json"
K.OUT_MD = os.path.join("research", "oikawa", "kata2-result.md")
K.OUT_CSV = os.path.join("research", "oikawa", "kata2-{}.csv")
K.TITLES = {"KT2-A": "オーナーの型1（一気版・決めたとおり）：クロス円3つがそろって東京時間の最安値（最高値）を割り、押し目（陽線2本）をつけずに一気に最安値まで動いたら、"
                     "線と最安値の50%で1/3・線で2/3。16時以降はユーロポンドの向きで1ペア（5分足・ロンドン時間の前後3時間・過去のデータ・1回だけ・手元の MT5 と Dukascopy）",
            "KT2-B": "オーナーの型1（一気版・いつも3等分）：同じ合図と一気の条件で、ドル円・ポンド円・ユーロ円に3等分して入る"
                     "（5分足・ロンドン時間の前後3時間・過去のデータ・1回だけ・手元の MT5 と Dukascopy）"}

main = K.main

if __name__ == "__main__":
    sys.exit(main())
