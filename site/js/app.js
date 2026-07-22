/* 순환 — 데이터 바인딩·해시 라우터·렌더 */
(function () {
  "use strict";
  const C = window.Charts, fmt = C.fmt;
  const $ = s => document.querySelector(s);
  const B = window.__DATA_SUNHWAN;

  /* ---------- 라우터 ---------- */
  const VIEWS = ["home", "ch1", "ch2", "ch3", "ch4"];
  function route() {
    const m = /^#\/(ch[1-6])$/.exec(location.hash);
    const view = m ? m[1] : "home";
    document.querySelectorAll("[data-view-root]").forEach(el => {
      el.hidden = view === "home" ? false : el.dataset.viewRoot !== view;
    });
    document.querySelectorAll(".tabs a").forEach(a =>
      a.classList.toggle("active", a.dataset.view === view));
    scrollTo(0, 0);
  }
  addEventListener("hashchange", route);

  /* ---------- 리빌 ---------- */
  function reveal() {
    const io = new IntersectionObserver(es => es.forEach(e => {
      if (e.isIntersecting) { e.target.classList.add("on"); io.unobserve(e.target); }
    }), { threshold: .12 });
    document.querySelectorAll("figure.viz, .gate").forEach(el => {
      el.classList.add("reveal"); io.observe(el);
    });
  }

  /* ---------- 홈 계기판 ---------- */
  function counters() {
    if (!$("#counters")) return;   // 홈 재구성: 계기판 행 제거 — 6개 수치는 단계 카드로 흡수
    const c = B.counters;
    const items = [
      [c.jeongbi_zones, "구역", "정비 파이프라인 (3개 시도)"],
      [c.cheongyak_rows, "행", "청약 데이터 수집"],
      [c.notices, "건", "분양 공고 (2020~)"],
      [c.label_cells, "개", "지역·분기 초기분양률 관측값 (12년)"],
      [c.reits, "종", "상장 리츠 전수"],
      [c.treasury_months, "개월", "국고 10년 금리"],
    ];
    $("#counters").innerHTML = items.map(([v, u, k]) =>
      `<div class="gauge"><div class="v">${Number(v).toLocaleString()}<small>${u}</small></div><div class="k">${k}</div></div>`).join("");
  }

  /* ---------- Ⅰ. 공급 ---------- */
  function renderSupply() {
    const J = B.jeongbi;
    if (!J || !$("#j-kpis")) return;
    const hist = J.regions.filter(r => r.history);
    $("#j-kpis").innerHTML = [
      [`${J.total.toLocaleString()}<span class="u">구역</span>`, "관측 파이프라인 (도시정비법 " + J.regions.reduce((a, r) => a + r.core, 0) + " + 소규모 " + J.regions.reduce((a, r) => a + r.small, 0) + ")"],
      [`${J.hist_n.toLocaleString()}<span class="u">구역</span>`, `단계 이력 보유 (${hist.map(r => r.name).join("·")})`],
      [`${(J.durations.find(d => d.pair === "조합설립 → 사업시행") || {}).med || "—"}<span class="u">년</span>`, "조합설립 → 사업시행 중위"],
      [`${J.durations.reduce((a, d) => a + d.med, 0).toFixed(0)}<span class="u">년+</span>`, "예정구역고시 → 준공 중위 합산(단계 합)"],
    ].map(([v, k], i) => `<div class="kpi"><div class="v${i >= 2 ? " gold" : ""}">${v}</div><div class="k">${k}</div></div>`).join("");

    C.hbars($("#j-funnel"), J.funnel.map(f => ({ name: f.stage, value: f.n })),
      { color: "--s2", emph: ["조합설립", "착공", "준공"], fmt: v => v + "구역",
        labelW: 110, width: 1160, rowH: 32, aria: "단계별 기록 보유 구역 수" });

    C.hbars($("#j-dur"), J.durations.map(d => ({ name: d.pair.replace(" → ", "→"), value: d.med })),
      { color: "--s1", emph: J.durations.filter(d => d.med >= 3).map(d => d.pair.replace(" → ", "→")),
        fmt: v => v.toFixed(1) + "년", labelW: 170, width: 1160, rowH: 30, aria: "인접 단계 소요기간 중위" });
    $("#j-dur-cap").textContent = J.durations.map(d =>
      `${d.pair} 중위 ${d.med}년 (IQR ${d.q1}~${d.q3} · n=${d.n})`).join(" · ") +
      " — 완주 구역 기준이라 중단·해제 구역의 시간은 담기지 않는다(생존 편향).";

    $("#j-regions").innerHTML = "<thead><tr><th>시도</th><th class='num'>구역</th><th class='num'>도시정비법</th><th class='num'>소규모(별도 법)</th><th>데이터 성격</th></tr></thead><tbody>" +
      J.regions.map(r => `<tr><td>${r.name}</td><td class="num">${r.total}</td><td class="num">${r.core}</td><td class="num">${r.small}</td><td>${r.history ? "단계 이력" : "현황 스냅샷"}</td></tr>`).join("") + "</tbody>";
  }

  /* ---------- Ⅱ. 분양 ---------- */
  function renderBunyang() {
    const D = B.bunyang;
    // KPI
    $("#b-kpis").innerHTML = [
      [`${B.counters.notices.toLocaleString()}<span class="u">건</span>`, "분양 공고 · 만 6년"],
      [`${(D.meta.coverage.compet_total / D.meta.n * 100).toFixed(0)}%`, "경쟁률 커버리지"],
      [`${D.price_cap.cap.med.toFixed(1)} : 1`, `분상제 적용 경쟁률 중위 (미적용 ${D.price_cap.non.med.toFixed(1)}:1)`],
      [`r = 0.47`, "log 경쟁률 ↔ 다음 분기 초기분양률"],
    ].map(([v, k], i) => `<div class="kpi"><div class="v${i === 3 ? " gold" : ""}">${v}</div><div class="k">${k}</div></div>`).join("");

    // ① 경쟁률 사다리
    const lad = D.ladder.map(x => ({ name: x.name, value: x.value, note: x.value == null ? "표본 없음" : undefined }));
    C.hbars($("#b-ladder"), lad, { color: "--s2", emph: D.ladder.filter(x => (x.value || 0) >= 95).map(x => x.name),
      fmt: v => v + "%", labelW: 120, width: 1160, rowH: 40, aria: "경쟁률 구간별 초기분양률" });
    $("#b-ladder-cap").innerHTML = D.ladder.map(x => `${x.name} n=${x.n}`).join(" · ") +
      " — 금 = 초기분양률 중위 95% 이상. 시도·분기 평균의 상관 관측이며 개별 단지 예측이 아니다.";

    // ①-2 프리미엄 산점 (시도 프록시 — 정직 캡션)
    const PR = D.premium;
    if (PR && $("#b-prem")) {
      C.scatter($("#b-prem"), PR.pts.map(p => ({ ...p, y: Math.min(p.y, 40), label: false })),
        { xName: "분양가/시세", yName: "경쟁률", xRef: 1.0, yRef: 1,
          groups: { "수도권": "--s2", "지방": "--s4" },
          xFmt: v => v.toFixed(1), yFmt: v => v.toFixed(0) + ":1", sizeK: 0.12, height: 480,
          aria: "분양가 프리미엄 대 경쟁률" });
      $("#b-prem-cap").textContent = `공고 ${PR.n}건(시세 매칭 실패·극단 ${PR.dropped}건 제외). ` +
        `log-log 상관 r = ${PR.r_loglog} — 사실상 무상관이다. 시세 분모가 시도 "대표 시군구" 프록시라 입지 차이가 씻겨나간 결과로, ` +
        "가격 적정성은 시군구 단위 시세 매칭(로드맵) 후에야 판정할 수 있다. 결과가 약하다는 것 자체를 기록해 둔다.";
    }
    // ② 히트맵 (기준선 80% 발산)
    C.heatmap($("#b-heat"), {
      xs: D.heat.xs.map(q => q.replace("Q", "'")), ys: D.heat.ys,
      cells: D.heat.cells.map(row => row.map(v => v == null ? null : v - 80)),
    }, { xName: "분기", yName: "시도", labelW: 60, cellH: 26, width: 1160, cellText: true,
         cellFmt: v => Math.round(v + 80), vFmt: v => (v + 80).toFixed(1) + "%", vLabel: "초기분양률",
         legend: "기준선 80% — 금 = 상회(순항), 청 = 하회(고전) · 진할수록 괴리 큼",
         aria: "시도별 분기별 초기분양률" });

    // ③ 전국 추이 + 맥박
    const mkq = arr => arr.map((p, i) => ({ x: i, label: p.q.replace("Q", " Q"), y: p.v }));
    const nat = D.pulse.filter(p => p.rate_nat != null).map(p => ({ q: p.q, v: p.rate_nat }));
    C.line($("#b-rate"), [{ name: "전국", color: "--s1", emph: true, points: mkq(nat) }],
      { aria: "전국 초기분양률", yFmt: v => v.toFixed(0) + "%", width: 560, height: 300, rightPad: 56 });
    C.line($("#b-pulse"), [
      { name: "공고", color: "--s2", emph: true, points: mkq(D.pulse.map(p => ({ q: p.q, v: p.n }))) },
      { name: "무순위", color: "--s3", points: mkq(D.pulse.map(p => ({ q: p.q, v: p.remainder }))) },
    ], { aria: "분기별 공고·무순위 건수", width: 560, height: 300, rightPad: 62 });

    // ④ 최신 분기 시도별
    $("#b-latest-title").textContent = `지금 분양이 가장 잘 소화되는 지역은 — ${D.latest.q.replace("Q", " Q")}`;
    const rows = D.latest.rows.map(r => ({ name: r.name, value: r.value,
      note: r.value == null ? "분양 실적 없음" : undefined }));
    C.hbars($("#b-latest"), rows, { color: "--s2", emph: ["전국"], fmt: v => v.toFixed(0) + "%",
      labelW: 60, width: 1160, rowH: 27, aria: "시도별 초기분양률 최신 분기" });
    $("#b-cap-latest").textContent = "결측 시도는 해당 분기에 기준(30세대 이상 민간분양)을 충족하는 실적이 관측되지 않은 지역이다.";

    // ④-2 지도 코로플레스 — 시점 모드 토글(공통 기준분기 / 지역별 최신). 집계 키는 D.map 단계에서 이미 제외.
    if (window.__KOREA__ && $("#b-koreamap")) {
      const mrows = (D.map || []).reduce((o, m) => (o[m.name] = m, o), {});
      const mc = D.map_common || {};
      const fqq = q => (q ? q.replace("Q", " Q") : "");
      const covPct = mc.coverage != null ? Math.round(mc.coverage * 100) : null;
      const wr = (D.map || []).filter(m => m.rate != null);          // 지역별 최신 채색 대상
      const cw = (D.map || []).filter(m => m.common_rate != null);   // 공통 기준분기 채색 대상
      const unitEl = $("#b-map-unit"), capEl = $("#b-cap-map");
      const setCap = mode => {   // koreaMap 이 모드 렌더 후 호출 — 부제·캡션 갱신
        if (mode === "common") {
          if (unitEl) unitEl.textContent = "% · 공통 기준분기 " + fqq(mc.q) + " · 클릭·탭하여 판독";
          let ext = "";
          if (cw.length) {
            const hi = cw.reduce((a, b) => (b.common_rate > a.common_rate ? b : a), cw[0]);
            const lo = cw.reduce((a, b) => (b.common_rate < a.common_rate ? b : a), cw[0]);
            ext = " (최고 " + hi.name + " " + hi.common_rate.toFixed(1) + "% · 최저 " + lo.name + " " + lo.common_rate.toFixed(1) + "%)";
          }
          capEl.textContent =
            "채색 = 공통 기준분기 " + fqq(mc.q) + " 의 시도별 평균 초기분양률 — 유효 지역 커버리지 80% 이상인 가장 최신 분기다. " +
            "유효 " + (mc.valid || 0) + "/" + (mc.total || 17) + " · 커버리지 " + (covPct == null ? "—" : covPct + "%") + ". " +
            "결측 " + ((mc.total || 17) - (mc.valid || 0)) + "개 지역은 회색(자료 없음)으로 두며 0으로 대체하지 않는다" + ext +
            ". 모든 지역이 같은 분기라 지역 간 직접 비교가 가능하다.";
        } else {
          if (unitEl) unitEl.textContent = "% · 지역별 최신 가용 분기 · 클릭·탭하여 판독";
          if (wr.length) {
            const lo = wr.reduce((a, b) => (b.rate < a.rate ? b : a), wr[0]);
            const hi = wr.reduce((a, b) => (b.rate > a.rate ? b : a), wr[0]);
            const hiNames = wr.filter(m => m.rate >= hi.rate - 1e-9).map(m => m.name);
            capEl.textContent =
              "채색 = 각 시도 최신 가용 분기의 민간아파트 평균 초기분양률(지역 평균 — 개별 단지가 아니다). " +
              "최고 " + hi.rate.toFixed(1) + "%(" + hiNames.join("·") + ")와 최저 " + lo.rate.toFixed(1) +
              "%(" + lo.name + " " + fqq(lo.q) + ")가 각 지역 최신 가용 분기 기준 약 " +
              Math.round(hi.rate / lo.rate) + "배 벌어진다. 공통 기준분기(" + fqq(mc.q) +
              ")보다 2분기 이상 과거인 지역은 사선으로 표시하고, 툴팁에 그 지역 기준 분기를 밝힌다.";
          }
        }
      };
      C.koreaMap($("#b-koreamap"), window.__KOREA__, mrows,
        { aria: "시도별 초기분양률 지도", common: mc, onMode: setCap });
    }
  }

  /* ---------- Ⅲ. 운영 ---------- */
  function renderOperating() {
    const O = B.operating;
    if (!O || !$("#o-kpis")) return;
    const K = O.kpi;
    $("#o-kpis").innerHTML = [
      [K.seoul_vac.toFixed(1) + "%", `서울 오피스 공실률 (${K.asof.replace("Q", " Q")})`],
      [K.nat_vac.toFixed(1) + "%", "전국 오피스 공실률"],
      [K.seoul_inc_ann.toFixed(1) + "%", "서울 소득수익률 연환산 — NOI 수익률 근사"],
      [K.seoul_total_q.toFixed(2) + "%", "서울 분기 투자수익률 (소득+자본)"],
    ].map(([v, k], i) => `<div class="kpi"><div class="v${i === 2 ? " gold" : ""}">${v}</div><div class="k">${k}</div></div>`).join("");

    C.hbars($("#o-vac-latest"), O.latest.map(x => ({ name: x.name, value: x.vac })),
      { color: "--s2", emph: ["서울"], fmt: v => v.toFixed(1) + "%",
        labelW: 60, width: 1160, rowH: 27, aria: "시도별 오피스 공실률" });
    const lo = O.latest[0], hi = O.latest[O.latest.length - 1];
    $("#o-vac-cap").textContent = `${lo.name} ${lo.vac}%에서 ${hi.name} ${hi.vac}%까지 — 오피스 운영 시장의 지역 격차는 주택보다 훨씬 크다. ` +
      "공실이 깊은 지역의 건물은 임대수익 기반 밸류에이션 자체가 성립하기 어렵다.";

    const mkq = arr => arr.map((p, i) => ({ x: i, label: p.yq.replace("Q", " Q"), y: p.v }));
    const COLS = { "서울": "--s1", "경기": "--s2", "부산": "--s3", "전국": "--s5" };
    // 다계열(시도별)은 dict 에서 온 독립 배열 — 라벨 축 일치가 app 단에서 보장되지
    // 않으므로 렌더 직전 alignByLabel 로 라벨 합집합에 재색인(툴팁 인덱스 공유 방어).
    C.line($("#o-vac-trend"), C.alignByLabel(Object.entries(O.trend_vac).map(([n, arr]) => (
      { name: n, color: COLS[n] || "--s4", emph: n === "서울", points: mkq(arr) }))),
      { aria: "공실률 추이", yFmt: v => v.toFixed(0) + "%", width: 560, height: 300, rightPad: 56 });
    C.line($("#o-rent-trend"), C.alignByLabel(Object.entries(O.trend_rent).map(([n, arr]) => (
      { name: n, color: COLS[n] || "--s4", emph: n === "서울", points: mkq(arr) }))),
      { aria: "임대가격지수 추이", width: 560, height: 300, rightPad: 56 });

    const inc = O.latest.filter(x => x.inc_ann != null).sort((a, b) => b.inc_ann - a.inc_ann);
    C.hbars($("#o-income"), inc.map(x => ({ name: x.name, value: x.inc_ann })),
      { color: "--s1", emph: ["서울"], fmt: v => v.toFixed(1) + "%",
        labelW: 60, width: 1160, rowH: 27, aria: "시도별 소득수익률 연환산" });
  }

  /* ---------- Ⅴ. 연결 ---------- */
  function renderLinkage() {
    const L = B.linkage;
    if (!L || !$("#l-spread")) return;   // #l-kpis 제거 — 3개 다리 카드가 정적 마크업으로 대체(수치 직접)

    const mkq = (arr, key) => arr.map((p, i) => ({ x: i, label: p.q.replace("Q", " Q"), y: p[key] }));
    C.line($("#l-pipe"), [{ name: "파이프라인", color: "--s2", emph: true,
      points: L.supply_link.map((p, i) => ({ x: i, label: p.q.replace("Q", " Q"), y: p.pipe / 1e4 })) }],
      { aria: "알려진 입주예정 파이프라인", yFmt: v => v.toFixed(0) + "만", width: 560, height: 290, rightPad: 70 });
    C.line($("#l-rate"), [{ name: "초기분양률", color: "--s1", emph: true, points: mkq(L.supply_link, "rate") }],
      { aria: "전국 초기분양률", yFmt: v => v.toFixed(0) + "%", width: 560, height: 290, rightPad: 74 });
    C.line($("#l-spread"), [{ name: "스프레드", color: "--s3", emph: true, points: mkq(L.ops_spread, "v") }],
      { aria: "서울 오피스 운영 스프레드", yFmt: v => (v >= 0 ? "+" : "") + v.toFixed(1) + "%p", width: 1160, height: 300, rightPad: 78 });
    C.line($("#l-vac"), [{ name: "공실률", color: "--s2", emph: true, points: mkq(L.cap_link, "vac") }],
      { aria: "서울 오피스 공실률", yFmt: v => v.toFixed(0) + "%", width: 560, height: 290, rightPad: 62 });
    C.line($("#l-pbv"), [{ name: "P/BV", color: "--s1", emph: true, points: mkq(L.cap_link, "pbv") }],
      { aria: "오피스 리츠 합산 P/BV", yFmt: v => v.toFixed(2), width: 560, height: 290, rightPad: 60 });

    $("#l-notes").innerHTML =
      "· 다리 ①의 파이프라인은 <b>청약홈 공고 기반(2020-02~)</b>만 집계 — 공고 없이 입주하는 물량은 빠져 있어 절대량이 아니라 방향으로 읽는다.<br>" +
      "· 다리 ③은 분기 " + L.cap_link.length + "개·국내 오피스 리츠 " + L.office_n + "종의 짧은 표본 — 강한 상관(r=" + L.r_cap + ")이지만 두 변수 모두 금리라는 공통 원인의 영향을 받는다.<br>" +
      "· 강건성 검증 결과 — 다리 ①: 분기 차분 r = " + L.robust.supply_d1 + "(소멸), 연간 변화 r = " + L.robust.supply_yoy + "(유지) → 단기 잡음이 아닌 중기 수급 수준의 관계. " +
      "다리 ③: 금리 통제 부분상관 r = " + L.robust.cap_partial + "(유지), 분기 차분 r = " + L.robust.cap_d1 + "(소멸) → 금리만으로 설명되지 않는 수준 관계이나, 표본 13개로 단정할 수 없다.<br>" +
      "· 세 다리 전부 상관 관측이다. 선행·후행(그레인저류) 검정과 시군구 단위 연결은 후속 고도화 대상이다.";
  }

  /* ---------- 긴 순위 막대: 상위5+하위5 기본 + 전체 펼치기 (8차 리뷰 ④) ----------
     · sorted = 정렬된 전체 배열 · build(item) → {name,value,note} · 토글 상태는 root._barsOpen에 영속
     · 재렌더는 항상 root가 보이는 상태(홈/자본 뷰)에서 일어나므로 폭 0 함정 없음 */
  function collapsibleBars(root, sorted, build, opts) {
    if (!root) return;
    const TOP = 5, BOT = 5, canCollapse = sorted.length > TOP + BOT + 1;
    let btn = root.nextElementSibling;
    if (!btn || !btn.classList.contains("bar-toggle")) {
      btn = document.createElement("button");
      btn.type = "button"; btn.className = "bar-toggle";
      root.insertAdjacentElement("afterend", btn);
      btn.addEventListener("click", () => { root._barsOpen = !root._barsOpen; paint(); });
    }
    function paint() {
      const open = !!root._barsOpen;
      let rows;
      if (canCollapse && !open) {
        const omit = sorted.length - TOP - BOT;
        rows = sorted.slice(0, TOP).map(build)
          .concat([{ name: "", value: NaN, note: `… 중위 ${omit}종 생략 …` }])
          .concat(sorted.slice(-BOT).map(build));
      } else {
        rows = sorted.map(build);
      }
      C.hbars(root, rows, opts);
      btn.hidden = !canCollapse;
      btn.textContent = open ? "접기 ▴" : `전체 ${sorted.length}종 보기 ▾`;
    }
    paint();
  }

  /* ---------- Ⅳ. 자본 ---------- */
  function renderReits() {
    const R = B.reits, K = R.kpi;
    $("#r-kpis").innerHTML = [
      [`${K.n}<span class="u">종</span>`, `상장 리츠 · 시총 ${K.mcap_total_jo}조`],
      [`${K.pb_med.toFixed(2)}`, "P/BV 중위 — 장부가의 ⅔"],
      [`${K.dy_med.toFixed(1)}%`, "TTM 배당률 중위 (일회성 배당 제외)"],
      [`+${K.spread.toFixed(1)}<span class="u">%p</span>`, `국고10년(${K.t10.toFixed(2)}%) 대비 스프레드`],
    ].map(([v, k], i) => `<div class="kpi"><div class="v${i === 3 ? " gold" : ""}">${v}</div><div class="k">${k}</div></div>`).join("");

    const tagName = it => it.name + (it.tags.length ? " · " + it.tags.join("·") : "");
    // ⓪ 밸류에이션 사분면 (정상 종목 — 특별배당·거래정지 제외)
    const sector = tp => tp.includes("해외") ? "해외" : tp.includes("오피스") ? "오피스" : tp.includes("리테일") ? "리테일"
      : tp.includes("물류") ? "물류" : tp.includes("주거") ? "주거" : tp.includes("호텔") ? "호텔" : "복합";
    const normal = R.items.filter(it => it.dy != null && !it.tags.length);
    C.scatter($("#r-quad"), normal.map(it => ({
      name: it.name.replace(/리츠$/, ""), x: it.pb, y: +(it.dy - K.t10).toFixed(1),
      size: it.mcap_eok, group: sector(it.type),
      label: it.pb >= 1 || it.pb <= 0.45 || Math.abs(it.dy - K.t10) >= 4,
    })), { xName: "P/BV", yName: "스프레드 %p", xRef: 1.0, yRef: 0,
      groups: { "오피스": "--s1", "리테일": "--s3", "물류": "--s2", "주거": "--s4", "복합": "--s5", "해외": "--ink-3" },
      xFmt: v => v.toFixed(1), yFmt: v => (v >= 0 ? "+" : "") + v.toFixed(0), sizeK: 0.45,
      aria: "리츠 밸류에이션 사분면" });
    $("#r-quad-cap").textContent = `일회성 제외 ${normal.length}종(특별배당 ${R.items.filter(i => i.tags.includes("특별배당")).length}종·거래정지 ${R.items.filter(i => i.tags.includes("거래정지")).length}종 제외). ` +
      "좌상(할인+고스프레드)이 곧 저평가는 아니다 — 할인엔 이유가 있을 수 있다. 자산의 질·부채 구조와 함께 읽어야 한다.";
    // ① P/장부NAV — P/BV 내림차순 상위5+하위5 기본, 전체 24종 펼치기
    const byPb = R.items.slice().sort((a, b) => b.pb - a.pb);
    collapsibleBars($("#r-pnav"), byPb, it => ({ name: tagName(it), value: it.pb }),
      { color: "--s2", emph: byPb.filter(it => it.pb >= 1).map(tagName),
        fmt: v => v.toFixed(2), labelW: 190, width: 1160, rowH: 26, aria: "리츠별 P/BV" });
    // ② TTM 배당률 — 내림차순 상위5+하위5 기본, 전체 24종 펼치기
    const byDy = R.items.slice().sort((a, b) => (b.dy ?? -1) - (a.dy ?? -1));
    collapsibleBars($("#r-dy"), byDy, it => ({ name: tagName(it), value: it.dy,
        note: it.dy == null ? "거래정지 — TTM 미산출" : undefined }),
      { color: "--s1", emph: byDy.filter(it => it.tags.includes("특별배당")).map(tagName),
        fmt: v => v.toFixed(1) + "%", labelW: 190, width: 1160, rowH: 26, aria: "리츠별 TTM 배당률" });
    $("#r-dy-cap").textContent = "금 강조 = 특별배당(자산 매각·청산성 분배) 포함 — 지속 가능한 수익률이 아니다. " +
      "일회성 배당 제외 중위 " + K.dy_med.toFixed(1) + "%가 이 시장의 기조적 수익률이다.";
    // ③ 국고10년
    C.line($("#r-t10"), [{ name: "국고10y", color: "--s2", emph: true,
      points: R.treasury.map((p, i) => ({ x: i, label: fmt.ym(p.ym), y: p.rate })) }],
      { aria: "국고채 10년 월평균", yFmt: v => v.toFixed(1) + "%", width: 560, height: 300, rightPad: 64 });
    $("#r-t10-cap").textContent = `최신 ${K.t10.toFixed(2)}% — 일회성 제외 리츠 배당 중위와의 간격 +${K.spread.toFixed(1)}%p가 리츠에 요구되는 위험 보상이다.`;
    // ③-2 장부상 부채비율
    const byLtv = R.items.filter(it => it.ltv != null).sort((a, b) => b.ltv - a.ltv);
    C.hbars($("#r-ltv"), byLtv.map(it => ({ name: it.name, value: it.ltv })),
      { color: "--s3", emph: byLtv.filter(it => it.ltv >= 60).map(it => it.name),
        fmt: v => v.toFixed(0) + "%", labelW: 170, width: 560, rowH: 24, aria: "리츠별 자산 대비 부채" });
    // ④ 섹터 표
    $("#r-sector").innerHTML = "<thead><tr><th>섹터</th><th class='num'>종목</th><th class='num'>P/BV</th><th class='num'>TTM 배당</th><th class='num'>부채/자산</th></tr></thead><tbody>" +
      R.sectors.map(s => { const ls = R.items.filter(i => i.ltv != null && sector(i.type) === s.name).map(i => i.ltv).sort((a, b) => a - b); const lm = ls.length ? ls[Math.floor(ls.length / 2)].toFixed(0) + "%" : "―"; return `<tr><td>${s.name}</td><td class="num">${s.n}</td><td class="num">${s.pb_med.toFixed(2)}</td><td class="num">${s.dy_med != null ? s.dy_med.toFixed(1) + "%" : "―"}</td><td class="num">${lm}</td></tr>`; }).join("") +
      "</tbody>";
  }

  /* ---------- 테마 ---------- */
  function initTheme() {
    const btn = document.querySelector(".theme-toggle");
    const icon = btn.querySelector(".ti");
    const sync = () => {
      const light = document.documentElement.dataset.theme !== "dark";
      btn.setAttribute("aria-pressed", String(light));
      if (icon) icon.textContent = light ? "☀" : "☾";   // 현재 테마 표시 (8차 리뷰 ⑤)
    };
    btn.addEventListener("click", () => {
      const r = document.documentElement;
      if (r.dataset.theme === "dark") delete r.dataset.theme; else r.dataset.theme = "dark";
      sync(); renderAll();
    });
    sync();
  }

  /* ---------- 모바일 목차 오버레이 (8차 리뷰 ②) ---------- */
  function initNav() {
    const ov = document.getElementById("nav-overlay");
    const openBtn = document.querySelector(".nav-menu-btn");
    if (!ov || !openBtn) return;
    const closeBtn = ov.querySelector(".nav-ov-close");
    const open = () => { ov.hidden = false; openBtn.setAttribute("aria-expanded", "true"); document.body.style.overflow = "hidden"; };
    const close = () => { ov.hidden = true; openBtn.setAttribute("aria-expanded", "false"); document.body.style.overflow = ""; };
    openBtn.addEventListener("click", open);
    if (closeBtn) closeBtn.addEventListener("click", close);
    ov.querySelectorAll("a").forEach(a => a.addEventListener("click", close)); // 링크 탭 → 닫고 라우팅
    addEventListener("keydown", e => { if (e.key === "Escape" && !ov.hidden) close(); });
  }

  /* ---------- 홈: 지금 시장 요약 ---------- */
  function pulseNow() {
    const el2 = $("#pulse-now");
    if (!el2) return;
    const D = B.bunyang, K = B.reits.kpi;
    const natLatest = D.latest.rows.find(r => r.name === "전국");
    el2.innerHTML = [
      ["공급", B.jeongbi.total.toLocaleString() + '<span class="u">구역</span>', `정비 파이프라인 3개 시도 — 조합설립→사업시행 중위 ${(B.jeongbi.durations.find(d => d.pair === "조합설립 → 사업시행") || {}).med || "—"}년`, true],
      ["분양", (natLatest && natLatest.value != null ? natLatest.value.toFixed(0) + "%" : "―"),
       `전국 초기분양률 ${D.latest.q.replace("Q", " Q")} — 기준선 80% ${natLatest && natLatest.value >= 80 ? "상회" : "하회"}`, true],
      ["운영", B.operating.kpi.seoul_vac.toFixed(1) + "%", `서울 오피스 공실률 ${B.operating.kpi.asof.replace("Q", " Q")} — 전국 ${B.operating.kpi.nat_vac.toFixed(1)}%`, true],
      ["자본", K.pb_med.toFixed(2), `리츠 P/BV 중위 — 장부가 대비 ${Math.round((1 - K.pb_med) * 100)}% 할인 · 스프레드 +${K.spread.toFixed(1)}%p`, true],
    ].map(([t, v, k, on]) => `<div class="kpi"><div class="k" style="margin:0 0 4px">${t} — 지금</div><div class="v${on ? " gold" : ""}">${v}</div><div class="k">${k}</div></div>`).join("");
  }

  function renderAll() { counters(); pulseNow(); renderSupply(); renderBunyang(); renderOperating(); renderReits(); renderLinkage(); }

  route();
  renderAll();
  reveal();
  initTheme();
  initNav();
})();
