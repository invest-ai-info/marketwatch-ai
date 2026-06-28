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
DOC_LIMITS_KB = {"SESSION_HANDOFF.md": 45, "CLAUDE.md": 35}
SCRATCH_LIMIT = 30          # 使い捨てscriptがこれを超えたらアーカイブ候補
SCRATCH_RE = re.compile(r"^_(fix|push|probe|test|recon|inspect|check|verify|apply|reset|syntax|"
                        r"martingale|overshoot|panic|selection|strategy|trendfollow|volume|money|"
                        r"mfe|sr_|xtab|validate_)")


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

    # ②（参考）ハンドオフ内の「✅完了」古セクション数（アーカイブ候補の目安）
    hp = p("SESSION_HANDOFF.md")
    if os.path.exists(hp):
        done = [l.strip() for l in open(hp, encoding="utf-8", errors="replace")
                if l.startswith("## ") and "✅" in l]
        if len(done) >= 8:
            findings.append(("🟡", f"SESSION_HANDOFF の ✅完了セクションが {len(done)}個＝直近を残し古いものはアーカイブ候補"))

    # ③ SYNC_FILES の死に登録（登録済みなのに実体が無い）
    sp = p("sync_to_github.py")
    if os.path.exists(sp):
        src = open(sp, encoding="utf-8", errors="replace").read()
        m = re.search(r"SYNC_FILES\s*=\s*\[(.*?)\n\]", src, re.S)
        entries = re.findall(r'"([^"]+)"', m.group(1)) if m else []
        missing = [e for e in entries if not os.path.exists(p(e))]
        if missing:
            findings.append(("🔴", f"SYNC_FILES 死に登録 {len(missing)}件（実体なし→該当行を削除）: " + ", ".join(missing[:8])))

    # ④ 使い捨てスクラッチ script の堆積
    allpy = [os.path.basename(x) for x in glob.glob(p("*.py"))]
    scratch = [x for x in allpy if SCRATCH_RE.match(x)]
    if len(scratch) > SCRATCH_LIMIT:
        findings.append(("🟡", f"使い捨てscriptが {len(scratch)}本（_fix/_push/_probe/_test等）＝`_scratch_archive/` へ移動でフォルダ整理（稼働系 _jp_* は対象外）"))

    # ⑤ 記憶の件数（多すぎなら consolidate-memory 推奨）
    if os.path.exists(MEM):
        n = sum(1 for l in open(MEM, encoding="utf-8", errors="replace") if l.strip().startswith("- ["))
        if n >= 30:
            findings.append(("🟡", f"記憶エントリ {n}件＝`/consolidate-memory` で重複統合・陳腐化整理を検討"))

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
              "整理は `mw declutter` で再実行。記憶は `/consolidate-memory`。文書スリム化は古い✅完了セクションを SESSION_ARCHIVE.md へ。"]
    report = "\n".join(lines)
    print(report)
    with open(p("DECLUTTER_REPORT.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(report + "\n")
    print(f"\n→ DECLUTTER_REPORT.md に保存（検出 {len(findings)}件）")


if __name__ == "__main__":
    main()
