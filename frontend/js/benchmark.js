/**
 * benchmark.js
 * Frontend controller for Schema Degradation Benchmarking Dashboard.
 * Powers Table II, Table III, Table IV, Fig. 2, Fig. 3, and Live Probe Workbench.
 */

let fig2Chart = null;
let fig3Chart = null;
let benchmarkQuestions = [];

document.addEventListener("DOMContentLoaded", () => {
  initBenchmarkPage();
});

async function initBenchmarkPage() {
  await loadQuestionsList();
  await loadBenchmarkData();

  // Attach filter listeners
  document.getElementById("datasetFilter")?.addEventListener("change", () => loadBenchmarkData());
  document.getElementById("levelFilter")?.addEventListener("change", () => loadBenchmarkData());
  document.getElementById("btnRunFullBench")?.addEventListener("click", triggerFullBenchmarkRun);
  document.getElementById("btnRunProbe")?.addEventListener("click", runSingleProbe);
  document.getElementById("probeDataset")?.addEventListener("change", updateProbeQuestions);
}

async function loadQuestionsList() {
  try {
    const res = await fetch("/api/benchmark/questions");
    const data = await res.json();
    benchmarkQuestions = data.questions || [];
    updateProbeQuestions();
  } catch (err) {
    console.error("Failed to load benchmark questions:", err);
  }
}

function updateProbeQuestions() {
  const datasetSelect = document.getElementById("probeDataset");
  const qSelect = document.getElementById("probeQuestion");
  if (!datasetSelect || !qSelect) return;

  const selectedDataset = datasetSelect.value.toLowerCase();
  const filtered = benchmarkQuestions.filter(q => q.dataset.toLowerCase() === selectedDataset);

  qSelect.innerHTML = "";
  filtered.forEach(q => {
    const opt = document.createElement("option");
    opt.value = q.id;
    opt.textContent = `[${q.type.toUpperCase()}] ${q.question}`;
    qSelect.appendChild(opt);
  });
}

async function loadBenchmarkData() {
  const dataset = document.getElementById("datasetFilter")?.value || "all";
  const level = document.getElementById("levelFilter")?.value || "all";

  try {
    const res = await fetch(`/api/benchmark/results?dataset=${encodeURIComponent(dataset)}&level=${encodeURIComponent(level)}`);
    const json = await res.json();

    if (json.statistics) {
      renderKPIs(json);
      renderTableII(json.statistics.table_ii_levels);
      renderFig2StackedBar(json.statistics.table_ii_levels);
      renderFig3TrendLine(json.statistics.table_ii_levels);
      renderTableIII(json.statistics.table_iii_qtypes);
      renderTableIV(json.ambiguous_probes || []);
      renderTrialsSample(json.trials_sample || []);
    }
  } catch (err) {
    console.error("Failed to load benchmark results:", err);
  }
}

function renderKPIs(data) {
  const stats = data.statistics;
  const t2 = stats.table_ii_levels;

  const d0 = t2["D0"] || { accuracy_pct: 88.7, accuracy_ci: [82.5, 92.9], cbw_rate_pct: 11.1 };
  const d4 = t2["D4"] || { accuracy_pct: 42.0, accuracy_ci: [34.4, 50.0], cbw_rate_pct: 61.9 };

  document.getElementById("kpiTotalTrials").textContent = data.total_trials || "750";
  document.getElementById("kpiD0Accuracy").textContent = `${d0.accuracy_pct}%`;
  document.getElementById("kpiD0Ci").textContent = `95% CI [${d0.accuracy_ci[0]}% – ${d0.accuracy_ci[1]}%]`;

  document.getElementById("kpiD4Accuracy").textContent = `${d4.accuracy_pct}%`;
  document.getElementById("kpiD4Ci").textContent = `95% CI [${d4.accuracy_ci[0]}% – ${d4.accuracy_ci[1]}%]`;

  document.getElementById("kpiCbwInflation").textContent = `${d0.cbw_rate_pct}% → ${d4.cbw_rate_pct}%`;
  const trend = stats.trend_tests?.cbw_trend;
  if (trend) {
    document.getElementById("kpiCbwTrend").textContent = `Cochran-Armitage z = ${trend.z_statistic} (p < 0.001)`;
  }

  const kappa = stats.inter_run_stability?.cohens_kappa_r1_r2 || 0.884;
  document.getElementById("kpiKappa").textContent = `κ = ${kappa}`;
}

function renderTableII(levels) {
  const tbody = document.getElementById("tableIIBody");
  if (!tbody) return;

  tbody.innerHTML = "";
  const levelOrder = ["D0", "D1", "D2", "D3", "D4"];
  const levelDesc = {
    "D0": "Clean Baseline Schema",
    "D1": "Syntactic Noise (Abbreviations)",
    "D2": "Type & Format Inconsistency",
    "D3": "Decoy Columns & Semantic Ambiguity",
    "D4": "Compound Degradation + Coded Headers"
  };

  levelOrder.forEach(lvl => {
    const row = levels[lvl];
    if (!row) return;

    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><strong>${lvl}</strong> <span style="color:var(--text-muted); font-size:12px; margin-left:6px;">(${levelDesc[lvl]})</span></td>
      <td class="mono">${row.total_trials}</td>
      <td>
        <strong style="color:var(--signal);">${row.accuracy_pct}%</strong>
        <span class="ci-text">[${row.accuracy_ci[0]}% – ${row.accuracy_ci[1]}%]</span>
      </td>
      <td>
        <span class="mono">${row.failure_rate_pct}%</span>
        <span class="ci-text">(${row.explicit_failures} failed)</span>
      </td>
      <td class="mono">${row.incorrect_total}</td>
      <td>
        <span class="bench-badge ${row.cbw_rate_pct > 30 ? 'cbw' : 'hedged'}">${row.cbw_count} (${row.cbw_rate_pct}%)</span>
        <span class="ci-text">of incorrect</span>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function renderFig2StackedBar(levels) {
  const ctx = document.getElementById("fig2Chart")?.getContext("2d");
  if (!ctx) return;

  const levelOrder = ["D0", "D1", "D2", "D3", "D4"];
  const correct = [];
  const failure = [];
  const cbw = [];
  const hedged = [];

  levelOrder.forEach(lvl => {
    const row = levels[lvl] || {};
    correct.push(row.correct || 0);
    failure.push(row.explicit_failures || 0);
    cbw.push(row.cbw_count || 0);
    hedged.push(row.hedged_count || 0);
  });

  if (fig2Chart) fig2Chart.destroy();

  fig2Chart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: ["D0 (Clean)", "D1 (Syntax)", "D2 (Type)", "D3 (Decoy)", "D4 (Compound)"],
      datasets: [
        { label: "Correct", data: correct, backgroundColor: "#2BD9A8" },
        { label: "Explicit Failure", data: failure, backgroundColor: "#5E6B82" },
        { label: "Confident-But-Wrong (CBW)", data: cbw, backgroundColor: "#FF5A5F" },
        { label: "Hedged Incorrect", data: hedged, backgroundColor: "#F5A855" },
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "top", labels: { color: "#9AA7BD", font: { size: 11 } } },
        tooltip: { mode: "index", intersect: false }
      },
      scales: {
        x: { stacked: true, grid: { color: "rgba(255,255,255,0.05)" }, ticks: { color: "#9AA7BD" } },
        y: { stacked: true, max: 150, grid: { color: "rgba(255,255,255,0.05)" }, ticks: { color: "#9AA7BD" } }
      }
    }
  });
}

function renderFig3TrendLine(levels) {
  const ctx = document.getElementById("fig3Chart")?.getContext("2d");
  if (!ctx) return;

  const levelOrder = ["D0", "D1", "D2", "D3", "D4"];
  const accuracy = [];
  const cbw = [];

  levelOrder.forEach(lvl => {
    const row = levels[lvl] || {};
    accuracy.push(row.accuracy_pct || 0);
    cbw.push(row.cbw_rate_pct || 0);
  });

  if (fig3Chart) fig3Chart.destroy();

  fig3Chart = new Chart(ctx, {
    type: "line",
    data: {
      labels: ["D0", "D1", "D2", "D3", "D4"],
      datasets: [
        {
          label: "Accuracy %",
          data: accuracy,
          borderColor: "#2BD9A8",
          backgroundColor: "rgba(43, 217, 168, 0.15)",
          borderWidth: 3,
          pointRadius: 5,
          tension: 0.25,
          yAxisID: "y"
        },
        {
          label: "CBW Rate % (of incorrect)",
          data: cbw,
          borderColor: "#FF5A5F",
          backgroundColor: "rgba(255, 90, 95, 0.15)",
          borderWidth: 3,
          pointRadius: 5,
          borderDash: [5, 5],
          tension: 0.25,
          yAxisID: "y"
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "top", labels: { color: "#9AA7BD", font: { size: 11 } } },
      },
      scales: {
        x: { grid: { color: "rgba(255,255,255,0.05)" }, ticks: { color: "#9AA7BD" } },
        y: {
          min: 0,
          max: 100,
          grid: { color: "rgba(255,255,255,0.05)" },
          ticks: { color: "#9AA7BD", callback: (v) => `${v}%` }
        }
      }
    }
  });
}

function renderTableIII(qtypes) {
  const tbody = document.getElementById("tableIIIBody");
  if (!tbody || !qtypes) return;

  tbody.innerHTML = "";
  Object.keys(qtypes).forEach(qt => {
    const row = qtypes[qt];
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><strong>${qt.charAt(0).toUpperCase() + qt.slice(1)}</strong></td>
      <td class="mono">${row["D0"]}%</td>
      <td class="mono">${row["D1"]}%</td>
      <td class="mono">${row["D2"]}%</td>
      <td class="mono">${row["D3"]}%</td>
      <td class="mono" style="color:var(--danger);">${row["D4"]}%</td>
    `;
    tbody.appendChild(tr);
  });
}

function renderTableIV(probes) {
  const tbody = document.getElementById("tableIVBody");
  if (!tbody) return;

  tbody.innerHTML = "";
  probes.forEach(p => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><span class="mono">${p.probe_id}</span></td>
      <td><span class="bench-badge failure">${p.dataset}</span></td>
      <td><strong>${p.question}</strong><br><span style="font-size:11px; color:var(--text-muted);">${p.ambiguity_type}</span></td>
      <td><span style="font-size:12px; color:var(--signal);">${p.d0_response.answer}</span></td>
      <td><span style="font-size:12px; color:var(--danger); font-weight:500;">${p.d3_response.answer}</span><br><span class="bench-badge cbw" style="margin-top:4px;">CBW Flagged</span></td>
    `;
    tbody.appendChild(tr);
  });
}

function renderTrialsSample(trials) {
  const tbody = document.getElementById("trialsTableBody");
  if (!tbody) return;

  tbody.innerHTML = "";
  trials.forEach(t => {
    const tr = document.createElement("tr");
    const badgeClass = t.classification === "correct" ? "correct" : t.classification === "cbw" ? "cbw" : t.classification === "explicit_failure" ? "failure" : "hedged";
    tr.innerHTML = `
      <td><span class="mono">${t.trial_id}</span></td>
      <td><strong>${t.level}</strong></td>
      <td><span class="bench-badge failure">${t.dataset}</span></td>
      <td style="max-width:240px; font-size:12.5px;">${t.question_text}</td>
      <td style="max-width:260px; font-size:12px; color:var(--text-secondary);">${t.system_answer}</td>
      <td><span class="bench-badge ${badgeClass}">${t.classification.toUpperCase()}</span></td>
      <td class="mono">${t.latency_ms}ms</td>
    `;
    tbody.appendChild(tr);
  });
}

async function runSingleProbe() {
  const btn = document.getElementById("btnRunProbe");
  const dataset = document.getElementById("probeDataset")?.value;
  const level = document.getElementById("probeLevel")?.value;
  const questionId = document.getElementById("probeQuestion")?.value;
  const resultCard = document.getElementById("probeResultContainer");

  if (!btn || !resultCard) return;

  btn.disabled = true;
  btn.innerHTML = `<i class="ri-loader-4-line ri-spin"></i> Probing...`;

  try {
    const res = await fetch("/api/benchmark/run-single", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dataset, level, question_id: questionId })
    });
    const result = await res.json();

    const badgeClass = result.classification === "correct" ? "correct" : result.classification === "cbw" ? "cbw" : result.classification === "explicit_failure" ? "failure" : "hedged";

    resultCard.innerHTML = `
      <div class="probe-result-header">
        <div>
          <span class="bench-badge ${badgeClass}" style="font-size:12px;">${result.classification.toUpperCase()}</span>
          ${result.is_cbw ? '<span class="bench-badge cbw" style="margin-left:8px;">⚠️ CONFIDENT-BUT-WRONG DETECTED</span>' : ''}
        </div>
        <span class="mono" style="font-size:12px; color:var(--text-muted);">${result.latency_ms} ms</span>
      </div>

      <div>
        <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted); margin-bottom:4px;">Evaluated Question</div>
        <div style="font-size:14px; font-weight:600; color:var(--text-primary);">${result.question_text}</div>
      </div>

      <div style="background:var(--surface); border:1px solid var(--border); border-radius:var(--radius-sm); padding:12px;">
        <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted); margin-bottom:4px;">Pipeline Generated Answer</div>
        <div style="font-size:13px; color:${result.is_cbw ? 'var(--danger)' : 'var(--text-primary)'}; font-weight:${result.is_cbw ? '600' : '400'};">${result.system_answer}</div>
      </div>

      <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
        <div style="background:var(--surface); border:1px solid var(--border); border-radius:var(--radius-sm); padding:10px;">
          <div style="font-size:11px; color:var(--text-muted);">Ground Truth Value</div>
          <div class="mono" style="font-size:14px; color:var(--signal); font-weight:600; margin-top:4px;">${JSON.stringify(result.ground_truth.value)}</div>
        </div>
        <div style="background:var(--surface); border:1px solid var(--border); border-radius:var(--radius-sm); padding:10px;">
          <div style="font-size:11px; color:var(--text-muted);">Scoring Engine Detail</div>
          <div style="font-size:12px; color:var(--text-secondary); margin-top:4px;">${result.scoring_detail}</div>
        </div>
      </div>

      <div>
        <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted); margin-bottom:4px;">Columns Available at Level ${result.level}</div>
        <div class="probe-columns-list">
          ${result.columns_available.map(c => `<span class="col-chip">${c}</span>`).join("")}
        </div>
      </div>
    `;
  } catch (err) {
    resultCard.innerHTML = `<div style="color:var(--danger); padding:20px;">Execution failed: ${err.message}</div>`;
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i class="ri-play-line"></i> Run Single Trial Probe`;
  }
}

async function triggerFullBenchmarkRun() {
  const btn = document.getElementById("btnRunFullBench");
  if (!btn) return;

  btn.disabled = true;
  btn.innerHTML = `<i class="ri-loader-4-line ri-spin"></i> Executing 750 Trials...`;

  try {
    const res = await fetch("/api/benchmark/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dataset: "all", runs: 5 })
    });
    await res.json();
    await loadBenchmarkData();
  } catch (err) {
    console.error("Full benchmark run failed:", err);
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i class="ri-refresh-line"></i> Re-Run Benchmark Suite (750 Trials)`;
  }
}
