# 순환(循環) — 부동산 자본의 생애주기 관측

**공급 → 분양 → 운영 → 자본.** 정비구역 1,061곳의 단계 이력에서 상장 리츠 24종의
P/BV까지, 부동산이 지어지고 팔리고 운영되다 자본시장에 편입되는 생애주기를
공공 데이터만으로 관측한다. 단계 사이의 연결(공실률↔리츠 P/BV r=−0.73 등)을
상관·부분상관·차분으로 검증하고, 불리한 결과까지 화면에 공개한다.

**라이브**: https://sunhwan.pages.dev

## 구조

```
src/collect/   수집 — 청약홈·KOSIS·DART·금융위 시세·ECOS·시도별 정비사업
src/build/     site_data.py(지표 계산) → assemble.py(단일 HTML 조립)
site/          템플릿·CSS 토큰·인라인 SVG 차트 엔진(charts.js)
data/          수집 원자료 (config.json의 API 키는 커밋하지 않는다)
```

재현: `python3 src/build/site_data.py && python3 src/build/assemble.py` → `web/index.html`
(단일 파일 · 외부 네트워크 요청 없음 · noindex 기본)

## 연구 시리즈

[수지(收支)](https://yoonjae.pages.dev) — 개별 사업의 손익 ·
**순환(循環)** — 시장과 자본의 구조 ·
[시차(時差)](https://sicha.pages.dev) — 신호의 전달시간
