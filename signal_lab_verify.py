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
  signals_all: リスト指定＝全シグナルが signal_types に同時発火していること（🆕 2026-07-19
               コンフルエンス次元・オーナー依頼「最低2つのテクニカル組み合わせ」。
               signal_types 欠落レコードは primary_signal 単独集合として照合＝コンボは不一致側に倒れる）
  reversal_long : true なら direction=long かつ primary_signal∈{rsi_oversold_bounce,bb_lower_touch}
  blocked    : true/false — sr_runway.blocked の値でフィルタ（sr_runway 無しは除外）
  tier       : elite/good/neutral/avoid — selection.tier（選別タグ）でフィルタ（selection 無しは除外）
  env        : A/B/C/D — environment.env_score（環境警戒）でフィルタ（🆕 2026-07-19 ファンダ次元・記録済みデータのみ・無しは除外）
  regime     : RISK_ON/RISK_OFF/NEUTRAL — risk_regime.regime でフィルタ（🆕 同上）

⚠️ このスクリプトは「固定の独立オラクル」。routine/エージェントが書き換えてはならない。
   対応していないフィルタ次元が必要な仮説は、人間がここを拡張するまで自動公開せずエスカレする。
   未対応のフィルタキーが claims に現れたら即RED（黙って無視しない）。

終了コード: 0=全緑（自動公開可）, 1=赤（要人間レビュー）。
"""
import datetime as _dt
import json, math, os, re, sys

ROOT = os.path.dirname(os.path.abspath(__file__))

GROUPS = {
    "metal":    {"GC=F", "SI=F"},
    "index":    {"NKD=F", "ES=F", "NQ=F", "YM=F", "^FTSE"},
    "jpy_fx":   {"USDJPY=X", "EURJPY=X", "GBPJPY=X", "AUDJPY=X"},
    "other_fx": {"EURUSD=X", "GBPUSD=X", "AUDUSD=X", "EURAUD=X", "GBPAUD=X"},
    "btc":      {"BTC-USD"},
    "oil":      {"CL=F"},
    # 🆕 2026-07-23 拡張ユニバース group（Q23・人間による正式拡張）。既存 group の定義は不変＝
    #   旧仮説の再計算を汚染しない。SYMBOLS_1D_EXTRA の8銘柄（1dレーン限定・2026-07-21〜記録）を新キーで層別。
    "metal_x":  {"HG=F", "PL=F"},
    "energy_x": {"NG=F"},
    "rates":    {"ZN=F"},
    "crypto_x": {"ETH-USD"},
    "index_x":  {"^GDAXI", "^HSI", "^SOX"},
}
REV = {"rsi_oversold_bounce", "bb_lower_touch"}
ALLOWED_FILTER_KEYS = {"ticker", "group", "direction", "trend", "tf", "signal", "signals_all",
                       "reversal_long", "blocked", "tier", "env", "regime",
                       "rsi_band", "ma_pos", "macd_side",  # 🆕 2026-07-20 指標ステート（人間による正式拡張）
                       "news",  # 🆕 2026-07-23 注目度次元（Q24・人間による正式拡張＝Q21 H-V2「人気過熱の劣後」の攻め転用）
                       "regime4",  # 🆕 2026-07-27 レジーム4状態（Q34・人間による正式拡張）
                       "fired_before", "fired_from"}  # 🆕 2026-08-12 IS/FWD分離（#067・人間による正式拡張＝下記コメント）
# ⚠️ `regime` と `regime4` は**別次元**（同じものにしない）。
#   regime  = ライブの risk_regime（RISK_ON 等）＝エンジンが発火時に記録する既存の語彙。
#   regime4 = 固定オラクル `research/_regime_state.py`（Q27で凍結・MA200×60日実現ボラの750日分位×
#             ヒステリシス21営業日・ポイントインタイム）の UP_LOW / UP_HIGH / DOWN_LOW / DOWN_HIGH。
#   語彙が違うものを同じキーに流し込むと既存仮説の母集団が汚染されるため分離した（Q23「既存groupの定義は不変」と同じ理由）。
#   値はレコードの `regime4` フィールドを読むだけ＝オラクルはローカル専用ファイルに依存しない
#   （クラウドroutineは research/ 配下を読めないので、直読みさせるとローカルとクラウドで挙動が割れる）。
#   バックテストへの後付けはローカルの `research/_regime4_annotate.py` が行う。


# 🆕 2026-07-23 注目度バンド（Q24・バンド境界は事前宣言＝以後変更しない。Q21 H-V2 と同じ 0 / 1-2 / 3+）
def news_band_of(d):
    """発火時点のニュース件数バンド: "0" / "1-2" / "3+"。記録が無い・数値でない場合は None＝マッチしない。"""
    nc = d.get("news_count")
    if isinstance(nc, bool) or not isinstance(nc, (int, float)):
        return None
    if nc <= 0:
        return "0"
    return "1-2" if nc <= 2 else "3+"


# 🆕 2026-07-20 指標ステート導出（オーナー依頼「指標の組み合わせ研究」・数式ロック）
#   発火時点の indicators_at_signal / entry から決定論で導出。記録が無い・数値でない場合は None＝マッチしない
#   （blocked/tier/env と同じ意味論）。バンド境界は事前宣言＝以後変更しない。
def rsi_band_of(d):
    """RSI水準: os(≤30) / low(30<r≤45) / mid(45<r≤55) / high(55<r<70) / ob(≥70)。"""
    ind = d.get("indicators_at_signal")
    r = ind.get("rsi") if isinstance(ind, dict) else None
    if not isinstance(r, (int, float)):
        return None
    if r <= 30:
        return "os"
    if r <= 45:
        return "low"
    if r <= 55:
        return "mid"
    if r < 70:
        return "high"
    return "ob"


def ma_pos_of(d):
    """エントリー価格とMA25/MA75の位置関係: above_both / below_both / above25_only / above75_only。"""
    ind = d.get("indicators_at_signal")
    e = d.get("entry")
    if not isinstance(ind, dict) or not isinstance(e, (int, float)):
        return None
    m25, m75 = ind.get("ma25"), ind.get("ma75")
    if not isinstance(m25, (int, float)) or not isinstance(m75, (int, float)):
        return None
    a25, a75 = e > m25, e > m75
    if a25 and a75:
        return "above_both"
    if not a25 and not a75:
        return "below_both"
    return "above25_only" if a25 else "above75_only"


def macd_side_of(d):
    """MACD本線の0ライン上下: pos(>0) / neg(≤0)。バックテストログには記録なし＝ライブ専用次元。"""
    ind = d.get("indicators_at_signal")
    m = ind.get("macd") if isinstance(ind, dict) else None
    if not isinstance(m, (int, float)):
        return None
    return "pos" if m > 0 else "neg"


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
    if "signals_all" in f:
        # 🆕 2026-07-19 コンフルエンス: 指定シグナル全てが同時発火していること
        have = set(d.get("signal_types") or ([d["primary_signal"]] if d.get("primary_signal") else []))
        if not set(f["signals_all"]).issubset(have):
            return False
    if "blocked" in f:
        sr = d.get("sr_runway")
        if not isinstance(sr, dict) or sr.get("blocked") != f["blocked"]:
            return False
    if "tier" in f:
        sel = d.get("selection")
        if not isinstance(sel, dict) or sel.get("tier") != f["tier"]:
            return False
    if "env" in f:
        # 🆕 2026-07-19 ファンダ次元: 環境警戒スコア（記録が無いレコードは除外＝blocked/tierと同じ意味論）
        envd = d.get("environment")
        if not isinstance(envd, dict) or envd.get("env_score") != f["env"]:
            return False
    if "regime" in f:
        rr = d.get("risk_regime")
        if not isinstance(rr, dict) or rr.get("regime") != f["regime"]:
            return False
    # 🆕 2026-07-20 指標ステート（記録が無いレコードはマッチしない＝blocked/tier/envと同じ意味論）
    if "rsi_band" in f and rsi_band_of(d) != f["rsi_band"]:
        return False
    if "ma_pos" in f and ma_pos_of(d) != f["ma_pos"]:
        return False
    if "macd_side" in f and macd_side_of(d) != f["macd_side"]:
        return False
    if "news" in f and news_band_of(d) != f["news"]:
        # 🆕 2026-07-23 注目度次元（記録が無いレコードはマッチしない＝blocked/tier/envと同じ意味論）
        return False
    if "regime4" in f and d.get("regime4") != f["regime4"]:
        # 🆕 2026-07-27 レジーム4状態（Q34・記録が無いレコードはマッチしない＝blocked/tier/envと同じ意味論）
        return False
    # 🆕 2026-08-12 IS/FWD分離（#067ループの構造修正・人間による正式拡張）:
    #   fired_before / fired_from = 発火時刻 fired_at の境界。値は "YYYY-MM-DD"（JST日付）。
    #   fired_at の ISO 文字列（+09:00）との辞書順比較＝#063 labnote の REG_DATE 方式を踏襲。
    #   IS = {"fired_before": "<REG_DATE翌日>"} / FWD = {"fired_from": "<REG_DATE翌日>"} で
    #   全期間を厳密に2分割できる（登録日=トラッカー registered_at、前向きは翌日以降の発火）。
    #   背景＝claims に期間の次元が無く「（IS）」ラベルの列を全期間の数字で埋めても緑で通った
    #   （2026-08-12 #067 コンプラ黒）。期間を claims で宣言可能にして塞ぐ。
    #   fired_at が無いレコードはどちらにもマッチしない（blocked/tier/env と同じ意味論）。
    if "fired_before" in f:
        fa = d.get("fired_at")
        if not fa or not (fa < f["fired_before"]):
            return False
    if "fired_from" in f:
        fa = d.get("fired_at")
        if not fa or not (fa >= f["fired_from"]):
            return False
    return True


def compute(data, f):
    rows = [d for d in data if closed(d) and match(d, f)]
    n = len(rows)
    k = sum(1 for d in rows if win(d))
    return k, n


def date_check(html):
    """公開日メタ（datePublished／公開：表記）が JST の今日と一致するか。
    クラウド routine は UTC 環境で朝 06:1x JST に走るため、モデルが UTC 日付（=前日）を
    書いてしまう事故がある（実例: 2026-07-06 #031 が 7/5 付けで公開）。決定論で検出する。
    過去記事の再監査時は環境変数 SIGNAL_LAB_SKIP_DATE_CHECK=1 で免除。"""
    if os.environ.get("SIGNAL_LAB_SKIP_DATE_CHECK") == "1":
        return []
    jst = _dt.datetime.now(_dt.timezone(_dt.timedelta(hours=9)))
    today = jst.strftime("%Y-%m-%d")
    today_jp = f"{jst.year}年{jst.month}月{jst.day}日"
    fails = []
    m = re.search(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})"', html)
    if m and m.group(1) != today:
        fails.append(f"datePublished {m.group(1)} ≠ JST今日 {today}（UTC日付ミスの疑い。再監査なら SIGNAL_LAB_SKIP_DATE_CHECK=1）")
    m2 = re.search(r'公開：\s*(\d{4}年\d{1,2}月\d{1,2}日)', html)
    if m2 and m2.group(1) != today_jp:
        fails.append(f"公開日表記 {m2.group(1)} ≠ JST今日 {today_jp}（UTC日付ミスの疑い）")
    # 🆕 2026-07-07: 下書き状態の残骸検査（実例: #032 が「公開：2026年7月7日（下書き中）」のまま公開された）
    if "下書き中" in html:
        fails.append("本文に「下書き中」が残っている（下書きテンプレの消し忘れ＝仕上げ工程のミス）")
    return fails


def article_date(html):
    """記事が名乗る公開日（JST・YYYY-MM-DD）。無ければ None。asof の妥当性検査に使う。"""
    m = re.search(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})"', html)
    if m:
        return m.group(1)
    m = re.search(r'公開：\s*(\d{4})年(\d{1,2})月(\d{1,2})日', html)
    return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" if m else None


def parse_asof(s):
    """asof 文字列 → aware datetime。タイムゾーン無しは JST とみなす。失敗は None。"""
    try:
        t = _dt.datetime.fromisoformat(str(s).strip().replace(" ", "T", 1))
    except (ValueError, AttributeError):
        return None
    return t if t.tzinfo else t.replace(tzinfo=_dt.timezone(_dt.timedelta(hours=9)))


def resolved_at(d):
    """決済が確定した時刻（aware）。無い/壊れているものは None。"""
    return parse_asof(d.get("outcome_resolved_at")) if d.get("outcome_resolved_at") else None


def apply_asof(data, asof, art_date):
    """基準時刻での凍結。戻り値 (絞ったdata, 不備リスト, 除外した決済済み件数)。

    ⚠️ 2026-08-11 追加。動機＝**エスカレした下書きが二度と検証できなくなる**問題:
       claims は生成時点(朝)のログで計算されるが、本オラクルは実行時のライブログで再計算する。
       日中に決済が増えると同じ下書きは永久に RED になり、🚩 が付いた回は**直そうにも直せない**
       （実例 #065 が2日放置・#067 が当日夕方に 11/11→2/11 へ転落）。
    ⚠️ 打ち切りは **`outcome_resolved_at`**（決済確定時刻）で行う。`fired_at` では誤り＝
       朝より前に発火して日中に決済した玉を「朝も計上済み」と誤認するため。
    ⚠️ **捏造不可の担保は失わない**: 数字は依然として実ログからの再計算と完全一致する必要があり、
       asof は「どの断面か」を選べるだけ。さらに断面を生成日に固定するため
       **asof は記事が名乗る公開日と同じJST日付でなければ RED**（遠い過去の都合のよい断面を選べない）。
       ⚠️ 既知の限界: 同一日内での断面選択は理論上残る（開示事項）。
    """
    fails = []
    if asof > _dt.datetime.now(_dt.timezone.utc):
        fails.append(f"asof {asof.isoformat()} が未来＝断面として不正")
    if art_date:
        a_jst = asof.astimezone(_dt.timezone(_dt.timedelta(hours=9))).strftime("%Y-%m-%d")
        if a_jst != art_date:
            fails.append(f"asof の日付 {a_jst} が記事の公開日 {art_date} と不一致"
                         f"＝生成日以外の断面は認めない（都合のよい切り口の防止）")
    kept, dropped = [], 0
    for d in data:
        if not closed(d):
            kept.append(d)          # 未決済は元から compute で除外される＝そのまま通す
            continue
        r = resolved_at(d)
        if r is None or r > asof:
            dropped += 1
        else:
            kept.append(d)
    return kept, fails, dropped


def main():
    argv = [a for a in sys.argv[1:]]
    asof_cli = None
    for i, a in enumerate(argv):
        if a == "--asof" and i + 1 < len(argv):
            asof_cli = argv[i + 1]
            argv = argv[:i] + argv[i + 2:]
            break
        if a.startswith("--asof="):
            asof_cli = a.split("=", 1)[1]
            argv = argv[:i] + argv[i + 1:]
            break
    if len(argv) < 2:
        print("usage: python signal_lab_verify.py <draft.html> <claims.json> [--asof <ISO8601>]")
        sys.exit(2)
    draft_path, claims_path = argv[0], argv[1]
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

    # 基準時刻の凍結（任意）。claims.json の "asof" ＞ CLI の --asof の順で拾う。
    # 無ければ**従来どおりライブ全量**＝既存記事の再監査に一切影響しない。
    asof_src = claims.get("asof") or asof_cli
    asof_note = ""
    if asof_src:
        asof = parse_asof(asof_src)
        if asof is None:
            fails.append(f"asof を解釈できない: {asof_src!r}（ISO8601で書く）")
        else:
            data, af, dropped = apply_asof(data, asof, article_date(html))
            fails.extend(af)
            for x in af:
                print(f"  ❌ asof: {x}")
            jst_txt = asof.astimezone(_dt.timezone(_dt.timedelta(hours=9))).strftime("%Y-%m-%d %H:%M JST")
            asof_note = f" / asof={jst_txt}（基準時刻以降の決済 {dropped}件を除外）"
    print(f"=== signal_lab_verify: article #{claims.get('article_id','?')} / signals N={len(data)}{asof_note} ===")
    for df in date_check(html):
        fails.append(df)
        print(f"  ❌ 日付: {df}")
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

    # 期間ラベルの取り違え検査（#067/#072 と同じ型の再発防止・上の period_label_check 参照）
    _buckets = {"IS": set(), "FWD": set(), "none": set()}
    for cl in claims["claims"]:
        f = cl.get("filter", {}) or {}
        if set(f) - ALLOWED_FILTER_KEYS:
            continue
        _k, _n = compute(data, f)
        if not _n:
            continue
        _key = period_bucket(f)
        _buckets[_key].add(round(100 * _k / _n, 1))
    period_bad = period_label_check(html, _buckets)
    for pb in period_bad:
        print(f"  ❌ 期間ラベル: {pb}")
    fails.extend(period_bad)

    # SVGチェック：①縦はみ出し(text/rectのy) ②text同士の重なり・横はみ出し
    svg_warn = svg_bounds_check(html) + text_overlap_check(html)
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


# ── 期間ラベルと出所の一致（2026-08-18 追加・人間による正式拡張／制約を増やす方向）
#
# 塞ぐ穴: 表の「IS 勝率」列に**全期間の数字**を書いても緑で通った。
#   claims の k/n は再計算一致するし、数字は記事HTMLに実在するので既存2検査を素通りする。
#   実例 #067(2026-08-12) と #072(2026-08-18) の**2回**同じ型で 🔴黒＝Opusコンプラ頼みだった。
#   SOP には「全期間の数字に（IS）とラベルするのは景表法上の優良誤認＝黒」と明記済みだが、
#   **文書に書いてあるだけでコードが止めていなかった**＝再発した。
#
# 規則: 期間を名乗る列（ヘッダに IS / FWD / OOS）のセルに出る勝率%は、
#       **その期間で絞った claim の値**でなければならない。
#       別期間の claim の値だったら赤（＝取り違えの疑い）。
#
# 誤検知を抑える2つの限定（2026-08-18 に過去68本で実測して決めた）:
#   ①claims が期間キー（fired_before/fired_from）を1つも使っていない記事は**対象外**。
#     8/12 の拡張以前は期間を表現する手段が無く、全部が 'none' 扱いになるため。
#     この限定が無いと #035/#037/#050/#054/#058/#066 の6本が誤って赤くなる（実測）。
#   ②信頼区間の列は**対象外**（ヘッダに CI/信頼区間、または値が範囲表記）。
#     CI境界は勝率そのものではないので集合が合わない。これが無いと #070 が誤って赤くなる（実測）。
#   → 実測結果（2026-08-18・過去66本を claims の主張値で照合）: **赤は #072 の1本だけ**
#     ＝Opusコンプラが🔴黒と判定した当の箇所（金属のIS列に全期間値）。**残り65本は緑のまま**。
#
# ⚠️ 「claim がまったく無い数字」は**ここでは赤にしない**。過去68本で373件あり（24本が該当）、
#    別種の緩さ（記事の数字が claims を超えて増える）なので、ここで一緒に締めるとレーンが止まる。
RE_PERIOD_IS  = re.compile(r"(?<![A-Za-z])IS(?![A-Za-z])")
RE_PERIOD_FWD = re.compile(r"(?<![A-Za-z])(FWD|OOS)(?![A-Za-z])")
RE_CELL_PCT   = re.compile(r"(\d+(?:\.\d+)?)\s*%")
RE_CI_HEAD    = re.compile(r"CI|信頼区間")


def period_bucket(f):
    """claim の filter を期間バケット（IS / FWD / none）へ振り分ける。

    ⚠️ **判定順が肝**＝`fired_from` を先に見る。`fired_from` と `fired_before` を
       **両方**持つ claim は「FWD期間の部分窓」（例: #071 の FWD Q1/Q2/後半）であって IS ではない。
       `fired_before` を先に見ると FWD の部分窓を IS と誤分類し、**正しい記事を赤にする**
       （2026-08-18 の初版で実際に踏み、#071 を誤って「取り違え3件」と判定した）。
    """
    if "fired_from" in f:
        return "FWD"
    if "fired_before" in f:
        return "IS"
    return "none"


def _cell_text(x):
    return re.sub(r"<[^>]+>", "", x).strip()


def period_label_check(html, bucket_pcts):
    """期間を名乗る列の数字が、その期間の claim 由来かを見る。戻り値: 違反メッセージの list。

    bucket_pcts = {"IS": {…%}, "FWD": {…%}, "none": {…%}}（呼び出し側が claim から作る）
    """
    if not (bucket_pcts.get("IS") or bucket_pcts.get("FWD")):
        return []          # 限定①: 期間キーを使っていない記事は対象外
    out = []
    for t in re.findall(r"<table.*?</table>", html, re.S):
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.S)
        if not rows:
            continue
        heads = [_cell_text(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", rows[0], re.S)]
        cols = {}
        for i, h in enumerate(heads):
            if RE_CI_HEAD.search(h):           # 限定②: CI列は見ない
                continue
            if RE_PERIOD_IS.search(h):
                cols[i] = "IS"
            elif RE_PERIOD_FWD.search(h):
                cols[i] = "FWD"
        if not cols:
            continue
        for r in rows[1:]:
            cells = [_cell_text(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)]
            if not cells:
                continue
            for i, kind in cols.items():
                if i >= len(cells) or "[" in cells[i] or "〜" in cells[i]:
                    continue               # 限定②: 範囲表記のセルも見ない
                for m in RE_CELL_PCT.finditer(cells[i]):
                    v = round(float(m.group(1)), 1)
                    if v in bucket_pcts[kind]:
                        continue
                    other = [k for k in ("IS", "FWD", "none") if k != kind and v in bucket_pcts.get(k, set())]
                    if other:
                        where = "全期間" if other == ["none"] else "/".join(other)
                        out.append(f"「{heads[i]}」列 行「{cells[0][:20]}」の {v}% は "
                                   f"{kind} で絞った claim に無く、{where} の claim の値＝期間の取り違えの疑い")
    return out


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


def _est_text_width(text, fs):
    """文字数×em係数で text の概算幅を返す（和文/全角≒1em・英数記号≒0.55em）。"""
    w = 0.0
    for ch in text:
        o = ord(ch)
        if (0x3040 <= o <= 0x30ff) or (0x3000 <= o <= 0x33ff) or (0x4e00 <= o <= 0x9fff) or (0xff00 <= o <= 0xffef):
            w += fs            # ひらがな/カタカナ/CJK/全角記号 ≒ 1em
        else:
            w += fs * 0.55     # 英数・半角記号 ≒ 0.55em
    return w


def _svg_text_boxes(body, with_pos=False):
    """SVG body 内の <text> を概算バウンディングボックス (x0,y0,x1,y1,text) のリストに変換。
    y は baseline なので上に約0.9em・下に約0.15em 伸ばす。
    with_pos=True のときは末尾に body 内の出現位置を足した6要素で返す（描画順の判定用）。
    ※既定の戻り値の形は変えない＝既存の text_overlap_check は影響を受けない。"""
    boxes = []
    for m in re.finditer(r'<text\b([^>]*)>(.*?)</text>', body, re.S):
        attrs, raw = m.group(1), m.group(2)
        xm = re.search(r'\bx="(-?[\d.]+)"', attrs)
        ym = re.search(r'\by="(-?[\d.]+)"', attrs)
        if not xm or not ym:
            continue
        x, y = float(xm.group(1)), float(ym.group(1))
        fsm = re.search(r'font-size="([\d.]+)"', attrs)
        fs = float(fsm.group(1)) if fsm else 12.0
        am = re.search(r'text-anchor="(start|middle|end)"', attrs)
        anchor = am.group(1) if am else "start"
        text = re.sub(r'<[^>]+>', '', raw).strip()
        if not text:
            continue
        w = _est_text_width(text, fs)
        if anchor == "middle":
            x0 = x - w / 2
        elif anchor == "end":
            x0 = x - w
        else:
            x0 = x
        box = (x0, y - fs * 0.9, x0 + w, y + fs * 0.15, text)
        boxes.append(box + (m.start(),) if with_pos else box)
    return boxes


def text_overlap_check(html):
    """同一 SVG 内で <text> 同士が重なっていないか／横にはみ出していないかを概算チェック。
    フォント実寸はレンダリングしないと測れないため、文字数×em係数で近似する。
    過検出しても『RED→人間レビュー』に回るだけ＝自動公開を止める安全側の判定。"""
    warns = []
    for m in re.finditer(r'<svg[^>]*viewBox="0 0 ([\d.]+) ([\d.]+)"(.*?)</svg>', html, re.S):
        W = float(m.group(1))
        boxes = _svg_text_boxes(m.group(3))
        # 横はみ出し（ボックス右端が幅を超える / 左端がマイナス）
        for (x0, y0, x1, y1, t) in boxes:
            if x1 > W + 2 or x0 < -2:
                warns.append(f"text「{t[:16]}」が左右にはみ出し（x {x0:.0f}〜{x1:.0f} / 幅 {W:.0f}）")
        # text 同士の重なり（両軸で tol px 超の重複）
        tol = 3.0
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                a, b = boxes[i], boxes[j]
                ox = min(a[2], b[2]) - max(a[0], b[0])
                oy = min(a[3], b[3]) - max(a[1], b[1])
                if ox > tol and oy > tol:
                    warns.append(f"text「{a[4][:14]}」と「{b[4][:14]}」が重なり（重複 {ox:.0f}x{oy:.0f}px）")
    return warns


def _svg_shape_boxes(body):
    """SVG body 内の「テキストを隠しうる不透明な図形」を (box, class, 出現位置) で返す。
    半透明（s-zone/s-band系）と塗り無し（s-fire / fill="none"）は隠さないので除外する。"""
    NON_OPAQUE = ("s-zone", "s-fire", "s-band")
    out = []
    for m in re.finditer(r'<(rect|circle|ellipse)\b([^>]*?)/?>', body):
        tag, attrs = m.group(1), m.group(2)
        cm = re.search(r'class="([^"]*)"', attrs)
        cls = cm.group(1) if cm else ""
        if any(k in cls for k in NON_OPAQUE) or 'fill="none"' in attrs:
            continue
        num = lambda n: (lambda g: float(g.group(1)) if g else None)(
            re.search(r'\b%s="(-?[\d.]+)"' % n, attrs))
        if tag == "rect":
            x, y, w, h = num("x"), num("y"), num("width"), num("height")
            if None in (x, y, w, h):
                continue
            box = (x, y, x + w, y + h)
        elif tag == "circle":
            cx, cy, r = num("cx"), num("cy"), num("r")
            if None in (cx, cy, r):
                continue
            box = (cx - r, cy - r, cx + r, cy + r)
        else:
            cx, cy, rx, ry = num("cx"), num("cy"), num("rx"), num("ry")
            if None in (cx, cy, rx, ry):
                continue
            box = (cx - rx, cy - ry, cx + rx, cy + ry)
        out.append((box, cls or tag, m.start()))
    return out


def text_occlusion_check(html):
    """<text> が「自分より後に描かれた不透明な図形」に隠れていないかをチェック。

    2026-07-29 追加。text_overlap_check は text 同士しか見ておらず、
    「ラベルの上に不透明な楕円を後から描いて文字が消える」欠陥を素通りしていた
    （実例＝図解の『翌朝の始値』が s-node の楕円に 28x9px 隠れた）。
    SVG は後に書いた要素が上に来るため、出現位置の前後で判定できる。"""
    warns = []
    for m in re.finditer(r'<svg[^>]*viewBox="0 0 ([\d.]+) ([\d.]+)"(.*?)</svg>', html, re.S):
        body = m.group(3)
        texts = _svg_text_boxes(body, with_pos=True)
        shapes = _svg_shape_boxes(body)
        tol = 3.0
        for (x0, y0, x1, y1, t, tpos) in texts:
            for (box, cls, spos) in shapes:
                if spos <= tpos:          # 先に描かれた図形はテキストの下＝隠さない
                    continue
                ox = min(x1, box[2]) - max(x0, box[0])
                oy = min(y1, box[3]) - max(y0, box[1])
                if ox > tol and oy > tol:
                    warns.append(f"text「{t[:14]}」が後から描かれた {cls} に隠れる"
                                 f"（重複 {ox:.0f}x{oy:.0f}px）")
    return warns


def band_parallel_check(html, min_ratio=1.2):
    """ボリンジャーバンド（class="s-bb" の2本）が平行チャネルになっていないかをチェック。

    2026-07-29 追加。BBの本質は「σに連動して伸縮する」ことなので、
    上下バンドの幅が一定＝平行だと、見た目がどれだけ曲がっていてもBBには見えない。
    実例＝guide-signal-anatomy.html は幅 76→73px（最大/最小 1.04倍）の平行チャネルだった。
    座標は `_gen_bb_panel.py` で計算して出すこと（目分量で描くと必ずこうなる）。"""
    warns = []
    for m in re.finditer(r'<svg[^>]*viewBox="0 0 ([\d.]+) ([\d.]+)"(.*?)</svg>', html, re.S):
        body = m.group(3)
        ds = [d for tag, d in
              ((t, (re.search(r'\bd="([^"]+)"', t) or [None, None])[1] if re.search(r'\bd="([^"]+)"', t) else None)
               for t in re.findall(r'<path\b[^>]*>', body))
              if d and 'class="s-bb"' in tag]
        if len(ds) != 2:
            continue
        series = []
        for d in ds:
            nums = [float(v) for v in re.findall(r'-?\d+(?:\.\d+)?', d)]
            series.append(list(zip(nums[0::2], nums[1::2])))
        if len(series[0]) != len(series[1]) or len(series[0]) < 4:
            continue                      # 点数が違う＝対応が取れないので判定しない
        widths = [abs(b[1] - a[1]) for a, b in zip(series[0], series[1])]
        if min(widths) <= 0.5:
            continue
        ratio = max(widths) / min(widths)
        if ratio < min_ratio:
            warns.append(f"ボリンジャーバンドが平行（幅 {min(widths):.0f}〜{max(widths):.0f}px"
                         f"＝最大/最小 {ratio:.2f}倍 < {min_ratio}）＝σに連動していない。"
                         f"`_gen_bb_panel.py` で計算し直す")
    return warns


if __name__ == "__main__":
    main()
