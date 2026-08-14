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
let currentImageAnalysis = null;
let backendAvailable = true;
let cameraStream = null;
let selectedImageDataUrl = "";
const assessmentStorageKey = "disfigurement-index-cases";
const observedChangeThreshold = 2.0;

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
  const imageSuggestionApplied = applyPendingImageSuggestion();
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

  document.querySelector("[data-load-history]")?.addEventListener("click", async () => {
    await loadCaseHistory();
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
  if (imageSuggestionApplied) {
    setMessage("#calculator-message", "Image suggestions applied. Review clinical domains before saving.", "soft");
  }
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

function applyPendingImageSuggestion() {
  let suggestion = null;
  try {
    suggestion = JSON.parse(window.sessionStorage.getItem("disfigurement-index-image-suggestion") || "null");
  } catch {
    suggestion = null;
  }
  if (!suggestion?.calculatorPayload?.domains) return false;
  const caseInput = document.querySelector("#caseId");
  const regionInput = document.querySelector("#anatomicalRegion");
  if (caseInput && suggestion.caseId) caseInput.value = suggestion.caseId;
  if (regionInput && suggestion.calculatorPayload.anatomicalRegion) {
    regionInput.value = suggestion.calculatorPayload.anatomicalRegion;
  }
  Object.entries(suggestion.calculatorPayload.domains).forEach(([domainId, value]) => {
    const input = Array.from(document.querySelectorAll("[data-domain]")).find((field) => field.dataset.domain === domainId);
    if (!input) return;
    input.value = value;
    updateSliderOutput(input);
  });
  window.sessionStorage.removeItem("disfigurement-index-image-suggestion");
  return true;
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
    algorithmVersion: "browser-local-composite-v1.1",
    score,
    baseScore: score,
    contextAdjustedScore: score,
    severityBand: cleanBand(score),
    completeness: 100,
    confidence,
    highestDriver: drivers[0]?.label || "Not available",
    drivers,
    calculatedAt: new Date().toISOString()
  };
}

function saveLocalAssessment(payload) {
  const result = calculateLocal(payload);
  const saved = getLocalAssessments();
  const caseHistory = localHistoryForCase(payload.caseId);
  const previous = caseHistory[0] || null;
  const item = {
    id: globalThis.crypto?.randomUUID ? globalThis.crypto.randomUUID() : String(Date.now()),
    createdAt: new Date().toISOString(),
    payload,
    result: {}
  };
  const savedResult = {
    ...result,
    assessmentId: item.id,
    createdAt: item.createdAt
  };
  item.result = savedResult;
  const nextSaved = [item, ...saved].slice(0, 100);
  window.localStorage.setItem(assessmentStorageKey, JSON.stringify(nextSaved));
  return {
    ...savedResult,
    change: calculateObservedChange(savedResult, previous),
    history: localHistoryForCase(payload.caseId)
  };
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

function getLocalAssessments() {
  return readLocalArray(assessmentStorageKey);
}

function normalizedCaseId(value) {
  return String(value || "").trim();
}

function localAssessmentSummary(item) {
  const payload = item?.payload || {};
  const result = item?.result || {};
  const score = Number(result.score ?? item?.score ?? 0);
  return {
    assessmentId: item?.id || result.assessmentId || item?.assessmentId,
    createdAt: item?.createdAt || result.createdAt || item?.created_at,
    caseId: normalizedCaseId(payload.caseId || item?.caseId),
    clinicalSetting: payload.clinicalSetting || item?.clinicalSetting || "",
    anatomicalRegion: payload.anatomicalRegion || item?.anatomicalRegion || "",
    score: Math.round(score * 10) / 10,
    severityBand: result.severityBand || cleanBand(score),
    confidence: Number(result.confidence ?? item?.confidence ?? 0),
    highestDriver: result.highestDriver || "Not available",
    algorithmVersion: result.algorithmVersion || "browser-local-composite-v1.1"
  };
}

function localHistoryForCase(caseId) {
  const normalized = normalizedCaseId(caseId);
  if (!normalized) return [];
  return getLocalAssessments()
    .map(localAssessmentSummary)
    .filter((item) => item.caseId === normalized)
    .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
    .slice(0, 12);
}

function calculateObservedChange(currentResult, previous) {
  const currentScore = Math.round(Number(currentResult?.score ?? 0) * 10) / 10;
  const comparisonNote = "Compare only when scoring conditions and documentation quality are similar.";
  if (!previous) {
    return {
      available: false,
      direction: "baseline",
      currentScore,
      previousScore: null,
      delta: null,
      absoluteDelta: null,
      previousAssessmentId: null,
      previousCreatedAt: null,
      interpretation: "First saved assessment for this Case ID.",
      comparisonNote
    };
  }

  const previousScore = Math.round(Number(previous.score ?? 0) * 10) / 10;
  const delta = Math.round((currentScore - previousScore) * 10) / 10;
  const absoluteDelta = Math.round(Math.abs(delta) * 10) / 10;
  let direction = "stable";
  let interpretation = "No material score change from the previous saved assessment.";
  if (absoluteDelta >= observedChangeThreshold && delta > 0) {
    direction = "increased";
    interpretation = "Composite score increased from the previous saved assessment.";
  } else if (absoluteDelta >= observedChangeThreshold && delta < 0) {
    direction = "decreased";
    interpretation = "Composite score decreased from the previous saved assessment.";
  }

  return {
    available: true,
    direction,
    currentScore,
    previousScore,
    delta,
    absoluteDelta,
    previousAssessmentId: previous.assessmentId,
    previousCreatedAt: previous.createdAt,
    interpretation,
    comparisonNote
  };
}

function formatDelta(change) {
  if (!change || change.delta === null || change.delta === undefined) return "Baseline";
  const sign = change.delta > 0 ? "+" : "";
  return `${sign}${change.delta} points`;
}

function directionLabel(value) {
  const labels = {
    baseline: "Baseline",
    stable: "Stable",
    increased: "Increased",
    decreased: "Decreased"
  };
  return labels[value] || "Not available";
}

function renderChange(result) {
  const panel = document.querySelector("#change-panel");
  const directionEl = document.querySelector("#change-direction");
  const deltaEl = document.querySelector("#change-delta");
  const timelineEl = document.querySelector("#case-timeline");
  if (!panel || !directionEl || !deltaEl || !timelineEl) return;

  const hasSavedContext = Boolean(result?.assessmentId || result?.history || result?.change);
  if (!hasSavedContext) {
    panel.hidden = true;
    timelineEl.innerHTML = "";
    return;
  }

  const history = Array.isArray(result.history) ? result.history : [];
  const change = result.change || calculateObservedChange(result, history[1] || null);
  panel.hidden = false;
  directionEl.textContent = directionLabel(change?.direction);
  deltaEl.textContent = formatDelta(change);

  if (!history.length) {
    timelineEl.innerHTML = `<li><span>No saved history yet</span></li>`;
    return;
  }

  timelineEl.innerHTML = history.slice(0, 5).map((item, index) => `
    <li>
      <span>${index === 0 ? "Latest" : formatDate(item.createdAt)}</span>
      <strong>${Number(item.score).toFixed(1)}/100</strong>
    </li>
  `).join("");
}

async function loadCaseHistory() {
  const caseId = normalizedCaseId(selectedText("#caseId"));
  if (!caseId) {
    setMessage("#calculator-message", "Enter a Case ID to show history.", "soft");
    return;
  }

  try {
    const data = backendAvailable
      ? await api.get(`/api/case-timeline?caseId=${encodeURIComponent(caseId)}`)
      : localTimelinePayload(caseId);
    renderChange({
      ...(currentResult || {}),
      assessmentId: data.history?.[0]?.assessmentId || currentResult?.assessmentId,
      change: data.latestChange,
      history: data.history || []
    });
    setMessage("#calculator-message", data.history?.length ? "Case history loaded." : "No saved history found.", "soft");
  } catch (error) {
    if (!isBackendUnavailable(error)) {
      setMessage("#calculator-message", responseErrorMessage(error, "History could not be loaded."), "soft");
      return;
    }
    backendAvailable = false;
    const data = localTimelinePayload(caseId);
    renderChange({
      ...(currentResult || {}),
      assessmentId: data.history?.[0]?.assessmentId || currentResult?.assessmentId,
      change: data.latestChange,
      history: data.history
    });
    setMessage("#calculator-message", data.history.length ? "Case history loaded." : "No saved history found.", "soft");
  }
}

function localTimelinePayload(caseId) {
  const history = localHistoryForCase(caseId);
  return {
    ok: true,
    caseId,
    history,
    latestChange: history.length
      ? calculateObservedChange(history[0], history[1] || null)
      : null
  };
}

function initImageAnalysis() {
  const form = document.querySelector("#image-form");
  const upload = document.querySelector("#imageUpload");
  if (!form || !upload) return;

  upload.addEventListener("change", async () => {
    const file = upload.files?.[0];
    if (!file) return;
    try {
      selectedImageDataUrl = await readFileAsDataUrl(file);
      setImagePreview(selectedImageDataUrl);
      setMessage("#analysis-message", "Photo ready for analysis.", "soft");
    } catch {
      setMessage("#analysis-message", "Photo could not be loaded.", "soft");
    }
  });

  document.querySelector("[data-start-camera]")?.addEventListener("click", async () => {
    await startCamera();
  });

  document.querySelector("[data-capture-photo]")?.addEventListener("click", () => {
    captureCameraPhoto();
  });

  document.querySelector("[data-reset-image]")?.addEventListener("click", () => {
    resetImageAnalysis();
  });

  document.querySelector("[data-copy-image-note]")?.addEventListener("click", async () => {
    await copyImageNote();
  });

  document.querySelector("[data-download-image-note]")?.addEventListener("click", () => {
    downloadImageNote();
  });

  document.querySelector("[data-apply-image-suggestion]")?.addEventListener("click", () => {
    applyImageSuggestionToCalculator();
  });

  document.querySelector("[data-load-image-history]")?.addEventListener("click", async () => {
    await loadImageHistory();
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    await analyzeSelectedImage();
  });
}

function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.addEventListener("load", () => resolve(String(reader.result || "")));
    reader.addEventListener("error", reject);
    reader.readAsDataURL(file);
  });
}

async function startCamera() {
  const video = document.querySelector("#camera-preview");
  const image = document.querySelector("#image-preview");
  const empty = document.querySelector("#image-empty-state");
  if (!video || !navigator.mediaDevices?.getUserMedia) {
    setMessage("#analysis-message", "Camera access is not available in this browser.", "soft");
    return;
  }
  try {
    stopCamera();
    cameraStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: "environment" }, width: { ideal: 1280 }, height: { ideal: 960 } },
      audio: false
    });
    video.srcObject = cameraStream;
    await video.play();
    video.hidden = false;
    if (image) image.hidden = true;
    if (empty) empty.hidden = true;
    setMessage("#analysis-message", "Camera ready. Capture a still image when aligned.", "soft");
  } catch {
    setMessage("#analysis-message", "Camera permission was not granted.", "soft");
  }
}

function stopCamera() {
  if (!cameraStream) return;
  cameraStream.getTracks().forEach((track) => track.stop());
  cameraStream = null;
}

function captureCameraPhoto() {
  const video = document.querySelector("#camera-preview");
  const canvas = document.querySelector("#image-canvas");
  if (!video || !canvas || video.hidden || !video.videoWidth) {
    setMessage("#analysis-message", "Start the camera before capturing.", "soft");
    return;
  }
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  const context = canvas.getContext("2d");
  if (!context) {
    setMessage("#analysis-message", "Camera capture is not available in this browser.", "soft");
    return;
  }
  context.drawImage(video, 0, 0, canvas.width, canvas.height);
  selectedImageDataUrl = canvas.toDataURL("image/jpeg", 0.92);
  setImagePreview(selectedImageDataUrl);
  stopCamera();
  setMessage("#analysis-message", "Camera photo captured.", "soft");
}

function setImagePreview(dataUrl) {
  const video = document.querySelector("#camera-preview");
  const image = document.querySelector("#image-preview");
  const empty = document.querySelector("#image-empty-state");
  if (video) video.hidden = true;
  if (image) {
    image.src = dataUrl;
    image.hidden = false;
  }
  if (empty) empty.hidden = true;
}

function resetImageAnalysis() {
  stopCamera();
  selectedImageDataUrl = "";
  currentImageAnalysis = null;
  const form = document.querySelector("#image-form");
  const video = document.querySelector("#camera-preview");
  const image = document.querySelector("#image-preview");
  const empty = document.querySelector("#image-empty-state");
  form?.reset();
  if (video) {
    video.srcObject = null;
    video.hidden = true;
  }
  if (image) {
    image.removeAttribute("src");
    image.hidden = true;
  }
  if (empty) empty.hidden = false;
  renderImageAnalysis(null);
  const message = document.querySelector("#analysis-message");
  if (message) message.hidden = true;
}

function collectImagePayload() {
  return {
    caseId: document.querySelector("#imageCaseId")?.value.trim(),
    anatomicalRegion: document.querySelector("#imageAnatomicalRegion")?.value,
    imageData: selectedImageDataUrl
  };
}

async function analyzeSelectedImage() {
  const payload = collectImagePayload();
  if (!payload.caseId) {
    setMessage("#analysis-message", "Enter a Case ID before analysis.", "soft");
    return;
  }
  if (!payload.imageData) {
    setMessage("#analysis-message", "Upload or capture a photo before analysis.", "soft");
    return;
  }

  setMessage("#analysis-message", "Analyzing image.", "soft");
  try {
    const result = await api.post("/api/image-analysis", payload);
    renderImageAnalysis(result);
    setImagePreview(result.overlayDataUrl || selectedImageDataUrl);
    setMessage("#analysis-message", "Image analysis complete.", "soft");
  } catch (error) {
    if (isBackendUnavailable(error)) {
      backendAvailable = false;
      setMessage("#analysis-message", "Image analysis requires the local backend server.", "soft");
      return;
    }
    setMessage("#analysis-message", responseErrorMessage(error, "Image analysis could not be completed."), "soft");
  }
}

function renderImageAnalysis(result) {
  currentImageAnalysis = result;
  const scoreEl = document.querySelector("#visual-index");
  const qualityEl = document.querySelector("#image-quality");
  const areaEl = document.querySelector("#detected-area");
  const colorEl = document.querySelector("#image-color");
  const textureEl = document.querySelector("#image-texture");
  const observationsEl = document.querySelector("#image-observations");
  const domainEl = document.querySelector("#image-domain-list");
  const historyEl = document.querySelector("#image-history");

  if (!result) {
    if (scoreEl) scoreEl.textContent = "0";
    if (qualityEl) qualityEl.textContent = "Not analyzed";
    if (areaEl) areaEl.textContent = "Not analyzed";
    if (colorEl) colorEl.textContent = "Not analyzed";
    if (textureEl) textureEl.textContent = "Not analyzed";
    if (observationsEl) observationsEl.innerHTML = `<li><span>Analyze an image to generate observations.</span></li>`;
    if (domainEl) domainEl.innerHTML = `<div><dt>Visual domains</dt><dd>Awaiting image</dd></div>`;
    if (historyEl) historyEl.innerHTML = `<li><span>No image analyses loaded</span></li>`;
    return;
  }

  if (scoreEl) scoreEl.textContent = String(result.visualIndex);
  if (qualityEl) qualityEl.textContent = `${result.quality?.qualityScore ?? 0}/100`;
  if (areaEl) areaEl.textContent = `${result.measurements?.detectedAreaPercent ?? 0}%`;
  if (colorEl) colorEl.textContent = `${result.measurements?.colorContrast ?? 0}`;
  if (textureEl) textureEl.textContent = `${result.measurements?.textureIrregularity ?? 0}`;

  if (observationsEl) {
    observationsEl.innerHTML = (result.observations || []).map((item) => `
      <li><span>${escapeHtml(item)}</span></li>
    `).join("");
  }

  if (domainEl) {
    domainEl.innerHTML = Object.entries(result.suggestedDomains || {}).map(([domain, value]) => `
      <div><dt>${escapeHtml(domainLabel(domain))}</dt><dd>${Number(value).toFixed(1)}</dd></div>
    `).join("");
  }

  renderImageHistory(result.history || []);
}

function renderImageHistory(history) {
  const historyEl = document.querySelector("#image-history");
  if (!historyEl) return;
  if (!history.length) {
    historyEl.innerHTML = `<li><span>No image analyses loaded</span></li>`;
    return;
  }
  historyEl.innerHTML = history.slice(0, 6).map((item, index) => `
    <li>
      <span>${index === 0 ? "Latest" : formatDate(item.createdAt)}</span>
      <strong>${Number(item.visualIndex).toFixed(1)}/100</strong>
    </li>
  `).join("");
}

async function loadImageHistory() {
  const caseId = normalizedCaseId(document.querySelector("#imageCaseId")?.value);
  if (!caseId) {
    setMessage("#analysis-message", "Enter a Case ID to show image history.", "soft");
    return;
  }
  try {
    const data = await api.get(`/api/image-analysis-timeline?caseId=${encodeURIComponent(caseId)}`);
    renderImageHistory(data.history || []);
    setMessage("#analysis-message", data.history?.length ? "Image history loaded." : "No image history found.", "soft");
  } catch (error) {
    if (isBackendUnavailable(error)) {
      setMessage("#analysis-message", "Image history requires the local backend server.", "soft");
      return;
    }
    setMessage("#analysis-message", responseErrorMessage(error, "Image history could not be loaded."), "soft");
  }
}

function domainLabel(domain) {
  const labels = {
    vascularity: "Vascularity",
    pigmentation: "Pigmentation",
    relief: "Relief",
    surface_area: "Surface area",
    clinician_global: "Clinician global",
    documentation_confidence: "Documentation confidence"
  };
  return labels[domain] || domain;
}

function buildImageNote() {
  const result = currentImageAnalysis || {};
  const observations = (result.observations || []).map((item) => `- ${item}`).join("\n") || "- Not analyzed";
  const domains = Object.entries(result.suggestedDomains || {})
    .map(([domain, value]) => `- ${domainLabel(domain)}: ${Number(value).toFixed(1)}`)
    .join("\n") || "- Not analyzed";
  return [
    "Disfigurement Index Image AI",
    "",
    `Case ID: ${document.querySelector("#imageCaseId")?.value.trim() || "Not entered"}`,
    `Region: ${selectedText("#imageAnatomicalRegion") || "Not selected"}`,
    `Visual estimate: ${result.visualIndex ?? 0}/100`,
    `Image quality: ${result.quality?.qualityScore ?? 0}/100`,
    `Detected area: ${result.measurements?.detectedAreaPercent ?? 0}%`,
    "",
    "Observations:",
    observations,
    "",
    "Suggested calculator inputs:",
    domains,
    "",
    `Generated: ${new Date().toLocaleString()}`
  ].join("\n");
}

async function copyImageNote() {
  if (!currentImageAnalysis) {
    setMessage("#analysis-message", "Analyze an image before copying a note.", "soft");
    return;
  }
  try {
    await navigator.clipboard.writeText(buildImageNote());
  } catch {
    const textarea = document.createElement("textarea");
    textarea.value = buildImageNote();
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    textarea.remove();
  }
  setMessage("#analysis-message", "Image note copied.", "soft");
}

function downloadImageNote() {
  if (!currentImageAnalysis) {
    setMessage("#analysis-message", "Analyze an image before downloading a note.", "soft");
    return;
  }
  const caseId = normalizedCaseId(document.querySelector("#imageCaseId")?.value).replace(/[^a-z0-9-]+/gi, "-") || "case";
  const blob = new Blob([buildImageNote()], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `disfigurement-image-analysis-${caseId}.txt`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  setMessage("#analysis-message", "Image note downloaded.", "soft");
}

function applyImageSuggestionToCalculator() {
  if (!currentImageAnalysis?.calculatorPayload) {
    setMessage("#analysis-message", "Analyze an image before applying suggestions.", "soft");
    return;
  }
  window.sessionStorage.setItem("disfigurement-index-image-suggestion", JSON.stringify({
    caseId: currentImageAnalysis.caseId,
    calculatorPayload: currentImageAnalysis.calculatorPayload
  }));
  window.location.href = "index.html";
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
    driversEl.innerHTML = (result.drivers || []).slice(0, 3).map((driver) => `
      <li>
        <span>${escapeHtml(driver.label)}</span>
      </li>
    `).join("");
  }
  renderChange(result);
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
  const change = result.change;

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
    `Observed change: ${change ? `${directionLabel(change.direction)} (${formatDelta(change)})` : "Not saved"}`,
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
    if (page === "image-analysis") initImageAnalysis();
    if (page === "forum") await initForum();
  } catch (error) {
    const fallback = document.querySelector("[data-page-error]");
    if (fallback) {
      setMessage(fallback, "Something went wrong. Please refresh and try again.", "soft");
    }
  }
}

init();
