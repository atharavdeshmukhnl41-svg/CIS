const API = "http://127.0.0.1:9000";

 

// ---------------- KPI ----------------

async function updateKPIs(vm) {

  try {

    const res = await fetch(`${API}/metrics?vm=${vm}`);

    const data = await res.json();

 

    document.getElementById("cpuCard").innerText = "CPU: " + data.cpu;

    document.getElementById("netCard").innerText =

      "Network: " + (data.network_in + data.network_out);

    document.getElementById("statusCard").innerText =

      "Status: " + data.status;

 

  } catch (e) {

    console.log("KPI error:", e);

  }

}

 

// ---------------- RCA ----------------

async function runRCA() {

  const vm = document.getElementById("vmName").value;

  const port = document.getElementById("port").value;

 

  try {

    const res = await fetch(`${API}/rca/vm?name=${vm}&port=${port}`);

    const data = await res.json();

 

    document.getElementById("rcaOutput").innerText =

      JSON.stringify(data, null, 2);

 

    updateKPIs(vm);

 

  } catch (e) {

    document.getElementById("rcaOutput").innerText = "Error";

  }

}

 

// ---------------- INCIDENT ----------------

async function loadIncidents() {

  const port = document.getElementById("port").value || 22;

 

  try {

    const res = await fetch(`${API}/incident/global?port=${port}`);

    const data = await res.json();

 

    document.getElementById("incidentOutput").innerText =

      JSON.stringify(data, null, 2);

 

  } catch (e) {

    console.log("Incident error:", e);

  }

}

 

// ---------------- ALERT ----------------

async function loadAlerts() {

  const vm = document.getElementById("vmName").value;

 

  try {

    const res = await fetch(`${API}/alerts?vm=${vm}`);

    const data = await res.json();

 

    document.getElementById("alertOutput").innerText =

      JSON.stringify(data, null, 2);

 

  } catch (e) {

    console.log("Alert error:", e);

  }

}

 

// ---------------- TOPOLOGY ----------------

async function loadTopology() {

  try {

    const res = await fetch(`${API}/topology`);

    const data = await res.json();

 

    console.log("Topology data:", data);

 

    renderGraph(data.nodes, data.edges);

 

  } catch (e) {

    console.log("Topology error:", e);

  }

}

 

// ---------------- AUTO REFRESH ----------------

setInterval(() => {

  const vm = document.getElementById("vmName").value;

  if (vm) updateKPIs(vm);

}, 5000);

// -------------------------
// CREATE APPROVAL REQUEST
// -------------------------
async function requestFix(action) {
 
const vm = document.getElementById("vmName").value.trim();
const port = document.getElementById("port").value.trim();
 
// ✅ VALIDATION (CRITICAL FIX)
if (!vm) {
  alert("VM name is required");
  return;
}
 
if (action === "fix_nsg" && !port) {
  alert("Port is required for NSG fix");
  return;
}
 
const res = await fetch(`${API}/approval/request`, {
  method: "POST",
  headers: {"Content-Type": "application/json"},
  body: JSON.stringify({ action, vm, port })
});
 
const data = await res.json();
 
alert("Request Created: " + data.id);
 
loadApprovals();
}
 
// -------------------------
// LOAD REQUESTS
// -------------------------
async function loadApprovals() {
 
  const res = await fetch(`${API}/approval/list`);
  const data = await res.json();
 
  document.getElementById("approvalOutput").innerText =
    JSON.stringify(data, null, 2);
}
 
// -------------------------
// APPROVE REQUEST
// -------------------------
async function approveRequest() {
 
const id = document.getElementById("approvalId").value.trim();
 
if (!id) {
  alert("Approval ID required");
  return;
}
 
const res = await fetch(`${API}/approval/approve`, {
  method: "POST",
  headers: {"Content-Type": "application/json"},
  body: JSON.stringify({ id: id })
});
 
const data = await res.json();
 
alert("Approved: " + data.status);
 
loadApprovals();
}

async function runRCA() {
 
const vm = document.getElementById("vmName").value.trim();
const port = document.getElementById("port").value.trim();
 
if (!vm) {
  alert("Enter VM name");
  return;
}
 
if (!port) {
  alert("Enter port");
  return;
}
 
try {
  const res = await fetch(`${API}/rca/vm?name=${vm}&port=${port}`);
  const data = await res.json();
 
  document.getElementById("rcaOutput").innerText =
   JSON.stringify(data, null, 2);
 
  updateKPIs(vm);
 
} catch (e) {
  document.getElementById("rcaOutput").innerText = "Error";
}
}