// 통계 — 인원별 새벽/야간/합계 + 총량 편차 + 간격 표준편차
const Stats = {
  async load() {
    const res = await API.get("/api/schedule/stats");
    const d = res.data;
    const summary = document.getElementById("stats-summary");
    summary.innerHTML = `
      <div class="stat"><b>${d.total.diff}</b><span>총량 편차 (min ${d.total.min} / max ${d.total.max})</span></div>
      <div class="stat"><b>${d.gap.mean_weeks}</b><span>평균 당직 간격(주)</span></div>
      <div class="stat"><b>${d.gap.stdev}</b><span>간격 표준편차 (작을수록 균일)</span></div>
    `;

    const members = Object.entries(d.per_member)
      .map(([id, v]) => ({ id, ...v }))
      .sort((a, b) => b.total - a.total || a.name.localeCompare(b.name));

    const wrap = document.getElementById("stats-table-wrap");
    if (!members.length) {
      wrap.innerHTML = `<div class="empty">생성된 당직표가 없습니다.</div>`;
      return;
    }
    const rows = members
      .map((m) => `<tr><td class="wk-period">${m.name}</td><td>${m.dawn}</td><td>${m.night}</td><td><b>${m.total}</b></td></tr>`)
      .join("");
    wrap.innerHTML = `<table>
      <thead><tr><th>이름</th><th>🌅 새벽</th><th>🌙 야간</th><th>합계</th></tr></thead>
      <tbody>${rows}</tbody></table>`;
  },
};
