/**
 * research.js
 * Frontend controller for Research Paper Walkthrough & Degradation Playground.
 */

let archLayers = [];
let currentSelectedLevel = "D0";

document.addEventListener("DOMContentLoaded", () => {
  initResearchPage();
});

async function initResearchPage() {
  await loadArchitectureSpecs();
  setupPlayground();
}

async function loadArchitectureSpecs() {
  try {
    const res = await fetch("/api/research/architecture");
    const data = await res.json();
    archLayers = data.layers || [];
    renderLayersList();
    if (archLayers.length > 0) {
      selectLayer(archLayers[0].id);
    }
  } catch (err) {
    console.error("Failed to load architecture specifications:", err);
  }
}

function renderLayersList() {
  const container = document.getElementById("layersListContainer");
  if (!container) return;

  container.innerHTML = archLayers.map((l, idx) => `
    <div class="layer-clickable ${idx === 0 ? 'active' : ''}" onclick="selectLayer(${l.id})" id="layerItem-${l.id}">
      <div>
        <div class="layer-tag" style="font-size:10px;">${l.tag}</div>
        <div style="font-weight:600; font-size:13.5px; color:var(--text-primary); margin-top:2px;">${l.name}</div>
      </div>
      <i class="ti ti-chevron-right" style="color:var(--text-muted);"></i>
    </div>
  `).join("");
}

function selectLayer(id) {
  const layer = archLayers.find(l => l.id === id);
  if (!layer) return;

  // Update active state in list
  document.querySelectorAll(".layer-clickable").forEach(el => el.classList.remove("active"));
  document.getElementById(`layerItem-${id}`)?.classList.add("active");

  // Render detail view
  const detailBox = document.getElementById("layerDetailContainer");
  if (!detailBox) return;

  detailBox.innerHTML = `
    <div style="display:flex; align-items:center; justify-content:space-between; border-bottom:1px solid var(--border); padding-bottom:12px;">
      <div>
        <span class="paper-pill" style="margin-bottom:4px;">${layer.tag}</span>
        <h3 style="font-size:18px; margin-top:4px;">${layer.name}</h3>
      </div>
      <span class="mono" style="font-size:12px; color:var(--signal);">Layer ${layer.id} of 5</span>
    </div>

    <div>
      <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:600; margin-bottom:4px;">Core Responsibility &amp; Design Purpose</div>
      <p style="font-size:13.5px; color:var(--text-primary); margin:0; line-height:1.6;">${layer.purpose}</p>
    </div>

    <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px;">
      <div style="background:var(--bg); border:1px solid var(--border); border-radius:var(--radius-sm); padding:12px;">
        <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:600; margin-bottom:4px;"><i class="ti ti-arrow-right"></i> Layer Inputs</div>
        <div style="font-size:12.5px; color:var(--text-secondary);">${layer.inputs}</div>
      </div>

      <div style="background:var(--bg); border:1px solid var(--border); border-radius:var(--radius-sm); padding:12px;">
        <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:600; margin-bottom:4px;"><i class="ti ti-arrow-left"></i> Layer Outputs</div>
        <div style="font-size:12.5px; color:var(--text-secondary);">${layer.outputs}</div>
      </div>
    </div>

    <div style="background:rgba(43, 217, 168, 0.05); border:1px solid rgba(43, 217, 168, 0.2); border-radius:var(--radius-sm); padding:14px;">
      <div style="font-size:11px; text-transform:uppercase; color:var(--signal); font-weight:600; margin-bottom:4px;"><i class="ti ti-shield-check"></i> Schema Resilience Mechanism</div>
      <div style="font-size:13px; color:var(--text-primary);">${layer.resilience_mechanism}</div>
    </div>

    <div>
      <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:600; margin-bottom:8px;">Underlying Source Modules</div>
      <div style="display:flex; flex-wrap:wrap; gap:8px;">
        ${layer.key_components.map(c => `<span class="meta-chip"><i class="ti ti-code"></i> ${c}</span>`).join("")}
      </div>
    </div>
  `;
}

function setupPlayground() {
  const datasetSelect = document.getElementById("pgDatasetSelect");
  const levelBtns = document.querySelectorAll(".level-pill-btn");

  datasetSelect?.addEventListener("change", () => loadPlaygroundData());
  levelBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      levelBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      currentSelectedLevel = btn.dataset.level;
      loadPlaygroundData();
    });
  });

  loadPlaygroundData();
}

async function loadPlaygroundData() {
  const dataset = document.getElementById("pgDatasetSelect")?.value || "sales";
  const tableContainer = document.getElementById("playgroundTableContainer");
  const explanationEl = document.getElementById("playgroundExplanation");

  if (!tableContainer) return;

  tableContainer.innerHTML = `<div class="skeleton" style="height:180px;"></div>`;

  try {
    const res = await fetch(`/api/research/preview-degraded?dataset=${dataset}&level=${currentSelectedLevel}`);
    const data = await res.json();

    if (explanationEl) {
      explanationEl.innerHTML = `<strong>Level ${data.level} Characteristics:</strong> ${data.explanation}`;
    }

    let html = `<table class="bench-table" style="font-size:12px;"><thead><tr>`;
    data.columns.forEach(c => {
      html += `<th>${c}</th>`;
    });
    html += `</tr></thead><tbody>`;

    data.rows.forEach(r => {
      html += `<tr>`;
      data.columns.forEach(c => {
        html += `<td class="mono">${r[c]}</td>`;
      });
      html += `</tr>`;
    });
    html += `</tbody></table>`;
    tableContainer.innerHTML = html;
  } catch (err) {
    tableContainer.innerHTML = `<div style="padding:16px; color:var(--danger);">Failed to load preview data.</div>`;
  }
}
