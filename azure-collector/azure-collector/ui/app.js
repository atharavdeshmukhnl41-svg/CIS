const BASE_URL = "http://127.0.0.1:8000";
 
// =========================
// VM RCA
// =========================
async function getVMRCA() {
    const name = document.getElementById("vmName").value;
    const port = document.getElementById("vmPort").value;
 
    const res = await fetch(`${BASE_URL}/rca/vm?name=${name}&port=${port}`);
    const data = await res.json();
 
    document.getElementById("vmResult").textContent =
        JSON.stringify(data, null, 2);
}
 
// =========================
// APP RCA
// =========================
async function getAppRCA() {
    const name = document.getElementById("appName").value;
    const port = document.getElementById("appPort").value;
 
    const res = await fetch(`${BASE_URL}/rca/app?name=${name}&port=${port}`);
    const data = await res.json();
 
    document.getElementById("appResult").textContent =
        JSON.stringify(data, null, 2);
}
 
// =========================
// METRICS
// =========================
async function getMetrics() {
    const vm = document.getElementById("metricVM").value;
 
    const res = await fetch(`${BASE_URL}/metrics?vm=${vm}`);
    const data = await res.json();
 
    document.getElementById("metricResult").textContent =
        JSON.stringify(data, null, 2);
}