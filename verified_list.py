# -*- coding: utf-8 -*-
"""検証済みリスト（verified-list.md）を、前向きの検証の記録から組み立てる（2026-09-28 オーナー「検証結果が1000回を超えて
期待値がプラスにならないようだったら検証はストップして検証済みリストに追加していってください」）。

⚠️ 手で書かない＝記録（SOURCES の JSON の verdicts）から毎回組み立てる。前向きの検証を足したら SOURCES に1行足す。
🆕 2026-09-30 総当たりのふるい分け（M6 など・kind: screen）は SCREEN_SOURCES に1行（理由ごとの件数と直す出発点の候補を載せる）。
⚠️ GitHub 側で生成＝手元から送らない（SYNC禁忌）。

実行: python verified_list.py   （前向きの検証のワークフローが、それぞれの計算のあとに回す）
"""
import datetime as dt
import json
import sys

OUT_MD = "verified-list.md"
# (記録の JSON, 登録の名前, 事前登録の節)
SOURCES = [
    ("yori-forward.json", "J4F 寄り付きの前向き（前の日に出来高が急増した銘柄）", "J4F"),
    ("london-lab.json", "L1・L2 ロンドン時間のドルの流れ（過去2年・1回だけ数えた）", ""),   # 🆕 2026-09-30 過去のデータで1000回以上
    ("london-hold-lab.json", "L4 ロンドン時間に入って長めに持つ（過去2年・1回だけ数えた）", "L4"),   # 🆕 2026-09-30
    ("s4-level-fade.json", "S4 前日のロンドン時間の高値・安値の反発×勝率型の出口（過去のデータ・1回だけ数えた・手元の MT5）", ""),   # 🆕 2026-09-30 手元で数えた記録の書き出し
    ("auto-forward.json", "AT3 4時間足のメールの合図をデモ口座で自動に建てる（前向き・手元の MT4）", ""),   # 🆕 2026-09-30 数字は R（unit: R）
]
# 🆕 2026-09-30 総当たりのふるい分け（kind: screen・判定は screen_judge.py）。組み合わせが数千あるので、1行ずつではなく
# 理由ごとの件数・昇格のあとで消えたもの・直す出発点の候補だけを載せる。関門を越えたものは昇格リスト（promotion_list.py）へ
SCREEN_SOURCES = [
    ("m6-screen.json", "M6 ポンド円・ロンドン時間の総当たり（手元の MT5 の5分足・過去に1回ずつ）"),
]


def _label(r):
    return f"{r['sec']}-{r['id']}" if r["sec"] else r["id"]


def _progress(r):
    """数えている途中の書き方。goal が回数なら「n/goal回」、期間の区切り（文字）なら「n回・期間」"""
    g = r.get("goal")
    return f"{r['n']}/{g}回" if isinstance(g, int) else f"{r['n']}回・{g}"


def _pct(x):
    return "—" if x is None else f"{x * 100:+.2f}％"


def _num(x, unit):
    """記録の単位で書く（unit: R＝損切りまでの幅を1とした単位／既定＝損益率）"""
    return _r(x) if unit == "R" else _pct(x)


def collect(sources=SOURCES):
    stop, plus, watching = [], [], []
    for path, name, sec in sources:
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            continue
        titles, goal = data.get("titles", {}), data.get("goal")
        for cid, title in titles.items():
            v = (data.get("verdicts") or {}).get(cid)
            if not v and data.get("kind") == "backtest":
                continue          # 過去のデータで1回だけ数えたもの＝ストップ以外は載せない（前向きは別に登録する）
            row = {"src": name, "sec": sec, "id": cid, "title": title, "goal": goal, "v": v, "unit": data.get("unit", "pct"),
                   "n": sum(1 for t in data.get("trades", []) if t.get("c") == cid)}
            (watching if not v else plus if v["status"] == "plus" else stop).append(row)
    return stop, plus, watching


def collect_screens(sources=None):
    out = []
    for path, name in (SCREEN_SOURCES if sources is None else sources):
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            continue
        if data.get("kind") == "screen":
            out.append(dict(data, src=name))
    return out


def _r(x):
    return "—" if x is None else f"{x:+.3f}R"


def _p(x):
    return "—" if x is None else f"{x * 100:.1f}％"


def render_screens(screens):
    """総当たりのふるい分けの節（落ちたもの）"""
    import screen_judge as J
    L = ["## 🧮 総当たりのふるい分け（過去のデータで1回ずつ・落ちたもの）", "",
         "組み合わせが数千あるので、理由ごとの件数だけを載せる（全部の表は手元の `research/` の下）。"
         "関門を越えたものは `promotion-list.md`（昇格リスト）へ。数字は1回あたりの損益（R＝損切りまでの幅を1とした単位・費用後）。", ""]
    if not screens:
        return L + ["- まだ無い（手元で数えた記録が届くと載る）", ""]
    for s in screens:
        L += [f"### {s['src']}", ""]
        for rd in s.get("rounds", []):
            c = s.get("counts", {}).get(rd["round"], {})
            parts = [f"{J.REASONS[k]} {c.get(k, 0):,}" for k in J.SCREEN_REASONS]
            L.append(f"- ラウンド {rd['round']}（{rd['ran_on']} 実行・{rd['n_combos']:,}通り・多重検定の総数 {rd['m_total']:,}）："
                     + "／".join(parts) + f"／**昇格候補 {c.get('candidate', 0):,}**")
            rdg = s.get("reading", {}).get(rd["round"], {})
            if rdg:
                tfname = {"M5": "5分足", "M15": "15分足", "H1": "1時間足"}
                L.append("  - 読むための数字（判定ではない）：" + "／".join(
                    f"{tfname.get(k, k)} 期待値がプラス {v['plus']}/{v['combos']}・期待値の中央値 {_r(v['median_mean'])}・勝率の中央値 {_p(v['median_win'])}"
                    for k, v in rdg.items()))
        for r in s.get("redo", []):
            L.append(f"- やり直し：ラウンド {r['round']}（{r['on']}）理由＝{r['reason']}")
        gone = s.get("stopped_after_promotion", [])
        L += ["", "#### 昇格のあとで消えたもの", ""]
        if gone:
            L += ["| 組み合わせ | ラウンド | 段階 | 判定日 | 回数 | 期待値 | 95％の幅 |", "|---|---|---|---|---:|---:|---|"]
            for g in gone:
                L.append(f"| {g['id']} {J.describe(s, g['id'])} | {g['round']} | {J.REASONS.get(g['reason'], g['reason'])} | "
                         f"{g['decided_on']} | {g['n']} | {_r(g['mean'])} | {_r(g['lo'])}〜{_r(g['hi'])} |")
        else:
            L.append("- 無い")
        near = s.get("near_misses", [])
        L += ["", f"#### 直す出発点の候補（上位{J.NEAR_TOP}・t＝期待値÷ぶれ の大きい順）", ""]
        if near:
            L += ["| 組み合わせ | ラウンド | 落ちた理由 | 回数 | 勝率 | 期待値 | 95％の幅 | PF |", "|---|---|---|---:|---:|---:|---|---:|"]
            for x in near:
                pf = "—" if x.get("pf") is None else f"{x['pf']:.2f}"
                L.append(f"| {x['id']} {J.describe(s, x['id'])} | {x['round']} | {J.REASONS.get(x['reason'], x['reason'])} | {x['n']} | "
                         f"{_p(x['win'])} | {_r(x['mean'])} | {_r(x['lo'])}〜{_r(x['hi'])} | {pf} |")
            L += ["", "⚠️ ここから選んで同じ期間で数え直すと、偶然の当たりを拾いやすい。直すときは、直す中身と理由を先に登録する（`PILLAR_PREREG.md`「M6」の「直して数え直す」）。"]
        else:
            L.append("- 無い")
        L.append("")
    return L


def render(stop, plus, watching, now=None, screens=()):
    now = now or dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(timespec="minutes")
    L = ["# 検証済みリスト", "",
         f"更新: {now}（GitHub Actions が記録から組み立てる。手で書かない）。",
         "決まり（2026-09-28 オーナー）：検証（前向き、または過去のデータで1回だけ数えたもの）で**1000回を超えて期待値がプラスにならなかったものは、検証をストップしてここに載せる**。"
         "「プラス」は費用後の平均の95％の幅がまるごと0より上のとき。数字は費用を引いた1回あたりの損益率（末尾が R のものは、損切りまでの幅を1とした単位）。銘柄名は出さない。", "",
         "## ⏹ ストップ（期待値がプラスにならなかった）", ""]
    if stop:
        L += ["| 検証 | 決まり | 判定日 | 回数 | 平均（費用後） | 95％の幅 | 理由 |", "|---|---|---|---:|---:|---|---|"]
        for r in stop:
            v = r["v"]
            u = r.get("unit")
            L.append(f"| {_label(r)} | {r['title']} | {v['decided_on']} | {v['n']} | {_num(v['mean'], u)} | "
                     f"{_num(v['lo'], u)}〜{_num(v['hi'], u)} | {v['reason']} |")
    else:
        L.append("- まだ無い")
    L += ["", "## ✅ プラスを確認（使うかどうかはオーナーが決める）", ""]
    if plus:
        L += ["| 検証 | 決まり | 判定日 | 回数 | 平均（費用後） | 95％の幅 |", "|---|---|---|---:|---:|---|"]
        for r in plus:
            v = r["v"]
            u = r.get("unit")
            L.append(f"| {_label(r)} | {r['title']} | {v['decided_on']} | {v['n']} | {_num(v['mean'], u)} | {_num(v['lo'], u)}〜{_num(v['hi'], u)} |")
    else:
        L.append("- まだ無い")
    L += ["", "## 👀 いま前向きで数えているもの", ""]
    L += [f"- {_label(r)} {r['title']}（{_progress(r)}）" for r in watching] or ["- 無い"]
    L += [""] + render_screens(screens)
    L += ["詳しい決まりは `PILLAR_PREREG.md` の各節。", "", "---", "",
          "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def main():
    md = render(*collect(), screens=collect_screens())
    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
