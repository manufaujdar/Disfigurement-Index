const api = {
  async get(path) {
    const response = await fetch(path, { headers: { Accept: "application/json" } });
    return parseResponse(response);
  },
  async post(path, payload) {
    const response = await fetch(path, {
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

async function parseResponse(response) {
  const data = await response.json();
  if (!response.ok) {
    const error = new Error("Please review the form and try again.");
    error.payload = data;
    throw error;
  }
  return data;
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

  const config = await api.get("/api/config");
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

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const payload = collectAssessmentPayload();
      const result = await api.post("/api/assessments", payload);
      renderResult(result);
      setMessage("#calculator-message", "Assessment saved.", "soft");
    } catch (error) {
      setMessage("#calculator-message", "Please complete all required fields.", "soft");
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
    const result = await api.post("/api/calculate", payload);
    renderResult(result);
    const message = document.querySelector("#calculator-message");
    if (message) message.hidden = true;
  } catch (error) {
    setMessage("#calculator-message", "Please complete all required fields.", "soft");
  }
}

function cleanBand(score) {
  if (score < 20) return "Minimal";
  if (score < 40) return "Mild";
  if (score < 60) return "Moderate";
  if (score < 80) return "Severe";
  return "Very severe";
}

function renderResult(result) {
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

async function initForum() {
  const form = document.querySelector("#forum-form");
  const list = document.querySelector("#comment-list");
  if (!form || !list) return;

  async function load() {
    const data = await api.get("/api/forum");
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
    try {
      await api.post("/api/forum", {
        doctorName: document.querySelector("#forumName").value.trim(),
        topic: document.querySelector("#forumTopic").value,
        comment: document.querySelector("#forumComment").value.trim()
      });
      form.reset();
      setMessage("#forum-message", "Comment posted.", "soft");
      await load();
    } catch (error) {
      setMessage("#forum-message", "Please complete the comment form.", "soft");
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
