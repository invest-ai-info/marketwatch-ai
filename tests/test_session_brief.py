# -*- coding: utf-8 -*-
"""ロンドン時間・NY時間の前の確認メール（session_brief.py・session-brief.yml）のテスト。2026-10-08 夜 新設。

確かめること＝①送る時間帯（平日・ロンドン前 13:30〜15:00／遅れ〜16:00・NY前 18:30〜20:00／遅れ〜21:00）とワークフローの時刻の一致
②今夜の指標の範囲（ロンドン前は 24:00 まで・NY前は翌 06:00 まで）・中銀の印・発表直後の倍率 ③通貨の強弱（24時間・今日の◯時から・約5日・
主なペア）④AIの通貨ごとの見立て・ニュースの見出し・決まりと研究の注意・金曜の印 ⑤件名 ⑥相乗り先が「まもなく」メールと同じ5本・
1日1通の印・秘密の値 ⑦見張り番への登録。

実行:  python tests/test_session_brief.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import json
import os
import re
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import session_brief as S  # noqa: E402

JST = S.JST


def T(s):
    return dt.datetime.fromisoformat(s).replace(tzinfo=JST)


def test_windows_and_workflow_times_agree():
    assert S.window("london", T("2026-10-09T13:29")) is None and S.window("london", T("2026-10-09T13:30")) == "send"
    assert S.window("london", T("2026-10-09T14:59")) == "send" and S.window("london", T("2026-10-09T15:00")) == "late"
    assert S.window("london", T("2026-10-09T16:00")) is None and S.window("ny", T("2026-10-09T19:59")) == "send"
    assert S.window("ny", T("2026-10-09T20:30")) == "late" and S.window("ny", T("2026-10-10T19:00")) is None   # 土曜
    assert S.session_now(T("2026-10-12T14:00")) == "london" and S.session_now(T("2026-10-12T17:00")) is None
    wf = open(".github/workflows/session-brief.yml", encoding="utf-8").read()
    assert '-ge 1330 ] && [ "$hm" -lt 1600 ]; then s=london; since=9; news=europe' in wf
    assert '-ge 1830 ] && [ "$hm" -lt 2100 ]; then s=ny; since=15; news=us' in wf
    assert (S.SESSIONS["london"]["open"], S.SESSIONS["london"]["close"], S.SESSIONS["ny"]["open"], S.SESSIONS["ny"]["close"]) == \
           ((13, 30), (16, 0), (18, 30), (21, 0))
    assert (S.SESSIONS["london"]["since"], S.SESSIONS["ny"]["since"]) == (9, 15)
    for cron in ("'41 4 * * 1-5'", "'7 5 * * 1-5'", "'23 5 * * 1-5'", "'41 9 * * 1-5'", "'7 10 * * 1-5'", "'23 10 * * 1-5'"):
        assert cron in wf, cron


def test_rides_the_same_workflows_as_the_alert():
    names = lambda p: re.findall(r'^\s+- "([^"]+)"', open(p, encoding="utf-8").read().split("types:")[0], re.M)
    assert names(".github/workflows/session-brief.yml") == names(".github/workflows/indicator-alert.yml") and len(names(".github/workflows/indicator-alert.yml")) == 5
    wf = open(".github/workflows/session-brief.yml", encoding="utf-8").read()
    assert "key: session-brief-${{ steps.s.outputs.session }}-${{ steps.s.outputs.date }}" in wf and "date -u > .session-marker" in wf
    assert "secrets.GMAIL_APP_PASSWORD" in wf and wf.count("continue-on-error: true") == 2 and "cancel-in-progress: false" in wf
    h = open("check_automation_health.py", encoding="utf-8").read()
    assert '"session-brief.yml",      6,' in h and '"session-brief.yml", 1, dt.date(2026, 10, 9), "workflow_run"' in h


EVENTS = {"events": [
    {"name": "英 雇用統計", "datetime": "2026-10-13T15:00:00+09:00", "affected_assets": ["GBPJPY=X"], "category": "indicator"},
    {"name": "英中銀 政策金利", "datetime": "2026-10-13T20:00:00+09:00", "affected_assets": ["GBPJPY=X"], "category": "central_bank"},
    {"name": "米 CPI（9月分）", "datetime": "2026-10-13T21:30:00+09:00", "affected_assets": ["all"], "category": "indicator"},
    {"name": "FOMC 政策金利", "datetime": "2026-10-14T03:00:00+09:00", "affected_assets": ["all"], "category": "central_bank"},
    {"name": "豪 雇用統計", "datetime": "2026-10-14T09:30:00+09:00", "affected_assets": ["AUDJPY=X"], "category": "indicator"},
    {"name": "🏖️ 英国休場", "datetime": "2026-10-13T00:00:00+09:00", "affected_assets": ["all"], "category": "market_holiday"}]}


def _events_path():
    d = tempfile.mkdtemp()
    p = os.path.join(d, "ev.json")
    json.dump(EVENTS, open(p, "w", encoding="utf-8"), ensure_ascii=False)
    return p


def test_events_windows():
    p = _events_path()
    ind, hol = S.events_in("london", T("2026-10-13T14:00"), p)
    assert [e["name"] for _, e in ind] == ["英 雇用統計", "英中銀 政策金利", "米 CPI（9月分）"] and [e["name"] for _, e in hol] == ["🏖️ 英国休場"]
    ind, _ = S.events_in("ny", T("2026-10-13T19:00"), p)
    assert [e["name"] for _, e in ind] == ["英中銀 政策金利", "米 CPI（9月分）", "FOMC 政策金利"]       # 翌 06:00 まで・豪の 09:30 は入らない
    s = "\n".join(S.events_section("ny", ind, T("2026-10-13T19:00")))
    assert "🏦 20:00（あと1.0h）  英中銀 政策金利" in s and "🚫 21:30（あと2.5h）  米 CPI（9月分）" in s and "🏦 03:00" in s
    assert "いま〜翌 06:00" in s and "新規を建てない" in s and "📏 過去2年の実測" in s
    s2 = "\n".join(S.events_section("london", S.events_in("london", T("2026-10-13T11:00"), p)[0], T("2026-10-13T11:00")))
    assert "🟡 15:00（あと4.0h）  英 雇用統計" in s2                                         # 3時間より先は 🟡
    assert S.events_in("ny", T("2026-10-13T19:00"), "/nonexistent.json") == (None, None)


FX_D = {"h24": {"USD": 0.4, "EUR": -0.1, "GBP": 0.06, "JPY": -0.3, "AUD": 0.0},
        "since": {"USD": 0.1, "EUR": 0.2, "GBP": -0.2, "JPY": 0.0, "AUD": 0.05},
        "d5": {"USD": 1.0, "EUR": -0.4, "GBP": -0.2, "JPY": -0.6, "AUD": 0.3},
        "pairs": {"GBPJPY=X": {"h24": 0.36, "since": -0.2, "d5": 0.4}, "EURUSD=X": {"h24": -0.5, "since": None, "d5": -1.4},
                  "USDJPY=X": {"h24": 0.7, "since": 0.1, "d5": 1.6}}}
FC = {"generated_at": "2026-10-13T06:15:00+09:00",
      "risk_regime": {"regime": "RISK_OFF", "confidence": "MID", "key_drivers": ["FOMC", "原油", "ドル高", "四つ目"]},
      "currencies": [{"code": "GBP", "lean": "WEAK", "conviction": "MID", "reason": "英中銀の利下げ観測"},
                     {"code": "USD", "lean": "STRONG", "conviction": "HIGH", "reason": "米金利の上昇"}]}
NEWS = {"items": [{"t": "英中銀総裁が講演", "s": "ロイター", "dt": "2026-10-13T10:05+09:00", "r": "GB"}]}


def test_build_london_sections_and_subject():
    subj, body = S.build("london", T("2026-10-13T14:00"), FX_D, NEWS, FC, "send", _events_path())
    assert subj == "🇬🇧 ロンドン時間の前 10/13(火)：強い 米ドル／弱い 円・今夜の指標 3件（15:00 英 雇用統計）"
    for s in ("24時間：米ドル +0.40%（強い）", "今日の東京時間（9時〜）：ユーロ +0.20%（強い）", "約5日（傾向）：米ドル +1.00%",
              "主なペア：ポンド円 +0.36%（24時間）・-0.20%（東京時間）／ユーロドル -0.50%（24時間）",
              "・ポンド 弱い（中）：英中銀の利下げ観測", "・材料：FOMC", "🇬🇧 10-13 10:05 英中銀総裁が講演（ロイター）",
              "L1・L2", "M6 ポンド円", "XC1", "🏖️ 休場", "投資助言ではありません", "ロンドン時間の前の確認"):
        assert s in body, s
    assert "四つ目" not in body and "金曜" not in body and "⏰" not in subj


def test_build_ny_friday_late_and_missing_parts():
    subj, body = S.build("ny", T("2026-10-16T20:10"), None, None, None, "late", _events_path())
    assert subj.startswith("⏰遅れ 🇺🇸 NY時間の前 10/16(金)：今夜の指標 0件") and "予定（20:00）より遅れて届いた" in body
    for s in ("値動きの強弱を取れなかった", "見立てを読めない", "米国のニュースの見出し", "取れなかった", "X5", "S2", "🚩 今日は金曜"):
        assert s in body, s
    fc_old = dict(FC, currencies=[])
    _, b2 = S.build("ny", T("2026-10-13T19:00"), FX_D, {"items": []}, fc_old, "send", _events_path())
    assert "12時間より古い" in b2 and "通貨ごと：このブリーフィングには無い" in b2 and "直近30時間になし" in b2 and "今日の欧州時間（15時〜）" in b2


def test_main_respects_the_window():
    assert S.main(["--now", "2026-10-10T14:00"]) == 0                     # 土曜＝送らない（送信まで進まない）
    assert S.main(["--now", "2026-10-09T17:00"]) == 0


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
