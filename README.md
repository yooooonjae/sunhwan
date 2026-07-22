# 순환(循環) — 부동산 자본의 생애주기 관측

**공급 → 분양 → 운영 → 자본.** 정비구역 1,061곳의 단계 이력에서 상장 리츠 24종의
P/BV까지, 부동산이 지어지고 팔리고 운영되다 자본시장에 편입되는 생애주기를
공공 데이터만으로 관측한다. 단계 사이의 연결(공실률↔리츠 P/BV r=−0.73 등)을
상관·부분상관·차분으로 검증하고, 불리한 결과까지 화면에 공개한다.

**라이브**: https://sunhwan.pages.dev

## 구성

```
src/collect/   수집 — 청약홈·HUG(KOSIS)·DART·금융위 시세·ECOS·시도별 정비사업 (원본 전량 캐시)
src/build/     site_data.py(지표 계산) · manifest.py(데이터 상태 명세) → assemble.py(단일 HTML 조립)
site/          템플릿·CSS 토큰·인라인 SVG 차트 엔진(charts.js) · static/(og.png 등 루트 자산)
data/          수집 원자료 (config.json 의 API 키는 커밋하지 않는다)
DATA_MANIFEST.json  원천별 관측월·수집일·행수·커버리지 (빌드 산출 · Ⅵ 방법론 표의 근거)
```

## 실행

```bash
make            # 타깃 목록
make all        # 전체 재빌드 — 지표 번들 → 단일 HTML (web/index.html)
make data       # 지표·번들 생성 (out/site_bundle.json + DATA_MANIFEST.json)
make manifest   # 데이터 상태 명세만 재생성
make build      # 단일 HTML 조립 (noindex 기본)
make serve      # 로컬 미리보기 (http://localhost:8791)
make og         # OG 이미지 재생성 (site/static/og.png · 1200×630)
make check      # 스모크 검증 — Python·JS 구문 (CI 동등)
```

`make` 없이도 동일하다 — `python3 src/build/site_data.py && python3 src/build/assemble.py` → `web/index.html`
(단일 파일 · 외부 네트워크 요청 없음 · noindex 기본, 검색 개방은 `assemble.py --index`).

운영(Ⅲ)·프리미엄 산점(Ⅱ)·연결(Ⅴ)은 자매 저장소 [수지](https://yoonjae.pages.dev)의 산출물을 참조한다.
기본 경로는 `~/개발`이며, 다른 위치에 두었다면 `.env`(→ `.env.example` 참고)의 `SUJI_DIR` 로 지정한다.

## 원칙

- **재현 가능**: 모든 수치는 수집 원본 캐시에서 재산출된다. 절대경로를 코드에 박지 않고(`SUJI_DIR`),
  빌드 산출물에 스탬프(커밋 短해시·데이터 컷오프·빌드일)를 남겨 어떤 상태의 산출인지 추적한다.
- **관측월 ≠ 수집일**: `manifest.py` 가 원천별 관측 종료 시점과 수집일을 분리해 `DATA_MANIFEST.json` 으로
  남기고, Ⅵ 방법론의 "데이터 상태" 표가 이를 그대로 노출한다. 자료의 지연을 숨기지 않는다.
- **증거 등급 표기**: 화면의 주장을 관측·통계적 관계·해석·미검증 4단으로 구분하고, Ⅱ·Ⅴ의 대표 지점에
  배지로 표시한다(범례는 Ⅵ 방법론). 상관은 상관으로, 해석은 해석으로 명시한다 — 상관 ≠ 인과.
- **오류 삼킴 금지**: 미치환 플레이스홀더·조사 분리 등은 빌드 단계에서 예외로 중단하고, 원자 스왑으로
  직전 정상 산출물을 보존한다.

## 연구 시리즈

[수지(收支)](https://yoonjae.pages.dev) — 개별 사업의 손익 ·
**순환(循環)** — 시장과 자본의 구조 ·
[시차(時差)](https://sicha.pages.dev) — 신호의 전달시간
