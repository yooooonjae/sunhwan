"""순환 사이트 빌드 — web/ 산출 (원자 스왑, 수지의 교훈 계승).

실행: python3 src/build/assemble.py [--index]
"""

import datetime
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "site"
STATIC = SITE / "static"      # og.png 등 정적 자산 → web/ 루트로 복사
BUNDLE = ROOT / "out" / "site_bundle.json"
MANIFEST = ROOT / "DATA_MANIFEST.json"


def robots() -> str:
    if "--index" in sys.argv:
        return '<meta name="robots" content="index, follow">'
    return '<meta name="robots" content="noindex, nofollow, noarchive">'


def minify_json(path: Path) -> str:
    s = json.dumps(json.loads(path.read_text()), ensure_ascii=False, separators=(",", ":"))
    return (s.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026"))


def git_short_hash() -> str:
    """빌드 스탬프용 커밋 短해시. BUILD_SHA env 우선(CI 주입 — 12자로 단축),
    없으면 git HEAD, git 부재·비저장소면 'nogit' (모두 읽기 전용)."""
    env = os.environ.get("BUILD_SHA", "").strip()
    if env:
        return env[:12]
    try:
        r = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
                           capture_output=True, text=True, timeout=5)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return "nogit"


def _esc(s) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def load_manifest() -> dict:
    """번들에 동봉된 manifest 우선, 없으면 DATA_MANIFEST.json 폴백."""
    m = json.loads(BUNDLE.read_text()).get("manifest")
    if m:
        return m
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text())
    raise RuntimeError("manifest 없음 — 먼저 python3 src/build/site_data.py (또는 manifest.py) 실행")


def manifest_table(m: dict) -> str:
    """Ⅵ 방법론 '데이터 상태' 표를 서버사이드 렌더 — 관측 종료 vs 수집일 분리."""
    rows = []
    for s in m["sources"]:
        rv = f"{s['rows']:,}" if isinstance(s["rows"], int) else _esc(s["rows"])
        rows.append(
            f"<tr><td>{_esc(s['source'])}</td>"
            f"<td class='num'>{_esc(s['observed_through'] or '—')}</td>"
            f"<td class='num' style='white-space:nowrap'>{_esc(s['collected_at'] or '—')}</td>"
            f"<td class='num'>{rv}</td><td>{_esc(s['coverage'])}</td></tr>")
    return ("<div style=\"overflow-x:auto\"><table>"
            "<thead><tr><th>원천</th><th class='num'>관측 종료</th>"
            "<th class='num'>수집일</th><th class='num'>행</th><th>커버리지</th></tr></thead>"
            "<tbody>" + "".join(rows) + "</tbody></table></div>")


def main():
    tpl = (SITE / "index.template.html").read_text()
    tpl = re.sub(r"\{\{CSS:([\w.\-]+)\}\}", lambda m: (SITE / "css" / m.group(1)).read_text(), tpl)
    tpl = re.sub(r"\{\{JS:([\w.\-]+)\}\}", lambda m: (SITE / "js" / m.group(1)).read_text(), tpl)
    tpl = tpl.replace("{{DATA}}", minify_json(BUNDLE))
    tpl = tpl.replace("{{KOREA}}", minify_json(SITE / "assets_korea.json"))  # 시도 SVG path (외부 요청 없음)
    tpl = tpl.replace("{{BUILT_AT}}", datetime.date.today().isoformat())
    tpl = tpl.replace("{{ROBOTS}}", robots())

    # 빌드 스탬프(푸터) + 데이터 상태 표(Ⅵ) — 커밋 短해시·데이터 컷오프·SSR 표
    mani = load_manifest()
    tpl = tpl.replace("{{COMMIT}}", git_short_hash())
    tpl = tpl.replace("{{DATA_CUTOFF}}", mani.get("cutoff") or "—")
    tpl = tpl.replace("{{MANIFEST_TABLE}}", manifest_table(mani))

    # 조사 분리 검사 — 강조 태그 닫힘과 조사 사이 공백/개행은 실화면 띄어쓰기가 된다 (5차 리뷰 채택)
    import re as _re
    _bad = _re.findall(r"</(?:b|strong|em|i)>[ \t]*\n[ \t]*(?:이|가|을|를|은|는|의|와|과|로|다|이다|한다|된다)[ .,<]", tpl)
    if _bad:
        raise RuntimeError(f"조사 분리 의심 {len(_bad)}건 — 태그와 조사를 붙이거나 조사를 태그 안으로: {_bad[:3]}")
    left = re.findall(r"\{\{[A-Z_:.\w\-]+\}\}", tpl)
    if left:
        raise RuntimeError(f"미치환 플레이스홀더: {left}")

    doc = ("<!DOCTYPE html>\n<html lang=\"ko\">\n<head>\n"
           + tpl[:tpl.index("<nav")] + "\n</head>\n<body>\n"
           + tpl[tpl.index("<nav"):] + "\n</body>\n</html>\n")

    tmp = ROOT / "web.tmp"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir()
    (tmp / "index.html").write_text(doc)
    # 정적 자산(og.png 등) 동봉 — 단일 html 옆에 루트 자산으로 복사 (원자 스왑 전)
    if STATIC.exists():
        for f in STATIC.iterdir():
            if f.is_file():
                shutil.copy(f, tmp / f.name)
    final = ROOT / "web"
    if final.exists():
        shutil.rmtree(final)
    tmp.rename(final)
    n_static = sum(1 for f in STATIC.iterdir() if f.is_file()) if STATIC.exists() else 0
    print(f"빌드: {final/'index.html'} ({(final/'index.html').stat().st_size/1024:.0f} KB, 단일 파일)"
          f" · 커밋 {git_short_hash()} · 컷오프 {mani.get('cutoff')} · 정적 {n_static}개")


if __name__ == "__main__":
    main()
