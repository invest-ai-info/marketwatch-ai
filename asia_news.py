# -*- coding: utf-8 -*-
"""朝のメール用：中国・オーストラリアのニュースの見出し（機械で拾う）。2026-10-08 夜 オーナー「午前中はオージー（豪ドル）の取引をする
可能性があるので、中国やオーストラリアなどのニュースで気になることがあったらそれも入れてください」。

サイトの最新ニュース（build_news_ticker.py）と同じ Google ニュースの RSS を、豪ドル・豪州・中国の言葉で検索し、
直近 MAX_AGE_HOURS 時間の見出しを新しい順に拾う（見出しの整形・広告元の除外・重複の見分けは build_news_ticker の関数を使う）。
**重要度の判断はしていない**（AI の判断は朝のブリーフィング fundamental-context.json の asia_watch 欄＝予約の指示に足したら出る）。

⚠️ 標準ライブラリだけ（朝のメールのワークフローは追加のライブラリを入れない）。取れなければ空（メールは止めない）。
⚠️ 一時ファイル .asia-news.json はワークフローの中だけ（リポジトリには入れない・.gitignore）。
"""
import datetime as dt
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import build_news_ticker as NT

OUT = ".asia-news.json"
QUERIES = (("AU", "豪ドル"), ("AU", "豪準備銀行 OR オーストラリア 経済 OR 豪州 経済"),
           ("CN", "中国 経済 OR 人民元 OR 中国人民銀行 OR 中国 景気"))
MAX_AGE_HOURS = 30
TOP = 6
MAX_AGE_MIN = 180          # 一時ファイルの古さ（朝のメールが読むとき）
UA = {"User-Agent": "Mozilla/5.0 marketwatch-jp/1.0"}
CN_WORDS = ("中国", "人民元", "香港", "上海", "習近平", "北京")
AU_WORDS = ("豪", "オーストラリア", "RBA", "オージー")


def region_of(title, default):
    if any(w in title for w in AU_WORDS):
        return "AU"
    if any(w in title for w in CN_WORDS):
        return "CN"
    return default


def parse(xml_text, region, now):
    """RSS の文字列 → [{"t", "s", "dt", "r", "u"}]（直近 MAX_AGE_HOURS 時間・日本語の見出しだけ）。純関数"""
    out = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return out
    for it in root.iter("item"):
        title = NT.clean_title(it.findtext("title") or "")
        src = (it.findtext("source") or "").strip()
        try:
            when = parsedate_to_datetime(it.findtext("pubDate") or "")
        except (TypeError, ValueError):
            continue
        if not title or when is None or len(re.findall(r"[ぁ-んァ-ヶ一-龠]", title)) < 3 or NT.is_ng_publisher(src):
            continue
        age_h = (now - when).total_seconds() / 3600
        if age_h < -0.5 or age_h > MAX_AGE_HOURS:
            continue
        out.append({"t": title, "s": src, "dt": when.astimezone(NT.JST).isoformat(timespec="minutes"),
                    "r": region_of(title, region), "u": it.findtext("link") or ""})
    return out


def pick(items, top=TOP):
    """新しい順・似た見出しは1つ（build_news_ticker.norm で前から20字が同じもの）"""
    seen, out = set(), []
    for x in sorted(items, key=lambda x: x["dt"], reverse=True):
        k = NT.norm(x["t"])[:20]
        if k in seen:
            continue
        seen.add(k)
        out.append(x)
        if len(out) == top:
            break
    return out


def fetch(query):
    with urllib.request.urlopen(urllib.request.Request(NT.gnews(query + " when:2d"), headers=UA), timeout=20) as r:
        return r.read().decode("utf-8", "replace")


def collect(get=fetch, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    items, errors = [], 0
    for region, q in QUERIES:
        try:
            items += parse(get(q), region, now)
        except Exception:  # noqa: BLE001
            errors += 1
    return {"items": pick(items), "errors": errors}


def load(path=OUT, now=None):
    try:
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
        made = dt.datetime.fromisoformat(d["generated_at"])
        now = now or dt.datetime.now(made.tzinfo)
        return d if (now - made).total_seconds() <= MAX_AGE_MIN * 60 else None
    except Exception:  # noqa: BLE001
        return None


def main():
    d = collect()
    d["generated_at"] = dt.datetime.now(NT.JST).isoformat(timespec="minutes")
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(d, fh, ensure_ascii=False)
    print(f"✅ 中国・豪州の見出し {len(d['items'])}件（取得エラー {d['errors']}/{len(QUERIES)}）")
    for x in d["items"]:
        print(f"   {x['dt'][5:16]} [{x['r']}] {x['t']}（{x['s']}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
