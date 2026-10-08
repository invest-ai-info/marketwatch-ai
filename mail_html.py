# -*- coding: utf-8 -*-
"""メールの見やすさ：文字だけの本文を、色付きの HTML に直す。2026-10-09 オーナー「今朝メールが届きましたが、ちょっと見づらいので
色を使って見やすくしてください。例えば銘柄コードを青にして、銘柄名を水色にするとか、見やすくする工夫を考えてください」。

使うメール＝朝の指標メール（send_indicator_digest.py の digest）・「まもなく」メール（同 alert）・ロンドン前／NY前のメール（session_brief.py）。
**文字の本文はそのまま**（テストが確かめている中身を変えない）＝この部品は見た目だけを足す。送るメールは「文字＋HTML」の2本立て
（multipart/alternative）＝HTML を表示できないメールソフトでは今までどおりの文字が出る。HTML を作れなかったときも文字だけで送る。

色と形の決まり（上げ下げの色はサイトと同じ＝緑 #1a7f37・赤 #cf222e）:
  ・銘柄コード＝青の太字・銘柄名＝水色の太字（米国株のティッカーも同じ）。銘柄の一覧は1銘柄＝1枚の札（1行目＝番号・コード・名前・印／
    2行目＝売買代金や騰落率／3行目＝💣地雷）を1枚おきに薄い灰色
  ・騰落率と通貨の強弱の％＝プラスは緑・マイナスは赤（0 は灰）。通貨の並び（強い ＞ … ＞ 弱い）は札にして、強い＝緑・弱い＝赤・中立＝灰
  ・強い／弱い／中立・上向き／下向き・リスクオン／リスクオフ＝緑／赤／灰の太字。時刻（21:30 など）＝太字
  ・【見出し】＝欄ごとに色の帯（日本株＝赤・通貨＝緑・ファンダ＝紫・ニュース＝橙・決算＝茶・指標＝青・研究と休場＝灰）
  ・🚫 の行（買わない・発表が近い）＝赤い枠／⚠️ 🚩 の行＝黄色い枠／🏦 中銀＝紫の枠／📏 実測と💣の説明＝薄い枠
  ・★C・B候補の両方＝橙の札・〔貸借〕＝灰の札・〔C …〕〔B候補 …〕＝赤の札・[重要度 高／中／低]＝赤／黄／灰の札
  ・※ の注記・影響:・根拠：・最後の決まり文句＝小さめの灰色

⚠️ 標準ライブラリだけ（メールのワークフローは追加のライブラリを入れない）。決まった形に当てはまらない行は、ただの文字として出す
（本文の形が変わっても壊れない＝色が付かないだけ）。Gmail は HTML が約102KB を超えると途中で切る＝style は短く書く（テストが大きさを見張る）。
"""
import html
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

CODE, NAME = "#0b57d0", "#0288d1"
UP, DOWN, FLAT = "#1a7f37", "#cf222e", "#6e7781"
TEXT, MUTED = "#24292f", "#6e7781"
LEAN_COLOR = {"強い": UP, "弱い": DOWN, "中立": FLAT, "上向き": UP, "下向き": DOWN, "リスクオン": UP, "リスクオフ": DOWN}
PILL = {"強い": ("#dafbe1", UP), "弱い": ("#ffebe9", DOWN), "中立": ("#eaeef2", "#57606a")}
# 見出しに含まれる言葉 → 帯の色（上から順に最初に当てはまったもの。「この時間の注意（…研究から）」は注意・「研究から…（日本株…）」は研究）
SECTION = (("注意", "#b42318"), ("研究", "#57606a"), ("日本株", "#b42318"), ("通貨", "#00796b"), ("ファンダ", "#6f42c1"),
           ("ニュース", "#c2410c"), ("決算", "#8a5a00"), ("休場", "#57606a"), ("指標", "#0b57d0"), ("今日", "#0b57d0"),
           ("今後", "#0b57d0"))
SECTION_DEFAULT = "#1f2a44"
# 行の頭の印 → 枠の色（背景, 左の線）
BOX = (("🚫", "#fff1f0", "#cf222e"), ("⚠️", "#fff8e1", "#d4a72c"), ("🚩", "#fff8e1", "#d4a72c"), ("🏦", "#f3efff", "#6f42c1"),
       ("💣", "#fff5f5", "#e5a0a0"), ("📏", "#eef4ff", "#9ab8f0"))
SMALL_HEADS = ("※", "影響:", "根拠：", "…ほか", "（一覧の更新")
PCT_HEADS = ("値動き", "24時間：", "今日の", "約5日", "主なペア", "豪ドル：")
CCY_LINE = re.compile(r"^・(\S+?) (?=(?:強い|弱い|中立)（)")              # 「・米ドル 強い（高）：…」の通貨名＝太字
ALERT_EVENT = re.compile(r"^\d{1,2}:\d{2} JST\s")                       # 「まもなく」メールの発表の行＝大きく
SEP = re.compile(r"^━+$")
ROW = re.compile(r"^(\s*)(\d+)\.\s(?:(\d{3}[0-9A-Z])\s(.+?)(?=\s\s|$))?(.*)$")
EARN_JP = re.compile(r"^(\s*🇯🇵 .*?\s)(\d{3}[0-9A-Z])\s(.+?)((?:（予定）)?)$")
EARN_US = re.compile(r"^(\s*🇺🇸 .*?\s)([A-Z][A-Z.\-]{0,6})\s(.+?)((?:（予定）)?)$")
TAG = re.compile(r"\s?(★C・B候補の両方|〔[^〕]+〕)")
RANK_ITEM = re.compile(r"(\S+?) ([+\-−]\d+(?:\.\d+)?%)（(強い|弱い|中立)）")
TOK = re.compile(
    r"(?P<pct>(?<![\w.])[+\-−]\d+(?:\.\d+)?[%％])"
    r"|(?P<lean>(?<=[（\s：])(?:強い|弱い|中立)(?=[）（]))"
    r"|(?P<dir>上向き|下向き|リスクオフ|リスクオン)"
    r"|(?P<time>(?<![\d:/.])\d{1,2}:\d{2}(?![\d:]))"
    r"|(?P<tag>★C・B候補の両方|〔[^〕]+〕)"
    r"|(?P<imp>\[重要度 [高中低]\])")
IMP = {"高": ("#ffebe9", DOWN), "中": ("#fff8c5", "#9a6700"), "低": ("#eaeef2", "#57606a")}
FONT = "-apple-system,'Hiragino Sans','Hiragino Kaku Gothic ProN',Meiryo,'Noto Sans JP',sans-serif"


def _e(s):
    return html.escape(s, quote=False)


def _span(text, style):
    return f'<span style="{style}">{_e(text)}</span>'


def _b(text, color=None):
    """太字（色つき）。<b> にして style を短くする＝Gmail の約102KB の切れ目から遠ざける"""
    return f'<b style="color:{color}">{_e(text)}</b>' if color else f"<b>{_e(text)}</b>"


def _badge(text, bg, fg):
    return f'<span style="background:{bg};color:{fg};border-radius:4px;padding:0 5px;font-size:12px;white-space:nowrap">{_e(text)}</span>'


def _tag(t):
    """★C・B候補の両方＝橙／〔C …〕〔B候補 …〕＝赤／ほかの〔…〕（貸借など）＝灰"""
    if t.startswith("★"):
        return _badge(t, "#fff1e5", "#bc4c00")
    if t.startswith(("〔C", "〔B")):
        return _badge(t, "#ffebe9", DOWN)
    return _badge(t, "#eaeef2", "#57606a")


def _pct_color(t):
    v = float(re.sub(r"[^\d.]", "", t) or 0)
    return FLAT if v == 0 else (UP if t[0] == "+" else DOWN)


def inline(s, pct=False):
    """1行の中の言葉に色を付ける（騰落率は pct=True の行だけ＝決まりの文の「+5% 以上」などは塗らない）"""
    out, i = [], 0
    for m in TOK.finditer(s):
        out.append(_e(s[i:m.start()]))
        i = m.end()
        k, t = m.lastgroup, m.group()
        if k == "pct":
            out.append(_b(t, _pct_color(t)) if pct else _e(t))
        elif k in ("lean", "dir"):
            out.append(_b(t, LEAN_COLOR[t]))
        elif k == "time":
            out.append(_b(t))
        elif k == "tag":
            out.append(_tag(t))
        else:
            out.append(_badge(t, *IMP[t[-2]]))
    out.append(_e(s[i:]))
    return "".join(out)


def _code_name(code, name):
    return f"{_b(code, CODE)} {_b(name, NAME)}"


def stock_row(m, zebra):
    """銘柄の一覧の1行 → 1枚の札（番号・コード・名前・印／売買代金や騰落率／💣地雷）"""
    ind, num, code, name, rest = m.groups()
    rest, mine = (rest.split("💣", 1) + [""])[:2] if "💣" in rest else (rest, "")
    tags = TAG.findall(rest)
    detail = TAG.sub("", rest).strip()
    head = f'<span style="color:{MUTED}">{num}.</span> ' + (_code_name(code, name) if code else inline(detail, True))
    if tags:
        head += " " + " ".join(_tag(t) for t in tags)
    parts = [f"<div>{head}</div>"]
    if code and detail:
        parts.append(f'<div style="font-size:13px">{inline(detail, True)}</div>')
    if mine:
        parts.append(f'<div style="font-size:13px;color:{DOWN};font-weight:bold">💣{_e(mine)}</div>')
    bg = "background:#f6f8fa;" if zebra else ""
    return f'<div style="{bg}padding:4px 8px;margin-left:{_pad(ind)}px;border-radius:4px">{"".join(parts)}</div>'


def ranking(s):
    """「24時間：米ドル +0.40%（強い） ＞ … ＞ 円 -0.30%（弱い）」→ 見出し＋強い／弱いの札。形が違えば None"""
    if "：" not in s or " ＞ " not in s:
        return None
    label, tail = s.split("：", 1)
    items = [RANK_ITEM.fullmatch(x) for x in tail.split(" ＞ ")]
    if not all(items):
        return None
    pills = []
    for m in items:
        bg, fg = PILL[m.group(3)]
        pills.append(f'<span style="display:inline-block;background:{bg};color:{fg};border-radius:10px;padding:1px 8px;margin:2px 0;'
                     f'font-weight:bold;white-space:nowrap">{_e(m.group(1))} {_e(m.group(2))} '
                     f'<span style="font-size:11px">{m.group(3)}</span></span>')
    sep = f' <span style="color:{MUTED}">＞</span> '
    return f'<div style="font-weight:bold">{inline(label.strip())}：</div><div>{sep.join(pills)}</div>'


def _pad(ind):
    return max(0, len(ind) - 2) * 7


def section_color(title):
    return next((c for w, c in SECTION if w in title), SECTION_DEFAULT)


def line_html(s, section=""):
    """本文の1行 → HTML（見出し・区切り・一覧の行は to_html が扱う）"""
    body = s.strip()
    ind = s[:len(s) - len(s.lstrip())]
    pad = _pad(ind)
    pad_css = f"padding-left:{pad}px;" if pad else ""
    if "決算" in section:
        m = EARN_JP.match(s) or EARN_US.match(s)
        if m:
            pre, code, name, tent = m.groups()
            return f'<div style="{pad_css}">{inline(pre.strip())} {_code_name(code, name)}{_e(tent)}</div>'
    rk = ranking(body)
    if rk:
        return f'<div style="{pad_css}margin:2px 0">{rk}</div>'
    if body.startswith(SMALL_HEADS):
        return f'<div style="{pad_css}font-size:12px;color:{MUTED}">{inline(body)}</div>'
    pct = body.startswith(PCT_HEADS)
    if ALERT_EVENT.match(body):
        return f'<div style="{pad_css}font-size:17px;font-weight:bold;color:{DOWN}">{_e(body)}</div>'
    m = CCY_LINE.match(body)
    if m:
        return f'<div style="{pad_css}">・{_b(m.group(1))}{inline(body[m.end() - 1:])}</div>'   # 空白から渡す＝「強い」の前の目印
    if body.startswith("→"):
        return f'<div style="{pad_css}"><span style="color:#bc4c00;font-weight:bold">→</span>{inline(body[1:], pct)}</div>'
    for head, bg, line in BOX:
        if body.startswith(head):
            return (f'<div style="margin:4px 0 4px {pad}px;background:{bg};border-left:4px solid {line};padding:4px 8px;'
                    f'border-radius:4px">{inline(body, pct)}</div>')
    return f'<div style="{pad_css}">{inline(body, pct)}</div>'


def to_html(body, subject=""):
    """文字の本文 → HTML の文書（見出し＝色の帯・一番上の題＝紺の帯・最後の区切りのあと＝小さめの灰色）"""
    lines = body.split("\n")
    seps = [i for i, x in enumerate(lines) if SEP.match(x.strip())]
    title = seps[0] + 1 if len(seps) >= 2 and seps[1] == seps[0] + 2 else None
    foot = seps[-1] if seps and (title is None or seps[-1] > title + 1) else None
    out, section, zebra = [], "", False
    for i, s in enumerate(lines):
        body_s = s.strip()
        if i in seps and i != foot:
            continue
        if i == title:
            out.append(f'<div style="background:#1f2a44;color:#fff;font-size:17px;font-weight:bold;padding:10px 12px;'
                       f'border-radius:8px;margin-bottom:6px">{_e(body_s)}</div>')
            continue
        if i == foot:
            out.append('<hr style="border:0;border-top:1px solid #d0d7de;margin:14px 0 6px">')
            continue
        if foot is not None and i > foot:
            out.append(f'<div style="font-size:12px;color:{MUTED}">{inline(body_s)}</div>')
            continue
        if not body_s:
            out.append('<div style="height:8px"></div>')
            zebra = False
            continue
        if body_s.startswith("【"):
            section = body_s
            out.append(f'<div style="background:{section_color(body_s)};color:#fff;font-weight:bold;padding:6px 10px;'
                       f'border-radius:6px;margin:14px 0 6px">{_e(body_s)}</div>')
            zebra = False
            continue
        m = ROW.match(s)
        if m:
            out.append(stock_row(m, zebra))
            zebra = not zebra
            continue
        zebra = False
        out.append(line_html(s, section))
    return ('<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{_e(subject)}</title></head><body style="margin:0;padding:0;background:#ffffff">'
            f'<div style="max-width:720px;margin:0 auto;padding:12px;font-family:{FONT};font-size:14px;line-height:1.6;'
            f'color:{TEXT};background:#ffffff;word-break:break-word">'
            + "\n".join(out) + "</div></body></html>")


def message(subject, body, sender, recipient):
    """送るメール＝文字＋HTML の2本立て。HTML を作れなければ文字だけ（メールは止めない）"""
    try:
        page = to_html(body, subject)
        msg = MIMEMultipart("alternative")
        msg.attach(MIMEText(body, "plain", "utf-8"))
        msg.attach(MIMEText(page, "html", "utf-8"))
    except Exception as e:  # noqa: BLE001
        print(f"  ⚠️ HTML を作れなかった＝文字だけで送る（{type(e).__name__}: {e}）")
        msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"], msg["From"], msg["To"] = subject, sender, recipient
    return msg
