// API fetch 래퍼 — 공통 에러 처리 (외부 의존성 없음)
const API = {
  async _req(method, url, body, isForm) {
    const opts = { method, headers: {} };
    if (body !== undefined) {
      if (isForm) {
        opts.body = body; // FormData
      } else {
        opts.headers["Content-Type"] = "application/json";
        opts.body = JSON.stringify(body);
      }
    }
    const res = await fetch(url, opts);
    const ct = res.headers.get("content-type") || "";
    if (!res.ok) {
      let detail = { message: `오류 (${res.status})`, code: "ERROR" };
      if (ct.includes("application/json")) {
        const j = await res.json().catch(() => null);
        if (j && j.detail) detail = typeof j.detail === "object" ? j.detail : { message: String(j.detail) };
        else if (j && j.error) detail = j.error;
      }
      const err = new Error(detail.message || "오류");
      err.code = detail.code;
      err.status = res.status;
      throw err;
    }
    if (ct.includes("application/json")) return res.json();
    return res;
  },
  get(url) { return this._req("GET", url); },
  post(url, body) { return this._req("POST", url, body); },
  put(url, body) { return this._req("PUT", url, body); },
  patch(url, body) { return this._req("PATCH", url, body); },
  del(url) { return this._req("DELETE", url); },
  upload(url, formData) { return this._req("POST", url, formData, true); },
};

function toast(msg, isError) {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.className = "toast" + (isError ? " error" : "");
  setTimeout(() => { t.className = "toast hidden"; }, 2600);
}
