# 순환(循環) — 빌드 · 미리보기 · 검증
# 재현: make all  (데이터 번들 → 단일 HTML) · 도움말: make
# 자매 저장소 '수지'(운영·연결 원료)는 SUJI_DIR 로 지정 (.env, 기본 ~/개발).

.DEFAULT_GOAL := help
-include .env
export

PY     ?= python3
PORT   ?= 8791
CHROME ?= /Applications/Google Chrome.app/Contents/MacOS/Google Chrome

.PHONY: help all data manifest build og serve check clean

help:  ## 타깃 목록
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
	  | awk 'BEGIN{FS=":.*?## "}{printf "  \033[1m%-9s\033[0m %s\n",$$1,$$2}'

all: data build  ## 전체 재빌드 (지표 번들 → 단일 HTML)

data:  ## 지표·번들 생성 (out/site_bundle.json + DATA_MANIFEST.json) — 수지 자료 필요(SUJI_DIR)
	$(PY) src/build/site_data.py

manifest:  ## 데이터 상태 명세만 재생성 (DATA_MANIFEST.json)
	$(PY) src/build/manifest.py

build:  ## 단일 HTML 조립 (web/index.html) — noindex 기본
	$(PY) src/build/assemble.py

og:  ## OG 이미지 재생성 (site/static/og.png · 1200×630)
	"$(CHROME)" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=2 \
	  --window-size=1200,630 --screenshot=site/static/og.png "file://$(CURDIR)/src/build/og_card.html"
	sips -z 630 1200 site/static/og.png >/dev/null

serve: build  ## 로컬 미리보기 (기본 http://localhost:8791)
	@echo "→ http://localhost:$(PORT)  (Ctrl+C 종료)"
	@cd web && $(PY) -m http.server $(PORT)

check:  ## 스모크 검증 — Python 구문 + JS 구문 (CI 동등)
	$(PY) -m py_compile src/build/*.py src/collect/*.py src/analysis/*.py
	@for f in site/js/*.js; do node --check "$$f"; done
	@echo "구문 검사 통과"

clean:  ## 산출물 정리 (web/ out/ web.tmp/ __pycache__) — DATA_MANIFEST.json 은 보존(수집일 동결)
	rm -rf web web.tmp out
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
