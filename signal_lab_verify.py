# -*- coding: utf-8 -*-
"""
signal_lab_verify.py — 研究日誌の数字を「固定コード」でライブ signals-log から独立再計算し、
記事下書きHTMLの主張値と突合する自動公開ゲート（決定論・LLM判断ゼロ）。

使い方:
    python signal_lab_verify.py drafts/draft-signal-lab-004.html drafts/labnotes/lab-004-claims.json
    （signals-log.json はリポジトリ直下を読む）

claims.json スキーマ:
{
  "article_id": "004",
  "claims": [
    {"label": "GC=F long",          "filter": {"ticker":"GC=F","direction":"long"},               "k":6,  "n":47},
    {"label": "GC=F long downtrend","filter": {"ticker":"GC=F","direction":"long","trend":"下降"}, "k":5,  "n":42},
    {"label": "other_fx reversalL",  "filter": {"group":"other_fx","reversal_long":true},           "k":33, "n":60}
  ]
}

filter のキー（全てAND・省略可）:
  ticker     : 単一ティッカー（例 "GC=F"）
  group      : metal/index/jpy_fx/other_fx/btc/oil/all
  direction  : long/short/any
  trend      : 下降 / 中立・もみあい / 上昇 / unknown
  tf         : 1h / 4h / 1d
  signal     : primary_signal の完全一致（例 "bb_lower_touch"）
  reversal_long : true なら direction=long かつ primary_signal∈{rsi_oversold_bounce,bb_lower_touch}
  blocked    : true/false — sr_runway.blocked の値でフィルタ（sr_runway 無しは除外）
  tier       : elite/good/neutral/avoid — selection.tier（選別タグ）でフィルタ（selection 無しは除外）

⚠️ このスクリプトは「固定の独立オラクル」。routine/エージェントが書き換えてはならない。
   対応していないフィルタ次元が必要な仮説は、人間がここを拡張するまで自動公開せずエスカレする。
   未対応のフィルタキーが claims に現れたら即RED（黙って無視しない）。

終了コード: 0=全緑（自動公開可）, 1=赤（要人間レビュー）。
"""
import json, math, os, re, sys

ROOT = os.path.dirname(os.path.abspath(__file__))

GROUPS = {
    "metal":    {"GC=F", "SI=F"},
    "index":    {"NKD=F", "ES=F", "NQ=F", "YM=F", "^FTSE"},
    "jpy_fx":   {"USDJPY=X", "EURJPY=X", "GBPJPY=X", "AUDJPY=X"},
    "other_fx": {"EURUSD=X", "GBPUSD=X", "AUDUSD=X", "EURAUD=X", "GBPAUD=X"},
    "btc":      {"BTC-USD"},
    "oil":      {"CL=F"},
}
REV = {"rsi_oversold_bounce", "bb_lower_touch"}
ALLOWED_FILTER_KEYS = {"ticker", "group", "direction", "trend", "tf", "signal", "reversal_long", "blocked", "tier"}


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 100.0)
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    pm = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0, c - pm) * 100, min(1, c + pm) * 100)


def closed(d):
    return d.get("outcome") in ("tp1", "tp2", "sl")


def win(d):
    return d.get("outcome") in ("tp1", "tp2")


def get_trend(d):
    ta = d.get("trend_alignment")
    if isinstance(ta, dict) and ta.get("higher_tf_trend"):
        return ta["higher_tf_trend"]
    return "unknown"


def match(d, f):
    """1シグナルが filter 条件を全て満たすか。"""
    if "ticker" in f and d.get("ticker") != f["ticker"]:
        return False
    if "group" in f and f["group"] != "all":
        if d.get("ticker") not in GROUPS.get(f["group"], set()):
            return False
    direction = f.get("direction", "any")
    is_long = "ロング" in (d.get("direction") or "")
    is_short = "ショート" in (d.get("direction") or "")
    if f.get("reversal_long"):
        if not (is_long and d.get("primary_signal") in REV):
            return False
    elif direction == "long" and not is_long:
        return False
    elif direction == "short" and not is_short:
        return False
    if "trend" in f and get_trend(d) != f["trend"]:
        return False
    if "tf" in f and d.get("timeframe") != f["tf"]:
        return False
    if "signal" in f and d.get("primary_signal") != f["signal"]:
        return False
    if "blocked" in f:
        sr = d.get("sr_runway")
        if not isinstance(sr, dict) or sr.get("blocked") != f["blocked"]:
            return False
    if "tier" in f:
        sel = d.get("selection")
        if not isinstance(sel, dict) or sel.get("tier") != f["tier"]:
            return False
    return True


def compute(data, f):
    rows = [d for d in data if closed(d) and match(d, f)]
    n = len(rows)
    k = sum(1 for d in rows if win(d))
    return k, n


def main():
    if len(sys.argv) < 3:
        print("usage: python signal_lab_verify.py <draft.html> <claims.json>")
        sys.exit(2)
    draft_path, claims_path = sys.argv[1], sys.argv[2]
    log_path = os.path.join(ROOT, "signals-log.json")
    if not os.path.exists(log_path):
        # fetch版フォールバック
        alt = os.path.join(ROOT, "_signals_live.json")
        log_path = alt if os.path.exists(alt) else log_path
    data = json.load(open(log_path, encoding="utf-8-sig"))
    claims = json.load(open(os.path.join(ROOT, claims_path) if not os.path.isabs(claims_path) else claims_path, encoding="utf-8-sig"))
    html = open(os.path.join(ROOT, draft_path) if not os.path.isabs(draft_path) else draft_path, encoding="utf-8-sig").read()

    fails = []
    oks = 0
    allowed_pcts = set()  # 要約ボックス完全性チェック用：claim の勝率＋CI境界
    print(f"=== signal_lab_verify: article #{claims.get('article_id','?')} / signals N={len(data)} ===")
    for cl in claims["claims"]:
        label = cl["label"]
        # 未対応のフィルタキーは黙って無視せず即RED（独立オラクルの穴を塞ぐ）
        bad_keys = set(cl.get("filter", {})) - ALLOWED_FILTER_KEYS
        if bad_keys:
            fails.append(f"[{label}] 未対応フィルタキー {sorted(bad_keys)}＝検証不能。verify.pyを人間が拡張するまでエスカレ")
            print(f"  ❌ {label}: 未対応フィルタキー {sorted(bad_keys)}（黙って無視せず赤）")
            continue
        k, n = compute(data, cl["filter"])
        lo, hi = wilson(k, n)
        pct = (100 * k / n) if n else 0
        for v in (pct, lo, hi):
            allowed_pcts.add(round(v, 1))
        # 1) k/n の独立再計算一致
        if k != cl["k"] or n != cl["n"]:
            fails.append(f"[{label}] k/n不一致: 再計算 {k}/{n} ≠ 主張 {cl['k']}/{cl['n']}")
            print(f"  ❌ {label}: 再計算 {k}/{n} ({pct:.1f}%) ≠ 主張 {cl['k']}/{cl['n']}")
            continue
        # 2) 記事HTMLに「k/n」と勝率%が実在するか（転記もれ/取り違え検出）
        frac_ok = re.search(rf"{cl['k']}\s*/\s*{cl['n']}\b", html) is not None
        pcttxt = f"{pct:.1f}%"
        pct_ok = pcttxt in html
        if not frac_ok and not pct_ok:
            fails.append(f"[{label}] 記事に {cl['k']}/{cl['n']} も {pcttxt} も見当たらない（取り違えの恐れ）")
            print(f"  ⚠️ {label}: 再計算一致だが記事HTMLに数字が無い ({cl['k']}/{cl['n']} / {pcttxt})")
            continue
        oks += 1
        print(f"  ✅ {label}: {k}/{n} = {pct:.1f}%  CI[{lo:.1f}~{hi:.1f}]  （記事掲載 frac={frac_ok} pct={pct_ok}）")

    # 要約ボックス完全性チェック：「30秒でわかる」info-box内の全%が claim値/CI境界/定数で裏付けられるか
    CONST_PCTS = {43.0, 50.0, 95.0, 100.0, 0.0}  # 損益分岐/閾値/信頼区間表記/一般表現
    summary_unexplained = []
    sm = re.search(r'30秒でわかる.*?</div>', html, re.S)
    if sm:
        for tok in re.findall(r'(\d+\.?\d*)%', sm.group(0)):
            v = round(float(tok), 1)
            if v not in allowed_pcts and v not in CONST_PCTS:
                summary_unexplained.append(tok + "%")
    else:
        summary_unexplained.append("（30秒まとめボックスが見つからない＝構造異常）")

    # SVG座標はみ出しチェック（text/rect の y が viewBox 高さ内か）
    svg_warn = svg_bounds_check(html)
    for w in svg_warn:
        print(f"  ⚠️ SVG: {w}")
    for u in summary_unexplained:
        print(f"  ❌ 要約ボックスに未検証の数値: {u}")

    print(f"--- 検証クレーム {oks}/{len(claims['claims'])} 緑 / 要約未検証 {len(summary_unexplained)}件 / SVG警告 {len(svg_warn)}件 ---")
    if summary_unexplained:
        fails.append(f"要約ボックスに claim で裏付けられない数値 {len(summary_unexplained)}件: {summary_unexplained}")
    if fails:
        print("RED（要人間レビュー）:")
        for f in fails:
            print("   - " + f)
        sys.exit(1)
    if svg_warn:
        print("RED（SVGはみ出しの恐れ→人間レビュー）")
        sys.exit(1)
    print("GREEN（数字・SVGとも自動公開条件を満たす）")
    sys.exit(0)


def svg_bounds_check(html):
    """各 <svg viewBox="0 0 W H"> 内の text y / rect (y+height) が H を超えていないか簡易チェック。"""
    warns = []
    for m in re.finditer(r'<svg[^>]*viewBox="0 0 ([\d.]+) ([\d.]+)"(.*?)</svg>', html, re.S):
        W, H = float(m.group(1)), float(m.group(2))
        body = m.group(3)
        for tm in re.finditer(r'<text[^>]*\by="([\d.]+)"', body):
            y = float(tm.group(1))
            if y > H + 0.5 or y < 0:
                warns.append(f"text y={y} が viewBox高さ {H} 外")
        for rm in re.finditer(r'<rect[^>]*\by="([\d.]+)"[^>]*\bheight="([\d.]+)"', body):
            y, h = float(rm.group(1)), float(rm.group(2))
            if y + h > H + 0.5:
                warns.append(f"rect y+height={y+h} が viewBox高さ {H} 超")
    return warns


if __name__ == "__main__":
    main()
