// Extracta browser UI: select PDFs, upload them, poll each task, show results and charts,
// and download exports. Everything that comes from a document is inserted with textContent,
// never as HTML: PDF content and LLM output are untrusted.

const root = document.getElementById("app");
const config = {
  maxUploadMb: Number(root.dataset.maxUploadMb),
  maxFiles: Number(root.dataset.maxFiles),
  resultTtlMinutes: Number(root.dataset.resultTtlMinutes),
};

const POLL_INTERVAL_MS = 2000;
const FORMATS = { csv: "CSV", xlsx: "XLSX", json: "JSON" };
const ACTIVE = new Set(["pending", "processing"]);
const STATUS = {
  pending: { icon: "⏳", label: "Pending" },
  processing: { icon: "⚙️", label: "Processing" },
  completed: { icon: "✓", label: "Completed" },
  failed: { icon: "✕", label: "Failed" },
  rejected: { icon: "✕", label: "Rejected" },
  expired: { icon: "⌛", label: "Expired" },
};
const TYPE_LABELS = {
  invoice: "Invoice",
  receipt: "Receipt",
  purchase_order: "Purchase order",
  quote: "Quote",
  bank_statement: "Bank statement",
  contract: "Contract",
  payslip: "Payslip",
  resume: "Resume",
  report: "Report",
  other: "Other",
};

// One fixed color per document type, readable on light and dark backgrounds.
const PALETTE = ["#4e79a7", "#f28e2b", "#59a14f", "#e15759", "#76b7b2", "#edc948", "#b07aa1", "#ff9da7", "#9c755f", "#bab0ac"];

const el = {
  form: document.getElementById("upload-form"),
  dropzone: document.getElementById("dropzone"),
  fileInput: document.getElementById("file-input"),
  selected: document.getElementById("selected-files"),
  uploadButton: document.getElementById("upload-button"),
  clearSelection: document.getElementById("clear-selection"),
  message: document.getElementById("message"),
  resultsBody: document.getElementById("results-body"),
  summary: document.getElementById("batch-summary"),
  ttlNotice: document.getElementById("ttl-notice"),
  exportAll: document.querySelectorAll("[data-export-all]"),
  charts: document.getElementById("charts"),
  chartsEmpty: document.getElementById("charts-empty"),
};

const state = {
  selected: [], // { file, error }
  batch: [], // { key, taskId, filename, status, result, error, saveToDb }
  polling: false,
};
let charts = null;

// ------------------------------------------------------------------ helpers

function h(tag, props = {}, children = []) {
  // Tiny element builder: text always goes through textContent.
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (key === "text") node.textContent = value;
    else if (key === "className") node.className = value;
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else if (value !== undefined && value !== null && value !== false) node.setAttribute(key, value);
  }
  for (const child of [].concat(children)) {
    if (child !== null && child !== undefined) node.append(child);
  }
  return node;
}

function showMessage(text, kind = "") {
  el.message.textContent = text;
  el.message.className = kind ? `message message--${kind}` : "message";
}

function formatAmount(amount, currency) {
  if (typeof amount !== "number") return "";
  try {
    return new Intl.NumberFormat(undefined, { style: "currency", currency: currency || "XXX" }).format(amount);
  } catch {
    return `${amount.toLocaleString()} ${currency || ""}`.trim(); // unknown currency code
  }
}

function formatSize(bytes) {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function isPdf(file) {
  return file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
}

// ------------------------------------------------------------------ file selection

function addFiles(fileList) {
  for (const file of fileList) {
    const duplicate = state.selected.some((s) => s.file.name === file.name && s.file.size === file.size);
    if (duplicate) continue;
    let error = null;
    if (!isPdf(file)) error = "Not a PDF";
    else if (file.size > config.maxUploadMb * 1024 * 1024) error = `Larger than ${config.maxUploadMb} MB`;
    state.selected.push({ file, error });
  }
  renderSelection();
}

function renderSelection() {
  const valid = state.selected.filter((s) => !s.error);
  el.selected.replaceChildren(
    ...state.selected.map((entry, index) =>
      h("li", { className: `file-list__item${entry.error ? " file-list__item--invalid" : ""}` }, [
        h("span", { className: "file-list__name", text: entry.file.name, title: entry.file.name }),
        h("span", {
          className: entry.error ? "file-list__error" : "muted",
          text: entry.error ?? formatSize(entry.file.size),
        }),
        h("button", {
          type: "button",
          className: "button button--ghost button--small",
          text: "Remove",
          "aria-label": `Remove ${entry.file.name}`,
          onclick: () => {
            state.selected.splice(index, 1);
            renderSelection();
          },
        }),
      ]),
    ),
  );
  const tooMany = valid.length > config.maxFiles;
  el.uploadButton.disabled = valid.length === 0 || tooMany;
  el.uploadButton.textContent = valid.length > 1 ? `Upload and process ${valid.length} files` : "Upload and process";
  el.clearSelection.hidden = state.selected.length === 0;
  if (tooMany) showMessage(`Select at most ${config.maxFiles} files per upload.`, "error");
}

el.fileInput.addEventListener("change", () => {
  addFiles(el.fileInput.files);
  el.fileInput.value = ""; // allow picking the same file again after removing it
});
el.clearSelection.addEventListener("click", () => {
  state.selected = [];
  renderSelection();
  showMessage("");
});
for (const eventName of ["dragenter", "dragover"]) {
  el.dropzone.addEventListener(eventName, (event) => {
    event.preventDefault();
    el.dropzone.classList.add("dropzone--active");
  });
}
for (const eventName of ["dragleave", "drop"]) {
  el.dropzone.addEventListener(eventName, () => el.dropzone.classList.remove("dropzone--active"));
}
el.dropzone.addEventListener("drop", (event) => {
  event.preventDefault();
  addFiles(event.dataTransfer.files);
});

// ------------------------------------------------------------------ upload

el.form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const files = state.selected.filter((s) => !s.error).map((s) => s.file);
  if (files.length === 0) return;

  const saveToDb = el.form.querySelector('input[name="save_to_db"]:checked').value === "true";
  const body = new FormData();
  for (const file of files) body.append("files", file, file.name);
  body.append("save_to_db", String(saveToDb));

  el.uploadButton.disabled = true;
  showMessage(`Uploading ${files.length} file(s)…`);
  try {
    const response = await fetch("/upload", { method: "POST", body });
    const data = await response.json().catch(() => ({}));
    if (!response.ok && !data.tasks) {
      showMessage(data.error || `Upload failed (HTTP ${response.status}).`, "error");
      return;
    }
    for (const task of data.tasks) {
      state.batch.push({ key: task.task_id, taskId: task.task_id, filename: task.filename, status: "pending", saveToDb });
    }
    for (const rejected of data.rejected) {
      state.batch.push({ key: crypto.randomUUID(), filename: rejected.filename, status: "rejected", error: rejected.error });
    }
    const note = data.rejected.length ? ` ${data.rejected.length} rejected.` : "";
    showMessage(`${data.tasks.length} file(s) queued for processing.${note}`, data.tasks.length ? "ok" : "error");
    state.selected = [];
    renderSelection();
    renderResults();
    startPolling();
  } catch {
    showMessage("Network error: the upload did not reach the server.", "error");
  } finally {
    renderSelection();
  }
});

// ------------------------------------------------------------------ polling

function startPolling() {
  if (state.polling) return;
  state.polling = true;
  setTimeout(pollOnce, POLL_INTERVAL_MS / 2);
}

async function pollOnce() {
  const active = state.batch.filter((entry) => ACTIVE.has(entry.status));
  for (const entry of active) {
    try {
      const response = await fetch(`/tasks/${encodeURIComponent(entry.taskId)}`);
      if (response.status === 404) {
        entry.status = "expired";
        entry.error = "The result expired or belongs to another browser session.";
        continue;
      }
      if (!response.ok) continue; // temporary server problem: try again on the next round
      const data = await response.json();
      entry.status = data.status;
      entry.result = data.result ?? null;
      entry.error = data.error ?? null;
    } catch {
      // Network hiccup: keep the current status and retry on the next round.
    }
  }
  renderResults();
  if (state.batch.some((entry) => ACTIVE.has(entry.status))) {
    setTimeout(pollOnce, POLL_INTERVAL_MS);
  } else {
    state.polling = false;
  }
}

// ------------------------------------------------------------------ results table

function describeDocument(doc) {
  const parts = [];
  const c = doc.commercial;
  if (c) {
    parts.push(c.issuer?.name, c.document_number && `No. ${c.document_number}`, formatAmount(c.total_amount, c.currency));
  } else if (doc.bank_statement) {
    const b = doc.bank_statement;
    parts.push(b.bank_name, b.account_number_last4 && `•••• ${b.account_number_last4}`, formatAmount(b.closing_balance, b.currency));
  } else if (doc.contract) {
    parts.push(doc.contract.title, doc.contract.parties.map((p) => p.name).join(" · "));
  } else if (doc.payslip) {
    parts.push(doc.payslip.employee_name, formatAmount(doc.payslip.net_pay, doc.payslip.currency));
  } else if (doc.resume) {
    parts.push(doc.resume.full_name, doc.resume.current_title);
  } else if (doc.report) {
    parts.push(doc.report.title, doc.report.period_covered);
  } else {
    parts.push(doc.title);
  }
  return parts.filter(Boolean).join(" — ") || doc.summary;
}

function statusBadge(status) {
  const { icon, label } = STATUS[status] ?? { icon: "•", label: status };
  // Icon + text: the status never depends on color alone.
  return h("span", { className: `badge badge--${status}` }, [h("span", { "aria-hidden": "true", text: icon }), label]);
}

function detailsCell(entry) {
  if (entry.status === "completed" && entry.result) {
    const doc = entry.result.document;
    const extra = [];
    if (entry.result.truncated) extra.push(h("div", { className: "muted", text: "Long document: only the first part was analysed." }));
    if (entry.result.saved_to_db) extra.push(h("div", { className: "muted", text: "Saved to the database." }));
    return h("td", { className: "results__details" }, [
      h("div", { text: describeDocument(doc) }),
      ...extra,
      h("details", {}, [h("summary", { text: "View extracted data" }), h("pre", { text: JSON.stringify(doc, null, 2) })]),
    ]);
  }
  if (entry.error) return h("td", { className: "results__details error-text", text: entry.error });
  return h("td", { className: "results__details muted", text: "Waiting for the AI extraction…" });
}

function downloadsCell(entry) {
  if (entry.status !== "completed") return h("td", { className: "results__downloads muted", text: "—" });
  return h(
    "td",
    { className: "results__downloads" },
    Object.entries(FORMATS).map(([fmt, label]) =>
      h("button", {
        type: "button",
        className: "button button--small",
        text: label,
        "aria-label": `Download ${entry.filename} as ${label}`,
        onclick: () => exportDocuments(fmt, "individual", { filename: entry.filename, document: entry.result.document }),
      }),
    ),
  );
}

function renderResults() {
  if (state.batch.length === 0) return;
  el.resultsBody.replaceChildren(
    ...state.batch.map((entry) =>
      h("tr", {}, [
        h("td", { className: "results__file", text: entry.filename }),
        h("td", {}, statusBadge(entry.status)),
        h("td", { text: entry.result ? TYPE_LABELS[entry.result.document.document_type] ?? "" : "" }),
        detailsCell(entry),
        downloadsCell(entry),
      ]),
    ),
  );

  const count = (status) => state.batch.filter((entry) => entry.status === status).length;
  const completed = count("completed");
  const active = state.batch.filter((entry) => ACTIVE.has(entry.status)).length;
  const problems = count("failed") + count("rejected") + count("expired");
  el.summary.textContent = `${completed} of ${state.batch.length} completed · ${active} in progress · ${problems} with problems`;
  for (const button of el.exportAll) button.disabled = completed === 0;

  const ephemeral = state.batch.some((entry) => entry.status === "completed" && entry.saveToDb === false);
  el.ttlNotice.hidden = !ephemeral;
  el.ttlNotice.textContent = `Process-only results are not saved: they expire after ${config.resultTtlMinutes} minutes and disappear if you close this page. Download them to keep them.`;
  renderCharts();
}

// ------------------------------------------------------------------ charts

function renderCharts() {
  const docs = state.batch.filter((entry) => entry.status === "completed").map((entry) => entry.result.document);
  el.charts.hidden = docs.length === 0;
  el.chartsEmpty.hidden = docs.length > 0;
  if (docs.length === 0) return;
  if (typeof window.Chart !== "function") {
    el.chartsEmpty.hidden = false;
    el.chartsEmpty.textContent = "Charts are unavailable: the chart library could not be loaded.";
    el.charts.hidden = true;
    return;
  }

  const byType = new Map();
  for (const doc of docs) {
    const label = TYPE_LABELS[doc.document_type] ?? doc.document_type;
    byType.set(label, (byType.get(label) ?? 0) + 1);
  }
  const byCurrency = new Map();
  for (const doc of docs) {
    const c = doc.commercial;
    if (c && typeof c.total_amount === "number") {
      const currency = c.currency || "Unknown";
      byCurrency.set(currency, (byCurrency.get(currency) ?? 0) + c.total_amount);
    }
  }

  if (!charts) {
    // Chart.js does not read CSS: pass it the page's theme colors (light or dark).
    window.Chart.defaults.color = cssVar("--muted");
    window.Chart.defaults.borderColor = cssVar("--border");
    const options = { responsive: true, maintainAspectRatio: false, animation: { duration: 300 } };
    charts = {
      types: new window.Chart(document.getElementById("type-chart"), {
        type: "doughnut",
        data: { labels: [], datasets: [{ data: [], borderColor: cssVar("--surface"), borderWidth: 2 }] },
        options: { ...options, plugins: { legend: { position: "right" } } },
      }),
      amounts: new window.Chart(document.getElementById("amount-chart"), {
        type: "bar",
        data: { labels: [], datasets: [{ label: "Total amount", data: [], backgroundColor: cssVar("--accent") }] },
        options: { ...options, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } },
      }),
    };
  }
  const typeNames = Object.values(TYPE_LABELS);
  charts.types.data.labels = [...byType.keys()];
  charts.types.data.datasets[0].data = [...byType.values()];
  charts.types.data.datasets[0].backgroundColor = [...byType.keys()].map(
    (label) => PALETTE[Math.max(0, typeNames.indexOf(label)) % PALETTE.length],
  );
  charts.types.update();
  charts.amounts.data.labels = [...byCurrency.keys()];
  charts.amounts.data.datasets[0].data = [...byCurrency.values()];
  charts.amounts.update();
}

// ------------------------------------------------------------------ exports

function filenameFrom(response, fallback) {
  const header = response.headers.get("Content-Disposition") || "";
  const utf8 = header.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8) return decodeURIComponent(utf8[1]);
  const plain = header.match(/filename="([^"]+)"/i);
  return plain ? plain[1] : fallback;
}

async function exportDocuments(fmt, scope, payload) {
  try {
    const response = await fetch(`/export/${fmt}/${scope}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      showMessage(data.error || `Export failed (HTTP ${response.status}).`, "error");
      return;
    }
    const url = URL.createObjectURL(await response.blob());
    const link = h("a", { href: url, download: filenameFrom(response, `export.${fmt}`) });
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch {
    showMessage("Network error: the export could not be downloaded.", "error");
  }
}

for (const button of el.exportAll) {
  button.addEventListener("click", () => {
    const items = state.batch
      .filter((entry) => entry.status === "completed")
      .map((entry) => ({ filename: entry.filename, document: entry.result.document }));
    if (items.length) exportDocuments(button.dataset.exportAll, "unified", { items });
  });
}

// Warn before leaving while process-only results live only in this page.
window.addEventListener("beforeunload", (event) => {
  if (state.batch.some((entry) => entry.status === "completed" && entry.saveToDb === false)) {
    event.preventDefault();
  }
});
