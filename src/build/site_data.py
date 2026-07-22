"""사이트 데이터 번들 생성 — out/site_bundle.json (빌드가 JS 로 래핑).

실행: python3 src/build/site_data.py
"""

import datetime
import json
import os
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "data"
OUT = ROOT / "out"
# 수지(收支) 저장소 위치 — 기본 ~/개발, SUJI_DIR 로 재정의(이식성).
SUJI = Path(os.environ.get("SUJI_DIR", str(Path.home() / "개발")))

REPRT_ORD = {"1분기": 1, "반기": 2, "3분기": 3, "사업": 4}
SIDO_ORDER = ["전국", "서울", "경기", "인천", "부산", "대구", "광주", "대전", "울산",
              "세종", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]


def bunyang_block():
    ds = json.load(open(D / "bunyang_dataset.json"))
    rows = ds["rows"]
    hug = json.load(open(D / "hug_initial_rate.json"))

    # ① 초기분양률 히트맵: 시도 × 최근 12분기
    qs = sorted({x["q"] for arr in hug.values() for x in arr})[-12:]
    sidos = [s for s in SIDO_ORDER if s in hug]
    heat = {"xs": qs, "ys": sidos,
            "cells": [[next((x["rate"] for x in hug[s] if x["q"] == q), None) for q in qs]
                      for s in sidos]}

    # ② 경쟁률 사다리: 구간별 초기분양률 중위 (라벨 = 공고분기+1)
    ladder_def = [("미달 (1:1 미만)", 0, 1), ("1~3:1", 1, 3), ("3~5:1", 3, 5),
                  ("5~10:1", 5, 10), ("10:1 이상", 10, 1e9)]
    ladder = []
    for name, lo, hi in ladder_def:
        vals = [r["label_q1"] for r in rows
                if r["compet_total"] is not None and r["label_q1"] is not None
                and lo <= r["compet_total"] < hi]
        ladder.append({"name": name, "value": round(statistics.median(vals), 1) if vals else None,
                       "n": len(vals)})

    # ③ 분상제 효과
    cap = [r["compet_total"] for r in rows if r["reg_price_cap"] and r["compet_total"] is not None]
    non = [r["compet_total"] for r in rows if not r["reg_price_cap"] and r["compet_total"] is not None]
    price_cap = {"cap": {"n": len(cap), "med": round(statistics.median(cap), 2)},
                 "non": {"n": len(non), "med": round(statistics.median(non), 2)}}

    # ④ 분기별 시장 맥: 공고 수·중위 경쟁률·무순위 건수·전국 초기분양률
    byq = defaultdict(lambda: {"n": 0, "compet": [], "rem": 0})
    for r in rows:
        b = byq[r["q"]]
        b["n"] += 1
        if r["compet_total"] is not None:
            b["compet"].append(r["compet_total"])
    rem = json.load(open(D / "cheongyak" / "remainder.json"))
    for r in rem:
        dt = r.get("RCRIT_PBLANC_DE") or ""
        if len(dt) >= 7:
            q = f"{dt[:4]}Q{(int(dt[5:7]) - 1) // 3 + 1}"
            byq[q]["rem"] += 1
    nat = {x["q"]: x["rate"] for x in hug.get("전국", [])}
    pulse = [{"q": q, "n": b["n"],
              "compet_med": round(statistics.median(b["compet"]), 2) if b["compet"] else None,
              "remainder": b["rem"], "rate_nat": nat.get(q)}
             for q, b in sorted(byq.items()) if q >= "2020Q1"]

    # ⑤ 최신 분기 시도별 초기분양률
    latest_q = qs[-1]
    latest = [{"name": s, "value": next((x["rate"] for x in hug[s] if x["q"] == latest_q), None)}
              for s in sidos]

    # ⑦ 지도 채색용: 각 시도의 "지역별 최신 가용 분기" + "공통 기준분기" 초기분양률.
    #    집계 키(전국·수도권·지방·광역시 계열)는 지도에서 제외 — SIDO_ORDER 의 실제 17개 시도만.
    def _qk(q):  # "2026Q1" → 정렬 키
        return (int(q[:4]), int(q[5]))
    real_sidos = [s for s in SIDO_ORDER if s != "전국"]        # 17개 시도
    # 공통 기준분기 = 유효 지역 커버리지 80% 이상인 분기 중 가장 최신 (없으면 최대 커버리지·최신 폴백)
    q_valid = defaultdict(int)
    for s in real_sidos:
        for x in hug.get(s, []):
            if x.get("rate") is not None:
                q_valid[x["q"]] += 1
    total_sido = len(real_sidos)
    elig = [q for q in q_valid if q_valid[q] / total_sido >= 0.8]
    common_q = (max(elig, key=_qk) if elig
                else max(q_valid, key=lambda q: (q_valid[q], _qk(q))) if q_valid else None)
    common = {"q": common_q, "valid": q_valid.get(common_q, 0), "total": total_sido,
              "coverage": round(q_valid.get(common_q, 0) / total_sido, 4) if common_q else 0}

    geo_map = []
    for s in real_sidos:
        ser = sorted(hug.get(s, []), key=lambda x: _qk(x["q"]))
        if not ser:
            geo_map.append({"name": s, "q": None, "rate": None,
                            "prev_q": None, "prev_rate": None, "delta": None,
                            "common_rate": None, "common_prev_q": None, "common_delta": None})
            continue
        last = ser[-1]
        prev = ser[-2] if len(ser) >= 2 else None
        # 공통 기준분기 값 + 직전 관측 대비 (없으면 결측 — 0 대체 금지)
        cr = cpq = cprev = None
        for i, x in enumerate(ser):
            if x["q"] == common_q:
                cr = x["rate"]
                if i > 0:
                    cpq, cprev = ser[i - 1]["q"], ser[i - 1]["rate"]
                break
        geo_map.append({"name": s, "q": last["q"], "rate": last["rate"],
                        "prev_q": prev["q"] if prev else None,
                        "prev_rate": prev["rate"] if prev else None,
                        "delta": round(last["rate"] - prev["rate"], 1) if prev else None,
                        "common_rate": cr, "common_prev_q": cpq,
                        "common_delta": round(cr - cprev, 1) if (cr is not None and cprev is not None) else None})

    # ⑥ 분양가 프리미엄 × 경쟁률 산점 — 시세 = 수지 RTMS 시도 대표구 중위(공고월)
    prem_pts, n_drop = [], 0
    rtms = json.load(open(SUJI / "data" / "rtms.json"))["trades"]
    CAP_REGIONS = {"서울", "경기", "인천"}
    med_cache = {}
    for sido, gus in rtms.items():
        gu = next(iter(gus))
        med_cache[sido] = {p["ym"]: p["median_price_per_m2"] for p in gus[gu] if p.get("median_price_per_m2")}
    for r in rows:
        if r["price_m2"] is None or r["compet_total"] is None:
            continue
        ym = r["date"][:4] + r["date"][5:7]
        base = med_cache.get(r["sido"], {}).get(ym)
        if not base:
            n_drop += 1
            continue
        prem = (r["price_m2"] * 1e4) / base  # 만원/㎡ → 원/㎡ 대비 배율
        if not (0.4 <= prem <= 3.0) or r["compet_total"] > 80:
            n_drop += 1
            continue
        prem_pts.append({"x": round(prem, 2), "y": round(min(r["compet_total"], 80), 2),
                         "size": r["supply"] or 100,
                         "group": "수도권" if r["sido"] in CAP_REGIONS else "지방",
                         "name": (r["name"] or "")[:16]})
    import math
    xs_ = [math.log(p["x"]) for p in prem_pts]; ys_ = [math.log1p(p["y"]) for p in prem_pts]
    n_ = len(prem_pts); mx_, my_ = sum(xs_) / n_, sum(ys_) / n_
    r_prem = (sum((a - mx_) * (b - my_) for a, b in zip(xs_, ys_))
              / (sum((a - mx_) ** 2 for a in xs_) ** .5 * sum((b - my_) ** 2 for b in ys_) ** .5))
    premium = {"pts": prem_pts, "n": n_, "dropped": n_drop, "r_loglog": round(r_prem, 2)}

    return {"heat": heat, "ladder": ladder, "price_cap": price_cap,
            "pulse": pulse, "latest": {"q": latest_q, "rows": latest},
            "map": geo_map, "map_common": common, "premium": premium, "meta": ds["meta"]}


def jeongbi_block():
    """Ⅰ장 공급 — Phase 1(대구·경기 이력 + 부산 스냅샷)."""
    J = json.load(open(D / "jeongbi_phase1.json"))
    schema = J["schema"]
    hist_regions = ["대구", "경기"]

    # 이력 구역(도정법만) 풀
    hist = [z for r in hist_regions for z in J["regions"][r] if not z.get("small_scale")]

    # ① 단계 퍼널: 단계일자 보유 구역 수 (이력 2지역 합)
    funnel = []
    for st_ in schema:
        n = sum(1 for z in hist if (z.get("dates") or {}).get(st_))
        funnel.append({"stage": st_, "n": n})

    # ② 인접 단계 소요기간: 중위·IQR (n>=10 만)
    import datetime as dt
    def yrs(a, b):
        try:
            d0 = dt.date.fromisoformat(a); d1 = dt.date.fromisoformat(b)
            return (d1 - d0).days / 365.25
        except (ValueError, TypeError):
            return None
    durations = []
    for i in range(len(schema) - 1):
        a, b = schema[i], schema[i + 1]
        vals = sorted(v for z in hist
                      if (v := yrs((z.get("dates") or {}).get(a), (z.get("dates") or {}).get(b))) is not None
                      and 0 <= v <= 30)
        if len(vals) >= 10:
            q = lambda p: vals[max(0, min(len(vals) - 1, int(p * len(vals))))]
            durations.append({"pair": f"{a} → {b}", "n": len(vals),
                              "med": round(statistics.median(vals), 1),
                              "q1": round(q(0.25), 1), "q3": round(q(0.75), 1)})

    # ③ 지역 현황
    regions = []
    for r, zones in J["regions"].items():
        core = [z for z in zones if not z.get("small_scale")]
        small = len(zones) - len(core)
        has_hist = any((z.get("dates") or {}).get(schema[0]) for z in core)
        regions.append({"name": r, "total": len(zones), "core": len(core), "small": small,
                        "history": has_hist})

    total = sum(r["total"] for r in regions)
    return {"funnel": funnel, "durations": durations, "regions": regions,
            "total": total, "hist_n": len(hist), "schema": schema}


def operating_block():
    """Ⅲ장 운영 — R-ONE 상업용 임대동향(수지 수집분 재사용). 오피스 중심."""
    C = json.load(open(SUJI / "data" / "rone_commercial.json"))
    vac, rent, yld = C["office_vacancy"], C["office_rent_index"], C["office_yield"]

    # ① 시도별 최신 공실률·소득수익률(연환산)
    latest = []
    for sido, series in vac.items():
        if sido == "전국" or not series:
            continue
        v = series[-1]["value"]
        y = yld.get(sido, [])
        inc_ann = round(y[-1]["income"] * 4, 2) if y else None
        latest.append({"name": sido, "vac": round(v, 1), "inc_ann": inc_ann})
    latest.sort(key=lambda x: x["vac"])

    # ② 추이(주요 시도): 공실률·임대지수
    KEY_SIDOS = ["서울", "경기", "부산", "전국"]
    trend_vac = {s_: [{"yq": p_["yq"], "v": round(p_["value"], 2)} for p_ in vac[s_]] for s_ in KEY_SIDOS if s_ in vac}
    trend_rent = {s_: [{"yq": p_["yq"], "v": round(p_["value"], 2)} for p_ in rent[s_]] for s_ in KEY_SIDOS if s_ in rent}

    seoul_y = yld["서울"][-1]
    nat_v = vac["전국"][-1]
    kpi = {
        "asof": nat_v["yq"],
        "seoul_vac": round(vac["서울"][-1]["value"], 1),
        "nat_vac": round(nat_v["value"], 1),
        "seoul_inc_ann": round(seoul_y["income"] * 4, 1),
        "seoul_total_q": round(seoul_y["total"], 2),
    }
    return {"latest": latest, "trend_vac": trend_vac, "trend_rent": trend_rent, "kpi": kpi}


def linkage_block():
    """Ⅴ장 연결 — 세 시장 단계를 잇는 다리(전부 자체 보유 데이터)."""
    det = json.load(open(D / "cheongyak" / "apt_detail.json"))
    hug = json.load(open(D / "hug_initial_rate.json"))
    tre = json.load(open(D / "treasury10y.json"))["series"]
    C = json.load(open(SUJI / "data" / "rone_commercial.json"))
    P = json.load(open(D / "reits_price.json"))["prices"]
    F = json.load(open(D / "reits_fin.json"))
    R = json.load(open(D / "reits_corp.json"))["reits"]

    def q_of(ym): return f"{ym[:4]}Q{(int(ym[4:6]) - 1) // 3 + 1}"
    def q_idx(q): return int(q[:4]) * 4 + int(q[5]) - 1
    def corr(a, b):
        n = len(a); ma, mb = sum(a) / n, sum(b) / n
        return (sum((x - ma) * (y - mb) for x, y in zip(a, b))
                / (sum((x - ma) ** 2 for x in a) ** .5 * sum((y - mb) ** 2 for y in b) ** .5))

    # A. t 시점에 공고로 알려진 향후 8분기 입주예정 물량 vs 전국 초기분양률
    notices = []
    for d in det:
        dt_, mvn, sup = d.get("RCRIT_PBLANC_DE") or "", d.get("MVN_PREARNGE_YM") or "", d.get("TOT_SUPLY_HSHLDCO") or 0
        if len(dt_) >= 7 and len(mvn) == 6 and sup:
            notices.append((q_idx(q_of(dt_[:4] + dt_[5:7])), q_idx(q_of(mvn)), sup))
    nat = {x["q"]: x["rate"] for x in hug["전국"]}
    qs = sorted(q for q in nat if "2021Q1" <= q <= "2026Q1")
    supply_link = []
    for q in qs:
        t = q_idx(q)
        pipe = sum(s_ for (a_, m_, s_) in notices if a_ <= t and t < m_ <= t + 8)
        supply_link.append({"q": q, "pipe": pipe, "rate": nat[q]})
    r_a = round(corr([x["pipe"] for x in supply_link], [x["rate"] for x in supply_link]), 2)

    # B. 서울 오피스 운영 스프레드 = 소득수익률 연환산 − 국고10y(분기평균)
    t10q = defaultdict(list)
    for x in tre:
        t10q[q_of(x["ym"])].append(x["rate"])
    ops_spread = [{"q": y["yq"], "v": round(y["income"] * 4 - statistics.mean(t10q[y["yq"]]), 2)}
                  for y in C["office_yield"]["서울"] if y["yq"] in t10q]

    # C. 국내 오피스 리츠 합산 P/BV(분기말) vs 서울 오피스 공실률
    REPRT_Q = {"1분기": 1, "반기": 2, "3분기": 3, "사업": 4}
    office = [t for t, m in R.items() if "오피스" in m["asset_type"] and "해외" not in m["asset_type"]]
    def pbv_at(qidx):
        tm = te = 0
        for t in office:
            pr = [p_ for p_ in P.get(t, []) if q_idx(q_of(p_["d"][:6])) <= qidx]
            eqs = [(e["year"] * 4 + REPRT_Q[e["reprt"]] - 1, e["equity"]) for e in F[t]["equity"]]
            eqs = [e for e in eqs if e[0] <= qidx]
            if pr and eqs:
                tm += pr[-1]["mcap"]; te += max(eqs)[1]
        return tm / te if te else None
    vac_s = {x["yq"]: x["value"] for x in C["office_vacancy"]["서울"]}
    cap_link = []
    for q in sorted(vac_s):
        if "2023Q1" <= q <= "2026Q1" and (pb := pbv_at(q_idx(q))):
            cap_link.append({"q": q, "pbv": round(pb, 3), "vac": round(vac_s[q], 1)})
    r_c = round(corr([x["pbv"] for x in cap_link], [x["vac"] for x in cap_link]), 2)

    # 강건성: 차분·전년동기 상관, 금리 통제 부분상관 (리뷰 후속 검증)
    import math
    pipe = [x["pipe"] for x in supply_link]; rate = [x["rate"] for x in supply_link]
    d = lambda a, k: [a[i] - a[i - k] for i in range(k, len(a))]
    r_supply_d1 = round(corr(d(pipe, 1), d(rate, 1)), 2)
    r_supply_yoy = round(corr(d(pipe, 4), d(rate, 4)), 2)
    pbv = [x["pbv"] for x in cap_link]; vac = [x["vac"] for x in cap_link]
    t10s = [statistics.mean(t10q[x["q"]]) for x in cap_link]
    r_pv, r_pt, r_vt = corr(pbv, vac), corr(pbv, t10s), corr(vac, t10s)
    r_cap_partial = round((r_pv - r_pt * r_vt) / math.sqrt((1 - r_pt ** 2) * (1 - r_vt ** 2)), 2)
    r_cap_d1 = round(corr(d(pbv, 1), d(vac, 1)), 2)
    robust = {"supply_d1": r_supply_d1, "supply_yoy": r_supply_yoy,
              "cap_partial": r_cap_partial, "cap_d1": r_cap_d1}

    return {"supply_link": supply_link, "r_supply": r_a,
            "ops_spread": ops_spread,
            "cap_link": cap_link, "r_cap": r_c,
            "office_n": len(office), "robust": robust}


def reits_block():
    P = json.load(open(D / "reits_price.json"))["prices"]
    F = json.load(open(D / "reits_fin.json"))
    R = json.load(open(D / "reits_corp.json"))["reits"]
    tre = json.load(open(D / "treasury10y.json"))["series"]

    items = []
    for t, meta in R.items():
        pr, fin = P.get(t), F.get(t)
        if not pr or not fin or not fin["equity"]:
            continue
        last = pr[-1]
        asof = f"{last['d'][:4]}-{last['d'][4:6]}-{last['d'][6:]}"
        eq = sorted(fin["equity"], key=lambda e: (e["year"], REPRT_ORD[e["reprt"]]))[-1]
        cut = (datetime.date.fromisoformat(asof) - datetime.timedelta(days=370)).isoformat()
        blocks = [b for b in fin["div"] if cut < b["stlm_dt"] <= asof]
        dps = sum(b.get("dps", 0) for b in blocks)
        stale = (datetime.date(2026, 7, 22) - datetime.date.fromisoformat(asof)).days > 30
        tags = []
        if stale:
            tags.append("거래정지")
        if any(b.get("yld", 0) >= 6 for b in blocks):
            tags.append("특별배당")
        ltv = round(eq["liab"] / eq["assets"] * 100, 1) if eq.get("liab") and eq.get("assets") else None
        items.append({
            "ticker": t, "name": meta["name"], "type": meta["asset_type"],
            "close": last["close"], "mcap_eok": round(last["mcap"] / 1e8),
            "pb": round(last["mcap"] / eq["equity"], 2),
            "dy": round(dps / last["close"] * 100, 1) if dps else None,
            "ltv": ltv, "tags": tags, "asof": last["d"],
        })

    normal = [i["dy"] for i in items if i["dy"] and not i["tags"]]
    t10 = tre[-1]["rate"]
    kpi = {"n": len(items), "pb_med": round(statistics.median(i["pb"] for i in items), 2),
           "dy_med": round(statistics.median(normal), 1),
           "t10": t10, "spread": round(statistics.median(normal) - t10, 1),
           "mcap_total_jo": round(sum(i["mcap_eok"] for i in items) / 1e4, 1)}

    # 섹터 집계 (대분류로 접기)
    def sector(tp):
        for key in ("오피스", "리테일", "물류", "주거", "호텔", "해외", "복합"):
            if key in tp:
                return key
        return "기타"
    sec = defaultdict(list)
    for i in items:
        sec[sector(i["type"])].append(i)
    sectors = [{"name": k, "n": len(v),
                "pb_med": round(statistics.median(x["pb"] for x in v), 2),
                "dy_med": round(statistics.median([x["dy"] for x in v if x["dy"]]), 1) if any(x["dy"] for x in v) else None}
               for k, v in sorted(sec.items(), key=lambda kv: -len(kv[1]))]

    return {"items": sorted(items, key=lambda i: i["pb"]),
            "kpi": kpi, "sectors": sectors,
            "treasury": [{"ym": x["ym"], "rate": x["rate"]} for x in tre]}


def main():
    OUT.mkdir(exist_ok=True)
    bundle = {
        "built_at": datetime.date.today().isoformat(),
        "bunyang": bunyang_block(),
        "jeongbi": jeongbi_block(),
        "operating": operating_block(),
        "linkage": linkage_block(),
        "reits": reits_block(),
        "counters": {},
    }
    ch = json.load(open(D / "cheongyak" / "_meta.json"))["counts"]
    bundle["counters"] = {
        "jeongbi_zones": bundle["jeongbi"]["total"],
        "cheongyak_rows": sum(ch.values()),
        "notices": ch["apt_detail"],
        "label_cells": sum(len(v) for v in json.load(open(D / "hug_initial_rate.json")).values()),
        "reits": bundle["reits"]["kpi"]["n"],
        "treasury_months": len(bundle["reits"]["treasury"]),
    }
    (OUT / "site_bundle.json").write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
    print("번들 생성:", {k: v for k, v in bundle["counters"].items()},
          "· 리츠 kpi", bundle["reits"]["kpi"])


if __name__ == "__main__":
    main()
