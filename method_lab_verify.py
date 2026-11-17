# -*- coding: utf-8 -*-
"""
method_lab_verify.py — 研究日誌「毎日の新しい方法」の回の数字を method-lab.json・method-lab-registry.json と突き合わせる
固定オラクル（2026-11-17 新設・オーナー決定「新しい方法を毎日探して…発表」）。

⚠️ routine・エージェントは編集しない（signal_lab_verify.py・exit_lab_verify.py と同じ固定コード。実行前に
   git checkout -- method_lab_verify.py）。直すのは下書きと method-claims.json のほう。

使い方: python method_lab_verify.py <draft.html> <method-claims.json>

method-claims.json の形:
{
  "article_id": "153",
  "method_date": "2026-11-18",                      # その日の候補（method-lab.json の batches の日付）
  "claims": [
    {"label": "探す期間の回数",     "what": "method", "period": "explore", "field": "n",      "value": 723},
    {"label": "探す期間の平均",     "what": "method", "period": "explore", "field": "mean",   "value": 0.20},
    {"label": "確かめる期間の差",   "what": "method", "period": "confirm", "field": "excess", "value": 0.02},
    {"label": "2024年の平均",       "what": "year",   "year": "2024",      "field": "mean",   "value": 0.38},
    {"label": "今日ためした数",     "what": "batch",  "field": "tried",    "value": 48},
    {"label": "外した方法の平均",   "what": "cull",   "field": "avgR",     "value": -0.18}
  ]
}
what と field:
  method（その日の新しい方法＝合格しなかった日は惜しかった方法）× period=explore／confirm:
      n・mean・lo・hi（R）・win（%・小数1桁）・placebo_mean・excess（R）・p（小数3桁）・z・per_year
  year（年ごと・図に使う）: n・mean
  batch: tried・pass_explore・pass_confirm・pass_frequency・pass_all・idea・mutation・random
  cull（その日に外した方法）: n・avgR・lo・hi・score（R）・pool_size
R の値は小数2桁（例 0.20・−0.05）。

検査（どれも赤＝公開しない）:
 ① method_date の候補が method-lab.json（いまの版 → 無ければ git の履歴）にある。cull の claim があれば、その日の
    外した記録が method-lab-registry.json（いまの版 → git の履歴）にある。
 ② claim ごとに値が一致する。
 ③ 本文の数字の出どころ: 差し込んだ表と箱（data-mw-method-snippet）・前向きトラッカー表を除いた本文（図の文字も含む）に出る
    「符号つきの小数」「◯R」「◯%」「◯回」は、どれかの claim の値か決まった定数でなければ赤。図の目盛り（小数1桁の符号つき）は許す。
 ④ ためした数を書く: batch の tried の claim が必ずある（たくさん試すほど偶然よく見えるものが混じる、の根拠）。
 ⑤ 言い方: 「おすすめ」「推奨」「最適」「ベスト」「〜べき」「儲かる」「必ず」「確実」「保証」などは赤（打ち消しは除く）。
 ⑥ 断り書き: 「偶然」と「前向き」の両方が本文にある。
 ⑦ 合格しなかった日（惜しかった方法）は「登録しました」と書かない。合格した日は「登録」と書く。
 ⑧ 差し込みの目印 4つ（METHOD_RESULT・METHOD_BATCH・CULL_BOX・RESEARCH_LIST）が本文にある（research_rotation.py report で差し込む）。
赤は method-lab.json が見つからないとき以外すべて [直せる]。
"""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
LAB_PATH = os.path.join(ROOT, "method-lab.json")
REG_PATH = os.path.join(ROOT, "method-lab-registry.json")
FIXABLE = "[直せる]"

METHOD_FIELDS = {"n", "mean", "lo", "hi", "win", "placebo_mean", "excess", "p", "z", "per_year"}
R_FIELDS = {"mean", "lo", "hi", "placebo_mean", "excess", "avgR", "score"}
BATCH_FIELDS = {"tried", "pass_explore", "pass_confirm", "pass_frequency", "pass_all", "idea", "mutation", "random"}
CULL_FIELDS = {"n", "avgR", "lo", "hi", "score", "pool_size"}
YEAR_FIELDS = {"n", "mean"}
CONST_R = {0.1, 0.15, 0.5, 1.0, 1.3, 1.33, 1.5, 2.0, 3.0}
CONST_PCT = {0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 50.0, 95.0, 100.0}
CONST_COUNT = {0, 1, 2, 3, 5, 10, 20, 30, 40, 48, 50, 80, 100, 2000, 2017, 2018}
MARKERS = ("METHOD_RESULT", "METHOD_BATCH", "CULL_BOX", "RESEARCH_LIST")
BANNED = [
    (r"おすすめ|オススメ|お勧め|推奨|最適|ベスト|一択|使うべき|選ぶべき|べきです|べきだ", "推奨・断定の言い方"),
    (r"必ず(?:勝|儲|利益|上が|下が)|儲か|確実に|保証|勝てる方法|負けない", "利益を約束する言い方"),
]
NEGATED = re.compile(r"[^。]{0,14}?(?:ではあり|ではな|ではご|するものではな|しません|しない|できません)")
SKIP_AFTER = re.compile(r"\s*(?:ATR|σ|倍|本|年|日|時間|か月|ヶ月|週|銘柄|つ|ペア|営業日|通り|%以内)")


def _git_versions(path, n=80):
    rel = os.path.basename(path)
    try:
        shas = subprocess.run(["git", "log", "--format=%H", "-n", str(n), "--", rel], cwd=ROOT,
                              capture_output=True, text=True, check=True).stdout.split()
    except Exception:
        shas = []
    for sha in shas:
        try:
            txt = subprocess.run(["git", "show", f"{sha}:{rel}"], cwd=ROOT, capture_output=True, text=True,
                                 check=True).stdout
            yield json.loads(txt), f"履歴 {sha[:7]}"
        except Exception:
            continue


def load_batch(date):
    if os.path.exists(LAB_PATH):
        cur = json.load(open(LAB_PATH, encoding="utf-8"))
        if date in (cur.get("batches") or {}):
            return cur["batches"][date], "いまの版"
    for d, where in _git_versions(LAB_PATH):
        if date in (d.get("batches") or {}):
            return d["batches"][date], where
    return None, None


def load_cull(date):
    if os.path.exists(REG_PATH):
        cur = json.load(open(REG_PATH, encoding="utf-8"))
        hit = [c for c in cur.get("culls", []) if c.get("date") == date]
        if hit:
            return hit[-1], "いまの版"
    for d, where in _git_versions(REG_PATH):
        hit = [c for c in d.get("culls", []) if c.get("date") == date]
        if hit:
            return hit[-1], where
    return None, None


def actual_value(cl, batch, cull):
    what, field = cl.get("what"), cl.get("field")
    ch = (batch or {}).get("chosen") or {}
    if what == "method":
        if field not in METHOD_FIELDS:
            return "bad"
        s = ch.get(cl.get("period")) or {}
        pl = s.get("placebo") or {}
        return {"n": s.get("n"), "mean": s.get("mean"), "lo": s.get("lo"), "hi": s.get("hi"),
                "win": None if s.get("win") is None else 100 * s["win"], "placebo_mean": pl.get("mean"),
                "excess": pl.get("excess"), "p": pl.get("p"), "z": pl.get("z"), "per_year": s.get("per_year")}[field]
    if what == "year":
        if field not in YEAR_FIELDS:
            return "bad"
        y = (ch.get("by_year") or {}).get(str(cl.get("year")))
        return None if not y else (y[0] if field == "n" else y[1])
    if what == "batch":
        if field not in BATCH_FIELDS:
            return "bad"
        c = (batch or {}).get("counts") or {}
        return (c.get("by_source") or {}).get(field) if field in ("idea", "mutation", "random") else c.get(field)
    if what == "cull":
        if field not in CULL_FIELDS:
            return "bad"
        return None if cull is None else cull.get(field)
    return "bad"


def same(field, actual, claimed):
    if actual is None or claimed is None:
        return False
    try:
        claimed = float(claimed)
    except Exception:
        return False
    if field in ("n", "pool_size") or field in BATCH_FIELDS:
        return int(round(claimed)) == int(actual)
    if field == "win":
        return abs(round(actual, 1) - claimed) < 0.051
    if field == "p":
        return abs(round(actual, 3) - claimed) < 0.00051
    if field in ("z", "per_year"):
        return abs(round(actual, 1) - claimed) < 0.051
    return abs(round(actual, 2) - claimed) < 0.0051


def body_text(html):
    """数字を拾う本文。head・script・style・差し込んだ表と箱・前向きトラッカー表は除く。"""
    for mk in MARKERS:
        html = re.sub(r"<!-- MW:%s -->.*?<!-- /MW:%s -->" % (mk, mk), " ", html, flags=re.S)
    html = re.sub(r"<div[^>]*data-mw-method-snippet.*?</div>\s*(?=<|$)", " ", html, flags=re.S)
    m = re.search(r"data-mw-tracker-legend", html)
    if m:
        end = html.find("</table>", m.end())
        if end > 0:
            start = html.rfind("<", 0, m.start())
            html = html[:start] + html[end + len("</table>"):]
    html = re.sub(r"<head\b.*?</head>|<script\b.*?</script>|<style\b.*?</style>", " ", html, flags=re.S | re.I)
    svg_parts = re.findall(r"<svg\b.*?</svg>", html, flags=re.S | re.I)
    text = re.sub(r"<svg\b.*?</svg>", " ", html, flags=re.S | re.I)
    clean = lambda h: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h)).replace("&minus;", "-")
    norm = lambda t: t.replace("−", "-").replace("－", "-").replace("＋", "+").replace("％", "%")
    return norm(clean(text)), norm(clean(" ".join(svg_parts)))


def numbers_in(text):
    out = []
    for m in re.finditer(r"(?<![\d.])([+\-]?)(\d[\d,]*(?:\.\d+)?)\s*(R(?![A-Za-z])|%|回(?!目))?", text):
        sign, num, unit = m.group(1), m.group(2), m.group(3) or ""
        dec = len(num.split(".")[1]) if "." in num else 0
        v = float(num.replace(",", "")) * (-1 if sign == "-" else 1)
        ctx = text[max(0, m.start() - 12):m.end() + 8]
        if unit in ("R", "%", "回"):
            out.append((unit, v, dec, bool(sign), ctx))
        elif sign and dec > 0 and not SKIP_AFTER.match(text, m.end()):
            out.append(("±", v, dec, True, ctx))
    return out


def main():
    if len(sys.argv) < 3:
        print("usage: python method_lab_verify.py <draft.html> <method-claims.json>")
        sys.exit(2)
    rd = lambda p: open(p if os.path.isabs(p) else os.path.join(ROOT, p), encoding="utf-8-sig").read()
    html = rd(sys.argv[1])
    claims = json.loads(rd(sys.argv[2]))
    date = claims.get("method_date")
    fails, fatal = [], []
    print(f"=== method_lab_verify: article #{claims.get('article_id', '?')} / method_date={date} ===")
    batch, where = load_batch(date)
    if batch is None:
        fatal.append(f"method-lab.json に {date} の候補が無い（method-lab.yml が動いていない・日付の書き間違い）")
        for f in fatal:
            print(f"  ❌ {f}")
        print("RED（要人間レビュー）")
        sys.exit(1)
    print(f"  method-lab.json: {where}（{(batch.get('counts') or {}).get('tried')}通り）")
    cull, cwhere = load_cull(date)
    if any(cl.get("what") == "cull" for cl in claims.get("claims", [])) and cull is None:
        fails.append(f"{FIXABLE} cull の claim があるのに、{date} に外した記録が method-lab-registry.json に無い"
                     "（research_rotation.py daily を先に動かす／外さなかった日は cull の claim を消す）")

    allowed = {"R": [], "%": [], "回": set(CONST_COUNT), "±": []}
    ok = 0
    for cl in claims.get("claims", []):
        label, field = cl.get("label", "?"), cl.get("field")
        act = actual_value(cl, batch, cull)
        if act == "bad":
            fails.append(f"{FIXABLE} [{label}] what={cl.get('what')!r} field={field!r} は使えない")
            continue
        if not same(field, act, cl.get("value")):
            fails.append(f"{FIXABLE} [{label}] {field}: 主張 {cl.get('value')} ≠ 記録 {act}（記録の値に直し、本文・図・30秒まとめも合わせる）")
            continue
        ok += 1
        v = float(cl["value"])
        if field in R_FIELDS or (cl.get("what") == "year" and field == "mean"):
            allowed["R"].append(v)
        elif field == "win":
            allowed["%"].append(v)
        elif field in ("p",):
            allowed["±"].append(v)
            allowed["%"].append(100 * v)
        elif field in ("z", "per_year"):
            allowed["±"].append(v)
            allowed["回"].add(int(round(v)))
        else:
            allowed["回"].add(int(round(v)))
    print(f"  claim {ok}/{len(claims.get('claims', []))} 一致")

    # ③ 本文の数字の出どころ
    text, svg = body_text(html)

    def backed(kind, v, dec, signed):
        if kind == "回":
            return int(round(v)) in allowed["回"]
        pool = allowed["%"] if kind == "%" else allowed["R"] + allowed["±"]
        if any(abs(round(p, dec) - v) < 0.5 * 10 ** -dec + 1e-9 for p in pool):
            return True
        return not signed and ((kind in ("R", "±") and abs(v) in CONST_R) or (kind == "%" and v in CONST_PCT))

    unbacked = []
    for part, in_svg in ((text, False), (svg, True)):
        for kind, v, dec, signed, ctx in numbers_in(part):
            if in_svg and kind == "±" and dec == 1:
                continue
            if not backed(kind, v, dec, signed):
                unbacked.append(f"{v:+g}{'' if kind == '±' else kind}（…{ctx.strip()}…）")
    for u in unbacked:
        fails.append(f"{FIXABLE} 出どころの無い数字: {u} → claim に入れる（method-lab.json から取る）か、本文から消す")

    # ④ ためした数
    if not any(cl.get("what") == "batch" and cl.get("field") == "tried" for cl in claims.get("claims", [])):
        fails.append(f"{FIXABLE} 今日ためした数（batch・tried）の claim が無い。本文に「今日は◯通りを試した」と書き、claim に入れる")
    # ⑤ 言い方
    for pat, why in BANNED:
        for m in re.finditer(pat, text):
            if NEGATED.match(text, m.end()):
                continue
            fails.append(f"{FIXABLE} 言い方「{text[max(0, m.start() - 10):m.end() + 6].strip()}」: {why}。起きたことだけを書く")
    # ⑥ 断り書き
    for word, why in (("偶然", "たくさん試すと偶然よく見えるものが混じることの断り"),
                      ("前向き", "登録した日より後のシグナルで確かめることの断り")):
        if word not in text:
            fails.append(f"{FIXABLE} 断り書きが無い:「{word}」（{why}）")
    # ⑦ 登録の書き方
    status = ((batch.get("chosen") or {}).get("status"))
    if status == "near_miss" and re.search(r"登録しました|登録した(?!日)", text):
        fails.append(f"{FIXABLE} 今日の方法は合格していない（惜しかった方法）のに「登録しました」と書いている")
    if status == "passed" and "登録" not in text:
        fails.append(f"{FIXABLE} 今日の方法は合格して前向きに登録した。本文に「登録」の一言を書く")
    # ⑧ 差し込みの目印
    raw = rd(sys.argv[1])
    for mk in MARKERS:
        if f"<!-- MW:{mk} -->" not in raw:
            fails.append(f"{FIXABLE} 差し込みの目印 <!-- MW:{mk} --> が無い（書いてから research_rotation.py report --into で差し込む）")

    print(f"--- 出どころの無い数字 {len(unbacked)}件 ---")
    if fails:
        print("RED:")
        for f in fails:
            print("   - " + f)
        print(f"→ 赤はすべて {FIXABLE}。指示どおり直して再実行（数字は method-lab.json から取り直す・最大3回）。緑にならなければエスカレ")
        sys.exit(1)
    print("GREEN（毎日の新しい方法の数字・言い方とも自動公開条件を満たす）")
    sys.exit(0)


if __name__ == "__main__":
    main()
