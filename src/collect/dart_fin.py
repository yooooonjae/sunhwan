"""DART 배당·재무 수집 — 리츠 24종의 배당수익률·P/장부NAV 재료.

실행: python3 src/collect/dart_fin.py
산출: data/reits_fin.json
  {ticker: {"div": [{year, dps, total_div, payout}...],      # 배당 (사업보고서 기준)
            "equity": [{year, reprt, assets, liab, equity}]}}  # 자본총계 (분기·반기·사업)

주의(정찰 함정 반영):
  · 자본총계 = 장부가 — 감정평가 실질 NAV 가 아니다. P/NAV 1차 근사로만 쓰고
    화면·리포트에 반드시 "장부가 기준"을 명기한다. 정밀 NAV 는 국토부 투자보고서(후속).
  · 리츠 결산월이 제각각 — 연도 비교는 bsns_year 가 아니라 보고서 기준일(rcept)로 정렬.
  · status "013" = 해당 보고서 없음(정상 — 상장 전 연도 등).
"""

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = "https://opendart.fss.or.kr/api"
YEARS = range(2020, 2027)
REPRTS = {"11013": "1분기", "11012": "반기", "11014": "3분기", "11011": "사업"}


def _get(op: str, params: dict) -> dict:
    qs = urllib.parse.urlencode(params, safe="%")
    req = urllib.request.Request(f"{BASE}/{op}.json?{qs}",
                                 headers={"User-Agent": "sunhwan/0.1"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def _num(s):
    try:
        return float(str(s).replace(",", ""))
    except (ValueError, TypeError):
        return None


def dividends(corp: str, key: str) -> list[dict]:
    out = []
    for y in YEARS:
        time.sleep(0.1)
        d = _get("alotMatter", {"crtfc_key": key, "corp_code": corp,
                                "bsns_year": y, "reprt_code": "11011"})
        if d.get("status") != "000":
            continue
        # 결산기 블록(stlm_dt) 단위로 당기(thstrm) 배당을 취한다 — 리츠는 반기/분기 결산이라
        # "연 1회 사업보고서" 가정이 깨진다. TTM 합산은 분석 계층에서 stlm_dt 기준으로 한다.
        # 보통주만(종류주 제외), "-" 는 무시. 같은 stlm_dt 중복 행은 마지막 유효값.
        blocks: dict = {}
        for item in d.get("list", []):
            se, knd = item.get("se", ""), item.get("stock_knd", "")
            if knd == "종류주":
                continue
            dt = item.get("stlm_dt", "")
            v = _num(item.get("thstrm"))
            if not dt or v is None:
                continue
            b = blocks.setdefault(dt, {"stlm_dt": dt})
            if "주당 현금배당금" in se:
                b["dps"] = v
            elif "현금배당금총액" in se:
                b["total_div"] = v             # 백만원
            elif "현금배당수익률" in se:
                b["yld"] = v                   # 당시 주가 기준 결산기 수익률(DART)
        out.extend(b for b in blocks.values() if "dps" in b or "total_div" in b)
    # 여러 bsns_year 가 같은 결산기를 중복 반환할 수 있다 — stlm_dt 로 최종 dedupe
    uniq = {b["stlm_dt"]: b for b in out}
    return sorted(uniq.values(), key=lambda b: b["stlm_dt"])


def equity_series(corp: str, key: str) -> list[dict]:
    out = []
    for y in range(2023, 2027):
        for reprt in REPRTS:
            time.sleep(0.1)
            d = _get("fnlttSinglAcnt", {"crtfc_key": key, "corp_code": corp,
                                        "bsns_year": y, "reprt_code": reprt})
            if d.get("status") != "000":
                continue
            row = {"year": y, "reprt": REPRTS[reprt]}
            for item in d.get("list", []):
                if item.get("fs_div") != "OFS":  # 개별(리츠는 대부분 개별 재무)
                    continue
                nm = item.get("account_nm", "")
                if nm == "자산총계":
                    row["assets"] = _num(item.get("thstrm_amount"))
                    row["basis"] = item.get("thstrm_dt", "")
                elif nm == "부채총계":
                    row["liab"] = _num(item.get("thstrm_amount"))
                elif nm == "자본총계":
                    row["equity"] = _num(item.get("thstrm_amount"))
            if row.get("equity") is not None:
                out.append(row)
    return out


def main():
    key = json.load(open(ROOT / "config.json"))["dart_key"]
    reits = json.load(open(ROOT / "data" / "reits_corp.json"))["reits"]
    out = {}
    for ticker, meta in reits.items():
        corp = meta["corp_code"]
        div = dividends(corp, key)
        eq = equity_series(corp, key)
        out[ticker] = {"name": meta["name"], "div": div, "equity": eq}
        print(f"  {meta['name']}: 배당 {len(div)}개년 · 자본 스냅샷 {len(eq)}개")
    (ROOT / "data" / "reits_fin.json").write_text(
        json.dumps(out, ensure_ascii=False), encoding="utf-8")
    n_div = sum(len(v["div"]) for v in out.values())
    n_eq = sum(len(v["equity"]) for v in out.values())
    print(f"완료: 배당 {n_div}행 · 자본 {n_eq}행")


if __name__ == "__main__":
    main()
