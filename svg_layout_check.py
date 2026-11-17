# -*- coding: utf-8 -*-
"""svg_layout_check.py — 図（SVG）の文字が、線・ローソク足・折れ線・図形に重なっていないかを見る。

🆕 2026-11-17 新設（オーナー「図解の文字が重なってて見づらい…確認する担当者がいたのにどうして」）。
   実例＝研究日誌 #152「4. 図で見ると」:
     ・「ここで買いのシグナル」が、その右の緑のローソク足2本（ひげと実体）の上に重なって読めない
     ・「RSIの30の線（売られすぎの目安）」を、あとから描いた RSI の折れ線が横切っている
   どちらも公開前の検査を全部通っていた。理由＝固定の検査（signal_lab_verify.py）が見ていたのは
     ① 文字どうしの重なり（text_overlap_check）
     ② 文字が「あとから描いた」不透明な四角・円に隠れる（text_occlusion_check・研究日誌のゲートでは未使用）
     ③ はみ出し（svg_bounds_check）
   だけで、「先に描いた図形の上に文字を載せた」「線・折れ線・パスが文字を横切る」は誰も見ていなかった。
   Opus のコンプラ・品質レーンは HTML の文字を読む係で、図を描いた画面は見ない（品質レーンは SVG を
   変えてはいけない決まり＝「SVG の重なりは機械が見る」前提）。→ 機械の穴がそのまま公開まで届いた。

見るもの（同じ <svg> の中・描く順番も考える）:
  A. 線（<line>・<polyline>・<polygon>・<path>・塗りなしの <rect>/<circle> の輪郭）が文字の箱を横切る
  B. 塗った図形（<rect>・<circle>・<ellipse>・塗った <polygon>/<path>）と文字の箱が一部だけ重なる
     （図形が文字をまるごと包み、しかも文字より先に描かれている＝「箱の上のラベル」は正しい使い方なので除く）
  除くもの: 図の背景（viewBox の 9割以上を覆う四角）／半透明（opacity・fill-opacity < 0.5）の帯や面／
            文字より先に描いた太さ1未満の線（目盛りの補助線）／
            回転した文字／縁取り（stroke＋paint-order）付きの文字＝線の上に載せる前提の文字／
            文字より先に描かれ、あとから描いた不透明な箱で隠された線（ラベルの下敷き）

文字の幅は signal_lab_verify._est_text_width（固定の検査と同じ見積もり＝和文1em・英数0.55em）を使う。
⚠️ 固定の検査（signal_lab_verify.py・check_guide_draft.py ほか）は編集しない決まり＝この検査は別ファイルで足し、
   研究日誌の公開（finalize_signal_lab.py）と `mw check`（check_site_consistency.py）から呼ぶ。

使い方:
  python svg_layout_check.py guide-signal-lab-152.html [ほかのファイル…]   # 重なりを一覧（あれば exit 1）
  python svg_layout_check.py --all                                         # 公開済みの全記事（多い順）
テスト: python tests/test_svg_layout_check.py
"""
import math
import re
import sys

from signal_lab_verify import _est_text_width

FIXABLE = "[直せる]"
TOL = 1.5          # 文字の箱を内側に縮める幅（px）＝線が箱の縁をかすめるだけなら数えない
AREA_TOL = 3.0     # 塗った図形との重なりは、縦横ともこれより大きいときだけ数える（固定の検査と同じ 3px）
BG_RATIO = 0.9     # viewBox の 9割以上を覆う四角＝背景
MIN_ALPHA = 0.5    # これより薄い塗り・線は数えない（半透明の帯）
THIN = 1.0         # 先に描いた線で太さがこれ未満＝目盛りの補助線（文字の下に透けても読める）
MIN_CROSS = 4.0    # 線が文字の箱の中を通る長さがこれ未満＝かすめるだけ・引き出し線の先が触れるだけ

_TAG = re.compile(r'<(/?)([a-zA-Z]+)\b((?:[^>"\']|"[^"]*"|\'[^\']*\')*?)(/?)>', re.S)
_NUM = r'-?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?'


def _attrs(s):
    return {k: v for k, v in re.findall(r'([\w:-]+)\s*=\s*"([^"]*)"', s)}


def _f(a, k, default=None):
    v = a.get(k)
    if v is None:
        return default
    m = re.match(r'\s*(' + _NUM + ')', v)
    return float(m.group(1)) if m else default


_CSS_KEYS = ("fill", "stroke", "stroke-width", "opacity", "fill-opacity", "stroke-opacity", "font-size",
             "text-anchor", "paint-order", "display", "visibility")


def class_styles(html):
    """ページの <style> から「.名前{…}」「text.名前{…}」の形の決まりだけ拾う＝{名前: {性質: 値}}。
    図の色・文字の寄せ方（text-anchor）を CSS の class で決めている記事がある（2026-11-17 実測＝
    text-anchor:middle を class で付けた文字を左寄せと見て、ありもしない重なりを数えた）。
    ダークモード用（body.dark .x 等の入れ子）は見ない＝明るい表示の見た目で判定する。"""
    out = {}
    for css in re.findall(r"<style\b[^>]*>(.*?)</style>", html, re.S | re.I):
        css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
        css = re.sub(r"@media[^{]*\{(?:[^{}]*\{[^{}]*\})*[^{}]*\}", "", css)    # 画面幅・ダークの分岐は見ない
        for sels, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
            decl = {k.strip().lower(): v.strip() for k, v in re.findall(r"([\w-]+)\s*:\s*([^;]+)", body)}
            decl = {k: v for k, v in decl.items() if k in _CSS_KEYS}
            if not decl:
                continue
            for sel in sels.split(","):
                m = re.fullmatch(r"\s*(?:[a-z]+)?\.([\w-]+)\s*", sel)
                if m:
                    out.setdefault(m.group(1), {}).update(decl)
    return out


def _style(a, css=None):
    """属性 < class の CSS < style="…" の順に上書きして、見た目の性質をそろえる。"""
    out = dict(a)
    for c in (a.get("class") or "").split():
        out.update((css or {}).get(c, {}))
    for k, v in re.findall(r'([\w-]+)\s*:\s*([^;]+)', a.get("style", "")):
        out[k.strip().lower()] = v.strip()
    return out


def _translate(t):
    """transform が translate だけなら (dx, dy)。それ以外（回転・拡大）を含むなら None。"""
    if not t:
        return (0.0, 0.0)
    parts = re.findall(r'(\w+)\s*\(([^)]*)\)', t)
    dx = dy = 0.0
    for name, args in parts:
        if name != "translate":
            return None
        nums = [float(x) for x in re.findall(_NUM, args)]
        dx += nums[0] if nums else 0.0
        dy += nums[1] if len(nums) > 1 else 0.0
    return (dx, dy)


def _alpha(a, which):
    """塗り（fill）／線（stroke）の濃さ。opacity と fill-opacity / stroke-opacity を掛ける。"""
    o = _f(a, "opacity", 1.0) * _f(a, f"{which}-opacity", 1.0)
    return o


def _paint(a, which, inherited):
    v = a.get(which, inherited.get(which))
    return (v or "").strip()


# ── 線分と箱の交差（Liang–Barsky）
def _seg_hits_box(p, q, box):
    """線分が箱の中を MIN_CROSS px 以上通るか（角をかすめる・引き出し線の先が文字の端に触れるだけは数えない）。"""
    return _seg_inside_len(p, q, box) >= MIN_CROSS


def _seg_inside_len(p, q, box):
    x0, y0, x1, y1 = box
    if x1 <= x0 or y1 <= y0:
        return 0.0
    dx, dy = q[0] - p[0], q[1] - p[1]
    t0, t1 = 0.0, 1.0
    for pk, qk in ((-dx, p[0] - x0), (dx, x1 - p[0]), (-dy, p[1] - y0), (dy, y1 - p[1])):
        if pk == 0:
            if qk < 0:
                return 0.0
            continue
        r = qk / pk
        if pk < 0:
            if r > t1:
                return 0.0
            t0 = max(t0, r)
        else:
            if r < t0:
                return 0.0
            t1 = min(t1, r)
    return max(0.0, t1 - t0) * math.hypot(dx, dy) if t0 <= t1 else 0.0


def _path_points(d):
    """<path d> を折れ線の点の列（部分パスごと）にする。曲線は8分割で近似。"""
    toks = re.findall(r'[MmLlHhVvCcSsQqTtAaZz]|' + _NUM, d)
    subs, cur, start = [], [], (0.0, 0.0)
    x = y = 0.0
    cmd, i = None, 0
    last_ctrl = None

    def nums(k):
        nonlocal i
        out = []
        while len(out) < k and i < len(toks) and not re.match(r'[A-Za-z]', toks[i]):
            out.append(float(toks[i]))
            i += 1
        return out if len(out) == k else None

    while i < len(toks):
        if re.match(r'[A-Za-z]', toks[i]):
            cmd = toks[i]
            i += 1
            if cmd in "Zz":
                if cur:
                    cur.append(start)
                    subs.append(cur)
                cur, (x, y) = [], start
                continue
        if cmd is None:
            break
        rel = cmd.islower()
        c = cmd.upper()
        if c in "ML":
            v = nums(2)
            if v is None:
                break
            nx, ny = (x + v[0], y + v[1]) if rel else (v[0], v[1])
            if c == "M":
                if cur:
                    subs.append(cur)
                cur, start = [(nx, ny)], (nx, ny)
                cmd = "l" if rel else "L"          # M の後の続きの数字は L
            else:
                cur.append((nx, ny))
            x, y = nx, ny
        elif c in "HV":
            v = nums(1)
            if v is None:
                break
            if c == "H":
                x = x + v[0] if rel else v[0]
            else:
                y = y + v[0] if rel else v[0]
            cur.append((x, y))
        elif c in "CSQT":
            k = {"C": 6, "S": 4, "Q": 4, "T": 2}[c]
            v = nums(k)
            if v is None:
                break
            pts = [(v[j] + (x if rel else 0), v[j + 1] + (y if rel else 0)) for j in range(0, k, 2)]
            if c == "S":
                c1 = (2 * x - last_ctrl[0], 2 * y - last_ctrl[1]) if last_ctrl else (x, y)
                pts = [c1] + pts
            elif c == "T":
                c1 = (2 * x - last_ctrl[0], 2 * y - last_ctrl[1]) if last_ctrl else (x, y)
                pts = [c1] + pts
            p0 = (x, y)
            for s in range(1, 9):
                t = s / 8
                if len(pts) == 3:      # 3次
                    (a1, b1), (a2, b2), (a3, b3) = pts
                    px = (1 - t) ** 3 * p0[0] + 3 * (1 - t) ** 2 * t * a1 + 3 * (1 - t) * t * t * a2 + t ** 3 * a3
                    py = (1 - t) ** 3 * p0[1] + 3 * (1 - t) ** 2 * t * b1 + 3 * (1 - t) * t * t * b2 + t ** 3 * b3
                else:                  # 2次
                    (a1, b1), (a2, b2) = pts
                    px = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * a1 + t * t * a2
                    py = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * b1 + t * t * b2
                cur.append((px, py))
            last_ctrl = pts[-2]
            x, y = pts[-1]
            continue
        elif c == "A":
            v = nums(7)
            if v is None:
                break
            nx, ny = (x + v[5], y + v[6]) if rel else (v[5], v[6])
            cur.append((nx, ny))
            x, y = nx, ny
        else:
            break
        last_ctrl = None
    if cur:
        subs.append(cur)
    return subs


def _items(body, W, H, css=None):
    """SVG の中身を描く順に並べる。戻り値＝[(順番, 種類, データ, 名前)]
    種類: "text"（箱・文字・縁取り有無）／"seg"（線分の列）／"area"（箱）。"""
    out = []
    stack = [{"dx": 0.0, "dy": 0.0, "ok": True, "alpha": 1.0}]
    order = 0
    skip_until = -1
    for m in _TAG.finditer(body):
        if m.start() < skip_until:
            continue                                     # <defs> などの中＝描かれない
        closing, tag, rawattrs, selfclose = m.group(1), m.group(2).lower(), m.group(3), m.group(4)
        if closing:
            if tag == "g" and len(stack) > 1:
                stack.pop()
            continue
        a = _style(_attrs(rawattrs), css)
        if a.get("display") == "none" or a.get("visibility") == "hidden":
            continue
        top = stack[-1]
        tr = _translate(a.get("transform", ""))
        if tag == "g":
            if selfclose:
                continue
            g = dict(top)
            for k in ("fill", "stroke", "stroke-width", "paint-order", "class", "font-size", "text-anchor"):
                if k in a:
                    g[k] = a[k]
            g["alpha"] = top["alpha"] * _f(a, "opacity", 1.0)
            if tr is None:
                g["ok"] = False
            else:
                g["dx"], g["dy"] = top["dx"] + tr[0], top["dy"] + tr[1]
            stack.append(g)
            continue
        if tag in ("defs", "clippath", "mask", "pattern", "marker", "symbol"):
            # 定義の中身は描かれない＝閉じタグまで飛ばす
            if not selfclose:
                end = body.lower().find(f"</{tag}>", m.end())
                skip_until = end if end > 0 else len(body)
            continue
        if not top["ok"] or tr is None:
            continue                                     # 回転・拡大の中は座標が読めない＝見ない
        dx, dy = top["dx"] + tr[0], top["dy"] + tr[1]
        order += 1
        alpha = top["alpha"] * _f(a, "opacity", 1.0)
        fill = _paint(a, "fill", top)
        stroke = _paint(a, "stroke", top)
        cls = a.get("class", top.get("class", "")) or ""
        sw = _f(a, "stroke-width", None)
        sw = sw if sw is not None else _f({"v": top.get("stroke-width", "1")}, "v", 1.0)
        fill_on = fill.lower() not in ("none", "transparent") and alpha * _f(a, "fill-opacity", 1.0) >= MIN_ALPHA
        stroke_on = (stroke and stroke.lower() not in ("none", "transparent")
                     and alpha * _f(a, "stroke-opacity", 1.0) >= MIN_ALPHA)
        if tag == "text":
            if "rotate" in a.get("transform", "") or "writing-mode" in a:
                continue
            end = body.find("</text>", m.end())
            raw = body[m.end():end] if end > 0 else ""
            text = re.sub(r"<[^>]+>", "", raw).strip()
            x, y = _f(a, "x"), _f(a, "y")
            if not text or x is None or y is None:
                continue
            fs = _f(a, "font-size", None) or _f({"v": top.get("font-size", "")}, "v", None) or 12.0
            anchor = a.get("text-anchor", top.get("text-anchor", "start"))
            w = _est_text_width(text, fs)
            x0 = x - w / 2 if anchor == "middle" else (x - w if anchor == "end" else x)
            box = (x0 + dx, y + dy - fs * 0.9, x0 + w + dx, y + dy + fs * 0.15)
            halo = bool(stroke_on and ("paint-order" in a or "paint-order" in top)) or \
                (stroke_on and _f(a, "stroke-width", 0) >= 2)
            out.append((order, "text", (box, text, halo), "text"))
            continue
        if tag == "line":
            if stroke_on or (not stroke and cls):
                p = (_f(a, "x1", 0) + dx, _f(a, "y1", 0) + dy)
                q = (_f(a, "x2", 0) + dx, _f(a, "y2", 0) + dy)
                out.append((order, "seg", ([(p, q)], sw), "線"))
            continue
        if tag in ("polyline", "polygon"):
            nums = [float(v) for v in re.findall(_NUM, a.get("points", ""))]
            pts = [(nums[j] + dx, nums[j + 1] + dy) for j in range(0, len(nums) - 1, 2)]
            if len(pts) < 2:
                continue
            if tag == "polygon":
                pts.append(pts[0])
                # 塗りは SVG の既定で黒＝fill の指定が無くても塗る（CSS の class で消す図は線だけ数える）
                if fill_on and not (not fill and cls):
                    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
                    out.append((order, "area", (min(xs), min(ys), max(xs), max(ys)), "多角形"))
            if tag == "polyline" or stroke_on:
                if tag == "polyline" and not stroke_on and not (not stroke and cls):
                    continue
                out.append((order, "seg", (list(zip(pts, pts[1:])), sw), "折れ線" if tag == "polyline" else "多角形の線"))
            continue
        if tag == "path":
            subs = _path_points(a.get("d", ""))
            segs = []
            for sp in subs:
                segs += [((p[0] + dx, p[1] + dy), (q[0] + dx, q[1] + dy)) for p, q in zip(sp, sp[1:])]
            if not segs:
                continue
            if stroke_on or (not stroke and cls):
                out.append((order, "seg", (segs, sw), "パスの線"))
            # 塗ったパスは小さい印（矢じり等）だけ面として数える（大きい面グラフは文字を載せる前提が多い）
            if fill and fill_on and fill.lower() != "none":
                xs = [p[0] for s in segs for p in s]
                ys = [p[1] for s in segs for p in s]
                bx = (min(xs), min(ys), max(xs), max(ys))
                if (bx[2] - bx[0]) * (bx[3] - bx[1]) < 0.05 * W * H:
                    out.append((order, "area", bx, "塗ったパス"))
            continue
        if tag in ("rect", "circle", "ellipse"):
            if tag == "rect":
                x, y, w, h = _f(a, "x", 0.0), _f(a, "y", 0.0), _f(a, "width"), _f(a, "height")
                if w is None or h is None:
                    continue
                bx = (x + dx, y + dy, x + w + dx, y + h + dy)
            elif tag == "circle":
                cx, cy, r = _f(a, "cx", 0.0), _f(a, "cy", 0.0), _f(a, "r")
                if r is None:
                    continue
                bx = (cx - r + dx, cy - r + dy, cx + r + dx, cy + r + dy)
            else:
                cx, cy, rx, ry = _f(a, "cx", 0.0), _f(a, "cy", 0.0), _f(a, "rx"), _f(a, "ry")
                if rx is None or ry is None:
                    continue
                bx = (cx - rx + dx, cy - ry + dy, cx + rx + dx, cy + ry + dy)
            if (bx[2] - bx[0]) * (bx[3] - bx[1]) >= BG_RATIO * W * H:
                continue                                 # 図の背景
            translucent = any(k in cls for k in ("s-zone", "s-band", "s-fire"))
            # fill の指定なし＝SVG の既定は黒で塗る（固定の検査 _svg_shape_boxes と同じ扱い）
            if fill_on and not translucent:
                name = {"rect": "四角", "circle": "円", "ellipse": "楕円"}[tag]
                out.append((order, "area", bx, f"{name}{'（' + cls + '）' if cls else ''}"))
            elif stroke_on and not translucent:
                x0, y0, x1, y1 = bx
                if tag == "rect":
                    segs = [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]
                else:
                    cx, cy, rx, ry = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2
                    ps = [(cx + rx * math.cos(2 * math.pi * k / 16), cy + ry * math.sin(2 * math.pi * k / 16))
                          for k in range(17)]
                    segs = list(zip(ps, ps[1:]))
                out.append((order, "seg", (segs, sw), "枠の線"))
            continue
    return out


def _inner(box, t):
    return (box[0] + t, box[1] + t, box[2] - t, box[3] - t)


def _contains(outer, inner):
    return outer[0] <= inner[0] + 0.5 and outer[1] <= inner[1] + 0.5 and \
        outer[2] >= inner[2] - 0.5 and outer[3] >= inner[3] - 0.5


def svg_warnings(svg_body, W, H, css=None):
    items = _items(svg_body, W, H, css)
    texts = [(o, d) for o, k, d, _n in items if k == "text"]
    areas = [(o, d, n) for o, k, d, n in items if k == "area"]
    warns = []
    for (to, (box, text, halo)) in texts:
        inner = _inner(box, TOL)
        # 文字の下敷き＝文字より先に描かれ、文字をまるごと包む不透明な箱（ラベルの背景・棒の中の文字）
        under = [ao for ao, ab, _n in areas if ao < to and _contains(ab, box)]
        mask_from = max(under) if under else 0
        hits = []
        for o, k, d, n in items:
            if o == to or k == "text":
                continue
            if o < mask_from:
                continue                                  # 下敷きの箱より前に描いた線・図形は隠れている
            if k == "seg":
                segs, sw = d
                if o < to and (halo or sw < THIN):
                    continue                              # 縁取り付きの文字／先に描いた細い目盛り線の上の文字は許す
                if any(_seg_hits_box(p, q, inner) for p, q in segs):
                    hits.append(f"{n}が横切る" if o > to else f"{n}の上に載っている")
            else:
                ab = d
                if o < to and _contains(ab, box):
                    continue                              # 箱の上のラベル（正しい使い方）
                ox = min(box[2], ab[2]) - max(box[0], ab[0])
                oy = min(box[3], ab[3]) - max(box[1], ab[1])
                if ox > AREA_TOL and oy > AREA_TOL:
                    hits.append(f"{n}に{'隠れる' if o > to else '重なる'}（{ox:.0f}x{oy:.0f}px）")
        if hits:
            uniq = list(dict.fromkeys(hits))
            warns.append(f"文字「{text[:18]}」が {'・'.join(uniq[:3])}"
                         f"{'ほか' if len(uniq) > 3 else ''}（x {box[0]:.0f}〜{box[2]:.0f}, y {box[1]:.0f}〜{box[3]:.0f}）")
    return warns


def layout_check(html):
    """HTML の中のすべての <svg viewBox="0 0 W H"> を見て、重なりの説明の一覧を返す（空＝問題なし）。"""
    out = []
    css = class_styles(html)
    for i, m in enumerate(re.finditer(r'<svg\b([^>]*)>(.*?)</svg>', html, re.S), 1):
        vb = re.search(r'viewBox="\s*(' + _NUM + r')[\s,]+(' + _NUM + r')[\s,]+(' + _NUM + r')[\s,]+(' + _NUM + r')\s*"',
                       m.group(1))
        if not vb or "<text" not in m.group(2):
            continue
        W, H = float(vb.group(3)), float(vb.group(4))
        for w in svg_warnings(m.group(2), W, H, css):
            out.append(f"{FIXABLE} 図{i}: {w}")
    return out


HOWTO = ("直し方＝文字を空いている場所へ動かす（線・ローソク足・棒と重ならない位置）／必要なら viewBox を広げて余白を作る。"
         "数字・図の中身（ローソク足・線の形）は変えない。直したら同じ検査をもう一度実行する")


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    if argv == ["--all"]:
        import glob
        import os
        root = os.path.dirname(os.path.abspath(__file__))
        rows = []
        for path in sorted(glob.glob(os.path.join(root, "guide-*.html"))):
            with open(path, encoding="utf-8-sig") as fh:
                n = len(layout_check(fh.read()))
            if n:
                rows.append((n, os.path.basename(path)))
        print(f"図の文字の重なり: {len(rows)}本・{sum(n for n, _ in rows)}件（多い順）")
        for n, name in sorted(rows, reverse=True):
            print(f"  {n:3d}件  {name}")
        return 1 if rows else 0
    bad = 0
    for path in argv:
        with open(path, encoding="utf-8-sig") as fh:
            html = fh.read()
        ws = layout_check(html)
        if ws:
            bad += 1
            print(f"❌ {path}: 図の文字の重なり {len(ws)}件")
            for w in ws:
                print(f"   - {w}")
        else:
            print(f"✅ {path}: 図の文字の重なりなし")
    if bad:
        print("→ " + HOWTO)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
