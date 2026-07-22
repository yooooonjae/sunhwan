"""Ⅱ장 분양성 데이터셋 조립 — 공고 단위 모델링 테이블.

실행: python3 src/analysis/bunyang.py
산출: data/bunyang_dataset.json
  rows: 공고별 {id, name, sido, date, q, supply, months_to_movein,
               reg_speculation, reg_adjust, reg_price_cap,
               price_m2(만원/㎡ 중위), compet_total, compet_r1_local,
               score_med, remainder_sido_q, unsold_sido, base_rate,
               label_q1, label_q2}
  meta: 커버리지·결측 통계

설계 노트
  · 라벨(HUG 초기분양률)은 시도·분기 "평균" — 단지 라벨이 아님을 모델 해석에 명기.
  · 경쟁률은 표기 문자열("(△15)") 대신 Σ접수/Σ공급 재계산 — 미달 표기 파싱 회피.
  · 거시(미분양·기준금리)는 수지(~/개발/out/market.json) 재사용 — 공고월 기준 조인.
"""

import json
import os
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# 수지(收支) 저장소 위치 — 기본 ~/개발, SUJI_DIR 로 재정의(이식성).
SUJI = Path(os.environ.get("SUJI_DIR", str(Path.home() / "개발")))
MARKET = SUJI / "out" / "market.json"


def _q(date: str) -> str:
    return f"{date[:4]}Q{(int(date[5:7]) - 1) // 3 + 1}"


def _next_q(q: str, n: int = 1) -> str:
    y, k = int(q[:4]), int(q[5])
    k += n
    return f"{y + (k - 1) // 4}Q{(k - 1) % 4 + 1}"


def _area_of(house_ty: str):
    """'084.9800A' → 84.98 (㎡). 파싱 실패는 None."""
    try:
        return float(house_ty.strip().rstrip("ABCDEFGH"))
    except (ValueError, AttributeError):
        return None


def main():
    D = ROOT / "data"
    det = json.load(open(D / "cheongyak" / "apt_detail.json"))
    mdl = json.load(open(D / "cheongyak" / "apt_model.json"))
    com = json.load(open(D / "cheongyak" / "compet.json"))
    sco = json.load(open(D / "cheongyak" / "score.json"))
    rem = json.load(open(D / "cheongyak" / "remainder.json"))
    hug = json.load(open(D / "hug_initial_rate.json"))

    # 주택형별 ㎡당 분양가(만원) → 공고 중위
    price_by = defaultdict(list)
    for m in mdl:
        area = _area_of(m.get("HOUSE_TY", ""))
        try:
            amt = float(m.get("LTTOT_TOP_AMOUNT") or 0)  # 만원
        except ValueError:
            amt = 0
        if area and amt > 0:
            price_by[str(m["HOUSE_MANAGE_NO"])].append(amt / area)

    # 경쟁률: 총합 + 1순위 해당지역
    agg = defaultdict(lambda: [0, 0, 0, 0])  # req, sup, r1l_req, r1l_sup
    for r in com:
        no = str(r.get("HOUSE_MANAGE_NO"))
        try:
            req, sup = int(r.get("REQ_CNT") or 0), int(r.get("SUPLY_HSHLDCO") or 0)
        except ValueError:
            continue
        a = agg[no]
        a[0] += req; a[1] += sup
        if r.get("SUBSCRPT_RANK_CODE") == 1 and r.get("RESIDE_SECD") == "01":
            a[2] += req; a[3] += sup

    # 가점: 공고 중위 평균가점
    score_by = defaultdict(list)
    for s in sco:
        try:
            score_by[str(s["HOUSE_MANAGE_NO"])].append(float(s.get("AVRG_SCORE")))
        except (ValueError, TypeError):
            pass

    # 무순위: 시도·분기 발생 건수 (미계약 스트레스의 거시 대리지표)
    rem_sq = defaultdict(int)
    for r in rem:
        dt, sido = r.get("RCRIT_PBLANC_DE") or "", r.get("SUBSCRPT_AREA_CODE_NM")
        if len(dt) >= 7 and sido:
            rem_sq[(sido, _q(dt))] += 1

    # 거시(수지 재사용): 시도·월 미분양, 월 기준금리
    unsold, base_rate = {}, {}
    if MARKET.exists():
        M = json.load(open(MARKET))
        for sido, series in (M.get("unsold") or {}).items():
            for p in series:
                unsold[(sido, p["ym"])] = p["value"]
        for p in M.get("base_rate") or []:
            base_rate[p["ym"]] = p["value"]

    label = {(reg, x["q"]): x["rate"] for reg, arr in hug.items() for x in arr}

    rows, miss = [], defaultdict(int)
    for d in det:
        no = str(d.get("HOUSE_MANAGE_NO"))
        date, sido = d.get("RCRIT_PBLANC_DE") or "", d.get("SUBSCRPT_AREA_CODE_NM")
        if len(date) < 7 or not sido:
            miss["meta"] += 1
            continue
        q, ym = _q(date), date[:4] + date[5:7]
        a = agg.get(no)
        prices = price_by.get(no)
        scores = score_by.get(no)
        mvn = d.get("MVN_PREARNGE_YM") or ""
        months_to = ((int(mvn[:4]) - int(ym[:4])) * 12 + int(mvn[4:]) - int(ym[4:])) if len(mvn) == 6 else None
        row = {
            "id": no, "name": d.get("HOUSE_NM"), "sido": sido, "date": date, "q": q,
            "supply": d.get("TOT_SUPLY_HSHLDCO"),
            "months_to_movein": months_to,
            "reg_speculation": d.get("SPECLT_RDN_EARTH_AT") == "Y",
            "reg_adjust": d.get("MDAT_TRGET_AREA_SECD") == "Y",
            "reg_price_cap": d.get("PARCPRC_ULS_AT") == "Y",
            "price_m2": round(statistics.median(prices), 1) if prices else None,
            "compet_total": round(a[0] / a[1], 3) if a and a[1] else None,
            "compet_r1_local": round(a[2] / a[3], 3) if a and a[3] else None,
            "score_med": round(statistics.median(scores), 1) if scores else None,
            "remainder_sido_q": rem_sq.get((sido, q), 0),
            "unsold_sido": unsold.get((sido, ym)),
            "base_rate": base_rate.get(ym),
            "label_q1": label.get((sido, _next_q(q))),
            "label_q2": label.get((sido, _next_q(q, 2))),
        }
        for k in ("price_m2", "compet_total", "score_med", "label_q1"):
            if row[k] is None:
                miss[k] += 1
        rows.append(row)

    meta = {
        "n": len(rows),
        "coverage": {k: len(rows) - miss[k] for k in ("price_m2", "compet_total", "score_med", "label_q1")},
        "missing": dict(miss),
        "note": "라벨=HUG 초기분양률(시도·분기 평균, 공고분기+1). 경쟁률=Σ접수/Σ공급 재계산.",
    }
    (D / "bunyang_dataset.json").write_text(
        json.dumps({"meta": meta, "rows": rows}, ensure_ascii=False), encoding="utf-8")
    print(f"공고 {meta['n']:,}건 · 커버리지 {meta['coverage']}")

    # 새니티: 분양가상한제 여부별 경쟁률 중위
    cap = [r["compet_total"] for r in rows if r["reg_price_cap"] and r["compet_total"] is not None]
    non = [r["compet_total"] for r in rows if not r["reg_price_cap"] and r["compet_total"] is not None]
    if cap and non:
        print(f"새니티 — 분상제 적용 경쟁률 중위 {statistics.median(cap):.2f}:1 vs 미적용 {statistics.median(non):.2f}:1")


if __name__ == "__main__":
    main()
