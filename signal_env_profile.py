# -*- coding: utf-8 -*-
"""signal_env_profile.py — テクニカルのシグナルが「効いたとき」「効かなかったとき」、どんな環境だったか。2026-09-26 新設。

オーナー依頼「過去のシグナル研究で、テクニカル指標が効いたときどんな環境だったか、効かなかったときどんな環境だったか、
という統計を取ってほしい」。実際に出たシグナル（signals-log.json）だけを使う＝バックテストではない。

━━ 事前に決めたルール（結果を見る前に固定・以後変えない） ━━
対象   : 決着したシグナル（tp1/tp2＝効いた、sl＝効かなかった）。期限切れ・計画なし・後付けの記録（pseudo_record）は除く。
損益   : 効いた＝tp1_pct/|sl_pct|（おおむね +1.33R）、効かなかった＝−1R。主な物差しは「勝率」、補助に損益（R）。
環境   : 発火した時点で記録された項目だけ（結果のあとに付けた敗因・勝因の分析は後出しなので使わない）。
         18項目・下の DIMS の区分（区分の境目も事前に固定。VIX・ADX・ニュース数は研究日誌の固定オラクルと同じ）。
公平さ : シグナルの種類（時間足 × 順張り/逆張り/その他 × 買い/売り × 資産クラス）ごとに、もともとの勝率が違う。
         各シグナルの「同じ種類の平均勝率」を引いた残り（超過勝率）で比べる＝環境の偏りと種類の偏りを混ぜない。
幅     : 同じ日のシグナルは環境を共有し、同じ銘柄も続けて出る。銘柄 × 日の二方向のまとまりで、安全側の出し方
         （exit_rule_backtest._mean_se_safe と同じ式）で標準誤差を出す。
判定   : 「確かめられた」＝①区分の数で割った厳しい基準（ボンフェローニ補正・両側 5%）で 0 を否定 ②差が 5 ポイント以上
         ③期間を前半・後半に分けて同じ向き、の3つすべて。
         「傾向あり（まだ偶然の可能性）」＝ふつうの 95% の幅で 0 を否定し差が 5 ポイント以上だが、①か③を満たさない。
         区分が約50あるので、何も差が無くても「傾向あり」は偶然で 2〜3 個は出る（5%×区分数）。
         それ以外＝差なし。どの区分も件数 40 未満は判定しない。
副次   : 順張り・逆張りに分けた同じ表（主張には使わず、読むための表）。

使い方:  python signal_env_profile.py            → signal-env-profile.md / .json を書く
"""
import collections
import datetime
import json
import math
import sys

import numpy as np

import signal_lab_verify as V

MIN_N = 40
MIN_EFF = 0.05        # 5 ポイント
ALPHA = 0.05
JST = datetime.timezone(datetime.timedelta(hours=9))
WEEKDAY = ["月", "火", "水", "木", "金", "土", "日"]


def g(d, *path):
    v = d
    for k in path:
        v = v.get(k) if isinstance(v, dict) else None
    return v


def num(x):
    return x if isinstance(x, (int, float)) and not isinstance(x, bool) else None


def fired_jst(d):
    try:
        return datetime.datetime.fromisoformat(d["fired_at"]).astimezone(JST)
    except (KeyError, ValueError, TypeError):
        return None


def session_of(d):
    t = fired_jst(d)
    if t is None:
        return None
    h = t.hour
    if 8 <= h < 15:
        return "東京（8〜15時）"
    if 15 <= h < 21:
        return "欧州（15〜21時）"
    if h >= 21 or h < 3:
        return "米国（21〜翌3時）"
    return "早朝（3〜8時）"


def vix24_of(d):
    c = num(g(d, "environment", "vix", "change_24h_pct"))
    if c is None:
        return None
    return "上昇（+5%超）" if c > 5 else ("低下（−5%超）" if c < -5 else "横ばい")


def atr_of(d):
    r = g(d, "environment", "atr_regime", "regime")
    if r is None:
        return None
    return "平常" if r == "normal" else "荒い（平常より大）"


def env_of(d):
    s = g(d, "environment", "env_score")
    if s is None:
        return None
    return {"A": "A（平穏）", "B": "B（警戒）"}.get(s, "C・D（危険）")


def tf_trend_of(d):
    t = g(d, "trend_alignment", "higher_tf_trend")
    return {"上昇": "上昇", "下降": "下降", "中立・もみあい": "もみあい"}.get(t)


def aligned_of(d):
    a = g(d, "trend_alignment", "aligned")
    return None if a is None else ("上位足と同じ向き" if a else "上位足と逆向き")


def bool_label(v, yes, no):
    return None if v is None else (yes if v else no)


# (キー, 見出し, 区分の関数, 区分の並び順)
DIMS = [
    # ── 市場全体の環境
    ("env", "環境警戒スコア", env_of, ["A（平穏）", "B（警戒）", "C・D（危険）"]),
    ("vix", "VIX（恐怖指数）の水準", lambda d: {"low": "15未満", "mid": "15〜25", "high": "25以上"}.get(V.vix_band_of(d)),
     ["15未満", "15〜25", "25以上"]),
    ("vix24", "VIX の前日比", vix24_of, ["低下（−5%超）", "横ばい", "上昇（+5%超）"]),
    ("risk", "リスクオン・オフ（相場の地合い）", lambda d: g(d, "risk_regime", "regime"), ["RISK_ON", "NEUTRAL", "RISK_OFF"]),
    ("fund", "ファンダの地合い（朝夕のブリーフィング）", lambda d: g(d, "fundamental_context", "regime"),
     ["RISK_ON", "NEUTRAL", "RISK_OFF"]),
    ("event", "24時間以内の重要指標", lambda d: bool_label(bool(g(d, "environment", "upcoming_events")) if g(d, "environment") else None,
                                                  "あり", "なし"), ["なし", "あり"]),
    ("crisis", "危機キーワードのニュース", lambda d: bool_label((num(g(d, "environment", "crisis_news", "hit_count")) or 0) > 0
                                                     if g(d, "environment") else None, "あり", "なし"), ["なし", "あり"]),
    ("news", "その銘柄のニュースの数", lambda d: {"0": "0件", "1-2": "1〜2件", "3+": "3件以上"}.get(V.news_band_of(d)),
     ["0件", "1〜2件", "3件以上"]),
    ("weekday", "曜日（日本時間）", lambda d: (lambda t: None if t is None else WEEKDAY[t.weekday()] if t.weekday() < 5 else "土日")(fired_jst(d)),
     ["月", "火", "水", "木", "金", "土日"]),
    ("session", "時間帯（日本時間）", session_of, ["東京（8〜15時）", "欧州（15〜21時）", "米国（21〜翌3時）", "早朝（3〜8時）"]),
    # ── 銘柄の状態
    ("atr", "値動きの荒さ（ATR が30日平均と比べて）", atr_of, ["平常", "荒い（平常より大）"]),
    ("adx", "トレンドの強さ（ADX）", lambda d: {"weak": "弱い（20未満）", "mid": "中（20〜25）", "strong": "強い（25以上）"}.get(V.adx_band_of(d)),
     ["弱い（20未満）", "中（20〜25）", "強い（25以上）"]),
    ("htf", "上位足のトレンド", tf_trend_of, ["上昇", "もみあい", "下降"]),
    ("aligned", "シグナルの向きと上位足", aligned_of, ["上位足と同じ向き", "上位足と逆向き"]),
    ("shape", "相場の形（選別の判定）", lambda d: {"trend_up": "上昇トレンド", "trend_down": "下降トレンド", "range": "もみあい"}.get(
        g(d, "selection", "regime")), ["上昇トレンド", "もみあい", "下降トレンド"]),
    ("wall", "近くの抵抗線・支持線（行く手の壁）", lambda d: bool_label(g(d, "sr_runway", "blocked"), "壁が近い", "壁が遠い"),
     ["壁が遠い", "壁が近い"]),
    ("rev", "直前の逆向きシグナル（往復ビンタ）", lambda d: bool_label(g(d, "whipsaw_check", "is_reversal"), "あり", "なし"),
     ["なし", "あり"]),
    ("fbias", "ファンダの向きとシグナルの向き", lambda d: bool_label(g(d, "fundamental_context", "bias_aligned"), "一致", "不一致"),
     ["一致", "不一致"]),
]


# ── t 分布（scipy なし）: 正則化不完全ベータ関数（連分数）で片側確率→二分法で臨界値
def _betacf(a, b, x):
    qab, qap, qam = a + b, a + 1, a - 1
    c, d = 1.0, 1 - qab * x / qap
    d = 1 / (d if abs(d) > 1e-30 else 1e-30)
    h = d
    for m in range(1, 300):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1 + aa * d
        d = 1 / (d if abs(d) > 1e-30 else 1e-30)
        c = 1 + aa / c if abs(c) > 1e-30 else 1 + aa / 1e-30
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1 + aa * d
        d = 1 / (d if abs(d) > 1e-30 else 1e-30)
        c = 1 + aa / c if abs(c) > 1e-30 else 1 + aa / 1e-30
        de = d * c
        h *= de
        if abs(de - 1) < 1e-12:
            break
    return h


def _betai(a, b, x):
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    lb = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x)
    if x < (a + 1) / (a + b + 2):
        return math.exp(lb) * _betacf(a, b, x) / a
    return 1 - math.exp(lb) * _betacf(b, a, 1 - x) / b


def t_two_sided_p(t, df):
    return _betai(df / 2, 0.5, df / (df + t * t))


def t_crit(alpha_two, df):
    lo, hi = 0.0, 1000.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if t_two_sided_p(mid, df) > alpha_two:
            lo = mid
        else:
            hi = mid
    return hi


def mean_se_safe(vals, groups):
    """exit_rule_backtest._mean_se_safe と同じ式（二方向のまとまり・4つのうち最大の分散）。戻り値: 平均・標準誤差・自由度。"""
    a = np.array(vals, float)
    n, m = len(a), float(a.mean())
    if n < 2:
        return m, float("inf"), 1
    e = a - m

    def ss(keyf):
        sums = {}
        for x, gg in zip(e, groups):
            k = keyf(gg)
            sums[k] = sums.get(k, 0.0) + x
        return sum(v * v for v in sums.values()), len(sums)

    s1, g1 = ss(lambda gg: gg[0])
    s2, g2 = ss(lambda gg: gg[1])
    s12, _ = ss(lambda gg: gg)
    v = max(s1 + s2 - s12, s1, s2, s12)
    G = min(g1, g2)
    if G < 2:
        return m, float("inf"), 1
    return m, math.sqrt(v * G / (G - 1)) / n, G - 1


def load(path="signals-log.json"):
    recs = json.load(open(path, encoding="utf-8"))
    out = []
    for d in recs:
        if d.get("pseudo_record") or d.get("outcome") not in ("tp1", "tp2", "sl"):
            continue
        t = fired_jst(d)
        if t is None:
            continue
        side = "long" if "ロング" in (d.get("direction") or "") else ("short" if "ショート" in (d.get("direction") or "") else "?")
        w = 1 if d["outcome"] in ("tp1", "tp2") else 0
        sl, tp = num(d.get("sl_pct")), num(d.get("tp1_pct"))
        r = (abs(tp / sl) if (sl and tp) else 4 / 3) if w else -1.0
        stratum = (d.get("timeframe"), V.family_of(d) or "other", side, V.asset_class_of(d) or "other")
        out.append({"d": d, "win": w, "r": r, "stratum": stratum, "ticker": d.get("ticker"),
                    "date": t.date().isoformat(), "fam": V.family_of(d) or "other"})
    base = collections.defaultdict(list)
    for x in out:
        base[x["stratum"]].append(x)
    for s, xs in base.items():
        pw, pr = sum(y["win"] for y in xs) / len(xs), sum(y["r"] for y in xs) / len(xs)
        for y in xs:
            y["xw"], y["xr"] = y["win"] - pw, y["r"] - pr
    return out


def analyze(rows, K, tag=""):
    dates = sorted({x["date"] for x in rows})
    mid = dates[len(dates) // 2] if dates else ""
    res = []
    n_win = sum(x["win"] for x in rows)
    n_loss = len(rows) - n_win
    for key, title, fn, order in DIMS:
        lab = [(fn(x["d"]), x) for x in rows]
        known = [(b, x) for b, x in lab if b is not None]
        wins = collections.Counter(b for b, x in known if x["win"])
        losses = collections.Counter(b for b, x in known if not x["win"])
        tw, tl = sum(wins.values()), sum(losses.values())
        buckets = []
        for b in order:
            xs = [x for bb, x in known if bb == b]
            n = len(xs)
            item = {"bucket": b, "n": n, "win_share": wins[b] / tw if tw else None,
                    "loss_share": losses[b] / tl if tl else None}
            if n >= 2:
                item["raw_winrate"] = sum(x["win"] for x in xs) / n
                item["avg_r"] = sum(x["r"] for x in xs) / n
            if n >= MIN_N:
                m, se, df = mean_se_safe([x["xw"] for x in xs], [(x["ticker"], x["date"]) for x in xs])
                mr, ser, _ = mean_se_safe([x["xr"] for x in xs], [(x["ticker"], x["date"]) for x in xs])
                h1 = [x["xw"] for x in xs if x["date"] < mid]
                h2 = [x["xw"] for x in xs if x["date"] >= mid]
                a1 = sum(h1) / len(h1) if h1 else None
                a2 = sum(h2) / len(h2) if h2 else None
                t95 = t_crit(ALPHA, df)
                tb = t_crit(ALPHA / K, df)
                lo, hi = m - t95 * se, m + t95 * se
                same = a1 is not None and a2 is not None and (a1 > 0) == (a2 > 0) == (m > 0)
                strict = abs(m) - tb * se > 0
                nominal = lo > 0 or hi < 0
                big = abs(m) >= MIN_EFF
                if strict and big and same:
                    verdict = "確かめられた・効きやすい" if m > 0 else "確かめられた・効きにくい"
                elif nominal and big:
                    verdict = "傾向あり（まだ偶然の可能性）・" + ("効きやすい側" if m > 0 else "効きにくい側")
                else:
                    verdict = "差なし"
                item.update(excess=m, se=se, lo=lo, hi=hi, df=df, half1=a1, half2=a2, excess_r=mr, se_r=ser,
                            verdict=verdict, strict=strict, same_dir=same)
            else:
                item["verdict"] = "件数不足（判定しない）"
            buckets.append(item)
        res.append({"key": key, "title": title, "coverage": len(known), "buckets": buckets})
    return {"n": len(rows), "n_win": n_win, "n_loss": n_loss, "dims": res, "split_date": mid, "tag": tag}


def pct(x, sign=False):
    if x is None:
        return "—"
    return f"{x * 100:+.1f}" if sign else f"{x * 100:.1f}"


def render(main, fams, K, meta):
    L = [f"# シグナルが「効いたとき」「効かなかったとき」の環境（{meta['asof']} 時点）", "",
         "オーナー依頼「テクニカル指標が効いたとき・効かなかったとき、どんな環境だったか」。実際に出たシグナルの記録"
         "（signals-log.json）だけで数えた。ルールは `signal_env_profile.py` の冒頭に、結果を見る前に固定してある。", "",
         f"- 対象: 決着したシグナル **{main['n']:,}件**（効いた＝利確 {main['n_win']:,}件・効かなかった＝損切り {main['n_loss']:,}件）。"
         f"期間 {meta['first']}〜{meta['last']}。期限切れ・計画なしは除外（{meta['excluded']:,}件）",
         f"- 全体の勝率 {main['n_win'] / main['n'] * 100:.1f}%。判定した区分の数 {K}（厳しい基準＝両側 {ALPHA / K * 100:.2f}%）。"
         f"前半・後半の境目 {main['split_date']}",
         "- **超過勝率**＝同じ種類のシグナル（時間足・順張り/逆張り・買い/売り・資産クラス）の平均勝率と比べて何ポイント上か下か。"
         "種類の偏りを取り除いた「環境だけの差」", ""]
    verdicts = [(dm, b) for dm in main["dims"] for b in dm["buckets"] if b.get("verdict", "").startswith(("確かめられた", "傾向あり"))]
    L += ["## 結論", ""]
    conf = [(dm, b) for dm, b in verdicts if b["verdict"].startswith("確かめられた")]
    tend = [(dm, b) for dm, b in verdicts if b["verdict"].startswith("傾向あり")]
    if conf:
        for dm, b in conf:
            L.append(f"- ✅ **{dm['title']}＝{b['bucket']}**：超過勝率 {pct(b['excess'], True)} ポイント"
                     f"（95%の幅 {pct(b['lo'], True)}〜{pct(b['hi'], True)}・{b['n']:,}件）→ {b['verdict']}")
    else:
        L.append("- ✅ 厳しい基準をすべて満たした区分（確かめられた）：**なし**")
    L.append(f"- 🟡 傾向あり（まだ偶然の可能性）：{len(tend)} 区分（何も差が無くても偶然で 2〜3 区分は出る数）")
    for dm, b in tend:
        L.append(f"  - {dm['title']}＝{b['bucket']}：{pct(b['excess'], True)} ポイント（{pct(b['lo'], True)}〜{pct(b['hi'], True)}・"
                 f"{b['n']:,}件・前半 {pct(b['half1'], True)}／後半 {pct(b['half2'], True)}）")
    L += ["", "## 項目ごとの表", "",
          "「効いた中の割合」「効かなかった中の割合」＝効いたシグナル（または効かなかったシグナル）のうち、その環境だった割合。"
          "両者が近ければ、その環境は勝ち負けと関係が薄い。", ""]
    for dm in main["dims"]:
        L += [f"### {dm['title']}（記録あり {dm['coverage']:,}件）", "",
              "| 区分 | 件数 | 効いた中の割合 | 効かなかった中の割合 | 勝率 | 超過勝率（95%の幅） | 前半／後半 | 判定 |",
              "|---|---:|---:|---:|---:|---|---|---|"]
        for b in dm["buckets"]:
            ex = (f"{pct(b['excess'], True)}（{pct(b['lo'], True)}〜{pct(b['hi'], True)}）" if "excess" in b else "—")
            hh = f"{pct(b.get('half1'), True)}／{pct(b.get('half2'), True)}" if "excess" in b else "—"
            L.append(f"| {b['bucket']} | {b['n']:,} | {pct(b['win_share'])}% | {pct(b['loss_share'])}% | "
                     f"{pct(b.get('raw_winrate'))}% | {ex} | {hh} | {b['verdict']} |")
        L.append("")
    L += ["## 副次の表：順張り・逆張りに分けた場合（読むための表・主張には使わない）", ""]
    for name, res in fams:
        L += [f"### {name}（{res['n']:,}件・勝率 {res['n_win'] / max(res['n'], 1) * 100:.1f}%）", "",
              "| 項目 | 区分 | 件数 | 超過勝率（95%の幅） | 判定 |", "|---|---|---:|---|---|"]
        for dm in res["dims"]:
            for b in dm["buckets"]:
                if b.get("verdict", "").startswith(("確かめられた", "傾向あり")):
                    L.append(f"| {dm['title']} | {b['bucket']} | {b['n']:,} | {pct(b['excess'], True)}"
                             f"（{pct(b['lo'], True)}〜{pct(b['hi'], True)}） | {b['verdict']} |")
        L.append("")
    L += ["## 読むときの注意", "",
          "- 期間は約4か月。この間に無かった相場（たとえば長い暴落）での振る舞いはわからない。",
          "- 「環境」と「結果」が同時に起きているだけで、環境が原因とは限らない。確かめられた区分も、使う前に前向き（これから出る"
          "シグナル）で確かめる。",
          "- 同じ種類のシグナルの平均と比べているので、「その環境では逆張りが多く出た」ような種類の偏りは差に入らない。",
          "- これは情報の整理であり、売買を勧めるものではない。"]
    return "\n".join(L) + "\n"


def main():
    rows = load()
    recs = json.load(open("signals-log.json", encoding="utf-8"))
    K = sum(len(o) for _k, _t, _f, o in DIMS)
    meta = {"asof": datetime.datetime.now(JST).strftime("%Y-%m-%d %H:%M"),
            "first": min(x["date"] for x in rows), "last": max(x["date"] for x in rows),
            "excluded": len(recs) - len(rows)}
    res = analyze(rows, K)
    fams = [("順張り（高値・安値ブレイク／MACD・移動平均の交差）", analyze([x for x in rows if x["fam"] == "tf"], K)),
            ("逆張り（RSI 売られすぎ反発／ボリンジャー下限タッチ）", analyze([x for x in rows if x["fam"] == "mr"], K))]
    md = render(res, fams, K, meta)
    open("signal-env-profile.md", "w", encoding="utf-8").write(md)
    json.dump({"meta": meta, "K": K, "main": res, "families": {n: r for n, r in fams}},
              open("signal-env-profile.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
