# -*- coding: utf-8 -*-
"""昇格リスト（promotion-list.md）を記録から組み立てる（2026-09-30 オーナー「成績の良いものは残して…昇格リスト登録する」）。

段は3つ（決まりは PILLAR_PREREG.md「M6」）:
  🥇 前向きでもプラス（使うかどうかはオーナーが決める）＝総当たりの前向きで1000回・幅がまるごと0より上／ほかの前向きの検証の「プラスを確認」
  👀 前向きで数えている（過去の関門と MT5 の実ティックの確かめを通った）
  🔬 昇格候補（過去のデータで関門を越えた・MT5 の確かめ待ち）
落ちたものは検証済みリスト（verified_list.py）へ。

⚠️ メールの「昇格エッジ」（signal-lab-tracker.json の status=promoted）とは別物。ここに載っても、自動でメールや売買にはつながらない。
⚠️ 手で書かない＝記録から毎回組み立てる。GitHub 側で生成＝手元から送らない（SYNC禁忌）。

実行: python promotion_list.py   （research-lists.yml・yori-forward.yml が verified_list.py のあとに回す）
"""
import datetime as dt
import sys

import screen_judge as J
import verified_list as V

OUT_MD = "promotion-list.md"


def _brief_line(x):
    if not x:
        return "—"
    s = f"{x['n']}回・期待値 {V._r(x.get('mean'))}［{V._r(x.get('lo'))}〜{V._r(x.get('hi'))}］"
    if x.get("win") is not None:
        s += f"・勝率 {V._p(x['win'])}"
    return s


def render(plus, screens, now=None):
    now = now or dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(timespec="minutes")
    items = [(s, it) for s in screens for it in s.get("promoted", [])]
    top = [(s, it) for s, it in items if it["stage"] == "plus"]
    fwd = [(s, it) for s, it in items if it["stage"] == "mt5_ok"]
    cand = [(s, it) for s, it in items if it["stage"] == "candidate"]
    L = ["# 昇格リスト", "",
         f"更新: {now}（GitHub Actions が記録から組み立てる。手で書かない）。",
         "決まり（2026-09-30 オーナー）：成績の良いものをここに載せる。過去のデータで関門を越えたもの（昇格候補）→ MT5 の実ティックでも残ったもの"
         "（前向きで数えている）→ 前向きの1000回でもプラス、と段を上がる。途中で落ちたものは `verified-list.md`（検証済みリスト）へ移る。",
         "⚠️ **メールの「昇格エッジ」（シグナル研究の promoted）とは別物**。ここに載っても、自動でメールや売買にはつながらない。", "",
         "## 🥇 前向きでもプラス（使うかどうかはオーナーが決める）", ""]
    if top or plus:
        L += ["| 検証 | 決まり | 判定日 | 前向きの成績 |", "|---|---|---|---|"]
        for s, it in top:
            f = it["forward"] or {}
            L.append(f"| {it['id']}（{it['round']}） | {s['src']}・{J.describe(s, it['id'])} | {f.get('decided_on', '—')} | {_brief_line(f)} |")
        for r in plus:
            v = r["v"]
            u = r.get("unit")
            L.append(f"| {V._label(r)} | {r['title']} | {v['decided_on']} | {v['n']}回・平均 {V._num(v['mean'], u)}［{V._num(v['lo'], u)}〜{V._num(v['hi'], u)}］ |")
    else:
        L.append("- まだ無い")
    L += ["", "## 👀 前向きで数えている（過去の関門と MT5 の確かめを通った・まだ決めない）", ""]
    if fwd:
        L += ["| 組み合わせ | 中身 | 過去（ふるい分け） | MT5 の実ティック | 前向き（登録より後だけ） |", "|---|---|---|---|---|"]
        for s, it in fwd:
            f = it["forward"]
            fw = f"{_brief_line(f)}（{f['n']}/{J.GOAL}回）" if f else f"0/{J.GOAL}回"
            L.append(f"| {it['id']}（{it['round']}） | {J.describe(s, it['id'])} | {_brief_line(it['screen'])} | {_brief_line(it['mt5'])} | {fw} |")
    else:
        L.append("- まだ無い")
    L += ["", "## 🔬 昇格候補（過去のデータで関門を越えた・MT5 の確かめ待ち）", ""]
    if cand:
        L += ["| 組み合わせ | 中身 | 回数 | 勝率 | 期待値 | 95％の幅 | PF | 偽薬 p |", "|---|---|---:|---:|---:|---|---:|---:|"]
        for s, it in cand:
            x = it["screen"]
            pf = "—" if x.get("pf") is None else f"{x['pf']:.2f}"
            pp = "—" if x.get("placebo_p") is None else f"{x['placebo_p']:.3f}"
            L.append(f"| {it['id']}（{it['round']}） | {J.describe(s, it['id'])} | {x['n']} | {V._p(x['win'])} | {V._r(x['mean'])} | "
                     f"{V._r(x['lo'])}〜{V._r(x['hi'])} | {pf} | {pp} |")
        L += ["", "⚠️ 数千通りから選んだので、関門を越えても偶然の当たりが混ざりうる。MT5 の実ティックと前向きで確かめるまで、売買の決まりにはしない。"]
    else:
        L.append("- まだ無い")
    L += ["", "## 数えている総当たり", ""]
    if screens:
        for s in screens:
            c = sum(rd["n_combos"] for rd in s.get("rounds", []))
            L.append(f"- {s['src']}：これまで {c:,}通り（ラウンド {'・'.join(rd['round'] for rd in s.get('rounds', []))}）")
    else:
        L.append("- まだ無い（手元で数えた記録が届くと載る）")
    L += ["", "詳しい決まりは `PILLAR_PREREG.md`「M6」。落ちたものの内訳は `verified-list.md`。", "", "---", "",
          "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def main():
    _, plus, _ = V.collect()
    md = render(plus, V.collect_screens())
    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
