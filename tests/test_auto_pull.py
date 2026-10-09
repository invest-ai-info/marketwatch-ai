# -*- coding: utf-8 -*-
"""auto_pull.py（手元を GitHub の最新にそろえる）の約束ごとのテスト。2026-09-26 新設。

手で作った「手元のフォルダ」と「GitHub の ZIP」で、次を固定する:
  手元で書き換えていないファイルだけを更新する／手元で書き換えたファイルには触れず「手元だけ」「両方」を見分ける／
  触ってはいけないファイル（sync_to_github.py・mw.py・_ 始まり・research/）に触れない／GitHub 側で作るデータは
  控えを残して最新にする／GitHub で消えたファイルは控えへ移す／下見は何も書かない／起動時の設定は冪等。
  2026-10-09 追加: 手元の版が GitHub に一度あった版（前回そろえた版より新しいもの）のままなら「両方で変更」にせず
  控えを残して最新にする／--help や知らない指定では取り込みを動かさない。

実行:  python tests/test_auto_pull.py     （pytest 不要。pytest でも動く）
"""
import contextlib
import datetime
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location("auto_pull", os.path.join(ROOT, "auto_pull.py"))
A = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(A)
# テストでは GitHub に問い合わせない（過去の版をたどる関数の既定を「履歴なし」にする。使うテストは history= で渡す）
A.past_versions = lambda root, rel: iter(())

T0 = datetime.datetime(2026, 9, 26, 6, 0, tzinfo=datetime.timezone.utc)
CSC = 'SYNC_FORBIDDEN = {\n    "signals-log.json",\n    "index.html",\n}\n'
STUB = "# sync stub for cloud environment\nSYNC_FILES = [\n" + "".join(
    f'    "guide-cloud-{i:03d}.html",\n' for i in range(100)) + "]\n"
LOCAL_SYNC = 'SYNC_FILES = [\n    "a.py",\n    "b.md",\n    "c.md",\n    "d.md",\n    "gone.md",\n]\n'


def make_zip(tmp, files, name="z.zip", commit="abcdef1234567890"):
    p = os.path.join(tmp, name)
    with zipfile.ZipFile(p, "w") as z:
        z.comment = commit.encode()
        base = {"check_site_consistency.py": CSC, "sync_to_github.py": STUB}
        base.update(files)
        for rel, body in base.items():
            z.writestr("marketwatch-ai-main/" + rel, body.encode("utf-8") if isinstance(body, str) else body)
    return p


def make_local(files):
    root = tempfile.mkdtemp()
    base = {"sync_to_github.py": LOCAL_SYNC, "mw.py": "# local mw\n"}
    base.update(files)
    for rel, body in base.items():
        p = os.path.join(root, *rel.split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(body.encode("utf-8") if isinstance(body, str) else body)
    return root


def read(root, rel):
    p = os.path.join(root, *rel.split("/"))
    return open(p, "rb").read().decode("utf-8") if os.path.exists(p) else None


def sha16(s):
    return A.blob_sha(s.encode("utf-8"))[:16]


def test_first_run_uses_boot_and_keeps_unknown():
    root = make_local({"a.py": "v1\n", "b.md": "手元で書いた\n"})
    zp = make_zip(root, {"a.py": "v2\n", "b.md": "GitHub の版\n"})
    code, lines = A.run(root, zip_path=zp, boot={sha16("v1\n")}, now=T0)
    assert read(root, "a.py") == "v2\n"                 # 土台の指紋に入っていた＝手元で変えていない→更新
    assert read(root, "b.md") == "手元で書いた\n"        # 指紋に無い＝触らない
    assert any("b.md" in l and "初回" in l for l in lines)


def test_regression_no_crlf_file_not_in_boot_is_kept():
    # 2026-09-26 の読み直しで見つけた不具合の固定: 改行コードの違いが無いファイルを「手元で変えていない」と誤判定しない
    root = make_local({"c.md": "手元だけの版\n"})
    zp = make_zip(root, {"c.md": "GitHub の版\n"})
    A.run(root, zip_path=zp, boot=set(), now=T0)
    assert read(root, "c.md") == "手元だけの版\n"


def test_second_run_tells_local_only_from_both_changed():
    root = make_local({"c.md": "c1\n", "d.md": "d1\n"})
    A.run(root, zip_path=make_zip(root, {"c.md": "c1\n", "d.md": "d1\n"}), boot=set(), now=T0)
    with open(os.path.join(root, "c.md"), "w", encoding="utf-8") as f:
        f.write("c 手元で変更\n")
    with open(os.path.join(root, "d.md"), "w", encoding="utf-8") as f:
        f.write("d 手元で変更\n")
    zp = make_zip(root, {"c.md": "c1\n", "d.md": "d2 GitHub で変更\n"}, name="z2.zip")
    _code, lines = A.run(root, zip_path=zp, boot=set(), now=T0 + datetime.timedelta(hours=2))
    assert read(root, "c.md") == "c 手元で変更\n" and read(root, "d.md") == "d 手元で変更\n"
    text = "\n".join(lines)
    assert "c.md … 手元だけ変更" in text
    assert "d.md … 両方で変更" in text
    assert "d.md … 両方で変更＝統合が必要（手元にしか無い行 1）" in text
    assert "c.md … 手元だけ変更＝`python mw.py sync` で送ればよい" in text   # 手元だけ変更には行数を添えない
    assert read(root, "_auto_pull_conflicts/d.md") == "d2 GitHub で変更\n"   # 統合用に GitHub 側の版を置く
    assert read(root, "_auto_pull_conflicts/c.md") is None


def test_both_changed_but_local_already_on_github_says_zero_lines():
    # 2026-10-09 の実例: 手元で足して送った → クラウドがさらに足した → 次の取り込みで「両方で変更」。中身は GitHub に全部ある
    root = make_local({"d.md": "d1\n"})
    A.run(root, zip_path=make_zip(root, {"d.md": "d1\n"}), boot=set(), now=T0)
    with open(os.path.join(root, "d.md"), "wb") as f:
        f.write("d1\r\n手元で足して送った行\r\n".encode("utf-8"))   # CRLF でも数えない
    zp = make_zip(root, {"d.md": "d1\n手元で足して送った行\nクラウドが足した行\n"}, name="z2.zip")
    _code, lines = A.run(root, zip_path=zp, boot=set(), now=T0 + datetime.timedelta(hours=2))
    text = "\n".join(lines)
    assert "d.md … 両方で変更＝統合が必要（手元にしか無い行 0＝" in text
    assert read(root, "d.md") == "d1\r\n手元で足して送った行\r\n"   # 知らせるだけ＝手元は触らない


def _sent_then_cloud_edited(name="d.md"):
    """前回そろえた版 d1 → 手元で1行足して送った版（GitHub に一度あった）→ クラウドがさらに足した版、の状態を作る。"""
    root = make_local({name: "d1\n"})
    A.run(root, zip_path=make_zip(root, {name: "d1\n"}), boot=set(), now=T0)
    sent = "d1\n手元で足して送った行\n"
    latest = sent + "クラウドが足した行\n"
    with open(os.path.join(root, name), "w", encoding="utf-8", newline="") as f:
        f.write(sent)
    return root, make_zip(root, {name: latest}, name="z2.zip"), sent, latest


def _history(*bodies):
    def h(root, rel):
        for i, b in enumerate(bodies):
            yield f"c{i:06d}", "2026-10-05T10:00:00Z", A.blob_sha(b.encode("utf-8"))
    return h


def test_local_equal_to_past_github_version_is_caught_up():
    # 2026-10-09 の実例（MY_TRADING_RULES.md・SESSION_HANDOFF.md）: 手元は送った版のまま＝書き換えていない→最新にする
    root, zp, sent, latest = _sent_then_cloud_edited()
    _code, lines = A.run(root, zip_path=zp, boot=set(), now=T0 + datetime.timedelta(hours=2),
                         history=_history(latest, sent, "d1\n"))
    text = "\n".join(lines)
    assert read(root, "d.md") == latest
    assert "両方で変更" not in text and "まだ GitHub に送っていない" not in text
    assert "GitHub の過去の版のまま" in text and "d.md（10/05 19:00 の版 c000001）" in text
    bdir = [d for d in os.listdir(os.path.join(root, "_pull_backup")) if d.endswith("-auto")][-1]
    assert read(root, f"_pull_backup/{bdir}/d.md") == sent              # 置き換える前の手元の版を控える
    st = json.load(open(os.path.join(root, "_auto_pull_state.json"), encoding="utf-8"))
    assert st["files"]["d.md"] == A.blob_sha(latest.encode("utf-8"))  # 次の起動では「同じ」になる
    assert "過去の版から更新 d.md" in read(root, "_auto_pull_report.txt")


def test_crlf_copy_of_past_github_version_is_caught_up():
    root, zp, sent, latest = _sent_then_cloud_edited()
    with open(os.path.join(root, "d.md"), "wb") as f:
        f.write(sent.replace("\n", "\r\n").encode("utf-8"))
    A.run(root, zip_path=zp, boot=set(), now=T0 + datetime.timedelta(hours=2), history=_history(latest, sent))
    assert read(root, "d.md") == latest


def test_version_older_than_last_sync_is_still_a_local_change():
    # 前回そろえた版より古い版に戻したのは手元の変更（意図して戻した可能性）＝触らず「両方で変更」
    root, zp, sent, latest = _sent_then_cloud_edited()
    _code, lines = A.run(root, zip_path=zp, boot=set(), now=T0 + datetime.timedelta(hours=2),
                         history=_history(latest, "d1\n", sent))
    assert read(root, "d.md") == sent
    assert "d.md … 両方で変更" in "\n".join(lines)


def test_history_failure_falls_back_to_notice():
    root, zp, sent, _latest = _sent_then_cloud_edited()

    def down(root_, rel):
        raise OSError("HTTP Error 403: rate limit")
        yield
    _code, lines = A.run(root, zip_path=zp, boot=set(), now=T0 + datetime.timedelta(hours=2), history=down)
    text = "\n".join(lines)
    assert read(root, "d.md") == sent and "d.md … 両方で変更" in text
    assert "照合はできなかった: HTTP Error 403" in text


def test_history_not_consulted_for_local_only_change_and_dry_run_writes_nothing():
    root, zp, sent, latest = _sent_then_cloud_edited()
    calls = []

    def spy(root_, rel):
        calls.append(rel)
        return _history(latest, sent)(root_, rel)
    _code, lines = A.run(root, zip_path=zp, dry=True, boot=set(), now=T0 + datetime.timedelta(hours=2), history=spy)
    assert read(root, "d.md") == sent and calls == ["d.md"]
    assert "最新にする予定" in "\n".join(lines)
    # 手元だけ変更（GitHub は前回そろえた版のまま）では問い合わせない
    root2 = make_local({"c.md": "c1\n"})
    A.run(root2, zip_path=make_zip(root2, {"c.md": "c1\n"}), boot=set(), now=T0)
    with open(os.path.join(root2, "c.md"), "w", encoding="utf-8") as f:
        f.write("c 手元で変更\n")
    calls.clear()
    A.run(root2, zip_path=make_zip(root2, {"c.md": "c1\n"}, name="z2.zip"), boot=set(),
          now=T0 + datetime.timedelta(hours=2), history=spy)
    assert calls == []


def test_help_and_unknown_flags_do_not_run():
    # 2026-10-09: --help を付けたら受け付けずに取り込みが動いた
    orig = A.run

    def boom(*a, **k):
        raise AssertionError("取り込みを動かしてはいけない")
    A.run = boom
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            for argv in (["--help"], ["-h"], ["--hook", "--help"]):
                assert A.main(argv) == 0
            assert A.main(["--hlep"]) == 2
            assert A.main(["--hook", "--bogus"]) == 0      # 起動時の自動実行は止めない
    finally:
        A.run = orig
    assert "知らない指定: --hlep" in out.getvalue()
    assert A.usage().startswith("使い方") and "--dry-run" in A.usage()


def test_never_touch_local_only_files():
    root = make_local({"_mine.py": "手元専用\n", "research/r.md": "非公開研究\n", "DOCTRINE.md": "台帳\n"})
    zp = make_zip(root, {"sync_to_github.py": "# スタブで上書きしてはいけない\n", "mw.py": "# GitHub 版\n",
                         "_mine.py": "GitHub 版\n", "research/r.md": "GitHub 版\n", "research/new.md": "x\n",
                         "DOCTRINE.md": "GitHub 版\n", "_new.py": "x\n"})
    A.run(root, zip_path=zp, boot=set(), now=T0)
    assert read(root, "sync_to_github.py") == LOCAL_SYNC and read(root, "mw.py") == "# local mw\n"
    assert read(root, "_mine.py") == "手元専用\n" and read(root, "research/r.md") == "非公開研究\n"
    assert read(root, "DOCTRINE.md") == "台帳\n"
    assert read(root, "research/new.md") is None and read(root, "_new.py") is None


def test_generated_data_is_refreshed_with_backup():
    root = make_local({"signals-log.json": '{"local": 1}'})
    zp = make_zip(root, {"signals-log.json": '{"github": 2}', "index.html": "<html>新</html>"})
    _code, lines = A.run(root, zip_path=zp, boot=set(), now=T0)
    assert read(root, "signals-log.json") == '{"github": 2}'
    assert read(root, "index.html") == "<html>新</html>"          # 手元に無い生成物も作る
    bdirs = os.listdir(os.path.join(root, "_pull_backup"))
    assert len(bdirs) == 1 and bdirs[0].endswith("-auto")
    assert read(root, f"_pull_backup/{bdirs[0]}/signals-log.json") == '{"local": 1}'


def test_new_files_created_and_deleted_ones_moved_to_backup():
    root = make_local({"gone.md": "g\n", "kept.md": "k\n"})
    A.run(root, zip_path=make_zip(root, {"gone.md": "g\n", "kept.md": "k\n"}), boot=set(), now=T0)
    with open(os.path.join(root, "kept.md"), "w", encoding="utf-8") as f:
        f.write("k 手元で変更\n")
    zp = make_zip(root, {"new/x.md": "新しい\n"}, name="z2.zip")      # gone.md と kept.md は GitHub で削除
    _code, lines = A.run(root, zip_path=zp, boot=set(), now=T0 + datetime.timedelta(hours=2))
    assert read(root, "new/x.md") == "新しい\n"
    assert read(root, "gone.md") is None                          # 手元で変えていない→控えへ移す
    bdir = [d for d in os.listdir(os.path.join(root, "_pull_backup")) if d.endswith("-auto")][-1]
    assert read(root, f"_pull_backup/{bdir}/gone.md") == "g\n"
    assert read(root, "kept.md") == "k 手元で変更\n"               # 手元で変えた→触らない
    assert any("kept.md" in l for l in lines)


def test_dry_run_writes_nothing():
    root = make_local({"a.py": "v1\n"})
    before = sorted(os.listdir(root))
    A.run(root, zip_path=make_zip(root, {"a.py": "v2\n", "n.md": "x\n"}), dry=True, boot={sha16("v1\n")}, now=T0)
    after = sorted(os.listdir(root))
    assert read(root, "a.py") == "v1\n"
    assert before + ["z.zip"] == after or sorted(before + ["z.zip"]) == after   # ZIP 以外は増えない


def test_crlf_only_difference_is_updated():
    root = make_local({"b.md": "x\r\ny\r\n"})
    A.run(root, zip_path=make_zip(root, {"b.md": "x\ny\n"}), boot=set(), now=T0)
    assert read(root, "b.md") == "x\ny\n"


def test_cloud_ledger_is_written():
    root = make_local({})
    A.run(root, zip_path=make_zip(root, {}), boot=set(), now=T0)
    ledger = read(root, "_cloud_ledger.txt").splitlines()
    names = [l for l in ledger if l and not l.startswith("#")]
    assert len(names) == 100 and names[0] == "guide-cloud-000.html"


def test_hook_mode_skips_download_within_interval():
    root = make_local({})
    A.run(root, zip_path=make_zip(root, {}), boot=set(), now=T0)
    orig = A.download_zip

    def boom():
        raise AssertionError("60分以内は取得しないはず")
    A.download_zip = boom
    try:
        code, lines = A.run(root, hook=True, boot=set(), now=T0 + datetime.timedelta(minutes=30))
    finally:
        A.download_zip = orig
    assert code == 0 and lines[0].startswith("[auto_pull] GitHub の最新に取り込み済み（30分前")


def test_hook_mode_download_failure_does_not_block():
    root = make_local({})
    orig = A.download_zip

    def fail():
        raise OSError("timed out")
    A.download_zip = fail
    try:
        code, lines = A.run(root, hook=True, boot=set(), now=T0)
    finally:
        A.download_zip = orig
    assert code == 0 and "取得できなかった" in lines[0] and lines[0].startswith("[auto_pull] ")


def test_install_hook_merges_and_is_idempotent():
    root = make_local({".claude/settings.local.json": json.dumps({
        "permissions": {"allow": ["Bash(ls:*)"]},
        "hooks": {"SessionStart": [{"matcher": "startup", "hooks": [{"type": "command", "command": "echo hi"}]}]}})})
    A.install_hook(root)
    A.install_hook(root)
    d = json.load(open(os.path.join(root, ".claude", "settings.local.json"), encoding="utf-8"))
    assert d["permissions"] == {"allow": ["Bash(ls:*)"]}                 # 既存の設定は残す
    groups = d["hooks"]["SessionStart"]
    ours = [g for g in groups if "auto_pull.py" in g["hooks"][0]["command"]]
    assert len(groups) == 2 and len(ours) == 1                           # 2回入れても1つだけ
    assert ours[0]["matcher"] == "startup|resume" and ours[0]["hooks"][0]["command"].endswith(" --hook")
    A.install_hook(root, uninstall=True)
    d = json.load(open(os.path.join(root, ".claude", "settings.local.json"), encoding="utf-8"))
    assert [g["hooks"][0]["command"] for g in d["hooks"]["SessionStart"]] == ["echo hi"]


def test_is_local_folder_rejects_cloud_stub():
    root = make_local({"sync_to_github.py": STUB})
    assert not A.is_local_folder(root)
    root2 = make_local({"sync_to_github.py": LOCAL_SYNC + "#" * 20000 + "\n"})
    assert A.is_local_folder(root2)


if __name__ == "__main__":
    fails = 0
    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for name, fn in tests:
        try:
            fn()
            print(f"  ✅ {name}")
        except AssertionError as e:
            fails += 1
            print(f"  ❌ {name}: {e}")
    print(f"--- {len(tests) - fails}/{len(tests)} 合格 ---")
    sys.exit(1 if fails else 0)
