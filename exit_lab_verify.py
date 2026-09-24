# -*- coding: utf-8 -*-
"""
exit_lab_verify.py — 研究日誌「出口の相性」回の数字を exit-lab.json と突き合わせる固定オラクル（2026-09-24 新設）。

signal_lab_verify.py は signals-log.json（エンジンの実際の記録）から k/n を計算し直す。
出口の相性の数字（平均R・いまの方式との差）は、Actions が価格から計算した exit-lab.json にしか無いので、ここで照合する。
⚠️ routine・エージェントは編集しない（signal_lab_verify.py と同じ固定コード。実行前に git checkout -- exit_lab_verify.py）。
   直すのは下書きと exit-claims.json のほう。

使い方: python exit_lab_verify.py <draft.html> <exit-claims.json> [--signal-claims <claims.json>]
  --signal-claims … 同じ記事の signal_lab_verify 用 claims.json。その k/n・勝率%・件数も本文に出てよい数字として数える。

exit-claims.json の形:
{
  "article_id": "110",
  "exit_lab_asof": "2026-09-27",          # 使った exit-lab.json の "asof"（週1で変わる）
  "claims": [
    {"label": "−2σタッチの買い・ATR損切り・利確なし", "tf": "1d", "entry": "bb_lower_touch", "side": "long",
     "sl": "atr", "tp": "none", "period": "is", "field": "vs_base", "value": 0.27}
  ]
}
field に使えるもの: FIELDS（下）。R の値は小数2桁、win は % で小数1桁（例 38.5）、件数は整数、flag は true/false。

検査（どれも赤＝公開しない）:
 ① exit_lab_asof の exit-lab.json を探す（いまの版 → 無ければ git の履歴）。
 ② claim ごとに値が exit-lab.json と一致する。
 ③ 本文の数字の出どころ: 前向きトラッカー表を除いた本文（図の文字も含む）に出る
    「符号つきの小数（+0.21 / −0.05）」「◯R」「◯%」「◯件」は、どれかの claim の値か、決まった定数でなければ赤。
    図の目盛り（図の中の小数1桁の符号つきの数）は許す。
 ④ 良い組だけを並べない: ある入口の表から組を引くとき、その表に「いまの方式より良い組」と「悪い組」の両方があるなら、
    claim にも両方を入れる。
 ⑤ 言い方: 「この出口が合う」「おすすめ」「推奨」「最適」「ベスト」「〜べき」「相性が良い」などは赤。
 ⑥ 断り書き: 「偶然」と「前向き」の両方が本文にある（組み合わせが多いぶん偶然で良く見えること／前向きで確かめること）。
 ⑦ 本文で「目立つ」と書くなら、flag の claim を1つ以上入れる（目立つ／目立たないの根拠をはっきりさせる）。
赤は exit-lab.json が見つからないとき以外すべて [直せる]（数字は exit-lab.json から取り直す／言い方を変える／断りを足す）。
"""
import json
import math
import os
import re
import subprocess
import sys

from signal_lab_verify import wilson

ROOT = os.path.dirname(os.path.abspath(__file__))
LAB_PATH = os.path.join(ROOT, "exit-lab.json")
FIXABLE = "[直せる]"
BASE = ("atr", "atr2")

R_FIELDS = {"avg", "lo", "hi", "p5", "worst", "vs_base", "vs_base_lo", "vs_base_hi", "risk_atr_median"}
FIELDS = R_FIELDS | {"win", "n", "n_entries", "flag", "bars_median"}
CONST_R = {0.1, 0.15, 0.3, 0.5, 1.0, 1.3, 1.5, 2.0, 3.0}         # 定義に出る R（1R・0.15R など）
CONST_PCT = {0.0, 5.0, 10.0, 25.0, 30.0, 43.0, 50.0, 70.0, 75.0, 95.0, 100.0}
CONST_COUNT = {0, 100}
# ⑤ 言い方。「出口の相性」という連載名そのものは許す（相性＋良い/悪いの評価を止める）
BANNED = [
    (r"(?:が|に|と)合う|合っている|合います|合いそう", "「合う」＝この入口にはこの出口、と読める"),
    (r"相性(?:が|の)?(?:良|よ|いい|抜群|ばっちり|悪|わる)", "相性の良し悪しを言い切っている"),
    (r"おすすめ|オススメ|お勧め|推奨|最適|ベスト|一択|使うべき|選ぶべき|べきです|べきだ", "推奨・断定の言い方"),
    (r"必ず(?:勝|儲|利益)|儲か|確実に|保証", "利益を約束する言い方"),
]
REQUIRED = [("偶然", "組み合わせが多いぶん偶然で良く見えることの断り"),
            ("前向き", "前向き（これから出るシグナル）で確かめることの断り")]
SKIP_AFTER = re.compile(r"\s*(?:ATR|σ|倍|本|年|日|時間|か月|ヶ月|週|銘柄|つ)")
# 打ち消し（免責の「売買推奨ではありません」「成果を保証するものではありません」）は言い方の検査から外す
NEGATED = re.compile(r"[^。]{0,14}?(?:ではあり|ではな|ではご|するものではな|しません|しない|できません)")


def load_lab(asof):
    """asof が一致する exit-lab.json（いまの版 → git の履歴）を返す。見つからなければ None。"""
    if os.path.exists(LAB_PATH):
        cur = json.load(open(LAB_PATH, encoding="utf-8"))
        if cur.get("asof") == asof:
            return cur, "いまの版"
    try:
        shas = subprocess.run(["git", "log", "--format=%H", "-n", "80", "--", "exit-lab.json"], cwd=ROOT,
                              capture_output=True, text=True, check=True).stdout.split()
    except Exception:
        shas = []
    for sha in shas:
        try:
            txt = subprocess.run(["git", "show", f"{sha}:exit-lab.json"], cwd=ROOT, capture_output=True,
                                 text=True, check=True).stdout
            d = json.loads(txt)
        except Exception:
            continue
        if d.get("asof") == asof:
            return d, f"履歴 {sha[:7]}"
    return None, None


def cell_key(c):
    return (c.get("tf"), c.get("entry"), c.get("side"), c.get("sl"), c.get("tp"), c.get("period"))


def field_value(cell, field):
    vb = cell.get("vs_base") or {}
    if field == "vs_base":
        return vb.get("avg")
    if field == "vs_base_lo":
        return vb.get("lo")
    if field == "vs_base_hi":
        return vb.get("hi")
    if field == "win":
        return None if cell.get("win") is None else 100 * cell["win"]
    if field == "flag":
        return bool(cell.get("flag", False))
    return cell.get(field)


def same(field, actual, claimed):
    if actual is None or claimed is None:
        return False
    if field == "flag":
        return bool(claimed) == actual
    if field in ("n", "n_entries"):
        return int(claimed) == int(actual)
    if field == "win":
        return abs(round(actual, 1) - float(claimed)) < 0.051
    if field == "bars_median":
        return abs(float(actual) - float(claimed)) < 0.51
    return abs(round(actual, 2) - float(claimed)) < 0.0051


def body_text(html):
    """数字を拾う本文。head・script・style と、前向きトラッカー表（表の見方〜表の終わり）は除く。"""
    tracker = ""
    m = re.search(r"data-mw-tracker-legend", html)
    if m:
        end = html.find("</table>", m.end())
        if end > 0:
            start = html.rfind("<", 0, m.start())
            tracker = html[start:end + len("</table>")]
            html = html[:start] + html[end + len("</table>"):]
    html = re.sub(r"<head\b.*?</head>|<script\b.*?</script>|<style\b.*?</style>", " ", html, flags=re.S | re.I)
    svg_parts = re.findall(r"<svg\b.*?</svg>", html, flags=re.S | re.I)
    text = re.sub(r"<svg\b.*?</svg>", " ", html, flags=re.S | re.I)
    clean = lambda h: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h)).replace("&minus;", "-")
    norm = lambda t: t.replace("−", "-").replace("－", "-").replace("＋", "+").replace("％", "%")
    return norm(clean(text)), norm(clean(" ".join(svg_parts))), norm(clean(tracker))


def _num(s):
    return float(s.replace(",", ""))


def numbers_in(text):
    """(種類, 値, 小数の桁数, 符号の有無, 前後の文字) を返す。"""
    out = []
    for m in re.finditer(r"(?<![\d.])([+\-]?)(\d[\d,]*(?:\.\d+)?)\s*(R(?![A-Za-z])|%|件)?", text):
        sign, num, unit = m.group(1), m.group(2), m.group(3) or ""
        dec = len(num.split(".")[1]) if "." in num else 0
        v = _num(num) * (-1 if sign == "-" else 1)
        ctx = text[max(0, m.start() - 12):m.end() + 8]
        if unit == "R":
            out.append(("R", v, dec, bool(sign), ctx))
        elif unit == "%":
            out.append(("%", v, dec, bool(sign), ctx))
        elif unit == "件":
            out.append(("件", v, dec, bool(sign), ctx))
        elif sign and dec > 0 and not SKIP_AFTER.match(text, m.end()):
            out.append(("±", v, dec, True, ctx))
    return out


def main():
    argv = sys.argv[1:]
    sig_claims_path = None
    if "--signal-claims" in argv:
        i = argv.index("--signal-claims")
        sig_claims_path = argv[i + 1] if i + 1 < len(argv) else None
        argv = argv[:i] + argv[i + 2:]
    if len(argv) < 2:
        print("usage: python exit_lab_verify.py <draft.html> <exit-claims.json> [--signal-claims <claims.json>]")
        sys.exit(2)
    rd = lambda p: open(p if os.path.isabs(p) else os.path.join(ROOT, p), encoding="utf-8-sig").read()
    html = rd(argv[0])
    claims = json.loads(rd(argv[1]))
    fails, fatal = [], []

    asof = claims.get("exit_lab_asof")
    lab, where = load_lab(asof)
    print(f"=== exit_lab_verify: article #{claims.get('article_id', '?')} / exit_lab_asof={asof} ===")
    if lab is None:
        if os.path.exists(LAB_PATH):
            now = json.load(open(LAB_PATH, encoding="utf-8")).get("asof")
            fails.append(f"{FIXABLE} exit_lab_asof={asof} の exit-lab.json が見つからない。いまの版（asof={now}）に合わせて "
                         f"exit_lab_asof を書き換え、claims の数字をいまの版から取り直す")
        else:
            fatal.append("exit-lab.json が無い（Actions の exit-lab.yml が一度も走っていない）")
        for f in fails + fatal:
            print(f"  ❌ {f}")
        print("RED（要人間レビュー）" if fatal else f"→ 赤はすべて {FIXABLE}。指示どおり直して再実行（最大3回）")
        sys.exit(1)
    print(f"  exit-lab.json: {where}（{len(lab.get('cells', []))}マス）")
    cells = {cell_key(c): c for c in lab.get("cells", [])}

    # ② claim ごとの一致
    allowed = {"R": [], "%": [], "件": set(CONST_COUNT)}
    claimed_cells = []
    for cl in claims.get("claims", []):
        label, field = cl.get("label", "?"), cl.get("field")
        key = cell_key(cl)
        cell = cells.get(key)
        if field not in FIELDS:
            fails.append(f"{FIXABLE} [{label}] field={field!r} は使えない（使えるもの: {sorted(FIELDS)}）")
            continue
        if cell is None:
            fails.append(f"{FIXABLE} [{label}] そのマスが exit-lab.json に無い {key}（名前の綴り・period を確かめる）")
            continue
        actual = field_value(cell, field)
        if not same(field, actual, cl.get("value")):
            shown = actual if not isinstance(actual, float) else round(actual, 2 if field in R_FIELDS else 1)
            fails.append(f"{FIXABLE} [{label}] {field}: 主張 {cl.get('value')} ≠ exit-lab.json {shown}"
                         f"（exit-lab.json の値に直し、本文・表・図・30秒まとめも合わせる）")
            continue
        print(f"  ✅ {label}: {field}={cl.get('value')}")
        claimed_cells.append(cell)
        if field in R_FIELDS:
            allowed["R"].append(float(cl["value"]))
        elif field == "win":
            allowed["%"].append(float(cl["value"]))
        elif field in ("n", "n_entries"):
            allowed["件"].add(int(cl["value"]))

    # --signal-claims: 同じ記事の signals-log 側の数字（signal_lab_verify が別に照合する）
    if sig_claims_path:
        try:
            sc = json.loads(rd(sig_claims_path))
            for cl in sc.get("claims", []):
                k, n = int(cl.get("k", 0)), int(cl.get("n", 0))
                allowed["件"].update({k, n})
                if n:
                    allowed["%"].append(100 * k / n)
                    allowed["%"].extend(wilson(k, n))   # signal_lab_verify と同じ「偶然のぶれの幅」
        except Exception as e:
            fails.append(f"{FIXABLE} --signal-claims を読めない: {e}")

    # ③ 本文の数字の出どころ
    text, svg, tracker = body_text(html)
    tracker_nums = {round(v, 2) for _k, v, _d, _s, _c in numbers_in(tracker)}

    def backed(kind, v, dec, signed):
        pool = allowed["R"] if kind in ("R", "±") else allowed["%"]
        if kind == "件":
            return int(round(v)) in allowed["件"] or round(v, 2) in tracker_nums
        if any(abs(round(p, dec) - v) < 0.5 * 10 ** -dec + 1e-9 for p in pool):
            return True
        if not signed and ((kind == "R" and abs(v) in CONST_R) or (kind == "%" and v in CONST_PCT)):
            return True
        return round(v, 2) in tracker_nums

    unbacked = []
    for part, in_svg in ((text, False), (svg, True)):
        for kind, v, dec, signed, ctx in numbers_in(part):
            if in_svg and kind == "±" and dec == 1:
                continue   # 図の目盛り（+0.2 / −0.5 など）
            if not backed(kind, v, dec, signed):
                unbacked.append(f"{v:+g}{'' if kind == '±' else kind}（…{ctx.strip()}…）")
    for u in unbacked:
        fails.append(f"{FIXABLE} 出どころの無い数字: {u} → claim に入れる（exit-lab.json から取る）か、本文から消す")

    # ④ 良い組だけを並べない
    blocks = {}
    for c in claimed_cells:
        if (c.get("sl"), c.get("tp")) == BASE:
            continue
        blocks.setdefault((c["tf"], c["entry"], c["side"], c["period"]), set()).add(
            c["sl"] + "/" + c["tp"])
    for (tf, es, side, period), combos in blocks.items():
        in_block = [c for c in lab["cells"] if (c["tf"], c["entry"], c["side"], c["period"]) == (tf, es, side, period)
                    and isinstance(c.get("vs_base"), dict) and c["vs_base"].get("avg") is not None]
        signs_all = {c["vs_base"]["avg"] > 0 for c in in_block}
        signs_claimed = {c["vs_base"]["avg"] > 0 for c in in_block if c["sl"] + "/" + c["tp"] in combos}
        if len(signs_all) == 2 and len(signs_claimed) < 2:
            lack = "悪い組（いまの方式より下）" if True in signs_claimed else "良い組（いまの方式より上）"
            fails.append(f"{FIXABLE} {tf}・{es}・{side}（{period}）の組が片側だけ。{lack}も1つ以上 claim と本文に入れる")

    # ⑤ 言い方
    for pat, why in BANNED:
        for m in re.finditer(pat, text):
            if NEGATED.match(text, m.end()):
                continue
            fails.append(f"{FIXABLE} 言い方「{text[max(0, m.start() - 10):m.end() + 6].strip()}」: {why}。"
                         f"「この組では平均が◯◯だった」のように、起きたことだけを書く")
    # ⑥ 断り書き
    for word, why in REQUIRED:
        if word not in text:
            fails.append(f"{FIXABLE} 断り書きが無い:「{word}」（{why}）")
    # ⑦ 目立つ
    if "目立つ" in text and not any(cl.get("field") == "flag" for cl in claims.get("claims", [])):
        fails.append(f"{FIXABLE} 本文に「目立つ」があるのに flag の claim が無い（目立つ／目立たないマスを flag で claim する）")

    print(f"--- claim {len(claimed_cells)}/{len(claims.get('claims', []))} 一致 / 出どころの無い数字 {len(unbacked)}件 ---")
    if fails:
        print("RED:")
        for f in fails:
            print("   - " + f)
        print(f"→ 赤はすべて {FIXABLE}。指示どおり直して再実行（数字は exit-lab.json から取り直す・最大3回）。緑にならなければエスカレ")
        sys.exit(1)
    print("GREEN（出口の相性の数字・言い方とも自動公開条件を満たす）")
    sys.exit(0)


if __name__ == "__main__":
    main()
