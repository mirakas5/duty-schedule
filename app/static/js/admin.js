// 관리 — 인증 게이트 + 명단/공휴일/생성
const Admin = {
  // 관리 탭 진입: 상태 확인 → 게이트 또는 관리 화면
  async enter() {
    let st;
    try { st = (await API.get("/api/admin/status")).data; }
    catch { st = { authed: false, ip_allowed: true, ip: "" }; }

    const gate = document.getElementById("admin-gate");
    const content = document.getElementById("admin-content");

    if (st.authed) {
      gate.classList.add("hidden");
      content.classList.remove("hidden");
      await this.load();
      return;
    }
    content.classList.add("hidden");
    gate.classList.remove("hidden");

    const msg = document.getElementById("admin-gate-msg");
    const pw = document.getElementById("admin-pw");
    const btn = document.getElementById("btn-admin-login");
    if (!st.ip_allowed) {
      msg.textContent = `이 PC(${st.ip})에서는 관리 기능을 사용할 수 없습니다. 관리자 PC에서 접속하세요.`;
      pw.disabled = true; btn.disabled = true;
    } else {
      msg.textContent = "관리 기능을 사용하려면 비밀번호를 입력하세요.";
      pw.disabled = false; btn.disabled = false;
    }
  },

  async login() {
    const pw = document.getElementById("admin-pw").value;
    const out = document.getElementById("admin-login-msg");
    try {
      await API.post("/api/admin/login", { password: pw });
      document.getElementById("admin-pw").value = "";
      out.textContent = ""; out.className = "msg";
      toast("관리자 로그인");
      await this.enter();
    } catch (err) { out.textContent = err.message; out.className = "msg error"; if (err.status === 401) Admin.enter(); }
  },

  async logout() {
    try { await API.post("/api/admin/logout", {}); } catch {}
    toast("관리 로그아웃");
    await this.enter();
  },

  async load() {
    await Promise.all([this.loadMembers(), this.loadHolidays()]);
  },

  // ── 명단 ──
  async loadMembers() {
    const members = await API.get("/api/members");
    const box = document.getElementById("member-list");
    if (!members.length) { box.innerHTML = `<div class="hint">등록된 멤버가 없습니다.</div>`; return; }
    box.innerHTML = members
      .map((m) => `<div class="li ${m.active ? "" : "inactive"}">
        <span class="grow">${m.name}</span>
        <button class="btn mini" data-act="toggle" data-id="${m.id}" data-active="${m.active}">${m.active ? "비활성" : "활성"}</button>
        <button class="btn mini" data-act="rename" data-id="${m.id}" data-name="${m.name}">이름</button>
        <button class="btn mini" data-act="del" data-id="${m.id}">삭제</button>
      </div>`)
      .join("");
    box.querySelectorAll("button").forEach((b) => b.addEventListener("click", (e) => this.memberAction(e.target.dataset)));
  },

  async memberAction(ds) {
    try {
      if (ds.act === "toggle") {
        await API.put(`/api/members/${ds.id}`, { active: ds.active !== "true" });
      } else if (ds.act === "rename") {
        const name = prompt("새 이름", ds.name);
        if (!name) return;
        await API.put(`/api/members/${ds.id}`, { name });
      } else if (ds.act === "del") {
        if (!confirm("삭제하시겠습니까?")) return;
        await API.del(`/api/members/${ds.id}`);
      }
      await this.loadMembers();
    } catch (err) { toast(err.message, true); if (err.status === 401) Admin.enter(); }
  },

  async upload() {
    const input = document.getElementById("member-file");
    const out = document.getElementById("upload-result");
    if (!input.files.length) { out.textContent = "파일을 선택하세요"; out.className = "msg error"; return; }
    if (!confirm("기존 명단과 생성된 스케줄이 모두 삭제되고 새 명단으로 교체됩니다. 진행할까요?")) return;
    const fd = new FormData();
    fd.append("file", input.files[0]);
    try {
      const r = await API.upload("/api/members/upload", fd);
      out.textContent = `완료 — 기존 ${r.cleared}명 삭제, ${r.total}명 등록 (스케줄 초기화됨)`;
      out.className = "msg";
      input.value = "";
      await this.loadMembers();
    } catch (err) { out.textContent = err.message; out.className = "msg error"; if (err.status === 401) Admin.enter(); }
  },

  // ── 공휴일 ──
  async loadHolidays() {
    const list = await API.get("/api/holidays");
    const box = document.getElementById("holiday-list");
    if (!list.length) { box.innerHTML = `<div class="hint">등록된 공휴일이 없습니다.</div>`; return; }
    const typeLabel = { national: "국가", temporary: "임시", company: "회사" };
    box.innerHTML = list
      .map((h) => `<div class="li">
        <span class="grow">${h.date} · ${h.name || "(무명)"} <small>[${typeLabel[h.type] || h.type}]</small></span>
        <button class="btn mini" data-id="${h.id}">삭제</button>
      </div>`)
      .join("");
    box.querySelectorAll("button").forEach((b) => b.addEventListener("click", async (e) => {
      try { await API.del(`/api/holidays/${e.target.dataset.id}`); await this.loadHolidays(); }
      catch (err) { toast(err.message, true); if (err.status === 401) Admin.enter(); }
    }));
  },

  async addHoliday() {
    const date = document.getElementById("holiday-date").value;
    const name = document.getElementById("holiday-name").value;
    const type = document.getElementById("holiday-type").value;
    if (!date) { toast("날짜를 선택하세요", true); return; }
    try {
      await API.post("/api/holidays", { date, name, type });
      document.getElementById("holiday-name").value = "";
      await this.loadHolidays();
      toast("공휴일 추가");
    } catch (err) { toast(err.message, true); if (err.status === 401) Admin.enter(); }
  },

  // ── 생성 ──
  async generate() {
    const start = document.getElementById("gen-start").value;
    const end = document.getElementById("gen-end").value;
    const wt = parseFloat(document.getElementById("gen-wt").value);
    const wg = parseFloat(document.getElementById("gen-wg").value);
    const reset = document.getElementById("gen-reset").checked;
    const out = document.getElementById("gen-result");
    if (!start) { out.textContent = "시작일을 선택하세요"; out.className = "msg error"; return; }
    const msg = reset
      ? "전체 초기화 후 생성합니다. 기존 당직표가 모두 삭제됩니다. 진행할까요?"
      : "이 구간을 생성(겹치는 구간은 교체)합니다. 진행할까요?";
    if (!confirm(msg)) return;
    try {
      const body = { start_date: start, weight_total: wt, weight_gap: wg, reset };
      if (end) body.end_date = end;
      const r = await API.post("/api/schedule/generate", body);
      const d = r.data;
      out.textContent =
        `생성 완료 — ${d.range.start}~${d.range.end} · ${d.generated_weeks}주/${d.generated_workdays}평일 ` +
        `(이력 ${d.carried_history_weeks}주 반영) · 누적 총량편차 ${d.fairness.total.diff} · 간격σ ${d.fairness.gap.stdev}`;
      out.className = "msg";
      toast("스케줄 생성 완료");
      if (typeof Schedule !== "undefined") Schedule.cur = null; // 달력 위치 재설정
    } catch (err) { out.textContent = err.message; out.className = "msg error"; if (err.status === 401) Admin.enter(); }
  },
};
