// Dependency-free PDF report generator.
//
// Opens a print-optimized document in a new window and triggers the browser's
// print dialog, where the user can choose "Save as PDF". This avoids any
// third-party PDF library (handy in restricted-network environments).

const RISK_COLORS = {
  Low: "#16a34a",
  Moderate: "#d97706",
  High: "#dc2626",
};

// Human-readable labels + ordering for the patient's questionnaire answers.
const NUMERIC_FIELDS = [
  ["age", "Age (years)"],
  ["weight_kg", "Weight (kg)"],
  ["height_cm", "Height (cm)"],
  ["cycle_length", "Avg. cycle length (days)"],
];
const BOOLEAN_FIELDS = [
  ["cycle_irregular", "Irregular menstrual cycles"],
  ["weight_gain", "Recent unexplained weight gain"],
  ["hair_growth", "Excess hair growth (face/body)"],
  ["skin_darkening", "Skin darkening (neck/underarms)"],
  ["hair_loss", "Hair loss / thinning on scalp"],
  ["pimples", "Frequent acne / pimples"],
  ["fast_food", "Frequent fast food"],
  ["exercise", "Regular exercise"],
  ["mood_swings", "Frequent mood swings"],
  ["family_history", "Family history of PCOS"],
];

function escapeHtml(str = "") {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function buildResponses(responses) {
  if (!responses) return "";

  const row = (label, value, isYes) => `
    <div class="resp">
      <span class="resp-k">${escapeHtml(label)}</span>
      <span class="resp-v${isYes ? " yes" : ""}">${escapeHtml(String(value))}</span>
    </div>`;

  const numeric = NUMERIC_FIELDS.filter(([k]) => responses[k] != null)
    .map(([k, label]) => row(label, responses[k], false))
    .join("");

  const boolean = BOOLEAN_FIELDS.filter(([k]) => k in responses)
    .map(([k, label]) => row(label, responses[k] ? "Yes" : "No", !!responses[k]))
    .join("");

  return `
    <h2>Assessment responses</h2>
    <div class="resp-grid">${numeric}${boolean}</div>`;
}

export function downloadReport({ result, name, responses }) {
  const { risk_level, probability, bmi, recommendations, disclaimer } = result;
  const pct = Math.round(probability * 100);
  const color = RISK_COLORS[risk_level] || "#334155";
  const displayName = name?.trim() || "Not provided";
  const now = new Date();
  const dateStr = now.toLocaleString();
  const fileTitle = `PCOS-Care-Report-${(name?.trim() || "user").replace(/\s+/g, "_")}`;

  const recRows = recommendations
    .map(
      (r) => `
        <div class="rec">
          <span class="tag">${escapeHtml(r.category)}</span>
          <div class="rec-body">
            <div class="rec-title">${escapeHtml(r.title)}</div>
            <div class="rec-detail">${escapeHtml(r.detail)}</div>
          </div>
        </div>`
    )
    .join("");

  const html = `<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<title>${escapeHtml(fileTitle)}</title>
<style>
  * { box-sizing: border-box; }
  body {
    font-family: "Segoe UI", Arial, sans-serif;
    color: #1e293b;
    margin: 0;
    padding: 32px 40px;
  }
  .header {
    display: flex; justify-content: space-between; align-items: flex-start;
    border-bottom: 3px solid #db2777; padding-bottom: 14px; margin-bottom: 20px;
  }
  .brand { font-size: 22px; font-weight: 800; color: #be185d; }
  .brand span { color: #334155; }
  .subtitle { font-size: 12px; color: #64748b; margin-top: 2px; }
  .meta { font-size: 12px; color: #475569; text-align: right; }
  .meta b { color: #1e293b; }
  .grid { display: flex; gap: 14px; margin: 18px 0; }
  .box {
    flex: 1; border: 1px solid #e2e8f0; border-radius: 10px; padding: 14px 16px;
  }
  .box .k { font-size: 11px; text-transform: uppercase; letter-spacing: .04em; color: #64748b; }
  .box .v { font-size: 26px; font-weight: 800; margin-top: 4px; }
  .risk-pill {
    display: inline-block; padding: 4px 14px; border-radius: 999px;
    color: #fff; font-weight: 700; font-size: 14px; background: ${color};
  }
  h2 { font-size: 15px; margin: 22px 0 10px; color: #0f172a; }
  .rec {
    display: flex; gap: 12px; padding: 10px 0; border-top: 1px solid #f1f5f9;
    page-break-inside: avoid;
  }
  .tag {
    flex-shrink: 0; align-self: flex-start; font-size: 10px; font-weight: 700;
    background: #fce7f3; color: #be185d; padding: 3px 8px; border-radius: 999px;
    text-transform: uppercase; letter-spacing: .03em;
  }
  .rec-title { font-weight: 700; font-size: 13px; }
  .rec-detail { font-size: 12px; color: #475569; margin-top: 2px; line-height: 1.5; }
  .resp-grid {
    display: grid; grid-template-columns: 1fr 1fr; gap: 6px 24px;
  }
  .resp {
    display: flex; justify-content: space-between; gap: 10px;
    border-bottom: 1px solid #f1f5f9; padding: 6px 0; font-size: 12px;
    page-break-inside: avoid;
  }
  .resp-k { color: #475569; }
  .resp-v { font-weight: 600; color: #1e293b; }
  .resp-v.yes { color: #be185d; }
  .disclaimer {
    margin-top: 24px; border: 1px solid #fcd34d; background: #fffbeb;
    color: #92400e; font-size: 11px; line-height: 1.5; padding: 12px 14px;
    border-radius: 8px;
  }
  .footer {
    margin-top: 18px; font-size: 10px; color: #94a3b8; text-align: center;
    border-top: 1px solid #e2e8f0; padding-top: 10px;
  }
  @media print { body { padding: 0; } }
</style>
</head>
<body>
  <div class="header">
    <div>
      <div class="brand">PCOS Care <span>AI</span></div>
      <div class="subtitle">Preliminary Risk Assessment Report</div>
    </div>
    <div class="meta">
      <div><b>Name:</b> ${escapeHtml(displayName)}</div>
      <div><b>Date:</b> ${escapeHtml(dateStr)}</div>
    </div>
  </div>

  <div class="grid">
    <div class="box">
      <div class="k">Risk level</div>
      <div class="v"><span class="risk-pill">${escapeHtml(risk_level)}</span></div>
    </div>
    <div class="box">
      <div class="k">Estimated probability</div>
      <div class="v" style="color:${color}">${pct}%</div>
    </div>
    <div class="box">
      <div class="k">BMI</div>
      <div class="v">${bmi}</div>
    </div>
  </div>

  ${buildResponses(responses)}

  <h2>Personalized recommendations</h2>
  ${recRows}

  <div class="disclaimer"><b>Disclaimer:</b> ${escapeHtml(disclaimer)}</div>

  <div class="footer">
    Generated by PCOS Care AI &middot; This report is an AI-generated estimate and
    is not a medical diagnosis.
  </div>

  <script>
    window.onload = function () {
      window.focus();
      window.print();
    };
  </script>
</body>
</html>`;

  const win = window.open("", "_blank");
  if (!win) {
    alert("Please allow pop-ups to download the PDF report.");
    return;
  }
  win.document.open();
  win.document.write(html);
  win.document.close();
}
