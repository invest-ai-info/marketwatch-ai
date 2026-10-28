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
    ("btg-lab.json", "BT 4時間足BTG改（FXism の教材）の機械で数えられる部分（過去のデータ・1回だけ数えた・手元の MT5）", ""),   # 🆕 2026-10-02 数字は R
    ("btg-judge.json", "BTJ 4時間足BTG改の合図に教材の判断（入る／見送る）を足したもの（過去のデータ・目隠しの判断・1回だけ）", ""),   # 🆕 2026-10-02 数字は R
    ("oikawa-lab.json", "OK 及川式の通貨の強弱（ドル円とユーロポンドで強い方に入る・豪ドルのシリーズ・5分足・ロンドン時間・次の足で手じまう・過去のデータ・1回だけ・手元の MT5）", ""),   # 記録の名前が OK-A／OK-B なので節の名前は付けない（OK-OK-A を防ぐ）   # 🆕 2026-10-10
    ("mr-lab.json", "MR 及川式の移動平均の逆張り（5分足が1時間足・4時間足の10SMAに初めて触れたら上位足の向きに入る・前回安値で利確・実体抜けで損切り・20分で手じまう・ロンドン時間・過去のデータ・1回だけ・手元の MT5）", ""),   # 記録の名前が MR-1／MR-4 なので節の名前は付けない   # 🆕 2026-10-13
    ("ms-lab.json", "MS 及川式のリスクリワードの例（5分足が15分足10SMA＝黄緑線に触れたら1時間足10SMAを損切りの線に1時間足の向きに入る・前回安値で利確・20分で手じまう・ロンドン時間・過去のデータ・1回だけ・手元の MT5）", ""),   # 記録の名前が MS-A／MS-B なので節の名前は付けない   # 🆕 2026-10-13
    ("kj-lab.json", "KJ 九条式（YouTube「極限トレーダー｜九条」・戻り高値を勢いよく上に抜けたあと、時間を待ってフィボナッチの押し目に指値で入る・15分足と1時間足・8ペア・過去のデータ・1回だけ・手元の MT5）", ""),   # 記録の名前が KJ-15／KJ-60 なので節の名前は付けない・数字は R   # 🆕 2026-10-20
    ("kjg-lab.json", "KJG 九条式を金で（Dukascopy の XAUUSD の1分足・戻り高値の上抜け→時間待ち→フィボの押し目に指値・15分足と1時間足・2021-10〜2026-09・費用は BigBoss の 0.24ドルを下限・過去のデータ・1回だけ）", ""),   # 記録の名前が KJG-15／KJG-60・数字は R   # 🆕 2026-10-20
    ("as-lab.json", "AS 浅見式（YouTube「FX初心者を最短でプロにする男」・移動平均の束が縮んだところでトレンドラインを実体で抜けた向きに入る・5分足・8ペア・過去のデータ・1回だけ・手元の MT5）", ""),   # 記録の名前が AS-A／AS-B・数字は R   # 🆕 2026-10-20
    ("rh-lab.json", "RH リオン式の高値付近からのショート（YouTube「FXVtuberリオンのトレードチャンネル byFXism」・1時間足の目立つ高値を少しだけ超えて戻されたら売る・安値は鏡で買う・利確1R・5分足・為替8ペア＋金・過去のデータ・1回だけ・手元の MT5 と Dukascopy）", ""),   # 記録の名前が RH-A／RH-B・数字は R   # 🆕 2026-10-20
    ("rv-lab.json", "RV リオン式の残りの入り方9つ（YouTube「FXVtuberリオンのトレードチャンネル byFXism」・1時間足ミドルの抜けと戻り・リバースタッチ・ヒゲハント・トレンドフォローフィニッシュ・安値切り上げ・75SMA・ソーサー・フラッグ・ダブルトップ・利確1R・5分足・為替8ペア＋金・過去のデータ・1回だけ）", ""),   # 記録の名前が RV1〜RV9（methods）・数字は R   # 🆕 2026-10-20
    ("calendar-forward.json", "R3F 月末月初の前向きの観察（米国・日本の早い窓・CFD の費用・36回ごとの見張り）", "R3F"),   # 🆕 2026-10-05
    ("fx-month-end-lab.json", "R4 月末の値決め前の為替ヘッジ（日足の近い形・論文のあと・1回だけ数えた）", ""),   # 🆕 2026-10-05
    ("r4-window-lab.json", "R4 腕C 月末の値決め前の為替ヘッジ（腕B と同じ問いを Dukascopy の1分足で確かめた・1回だけ数えた）", "R4"),   # 🆕 2026-10-05 夜（判定は腕B・PREREG「R4 の記録の訂正」）
    ("r4-armb.json", "R4 腕B 月末のロンドン 08:00→16:00 の為替ヘッジ（手元の MT5 の1時間足・月の真ん中の日と比べた・1回だけ数えた）", "R4"),   # 🆕 2026-10-05
    ("intl-tom-lab.json", "R6 ほかの国の株価指数の月末月初（論文のあと・1回だけ数えた）", ""),   # 🆕 2026-10-05 深夜 R3F を育てる確かめ
    ("fx-confirm-lab.json", "XC X の候補を昔の期間で確かめる（ECB の値決め前のユーロドル・大きな月曜の窓・FOMC の日・Dukascopy の1時間足・2004〜2011年・1回だけ数えた）", "XC"),   # 🆕 2026-10-08
    ("fx-clock-lab.json", "X 為替の時計の癖（値決めの前後・月曜の窓・FOMC の日・Dukascopy の1時間足・2012〜2026-09・1回だけ数えた）", "X"),   # 🆕 2026-10-07 FX 短期の加速
    ("index-open-lab.json", "R7 株価指数の朝の窓・夜の上げ（1321.T・SPY の日足・2009〜2026-09・1回だけ数えた）", "R7"),   # 🆕 2026-10-06
    ("night-history-lab.json", "R8 日経平均の夜の上げを昔の時代（1992〜2010年）で確かめる（^N225 の日足・1回だけ数えた）", "R8"),   # 🆕 2026-10-08
    ("sq-week-lab.json", "R9 SQ週（オプションの満期の週）の日経平均・S&P500（日足の終値・1992〜2026-09・1回だけ数えた）", "R9"),   # 🆕 2026-10-08
    ("lunch-gap-lab.json", "R10 日本の昼休みの窓のあと後場は続くか戻るか（1321.T の1時間足・約2年・1回だけ数えた）", "R10"),   # 🆕 2026-10-08
    ("tom-basket-lab.json", "J41 日本の早い月末月初を個別株の籠で・引け成行どうし（2006〜2026-09・1回だけ数えた）", "J41"),   # 🆕 2026-10-08
    ("momentum-lab.json", "J42 日本株の数か月単位のモメンタム（12−1・残差・52週高値・月1回の入れ替え・1995〜2026-08・1回だけ数えた）", "J42"),   # 🆕 2026-10-08
    ("highs-shape-lab.json", "J48 上場来高値の「形」（じわじわ・25日線からの離れ・その日の上げ・引けの強さ・久しぶりの更新・上場1年未満で分け、次の日の寄りから60営業日・全体と比べた差・2006〜2026-07・1回だけ数えた）", "J48"),   # 🆕 2026-10-27 ✕ の問いだけ載る
    ("highs-entry-lab.json", "J49 上場来高値の罠の見分け・押し目の深さ・手じまい（急騰の重なり・翌日の崩れ・5本以内の下げ／−5・−10・−20％と25日線の指値／損切り・戻り売り・利確・60本・全体と比べた差・2006〜2026-07・1回だけ数えた）", "J49"),   # 🆕 2026-10-28 ✕ の問いだけ載る
    ("momentum-forward.json", "J42F 過去12か月で一番上げた10銘柄は翌月弱いか（前向き・決める月 2026-10〜2028-09 の24か月で判定）", "J42F"),   # 🆕 2026-10-08
    ("tsmom-lab.json", "R11 株価指数・商品（MT4）と為替（MT5）の時系列モメンタム（12か月の向き・量をそろえる・月1・1回だけ数えた）", "R11"),   # 🆕 2026-10-08 夜
    ("fx-value-lab.json", "F2 為替の割安と経済の勢い（8通貨・実質実効為替レートの5年の変化／物価・失業率の12か月の変化・月1・費用とスワップ・2004〜2026-08・1回だけ数えた）", "F2"),   # 🆕 2026-10-10 ファンダの柱の1本目
    ("sq-morning-lab.json", "J43 SQの日（第2金曜日）の朝：寄りの窓の戻しと「寄りで買わない」目印をほかの金曜日と比べる（日足の寄り→大引け・2006〜2026-10・1回だけ数えた）", "J43"),   # 🆕 2026-10-09
    ("gap-forward.json", "J13F 窓の戻し・前向き（全上場の毎朝・寄り→9:30）", "J13F"),   # 🆕 2026-10-06 夜 腕B。取引は持たず progress に回数
    ("bounce-cost-lab.json", "J19 安く寄った株の戻り（銘柄ごとの売り買いの差を引く・2006〜2026年・1回だけ数えた）", ""),   # 🆕 2026-10-07
    ("open5-skip-lab.json", "J27 最初の5分で下げた株を足を1本空けて買う（9:10→9:30・銘柄ごとの売り買いの差を引く・約40朝・1回だけ数えた）", ""),   # 🆕 2026-10-07 夜
    ("market-dip-forward.json", "J25F 相場全体が安く寄った朝の深い下げを指値で拾う・前向き（全上場の毎朝・寄り→9:30・費用後）", "J25F"),   # 🆕 2026-10-07
    ("auction-forward.json", "J31F 空売りの前向き（目印 B・C・10億円以上・寄り成行で売り引け成行で買い戻す・損切りなし／+10%・費用後）", "J31F"),   # 🆕 2026-10-08
    ("lunch-gap-forward.json", "R10F 昼休みの窓と同じ向きに後場を持つ前向き（1321.T の1時間足・費用 0.01%）", "R10F"),   # 🆕 2026-10-08
    # 🆕 2026-10-18 F1 日本株の割安×質（手元の J-Quants で数えて送る・群の件数と差だけ＝銘柄は入れない）。
    #    昔の時代の1回だけの結果（G ✅・Z と A ✕）と、G の前向き（判定日24本で1回だけ）
    ("f1-early-lab.json", "F1 日本株の割安×質を昔の時代（2016-10〜2021-06）で確かめる（グレアムの守り・ズールー・資産成長・手元の J-Quants・1回だけ数えた）", "F1"),
    ("f1g-forward.json", "F1GF グレアムの守りの前向き（点4以上と1以下の「12か月後に−30%以下」の割合の差・毎月最初の営業日・判定日24本で判定・手元で数えて送る）", "F1GF"),
    # 🆕 2026-10-27 J47 上場来高値のその後×業績の裏づけ（手元で J-Quants の10年分を1回・要約だけ送る＝銘柄は入れない）。
    #    届く前は何も載らない（ファイルが無ければ飛ばす）。✕ の問いは stop・✅ は plus（使う前に前向きで確かめる）
    ("highs-fund-lab.json", "J47 上場来高値のその後は業績の裏づけで分かれるか（上方修正・増益率・赤字・決算からの日数・60営業日・TOPIX と比べた差・2017〜2026-07・手元の J-Quants・1回だけ数えた）", "J47"),
    ("highs-value-lab.json", "J50 上場来高値のあとの −10％ の押し目は業績に対して割安なら戻るか（予想PER・PEG・押しのあいだの業績修正・業種の中の位置・60営業日・TOPIX と比べた差・2017〜2026-07・手元の J-Quants・1回だけ数えた）", "J50"),   # 🆕 2026-10-28
    ("j9-yutai-lab.json", "J9 株主優待の権利付き最終日に向けた上昇と、空売りできない株（論文の後の5年・有報から集めた優待・手元の J-Quants・1回だけ数えた）", "J9"),   # 🆕 2026-10-28 手元で数えて送る・件数と差だけ
    ("stop-entry-lab.json", "SE 損切りの線まで待って同じ向きに指値で入る（日足・4時間足・監視18銘柄・入口60・費用後・過去のデータ・1回だけ）", "SE"),   # 🆕 2026-10-24 テクニカルの区切りの例外・数字は R
    ("se-m5-lab.json", "SE 損切りの線まで待って同じ向きに指値で入る（5分足・8ペア・入口32・実スプレッド・過去のデータ・1回だけ・手元の MT5）", "SE"),   # 🆕 2026-10-24 手元で数えて送る・数字は R
]
# 🆕 2026-10-06 目印（見分け方）の前向き（kind: marker）。「期待値がプラスか」ではなく「目印あり−なしの差が0より下か」を
# 判定するので、上の SOURCES とは別の節に載せる（確認＝confirm／ストップ＝stop）
MARKER_SOURCES = [
    ("highs-trap-forward.json", "J10F 高値更新の翌朝の罠の目印・前向き", "J10F"),
    ("gap-forward.json", "J13F 窓の戻し・前向き（全上場の毎朝・寄り→9:30）", "J13F"),   # 🆕 2026-10-06 夜 腕A（marker_titles）
    ("prevgap-forward.json", "J17F 「寄りで買わない」目印の前向き（その銘柄だけの窓・前の日 +5％以上との重なり・寄り→9:30）", "J17F"),   # 🆕 2026-10-07
    ("tvsurge-forward.json", "J26F 目印C「前の日の売買代金の急増」の前向き（20営業日平均の5倍以上・寄り→9:30）", "J26F"),   # 🆕 2026-10-07 夜
]
# 🆕 2026-10-07 見込みなしで途中で止めた前向きの腕（オーナー「検証中リストは増えすぎても見づらくなるので、見込みがないと
# 思ったら検証済みリストに移動させてください」・決まり＝PILLAR_PREREG.md「見込みなしで止める決まり」③）。前向きの記録
# （Actions が書く）は書き換えない＝ここに1行足すと、検証中リスト・研究の地図から外れ、この一覧の「⏹ ストップ」に載る。
# 根拠は結果の出たほかの検証だけ（その前向き自身の途中の数字は見ない）。n＝止めた日の回数。あとで決めた回数に届いて
# 本当の判定が出たら、そちらを優先して載せる。reason は公開ページにも出す＝記号や検証の番号を入れない（番号は evidence へ）
RETIRED = [
    # 2026-10-07 夜：J13F 腕B（窓 −3％以下を寄りで買う）は J28 で費用の見積もりが重すぎる疑いが出たので取り消した（PREREG「見込みなしで止める決まり」の追記）
    {"src": "yori-forward.json", "id": "F2", "on": "2026-10-07", "n": 4, "cat": "jp",
     "name": "前の日に出来高が急に増えた株のうち、前の日の終わりより3パーセント以上高く始まったものを寄りで買い、9時15分に売る形", "evidence": "J13・J14・J15・J18・J22",
     "reason": "高く始まった株は寄りのあとにほかの株より値下がりしやすい（戻されやすい）と、ほかの検証で昔の期間も最近も出ている。判定まで4〜5年かかる"},
    {"src": "yori-forward.json", "id": "F4", "on": "2026-10-07", "n": 3, "cat": "jp",
     "name": "前の日に出来高が急に増えた株のうち、前の日に5パーセント以上上がり、9時15分に寄りから2パーセント以上上がっているものを買い、大引けで売る形", "evidence": "J16・J20",
     "reason": "前の日に5パーセント以上上がった株は寄りのあとにほかの株より値下がりしやすいと、ほかの検証で昔の期間も最近も出ている。判定まで約6年かかる"},
    {"src": "yori-forward.json", "id": "F6", "on": "2026-10-07", "n": 1, "cat": "jp",
     "name": "前の日に出来高が急に増えた株のうち、前の日の終わりより3パーセント以上高く始まったものを寄りで買い、9時30分に売る形", "evidence": "J13・J14・J15・J18・J22",
     "reason": "高く始まった株は寄りのあとにほかの株より値下がりしやすい（戻されやすい）と、ほかの検証で昔の期間も最近も出ている。判定まで4〜5年かかる"},
]
# 🆕 2026-10-18 過去のデータで1回だけ数えて「◯ 低い費用ならプラス」などの途中の判定だった腕を、そのあとの確かめ
# （実際の費用の測り直しなど）を受けてオーナーが区切ったもの。記録（Actions が書く）は書き換えない＝ここに1行足すと
# 検証済みリストの「⏹ ストップ」に載る。数字は記録の results[腕]["net"]（ベーシスポイント）から取る＝手で写さない。
# reason は公開ページにも出す＝記号や検証の番号を入れない（番号は evidence へ）
CLOSED = [
    {"src": "fx-confirm-lab.json", "id": "XC1", "on": "2026-10-18", "evidence": "X3・XC1・手元の費用の測り直し（10/10）",
     "reason": "過去のデータで2回（2012〜2026年と、使っていなかった2004〜2011年）同じ向きに出たが、使っている業者の口座で"
               "実際の往復の費用を測ると中央値1.55pips（手数料込み）で、費用を引く前の約+1.9ベーシスポイントがほとんど残らないため、"
               "前向きはせずに区切った（2026-10-18 オーナーの判断）"},
]
TRACKER = "signal-lab-tracker.json"     # 🆕 2026-10-07 シグナルの条件（仮説）の採点で終わったもの（⛔反証・⏹見込みなし）


# 🆕 2026-10-08 夜 判定の数字はそのままで、記録に書かれた理由の文だけを正確なものに直す表（記録のファイル名, 腕）→ 理由。
#    R11 の道具は「偽薬に勝ったか」で言い分けずに「偽薬やいつも買いと区別できない」と書いた＝Q1 は偽薬には勝っている（p 0.0035）ので直す
REASON_FIX = {
    ("tsmom-lab.json", "Q1"): "過去のデータで1回だけ数えて、でたらめな向きには勝つが、いつも買い（同じ量・同じ費用）より成績が低く、"
                              "費用後の平均の幅も0をまたぐ（1990-01〜2026-08）",
    ("tsmom-lab.json", "Q2"): "過去のデータで1回だけ数えて、スワップ込みの費用後の平均がマイナス寄りで、でたらめな向きと区別できない（2005-04〜2026-08）",
}


def retired(src, cid):
    """見込みなしで止めた腕なら RETIRED の1行、そうでなければ None（src は記録の JSON のファイル名）"""
    base = src.replace("\\", "/").rsplit("/", 1)[-1]
    return next((r for r in RETIRED if r["src"] == base and r["id"] == cid), None)


def closed(src, cid):
    """オーナーが区切った過去のデータの腕なら CLOSED の1行、そうでなければ None"""
    base = src.replace("\\", "/").rsplit("/", 1)[-1]
    return next((c for c in CLOSED if c["src"] == base and c["id"] == cid), None)


def closed_verdict(data, c):
    """記録の results[腕]["net"]（ベーシスポイント）から「⏹ ストップ」の判定を組み立てる（verdicts と同じ単位＝割合）"""
    res = ((data.get("results") or {}).get(c["id"]) or {})
    net = res.get("net") or {}
    bp = (lambda x: None if x is None else x / 10000)
    return {"status": "stop", "decided_on": c["on"], "n": res.get("n"), "mean": bp(net.get("mean")),
            "lo": bp(net.get("lo")), "hi": bp(net.get("hi")), "reason": c["reason"], "closed": True}


def retired_verdict(r):
    return {"status": "stop", "decided_on": r["on"], "n": r["n"], "mean": None, "lo": None, "hi": None,
            "reason": f"見込みなしで途中で止めた：{r['reason']}（根拠：{r['evidence']}・途中の数字は見ていない）", "retired": True}


# 🆕 2026-09-30 総当たりのふるい分け（kind: screen・判定は screen_judge.py）。組み合わせが数千あるので、1行ずつではなく
# 理由ごとの件数・昇格のあとで消えたもの・直す出発点の候補だけを載せる。関門を越えたものは昇格リスト（promotion_list.py）へ
SCREEN_SOURCES = [
    ("m6-screen.json", "M6 ポンド円・ロンドン時間の総当たり（手元の MT5 の5分足・過去に1回ずつ）"),
    ("m7-screen.json", "M7 4時間足の総当たり（為替8ペア・手元の MT5 の実スプレッド・1回ずつ）"),   # 🆕 2026-10-01
]


def _label(r):
    return f"{r['sec']}-{r['id']}" if r["sec"] else r["id"]


def _progress(r):
    """数えている途中の書き方。goal が回数なら「n/goal回」、期間の区切り（文字）なら「n回・期間」"""
    g = r.get("goal")
    return f"{r['n']}/{g}回" if isinstance(g, int) else f"{r['n']}回・{g}"


def _pct(x):
    return "—" if x is None else f"{x * 100:+.2f}％"


def _count(data, cid, flagged=False):
    """数えた回数。取引を1行ずつ持たない記録（J13F）は progress に回数を書く"""
    if cid in (data.get("progress") or {}):
        return data["progress"][cid]
    return sum(1 for t in data.get("trades", []) if t.get("c") == cid and (t.get("f") or not flagged))


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
            if not v and retired(path, cid):
                v = retired_verdict(retired(path, cid))      # 🆕 2026-10-07 見込みなしで途中で止めた
            if not v and closed(path, cid):
                v = closed_verdict(data, closed(path, cid))  # 🆕 2026-10-18 途中の判定のあとオーナーが区切った
            if not v and data.get("kind") == "backtest":
                continue          # 過去のデータで1回だけ数えたもの＝ストップ以外は載せない（前向きは別に登録する）
            fix = REASON_FIX.get((path.replace("\\", "/").rsplit("/", 1)[-1], cid))
            if v and fix:
                v = dict(v, reason=fix)
            row = {"src": name, "sec": sec, "id": cid, "title": title, "goal": goal, "v": v, "unit": data.get("unit", "pct"),
                   "n": _count(data, cid)}
            (watching if not v else plus if v["status"] == "plus" else stop).append(row)
    return stop, plus, watching


def collect_markers(sources=None):
    """目印の前向き（kind: marker）→ 行の一覧。n＝目印ありの取引の回数"""
    out = []
    for path, name, sec in (MARKER_SOURCES if sources is None else sources):
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            continue
        if data.get("kind") == "marker":
            titles, verdicts = data.get("titles", {}), data.get("verdicts")
        elif data.get("marker_titles"):          # 🆕 J13F：1つの記録に買いの腕（titles）と目印の腕（marker_titles）がある
            titles, verdicts = data["marker_titles"], data.get("marker_verdicts")
        else:
            continue
        for cid, title in titles.items():
            v = (verdicts or {}).get(cid)
            if not v and retired(path, cid):
                v = retired_verdict(retired(path, cid))      # 🆕 2026-10-07 見込みなしで途中で止めた
            out.append({"src": name, "sec": sec, "id": cid, "title": title, "goal": data.get("goal"),
                        "v": v, "n": _count(data, cid, flagged=True)})
    return out


def render_markers(rows):
    """目印（見分け方）の前向きの節"""
    L = ["## 🔎 目印（見分け方）の前向き", "",
         "「入らない方がいい」目印が本当に効くかを、登録のあとの取引だけで数えたもの。数字は目印あり−なしの平均の差（費用前）。"
         "目印ありが決めた回数に届いた日に1回だけ判定し、差の95％の幅がまるごと0より下なら「確認」、それ以外は「ストップ」。", ""]
    if not rows:
        return L + ["- まだ無い", ""]
    done = [r for r in rows if r["v"]]
    if done:
        L += ["| 検証 | 目印 | 結果 | 判定日 | 目印ありの回数 | 差 | 95％の幅 | 理由 |", "|---|---|---|---|---:|---:|---|---|"]
        for r in done:
            v = r["v"]
            res = "✅ 確認" if v["status"] == "confirm" else "⏹ ストップ"
            L.append(f"| {_label(r)} | {r['title']} | {res} | {v['decided_on']} | {v['n']} | {_pct(v['mean'])} | "
                     f"{_pct(v['lo'])}〜{_pct(v['hi'])} | {v['reason']} |")
    L += [f"- 👀 {_label(r)} {r['title']}（目印あり {_progress(r)}）" for r in rows if not r["v"]]
    return L + [""]


def collect_tracker(path=TRACKER):
    """シグナルの条件（仮説）の採点で終わったもの → 行の一覧（新しく止めた順）。⛔反証＝期待と逆向きにはっきり出た／
    ⏹見込みなし＝signal_lab_tracker.futility（効きが小さすぎる・時間がかかりすぎる）"""
    try:
        with open(path, encoding="utf-8") as fh:
            hyps = json.load(fh).get("hypotheses") or []
    except (OSError, ValueError):
        return []
    import signal_lab_tracker as T
    flips = {h.get("flipped_from"): h for h in hyps if h.get("flipped_from")}
    out = []
    for h in hyps:
        st = h.get("status")
        if st not in ("rejected", "retired"):
            continue
        f = h.get("forward") or {}
        fl = flips.get(h.get("id")) or {}
        on = (h.get("retired_at") or h.get("rejected_at")
              or ((fl.get("flip_evidence") or {}).get("window") or "").split("〜")[-1] or "")
        if st == "retired":
            why = T.RETIRE_WORDS.get(h.get("retire_reason"), "見込みなし")
        else:
            why = "期待と逆向きにはっきり出た" + (f"（逆向きで登録し直した：{fl['id']}）" if fl.get("id") else "")
        out.append({"id": h.get("id"), "name": T.plain_name(h.get("filter") or {}), "kind": h.get("kind"), "status": st,
                    "registered": (h.get("registered_at") or "")[:10], "on": on, "n": f.get("n") or 0,
                    "mean": f.get("avgR"), "lo": f.get("rci_lo"), "hi": f.get("rci_hi"), "why": why})
    return sorted(out, key=lambda r: (r["on"], r["id"] or ""), reverse=True)


def render_tracker(rows):
    """シグナルの条件（仮説）の採点で終わったものの節"""
    L = ["## 🧪 シグナルの条件（仮説）の採点で終わったもの", "",
         "登録した日より後に出たシグナルだけで採点した仮説のうち、期待と逆向きにはっきり出た（⛔ 反証）か、見込みなしで止めた（⏹）もの。"
         "数字はいまの記録の1回あたりの損益（R＝損切りまでの幅を1とした単位）と、その95％の幅（止めたあとも採点は続くので、止めた日の数字とは違うことがある）。決まりは `signal_lab_tracker.py` と "
         "`PILLAR_PREREG.md`「見込みなしで止める決まり」。", ""]
    if not rows:
        return L + ["- まだ無い", ""]
    L += ["| 仮説 | 問い | 結果 | 止めた日 | 前向きの回数 | 平均 | 95％の幅 | 理由 |", "|---|---|---|---|---:|---:|---|---|"]
    for r in rows:
        q = "負けやすいか" if r["kind"] == "gate" else "勝ちやすいか"
        res = "⏹ 見込みなし" if r["status"] == "retired" else "⛔ 反証"
        L.append(f"| {r['id']} {r['name']} | {q} | {res} | {r['on'] or '—'} | {r['n']} | {_r(r['mean'])} | "
                 f"{_r(r['lo'])}〜{_r(r['hi'])} | {r['why']} |")
    return L + [""]


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
                tfname = {"M5": "5分足", "M15": "15分足", "H1": "1時間足", "H4": "4時間足"}
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


def render(stop, plus, watching, now=None, screens=(), markers=(), tracker=()):
    now = now or dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(timespec="minutes")
    L = ["# 検証済みリスト", "",
         f"更新: {now}（GitHub Actions が記録から組み立てる。手で書かない）。",
         "決まり（2026-09-28 オーナー）：検証（前向き、または過去のデータで1回だけ数えたもの）で**1000回を超えて期待値がプラスにならなかったものは、検証をストップしてここに載せる**。"
         "「プラス」は費用後の平均の95％の幅がまるごと0より上のとき。数字は費用を引いた1回あたりの損益率（末尾が R のものは、損切りまでの幅を1とした単位）。銘柄名は出さない。", "",
         "🆕 2026-10-07〜 判定を待たずに**見込みなしで途中で止めたもの**も「⏹ ストップ」に載せる（理由の欄に「見込みなし」・決まりは `PILLAR_PREREG.md`「見込みなしで止める決まり」）。", "",
         "## ⏹ ストップ（期待値がプラスにならなかった・見込みなしで止めた）", ""]
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
    L += [""] + render_markers(list(markers))
    L += render_tracker(list(tracker))
    L += render_screens(screens)
    L += ["詳しい決まりは `PILLAR_PREREG.md` の各節。", "", "---", "",
          "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def main():
    md = render(*collect(), screens=collect_screens(), markers=collect_markers(), tracker=collect_tracker())
    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
