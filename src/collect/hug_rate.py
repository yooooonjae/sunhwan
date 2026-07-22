"""HUG 민간아파트 평균 초기분양률 — 분양성 모델의 종속변수(라벨).

실행: python3 src/collect/hug_rate.py
산출: data/hug_initial_rate.json  {region: [{q: "2020Q1", rate: 89.5}...]}

경로 주의: data.go.kr 15088926 은 LINK 형(odcloud 파일 아님 — 404 함정).
정식 경로는 KOSIS 승인통계(orgId 414):
  DT_41401N_004 구계열(2014Q3~) + DT_41401N_008 신계열(최근) — 경계 중복은 신계열 우선.
초기분양률 = 분양개시 3~6개월 시점의 분양률(30세대 이상 민간아파트, 지역 평균).
단지 단위 라벨이 아니라 "지역·분기 평균"임을 모델·화면에 반드시 명기한다.
"""

import json
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
URL = "https://kosis.kr/openapi/Param/statisticsParameterData.do"
TABLES = ["DT_41401N_004", "DT_41401N_008"]  # 구계열 → 신계열 순 (신이 덮어씀)


def fetch(tbl: str, key: str) -> list[dict]:
    qs = urllib.parse.urlencode({
        "method": "getList", "apiKey": key, "format": "json", "jsonVD": "Y",
        "orgId": "414", "tblId": tbl, "objL1": "ALL", "itmId": "ALL",
        "prdSe": "Q", "newEstPrdCnt": "60",
    })
    with urllib.request.urlopen(f"{URL}?{qs}", timeout=30) as r:
        d = json.loads(r.read())
    if isinstance(d, dict):  # KOSIS 오류는 dict 로 온다
        raise RuntimeError(f"KOSIS {tbl}: {str(d)[:120]}")
    return d


def main():
    key = json.load(open("/Users/iseul/개발/config.json"))["kosis_key"]
    merged: dict[str, dict[str, float]] = {}
    for tbl in TABLES:  # 순서: 구계열 먼저, 신계열이 같은 (지역,분기)를 덮어쓴다
        for r in fetch(tbl, key):
            region = r.get("C1_NM", "").strip()
            prd = r.get("PRD_DE", "")          # "202601" = 2026Q1
            try:
                rate = float(r.get("DT"))
            except (TypeError, ValueError):
                continue
            if len(prd) == 6 and region:
                q = f"{prd[:4]}Q{int(prd[4:])}"
                merged.setdefault(region, {})[q] = round(rate, 1)
    out = {reg: [{"q": q, "rate": v} for q, v in sorted(m.items())]
           for reg, m in merged.items()}
    (ROOT / "data" / "hug_initial_rate.json").write_text(
        json.dumps(out, ensure_ascii=False), encoding="utf-8")
    qs_all = sorted({q for m in merged.values() for q in m})
    print(f"지역 {len(out)}개 · 분기 {qs_all[0]}~{qs_all[-1]} · 총 {sum(len(v) for v in out.values())}셀")
    nat = {x['q']: x['rate'] for x in out.get('전국', [])}
    tail = sorted(nat.items())[-4:]
    print("전국 최근:", tail)


if __name__ == "__main__":
    main()
