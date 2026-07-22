"""리츠 24종 일별 주가·시총 백필 — 금융위 주식시세정보 API.

실행: python3 src/collect/reits_price.py
산출: data/reits_price.json  {ticker: [{d, close, mcap, shares}...]} (날짜 오름차순)

pykrx 붕괴(2025-12 KRX 로그인화) 이후의 표준 경로. T+1 13시 갱신(비실시간).
"""

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
URL = "https://apis.data.go.kr/1160100/service/GetStockSecuritiesInfoService/getStockPriceInfo"
BEGIN = "20200101"   # 청약홈 백필과 시계 정렬
PER = 3000           # 종목당 1콜 목표(6.5년 ≈ 1,600행)


def fetch_ticker(ticker: str, key: str) -> list[dict]:
    rows, page = [], 1
    while True:
        qs = urllib.parse.urlencode({
            "serviceKey": key, "resultType": "json",
            "numOfRows": PER, "pageNo": page,
            "likeSrtnCd": ticker, "beginBasDt": BEGIN,
        }, safe="%")
        req = urllib.request.Request(f"{URL}?{qs}", headers={"User-Agent": "sunhwan/0.1"})
        with urllib.request.urlopen(req, timeout=60) as r:
            body = json.loads(r.read())["response"]["body"]
        items = body.get("items") or {}
        batch = items.get("item") or []
        if isinstance(batch, dict):
            batch = [batch]
        # likeSrtnCd 는 전방일치 — 정확히 이 종목만 남긴다
        rows.extend(b for b in batch if b.get("srtnCd") == ticker)
        if page * PER >= int(body.get("totalCount", 0)) or not batch:
            break
        page += 1
    rows.sort(key=lambda b: b["basDt"])
    return [{"d": b["basDt"], "close": int(b["clpr"]),
             "mcap": int(b["mrktTotAmt"]), "shares": int(b["lstgStCnt"])} for b in rows]


def main():
    cfg = json.load(open(ROOT / "config.json"))
    reits = json.load(open(ROOT / "data" / "reits_corp.json"))["reits"]
    out, missing = {}, []
    for ticker, meta in reits.items():
        time.sleep(0.3)
        try:
            series = fetch_ticker(ticker, cfg["service_key"])
        except Exception as e:
            series = []
            print(f"  {ticker} {meta['name']}: 오류 {str(e)[:60]}")
        if series:
            out[ticker] = series
            print(f"  {ticker} {meta['name']}: {len(series):,}일 ({series[0]['d']}~{series[-1]['d']})")
        else:
            missing.append(f"{ticker} {meta['name']}")
    (ROOT / "data" / "reits_price.json").write_text(
        json.dumps({"prices": out, "missing": missing, "begin": BEGIN},
                   ensure_ascii=False), encoding="utf-8")
    print(f"완료: {len(out)}/{len(reits)}종 · 미수집 {missing or '없음'}")


if __name__ == "__main__":
    main()
