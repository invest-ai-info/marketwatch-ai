# -*- coding: utf-8 -*-
"""J40 売り禁・規制はどれくらいかかるか：J31F の売りの対象に、その朝かかっていた規制を前向きで記録する（読むだけ）。
2026-10-08 登録・オーナー「両方登録して進めてください」。PILLAR_PREREG.md「J40」。

--probe＝日本証券金融（売り禁・注意喚起）と日本取引所グループ（増担保規制）の公表資料の場所と形を調べる（見出しと件数だけ）。
--record＝その日の分の記録（PREREG「J40」の追記の読み方・2026-10-08 夕方）。J31F の実行（auction-forward.yml）の前に回す。
日々公表銘柄はすでに毎日取っている jp-margin.json を使う。記録するのはその朝の「寄りで買わない目印」の候補に入る銘柄だけ。

⚠️ probe の表示は見出しと件数だけ（銘柄コードは伏せる・銘柄名の列は件数だけ）。
⚠️ 出力（short-limits.json / .md）は GitHub 側で生成＝手元から送らない（SYNC禁忌）。銘柄は J31F と同じ伏せた印で持つ。

実行: python short_limits.py --probe    （Actions の short-limits.yml から手動で）
      python short_limits.py --record   （Actions の auction-forward.yml から平日に・その日の分を1回）
"""
import datetime as dt
import hashlib
import io
import json
import re
import sys

import jp_taishaku as JT

SITES = (("日本取引所グループ（信用取引の規制＝増担保など）", "https://www.jpx.co.jp/markets/equities/margin-reg/index.html"),
         ("日本取引所グループ（日々公表）", "https://www.jpx.co.jp/markets/equities/margin-daily/index.html"),
         ("日本取引所グループ（注意喚起）", "https://www.jpx.co.jp/markets/equities/alerts/index.html"),
         ("日本証券金融（貸借取引銘柄別制限措置等一覧）", "https://www.taisyaku.jp/restrictive.php"))   # 10/8 1回目の probe で見つけた（いちばん大事＝記録の最後に出す）
KEYWORDS = re.compile(r"申込停止|停止措置|制限措置|注意喚起|増担保|規制|日々公表|品貸|貸借取引|逆日歩")
A_RE = re.compile(r'<a\s[^>]*href="([^"#]+)"[^>]*>(.*?)</a>', re.I | re.S)
FILE_EXT = re.compile(r"\.(csv|xlsx?|pdf|zip|txt)(\?|$)", re.I)
MAX_PAGES = 2                 # 1つの入口から見るページの数（入口ともう1ページ）


def links(html, base):
    """ページの HTML → [(絶対 URL, リンクの文字)]（同じ URL は1回）。純関数"""
    root = re.match(r"https?://[^/]+", base).group(0)
    out, seen = [], set()
    for href, text in A_RE.findall(html):
        href = href.strip()
        if href.startswith(("mailto:", "javascript:")):
            continue
        url = href if href.startswith("http") else root + href if href.startswith("/") else base.rsplit("/", 1)[0] + "/" + href
        if url in seen:
            continue
        seen.add(url)
        out.append((url, re.sub(r"<[^>]+>|\s+", " ", text).strip()))
    return out


def keyword_links(pairs):
    """リンクの文字か URL に規制の言葉があるもの。純関数"""
    return [(u, t) for u, t in pairs if KEYWORDS.search(t) or KEYWORDS.search(u)]


def decode(raw):
    for enc in ("utf-8", "cp932"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


DATE_RE = re.compile(r"^\d{4}[/\-年.]\d{1,2}[/\-月.]\d{1,2}日?$")


def mask(v):
    s = str(v).strip().strip('"').strip()
    return "（コード）" if JT.CODE_RE.match(s) or re.fullmatch(r"\d{4}0?", s) else s[:14]


def mask_row(cells):
    """データの行：コードは伏せ、日付・数字・規制の言葉だけ残し、ほか（銘柄名など）は「…」。見出しの行（コードが無い行）はそのまま"""
    m = [mask(c) for c in cells]
    if "（コード）" not in m:
        return m
    return [c if c == "（コード）" or DATE_RE.match(c) or re.fullmatch(r"[\d.,%％\-]+", c) or KEYWORDS.search(c) or c in ("", "nan") else "…"
            for c in m]


def html_tables(html):
    """ページの表 → [(行数, 見出しの行, 2行目)]（コードは伏せる・2行目は先頭の4つだけ）。純関数"""
    out = []
    for t in re.findall(r"<table.*?</table>", html, re.S | re.I):
        rows = re.findall(r"<tr.*?</tr>", t, re.S | re.I)
        cells = [mask_row([re.sub(r"<[^>]+>|\s+", " ", c).strip() for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", r, re.S | re.I)])
                 for r in rows[:3]]
        out.append((len(rows), cells[0][:10] if cells else [], cells[1][:8] if len(cells) > 1 else []))
    return out


def show_table(url, raw):
    """表の形だけ（先頭3行の見出し・行数・列ごとの値の種類の数）"""
    import pandas as pd
    if re.search(r"\.csv", url, re.I):
        text = decode(raw)
        lines = text.splitlines()
        print(f"    CSV {len(lines)}行")
        for i, line in enumerate(lines[:3]):
            print(f"    {i}行目：{mask_row(line.split(','))[:12]}")
        return
    sheets = pd.read_excel(io.BytesIO(raw), sheet_name=None, dtype=str, header=None)
    for name, df in sheets.items():
        print(f"    表「{name}」：{df.shape[0]}行×{df.shape[1]}列")
        for i in range(min(3, len(df))):
            print(f"    {i}行目：{mask_row(df.iloc[i].tolist())[:12]}")


def probe(get=JT.http):
    for site, top in SITES:
        print(f"\n=== {site}：{top}", flush=True)
        seen_pages = 0
        queue = [(top, "（入口）")]
        visited = set()
        while queue and seen_pages < MAX_PAGES:
            url, why = queue.pop(0)
            if url in visited:
                continue
            visited.add(url)
            seen_pages += 1
            try:
                html = decode(get(url))
            except Exception as e:  # noqa: BLE001
                print(f"  ✕ 取れない {url}（{why}）：{type(e).__name__}: {str(e)[:100]}")
                continue
            title = re.search(r"<title>(.*?)</title>", html, re.S)
            hits = keyword_links(links(html, url))
            print(f"  ▼ {url}（{why}）「{(title.group(1).strip() if title else '')[:40]}」規制の言葉のリンク {len(hits)}件")
            for n, head, second in html_tables(html)[:8]:
                print(f"    表：{n}行・見出し {head}・2行目 {second}")
            files = [(u, t) for u, t in links(html, url) if FILE_EXT.search(u)]
            if files:
                print(f"    資料のリンク {len(files)}件：" + "／".join(f"{t[:20]}→{u.rsplit('/', 1)[-1]}" for u, t in files[:8]))
            for u, t in hits[:30]:
                print(f"    - {t[:50]} → {u}")
            for u, t in hits:
                if FILE_EXT.search(u):
                    continue
                if u.startswith(re.match(r"https?://[^/]+", top).group(0)) and u not in visited and len(queue) < 6 and url == top:
                    queue.append((u, t[:30]))
            for u, t in [h for h in links(html, url) if re.search(r"\.(csv|xlsx?)(\?|$)", h[0], re.I)][:2]:
                try:
                    show_table(u, get(u))
                except Exception as e:  # noqa: BLE001
                    print(f"    ✕ 読めない {u}：{type(e).__name__}: {str(e)[:100]}")
    print("\nprobe だけ（損益は数えていない・何も書き出していない）。読み方は PREREG「J40」の追記に書いてから記録の道具を足す")
    return 0


# ════════════════════ 毎朝の記録（PREREG「J40」の追記） ════════════════════

STATE, OUT_MD = "short-limits.json", "short-limits.md"
JSF_URL = "https://www.taisyaku.jp/restrictive.php"
JPX_URL = "https://www.jpx.co.jp/markets/equities/margin-reg/index.html"
MARGIN, HIGHS = "jp-margin.json", "jp-highs.json"
CATS = ("ban", "jsf_alert", "jsf_other", "zoutanpo", "daily")
CAT_NAMES = {"ban": "売り禁（申込停止）", "jsf_alert": "注意喚起（日本証券金融）", "jsf_other": "その他の措置（日本証券金融）",
             "zoutanpo": "増担保規制（日本取引所グループ）", "daily": "日々公表"}
MARKERS_STALE = 4
DATE_ANY = re.compile(r"(\d{4})[/\-年.](\d{1,2})[/\-月.](\d{1,2})")
JST = dt.timezone(dt.timedelta(hours=9))


def tag(code):
    """J31F（auction_forward.tag）と同じ伏せた印"""
    return hashlib.sha1(("j31f:" + str(code)).encode()).hexdigest()[:10]


def table_rows(html, need):
    """need の見出しをすべて含む最初の表 → [{見出し: 値}]（タグを外した文字）。無ければ None。純関数"""
    for t in re.findall(r"<table.*?</table>", html, re.S | re.I):
        rows = re.findall(r"<tr.*?</tr>", t, re.S | re.I)
        cells = [[re.sub(r"<[^>]+>|\s+", " ", c).strip() for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", r, re.S | re.I)] for r in rows]
        if not cells or not all(n in cells[0] for n in need):
            continue
        head = cells[0]
        return [dict(zip(head, c)) for c in cells[1:] if c]
    return None


def dates_in(text):
    out = []
    for y, m, d in DATE_ANY.findall(text or ""):
        try:
            out.append(dt.date(int(y), int(m), int(d)))
        except ValueError:
            continue
    return out


def jsf_cats(rows, today):
    """日本証券金融の表の行 → ({"ban"/"jsf_alert"/"jsf_other": コードの集合}, 実施措置ごとの件数)。まだ効いていない行は入れない"""
    out = {k: set() for k in ("ban", "jsf_alert", "jsf_other")}
    labels = {}
    for r in rows:
        code = r.get("コード", "").strip()
        if not JT.CODE_RE.match(code):
            continue
        ds = dates_in(r.get("通知日・実施日", ""))
        if ds and max(ds) > today:
            continue
        measure = r.get("実施措置", "").strip()
        labels[measure] = labels.get(measure, 0) + 1
        key = "ban" if "申込停止" in measure else "jsf_alert" if "注意喚起" in measure else "jsf_other"
        out[key].add(code)
    return out, labels


def jpx_zoutanpo(rows, today):
    out = set()
    for r in rows:
        code = r.get("コード", "").strip()
        ds = dates_in(r.get("実施日", ""))
        if JT.CODE_RE.match(code) and ds and min(ds) <= today:
            out.add(code)
    return out


def load_json(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def candidates(highs, today):
    """その朝の「寄りで買わない目印」の候補（jp-highs.json の markers の行）。古い・無いときは None（＝全部を記録）"""
    mk = (highs or {}).get("markers") or {}
    try:
        age = (today - dt.date.fromisoformat(mk.get("asof", ""))).days
    except ValueError:
        return None
    if age <= 0 or age > MARKERS_STALE:
        return None
    return {r["code"] for r in mk.get("rows") or [] if r.get("code")}


def build_entry(today, jsf_html, jpx_html, margin, highs, now):
    """1日分の記録（純関数）。表が読めなかった源は ok=False"""
    entry = {"recorded_at": now, "jsf_ok": False, "jpx_ok": False, "daily_ok": False, "tags": {}, "counts": {}, "labels": {}}
    sets = {}
    rows = table_rows(jsf_html, ("コード", "実施措置")) if jsf_html else None
    if rows:
        c, labels = jsf_cats(rows, today)
        sets.update(c)
        entry.update(jsf_ok=True, labels=labels)
    rows = table_rows(jpx_html, ("コード", "実施日")) if jpx_html else None
    if rows is not None:
        sets["zoutanpo"] = jpx_zoutanpo(rows, today)
        entry["jpx_ok"] = True
    if margin and margin.get("rows"):
        sets["daily"] = {r.get("code") for r in margin["rows"] if r.get("code")}
        entry.update(daily_ok=True, daily_asof=margin.get("asof"))
    cand = candidates(highs, today)
    entry["candidates"] = None if cand is None else len(cand)
    for k, codes in sets.items():
        entry["counts"][k] = len(codes)
        keep = codes if cand is None else codes & cand
        entry["tags"][k] = sorted(tag(c) for c in keep)
    return entry


def record(today=None, get=JT.http, state_path=STATE):
    now = dt.datetime.now(JST)
    today = today or now.date()
    st = load_json(state_path) or {"registered": "J40", "kind": "record", "days": {}, "runs": []}
    day = today.isoformat()
    old = st["days"].get(day)
    if today.weekday() >= 5:
        print("土日は記録しない")
        return st
    if old and old.get("jsf_ok") and old.get("jpx_ok"):
        print(f"{day} は記録済み（取り直さない）")
        return st
    pages = {}
    for key, url in (("jsf", JSF_URL), ("jpx", JPX_URL)):
        try:
            pages[key] = decode(get(url))
        except Exception as e:  # noqa: BLE001
            print(f"⚠️ {url} を取れない：{type(e).__name__}: {str(e)[:120]}")
            pages[key] = None
    entry = build_entry(today, pages["jsf"], pages["jpx"], load_json(MARGIN), load_json(HIGHS), now.isoformat(timespec="minutes"))
    st["days"][day] = entry
    st["runs"] = (st.get("runs") or [])[-30:] + [{"at": now.isoformat(timespec="minutes"), "day": day,
                                                   "jsf_ok": entry["jsf_ok"], "jpx_ok": entry["jpx_ok"]}]
    with open(state_path, "w", encoding="utf-8") as fh:
        json.dump(st, fh, ensure_ascii=False, indent=0)
        fh.write("\n")
    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write(render_md(st))
    print(f"{day}：日本証券金融 {'✅' if entry['jsf_ok'] else '✕'}・日本取引所グループ {'✅' if entry['jpx_ok'] else '✕'}・"
          f"日々公表 {'✅' if entry['daily_ok'] else '✕'}・件数 {entry['counts']}・目印の候補 {entry['candidates']}")
    return st


def render_md(st):
    L = ["# J40 売り禁・規制の前向き記録（毎朝・読むだけ）", "",
         "事前登録＝`PILLAR_PREREG.md`「J40」（読み方は同じ節の追記）。銘柄名とコードは出さない（J31F の欄は `auction-forward.md`）。", "",
         "| 日 | 日本証券金融 | 日本取引所グループ | 売り禁 | 注意喚起 | その他の措置 | 増担保 | 日々公表 | 目印の候補 |", "|---|---|---|---:|---:|---:|---:|---:|---:|"]
    for day in sorted(st.get("days", {}), reverse=True)[:30]:
        e = st["days"][day]
        c = e.get("counts", {})
        L.append(f"| {day} | {'✅' if e.get('jsf_ok') else '✕'} | {'✅' if e.get('jpx_ok') else '✕'} | " +
                 " | ".join(str(c.get(k, '—')) for k in CATS) + f" | {e.get('candidates') if e.get('candidates') is not None else '全部'} |")
    L += ["", "- 件数はその朝に効いている全体の数（記録する印は目印の候補に入る銘柄だけ）", "", "---", "",
          "※ 研究の記録です。投資助言ではありません。"]
    return "\n".join(L) + "\n"


def main(argv):
    if "--probe" in argv:
        return probe()
    if "--record" in argv:
        record()
        return 0
    print("使い方：--probe／--record")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
