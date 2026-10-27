# -*- coding: utf-8 -*-
"""TDnet の適時開示を毎日ためて、高値更新の台帳（J44）のケースに「その前30日の開示」を付ける（読むだけ・判定しない）。
2026-10-27 オーナー「残りも二つとも進めてください」＝10/26 の候補「TDnet の開示一覧（買収・提携・自社株買い・業績修正などの
見出し）を Actions で毎日ためて、台帳のケースに『その前30日の開示』を付ける」。PILLAR_PREREG.md「J44」の 10/27 の追記。

- 取る：TDnet の開示一覧（https://www.release.tdnet.info/inbs/I_list_NNN_YYYYMMDD.html）。TDnet は約1か月しか残らないので、
  毎日、まだ取っていない日（さかのぼれる範囲）と、直近2日（夜遅くの開示の取りこぼし）を取る
- 分ける：表題の決まった言葉で種類（TAGS）を付ける。業績予想の修正と「予想と実績の差異」は PDF の表（前回予想→今回予想／
  予想→実績）から向きを読む（読めなければ「向き不明」）
- ためる：`tdnet-events.csv`＝種類の付いた開示だけ（日付・時刻・コード・種類・向き・PDF の番号。表題と会社名は置かない）／
  `tdnet-days.json`＝日ごとの件数と取った時刻（どの日を取り終えたか）
- 付ける：`highs-tdnet.csv`＝台帳のケース（日付・コード）ごとに、その日の引け（15:30）までの30暦日の種類ごとの件数と、
  その日の引けのあと（15:30 以降）の種類。窓の全部の日を取り終えていないケースは td_cover＝0
- 読む：`highs-tdnet.md`＝取れた範囲・上場来高値のケースの種類ごとの件数と、台帳の5日後・20取引日あとの読むための表（判定しない）

⚠️ 読むだけ。目立った種類を決まりにするなら、別に事前登録して後のケースで確かめる（J44 と同じ）。
⚠️ 出力は GitHub 側で生成＝ローカルから push しない（SYNC禁忌）。表題そのものは置かない（種類と向きだけ）。

実行: python tdnet_events.py            （取る＋付ける。Actions の tdnet-events.yml から）
      python tdnet_events.py --attach   （付けるだけ。取らない）
"""
import csv
import datetime as dt
import html
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time
import unicodedata
import urllib.request

BASE = "https://www.release.tdnet.info/inbs/"
UA = {"User-Agent": "Mozilla/5.0"}
JST = dt.timezone(dt.timedelta(hours=9))
EVENTS_CSV, DAYS_JSON = "tdnet-events.csv", "tdnet-days.json"
LEDGER = "highs-ledger.csv"
OUT_CSV, OUT_MD = "highs-tdnet.csv", "highs-tdnet.md"
LEDGER_FROM = "2026-10-08"
BACK_DAYS = 45                 # さかのぼって探す暦日（TDnet は約1か月＋α 残る）
REFRESH_DAYS = 2               # 取り終えた日でも、直近のこの暦日数は取り直す（夜遅くの開示）
WINDOW = 30                    # その前30暦日
CLOSE = "15:30"                # 引け（これ以降の開示は「その日の引けのあと」）
PER_PAGE = 100
PAUSE = 0.25
EVENT_COLS = ("date", "time", "code", "tags", "dir", "doc")

# (種類, 表題の言葉, 除く言葉)。上から順に全部見る（1つの開示に複数の種類が付く）
TAGS = (
    ("決算", r"決算短信", None),
    ("業績修正", r"業績予想.{0,20}修正|業績.{0,4}修正|(連結|個別|通期|半期|四半期)\)?.{0,6}予想.{0,4}修正|上方修正|下方修正", r"分配"),
    ("差異", r"予想.{0,14}実績.{0,6}差異|予想値.{0,6}差異|実績.{0,4}差異", r"分配"),
    ("増配", r"増配|記念配当|特別配当", None),
    ("減配", r"減配|無配", None),
    ("自社株買い", r"自己株式.{0,8}(取得|買付).{0,24}(決定|に関するお知らせ$)|立会外買付|自己株式の公開買付", r"取得状況|取得結果|取得終了|進捗|処分|無償取得"),
    ("自社株買いの進み", r"自己株式.{0,8}取得(状況|結果|終了)|自己株式取得.{0,8}進捗", None),
    ("自己株式の消却", r"自己株式.{0,4}消却", None),
    ("M&A", r"子会社化|株式.{0,2}取得|事業.{0,4}譲(受|り受)|吸収合併|経営統合|株式交換|株式移転|公開買付け.{0,6}(開始|実施)|買収", r"自己株式"),
    ("TOB・上場廃止", r"公開買付け.{0,20}(賛同|意見表明)|上場廃止|MBO|マネジメント・バイアウト|スクイーズアウト|株式併合", None),
    ("提携", r"業務提携|資本提携|資本業務提携|業務・資本提携", None),
    ("増資・売出し", r"売出し|公募|新株式発行|第三者割当による新株|新株予約権.{0,12}(発行|割当)|新株予約権付社債",
     r"自己株式の処分|譲渡制限付株式報酬|株式報酬|ストック・?オプション|払込完了|行使"),
    ("大株主の異動", r"主要株主|筆頭株主|大株主|その他の関係会社の異動|親会社.{0,6}異動|大量保有", None),
    ("株主総会・提案", r"臨時株主総会|株主提案|招集請求|招集許可|委任状", None),
    ("中期計画", r"中期経営計画|中計|成長ロードマップ|長期ビジョン", None),
    ("株主還元の方針", r"株主還元|配当方針|資本政策|キャピタルアロケーション|資本コスト", None),
    ("株式分割", r"株式分割", None),
    ("特別利益", r"特別利益|売却益", None),
    ("特別損失", r"特別損失|減損|評価損", None),
    ("不祥事・事故・調査", r"不適切|調査委員会|第三者委員会|不正|過年度.{0,8}訂正|改善報告書|特別注意銘柄|事故|漏えい|漏洩", None),
)
DIR_TAGS = ("業績修正", "差異")
SKIP_TITLE = r"ETF|ＥＴＦ|ETN|ＥＴＮ|投資法人|投資信託|受益証券|日々の開示事項|分配金"
# 付ける列＝その日の引けまでの30暦日の件数（向きの付く種類は向きで分ける）
COUNT_COLS = ("上方修正", "下方修正", "修正・向き不明", "上振れ", "下振れ", "差異・向き不明") + \
    tuple(t for t, *_ in TAGS if t not in DIR_TAGS)
OUT_COLS = ("date", "code", "kind", "td_cover", "td_from", "td_n30", "td_earn_days") + tuple(f"td_{c}" for c in COUNT_COLS) + ("td_after",)


# ════════════════════ 取る ════════════════════

def get(url, tries=3, timeout=30, binary=False):
    for k in range(tries):
        try:
            raw = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()
            return raw if binary else raw.decode("utf-8", "ignore")
        except Exception:  # noqa: BLE001
            time.sleep(1 + 2 * k)
    return None


def _cell(row, cls):
    m = re.search(r'class="[^"]*\b' + cls + r'\b[^"]*"[^>]*>(.*?)</td>', row, re.S)
    return html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip() if m else ""


def parse_list(page):
    """一覧の1ページ → (全件数, [{time, code, name, title, doc, place}])。純関数"""
    m = re.search(r"全\s*(\d+)\s*件", page or "")
    total = int(m.group(1)) if m else 0
    rows = []
    for r in re.findall(r"<tr>(.*?)</tr>", page or "", re.S):
        if "kjCode" not in r:
            continue
        link = re.search(r'href="([^"]+)\.pdf"', r)
        code5 = _cell(r, "kjCode")
        rows.append({"time": _cell(r, "kjTime"), "code": code5[:4], "name": _cell(r, "kjName"), "title": _cell(r, "kjTitle"),
                     "doc": link.group(1) if link else "", "place": _cell(r, "kjPlace")})
    return total, rows


def fetch_day(day, getter=get, pause=PAUSE):
    """→ (全件数, 行) または None（1ページ目が取れない＝その日はまだ無い・もう消えた）"""
    first = getter(f"{BASE}I_list_001_{day:%Y%m%d}.html")
    if first is None:
        return None
    total, rows = parse_list(first)
    for n in range(2, math.ceil(total / PER_PAGE) + 1):
        time.sleep(pause)
        page = getter(f"{BASE}I_list_{n:03d}_{day:%Y%m%d}.html")
        if page is None:
            return None                          # 途中のページが取れない日は「取り終えていない」
        rows += parse_list(page)[1]
    return total, rows


# ════════════════════ 分ける ════════════════════

def tags_of(title):
    """表題 → 種類の一覧。純関数"""
    t = unicodedata.normalize("NFKC", title or "")
    if re.search(SKIP_TITLE, t):
        return []
    out = []
    for tag, pat, ex in TAGS:
        if re.search(pat, t) and not (ex and re.search(ex, t)):
            out.append(tag)
    return out


def title_direction(title):
    t = unicodedata.normalize("NFKC", title or "")
    if "上方修正" in t:
        return "上方"
    if "下方修正" in t:
        return "下方"
    return None


_NUM = re.compile(r"[△▲\-−]?\s?\d[\d,]*(?:\.\d+)?|(?<![\d,])[―\-—](?![\d,])")
_DATE_TAIL = re.compile(r"^\s*(年|月|日|期|四半期|頁|億|社)")


def _norm(text):
    """全角→半角・数字の間の1文字の空白を詰める（「１ ２ ５ ,０ ０ ０」→「125,000」。列の間の2つ以上の空白は残す）"""
    t = unicodedata.normalize("NFKC", text)
    return re.sub(r"(?<=[\d,.])\s(?=[\d,.])", "", t)


def nums(text):
    """数字（△▲−はマイナス）と「－」（値なし＝None）を順に。日付・単位の前の数字は除く。純関数"""
    out = []
    for m in _NUM.finditer(text):
        tok = m.group(0).replace(" ", "")
        if _DATE_TAIL.match(text[m.end():m.end() + 3]):
            continue
        if tok in ("―", "-", "—"):
            out.append(None)
            continue
        neg = tok[0] in "△▲-−"
        try:
            v = float(tok.lstrip("△▲-−").replace(",", ""))
        except ValueError:
            continue
        out.append(-v if neg else v)
    return out


_LABEL = re.compile(r"[(]\s*[AB]\s*[)]")
_A = re.compile(r"前\s*回\s*(発\s*表\s*)?(予\s*想|公\s*表)|予\s*想\s*値|^\s*予\s*想\s*[(]")
_B_REV = re.compile(r"今\s*回\s*(修\s*正|発\s*表)?\s*予\s*想|今\s*回\s*修\s*正")
_B_ACT = re.compile(r"実\s*績\s*値?\s*[(]|実\s*績\s*値")
_END = re.compile(r"増\s*減\s*額|増\s*減\s*率|前\s*期\s*実\s*績|ご\s*参\s*考|前\s*年\s*同")


def tables(text):
    """PDF の文字 → [(種類 "修正"/"差異", 前の行の数字, 後の行の数字, 表の前の4行)]。純関数"""
    lines = _norm(text).split("\n")
    res, i = [], 0
    while i < len(lines):
        if not _A.search(lines[i]):
            i += 1
            continue
        j = next((k for k in range(i + 1, min(i + 8, len(lines))) if _B_REV.search(lines[k]) or _B_ACT.search(lines[k])), None)
        if j is None:
            i += 1
            continue
        kind = "修正" if _B_REV.search(lines[j]) else "差異"
        k = next((x for x in range(j + 1, min(j + 8, len(lines))) if _END.search(lines[x])), min(j + 3, len(lines)))
        a = nums(_LABEL.sub("", " ".join(lines[i:j])))
        b = nums(_LABEL.sub("", " ".join(lines[j:k])))
        res.append((kind, a, b, " ".join(lines[max(0, i - 4):i])))
        i = k
    return res


def _dir(a, b):
    """営業利益（2列目）→ 経常（3列目）→ 純利益（4列目）の順に、変わった最初の列の向き"""
    if len(a) < 4 or len(b) < 4:
        return None
    seen = False
    for col in (1, 2, 3):
        x, y = a[col], b[col]
        if x is None or y is None:
            continue
        seen = True
        if y != x:
            return "上方" if y > x else "下方"
    return "横ばい" if seen else None


def pdf_direction(text, kind):
    """kind＝"修正"／"差異" → "上方"/"下方"/"横ばい"/None。修正は「通期」と書かれた表を先に、無ければ最初の表"""
    ts = [t for t in tables(text) if t[0] == kind]
    ts.sort(key=lambda t: 0 if "通期" in t[3] else 1)
    for _, a, b, _ in ts:
        d = _dir(a, b)
        if d:
            return d
    return None


def pdf_text(doc, getter=get):
    """PDF を取って pdftotext -layout の文字に（取れなければ ""）"""
    raw = getter(f"{BASE}{doc}.pdf", binary=True)
    if not raw:
        return ""
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "a.pdf")
        with open(p, "wb") as fh:
            fh.write(raw)
        try:
            subprocess.run(["pdftotext", "-layout", p, p + ".txt"], capture_output=True, timeout=60)
            with open(p + ".txt", encoding="utf-8", errors="ignore") as fh:
                return fh.read()
        except (OSError, subprocess.SubprocessError):
            return ""


def classify(row, reader=None):
    """一覧の1行 → events の1行（種類が無ければ None）。reader(doc)→PDF の文字（向きを読むときだけ呼ぶ）"""
    tags = tags_of(row["title"])
    if not tags:
        return None
    d = ""
    if "業績修正" in tags:
        d = title_direction(row["title"]) or (pdf_direction(reader(row["doc"]), "修正") if reader and row["doc"] else None) or "不明"
    elif "差異" in tags:
        d = (pdf_direction(reader(row["doc"]), "差異") if reader and row["doc"] else None) or "不明"
    return {"time": row["time"], "code": row["code"], "tags": "|".join(tags), "dir": d, "doc": row["doc"]}


# ════════════════════ ためる ════════════════════

def read_events(path=EVENTS_CSV):
    try:
        with open(path, encoding="utf-8-sig") as fh:
            return list(csv.DictReader(fh))
    except OSError:
        return []


def write_events(rows, path=EVENTS_CSV):
    rows = sorted(rows, key=lambda r: (r["date"], r["time"], r["code"], r["doc"]))
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=EVENT_COLS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in EVENT_COLS})


def read_days(path=DAYS_JSON):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {"days": {}}


def collect(today, events, days, getter=get, reader=None, back=BACK_DAYS, refresh=REFRESH_DAYS, log=print):
    """まだ取っていない日（さかのぼれる範囲）と直近の日を取り、events と days を更新して返す"""
    known = {(r["date"], r["doc"]): r for r in events}
    for k in range(back, -1, -1):
        day = today - dt.timedelta(days=k)
        key = day.isoformat()
        if day.weekday() >= 5:
            continue
        if key in days["days"] and k > refresh:
            continue
        got = fetch_day(day, getter)
        if got is None:
            continue
        total, rows = got
        if total == 0 and k > refresh:
            days["days"][key] = {"total": 0, "tagged": 0, "at": dt.datetime.now(JST).isoformat(timespec="minutes")}
            continue
        if total == 0:
            continue                                # 今日・昨日の0件は「まだ」かもしれない＝取り終えた扱いにしない
        new = []
        for r in rows:
            old = known.get((key, r["doc"]))
            if old and old.get("dir") not in ("不明",):
                new.append(old)                     # 取り直しでも PDF は読み直さない
                continue
            e = classify(r, reader)
            if e:
                new.append(dict(e, date=key))
        events = [e for e in events if e["date"] != key] + new
        known.update({(key, e["doc"]): e for e in new})
        days["days"][key] = {"total": total, "tagged": len(new), "at": dt.datetime.now(JST).isoformat(timespec="minutes")}
        log(f"  {key}: 全{total}件・種類つき{len(new)}件")
    return events, days


# ════════════════════ 付ける ════════════════════

def covered(day_iso, days):
    """day の前30暦日〜day の平日をすべて取り終えているか"""
    d = dt.date.fromisoformat(day_iso)
    for k in range(WINDOW + 1):
        x = d - dt.timedelta(days=k)
        if x.weekday() < 5 and x.isoformat() not in days["days"]:
            return False
    return True


def attach_one(date, code, kind, by_code, days):
    """台帳の1ケース → highs-tdnet.csv の1行"""
    d = dt.date.fromisoformat(date)
    lo = (d - dt.timedelta(days=WINDOW)).isoformat()
    pre, after = [], []
    for e in by_code.get(code, ()):
        if lo < e["date"] < date or (e["date"] == date and e["time"] < CLOSE):
            pre.append(e)
        elif e["date"] == date and e["time"] >= CLOSE:
            after.append(e)
    cnt = {c: 0 for c in COUNT_COLS}
    earn = None
    for e in pre:
        for t in e["tags"].split("|"):
            if t == "業績修正":
                cnt[{"上方": "上方修正", "下方": "下方修正"}.get(e["dir"], "修正・向き不明")] += 1
            elif t == "差異":
                cnt[{"上方": "上振れ", "下方": "下振れ"}.get(e["dir"], "差異・向き不明")] += 1
            elif t in cnt:
                cnt[t] += 1
            if t == "決算":
                earn = (d - dt.date.fromisoformat(e["date"])).days if earn is None else min(earn, (d - dt.date.fromisoformat(e["date"])).days)
    out = {"date": date, "code": code, "kind": kind, "td_cover": int(covered(date, days)),
           "td_from": min(days["days"]) if days["days"] else "", "td_n30": len(pre), "td_earn_days": "" if earn is None else earn}
    out.update({f"td_{c}": cnt[c] for c in COUNT_COLS})
    out["td_after"] = "|".join(sorted({(t + ("・" + e["dir"] if t in DIR_TAGS and e["dir"] else "")) for e in after for t in e["tags"].split("|")}))
    return out


def attach(ledger_rows, events, days):
    by_code = {}
    for e in events:
        by_code.setdefault(e["code"], []).append(e)
    seen, out = set(), []
    for r in ledger_rows:
        if r.get("date", "") < LEDGER_FROM or (r["date"], r["code"]) in seen:
            continue
        seen.add((r["date"], r["code"]))
        out.append(attach_one(r["date"], r["code"], r.get("kind", ""), by_code, days))
    return out


def write_attached(rows, path=OUT_CSV):
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=OUT_COLS)
        w.writeheader()
        for r in rows:
            w.writerow(r)


# ════════════════════ 読む ════════════════════

def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


GROUPS = (("上方修正あり", lambda a: a["td_上方修正"] > 0), ("下方修正あり", lambda a: a["td_下方修正"] > 0),
          ("決算から5日以内", lambda a: a["td_earn_days"] != "" and int(a["td_earn_days"]) <= 5),
          ("自社株買いの決定", lambda a: a["td_自社株買い"] > 0), ("M&A・提携", lambda a: a["td_M&A"] + a["td_提携"] > 0),
          ("増配", lambda a: a["td_増配"] > 0), ("株主総会・提案・大株主の異動", lambda a: a["td_株主総会・提案"] + a["td_大株主の異動"] > 0),
          ("30日の種類つきの開示なし", lambda a: a["td_n30"] == 0))


def render_md(attached, ledger_rows, events, days, now=""):
    led = {(r["date"], r["code"]): r for r in ledger_rows}
    ath = [a for a in attached if a["kind"] in ("記録上の最高値", "上場来") and a["td_cover"]]
    dd = sorted(days["days"])
    L = ["# 高値更新の台帳 × TDnet の開示（その前30日・読むだけ）", "",
         f"更新: {now}（`tdnet_events.py`・J44 の 2026-10-27 の追記）", "",
         "- TDnet の開示一覧を毎日ため、表題の言葉で種類を付けた（業績予想の修正と「予想と実績の差異」は PDF の表から向きを読む）",
         "- 台帳のケースごとに、その日の引け（15:30）までの30暦日の開示の種類を数えた。15:30 以降の開示は「引けのあと」に分けた",
         "- ⚠️ 読むだけ・判定しない。目立った種類を決まりにするなら、別に事前登録して後のケースで確かめる。過去の成績は将来を約束しない", "",
         "## 取れた範囲", "",
         f"- 取り終えた日：{dd[0] if dd else '—'} 〜 {dd[-1] if dd else '—'}（{len(dd)}日・開示 {sum(v['total'] for v in days['days'].values()):,}件・種類つき {len(events):,}件）",
         f"- 業績修正の向き：上方 {sum(1 for e in events if '業績修正' in e['tags'] and e['dir'] == '上方')}・"
         f"下方 {sum(1 for e in events if '業績修正' in e['tags'] and e['dir'] == '下方')}・"
         f"横ばい {sum(1 for e in events if '業績修正' in e['tags'] and e['dir'] == '横ばい')}・"
         f"向き不明 {sum(1 for e in events if '業績修正' in e['tags'] and e['dir'] == '不明')}",
         f"- 台帳のケース {len(attached)}件のうち、30日の窓を全部取り終えたもの {sum(a['td_cover'] for a in attached)}件"
         f"（上場来高値 {len(ath)}件）。TDnet は約1か月しか残らないので、取り始め（{dd[0] if dd else '—'}）から30日より前のケースは窓が欠ける", ""]
    L += ["## 上場来高値（記録上の最高値）のケース：その前30日の開示の種類（読むための表・判定しない）", "",
          "| 種類 | 件数 | 5日後 続伸 | 5日後 だまし | 20取引日あと埋まった | TOPIX比の平均（20取引日） |", "|---|---:|---:|---:|---:|---:|"]
    for name, f in GROUPS:
        xs = [a for a in ath if f(a)]
        lab = [led.get((a["date"], a["code"]), {}).get("label5", "") for a in xs]
        lab = [x for x in lab if x]
        ex = [_f(led.get((a["date"], a["code"]), {}).get("ex20")) for a in xs]
        ex = [x for x in ex if x is not None]
        L.append(f"| {name} | {len(xs)} | {sum(x == '続伸' for x in lab)}/{len(lab)} | {sum(x == 'だまし' for x in lab)}/{len(lab)} | "
                 f"{len(ex)} | {('—' if not ex else f'{sum(ex) / len(ex) * 100:+.1f}％')} |")
    recent = sorted({a["date"] for a in ath})[-5:]
    L += ["", "## 最近の上場来高値のケース（その前30日の種類・引けのあと）", "", "| 日付 | コード | 銘柄 | 30日の種類 | 引けのあと |", "|---|---|---|---|---|"]
    for a in sorted([a for a in ath if a["date"] in recent], key=lambda a: (a["date"], a["code"]), reverse=True):
        kinds = "・".join(f"{c}{a['td_' + c]}" for c in COUNT_COLS if a["td_" + c]) or "—"
        L.append(f"| {a['date']} | {a['code']} | {led.get((a['date'], a['code']), {}).get('name', '')} | {kinds} | {a['td_after'] or '—'} |")
    return "\n".join(L) + "\n"


def main(argv):
    today = dt.datetime.now(JST).date()
    events, days = read_events(), read_days()
    if "--attach" not in argv:
        events, days = collect(today, events, days, reader=pdf_text)
        write_events(events)
        with open(DAYS_JSON, "w", encoding="utf-8") as fh:
            json.dump(days, fh, ensure_ascii=False, indent=1, sort_keys=True)
    try:
        with open(LEDGER, encoding="utf-8-sig") as fh:
            ledger_rows = list(csv.DictReader(fh))
    except OSError:
        ledger_rows = []
    attached = attach(ledger_rows, events, days)
    write_attached(attached)
    md = render_md(attached, ledger_rows, events, days, now=dt.datetime.now(JST).isoformat(timespec="minutes"))
    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write(md)
    print(md[:3000])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
