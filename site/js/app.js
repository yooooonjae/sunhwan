/* 순환 — 데이터 바인딩·해시 라우터·렌더 */
(function () {
  "use strict";
  const C = window.Charts, fmt = C.fmt;
  const $ = s => document.querySelector(s);
  const B = window.__DATA_SUNHWAN;

  /* ---------- 라우터 ---------- */
  const VIEWS = ["home", "ch1", "ch2", "ch3", "ch4"];
  function route() {
    const m = /^#\/(ch[1-4])$/.exec(location.hash);
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
    const c = B.counters;
    const items = [
      [c.cheongyak_rows, "행", "청약 데이터 수집"],
      [c.notices, "건", "분양 공고 (2020~)"],
      [c.label_cells, "셀", "초기분양률 라벨 (12년)"],
      [c.reits, "종", "상장 리츠 전수"],
      [c.treasury_months, "개월", "국고 10년 금리"],
    ];
    $("#counters").innerHTML = items.map(([v, u, k]) =>
      `<div class="gauge"><div class="v">${Number(v).toLocaleString()}<small>${u}</small></div><div class="k">${k}</div></div>`).join("");
  }

  /* ---------- Ⅱ. 분양 ---------- */
  function renderBunyang() {
    const D = B.bunyang;
    // KPI
    $("#b-kpis").innerHTML = [
      [`${B.counters.notices.toLocaleString()}건`, "분양 공고 · 만 6년"],
      [`${(D.meta.coverage.compet_total / D.meta.n * 100).toFixed(0)}%`, "경쟁률 커버리지"],
      [`${D.price_cap.cap.med.toFixed(1)} : 1`, `분상제 적용 경쟁률 중위 (미적용 ${D.price_cap.non.med.toFixed(1)}:1)`],
      [`r = 0.47`, "log 경쟁률 ↔ 다음 분기 초기분양률"],
    ].map(([v, k], i) => `<div class="kpi"><div class="v${i === 3 ? " gold" : ""}">${v}</div><div class="k">${k}</div></div>`).join("");

    // ① 경쟁률 사다리
    const lad = D.ladder.map(x => ({ name: x.name, value: x.value, note: x.value == null ? "표본 없음" : undefined }));
    C.hbars($("#b-ladder"), lad, { color: "--s2", emph: D.ladder.filter(x => (x.value || 0) >= 95).map(x => x.name),
      fmt: v => v + "%", labelW: 120, width: 1160, rowH: 40, aria: "경쟁률 구간별 초기분양률" });
    $("#b-ladder-cap").innerHTML = D.ladder.map(x => `${x.name} n=${x.n}`).join(" · ") +
      " — 금 = 사실상 완판(95%+). 경쟁이 확인된 시장은 계약도 이뤄진다.";

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
    $("#b-latest-title").textContent = `시도별 초기분양률 — ${D.latest.q.replace("Q", " Q")}`;
    const rows = D.latest.rows.map(r => ({ name: r.name, value: r.value,
      note: r.value == null ? "분양 실적 없음" : undefined }));
    C.hbars($("#b-latest"), rows, { color: "--s2", emph: ["전국"], fmt: v => v.toFixed(0) + "%",
      labelW: 60, width: 1160, rowH: 27, aria: "시도별 초기분양률 최신 분기" });
    $("#b-cap-latest").textContent = "결측 시도는 해당 분기 30세대 이상 민간분양 실적이 없는 곳 — 공급 자체가 멈춘 시장이다.";
  }

  /* ---------- Ⅲ. 자본 ---------- */
  function renderReits() {
    const R = B.reits, K = R.kpi;
    $("#r-kpis").innerHTML = [
      [`${K.n}종`, `상장 리츠 · 시총 ${K.mcap_total_jo}조`],
      [`${K.pb_med.toFixed(2)}`, "P/장부NAV 중위 — 장부가의 ⅔"],
      [`${K.dy_med.toFixed(1)}%`, "TTM 배당률 중위 (정상 종목)"],
      [`+${K.spread.toFixed(1)}%p`, `국고10년(${K.t10.toFixed(2)}%) 대비 스프레드`],
    ].map(([v, k], i) => `<div class="kpi"><div class="v${i === 3 ? " gold" : ""}">${v}</div><div class="k">${k}</div></div>`).join("");

    const tagName = it => it.name + (it.tags.length ? " · " + it.tags.join("·") : "");
    // ① P/장부NAV
    C.hbars($("#r-pnav"), R.items.map(it => ({ name: tagName(it), value: it.pb })),
      { color: "--s2", emph: R.items.filter(it => it.pb >= 1).map(tagName),
        fmt: v => v.toFixed(2), labelW: 190, width: 1160, rowH: 26, aria: "리츠별 P/장부NAV" });
    // ② TTM 배당률
    const byDy = R.items.slice().sort((a, b) => (b.dy ?? -1) - (a.dy ?? -1));
    C.hbars($("#r-dy"), byDy.map(it => ({ name: tagName(it), value: it.dy,
        note: it.dy == null ? "거래정지 — TTM 미산출" : undefined })),
      { color: "--s1", emph: byDy.filter(it => it.tags.includes("특별배당")).map(tagName),
        fmt: v => v.toFixed(1) + "%", labelW: 190, width: 1160, rowH: 26, aria: "리츠별 TTM 배당률" });
    $("#r-dy-cap").textContent = "금 강조 = 특별배당(자산 매각·청산성 분배) 포함 — 지속 가능한 수익률이 아니다. " +
      "정상 종목 중위 " + K.dy_med.toFixed(1) + "%가 이 시장의 진짜 체온.";
    // ③ 국고10년
    C.line($("#r-t10"), [{ name: "국고10y", color: "--s2", emph: true,
      points: R.treasury.map((p, i) => ({ x: i, label: fmt.ym(p.ym), y: p.rate })) }],
      { aria: "국고채 10년 월평균", yFmt: v => v.toFixed(1) + "%", width: 560, height: 300, rightPad: 64 });
    $("#r-t10-cap").textContent = `최신 ${K.t10.toFixed(2)}% — 정상 리츠 배당 중위와의 간격 +${K.spread.toFixed(1)}%p가 리츠에 요구되는 위험 보상이다.`;
    // ④ 섹터 표
    $("#r-sector").innerHTML = "<thead><tr><th>섹터</th><th class='num'>종목</th><th class='num'>P/장부NAV</th><th class='num'>TTM 배당</th></tr></thead><tbody>" +
      R.sectors.map(s => `<tr><td>${s.name}</td><td class="num">${s.n}</td><td class="num">${s.pb_med.toFixed(2)}</td><td class="num">${s.dy_med != null ? s.dy_med.toFixed(1) + "%" : "―"}</td></tr>`).join("") +
      "</tbody>";
  }

  /* ---------- 테마 ---------- */
  function initTheme() {
    const btn = document.querySelector(".theme-toggle");
    const sync = () => {
      const light = document.documentElement.dataset.theme === "light";
      btn.setAttribute("aria-pressed", String(light));
    };
    btn.addEventListener("click", () => {
      const r = document.documentElement;
      r.dataset.theme = r.dataset.theme === "light" ? "" : "light";
      if (!r.dataset.theme) delete r.dataset.theme;
      sync(); renderAll();
    });
    sync();
  }

  function renderAll() { counters(); renderBunyang(); renderReits(); }

  route();
  renderAll();
  reveal();
  initTheme();
})();
