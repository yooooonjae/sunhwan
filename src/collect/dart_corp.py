"""DART 고유번호(corp_code) ↔ 상장 리츠 24종 매핑 구축.

실행: python3 src/collect/dart_corp.py
산출: data/reits_corp.json — {ticker: {name, corp_code, dart_name}}

DART 의 모든 재무·배당·공시 API 는 종목코드가 아니라 8자리 corp_code 를 쓴다.
corpCode.xml(zip) 전체를 받아 stock_code 로 매칭한다 — 리츠 법인명은
"○○위탁관리부동산투자회사" 식이라 이름 검색은 불안정하다(정찰 함정 #8).
"""

import io
import json
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# 2026-07 상장 리츠 24종 (정찰 보고 기준; 자산유형은 국토부 리츠 API로 추후 정합화)
REITS = {
    "293940": ("신한알파리츠", "오피스"),
    "088260": ("이리츠코크렙", "리테일"),
    "330590": ("롯데리츠", "리테일"),
    "338100": ("NH프라임리츠", "오피스·재간접"),
    "334890": ("이지스밸류리츠", "오피스·리테일"),
    "350520": ("이지스레지던스리츠", "주거"),
    "357250": ("미래에셋맵스리츠", "리테일"),
    "348950": ("제이알글로벌리츠", "해외 오피스"),
    "357120": ("코람코라이프인프라리츠", "리테일·인프라"),
    "365550": ("ESR켄달스퀘어리츠", "물류"),
    "377190": ("디앤디플랫폼리츠", "복합"),
    "395400": ("SK리츠", "복합"),
    "400760": ("NH올원리츠", "복합"),
    "396690": ("미래에셋글로벌리츠", "해외 물류"),
    "404990": ("신한서부티엔디리츠", "호텔·리테일"),
    "417310": ("코람코더원리츠", "오피스"),
    "357430": ("마스턴프리미어리츠", "해외·복합"),
    "432320": ("KB스타리츠", "해외 오피스"),
    "451800": ("한화리츠", "오피스"),
    "448730": ("삼성FN리츠", "오피스"),
    "481850": ("신한글로벌액티브리츠", "해외·재간접"),
    "0030R0": ("대신밸류리츠", "오피스"),
    "145270": ("케이탑리츠", "오피스·자기관리"),
    "140910": ("에이리츠", "개발·자기관리"),
}


def main():
    key = json.load(open(ROOT / "config.json"))["dart_key"]
    url = f"https://opendart.fss.or.kr/api/corpCode.xml?crtfc_key={key}"
    raw = urllib.request.urlopen(url, timeout=60).read()
    zf = zipfile.ZipFile(io.BytesIO(raw))
    xml = zf.read(zf.namelist()[0]).decode("utf-8")
    root = ET.fromstring(xml)

    by_stock = {}
    for el in root.iter("list"):
        sc = (el.findtext("stock_code") or "").strip()
        if sc:
            by_stock[sc] = {
                "corp_code": el.findtext("corp_code", "").strip(),
                "dart_name": el.findtext("corp_name", "").strip(),
            }

    out, missing = {}, []
    for ticker, (name, asset) in REITS.items():
        hit = by_stock.get(ticker)
        if hit:
            out[ticker] = {"name": name, "asset_type": asset, **hit}
        else:
            missing.append(f"{ticker} {name}")

    (ROOT / "data" / "reits_corp.json").write_text(
        json.dumps({"reits": out, "missing": missing,
                    "total_listed_in_dart": len(by_stock)},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"매핑 {len(out)}/{len(REITS)} · 미매칭 {missing or '없음'} · DART 상장법인 {len(by_stock):,}")


if __name__ == "__main__":
    main()
