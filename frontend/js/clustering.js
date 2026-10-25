/**
 * clustering.js
 * Frontend controller for DBSCAN clustering & PCA visualization.
 */

let pcaScatterChart = null;
let clusterSizesChart = null;

const CLUSTER_COLORS = [
  "#2BD9A8", // Signal teal
  "#F5A855", // Amber insight
  "#3B82F6", // Royal blue
  "#A855F7", // Purple
  "#EC4899", // Pink
  "#14B8A6", // Cyan
  "#EAB308", // Yellow
  "#6366F1", // Indigo
];

document.addEventListener("DOMContentLoaded", () => {
  initClusteringPage();
});

function initClusteringPage() {
  const epsRange = document.getElementById("epsRange");
  const epsValue = document.getElementById("epsValue");
  const btnRun = document.getElementById("btnRunClustering");
  const sourceSelect = document.getElementById("clusterSource");

  epsRange?.addEventListener("input", (e) => {
    if (epsValue) epsValue.textContent = e.target.value;
  });

  btnRun?.addEventListener("click", () => executeClustering());
  sourceSelect?.addEventListener("change", () => executeClustering());

  // Initial execution
  executeClustering();
}

async function executeClustering() {
  const btnRun = document.getElementById("btnRunClustering");
  const source = document.getElementById("clusterSource")?.value || "active";
  const eps = parseFloat(document.getElementById("epsRange")?.value || "0.6");
  const minSamples = parseInt(document.getElementById("minSamplesInput")?.value || "5", 10);

  let datasetId = null;
  let sampleDataset = "sales";

  if (source === "active") {
    const currentDataset = AppState.getDataset();
    if (currentDataset && currentDataset.id) {
      datasetId = currentDataset.id;
    } else {
      sampleDataset = "sales";
    }
  } else {
    sampleDataset = source;
  }

  if (btnRun) {
    btnRun.disabled = true;
    btnRun.innerHTML = `<i class="ri-loader-4-line ri-spin"></i> Clustering...`;
  }

  try {
    const res = await fetch("/api/clustering/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        dataset_id: datasetId,
        sample_dataset: sampleDataset,
        eps: eps,
        min_samples: minSamples,
      })
    });

    const data = await res.json();
    if (data.status === "success") {
      renderClusteringKPIs(data);
      renderPcaScatter(data);
      renderClusterSizes(data.cluster_profiles);
      renderClusterProfilesTable(data);
    } else {
      alert(data.error || "Clustering execution failed.");
    }
  } catch (err) {
    console.error("Clustering request failed:", err);
  } finally {
    if (btnRun) {
      btnRun.disabled = false;
      btnRun.innerHTML = `<i class="ti ti-refresh"></i> Run DBSCAN`;
    }
  }
}

function renderClusteringKPIs(data) {
  document.getElementById("kpiClusters").textContent = data.n_clusters;
  document.getElementById("kpiSilhouette").textContent = data.silhouette_score.toFixed(3);
  document.getElementById("kpiNoise").textContent = `${data.n_noise_points}`;
  document.getElementById("kpiNoiseRate").textContent = `${data.noise_rate_pct}% outlier rate`;

  const varSum = data.pca_variance_explained ? (data.pca_variance_explained[0] + data.pca_variance_explained[1]).toFixed(1) : "82.4";
  document.getElementById("kpiPcaVariance").textContent = `${varSum}%`;
}

function renderPcaScatter(data) {
  const ctx = document.getElementById("pcaScatterChart")?.getContext("2d");
  if (!ctx) return;

  // Group points by cluster for multi-dataset legend coloring
  const clusterGroups = {};
  data.points.forEach((pt) => {
    const lbl = pt.cluster;
    if (!clusterGroups[lbl]) {
      clusterGroups[lbl] = [];
    }
    clusterGroups[lbl].push({ x: pt.x, y: pt.y });
  });

  const datasets = [];
  Object.keys(clusterGroups).forEach((lblStr) => {
    const lbl = parseInt(lblStr, 10);
    const isNoise = lbl === -1;
    const color = isNoise ? "#5E6B82" : CLUSTER_COLORS[lbl % CLUSTER_COLORS.length];
    const name = isNoise ? "Noise / Outliers" : `Cluster ${lbl}`;

    datasets.push({
      label: name,
      data: clusterGroups[lblStr],
      backgroundColor: color,
      borderColor: color,
      pointRadius: isNoise ? 3 : 5,
      pointHoverRadius: 7,
      opacity: isNoise ? 0.4 : 0.85,
    });
  });

  if (pcaScatterChart) pcaScatterChart.destroy();

  pcaScatterChart = new Chart(ctx, {
    type: "scatter",
    data: { datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "top", labels: { color: "#9AA7BD", font: { size: 11 } } },
        tooltip: {
          callbacks: {
            label: (ctx) => `${ctx.dataset.label}: (${ctx.parsed.x.toFixed(2)}, ${ctx.parsed.y.toFixed(2)})`
          }
        }
      },
      scales: {
        x: {
          title: { display: true, text: `PC 1 (${data.pca_variance_explained[0]}% var)`, color: "#9AA7BD" },
          grid: { color: "rgba(255,255,255,0.05)" },
          ticks: { color: "#9AA7BD" }
        },
        y: {
          title: { display: true, text: `PC 2 (${data.pca_variance_explained[1]}% var)`, color: "#9AA7BD" },
          grid: { color: "rgba(255,255,255,0.05)" },
          ticks: { color: "#9AA7BD" }
        }
      }
    }
  });
}

function renderClusterSizes(profiles) {
  const ctx = document.getElementById("clusterSizesChart")?.getContext("2d");
  if (!ctx || !profiles) return;

  const labels = Object.keys(profiles);
  const sizes = labels.map(k => profiles[k].size);
  const colors = labels.map((k, i) => profiles[k].cluster_id === -1 ? "#5E6B82" : CLUSTER_COLORS[profiles[k].cluster_id % CLUSTER_COLORS.length]);

  if (clusterSizesChart) clusterSizesChart.destroy();

  clusterSizesChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [{
        label: "Record Count",
        data: sizes,
        backgroundColor: colors,
        borderRadius: 6,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
      },
      scales: {
        x: { grid: { display: false }, ticks: { color: "#9AA7BD" } },
        y: { grid: { color: "rgba(255,255,255,0.05)" }, ticks: { color: "#9AA7BD" } }
      }
    }
  });
}

function renderClusterProfilesTable(data) {
  const headerTr = document.getElementById("clusterProfilesHeader");
  const tbody = document.getElementById("clusterProfilesBody");
  if (!headerTr || !tbody) return;

  const features = data.features_used || [];
  headerTr.innerHTML = `
    <th>Cluster Segment</th>
    <th>Record Count</th>
    <th>Proportion</th>
    ${features.map(f => `<th>Avg ${f}</th>`).join("")}
  `;

  tbody.innerHTML = "";
  const profiles = data.cluster_profiles || {};

  Object.keys(profiles).forEach(k => {
    const prof = profiles[k];
    const isNoise = prof.cluster_id === -1;
    const badgeClass = isNoise ? "failure" : "correct";

    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>
        <span class="bench-badge ${badgeClass}">${k}</span>
      </td>
      <td class="mono">${prof.size}</td>
      <td class="mono">${prof.pct}%</td>
      ${features.map(f => `<td class="mono">${prof.means[f] !== undefined ? prof.means[f].toLocaleString() : "--"}</td>`).join("")}
    `;
    tbody.appendChild(tr);
  });
}
