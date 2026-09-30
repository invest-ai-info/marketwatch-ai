# -*- coding: utf-8 -*-
"""検証済みリスト（verified-list.md）を、前向きの検証の記録から組み立てる（2026-09-28 オーナー「検証結果が1000回を超えて
期待値がプラスにならないようだったら検証はストップして検証済みリストに追加していってください」）。

⚠️ 手で書かない＝記録（SOURCES の JSON の verdicts）から毎回組み立てる。前向きの検証を足したら SOURCES に1行足す。
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
]


def _label(r):
    return f"{r['sec']}-{r['id']}" if r["sec"] else r["id"]


def _pct(x):
    return "—" if x is None else f"{x * 100:+.2f}％"


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
            row = {"src": name, "sec": sec, "id": cid, "title": title, "goal": goal, "v": v,
                   "n": sum(1 for t in data.get("trades", []) if t.get("c") == cid)}
            (watching if not v else plus if v["status"] == "plus" else stop).append(row)
    return stop, plus, watching


def render(stop, plus, watching, now=None):
    now = now or dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(timespec="minutes")
    L = ["# 検証済みリスト", "",
         f"更新: {now}（GitHub Actions が記録から組み立てる。手で書かない）。",
         "決まり（2026-09-28 オーナー）：検証（前向き、または過去のデータで1回だけ数えたもの）で**1000回を超えて期待値がプラスにならなかったものは、検証をストップしてここに載せる**。"
         "「プラス」は費用後の平均の95％の幅がまるごと0より上のとき。数字は費用を引いた1回あたりの損益率。銘柄名は出さない。", "",
         "## ⏹ ストップ（期待値がプラスにならなかった）", ""]
    if stop:
        L += ["| 検証 | 決まり | 判定日 | 回数 | 平均（費用後） | 95％の幅 | 理由 |", "|---|---|---|---:|---:|---|---|"]
        for r in stop:
            v = r["v"]
            L.append(f"| {_label(r)} | {r['title']} | {v['decided_on']} | {v['n']} | {_pct(v['mean'])} | "
                     f"{_pct(v['lo'])}〜{_pct(v['hi'])} | {v['reason']} |")
    else:
        L.append("- まだ無い")
    L += ["", "## ✅ プラスを確認（使うかどうかはオーナーが決める）", ""]
    if plus:
        L += ["| 検証 | 決まり | 判定日 | 回数 | 平均（費用後） | 95％の幅 |", "|---|---|---|---:|---:|---|"]
        for r in plus:
            v = r["v"]
            L.append(f"| {_label(r)} | {r['title']} | {v['decided_on']} | {v['n']} | {_pct(v['mean'])} | {_pct(v['lo'])}〜{_pct(v['hi'])} |")
    else:
        L.append("- まだ無い")
    L += ["", "## 👀 いま前向きで数えているもの", ""]
    L += [f"- {_label(r)} {r['title']}（{r['n']}/{r['goal']}回）" for r in watching] or ["- 無い"]
    L += ["", "詳しい決まりは `PILLAR_PREREG.md` の各節。", "", "---", "",
          "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def main():
    md = render(*collect())
    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
