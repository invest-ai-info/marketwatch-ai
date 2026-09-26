# -*- coding: utf-8 -*-
"""auto_pull.py — 手元（ローカル）のフォルダを GitHub の最新にそろえる。2026-09-26 新設。

オーナー指示「研究はとても大事なことなので作ってください」。手元の Claude Code の起動時に自動で動く
（`python auto_pull.py --install-hook` で1回だけ設定する）。手元のフォルダ専用＝クラウドや Actions では動かない。

なぜ要るか:
  このリポジトリは GitHub 側（routine・Actions・クラウドの Claude）が毎日直接書き換える＝手元は放っておくと必ず遅れる。
  2026-09-26 に、手元が 9/1 から25日分（約580件）遅れていたこと、手元の作業（9/23〜24 の CLAUDE.md など。
  MY_TRADING_RULES.md は3か月）が送られないまま埋もれていたことが見つかった。遅れたまま送ると巻き戻し事故になる。

何をするか（API は使わない＝GitHub の ZIP を1回取るだけ。_reconcile.py は件数が多いと API が応答しなくなった）:
  ・手元で書き換えていないファイル → GitHub の最新にする（新しいファイルは作る・GitHub で消えたものは控えへ移す）
  ・手元で書き換えたファイル → 触らない。「手元だけ変更＝送ればよい」「両方で変更＝統合が必要」を見分けて知らせる
    （統合に使えるよう、GitHub 側の版を _auto_pull_conflicts\\ に置く）
  ・GitHub 側で作るデータ（SYNC 禁忌＝signals-log.json など）→ 研究に使うので常に最新にする。
    手元で書き換えていたら、置き換える前に _pull_backup\\ へ控えを残す（手元からは送れないファイルなので失うものは控えだけ）
  ・_cloud_ledger.txt（クラウドが公開した記事の台帳。check_site_consistency.py が読む）を最新にする
  ・絶対に触らない: research\\ ／ 先頭が _ のファイル ／ sync_to_github.py（GitHub 側はスタブ）／ mw.py ／
    .sync-cache.json ／ .claude\\settings.local.json ／ 非公開研究の台帳（DOCTRINE.md など）

「手元で書き換えたか」の判定（時刻では決めない＝CLAUDE.md「時刻の新しさは正しさではない」）:
  前回そろえたときの GitHub の版の指紋を _auto_pull_state.json に覚えておき、いまの手元の指紋と比べる。
  初回だけは下の BOOT（2026-09-26 に手元を一括でそろえた時点以降に GitHub に存在した版の指紋）で判定する。

使い方（プロジェクトのフォルダで）:
  python auto_pull.py                    取り込む（結果を表示・全件は _auto_pull_report.txt）
  python auto_pull.py --dry-run          下見だけ（何も書き換えない）
  python auto_pull.py --install-hook     手元の Claude Code の起動時に自動で動くよう設定（.claude\\settings.local.json）
  python auto_pull.py --uninstall-hook   その設定を外す
  （--hook は起動時の自動実行用＝短い要約だけを出す。前回の取り込みから60分以内なら取得を省く）
"""
import ast
import datetime
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import time
import urllib.request
import zipfile

ZIP_URL = "https://codeload.github.com/invest-ai-info/marketwatch-ai/zip/refs/heads/main"
HERE = os.path.dirname(os.path.abspath(__file__))
HOOK_MIN_INTERVAL_MIN = 60
KEEP_BACKUPS = 15
SHOW_MAX = 15
# 絶対に触らない（パス）
NEVER = {"sync_to_github.py", "mw.py", ".sync-cache.json", ".claude/settings.local.json"}
# 非公開研究の台帳（SYNC 禁忌に載っているが GitHub 側の生成物ではない＝「常に最新にする」の対象から外す）
LOCAL_ONLY_NAMES = {"DOCTRINE.md", "DOCTRINE_ARCHIVE.md", "hypothesis_queue.md", "hypothesis_queue_archive.md"}
# 2026-09-26 に手元を一括でそろえた時点以降に GitHub に存在した版の指紋（blob sha 先頭16桁）。初回の判定だけに使う。
BOOT = set("""
010d22e9fd0b5913 0111361cd000ce22 01a685336ca60eb2 02088b22900b8b7a 02654745ec9356cb
030f4d601ccbd08f 03edbab479c057c4 04bafbe1eaf9e046 0768aa96f924cf93 0a68ac283dbb3e0d
0b3608595d79063b 0c29bf5c0a4d844b 0d02dd3c0bcb3fde 0ecc5bb3b299de4a 0ffccee49ca92e8d
1037ac04b59e0ccd 11ebe355b48c638a 1370340e43c7d03a 137b012d65ea22b3 141ac991cb6ed6ca
146ddaa7d25adbe5 1569e36d96cb8492 18df6adcf938ae26 1a1f44fb5ede21b0 1c2d22414c636e37
1f832255debebaaa 289ce3a54772401e 2e636b7eb8df9b5c 2ebbdda5a78a2d48 30a2ca8d1910c60a
369180fcd179413b 3bebb4305a41a437 3e46cd7ef25053c2 3fbb8b02516046c6 48e77e41f3d0b592
4905387b3e59498a 4c1649274c8348c8 4c7ed4b72a1dd387 551b06dbcc9eecd2 57e8f70fdef168d6
5b923325e2ddbe6c 5d22981999b6bae7 5d4dd633a3d39497 5d9eb266c1995c30 5f9dd3cb0409b6a5
6390825d8f2d6bd3 67342ff7060e1898 69e6ef76ff9cdab0 6adabc13fe50f5ec 6b22eb2a6e9fbdcf
6dd562332c482f13 6f2511dafb2c4782 706e52870f038b59 7418632bbc8cfb77 750d682fedb0779a
751aa0b141c6e62a 757d64953371153a 7667832b6b8cb368 78963bd753e99407 79ad7e5936e3100c
7daa69adcab4e4d6 7eb8186809310d47 7f2300fe55c814b7 7f5c58eb2352d06d 802b2c18722e3d6d
80dc6757da35ac4a 8144fd4de7527820 8354629dfd08b604 847ee3bdd8614ebd 86818a05a44ad681
8897cb49f0c50c01 89f830f1abec9981 8fb53d626461b1b5 931a09112449114e 942bdf2e46ab76a1
95dfaf041960fc2c 97d5054a3ad9162d 990acf422f5c8153 9979fe883033121f 9a2482de51326ef8
9b7b7f315affa41c 9d83b7986554d80e 9de8e5b93cfbe2d0 9fd7dcbe60cc9375 a0d03b20017d89c1
a16876352b65529f a4087e77725620d0 a423b5ccdb31f7ab a74744e00756f3e7 a7be9df773590e6e
a8f141c283db8436 ad21fdab80b850ff ae203a1c48b66c36 ae64c88c879dac81 af0e04bc11f4b1d9
b2c3f0b1419ae24d b5c4f767db6c5836 b6382ddee372e56e b68086bb739eef37 bb2ded6361ec1927
bb5f627bcc27d0fb bc01033d096a7278 bd346c5740d8a9e1 c061135fc6500244 c13fcf5e45c89616
c22cdd3e2fdcbdcb c51ac65374300328 c53d1308403529af c559bea2f3bf0aca c5fc86c88f07c66c
c85dc43ec401d200 cc3fe05f4f2b387a cde285fc96bc37f6 cf6eb17c012dd96d d01a0a41908da8c4
d02f887b6155858e d26452134aa4d460 d5df4615b6e7ca11 d658baf4f5ce2b62 d84a9870ff7f9f8d
d85f8473c81db148 d8d6e13ce68a292a da382e6d552aa5fd dfbe72b6c23111d1 e03142fccfa18d81
e23de29acef7bbaa e312e29e0d3768ee e39c07844378917f e99029c6aa32166a ea1e7436b39bcfb5
ed91515fea760e9b ef4c872fc15f5b16 f0dca5fde42690c2 f11ad512facd444e f2bed5a9fd77385e
f4ef9862fde5b350 f66574d492842dde f6c633e446b31f1a fbfd705478f03a4a fc60452f22d9ceb1
""".split())


def blob_sha(b):
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()


def file_sha(p):
    try:
        with open(p, "rb") as f:
            return blob_sha(f.read())
    except OSError:
        return None


def lf_sha(p):
    try:
        with open(p, "rb") as f:
            b = f.read()
    except OSError:
        return None
    lf = b.replace(b"\r\n", b"\n")
    return blob_sha(lf) if lf != b else None


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc)


def jst(t):
    return t.astimezone(datetime.timezone(datetime.timedelta(hours=9))).strftime("%m/%d %H:%M")


def sync_files_of(src):
    m = re.search(r"SYNC_FILES\s*=\s*\[(.*?)\n\]", src or "", re.S)
    return re.findall(r'"([^"]+)"', m.group(1)) if m else []


def forbidden_of(src):
    for n in ast.parse(src).body:
        if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "SYNC_FORBIDDEN":
            return set(ast.literal_eval(n.value))
    raise RuntimeError("ZIP の check_site_consistency.py から SYNC_FORBIDDEN を読めない")


def is_local_folder(root):
    """手元のフォルダか（本物の sync_to_github.py と mw.py がある）。クラウド・Actions では False。"""
    if os.environ.get("GITHUB_ACTIONS") == "true":
        return False
    sp = os.path.join(root, "sync_to_github.py")
    if not (os.path.isfile(sp) and os.path.isfile(os.path.join(root, "mw.py"))):
        return False
    try:
        src = open(sp, encoding="utf-8", errors="replace").read()
    except OSError:
        return False
    return "sync stub for cloud" not in src and os.path.getsize(sp) >= 20000


def load_state(root):
    try:
        with open(os.path.join(root, "_auto_pull_state.json"), encoding="utf-8") as f:
            st = json.load(f)
        if isinstance(st.get("files"), dict):
            return st
    except (OSError, ValueError):
        pass
    return {"files": {}, "last_success": None, "commit": None, "notice": []}


def save_state(root, st):
    p = os.path.join(root, "_auto_pull_state.json")
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=1, sort_keys=True)
    os.replace(tmp, p)


def download_zip():
    path = os.path.join(tempfile.gettempdir(), "marketwatch-ai-auto-pull.zip")
    tmp = path + ".part"
    req = urllib.request.Request(ZIP_URL, headers={"User-Agent": "mw-auto-pull"})
    with urllib.request.urlopen(req, timeout=60) as r, open(tmp, "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
    zipfile.ZipFile(tmp).close()   # 壊れていないか
    os.replace(tmp, path)
    return path


def lpath(root, rel):
    return os.path.join(root, *rel.split("/"))


def write_bytes(root, rel, data):
    p = lpath(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".pulltmp"
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, p)


def backup(root, bdir, rel):
    src = lpath(root, rel)
    dst = os.path.join(bdir, *rel.split("/"))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)


def prune_backups(root):
    base = os.path.join(root, "_pull_backup")
    try:
        dirs = sorted(d for d in os.listdir(base) if d.endswith("-auto"))
    except OSError:
        return
    for d in dirs[:-KEEP_BACKUPS]:
        shutil.rmtree(os.path.join(base, d), ignore_errors=True)


def run(root, zip_path=None, dry=False, hook=False, boot=None, now=None):
    """戻り値: (終了コード, 表示する行のリスト)。hook=True は要約だけ・60分以内なら取得を省く。"""
    boot = BOOT if boot is None else boot
    now = now or now_utc()
    st = load_state(root)
    if hook and st.get("last_success") and not zip_path:
        age = (now - datetime.datetime.fromisoformat(st["last_success"])).total_seconds() / 60
        if 0 <= age < HOOK_MIN_INTERVAL_MIN:
            return 0, tagged(hook, [f"GitHub の最新に取り込み済み（{int(age)}分前・main {st.get('commit') or '?'}）"]
                            + st.get("notice", []))
    try:
        zp = zip_path or download_zip()
        z = zipfile.ZipFile(zp)
    except Exception as e:
        last = st.get("last_success")
        when = jst(datetime.datetime.fromisoformat(last)) if last else "まだ一度も取り込んでいない"
        return 0, tagged(hook, [f"⚠️ GitHub の最新を取得できなかった（{e}）。手元は前回（{when}）の状態のまま。",
                                "   送る（mw sync）前に、必ずもう一度 `python auto_pull.py` を実行すること。"])
    names = [n for n in z.namelist() if not n.endswith("/")]
    pre = names[0].split("/")[0] + "/"
    remote = {n[len(pre):]: n for n in names if n.startswith(pre)}
    commit = (z.comment or b"").decode("ascii", "replace")[:7] or "?"
    forbidden = forbidden_of(z.read(remote["check_site_consistency.py"]).decode("utf-8"))
    stub = sync_files_of(z.read(remote["sync_to_github.py"]).decode("utf-8", "replace")) \
        if "sync_to_github.py" in remote else []
    try:
        local_sync = set(sync_files_of(open(lpath(root, "sync_to_github.py"), encoding="utf-8").read()))
    except (OSError, UnicodeDecodeError):
        local_sync = set()

    def untouchable(rel):
        base = rel.rsplit("/", 1)[-1]
        return (rel in NEVER or base.startswith("_") or rel.startswith("research/")
                or base in LOCAL_ONLY_NAMES)

    files = dict(st["files"])
    bdir = os.path.join(root, "_pull_backup", now.strftime("%Y%m%d-%H%M%S") + "-auto")
    conflict_dir = os.path.join(root, "_auto_pull_conflicts")
    updated, created, gen_replaced, removed, fails = [], [], [], [], []
    unsent, other_diff, kept_deleted = [], [], []
    same = 0
    if not dry:
        shutil.rmtree(conflict_dir, ignore_errors=True)   # 前回の統合用の控えは、今回の判定で置き直す
    for rel in sorted(remote):
        if untouchable(rel):
            continue
        p = lpath(root, rel)
        rb = z.read(remote[rel])
        R = blob_sha(rb)
        L = file_sha(p)
        prev = files.get(rel)
        if L == R:
            files[rel] = R
            same += 1
            continue
        try:
            if L is None:
                if os.path.exists(p):   # 同名のフォルダなど
                    other_diff.append((rel, "手元に同名のフォルダ"))
                    continue
                if not dry:
                    write_bytes(root, rel, rb)
                files[rel] = R
                created.append(rel)
                continue
            lf = lf_sha(p)   # 改行コード（CRLF）だけの違いは「書き換えていない」とみなす
            untouched = (prev == L) or (prev is None and L[:16] in boot) or (lf is not None and lf in (R, prev))
            if untouched:
                if not dry:
                    write_bytes(root, rel, rb)
                files[rel] = R
                updated.append(rel)
            elif rel.rsplit("/", 1)[-1] in forbidden:
                if not dry:
                    backup(root, bdir, rel)
                    write_bytes(root, rel, rb)
                files[rel] = R
                gen_replaced.append(rel)
            else:
                if prev is None:
                    kind = "手元と GitHub で違う（初回のため、どちらが新しいか判定できない）"
                elif prev != R:
                    kind = "両方で変更＝統合が必要"
                else:
                    kind = "手元だけ変更＝`python mw.py sync` で送ればよい"
                if rel in local_sync:
                    if prev != R and not dry:
                        cp = os.path.join(conflict_dir, *rel.split("/"))
                        os.makedirs(os.path.dirname(cp), exist_ok=True)
                        with open(cp, "wb") as f:
                            f.write(rb)
                        kind += f"（GitHub 側の版: _auto_pull_conflicts/{rel}）"
                    unsent.append((rel, kind))
                else:
                    other_diff.append((rel, kind))
        except OSError as e:
            fails.append(f"{rel}（{e}）")
    # GitHub で消えたファイル（前回そろえた版のまま＝手元で変えていなければ、控えへ移す）
    for rel in sorted(set(files) - set(remote)):
        p = lpath(root, rel)
        L = file_sha(p)
        if L is None:
            files.pop(rel, None)
        elif L == files[rel]:
            if not dry:
                try:
                    dst = os.path.join(bdir, *rel.split("/"))
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.move(p, dst)
                except OSError as e:
                    fails.append(f"{rel}（{e}）")
                    continue
            files.pop(rel, None)
            removed.append(rel)
        else:
            kept_deleted.append(rel)
    # クラウドが公開した記事の台帳
    if not dry and len(stub) >= 100:
        with open(lpath(root, "_cloud_ledger.txt"), "w", encoding="utf-8") as f:
            f.write("# クラウドが公開した記事の台帳（GitHub 側 sync_to_github.py スタブの SYNC_FILES）\n"
                    f"# {jst(now)} JST auto_pull.py が書き出し（main {commit}・{len(stub)}本）\n")
            f.write("\n".join(stub) + "\n")

    notice = []
    if unsent:
        notice.append(f"⚠️ 手元で変更・まだ GitHub に送っていないファイル {len(unsent)} 件（SYNC_FILES）:")
        notice += [f"  - {rel} … {kind}" for rel, kind in unsent[:SHOW_MAX]]
        if len(unsent) > SHOW_MAX:
            notice.append(f"  …ほか {len(unsent) - SHOW_MAX} 件（_auto_pull_report.txt）")
    if kept_deleted:
        notice.append(f"⚠️ GitHub では削除済みだが手元で変更あり（触っていない）: " + ", ".join(kept_deleted[:5]))
    if fails:
        notice.append(f"❌ 書き込みに失敗 {len(fails)} 件（OneDrive の同期中など）→ もう一度 `python auto_pull.py`")
    head = (f"{'（下見）' if dry else ''}GitHub の最新（main {commit}）に手元をそろえ{'る予定' if dry else 'ました'}："
            f"更新 {len(updated)}・新規 {len(created)}・GitHub で削除 {len(removed)}・データ更新 {len(gen_replaced)}"
            f"（同じ {same}）")
    lines = [head] + notice
    if gen_replaced and not dry:
        lines.append(f"   GitHub 側で作るデータは、置き換える前の手元の版を {os.path.relpath(bdir, root)} に控えた: "
                     + ", ".join(gen_replaced[:5]) + (" …" if len(gen_replaced) > 5 else ""))
    if other_diff:
        lines.append(f"   ほか、SYNC_FILES 外で手元と違うもの {len(other_diff)} 件（送られないので放置で害なし・触っていない）")
    if not dry:
        st.update(files=files, last_success=now.isoformat(), commit=commit, notice=notice)
        save_state(root, st)
        prune_backups(root)
        rep = [f"# auto_pull の結果（{jst(now)} JST・main {commit}）", ""] + lines + [""]
        rep += [f"更新      {r}" for r in updated] + [f"新規      {r}" for r in created]
        rep += [f"削除      {r}" for r in removed] + [f"データ更新 {r}" for r in gen_replaced]
        rep += [f"未送信    {r} … {k}" for r, k in unsent] + [f"SYNC外の差 {r} … {k}" for r, k in other_diff]
        rep += [f"失敗      {x}" for x in fails]
        with open(lpath(root, "_auto_pull_report.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(rep) + "\n")
    return (1 if fails else 0), tagged(hook, lines)


def tagged(hook, lines):
    return ["[auto_pull] " + l for l in lines] if hook else lines


def install_hook(root, uninstall=False):
    """手元の Claude Code の起動時（startup / resume）に `auto_pull.py --hook` を動かす設定を
    .claude/settings.local.json（このフォルダ専用・GitHub には送らない）に冪等に書く。"""
    sp = os.path.join(root, ".claude", "settings.local.json")
    data = {}
    if os.path.isfile(sp):
        try:
            with open(sp, encoding="utf-8") as f:
                data = json.load(f)
        except ValueError as e:
            return 1, [f"❌ {sp} が JSON として読めない（{e}）→ 何もしない。中身を確認してください"]
        shutil.copy2(sp, sp + ".bak")
    hooks = data.setdefault("hooks", {})
    starts = [g for g in hooks.get("SessionStart", [])
              if not any("auto_pull.py" in (h.get("command") or "") for h in g.get("hooks", []))]
    if not uninstall:
        script = os.path.join(root, "auto_pull.py").replace("\\", "/")
        # Windows では起動時の処理を Git Bash か PowerShell が動かす。
        # ・Python はいつも使っている `python` で呼ぶ（Microsoft Store 版の実体を絶対パスで呼ぶと Git Bash から動かないことがある）
        # ・引用符で始まる行は PowerShell で文法エラーになるので、空白が無ければ囲まない（どちらの殻でも同じ形で動く）
        if " " in script:
            cmd = f'python "{script}" --hook'
            note = "   ⚠️ パスに空白があるため引用符で囲んだ"
        else:
            cmd = f"python {script} --hook"
            note = ""
        starts.append({"matcher": "startup|resume",
                       "hooks": [{"type": "command", "command": cmd, "timeout": 180}]})
    if starts:
        hooks["SessionStart"] = starts
    else:
        hooks.pop("SessionStart", None)
    if not hooks:
        data.pop("hooks", None)
    os.makedirs(os.path.dirname(sp), exist_ok=True)
    with open(sp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    if uninstall:
        return 0, [f"✅ 起動時の自動取り込みを外した（{sp}）"]
    return 0, [f"✅ 手元の Claude Code の起動時に自動で取り込む設定を書いた（{sp}）",
               f"   動かす命令: {cmd}",
               "   次に Claude Code を起動したときから動く。まず一度 `python auto_pull.py` を手で実行しておくと確実"] + ([note] if note else [])


def main(argv):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    hook = "--hook" in argv
    if not is_local_folder(HERE):
        if not hook:   # 起動時の自動実行では黙って終わる（クラウドのセッションを邪魔しない）
            print("❌ 手元のフォルダ専用（本物の sync_to_github.py と mw.py があるフォルダで実行する）")
        return 0 if hook else 1
    if "--install-hook" in argv or "--uninstall-hook" in argv:
        code, lines = install_hook(HERE, uninstall="--uninstall-hook" in argv)
    else:
        given = [a for a in argv if a.lower().endswith(".zip")]
        code, lines = run(HERE, zip_path=given[0] if given else None, dry="--dry-run" in argv, hook=hook)
        if not hook:
            lines.append("（全件は _auto_pull_report.txt）" if "--dry-run" not in argv else "（下見なので何も書き換えていない）")
    print("\n".join(lines))
    return 0 if hook else code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
