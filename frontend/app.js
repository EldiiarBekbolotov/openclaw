/**
 * Hack United Sponsorship Outreach Dashboard JavaScript
 * Handles API calls, UI updates, and user interactions
 */

// API base URL - Railway backend for production, localhost for development
const RAILWAY_API_BASE = "https://openclaw-production-17905.up.railway.app";
const API_BASE =
  window.location.hostname === "localhost"
    ? "http://localhost:8000"
    : RAILWAY_API_BASE;

// DOM elements
const elements = {
  // Stats
  totalLeads: document.getElementById("total-leads"),
  emailsSent: document.getElementById("emails-sent"),
  replyRate: document.getElementById("reply-rate"),
  avgScore: document.getElementById("avg-score"),

  // Form
  addLeadForm: document.getElementById("add-lead-form"),
  formMessage: document.getElementById("form-message"),

  // Leads table
  statusFilter: document.getElementById("status-filter"),
  refreshLeadsBtn: document.getElementById("refresh-leads"),
  leadsTbody: document.getElementById("leads-tbody"),

  // Activity log
  activityLog: document.getElementById("activity-log"),
};

// Initialize the dashboard
document.addEventListener("DOMContentLoaded", function () {
  initializeDashboard();
});

function initializeDashboard() {
  // Load initial data
  loadStats();
  loadLeads();

  // Set up event listeners
  setupEventListeners();

  // Add initial activity log entry
  addActivityItem("Dashboard loaded successfully", "success");
}

function setupEventListeners() {
  // Add lead form submission
  elements.addLeadForm.addEventListener("submit", handleAddLead);

  // Status filter change
  elements.statusFilter.addEventListener("change", handleStatusFilterChange);

  // Refresh leads button
  elements.refreshLeadsBtn.addEventListener("click", () => {
    loadLeads();
    addActivityItem("Leads refreshed", "success");
  });
}

async function loadStats() {
  try {
    console.log("Loading stats from:", `${API_BASE}/api/get_campaign_stats`);
    const response = await fetch(`${API_BASE}/api/get_campaign_stats`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    console.log("Stats data:", data);

    // Update stats display
    elements.totalLeads.textContent = data.total_leads || 0;
    elements.emailsSent.textContent = data.emails_sent || 0;
    elements.replyRate.textContent = `${data.reply_rate_percent || 0}%`;
    elements.avgScore.textContent = `${data.average_score || 0}/10`;

    addActivityItem("Campaign stats loaded", "success");
  } catch (error) {
    console.error("Error loading stats:", error);
    addActivityItem(`Failed to load stats: ${error.message}`, "error");

    // Show error in UI
    elements.totalLeads.textContent = "Error";
    elements.emailsSent.textContent = "Error";
    elements.replyRate.textContent = "Error";
    elements.avgScore.textContent = "Error";
  }
}

async function loadLeads(statusFilter = "") {
  try {
    // Show loading state
    elements.leadsTbody.innerHTML =
      '<tr><td colspan="7" class="loading">Loading leads...</td></tr>';

    // Build query string
    const params = new URLSearchParams();
    if (statusFilter) {
      params.append("status", statusFilter);
    }
    params.append("limit", "50"); // Load up to 50 leads

    const url = `${API_BASE}/api/get_leads?${params}`;
    console.log("Loading leads from:", url);
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    console.log(`Loaded ${data.leads?.length || 0} leads:`, data);

    // Clear loading state
    elements.leadsTbody.innerHTML = "";

    if (data.leads.length === 0) {
      elements.leadsTbody.innerHTML =
        '<tr><td colspan="7" class="loading">No leads found</td></tr>';
      return;
    }

    // Populate table
    data.leads.forEach((lead) => {
      const row = createLeadRow(lead);
      elements.leadsTbody.appendChild(row);
    });

    addActivityItem(`Loaded ${data.leads.length} leads`, "success");
  } catch (error) {
    console.error("Error loading leads:", error);
    addActivityItem(`Failed to load leads: ${error.message}`, "error");

    // Show error in table
    elements.leadsTbody.innerHTML =
      '<tr><td colspan="7" class="loading">Error loading leads</td></tr>';
  }
}

function createLeadRow(lead) {
  const row = document.createElement("tr");

  // Format score with color coding
  const score = lead.score || "";
  const scoreClass =
    score >= 8 ? "high-score" : score >= 6 ? "medium-score" : "low-score";

  // Format status with appropriate styling
  const status = lead.status || "";
  const statusClass = getStatusClass(status);

  row.innerHTML = `
        <td>${escapeHtml(lead.company || "")}</td>
        <td>${escapeHtml(lead.email || "")}</td>
        <td>${escapeHtml(lead.industry || "")}</td>
        <td class="${scoreClass}">${score}</td>
        <td class="${statusClass}">${status}</td>
        <td>${escapeHtml(lead.sent_date || "")}</td>
        <td>${escapeHtml(lead.reply || "")}</td>
    `;

  return row;
}

function getStatusClass(status) {
  const statusLower = (status || "").toLowerCase();
  switch (statusLower) {
    case "sent":
      return "status-sent";
    case "replied":
      return "status-replied";
    case "bounced":
      return "status-bounced";
    case "failed":
      return "status-failed";
    default:
      return "";
  }
}

async function handleAddLead(event) {
  event.preventDefault();

  // Clear previous messages
  elements.formMessage.className = "";
  elements.formMessage.textContent = "";

  // Get form data
  const formData = new FormData(event.target);
  const leadData = {
    email: (formData.get("email") || "").trim(),
    company: (formData.get("company") || "").trim(),
    industry: (formData.get("industry") || "").trim(),
    website: (formData.get("website") || "").trim(),
    description: (formData.get("description") || "").trim(),
    source: "Manual entry",
  };

  // Basic validation
  if (!leadData.email || !leadData.company) {
    showFormMessage("Please fill in all required fields", "error");
    return;
  }

  // Get submit button outside try block so it's available in finally
  const submitBtn = event.target.querySelector('button[type="submit"]');
  const originalText = submitBtn.textContent;

  try {
    // Show loading state
    submitBtn.textContent = "Adding...";
    submitBtn.disabled = true;

    console.log("Sending lead data:", leadData);
    const response = await fetch(`${API_BASE}/api/add_lead`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(leadData),
    });

    const result = await response.json();
    console.log(`API Response (${response.status}):`, result);

    if (response.ok) {
      showFormMessage("Lead added successfully!", "success");
      event.target.reset(); // Clear form
      loadLeads(); // Refresh leads list
      loadStats(); // Refresh stats
      addActivityItem(`Added lead: ${leadData.company}`, "success");
    } else {
      const errorMsg = result.error || result.message || `Server error (${response.status})`;
      showFormMessage(errorMsg, "error");
      addActivityItem(`Failed to add lead: ${errorMsg}`, "error");
    }
  } catch (error) {
    console.error("Network error:", error);
    const errorMsg = `Network error: ${error.message}`;
    showFormMessage(errorMsg, "error");
    addActivityItem(errorMsg, "error");
  } finally {
    // Reset button state
    submitBtn.textContent = originalText;
    submitBtn.disabled = false;
  }
}

function handleStatusFilterChange() {
  const status = elements.statusFilter.value;
  loadLeads(status);
  addActivityItem(`Filtered leads by status: ${status || "all"}`, "success");
}

function showFormMessage(message, type) {
  elements.formMessage.textContent = message;
  elements.formMessage.className = type;
}

function addActivityItem(message, type = "info") {
  const item = document.createElement("div");
  item.className = `activity-item ${type}`;
  item.textContent = `${new Date().toLocaleTimeString()}: ${message}`;

  // Add to top of activity log
  elements.activityLog.insertBefore(item, elements.activityLog.firstChild);

  // Keep only last 10 items
  while (elements.activityLog.children.length > 10) {
    elements.activityLog.removeChild(elements.activityLog.lastChild);
  }
}

// Utility function to escape HTML
function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// Auto-refresh stats every 5 minutes
setInterval(
  () => {
    loadStats();
    addActivityItem("Auto-refreshed stats", "success");
  },
  5 * 60 * 1000,
);
