const API = "http://127.0.0.1:9000";

// Global state
let currentVM = '';
let currentPort = '22';

// Initialize the dashboard
document.addEventListener('DOMContentLoaded', function() {
  initializeDashboard();
});

function initializeDashboard() {
  // Set up event listeners
  document.getElementById('runRcaBtn').addEventListener('click', runRCA);
  document.getElementById('refreshBtn').addEventListener('click', refreshAll);
  document.getElementById('loadTopologyBtn').addEventListener('click', async () => {
    await refreshTopology();
    await populateVMSelector();
    loadTopology();
  });
  document.getElementById('loadAlertsBtn').addEventListener('click', loadAlerts);
  document.getElementById('loadIncidentsBtn').addEventListener('click', loadIncidents);

  // VM selector change
  document.getElementById('vmSelector').addEventListener('change', function(e) {
    currentVM = e.target.value;
    if (currentVM) {
      updateMetrics(currentVM);
    }
  });

  // Port selector change
  document.getElementById('portSelector').addEventListener('change', function(e) {
    currentPort = e.target.value;
  });

  // Auto-refresh metrics every 30 seconds
  setInterval(() => {
    if (currentVM) {
      updateMetrics(currentVM);
    }
  }, 30000);

  // Populate VM selector immediately if possible, then refresh topology and update it again.
  populateVMSelector().catch(() => {}).then(async () => {
    await refreshTopology();
    await populateVMSelector();
    loadTopology();
  });
}

// ---------------- RCA Functions ----------------

async function runRCA() {
  const vm = document.getElementById('vmSelector').value;
  const port = document.getElementById('portSelector').value;

  if (!vm) {
    showNotification('Please select a VM first', 'warning');
    return;
  }

  currentVM = vm;
  currentPort = port;

  // Show loading state
  showRCALoading();

  try {
    const res = await fetch(`${API}/rca/vm?name=${vm}&port=${port}`);
    const data = await res.json();

    if (data.error) {
      showRCAError(data.error);
      return;
    }

    renderRCA(data);

    // Automatically generate alerts and incidents
    await generateAlerts(vm, port);
    await loadIncidents();

    // Update metrics
    updateMetrics(vm);

  } catch (e) {
    console.error('RCA error:', e);
    showRCAError('Failed to run RCA analysis');
  }
}

function showRCALoading() {
  document.getElementById('rcaPath').innerHTML = '<div class="loading"><i class="fas fa-search"></i> Analyzing root cause...</div>';
  document.getElementById('rcaIssues').innerHTML = '';
  document.getElementById('rcaRootCause').innerHTML = '';
  document.getElementById('rcaSuggestions').innerHTML = '';
  document.getElementById('rcaConfidence').innerHTML = '';
}

function showRCAError(error) {
  document.getElementById('rcaPath').innerHTML = `<div class="empty-state"><i class="fas fa-exclamation-triangle"></i><h4>Analysis Failed</h4><p>${error}</p></div>`;
}

function renderRCA(data) {
  // Render path flow
  renderPathFlow(data.path || []);

  // Render issues
  renderIssues(data.issues || []);

  // Render root cause
  renderRootCause(data.root_cause);
  renderImpact(data.impact);

  // Render suggestions (use 'fix' field from RCA engine)
  renderSuggestions(data.fix ? [data.fix] : []);

  // Render confidence (fix percentage calculation)
  renderConfidence(data.confidence || 0);
}

function renderPathFlow(path) {
  const pathContainer = document.getElementById('rcaPath');

  if (!path || path.length === 0) {
    pathContainer.innerHTML = '<div class="empty-state"><i class="fas fa-route"></i><h4>No Path Data</h4></div>';
    return;
  }

  let html = '<div class="rca-path-flow">';

  path.forEach((step, index) => {
    const status = getStepStatus(step);
    html += `
      <div class="path-step">
        <div class="path-step-icon ${status.class}">
          <i class="fas ${status.icon}"></i>
        </div>
        <div class="path-step-label">${step.name || step}</div>
      </div>
    `;

    if (index < path.length - 1) {
      html += '<i class="fas fa-arrow-right" style="color: var(--text-muted); margin: 0 8px;"></i>';
    }
  });

  html += '</div>';
  pathContainer.innerHTML = html;
}

function getStepStatus(step) {
  // Determine status based on step properties
  if (step.status === 'error' || step.type === 'failure') {
    return { class: 'error', icon: 'fa-times' };
  } else if (step.status === 'warning') {
    return { class: 'warning', icon: 'fa-exclamation-triangle' };
  } else if (step.status === 'success' || step.type === 'healthy') {
    return { class: 'success', icon: 'fa-check' };
  }
  return { class: 'info', icon: 'fa-info' };
}

function renderIssues(issues) {
  const issuesContainer = document.getElementById('rcaIssues');

  if (!issues || issues.length === 0) {
    issuesContainer.innerHTML = '<div class="empty-state"><i class="fas fa-check-circle"></i><h4>No Issues Found</h4></div>';
    return;
  }

  let html = '';
  issues.forEach(issue => {
    const severity = getIssueSeverity(issue);
    html += `
      <div class="issue-item">
        <i class="fas ${severity.icon} issue-icon ${severity.class}"></i>
        <div class="issue-text">${issue.description || issue.title || issue}</div>
      </div>
    `;
  });

  issuesContainer.innerHTML = html;
}

function getIssueSeverity(issue) {
  const severity = issue.severity || issue.level || 'info';
  switch (severity.toLowerCase()) {
    case 'critical':
    case 'error':
      return { class: 'error', icon: 'fa-times-circle' };
    case 'warning':
    case 'medium':
      return { class: 'warning', icon: 'fa-exclamation-triangle' };
    case 'low':
    case 'info':
      return { class: 'info', icon: 'fa-info-circle' };
    default:
      return { class: 'success', icon: 'fa-check-circle' };
  }
}

function renderRootCause(rootCause) {
  const rootCauseContainer = document.getElementById('rcaRootCause');

  if (!rootCause) {
    rootCauseContainer.innerHTML = '';
    return;
  }

  rootCauseContainer.innerHTML = `
    <h4><i class="fas fa-bullseye"></i> Root Cause Identified</h4>
    <p>${rootCause.description || rootCause}</p>
  `;
}

function renderImpact(impact) {
  const impactContainer = document.getElementById('rcaImpact');

  if (!impact) {
    impactContainer.innerHTML = '';
    return;
  }

  impactContainer.innerHTML = `
    <h4><i class="fas fa-bolt"></i> Impact</h4>
    <p>${impact}</p>
  `;
}

function renderSuggestions(suggestions) {
  const suggestionsContainer = document.getElementById('rcaSuggestions');

  if (!suggestions || suggestions.length === 0) {
    suggestionsContainer.innerHTML = '<div class="empty-state"><i class="fas fa-lightbulb"></i><h4>No Suggestions Available</h4></div>';
    return;
  }

  let html = '';
  suggestions.forEach(suggestion => {
    html += `
      <div class="suggestion-item">
        <i class="fas fa-tools suggestion-icon"></i>
        <div class="suggestion-text">${suggestion.description || suggestion}</div>
      </div>
    `;
  });

  suggestionsContainer.innerHTML = html;
}

function renderConfidence(confidence) {
  const confidenceContainer = document.getElementById('rcaConfidence');
  // RCA engine returns confidence as percentage (0-100), not decimal
  const percentage = Math.min(100, Math.max(0, confidence || 0));

  confidenceContainer.innerHTML = `
    <div class="confidence-bar">
      <div class="confidence-fill" style="width: ${percentage}%"></div>
    </div>
    <div class="confidence-text">${percentage}% Confidence</div>
  `;
}

// ---------------- Alerts Functions ----------------

async function loadAlerts() {
  const vm = document.getElementById('vmSelector').value;
  const port = document.getElementById('portSelector').value;

  if (!vm) {
    showAlertsEmpty('Select a VM to view alerts');
    return;
  }

  try {
    const res = await fetch(`${API}/alerts/evaluate?vm=${encodeURIComponent(vm)}&port=${encodeURIComponent(port)}`);
    const data = await res.json();

    if (data.error) {
      showAlertsError(data.error);
      return;
    }

    renderAlerts(data.alerts || []);

  } catch (e) {
    console.error('Alerts error:', e);
    showAlertsError('Failed to load alerts');
  }
}

async function generateAlerts(vm, port) {
  try {
    await fetch(`${API}/alerts/evaluate?vm=${encodeURIComponent(vm)}&port=${encodeURIComponent(port)}`);
    await loadAlerts(); // Refresh alerts display
  } catch (e) {
    console.warn('Alert generation failed:', e);
  }
}

function showAlertsEmpty(message) {
  document.getElementById('alertsList').innerHTML = `<div class="empty-state"><i class="fas fa-bell-slash"></i><h4>No Alerts</h4><p>${message}</p></div>`;
}

function showAlertsError(error) {
  document.getElementById('alertsList').innerHTML = `<div class="empty-state"><i class="fas fa-exclamation-triangle"></i><h4>Error Loading Alerts</h4><p>${error}</p></div>`;
}

function renderAlerts(alerts) {
  const alertsContainer = document.getElementById('alertsList');

  if (!alerts || alerts.length === 0) {
    showAlertsEmpty('No active alerts');
    return;
  }

  let html = '';
  alerts.forEach(alert => {
    const severity = getAlertSeverity(alert);
    const timeAgo = getTimeAgo(alert.created_at);

    html += `
      <div class="alert-item ${severity.class}">
        <i class="fas ${severity.icon} alert-icon"></i>
        <div class="alert-content">
          <div class="alert-title">${alert.issue?.title || alert.title || 'Alert'}</div>
          <div class="alert-description">${alert.issue?.description || alert.description || ''}</div>
          <div class="alert-time">${timeAgo}</div>
        </div>
      </div>
    `;
  });

  alertsContainer.innerHTML = html;
}

function getAlertSeverity(alert) {
  const severity = alert.issue?.severity || alert.severity || 'info';
  switch (severity.toLowerCase()) {
    case 'critical':
      return { class: 'critical', icon: 'fa-times-circle' };
    case 'high':
    case 'error':
      return { class: 'high', icon: 'fa-exclamation-circle' };
    case 'medium':
    case 'warning':
      return { class: 'medium', icon: 'fa-exclamation-triangle' };
    case 'low':
      return { class: 'low', icon: 'fa-info-circle' };
    default:
      return { class: 'info', icon: 'fa-info-circle' };
  }
}

// ---------------- Incidents Functions ----------------

async function loadIncidents() {
  const vm = document.getElementById('vmSelector').value;
  const port = document.getElementById('portSelector').value;

  try {
    const query = new URLSearchParams();
    query.set("port", port);
    if (vm) query.set("vm", vm);

    const res = await fetch(`${API}/incident/global?${query.toString()}`);
    const data = await res.json();

    if (data.error) {
      showIncidentsError(data.error);
      return;
    }

    renderIncidents(data.incidents || []);

  } catch (e) {
    console.error('Incidents error:', e);
    showIncidentsError('Failed to load incidents');
  }
}

function showIncidentsError(error) {
  document.getElementById('incidentsList').innerHTML = `<div class="empty-state"><i class="fas fa-exclamation-triangle"></i><h4>Error Loading Incidents</h4><p>${error}</p></div>`;
}

function renderIncidents(incidents) {
  const incidentsContainer = document.getElementById('incidentsList');

  if (!incidents || incidents.length === 0) {
    incidentsContainer.innerHTML = '<div class="empty-state"><i class="fas fa-check-circle"></i><h4>No Active Incidents</h4><p>All systems operational</p></div>';
    return;
  }

  let html = '';
  incidents.forEach(incident => {
    const priority = getIncidentPriority(incident.priority);
    const timeAgo = getTimeAgo(incident.created_at);

    html += `
      <div class="incident-card ${priority.class}">
        <div class="incident-header">
          <div class="incident-id">${incident.incident_id || 'INC-' + incident.id}</div>
          <div class="incident-priority ${priority.class}">${incident.priority || 'UNKNOWN'}</div>
        </div>
        <div class="incident-title">${incident.title || 'Incident Detected'}</div>
        <div class="incident-description">${incident.description || incident.business_impact || ''}</div>
        <div class="incident-meta">
          <span><i class="fas fa-server"></i> ${incident.affected_vms?.join(', ') || 'Multiple VMs'}</span>
          <span><i class="fas fa-clock"></i> ${timeAgo}</span>
        </div>
        <div class="incident-actions">
          <button class="btn-small btn-secondary" onclick="acknowledgeIncident('${incident.incident_id || incident.id}')">
            <i class="fas fa-check"></i> Acknowledge
          </button>
          <button class="btn-small btn-primary" onclick="viewIncidentDetails('${incident.incident_id || incident.id}')">
            <i class="fas fa-eye"></i> Details
          </button>
        </div>
      </div>
    `;
  });

  incidentsContainer.innerHTML = html;
}

function getIncidentPriority(priority) {
  switch (priority?.toLowerCase()) {
    case 'p0':
    case 'critical':
      return { class: 'p0' };
    case 'p1':
    case 'high':
      return { class: 'p1' };
    case 'p2':
    case 'medium':
      return { class: 'p2' };
    case 'p3':
    case 'low':
      return { class: 'p3' };
    case 'p4':
    case 'info':
      return { class: 'p4' };
    default:
      return { class: 'p3' };
  }
}

async function acknowledgeIncident(incidentId) {
  try {
    const res = await fetch(`${API}/incident/${incidentId}/acknowledge`, {
      method: 'POST'
    });

    if (res.ok) {
      showNotification('Incident acknowledged', 'success');
      loadIncidents(); // Refresh the list
    } else {
      throw new Error('Failed to acknowledge incident');
    }
  } catch (e) {
    console.error('Acknowledge incident error:', e);
    showNotification('Failed to acknowledge incident', 'error');
  }
}

function viewIncidentDetails(incidentId) {
  // For now, just show a notification. Could expand to show modal with details
  showNotification(`Viewing details for incident ${incidentId}`, 'info');
}

// ---------------- Topology Functions ----------------

async function loadTopology() {
  const port = document.getElementById('portSelector').value;

  try {
    await populateVMSelector();
    const vm = document.getElementById('vmSelector').value;

    // Pass VM and port for enhanced topology with failure detection
    const params = new URLSearchParams();
    if (vm) params.append('vm', vm);
    if (port) params.append('port', port);

    const url = `${API}/topology${params.toString() ? '?' + params.toString() : ''}`;
    const res = await fetch(url);
    const data = await res.json();

    if (data.error) {
      console.error('Topology error:', data.error);
      showNotification('Failed to load topology: ' + data.error, 'error');
      return;
    }

    console.log('Topology data:', data);
    renderGraph(data.nodes || [], data.edges || []);

    // Show failing components if any
    if (data.failing_components && data.failing_components.length > 0) {
      showFailingComponents(data.failing_components);
    }

  } catch (e) {
    console.error('Topology error:', e);
    showNotification('Failed to load topology', 'error');
  }
}

function showFailingComponents(failingComponents) {
  let message = `Found ${failingComponents.length} failing component(s):\n`;
  failingComponents.forEach(comp => {
    message += `• ${comp.name} (${comp.type}): ${comp.reason}\n`;
  });
  showNotification(message, 'warning');
}

// ---------------- Metrics Functions ----------------

async function updateMetrics(vm) {
  try {
    const res = await fetch(`${API}/metrics?vm=${vm}`);
    const data = await res.json();

    // Update CPU metric
    document.getElementById('cpuMetric').querySelector('.metric-value').textContent = data.cpu || '--';

    // Update Network metric
    const networkTotal = (data.network_in || 0) + (data.network_out || 0);
    document.getElementById('networkMetric').querySelector('.metric-value').textContent = networkTotal || '--';

    // Update Status metric
    document.getElementById('statusMetric').querySelector('.metric-value').textContent = data.status || '--';

  } catch (e) {
    console.error('Metrics error:', e);
  }
}

async function populateVMSelector() {
  const vmSelector = document.getElementById('vmSelector');
  const previousValue = vmSelector.value;

  try {
    const res = await fetch(`${API}/vms`);
    const data = await res.json();
    const vms = data.vms || [];

    vmSelector.innerHTML = '<option value="">Select VM...</option>';

    vms.forEach(vm => {
      const option = document.createElement('option');
      option.value = vm.name;
      option.textContent = vm.name;
      vmSelector.appendChild(option);
    });

    if (previousValue && Array.from(vmSelector.options).some(opt => opt.value === previousValue)) {
      vmSelector.value = previousValue;
      currentVM = previousValue;
    } else if (!previousValue && vms.length === 1) {
      vmSelector.value = vms[0].name;
      currentVM = vms[0].name;
      updateMetrics(currentVM);
    }

  } catch (e) {
    console.error('Failed to populate VM selector:', e);
  }
}

async function refreshTopology() {
  try {
    const res = await fetch(`${API}/refresh`, {
      method: 'POST'
    });
    const data = await res.json();

    if (!res.ok || data.error) {
      showNotification('Azure topology refresh failed: ' + (data.error || 'unknown'), 'error');
      return false;
    }

    showNotification(`Topology refreshed from Azure (${data.nodes} nodes, ${data.edges} edges)`, 'success');
    return true;
  } catch (e) {
    console.error('Refresh topology error:', e);
    showNotification('Failed to refresh topology from Azure', 'error');
    return false;
  }
}

// ---------------- Utility Functions ----------------

async function refreshAll() {
  await refreshTopology();
  await populateVMSelector();

  if (currentVM) {
    runRCA();
  } else {
    loadTopology();
    loadAlerts();
    loadIncidents();
  }
}

function getTimeAgo(timestamp) {
  if (!timestamp) return 'Just now';

  const now = new Date();
  const time = new Date(timestamp);
  const diffMs = now - time;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${diffDays}d ago`;
}

function showNotification(message, type = 'info') {
  // Create a simple notification. In a real app, you'd use a proper notification system
  console.log(`[${type.toUpperCase()}] ${message}`);

  // For now, just log to console. Could implement toast notifications
  const notification = document.createElement('div');
  notification.className = `notification notification-${type}`;
  notification.textContent = message;
  notification.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    background: var(--${type === 'error' ? 'error' : type === 'success' ? 'success' : 'info'});
    color: white;
    padding: 12px 16px;
    border-radius: 8px;
    box-shadow: var(--shadow-lg);
    z-index: 1000;
    animation: slideIn 0.3s ease;
  `;

  document.body.appendChild(notification);

  setTimeout(() => {
    notification.style.animation = 'slideOut 0.3s ease';
    setTimeout(() => notification.remove(), 300);
  }, 3000);
}

// Add notification styles dynamically
const style = document.createElement('style');
style.textContent = `
  @keyframes slideIn {
    from { transform: translateX(100%); opacity: 0; }
    to { transform: translateX(0); opacity: 1; }
  }
  @keyframes slideOut {
    from { transform: translateX(0); opacity: 1; }
    to { transform: translateX(100%); opacity: 0; }
  }
`;
document.head.appendChild(style);
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

// Duplicate runRCA removed; the original handler is already defined earlier.