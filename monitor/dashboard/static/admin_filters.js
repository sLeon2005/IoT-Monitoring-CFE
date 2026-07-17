const authPanel = document.querySelector("#auth-panel");
const passwordInput = document.querySelector("#admin-password");
const unlockButton = document.querySelector("#unlock-button");
const summary = document.querySelector("#summary");
const saveState = document.querySelector("#save-state");
const editor = document.querySelector("#sections-editor");
const addSectionButton = document.querySelector("#add-section-button");
const saveButton = document.querySelector("#save-button");
const sectionTemplate = document.querySelector("#section-template");

let adminPassword = "";
let authRequired = false;
let dirty = false;

function getHeaders() {
  const headers = {
    "Content-Type": "application/json",
  };

  if (adminPassword) {
    headers["X-Admin-Password"] = adminPassword;
  }

  return headers;
}

async function loadStatus() {
  const response = await fetch("/api/admin/filters/status", { cache: "no-store" });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  const payload = await response.json();
  authRequired = Boolean(payload.auth_required);
  authPanel.hidden = !authRequired;
}

async function loadFilters() {
  setBusy(true);

  try {
    const response = await fetch("/api/admin/filters", {
      cache: "no-store",
      headers: getHeaders(),
    });

    if (response.status === 401) {
      authPanel.hidden = false;
      setMessage("Ingresa la contraseña para editar filtros.", true);
      return;
    }

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const payload = await response.json();
    renderSections(Array.isArray(payload.sections) ? payload.sections : []);
    updateSummary();
    dirty = false;
    setMessage("Sin cambios pendientes", false);
  } catch (error) {
    setMessage("No fue posible cargar los filtros.", true);
  } finally {
    setBusy(false);
  }
}

function renderSections(sections) {
  editor.innerHTML = "";

  for (const section of sections) {
    editor.appendChild(createSectionElement(section.name, section.terms || []));
  }

  if (sections.length === 0) {
    editor.appendChild(createSectionElement("Nueva seccion", []));
  }
}

function createSectionElement(name, terms) {
  const fragment = sectionTemplate.content.cloneNode(true);
  const sectionElement = fragment.querySelector(".filter-section");
  const nameInput = fragment.querySelector(".section-name");
  const termsTextarea = fragment.querySelector(".section-terms");
  const removeButton = fragment.querySelector(".remove-section");

  nameInput.value = name || "";
  termsTextarea.value = terms.join("\n");

  nameInput.addEventListener("input", markDirty);
  termsTextarea.addEventListener("input", markDirty);
  termsTextarea.addEventListener("blur", () => {
    termsTextarea.value = normalizeTermsInput(termsTextarea.value).join("\n");
    markDirty();
  });
  removeButton.addEventListener("click", () => {
    const sectionName = nameInput.value.trim() || "esta sección";
    const confirmed = window.confirm(
      `¿Confirmas que deseas eliminar ${sectionName}? Esta acción quitará la sección y sus términos del editor.`,
    );

    if (!confirmed) {
      return;
    }

    sectionElement.remove();
    markDirty();
  });

  return fragment;
}

function collectSections() {
  return [...editor.querySelectorAll(".filter-section")].map((section) => {
    const name = section.querySelector(".section-name").value;
    const termsTextarea = section.querySelector(".section-terms");
    const terms = normalizeTermsInput(termsTextarea.value);
    termsTextarea.value = terms.join("\n");

    return { name, terms };
  });
}

function collectSectionsForSummary() {
  return [...editor.querySelectorAll(".filter-section")].map((section) => {
    const name = section.querySelector(".section-name").value;
    const terms = section
      .querySelector(".section-terms")
      .value.split(/\r?\n/)
      .map((term) => term.trim())
      .filter(Boolean);

    return { name, terms };
  });
}

function normalizeTermsInput(value) {
  return value
    .split(/\r?\n/)
    .map(normalizeTerm)
    .filter(Boolean);
}

function normalizeTerm(value) {
  return String(value ?? "")
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

async function saveFilters() {
  setBusy(true);

  try {
    const response = await fetch("/api/admin/filters", {
      method: "POST",
      headers: getHeaders(),
      body: JSON.stringify({ sections: collectSections() }),
    });

    if (response.status === 401) {
      authPanel.hidden = false;
      setMessage("Contraseña incorrecta.", true);
      return;
    }

    const payload = await response.json();

    if (!response.ok) {
      throw new Error(payload.error || `HTTP ${response.status}`);
    }

    renderSections(Array.isArray(payload.sections) ? payload.sections : []);
    updateSummary();
    dirty = false;
    setMessage("Cambios guardados.", false, true);
  } catch (error) {
    setMessage(error.message || "No fue posible guardar.", true);
  } finally {
    setBusy(false);
  }
}

function updateSummary() {
  const sections = collectSectionsForSummary();
  const termCount = sections.reduce((total, section) => total + section.terms.length, 0);
  summary.textContent = `${sections.length} secciones, ${termCount} terminos`;
}

function markDirty() {
  dirty = true;
  updateSummary();
  setMessage("Cambios pendientes", false);
}

function setMessage(message, isError, isOk = false) {
  saveState.textContent = message;
  saveState.classList.toggle("is-error", Boolean(isError));
  saveState.classList.toggle("is-ok", Boolean(isOk));
}

function setBusy(isBusy) {
  saveButton.disabled = isBusy;
  addSectionButton.disabled = isBusy;
  unlockButton.disabled = isBusy;
}

addSectionButton.addEventListener("click", () => {
  editor.appendChild(createSectionElement("Nueva seccion", []));
  markDirty();
});

saveButton.addEventListener("click", saveFilters);

unlockButton.addEventListener("click", () => {
  adminPassword = passwordInput.value;
  loadFilters();
});

passwordInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    adminPassword = passwordInput.value;
    loadFilters();
  }
});

window.addEventListener("beforeunload", (event) => {
  if (!dirty) {
    return;
  }

  event.preventDefault();
});

loadStatus()
  .then(loadFilters)
  .catch(() => setMessage("No fue posible iniciar el editor.", true));
