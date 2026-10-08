# -*- coding: utf-8 -*-
"""J36 J31 の売りは、制度信用で空売りできる「貸借銘柄」だけでも残るか。2026-10-08 登録・オーナー「リアを登録し続けてください」。
PILLAR_PREREG.md「J36」。

貸借銘柄の一覧は日本取引所グループの公表資料（いまの一覧）。一覧の形はクラウドのセッションから見えないので、先に --probe
（資料の場所・表の見出し・件数だけ・損益なし）を回し、読み方を PREREG「J36」の追記に書いてから --check・本番に進む。
**目隠しではない**（同じ取引を J31〜J35 で数えた）。

⚠️ 決まりは PILLAR_PREREG.md「J36」と下の定数に固定。行・組・幅は J31（auction_lab）・J32（stop_short_lab）・J29（bounce_range_lab）の
   関数をそのまま使う。
⚠️ 出力（taishaku-lab.json / .md）は集計だけ・銘柄名とコードは出さない（SYNC禁忌）。probe は表の見出しと区分の値だけを表示する
   （銘柄名の列は件数だけ）。

実行: python taishaku_lab.py --probe   （資料の場所・表の見出し・件数だけ。損益は数えない・何も書き出さない）
      python taishaku_lab.py --check   （貸借銘柄の数と組ごとの件数だけ。損益は数えない）
      python taishaku_lab.py           （本番。Actions の taishaku-lab.yml から手動で・1回だけ）
"""
import datetime as dt
import io
import json
import re
import sys
import urllib.request

import numpy as np

import auction_lab as AU
import bounce_range_lab as BR
import highs_trap_lab as T
import jp_bars
import pillar_lab as P
import prevgap_lab as PG
import stop_short_lab as SS
import yori_lab as Y

OUT_JSON, OUT_MD = "taishaku-lab.json", "taishaku-lab.md"
C = AU.C
ERAS = AU.ERAS
UA = {"User-Agent": "Mozilla/5.0", "Accept-Language": "ja"}
PAGES = ("https://www.jpx.co.jp/listing/others/margin/index.html",
         "https://www.jpx.co.jp/markets/statistics-equities/margin/05.html",
         "https://www.jpx.co.jp/markets/statistics-equities/margin/index.html")
FILE_RE = re.compile(r'href="([^"]+\.(?:xlsx?|csv|zip|pdf))"[^>]*>(.*?)</a>', re.I | re.S)
CODE_RE = re.compile(r"^\d{3}[0-9A-Z]$")
N_Q = 2
ALPHA = 0.05 / N_Q            # 97.5％ の幅
MIN_LIST = 1000               # 貸借銘柄がこれ未満しか読めなければ数えない（約2,000のはず）
OK_ALL, OK_OLD, NONE = "✅ 貸借銘柄だけでも残る", "△ 昔だけ（最近は届かない）", "✕ 貸借銘柄だけでは残らない"


# ════════════════════ 資料 ════════════════════

def http(url, timeout=60):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()


def file_links(html, base="https://www.jpx.co.jp"):
    """ページの HTML → [(絶対 URL, リンクの文字)]。純関数"""
    out = []
    for href, text in FILE_RE.findall(html):
        url = href if href.startswith("http") else base + href
        out.append((url, re.sub(r"<[^>]+>|\s+", " ", text).strip()))
    return out


def code_column(df):
    """4桁の銘柄コードがいちばん多い列の名前（無ければ None）。純関数"""
    best, best_n = None, 0
    for col in df.columns:
        vals = df[col].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
        n = int(vals.str.match(CODE_RE).sum())
        if n > best_n:
            best, best_n = col, n
    return best if best_n >= 50 else None


def taishaku_codes(df, col_code, col_kind, word="貸借"):
    """区分の列に word を含む行の銘柄コードの集合。純関数"""
    codes = df[col_code].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    kind = df[col_kind].astype(str)
    return {c for c, k in zip(codes, kind) if CODE_RE.match(c) and word in k}


def describe(df):
    """probe 用：列ごとに（区分の列なら値の種類と件数／それ以外は値の種類の数だけ）。銘柄名は出さない"""
    out = {}
    for col in df.columns:
        vals = df[col].dropna().astype(str).str.strip()
        uniq = vals.unique()
        if len(uniq) <= 12:
            out[str(col)] = {str(u): int((vals == u).sum()) for u in uniq}
        else:
            out[str(col)] = f"（{len(uniq)}種類・{int(vals.str.match(CODE_RE).sum())}行が銘柄コードの形）"
    return out


def probe():
    import pandas as pd
    for page in PAGES:
        print(f"\n=== {page}", flush=True)
        try:
            html = http(page).decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001
            print(f"  取れない：{type(e).__name__}: {str(e)[:120]}")
            continue
        links = file_links(html)
        print(f"  資料のリンク {len(links)}件")
        for url, text in links[:25]:
            print(f"  - {text[:60]} → {url}")
        for url, text in [x for x in links if re.search(r"\.xlsx?$", x[0], re.I)][:3]:
            try:
                sheets = pd.read_excel(io.BytesIO(http(url)), sheet_name=None, dtype=str, header=None)
            except Exception as e:  # noqa: BLE001
                print(f"  ✕ 読めない {url}：{type(e).__name__}: {str(e)[:120]}")
                continue
            for name, df in sheets.items():
                print(f"  ▼ {url.rsplit('/', 1)[-1]} の表「{name}」：{df.shape[0]}行×{df.shape[1]}列")
                for i in range(min(8, len(df))):
                    row = [str(v)[:14] if not CODE_RE.match(str(v).strip()) else "（コード）" for v in df.iloc[i].tolist()]
                    if i < 6:
                        print(f"    {i}行目：{row}")
                print(f"    列の中身：{json.dumps(describe(df), ensure_ascii=False)[:1500]}")
    return 0


def load_list():
    """→ (貸借銘柄のコードの集合, 説明)。読み方は PREREG「J36」の追記で決める（probe のあと）"""
    raise RuntimeError("貸借銘柄の一覧の読み方がまだ決まっていない（先に --probe を回し、PREREG「J36」の追記で決める）")


# ════════════════════ 数える ════════════════════

def summary_of(by_era):
    plus = [q.get("lo") is not None and q["lo"] > 0 for q in (by_era["e1"], by_era["e2"], by_era["e3"])]
    if all(plus):
        return OK_ALL
    if plus[0] and plus[1]:
        return OK_OLD
    return NONE


def flags(A, codes, code_list):
    """行ごとに貸借銘柄か（code 列は load の並びの番号）"""
    tai = np.array([c in code_list for c in codes], bool)
    return tai[A[:, C["code"]].astype(int)]


def analyze(A, is_tai):
    A_, idio = PG.idio_gap(A)
    res = {"eras": {}, "groups": {}}
    sel = SS.groups(A_, idio)
    tai = is_tai(A_)
    v = -A_[:, C["rclose"]] - AU.SHORT_COST
    for key, name, span in ERAS:
        em = AU.era_mask(A_, span)
        days = np.unique(A_[em, C["day"]])
        res["eras"][key] = {"name": name, "days": int(len(days)),
                            "first": dt.date.fromordinal(int(days[0])).isoformat() if len(days) else None,
                            "last": dt.date.fromordinal(int(days[-1])).isoformat() if len(days) else None}
    for g, gname in SS.GROUPS:
        top = SS.top_mask(A_, sel[g])
        by_era, read = {}, {}
        for key, _, span in ERAS:
            m = AU.era_mask(A_, span) & sel[g]
            q = BR.net_mean(A_, v, m & tai, alpha=ALPHA)
            by_era[key] = q
            read[key] = {"tai": BR._plain(v, m & tai), "other": BR._plain(v, m & ~tai), "share": float((m & tai).sum() / max(m.sum(), 1)),
                         "top3_tai": BR._plain(v, m & top & tai), "top3_other": BR._plain(v, m & top & ~tai)}
        res["groups"][g] = {"name": gname, "eras": by_era, "read": read, "summary": summary_of(by_era)}
    return res


def check_summary(A, is_tai, n_list, missing, n_codes, store):
    B, idio = PG.idio_gap(A)
    sel = SS.groups(B, idio)
    tai = is_tai(B)
    out = {"n_codes": n_codes, "n_list": n_list, "missing": {k: len(v) for k, v in missing.items()}, "rows": int(len(A)), "store": store, "eras": {}}
    for key, name, span in ERAS:
        em = AU.era_mask(B, span)
        out["eras"][key] = {g: {"all": int((em & sel[g]).sum()), "taishaku": int((em & sel[g] & tai).sum())} for g, _ in SS.GROUPS}
    return out


# ════════════════════ 書く ════════════════════

def _p(x, d=2):
    return Y._pct(x, d) if x is not None else "—"


def _band(q):
    return "—" if q.get("lo") is None else f"{_p(q['lo'])}〜{_p(q['hi'])}"


def _cell(c):
    return "—" if c.get("mean") is None else f"{_p(c['mean'])}（{c['n']:,}）"


def render_md(res):
    L = ["# J36 J31 の売りは、制度信用で空売りできる「貸借銘柄」だけでも残るか", "",
         f"更新: {res.get('generated_at', '')}（事前登録＝`PILLAR_PREREG.md`「J36」・指紋 `{(res.get('prereg_sha256') or '')[:12]}`）", ""]
    r = res.get("result") or {}
    if "error" in r:
        return "\n".join(L + [f"⚠️ 計算できず：{r['error']}", "", "※ 研究の記録です。投資助言ではありません。"]) + "\n"
    L += ["**目隠しではない**（同じ取引を J31〜J35 で数えた）。前の日の売買代金10億円以上の目印 B・C の株を寄り成行で売り引け成行で買い戻したときの、"
          f"1回あたりの損益率（プラス＝売りが勝った・費用 0.03％ 込み）。貸借銘柄＝{r.get('list_note', '')}（いまの一覧を昔に当てている）。"
          "幅は 97.5％（日と銘柄で引き直した広いほう）。", ""]
    for key, e in r["eras"].items():
        L.append(f"- {e['name']}：{e['first']}〜{e['last']}・{e['days']:,}営業日")
    L += ["", "## まとめ", "", "| 組 | まとめ |", "|---|---|"]
    for g, x in r["groups"].items():
        L.append(f"| {g} {x['name']} | **{x['summary']}** |")
    for g, x in r["groups"].items():
        L += ["", f"## {g} {x['name']}", "",
              "| 時代 | 貸借銘柄の割合 | 貸借銘柄だけ | 97.5％の幅 | 前半／後半 | 貸借銘柄でない株 | 上位3：貸借銘柄／それ以外 |", "|---|---:|---:|---|---|---:|---|"]
        for key, q in x["eras"].items():
            rd = x["read"][key]
            L.append(f"| {r['eras'][key]['name']} | {rd['share'] * 100:.0f}％ | {_cell(rd['tai'])} | {_band(q)} | {_p(q.get('early'))}／{_p(q.get('late'))} | "
                     f"{_cell(rd['other'])} | {_cell(rd['top3_tai'])}／{_cell(rd['top3_other'])} |")
    L += ["", "## 注意", "",
          "- いまの貸借銘柄の一覧を昔に当てている（昔は貸借銘柄でなかった株・いまは外れた株がある）",
          "- 貸借銘柄でも、売り禁（申込停止）・逆日歩・注意喚起の日は売れない・費用が増える（入れていない）",
          "- 気配と始値のずれ・ストップ高で買い戻せない日・いま上場している銘柄だけ（J31 と同じ限界）", "", "---", "",
          "※ 研究の記録です。投資助言ではありません。空売りは損失が限られない取引です。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def main(argv):
    if "--probe" in argv:
        return probe()
    res = {"generated_at": dt.datetime.now(P.JST).isoformat(timespec="minutes"), "prereg_file": P.PREREG,
           "prereg_sha256": P.prereg_sha256()}
    try:
        code_list, note = load_list()
        if len(code_list) < MIN_LIST:
            raise RuntimeError(f"貸借銘柄が {len(code_list)} しか読めない（{MIN_LIST}未満）")
        stocks, list_date = jp_bars.load_universe()
        codes = sorted(stocks)
        A, missing, drops = AU.load(codes, jp_bars.fetcher())
        store = jp_bars.info()
        res["price_store"] = store
        is_tai = lambda X: flags(X, codes, code_list)  # noqa: E731
        if "--check" in argv:
            print(json.dumps(check_summary(A, is_tai, len(code_list), missing, len(codes), store), ensure_ascii=False, indent=1))
            return 0
        if not store or store.get("daily_range") != jp_bars.FULL_DAILY:
            raise RuntimeError("値段の置き場の日足が全期間版ではない（先に jp-bars-cache を回す）")
        if len(set(missing["daily"])) > T.MAX_MISSING * len(codes):
            raise RuntimeError("日足を取れなかった銘柄が5％超。偏った組で数えない（取り直す）")
        res["result"] = dict(analyze(A, is_tai), n_codes=len(codes), list_date=list_date, n_list=len(code_list), list_note=note,
                             n_missing={k: len(v) for k, v in missing.items()}, n_dropped=drops["n"])
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        if "--check" in argv:
            return 1
        res["result"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1, default=str)
    md = render_md(res)
    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
