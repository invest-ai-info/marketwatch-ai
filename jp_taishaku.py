# -*- coding: utf-8 -*-
"""貸借銘柄（制度信用で空売りできる銘柄）の一覧を、日本取引所グループの公表資料から読む。2026-10-08 新設。

読み方は PILLAR_PREREG.md「J36」の追記（probe のあと）のとおり：「制度信用銘柄・貸借銘柄」のページの最初の Excel の表で、
「銘柄コード」の見出しの行から下を読み、信用区分がちょうど「貸借銘柄」の銘柄コードを貸借銘柄とする。

使うところ: taishaku_lab.py（J36）／auction_forward.py（J31F の読むだけの欄）／build_jp_highs.py（朝のメールの〔貸借〕の印）
⚠️ 軽い部品（標準ライブラリと pandas だけ）。研究のラボを import しない（build_jp_highs から呼ぶため）。
⚠️ 一覧は「取りに行った時点の一覧」。売り禁（貸借取引の申込停止）や証券会社ごとの在庫は入っていない。
"""
import io
import re
import urllib.request

UA = {"User-Agent": "Mozilla/5.0", "Accept-Language": "ja"}
PAGES = ("https://www.jpx.co.jp/listing/others/margin/index.html",
         "https://www.jpx.co.jp/markets/statistics-equities/margin/05.html",
         "https://www.jpx.co.jp/markets/statistics-equities/margin/index.html")
FILE_RE = re.compile(r'href="([^"]+\.(?:xlsx?|csv|zip|pdf))"[^>]*>(.*?)</a>', re.I | re.S)
CODE_RE = re.compile(r"^\d{3}[0-9A-Z]$")
MIN_LIST = 1000               # 貸借銘柄がこれ未満しか読めなければ使わない（2026-10-01 現在 2,671）


def http(url, timeout=60):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()


def file_links(html, base="https://www.jpx.co.jp"):
    """ページの HTML → [(絶対 URL, リンクの文字)]。純関数"""
    out = []
    for href, text in FILE_RE.findall(html):
        url = href if href.startswith("http") else base + href
        out.append((url, re.sub(r"<[^>]+>|\s+", " ", text).strip()))
    return out


def parse_list(raw):
    """一覧の表（見出しなしで読んだもの）→ (貸借銘柄のコードの集合, 一覧の日付の文字, 区分ごとの件数)。PREREG「J36」の追記の読み方。純関数"""
    head = next((i for i in range(min(20, len(raw))) if "銘柄コード" in [str(v).strip() for v in raw.iloc[i].tolist()]), None)
    if head is None:
        raise RuntimeError("一覧の表に「銘柄コード」の見出しの行が無い（資料の形が変わった？）")
    cols = [str(v).strip() for v in raw.iloc[head].tolist()]
    if "信用区分" not in cols:
        raise RuntimeError("一覧の表に「信用区分」の列が無い（資料の形が変わった？）")
    df = raw.iloc[head + 1:].copy()
    df.columns = cols
    asof = next((str(v).strip() for v in raw.iloc[:head].astype(str).values.ravel() if "現在" in str(v)), "")
    kinds = df["信用区分"].astype(str).str.strip()
    counts = {k: int((kinds == k).sum()) for k in sorted(set(kinds)) if k and k != "nan"}
    codes = df["銘柄コード"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    return {c for c, k in zip(codes, kinds) if CODE_RE.match(c) and k == "貸借銘柄"}, asof, counts


def load(get=http):
    """→ (貸借銘柄のコードの集合, 一覧の日付の文字, 区分ごとの件数)。読めない・MIN_LIST 未満なら RuntimeError"""
    import pandas as pd
    html = get(PAGES[0]).decode("utf-8", "replace")
    xls = [u for u, _ in file_links(html) if re.search(r"\.xlsx?$", u, re.I)]
    if not xls:
        raise RuntimeError("「制度信用銘柄・貸借銘柄」のページに Excel のリンクが無い（ページの形が変わった？）")
    raw = pd.read_excel(io.BytesIO(get(xls[0])), sheet_name=0, dtype=str, header=None)
    codes, asof, counts = parse_list(raw)
    if len(codes) < MIN_LIST:
        raise RuntimeError(f"貸借銘柄が {len(codes)} しか読めない（{MIN_LIST}未満）")
    return codes, asof, counts


def load_or_none(get=http):
    """→ {"codes": 集合, "asof": 一覧の日付, "n": 銘柄数} か None。取れなければ理由を表示して None（呼ぶ側は印を付けずに続ける）"""
    try:
        codes, asof, _ = load(get)
    except Exception as e:  # noqa: BLE001  一覧が取れなくても本体の仕事は止めない
        print(f"⚠️ 貸借銘柄の一覧を取れない＝今回は〔貸借〕を付けない：{type(e).__name__}: {str(e)[:160]}", flush=True)
        return None
    print(f"貸借銘柄の一覧（{asof or '日付不明'}・{len(codes):,}銘柄）", flush=True)
    return {"codes": codes, "asof": asof, "n": len(codes)}
