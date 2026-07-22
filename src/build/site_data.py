"""사이트 데이터 번들 생성 — out/site_bundle.json (빌드가 JS 로 래핑).

실행: python3 src/build/site_data.py
"""

import datetime
import json
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "data"
OUT = ROOT / "out"

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

    return {"heat": heat, "ladder": ladder, "price_cap": price_cap,
            "pulse": pulse, "latest": {"q": latest_q, "rows": latest},
            "meta": ds["meta"]}


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
        items.append({
            "ticker": t, "name": meta["name"], "type": meta["asset_type"],
            "close": last["close"], "mcap_eok": round(last["mcap"] / 1e8),
            "pb": round(last["mcap"] / eq["equity"], 2),
            "dy": round(dps / last["close"] * 100, 1) if dps else None,
            "tags": tags, "asof": last["d"],
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
        "reits": reits_block(),
        "counters": {},
    }
    ch = json.load(open(D / "cheongyak" / "_meta.json"))["counts"]
    bundle["counters"] = {
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
