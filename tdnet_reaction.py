# -*- coding: utf-8 -*-
"""TDnet の開示のあと、次の丸1日でどう動いたかを追う（読むだけ・試験・結果はメールだけ）。PILLAR_PREREG.md「J51」。

2026-11-10 オーナー「1日で発表される日本株に関するニュースを読んで、ダブってるものは別として、すべてを読んで、
その次の日にどんな動きをしたのか追うことはできますか」→「一から始めてもらって、メディアの見出しはいりません。
結果はメールだけで、とりあえずは試験的にやってみましょう。1日のニュースを全部読むとトークンは足りますか。
足りないようだったら節約してできるように工夫してください」。

- 読む：その日の TDnet の開示一覧を全件（ETF・投資信託・投資法人は除く）。種類は表題の言葉（`tdnet_events.TAGS` と同じ）。
  業績修正・差異の向きは `tdnet-events.csv`（PDF の表から読んだもの）→ 無ければ表題の言葉（上方修正／下方修正）。
  **AI は使わない＝トークンは使わない**（全文を AI で読むと1日 約390万字〔11/9 の 567件から30件を抜いて測った〕＝
  1回の会話で読める量の数倍〜数十倍。表題と会社名だけなら1日 約2万字。数字はプログラムが読む）
- まとめる（重複）：同じ会社・同じ開示日・同じ反応の日の開示は1件の「出来事」（決算短信＋説明資料＋配当の修正…＝1社1件）。
  訂正だけの出来事は「訂正」（種類を数えない）
- 測る（開示の直前の値段 → 開示のあとの最初の丸1日〔反応の日〕の引け）。TOPIX（1306）の同じ時間の動きを引いた差も:
  ・寄り前（9:00 より前）＝前の取引日の終値 → その日の引け
  ・場中（9:00〜15:29）＝開示の時刻までに終わった最後の5分足の終値（無ければ前の取引日の終値）→ 次の取引日の引け
    （その日の残り＝その日の引け ÷ 直前の値段 も別に出す）
  ・引け後（15:30 以降）＝その日の終値 → 次の取引日の引け
  ・窓＝反応の日の寄り ÷ その前の取引日の終値
- 出す：`tdnet-reaction.csv`（コード・種類・数字だけ＝表題と会社名は置かない）／`tdnet-reaction-days.json`（日ごとの件数と送った時刻）／`tdnet-reaction-trend.json`（傾向）。
  メール＝開示の日ごとに1通（反応の日の 16:30 より後）。表題と会社名はメールにだけ載せる（オーナー宛て）

🆕 2026-11-10 夜 オーナー「この内容を毎日蓄積していって、どんなニュースがあったときに次の日、もしくは1週間、1ヶ月…
上がるのか下がるのか、どんな動きをするのか、傾向を登録して蓄積していってください」（PILLAR_PREREG.md「J51」の追記）:
- あとから埋める：反応の日を1日目として **5日目（1週間）・20日目（1か月）の引け**（直前の値段から・TOPIX と比べた差も）と、
  1週間のうちの一番高い・安い値段（TOPIX を引かない）。毎回、引けが確定した分を埋める（値段は比で戻す＝台帳に値段は置かない）
- 傾向：`tdnet-reaction-trend.json`＝種類（23）×期間（次の日・1週間・1か月）の累積（社数・平均・中央値・上げた割合）を毎回まとめ直す
  （読むだけ）。**判定は升ごとに1回だけ**＝2026-11-11 からの開示で、2027-02-15 以降に 100社・開示の日20日以上たまったら、
  開示の日でまとめた標準誤差で z が 69の升で割った基準（両側 0.05/69＝約3.38）を超え、前半と後半が同じ向きなら「✅ 上向き／下向き」、
  それ以外は「✕ 見えない」。一度決めたら変えない。メールの最後に「これまでの傾向」を毎回のせる

⚠️ 判定が ✅ でも、売買の決まりにするなら別に事前登録して登録より後の分で確かめる（費用も入れて）。
⚠️ 出力は GitHub 側で生成＝ローカルから push しない（SYNC禁忌）。

実行: python tdnet_reaction.py                 （まだ送っていない開示の日を測って送る。Actions の tdnet-reaction.yml から）
      python tdnet_reaction.py --dry-run       （送らず、本文を表示するだけ。記録も書かない）
      python tdnet_reaction.py --day 2026-11-09 --dry-run --html-out a.html   （日を決めて試す）
"""
import argparse
import csv
import datetime as dt
import json
import os
import re
import smtplib
import statistics
import sys
import time
import unicodedata
import urllib.request

import tdnet_events as T

JST = dt.timezone(dt.timedelta(hours=9))
START = "2026-11-09"            # この開示日から（11/10 に登録。11/9 の開示 → 11/10 の値動きが最初の1通）
LOOK_DAYS = 7                   # さかのぼって「まだ送っていない日」を探す暦日
MAX_MAIL = 3                    # 1回に送る通数の上限（止まっていた日がたまったとき）
READY = (16, 30)                # 反応の日のこの時刻より後に測る（引け 15:30・Yahoo の日足が落ち着くまで）
OPEN_MIN, CLOSE_MIN = 9 * 60, 15 * 60 + 30
BAR_MIN = 5
TOPIX = "1306"
LEDGER, DAYS, TREND = "tdnet-reaction.csv", "tdnet-reaction-days.json", "tdnet-reaction-trend.json"
COLS = ("date", "code", "slot", "time", "docs", "tags", "rev", "diff", "base_on", "react_on",
        "gap", "rest", "react", "topix", "ex", "ok",
        "d5", "tx5", "ex5", "hi5", "lo5", "d20", "tx20", "ex20")   # 🆕 11/10 夜 1週間（5取引日）・1か月（20取引日）＝あとから埋める
# 🆕 2026-11-10 夜 オーナー「毎日蓄積していって、どんなニュースがあったときに次の日、もしくは1週間、1ヶ月…上がるのか下がるのか、
#    傾向を登録して蓄積していってください」＝PILLAR_PREREG.md「J51」の 11/10 夜の追記。ここの数字は登録から（結果を見る前に固定）
HORIZONS = (("d5", "tx5", "ex5", 5), ("d20", "tx20", "ex20", 20))   # 反応の日を1日目として5日目・20日目の引け
H_KEYS = (("次の日", "ex"), ("1週間", "ex5"), ("1か月", "ex20"))
KINDS = ("決算", "上方修正", "下方修正", "実績の上振れ", "実績の下振れ", "増配", "減配", "自社株買い", "自社株買いの進み",
         "自己株式の消却", "M&A", "TOB・上場廃止", "提携", "増資・売出し", "大株主の異動", "株主総会・提案", "中期計画",
         "株主還元の方針", "株式分割", "特別利益", "特別損失", "不祥事・事故・調査", "その他")   # 判定する種類（23×3＝69の升）
JUDGE_START = "2026-11-11"      # 判定に使う開示の日（登録した 11/10 より後だけ。11/9・11/10 は読むだけ）
JUDGE_FROM = "2027-02-15"       # この日より前は判定しない（決算の季節1つだけで決めないため・約60取引日）
JUDGE_N, JUDGE_DAYS = 100, 20   # 升ごとに 100社以上・開示の日が20日以上たまったら1回だけ
ALPHA = 0.05                    # 69の升で割る（多重検定）＝両側 0.05/69
SKIP = T.SKIP_TITLE + r"|投資法人|インフラファンド"
FIX = r"訂正"
PAUSE = 0.15
TOP_N, LIST_N, MIN_N = 10, 10, 10
TITLE_LEN = 42
UA = {"User-Agent": "Mozilla/5.0"}
TAG_ORDER = [t for t, *_ in T.TAGS]


# ════════════════════ 読む・まとめる（純関数） ════════════════════

def minutes(hhmm):
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def slot_of(hhmm):
    m = minutes(hhmm)
    return "寄り前" if m < OPEN_MIN else ("場中" if m < CLOSE_MIN else "引け後")


def skip_row(row):
    t = unicodedata.normalize("NFKC", (row.get("title") or "") + " " + (row.get("name") or ""))
    return bool(re.search(SKIP, t))


def doc_tags(row):
    """1件の開示 → 種類（訂正だけの開示は ["訂正"]）"""
    t = unicodedata.normalize("NFKC", row.get("title") or "")
    if re.search(FIX, t):
        return ["訂正"]
    return T.tags_of(row.get("title") or "")


def group_rows(rows, day, trading_days, dirs=None):
    """一覧の行 → 出来事（同じ会社・同じ反応の日）。dirs＝{doc: (業績修正の向き, 差異の向き)}（tdnet-events.csv から）。
    trading_days＝取引日の昇順の一覧（反応の日を決める。day より後が無ければ反応の日は None）。純関数"""
    dirs = dirs or {}
    nxt = next((d for d in trading_days if d > day), None)
    groups = {}
    for r in rows:
        if skip_row(r) or not r.get("code"):
            continue
        slot = slot_of(r["time"])
        react_on = day if slot == "寄り前" else nxt
        key = (r["code"], react_on)
        g = groups.setdefault(key, {"date": day, "code": r["code"], "name": (r.get("name") or "").strip(), "react_on": react_on,
                                    "time": r["time"], "slot": slot, "docs": [], "tags": [], "rev": "", "diff": ""})
        if minutes(r["time"]) < minutes(g["time"]):
            g["time"], g["slot"] = r["time"], slot
        tg = doc_tags(r)
        g["docs"].append({"time": r["time"], "title": r.get("title") or "", "tags": tg})
        for t in tg:
            if t not in g["tags"]:
                g["tags"].append(t)
        rv, df = dirs.get(r.get("doc"), ("", ""))
        if "業績修正" in tg and not g["rev"]:
            g["rev"] = rv or T.title_direction(r.get("title")) or "不明"
        if "差異" in tg and not g["diff"]:
            g["diff"] = df or "不明"
    out = []
    for g in groups.values():
        real = [t for t in g["tags"] if t != "訂正"]
        g["tags"] = sorted(real, key=TAG_ORDER.index) if real else (["訂正"] if "訂正" in g["tags"] else ["その他"])
        g["docs"].sort(key=lambda d: minutes(d["time"]))
        out.append(g)
    return sorted(out, key=lambda g: (minutes(g["time"]), g["code"]))


def dirs_from_events(events, day):
    """tdnet-events.csv の行 → {doc: (業績修正の向き, 差異の向き)}（その日の分だけ）"""
    out = {}
    for e in events:
        if e.get("date") != day or not e.get("dir"):
            continue
        tags = (e.get("tags") or "").split("|")
        out[e["doc"]] = (e["dir"] if "業績修正" in tags else "", e["dir"] if "差異" in tags else "")
    return out


# ════════════════════ 測る（純関数） ════════════════════

def daily_map(bars):
    """[(時刻, 始, 高, 安, 終, 出来高)] → {日付 ISO: (始, 終)}"""
    return {t.date().isoformat(): (o, c) for t, o, h, l, c, v in bars}


def prev_day(days, d):
    p = [x for x in days if x < d]
    return p[-1] if p else None


def base_price(slot, day, hhmm, daily, bars5, days):
    """開示の直前の値段と、それがどの日のものか。→ (値段, 日付) か (None, None)"""
    if slot == "引け後":
        return (daily[day][1], day) if day in daily else (None, None)
    if slot == "場中":
        cut = minutes(hhmm)
        last = None
        for t, o, h, l, c, v in bars5 or []:
            if t.date().isoformat() != day:
                continue
            if t.hour * 60 + t.minute + BAR_MIN <= cut:
                last = c
        if last is not None:
            return last, day
    p = prev_day(days, day)
    return (daily[p][1], p) if p and p in daily else (None, None)


def measure(g, daily, bars5, days, tx_daily, tx_bars5):
    """出来事 g に数字を足す（測れなければ ok=0）。daily/tx_daily＝{日付: (始, 終)}・bars5＝5分足"""
    r = g["react_on"]
    res = {"base_on": "", "gap": None, "rest": None, "react": None, "topix": None, "ex": None, "ok": 0}
    if not r or r not in daily or r not in tx_daily:
        return res
    base, bday = base_price(g["slot"], g["date"], g["time"], daily, bars5, days)
    tbase, _ = base_price(g["slot"], g["date"], g["time"], tx_daily, tx_bars5, days)
    if not base or not tbase:
        return res
    res["base_on"] = bday
    p = prev_day(days, r)
    if p in daily:
        res["gap"] = daily[r][0] / daily[p][1] - 1
    if g["slot"] == "場中" and g["date"] in daily and bday == g["date"]:
        res["rest"] = daily[g["date"]][1] / base - 1
    res["react"] = daily[r][1] / base - 1
    res["topix"] = tx_daily[r][1] / tbase - 1
    res["ex"] = res["react"] - res["topix"]
    res["ok"] = 1
    return res


# ════════════════════ まとめる（数字 → 表・本文） ════════════════════

def kind_keys(g):
    """種類ごとの表の行（向きの付く種類は向きで分ける）"""
    out = []
    for t in g["tags"]:
        if t == "業績修正":
            out.append({"上方": "上方修正", "下方": "下方修正"}.get(g["rev"], "業績修正（横ばい・不明）"))
        elif t == "差異":
            out.append({"上方": "実績の上振れ", "下方": "実績の下振れ"}.get(g["diff"], "実績の差異（不明）"))
        else:
            out.append(t)
    return out


def kind_table(groups):
    """→ [(種類, 社数, 平均, 中央値, 上げた割合)]（TOPIX と比べた差）。社数の多い順"""
    acc = {}
    for g in groups:
        if not g.get("ok"):
            continue
        for k in kind_keys(g):
            acc.setdefault(k, []).append(g["ex"])
    rows = [(k, len(v), statistics.mean(v), statistics.median(v), sum(1 for x in v if x > 0) / len(v)) for k, v in acc.items()]
    return sorted(rows, key=lambda x: (-x[1], x[0]))


def pct(x, nd=1):
    if x is None:
        return "—"
    v = x * 100
    return f"{'+' if v >= 0 else '−'}{abs(v):.{nd}f}%"


def wd(d):
    x = dt.date.fromisoformat(d)
    return f"{x.month}/{x.day}（{'月火水木金土日'[x.weekday()]}）"


def short(s, n=TITLE_LEN):
    s = re.sub(r"\s+", " ", unicodedata.normalize("NFKC", s or "")).strip()
    return s if len(s) <= n else s[:n - 1] + "…"


TITLE_FIRST = ("TOB・上場廃止", "不祥事・事故・調査", "業績修正", "差異", "M&A", "提携", "決算", "増配", "減配", "自社株買い",
               "株式分割", "中期計画", "株主還元の方針")


def main_title(g):
    """メールに出す代表の表題＝大事な種類の開示を先に（TOB・不祥事・業績修正…・決算）。種類が無ければ最初の開示"""
    def rank(d):
        r = [TITLE_FIRST.index(t) for t in d["tags"] if t in TITLE_FIRST]
        if r:
            return min(r)
        return len(TITLE_FIRST) + (2 if d["tags"] == ["訂正"] else 0 if d["tags"] else 1)
    return min(g["docs"], key=lambda d: (rank(d), minutes(d["time"])))["title"]


def stock_line(i, g):
    tags = "".join(f"〔{k}〕" for k in kind_keys(g))
    head = f"  {i}. {g['code']} {short(g['name'], 16)}  "
    nums = f"TOPIX比 {pct(g['ex'])}（{g['slot']} {g['time']}・窓 {pct(g['gap'])}"
    if g.get("rest") is not None:
        nums += f"・その日の残り {pct(g['rest'])}"
    nums += "）"
    more = f"ほか{len(g['docs']) - 1}件" if len(g["docs"]) > 1 else ""
    return [head + nums + " " + tags, f"     「{short(main_title(g))}」{more}"]


def build_mail(day, groups, n_docs, trend=None):
    """→ (件名, 本文)。groups は measure 済み・trend＝build_trend の結果（あれば「これまでの傾向」を足す）"""
    react_days = sorted({g["react_on"] for g in groups if g["react_on"]})
    nxt = [d for d in react_days if d > day]
    rd = nxt[0] if nxt else (react_days[0] if react_days else day)
    ok = [g for g in groups if g.get("ok")]
    tagged = [g for g in groups if g["tags"] not in (["その他"], ["訂正"])]
    tx = [g["topix"] for g in ok if g["slot"] == "引け後"]
    up = sum(1 for g in ok if g["ex"] > 0)
    subj = f"📰 開示→次の日の値動き（試験）{wd(day)}の開示 {len(groups)}社 → {wd(rd)}"
    L = ["━" * 24, f"📰 開示→次の日の値動き（試験）{wd(day)}の開示 → {wd(rd)}", "━" * 24, "", "【要点】",
         f"・開示 {n_docs}件 → 同じ会社・同じ日をまとめて {len(groups)}社（種類あり {len(tagged)}社・種類なし {len(groups) - len(tagged)}社）",
         f"・測れた {len(ok)}社" + (f"（引け後の開示と同じ時間の TOPIX {pct(statistics.median(tx))}）" if tx else "")]
    if ok:
        L.append(f"・TOPIX と比べて上げた {up}社・下げた {len(ok) - up}社（平均 {pct(statistics.mean(g['ex'] for g in ok))}）")
        hi = max(ok, key=lambda g: g["ex"])
        lo = min(ok, key=lambda g: g["ex"])
        L.append(f"・いちばん上げた {hi['code']} {short(hi['name'], 14)} {pct(hi['ex'])}／いちばん下げた {lo['code']} {short(lo['name'], 14)} {pct(lo['ex'])}")
    L += ["", "【種類ごと（TOPIX と比べた差・開示の直前 → 次の丸1日の引け）】"]
    table = kind_table(groups)
    for k, n, m, md, r in table:
        if n >= MIN_N:
            L.append(f"・{k} {n}社：平均 {pct(m)}・中央値 {pct(md)}・上げ {r * 100:.0f}%")
    few = [f"{k} {n}社 {pct(m)}" for k, n, m, md, r in table if n < MIN_N]
    if few:
        L.append(f"・{MIN_N}社未満（参考・平均だけ）：" + "／".join(few))
    if not ok:
        L.append("・測れた会社なし")
    L.append("（1社に種類が2つ以上あれば、どちらの行にも入る）")
    ranked = sorted(ok, key=lambda g: -g["ex"])
    for title, lst in (("【大きく上げた10社（TOPIX比）】", ranked[:TOP_N]),
                       ("【大きく下げた10社（TOPIX比）】", list(reversed(ranked[-TOP_N:])) if len(ranked) > TOP_N else [])):
        if not lst:
            continue
        L += ["", title]
        for i, g in enumerate(lst, 1):
            L += stock_line(i, g)
    for title, key in (("【上方修正（TOPIX比の大きい順）】", "上方修正"), ("【下方修正（TOPIX比の小さい順）】", "下方修正")):
        lst = [g for g in ok if key in kind_keys(g)]
        lst.sort(key=lambda g: g["ex"], reverse=(key == "上方修正"))
        if not lst:
            continue
        L += ["", title + (f"＝{len(lst)}社のうち {LIST_N}社" if len(lst) > LIST_N else "")]
        for i, g in enumerate(lst[:LIST_N], 1):
            L += stock_line(i, g)
    if trend:
        L += trend_lines(trend)
    L += ["", "━" * 24,
          "※ 読むだけの記録（試験・PILLAR_PREREG.md「J51」）。1日だけの数字で、売買の決まりではない（決まりにするなら別に事前登録して確かめる）",
          "※ 測り方：開示の直前の値段（引け後＝その日の終値・場中＝開示の時刻までの最後の5分足・寄り前＝前の日の終値）→ 開示のあとの最初の丸1日の引け。"
          "TOPIX は 1306 の同じ時間。窓＝反応の日の寄り ÷ 前の日の終値",
          "※ 種類は表題の言葉で付けた（業績修正・差異の向きは PDF の表から）。AI は使っていない＝トークンは使わない。値段は Yahoo の日足と5分足（約16分遅れ）",
          "※ 同じ会社の同じ日の開示は1社にまとめた。ETF・投資信託・投資法人は除いた"]
    return subj, "\n".join(L)


# ════════════════════ あとから埋める（1週間・1か月）＝純関数 ════════════════════

def ohlc_map(bars):
    """[(時刻, 始, 高, 安, 終, 出来高)] → {日付 ISO: (始, 高, 安, 終)}"""
    return {t.date().isoformat(): (o, h, l, c) for t, o, h, l, c, v in bars}


def horizon_day(days, react_on, k):
    """反応の日を1日目として k 日目の取引日（まだ無ければ None）"""
    if react_on not in days:
        return None
    i = days.index(react_on) + k - 1
    return days[i] if i < len(days) else None


def matured(day, now):
    """その日の引けが確定したか（当日は 16:30 より後）"""
    t = now.date().isoformat()
    return day < t or (day == t and (now.hour, now.minute) >= READY)


def close_upto(ohlc, start, end):
    """start〜end のうち end 以前で最後の終値（取引の無かった日は前の値のまま）"""
    ks = [d for d in ohlc if start <= d <= end]
    return ohlc[max(ks)][3] if ks else None


def needs_fill(r, days, now):
    """1週間・1か月のうち、引けが確定したのにまだ空いている升があるか"""
    if str(r.get("ok")) != "1" or not r.get("react") or not r.get("react_on"):
        return False
    for key, _, _, k in HORIZONS:
        if r.get(key):
            continue
        if r["react_on"] < days[0]:
            return True                                   # 古すぎて取引日が分からない＝na にする
        t = horizon_day(days, r["react_on"], k)
        if t and matured(t, now):
            return True
    return False


def fill_row(r, days, ohlc, tx, now):
    """台帳の1行（文字の dict）に 1週間・1か月を足す。値段は比で戻す（直前の値段＝反応の日の終値 ÷ (1＋反応)）。
    株式分割があっても同じ Yahoo の系列から取るのでそろう。→ 変えたら True"""
    R = r["react_on"]
    changed = False
    for key, txk, exk, k in HORIZONS:
        if r.get(key):
            continue
        if R < days[0] or ((ohlc and tx) and (R not in ohlc or R not in tx)):
            r[key] = r[txk] = r[exk] = "na"              # 古すぎる・その銘柄の反応の日の値段が無い（上場廃止など）
            changed = True
            continue
        if not ohlc or not tx:
            continue                                      # 値段が取れなかった回＝次の回にもう一度
        t = horizon_day(days, R, k)
        if not t or not matured(t, now):
            continue
        base = ohlc[R][3] / (1 + float(r["react"]))
        tbase = tx[R][3] / (1 + float(r["topix"]))
        c, tc = close_upto(ohlc, R, t), close_upto(tx, R, t)
        if c is None or tc is None:
            r[key] = r[txk] = r[exk] = "na"
            changed = True
            continue
        d, x = c / base - 1, tc / tbase - 1
        r[key], r[txk], r[exk] = f"{d:.6f}", f"{x:.6f}", f"{d - x:.6f}"
        if k == 5:
            win = [ohlc[x_] for x_ in ohlc if R <= x_ <= t]
            r["hi5"] = f"{max(b[1] for b in win) / base - 1:.6f}"
            r["lo5"] = f"{min(b[2] for b in win) / base - 1:.6f}"
        changed = True
    return changed


def fill_all(rows, days, now, getter=None, pause=PAUSE, log=print):
    """台帳の行のうち、引けが確定した 1週間・1か月を埋める（その銘柄の日足を1回だけ取る）。→ 埋めた行の数"""
    getter = getter or fetch_chart
    todo = [r for r in rows if needs_fill(r, days, now)]
    if not todo:
        return 0
    tx = ohlc_map(getter(TOPIX, "1d", "3mo") or [])
    cache, n = {}, 0
    for r in todo:
        c = r["code"]
        if c not in cache:
            time.sleep(pause)
            cache[c] = ohlc_map(getter(c, "1d", "3mo") or [])
        n += 1 if fill_row(r, days, cache[c], tx, now) else 0
    log(f"  1週間・1か月を埋めた：{n}行（{len(cache)}社）")
    return n


# ════════════════════ 傾向（累積と、1回だけの判定）＝純関数 ════════════════════

def row_kinds(r):
    tags = [t for t in (r.get("tags") or "").split("|") if t]
    return kind_keys({"tags": tags, "rev": r.get("rev") or "", "diff": r.get("diff") or ""})


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def cell_values(rows, kind, col, since=None, until=None):
    """→ [(開示の日, その列の値)]（測れた行だけ・na と空は除く）"""
    out = []
    for r in rows:
        if str(r.get("ok")) != "1" or (since and r["date"] < since) or (until and r["date"] > until):
            continue
        v = num(r.get(col))
        if v is not None and kind in row_kinds(r):
            out.append((r["date"], v))
    return out


def cluster_z(vals):
    """開示の日ごとにまとめた（同じ日の会社は同じ相場の動きを受ける）標準誤差で、平均 ÷ 標準誤差。→ (平均, z, 日数)"""
    n = len(vals)
    if n == 0:
        return None, None, 0
    mean = sum(v for _, v in vals) / n
    by = {}
    for d, v in vals:
        s_, k = by.get(d, (0.0, 0))
        by[d] = (s_ + v, k + 1)
    g = len(by)
    if g < 2:
        return mean, None, g
    var = g / (g - 1) * sum((s_ - k * mean) ** 2 for s_, k in by.values()) / n ** 2
    return mean, (mean / var ** 0.5 if var > 0 else None), g


def z_crit(cells=len(KINDS) * len(H_KEYS), alpha=ALPHA):
    return statistics.NormalDist().inv_cdf(1 - alpha / (2 * cells))


def judge_cell(vals, today):
    """1つの升（種類×期間）を判定できれば判定して返す。できなければ None（まだたまり中）"""
    if today < JUDGE_FROM or len(vals) < JUDGE_N:
        return None
    mean, z, g = cluster_z(vals)
    if g < JUDGE_DAYS or z is None:
        return None
    vs = sorted(vals)
    h = len(vs) // 2
    m1 = sum(v for _, v in vs[:h]) / h
    m2 = sum(v for _, v in vs[h:]) / (len(vs) - h)
    zc = z_crit()
    if z >= zc and m1 > 0 and m2 > 0:
        st = "✅ 上向き"
    elif z <= -zc and m1 < 0 and m2 < 0:
        st = "✅ 下向き"
    else:
        st = "✕ 見えない"
    return {"decided_on": today, "n": len(vals), "days": g, "mean": round(mean, 6), "z": round(z, 3),
            "z_crit": round(zc, 3), "first_half": round(m1, 6), "second_half": round(m2, 6), "status": st}


def build_trend(rows, prev, today):
    """→ 傾向の記録。cells＝11/9 からの累積（読むだけ）・verdicts＝1回だけの判定（一度決めたら変えない）"""
    verdicts = dict((prev or {}).get("verdicts") or {})
    cells = {}
    for kind in KINDS:
        c = {}
        for name, col in H_KEYS:
            vals = [v for _, v in cell_values(rows, kind, col)]
            c[name] = {"n": len(vals)}
            if vals:
                c[name].update(mean=round(statistics.mean(vals), 6), median=round(statistics.median(vals), 6),
                               up=round(sum(1 for v in vals if v > 0) / len(vals), 3))
            key = f"{kind}|{name}"
            if key not in verdicts:
                v = judge_cell(cell_values(rows, kind, col, since=JUDGE_START, until=today), today)
                if v:
                    verdicts[key] = v
        for name, col in (("1週間の途中の高値", "hi5"), ("1週間の途中の安値", "lo5")):
            vals = [v for _, v in cell_values(rows, kind, col)]
            if vals:
                c[name] = {"n": len(vals), "median": round(statistics.median(vals), 6)}
        cells[kind] = c
    return {"registered": "J51（2026-11-10 夜の追記）", "updated": today, "start": START, "judge_start": JUDGE_START,
            "judge_from": JUDGE_FROM, "judge_n": JUDGE_N, "judge_days": JUDGE_DAYS, "z_crit": round(z_crit(), 3),
            "cells": cells, "verdicts": verdicts}


def trend_lines(tr, min_n=MIN_N):
    """メールの「これまでの傾向」の行"""
    L = ["", f"【これまでの傾向（{wd(tr['start'])}からの累積・TOPIX と比べた差の平均・読むだけ）】"]
    rows = [(k, c) for k, c in tr["cells"].items() if c["次の日"]["n"] >= min_n]
    rows.sort(key=lambda kc: -kc[1]["次の日"]["n"])
    for k, c in rows:
        parts = []
        for name, _ in H_KEYS:
            x = c[name]
            parts.append(f"{name} {pct(x.get('mean'))}（{x['n']}社）" if x["n"] else f"{name} —")
        L.append(f"・{k}：" + "／".join(parts))
        hi, lo = c.get("1週間の途中の高値"), c.get("1週間の途中の安値")
        if hi and lo and hi["n"] >= min_n:
            L.append(f"   1週間の途中の値幅（中央値・TOPIX を引かない）：高値 {pct(hi['median'])}・安値 {pct(lo['median'])}")
    if not rows:
        L.append(f"・まだ {min_n}社以上たまった種類なし")
    done = [(k, v) for k, v in sorted(tr["verdicts"].items())]
    if done:
        L.append("・判定（1回だけ・固定）：" + "／".join(f"{k.replace('|', 'の')} {v['status']}（{v['n']}社・{pct(v['mean'])}）"
                                                for k, v in done))
    L.append(f"（{min_n}社以上の種類だけ。判定は {tr['judge_from']} 以降、{tr['judge_start']} からの開示で"
             f"升ごとに {tr['judge_n']}社・開示の日 {tr['judge_days']}日がたまったら1回だけ＝{len(KINDS) * len(H_KEYS)}の升で割った厳しい基準）")
    return L


# ════════════════════ 取る（Yahoo） ════════════════════

def fetch_chart(code, interval, rng, tries=3):
    """Yahoo の足 → [(JST の時刻, 始, 高, 安, 終, 出来高)]（値の欠けた足は除く）。取れなければ None"""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{code}.T?range={rng}&interval={interval}"
    for k in range(tries):
        try:
            d = json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30))["chart"]["result"][0]
            q = d["indicators"]["quote"][0]
            out = []
            for t, o, h, l, c, v in zip(d.get("timestamp") or [], q["open"], q["high"], q["low"], q["close"], q["volume"]):
                if None in (o, h, l, c):
                    continue
                out.append((dt.datetime.fromtimestamp(t, JST), float(o), float(h), float(l), float(c), float(v or 0)))
            return out
        except Exception:  # noqa: BLE001
            time.sleep(1 + 2 * k)
    return None


def measure_all(groups, days, getter=fetch_chart, pause=PAUSE, log=print):
    tx_d = getter(TOPIX, "1d", "3mo") or []
    tx_5 = getter(TOPIX, "5m", "1mo") or []
    tx_daily = daily_map(tx_d)
    cache = {}
    for g in groups:
        c = g["code"]
        if c not in cache:
            time.sleep(pause)
            cache[c] = {"d": daily_map(getter(c, "1d", "3mo") or []), "5": None}
        if g["slot"] == "場中" and cache[c]["5"] is None:
            time.sleep(pause)
            cache[c]["5"] = getter(c, "5m", "1mo") or []
        g.update(measure(g, cache[c]["d"], cache[c]["5"], days, tx_daily, tx_5))
    log(f"  値段：{len(cache)}社・測れた {sum(1 for g in groups if g.get('ok'))}社")
    return groups


# ════════════════════ ためる・送る ════════════════════

def read_ledger(path=LEDGER):
    try:
        with open(path, encoding="utf-8-sig") as fh:
            return list(csv.DictReader(fh))
    except OSError:
        return []


def ledger_rows(groups):
    out = []
    for g in groups:
        r = {"date": g["date"], "code": g["code"], "slot": g["slot"], "time": g["time"], "docs": len(g["docs"]),
             "tags": "|".join(g["tags"]), "rev": g["rev"], "diff": g["diff"], "base_on": g.get("base_on", ""),
             "react_on": g["react_on"] or "", "ok": g.get("ok", 0)}
        for k in ("gap", "rest", "react", "topix", "ex"):
            r[k] = "" if g.get(k) is None else f"{g[k]:.6f}"
        out.append(r)
    return out


def save_ledger(rows, path=LEDGER):
    rows = sorted(rows, key=lambda r: (r["date"], r["time"], r["code"]))
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in COLS})


def read_json(path, empty):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return empty


def save_json(obj, path):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1)
        fh.write("\n")


def read_days(path=DAYS):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {"start": START, "days": {}}


def pending_days(now, done, trading_days, start=START, look=LOOK_DAYS):
    """まだ送っていない開示の日のうち、反応の日の引けが済んだもの（古い順）"""
    out = []
    for k in range(look, -1, -1):
        d = (now.date() - dt.timedelta(days=k)).isoformat()
        if d < start or d in done or dt.date.fromisoformat(d).weekday() >= 5:
            continue
        nxt = next((x for x in trading_days if x > d), None)
        if not nxt:
            continue
        if nxt == now.date().isoformat() and (now.hour, now.minute) < READY:
            continue
        out.append(d)
    return out


def send(subject, body):
    """→ True（送れた）／False（設定なし＝送らない）"""
    import mail_html
    sender = os.environ.get("GMAIL_USER", "")
    password = os.environ.get("GMAIL_APP_PASSWORD", "")
    recipient = os.environ.get("ALERT_RECIPIENT", "") or sender
    if not sender or not password:
        print("  ⚠️ GMAIL_USER / GMAIL_APP_PASSWORD 未設定＝送信スキップ")
        return False
    msg = mail_html.message(subject, body, sender, recipient)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as server:
        server.login(sender, password)
        server.send_message(msg)
    print(f"✅ 送信しました: {subject}")
    return True


def run_day(day, trading_days, events, getter=fetch_chart, fetcher=T.fetch_day, log=print):
    """→ (出来事, 開示の件数) か None（一覧が取れない）"""
    got = fetcher(dt.date.fromisoformat(day))
    if got is None:
        log(f"  {day}: TDnet の一覧が取れない")
        return None
    total, rows = got
    rows = [r for r in rows if not skip_row(r)]
    groups = group_rows(rows, day, trading_days, dirs_from_events(events, day))
    log(f"  {day}: 開示 {len(rows)}件（ETF 等を除く）→ {len(groups)}社")
    return measure_all(groups, trading_days, getter, log=log), len(rows)


def main(argv=None):
    ap = argparse.ArgumentParser(description="TDnet の開示 → 次の丸1日・1週間・1か月の値動き（読むだけ・試験）")
    ap.add_argument("--day", help="開示の日を決めて測る（YYYY-MM-DD）")
    ap.add_argument("--dry-run", action="store_true", help="送らず本文を表示するだけ（記録も書かない）")
    ap.add_argument("--no-fill", action="store_true", help="1週間・1か月を埋めない（試すときに速くする）")
    ap.add_argument("--html-out", help="メールの HTML をこのファイルにも書く")
    ap.add_argument("--now", help="時刻を決めて試す（例 2026-11-11T17:10）")
    a = ap.parse_args(argv)
    now = dt.datetime.fromisoformat(a.now).replace(tzinfo=JST) if a.now else dt.datetime.now(JST)
    today = now.date().isoformat()
    state = read_days()
    tx = fetch_chart(TOPIX, "1d", "3mo") or []
    trading_days = sorted(daily_map(tx))
    if not trading_days:
        print("🚨 1306 の日足が取れない＝今回は測らない")
        return 1
    ledger = read_ledger()
    prev_trend = read_json(TREND, {})
    if not a.no_fill:
        fill_all(ledger, trading_days, now)               # ① 引けが確定した 1週間・1か月を埋める（毎回）
    todo = [a.day] if a.day else pending_days(now, {d for d, v in state["days"].items() if v.get("mailed")}, trading_days)
    if not todo:
        print("  まだ送っていない日で、反応の日の引けが済んだものは無い")
    events = T.read_events() if todo else []
    sent = 0
    for day in todo:                                      # ② まだ送っていない開示の日を測って送る
        if sent >= MAX_MAIL:
            break
        got = run_day(day, trading_days, events)
        if got is None:
            continue
        groups, n_docs = got
        if not groups:
            state["days"][day] = {"docs": n_docs, "groups": 0, "measured": 0, "mailed": "（開示なし）"}
            continue
        old = {(r["date"], r["code"], r["react_on"]): r for r in ledger if r["date"] == day}
        new = ledger_rows(groups)
        for r in new:                                     # 測り直した日でも、埋めた 1週間・1か月は残す
            o = old.get((r["date"], r["code"], r["react_on"]))
            if o:
                r.update({k: o.get(k, "") for k in COLS[16:] if o.get(k)})
        ledger = [r for r in ledger if r["date"] != day] + new
        trend = build_trend(ledger, prev_trend, today)
        subject, body = build_mail(day, groups, n_docs, trend)
        if a.html_out:
            import mail_html
            with open(a.html_out, "w", encoding="utf-8") as fh:
                fh.write(mail_html.to_html(body, subject))
        if a.dry_run:
            print(f"Subject: {subject}\n\n{body}")
            continue
        save_ledger(ledger)                               # 送る前に台帳を書く（送ったあとに落ちても数字は残る）
        ok = send(subject, body)
        state["days"][day] = {"docs": n_docs, "groups": len(groups), "measured": sum(1 for g in groups if g.get("ok")),
                              "react_on": next((x for x in trading_days if x > day), ""),
                              "mailed": dt.datetime.now(JST).isoformat(timespec="minutes") if ok else ""}
        sent += 1 if ok else 0
    trend = build_trend(ledger, prev_trend, today)        # ③ 傾向（累積と1回だけの判定）を毎回まとめ直す
    if a.dry_run:
        print("\n".join(trend_lines(trend)))
        return 0
    save_ledger(ledger)
    save_json(trend, TREND)
    save_json(state, DAYS)
    return 0

if __name__ == "__main__":
    sys.exit(main())
