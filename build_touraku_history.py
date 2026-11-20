# -*- coding: utf-8 -*-
"""東証プライムの騰落レシオ（値上がり銘柄数／値下がり銘柄数）の日次の数を touraku-history.json に書く。
責務は「日足から上げ下げを数える」と「JSON の読み書き」だけ。HTML は触らない。ネットワークも叩かない。

🔁 2026-11-20 J-Quants をやめて Yahoo の日足に替えた（オーナー決定「A と B から直す」）:
  J-Quants の公式の案内（https://jpx-jquants.com/ja/help/usage）では、取ったデータや分析結果を
  サイトで第三者に見せること・続けて配信することが × とされている。旧版はプライム全銘柄の終値を
  J-Quants から取り、健康度ページに「出典: J-Quants」で毎日出していた（弁護士の相談メモ⑪ の A）。
  いまは build_jp_highs.py が毎夕 東証の全銘柄（約3,700・市場区分つき）の日足を Yahoo から2年分
  取っているので、その中のプライムの銘柄で上げ下げを数える（取りに行く回数は増えない）。
  ⚠️ J-Quants の API を GitHub 側で呼び戻さない（check_site_consistency.py が見張る）。

数え方（旧版と同じ定義）:
  市場の営業日＝プライムの銘柄の半分以上に足がある日（Yahoo がまれに休みの日に出す足を数えない）。
  営業日の並びで隣り合う2日の両方に終値がある銘柄だけを比べ、上がった数・下がった数を数える
  （変わらずと、前の営業日に売買の無かった銘柄は数えない）。
  ratio25 ＝ 直近25営業日の上がった数の合計 ÷ 下がった数の合計 × 100。
  ⚠️ プライムかどうかは「いまの」東証の一覧で決める（旧版の J-Quants も同じ）。

毎回2年分の日足から全部数え直して置き換える（足したり混ぜたりしない）＝ Yahoo が過去の足を直せば
次の回で直る。ファイルの "source" が SOURCE でないもの（＝旧版の J-Quants の数）は読む側が
空として扱う＝置き換わるまで、J-Quants から来た数は1つも表に出ない。

使う側:
  build_jp_highs.py           … update_from_bars() で書く（jp-highs.yml・平日の夕方）
  build_health_history.py     … load_points() と ratio25 で健康度の履歴の系列を作る
  generate_market_news.py     … load_points() と ratio25 で健康度ページの今の値を出す

実行（中身を見るだけ）: python build_touraku_history.py
"""
import datetime as dt
import json
import math
import os
import sys

JST = dt.timezone(dt.timedelta(hours=9))
HERE = os.path.dirname(os.path.abspath(__file__))
HISTORY_PATH = os.path.join(HERE, "touraku-history.json")

SOURCE = "yahoo-daily"     # ⚠️ これ以外の source のファイルは読まない（旧版の J-Quants の数を出さないため）
SOURCE_LABEL = "東証プライムの全銘柄の終値（Yahoo の日足）から当サイトが数えた25日騰落レシオ"
RATIO_WINDOW = 25          # 「25日騰落レシオ」の窓
KEEP_POINTS = 300          # 残す営業日（健康度の履歴は1年＝約245営業日＋窓の25日）
MIN_DAY_COVER = 0.5        # その日に足のある銘柄がプライムのこの割合に届かない日は営業日と見なさない


def ratio25(points):
    """直近 RATIO_WINDOW 日ぶんの up/down 合計から25日騰落レシオを計算。
    窓に満たなければ None（正直に「まだ計算できない」を返す）。"""
    if len(points) < RATIO_WINDOW:
        return None
    window = points[-RATIO_WINDOW:]
    up_sum = sum(p[1] for p in window)
    down_sum = sum(p[2] for p in window)
    if down_sum == 0:
        return None
    return round(up_sum / down_sum * 100, 1)


def compute_up_down(prev_closes, today_closes):
    """2日分の {Code: Close} から (値上がり銘柄数, 値下がり銘柄数) を数える。純関数。"""
    up = down = 0
    for code, c in today_closes.items():
        p = prev_closes.get(code)
        if p is None:
            continue
        if c > p:
            up += 1
        elif c < p:
            down += 1
    return up, down


def points_from_bars(bars_by_code, asof=None, min_cover=MIN_DAY_COVER):
    """{コード: [(日付, 高値, 安値, 終値, 出来高), ...]} → [[日付, 上がった数, 下がった数], ...]（古い順）。純関数。

    bars_by_code にはプライムの銘柄だけを渡す。asof より後の日は数えない。
    """
    closes = {}                      # {日付: {コード: 終値}}
    for code, bars in bars_by_code.items():
        for b in bars:
            d, c = b[0], b[3]
            if c is None or (asof and d > asof):
                continue
            closes.setdefault(d, {})[code] = float(c)
    need = max(1, math.ceil(len(bars_by_code) * min_cover))
    days = sorted(d for d, m in closes.items() if len(m) >= need)
    out = []
    for prev_d, d in zip(days, days[1:]):
        up, down = compute_up_down(closes[prev_d], closes[d])
        if up + down > 0:
            out.append([d, up, down])
    return out


def empty_history():
    return {"updated_at": None, "source": SOURCE, "points": [], "health": {"last_ok": None, "points": 0}}


def load_history(path=HISTORY_PATH):
    """壊れていても・無くても、必ず正しい形の器を返す。source が SOURCE でなければ空の器（旧版の J-Quants の数）。"""
    try:
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
    except Exception:
        return empty_history()
    if not isinstance(doc, dict) or doc.get("source") != SOURCE:
        return empty_history()
    base = empty_history()
    base["updated_at"] = doc.get("updated_at")
    base["points"] = [list(p) for p in (doc.get("points") or [])]
    base["health"]["last_ok"] = (doc.get("health") or {}).get("last_ok")
    base["health"]["points"] = len(base["points"])
    return base


def load_points(path=HISTORY_PATH):
    """読む側の入口（健康度の履歴・健康度ページ）。旧版の J-Quants の数なら []。"""
    return load_history(path)["points"]


def save_history(doc, path=HISTORY_PATH):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))


def build_doc(points, now_jst_date):
    """数えた点から保存する形を作る。純関数。"""
    pts = [list(p) for p in points][-KEEP_POINTS:]
    return {"updated_at": now_jst_date, "source": SOURCE, "points": pts,
            "health": {"last_ok": pts[-1][0] if pts else None, "points": len(pts)}}


def is_current(path, asof):
    """touraku-history.json が Yahoo の数で、asof の日まで入っているか（build_jp_highs の「もう済んだ」の判定用）。"""
    pts = load_points(path)
    return bool(pts) and bool(asof) and pts[-1][0] >= asof


def update_from_bars(prime_bars, asof, path=HISTORY_PATH, now=None):
    """build_jp_highs.py から呼ぶ。プライムの日足で全部数え直して置き換える。戻り値はログ用の1行。

    点が窓（25日）に届かないときは書かない（日足が取れなかった回に、いまの良いファイルを壊さない）。
    """
    pts = points_from_bars(prime_bars, asof)
    if len(pts) < RATIO_WINDOW:
        return f"⚠️ 騰落の数が {len(pts)}日しか作れない（プライム {len(prime_bars)}銘柄）＝書かない"
    now = now or dt.datetime.now(JST)
    doc = build_doc(pts, now.strftime("%Y-%m-%d"))
    save_history(doc, path)
    last = doc["points"][-1]
    return (f"{len(doc['points'])}日（{doc['points'][0][0]}〜{last[0]}）・プライム {len(prime_bars)}銘柄・"
            f"最後の日 上がった {last[1]}／下がった {last[2]}・25日騰落レシオ {ratio25(doc['points'])}")


def main():
    doc = load_history()
    pts = doc["points"]
    print(f"{HISTORY_PATH}: source={SOURCE if pts else '（空・または旧版の J-Quants の数＝読まない）'}")
    print(f"  points: {len(pts)}件（最新 {pts[-1] if pts else '-'}）")
    r25 = ratio25(pts)
    print(f"  現在の25日騰落レシオ: {r25 if r25 is not None else 'N/A（データ不足）'}")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
