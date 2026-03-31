const API = "http://127.0.0.1:9000";
 
function formatOutput(data) {
    return JSON.stringify(data, null, 2);
}
 
// ==========================
// VM RCA
// ==========================
async function checkVM() {
    const nameEl = document.getElementById("vmName");
    const portEl = document.getElementById("vmPort");
    const output = document.getElementById("vmResult");
 
    if (!nameEl || !portEl || !output) return;
 
    const name = nameEl.value;
    const port = portEl.value || 22;
 
    output.innerText = "Loading...";
 
    if (!name) {
        output.innerText = "❌ VM name required";
        return;
    }
 
    try {
        const res = await fetch(`${API}/rca/vm?name=${name}&port=${port}`);
        const data = await res.json();
 
        output.innerText = formatOutput(data);
        window.lastManualVMCheck = Date.now();
 
    } catch (err) {
        output.innerText = "❌ Error: " + err;
    }
}
 
// ==========================
// APPLICATION RCA
// ==========================
async function checkApp() {
    const nameEl = document.getElementById("appName");
    const portEl = document.getElementById("appPort");
    const output = document.getElementById("appResult");
 
    if (!nameEl || !portEl || !output) return;
 
    const name = nameEl.value;
    const port = portEl.value || 22;
 
    output.innerText = "Loading...";
 
    if (!name) {
        output.innerText = "❌ App name required";
        return;
    }
 
    try {
        const res = await fetch(`${API}/rca/app?name=${name}&port=${port}`);
        const data = await res.json();
 
        output.innerText = formatOutput(data);
 
    } catch (err) {
        output.innerText = "❌ Error: " + err;
    }
}
 
// ==========================
// METRICS
// ==========================
async function getMetrics() {
    const vmEl = document.getElementById("metricsVm");
    const output = document.getElementById("metricsResult");
 
    if (!vmEl || !output) return;
 
    const vm = vmEl.value;
 
    output.innerText = "Loading...";
 
    if (!vm) {
        output.innerText = "❌ VM required";
        return;
    }
 
    try {
        const res = await fetch(`${API}/metrics?vm=${vm}`);
        const data = await res.json();
 
        output.innerText = formatOutput(data);
 
    } catch (err) {
        output.innerText = "❌ Error: " + err;
    }
}
 
// ==========================
// ALERTS
// ==========================
async function loadAlerts() {
    const vmEl = document.getElementById("alertVM");
    const output = document.getElementById("alertResult");
 
    if (!vmEl || !output) return;
 
    const vm = vmEl.value;
 
    output.innerText = "Loading...";
 
    if (!vm) {
        output.innerText = "❌ VM required";
        return;
    }
 
    try {
        const res = await fetch(`${API}/alerts?vm=${vm}`);
        const data = await res.json();
 
        output.innerText = formatOutput(data);
 
    } catch (err) {
        output.innerText = "❌ Error: " + err;
    }
}
 
// ==========================
// AUTO REFRESH (SAFE)
// ==========================
function startAutoRefresh() {
  setInterval(async () => {
    const vm = document.getElementById("vmName").value;
    if (!vm) return;
 
    try {
      // 🔥 ALWAYS CALL METRICS FIRST (FOR FRESH STATE)
      const mRes = await fetch(`${API}/metrics?vm=${vm}`);
      const mData = await mRes.json();
 
      document.getElementById("metricsResult").innerText =
        JSON.stringify(mData, null, 2);
 
      // ===== ALERTS =====
      const aRes = await fetch(`${API}/alerts?vm=${vm}`);
      const aData = await aRes.json();
 
      document.getElementById("alertResult").innerText =
        JSON.stringify(aData, null, 2);
 
      // ===== RCA =====
      const port = document.getElementById("port").value || 22;
 
      const rcaRes = await fetch(
        `${API}/rca/vm?name=${vm}&port=${port}`
      );
      const rcaData = await rcaRes.json();
 
      document.getElementById("vmResult").innerText =
        JSON.stringify(rcaData, null, 2);
 
    } catch (err) {
      console.log("Auto refresh error:", err);
    }
 
  }, 5000); // 🔥 reduce to 5 sec
}
 
// ==========================
// INIT (CRITICAL FIX)
// ==========================
document.addEventListener("DOMContentLoaded", function () {
    startAutoRefresh();
});