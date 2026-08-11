# -*- coding: utf-8 -*-
"""declutter_audit.py — 「整理係」: ルール/文書/コードの"重さ・腐り"を機械的に洗い出す。

設計思想（[[feedback_rules_as_code]]）: 整理を"人の記憶頼みの係"にすると、それ自体が忘れられる。
だから決定論で定期スキャンし、**重い/古い/重複/死んでる候補を提示するだけ**（自動削除はしない＝判断は人間）。
公開ゲートと同じ「surface → 人が承認」方式。読取専用・トークン0。

実行: python declutter_audit.py  （または mw.py declutter）
出力: コンソール ＋ DECLUTTER_REPORT.md（OneDriveで見える）。終了コード0固定（情報提供）。
"""
import os, re, glob, sys, datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
MEM = os.path.expanduser("~/.claude/projects/C--Users-info0/memory/MEMORY.md")

# 閾値（超えたら「軽くする候補」）。毎セッション読む文書を重く保たないため。
# 2026-07-02 トークン効率化＝閾値を実測ベースに厳格化（毎セッションの固定オーバーヘッド予算）。
# ⚠️ 2026-07-26: 進化ループ文書の閾値は **`_doctrine_check.py` が単一ソース**（ここは月次の二重
# チェック）。7/26 に一次側だけ 14→36 に直してここが取り残され、同じ警告が別経路から鳴り続けた。
# 二度と分岐しないよう import で引く。`_doctrine_check.py` は `_`プレフィックス＝ローカル専用で
# GitHub には無いため、クラウド実行時のフォールバックだけ数値を持つ（値は一次側と一致させること）。
#
# ⚠️ 2026-07-29: **DOCTRINE.md をこの表から削除**（オーナー承認）。値は一致していたが、一次側は
# 「error(28KB)まで残り N KB＝知見約M行ぶん」という**カウントダウン付きの行動可能な警告**を出すのに対し、
# ここは定型文の「古い完了セクションを退避してスリム化」を出していた＝**一次側が明確に否定した対処**
# （DOCTRINE は §2実証済み知見と §5稼働中コミットが本体で削減余地なし・SESSION_HANDOFF 7/28節）。
# 同じ閾値が二重に鳴る上に文言が劣化するので、DOCTRINE の監視は一次側に一本化する。
# ⚠️ 2026-08-11: **hypothesis_queue.md もこの表から削除**（オーナー承認・DOCTRINE を外したのと同じ理由）。
# 一次側（`_doctrine_check.check_queue_wip`）が **バイト数→アクティブQの本数** に変わったため、
# ここでバイト数を見ると「古い完了セクションを退避してスリム化」という**一次側が明確に否定した対処**を
# 出すことになる（キューの正しい対処は「仮説を1本閉じる」であって「文書を削る」ではない。
# 閉じたQは既にアーカイブ済みで、残っているのは全て進行中＝退避できるものが無い）。
# 監視は一次側に一本化する。⚠️ 閾値の単一ソースは `_doctrine_check.QUEUE_WARN_N/QUEUE_ERR_N`。
DOC_LIMITS_KB = {"SESSION_HANDOFF.md": 30, "CLAUDE.md": 32}
MEMORY_LIMIT_KB = 4  # auto-memory索引（毎セッション自動注入）。詳細は各memoryファイル側へ
MEMORY_FILE_LIMIT_KB = 20   # 個別memoryファイル。recall時に丸ごと文脈へ入る＝1件の重さが実コスト
SCRATCH_LIMIT = 30          # 使い捨てscriptがこれを超えたらアーカイブ候補
SCRATCH_RE = re.compile(r"^_(fix|push|probe|test|recon|inspect|check|verify|apply|reset|syntax|"
                        r"martingale|overshoot|panic|selection|strategy|trendfollow|volume|money|"
                        r"mfe|sr_|xtab|validate_)")

# セクション見出し（h2）。⚠️ 2026-07-29: 旧実装は `l.startswith("## ")` だったが、SESSION_HANDOFF は
# 全体が引用ブロック記法（`> ## …`）で書かれているため **14個中10個の見出しが不可視＝検出0個** で、
# 「✅完了セクションが8個以上」の判定が構造的に一度も発火しない死にコードだった。
# 先頭の `> ` を許容して修正。h3(`### `)は節内の小見出し＝セッション単位ではないので意図的に除外
# （`##` の直後に `\s` を要求するので `###` にはマッチしない）。
# ⚠️ 初版は `^>?\s*##\s` だったが `\s*` が行頭インデントまで飲み、`    ## x`（4スペース＝コード
# ブロック）を見出しと誤検出した（旧 startswith 版には無かった退行・Codex レビューで検出）。
# markdown 準拠で「見出し前の空白は3つまで」「引用は多重可」に修正。
DONE_SEC_RE = re.compile(r"^ {0,3}(?:(?:> ?)+ {0,3})?##\s")


def kb(p):
    return os.path.getsize(p) / 1024 if os.path.exists(p) else 0.0


def main():
    p = lambda s: os.path.join(HERE, s)
    findings = []   # (icon, text)

    # ① 毎回読む文書の肥大
    for f, lim in DOC_LIMITS_KB.items():
        size = kb(p(f))
        if size > lim:
            findings.append(("🟡", f"{f} が {size:.0f}KB（目安{lim}KB超）＝古い完了セクションを SESSION_ARCHIVE.md へ退避してスリム化"))
    if kb(MEM) > MEMORY_LIMIT_KB:
        findings.append(("🟡", f"MEMORY.md が {kb(MEM):.0f}KB（目安{MEMORY_LIMIT_KB}KB超）＝索引行を短く・詳細は各memoryファイルへ（毎セッション自動注入されるため）"))

    # ②（参考）ハンドオフ内の「✅完了」古セクション数（アーカイブ候補の目安）
    hp = p("SESSION_HANDOFF.md")
    if os.path.exists(hp):
        done = [l.strip() for l in open(hp, encoding="utf-8", errors="replace")
                if DONE_SEC_RE.match(l) and "✅" in l]
        if len(done) >= 8:
            findings.append(("🟡", f"SESSION_HANDOFF の ✅完了セクションが {len(done)}個＝直近を残し古いものはアーカイブ候補"))

    # ③ SYNC_FILES の死に登録（登録済みなのに実体が無い）
    sp = p("sync_to_github.py")
    if os.path.exists(sp):
        src = open(sp, encoding="utf-8", errors="replace").read()
        m = re.search(r"SYNC_FILES\s*=\s*\[(.*?)\n\]", src, re.S)
        # コメント（# 以降）は行ごとに捨ててから引用文字列を拾う。コメント内の "…" を登録と誤認した
        # 実例＝2026-08-06 の "Page build failed."（8/5 の .nojekyll 経緯コメント）→ 🔴誤検知
        entries = [e for ln in (m.group(1).splitlines() if m else [])
                   for e in re.findall(r'"([^"]+)"', ln.split("#", 1)[0])]
        missing = [e for e in entries if not os.path.exists(p(e))]
        if missing:
            findings.append(("🔴", f"SYNC_FILES 死に登録 {len(missing)}件（実体なし→該当行を削除）: " + ", ".join(missing[:8])))

    # ④ 使い捨てスクラッチ script の堆積
    allpy = [os.path.basename(x) for x in glob.glob(p("*.py"))]
    scratch = [x for x in allpy if SCRATCH_RE.match(x)]
    if len(scratch) > SCRATCH_LIMIT:
        findings.append(("🟡", f"使い捨てscriptが {len(scratch)}本（_fix/_push/_probe/_test等）＝`_scratch_archive/` へ移動でフォルダ整理（稼働系 _jp_* は対象外）"))

    # ⑤ 記憶の"重さ"（⚠️ 2026-07-29 改定＝「件数」→「1ファイルのKB」・オーナー承認）
    # 旧実装は MEMORY.md の索引行が30件以上で `/consolidate-memory` を促していたが、実測すると
    # 32件=304.8KB のうち **上位2ファイルだけで44%**（jp_doublebagger 72.9KB / signal_edge_research
    # 61.2KB）を占めており、件数は重さの代理指標として機能していなかった＝統合して件数を減らしても
    # recall時に注入される実バイト数は1バイトも減らない（＝警告が黙るだけで問題は残る）。
    # 個別memoryは recall で丸ごと文脈に入るので、**重いファイルを名指しする**ほうが行動可能。
    mem_dir = os.path.dirname(MEM)
    mem_files = [(os.path.basename(f), kb(f)) for f in glob.glob(os.path.join(mem_dir, "*.md"))
                 if os.path.isfile(f) and os.path.basename(f) != os.path.basename(MEM)]
    heavy = sorted([x for x in mem_files if x[1] > MEMORY_FILE_LIMIT_KB], key=lambda x: -x[1])
    if heavy:
        total = sum(k for _, k in mem_files)
        share = sum(k for _, k in heavy) / total * 100 if total else 0
        detail = "、".join(f"{n[:-3]}({k:.0f}KB)" for n, k in heavy[:5])
        findings.append(("🟡", f"重い記憶ファイル {len(heavy)}件（1件{MEMORY_FILE_LIMIT_KB}KB超）"
                               f"＝全{len(mem_files)}件{total:.0f}KB の{share:.0f}%を占有。"
                               f"要点を残して分割/要約: {detail}"))

    # ─── レポート ───
    today = datetime.date.today().isoformat()
    lines = [f"# 🧹 整理監査レポート（{today}）", "",
             "整理係（決定論・読取専用）が検出した「重さ・腐り」の候補です。**自動削除はしません。下記はあなたが承認して整理する候補**。", ""]
    if findings:
        lines.append(f"## 検出 {len(findings)}件")
        for icon, t in findings:
            lines.append(f"- {icon} {t}")
    else:
        lines.append("## ✅ 検出なし — 今は十分スリムです")
    lines += ["", "---",
              "凡例: 🔴=明確な腐り(除去推奨) / 🟡=肥大・堆積(整理候補)。",
              "整理は `mw declutter` で再実行。記憶は重いファイルを分割/要約（重複・陳腐化の整理は `/consolidate-memory`）。"
              "文書スリム化は古い✅完了セクションを SESSION_ARCHIVE.md へ。DOCTRINE/キューの予算は `mw evolve`（一次側）。"]
    report = "\n".join(lines)
    print(report)
    with open(p("DECLUTTER_REPORT.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(report + "\n")
    print(f"\n→ DECLUTTER_REPORT.md に保存（検出 {len(findings)}件）")


if __name__ == "__main__":
    main()
