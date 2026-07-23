"""② 리츠 지표 계산 계약 테스트 — P/BV·배당수익률·부채비율.

계산 함수(site_data.pbv / div_yield / debt_ratio)를 순수 단위로 검증하고,
추가로 reits_block() 산출 번들의 불변식을 확인한다(커밋된 data/ 재사용).

pytest 로 수집되며, 의존성 없이 `python3 tests/test_reits.py` 로도 실행된다.
"""

import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "build"))

import site_data  # noqa: E402
from site_data import debt_ratio, div_yield, pbv  # noqa: E402


def test_pbv():
    """P/BV = 시가총액 / 자기자본 (소수 둘째 자리 반올림)."""
    assert pbv(2000, 1000) == 2.0
    assert pbv(500, 1000) == 0.5
    assert pbv(100, 3) == 33.33          # 33.333… → 33.33


def test_div_yield():
    """배당수익률(%) = 주당배당금 / 종가 × 100 (첫째 자리). 배당 없으면 None."""
    assert div_yield(250, 5000) == 5.0    # 250/5000*100
    assert div_yield(333, 10000) == 3.3   # 3.33 → 3.3
    assert div_yield(0, 5000) is None     # 배당 0 → None
    assert div_yield(None, 5000) is None  # 배당 결측 → None


def test_debt_ratio():
    """부채비율(총자산 대비, %) = 부채 / 자산 × 100. 결측/0 이면 None."""
    assert debt_ratio(600, 1000) == 60.0
    assert debt_ratio(1, 3) == 33.3       # 33.333… → 33.3
    assert debt_ratio(None, 1000) is None
    assert debt_ratio(500, None) is None
    assert debt_ratio(0, 1000) is None    # 부채 0(falsy) → None (원 코드 규약)


def test_reits_block_bundle_invariants():
    """산출 번들 검증 — reits_block() 이 커밋된 data/ 로 일관된 지표를 낸다."""
    b = site_data.reits_block()
    items = b["items"]
    assert items, "리츠 항목이 비어 있음"
    assert b["kpi"]["n"] == len(items)
    # kpi.pb_med 는 항목 pb 의 중위값과 정확히 일치해야 한다(필드 배선 검증).
    assert b["kpi"]["pb_med"] == round(statistics.median(i["pb"] for i in items), 2)
    for i in items:
        assert isinstance(i["pb"], (int, float))
        # dy·ltv 는 None 이거나 비음수이며 계산식대로 소수 첫째 자리로 반올림돼 있어야 한다.
        assert i["dy"] is None or (i["dy"] >= 0 and round(i["dy"], 1) == i["dy"])
        assert i["ltv"] is None or (i["ltv"] >= 0 and round(i["ltv"], 1) == i["ltv"])


if __name__ == "__main__":
    import inspect
    tests = [f for n, f in sorted(globals().items())
             if n.startswith("test_") and inspect.isfunction(f)]
    for f in tests:
        f()
        print("  ok ", f.__name__)
    print(f"\n{len(tests)} passed (test_reits)")
