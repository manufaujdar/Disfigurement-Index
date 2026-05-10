const api = {
  baseUrl: window.location.protocol === "file:" ? "http://127.0.0.1:4173" : "",
  async get(path) {
    const response = await fetch(`${this.baseUrl}${path}`, { headers: { Accept: "application/json" } });
    return parseResponse(response);
  },
  async post(path, payload) {
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });
    return parseResponse(response);
  }
};

let currentResult = null;
let backendAvailable = true;

const fallbackConfig = {
  domains: [
    { id: "vascularity", label: "Vascularity / redness", min: 1, max: 10, default: 3, weight: 0.09 },
    { id: "pigmentation", label: "Pigmentation difference", min: 1, max: 10, default: 3, weight: 0.09 },
    { id: "thickness", label: "Thickness / height", min: 1, max: 10, default: 3, weight: 0.10 },
    { id: "relief", label: "Relief / surface irregularity", min: 1, max: 10, default: 3, weight: 0.10 },
    { id: "pliability", label: "Pliability / tissue stiffness", min: 1, max: 10, default: 3, weight: 0.10 },
    { id: "surface_area", label: "Surface area / extent", min: 1, max: 10, default: 3, weight: 0.10 },
    { id: "pain", label: "Pain or tenderness", min: 1, max: 10, default: 2, weight: 0.08 },
    { id: "itch", label: "Itch / dysesthesia", min: 1, max: 10, default: 2, weight: 0.06 },
    { id: "functional_limitation", label: "Functional limitation", min: 1, max: 10, default: 2, weight: 0.11 },
    { id: "anatomical_visibility", label: "Anatomical visibility / social noticeability", min: 1, max: 10, default: 4, weight: 0.10 },
    { id: "clinician_global", label: "Clinician global severity", min: 1, max: 10, default: 3, weight: 0.07 }
  ],
  qualityDomains: [
    { id: "documentation_confidence", label: "Documentation confidence", min: 1, max: 10, default: 7 }
  ]
};

const regionModifiers = {
  face: 1.08,
  neck: 1.04,
  "upper-limb": 1.02,
  "lower-limb": 1,
  trunk: 0.96,
  multiple: 1.06
};

async function parseResponse(response) {
  let data = {};
  try {
    data = await response.json();
  } catch {
    data = {};
  }
  if (!response.ok) {
    const error = new Error("Please review the form and try again.");
    error.payload = data;
    throw error;
  }
  return data;
}

function isBackendUnavailable(error) {
  return !error || !Object.prototype.hasOwnProperty.call(error, "payload");
}

function responseErrorMessage(error, fallback) {
  const errors = error?.payload?.errors;
  return Array.isArray(errors) && errors.length ? errors.join(" ") : fallback;
}

function readLocalArray(key) {
  try {
    const value = JSON.parse(window.localStorage.getItem(key) || "[]");
    return Array.isArray(value) ? value : [];
  } catch {
    return [];
  }
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatDate(value) {
  if (!value) return "Not available";
  return new Date(value).toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  });
}

function setMessage(target, message, type = "soft") {
  const element = typeof target === "string" ? document.querySelector(target) : target;
  if (!element) return;
  element.className = `notice notice-${type}`;
  element.textContent = message;
  element.hidden = false;
}

function initNav() {
  const navToggle = document.querySelector("[data-nav-toggle]");
  const siteNav = document.querySelector(".site-nav");

  if (!navToggle || !siteNav) return;

  navToggle.addEventListener("click", () => {
    const isOpen = siteNav.classList.toggle("is-open");
    navToggle.setAttribute("aria-expanded", String(isOpen));
  });
}

async function initCalculator() {
  const form = document.querySelector("#index-form");
  const domainGrid = document.querySelector("#domain-fields");
  if (!form || !domainGrid) return;

  let config;
  try {
    config = await api.get("/api/config");
  } catch {
    backendAvailable = false;
    config = fallbackConfig;
  }
  renderDomainFields(config.domains, config.qualityDomains);
  let debounceTimer;
  const runCalculation = () => {
    window.clearTimeout(debounceTimer);
    debounceTimer = window.setTimeout(calculateOnly, 220);
  };

  form.addEventListener("input", (event) => {
    if (event.target.matches("[data-domain]")) {
      updateSliderOutput(event.target);
      runCalculation();
    }
  });
  form.addEventListener("change", runCalculation);

  document.querySelector("[data-calculate]")?.addEventListener("click", async () => {
    await calculateOnly();
  });

  document.querySelector("[data-print-result]")?.addEventListener("click", () => {
    window.print();
  });

  document.querySelector("[data-copy-summary]")?.addEventListener("click", async () => {
    await copySummary();
  });

  document.querySelector("[data-download-summary]")?.addEventListener("click", () => {
    downloadSummary();
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = collectAssessmentPayload();
    try {
      const result = backendAvailable ? await api.post("/api/assessments", payload) : saveLocalAssessment(payload);
      renderResult(result);
      setMessage("#calculator-message", "Assessment saved.", "soft");
    } catch (error) {
      if (isBackendUnavailable(error) && payload.clinicianName && payload.caseId) {
        backendAvailable = false;
        const result = saveLocalAssessment(payload);
        renderResult(result);
        setMessage("#calculator-message", "Assessment saved.", "soft");
        return;
      }
      setMessage("#calculator-message", responseErrorMessage(error, "Please complete all required fields."), "soft");
    }
  });

  document.querySelector("[data-reset-calculator]")?.addEventListener("click", () => {
    form.reset();
    form.querySelectorAll("[data-domain]").forEach(updateSliderOutput);
    calculateOnly();
  });

  await calculateOnly();
}

function renderDomainFields(domains, qualityDomains) {
  const domainGrid = document.querySelector("#domain-fields");
  const qualityGrid = document.querySelector("#quality-fields");
  if (!domainGrid || !qualityGrid) return;

  domainGrid.innerHTML = domains.map(domainField).join("");
  qualityGrid.innerHTML = qualityDomains.map(domainField).join("");
}

function domainField(domain) {
  return `
    <label class="domain-field">
      <span>${escapeHtml(domain.label)}</span>
      <input
        id="${escapeHtml(domain.id)}"
        type="range"
        min="${domain.min}"
        max="${domain.max}"
        step="0.5"
        value="${domain.default}"
        data-domain="${escapeHtml(domain.id)}"
      >
      <output for="${escapeHtml(domain.id)}">${domain.default}</output>
    </label>
  `;
}

function updateSliderOutput(input) {
  const output = input.parentElement.querySelector("output");
  if (output) {
    output.value = input.value;
    output.textContent = input.value;
  }
}

function collectAssessmentPayload() {
  const domains = {};
  document.querySelectorAll("[data-domain]").forEach((input) => {
    domains[input.dataset.domain] = Number(input.value);
  });

  return {
    clinicianName: document.querySelector("#clinicianName")?.value.trim(),
    caseId: document.querySelector("#caseId")?.value.trim(),
    clinicalSetting: document.querySelector("#clinicalSetting")?.value,
    anatomicalRegion: document.querySelector("#anatomicalRegion")?.value,
    notes: document.querySelector("#clinicalNotes")?.value.trim(),
    domains
  };
}

async function calculateOnly() {
  try {
    const payload = collectAssessmentPayload();
    const result = backendAvailable ? await api.post("/api/calculate", payload) : calculateLocal(payload);
    renderResult(result);
    const message = document.querySelector("#calculator-message");
    if (message) message.hidden = true;
  } catch (error) {
    if (!isBackendUnavailable(error)) {
      setMessage("#calculator-message", responseErrorMessage(error, "Please review scoring inputs."), "soft");
      return;
    }
    backendAvailable = false;
    const payload = collectAssessmentPayload();
    const result = calculateLocal(payload);
    renderResult(result);
  }
}

function normalize(value, min, max) {
  return (Number(value) - min) / (max - min);
}

function calculateLocal(payload) {
  const contributions = fallbackConfig.domains.map((domain) => {
    const raw = Number(payload.domains[domain.id] ?? domain.default);
    const normalized = Math.max(0, Math.min(normalize(raw, domain.min, domain.max), 1));
    return {
      id: domain.id,
      label: domain.label,
      raw,
      weight: domain.weight,
      contribution: normalized * domain.weight * 100
    };
  });
  const baseScore = contributions.reduce((total, item) => total + item.contribution, 0);
  const modifier = regionModifiers[payload.anatomicalRegion] || 1;
  const score = Math.round(Math.max(0, Math.min(baseScore * modifier, 100)) * 10) / 10;
  const confidenceRaw = Number(payload.domains.documentation_confidence ?? 7);
  const confidence = Math.round(normalize(confidenceRaw, 1, 10) * 1000) / 10;
  const drivers = contributions
    .sort((a, b) => b.contribution - a.contribution)
    .slice(0, 5)
    .map((item) => ({ ...item, contribution: Math.round(item.contribution * 100) / 100 }));

  return {
    ok: true,
    score,
    confidence,
    highestDriver: drivers[0]?.label || "Not available",
    drivers
  };
}

function saveLocalAssessment(payload) {
  const result = calculateLocal(payload);
  const saved = readLocalArray("disfigurement-index-cases");
  saved.unshift({
    id: globalThis.crypto?.randomUUID ? globalThis.crypto.randomUUID() : String(Date.now()),
    createdAt: new Date().toISOString(),
    payload,
    result
  });
  window.localStorage.setItem("disfigurement-index-cases", JSON.stringify(saved.slice(0, 100)));
  return result;
}

function getLocalComments() {
  return readLocalArray("disfigurement-index-comments");
}

function saveLocalComment(payload) {
  const doctorName = String(payload.doctorName || "").trim();
  const topic = String(payload.topic || "").trim();
  const comment = String(payload.comment || "").trim();
  if (!doctorName || !topic || !comment) {
    throw new Error("Forum comment is incomplete.");
  }

  const saved = getLocalComments();
  const item = {
    id: globalThis.crypto?.randomUUID ? globalThis.crypto.randomUUID() : String(Date.now()),
    created_at: new Date().toISOString(),
    doctor_name: doctorName,
    topic,
    comment
  };
  saved.unshift(item);
  window.localStorage.setItem("disfigurement-index-comments", JSON.stringify(saved.slice(0, 100)));
  return item;
}

function cleanBand(score) {
  if (score < 20) return "Minimal";
  if (score < 40) return "Mild";
  if (score < 60) return "Moderate";
  if (score < 80) return "Severe";
  return "Very severe";
}

function renderResult(result) {
  currentResult = result;
  const scoreEl = document.querySelector("#index-score");
  const bandEl = document.querySelector("#severity-band");
  const meterEl = document.querySelector("#score-meter");
  const confidenceEl = document.querySelector("#confidence");
  const driverEl = document.querySelector("#highest-driver");
  const driversEl = document.querySelector("#driver-list");

  if (scoreEl) scoreEl.textContent = String(result.score);
  if (bandEl) bandEl.textContent = cleanBand(result.score);
  if (meterEl) meterEl.style.width = `${Math.max(0, Math.min(result.score, 100))}%`;
  if (confidenceEl) confidenceEl.textContent = `${result.confidence}%`;
  if (driverEl) driverEl.textContent = result.highestDriver;

  if (driversEl) {
    driversEl.innerHTML = result.drivers.slice(0, 3).map((driver) => `
      <li>
        <span>${escapeHtml(driver.label)}</span>
      </li>
    `).join("");
  }
}

function selectedText(selector) {
  const element = document.querySelector(selector);
  if (!element) return "";
  if (element.tagName === "SELECT") {
    return element.selectedOptions[0]?.textContent || "";
  }
  return element.value || "";
}

function buildSummary() {
  const result = currentResult || {};
  const drivers = (result.drivers || [])
    .slice(0, 3)
    .map((driver) => `- ${driver.label}`)
    .join("\n");
  const notes = selectedText("#clinicalNotes").trim();

  return [
    "Disfigurement Index",
    "",
    `Case ID: ${selectedText("#caseId") || "Not entered"}`,
    `Clinician: ${selectedText("#clinicianName") || "Not entered"}`,
    `Setting: ${selectedText("#clinicalSetting") || "Not selected"}`,
    `Region: ${selectedText("#anatomicalRegion") || "Not selected"}`,
    "",
    `Index: ${result.score ?? 0}/100`,
    `Band: ${cleanBand(result.score ?? 0)}`,
    `Confidence: ${result.confidence ?? 0}%`,
    `Main factor: ${result.highestDriver || "Not available"}`,
    "",
    "Key factors:",
    drivers || "- Not available",
    "",
    "Clinical notes:",
    notes || "None",
    "",
    `Generated: ${new Date().toLocaleString()}`
  ].join("\n");
}

async function copySummary() {
  const summary = buildSummary();
  try {
    await navigator.clipboard.writeText(summary);
  } catch {
    const textarea = document.createElement("textarea");
    textarea.value = summary;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    textarea.remove();
  }
  setMessage("#calculator-message", "Summary copied.", "soft");
}

function downloadSummary() {
  const caseId = selectedText("#caseId").trim().replace(/[^a-z0-9-]+/gi, "-") || "case";
  const blob = new Blob([buildSummary()], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `disfigurement-index-${caseId}.txt`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  setMessage("#calculator-message", "Summary downloaded.", "soft");
}

async function initForum() {
  const form = document.querySelector("#forum-form");
  const list = document.querySelector("#comment-list");
  if (!form || !list) return;

  async function load() {
    let data;
    try {
      data = backendAvailable ? await api.get("/api/forum") : { comments: getLocalComments() };
    } catch (error) {
      if (!isBackendUnavailable(error)) throw error;
      backendAvailable = false;
      data = { comments: getLocalComments() };
    }
    if (!data.comments.length) {
      list.innerHTML = `<p class="empty-state">No comments yet. Add the first clinical feedback entry.</p>`;
      return;
    }
    list.innerHTML = data.comments.map((item) => `
      <article class="comment-item">
        <div class="comment-meta">
          <strong>${escapeHtml(item.doctor_name)}</strong>
          <span class="comment-topic">${escapeHtml(item.topic)}</span>
          <span>${formatDate(item.created_at)}</span>
        </div>
        <p>${escapeHtml(item.comment)}</p>
      </article>
    `).join("");
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = {
      doctorName: document.querySelector("#forumName").value.trim(),
      topic: document.querySelector("#forumTopic").value,
      comment: document.querySelector("#forumComment").value.trim()
    };
    try {
      if (backendAvailable) {
        await api.post("/api/forum", payload);
      } else {
        saveLocalComment(payload);
      }
      form.reset();
      setMessage("#forum-message", "Comment posted.", "soft");
      await load();
    } catch (error) {
      if (isBackendUnavailable(error)) {
        backendAvailable = false;
        try {
          saveLocalComment(payload);
          form.reset();
          setMessage("#forum-message", "Comment posted.", "soft");
          await load();
          return;
        } catch {
          setMessage("#forum-message", "Please complete the comment form.", "soft");
          return;
        }
      }
      setMessage("#forum-message", responseErrorMessage(error, "Please complete the comment form."), "soft");
    }
  });

  await load();
}

async function init() {
  initNav();
  const page = document.body.dataset.page;

  try {
    if (page === "calculator") await initCalculator();
    if (page === "forum") await initForum();
  } catch (error) {
    const fallback = document.querySelector("[data-page-error]");
    if (fallback) {
      setMessage(fallback, "Something went wrong. Please refresh and try again.", "soft");
    }
  }
}

init();
