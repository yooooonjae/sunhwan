"""청약홈(한국부동산원) 전량 백필 — Ⅱ장 「분양」의 원천.

실행: python3 src/collect/cheongyak.py
산출: data/cheongyak/{op}.json + 원본 페이지 캐시 data/raw/cheongyak/{op}_p{n}.json

오퍼레이션 5종 (odcloud, 소급 하한 2020-02 = 청약홈 개시):
  apt_detail   분양정보(공고 단위: 공급규모·일정·지역·규제 플래그)
  apt_model    주택형별 상세(전용면적·세대수·공급금액 = 분양가)  ← 분양가는 여기에만 있다
  remainder    무순위/잔여세대 공고  ← "미계약 발생"의 대리지표
  compet       순위별·주택형별 접수·경쟁률
  score        주택형별 당첨가점 최저/최고/평균

쿼터: 개발계정 일 40,000건 — perPage 500 이면 전량 백필도 수백 콜 이내.
"""

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "cheongyak"
OUT = ROOT / "data" / "cheongyak"

BASE = "https://api.odcloud.kr/api"
OPS = {
    "apt_detail": f"{BASE}/ApplyhomeInfoDetailSvc/v1/getAPTLttotPblancDetail",
    "apt_model":  f"{BASE}/ApplyhomeInfoDetailSvc/v1/getAPTLttotPblancMdl",
    "remainder":  f"{BASE}/ApplyhomeInfoDetailSvc/v1/getRemndrLttotPblancDetail",
    "compet":     f"{BASE}/ApplyhomeInfoCmpetRtSvc/v1/getAPTLttotPblancCmpet",
    "score":      f"{BASE}/ApplyhomeInfoCmpetRtSvc/v1/getAPTLttotPblancScore",
}
PER_PAGE = 500
CALL_GAP = 0.15


def _get(url: str, params: dict) -> dict:
    qs = urllib.parse.urlencode(params, safe="%")
    req = urllib.request.Request(f"{url}?{qs}", headers={"User-Agent": "sunhwan/0.1"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def collect_op(op: str, key: str) -> list[dict]:
    """한 오퍼레이션 전량 페이지네이션. 원본 페이지는 캐시(있으면 재호출 스킵)."""
    url = OPS[op]
    rows: list[dict] = []
    page = 1
    while True:
        cache = RAW / f"{op}_p{page}.json"
        if cache.exists():
            d = json.loads(cache.read_text())
        else:
            time.sleep(CALL_GAP)
            d = _get(url, {"page": page, "perPage": PER_PAGE, "serviceKey": key})
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(d, ensure_ascii=False))
        batch = d.get("data", [])
        rows.extend(batch)
        total = d.get("totalCount", 0)
        if page * PER_PAGE >= total or not batch:
            # 마지막 페이지는 다음 실행에서 갱신되도록 캐시하지 않는다(신규 공고 유입 지점)
            if page * PER_PAGE >= total and cache.exists() and len(batch) < PER_PAGE:
                cache.unlink()
            return rows
        page += 1


def main():
    key = json.load(open(ROOT / "config.json"))["service_key"]
    OUT.mkdir(parents=True, exist_ok=True)
    summary = {}
    for op in OPS:
        rows = collect_op(op, key)
        (OUT / f"{op}.json").write_text(
            json.dumps(rows, ensure_ascii=False), encoding="utf-8")
        summary[op] = len(rows)
        print(f"  {op}: {len(rows):,}행")
    (OUT / "_meta.json").write_text(json.dumps(
        {"counts": summary, "per_page": PER_PAGE,
         "note": "소급 하한 2020-02(청약홈 개시). 분양가는 apt_model.공급금액."},
        ensure_ascii=False, indent=1))
    print("백필 완료:", sum(summary.values()), "행 총계")


if __name__ == "__main__":
    main()
