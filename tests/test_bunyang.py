"""① 공통 기준분기 80% 선택 규칙 계약 테스트 — site_data.common_base_quarter.

규칙: 유효 지역(rate!=None) 커버리지가 80% 이상인 분기 중 가장 최신을 고르되,
80%를 넘는 분기가 없으면 (최대 커버리지, 최신)으로 폴백한다.

pytest 로 수집되며, 의존성 없이 `python3 tests/test_bunyang.py` 로도 실행된다.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "build"))

from site_data import SIDO_ORDER, common_base_quarter  # noqa: E402

FIX = ROOT / "tests" / "fixtures"
FIVE = ["서울", "경기", "부산", "대구", "인천"]  # total=5 → 80% 임계 = 4


def test_fixture_exact_80pct_boundary_picks_latest_eligible():
    """hug 축소판: 2025Q2 가 정확히 80%(4/5) 경계 — 포함되어 선택되고,
    더 최신인 2025Q3(2/5=40%)은 제외된다. (집계 키 '전국'은 real_sidos 필터로 무시)"""
    hug = json.load(open(FIX / "hug_min.json"))
    r = common_base_quarter(hug, FIVE)
    assert r["q"] == "2025Q2", r
    assert r["valid"] == 4 and r["total"] == 5
    assert r["coverage"] == 0.8


def test_newest_below_threshold_is_skipped():
    """최신 분기가 80% 미만(3/5=60%)이면 건너뛰고, 직전의 적격 분기(4/5)를 고른다."""
    hug = {
        "서울": [{"q": "2025Q1", "rate": 1.0}, {"q": "2025Q2", "rate": 1.0}, {"q": "2025Q3", "rate": 1.0}],
        "경기": [{"q": "2025Q1", "rate": 1.0}, {"q": "2025Q2", "rate": 1.0}, {"q": "2025Q3", "rate": 1.0}],
        "부산": [{"q": "2025Q1", "rate": 1.0}, {"q": "2025Q2", "rate": 1.0}, {"q": "2025Q3", "rate": 1.0}],
        "대구": [{"q": "2025Q1", "rate": 1.0}, {"q": "2025Q2", "rate": 1.0}],   # Q3 없음
        "인천": [{"q": "2025Q1", "rate": 1.0}],                                  # Q2·Q3 없음
    }
    # Q1 5/5=1.0(적격), Q2 4/5=0.8(적격), Q3 3/5=0.6(부적격) → 최신 적격 = Q2
    r = common_base_quarter(hug, FIVE)
    assert r["q"] == "2025Q2", r
    assert r["coverage"] == 0.8


def test_fallback_when_none_reach_80pct():
    """80%에 닿는 분기가 하나도 없으면 (최대 커버리지, 최신) 폴백."""
    hug = {
        "서울": [{"q": "2025Q1", "rate": 1.0}, {"q": "2025Q2", "rate": 1.0}],
        "경기": [{"q": "2025Q1", "rate": 1.0}, {"q": "2025Q2", "rate": 1.0}],
        "부산": [{"q": "2025Q1", "rate": 1.0}],   # Q2 없음
    }
    # Q1 3/5=0.6, Q2 2/5=0.4 → 적격 없음 → 최대 커버리지(Q1, 3표) 선택
    r = common_base_quarter(hug, FIVE)
    assert r["q"] == "2025Q1", r
    assert r["valid"] == 3 and r["coverage"] == 0.6


def test_fallback_tiebreak_prefers_latest():
    """폴백 시 커버리지 동률이면 더 최신 분기를 고른다."""
    hug = {
        "서울": [{"q": "2025Q1", "rate": 1.0}, {"q": "2025Q2", "rate": 1.0}],
        "경기": [{"q": "2025Q1", "rate": 1.0}, {"q": "2025Q2", "rate": 1.0}],
    }
    # 두 분기 모두 2/5=0.4 동률 → 최신 Q2
    r = common_base_quarter(hug, FIVE)
    assert r["q"] == "2025Q2", r


def test_empty_hug_returns_none():
    """관측이 전혀 없으면 q=None·coverage=0(0 대체 금지 규약)."""
    r = common_base_quarter({}, FIVE)
    assert r["q"] is None
    assert r["valid"] == 0 and r["total"] == 5 and r["coverage"] == 0


def test_default_17_sido_threshold_is_14():
    """기본 real_sidos(17개 시도)에서 80% 임계 = 14. 14/17 적격·13/17 부적격."""
    reals = [s for s in SIDO_ORDER if s != "전국"]
    assert len(reals) == 17
    hug = {}
    for i, s in enumerate(reals):
        arr = []
        if i < 14:                     # 2024Q1: 앞 14개 시도 관측 → 14/17=0.8235 적격
            arr.append({"q": "2024Q1", "rate": 1.0})
        if i < 13:                     # 2024Q2: 앞 13개 시도 관측 → 13/17=0.7647 부적격
            arr.append({"q": "2024Q2", "rate": 1.0})
        hug[s] = arr
    r = common_base_quarter(hug)       # real_sidos 생략 → 기본 17개 시도
    assert r["q"] == "2024Q1", r       # 더 최신 Q2 는 80% 미달로 제외
    assert r["valid"] == 14 and r["total"] == 17
    assert r["coverage"] == 0.8235


if __name__ == "__main__":
    import inspect
    tests = [f for n, f in sorted(globals().items())
             if n.startswith("test_") and inspect.isfunction(f)]
    for f in tests:
        f()
        print("  ok ", f.__name__)
    print(f"\n{len(tests)} passed (test_bunyang)")
