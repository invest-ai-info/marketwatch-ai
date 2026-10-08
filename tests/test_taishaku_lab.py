# -*- coding: utf-8 -*-
"""J36 貸借銘柄だけでも残るか（taishaku_lab.py）のテスト。2026-10-08 新設。

値動きはすべて作り物。確かめること＝①事前登録と定数の一致 ②資料のリンクの拾い方・銘柄コードの列・区分の列から貸借銘柄を拾う
③probe の表示に銘柄名が出ない ④行ごとの貸借銘柄の印と判定の言葉 ⑤出力に銘柄コードを出さない ⑥ワークフローと SYNC 禁忌。

実行:  python tests/test_taishaku_lab.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import taishaku_lab as K  # noqa: E402


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## J36 J31 の売りは、制度信用で空売りできる「貸借銘柄」だけでも残るか" in text and "**目隠しではない**" in text
    assert "`--probe`" in text and "**いまの一覧を昔に当てている**" in text
    assert K.N_Q == 2 and abs(K.ALPHA - 0.025) < 1e-12 and "p＜0.05÷2＝97.5％" in text and K.MIN_LIST == 1000


def test_links_and_columns():
    html = '<a href="/a/list.xlsx">貸借銘柄一覧 (Excel)</a> <a href="https://x.jp/b.pdf"><span>週末残高</span></a> <a href="/c.html">他</a>'
    assert K.file_links(html) == [("https://www.jpx.co.jp/a/list.xlsx", "貸借銘柄一覧 (Excel)"), ("https://x.jp/b.pdf", "週末残高")]
    df = pd.DataFrame({"名": [f"会社{i}" for i in range(80)], "コード": [str(1300 + i) for i in range(79)] + ["130A"],
                       "区分": ["貸借銘柄"] * 50 + ["制度信用銘柄"] * 30})
    assert K.code_column(df) == "コード" and K.code_column(df[["名"]]) is None
    got = K.taishaku_codes(df, "コード", "区分")
    assert len(got) == 50 and "1300" in got and "130A" not in got
    desc = K.describe(df)
    assert desc["区分"] == {"貸借銘柄": 50, "制度信用銘柄": 30} and "会社" not in json.dumps(desc, ensure_ascii=False)


def _row(day, code, gap, rc, turnover=15.0, rprev=0.0, ratio=1.0):
    r = np.full(len(K.C), np.nan)
    r[[K.C["day"], K.C["code"], K.C["gap"], K.C["rprev"], K.C["turnover"], K.C["tv_ratio"], K.C["rclose"], K.C["rhigh"], K.C["rlow"]]] = \
        [day, code, gap, rprev, turnover, ratio, rc, max(rc, 0), min(rc, 0)]
    return r


def _synthetic(own_tai, own_other, n=520, days_per_era=20, seed=1):
    """目印 B・C の株（20％）のうち、偶数の番号＝貸借銘柄は own_tai、奇数は own_other だけ下がる"""
    rng = np.random.default_rng(seed)
    rows = []
    for start in ("2008-03-03", "2018-03-01", "2025-03-03"):
        d0 = dt.date.fromisoformat(start)
        days = [d for d in (d0 + dt.timedelta(i) for i in range(days_per_era * 2)) if d.weekday() < 5][:days_per_era]
        for d in days:
            up = rng.uniform(size=n) < 0.2
            for c in range(n):
                own = (own_tai if c % 2 == 0 else own_other) if up[c] else 0.0
                rc = -own + rng.normal(0, 0.004)
                rows.append(_row(d.toordinal(), c, (0.04 if up[c] else 0.0) + rng.normal(0, 0.002), rc,
                                 rprev=0.06 if up[c] else 0.0, ratio=7.0 if up[c] else 1.0))
    return np.array(rows)


def test_flags_and_judge():
    codes = [str(1000 + i) for i in range(520)]
    tai_list = {c for i, c in enumerate(codes) if i % 2 == 0}
    is_tai = lambda X: K.flags(X, codes, tai_list)  # noqa: E731
    good = K.analyze(_synthetic(0.01, 0.0), is_tai)
    assert all(x["summary"] == K.OK_ALL for x in good["groups"].values())
    assert abs(good["groups"]["K3"]["read"]["e1"]["share"] - 0.5) < 0.1
    bad = K.analyze(_synthetic(0.0, 0.01, seed=2), is_tai)                # 取り分が貸借銘柄でない株だけにある
    g = bad["groups"]["K2"]
    assert g["summary"] == K.NONE and g["read"]["e2"]["other"]["mean"] > 0.008
    md = K.render_md({"generated_at": "x", "prereg_sha256": "0" * 64, "result": dict(good, list_note="テスト", n_codes=520)})
    assert "## まとめ" in md and "貸借銘柄の割合" in md and "投資助言ではありません" in md and not any(c in md for c in ("1000", "1002"))
    out = K.check_summary(_synthetic(0.01, 0.0, seed=3), is_tai, 260, {"daily": [], "h1": [], "m5": []}, 520, None)
    assert out["n_list"] == 260 and out["eras"]["e1"]["K3"]["taishaku"] > 0 and "mean" not in repr(out)


def test_list_reading_not_decided_yet_fails_safely():
    try:
        K.load_list()
        assert False, "読み方を決める前に数えてしまう"
    except RuntimeError as e:
        assert "--probe" in str(e)


def test_workflow_and_sync_forbidden():
    wf = open(".github/workflows/taishaku-lab.yml", encoding="utf-8").read()
    assert "python -u taishaku_lab.py --probe" in wf and "python -u taishaku_lab.py --check" in wf and "options: [probe, check, run]" in wf
    assert "python tests/test_taishaku_lab.py" in wf and "taishaku-lab.json taishaku-lab.md" in wf and "restore-keys: jp-bars-" in wf
    assert '"taishaku-lab.json", "taishaku-lab.md"' in open("check_site_consistency.py", encoding="utf-8").read()


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"✅ {name}")
            except AssertionError as e:
                fails += 1
                print(f"❌ {name}: {e}")
    sys.exit(1 if fails else 0)
