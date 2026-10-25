/* ============================================================
   forecast.js — metric picker + Prophet / LinearRegression rendering.
   ============================================================ */

document.addEventListener("DOMContentLoaded", async () => {
  const dataset = requireDatasetOrRedirect();
  if (!dataset) return;

  const datasetId = dataset.id || dataset.dataset_id || 1;
  const metricSelect = document.getElementById("metric-select");
  const modelSelect = document.getElementById("model-select");
  const horizonInput = document.getElementById("horizon-input");
  const runBtn = document.getElementById("run-forecast");
  const resultEl = document.getElementById("forecast-result");

  try {
    const dashboard = await apiFetch(`/analytics/${datasetId}/dashboard`);
    const numericKeys = Object.keys(dashboard.kpis).filter((k) => k.startsWith("total_")).map((k) => k.replace("total_", ""));
    const fallback = numericKeys.length ? numericKeys : ["revenue"];
    metricSelect.innerHTML = fallback.map((m) => `<option value="${m}">${m.charAt(0).toUpperCase() + m.slice(1)}</option>`).join("");
  } catch {
    metricSelect.innerHTML = `<option value="revenue">Revenue</option><option value="profit">Profit</option>`;
  }

  runBtn.addEventListener("click", async () => {
    const metric = metricSelect.value;
    const model = modelSelect?.value || "prophet";
    const horizon = parseInt(horizonInput.value, 10) || 6;
    resultEl.innerHTML = `<div class="empty-state"><span class="spinner"></span></div>`;

    try {
      const result = await apiFetch("/forecast", {
        method: "POST",
        body: JSON.stringify({ dataset_id: datasetId, metric, horizon_periods: horizon, model }),
      });

      if (result.error) {
        resultEl.innerHTML = `<div class="empty-state"><i class="ti ti-alert-circle"></i>${result.error}</div>`;
        return;
      }

      const metrics = result.metrics || { r2: result.confidence, rmse: "—", mape: "—" };
      const comp = result.model_comparison;

      resultEl.innerHTML = `
        <div class="grid grid-4" style="margin-bottom:18px">
          <div class="card kpi-card">
            <div class="card-title"><i class="ti ti-cpu"></i> Active Model</div>
            <div class="kpi-value" style="font-size:20px; color:var(--signal);">${result.model_used === 'prophet' ? 'Prophet (Additive)' : 'Linear Regression'}</div>
            <div class="stat-tag">Trend &amp; Seasonality</div>
          </div>
          <div class="card kpi-card">
            <div class="card-title"><i class="ti ti-chart-line"></i> Goodness of Fit (R²)</div>
            <div class="kpi-value">${(metrics.r2 * 100).toFixed(1)}%</div>
            <div class="stat-tag">Variance Explained</div>
          </div>
          <div class="card kpi-card">
            <div class="card-title"><i class="ti ti-calculator"></i> Error Metric (RMSE)</div>
            <div class="kpi-value">${typeof metrics.rmse === 'number' ? metrics.rmse.toLocaleString() : metrics.rmse}</div>
            <div class="stat-tag">Root Mean Sq Error</div>
          </div>
          <div class="card kpi-card">
            <div class="card-title"><i class="ti ti-percentage"></i> MAPE Accuracy</div>
            <div class="kpi-value" style="color:var(--signal);">${typeof metrics.mape === 'number' ? metrics.mape + '%' : metrics.mape}</div>
            <div class="stat-tag">Mean Abs Pct Error</div>
          </div>
        </div>

        <div class="card" style="margin-bottom:20px">
          <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:12px;">
            <div class="card-title"><i class="ti ti-chart-line"></i> ${metric} — Historical Actuals vs Projected Path</div>
            <span class="bench-badge correct">${result.model_used.toUpperCase()}</span>
          </div>
          <div style="height:320px"><canvas id="forecast-chart"></canvas></div>
        </div>

        ${comp ? `
        <div class="card" style="margin-bottom:20px">
          <div class="card-title" style="font-size:15px; font-weight:600; margin-bottom:12px;"><i class="ti ti-arrows-diff"></i> Side-by-Side Model Comparison (Prophet vs. Linear Regression)</div>
          <div class="bench-table-wrap">
            <table class="bench-table">
              <thead>
                <tr>
                  <th>Model Architecture</th>
                  <th>Fit Quality (R²)</th>
                  <th>RMSE Error</th>
                  <th>MAPE Error</th>
                  <th>Projected Next Value</th>
                </tr>
              </thead>
              <tbody>
                <tr style="${result.model_used === 'prophet' ? 'background:rgba(43,217,168,0.06); font-weight:600;' : ''}">
                  <td><strong>Prophet (Additive Seasonality)</strong></td>
                  <td class="mono">${(comp.prophet.r2 * 100).toFixed(1)}%</td>
                  <td class="mono">${comp.prophet.rmse.toLocaleString()}</td>
                  <td class="mono">${comp.prophet.mape}%</td>
                  <td class="mono" style="color:var(--signal);">${comp.prophet.forecast_values[0].toLocaleString()}</td>
                </tr>
                <tr style="${result.model_used === 'linear_regression' ? 'background:rgba(43,217,168,0.06); font-weight:600;' : ''}">
                  <td><strong>Linear Regression (OLS)</strong></td>
                  <td class="mono">${(comp.linear_regression.r2 * 100).toFixed(1)}%</td>
                  <td class="mono">${comp.linear_regression.rmse.toLocaleString()}</td>
                  <td class="mono">${comp.linear_regression.mape}%</td>
                  <td class="mono">${comp.linear_regression.forecast_values[0].toLocaleString()}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        ` : ''}

        <div class="card">
          <div class="card-title" style="font-size:15px; font-weight:600; margin-bottom:12px;"><i class="ti ti-table"></i> Predicted Values &amp; 95% Confidence Interval Cone</div>
          <div class="bench-table-wrap">
            <table class="bench-table">
              <thead>
                <tr>
                  <th>Period</th>
                  <th>Point Prediction</th>
                  <th>95% Lower Bound</th>
                  <th>95% Upper Bound</th>
                  <th>Confidence Band Width</th>
                </tr>
              </thead>
              <tbody>
                ${result.predictions.map((p) => {
                  const spread = (p.upper_bound - p.lower_bound).toFixed(2);
                  return `
                    <tr>
                      <td class="primary mono">${p.period}</td>
                      <td class="mono" style="font-weight:600; color:var(--signal);">${p.value.toLocaleString()}</td>
                      <td class="mono" style="color:var(--text-muted);">${p.lower_bound ? p.lower_bound.toLocaleString() : '—'}</td>
                      <td class="mono" style="color:var(--text-muted);">${p.upper_bound ? p.upper_bound.toLocaleString() : '—'}</td>
                      <td class="mono">±${(spread / 2).toLocaleString()}</td>
                    </tr>
                  `;
                }).join("")}
              </tbody>
            </table>
          </div>
        </div>`;

      renderChart("forecast-chart", result.chart);
    } catch (err) {
      resultEl.innerHTML = `<div class="empty-state"><i class="ti ti-alert-circle"></i>${err.message}</div>`;
    }
  });
});
