"""데이터 상태 명세 — DATA_MANIFEST.json 생성.

원천별로 {source, observed_through, collected_at, rows, coverage} 를 계산해
저장소 루트 DATA_MANIFEST.json 으로 남긴다. 방법론(Ⅵ)의 "데이터 상태" 표와
푸터 빌드 스탬프(데이터 컷오프)가 이 산출을 근거로 삼는다.

핵심 구분:
  · observed_through — 관측월(자료가 다루는 마지막 시점). 자료 내용에서 도출되어 재현 가능.
  · collected_at     — 수집일(원본 캐시가 마지막으로 기록된 날짜, 로컬 파일 기준).

collected_at 은 파일 mtime 에서 채우되, 이미 DATA_MANIFEST.json 에 기록돼 있으면
그 값을 보존한다(클론·재빌드로 파일 시각이 바뀌어도 확정 수집일이 흔들리지 않도록).
`--refresh` 플래그를 주면 기존 값을 무시하고 mtime 에서 다시 채운다.

실행: python3 src/build/manifest.py [--refresh]
"""

import datetime
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "data"
MANIFEST = ROOT / "DATA_MANIFEST.json"
# 운영(Ⅲ)·프리미엄 산점 분모는 부속 저장소 '수지' 산출을 재사용 (기본 ~/개발, SUJI_DIR 로 재정의).
SUJI = Path(os.path.expanduser(os.environ.get("SUJI_DIR", str(Path.home() / "개발"))))


def _mtime(path: Path) -> str | None:
    if not path.exists():
        return None
    return datetime.date.fromtimestamp(path.stat().st_mtime).isoformat()


def _pct(part, whole) -> int:
    return round(part / whole * 100) if whole else 0


def _q_end(q: str) -> str:
    """'2026Q1' → 분기말 ISO 날짜(커버리지 비교용)."""
    y, qq = int(q[:4]), int(q[5])
    m, d = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}[qq]
    return f"{y:04d}-{m:02d}-{d:02d}"


def _month_end(ym: str) -> str:
    """'202606' 또는 '2026-06' → 월말 ISO 날짜."""
    ym = ym.replace("-", "")
    y, m = int(ym[:4]), int(ym[4:6])
    nxt = datetime.date(y + (m == 12), (m % 12) + 1, 1)
    return (nxt - datetime.timedelta(days=1)).isoformat()


def _obs_date(observed_through: str, collected_at: str | None) -> str | None:
    """표시용 observed_through 문자열을 커버리지 비교용 ISO 날짜로 정규화."""
    s = (observed_through or "").strip()
    try:
        if len(s) >= 6 and s[4] == "Q":
            return _q_end(s)
        if len(s) == 10 and s[4] == "-" and s[7] == "-":
            return s
        if len(s) == 7 and s[4] == "-":
            return _month_end(s)
    except (ValueError, KeyError, IndexError):
        pass
    return collected_at  # 스냅샷 등 관측 시점이 없는 원천은 수집일을 컷오프에 반영


def _sources() -> list[dict]:
    S: list[dict] = []

    # ① 청약홈 (분양공고·경쟁률·가점·무순위)
    meta = json.load(open(D / "cheongyak" / "_meta.json"))["counts"]
    bun = json.load(open(D / "bunyang_dataset.json"))
    bmeta, brows = bun["meta"], bun["rows"]
    last_notice = max((r["date"] for r in brows if r.get("date")), default=None)
    S.append({
        "key": "cheongyak",
        "source": "한국부동산원 청약홈 (분양공고·경쟁률·가점·무순위)",
        "observed_through": last_notice,
        "collected_at": _mtime(D / "cheongyak" / "_meta.json"),
        "rows": sum(meta.values()),
        "coverage": f"경쟁률 {_pct(bmeta['coverage']['compet_total'], bmeta['n'])}% · "
                    f"분양가 {_pct(bmeta['coverage']['price_m2'], bmeta['n'])}% (공고 {bmeta['n']:,}건 기준)",
    })

    # ② HUG × KOSIS 초기분양률
    hug = json.load(open(D / "hug_initial_rate.json"))
    hug_qs = sorted({x["q"] for arr in hug.values() for x in arr})
    hug_cells = sum(len(v) for v in hug.values())
    S.append({
        "key": "hug_rate",
        "source": "HUG 민간아파트 평균 초기분양률 (KOSIS)",
        "observed_through": hug_qs[-1] if hug_qs else None,
        "collected_at": _mtime(D / "hug_initial_rate.json"),
        "rows": hug_cells,
        "coverage": f"23개 지역 · 관측 있는 분기만 ({hug_qs[0]}~)" if hug_qs else "—",
    })

    # ③ DART 리츠 재무 (재무상태·배당)
    fin = json.load(open(D / "reits_fin.json"))
    corp = json.load(open(D / "reits_corp.json"))["reits"]
    eq_n = sum(len(v.get("equity", [])) for v in fin.values())
    div_n = sum(len(v.get("div", [])) for v in fin.values())
    ltv_ok = sum(1 for v in fin.values()
                 if v.get("equity") and v["equity"][-1].get("liab") and v["equity"][-1].get("assets"))
    last_stlm = max((b["stlm_dt"] for v in fin.values() for b in v.get("div", []) if b.get("stlm_dt")),
                    default=None)
    S.append({
        "key": "reits_fin",
        "source": "DART OpenAPI 리츠 재무 (재무상태·배당)",
        "observed_through": last_stlm,
        "collected_at": _mtime(D / "reits_fin.json"),
        "rows": eq_n + div_n,
        "coverage": f"재무 {len(fin)}/{len(corp)} · 배당 {div_n}결산기 · 부채비율 {ltv_ok}/{len(corp)}",
    })

    # ④ 금융위 주식시세 (리츠 일별 종가·시총)
    price = json.load(open(D / "reits_price.json"))["prices"]
    price_rows = sum(len(v) for v in price.values())
    last_px = max((p["d"] for v in price.values() for p in v), default=None)
    last_px_iso = f"{last_px[:4]}-{last_px[4:6]}-{last_px[6:]}" if last_px else None
    S.append({
        "key": "reits_price",
        "source": "금융위 주식시세 (리츠 일별 종가·시가총액)",
        "observed_through": last_px_iso,
        "collected_at": _mtime(D / "reits_price.json"),
        "rows": price_rows,
        "coverage": f"상장 {len(price)}/{len(corp)}종 · 상장일~",
    })

    # ⑤ 한국은행 ECOS 국고채 10년
    tre = json.load(open(D / "treasury10y.json"))["series"]
    last_ym = tre[-1]["ym"] if tre else None
    S.append({
        "key": "treasury10y",
        "source": "한국은행 ECOS 국고채 10년 (월평균)",
        "observed_through": f"{last_ym[:4]}-{last_ym[4:6]}" if last_ym else None,
        "collected_at": _mtime(D / "treasury10y.json"),
        "rows": len(tre),
        "coverage": f"{len(tre)}개월 연속" + (f" ({tre[0]['ym'][:4]}-{tre[0]['ym'][4:6]}~)" if tre else ""),
    })

    # ⑥ 시도별 정비사업 (대구·경기·부산) — 이력 스냅샷 혼합
    jb = json.load(open(D / "jeongbi_phase1.json"))
    jbm = jb["meta"]
    total = sum(len(z) for z in jb["regions"].values())
    S.append({
        "key": "jeongbi",
        "source": "시도별 정비사업 (대구·경기·부산)",
        "observed_through": "현황 스냅샷 (관측 이력 지역별 상이)",
        "collected_at": jbm.get("generated") or _mtime(D / "jeongbi_phase1.json"),
        "rows": total,
        "coverage": " · ".join(f"{k} {v}" for k, v in jbm.get("counts", {}).items())
                    + " (대구·경기 이력 / 부산 스냅샷)",
    })

    # ⑦ R-ONE 상업용 임대동향 (운영 Ⅲ — 수지 재사용)
    rone_path = SUJI / "data" / "rone_commercial.json"
    if rone_path.exists():
        rone = json.load(open(rone_path))
        vac = rone.get("office_vacancy", {})
        yqs = sorted({p["yq"] for arr in vac.values() for p in arr})
        rows = sum(len(v) for v in vac.values())
        S.append({
            "key": "operating",
            "source": "한국부동산원 상업용 임대동향 R-ONE (수지 재사용)",
            "observed_through": yqs[-1] if yqs else None,
            "collected_at": _mtime(rone_path),
            "rows": rows,
            "coverage": f"오피스 공실·임대·수익률 {len([s for s in vac if s != '전국'])}개 시도"
                        + (f" ({yqs[0]}~)" if yqs else ""),
        })

    # ⑧ RTMS 실거래 (Ⅱ 프리미엄 산점 시세 분모 프록시 — 수지 재사용)
    rtms_path = SUJI / "data" / "rtms.json"
    if rtms_path.exists():
        rtms = json.load(open(rtms_path))["trades"]
        yms, rows = [], 0
        for sido, gus in rtms.items():
            for gu, pts in gus.items():
                rows += len(pts)
                yms += [p["ym"] for p in pts if p.get("ym")]
        last_rtms = max(yms) if yms else None
        S.append({
            "key": "rtms",
            "source": "국토부 실거래가 RTMS (분양가 프리미엄 분모 프록시 · 수지 재사용)",
            "observed_through": f"{last_rtms[:4]}-{last_rtms[4:6]}" if last_rtms else None,
            "collected_at": _mtime(rtms_path),
            "rows": rows,
            "coverage": f"{len(rtms)}개 시도 대표 시군구 프록시 (단지 시세 아님)",
        })

    return S


def generate(write: bool = True, refresh: bool = False) -> dict:
    """DATA_MANIFEST.json 을 계산해 dict 로 반환하고(옵션) 파일로 기록."""
    prior = {}
    if MANIFEST.exists() and not refresh:
        try:
            for s in json.load(open(MANIFEST)).get("sources", []):
                if s.get("key"):
                    prior[s["key"]] = s.get("collected_at")
        except (ValueError, KeyError):
            prior = {}

    sources = _sources()
    # collected_at 동결 — 이미 기록된 값이 있으면 보존(재빌드 안정성)
    for s in sources:
        frozen = prior.get(s["key"])
        if frozen:
            s["collected_at"] = frozen

    # 데이터 컷오프 = 자료가 어디까지 닿아 있는가.
    # 일 단위(정확 날짜) 관측이 있으면 그 중 최신을 쓴다 — 월·분기 집계의 '월말' 합성으로
    # 컷오프가 미래로 부풀지 않게. 정확 날짜가 없을 때만 정규화(월말·분기말)로 폴백한다.
    def _is_iso_day(s):
        return isinstance(s, str) and len(s) == 10 and s[4] == "-" and s[7] == "-"
    precise = [s["observed_through"] for s in sources if _is_iso_day(s["observed_through"])]
    if precise:
        cutoff = max(precise)
    else:
        obs_dates = [d for d in (_obs_date(s["observed_through"], s["collected_at"]) for s in sources) if d]
        cutoff = max(obs_dates) if obs_dates else None

    manifest = {
        "generated": datetime.date.today().isoformat(),
        "cutoff": cutoff,
        "note": "observed_through=관측 종료(자료 기준) · collected_at=수집일(원본 캐시 기준). "
                "cutoff=관측 종료 중 최신.",
        "sources": sources,
    }
    if write:
        MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return manifest


def main():
    m = generate(write=True, refresh="--refresh" in sys.argv)
    print(f"DATA_MANIFEST.json — {len(m['sources'])}개 원천 · 컷오프 {m['cutoff']}")
    for s in m["sources"]:
        print(f"  · {s['source']}\n      관측 {s['observed_through']} · 수집 {s['collected_at']} "
              f"· {s['rows']:,}행 · {s['coverage']}")


if __name__ == "__main__":
    main()
