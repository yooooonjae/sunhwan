// ③ node 계약 테스트 — 빌드 산출 web/index.html 의 해시 라우트·앱바 링크 형식.
//    의존성 없이 `node tests/test_routes.js` 로 실행. 실패 시 비영(非零) 종료.
//    (해시 라우트·앱바 링크는 템플릿 정적 산출이므로 데이터와 무관하게 계약을 이룬다.)

const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const INDEX = path.join(ROOT, "web", "index.html");

if (!fs.existsSync(INDEX)) {
  console.error(`web/index.html 없음 — 먼저 빌드하라: python3 src/build/assemble.py\n  (경로: ${INDEX})`);
  process.exit(1);
}
const html = fs.readFileSync(INDEX, "utf8");

let failures = 0;
function assert(cond, msg) {
  if (cond) console.log("  ok   " + msg);
  else { console.error("  FAIL " + msg); failures++; }
}

// 앱바 존재
assert(/<nav class="appbar">/.test(html), "appbar 존재");

// 해시 라우트 #/ch1 ~ #/ch6 + 앱바 탭 링크 형식: <a href="#/chN" data-view="chN">
for (let n = 1; n <= 6; n++) {
  const re = new RegExp(`<a href="#/ch${n}" data-view="ch${n}">`);
  assert(re.test(html), `앱바 탭 링크 형식 #/ch${n} (data-view="ch${n}")`);
}

// 브랜드 홈 링크
assert(/class="brand" href="#\/home"/.test(html), "브랜드 홈 링크 #/home");

// 앱바 탭 6개(장 Ⅰ~Ⅵ)
const tabCount = (html.match(/data-view="ch[1-6]"/g) || []).length;
assert(tabCount === 6, `앱바 탭 정확히 6개 (실측 ${tabCount})`);

if (failures) {
  console.error(`\n${failures}건 실패 (test_routes)`);
  process.exit(1);
}
console.log(`\n모든 라우트 계약 통과 (test_routes · ${tabCount}개 탭)`);
