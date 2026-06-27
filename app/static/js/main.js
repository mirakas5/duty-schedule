// 부트스트랩 — 탭 전환 + 이벤트 바인딩
document.addEventListener("DOMContentLoaded", () => {
  // 탭 전환
  const tabs = document.querySelectorAll(".tab");
  tabs.forEach((t) => t.addEventListener("click", () => switchTab(t.dataset.tab)));

  function switchTab(name) {
    tabs.forEach((t) => t.classList.toggle("active", t.dataset.tab === name));
    document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
    document.getElementById("tab-" + name).classList.add("active");
    if (name === "schedule") Schedule.load();
    else if (name === "stats") Stats.load();
    else if (name === "admin") Admin.enter();
  }

  // 관리 인증
  document.getElementById("btn-admin-login").addEventListener("click", () => Admin.login());
  document.getElementById("btn-admin-logout").addEventListener("click", () => Admin.logout());
  document.getElementById("admin-pw").addEventListener("keydown", (e) => { if (e.key === "Enter") Admin.login(); });

  // 관리 버튼
  document.getElementById("btn-upload").addEventListener("click", () => Admin.upload());
  document.getElementById("btn-add-holiday").addEventListener("click", () => Admin.addHoliday());
  document.getElementById("btn-generate").addEventListener("click", () => Admin.generate());

  // 내보내기
  document.getElementById("btn-export").addEventListener("click", () => {
    window.location.href = "/api/schedule/export";
  });

  // 달력 네비게이션
  document.getElementById("cal-prev").addEventListener("click", () => Schedule.shift(-1));
  document.getElementById("cal-next").addEventListener("click", () => Schedule.shift(1));
  document.getElementById("cal-today").addEventListener("click", () => Schedule.goToday());

  // 컨텍스트 메뉴
  const cmenu = document.getElementById("context-menu");
  cmenu.querySelectorAll("button").forEach((b) =>
    b.addEventListener("click", () => {
      ContextMenu.hide();
      if (b.dataset.action === "edit") EditModal.open();
      else if (b.dataset.action === "delete") Schedule.deleteCell();
    })
  );
  document.addEventListener("click", (e) => { if (!cmenu.contains(e.target)) ContextMenu.hide(); });
  document.addEventListener("scroll", () => ContextMenu.hide(), true);

  // 수정 모달
  document.getElementById("edit-cancel").addEventListener("click", () => EditModal.close());
  document.getElementById("edit-save").addEventListener("click", () => {
    const id = Number(document.getElementById("edit-select").value);
    EditModal.close();
    Schedule.saveEdit(id);
  });

  // 기본 탭(당직표) 로드
  Schedule.load();
});
