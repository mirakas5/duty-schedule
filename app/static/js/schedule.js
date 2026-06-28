// 당직 달력 — 월간 렌더 + 드래그앤드롭 교환(일 단위) + 클릭/우클릭 수정·삭제
const Schedule = {
  days: [],
  activeMembers: [],
  dateMap: {},      // "YYYY-MM-DD" → day 객체
  holidayMap: {},   // "YYYY-MM-DD" → 공휴일명
  cur: null,        // {y, m}
  dragSrc: null,
  ctx: null,

  async load() {
    [this.days, this.activeMembers, this.holidays] = await Promise.all([
      API.get("/api/schedule"),
      API.get("/api/members?active_only=true"),
      API.get("/api/holidays"),
    ]);
    this.dateMap = {};
    this.days.forEach((d) => { this.dateMap[d.date] = d; });
    this.holidayMap = {};
    this.holidays.forEach((h) => { this.holidayMap[h.date] = h.name || "공휴일"; });

    if (!this.cur) {
      const base = this.days.length ? this.days[0].date : new Date().toISOString().slice(0, 10);
      const [y, m] = base.split("-");
      this.cur = { y: Number(y), m: Number(m) - 1 };
    }
    this.render();
  },

  shift(delta) {
    let { y, m } = this.cur;
    m += delta;
    if (m < 0) { m = 11; y -= 1; }
    if (m > 11) { m = 0; y += 1; }
    this.cur = { y, m };
    this.render();
  },

  goToday() {
    const n = new Date();
    this.cur = { y: n.getFullYear(), m: n.getMonth() };
    this.render();
  },

  pad(n) { return String(n).padStart(2, "0"); },

  render() {
    const empty = document.getElementById("schedule-empty");
    const cal = document.getElementById("calendar");
    document.getElementById("cal-title").textContent = `${this.cur.y}년 ${this.cur.m + 1}월`;

    if (!this.days.length) {
      cal.innerHTML = "";
      empty.classList.remove("hidden");
      return;
    }
    empty.classList.add("hidden");

    const { y, m } = this.cur;
    const todayStr = new Date().toISOString().slice(0, 10);
    const firstDow = new Date(y, m, 1).getDay();
    const daysInMonth = new Date(y, m + 1, 0).getDate();
    const dow = ["일", "월", "화", "수", "목", "금", "토"];

    let cells = dow.map((d, i) => `<div class="cal-head ${i === 0 ? "sun" : ""} ${i === 6 ? "sat" : ""}">${d}</div>`).join("");
    for (let i = 0; i < firstDow; i++) cells += `<div class="cal-cell empty-cell"></div>`;

    for (let day = 1; day <= daysInMonth; day++) {
      const ds = `${y}-${this.pad(m + 1)}-${this.pad(day)}`;
      const dowIdx = new Date(y, m, day).getDay();
      const isWeekend = dowIdx === 0 || dowIdx === 6;
      const holiday = this.holidayMap[ds];
      const dayObj = this.dateMap[ds];
      const todayCls = ds === todayStr ? "today" : "";

      let inner = `<div class="cal-date">${day}</div>`;
      if (holiday) {
        inner += `<div class="cal-holiday">${holiday}</div>`;
      } else if (dayObj) {
        inner += this.chip(dayObj, "dawn") + this.chip(dayObj, "night");
      }
      const cls = `cal-cell ${todayCls} ${isWeekend ? "weekend" : ""} ${holiday ? "holiday" : ""}`;
      cells += `<div class="${cls}">${inner}</div>`;
    }

    cal.innerHTML = cells;
    cal.querySelectorAll(".chip").forEach((el) => this.bindCell(el));
  },

  chip(d, slot) {
    const c = d[slot];
    const name = c.member_name || "공석";
    const cls = "chip " + slot + (c.member_name ? "" : " empty-slot");
    const icon = slot === "dawn" ? "🌅" : "🌙";
    return `<span class="${cls}" draggable="true"
      data-day-id="${d.id}" data-slot="${slot}"
      data-member-id="${c.member_id == null ? "" : c.member_id}"
      data-version="${d.version}" title="${slot === "dawn" ? "새벽근무" : "야간근무"} · 클릭=수정/삭제, 드래그=교환">${icon}${name}</span>`;
  },

  bindCell(el) {
    el.addEventListener("dragstart", (e) => {
      this.dragSrc = this.read(el);
      this._dragging = true;
      el.classList.add("dragging");
      e.dataTransfer.effectAllowed = "move";
    });
    el.addEventListener("dragend", () => { el.classList.remove("dragging"); setTimeout(() => { this._dragging = false; }, 50); });
    el.addEventListener("dragover", (e) => { e.preventDefault(); el.classList.add("drag-over"); });
    el.addEventListener("dragleave", () => el.classList.remove("drag-over"));
    el.addEventListener("drop", (e) => {
      e.preventDefault();
      el.classList.remove("drag-over");
      this.onDrop(this.read(el));
    });
    // 클릭으로 메뉴 열기(우클릭이 막히는 환경 대비). 드래그 직후 클릭은 무시.
    el.addEventListener("click", (e) => {
      if (this._dragging) return;
      e.stopPropagation();
      this.ctx = this.read(el);
      ContextMenu.show(e.clientX, e.clientY);
    });
    // 우클릭도 유지
    el.addEventListener("contextmenu", (e) => {
      e.preventDefault();
      this.ctx = this.read(el);
      ContextMenu.show(e.clientX, e.clientY);
    });
  },

  read(el) {
    return {
      dayId: Number(el.dataset.dayId),
      slot: el.dataset.slot,
      memberId: el.dataset.memberId === "" ? null : Number(el.dataset.memberId),
      version: Number(el.dataset.version),
    };
  },

  async onDrop(target) {
    const src = this.dragSrc;
    this.dragSrc = null;
    if (!src) return;
    if (src.dayId === target.dayId && src.slot === target.slot) return;
    try {
      await API.post("/api/schedule/swap", {
        a_day_id: src.dayId, a_slot: src.slot,
        b_day_id: target.dayId, b_slot: target.slot,
        a_version: src.version, b_version: target.version,
      });
      toast("교환 완료");
      await this.load();
    } catch (err) {
      toast(err.message, true);
      if (err.status === 409) await this.load();
    }
  },

  async deleteCell() {
    const c = this.ctx;
    try {
      await API.patch(`/api/schedule/day/${c.dayId}`, { slot: c.slot, member_id: null, version: c.version });
      toast("삭제(공석) 완료");
      await this.load();
    } catch (err) {
      toast(err.message, true);
      if (err.status === 409) await this.load();
    }
  },

  async saveEdit(memberId) {
    const c = this.ctx;
    try {
      await API.patch(`/api/schedule/day/${c.dayId}`, { slot: c.slot, member_id: memberId, version: c.version });
      toast("수정 완료");
      await this.load();
    } catch (err) {
      toast(err.message, true);
      if (err.status === 409) await this.load();
    }
  },
};

const ContextMenu = {
  show(x, y) {
    const menu = document.getElementById("context-menu");
    menu.style.left = Math.min(x, window.innerWidth - 130) + "px";
    menu.style.top = Math.min(y, window.innerHeight - 90) + "px";
    menu.classList.remove("hidden");
  },
  hide() { document.getElementById("context-menu").classList.add("hidden"); },
};

const EditModal = {
  open() {
    const sel = document.getElementById("edit-select");
    sel.innerHTML = Schedule.activeMembers.map((m) => `<option value="${m.id}">${m.name}</option>`).join("");
    if (Schedule.ctx && Schedule.ctx.memberId != null) sel.value = String(Schedule.ctx.memberId);
    document.getElementById("edit-modal").classList.remove("hidden");
  },
  close() { document.getElementById("edit-modal").classList.add("hidden"); },
};
