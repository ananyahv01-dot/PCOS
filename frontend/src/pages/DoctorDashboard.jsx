import { useEffect, useMemo, useState } from "react";
import { FileDown, FileUp, Loader2, Stethoscope, X } from "lucide-react";
import {
  getAssessment,
  getDoctorAssessments,
  uploadPrescription,
} from "../api.js";
import { downloadReport } from "../report.js";
import { useAuth } from "../auth.jsx";

const RISK_COLORS = { Low: "#16a34a", Moderate: "#d97706", High: "#dc2626" };

function CountCard({ label, value, color }) {
  return (
    <div className="card">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="mt-1 text-3xl font-extrabold" style={{ color }}>
        {value}
      </p>
    </div>
  );
}

// Modal for uploading a prescription file against a patient's assessment.
function UploadModal({ row, onClose, onUploaded }) {
  const [file, setFile] = useState(null);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    if (!file) return setError("Please choose a file.");
    setBusy(true);
    setError("");
    try {
      await uploadPrescription({
        patientEmail: row.user_email,
        note,
        assessmentId: row.id,
        file,
      });
      onUploaded(`Prescription uploaded for ${row.name || row.user_email}.`);
    } catch (err) {
      setError(err?.response?.data?.detail?.toString() || "Upload failed.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-40 grid place-items-center bg-black/40 p-4">
      <div className="card w-full max-w-md">
        <div className="flex items-start justify-between">
          <h3 className="font-bold text-slate-800">Upload prescription</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <X size={20} />
          </button>
        </div>
        <p className="mt-1 text-sm text-slate-500">
          For <span className="font-medium">{row.name || "patient"}</span> ·{" "}
          {row.user_email}
        </p>

        <form onSubmit={submit} className="mt-4 space-y-4">
          <div>
            <label className="label">Prescription file (PDF or image)</label>
            <input
              type="file"
              accept=".pdf,image/png,image/jpeg,image/webp"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="block w-full text-sm text-slate-600 file:mr-3 file:rounded-lg file:border-0 file:bg-brand-50 file:px-4 file:py-2 file:font-semibold file:text-brand-700 hover:file:bg-brand-100"
              required
            />
          </div>
          <div>
            <label className="label">Note (optional)</label>
            <textarea
              className="input"
              rows={3}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="e.g. Start Metformin 500mg, review in 3 months"
            />
          </div>

          {error && (
            <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
              {error}
            </div>
          )}

          <div className="flex justify-end gap-2">
            <button type="button" className="btn-ghost" onClick={onClose}>
              Cancel
            </button>
            <button className="btn-primary" disabled={busy}>
              {busy ? <Loader2 size={18} className="animate-spin" /> : "Upload"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function DoctorDashboard() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("All");
  const [uploadRow, setUploadRow] = useState(null);
  const [busyReport, setBusyReport] = useState(null);
  const [toast, setToast] = useState("");

  const load = () => {
    setLoading(true);
    getDoctorAssessments()
      .then(setData)
      .catch(() => setError("Could not load assessments."))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const rows = useMemo(() => {
    if (!data) return [];
    return filter === "All"
      ? data.assessments
      : data.assessments.filter((a) => a.risk_level === filter);
  }, [data, filter]);

  const onReport = async (row) => {
    setBusyReport(row.id);
    try {
      const detail = await getAssessment(row.id);
      downloadReport({
        result: detail,
        name: detail.name,
        responses: detail.responses,
      });
    } catch {
      setError("Could not generate the report for this assessment.");
    } finally {
      setBusyReport(null);
    }
  };

  const onUploaded = (msg) => {
    setUploadRow(null);
    setToast(msg);
    setTimeout(() => setToast(""), 4000);
  };

  if (loading) {
    return (
      <div className="grid place-items-center py-32 text-slate-400">
        <Loader2 className="animate-spin" size={30} />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <div className="flex items-center gap-3">
        <span className="grid h-11 w-11 place-items-center rounded-xl bg-brand-50 text-brand-600">
          <Stethoscope size={22} />
        </span>
        <div>
          <h1 className="text-3xl font-extrabold text-slate-900">Doctor dashboard</h1>
          <p className="text-sm text-slate-500">
            {user?.name} · Patient assessment review
          </p>
        </div>
      </div>

      {error && (
        <div className="mt-4 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}
      {toast && (
        <div className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">
          {toast}
        </div>
      )}

      <div className="mt-6 grid gap-4 sm:grid-cols-4">
        <CountCard label="Total" value={data?.total || 0} color="#0f172a" />
        <CountCard label="High risk" value={data?.counts.High || 0} color={RISK_COLORS.High} />
        <CountCard label="Moderate risk" value={data?.counts.Moderate || 0} color={RISK_COLORS.Moderate} />
        <CountCard label="Low risk" value={data?.counts.Low || 0} color={RISK_COLORS.Low} />
      </div>

      <div className="card mt-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="font-semibold text-slate-800">Assessments</h2>
          <div className="flex gap-1 rounded-lg bg-slate-100 p-1">
            {["All", "High", "Moderate", "Low"].map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`rounded-md px-3 py-1 text-sm font-medium transition ${
                  filter === f ? "bg-white text-brand-700 shadow-sm" : "text-slate-500"
                }`}
              >
                {f}
              </button>
            ))}
          </div>
        </div>

        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500">
                <th className="pb-2">Date</th>
                <th className="pb-2">Patient</th>
                <th className="pb-2">Account</th>
                <th className="pb-2">Age</th>
                <th className="pb-2">BMI</th>
                <th className="pb-2">Prob.</th>
                <th className="pb-2">Risk</th>
                <th className="pb-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 && (
                <tr>
                  <td colSpan="8" className="py-8 text-center text-slate-400">
                    No assessments for this filter.
                  </td>
                </tr>
              )}
              {rows.map((a) => (
                <tr key={a.id} className="border-t border-slate-100">
                  <td className="py-2 text-slate-500">
                    {new Date(a.created_at).toLocaleString()}
                  </td>
                  <td className="py-2 font-medium text-slate-700">{a.name || "—"}</td>
                  <td className="py-2 text-slate-500">{a.user_email || "guest"}</td>
                  <td className="py-2">{a.age}</td>
                  <td className="py-2">{a.bmi}</td>
                  <td className="py-2">{Math.round(a.probability * 100)}%</td>
                  <td className="py-2">
                    <span
                      className="rounded-full px-2 py-0.5 text-xs font-semibold text-white"
                      style={{ backgroundColor: RISK_COLORS[a.risk_level] }}
                    >
                      {a.risk_level}
                    </span>
                  </td>
                  <td className="py-2">
                    <div className="flex gap-1.5">
                      <button
                        onClick={() => onReport(a)}
                        disabled={busyReport === a.id}
                        className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                        title="Download PDF report"
                      >
                        {busyReport === a.id ? (
                          <Loader2 size={13} className="animate-spin" />
                        ) : (
                          <FileDown size={13} />
                        )}
                        Report
                      </button>
                      <button
                        onClick={() => setUploadRow(a)}
                        disabled={!a.user_email}
                        title={
                          a.user_email
                            ? "Upload prescription"
                            : "Guest assessment — no patient account to attach to"
                        }
                        className="inline-flex items-center gap-1 rounded-lg border border-brand-200 px-2.5 py-1 text-xs font-semibold text-brand-700 hover:bg-brand-50 disabled:opacity-40 disabled:cursor-not-allowed"
                      >
                        <FileUp size={13} /> Rx
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {uploadRow && (
        <UploadModal
          row={uploadRow}
          onClose={() => setUploadRow(null)}
          onUploaded={onUploaded}
        />
      )}
    </div>
  );
}
